#!/usr/bin/env python3
"""Record confirmed Hermes delivery in Exdigm DB, then advance local recovery state."""
from __future__ import annotations

import argparse
from contextlib import closing
import json
import sqlite3
from datetime import datetime
from pathlib import Path
import subprocess
import uuid


RECORD_CONFIG = Path("/etc/exdigm-sam/record-command.json")


def read_executions(profile: Path, execution_id=None) -> list[dict]:
    state = json.loads(
        (profile / "state" / "exdigm_error_monitor.json").read_text(
            encoding="utf-8"
        )
    )
    job_id = state.get("exdigm_monitor_job_id")
    if not isinstance(job_id, str) or not job_id.strip():
        raise ValueError("The installed Exdigm monitor job identity is required")
    database = profile / "cron" / "executions.db"
    with closing(
        sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=5)
    ) as db:
        db.row_factory = sqlite3.Row
        if execution_id:
            rows = db.execute(
                "SELECT id,status,delivery_outcome,finished_at FROM executions "
                "WHERE id=? AND job_id=?",
                (execution_id, job_id),
            )
        else:
            rows = db.execute(
                "SELECT id,status,delivery_outcome,finished_at FROM executions "
                "WHERE job_id=? AND status IN ('claimed','running')",
                (job_id,),
            )
        return [dict(row) for row in rows]


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def record_db_deliveries(
    profile: Path,
    pending: dict,
    receipt: dict,
    *,
    settings_reader=None,
    runner=subprocess.run,
) -> None:
    command = json.loads(RECORD_CONFIG.read_text(encoding="utf-8"))
    if not isinstance(command, list) or not command:
        raise ValueError("Sam's restricted record command is invalid")
    if settings_reader is None:
        from dotenv import dotenv_values

        settings_reader = dotenv_values
    owner_chat_id = (
        settings_reader(profile / ".env").get("TELEGRAM_HOME_CHANNEL") or ""
    ).strip()
    if not owner_chat_id:
        raise ValueError("Sam's owner Telegram conversation is not configured")
    delivered_at = receipt.get("finished_at")
    if not isinstance(delivered_at, str):
        raise ValueError("Hermes delivery completion time is missing")
    completion = datetime.fromisoformat(delivered_at)
    if completion.tzinfo is None:
        raise ValueError("Hermes delivery completion time has no time zone")
    for track_id, revision in pending["tracks"].items():
        entry_id = str(
            uuid.uuid5(
                uuid.UUID(track_id),
                f"hermes:{revision}:{receipt['id']}",
            )
        )
        payload = {
            "operation": "delivery",
            "track_id": track_id,
            "subject_revision": revision,
            "entry_id": entry_id,
            "delivery": {
                "message_id": f"hermes-execution:{receipt['id']}",
                "chat_id": owner_chat_id,
                "delivered_at": completion.isoformat(timespec="seconds"),
            },
        }
        completed = runner(
            [*command, "pipeline", "--json-input"],
            input=json.dumps(payload, ensure_ascii=False),
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if completed.returncode:
            raise RuntimeError("Exdigm DB did not confirm Hermes report delivery")
        saved = json.loads(completed.stdout)
        transitions = saved["selected_track"]["transitions"]
        if not any(
            item.get("entry_id") == entry_id
            and item.get("event_type") == "report_delivered"
            for item in transitions
        ):
            raise RuntimeError("Exdigm DB delivery receipt is missing")


def update_checkpoint(
    path: Path,
    checkpoint=None,
    *,
    receipt_reader=read_executions,
    delivery_writer=None,
) -> bool:
    state = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    pending = state.get("exdigm_pending_delivery")
    if not pending:
        return False
    if checkpoint and checkpoint != pending["checkpoint"]:
        raise ValueError("Checkpoint does not match the pending delivery")
    receipts = receipt_reader(path.parent.parent, pending["execution_id"])
    if (
        len(receipts) != 1
        or receipts[0]["status"] != "completed"
        or receipts[0]["delivery_outcome"] != "delivered"
    ):
        return False
    writer = delivery_writer or record_db_deliveries
    writer(path.parent.parent, pending, receipts[0])
    seen = state.setdefault("exdigm_delivered_track_revisions", {})
    for track_id, revision in pending["tracks"].items():
        seen[track_id] = max(seen.get(track_id, 0), revision)
    current = pending["checkpoint"]
    previous_time = state.get("exdigm_error_checkpoint_updated_at")
    previous = (
        (
            datetime.fromisoformat(previous_time),
            state.get("exdigm_error_checkpoint_track_id", ""),
        )
        if previous_time
        else None
    )
    candidate = (
        datetime.fromisoformat(current["updated_at"]),
        current["track_id"],
    )
    if previous is None or candidate > previous:
        state["exdigm_error_checkpoint_updated_at"] = current["updated_at"]
        state["exdigm_error_checkpoint_track_id"] = current["track_id"]
    state["last_exdigm_error_check_at"] = (
        datetime.now().astimezone().isoformat(timespec="seconds")
    )
    del state["exdigm_pending_delivery"]
    save_state(path, state)
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("state_path", type=Path)
    parser.add_argument("updated_at", nargs="?")
    parser.add_argument("track_id", nargs="?")
    args = parser.parse_args()
    checkpoint = (
        {"updated_at": args.updated_at, "track_id": args.track_id}
        if args.updated_at and args.track_id
        else None
    )
    updated = update_checkpoint(args.state_path, checkpoint)
    print(f"exdigm_error_checkpoint_updated={str(updated).lower()}")


if __name__ == "__main__":
    main()
