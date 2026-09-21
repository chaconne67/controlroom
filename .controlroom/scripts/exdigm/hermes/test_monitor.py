import json
from pathlib import Path
import sqlite3

import pytest

import exdigm_error_context as collector
import update_exdigm_error_checkpoint as checkpoint


@pytest.fixture
def profile(tmp_path, monkeypatch):
    (tmp_path / "cron").mkdir()
    with sqlite3.connect(tmp_path / "cron" / "executions.db") as db:
        db.execute(
            "CREATE TABLE executions (id TEXT, job_id TEXT, status TEXT, delivery_outcome TEXT)"
        )
        db.execute(
            "INSERT INTO executions VALUES ('current', 'sam-monitor', 'running', NULL)"
        )
    command_path = tmp_path / "record-command.json"
    command_path.write_text(json.dumps({"command": ["ssh", "sam-record"]}))
    monkeypatch.setattr(collector, "PROFILE_ROOT", tmp_path)
    monkeypatch.setattr(
        collector, "STATE_PATH", tmp_path / "state" / "exdigm_error_monitor.json"
    )
    monkeypatch.setattr(collector, "ERROR_LOG", tmp_path / "logs" / "errors.log")
    monkeypatch.setattr(collector, "RECORD_CONFIG", command_path)
    checkpoint.save_state(
        collector.STATE_PATH,
        {
            "preserve": True,
            "exdigm_monitor_job_id": "sam-monitor",
            "exdigm_error_checkpoint_created_at": "2026-09-18T00:00:00+09:00",
            "exdigm_error_checkpoint_id": "old",
        },
    )
    return tmp_path


def probe(command, state, timeout=45):
    assert command == ["ssh", "sam-record"]
    assert timeout == 45
    return {
        "available": True,
        "errors": [{
            "id": "old-error", "created_at": "2026-09-17T00:00:00+09:00",
            "occurred_at": "2026-09-17T00:00:00+09:00",
            "handling_revision": 2, "current_handling_revision": 2,
            "category": "defect", "next_action": "approve_deploy",
            "summary": "기존 오류의 수정 결과",
            "handling_context": {"commit": "a" * 40},
            "processing_results": [{"revision": 2, "status": "succeeded"}],
        }],
    }


def test_preparation_uses_restricted_command_and_keeps_checkpoint(profile):
    result = collector.prepare_context(runner=probe)
    state = collector.load_state()
    assert result["new_exdigm_errors"][0]["next_action"] == "approve_deploy"
    assert state["exdigm_error_checkpoint_id"] == "old"
    assert state["exdigm_pending_delivery"]["execution_id"] == "current"
    assert state["exdigm_pending_delivery"]["revisions"] == {"old-error": 2}
    assert state["preserve"] is True


@pytest.mark.parametrize("status,outcome", [
    ("running", None), ("failed", "delivered"), ("completed", "suppressed"),
    ("completed", "queued"), ("completed", "not_configured"), ("unknown", None),
])
def test_only_completed_actual_delivery_can_advance(profile, status, outcome):
    collector.prepare_context(runner=probe)
    before = collector.STATE_PATH.read_bytes()
    with sqlite3.connect(profile / "cron" / "executions.db") as db:
        db.execute(
            "UPDATE executions SET status=?, delivery_outcome=?", (status, outcome)
        )
    assert checkpoint.update_checkpoint(collector.STATE_PATH) is False
    assert collector.STATE_PATH.read_bytes() == before


def test_delivered_revision_advances(profile):
    collector.prepare_context(runner=probe)
    with sqlite3.connect(profile / "cron" / "executions.db") as db:
        db.execute(
            "UPDATE executions SET status='completed', delivery_outcome='delivered'"
        )
    assert checkpoint.update_checkpoint(collector.STATE_PATH) is True
    state = collector.load_state()
    assert state["exdigm_delivered_revisions"] == {"old-error": 2}
    assert "exdigm_pending_delivery" not in state


def test_empty_board_does_not_prepare_delivery(profile):
    empty = lambda *args, **kwargs: {"available": True, "errors": []}
    assert collector.prepare_context(runner=empty) is None
    assert "exdigm_pending_delivery" not in collector.load_state()


def test_failed_board_read_is_distinct_from_no_errors(profile, monkeypatch, capsys):
    def fail():
        raise TimeoutError("PRIVATE")

    monkeypatch.setattr(collector, "prepare_context", fail)
    before = collector.STATE_PATH.read_bytes()
    collector.main()
    output = capsys.readouterr().out
    assert json.loads(output)["exdigm_monitor_error"]["error_type"] == "TimeoutError"
    assert "PRIVATE" not in output + collector.ERROR_LOG.read_text()
    assert collector.STATE_PATH.read_bytes() == before


def test_corrupt_state_is_not_reset(profile):
    collector.STATE_PATH.write_text("broken")
    with pytest.raises(json.JSONDecodeError):
        collector.prepare_context(runner=probe)
    assert collector.STATE_PATH.read_text() == "broken"


def test_manual_probe_cannot_claim_another_jobs_delivery(profile):
    with sqlite3.connect(profile / "cron" / "executions.db") as db:
        db.execute("UPDATE executions SET job_id='different-job'")
    with pytest.raises(RuntimeError, match="single active"):
        collector.prepare_context(runner=probe)


def test_monitor_has_no_broad_product_shell_or_embedded_sql():
    source = Path(collector.__file__).read_text(encoding="utf-8")
    assert "shell-readonly" not in source
    assert "49.247.202.197" not in source
    assert "SELECT " not in source
    assert "sam-record" not in source


def test_run_probe_sends_only_delivered_revision_cursor(profile, monkeypatch):
    observed = {}

    def run(command, **kwargs):
        observed.update(command=command, kwargs=kwargs)
        return type("Completed", (), {
            "returncode": 0,
            "stdout": json.dumps({"available": True, "errors": []}),
        })()

    monkeypatch.setattr(collector.subprocess, "run", run)
    value = collector.run_probe(
        ["ssh", "restricted"], {"exdigm_delivered_revisions": {"id": 7}, "secret": "x"}
    )
    assert value == {"available": True, "errors": []}
    assert observed["command"] == ["ssh", "restricted", "--list"]
    assert json.loads(observed["kwargs"]["input"]) == {
        "delivered_revisions": {"id": 7}
    }
