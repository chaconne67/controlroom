import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from contextlib import contextmanager
import uuid

import repair_once as repair


def result(action="user_action"):
    details = dict.fromkeys(repair.DETAILS, "")
    details.update(owner="owner", required_action="Provide missing evidence", resume_condition="Evidence received")
    if action == "approve_deploy":
        details.update(root_cause="Reproduced defect", commit="b"*40,
                       verification="Official checks passed", rollback="Deploy approved prior commit")
    return {"category": "defect" if action=="approve_deploy" else "unclassified", "next_action": action,
            "status": "succeeded", "action": "Observed handling result", "details": details}


class RepairTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = {"record_command": ["record"], "codex_command": ["codex"],
                       "code_ssh": ["ssh", "restricted"], "project_root": "/controlroom/exdigm",
                       "debug_root": "/debug", "production_root": "/prod", "restricted_user": "repair-test-user"}
        self.calls = []
        self.case = {"id": str(uuid.uuid4()), "handling_revision": 2, "processing_status": "in_progress"}
        self.reply = result()
        self.releases = []
        self.commands_verified = True

    @contextmanager
    def lease(self, *args):
        release = []
        try:
            yield release
        finally:
            self.releases.append(bool(release))

    def command(self, command, **kwargs):
        self.calls.append((command, kwargs))
        if command[0] == "record":
            if "--claim-next" in command:
                if self.case is not None:
                    self.case.setdefault("handling_context", {"automation_run": command[-1], "workspace_reserved": "yes"})
                return json.dumps(self.case)
            if "--read" in command:
                return json.dumps(self.case)
            payload = json.loads(kwargs["payload"])
            return json.dumps({**self.case, "next_action": payload["next_action"], "handling_revision": 3})
        target = Path(command[command.index("--output-last-message")+1])
        target.write_text(json.dumps(self.reply))
        if kwargs.get("evidence"):
            events = [{"type": "thread.started", "thread_id": str(uuid.uuid4())}]
            if self.commands_verified:
                events.extend({"type": "item.completed", "item": {"id": check, "type": "command_execution", "exit_code": 0,
                              "command": f"ssh restricted scripts/debug_workspace.sh {check}"}} for check in ("test", "check"))
            kwargs["evidence"].write_text("\n".join(json.dumps(event) for event in events))
        return ""

    def invoke(self):
        with patch.object(repair, "preflight", return_value={"head": "a"*40}), \
             patch.object(repair, "workspace_lock", self.lease), \
             patch.object(repair, "run_command", side_effect=self.command), \
             patch.object(repair, "remote", side_effect=lambda c,s: "" if "status" in s else "b"*40):
            return repair.execute_once(self.config, self.root)

    def test_no_work_never_starts_codex(self):
        self.case = None
        self.assertEqual(self.invoke(), {"state": "no_work"})
        self.assertFalse(any(c[0][0]=="codex" for c in self.calls))
        self.assertEqual(self.releases, [True])

    def test_user_action_releases_only_unchanged_workspace(self):
        self.assertEqual(self.invoke()["next_action"], "user_action")
        payload = json.loads(self.calls[-1][1]["payload"])
        self.assertEqual(json.loads(payload["details_json"])["workspace_reserved"], "no")
        self.assertEqual(self.releases, [True])

    def test_repair_commit_releases_workspace_for_next_case(self):
        self.reply = result("approve_deploy")
        self.assertEqual(self.invoke()["next_action"], "approve_deploy")
        payload = json.loads(self.calls[-1][1]["payload"])
        details = json.loads(payload["details_json"])
        self.assertEqual(details["workspace_reserved"], "no")
        self.assertEqual(details["base_commit"], "a"*40)
        self.assertTrue(details["repair_ref"].startswith("refs/operational-repairs/"))
        self.assertEqual(self.releases, [True])
        self.assertFalse((self.root/"active.json").exists())
        self.assertEqual(sum(c[0][0]=="codex" for c in self.calls), 1)

    def test_claimed_verification_without_execution_evidence_is_rejected(self):
        self.reply = result("approve_deploy")
        self.commands_verified = False
        with self.assertRaisesRegex(ValueError, "Missing successful official"):
            self.invoke()
        payload = json.loads(self.calls[-1][1]["payload"])
        self.assertEqual(payload["next_action"], "user_action")
        self.assertEqual(self.releases, [False])

    def test_lost_result_response_replays_without_codex(self):
        ordinary = self.command
        lost = [False]
        def lost_response(command, **kwargs):
            answer = ordinary(command, **kwargs)
            if command[0]=="record" and "--json-input" in command and not lost[0]:
                lost[0] = True
                raise TimeoutError("response lost after commit")
            return answer
        self.command = lost_response
        with self.assertRaises(TimeoutError):
            self.invoke()
        self.assertTrue((self.root/"active.json").exists())
        self.invoke()
        self.assertEqual(sum(c[0][0]=="codex" for c in self.calls), 1)
        payloads = [k["payload"] for c,k in self.calls if c[0]=="record" and "--json-input" in c]
        self.assertEqual(payloads[0], payloads[1])

    def test_frozen_result_replay_preserves_args_and_checks_workspace(self):
        self.reply = result("approve_deploy")
        ordinary = self.command
        def lost_response(command, **kwargs):
            answer = ordinary(command, **kwargs)
            if command[0] == "record" and "--json-input" in command:
                raise TimeoutError("response lost after commit")
            return answer
        self.command = lost_response
        with self.assertRaises(TimeoutError):
            self.invoke()
        self.command = ordinary
        with patch.object(repair, "preflight", return_value={"head": "a"*40}), \
             patch.object(repair, "workspace_lock", self.lease), \
             patch.object(repair, "run_command", side_effect=self.command), \
             patch.object(repair, "park_repair") as parked:
            self.assertEqual(repair.execute_once(self.config, self.root)["next_action"], "approve_deploy")
        payloads = [k["payload"] for c,k in self.calls if c[0] == "record" and "--json-input" in c]
        self.assertEqual(payloads[0], payloads[1])
        parked.assert_called_once_with(self.config, json.loads(json.loads(payloads[0])["details_json"]))
        self.assertEqual(sum(c[0][0]=="codex" for c in self.calls), 1)

    def test_failed_parking_does_not_release_or_record_a_completed_result(self):
        self.reply = result("approve_deploy")
        with patch.object(repair, "park_repair", side_effect=RuntimeError("Keep existing changes")):
            with self.assertRaisesRegex(RuntimeError, "Keep existing changes"):
                self.invoke()
        self.assertEqual(self.releases, [False])
        self.assertTrue((self.root/"active.json").exists())
        self.assertFalse(any("--json-input" in c for c,k in self.calls))
        self.invoke()
        self.assertEqual(sum(c[0][0]=="codex" for c in self.calls), 1)

    def test_human_handled_claim_never_starts_or_overwrites(self):
        self.case["processing_status"] = "succeeded"
        with self.assertRaisesRegex(RuntimeError, "ownership"):
            self.invoke()
        self.assertFalse(any(c[0] == "codex" or "--json-input" in c for c,k in self.calls))

    def test_interrupted_execution_never_restarts_repair(self):
        ordinary = self.command
        def interrupted(command, **kwargs):
            if command[0]=="codex":
                self.calls.append((command, kwargs))
                raise TimeoutError("deadline")
            return ordinary(command, **kwargs)
        self.command = interrupted
        with self.assertRaises(TimeoutError):
            self.invoke()
        with self.assertRaisesRegex(RuntimeError, "Previous execution"):
            self.invoke()
        self.assertEqual(sum(c[0][0]=="codex" for c in self.calls), 1)
        self.assertTrue((self.root/"active.json").exists())
        self.assertTrue(all(not release for release in self.releases))
        payloads = [k["payload"] for c,k in self.calls if c[0] == "record" and "--json-input" in c]
        self.assertEqual(payloads[0], payloads[1])

    def test_bad_output_gets_one_format_correction_only(self):
        ordinary = self.command
        def first_bad(command, **kwargs):
            if command[0]=="codex" and "resume" not in command:
                valid = self.reply
                self.reply = {"missing": "contract"}
                answer = ordinary(command, **kwargs)
                self.reply = valid
                return answer
            return ordinary(command, **kwargs)
        self.command = first_bad
        self.invoke()
        codex = [c for c,k in self.calls if c[0]=="codex"]
        self.assertEqual(len(codex), 2)
        self.assertIn("resume", codex[1])
        self.assertIn('sandbox_mode="read-only"', codex[1])

    def test_second_bad_output_is_not_silently_accepted(self):
        self.reply = {"invalid": "output"}
        with self.assertRaises(ValueError):
            self.invoke()
        with self.assertRaisesRegex(RuntimeError, "Previous execution"):
            self.invoke()
        self.assertEqual(sum(c[0][0]=="codex" for c in self.calls), 2)

    def test_remote_reservation_retained_and_released_on_same_run_only(self):
        self.config["code_ssh"] = ["bash", "-c"]
        self.config["debug_root"] = str(self.root)
        run_id = str(uuid.uuid4())
        with repair.workspace_lock(self.config, run_id):
            with self.assertRaises(RuntimeError):
                with repair.workspace_lock(self.config, str(uuid.uuid4())):
                    self.fail("Concurrent writer acquired workspace")
        reservation = self.root / "runtime" / "operational-repair.json"
        self.assertEqual(json.loads(reservation.read_text())["run_id"], run_id)
        with repair.workspace_lock(self.config, run_id) as release:
            release.append(True)
        self.assertFalse(reservation.exists())

    def test_failed_remote_release_is_not_reported_as_success(self):
        self.config["code_ssh"] = ["bash", "-c"]
        self.config["debug_root"] = str(self.root)
        with self.assertRaises(RuntimeError):
            with repair.workspace_lock(self.config, str(uuid.uuid4())) as release:
                (self.root / "runtime" / "operational-repair.json").unlink()
                release.append(True)

    def test_unclassified_cannot_be_closed(self):
        value = result()
        value["next_action"]="none"
        value["details"]["outcome_verification"]="invented"
        with self.assertRaises(ValueError):
            repair.validate_result(value)

    def test_approval_needs_reviewable_details(self):
        value = result("approve_deploy")
        value["details"]["verification"]=""
        with self.assertRaises(ValueError):
            repair.validate_result(value)

    def test_existing_broad_main_user_is_rejected(self):
        import os
        import pwd
        self.config["restricted_user"]="different-from-"+pwd.getpwuid(os.getuid()).pw_name
        with self.assertRaisesRegex(RuntimeError, "restricted main-server account"):
            repair.preflight(self.config)


class GitParkingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.prod, self.debug = self.root/"prod", self.root/"debug"
        self.prod.mkdir()
        self.git(self.prod, "init", "-b", "main")
        self.git(self.prod, "config", "user.name", "Repair test")
        self.git(self.prod, "config", "user.email", "repair@example.invalid")
        self.git(self.prod, "config", "core.hooksPath", "/dev/null")
        (self.prod/".gitignore").write_text("runtime/\n")
        (self.prod/"example.txt").write_text("original\n")
        self.git(self.prod, "add", ".")
        self.git(self.prod, "commit", "-m", "Baseline")
        self.base = self.git(self.prod, "rev-parse", "HEAD")
        self.git(self.prod, "worktree", "add", "--detach", str(self.debug), self.base)
        self.config = {"code_ssh": ["bash", "-c"], "debug_root": str(self.debug),
                       "production_root": str(self.prod), "record_command": ["record"],
                       "codex_command": ["codex"], "project_root": str(self.root)}

    def git(self, root, *args):
        return subprocess.run(["git", "-C", str(root), *args], check=True, text=True,
                              capture_output=True).stdout.strip()

    def repair_commit(self, name):
        (self.debug/name).write_text(name)
        self.git(self.debug, "add", name)
        self.git(self.debug, "commit", "-m", name)
        return {"base_commit": self.base, "commit": self.git(self.debug, "rev-parse", "HEAD"),
                "repair_ref": "refs/operational-repairs/"+str(uuid.uuid4())}

    def test_park_preserves_commit_and_is_safe_to_replay(self):
        details = self.repair_commit("case-a.txt")
        # A stopped attempt may already have pinned the commit before switching.
        self.git(self.debug, "update-ref", details["repair_ref"], details["commit"])
        repair.park_repair(self.config, details)
        repair.park_repair(self.config, details)
        self.assertEqual(self.git(self.debug, "rev-parse", "HEAD"), self.base)
        self.assertEqual(self.git(self.debug, "rev-parse", details["repair_ref"]), details["commit"])
        self.assertEqual(self.git(self.debug, "show", details["repair_ref"]+":case-a.txt"), "case-a.txt")
        self.assertEqual(self.git(self.prod, "rev-parse", "HEAD"), self.base)

    def test_dirty_workspace_is_preserved(self):
        details = self.repair_commit("case-a.txt")
        (self.debug/"example.txt").write_text("Another writer's change")
        with self.assertRaises(RuntimeError):
            repair.park_repair(self.config, details)
        self.assertEqual((self.debug/"example.txt").read_text(), "Another writer's change")
        self.assertEqual(self.git(self.debug, "rev-parse", "HEAD"), details["commit"])
        self.assertEqual(self.git(self.debug, "for-each-ref", details["repair_ref"]), "")

    def test_unrelated_commit_is_preserved(self):
        details = self.repair_commit("case-a.txt")
        other = self.repair_commit("other-work.txt")
        with self.assertRaises(RuntimeError):
            repair.park_repair(self.config, details)
        self.assertEqual(self.git(self.debug, "rev-parse", "HEAD"), other["commit"])
        self.assertEqual(self.git(self.debug, "for-each-ref", details["repair_ref"]), "")

    def test_conflicting_reference_is_not_overwritten(self):
        details = self.repair_commit("case-a.txt")
        self.git(self.debug, "update-ref", details["repair_ref"], self.base)
        with self.assertRaises(RuntimeError):
            repair.park_repair(self.config, details)
        self.assertEqual(self.git(self.debug, "rev-parse", details["repair_ref"]), self.base)
        self.assertEqual(self.git(self.debug, "rev-parse", "HEAD"), details["commit"])

    def test_changed_production_requires_reconciliation(self):
        details = self.repair_commit("case-a.txt")
        self.git(self.prod, "commit", "--allow-empty", "-m", "New production version")
        with self.assertRaises(RuntimeError):
            repair.park_repair(self.config, details)
        self.assertEqual(self.git(self.debug, "rev-parse", "HEAD"), details["commit"])
        self.assertEqual(self.git(self.debug, "for-each-ref", details["repair_ref"]), "")

    def test_two_pending_approvals_allow_two_independent_repairs(self):
        recorded, codex_runs = [], []
        original_command = repair.run_command
        case = None
        name = None

        def preflight(config):
            self.assertEqual(self.git(self.debug, "status", "--porcelain"), "")
            self.assertEqual(self.git(self.debug, "rev-parse", "HEAD"), self.base)
            return {"head": self.base}

        def command(command, **kwargs):
            if command[0] == "record":
                if "--claim-next" in command:
                    case["handling_context"] = {"automation_run": command[-1], "workspace_reserved": "yes"}
                    return json.dumps(case)
                if "--read" in command:
                    return json.dumps(case)
                payload = json.loads(kwargs["payload"])
                recorded.append(payload)
                return json.dumps({**case, "next_action": payload["next_action"]})
            if command[0] == "codex":
                codex_runs.append(name)
                details = self.repair_commit(name)
                value = result("approve_deploy")
                value["details"]["commit"] = details["commit"]
                Path(command[command.index("--output-last-message")+1]).write_text(json.dumps(value))
                events = [{"type": "item.completed", "item": {"id": check, "type": "command_execution",
                           "exit_code": 0, "command": "scripts/debug_workspace.sh "+check}} for check in ("test", "check")]
                kwargs["evidence"].write_text("\n".join(map(json.dumps, events)))
                return ""
            return original_command(command, **kwargs)

        with patch.object(repair, "preflight", side_effect=preflight), \
             patch.object(repair, "run_command", side_effect=command):
            for name in ("case-a.txt", "case-b.txt"):
                case = {"id": str(uuid.uuid4()), "handling_revision": 2, "processing_status": "in_progress"}
                outcome = repair.execute_once(self.config, self.root/"state")
                self.assertEqual(outcome["next_action"], "approve_deploy")
                self.assertFalse((self.root/"state"/"active.json").exists())
                self.assertFalse((self.debug/"runtime"/"operational-repair.json").exists())

        self.assertEqual(codex_runs, ["case-a.txt", "case-b.txt"])
        self.assertEqual(len(recorded), 2)
        for payload in recorded:
            details = json.loads(payload["details_json"])
            self.assertEqual(details["workspace_reserved"], "no")
            self.assertEqual(self.git(self.debug, "rev-parse", details["repair_ref"]), details["commit"])
            self.assertEqual(self.git(self.debug, "rev-parse", details["commit"]+"^"), self.base)
        self.assertEqual(self.git(self.debug, "rev-parse", "HEAD"), self.base)
        self.assertEqual(self.git(self.prod, "rev-parse", "HEAD"), self.base)


if __name__ == "__main__":
    unittest.main()
