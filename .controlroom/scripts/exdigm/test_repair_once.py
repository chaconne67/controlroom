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
    details["test_targets"] = []
    details.update(owner="owner", required_action="Provide missing evidence", resume_condition="Evidence received")
    if action == "approve_deploy":
        details.update(root_cause="Reproduced defect", commit="b"*40,
                       verification="Focused tests and check passed", rollback="Deploy approved prior commit",
                       test_targets=["tests/test_repair.py::test_regression"])
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
        self.verification_ok = True
        self.verification_calls = []

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
            kwargs["evidence"].write_text("\n".join(json.dumps(event) for event in events))
        return ""

    def verify(self, config, directory, commit, test_targets):
        self.verification_calls.append((commit, test_targets))
        if not self.verification_ok:
            raise RuntimeError("Official test command failed")
        return {
            check: {
                "command": f"scripts/debug_workspace.sh {check}",
                "exit_code": 0,
                "evidence": str(directory/f"official-{check}.log"),
            }
            for check in ("test", "check")
        }

    def invoke(self):
        with patch.object(repair, "preflight", return_value={"head": "a"*40}), \
             patch.object(repair, "workspace_lock", self.lease), \
             patch.object(repair, "run_command", side_effect=self.command), \
             patch.object(repair, "run_official_verification", side_effect=self.verify), \
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
        self.assertEqual(self.verification_calls, [("b"*40, ["tests/test_repair.py::test_regression"])])
        recorded = next(json.loads(k["payload"]) for c,k in self.calls
                        if c[0] == "record" and "--json-input" in c)
        self.assertEqual(
            json.loads(json.loads(recorded["details_json"])["test_targets"]),
            ["tests/test_repair.py::test_regression"],
        )

    def test_failed_runner_owned_verification_is_rejected(self):
        self.reply = result("approve_deploy")
        self.verification_ok = False
        with self.assertRaisesRegex(RuntimeError, "Official test command failed"):
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
             patch.object(repair, "run_official_verification", side_effect=self.verify), \
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

    def test_initial_codex_run_uses_os_account_as_the_external_sandbox(self):
        self.invoke()
        codex = next(c for c,k in self.calls if c[0] == "codex")
        self.assertIn("danger-full-access", codex)
        self.assertNotIn("sandbox_workspace_write.network_access=true", codex)

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

    def test_deployment_needs_safe_focused_test_targets(self):
        value = result("approve_deploy")
        for targets in ([], ["../test_secret.py"], ["manage.py"], ["-k expression"],
                        ["tests/test_ok.py\n--collect-only"]):
            value["details"]["test_targets"] = targets
            with self.subTest(targets=targets), self.assertRaises(ValueError):
                repair.validate_result(value)

    def test_non_deployment_cannot_smuggle_test_targets(self):
        value = result("user_action")
        value["details"]["test_targets"] = ["tests/test_ok.py"]
        with self.assertRaises(ValueError):
            repair.validate_result(value)

    def test_existing_broad_main_user_is_rejected(self):
        import os
        import pwd
        self.config["restricted_user"]="different-from-"+pwd.getpwuid(os.getuid()).pw_name
        with self.assertRaisesRegex(RuntimeError, "restricted main-server account"):
            repair.preflight(self.config)

    def test_preflight_rejects_each_runtime_access_mode(self):
        import io
        import os
        import pwd
        import shlex
        from contextlib import redirect_stdout
        self.config["restricted_user"] = pwd.getpwuid(os.getuid()).pw_name
        self.config["protected_runtime_paths"] = ["/private-runtime"]

        def execute_remote(config, command):
            argv = shlex.split(command)
            def output(command, **kwargs):
                if command[0] == "id":
                    return "repair-test-user\n"
                if "--git-common-dir" in command:
                    return command[2] + "/.git"
                return "" if "status" in command else "a" * 40
            capture = io.StringIO()
            with patch("sys.argv", argv[2:]), redirect_stdout(capture), \
                 patch("subprocess.check_output", side_effect=output), \
                 patch("subprocess.run", return_value=subprocess.CompletedProcess([], 1)), \
                 patch("pathlib.Path.is_dir", return_value=True):
                exec(argv[2], {})
            return capture.getvalue()

        for mode in (os.R_OK, os.W_OK, os.X_OK, 0):
            with self.subTest(mode=mode), patch("os.getuid", return_value=os.getuid()), \
                 patch("os.access", side_effect=lambda path, requested: str(path) == "/private-runtime" and requested == mode), \
                 patch.object(repair, "remote", side_effect=execute_remote):
                if mode:
                    with self.assertRaisesRegex(SystemExit, "protected runtime data"):
                        repair.preflight(self.config)
                else:
                    self.assertEqual(repair.preflight(self.config), {"head": "a" * 40})

    def test_preflight_rejects_shared_or_writable_git_objects(self):
        import io
        import os
        import pwd
        import shlex
        from contextlib import redirect_stdout
        self.config["restricted_user"] = pwd.getpwuid(os.getuid()).pw_name
        self.config["protected_runtime_paths"] = ["/private-runtime"]

        for scenario in ("shared", "writable", "isolated"):
            def execute_remote(config, command):
                argv = shlex.split(command)
                def output(command, **kwargs):
                    if command[0] == "id":
                        return "repair-test-user\n"
                    if "--git-common-dir" in command:
                        return "/prod/.git" if scenario == "shared" else command[2] + "/.git"
                    return "" if "status" in command else "a" * 40
                capture = io.StringIO()
                with patch("sys.argv", argv[2:]), redirect_stdout(capture), \
                     patch("subprocess.check_output", side_effect=output), \
                     patch("subprocess.run", return_value=subprocess.CompletedProcess([], 1)), \
                     patch("pathlib.Path.is_dir", return_value=True), \
                     patch("pathlib.Path.rglob", return_value=iter([Path("/prod/.git/objects/aa/blob")])):
                    exec(argv[2], {})
                return capture.getvalue()
            with self.subTest(scenario=scenario), \
                 patch("os.access", side_effect=lambda path, mode: scenario == "writable" and str(path) == "/prod/.git/objects/aa/blob" and mode == os.W_OK), \
                 patch.object(repair, "remote", side_effect=execute_remote):
                if scenario == "shared":
                    with self.assertRaisesRegex(SystemExit, "independent Git"):
                        repair.preflight(self.config)
                elif scenario == "writable":
                    with self.assertRaisesRegex(SystemExit, "production Git objects"):
                        repair.preflight(self.config)
                else:
                    self.assertEqual(repair.preflight(self.config), {"head": "a" * 40})

    def test_preflight_requires_explicit_runtime_boundary(self):
        import os
        import pwd
        self.config["restricted_user"] = pwd.getpwuid(os.getuid()).pw_name
        for paths in (None, [], ["relative"], [None], "/private-runtime"):
            self.config["protected_runtime_paths"] = paths
            with self.subTest(paths=paths), self.assertRaisesRegex(RuntimeError, "protection paths"):
                repair.preflight(self.config)


class OfficialVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.debug = self.root / "debug"
        scripts = self.debug / "scripts"
        scripts.mkdir(parents=True)
        verifier = scripts / "debug_workspace.sh"
        verifier.write_text(
            "#!/bin/sh\n"
            "printf '%s\\n' \"$*\" >> verification.calls\n"
            "printf '%s output\\n' \"$1\"\n"
            "test ! -f \"fail-$1\"\n",
            encoding="utf-8",
        )
        verifier.chmod(0o755)
        tests = self.debug / "tests"
        tests.mkdir()
        (tests / "test_repair.py").write_text("def test_regression(): pass\n")
        subprocess.run(["git", "-C", str(self.debug), "init"], check=True,
                       stdout=subprocess.DEVNULL)
        subprocess.run(["git", "-C", str(self.debug), "add", "scripts/debug_workspace.sh", "tests/test_repair.py"],
                       check=True)
        self.state = self.root / "state"
        self.state.mkdir()
        self.config = {
            "code_ssh": ["bash", "-c"],
            "debug_root": str(self.debug),
        }
        self.commit = "b" * 40
        self.targets = ["tests/test_repair.py::test_regression"]

    def test_runner_executes_each_official_check_once_and_reuses_receipt(self):
        expected = repair.run_official_verification(
            self.config, self.state, self.commit, self.targets
        )
        replayed = repair.run_official_verification(
            self.config, self.state, self.commit, self.targets
        )

        self.assertEqual(replayed, expected)
        self.assertEqual(
            (self.debug / "verification.calls").read_text().splitlines(),
            ["test tests/test_repair.py::test_regression", "check"],
        )
        self.assertIn("test output", (self.state / "official-test.log").read_text())
        self.assertIn("check output", (self.state / "official-check.log").read_text())
        receipt = json.loads(
            (self.state / "official-verification.json").read_text()
        )
        self.assertEqual(receipt["commit"], self.commit)
        self.assertEqual(receipt["test_targets"], self.targets)
        self.assertEqual(set(receipt["checks"]), {"test", "check"})

    def test_failed_check_is_not_receipted_as_success(self):
        (self.debug / "fail-check").touch()

        with self.assertRaisesRegex(RuntimeError, "status 1"):
            repair.run_official_verification(self.config, self.state, self.commit, self.targets)

        receipt = json.loads(
            (self.state / "official-verification.json").read_text()
        )
        self.assertEqual(set(receipt["checks"]), {"test"})
        self.assertIn("check output", (self.state / "official-check.log").read_text())

    def test_receipt_cannot_be_reused_for_another_commit(self):
        repair.run_official_verification(self.config, self.state, self.commit, self.targets)

        with self.assertRaisesRegex(RuntimeError, "does not match"):
            repair.run_official_verification(
                self.config, self.state, "c" * 40, self.targets
            )

    def test_receipt_cannot_be_reused_for_different_targets(self):
        repair.run_official_verification(self.config, self.state, self.commit, self.targets)
        with self.assertRaisesRegex(RuntimeError, "does not match"):
            repair.run_official_verification(
                self.config, self.state, self.commit,
                ["tests/test_repair.py"],
            )

    def test_untracked_or_escaping_target_is_rejected_before_pytest(self):
        (self.debug / "tests" / "test_untracked.py").write_text("def test_x(): pass\n")
        for target in ("tests/test_untracked.py", "../tests/test_repair.py"):
            state = self.state / target.replace("/", "_")
            state.mkdir()
            with self.subTest(target=target), self.assertRaises((RuntimeError, ValueError)):
                repair.run_official_verification(
                    self.config, state, self.commit, [target]
                )


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
                kwargs["evidence"].write_text("")
                return ""
            return original_command(command, **kwargs)

        verified = []
        def verification(config, directory, commit, test_targets):
            verified.append((commit, test_targets))
            return {check: {"command": "scripts/debug_workspace.sh "+check,
                            "exit_code": 0, "evidence": str(directory/("official-"+check+".log"))}
                    for check in ("test", "check")}

        with patch.object(repair, "preflight", side_effect=preflight), \
             patch.object(repair, "run_command", side_effect=command), \
             patch.object(repair, "run_official_verification", side_effect=verification):
            for name in ("case-a.txt", "case-b.txt"):
                case = {"id": str(uuid.uuid4()), "handling_revision": 2, "processing_status": "in_progress"}
                outcome = repair.execute_once(self.config, self.root/"state")
                self.assertEqual(outcome["next_action"], "approve_deploy")
                self.assertFalse((self.root/"state"/"active.json").exists())
                self.assertFalse((self.debug/"runtime"/"operational-repair.json").exists())

        self.assertEqual(codex_runs, ["case-a.txt", "case-b.txt"])
        self.assertEqual(len(verified), 2)
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
