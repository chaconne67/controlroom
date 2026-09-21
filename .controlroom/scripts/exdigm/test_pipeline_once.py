import copy
import unittest
import uuid

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
            },
        )
        self.assertIn("샘은 주인님과 DB 사이의 통신만 담당", prompt)
        self.assertIn("코드·설정·데이터·Git 상태를 바꾸지 마세요", prompt)
        self.assertIn("approve_change", prompt)

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


if __name__ == "__main__":
    unittest.main()
