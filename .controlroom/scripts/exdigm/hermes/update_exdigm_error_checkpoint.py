#!/usr/bin/env python3
"""Acknowledge the configured Hermes job only after its actual delivery."""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

def read_executions(profile: Path, execution_id=None) -> list[dict]:
    state = json.loads((profile / "state" / "exdigm_error_monitor.json").read_text(encoding="utf-8"))
    job_id = state.get("exdigm_monitor_job_id")
    if not isinstance(job_id, str) or not job_id.strip():
        raise ValueError("The installed Exdigm monitor job identity is required")
    database = profile / "cron" / "executions.db"
    with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=5) as db:
        db.row_factory = sqlite3.Row
        if execution_id:
            rows = db.execute(
                "SELECT id,status,delivery_outcome FROM executions WHERE id=? AND job_id=?",
                (execution_id, job_id),
            )
        else:
            rows = db.execute(
                "SELECT id,status,delivery_outcome FROM executions "
                "WHERE job_id=? AND status IN ('claimed','running')",
                (job_id,),
            )
        return [dict(row) for row in rows]


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def update_checkpoint(path: Path, checkpoint=None, *, receipt_reader=read_executions) -> bool:
    state = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    pending = state.get("exdigm_pending_delivery")
    if not pending:
        return False
    if checkpoint and checkpoint != pending["checkpoint"]:
        raise ValueError("Checkpoint does not match the pending delivery")
    receipts = receipt_reader(path.parent.parent, pending["execution_id"])
    if len(receipts) != 1 or receipts[0]["status"] != "completed" or receipts[0]["delivery_outcome"] != "delivered":
        return False
    seen = state.setdefault("exdigm_delivered_revisions", {})
    for error_id, revision in pending["revisions"].items():
        seen[error_id] = max(seen.get(error_id, 0), revision)
    checkpoint = pending["checkpoint"]
    previous_time = state.get("exdigm_error_checkpoint_created_at")
    previous = (datetime.fromisoformat(previous_time), state.get("exdigm_error_checkpoint_id", "")) if previous_time else None
    current = (datetime.fromisoformat(checkpoint["created_at"]), checkpoint["id"])
    if previous is None or current > previous:
        state["exdigm_error_checkpoint_created_at"] = checkpoint["created_at"]
        state["exdigm_error_checkpoint_id"] = checkpoint["id"]
    state["last_exdigm_error_check_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    del state["exdigm_pending_delivery"]
    save_state(path, state)
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("state_path", type=Path)
    parser.add_argument("created_at", nargs="?")
    parser.add_argument("error_id", nargs="?")
    args = parser.parse_args()
    checkpoint = {"created_at": args.created_at, "id": args.error_id} if args.created_at and args.error_id else None
    updated = update_checkpoint(args.state_path, checkpoint)
    print(f"exdigm_error_checkpoint_updated={str(updated).lower()}")


if __name__ == "__main__":
    main()
