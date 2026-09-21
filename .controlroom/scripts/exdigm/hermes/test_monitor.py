import hashlib
import json
import os
import sqlite3
import subprocess
from types import SimpleNamespace
import uuid

import pytest

import exdigm_error_context as collector
import update_exdigm_error_checkpoint as checkpoint


@pytest.fixture
def profile(tmp_path, monkeypatch):
    (tmp_path / "cron").mkdir()
    with sqlite3.connect(tmp_path / "cron" / "executions.db") as db:
        db.execute(
            "CREATE TABLE executions "
            "(id TEXT, job_id TEXT, status TEXT, delivery_outcome TEXT, finished_at TEXT)"
        )
        db.execute(
            "INSERT INTO executions VALUES "
            "('current', 'sam-monitor', 'running', NULL, NULL)"
        )
    with sqlite3.connect(tmp_path / "cron" / "deliveries.db") as db:
        db.execute(
            "CREATE TABLE deliveries "
            "(execution_id TEXT, for_failure INTEGER, status TEXT, finished_at TEXT)"
        )
    monkeypatch.setattr(collector, "PROFILE_ROOT", tmp_path)
    monkeypatch.setattr(
        collector,
        "STATE_PATH",
        tmp_path / "state" / "exdigm_error_monitor.json",
    )
    monkeypatch.setattr(
        collector, "ERROR_LOG", tmp_path / "logs" / "errors.log"
    )
    checkpoint.save_state(
        collector.STATE_PATH,
        {
            "preserve": True,
            "exdigm_monitor_job_id": "sam-monitor",
            "exdigm_error_checkpoint_updated_at": "2026-09-18T00:00:00+09:00",
            "exdigm_error_checkpoint_track_id": "old-track",
        },
    )
    return tmp_path


def track_row():
    return {
        "event_id": "00000000-0000-0000-0000-000000000001",
        "event_created_at": "2026-09-17T00:00:00+09:00",
        "occurred_at": "2026-09-17T00:00:00+09:00",
        "event_summary": "수정 결과",
        "source": "fixture",
        "error_type": "Fixture",
        "track_id": "00000000-0000-0000-0000-000000000002",
        "sequence": 1,
        "track_title": "배포 대기 트랙",
        "track_scope": "한 실패 경계",
        "blocking": True,
        "track_status": "waiting",
        "category": "defect",
        "next_action": "approve_deploy",
        "track_revision": 2,
        "handling_context": {
            "commit": "a" * 40,
            "base_commit": "b" * 40,
            "repair_ref": "refs/operational-repairs/00000000-0000-0000-0000-000000000003",
            "verification": "passed",
            "verification_receipt": "sha256:receipt",
            "rollback": "previous release",
        },
        "last_result": {
            "revision": 2,
            "status": "succeeded",
            "action": "verified repair",
        },
        "updated_at": "2026-09-18T01:00:00+09:00",
    }


def probe(*args, **kwargs):
    return collector.MARKER + json.dumps(
        {"available": True, "tracks": [track_row()]}
    )


def noop_writer(*args):
    return None


def test_preparation_stages_exact_track_revision_and_job(profile):
    result = collector.prepare_context(
        runner=probe, delivery_writer=noop_writer
    )
    state = collector.load_state()
    row = result["new_exdigm_tracks"][0]
    assert row["next_action"] == "approve_deploy"
    assert row["approval_request"]["track_revision"] == 2
    assert state["exdigm_error_checkpoint_track_id"] == "old-track"
    assert state["exdigm_pending_delivery"] == {
        "execution_id": "current",
        "job_id": "sam-monitor",
        "checkpoint": {
            "updated_at": row["updated_at"],
            "track_id": row["track_id"],
        },
        "tracks": {row["track_id"]: 2},
    }
    assert state["preserve"] is True


@pytest.mark.parametrize(
    "status,outcome",
    [
        ("running", None),
        ("failed", "delivered"),
        ("completed", "suppressed"),
        ("completed", "queued"),
        ("completed", "not_configured"),
        ("unknown", None),
    ],
)
def test_only_completed_actual_delivery_records_db_and_advances(
    profile, status, outcome
):
    collector.prepare_context(runner=probe, delivery_writer=noop_writer)
    before = collector.STATE_PATH.read_bytes()
    with sqlite3.connect(profile / "cron" / "executions.db") as db:
        db.execute(
            "UPDATE executions SET status=?, delivery_outcome=?",
            (status, outcome),
        )
    calls = []
    assert (
        checkpoint.update_checkpoint(
            collector.STATE_PATH,
            delivery_writer=lambda *args: calls.append(args),
        )
        is False
    )
    assert calls == []
    assert collector.STATE_PATH.read_bytes() == before


def test_confirmed_delivery_records_db_before_local_checkpoint(profile):
    collector.prepare_context(runner=probe, delivery_writer=noop_writer)
    with sqlite3.connect(profile / "cron" / "executions.db") as db:
        db.execute(
            "UPDATE executions SET status='completed', "
            "delivery_outcome='delivered'"
        )
    calls = []
    assert checkpoint.update_checkpoint(
        collector.STATE_PATH,
        delivery_writer=lambda *args: calls.append(args),
    )
    assert len(calls) == 1
    _, pending, receipt = calls[0]
    assert pending["tracks"] == {track_row()["track_id"]: 2}
    assert receipt["id"] == "current"
    state = collector.load_state()
    assert state["exdigm_delivered_track_revisions"] == {
        track_row()["track_id"]: 2
    }
    assert "exdigm_pending_delivery" not in state


def test_durable_delivery_reconciles_after_execution_finalization_is_interrupted(profile):
    collector.prepare_context(runner=probe, delivery_writer=noop_writer)
    with sqlite3.connect(profile / "cron" / "executions.db") as db:
        db.execute(
            "UPDATE executions SET status='failed', delivery_outcome=NULL, "
            "finished_at='2026-09-21T17:09:19+09:00'"
        )
    with sqlite3.connect(profile / "cron" / "deliveries.db") as db:
        db.execute(
            "INSERT INTO deliveries VALUES "
            "('current', 0, 'delivered', '2026-09-21T17:09:18+09:00')"
        )
    calls = []
    assert checkpoint.update_checkpoint(
        collector.STATE_PATH,
        delivery_writer=lambda *args: calls.append(args),
    )
    assert len(calls) == 1
    _, pending, receipt = calls[0]
    assert pending["tracks"] == {track_row()["track_id"]: 2}
    assert receipt == {
        "id": "current",
        "status": "completed",
        "delivery_outcome": "delivered",
        "finished_at": "2026-09-21T17:09:18+09:00",
    }
    assert "exdigm_pending_delivery" not in collector.load_state()


def test_failure_notification_is_not_mistaken_for_the_track_report(profile):
    collector.prepare_context(runner=probe, delivery_writer=noop_writer)
    with sqlite3.connect(profile / "cron" / "executions.db") as db:
        db.execute(
            "UPDATE executions SET status='failed', delivery_outcome=NULL, "
            "finished_at='2026-09-21T17:09:19+09:00'"
        )
    with sqlite3.connect(profile / "cron" / "deliveries.db") as db:
        db.execute(
            "INSERT INTO deliveries VALUES "
            "('current', 1, 'delivered', '2026-09-21T17:09:18+09:00')"
        )
    before = collector.STATE_PATH.read_bytes()
    calls = []
    assert not checkpoint.update_checkpoint(
        collector.STATE_PATH,
        delivery_writer=lambda *args: calls.append(args),
    )
    assert calls == []
    assert collector.STATE_PATH.read_bytes() == before


def test_unconfirmed_previous_delivery_is_never_replaced_by_next_execution(profile):
    collector.prepare_context(runner=probe, delivery_writer=noop_writer)
    with sqlite3.connect(profile / "cron" / "executions.db") as db:
        db.execute("UPDATE executions SET status='failed', delivery_outcome=NULL")
        db.execute(
            "INSERT INTO executions VALUES "
            "('second', 'sam-monitor', 'running', NULL, NULL)"
        )
    before = collector.STATE_PATH.read_bytes()
    with pytest.raises(RuntimeError, match="unconfirmed"):
        collector.prepare_context(runner=probe, delivery_writer=noop_writer)
    assert collector.STATE_PATH.read_bytes() == before


def test_db_receipt_failure_preserves_pending_delivery(profile):
    collector.prepare_context(runner=probe, delivery_writer=noop_writer)
    with sqlite3.connect(profile / "cron" / "executions.db") as db:
        db.execute(
            "UPDATE executions SET status='completed', "
            "delivery_outcome='delivered'"
        )
    before = collector.STATE_PATH.read_bytes()

    def fail(*args):
        raise RuntimeError("DB unavailable")

    with pytest.raises(RuntimeError, match="DB unavailable"):
        checkpoint.update_checkpoint(
            collector.STATE_PATH, delivery_writer=fail
        )
    assert collector.STATE_PATH.read_bytes() == before


def test_approval_request_hash_matches_product_contract():
    row = track_row()
    request = collector.approval_request(row)
    value = {key: request[key] for key in request if key != "request_hash"}
    expected = hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    assert request["request_hash"] == expected
    assert request["track_id"] == row["track_id"]


def test_empty_result_does_not_stage_delivery(profile):
    empty = lambda *a, **k: collector.MARKER + json.dumps(
        {"available": True, "tracks": []}
    )
    assert (
        collector.prepare_context(
            runner=empty, delivery_writer=noop_writer
        )
        is None
    )
    assert "exdigm_pending_delivery" not in collector.load_state()


def test_failed_probe_is_silent_error_and_preserves_state(
    profile, monkeypatch, capsys
):
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
        collector.prepare_context(
            runner=probe, delivery_writer=noop_writer
        )
    assert collector.STATE_PATH.read_text() == "broken"


def test_manual_probe_cannot_claim_another_jobs_delivery(profile):
    with sqlite3.connect(profile / "cron" / "executions.db") as db:
        db.execute("UPDATE executions SET job_id='different-job'")
    with pytest.raises(RuntimeError, match="single active"):
        collector.prepare_context(
            runner=probe, delivery_writer=noop_writer
        )
    assert "exdigm_pending_delivery" not in collector.load_state()


def test_missing_job_identity_never_guesses(profile):
    state = collector.load_state()
    del state["exdigm_monitor_job_id"]
    checkpoint.save_state(collector.STATE_PATH, state)
    with pytest.raises(ValueError, match="identity"):
        collector.prepare_context(
            runner=probe, delivery_writer=noop_writer
        )


def test_generated_query_uses_track_and_db_delivery_receipt():
    code = collector.remote_code()
    compile(code, "readonly_probe", "exec")
    assert "projects_operationalerrortrack" in code
    assert "projects_operationalerrortransition" in code
    assert "report_delivered" in code
    assert "LIMIT 100" in code
    assert "UPDATE " not in code and "INSERT " not in code


def test_db_delivery_receipt_is_bound_to_the_owner_chat(profile, monkeypatch):
    config = profile / "record-command.json"
    config.write_text(json.dumps(["sam-record"]), encoding="utf-8")
    monkeypatch.setattr(checkpoint, "RECORD_CONFIG", config)
    track_id = "00000000-0000-0000-0000-000000000002"
    pending = {
        "job_id": "sam-monitor",
        "tracks": {track_id: 4},
    }
    seen = {}

    def runner(command, **kwargs):
        payload = json.loads(kwargs["input"])
        seen.update(payload)
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "selected_track": {
                        "transitions": [
                            {
                                "entry_id": payload["entry_id"],
                                "event_type": "report_delivered",
                            }
                        ]
                    }
                }
            ),
        )

    checkpoint.record_db_deliveries(
        profile,
        pending,
        {
            "id": str(uuid.uuid4()),
            "finished_at": "2026-09-21T10:00:00+09:00",
        },
        settings_reader=lambda path: {"TELEGRAM_HOME_CHANNEL": "123"},
        runner=runner,
    )
    assert seen["delivery"]["chat_id"] == "123"
    assert seen["delivery"]["message_id"].startswith("hermes-execution:")


@pytest.mark.skipif(
    os.environ.get("EXDIGM_RESULT_SQL_TESTS") != "1",
    reason="Opt-in official read-only PostgreSQL verification",
)
def test_live_track_probe_is_read_only_and_json_decodable():
    try:
        output = collector.run_probe(
            collector.build_remote_command(), timeout=90
        )
    except subprocess.CalledProcessError as error:
        raise AssertionError(error.output) from None
    parsed = collector.parse_probe_output(output)
    assert parsed["available"] is True
    assert isinstance(parsed["tracks"], list)
