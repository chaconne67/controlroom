import json
from pathlib import Path
import tempfile
import unittest
import uuid

import restricted_access as access


class RestrictedAccessTests(unittest.TestCase):
    def test_public_reads_preserve_existing_cli_arguments(self):
        for args in (
            [
                "get",
                "project/exdigm-operating-context",
                "--source",
                "default",
            ],
            [
                "query",
                "operational errors",
                "--source-id",
                "default",
                "--json",
            ],
            ["list", "--source", "default"],
        ):
            self.assertEqual(access.gbrain_args(args), args)

    def test_private_sources_and_mutating_gbrain_commands_are_denied(self):
        for args in (
            ["capture", "--source", "default"],
            ["sql", "SELECT 1"],
            ["get", "page", "--source", "personal"],
            ["get", "--source", "default"],
            [
                "query",
                "term",
                "--source-id",
                "default",
                "--source-id",
                "personal",
            ],
        ):
            with self.subTest(args=args), self.assertRaises(ValueError):
                access.gbrain_args(args)

    def test_worker_transport_is_mode_scoped(self):
        run = str(uuid.uuid4())
        track = str(uuid.uuid4())
        event = str(uuid.uuid4())
        repair = [
            "pipeline",
            "claim",
            "--mode",
            "repair",
            "--automation-run",
            run,
        ]
        deploy = [
            "pipeline",
            "claim",
            "--mode",
            "deploy",
            "--automation-run",
            run,
        ]
        self.assertEqual(access.record_args(repair, "repair"), repair)
        self.assertEqual(access.record_args(deploy, "deploy"), deploy)
        for worker in ("repair", "deploy", "sam"):
            for args in (
                ["pipeline", "read-track", "--track-id", track],
                ["pipeline", "read-event", "--event-id", event],
                ["pipeline", "--json-input"],
            ):
                self.assertEqual(access.pipeline_args(args, worker), args)
        with self.assertRaises(ValueError):
            access.record_args(deploy, "repair")
        with self.assertRaises(ValueError):
            access.record_args(repair, "deploy")
        with self.assertRaises(ValueError):
            access.pipeline_args(["pipeline", "shell"], "repair")

    def fixture(self, action="investigate"):
        run = uuid.uuid4()
        case = {
            "id": uuid.uuid4(),
            "revision": 3,
            "next_action": action,
            "handling_context": {"automation_run": str(run)},
        }
        payload = {
            "operation": "result",
            "track_id": str(case["id"]),
            "status": "succeeded",
            "action": "Verified result",
            "category": "defect",
            "next_action": "approve_change",
            "expected_revision": 3,
            "entry_id": str(uuid.uuid5(run, "result")),
            "actor": "main_codex",
            "details": {
                "root_cause": "verified",
                "proposal": "fix",
                "alternatives": "none",
                "recommendation_reason": "root fix",
                "impact": "bounded",
                "verification": "tests",
                "rollback": "previous",
            },
        }
        return case, payload

    def test_repair_worker_can_record_only_owned_stage_transition(self):
        case, payload = self.fixture()
        self.assertEqual(
            access.authorize_pipeline(payload, case, "repair"), payload
        )
        for change in (
            {"entry_id": str(uuid.uuid4())},
            {"track_id": str(uuid.uuid4())},
            {"expected_revision": 2},
            {"actor": "sam"},
            {"next_action": "approve_deploy"},
            {"operation": "decide"},
            {"details": {"approval_decision": "approve"}},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                access.authorize_pipeline(
                    {**payload, **change}, case, "repair"
                )

    def test_lost_result_response_allows_only_the_exact_ledger_replay(self):
        case, payload = self.fixture()
        advanced = {
            **case,
            "revision": 4,
            "next_action": "approve_change",
        }
        existing = {
            "track_id": case["id"],
            "track_revision": 4,
            "event_type": "result_recorded",
            "actor": "main_codex",
        }
        self.assertEqual(
            access.authorize_pipeline(payload, advanced, "repair", existing),
            payload,
        )
        for change in (
            {"actor": "deploy_codex"},
            {"track_id": uuid.uuid4()},
            {"track_revision": 5},
            {"event_type": "decision_recorded"},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                access.authorize_pipeline(
                    payload,
                    advanced,
                    "repair",
                    {**existing, **change},
                )

    def test_split_is_investigation_only_and_owned(self):
        case, payload = self.fixture()
        split = {
            "operation": "split",
            "track_id": str(case["id"]),
            "expected_revision": 3,
            "entry_id": str(
                uuid.uuid5(
                    uuid.UUID(case["handling_context"]["automation_run"]),
                    "split",
                )
            ),
            "actor": "main_codex",
            "children": [
                {"title": "one", "scope": "first", "blocking": True},
                {"title": "two", "scope": "second", "blocking": True},
            ],
        }
        self.assertEqual(
            access.authorize_pipeline(split, case, "repair"), split
        )
        case["next_action"] = "repair"
        with self.assertRaises(ValueError):
            access.authorize_pipeline(split, case, "repair")
        replay_case = {**case, "revision": 4, "next_action": "none"}
        existing = {
            "track_id": case["id"],
            "track_revision": 4,
            "event_type": "result_recorded",
            "actor": "main_codex",
        }
        self.assertEqual(
            access.authorize_pipeline(split, replay_case, "repair", existing),
            split,
        )

    def test_deploy_worker_cannot_record_repair_or_owner_decision(self):
        case, payload = self.fixture("deploy")
        payload.update(
            actor="deploy_codex",
            next_action="verify_result",
            details={
                "verification": "production commit confirmed",
                "deployment_status": "succeeded",
                "deployed_commit": "a" * 40,
            },
        )
        self.assertEqual(
            access.authorize_pipeline(payload, case, "deploy"), payload
        )
        for change in (
            {"next_action": "approve_deploy"},
            {"actor": "main_codex"},
            {"operation": "decide"},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                access.authorize_pipeline(
                    {**payload, **change}, case, "deploy"
                )

    def test_deployment_contract_rejects_ambiguous_values(self):
        payload = {
            "track_id": str(uuid.uuid4()),
            "expected_revision": 4,
            "commit": "a" * 40,
            "repair_ref": f"refs/operational-repairs/{uuid.uuid4()}",
            "approval_entry_id": str(uuid.uuid4()),
            "request_hash": "b" * 64,
        }
        self.assertEqual(access._deployment_contract(payload), payload)
        for change in (
            {"commit": "main"},
            {"repair_ref": "refs/heads/main"},
            {"request_hash": "short"},
            {"unexpected": "field"},
        ):
            with self.subTest(change=change), self.assertRaises(
                (ValueError, TypeError)
            ):
                access._deployment_contract({**payload, **change})

    def test_deployment_status_requires_an_exact_completion_receipt(self):
        payload = {
            "track_id": str(uuid.uuid4()),
            "approval_entry_id": str(uuid.uuid4()),
            "commit": "a" * 40,
        }
        with tempfile.TemporaryDirectory() as temporary:
            receipt_path = Path(temporary) / "deployment.json"
            log_path = Path(temporary) / "deployment.log"
            log_path.write_text("official deploy passed\n", encoding="utf-8")
            receipt = access._write_deployment_receipt(
                receipt_path,
                payload,
                payload["commit"],
                log_path,
            )
            self.assertTrue(receipt["completed"])
            self.assertEqual(
                access._read_deployment_receipt(
                    receipt_path,
                    payload,
                    payload["commit"],
                ),
                receipt,
            )
            with self.assertRaises(ValueError):
                access._read_deployment_receipt(
                    receipt_path,
                    {**payload, "commit": "b" * 40},
                    payload["commit"],
                )

    def test_legacy_transport_remains_repair_only_during_migration(self):
        identifier = str(uuid.uuid4())
        for args in (
            ["--claim-next", "--automation-run", identifier],
            [identifier, "--read"],
            ["--json-input"],
        ):
            self.assertEqual(access.record_args(args, "repair"), args)
            with self.assertRaises(ValueError):
                access.record_args(args, "deploy")


if __name__ == "__main__":
    unittest.main()
