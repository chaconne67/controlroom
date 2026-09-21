#!/usr/bin/env python3
"""Read reportable Exdigm event tracks; Sam never performs technical work."""
from __future__ import annotations

import base64
import hashlib
import json
import subprocess
from pathlib import Path

from update_exdigm_error_checkpoint import (
    read_executions,
    save_state,
    update_checkpoint,
)

PROFILE_ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = PROFILE_ROOT / "state" / "exdigm_error_monitor.json"
ERROR_LOG = PROFILE_ROOT / "logs" / "exdigm_error_context.log"
SSH_TARGET = "chaconne@49.247.202.197"
REMOTE_ROOT = "/home/chaconne/exdigm-debug"
MARKER = "EXDIGM_ERROR_JSON="
APPROVAL_FIELDS = {
    "user_action": (
        "owner",
        "required_action",
        "resume_condition",
        "verification",
        "stop_reason",
    ),
    "external_wait": (
        "owner",
        "resume_condition",
        "verification",
        "stop_reason",
    ),
    "approve_change": (
        "root_cause",
        "proposal",
        "alternatives",
        "recommendation_reason",
        "impact",
        "verification",
        "rollback",
    ),
    "approve_deploy": (
        "commit",
        "base_commit",
        "repair_ref",
        "verification",
        "verification_receipt",
        "rollback",
    ),
    "approve_close": ("outcome_verification", "verification"),
}


def load_state() -> dict:
    return (
        json.loads(STATE_PATH.read_text(encoding="utf-8"))
        if STATE_PATH.exists()
        else {}
    )


def log_failure(exc: Exception) -> None:
    ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
    with ERROR_LOG.open("a", encoding="utf-8") as stream:
        stream.write(f"Exdigm monitor failed: {type(exc).__name__}\n")


def parse_probe_output(text: str) -> dict:
    for line in reversed(text.splitlines()):
        if line.startswith(MARKER):
            return json.loads(line[len(MARKER) :])
    raise ValueError("Exdigm error probe did not return its JSON marker")


def remote_code() -> str:
    return f'''import json
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("SELECT to_regclass('public.projects_operationalerrortrack')")
    if cursor.fetchone()[0] is None:
        result = {{"available": False, "tracks": []}}
    else:
        cursor.execute("""
            SELECT e.id::text, e.created_at, e.occurred_at, e.summary, e.source,
                   e.error_type, t.id::text, t.sequence, t.title, t.scope,
                   t.blocking, t.status, t.category, t.next_action, t.revision,
                   t.handling_context, t.processing_history->-1, t.updated_at
            FROM projects_operationalerrortrack t
            JOIN projects_operationalerror e ON e.id=t.error_id
            WHERE e.summary <> '테스트 오류 기록입니다. 실제 운영 장애가 아닙니다.'
              AND (
                    t.next_action IN (
                        'user_action','external_wait','approve_change',
                        'approve_deploy','approve_close'
                    )
                    OR t.status IN ('deferred','rejected','resolved','failed')
                  )
              AND NOT EXISTS (
                    SELECT 1
                    FROM projects_operationalerrortransition x
                    WHERE x.track_id=t.id
                      AND x.event_type='report_delivered'
                      AND x.track_revision=t.revision
                  )
            ORDER BY t.updated_at, t.id
            LIMIT 100
        """)
        names = (
            "event_id","event_created_at","occurred_at","event_summary","source",
            "error_type","track_id","sequence","track_title","track_scope",
            "blocking","track_status","category","next_action","track_revision",
            "handling_context","last_result","updated_at"
        )
        tracks = []
        for row in cursor.fetchall():
            values = list(row)
            for index in (1,2,17):
                values[index] = values[index].isoformat()
            for index in (15,16):
                if isinstance(values[index], str):
                    values[index] = json.loads(values[index])
            tracks.append(dict(zip(names, values)))
        result = {{"available": True, "tracks": tracks}}
print({MARKER!r} + json.dumps(result, ensure_ascii=False))
'''


def build_remote_command() -> str:
    encoded = base64.b64encode(remote_code().encode("utf-8")).decode("ascii")
    shell_code = f"import base64;exec(base64.b64decode('{encoded}'))"
    return (
        f'cd {REMOTE_ROOT} && PYTHONIOENCODING=utf-8 '
        f'scripts/debug_workspace.sh shell-readonly -c "{shell_code}"'
    )


def run_probe(command: str, timeout: int = 45) -> str:
    return subprocess.check_output(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=10",
            SSH_TARGET,
            command,
        ],
        text=True,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def approval_request(row):
    names = APPROVAL_FIELDS.get(row["next_action"])
    if names is None:
        return None
    request = {
        "event_id": row["event_id"],
        "track_id": row["track_id"],
        "track_revision": row["track_revision"],
        "next_action": row["next_action"],
        "details": {
            name: row["handling_context"].get(name, "") for name in names
        },
    }
    request["request_hash"] = hashlib.sha256(
        json.dumps(
            request,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return request


def collect_context(runner=run_probe) -> dict | None:
    parsed = parse_probe_output(runner(build_remote_command(), timeout=45))
    if not parsed.get("available"):
        raise RuntimeError("Operational-error track table unavailable")
    tracks = parsed.get("tracks") or []
    if not tracks:
        return None
    for row in tracks:
        row["approval_request"] = approval_request(row)
    newest = max(tracks, key=lambda row: (row["updated_at"], row["track_id"]))
    return {
        "new_exdigm_tracks": tracks,
        "exdigm_error_checkpoint": {
            "updated_at": newest["updated_at"],
            "track_id": newest["track_id"],
        },
        "exdigm_error_state_path": str(STATE_PATH),
    }


def prepare_context(
    *,
    runner=run_probe,
    receipt_reader=read_executions,
    delivery_writer=None,
) -> dict | None:
    update_checkpoint(
        STATE_PATH,
        receipt_reader=receipt_reader,
        delivery_writer=delivery_writer,
    )
    state = load_state()
    context = collect_context(runner=runner)
    if context:
        active = receipt_reader(PROFILE_ROOT)
        if len(active) != 1:
            raise RuntimeError(
                "A single active Hermes execution is required before preparing delivery"
            )
        previous = state.get("exdigm_pending_delivery")
        if previous and previous["execution_id"] != active[0]["id"]:
            previous_runs = receipt_reader(
                PROFILE_ROOT, previous["execution_id"]
            )
            if previous_runs and previous_runs[0]["status"] in {
                "claimed",
                "running",
            }:
                raise RuntimeError("Previous Hermes delivery is still active")
        state["exdigm_pending_delivery"] = {
            "execution_id": active[0]["id"],
            "job_id": state["exdigm_monitor_job_id"],
            "checkpoint": context["exdigm_error_checkpoint"],
            "tracks": {
                row["track_id"]: row["track_revision"]
                for row in context["new_exdigm_tracks"]
            },
        }
        save_state(STATE_PATH, state)
    return context


def main() -> None:
    try:
        context = prepare_context()
    except Exception as exc:
        log_failure(exc)
        context = {
            "exdigm_monitor_error": {
                "error_type": type(exc).__name__,
                "message": (
                    "엑스다임 오류 확인 또는 전달 확인에 실패했습니다. "
                    "기존 확인 위치를 보존했습니다."
                ),
            }
        }
    if context:
        print(json.dumps(context, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
