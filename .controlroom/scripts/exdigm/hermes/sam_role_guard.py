#!/usr/bin/env python3
"""Fail closed when Sam tries to execute Exdigm operational-error work."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import sys
import time


POLICY = (
    "Exdigm 운영 오류 문맥에서 샘은 통신만 담당합니다. DB 조회·보고·실제 주인님 답변의 "
    "결정 영수증 기록만 하세요. 조사·수정·테스트·Git·위임·배포·운영 검증은 main 서버의 "
    "systemd Codex 작업자 책임입니다. 프로세스·서비스도 조작하지 마세요. '문제해결', "
    "'수정해', '승인 진행해', '배포해'라는 직접 표현도 샘의 기술 실행 권한을 열지 않습니다."
)
PROJECT_PATTERN = re.compile(r"(?:\bexdigm\b|엑스다임)", re.IGNORECASE)
ERROR_PATTERN = re.compile(
    r"(?:운영\s*(?:오류|에러)|자동\s*수정|오류|에러|operational[ _-]*error|"
    r"repair|pipeline|파이프라인|트랙|approve_(?:change|deploy|close)|"
    r"external_wait|main\s*codex|통신병)",
    re.IGNORECASE,
)
TARGET_MARKERS = (
    "/home/chaconne/controlroom/.controlroom/scripts/exdigm",
    "/home/chaconne/controlroom/exdigm/skills/exdigm-error-control",
    "/home/chaconne/controlroom/exdigm/docs/operational-error-event-pipeline",
    "/home/chaconne/controlroom/exdigm/docs/operational-error-triage-repair-policy",
    "/home/chaconne/.hermes/scripts/exdigm",
    "/home/chaconne/.hermes/skills/exdigm-error-control",
    "/etc/exdigm-repair",
    "/etc/exdigm-deploy",
    "/home/exdigm-repair",
    "/home/exdigm-deploy",
    "exdigm-error-control",
    "exdigm_error_context.py",
    "update_exdigm_error_checkpoint.py",
    "exdigm-repair.service",
    "exdigm-repair.timer",
    "exdigm-deploy.service",
    "exdigm-deploy.timer",
    "130323c787e0",
)
RESTRICTED_TOOLS = {
    "terminal",
    "patch",
    "write_file",
    "read_file",
    "search_files",
    "execute_code",
    "delegate_task",
    "skill_manage",
    "cronjob_manage",
    "computer",
    "browser",
    "web_search",
    "web_extract",
    "memory",
    "tool_search",
    "tool_describe",
    "tool_call",
    "vision_analyze",
    "image_gen",
}
RESTRICTED_TOOL_PREFIXES = (
    "browser_",
    "computer_",
    "cronjob_",
    "web_",
    "tool_",
    "vision_",
    "image_",
)
DECISION_SCRIPT = (
    "/home/chaconne/controlroom/exdigm/skills/"
    "exdigm-error-control/scripts/decision.py"
)
MONITOR_SCRIPTS = {
    "/home/chaconne/.hermes/scripts/exdigm_error_context.py",
    "/home/chaconne/.hermes/scripts/update_exdigm_error_checkpoint.py",
}
PYTHON_EXECUTABLES = {
    "python",
    "python3",
    "/usr/bin/python3",
    "/home/chaconne/.hermes/hermes-agent/venv/bin/python",
    "/home/chaconne/.hermes/hermes-agent/venv/bin/python3",
}


def _runtime_root() -> Path:
    home = Path(os.environ.get("HERMES_HOME", "/home/chaconne/.hermes"))
    return home / "runtime" / "exdigm-sam-role-guard"


def _marker_path(session_id: str) -> Path:
    digest = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
    return _runtime_root() / f"{digest}.json"


def _text(value) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError):
        return str(value)


def _is_error_context(payload: dict) -> bool:
    extra = payload.get("extra") if isinstance(payload.get("extra"), dict) else {}
    current = str(extra.get("user_message") or "")
    history = extra.get("conversation_history")
    history_text = ""
    if isinstance(history, list):
        recent = history[-24:]
        history_text = "\n".join(
            str(item.get("content") or "")
            for item in recent
            if isinstance(item, dict) and item.get("role") in {"user", "assistant"}
        )
    combined = f"{current}\n{history_text}"
    return bool(PROJECT_PATTERN.search(combined) and ERROR_PATTERN.search(combined))


def _mark(session_id: str, extra: dict | None = None) -> None:
    extra = extra or {}
    root = _runtime_root()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = _marker_path(session_id)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(
            {
                "session_id": session_id,
                "task_id": str(extra.get("task_id") or ""),
                "turn_id": str(extra.get("turn_id") or ""),
                "marked_at": time.time(),
            }
        ),
        encoding="utf-8",
    )
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def _clear(session_id: str) -> None:
    if session_id:
        _marker_path(session_id).unlink(missing_ok=True)


def _is_marked(session_id: str, extra: dict | None = None) -> bool:
    if not session_id:
        return False
    path = _marker_path(session_id)
    if not path.is_file():
        return False
    try:
        marker = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return True
    extra = extra or {}
    compared = False
    for key in ("task_id", "turn_id"):
        marked_value = str(marker.get(key) or "")
        current_value = str(extra.get(key) or "")
        if marked_value and current_value:
            compared = True
            if marked_value != current_value:
                return False
    if compared:
        return True
    marked_at = marker.get("marked_at")
    return isinstance(marked_at, (int, float)) and time.time() - marked_at <= 7200


def _has_shell_control(command: str) -> bool:
    return bool(re.search(r"(?:[;&|><`\n]|\$\(|\$\{)", command))


def _allowed_helper(tool_input: dict) -> bool:
    command = tool_input.get("command")
    if not isinstance(command, str) or not command.strip() or _has_shell_control(command):
        return False
    try:
        tokens = shlex.split(command)
    except ValueError:
        return False
    if not tokens:
        return False
    script_indexes = [
        index
        for index, token in enumerate(tokens)
        if token == DECISION_SCRIPT or token in MONITOR_SCRIPTS
    ]
    if len(script_indexes) != 1:
        return False
    index = script_indexes[0]
    if index == 0:
        prefix_ok = True
    else:
        prefix_ok = index == 1 and tokens[0] in PYTHON_EXECUTABLES
    if not prefix_ok:
        return False
    script = tokens[index]
    if script == DECISION_SCRIPT:
        return len(tokens) > index + 1 and tokens[index + 1] in {
            "inspect",
            "decide",
            "deliver",
        }
    return len(tokens) == index + 1


def evaluate(payload: dict) -> dict:
    event = payload.get("hook_event_name")
    session_id = str(payload.get("session_id") or "")
    if event == "pre_llm_call":
        extra = payload.get("extra") if isinstance(payload.get("extra"), dict) else {}
        if session_id and _is_error_context(payload):
            _mark(session_id, extra)
            return {"context": POLICY}
        _clear(session_id)
        return {}
    if event != "pre_tool_call":
        return {}
    tool_name = str(payload.get("tool_name") or "")
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        tool_input = {}
    target_text = f"{_text(tool_input)}\n{payload.get('cwd') or ''}".lower()
    target = any(marker.lower() in target_text for marker in TARGET_MARKERS)
    extra = payload.get("extra") if isinstance(payload.get("extra"), dict) else {}
    locked = _is_marked(session_id, extra)
    if tool_name == "terminal" and (locked or target) and _allowed_helper(tool_input):
        return {}
    restricted = tool_name in RESTRICTED_TOOLS or tool_name.startswith(
        RESTRICTED_TOOL_PREFIXES
    )
    if restricted and (locked or target):
        return {
            "action": "block",
            "message": (
                "Exdigm 운영 오류에서 Sam은 통신 전담입니다. 이 기술 실행은 차단됐습니다. "
                "현재 트랙의 실제 사용자 결정만 decision.py로 기록하고, 조사·수정·테스트·"
                "배포는 main systemd Codex 작업자에게 맡기세요."
            ),
        }
    return {}


def main() -> None:
    payload = json.load(sys.stdin)
    if not isinstance(payload, dict):
        raise ValueError("Hook payload must be an object")
    print(json.dumps(evaluate(payload), ensure_ascii=False))


if __name__ == "__main__":
    main()
