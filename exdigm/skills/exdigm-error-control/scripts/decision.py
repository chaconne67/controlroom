#!/usr/bin/env python3
"""Bind Sam's decision to an actual owner message and an existing DB request."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import sqlite3
import sys
import uuid

sys.path.insert(0, str(Path.home()/"controlroom/.controlroom/scripts/exdigm"))
from repair_once import run_command, save_json

SSH_TARGET = "chaconne@49.247.202.197"
APP_SERVICE = "Exdigm_exdigm_app"


def record_rpc(arguments, payload=None):
    # Resolve one current Swarm task; JSON stays on stdin, never in shell text.
    script = """import os,subprocess,sys
ids=subprocess.check_output(['docker','ps','-q','--filter','label=com.docker.swarm.service.name='+sys.argv[1]],text=True).split()
if len(ids)!=1:
    raise SystemExit('One active Exdigm app task is required')
os.execvp('docker',['docker','exec','-i',ids[0],'python','manage.py','record_operational_error_result',*sys.argv[2:]])
"""
    command = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", SSH_TARGET,
               shlex.join(["python3", "-c", script, APP_SERVICE, *arguments])]
    try:
        return json.loads(run_command(command, payload=None if payload is None else json.dumps(payload, ensure_ascii=False)))
    except RuntimeError as exc:
        raise RuntimeError("Exdigm result command failed; verify the deployed handling schema and app task before retrying") from exc


def request_view(case):
    action, details = case["next_action"], case["handling_context"]
    required = {"approve_change": ("proposal", "impact", "verification", "rollback"),
                "approve_deploy": ("commit", "verification", "rollback")}
    if action not in required or any(not details.get(key, "").strip() for key in required.get(action, ())):
        raise ValueError("The record has no complete approval request")
    if action == "approve_deploy" and not re.fullmatch(r"[0-9a-f]{40}", details["commit"]):
        raise ValueError("The request must identify its exact commit")
    request = {"error_id": str(uuid.UUID(case["id"])), "revision": case["handling_revision"],
               "next_action": action, "category": case["category"],
               "details": {key: value for key, value in details.items() if not key.startswith("approval_")}}
    encoded = json.dumps(request, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return {**request, "request_hash": hashlib.sha256(encoded).hexdigest(), "summary": case["summary"]}


def authenticated_reply(profile, environment):
    from dotenv import dotenv_values
    identity = {key: environment.get("HERMES_SESSION_"+key.upper(), "")
                for key in ("id", "platform", "chat_id", "chat_type", "user_id", "message_id")}
    if (any(not value for value in identity.values()) or identity["platform"] != "telegram"
            or identity["chat_type"] != "dm" or environment.get("HERMES_CRON_SESSION") == "1"):
        raise ValueError("A current owner Telegram message is required; scheduled and CLI sessions cannot approve")
    settings = dotenv_values(profile / ".env")
    allowed = {item.strip() for item in (settings.get("TELEGRAM_ALLOWED_USERS") or "").split(",") if item.strip()}
    if identity["user_id"] not in allowed or identity["chat_id"] != settings.get("TELEGRAM_HOME_CHANNEL"):
        raise ValueError("This message is outside Sam's configured owner conversation")
    with sqlite3.connect((profile / "state.db").as_uri()+"?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        row = db.execute("""SELECT m.id,m.timestamp,m.content FROM messages m JOIN sessions s ON s.id=m.session_id
            WHERE s.id=? AND s.source='telegram' AND s.user_id=? AND s.chat_id=? AND s.chat_type='dm'
              AND m.platform_message_id=? AND m.role='user' AND m.active=1
              AND m.compacted=0 AND m._compressed_summary=0 ORDER BY m.id DESC LIMIT 1""",
                         (identity["id"], identity["user_id"], identity["chat_id"], identity["message_id"])).fetchone()
    if row is None or not row["content"]:
        raise ValueError("The original user message is absent from the Hermes conversation ledger")
    return {"approval_actor": "sam", "approval_user_id": identity["user_id"],
            "approval_session_id": identity["id"], "approval_message_id": identity["message_id"],
            "approval_message_sha256": hashlib.sha256(row["content"].encode()).hexdigest(),
            "approval_message_at": datetime.fromtimestamp(row["timestamp"], timezone.utc).isoformat()}


def decide(profile, environment, error_id, revision, request_hash, decision, rpc=record_rpc):
    import fcntl
    proof = authenticated_reply(profile, environment)
    error_id = str(uuid.UUID(error_id))
    if revision < 1 or not re.fullmatch(r"[0-9a-f]{64}", request_hash) or decision not in {"approve", "reject", "defer"}:
        raise ValueError("Invalid decision identity")
    entry_id = str(uuid.uuid5(uuid.UUID(error_id), f"sam:{revision}:{request_hash}:{decision}"))
    directory = profile / "state" / "exdigm_approvals"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = directory / (entry_id+".json")
    with path.with_suffix(".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            if json.loads(payload["details_json"])["approval_user_id"] != proof["approval_user_id"]:
                raise ValueError("A different owner already recorded this decision")
        else:
            case = rpc([error_id, "--read"])
            request = request_view(case)
            if request["revision"] != revision or request["request_hash"] != request_hash:
                raise ValueError("Approval request changed; inspect the current request and obtain a decision on that version")
            history = [item for item in case["processing_history"] if item.get("revision") == revision]
            if len(history) != 1 or not history[0].get("recorded_at"):
                raise ValueError("The request revision has no recorded origin")
            if datetime.fromisoformat(proof["approval_message_at"]) < datetime.fromisoformat(history[0]["recorded_at"]):
                raise ValueError("A message from before this request cannot authorize it")
            details = {**proof, "approval_decision": decision, "approval_request_revision": str(revision),
                       "approval_request_hash": request_hash, "approval_request_type": request["next_action"],
                       "approval_commit": request["details"].get("commit", ""), "approval_entry_id": entry_id}
            action = request["next_action"]
            if decision == "reject":
                action = "user_action"
                details.update(owner="controlroom", required_action="주인님의 거절 사유에 맞게 요청을 검토하세요.",
                               resume_condition="검토한 새 요청에 대한 주인님의 명시적 지시")
            payload = {"error_id": error_id, "status": "succeeded", "expected_revision": revision, "entry_id": entry_id,
                       "action": f"샘이 주인님의 {decision} 결정을 요청 개정 {revision}에 기록했습니다. 작업 실행 결과와 구분합니다.",
                       "next_action": action, "details_json": json.dumps(details, ensure_ascii=False)}
            save_json(path, payload)
        saved = rpc(["--json-input"], payload)
    receipts = [item for item in saved["processing_history"] if item.get("entry_id") == entry_id]
    if len(receipts) != 1 or receipts[0].get("handling_context", {}).get("approval_request_hash") != request_hash:
        raise ValueError("The DB did not confirm this decision")
    return {"error_id": error_id, "decision": decision, "approval_entry_id": entry_id,
            "request_revision": revision, "recorded_revision": receipts[0]["revision"],
            "current_revision": saved["handling_revision"], "next_action": saved["next_action"],
            "commit": receipts[0]["handling_context"].get("approval_commit", ""),
            "execution_allowed": decision == "approve" and saved["handling_revision"] == receipts[0]["revision"]}


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("inspect", "decide"))
    parser.add_argument("error_id", type=uuid.UUID)
    parser.add_argument("--revision", type=int)
    parser.add_argument("--request-hash")
    parser.add_argument("--decision", choices=("approve", "reject", "defer"))
    args = parser.parse_args()
    if args.action == "inspect":
        output = request_view(record_rpc([str(args.error_id), "--read"]))
    else:
        if args.revision is None or not args.request_hash or not args.decision:
            parser.error("decide requires revision, request-hash and decision")
        profile = Path(os.environ.get("HERMES_HOME", str(Path.home()/".hermes"))).resolve()
        output = decide(profile, os.environ, str(args.error_id), args.revision, args.request_hash, args.decision)
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
