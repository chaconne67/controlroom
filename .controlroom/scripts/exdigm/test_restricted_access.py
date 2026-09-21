import json
import unittest
from unittest.mock import patch
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

    def deploy_fixture(self):
        error_id, run_id, approval_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        commit, base = "a" * 40, "b" * 40
        details = {
            "approval_decision": "approve", "approval_request_type": "approve_deploy",
            "approval_commit": commit, "commit": commit, "base_commit": base,
            "repair_ref": "refs/operational-repairs/" + str(uuid.uuid4()),
            "approval_request_hash": "c" * 64, "approval_entry_id": str(approval_id),
            "automation_run": str(run_id), "workspace_reserved": "yes",
        }
        request = {"action": "execute", "error_id": str(error_id), "revision": 8,
                   "commit": commit, "automation_run": str(run_id)}
        case = {"id": str(error_id), "handling_revision": 8, "processing_status": "in_progress",
                "next_action": "repair", "handling_context": details,
                "processing_history": [
                    {"entry_id": str(approval_id), "revision": 7, "next_action": "repair",
                     "handling_context": details.copy()},
                    {"entry_id": str(run_id), "revision": 8, "next_action": "repair",
                     "handling_context": details.copy()},
                ]}
        return request, case

    def test_deploy_transport_accepts_only_exact_revision_bound_arguments(self):
        request, _ = self.deploy_fixture()
        args = ["execute", "--error-id", request["error_id"], "--revision", "8",
                "--commit", request["commit"], "--automation-run", request["automation_run"]]
        self.assertEqual(access.deploy_args(args), request)
        self.assertEqual(access.deploy_args(["check"]), {"action": "check"})
        for changed in (args[:-1], [*args[:-2], "--run", args[-1]],
                        [*args[:6], "x" * 40, *args[7:]], ["shell"]):
            with self.subTest(changed=changed), self.assertRaises((ValueError, TypeError)):
                access.deploy_args(changed)

    def test_deploy_requires_immediate_exact_approval_and_current_claim(self):
        request, case = self.deploy_fixture()
        self.assertEqual(access.authorize_deploy(request, case), case["handling_context"])
        mutations = (
            ("request revision", lambda r, c: r.update(revision=7)),
            ("decision", lambda r, c: c["handling_context"].update(approval_decision="defer")),
            ("commit", lambda r, c: c["handling_context"].update(approval_commit="d" * 40)),
            ("owner", lambda r, c: c["handling_context"].update(automation_run=str(uuid.uuid4()))),
            ("reservation", lambda r, c: c["handling_context"].update(workspace_reserved="no")),
            ("history", lambda r, c: c.update(processing_history=c["processing_history"][:-1])),
        )
        for name, mutate in mutations:
            with self.subTest(name=name):
                changed_request, changed_case = self.deploy_fixture()
                mutate(changed_request, changed_case)
                with self.assertRaises(ValueError):
                    access.authorize_deploy(changed_request, changed_case)

    def test_execute_uses_only_saved_ref_and_official_deploy_script(self):
        request, case = self.deploy_fixture()
        details = case["handling_context"]
        arguments = ["execute", "--error-id", request["error_id"], "--revision", "8",
                     "--commit", request["commit"], "--automation-run", request["automation_run"]]
        values = {
            (str(access.DEPLOY_DEBUG_ROOT), "rev-parse", details["repair_ref"]): request["commit"],
            (str(access.DEPLOY_PRODUCTION_ROOT), "rev-parse", "HEAD"): details["base_commit"],
            (str(access.DEPLOY_DEBUG_ROOT), "rev-parse", "HEAD"): details["base_commit"],
            (str(access.DEPLOY_DEBUG_ROOT), "status", "--porcelain"): "",
        }
        def git(root, *args):
            return values[(str(root), *args)]
        receipt = {"production": request["commit"], "debug": request["commit"],
                   "origin_main": request["commit"], "services": {}}
        with patch.object(access, "read_deploy_case", return_value=case), \
             patch.object(access, "git_read", side_effect=git), \
             patch.object(access, "deployment_state", return_value=receipt), \
             patch.object(access.subprocess, "run") as run, \
             patch("builtins.print"):
            access.deploy(arguments)
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[-1].args[0], [str(access.DEPLOY_SCRIPT), "prod"])
        self.assertEqual(run.call_args_list[-1].kwargs["cwd"], access.DEPLOY_DEBUG_ROOT)
        self.assertTrue(run.call_args_list[-1].kwargs["check"])


if __name__ == "__main__":
    unittest.main()
