import json
import hashlib
from types import SimpleNamespace
import unittest
import uuid

import restricted_access as access


class RestrictedAccessTests(unittest.TestCase):
    def test_public_reads_preserve_existing_cli_arguments(self):
        for args in (
            ["get", "project/exdigm-operating-context", "--source", "default"],
            ["query", "operational errors", "--source-id", "default", "--json"],
            ["list", "--source", "default"],
        ):
            self.assertEqual(access.gbrain_args(args), args)

    def test_private_sources_and_mutating_commands_are_denied(self):
        for args in (
            ["capture", "--source", "default"], ["sql", "SELECT 1"],
            ["get", "page", "--source", "personal"],
            ["get", "--source", "default"],
        ):
            with self.subTest(args=args), self.assertRaises(ValueError):
                access.gbrain_args(args)

    def test_record_and_sam_transports_are_separate(self):
        identifier = str(uuid.uuid4())
        for args in (
            ["--claim-next", "--automation-run", identifier],
            [identifier, "--read"], ["--json-input"],
        ):
            self.assertEqual(access.record_args(args), args)
        for args in (["--list"], [identifier, "--read"], ["--json-input"]):
            self.assertEqual(access.sam_args(args), args)
        for args in ([], ["shell"], ["--claim-next", "--automation-run", identifier]):
            with self.subTest(args=args), self.assertRaises(ValueError):
                access.sam_args(args)

    def result_fixture(self, current="investigate", target="approve_deploy"):
        run = uuid.uuid4()
        case = {
            "id": uuid.uuid4(), "next_action": current, "processing_history": [],
            "handling_context": {"automation_run": str(run)},
        }
        payload = {
            "error_id": str(case["id"]), "status": "succeeded",
            "action": "Verified result", "next_action": target,
            "expected_revision": 2,
            "entry_id": str(uuid.uuid5(run, "result")),
            "details_json": json.dumps({"commit": "a" * 40}),
        }
        return case, payload

    def test_worker_result_is_owned_and_follows_current_action(self):
        case, payload = self.result_fixture()
        self.assertEqual(access.authorize_result(payload, case), payload)
        for change in (
            {"entry_id": str(uuid.uuid4())}, {"error_id": str(uuid.uuid4())},
            {"next_action": "verify_result"}, {"status": "in_progress"},
            {"details_json": json.dumps({"approval_decision": "approve"})},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                access.authorize_result({**payload, **change}, case)

    def sam_fixture(self, action="approve_change", decision="approve"):
        error_id = uuid.uuid4()
        context = {
            "proposal": "Change the validated contract", "impact": "One producer",
            "verification": "Focused regression", "rollback": "Revert commit",
        }
        if action == "approve_deploy":
            context = {
                "commit": "a" * 40, "verification": "Tests passed",
                "rollback": "Deploy previous commit",
            }
        elif action == "user_action":
            context = {
                "owner": "owner", "required_action": "Provide source",
                "resume_condition": "Source received",
            }
        elif action == "external_wait":
            context = {"owner": "provider", "resume_condition": "Provider recovers"}
        case = {
            "id": error_id, "category": "defect", "next_action": action,
            "handling_revision": 4, "handling_context": context,
            "processing_history": [],
        }
        _, request_hash = access._canonical_request(case)
        instruction = "Use the supplied answer"
        entry_id = str(uuid.uuid5(
            error_id,
            (
                f"sam:4:{request_hash}:{decision}:456:"
                f"{hashlib.sha256(instruction.encode()).hexdigest()}"
            ),
        ))
        target = access._sam_target(action, decision)
        details = {
            "approval_actor": "sam", "approval_user_id": "123",
            "approval_session_id": "session", "approval_chat_id": "123",
            "approval_message_id": "456",
            "approval_message_sha256": "b" * 64,
            "approval_message_at": "2026-09-21T00:00:00+00:00",
            "owner_decision": decision, "owner_instruction": instruction,
            "approval_decision": decision, "approval_request_revision": "4",
            "approval_request_hash": request_hash, "approval_request_type": action,
            "approval_commit": context.get("commit", ""), "approval_entry_id": entry_id,
        }
        if decision == "reject":
            details["stop_reason"] = "Owner rejected the request"
        payload = {
            "error_id": str(error_id), "status": "succeeded",
            "action": "Sam recorded the owner's response.",
            "next_action": target, "expected_revision": 4,
            "entry_id": entry_id, "details_json": json.dumps(details),
        }
        return case, payload

    def test_owner_approval_only_changes_the_board_action(self):
        for action, target in (("approve_change", "repair"), ("approve_deploy", "deploy")):
            with self.subTest(action=action):
                case, payload = self.sam_fixture(action)
                self.assertEqual(payload["next_action"], target)
                self.assertEqual(access.authorize_sam(payload, case), payload)

    def test_other_owner_responses_have_bounded_transitions(self):
        combinations = (
            ("approve_change", "reject", "none"),
            ("approve_deploy", "defer", "approve_deploy"),
            ("approve_change", "revise", "investigate"),
            ("user_action", "respond", "investigate"),
            ("external_wait", "respond", "investigate"),
        )
        for action, decision, target in combinations:
            with self.subTest(action=action, decision=decision):
                case, payload = self.sam_fixture(action, decision)
                self.assertEqual(payload["next_action"], target)
                self.assertEqual(access.authorize_sam(payload, case), payload)

    def test_forged_or_cross_request_owner_response_is_denied(self):
        case, payload = self.sam_fixture("approve_deploy")
        details = json.loads(payload["details_json"])
        variants = (
            {**payload, "entry_id": str(uuid.uuid4())},
            {**payload, "next_action": "repair"},
            {**payload, "details_json": json.dumps({**details, "approval_commit": "c" * 40})},
            {**payload, "details_json": json.dumps({**details, "commit": "c" * 40})},
        )
        for variant in variants:
            with self.subTest(variant=variant), self.assertRaises(ValueError):
                access.authorize_sam(variant, case)

    def test_deployment_contract_has_one_exact_row_and_run(self):
        payload = {
            "error_id": str(uuid.uuid4()), "expected_revision": 7,
            "automation_run": str(uuid.uuid4()), "commit": "a" * 40,
            "repair_ref": "refs/operational-repairs/" + str(uuid.uuid4()),
            "approval_entry_id": str(uuid.uuid4()), "request_hash": "b" * 64,
        }
        self.assertEqual(access._deployment_contract(payload), payload)
        with self.assertRaises(ValueError):
            access._deployment_contract({**payload, "commit": "main"})

    def test_deployment_requires_current_claim_and_matching_owner_receipt(self):
        payload = {
            "error_id": str(uuid.uuid4()), "expected_revision": 7,
            "automation_run": str(uuid.uuid4()), "commit": "a" * 40,
            "repair_ref": "refs/operational-repairs/" + str(uuid.uuid4()),
            "approval_entry_id": str(uuid.uuid4()), "request_hash": "b" * 64,
        }
        approved = {
            "commit": payload["commit"], "repair_ref": payload["repair_ref"],
            "approval_entry_id": payload["approval_entry_id"],
            "approval_request_hash": payload["request_hash"],
            "approval_decision": "approve",
            "approval_request_type": "approve_deploy",
        }
        error = SimpleNamespace(
            next_action="deploy", processing_status="in_progress",
            handling_revision=7,
            handling_context={
                **approved, "automation_run": payload["automation_run"],
                "workspace_reserved": "yes", "base_commit": "c" * 40,
            },
            processing_history=[{
                "entry_id": payload["approval_entry_id"],
                "handling_context": approved,
            }],
        )
        self.assertEqual(access._authorize_deployment_row(error, payload), "c" * 40)
        for attribute, value in (
            ("next_action", "verify_result"),
            ("processing_status", "succeeded"),
            ("handling_revision", 8),
        ):
            with self.subTest(attribute=attribute):
                changed = SimpleNamespace(**vars(error))
                setattr(changed, attribute, value)
                with self.assertRaises(ValueError):
                    access._authorize_deployment_row(changed, payload)
        changed = SimpleNamespace(**vars(error))
        changed.processing_history = []
        with self.assertRaisesRegex(ValueError, "receipt"):
            access._authorize_deployment_row(changed, payload)


if __name__ == "__main__":
    unittest.main()
