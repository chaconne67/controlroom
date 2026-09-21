#!/usr/bin/env python3
"""Run one main-server Codex investigation, approved repair, or verification."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import time
import uuid

from repair_once import (
    park_repair,
    preflight,
    run_command,
    run_official_verification,
    save_json,
    validate_test_targets,
    workspace_lock,
)


CATEGORIES = ["user_action", "expected_stop", "external_wait", "defect", "unclassified"]
ACTIONS = [
    "investigate", "user_action", "external_wait", "approve_change",
    "approve_deploy", "approve_close", "none",
]
STRING_DETAILS = [
    "root_cause", "owner", "required_action", "resume_condition", "proposal",
    "alternatives", "recommendation_reason", "impact", "verification", "rollback",
    "commit", "stop_reason", "outcome_verification",
]
DETAILS = [*STRING_DETAILS, "test_targets"]
SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "category": {"type": "string", "enum": CATEGORIES},
        "next_action": {"type": "string", "enum": ACTIONS},
        "status": {"type": "string", "enum": ["succeeded", "failed"]},
        "action": {"type": "string"},
        "details": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                **{key: {"type": "string"} for key in STRING_DETAILS},
                "test_targets": {
                    "type": "array", "items": {"type": "string"}, "maxItems": 20,
                },
            },
            "required": DETAILS,
        },
        "split_tracks": {
            "type": "array",
            "minItems": 0,
            "maxItems": 10,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "title": {"type": "string"},
                    "scope": {"type": "string"},
                    "blocking": {"type": "boolean"},
                },
                "required": ["title", "scope", "blocking"],
            },
        },
    },
    "required": ["category", "next_action", "status", "action", "details", "split_tracks"],
}


def prompt_for(case, config):
    track = case["selected_track"]
    stage = track["next_action"]
    stage_rules = {
        "investigate": """이번 단계는 조사와 수정안 작성만 합니다. 코드·설정·데이터·Git 상태를 바꾸지 마세요.
오류 한 건 안에 독립적으로 승인·실행해야 할 실패가 둘 이상이면 먼저 경계를 정하고 split_tracks에 2~10개로
분해하세요. 한 원인과 한 수정/검증/배포로 함께 닫히는 실패만 같은 트랙에 둡니다. 코드 변경이 필요하면
확인된 원인, 권장안, 대안과 선택 이유, 영향, 검증, 복구안을 작성해 approve_change로 끝내세요.""",
        "repair": """주인님이 이 트랙의 approve_change 요청을 승인했습니다. handling_context에 결박된 정확한
제안 범위만 구현하세요. 새 범위나 다른 해결책이 필요하면 임의로 넓히지 말고 새 approve_change로 돌아가세요.
공식 debug 검사, catalog 갱신, code-review-loop, 깨끗한 커밋을 완료한 뒤 approve_deploy를 요청하세요.""",
        "verify_result": """승인된 커밋의 운영 배포는 끝났습니다. 코드·설정·데이터를 바꾸지 말고 원래 실패
업무, 같은 원인의 변형, 관련 기존 성공 흐름이 실제 운영 결과를 생산하는지 확인하세요. 프로그램 상태만
보지 말고 필수 결과의 생산·전달·사용을 확인한 뒤 approve_close를 요청하세요.""",
    }[stage]
    return f"""Exdigm 운영 오류 사건의 처리 트랙 한 건을 담당하는 메인 서버 Codex입니다.
샘은 주인님과 DB 사이의 통신만 담당하며 조사·수정·검증·배포를 실행하지 않습니다. 주인님의 결정을
대신 만들거나 기록하지 말고, 기술 실행 결과만 출력하세요.

{stage_rules}

먼저 이 조정실의 AGENTS.md, docs/README.md, operational-error-event-pipeline-20260921.md와
operational-error-triage-repair-policy-20260918.md를 읽고
관련 스킬과 기존 공식 경로를 따르세요. 문제해결 절차, SSP, 최소 구현, 기존 변경 보존을 적용하세요.
실제 주인님만 제공할 수 있는 자료·인증·새 권한·업무 선택이면 user_action, 외부 시스템/담당자 조건이면
external_wait를 사용합니다. 근거 없이 none으로 닫거나 값을 지어내지 마세요. 운영 배포, 운영 DB/권한 변경,
push, 사용자 승인 대행, 실고객 메시지 발송은 이 실행에서 금지됩니다.

원격 코드 연결: {json.dumps(config['code_ssh'], ensure_ascii=False)}
디버깅 경로: {config['debug_root']}
최종 응답은 제공된 JSON schema를 정확히 따르고 없는 문자열 근거는 빈 문자열, 분해하지 않으면
split_tracks는 빈 배열로 두세요.
사건과 선택 트랙 JSON:\n{json.dumps(case, ensure_ascii=False)}
"""


def validate_result(result, current_action):
    if not isinstance(result, dict) or set(result) != set(SCHEMA["required"]):
        raise ValueError("Result keys do not match the pipeline output contract")
    if (
        result["category"] not in CATEGORIES
        or result["next_action"] not in ACTIONS
        or result["status"] not in {"succeeded", "failed"}
    ):
        raise ValueError("Invalid classification or next action")
    if not isinstance(result["action"], str) or not 1 <= len(result["action"].strip()) <= 8000:
        raise ValueError("Missing or oversized observed result")
    details = result["details"]
    if (
        not isinstance(details, dict)
        or set(details) != set(DETAILS)
        or not all(isinstance(details[key], str) for key in STRING_DETAILS)
        or not isinstance(details["test_targets"], list)
    ):
        raise ValueError("Invalid evidence details")
    splits = result["split_tracks"]
    if not isinstance(splits, list):
        raise ValueError("Split tracks must be a list")
    if splits:
        if current_action != "investigate" or result["next_action"] != "investigate":
            raise ValueError("Only investigation can split a failure track")
        if not 2 <= len(splits) <= 10:
            raise ValueError("A split needs two to ten child tracks")
        if any(
            not isinstance(item, dict)
            or set(item) != {"title", "scope", "blocking"}
            or not isinstance(item["title"], str)
            or not item["title"].strip()
            or len(item["title"]) > 300
            or not isinstance(item["scope"], str)
            or not item["scope"].strip()
            or len(item["scope"]) > 8000
            or not isinstance(item["blocking"], bool)
            for item in splits
        ):
            raise ValueError("Invalid split track contract")
        if not any(item["blocking"] for item in splits):
            raise ValueError("A split must preserve at least one blocking track")
        if details["test_targets"]:
            raise ValueError("Track splitting cannot claim repair verification")
        return result
    allowed = {
        "investigate": {"approve_change", "user_action", "external_wait", "none"},
        "repair": {"approve_deploy", "approve_change", "user_action", "external_wait"},
        "verify_result": {"approve_close", "approve_change", "user_action", "external_wait"},
    }[current_action]
    if result["next_action"] not in allowed:
        raise ValueError("Result is not valid for the current pipeline stage")
    if (
        result["status"] == "failed"
        and result["next_action"] not in {"user_action", "external_wait"}
    ):
        raise ValueError("A failed execution cannot advance the pipeline")
    targets = details["test_targets"]
    if result["next_action"] == "approve_deploy":
        validate_test_targets(targets)
    elif targets:
        raise ValueError("Focused test targets belong only to a deployment request")
    required = {
        "user_action": ["owner", "required_action", "resume_condition", "verification", "stop_reason"],
        "external_wait": ["owner", "resume_condition", "verification", "stop_reason"],
        "approve_change": [
            "root_cause", "proposal", "alternatives", "recommendation_reason",
            "impact", "verification", "rollback",
        ],
        "approve_deploy": ["root_cause", "commit", "verification", "rollback"],
        "approve_close": ["root_cause", "verification", "outcome_verification"],
        "none": ["stop_reason"],
    }[result["next_action"]]
    if result["category"] == "defect" and "root_cause" not in required:
        required.append("root_cause")
    if any(not details[key].strip() for key in required):
        raise ValueError("Missing required pipeline evidence: " + ", ".join(required))
    if result["next_action"] == "none" and result["category"] != "expected_stop":
        raise ValueError("Investigation may close directly only for a confirmed expected stop")
    return result


def _receipt_hash(path):
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _record(config, payload):
    return json.loads(
        run_command(
            [*config["record_command"], "pipeline", "--json-input"],
            payload=json.dumps(payload, ensure_ascii=False),
        )
    )


def execute_once(config, state_root):
    import fcntl

    os.umask(0o077)
    state_root.mkdir(parents=True, exist_ok=True)
    with (state_root / "launcher.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        active = state_root / "active.json"
        if active.exists():
            run = json.loads(active.read_text(encoding="utf-8"))
        else:
            run = {"id": str(uuid.uuid4()), "baseline": preflight(config)}
            save_json(active, run)
        directory = state_root / run["id"]
        directory.mkdir(exist_ok=True)
        outcome = {"state": "no_work"}
        with workspace_lock(config, run["id"]) as release:
            case_path = directory / "case.json"
            result_path = directory / "result.json"
            if not case_path.exists():
                case = json.loads(
                    run_command(
                        [
                            *config["record_command"], "pipeline", "claim",
                            "--mode", "repair", "--automation-run", run["id"],
                        ]
                    )
                )
                if case is None:
                    release.append(True)
                else:
                    save_json(case_path, case)
            if case_path.exists():
                case = json.loads(case_path.read_text(encoding="utf-8"))
                track = case["selected_track"]
                payload_path = directory / "result-payload.json"
                interrupted_path = directory / "interrupted-payload.json"
                if interrupted_path.exists():
                    _record(config, json.loads(interrupted_path.read_text(encoding="utf-8")))
                    raise RuntimeError("Previous execution is incomplete; reconcile it before resuming")
                if payload_path.exists():
                    payload = json.loads(payload_path.read_text(encoding="utf-8"))
                else:
                    current = json.loads(
                        run_command(
                            [
                                *config["record_command"], "pipeline", "read-track",
                                "--track-id", track["id"],
                            ]
                        )
                    )["selected_track"]
                    if (
                        current["status"] != "running"
                        or current["revision"] != track["revision"]
                        or current["handling_context"].get("automation_run") != run["id"]
                        or current["handling_context"].get("workspace_reserved") != "yes"
                    ):
                        raise RuntimeError("Track ownership changed; do not restart technical work")
                    try:
                        if not result_path.exists():
                            if (directory / "codex-started.json").exists():
                                raise RuntimeError("Previous Codex execution is incomplete")
                            if preflight(config) != run["baseline"]:
                                raise RuntimeError("Workspace changed after claim")
                            save_json(directory / "schema.json", SCHEMA)
                            save_json(
                                directory / "codex-started.json",
                                {"run": run["id"], "deadline": time.time() + 3600},
                            )
                            command = [
                                *config["codex_command"], "exec", "--sandbox", "danger-full-access",
                                "-c", 'approval_policy="never"', "--cd", config["project_root"],
                                "--json", "--output-schema", str(directory / "schema.json"),
                                "--output-last-message", str(result_path), "-",
                            ]
                            run_command(
                                command,
                                payload=prompt_for(case, config),
                                timeout=3500,
                                evidence=directory / "execution.jsonl",
                            )
                        try:
                            result = validate_result(
                                json.loads(result_path.read_text(encoding="utf-8")),
                                track["next_action"],
                            )
                        except (json.JSONDecodeError, ValueError, TypeError) as error:
                            retry_path = directory / "format-retry.json"
                            if retry_path.exists():
                                raise
                            events = [
                                json.loads(line)
                                for line in (directory / "execution.jsonl")
                                .read_text(encoding="utf-8")
                                .splitlines()
                                if line.strip()
                            ]
                            session = next(
                                event["thread_id"]
                                for event in events
                                if event.get("type") == "thread.started"
                            )
                            uuid.UUID(session)
                            deadline = json.loads(
                                (directory / "codex-started.json").read_text(
                                    encoding="utf-8"
                                )
                            )["deadline"]
                            remaining = int(deadline - time.time())
                            if remaining <= 0:
                                raise RuntimeError(
                                    "Codex execution time budget exhausted"
                                )
                            save_json(retry_path, {"session": session})
                            correction = (
                                f"마지막 결과가 출력 계약을 어겼습니다: {error}. "
                                "조사·수정·도구 실행을 반복하지 말고 이미 확인한 결과의 "
                                "JSON 형식과 필수 근거만 바로잡으세요. 없는 근거를 만들지 마세요."
                            )
                            command = [
                                *config["codex_command"],
                                "exec",
                                "resume",
                                session,
                                "-c",
                                'sandbox_mode="read-only"',
                                "-c",
                                'approval_policy="never"',
                                "--json",
                                "--output-schema",
                                str(directory / "schema.json"),
                                "--output-last-message",
                                str(result_path),
                                "-",
                            ]
                            run_command(
                                command,
                                payload=correction,
                                timeout=remaining,
                                evidence=directory / "format-execution.jsonl",
                            )
                            result = validate_result(
                                json.loads(result_path.read_text(encoding="utf-8")),
                                track["next_action"],
                            )
                        if result["split_tracks"]:
                            if preflight(config) != run["baseline"]:
                                raise RuntimeError("Investigation changed the repair workspace")
                            payload = {
                                "operation": "split",
                                "track_id": track["id"],
                                "expected_revision": track["revision"],
                                "entry_id": str(uuid.uuid5(uuid.UUID(run["id"]), "split")),
                                "actor": "main_codex",
                                "children": result["split_tracks"],
                            }
                        else:
                            details = {
                                key: (
                                    json.dumps(value, ensure_ascii=False)
                                    if key == "test_targets"
                                    else value
                                )
                                for key, value in result["details"].items()
                                if value
                            }
                            details["execution_evidence"] = str(directory / "execution.jsonl")
                            if result["next_action"] == "approve_deploy":
                                commit = details["commit"]
                                head = run_command(
                                    [
                                        *config["code_ssh"],
                                        shlex.join(
                                            ["git", "-C", config["debug_root"], "rev-parse", "HEAD"]
                                        ),
                                    ]
                                )
                                dirty = run_command(
                                    [
                                        *config["code_ssh"],
                                        shlex.join(
                                            ["git", "-C", config["debug_root"], "status", "--porcelain"]
                                        ),
                                    ]
                                )
                                if head != commit or dirty or head == run["baseline"]["head"]:
                                    raise ValueError("Reported repair commit does not match the clean workspace")
                                checks = run_official_verification(
                                    config,
                                    directory,
                                    commit,
                                    result["details"]["test_targets"],
                                )
                                receipt = directory / "official-verification.json"
                                details.update(
                                    verification_commands=json.dumps(checks, ensure_ascii=False),
                                    verification_receipt=_receipt_hash(receipt),
                                    base_commit=run["baseline"]["head"],
                                    repair_ref=f"refs/operational-repairs/{run['id']}",
                                    workspace_reserved="no",
                                )
                            else:
                                if preflight(config) != run["baseline"]:
                                    raise RuntimeError("Non-repair stage changed the workspace")
                                details["workspace_reserved"] = "no"
                            payload = {
                                "operation": "result",
                                "track_id": track["id"],
                                "status": result["status"],
                                "action": result["action"],
                                "category": result["category"],
                                "next_action": result["next_action"],
                                "expected_revision": track["revision"],
                                "entry_id": str(uuid.uuid5(uuid.UUID(run["id"]), "result")),
                                "actor": "main_codex",
                                "details": details,
                            }
                        save_json(payload_path, payload)
                    except Exception as error:
                        failure = {
                            "operation": "result",
                            "track_id": track["id"],
                            "status": "failed",
                            "action": (
                                f"main Codex 실행 중단: {type(error).__name__}. "
                                "실행 자료와 실제 작업 상태를 대조해야 합니다."
                            ),
                            "next_action": "external_wait",
                            "expected_revision": track["revision"],
                            "entry_id": str(uuid.uuid5(uuid.UUID(run["id"]), "interrupted")),
                            "actor": "main_codex",
                            "details": {
                                "owner": "controlroom",
                                "resume_condition": "기존 실행과 작업공간을 대조한 뒤 같은 실행을 인계합니다.",
                                "verification": "정상 결과 기록 전에 실행이 중단됐습니다.",
                                "stop_reason": f"{type(error).__name__}; 실제 실행 상태는 아직 미확인입니다.",
                                "workspace_reserved": "yes",
                            },
                        }
                        save_json(interrupted_path, failure)
                        try:
                            _record(config, failure)
                        except Exception:
                            pass
                        raise
                details = payload.get("details", {})
                if payload.get("next_action") == "approve_deploy" and details.get("repair_ref"):
                    park_repair(config, details)
                saved = _record(config, payload)
                save_json(directory / "recorded.json", saved)
                if payload["operation"] == "split" or details.get("workspace_reserved") == "no":
                    if preflight(config) != run["baseline"]:
                        raise RuntimeError("Workspace changed before reservation release")
                    release.append(True)
                selected = saved.get("selected_track", {})
                outcome = {
                    "state": "recorded",
                    "event_id": saved["id"],
                    "track_id": selected.get("id"),
                    "next_action": selected.get("next_action"),
                }
        active.unlink()
        return outcome


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    config = json.loads(arguments.config.read_text(encoding="utf-8"))
    if arguments.check:
        print(json.dumps(preflight(config)))
    else:
        print(json.dumps(execute_once(config, arguments.state_root), ensure_ascii=False))


if __name__ == "__main__":
    main()
