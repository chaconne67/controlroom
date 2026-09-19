#!/usr/bin/env python3
"""Read new incidents and later handling revisions for the Hermes monitor."""
from __future__ import annotations

import base64
import json
import subprocess
from pathlib import Path

from update_exdigm_error_checkpoint import read_executions, save_state, update_checkpoint

PROFILE_ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = PROFILE_ROOT / "state" / "exdigm_error_monitor.json"
ERROR_LOG = PROFILE_ROOT / "logs" / "exdigm_error_context.log"
SSH_TARGET = "chaconne@49.247.202.197"
REMOTE_ROOT = "/home/chaconne/exdigm-debug"
MARKER = "EXDIGM_ERROR_JSON="


def load_state() -> dict:
    return json.loads(STATE_PATH.read_text(encoding="utf-8")) if STATE_PATH.exists() else {}


def log_failure(exc: Exception) -> None:
    ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
    with ERROR_LOG.open("a", encoding="utf-8") as stream:
        stream.write(f"Exdigm monitor failed: {type(exc).__name__}\n")


def parse_probe_output(text: str) -> dict:
    for line in reversed(text.splitlines()):
        if line.startswith(MARKER):
            return json.loads(line[len(MARKER):])
    raise ValueError("Exdigm error probe did not return its JSON marker")


def remote_code(state: dict) -> str:
    # to_jsonb keeps this query usable before the additive migration is deployed.
    # Old rows do not become a new backlog just because classification was added.
    parameters = [
        state.get("exdigm_error_checkpoint_created_at"),
        state.get("exdigm_error_checkpoint_created_at"),
        state.get("exdigm_error_checkpoint_id") or "00000000-0000-0000-0000-000000000000",
        json.dumps(state.get("exdigm_delivered_revisions", {})),
    ]
    return f'''import json
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("SELECT to_regclass('public.projects_operationalerror')")
    if cursor.fetchone()[0] is None:
        result = {{"available": False, "errors": []}}
    else:
        cursor.execute("""
            SELECT id::text, created_at, occurred_at, summary, source, error_type,
                   COALESCE(to_jsonb(e)->>'category', 'unclassified'),
                   COALESCE(to_jsonb(e)->>'next_action', 'investigate'),
                   COALESCE((to_jsonb(e)->>'handling_revision')::int, 0),
                   COALESCE(to_jsonb(e)->'handling_context', '{{}}'::jsonb),
                   COALESCE(to_jsonb(e)->'processing_history'->-1, '{{}}'::jsonb)
            FROM projects_operationalerror e
            WHERE (%s::timestamptz IS NULL
                   OR (created_at, id) > (%s::timestamptz, %s::uuid)
                   OR COALESCE((to_jsonb(e)->>'handling_revision')::int, 0)
                      > COALESCE((%s::jsonb->>id::text)::int, 0))
              AND summary <> '테스트 오류 기록입니다. 실제 운영 장애가 아닙니다.'
              AND NOT (COALESCE(to_jsonb(e)->>'category', '') = 'expected_stop'
                       AND COALESCE(to_jsonb(e)->>'next_action', '') = 'none')
            ORDER BY created_at, id LIMIT 100
        """, {parameters!r})
        errors = [
            dict(zip(("id", "created_at", "occurred_at", "summary", "source", "error_type",
                      "category", "next_action", "handling_revision", "handling_context", "last_result"),
                     (row[0], row[1].isoformat(), row[2].isoformat(), *row[3:])))
            for row in cursor.fetchall()
        ]
        result = {{"available": True, "errors": errors}}
print({MARKER!r} + json.dumps(result, ensure_ascii=False))
'''


def build_remote_command(state: dict) -> str:
    encoded = base64.b64encode(remote_code(state).encode("utf-8")).decode("ascii")
    shell_code = f"import base64;exec(base64.b64decode('{encoded}'))"
    return f'cd {REMOTE_ROOT} && PYTHONIOENCODING=utf-8 scripts/debug_workspace.sh shell-readonly -c "{shell_code}"'


def run_probe(command: str, timeout: int = 45) -> str:
    return subprocess.check_output(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", SSH_TARGET, command],
        text=True, stderr=subprocess.STDOUT, timeout=timeout, encoding="utf-8", errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def collect_context(state: dict, runner=run_probe) -> dict | None:
    parsed = parse_probe_output(runner(build_remote_command(state), timeout=45))
    if not parsed.get("available"):
        raise RuntimeError("Operational-error table unavailable")
    errors = parsed.get("errors") or []
    if not errors:
        return None
    newest = max(errors, key=lambda row: (row["created_at"], row["id"]))
    return {
        "new_exdigm_errors": errors,
        "exdigm_error_checkpoint": {"created_at": newest["created_at"], "id": newest["id"]},
        "exdigm_error_state_path": str(STATE_PATH),
    }


def prepare_context(*, runner=run_probe, receipt_reader=read_executions) -> dict | None:
    # A failed/suppressed/queued/unknown run never consumes its pending revisions.
    update_checkpoint(STATE_PATH, receipt_reader=receipt_reader)
    state = load_state()
    context = collect_context(state, runner=runner)
    if context:
        active = receipt_reader(PROFILE_ROOT)
        if len(active) != 1:
            raise RuntimeError("A single active Hermes execution is required before preparing delivery")
        previous = state.get("exdigm_pending_delivery")
        if previous and previous["execution_id"] != active[0]["id"]:
            previous_runs = receipt_reader(PROFILE_ROOT, previous["execution_id"])
            if previous_runs and previous_runs[0]["status"] in {"claimed", "running"}:
                raise RuntimeError("Previous Hermes delivery is still active")
        state["exdigm_pending_delivery"] = {
            "execution_id": active[0]["id"],
            "checkpoint": context["exdigm_error_checkpoint"],
            "revisions": {row["id"]: row.get("handling_revision", 0) for row in context["new_exdigm_errors"]},
        }
        save_state(STATE_PATH, state)
    return context


def main() -> None:
    try:
        context = prepare_context()
    except Exception as exc:
        log_failure(exc)
        context = {"exdigm_monitor_error": {
            "error_type": type(exc).__name__,
            "message": "엑스다임 오류 확인 또는 전달 확인에 실패했습니다. 기존 확인 위치를 보존했습니다.",
        }}
    if context:
        print(json.dumps(context, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
