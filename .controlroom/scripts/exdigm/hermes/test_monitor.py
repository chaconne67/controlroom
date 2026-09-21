import json
import ast
import base64
import os
import sqlite3
import subprocess
import uuid
import zlib

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


@pytest.mark.skipif(os.environ.get("EXDIGM_RESULT_SQL_TESTS") != "1", reason="Opt-in official read-only PostgreSQL verification")
def test_result_selection_on_postgres(monkeypatch):
    """Exercise the emitted SELECT with CTE fixtures, without writing any DB rows."""
    original_remote_code = collector.remote_code
    error_id = "00000000-0000-0000-0000-000000000001"
    entry_id = "00000000-0000-0000-0000-000000000002"
    completed = {"revision": 2, "status": "succeeded", "action": "Verified result",
                 "category": "defect", "next_action": "approve_deploy", "handling_context": {"root_cause": "Verified cause"}}
    cases = [
        ("raw failure", [], 0, "unclassified", "investigate", 0, []),
        ("investigation started", [{"revision": 1, "status": "in_progress"}], 1, "unclassified", "investigate", 0, []),
        ("repair result", [completed], 2, "defect", "approve_deploy", 0, [2]),
        ("processing failed", [{**completed, "status": "failed"}], 2, "unclassified", "user_action", 0, [2]),
        ("confirmed expected stop", [{**completed, "category": "expected_stop", "next_action": "none"}], 2, "expected_stop", "none", 0, [2]),
        ("external wait finding", [{**completed, "category": "external_wait", "next_action": "external_wait"}], 2, "external_wait", "external_wait", 0, [2]),
        ("next stage running", [completed, {"revision": 3, "status": "in_progress"}], 3, "defect", "approve_deploy", 0, [2]),
        ("delivered result then progress", [completed, {"revision": 3, "status": "in_progress"}], 3, "defect", "approve_deploy", 2, []),
        ("two unseen results", [completed, {"revision": 3, "status": "in_progress"}, {**completed, "revision": 4}], 4, "defect", "none", 0, [2, 4]),
        ("already delivered", [completed, {**completed, "revision": 4}], 4, "defect", "none", 4, []),
        ("approval receipt only", [completed, {**completed, "revision": 3, "entry_id": entry_id,
                                              "handling_context": {"approval_entry_id": entry_id}}], 3, "defect", "approve_deploy", 2, []),
        ("result after old approval", [completed, {**completed, "revision": 4, "entry_id": "deployment-result",
                                                   "handling_context": {"approval_entry_id": entry_id}}], 4, "defect", "none", 2, [4]),
        ("legacy history without revision", [{"status": "succeeded", "action": "Historical result"}], 0, "unclassified", "investigate", 0, []),
    ]
    cte = """WITH projects_operationalerror AS (
        SELECT * FROM jsonb_to_recordset(%s::jsonb) AS fixture(
            id uuid,created_at timestamptz,occurred_at timestamptz,summary text,source text,error_type text,
            category text,next_action text,handling_revision int,handling_context jsonb,processing_history jsonb)) """
    requests = []
    expected = []
    for name, history, revision, category, action, seen, revisions in cases:
        state = {"exdigm_delivered_revisions": {error_id: seen},
                 "exdigm_error_checkpoint_created_at": "2026-09-19T00:00:00+00:00", "exdigm_error_checkpoint_id": error_id}
        calls = [node for node in ast.walk(ast.parse(collector.remote_code(state)))
                 if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "execute"]
        call = next(node for node in calls if "FROM projects_operationalerror" in ast.literal_eval(node.args[0]))
        query, parameters = ast.literal_eval(call.args[0]), ast.literal_eval(call.args[1])
        row = {"id": error_id, "created_at": "2026-09-18T00:00:00+00:00", "occurred_at": "2026-09-18T00:00:00+00:00",
               "summary": "Fixture for SELECT only", "source": "fixture", "error_type": "Fixture",
               "category": category, "next_action": action, "handling_revision": revision,
               "handling_context": {}, "processing_history": history}
        if name == "raw failure":
            row["created_at"] = "2026-09-20T00:00:00+00:00"
        requests.append({"name": name, "sql": cte+query, "parameters": [json.dumps([row]), *parameters]})
        expected.append({"name": name, "revisions": revisions})
    # Old raw rows must not consume the page limit ahead of a later result.
    raw = {**row, "handling_revision": 0, "processing_history": []}
    backlog = [{**raw, "id": str(uuid.UUID(int=i)), "created_at": "2026-09-17T00:00:00+00:00"} for i in range(100, 220)]
    backlog.append({**row, "handling_revision": 2, "processing_history": [completed]})
    requests.append({"name": "raw backlog cannot hide result", "sql": cte+query, "parameters": [json.dumps(backlog), *parameters]})
    expected.append({"name": "raw backlog cannot hide result", "revisions": [2]})
    source = f'''import json
from django.db import connection
out = []
with connection.cursor() as cursor:
    for case in {requests!r}:
        cursor.execute(case["sql"], case["parameters"])
        rows = cursor.fetchall()
        revisions = []
        for row in rows:
            value = row[11]
            value = json.loads(value) if isinstance(value, str) else value
            revisions.extend(item["revision"] for item in value)
        out.append({{"name": case["name"], "revisions": revisions}})
print({collector.MARKER!r} + json.dumps(out))
'''
    encoded = base64.b64encode(zlib.compress(source.encode("utf-8"))).decode("ascii")
    monkeypatch.setattr(collector, "remote_code", lambda state: f"import base64,zlib;exec(zlib.decompress(base64.b64decode('{encoded}')))")
    try:
        output = collector.run_probe(collector.build_remote_command({}), timeout=90)
    except subprocess.CalledProcessError as error:
        raise AssertionError(error.output) from None
    actual = collector.parse_probe_output(output)
    assert actual == expected

    # Run the full generated probe too: Django's raw JSONB values need decoding,
    # and an in-progress revision must not be acknowledged as a completed result.
    tree = ast.parse(original_remote_code({}))
    call = next(node for node in ast.walk(tree) if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute) and node.func.attr == "execute"
                and "FROM projects_operationalerror" in ast.literal_eval(node.args[0]))
    fixture = {**row, "handling_revision": 3, "processing_history": [completed, {"revision": 3, "status": "in_progress"}]}
    call.args[0] = ast.Constant(cte+ast.literal_eval(call.args[0]))
    call.args[1] = ast.parse(repr([json.dumps([fixture]), *ast.literal_eval(call.args[1])]), mode="eval").body
    encoded = base64.b64encode(zlib.compress(ast.unparse(ast.fix_missing_locations(tree)).encode())).decode("ascii")
    monkeypatch.setattr(collector, "remote_code", lambda state: f"import base64,zlib;exec(zlib.decompress(base64.b64decode('{encoded}')))")
    result = collector.collect_context({})["new_exdigm_errors"][0]
    assert result["handling_revision"] == 2
    assert result["current_handling_revision"] == 3
    assert result["processing_results"] == [completed]
    assert isinstance(result["handling_context"], dict)
