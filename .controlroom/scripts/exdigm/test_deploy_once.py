import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid
from unittest.mock import patch

import deploy_once as deploy


class DeploymentRunnerTests(unittest.TestCase):
    def test_contract_is_bound_to_owner_approval_receipt(self):
        repair = uuid.uuid4()
        track = {
            "id": str(uuid.uuid4()),
            "revision": 7,
            "handling_context": {
                "commit": "a" * 40,
                "repair_ref": f"refs/operational-repairs/{repair}",
                "approval_entry_id": str(uuid.uuid4()),
                "approval_request_hash": "b" * 64,
                "approval_decision": "approve",
                "approved_action": "approve_deploy",
                "base_commit": "c" * 40,
                "verification_receipt": "sha256:" + "d" * 64,
            },
        }
        contract = deploy._deployment_contract(track)
        self.assertEqual(contract["track_id"], track["id"])
        self.assertEqual(contract["expected_revision"], 7)
        self.assertEqual(contract["commit"], "a" * 40)
        for key in (
            "approval_decision",
            "approved_action",
            "commit",
            "base_commit",
            "verification_receipt",
        ):
            changed = json.loads(json.dumps(track))
            changed["handling_context"][key] = "wrong"
            with self.subTest(key=key), self.assertRaises(ValueError):
                deploy._deployment_contract(changed)

    def test_helper_executes_only_configured_forced_command_with_stdin_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake = root / "fake.py"
            fake.write_text(
                "import json,sys; p=json.load(sys.stdin); "
                "print(json.dumps({'production_commit':p['commit']}))\n",
                encoding="utf-8",
            )
            helper = root / "helper.py"
            result = root / "result.json"
            contract = {"commit": "a" * 40}
            deploy._write_helper(
                helper,
                {"deploy_command": [sys.executable, str(fake)]},
                contract,
                result,
            )
            completed = subprocess.run(
                [sys.executable, str(helper)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(
                json.loads(result.read_text())["production_commit"],
                contract["commit"],
            )

    def test_success_payload_schedules_main_codex_verification(self):
        run = str(uuid.uuid4())
        track = {
            "id": str(uuid.uuid4()),
            "revision": 8,
            "category": "defect",
        }
        contract = {"commit": "a" * 40}
        payload = deploy._success_payload(
            run,
            track,
            contract,
            Path("evidence.jsonl"),
            {"production_commit": "a" * 40},
        )
        self.assertEqual(payload["actor"], "deploy_codex")
        self.assertEqual(payload["next_action"], "verify_result")
        self.assertEqual(payload["details"]["workspace_reserved"], "no")

    def test_prompt_explicitly_keeps_sam_out_of_execution(self):
        prompt = deploy._prompt(
            Path("helper.py"),
            {"commit": "a" * 40, "track_id": str(uuid.uuid4())},
        )
        self.assertIn("샘은 결정을 전달·기록했을 뿐 실행자가 아닙니다", prompt)
        self.assertIn("helper 밖의", prompt)

    def test_lost_codex_response_recovers_confirmed_exact_deployment(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            run = str(uuid.uuid4())
            track = {
                "id": str(uuid.uuid4()),
                "revision": 8,
                "category": "defect",
            }
            contract = {"commit": "a" * 40}
            with patch.object(
                deploy,
                "_deploy_status",
                return_value={
                    "production_commit": "a" * 40,
                    "deployment_completed": True,
                },
            ):
                payload = deploy._recover_deployed(
                    {}, run, track, contract, directory
                )
            self.assertEqual(payload["next_action"], "verify_result")
            self.assertEqual(payload["details"]["workspace_reserved"], "no")
            self.assertTrue((directory / "status-recovery.json").is_file())

    def test_matching_commit_without_completion_receipt_is_not_recovered(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(
                deploy,
                "_deploy_status",
                return_value={
                    "production_commit": "a" * 40,
                    "deployment_completed": False,
                },
            ):
                payload = deploy._recover_deployed(
                    {},
                    str(uuid.uuid4()),
                    {
                        "id": str(uuid.uuid4()),
                        "revision": 8,
                        "category": "defect",
                    },
                    {"commit": "a" * 40},
                    Path(temporary),
                )
            self.assertIsNone(payload)


if __name__ == "__main__":
    unittest.main()
