#!/usr/bin/env python3
"""Read undelivered DB-board results through Sam's restricted read command."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from update_exdigm_error_checkpoint import read_executions, save_state, update_checkpoint


PROFILE_ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = PROFILE_ROOT / "state" / "exdigm_error_monitor.json"
ERROR_LOG = PROFILE_ROOT / "logs" / "exdigm_error_context.log"
RECORD_CONFIG = Path("/etc/exdigm-sam/record-command.json")


def load_state() -> dict:
    return json.loads(STATE_PATH.read_text(encoding="utf-8")) if STATE_PATH.exists() else {}


def log_failure(exc: Exception) -> None:
    ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
    with ERROR_LOG.open("a", encoding="utf-8") as stream:
        stream.write(f"Exdigm monitor failed: {type(exc).__name__}\n")


def load_command() -> list[str]:
    value = json.loads(RECORD_CONFIG.read_text(encoding="utf-8"))
    command = value.get("command") if isinstance(value, dict) else None
    if not isinstance(command, list) or not command or not all(
        isinstance(item, str) and item for item in command
    ):
        raise ValueError("Sam's restricted board command is unavailable")
    return command


def run_probe(command: list[str], state: dict, timeout: int = 45) -> dict:
    payload = {
        "delivered_revisions": state.get("exdigm_delivered_revisions", {})
    }
    completed = subprocess.run(
        [*command, "--list"],
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if completed.returncode:
        raise RuntimeError("Sam's restricted Exdigm board read failed")
    value = json.loads(completed.stdout)
    if not isinstance(value, dict):
        raise ValueError("Exdigm board returned an invalid response")
    return value


def collect_context(state: dict, runner=run_probe) -> dict | None:
    parsed = runner(load_command(), state, timeout=45)
    if not parsed.get("available"):
        raise RuntimeError("Operational-error board unavailable")
    errors = parsed.get("errors") or []
    if not isinstance(errors, list):
        raise ValueError("Operational-error board returned invalid rows")
    if not errors:
        return None
    newest = max(errors, key=lambda row: (row["created_at"], row["id"]))
    return {
        "new_exdigm_errors": errors,
        "exdigm_error_checkpoint": {
            "created_at": newest["created_at"], "id": newest["id"]
        },
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
            raise RuntimeError(
                "A single active Hermes execution is required before preparing delivery"
            )
        previous = state.get("exdigm_pending_delivery")
        if previous and previous["execution_id"] != active[0]["id"]:
            previous_runs = receipt_reader(PROFILE_ROOT, previous["execution_id"])
            if previous_runs and previous_runs[0]["status"] in {"claimed", "running"}:
                raise RuntimeError("Previous Hermes delivery is still active")
        state["exdigm_pending_delivery"] = {
            "execution_id": active[0]["id"],
            "checkpoint": context["exdigm_error_checkpoint"],
            "revisions": {
                row["id"]: row.get("handling_revision", 0)
                for row in context["new_exdigm_errors"]
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
