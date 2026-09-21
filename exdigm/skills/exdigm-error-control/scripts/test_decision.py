import copy
from contextlib import closing
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import uuid

import decision


class DecisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.profile = Path(self.temp.name)
        (self.profile / ".env").write_text(
            "TELEGRAM_ALLOWED_USERS=123\nTELEGRAM_HOME_CHANNEL=123\n"
        )
        self.env = {
            "HERMES_SESSION_" + key.upper(): value
            for key, value in {
                "id": "sam-session",
                "platform": "telegram",
                "chat_id": "123",
                "chat_type": "dm",
                "user_id": "123",
                "message_id": "456",
            }.items()
        }
        with closing(sqlite3.connect(self.profile / "state.db")) as db:
            db.executescript(
                """
                CREATE TABLE sessions (
                    id TEXT, source TEXT, user_id TEXT, chat_id TEXT, chat_type TEXT
                );
                CREATE TABLE messages (
                    id INTEGER, session_id TEXT, role TEXT, content TEXT, timestamp REAL,
                    platform_message_id TEXT, active INTEGER, compacted INTEGER,
                    _compressed_summary INTEGER
                );
                INSERT INTO sessions VALUES (
                    'sam-session','telegram','123','123','dm'
                );
                """
            )
            db.execute(
                """INSERT INTO messages VALUES (
                    1,'sam-session','user','Approve the displayed change',
                    ?,'456',1,0,0
                )""",
                (
                    datetime.fromisoformat(
                        "2026-09-19T03:00:00+00:00"
                    ).timestamp(),
                ),
            )
            db.commit()
        self.track_id = str(uuid.uuid4())
        self.event_id = str(uuid.uuid4())
        self.request = {
            "event_id": self.event_id,
            "track_id": self.track_id,
            "track_revision": 2,
            "next_action": "approve_deploy",
            "details": {
                "commit": "a" * 40,
                "base_commit": "b" * 40,
                "repair_ref": f"refs/operational-repairs/{uuid.uuid4()}",
                "verification": "Passed checks",
                "verification_receipt": "sha256:verified",
                "rollback": "Restore previous release",
            },
            "request_hash": hashlib.sha256(b"request").hexdigest(),
        }
        self.case = {
            "id": self.event_id,
            "summary": "A verified repair awaits deployment",
            "selected_track": {
                "id": self.track_id,
                "revision": 2,
                "next_action": "approve_deploy",
                "status": "waiting",
                "title": "repair",
                "approval_request": copy.deepcopy(self.request),
                "transitions": [
                    {
                        "entry_id": str(uuid.uuid4()),
                        "track_revision": 2,
                        "event_type": "result_recorded",
                        "actor": "main_codex",
                        "recorded_at": "2026-09-19T01:00:00+00:00",
                    }
                ],
            },
        }
        self.payloads = []

    def rpc(self, args, payload=None):
        if args[0] == "read-track":
            return copy.deepcopy(self.case)
        self.payloads.append(copy.deepcopy(payload))
        track = self.case["selected_track"]
        existing = [
            item
            for item in track["transitions"]
            if item.get("entry_id") == payload["entry_id"]
        ]
        if existing:
            return copy.deepcopy(self.case)
        if payload["operation"] == "decide":
            if payload["expected_revision"] != track["revision"]:
                raise ValueError("Revision changed")
            approval_at = datetime.fromisoformat(
                payload["proof"]["approval_message_at"]
            )
            origin_at = datetime.fromisoformat(track["transitions"][-1]["recorded_at"])
            if approval_at < origin_at:
                raise ValueError("Owner decision predates the approval request")
            track["revision"] += 1
            track["next_action"] = {
                "approve": "deploy",
                "reject": "none",
                "defer": "none",
                "revise": "investigate",
                "respond": "investigate",
            }[payload["decision"]]
            track["transitions"].append(
                {
                    "entry_id": payload["entry_id"],
                    "track_revision": track["revision"],
                    "event_type": "decision_recorded",
                    "actor": "owner",
                    "payload": {
                        "handling_context": {
                            "approval_decision": payload["decision"]
                        }
                    },
                }
            )
        elif payload["operation"] == "delivery":
            track["transitions"].append(
                {
                    "entry_id": payload["entry_id"],
                    "track_revision": payload["subject_revision"],
                    "event_type": "report_delivered",
                    "actor": "sam",
                    "payload": payload["delivery"],
                }
            )
        return copy.deepcopy(self.case)

    def invoke(self, value="approve", rpc=None, instruction=""):
        return decision.decide(
            self.profile,
            self.env,
            self.track_id,
            2,
            self.request["request_hash"],
            value,
            instruction=instruction,
            rpc=rpc or self.rpc,
        )

    def test_owner_decision_records_communication_and_never_executes(self):
        result = self.invoke()
        self.assertFalse(result["sam_execution_allowed"])
        self.assertEqual(result["next_executor"], "deploy_codex")
        self.assertEqual(result["next_action"], "deploy")
        payload = self.payloads[0]
        self.assertEqual(payload["operation"], "decide")
        self.assertEqual(payload["proof"]["recorded_by"], "sam")
        self.assertEqual(payload["proof"]["approval_message_id"], "456")
        self.assertNotIn("Approve the displayed change", json.dumps(payload))

    def test_cron_cli_other_user_and_other_chat_cannot_decide(self):
        for change in (
            {"HERMES_CRON_SESSION": "1"},
            {"HERMES_SESSION_USER_ID": "999"},
            {"HERMES_SESSION_CHAT_ID": "999"},
            {},
        ):
            with self.subTest(change=change):
                environment = {} if not change else {**self.env, **change}
                with self.assertRaises(ValueError):
                    decision.decide(
                        self.profile,
                        environment,
                        self.track_id,
                        2,
                        self.request["request_hash"],
                        "approve",
                        rpc=self.rpc,
                    )
        self.assertEqual(self.payloads, [])

    def test_assistant_or_synthetic_summary_is_not_owner_input(self):
        for update in (
            "role='assistant'",
            "role='user',_compressed_summary=1",
            "_compressed_summary=0,active=0",
        ):
            with self.subTest(update=update):
                with closing(sqlite3.connect(self.profile / "state.db")) as db:
                    db.execute("UPDATE messages SET " + update)
                    db.commit()
                with self.assertRaisesRegex(ValueError, "original user message"):
                    self.invoke()
        self.assertEqual(self.payloads, [])

    def test_changed_request_requires_a_new_owner_decision(self):
        for changed in ("revision", "hash"):
            with self.subTest(changed=changed):
                original = copy.deepcopy(self.case)
                if changed == "revision":
                    self.case["selected_track"]["revision"] = 3
                    self.case["selected_track"]["approval_request"][
                        "track_revision"
                    ] = 3
                else:
                    self.case["selected_track"]["approval_request"][
                        "request_hash"
                    ] = "f" * 64
                with self.assertRaisesRegex(ValueError, "request changed"):
                    self.invoke()
                self.case = original
        self.assertEqual(self.payloads, [])

    def test_lost_response_replays_the_same_decision_once(self):
        def lost_response(args, payload=None):
            response = self.rpc(args, payload)
            if payload is not None:
                raise TimeoutError("Lost response after DB commit")
            return response

        with self.assertRaises(TimeoutError):
            self.invoke(rpc=lost_response)
        result = self.invoke()
        self.assertFalse(result["sam_execution_allowed"])
        self.assertEqual(self.payloads[0], self.payloads[1])
        decisions = [
            item
            for item in self.case["selected_track"]["transitions"]
            if item["event_type"] == "decision_recorded"
        ]
        self.assertEqual(len(decisions), 1)

    def test_reject_defer_and_revise_do_not_make_sam_an_executor(self):
        original = copy.deepcopy(self.case)
        for value in ("reject", "defer", "revise"):
            with self.subTest(value=value):
                self.case = copy.deepcopy(original)
                self.payloads.clear()
                result = self.invoke(
                    value,
                    instruction="Reduce the scope and investigate again"
                    if value == "revise"
                    else "",
                )
                self.assertFalse(result["sam_execution_allowed"])
                self.assertIsNone(
                    result["next_executor"]
                    if value in {"reject", "defer"}
                    else None
                )

    def test_report_delivery_is_a_communication_receipt_without_revision_change(self):
        result = decision.record_delivery(
            self.track_id,
            2,
            "outgoing-789",
            "123",
            "2026-09-19T03:01:00+00:00",
            rpc=self.rpc,
        )
        self.assertEqual(result["subject_revision"], 2)
        self.assertEqual(self.case["selected_track"]["revision"], 2)
        self.assertEqual(
            self.case["selected_track"]["transitions"][-1]["actor"], "sam"
        )

    def test_owner_blocker_response_schedules_main_codex_not_sam(self):
        self.case["selected_track"]["next_action"] = "user_action"
        self.case["selected_track"]["approval_request"][
            "next_action"
        ] = "user_action"
        result = self.invoke(
            "respond",
            instruction="The requested source is now available.",
        )
        self.assertEqual(result["next_action"], "investigate")
        self.assertEqual(result["next_executor"], "main_codex")
        self.assertFalse(result["sam_execution_allowed"])
        self.assertEqual(
            self.payloads[0]["proof"]["instruction"],
            "The requested source is now available.",
        )


if __name__ == "__main__":
    unittest.main()
