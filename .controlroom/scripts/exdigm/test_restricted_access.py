import json
import unittest
import uuid

import restricted_access as access


class RestrictedAccessTests(unittest.TestCase):
    def test_public_reads_preserve_existing_cli_arguments(self):
        for args in (["get", "project/exdigm-operating-context", "--source", "default"],
                     ["query", "operational errors", "--source-id", "default", "--json"],
                     ["list", "--source", "default"]):
            self.assertEqual(access.gbrain_args(args), args)

    def test_private_sources_and_mutating_commands_are_denied(self):
        for args in (["capture", "--source", "default"], ["sql", "SELECT 1"],
                     ["get", "page", "--source", "personal"], ["get", "--source", "default"],
                     ["query", "term", "--source-id", "default", "--source-id", "personal"],
                     ["get", "page", "--source", "default", "--output", "/etc/test"]):
            with self.subTest(args=args), self.assertRaises(ValueError):
                access.gbrain_args(args)

    def test_record_transport_exposes_only_existing_three_operations(self):
        identifier = str(uuid.uuid4())
        for args in (["--claim-next", "--automation-run", identifier], [identifier, "--read"], ["--json-input"]):
            self.assertEqual(access.record_args(args), args)
        for args in ([], ["shell"], [identifier, "--status", "succeeded"], ["--claim-next", "--automation-run", "x"]):
            with self.subTest(args=args), self.assertRaises(ValueError):
                access.record_args(args)

    def fixture(self):
        run = uuid.uuid4()
        case = {"id": uuid.uuid4(), "handling_context": {"automation_run": str(run)}}
        payload = {"error_id": str(case["id"]), "status": "succeeded", "action": "Verified result",
                   "next_action": "approve_deploy", "expected_revision": 2,
                   "entry_id": str(uuid.uuid5(run, "result")), "details_json": json.dumps({"commit": "a" * 40})}
        return case, payload

    def test_claimed_results_and_interruption_are_allowed(self):
        case, payload = self.fixture()
        self.assertEqual(access.authorize_result(payload, case), payload)
        payload.update(status="failed", next_action="user_action",
                       entry_id=str(uuid.uuid5(uuid.UUID(case["handling_context"]["automation_run"]), "interrupted")))
        self.assertEqual(access.authorize_result(payload, case), payload)

    def test_unowned_result_and_forged_approval_are_denied(self):
        for change in ({"entry_id": str(uuid.uuid4())}, {"error_id": str(uuid.uuid4())},
                       {"expected_revision": None}, {"next_action": "repair"},
                       {"status": "in_progress"}, {"approval": "approved"},
                       {"details_json": json.dumps({"approval_decision": "approved"})}):
            case, payload = self.fixture()
            with self.subTest(change=change), self.assertRaises(ValueError):
                access.authorize_result({**payload, **change}, case)


if __name__ == "__main__":
    unittest.main()
