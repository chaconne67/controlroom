#!/usr/bin/env python3
"""Forced SSH entry points for GBrain and the operational-error pipeline."""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
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
    "alternatives", "recommendation_reason", "impact", "verification", "rollback", "commit", "stop_reason",
    "outcome_verification", "execution_evidence", "verification_commands",
    "base_commit", "repair_ref", "workspace_reserved", "test_targets",
}
RESULT_ACTIONS = {
    "user_action", "external_wait", "approve_change", "approve_deploy",
    "verify_result", "none",
}
PIPELINE_FIELDS = {
    "operation", "event_id", "track_id", "automation_run", "mode", "status",
    "action", "processed_at", "category", "next_action", "expected_revision",
    "entry_id", "actor", "details", "children", "request_hash", "decision",
    "proof", "subject_revision", "delivery",
}
PIPELINE_DETAIL_FIELDS = {
    *DETAIL_FIELDS, "verification_receipt", "deployment_status",
    "deployed_commit", "deployment_evidence", "executor",
}
SAM_PROOF_FIELDS = {
    "approval_message_id", "approval_chat_id", "approval_message_at",
    "approval_actor_id", "approval_message_sha256", "approval_session_id",
    "instruction", "recorded_by",
}
SAM_DELIVERY_FIELDS = {"message_id", "chat_id", "delivered_at"}
DEPLOY_FIELDS = {
    "track_id", "expected_revision", "commit", "repair_ref",
    "approval_entry_id", "request_hash",
}


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


def pipeline_args(arguments, worker):
    if arguments == ["pipeline", "--json-input"]:
        return arguments
    if len(arguments) == 6 and arguments[:2] == ["pipeline", "claim"]:
        if arguments[2] != "--mode" or arguments[4] != "--automation-run":
            raise ValueError("Invalid pipeline claim arguments")
        if arguments[3] != worker:
            raise ValueError("This identity cannot claim that pipeline mode")
        uuid.UUID(arguments[5])
        return arguments
    if len(arguments) == 4 and tuple(arguments[:2]) in {
        ("pipeline", "read-track"),
        ("pipeline", "read-event"),
    }:
        expected = "--track-id" if arguments[1] == "read-track" else "--event-id"
        if arguments[2] != expected:
            raise ValueError("Invalid pipeline read arguments")
        uuid.UUID(arguments[3])
        return arguments
    raise ValueError("Only pipeline claim, read, and owned writes are allowed")


def record_args(arguments, worker="repair"):
    if arguments and arguments[0] == "pipeline":
        return pipeline_args(arguments, worker)
    if len(arguments) == 3 and arguments[:2] == ["--claim-next", "--automation-run"]:
        if worker != "repair":
            raise ValueError("Legacy claims belong to the repair worker")
        uuid.UUID(arguments[2])
    elif len(arguments) == 2 and arguments[1] == "--read":
        if worker != "repair":
            raise ValueError("Legacy reads belong to the repair worker")
        uuid.UUID(arguments[0])
    elif arguments != ["--json-input"]:
        raise ValueError("Only claim, read, and owned result recording are allowed")
    elif worker != "repair":
        raise ValueError("Legacy results belong to the repair worker")
    return arguments


def authorize_result(payload, case):
    if not isinstance(payload, dict) or set(payload) - RESULT_FIELDS:
        raise ValueError("Unsupported result fields")
    if payload.get("status") not in {"succeeded", "failed"} or payload.get("next_action") not in RESULT_ACTIONS:
        raise ValueError("Only completed handling results are allowed")
    run = uuid.UUID(case["handling_context"]["automation_run"])
    allowed_ids = {str(uuid.uuid5(run, kind)) for kind in ("result", "interrupted")}
    if payload.get("entry_id") not in allowed_ids or str(case["id"]) != payload.get("error_id"):
        raise ValueError("The result must belong to the claimed automation run")
    if type(payload.get("expected_revision")) is not int:
        raise ValueError("The claimed revision is required")
    details = json.loads(payload.get("details_json", "null"))
    if not isinstance(details, dict) or set(details) - DETAIL_FIELDS:
        raise ValueError("Approval decisions and other context fields are forbidden")
    return payload


def authorize_pipeline(payload, case, worker, existing=None):
    if not isinstance(payload, dict) or set(payload) - PIPELINE_FIELDS:
        raise ValueError("Unsupported pipeline fields")
    operation = payload.get("operation")
    if operation not in {"result", "split"}:
        raise ValueError("Worker identities can only record owned results or splits")
    run = uuid.UUID(case["handling_context"]["automation_run"])
    if str(case["id"]) != str(payload.get("track_id")):
        raise ValueError("The pipeline result must belong to the claimed track")
    if type(payload.get("expected_revision")) is not int:
        raise ValueError("The claimed track revision is required")
    actor = "main_codex" if worker == "repair" else "deploy_codex"
    replay = existing is not None and (
        str(existing.get("track_id")) == str(case["id"])
        and existing.get("track_revision") == payload.get("expected_revision", -1) + 1
        and existing.get("event_type") == "result_recorded"
        and existing.get("actor") == actor
    )
    if existing is not None and not replay:
        raise ValueError("The pipeline entry identity belongs to another transition")
    if not replay and payload.get("expected_revision") != case["revision"]:
        raise ValueError("The claimed track revision is required")
    if payload.get("actor") != actor:
        raise ValueError("The technical result actor does not match this identity")
    if operation == "split":
        if worker != "repair" or (
            not replay and case["next_action"] != "investigate"
        ):
            raise ValueError("Only the investigation worker can split a track")
        if payload.get("entry_id") != str(uuid.uuid5(run, "split")):
            raise ValueError("The split must belong to the claimed automation run")
        children = payload.get("children")
        if not isinstance(children, list) or not 2 <= len(children) <= 10:
            raise ValueError("A split needs two to ten child tracks")
        return payload
    allowed_ids = {str(uuid.uuid5(run, kind)) for kind in ("result", "interrupted")}
    if payload.get("entry_id") not in allowed_ids:
        raise ValueError("The result must belong to the claimed automation run")
    if payload.get("status") not in {"succeeded", "failed"}:
        raise ValueError("Only completed pipeline results are allowed")
    transitions = {
        "repair": {
            "investigate": {"approve_change", "user_action", "external_wait", "none"},
            "repair": {"approve_deploy", "approve_change", "user_action", "external_wait"},
            "verify_result": {"approve_close", "approve_change", "user_action", "external_wait"},
        },
        "deploy": {
            "deploy": {"verify_result", "external_wait"},
        },
    }
    allowed = transitions.get(worker, {}).get(case["next_action"], set())
    if not replay and payload.get("next_action") not in allowed:
        raise ValueError("The result is not a valid transition for this worker")
    details = payload.get("details")
    if not isinstance(details, dict) or set(details) - PIPELINE_DETAIL_FIELDS:
        raise ValueError("Approval decisions and unsupported context fields are forbidden")
    return payload


def record(arguments, worker="repair"):
    arguments = record_args(arguments, worker)
    # This file and environment are root-owned. Product code is the immutable
    # deployed checkout, never the editable debug worktree or its dependencies.
    environment = json.loads(Path("/etc/exdigm/repair-record.json").read_text())
    os.environ.clear()
    os.environ.update(environment)
    os.environ.update(PATH="/usr/bin:/bin", PYTHON_DOTENV_DISABLED="1")
    root = Path("/home/chaconne/exdigm")
    os.chdir(root)
    sys.path.insert(0, str(root))
    import django
    django.setup()
    from django.core.management import call_command
    from projects.models import (
        OperationalError,
        OperationalErrorTrack,
        OperationalErrorTransition,
    )
    if arguments and arguments[0] == "pipeline":
        pipeline_arguments = arguments[1:]
        if pipeline_arguments == ["--json-input"]:
            payload = json.load(sys.stdin)
            if not isinstance(payload, dict):
                raise ValueError("Unsupported pipeline input")
            case = OperationalErrorTrack.objects.values(
                "id", "revision", "next_action", "handling_context"
            ).get(pk=payload.get("track_id"))
            existing = OperationalErrorTransition.objects.values(
                "track_id", "track_revision", "event_type", "actor"
            ).filter(entry_id=payload.get("entry_id")).first()
            authorize_pipeline(payload, case, worker, existing)
            sys.stdin = io.StringIO(json.dumps(payload, ensure_ascii=False))
        call_command("manage_operational_error", *pipeline_arguments)
        return
    if arguments == ["--json-input"]:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict) or set(payload) - RESULT_FIELDS:
            raise ValueError("Unsupported result fields")
        case = OperationalError.objects.values("id", "handling_context").get(pk=payload.get("error_id"))
        authorize_result(payload, case)
        sys.stdin = io.StringIO(json.dumps(payload, ensure_ascii=False))
    call_command("record_operational_error_result", *arguments)


def sam_record(arguments):
    arguments = pipeline_args(arguments, "sam")
    environment = json.loads(Path("/etc/exdigm/repair-record.json").read_text())
    os.environ.clear()
    os.environ.update(environment)
    os.environ.update(PATH="/usr/bin:/bin", PYTHON_DOTENV_DISABLED="1")
    root = Path("/home/chaconne/exdigm")
    os.chdir(root)
    sys.path.insert(0, str(root))
    import django
    django.setup()
    from django.core.management import call_command
    pipeline_arguments = arguments[1:]
    if pipeline_arguments == ["--json-input"]:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict) or set(payload) - PIPELINE_FIELDS:
            raise ValueError("Unsupported Sam pipeline fields")
        operation = payload.get("operation")
        if operation == "decide":
            if payload.get("decision") not in {
                "approve",
                "reject",
                "defer",
                "revise",
                "respond",
            }:
                raise ValueError("Invalid owner decision")
            proof = payload.get("proof")
            if not isinstance(proof, dict) or set(proof) - SAM_PROOF_FIELDS:
                raise ValueError("Invalid owner decision proof")
        elif operation == "delivery":
            delivery = payload.get("delivery")
            if not isinstance(delivery, dict) or set(delivery) - SAM_DELIVERY_FIELDS:
                raise ValueError("Invalid report delivery proof")
        else:
            raise ValueError("Sam can only record owner decisions and report delivery")
        sys.stdin = io.StringIO(json.dumps(payload, ensure_ascii=False))
    call_command("manage_operational_error", *pipeline_arguments)


def _deployment_contract(payload):
    if not isinstance(payload, dict) or set(payload) != DEPLOY_FIELDS:
        raise ValueError("Invalid deployment contract fields")
    for name in ("track_id", "approval_entry_id"):
        uuid.UUID(str(payload[name]))
    if type(payload["expected_revision"]) is not int:
        raise ValueError("Deployment revision is required")
    if (
        not isinstance(payload["commit"], str)
        or len(payload["commit"]) != 40
        or any(character not in "0123456789abcdef" for character in payload["commit"])
    ):
        raise ValueError("Deployment commit is invalid")
    if not payload["repair_ref"].startswith("refs/operational-repairs/"):
        raise ValueError("Deployment repair ref is invalid")
    uuid.UUID(payload["repair_ref"].removeprefix("refs/operational-repairs/"))
    if (
        not isinstance(payload["request_hash"], str)
        or len(payload["request_hash"]) != 64
        or any(character not in "0123456789abcdef" for character in payload["request_hash"])
    ):
        raise ValueError("Deployment request hash is invalid")
    return payload


def _load_deployment_track(payload):
    from projects.models import OperationalErrorTrack, OperationalErrorTransition

    track = OperationalErrorTrack.objects.get(pk=payload["track_id"])
    context = track.handling_context
    if track.next_action != "deploy" or track.revision != payload["expected_revision"]:
        raise ValueError("Deployment track changed")
    expected = {
        "commit": payload["commit"],
        "repair_ref": payload["repair_ref"],
        "approval_entry_id": payload["approval_entry_id"],
        "approval_request_hash": payload["request_hash"],
        "approval_decision": "approve",
        "approved_action": "approve_deploy",
    }
    if any(context.get(key) != value for key, value in expected.items()):
        raise ValueError("Deployment does not match the owner-approved request")
    base = context.get("base_commit")
    receipt = context.get("verification_receipt")
    if (
        not isinstance(base, str)
        or len(base) != 40
        or any(character not in "0123456789abcdef" for character in base)
        or not isinstance(receipt, str)
        or not receipt.startswith("sha256:")
        or len(receipt) != 71
        or any(character not in "0123456789abcdef" for character in receipt[7:])
    ):
        raise ValueError("Approved deployment evidence is incomplete")
    decision = OperationalErrorTransition.objects.get(
        entry_id=payload["approval_entry_id"],
        track=track,
        event_type="decision_recorded",
        actor="owner",
    )
    decision_context = decision.payload.get("handling_context", {})
    approved_evidence = {
        **expected,
        "base_commit": base,
        "verification_receipt": receipt,
    }
    if any(
        decision_context.get(key) != value
        for key, value in approved_evidence.items()
    ):
        raise ValueError("Owner approval ledger does not match deployment")
    return track


def _git_read(root, *arguments):
    return subprocess.check_output(
        ["git", "-C", str(root), *arguments], text=True
    ).strip()


def _read_deployment_receipt(path, payload, production_head):
    if not path.exists():
        return None
    receipt = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "track_id": payload["track_id"],
        "approval_entry_id": payload["approval_entry_id"],
        "approved_commit": payload["commit"],
        "production_commit": production_head,
        "completed": True,
    }
    deployment_log = receipt.get("deployment_log") if isinstance(receipt, dict) else None
    log_path = Path(deployment_log) if isinstance(deployment_log, str) else None
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
        "track_id": payload["track_id"],
        "approval_entry_id": payload["approval_entry_id"],
        "approved_commit": payload["commit"],
        "production_commit": production_commit,
        "deployment_log": str(log_path),
        "completed": True,
    }
    temporary = path.with_suffix(".tmp")
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    with os.fdopen(descriptor, "w") as stream:
        json.dump(receipt, stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    return receipt


def deploy(arguments):
    if arguments not in (["execute"], ["status"]):
        raise ValueError("Only exact deployment execution and status are allowed")
    payload = _deployment_contract(json.load(sys.stdin))
    environment = json.loads(Path("/etc/exdigm/repair-record.json").read_text())
    os.environ.clear()
    os.environ.update(environment)
    os.environ.update(PATH="/usr/local/bin:/usr/bin:/bin", PYTHON_DOTENV_DISABLED="1")
    production = Path("/home/chaconne/exdigm")
    debug = Path("/home/chaconne/exdigm-debug")
    os.chdir(production)
    sys.path.insert(0, str(production))
    import django
    django.setup()
    track = _load_deployment_track(payload)
    production_head = _git_read(production, "rev-parse", "HEAD")
    runtime = debug / "runtime"
    receipt_path = runtime / f"deployment-{payload['approval_entry_id']}.json"
    receipt = _read_deployment_receipt(receipt_path, payload, production_head)
    receipt_confirmed = receipt is not None
    result = {
        "track_id": str(track.pk),
        "approved_commit": payload["commit"],
        "production_commit": production_head,
        "deployment_completed": receipt is not None,
    }
    if receipt is not None:
        result["deployment_log"] = receipt["deployment_log"]
    if arguments == ["status"]:
        print(json.dumps(result))
        return

    import fcntl
    runtime.mkdir(exist_ok=True)
    lock_stream = (runtime / "operational-repair.lock").open("a")
    fcntl.flock(lock_stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
    reservation = runtime / "operational-repair.json"
    run_id = payload["approval_entry_id"]
    if reservation.exists():
        if json.loads(reservation.read_text())["run_id"] != run_id:
            raise ValueError("Another task owns the deployment workspace")
    else:
        descriptor = os.open(
            reservation,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o644,
        )
        with os.fdopen(descriptor, "w") as stream:
            json.dump({"run_id": run_id, "purpose": "approved-deployment"}, stream)
            stream.flush()
            os.fsync(stream.fileno())
    success = False
    try:
        if _git_read(debug, "status", "--porcelain"):
            raise ValueError("Debug workspace is not clean")
        if subprocess.run(
            ["git", "-C", str(debug), "symbolic-ref", "-q", "HEAD"],
            stdout=subprocess.DEVNULL,
        ).returncode != 1:
            raise ValueError("Debug workspace is not detached")
        if _git_read(debug, "rev-parse", payload["repair_ref"]) != payload["commit"]:
            raise ValueError("Frozen repair ref does not match the approved commit")
        base = track.handling_context.get("base_commit")
        if production_head not in {base, payload["commit"]}:
            raise ValueError("Production changed after deployment approval")
        subprocess.run(
            ["git", "-C", str(debug), "merge-base", "--is-ancestor", base, payload["commit"]],
            check=True,
        )
        if production_head != payload["commit"] or receipt is None:
            subprocess.run(
                ["git", "-C", str(debug), "switch", "--detach", payload["commit"]],
                check=True,
            )
            log_path = runtime / f"deployment-{run_id}.log"
            completed = subprocess.run(
                ["scripts/deploy/deploy.sh", "prod"],
                cwd=debug,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            log_path.write_text(completed.stdout, encoding="utf-8")
            os.chmod(log_path, 0o600)
            if completed.returncode:
                raise RuntimeError("Official production deployment failed")
        else:
            log_path = runtime / f"deployment-{run_id}.log"
            if not log_path.exists():
                log_path.write_text(
                    "Production already matched the exact owner-approved commit.\n",
                    encoding="utf-8",
                )
                os.chmod(log_path, 0o600)
        deployed = _git_read(production, "rev-parse", "HEAD")
        if deployed != payload["commit"] or _git_read(production, "status", "--porcelain"):
            raise RuntimeError("Production did not reach the approved clean commit")
        receipt = _write_deployment_receipt(
            receipt_path,
            payload,
            deployed,
            log_path,
        )
        result.update(
            production_commit=deployed,
            deployment_log=str(log_path),
            deployment_completed=True,
            idempotent=(
                production_head == payload["commit"] and receipt_confirmed
            ),
        )
        success = True
        print(json.dumps(result))
    finally:
        if success:
            reservation.unlink(missing_ok=True)
        lock_stream.close()


def main():
    arguments = shlex.split(os.environ.get("SSH_ORIGINAL_COMMAND", ""))
    mode = sys.argv[1] if len(sys.argv) == 2 else ""
    if not arguments or arguments.pop(0) != mode:
        raise ValueError("Explicit forced-command mode is required")
    if mode == "gbrain":
        os.execv("/srv/consolidation/infra/gbrain-host",
                 ["gbrain-host", *gbrain_args(arguments)])
    elif mode == "record":
        record(arguments, "repair")
    elif mode == "deploy-record":
        record(arguments, "deploy")
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
        # Keep DB connection strings and source material out of SSH error output.
        print(f"Restricted request failed: {type(error).__name__}", file=sys.stderr)
        raise SystemExit(1)
