import copy
from datetime import datetime
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
                "id": "sam-session", "platform": "telegram", "chat_id": "123",
                "chat_type": "dm", "user_id": "123", "message_id": "456",
            }.items()
        }
        with sqlite3.connect(self.profile / "state.db") as db:
            db.executescript("""
                CREATE TABLE sessions (id TEXT,source TEXT,user_id TEXT,chat_id TEXT,chat_type TEXT);
                CREATE TABLE messages (id INTEGER,session_id TEXT,role TEXT,content TEXT,timestamp REAL,
                    platform_message_id TEXT,active INTEGER,compacted INTEGER,_compressed_summary INTEGER);
                INSERT INTO sessions VALUES ('sam-session','telegram','123','123','dm');
            """)
            db.execute(
                "INSERT INTO messages VALUES (1,'sam-session','user','Approve the displayed change',?,'456',1,0,0)",
                (datetime.fromisoformat("2026-09-19T03:00:00+00:00").timestamp(),),
            )
        self.case = {
            "id": str(uuid.uuid4()), "summary": "A verified repair awaits deployment",
            "handling_revision": 2, "next_action": "approve_deploy", "category": "defect",
            "handling_context": {
                "commit": "a" * 40, "base_commit": "b" * 40,
                "verification": "Passed checks", "rollback": "Restore previous release",
            },
            "processing_history": [
                {"revision": 2, "recorded_at": "2026-09-19T01:00:00+00:00"}
            ],
        }
        self.request_hash = decision.request_view(self.case)["request_hash"]
        self.payloads = []

    def rpc(self, args, payload=None):
        if "--read" in args:
            return copy.deepcopy(self.case)
        self.payloads.append(copy.deepcopy(payload))
        previous = [
            item for item in self.case["processing_history"]
            if item.get("entry_id") == payload["entry_id"]
        ]
        if not previous:
            if payload["expected_revision"] != self.case["handling_revision"]:
                raise ValueError("Revision changed")
            self.case["handling_revision"] += 1
            self.case["handling_context"].update(json.loads(payload["details_json"]))
            self.case["next_action"] = payload["next_action"]
            self.case["processing_history"].append({
                "entry_id": payload["entry_id"],
                "revision": self.case["handling_revision"],
                "status": payload["status"], "action": payload["action"],
                "next_action": payload["next_action"],
                "handling_context": copy.deepcopy(self.case["handling_context"]),
            })
        return copy.deepcopy(self.case)

    def invoke(self, value="approve", instruction="", rpc=None):
        return decision.decide(
            self.profile, self.env, self.case["id"], 2, self.request_hash,
            value, instruction, rpc or self.rpc,
        )

    def test_approval_records_only_and_main_gets_deploy_action(self):
        result = self.invoke()
        self.assertFalse(result["sam_execution_allowed"])
        self.assertEqual(result["next_action"], "deploy")
        self.assertEqual(result["commit"], "a" * 40)
        details = self.case["handling_context"]
        self.assertEqual(details["approval_actor"], "sam")
        self.assertEqual(details["approval_message_id"], "456")
        self.assertEqual(details["approval_request_hash"], self.request_hash)
        self.assertNotIn("Approve the displayed change", json.dumps(self.payloads))

    def test_change_approval_routes_to_main_repair_not_sam(self):
        self.case["next_action"] = "approve_change"
        self.case["handling_context"] = {
            "proposal": "Change shared structure", "impact": "Known callers",
            "verification": "Focused tests", "rollback": "Revert commit",
        }
        self.request_hash = decision.request_view(self.case)["request_hash"]
        result = self.invoke()
        self.assertEqual(result["next_action"], "repair")
        self.assertFalse(result["sam_execution_allowed"])

    def test_reject_defer_revise_and_respond_have_bounded_actions(self):
        cases = (
            ("approve_deploy", "reject", "not this change", "none"),
            ("approve_deploy", "defer", "", "approve_deploy"),
            ("approve_deploy", "revise", "use the smaller option", "investigate"),
            ("user_action", "respond", "the source is in Drive", "investigate"),
        )
        for action, response, instruction, target in cases:
            with self.subTest(action=action, response=response):
                self.setUp()
                if action == "user_action":
                    self.case["next_action"] = action
                    self.case["handling_context"] = {
                        "owner": "owner", "required_action": "Provide source",
                        "resume_condition": "Source received",
                    }
                    self.request_hash = decision.request_view(self.case)["request_hash"]
                outcome = self.invoke(response, instruction)
                self.assertEqual(outcome["next_action"], target)
                self.assertFalse(outcome["sam_execution_allowed"])

    def test_revision_or_response_without_instruction_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "require"):
            self.invoke("revise")
        self.assertEqual(self.payloads, [])

    def test_cron_and_cli_cannot_record_owner_response(self):
        self.env["HERMES_CRON_SESSION"] = "1"
        with self.assertRaisesRegex(ValueError, "current owner"):
            self.invoke()
        self.env = {}
        with self.assertRaisesRegex(ValueError, "current owner"):
            self.invoke()
        self.assertEqual(self.payloads, [])

    def test_other_user_or_chat_cannot_record(self):
        for key in ("HERMES_SESSION_USER_ID", "HERMES_SESSION_CHAT_ID"):
            with self.subTest(key=key):
                original = self.env[key]
                self.env[key] = "999"
                with self.assertRaisesRegex(ValueError, "owner conversation"):
                    self.invoke()
                self.env[key] = original
        self.assertEqual(self.payloads, [])

    def test_old_message_cannot_authorize_a_new_request(self):
        self.case["processing_history"][0]["recorded_at"] = "2026-09-19T04:00:00+00:00"
        with self.assertRaisesRegex(ValueError, "before this request"):
            self.invoke()
        self.assertEqual(self.payloads, [])

    def test_changed_revision_or_commit_requires_current_response(self):
        for changed in ("revision", "commit"):
            with self.subTest(changed=changed):
                old = copy.deepcopy(self.case)
                if changed == "revision":
                    self.case["handling_revision"] = 3
                else:
                    self.case["handling_context"]["commit"] = "c" * 40
                with self.assertRaisesRegex(ValueError, "request changed"):
                    self.invoke()
                self.case = old
        self.assertEqual(self.payloads, [])

    def test_lost_response_replays_identical_payload_once(self):
        def lost_response(args, payload=None):
            response = self.rpc(args, payload)
            if payload is not None:
                raise TimeoutError("Lost response after commit")
            return response

        with self.assertRaises(TimeoutError):
            self.invoke(rpc=lost_response)
        result = self.invoke()
        self.assertFalse(result["sam_execution_allowed"])
        self.assertEqual(self.payloads[0], self.payloads[1])
        self.assertEqual(len(self.case["processing_history"]), 2)


if __name__ == "__main__":
    unittest.main()
