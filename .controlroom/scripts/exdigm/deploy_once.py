#!/usr/bin/env python3
"""Let a main-server Codex execute one exact owner-approved deployment."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time
import uuid

from repair_once import run_command, save_json


SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "status": {"type": "string", "enum": ["succeeded", "failed"]},
        "action": {"type": "string"},
    },
    "required": ["status", "action"],
}


def preflight(config):
    import pwd

    if pwd.getpwuid(os.getuid()).pw_name != config["restricted_user"] or os.getuid() == 0:
        raise RuntimeError("Run from the provisioned deployment identity")
    for name in ("record_command", "deploy_command", "codex_command"):
        value = config.get(name)
        if not isinstance(value, list) or not value or not all(isinstance(item, str) for item in value):
            raise RuntimeError(f"Deployment config requires {name}")
    root = Path(config["project_root"])
    if not (root / "AGENTS.md").is_file():
        raise RuntimeError("Deployment Codex project context is unavailable")
    return {
        "identity": config["restricted_user"],
        "codex": run_command([*config["codex_command"], "--version"]),
    }


def _pipeline(config, arguments, payload=None):
    output = run_command(
        [*config["record_command"], "pipeline", *arguments],
        payload=None if payload is None else json.dumps(payload, ensure_ascii=False),
    )
    return json.loads(output)


def _deployment_contract(track):
    context = track["handling_context"]
    required = (
        "commit", "repair_ref", "approval_entry_id", "approval_request_hash",
        "approval_decision", "approved_action", "base_commit",
        "verification_receipt",
    )
    if any(not isinstance(context.get(name), str) or not context[name] for name in required):
        raise ValueError("Deployment track has incomplete owner approval evidence")
    if context["approval_decision"] != "approve" or context["approved_action"] != "approve_deploy":
        raise ValueError("Deployment track is not owner-approved")
    if not re.fullmatch(r"[0-9a-f]{40}", context["commit"]):
        raise ValueError("Deployment track has an invalid commit")
    if not re.fullmatch(r"[0-9a-f]{40}", context["base_commit"]):
        raise ValueError("Deployment track has an invalid base commit")
    if not re.fullmatch(
        r"sha256:[0-9a-f]{64}", context["verification_receipt"]
    ):
        raise ValueError("Deployment track has an invalid verification receipt")
    if not re.fullmatch(r"[0-9a-f]{64}", context["approval_request_hash"]):
        raise ValueError("Deployment track has an invalid request hash")
    uuid.UUID(context["approval_entry_id"])
    prefix = "refs/operational-repairs/"
    if not context["repair_ref"].startswith(prefix):
        raise ValueError("Deployment track has an invalid repair ref")
    uuid.UUID(context["repair_ref"][len(prefix) :])
    return {
        "track_id": track["id"],
        "expected_revision": track["revision"],
        "commit": context["commit"],
        "repair_ref": context["repair_ref"],
        "approval_entry_id": context["approval_entry_id"],
        "request_hash": context["approval_request_hash"],
    }


def _deploy_status(config, contract):
    return json.loads(
        run_command(
            [*config["deploy_command"], "status"],
            payload=json.dumps(contract),
        )
    )


def _write_helper(path, config, contract, result_path):
    source = f'''import json,subprocess
from pathlib import Path
command={config["deploy_command"] + ["execute"]!r}
payload={json.dumps(contract)!r}
target=Path({str(result_path)!r})
completed=subprocess.run(command,input=payload,text=True,encoding="utf-8",
    stdout=subprocess.PIPE,stderr=subprocess.PIPE)
if completed.returncode:
    raise SystemExit("Approved deployment command failed; inspect the forced-command host log")
data=json.loads(completed.stdout)
temporary=target.with_suffix(".tmp")
temporary.write_text(json.dumps(data),encoding="utf-8")
temporary.replace(target)
print(json.dumps(data))
'''
    path.write_text(source, encoding="utf-8")
    os.chmod(path, 0o500)


def _prompt(helper, contract):
    return f"""주인님이 승인한 Exdigm 운영 배포 한 건입니다. 샘은 결정을 전달·기록했을 뿐 실행자가 아닙니다.
당신은 메인 서버의 배포 Codex입니다. 아래 단일 helper를 정확히 한 번 실행하고 그 결과를 확인하세요.
helper 밖의 코드·DB·권한·Git·서비스를 직접 바꾸지 말고, 다른 커밋이나 다른 트랙을 배포하지 마세요.
helper가 실패하면 우회·재시도·수동 배포하지 말고 failed로 보고하세요. 성공 출력의 production_commit이
승인된 commit과 같은지 확인한 뒤 succeeded로 보고하세요.

실행 명령: python3 {helper}
승인 계약: {json.dumps(contract, ensure_ascii=False)}
최종 응답은 제공된 JSON schema만 사용하세요.
"""


def _success_payload(run_id, track, contract, evidence, status):
    return {
        "operation": "result",
        "track_id": track["id"],
        "status": "succeeded",
        "action": "메인 서버 배포 Codex가 주인님이 승인한 정확한 커밋을 운영에 배포했습니다.",
        "category": track["category"],
        "next_action": "verify_result",
        "expected_revision": track["revision"],
        "entry_id": str(uuid.uuid5(uuid.UUID(run_id), "result")),
        "actor": "deploy_codex",
        "details": {
            "deployment_status": "succeeded",
            "deployed_commit": contract["commit"],
            "deployment_evidence": str(evidence),
            "verification": (
                "강제 배포 명령의 결과와 독립 status 조회에서 운영 커밋이 "
                f"{status['production_commit']}으로 일치했습니다."
            ),
            "workspace_reserved": "no",
        },
    }


def _recover_deployed(config, run_id, track, contract, directory):
    status = _deploy_status(config, contract)
    if (
        status.get("production_commit") != contract["commit"]
        or status.get("deployment_completed") is not True
    ):
        return None
    receipt = directory / "status-recovery.json"
    save_json(receipt, status)
    return _success_payload(run_id, track, contract, receipt, status)


def execute_once(config, state_root):
    import fcntl

    os.umask(0o077)
    state_root.mkdir(parents=True, exist_ok=True)
    with (state_root / "launcher.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        active = state_root / "active.json"
        if active.exists():
            run = json.loads(active.read_text(encoding="utf-8"))
        else:
            run = {"id": str(uuid.uuid4()), "preflight": preflight(config)}
            save_json(active, run)
        directory = state_root / run["id"]
        directory.mkdir(exist_ok=True)
        case_path = directory / "case.json"
        payload_path = directory / "result-payload.json"
        if not case_path.exists():
            case = _pipeline(
                config,
                ["claim", "--mode", "deploy", "--automation-run", run["id"]],
            )
            if case is None:
                active.unlink()
                return {"state": "no_work"}
            save_json(case_path, case)
        case = json.loads(case_path.read_text(encoding="utf-8"))
        track = case["selected_track"]
        if payload_path.exists():
            payload = json.loads(payload_path.read_text(encoding="utf-8"))
        else:
            current = _pipeline(
                config, ["read-track", "--track-id", track["id"]]
            )["selected_track"]
            if (
                current["status"] != "running"
                or current["revision"] != track["revision"]
                or current["handling_context"].get("automation_run") != run["id"]
                or current["handling_context"].get("workspace_reserved") != "yes"
            ):
                raise RuntimeError("Deployment track ownership changed")
            contract = _deployment_contract(current)
            result_path = directory / "deployment-result.json"
            started = directory / "codex-started.json"
            try:
                if started.exists() and not result_path.exists():
                    payload = _recover_deployed(
                        config, run["id"], current, contract, directory
                    )
                    if payload is None:
                        raise RuntimeError("Interrupted deployment outcome is not confirmed")
                else:
                    helper = directory / "perform-approved-deploy.py"
                    _write_helper(helper, config, contract, result_path)
                    schema_path = directory / "schema.json"
                    save_json(schema_path, SCHEMA)
                    save_json(started, {"run": run["id"], "deadline": time.time() + 7200})
                    message_path = directory / "codex-result.json"
                    run_command(
                        [
                            *config["codex_command"], "exec", "--sandbox", "danger-full-access",
                            "-c", 'approval_policy="never"', "--cd", config["project_root"],
                            "--json", "--output-schema", str(schema_path),
                            "--output-last-message", str(message_path), "-",
                        ],
                        payload=_prompt(helper, contract),
                        timeout=7100,
                        evidence=directory / "execution.jsonl",
                    )
                    message = json.loads(message_path.read_text(encoding="utf-8"))
                    if set(message) != {"status", "action"} or message["status"] != "succeeded":
                        raise RuntimeError("Deployment Codex did not report success")
                    deployed = json.loads(result_path.read_text(encoding="utf-8"))
                    if deployed.get("production_commit") != contract["commit"]:
                        raise RuntimeError("Forced deployment result has the wrong commit")
                    status = _deploy_status(config, contract)
                    if status.get("production_commit") != contract["commit"]:
                        raise RuntimeError("Production status does not match the approved commit")
                    payload = _success_payload(
                        run["id"], current, contract, directory / "execution.jsonl", status
                    )
                save_json(payload_path, payload)
            except Exception as error:
                try:
                    recovered = _recover_deployed(
                        config, run["id"], current, contract, directory
                    )
                except Exception:
                    recovered = None
                if recovered is not None:
                    payload = recovered
                    save_json(payload_path, payload)
                else:
                    failure = {
                        "operation": "result",
                        "track_id": current["id"],
                        "status": "failed",
                        "action": f"승인된 배포 실행 중단: {type(error).__name__}.",
                        "next_action": "external_wait",
                        "expected_revision": current["revision"],
                        "entry_id": str(
                            uuid.uuid5(uuid.UUID(run["id"]), "interrupted")
                        ),
                        "actor": "deploy_codex",
                        "details": {
                            "owner": "controlroom",
                            "resume_condition": "배포 로그·운영 커밋·작업공간 예약을 대조한 뒤 같은 실행을 인계합니다.",
                            "verification": "배포 성공과 원래 업무 결과는 확인되지 않았습니다.",
                            "stop_reason": f"{type(error).__name__}; 실제 배포 상태 대조가 필요합니다.",
                            "workspace_reserved": "yes",
                        },
                    }
                    save_json(directory / "interrupted-payload.json", failure)
                    try:
                        _pipeline(config, ["--json-input"], failure)
                    except Exception:
                        pass
                    raise
        saved = _pipeline(config, ["--json-input"], payload)
        save_json(directory / "recorded.json", saved)
        active.unlink()
        return {
            "state": "recorded",
            "event_id": saved["id"],
            "track_id": saved["selected_track"]["id"],
            "next_action": saved["selected_track"]["next_action"],
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    config = json.loads(arguments.config.read_text(encoding="utf-8"))
    if arguments.check:
        print(json.dumps(preflight(config)))
    else:
        print(json.dumps(execute_once(config, arguments.state_root), ensure_ascii=False))


if __name__ == "__main__":
    main()
