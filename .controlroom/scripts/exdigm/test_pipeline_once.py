import copy
from contextlib import contextmanager
import json
from pathlib import Path
import tempfile
import unittest
import uuid
from unittest import mock

import pipeline_once as pipeline


def details(**updates):
    value = {key: "" for key in pipeline.STRING_DETAILS}
    value["test_targets"] = []
    value.update(updates)
    return value


class PipelineContractTests(unittest.TestCase):
    def test_investigation_can_only_propose_or_split_not_repair(self):
        proposal = {
            "category": "defect",
            "next_action": "approve_change",
            "status": "succeeded",
            "action": "Confirmed cause and prepared a bounded proposal",
            "details": details(
                root_cause="reproduced producer defect",
                proposal="fix producer boundary",
                alternatives="consumer workaround",
                recommendation_reason="removes the source cause",
                impact="one producer and callers",
                verification="failure variants and success cases",
                rollback="restore previous commit",
            ),
            "split_tracks": [],
        }
        self.assertEqual(
            pipeline.validate_result(copy.deepcopy(proposal), "investigate"),
            proposal,
        )
        forbidden = copy.deepcopy(proposal)
        forbidden["next_action"] = "approve_deploy"
        forbidden["details"].update(
            commit="a" * 40, test_targets=["tests/test_example.py"]
        )
        with self.assertRaisesRegex(ValueError, "current pipeline stage"):
            pipeline.validate_result(forbidden, "investigate")

    def test_multiple_failures_split_before_independent_approval(self):
        result = {
            "category": "unclassified",
            "next_action": "investigate",
            "status": "succeeded",
            "action": "Separated two independently resolvable failures",
            "details": details(),
            "split_tracks": [
                {"title": "file", "scope": "generation", "blocking": True},
                {"title": "mail", "scope": "delivery", "blocking": True},
            ],
        }
        self.assertEqual(
            pipeline.validate_result(copy.deepcopy(result), "investigate"),
            result,
        )
        with self.assertRaisesRegex(ValueError, "Only investigation"):
            pipeline.validate_result(result, "repair")
        nonblocking = copy.deepcopy(result)
        for child in nonblocking["split_tracks"]:
            child["blocking"] = False
        with self.assertRaisesRegex(ValueError, "blocking track"):
            pipeline.validate_result(nonblocking, "investigate")

    def test_approved_repair_must_end_at_separate_deploy_approval(self):
        result = {
            "category": "defect",
            "next_action": "approve_deploy",
            "status": "succeeded",
            "action": "Implemented and committed approved change",
            "details": details(
                root_cause="confirmed",
                commit="a" * 40,
                verification="focused regression passed",
                rollback="deploy previous commit",
                test_targets=["tests/test_pipeline.py::test_case"],
            ),
            "split_tracks": [],
        }
        self.assertEqual(
            pipeline.validate_result(copy.deepcopy(result), "repair"), result
        )
        with self.assertRaisesRegex(ValueError, "current pipeline stage"):
            pipeline.validate_result(result, "investigate")

    def test_outcome_verification_requests_owner_close(self):
        result = {
            "category": "defect",
            "next_action": "approve_close",
            "status": "succeeded",
            "action": "Original business outcome is restored",
            "details": details(
                root_cause="confirmed",
                verification="production path checked",
                outcome_verification="required output was produced and consumed",
            ),
            "split_tracks": [],
        }
        self.assertEqual(
            pipeline.validate_result(copy.deepcopy(result), "verify_result"),
            result,
        )

    def test_prompt_assigns_execution_to_main_codex_not_sam(self):
        case = {
            "selected_track": {
                "next_action": "investigate",
                "id": str(uuid.uuid4()),
            }
        }
        prompt = pipeline.prompt_for(
            case,
            {
                "code_ssh": ["ssh", "restricted"],
                "debug_root": "/debug",
                "gbrain_ssh": ["ssh", "gbrain"],
                "remote_uv": "/remote/uv",
            },
        )
        self.assertIn("샘은 주인님과 DB 사이의 통신만 담당", prompt)
        self.assertIn("코드·설정·데이터·Git 상태를 바꾸지 마세요", prompt)
        self.assertIn("approve_change", prompt)
        self.assertIn('["ssh", "gbrain"]', prompt)
        self.assertIn("/remote/uv", prompt)
        self.assertIn("직접 실행하지 마세요", prompt)

    def test_agent_environment_preflight_uses_restricted_existing_paths(self):
        config = {
            "code_ssh": ["ssh", "code"],
            "gbrain_ssh": ["ssh", "gbrain"],
            "remote_uv": "/home/chaconne/.local/bin/uv",
        }
        with mock.patch.object(
            pipeline,
            "run_command",
            side_effect=[
                "# GBrain Operating Protocol for Agents",
                "uv 0.8.22",
            ],
        ) as run:
            self.assertEqual(
                pipeline.agent_environment_preflight(config),
                {"gbrain": "default-read", "remote_uv": "uv 0.8.22"},
            )
        self.assertEqual(
            run.call_args_list,
            [
                mock.call(
                    [
                        "ssh",
                        "gbrain",
                        "gbrain get agent/gbrain-operating-protocol --source default",
                    ],
                    timeout=45,
                ),
                mock.call(
                    [
                        "ssh",
                        "code",
                        "/home/chaconne/.local/bin/uv --version",
                    ],
                    timeout=45,
                ),
            ],
        )

    def test_malformed_or_failed_result_cannot_advance(self):
        result = {
            "category": "defect",
            "next_action": "approve_change",
            "status": "failed",
            "action": "Investigation failed",
            "details": details(
                root_cause="unconfirmed",
                proposal="guess",
                alternatives="unknown",
                recommendation_reason="unknown",
                impact="unknown",
                verification="not completed",
                rollback="not applicable",
            ),
            "split_tracks": [],
        }
        with self.assertRaisesRegex(ValueError, "cannot advance"):
            pipeline.validate_result(result, "investigate")
        result["status"] = "succeeded"
        result["split_tracks"] = {}
        with self.assertRaisesRegex(ValueError, "must be a list"):
            pipeline.validate_result(result, "investigate")

    def test_clean_invalid_execution_records_wait_and_releases_workspace(self):
        with tempfile.TemporaryDirectory() as temporary:
            state_root = Path(temporary)
            run_calls = []
            records = []
            releases = []
            track = {
                "id": str(uuid.uuid4()),
                "status": "running",
                "revision": 3,
                "next_action": "investigate",
                "handling_context": {},
            }
            case = {"id": str(uuid.uuid4()), "selected_track": track}

            @contextmanager
            def workspace_lock(*_args):
                release = []
                try:
                    yield release
                finally:
                    releases.append(bool(release))

            def run_command(command, **kwargs):
                run_calls.append(command)
                if command[0] == "record":
                    if "claim" in command:
                        run_id = command[command.index("--automation-run") + 1]
                        track["handling_context"] = {
                            "automation_run": run_id,
                            "workspace_reserved": "yes",
                        }
                        return json.dumps(case)
                    if "read-track" in command:
                        return json.dumps({"selected_track": track})
                    payload = json.loads(kwargs["payload"])
                    records.append(payload)
                    return json.dumps(
                        {
                            "id": case["id"],
                            "selected_track": {
                                **track,
                                "status": "waiting",
                                "next_action": payload["next_action"],
                            },
                        }
                    )
                result_path = Path(
                    command[command.index("--output-last-message") + 1]
                )
                result_path.write_text(
                    json.dumps({"invalid": "contract"}), encoding="utf-8"
                )
                if kwargs.get("evidence"):
                    kwargs["evidence"].write_text(
                        json.dumps(
                            {
                                "type": "thread.started",
                                "thread_id": str(uuid.uuid4()),
                            }
                        )
                        + "\n",
                        encoding="utf-8",
                    )
                return ""

            config = {
                "record_command": ["record"],
                "codex_command": ["codex"],
                "code_ssh": ["ssh", "restricted"],
                "gbrain_ssh": ["ssh", "gbrain"],
                "remote_uv": "/remote/uv",
                "project_root": "/controlroom/exdigm",
                "debug_root": "/debug",
                "production_root": "/prod",
                "restricted_user": "repair-test-user",
            }
            baseline = {"head": "a" * 40}
            fake_fcntl = mock.Mock(LOCK_EX=1, LOCK_NB=2)
            with mock.patch.dict(
                "sys.modules", {"fcntl": fake_fcntl}
            ), mock.patch.object(
                pipeline, "preflight", return_value=baseline
            ), mock.patch.object(
                pipeline, "agent_environment_preflight", return_value={}
            ), mock.patch.object(
                pipeline, "workspace_lock", workspace_lock
            ), mock.patch.object(
                pipeline, "run_command", side_effect=run_command
            ):
                outcome = pipeline.execute_once(config, state_root)

            self.assertEqual(outcome["next_action"], "external_wait")
            self.assertEqual(releases, [True])
            self.assertFalse((state_root / "active.json").exists())
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["status"], "failed")
            self.assertEqual(records[0]["details"]["workspace_reserved"], "no")
            self.assertEqual(sum(call[0] == "codex" for call in run_calls), 2)
            self.assertTrue(
                next(state_root.glob("*/result-payload.json")).is_file()
            )
            self.assertFalse(any(state_root.glob("*/interrupted-payload.json")))


if __name__ == "__main__":
    unittest.main()
