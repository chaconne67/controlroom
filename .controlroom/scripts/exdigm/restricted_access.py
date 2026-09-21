#!/usr/bin/env python3
"""Forced SSH entry points; reuse the existing GBrain and error-result commands."""
from __future__ import annotations

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
    "impact", "verification", "rollback", "commit", "stop_reason",
    "outcome_verification", "execution_evidence", "verification_commands",
    "base_commit", "repair_ref", "workspace_reserved", "test_targets",
}
RESULT_ACTIONS = {
    "user_action", "external_wait", "approve_change", "approve_deploy",
    "verify_result", "none",
}
DEPLOY_DEBUG_ROOT = Path("/home/chaconne/exdigm-debug")
DEPLOY_PRODUCTION_ROOT = Path("/home/chaconne/exdigm")
DEPLOY_SCRIPT = DEPLOY_DEBUG_ROOT / "scripts/deploy/deploy.sh"
DEPLOY_SERVICES = (
    "Exdigm_exdigm_app",
    "Exdigm_exdigm_sse",
    "Exdigm_exdigm_notification_dispatcher",
)


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


def record(arguments):
    arguments = record_args(arguments)
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
    from projects.models import OperationalError
    if arguments == ["--json-input"]:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict) or set(payload) - RESULT_FIELDS:
            raise ValueError("Unsupported result fields")
        case = OperationalError.objects.values("id", "handling_context").get(pk=payload.get("error_id"))
        authorize_result(payload, case)
        sys.stdin = io.StringIO(json.dumps(payload, ensure_ascii=False))
    call_command("record_operational_error_result", *arguments)


def deploy_args(arguments):
    """Accept only the fixed, revision-bound deployment protocol."""
    if arguments == ["check"]:
        return {"action": "check"}
    flags = ("--error-id", "--revision", "--commit", "--automation-run")
    if len(arguments) != 9 or arguments[0] not in {"execute", "verify"} \
            or tuple(arguments[index] for index in (1, 3, 5, 7)) != flags:
        raise ValueError("Invalid deployment request")
    error_id = str(uuid.UUID(arguments[2]))
    revision = int(arguments[4])
    commit = arguments[6]
    run_id = str(uuid.UUID(arguments[8]))
    if revision < 1 or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Invalid deployment identity")
    return {"action": arguments[0], "error_id": error_id, "revision": revision,
            "commit": commit, "automation_run": run_id}


def authorize_deploy(request, case):
    """Bind an exact approved request to the current main-runner claim."""
    if str(case.get("id")) != request["error_id"] \
            or case.get("handling_revision") != request["revision"] \
            or case.get("processing_status") != "in_progress" \
            or case.get("next_action") != "repair":
        raise ValueError("Deployment case is not the current claimed repair")
    details = case.get("handling_context")
    if not isinstance(details, dict) or any(details.get(key) != value for key, value in {
        "approval_decision": "approve",
        "approval_request_type": "approve_deploy",
        "approval_commit": request["commit"],
        "commit": request["commit"],
        "automation_run": request["automation_run"],
        "workspace_reserved": "yes",
    }.items()):
        raise ValueError("Deployment approval or ownership does not match")
    if not re.fullmatch(r"[0-9a-f]{40}", details.get("base_commit", "")) \
            or not re.fullmatch(r"refs/operational-repairs/[0-9a-f-]{36}", details.get("repair_ref", "")) \
            or not re.fullmatch(r"[0-9a-f]{64}", details.get("approval_request_hash", "")):
        raise ValueError("Deployment evidence is incomplete")
    approval_id = str(uuid.UUID(details.get("approval_entry_id", "")))
    run_id = request["automation_run"]
    history = case.get("processing_history")
    if not isinstance(history, list):
        raise ValueError("Deployment history is unavailable")
    approval = [item for item in history if item.get("entry_id") == approval_id]
    claim = [item for item in history if item.get("entry_id") == run_id]
    if len(approval) != 1 or approval[0].get("revision") != request["revision"] - 1 \
            or approval[0].get("next_action") != "repair" \
            or approval[0].get("handling_context", {}).get("approval_request_hash") != details["approval_request_hash"] \
            or len(claim) != 1 or claim[0].get("revision") != request["revision"]:
        raise ValueError("Deployment approval is not the immediately claimed decision")
    return details


def read_deploy_case(error_id):
    ids = subprocess.check_output([
        "docker", "ps", "-q", "--filter",
        "label=com.docker.swarm.service.name=Exdigm_exdigm_app",
    ], text=True).split()
    if len(ids) != 1:
        raise RuntimeError("One active Exdigm app task is required")
    output = subprocess.check_output([
        "docker", "exec", ids[0], "python", "manage.py",
        "record_operational_error_result", error_id, "--read",
    ], text=True)
    return json.loads(output)


def git_read(root, *arguments):
    return subprocess.check_output(
        ["git", "-C", str(root), *arguments], text=True
    ).strip()


def deployment_state(commit):
    production = git_read(DEPLOY_PRODUCTION_ROOT, "rev-parse", "HEAD")
    debug = git_read(DEPLOY_DEBUG_ROOT, "rev-parse", "HEAD")
    if git_read(DEPLOY_PRODUCTION_ROOT, "status", "--porcelain") \
            or git_read(DEPLOY_DEBUG_ROOT, "status", "--porcelain"):
        raise RuntimeError("Deployment worktrees must be clean")
    remote = git_read(DEPLOY_DEBUG_ROOT, "ls-remote", "origin", "refs/heads/main").split()
    if len(remote) != 2 or remote[0] != commit or production != commit or debug != commit:
        raise RuntimeError("Git deployment state does not match the approved commit")
    services = {}
    for service in DEPLOY_SERVICES:
        ids = subprocess.check_output([
            "docker", "ps", "-q", "--filter", f"label=com.docker.swarm.service.name={service}",
        ], text=True).split()
        if len(ids) != 1:
            raise RuntimeError("One active task is required for every deployed service")
        source = subprocess.check_output(
            ["docker", "exec", ids[0], "cat", "/app/.source-commit"], text=True
        ).strip()
        if source != commit:
            raise RuntimeError("A running service does not use the approved commit")
        services[service] = source
    return {"production": production, "debug": debug, "origin_main": remote[0],
            "services": services}


def deploy(arguments):
    request = deploy_args(arguments)
    if request["action"] == "check":
        import pwd
        if os.geteuid() == 0 or pwd.getpwuid(os.geteuid()).pw_name != "chaconne" \
                or not DEPLOY_SCRIPT.is_file() or not os.access(DEPLOY_SCRIPT, os.X_OK):
            raise RuntimeError("Approved deployment gateway is not ready")
        print(json.dumps({"ready": True, "executor": "chaconne",
                          "deploy_script": str(DEPLOY_SCRIPT)}))
        return
    details = authorize_deploy(request, read_deploy_case(request["error_id"]))
    if git_read(DEPLOY_DEBUG_ROOT, "rev-parse", details["repair_ref"]) != request["commit"]:
        raise RuntimeError("Saved repair reference does not match the approved commit")
    if request["action"] == "execute":
        production = git_read(DEPLOY_PRODUCTION_ROOT, "rev-parse", "HEAD")
        debug = git_read(DEPLOY_DEBUG_ROOT, "rev-parse", "HEAD")
        if production != request["commit"]:
            if production != details["base_commit"] or debug not in {details["base_commit"], request["commit"]} \
                    or git_read(DEPLOY_DEBUG_ROOT, "status", "--porcelain"):
                raise RuntimeError("Deployment base or debug workspace changed")
            if debug != request["commit"]:
                subprocess.run([
                    "git", "-C", str(DEPLOY_DEBUG_ROOT), "switch", "--detach", request["commit"],
                ], check=True)
            subprocess.run([str(DEPLOY_SCRIPT), "prod"], cwd=DEPLOY_DEBUG_ROOT, check=True)
    receipt = deployment_state(request["commit"])
    print(json.dumps({"state": "deployed", "commit": request["commit"], **receipt}))


def main():
    arguments = shlex.split(os.environ.get("SSH_ORIGINAL_COMMAND", ""))
    mode = sys.argv[1] if len(sys.argv) == 2 else ""
    if not arguments or arguments.pop(0) != mode:
        raise ValueError("Explicit forced-command mode is required")
    if mode == "gbrain":
        os.execv("/srv/consolidation/infra/gbrain-host",
                 ["gbrain-host", *gbrain_args(arguments)])
    elif mode == "record":
        record(arguments)
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
