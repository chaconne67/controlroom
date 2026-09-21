#!/usr/bin/env python3
"""Let Sam read, report, and record owner communication without executing work."""
from __future__ import annotations

import argparse
from contextlib import closing, contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import uuid

sys.path.insert(0, str(Path.home() / "controlroom/.controlroom/scripts/exdigm"))
from repair_once import run_command, save_json


RECORD_CONFIG = Path("/etc/exdigm-sam/record-command.json")


@contextmanager
def exclusive_lock(path):
    """Serialize one owner decision on Linux and keep tests portable."""
    with path.open("a+b") as stream:
        if os.name == "nt":
            import msvcrt

            stream.seek(0, os.SEEK_END)
            if stream.tell() == 0:
                stream.write(b"\0")
                stream.flush()
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(stream, fcntl.LOCK_EX)
            yield


def record_rpc(arguments, payload=None):
    command = json.loads(RECORD_CONFIG.read_text(encoding="utf-8"))
    if not isinstance(command, list) or not command or not all(
        isinstance(item, str) for item in command
    ):
        raise RuntimeError("Sam's restricted record command is invalid")
    try:
        return json.loads(
            run_command(
                [*command, "pipeline", *arguments],
                payload=None
                if payload is None
                else json.dumps(payload, ensure_ascii=False),
            )
        )
    except RuntimeError as exc:
        raise RuntimeError(
            "Exdigm communication record failed; verify the deployed pipeline before retrying"
        ) from exc


def reconcile_pending_delivery(profile):
    state_path = profile / "state" / "exdigm_error_monitor.json"
    if not state_path.exists():
        return
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if not state.get("exdigm_pending_delivery"):
        return
    scripts = profile / "scripts"
    sys.path.insert(0, str(scripts))
    try:
        from update_exdigm_error_checkpoint import update_checkpoint
    finally:
        sys.path.pop(0)
    if not update_checkpoint(state_path):
        raise ValueError(
            "The preceding Exdigm report delivery is not confirmed yet; retry after Hermes records it"
        )


def request_view(case):
    track = case.get("selected_track")
    if not isinstance(track, dict):
        raise ValueError("The response has no selected handling track")
    request = track.get("approval_request")
    if not isinstance(request, dict):
        raise ValueError("The track has no current approval request")
    if (
        request.get("track_id") != track.get("id")
        or request.get("track_revision") != track.get("revision")
        or request.get("next_action") != track.get("next_action")
        or not re.fullmatch(r"[0-9a-f]{64}", request.get("request_hash", ""))
    ):
        raise ValueError("The approval request identity is inconsistent")
    return {
        **request,
        "event_summary": case.get("summary", ""),
        "track_title": track.get("title", ""),
        "track_status": track.get("status", ""),
    }


def authenticated_reply(profile, environment):
    from dotenv import dotenv_values

    identity = {
        key: environment.get("HERMES_SESSION_" + key.upper(), "")
        for key in ("id", "platform", "chat_id", "chat_type", "user_id", "message_id")
    }
    if (
        any(not value for value in identity.values())
        or identity["platform"] != "telegram"
        or identity["chat_type"] != "dm"
        or environment.get("HERMES_CRON_SESSION") == "1"
    ):
        raise ValueError(
            "A current owner Telegram message is required; scheduled and CLI sessions cannot approve"
        )
    settings = dotenv_values(profile / ".env")
    allowed = {
        item.strip()
        for item in (settings.get("TELEGRAM_ALLOWED_USERS") or "").split(",")
        if item.strip()
    }
    if (
        identity["user_id"] not in allowed
        or identity["chat_id"] != settings.get("TELEGRAM_HOME_CHANNEL")
    ):
        raise ValueError("This message is outside Sam's configured owner conversation")
    with closing(
        sqlite3.connect((profile / "state.db").as_uri() + "?mode=ro", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        row = db.execute(
            """SELECT m.id,m.timestamp,m.content FROM messages m
               JOIN sessions s ON s.id=m.session_id
               WHERE s.id=? AND s.source='telegram' AND s.user_id=? AND s.chat_id=?
                 AND s.chat_type='dm' AND m.platform_message_id=? AND m.role='user'
                 AND m.active=1 AND m.compacted=0 AND m._compressed_summary=0
               ORDER BY m.id DESC LIMIT 1""",
            (
                identity["id"],
                identity["user_id"],
                identity["chat_id"],
                identity["message_id"],
            ),
        ).fetchone()
    if row is None or not row["content"]:
        raise ValueError("The original user message is absent from the Hermes conversation ledger")
    return {
        "approval_actor_id": identity["user_id"],
        "approval_chat_id": identity["chat_id"],
        "approval_message_id": identity["message_id"],
        "approval_message_at": datetime.fromtimestamp(
            row["timestamp"], timezone.utc
        ).isoformat(),
        "approval_message_sha256": hashlib.sha256(
            row["content"].encode()
        ).hexdigest(),
        "approval_session_id": identity["id"],
        "recorded_by": "sam",
    }


def decide(
    profile,
    environment,
    track_id,
    revision,
    request_hash,
    decision,
    *,
    instruction="",
    rpc=record_rpc,
):
    reconcile_pending_delivery(profile)
    proof = authenticated_reply(profile, environment)
    track_id = str(uuid.UUID(track_id))
    if (
        revision < 1
        or not re.fullmatch(r"[0-9a-f]{64}", request_hash)
        or decision not in {"approve", "reject", "defer", "revise", "respond"}
    ):
        raise ValueError("Invalid decision identity")
    if decision in {"revise", "respond"}:
        if not instruction.strip():
            raise ValueError(
                "A revision or blocker response requires the owner's instruction"
            )
        proof["instruction"] = instruction.strip()
    instruction = instruction.strip()
    entry_id = str(
        uuid.uuid5(
            uuid.UUID(track_id),
            (
                f"sam:{revision}:{request_hash}:{decision}:"
                f"{proof['approval_message_id']}:"
                f"{hashlib.sha256(instruction.encode()).hexdigest()}"
            ),
        )
    )
    directory = profile / "state" / "exdigm_approvals"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = directory / (entry_id + ".json")
    with exclusive_lock(path.with_suffix(".lock")):
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            expected_proof = {**proof}
            if decision in {"revise", "respond"}:
                expected_proof["instruction"] = instruction
            if payload["proof"] != expected_proof:
                raise ValueError("This decision receipt belongs to another owner message")
        else:
            case = rpc(["read-track", "--track-id", track_id])
            request = request_view(case)
            if (
                request["track_revision"] != revision
                or request["request_hash"] != request_hash
            ):
                raise ValueError(
                    "Approval request changed; inspect it and obtain a decision on that version"
                )
            payload = {
                "operation": "decide",
                "track_id": track_id,
                "expected_revision": revision,
                "request_hash": request_hash,
                "decision": decision,
                "proof": proof,
                "entry_id": entry_id,
            }
            save_json(path, payload)
        saved = rpc(["--json-input"], payload)
    track = saved["selected_track"]
    receipt = next(
        (
            item
            for item in track["transitions"]
            if item.get("entry_id") == entry_id
            and item.get("event_type") == "decision_recorded"
        ),
        None,
    )
    if receipt is None:
        raise ValueError("The DB did not confirm the owner decision")
    next_executor = {
        "repair": "main_codex",
        "deploy": "deploy_codex",
        "investigate": "main_codex",
    }.get(track["next_action"])
    return {
        "event_id": saved["id"],
        "track_id": track_id,
        "decision": decision,
        "approval_entry_id": entry_id,
        "request_revision": revision,
        "recorded_revision": track["revision"],
        "next_action": track["next_action"],
        "next_executor": next_executor,
        "sam_execution_allowed": False,
    }


def record_delivery(track_id, revision, message_id, chat_id, delivered_at, rpc=record_rpc):
    track_id = str(uuid.UUID(track_id))
    entry_id = str(
        uuid.uuid5(uuid.UUID(track_id), f"delivery:{revision}:{message_id}")
    )
    payload = {
        "operation": "delivery",
        "track_id": track_id,
        "subject_revision": revision,
        "entry_id": entry_id,
        "delivery": {
            "message_id": message_id,
            "chat_id": chat_id,
            "delivered_at": delivered_at,
        },
    }
    saved = rpc(["--json-input"], payload)
    receipts = [
        item
        for item in saved["selected_track"]["transitions"]
        if item.get("entry_id") == entry_id
        and item.get("event_type") == "report_delivered"
    ]
    if len(receipts) != 1:
        raise ValueError("The DB did not confirm report delivery")
    return {
        "event_id": saved["id"],
        "track_id": track_id,
        "subject_revision": revision,
        "delivery_entry_id": entry_id,
    }


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("inspect", "decide", "deliver"))
    parser.add_argument("track_id", type=uuid.UUID)
    parser.add_argument("--revision", type=int)
    parser.add_argument("--request-hash")
    parser.add_argument(
        "--decision",
        choices=("approve", "reject", "defer", "revise", "respond"),
    )
    parser.add_argument("--instruction", default="")
    parser.add_argument("--message-id")
    parser.add_argument("--chat-id")
    parser.add_argument("--delivered-at")
    args = parser.parse_args()
    if args.action == "inspect":
        output = request_view(
            record_rpc(["read-track", "--track-id", str(args.track_id)])
        )
    elif args.action == "decide":
        if args.revision is None or not args.request_hash or not args.decision:
            parser.error("decide requires revision, request-hash and decision")
        profile = Path(
            os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))
        ).resolve()
        output = decide(
            profile,
            os.environ,
            str(args.track_id),
            args.revision,
            args.request_hash,
            args.decision,
            instruction=args.instruction,
        )
    else:
        if (
            args.revision is None
            or not args.message_id
            or not args.chat_id
            or not args.delivered_at
        ):
            parser.error(
                "deliver requires revision, message-id, chat-id and delivered-at"
            )
        output = record_delivery(
            str(args.track_id),
            args.revision,
            args.message_id,
            args.chat_id,
            args.delivered_at,
        )
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
