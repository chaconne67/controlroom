import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys


MODULE_PATH = Path(__file__).with_name("sam_role_guard.py")
SPEC = importlib.util.spec_from_file_location("sam_role_guard", MODULE_PATH)
guard = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(guard)


def payload(event, *, session="session-one", tool=None, tool_input=None, extra=None):
    return {
        "hook_event_name": event,
        "session_id": session,
        "tool_name": tool,
        "tool_input": tool_input,
        "extra": extra or {},
    }


def test_error_context_injects_policy_and_locks_session(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    result = guard.evaluate(
        payload(
            "pre_llm_call",
            extra={"user_message": "엑스다임 운영 오류를 문제해결해"},
        )
    )
    assert "통신만" in result["context"]
    assert guard._is_marked("session-one")


def test_locked_session_blocks_patch_terminal_and_delegation(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    guard._mark("session-one")
    for tool, tool_input in (
        ("patch", {"path": "/tmp/unrelated.py"}),
        ("terminal", {"command": "git status", "workdir": "/tmp"}),
        ("delegate_task", {"tasks": [{"goal": "investigate"}]}),
        ("read_file", {"path": "/tmp/evidence.txt"}),
        ("web_search", {"query": "Exdigm error"}),
        ("browser_exec", {"action": "open", "url": "https://example.com"}),
    ):
        result = guard.evaluate(
            payload("pre_tool_call", tool=tool, tool_input=tool_input)
        )
        assert result["action"] == "block"


def test_unrelated_next_turn_clears_session_lock(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    guard.evaluate(
        payload(
            "pre_llm_call",
            extra={
                "user_message": "Exdigm 운영 오류를 확인해",
                "task_id": "error-task",
                "turn_id": "error-turn",
            },
        )
    )
    assert guard._is_marked(
        "session-one", {"task_id": "error-task", "turn_id": "error-turn"}
    )
    guard.evaluate(
        payload(
            "pre_llm_call",
            extra={
                "user_message": "FundKeeper 보고서를 읽어줘",
                "task_id": "other-task",
                "turn_id": "other-turn",
            },
        )
    )
    assert not guard._is_marked("session-one")


def test_targeted_write_is_blocked_without_prior_marker(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    result = guard.evaluate(
        payload(
            "pre_tool_call",
            session="fresh",
            tool="patch",
            tool_input={
                "path": (
                    "/home/chaconne/controlroom/.controlroom/scripts/"
                    "exdigm/pipeline_once.py"
                )
            },
        )
    )
    assert result["action"] == "block"


def test_targeted_working_directory_blocks_relative_terminal_command(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    request = payload(
        "pre_tool_call",
        session="fresh",
        tool="terminal",
        tool_input={"command": "git status"},
    )
    request["cwd"] = "/home/chaconne/controlroom/.controlroom/scripts/exdigm"
    result = guard.evaluate(request)
    assert result["action"] == "block"


def test_exact_communication_helpers_remain_allowed(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    guard._mark("session-one")
    python = "/home/chaconne/.hermes/hermes-agent/venv/bin/python"
    decision = (
        "/home/chaconne/controlroom/exdigm/skills/"
        "exdigm-error-control/scripts/decision.py"
    )
    commands = (
        f"{python} {decision} inspect 00000000-0000-0000-0000-000000000001",
        f"{python} {decision} decide 00000000-0000-0000-0000-000000000001 "
        "--revision 3 --request-hash abc --decision approve",
        f"{python} /home/chaconne/.hermes/scripts/exdigm_error_context.py",
        f"{python} /home/chaconne/.hermes/scripts/update_exdigm_error_checkpoint.py",
    )
    for command in commands:
        assert guard.evaluate(
            payload(
                "pre_tool_call",
                tool="terminal",
                tool_input={"command": command},
            )
        ) == {}


def test_helper_path_cannot_be_combined_with_another_command(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    guard._mark("session-one")
    command = (
        "/home/chaconne/.hermes/hermes-agent/venv/bin/python "
        "/home/chaconne/.hermes/scripts/exdigm_error_context.py && git status"
    )
    result = guard.evaluate(
        payload("pre_tool_call", tool="terminal", tool_input={"command": command})
    )
    assert result["action"] == "block"


def test_unrelated_project_tool_call_is_not_blocked(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    assert guard.evaluate(
        payload(
            "pre_tool_call",
            session="fresh",
            tool="terminal",
            tool_input={"command": "git status", "workdir": "/srv/fundkeeper"},
        )
    ) == {}


def test_unrelated_exdigm_feature_is_not_path_blocked_without_error_context(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    assert guard.evaluate(
        payload(
            "pre_tool_call",
            session="fresh",
            tool="terminal",
            tool_input={"command": "git status", "workdir": "/home/chaconne/exdigm-debug"},
        )
    ) == {}


def test_old_turn_marker_does_not_block_a_different_turn(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    guard._mark(
        "session-one", {"task_id": "old-task", "turn_id": "old-turn"}
    )
    assert guard.evaluate(
        payload(
            "pre_tool_call",
            tool="read_file",
            tool_input={"path": "/srv/fundkeeper/report.txt"},
            extra={"task_id": "new-task", "turn_id": "new-turn"},
        )
    ) == {}


def test_subprocess_wire_protocol(tmp_path):
    request = payload(
        "pre_tool_call",
        session="fresh",
        tool="write_file",
        tool_input={
            "path": (
                "/home/chaconne/controlroom/.controlroom/scripts/"
                "exdigm/pipeline_once.py"
            )
        },
    )
    completed = subprocess.run(
        [sys.executable, str(MODULE_PATH)],
        input=json.dumps(request),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "HERMES_HOME": str(tmp_path)},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["action"] == "block"
