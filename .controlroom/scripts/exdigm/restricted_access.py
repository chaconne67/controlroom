#!/usr/bin/env python3
"""Forced SSH entry points; reuse the existing GBrain and error-result commands."""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
import shlex
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
    else:
        raise ValueError("Unsupported access mode")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Keep DB connection strings and source material out of SSH error output.
        print(f"Restricted request failed: {type(error).__name__}", file=sys.stderr)
        raise SystemExit(1)
