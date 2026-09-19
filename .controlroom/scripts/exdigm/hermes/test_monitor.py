import json
import sqlite3

import pytest

import exdigm_error_context as collector
import update_exdigm_error_checkpoint as checkpoint


@pytest.fixture
def profile(tmp_path, monkeypatch):
    (tmp_path / "cron").mkdir()
    with sqlite3.connect(tmp_path / "cron" / "executions.db") as db:
        db.execute("CREATE TABLE executions (id TEXT, job_id TEXT, status TEXT, delivery_outcome TEXT)")
        db.execute("INSERT INTO executions VALUES ('current', 'sam-monitor', 'running', NULL)")
    monkeypatch.setattr(collector, "PROFILE_ROOT", tmp_path)
    monkeypatch.setattr(collector, "STATE_PATH", tmp_path / "state" / "exdigm_error_monitor.json")
    monkeypatch.setattr(collector, "ERROR_LOG", tmp_path / "logs" / "errors.log")
    checkpoint.save_state(collector.STATE_PATH, {"preserve": True, "exdigm_monitor_job_id": "sam-monitor", "exdigm_error_checkpoint_created_at": "2026-09-18T00:00:00+09:00", "exdigm_error_checkpoint_id": "old"})
    return tmp_path


def probe(*args, **kwargs):
    return collector.MARKER + json.dumps({"available": True, "errors": [{
        "id": "old-error", "created_at": "2026-09-17T00:00:00+09:00",
        "occurred_at": "2026-09-17T00:00:00+09:00", "handling_revision": 2,
        "category": "defect", "next_action": "approve_deploy", "summary": "기존 오류의 수정 결과",
        "handling_context": {"commit": "a" * 40},
    }]})


def test_preparation_keeps_checkpoint_and_exact_execution(profile):
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
        db.execute("UPDATE executions SET status=?, delivery_outcome=?", (status, outcome))
    assert checkpoint.update_checkpoint(collector.STATE_PATH) is False
    assert collector.STATE_PATH.read_bytes() == before


def test_delivered_revision_advances_without_regressing_creation_cursor(profile):
    collector.prepare_context(runner=probe)
    with sqlite3.connect(profile / "cron" / "executions.db") as db:
        db.execute("UPDATE executions SET status='completed', delivery_outcome='delivered'")
    assert checkpoint.update_checkpoint(collector.STATE_PATH) is True
    state = collector.load_state()
    assert state["exdigm_delivered_revisions"] == {"old-error": 2}
    assert state["exdigm_error_checkpoint_id"] == "old"
    assert "exdigm_pending_delivery" not in state
    assert checkpoint.update_checkpoint(collector.STATE_PATH) is False


def test_legacy_checkpoint_command_cannot_consume_unreported_rows(profile):
    before = collector.STATE_PATH.read_bytes()
    assert checkpoint.update_checkpoint(collector.STATE_PATH, {"created_at": "tomorrow", "id": "new"}) is False
    assert collector.STATE_PATH.read_bytes() == before


def test_checkpoint_compares_the_instant_across_timezone_offsets(profile):
    collector.prepare_context(runner=probe)
    state = collector.load_state()
    state["exdigm_error_checkpoint_created_at"] = "2026-09-16T16:00:00+00:00"
    checkpoint.save_state(collector.STATE_PATH, state)
    with sqlite3.connect(profile / "cron" / "executions.db") as db:
        db.execute("UPDATE executions SET status='completed', delivery_outcome='delivered'")
    checkpoint.update_checkpoint(collector.STATE_PATH)
    assert collector.load_state()["exdigm_error_checkpoint_created_at"] == "2026-09-16T16:00:00+00:00"


def test_empty_result_does_not_prepare_delivery(profile):
    assert collector.prepare_context(runner=lambda *a, **k: collector.MARKER + '{"available":true,"errors":[]}') is None
    assert "exdigm_pending_delivery" not in collector.load_state()


def test_failed_probe_is_distinct_from_no_errors(profile, monkeypatch, capsys):
    def fail():
        raise TimeoutError("PRIVATE")
    monkeypatch.setattr(collector, "prepare_context", fail)
    before = collector.STATE_PATH.read_bytes()
    collector.main()
    output = capsys.readouterr().out
    assert json.loads(output)["exdigm_monitor_error"]["error_type"] == "TimeoutError"
    assert "PRIVATE" not in output + collector.ERROR_LOG.read_text()
    assert collector.STATE_PATH.read_bytes() == before


def test_corrupt_state_is_not_reset_and_replayed_as_new(profile):
    collector.STATE_PATH.write_text("broken")
    with pytest.raises(json.JSONDecodeError):
        collector.prepare_context(runner=probe)
    assert collector.STATE_PATH.read_text() == "broken"


def test_manual_probe_cannot_claim_another_jobs_delivery(profile):
    with sqlite3.connect(profile / "cron" / "executions.db") as db:
        db.execute("UPDATE executions SET job_id='different-job'")
    with pytest.raises(RuntimeError, match="single active"):
        collector.prepare_context(runner=probe)
    assert "exdigm_pending_delivery" not in collector.load_state()


def test_missing_installed_job_identity_never_guesses_another_profile(profile):
    state = collector.load_state()
    del state["exdigm_monitor_job_id"]
    checkpoint.save_state(collector.STATE_PATH, state)
    with pytest.raises(ValueError, match="identity"):
        collector.prepare_context(runner=probe)
    assert "exdigm_pending_delivery" not in collector.load_state()


def test_generated_query_has_revision_and_legacy_schema_support():
    code = collector.remote_code({"exdigm_delivered_revisions": {"old-error": 2}})
    compile(code, "readonly_probe", "exec")
    assert "to_jsonb(e)->>'handling_revision'" in code
    assert "LIMIT 100" in code
    assert "old-error" in code
    assert "UPDATE " not in code and "INSERT " not in code
