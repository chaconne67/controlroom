#!/usr/bin/env python3
"""Narrow forced-SSH entry points for the Exdigm operational-error board.

The product host only exposes the existing OperationalError row as a board.
Main may claim/read/write technical results and execute one exact approved
deployment. Sam may list completed results, read approval facts, and append an
owner decision. No endpoint calls Codex or another agent.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import uuid


RESULT_FIELDS = {
    "error_id", "status", "action", "category", "next_action",
    "expected_revision", "entry_id", "details_json",
}
DETAIL_FIELDS = {
    "root_cause", "owner", "required_action", "resume_condition", "proposal",
    "alternatives", "recommendation_reason", "impact", "verification",
    "rollback", "commit", "stop_reason",
    "outcome_verification", "execution_evidence", "verification_commands",
    "base_commit", "repair_ref", "workspace_reserved", "test_targets",
    "deployed_commit", "deployment_evidence",
}
RESULT_ACTIONS = {
    "user_action", "external_wait", "approve_change", "approve_deploy",
    "verify_result", "none",
}
RESULT_TRANSITIONS = {
    "investigate": {
        "approve_change", "approve_deploy", "user_action", "external_wait", "none",
    },
    "repair": {"approve_change", "approve_deploy", "user_action", "external_wait"},
    "deploy": {"verify_result", "external_wait"},
    "verify_result": {"approve_change", "user_action", "external_wait", "none"},
}
SAM_DECISIONS = {"approve", "reject", "defer", "revise", "respond"}
SAM_PROOF_FIELDS = {
    "approval_actor", "approval_user_id", "approval_session_id", "approval_chat_id",
    "approval_message_id", "approval_message_sha256", "approval_message_at",
}
SAM_DETAIL_FIELDS = {
    *SAM_PROOF_FIELDS, "owner_decision", "owner_instruction",
    "approval_decision", "approval_request_revision", "approval_request_hash",
    "approval_request_type", "approval_commit", "approval_entry_id", "stop_reason",
}
DEPLOY_FIELDS = {
    "error_id", "expected_revision", "automation_run", "commit", "repair_ref",
    "approval_entry_id", "request_hash",
}
HEX40 = re.compile(r"[0-9a-f]{40}")
HEX64 = re.compile(r"[0-9a-f]{64}")
REPAIR_REF = re.compile(r"refs/operational-repairs/([0-9a-f-]{36})")


def gbrain_args(arguments):
    """Only explicit public-source reads; no capture, SQL, or shell commands."""
    if not arguments or arguments[0] not in {"get", "query", "list"}:
        raise ValueError("Only public GBrain reads are allowed")
    command = arguments[0]
    positional = 1 if command == "list" else 2
    if len(arguments) < positional or (positional == 2 and arguments[1].startswith("-")):
        raise ValueError("A page or query is required")
    source_flag = "--source-id" if command == "query" else "--source"
    options = arguments[positional:]
    if len(options) < 2 or options[:2] != [source_flag, "default"]:
        raise ValueError("The public default source must be explicit")
    if any(option not in {"--json", "--include-content"} for option in options[2:]):
        raise ValueError("Unsupported read option")
    return arguments


def record_args(arguments):
    if len(arguments) == 3 and arguments[:2] == ["--claim-next", "--automation-run"]:
        uuid.UUID(arguments[2])
    elif len(arguments) == 2 and arguments[1] == "--read":
        uuid.UUID(arguments[0])
    elif arguments != ["--json-input"]:
        raise ValueError("Only claim, read, and owned result recording are allowed")
    return arguments


def sam_args(arguments):
    if arguments in (["--list"], ["--json-input"]):
        return arguments
    if len(arguments) == 2 and arguments[1] == "--read":
        uuid.UUID(arguments[0])
        return arguments
    raise ValueError("Sam can only list/read the board or record an owner response")


def _canonical_request(case):
    action = case["next_action"]
    details = case.get("handling_context") or {}
    required = {
        "approve_change": ("proposal", "impact", "verification", "rollback"),
        "approve_deploy": ("commit", "verification", "rollback"),
        "user_action": ("owner", "required_action", "resume_condition"),
        "external_wait": ("owner", "resume_condition"),
    }
    if action not in required or any(
        not isinstance(details.get(key), str) or not details[key].strip()
        for key in required[action]
    ):
        raise ValueError("The row has no complete owner request")
    if action == "approve_deploy" and not HEX40.fullmatch(details["commit"]):
        raise ValueError("The deployment request has no exact commit")
    request = {
        "error_id": str(case["id"]),
        "revision": case["handling_revision"],
        "next_action": action,
        "category": case["category"],
        "details": {
            key: value for key, value in details.items()
            if not key.startswith("approval_")
        },
    }
    encoded = json.dumps(
        request, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode()
    return request, hashlib.sha256(encoded).hexdigest()


def authorize_result(payload, case):
    if not isinstance(payload, dict) or set(payload) - RESULT_FIELDS:
        raise ValueError("Unsupported result fields")
    if (
        payload.get("status") not in {"succeeded", "failed"}
        or payload.get("next_action") not in RESULT_ACTIONS
    ):
        raise ValueError("Only completed handling results are allowed")
    run = uuid.UUID(case["handling_context"]["automation_run"])
    allowed_ids = {str(uuid.uuid5(run, kind)) for kind in ("result", "interrupted")}
    if payload.get("entry_id") not in allowed_ids or str(case["id"]) != payload.get("error_id"):
        raise ValueError("The result must belong to the claimed automation run")
    if type(payload.get("expected_revision")) is not int:
        raise ValueError("The claimed revision is required")
    details = json.loads(payload.get("details_json", "null"))
    if not isinstance(details, dict) or set(details) - DETAIL_FIELDS:
        raise ValueError("Approval decisions and unsupported context fields are forbidden")
    existing = next(
        (row for row in case.get("processing_history", []) if row.get("entry_id") == payload["entry_id"]),
        None,
    )
    if existing is None and payload["next_action"] not in RESULT_TRANSITIONS.get(case["next_action"], set()):
        raise ValueError("The worker result is not valid for the current board action")
    return payload


def _sam_target(request_action, decision):
    if decision == "approve":
        return {"approve_change": "repair", "approve_deploy": "deploy"}.get(request_action)
    if decision == "reject":
        return "none"
    if decision == "defer":
        return request_action
    if decision == "revise" and request_action in {"approve_change", "approve_deploy"}:
        return "investigate"
    if decision == "respond" and request_action in {"user_action", "external_wait"}:
        return "investigate"
    return None


def authorize_sam(payload, case):
    if not isinstance(payload, dict) or set(payload) - RESULT_FIELDS:
        raise ValueError("Unsupported Sam result fields")
    if (
        payload.get("status") != "succeeded"
        or str(case["id"]) != payload.get("error_id")
        or type(payload.get("expected_revision")) is not int
        or "category" in payload
    ):
        raise ValueError("Sam may only append one completed owner response")
    details = json.loads(payload.get("details_json", "null"))
    if not isinstance(details, dict) or set(details) - SAM_DETAIL_FIELDS or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in details.items()
    ):
        raise ValueError("Owner response details must be text fields")
    decision = details.get("owner_decision")
    if (
        decision not in SAM_DECISIONS
        or details.get("approval_actor") != "sam"
        or details.get("approval_decision") != decision
        or details.get("approval_request_revision") != str(payload["expected_revision"])
        or not HEX64.fullmatch(details.get("approval_message_sha256", ""))
        or any(not details.get(key) for key in SAM_PROOF_FIELDS)
    ):
        raise ValueError("Owner response proof is incomplete")
    request_type = details.get("approval_request_type")
    request_hash = details.get("approval_request_hash")
    if not HEX64.fullmatch(request_hash or ""):
        raise ValueError("Owner response request hash is invalid")
    entry_id = str(uuid.uuid5(
        uuid.UUID(str(case["id"])),
        (
            f"sam:{payload['expected_revision']}:{request_hash}:{decision}:"
            f"{details['approval_message_id']}:"
            f"{hashlib.sha256(details.get('owner_instruction', '').encode()).hexdigest()}"
        ),
    ))
    if payload.get("entry_id") != entry_id or details.get("approval_entry_id") != entry_id:
        raise ValueError("Owner response identity does not match its request")
    previous = next(
        (row for row in case.get("processing_history", []) if row.get("entry_id") == entry_id),
        None,
    )
    if previous is not None:
        if (
            previous.get("status") != payload.get("status")
            or previous.get("action") != payload.get("action")
            or previous.get("next_action") != payload.get("next_action")
        ):
            raise ValueError("The owner response replay differs from its receipt")
        return payload
    request, current_hash = _canonical_request(case)
    target = _sam_target(request["next_action"], decision)
    if (
        request["revision"] != payload["expected_revision"]
        or current_hash != request_hash
        or request_type != request["next_action"]
        or target is None
        or payload.get("next_action") != target
    ):
        raise ValueError("The owner response does not match the current request")
    instruction = details.get("owner_instruction", "").strip()
    if decision in {"revise", "respond"} and not instruction:
        raise ValueError("This owner response requires the owner's instruction")
    if decision == "approve" and request_type == "approve_deploy":
        if details.get("approval_commit") != request["details"]["commit"]:
            raise ValueError("Deployment approval does not match the requested commit")
    return payload


def _setup_django():
    environment = json.loads(Path("/etc/exdigm/repair-record.json").read_text())
    os.environ.clear()
    os.environ.update(environment)
    os.environ.update(PATH="/usr/local/bin:/usr/bin:/bin", PYTHON_DOTENV_DISABLED="1")
    root = Path("/home/chaconne/exdigm")
    os.chdir(root)
    sys.path.insert(0, str(root))
    import django
    django.setup()
    return root


def record(arguments):
    arguments = record_args(arguments)
    _setup_django()
    from django.core.management import call_command
    from projects.models import OperationalError
    if arguments == ["--json-input"]:
        payload = json.load(sys.stdin)
        case = OperationalError.objects.values(
            "id", "next_action", "handling_context", "processing_history"
        ).get(pk=payload.get("error_id"))
        authorize_result(payload, case)
        sys.stdin = io.StringIO(json.dumps(payload, ensure_ascii=False))
    call_command("record_operational_error_result", *arguments)


def _safe_case(error):
    return {
        "id": str(error.pk),
        "created_at": error.created_at.isoformat(),
        "occurred_at": error.occurred_at.isoformat(),
        "summary": error.summary,
        "source": error.source,
        "error_type": error.error_type,
        "processing_status": error.processing_status,
        "processing_history": [
            {
                key: entry[key]
                for key in ("revision", "recorded_at", "entry_id", "status")
                if key in entry
            }
            for entry in (
                error.processing_history
                if isinstance(error.processing_history, list)
                else []
            )
        ],
        "category": error.category,
        "next_action": error.next_action,
        "handling_revision": error.handling_revision,
        "handling_context": error.handling_context,
    }


def _sam_list(OperationalError):
    state = json.load(sys.stdin)
    delivered = state.get("delivered_revisions", {}) if isinstance(state, dict) else None
    if not isinstance(delivered, dict) or any(
        not isinstance(key, str) or type(value) is not int or value < 0
        for key, value in delivered.items()
    ):
        raise ValueError("Delivered revisions must be a UUID-to-integer mapping")
    rows = []
    for error in OperationalError.objects.order_by("created_at", "id").iterator():
        if error.summary == "테스트 오류 기록입니다. 실제 운영 장애가 아닙니다.":
            continue
        seen = delivered.get(str(error.pk), 0)
        results = []
        for entry in error.processing_history if isinstance(error.processing_history, list) else []:
            revision = entry.get("revision", 0)
            if (
                type(revision) is int
                and revision > seen
                and entry.get("status") in {"succeeded", "failed"}
                and entry.get("entry_id")
                != (entry.get("handling_context") or {}).get("approval_entry_id")
            ):
                results.append(entry)
        if results:
            row = _safe_case(error)
            row["processing_results"] = results
            row["handling_revision"] = max(entry["revision"] for entry in results)
            row["current_handling_revision"] = error.handling_revision
            rows.append(row)
        if len(rows) == 100:
            break
    print(json.dumps({"available": True, "errors": rows}, ensure_ascii=False))


def sam_record(arguments):
    arguments = sam_args(arguments)
    _setup_django()
    from django.core.management import call_command
    from projects.models import OperationalError
    if arguments == ["--list"]:
        _sam_list(OperationalError)
        return
    if len(arguments) == 2 and arguments[1] == "--read":
        print(json.dumps(_safe_case(OperationalError.objects.get(pk=arguments[0])), ensure_ascii=False))
        return
    payload = json.load(sys.stdin)
    case = OperationalError.objects.values(
        "id", "category", "next_action", "handling_revision", "handling_context",
        "processing_history",
    ).get(pk=payload.get("error_id"))
    authorize_sam(payload, case)
    sys.stdin = io.StringIO(json.dumps(payload, ensure_ascii=False))
    call_command("record_operational_error_result", "--json-input")


def _deployment_contract(payload):
    if not isinstance(payload, dict) or set(payload) != DEPLOY_FIELDS:
        raise ValueError("Invalid deployment contract fields")
    for key in ("error_id", "automation_run", "approval_entry_id"):
        uuid.UUID(str(payload[key]))
    if type(payload["expected_revision"]) is not int:
        raise ValueError("Deployment revision is required")
    if not HEX40.fullmatch(payload["commit"]):
        raise ValueError("Deployment commit is invalid")
    match = REPAIR_REF.fullmatch(payload["repair_ref"])
    if not match:
        raise ValueError("Deployment repair ref is invalid")
    uuid.UUID(match.group(1))
    if not HEX64.fullmatch(payload["request_hash"]):
        raise ValueError("Deployment request hash is invalid")
    return payload


def _git_read(root, *arguments):
    return subprocess.check_output(["git", "-C", str(root), *arguments], text=True).strip()


def _read_deployment_receipt(path, payload, production_head):
    if not path.exists():
        return None
    receipt = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "error_id": payload["error_id"],
        "approval_entry_id": payload["approval_entry_id"],
        "approved_commit": payload["commit"],
        "production_commit": production_head,
        "completed": True,
    }
    log_path = Path(receipt.get("deployment_log", "")) if isinstance(receipt, dict) else None
    if (
        not isinstance(receipt, dict)
        or any(receipt.get(key) != value for key, value in expected.items())
        or log_path is None
        or log_path.parent != path.parent
        or not log_path.is_file()
    ):
        raise ValueError("Deployment completion receipt is invalid")
    return receipt


def _write_deployment_receipt(path, payload, production_commit, log_path):
    receipt = {
        "error_id": payload["error_id"],
        "approval_entry_id": payload["approval_entry_id"],
        "approved_commit": payload["commit"],
        "production_commit": production_commit,
        "deployment_log": str(log_path),
        "completed": True,
    }
    temporary = path.with_suffix(".tmp")
    descriptor = os.open(
        temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0), 0o600
    )
    with os.fdopen(descriptor, "w") as stream:
        json.dump(receipt, stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    return receipt


def _authorize_deployment_row(error, payload):
    context = error.handling_context if isinstance(error.handling_context, dict) else {}
    expected = {
        "automation_run": payload["automation_run"],
        "commit": payload["commit"],
        "repair_ref": payload["repair_ref"],
        "approval_entry_id": payload["approval_entry_id"],
        "approval_request_hash": payload["request_hash"],
        "approval_decision": "approve",
        "approval_request_type": "approve_deploy",
        "workspace_reserved": "yes",
    }
    if (
        error.next_action != "deploy"
        or error.processing_status != "in_progress"
        or error.handling_revision != payload["expected_revision"]
        or any(context.get(key) != value for key, value in expected.items())
    ):
        raise ValueError("Deployment does not match the current owner-approved row")
    decision = next(
        (entry for entry in error.processing_history if entry.get("entry_id") == payload["approval_entry_id"]),
        None,
    )
    if decision is None or any(
        (decision.get("handling_context") or {}).get(key) != value
        for key, value in expected.items()
        if key not in {"automation_run", "workspace_reserved"}
    ):
        raise ValueError("The owner approval receipt does not match the deployment")
    base = context.get("base_commit", "")
    if not HEX40.fullmatch(base):
        raise ValueError("The approved repair has no exact base commit")
    return base


def deploy(arguments):
    import fcntl

    if arguments != ["execute"]:
        raise ValueError("Only exact approved deployment execution is allowed")
    payload = _deployment_contract(json.load(sys.stdin))
    _setup_django()
    from projects.models import OperationalError
    error = OperationalError.objects.get(pk=payload["error_id"])
    base = _authorize_deployment_row(error, payload)

    production = Path("/home/chaconne/exdigm")
    debug = Path("/home/chaconne/exdigm-debug")
    runtime = debug / "runtime"
    reservation = runtime / "operational-repair.json"
    lock_stream = (runtime / "operational-repair.lock").open("a")
    try:
        try:
            fcntl.flock(lock_stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            pass
        else:
            fcntl.flock(lock_stream, fcntl.LOCK_UN)
            raise ValueError("The main worker is not holding the deployment workspace lock")
        if (
            not reservation.is_file()
            or json.loads(reservation.read_text()).get("run_id") != payload["automation_run"]
        ):
            raise ValueError("The deployment workspace reservation does not match the main worker")
        production_head = _git_read(production, "rev-parse", "HEAD")
        receipt_path = runtime / f"deployment-{payload['approval_entry_id']}.json"
        receipt = _read_deployment_receipt(receipt_path, payload, production_head)
        if receipt is None:
            if _git_read(debug, "status", "--porcelain"):
                raise ValueError("Debug workspace is not clean")
            if subprocess.run(
                ["git", "-C", str(debug), "symbolic-ref", "-q", "HEAD"],
                stdout=subprocess.DEVNULL,
            ).returncode != 1:
                raise ValueError("Debug workspace must remain detached")
            if _git_read(debug, "rev-parse", payload["repair_ref"]) != payload["commit"]:
                raise ValueError("Frozen repair ref does not match the approved commit")
            if production_head not in {base, payload["commit"]}:
                raise ValueError("Production changed after deployment approval")
            subprocess.run(
                ["git", "-C", str(debug), "merge-base", "--is-ancestor", base, payload["commit"]], check=True
            )
            subprocess.run(
                ["git", "-C", str(debug), "switch", "--detach", payload["commit"]], check=True
            )
            log_path = runtime / f"deployment-{payload['approval_entry_id']}.log"
            completed = subprocess.run(
                ["scripts/deploy/deploy.sh", "prod"], cwd=debug,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                encoding="utf-8", errors="replace",
            )
            log_path.write_text(completed.stdout, encoding="utf-8")
            os.chmod(log_path, 0o600)
            if completed.returncode:
                raise RuntimeError("Official production deployment failed")
            deployed = _git_read(production, "rev-parse", "HEAD")
            if deployed != payload["commit"] or _git_read(production, "status", "--porcelain"):
                raise RuntimeError("Production did not reach the approved clean commit")
            receipt = _write_deployment_receipt(receipt_path, payload, deployed, log_path)
        print(json.dumps({
            "error_id": payload["error_id"],
            "approved_commit": payload["commit"],
            "production_commit": receipt["production_commit"],
            "deployment_log": receipt["deployment_log"],
            "deployment_completed": True,
        }))
    finally:
        lock_stream.close()


def main():
    arguments = shlex.split(os.environ.get("SSH_ORIGINAL_COMMAND", ""))
    mode = sys.argv[1] if len(sys.argv) == 2 else ""
    if not arguments or arguments.pop(0) != mode:
        raise ValueError("Explicit forced-command mode is required")
    if mode == "gbrain":
        os.execv("/srv/consolidation/infra/gbrain-host", ["gbrain-host", *gbrain_args(arguments)])
    elif mode == "record":
        record(arguments)
    elif mode == "sam-record":
        sam_record(arguments)
    elif mode == "deploy":
        deploy(arguments)
    else:
        raise ValueError("Unsupported access mode")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Restricted request failed: {type(error).__name__}", file=sys.stderr)
        raise SystemExit(1)
