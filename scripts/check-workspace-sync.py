#!/usr/bin/env python3
"""Exercise the installed sync entrypoints against two real Git workspaces."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("kit_sync_checks", ROOT / "scripts/check-kit-sync.py")
assert spec and spec.loader
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)
run = checks.run


class WorkspaceSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = checks.KitFixture()
        self.addCleanup(self.fixture.close)
        self.remotes: dict[str, Path] = {}
        for name, text in (("control-room-docs", "first next step\n"), ("venture", "print('initial')\n")):
            seed = self.fixture.root / (name + "-seed")
            remote = self.fixture.root / (name + ".git")
            run("git", "init", "--initial-branch=main", seed)
            self.fixture._configure(seed)
            filename = "plan.md" if name == "control-room-docs" else "app.py"
            (seed / filename).write_text(text, encoding="utf-8")
            (seed / ".gitattributes").write_text("* -text\n", encoding="utf-8")
            if name == "control-room-docs":
                (seed / ".gitignore").write_text(".env*\n*.pem\n", encoding="utf-8")
            run("git", "add", "-A", cwd=seed)
            run("git", "commit", "-m", "initial", cwd=seed)
            run("git", "clone", "--bare", seed, remote)
            self.remotes[name] = remote
        manifest = self.fixture.seed / "manifests/windows-control-projects.tsv"
        manifest.parent.mkdir(exist_ok=True)
        manifest.write_text(
            "# directory\tkind\ttarget\n"
            "_control-docs\tdocs\thttps://github.com/chaconne67/control-room-docs.git\n"
            "venture\tgit\thttps://github.com/chaconne67/venture.git\n",
            encoding="utf-8",
        )
        # Link-installation behavior is covered by the real installer checks.
        # This fixture keeps the actual shared Git restore and synchronization functions.
        (self.fixture.seed / "install.sh").write_text(
            '#!/usr/bin/env bash\nset -euo pipefail\n'
            'kit="$(cd "$(dirname "$0")" && pwd)"\n'
            '. "$kit/shell/kit-aliases.sh"\n'
            '_kit_restore_control_repositories "$kit" "$HOME"\n'
            '[ -f "$HOME/projects/_control-docs/plan.md" ] || { echo "missing planning source" >&2; exit 1; }\n'
            'printf "%s\\n" "$1" >> "$HOME/install.log"\n',
            encoding="utf-8",
        )
        (self.fixture.seed / "install.sh").chmod(0o755)
        run("git", "add", "-A", cwd=self.fixture.seed)
        run("git", "commit", "-m", "workspace manifest", cwd=self.fixture.seed)
        run("git", "push", cwd=self.fixture.seed)

    def env(self, home: Path) -> dict[str, str]:
        env = dict(os.environ, HOME=str(home), GIT_TERMINAL_PROMPT="0",
                   GIT_CONFIG_COUNT=str(len(self.remotes)), GIT_ALLOW_PROTOCOL="file")
        for i, (name, remote) in enumerate(self.remotes.items()):
            env[f"GIT_CONFIG_KEY_{i}"] = f"url.{remote.as_uri()}.insteadOf"
            env[f"GIT_CONFIG_VALUE_{i}"] = f"https://github.com/chaconne67/{name}.git"
        return env

    def command(self, home: Path, command: str, *, check: bool = True) -> subprocess.CompletedProcess[str]:
        return run(
            checks.BASH, "--noprofile", "--norc", "-c",
            '. "$HOME/kmh-agent-kit/shell/kit-aliases.sh"; ' + command,
            env=self.env(home), check=check,
        )

    def device(self, *, spaces: bool = False) -> tuple[Path, Path]:
        home, kit = self.fixture.clone("windows-control")
        if spaces:
            new_home = home.with_name(home.name + " Korean 조정실")
            home.rename(new_home)
            home, kit = new_home, new_home / "kmh-agent-kit"
        self.command(home, "kitpull")
        for directory in ("_control-docs", "venture"):
            self.fixture._configure(home / "projects" / directory)
        return home, kit

    def commit_code(self, home: Path, content: str) -> str:
        repo = home / "projects/venture"
        (repo / "app.py").write_text(content, encoding="utf-8")
        run("git", "add", "app.py", cwd=repo)
        run("git", "commit", "-m", "project change", cwd=repo)
        return run("git", "rev-parse", "HEAD", cwd=repo).stdout.strip()

    def test_two_devices_round_trip_kit_plan_and_committed_project(self) -> None:
        a, kit_a = self.device(spaces=True)
        b, kit_b = self.device()
        (kit_a / "common.txt").write_text("portable rules\n", encoding="utf-8")
        plan_a = a / "projects/_control-docs/plan.md"
        plan_a.write_bytes("## 재개 정보\r\n다음: 다음 단계의 검증\n".encode())
        first_code = self.commit_code(a, "print('from A')\n")
        self.command(a, 'kitpush "device A checkpoint"')
        self.command(b, "kitpull")
        self.assertEqual((kit_b / "common.txt").read_text(), "portable rules\n")
        self.assertEqual((b / "projects/_control-docs/plan.md").read_bytes(), plan_a.read_bytes())
        self.assertEqual(run("git", "rev-parse", "HEAD", cwd=b / "projects/venture").stdout.strip(), first_code)
        (b / "projects/_control-docs/plan.md").write_text("verified by B; next: review\n", encoding="utf-8")
        second_code = self.commit_code(b, "print('from B')\n")
        self.command(b, 'kitpush "device B checkpoint"')
        self.command(a, "kitpull")
        self.assertEqual(plan_a.read_text(), "verified by B; next: review\n")
        self.assertEqual(run("git", "rev-parse", "HEAD", cwd=a / "projects/venture").stdout.strip(), second_code)
        for home in (a, b):
            for directory in ("kmh-agent-kit", "projects/_control-docs", "projects/venture"):
                self.assertEqual(run("git", "status", "--porcelain", cwd=home / directory).stdout, "")

    def test_dirty_code_is_not_staged_and_independent_documents_are_saved(self) -> None:
        home, _ = self.device()
        venture = home / "projects/venture"
        baseline = run("git", "rev-parse", "HEAD", cwd=venture).stdout.strip()
        (venture / "app.py").write_text("unfinished code\n", encoding="utf-8")
        (venture / "private.txt").write_text("synthetic untracked work\n", encoding="utf-8")
        run("git", "add", "app.py", cwd=venture)
        staged = run("git", "diff", "--cached", "--binary", cwd=venture).stdout
        (home / "projects/_control-docs/plan.md").write_text("resume still saved\n", encoding="utf-8")
        (home / "projects/_control-docs/.env").write_text("SYNTHETIC_TEST_VALUE=placeholder\n", encoding="utf-8")
        result = self.command(home, "kitpush", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("미커밋", result.stderr)
        self.assertEqual(run("git", "diff", "--cached", "--binary", cwd=venture).stdout, staged)
        self.assertEqual(run("git", "rev-parse", "HEAD", cwd=venture).stdout.strip(), baseline)
        self.assertEqual((venture / "private.txt").read_text(), "synthetic untracked work\n")
        self.assertEqual(run("git", "--git-dir", self.remotes["control-room-docs"], "show", "main:plan.md").stdout, "resume still saved\n")
        self.assertNotIn(".env", run("git", "--git-dir", self.remotes["control-room-docs"], "ls-tree", "--name-only", "main").stdout.splitlines())

    def test_dirty_documents_are_preserved_while_clean_code_can_be_pulled(self) -> None:
        a, _ = self.device()
        b, _ = self.device()
        expected = self.commit_code(b, "print('new remote')\n")
        self.command(b, "kitpush")
        plan = a / "projects/_control-docs/plan.md"
        plan.write_text("local unfinished plan\n", encoding="utf-8")
        result = self.command(a, "kitpull", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(plan.read_text(), "local unfinished plan\n")
        self.assertEqual(run("git", "rev-parse", "HEAD", cwd=a / "projects/venture").stdout.strip(), expected)

    def test_document_conflict_aborts_and_keeps_both_commits(self) -> None:
        a, _ = self.device()
        b, _ = self.device()
        (a / "projects/_control-docs/plan.md").write_text("A decision\n", encoding="utf-8")
        self.command(a, "kitpush")
        repo_b = b / "projects/_control-docs"
        (repo_b / "plan.md").write_text("B decision\n", encoding="utf-8")
        result = self.command(b, "kitpush", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((repo_b / "plan.md").read_text(), "B decision\n")
        self.assertEqual(run("git", "status", "--porcelain", cwd=repo_b).stdout, "")
        self.assertEqual(run("git", "rev-list", "--left-right", "--count", "HEAD...origin/main", cwd=repo_b).stdout.strip(), "1\t1")
        self.assertEqual(run("git", "--git-dir", self.remotes["control-room-docs"], "show", "main:plan.md").stdout, "A decision\n")

    def test_wrong_origin_is_rejected_before_any_document_push(self) -> None:
        home, _ = self.device()
        repo = home / "projects/_control-docs"
        run("git", "remote", "set-url", "origin", "https://github.com/unrelated/not-authorized.git", cwd=repo)
        (repo / "plan.md").write_text("do not upload\n", encoding="utf-8")
        result = self.command(home, "kitpush", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("origin", result.stderr)
        self.assertEqual((repo / "plan.md").read_text(), "do not upload\n")
        self.assertEqual(run("git", "--git-dir", self.remotes["control-room-docs"], "show", "main:plan.md").stdout, "first next step\n")

    def test_updated_documents_are_checked_by_final_installer(self) -> None:
        home, _ = self.device()
        seed = self.fixture.root / "control-room-docs-seed"
        run("git", "rm", "plan.md", cwd=seed)
        run("git", "commit", "-m", "remove required source", cwd=seed)
        run("git", "push", self.remotes["control-room-docs"], "main", cwd=seed)
        result = self.command(home, "kitpull", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing planning source", result.stderr)
        self.assertFalse((home / "projects/_control-docs/plan.md").exists())

    def test_separate_push_destination_is_rejected(self) -> None:
        home, _ = self.device()
        unintended = self.fixture.root / "unintended.git"
        run("git", "init", "--bare", "--initial-branch=main", unintended)
        self.remotes["unintended"] = unintended
        repo = home / "projects/_control-docs"
        run("git", "config", "remote.origin.pushurl",
            "https://github.com/chaconne67/unintended.git", cwd=repo)
        (repo / "plan.md").write_text("keep within the registered repository\n", encoding="utf-8")
        result = self.command(home, "kitpush", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("push", result.stderr)
        self.assertEqual(run("git", "--git-dir", unintended, "show-ref", check=False).stdout, "")

    def test_unavailable_document_remote_does_not_stop_committed_code(self) -> None:
        home, _ = self.device()
        expected = self.commit_code(home, "print('independent save')\n")
        (home / "projects/_control-docs/plan.md").write_text("preserve while offline\n", encoding="utf-8")
        self.remotes["control-room-docs"] = self.fixture.root / "unavailable.git"
        result = self.command(home, "kitpush", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((home / "projects/_control-docs/plan.md").read_text(), "preserve while offline\n")
        self.assertEqual(run("git", "--git-dir", self.remotes["venture"], "rev-parse", "main").stdout.strip(), expected)

    def test_other_document_branch_is_preserved(self) -> None:
        home, _ = self.device()
        repo = home / "projects/_control-docs"
        run("git", "checkout", "-b", "ongoing-plan", cwd=repo)
        result = self.command(home, "kitpull", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(run("git", "branch", "--show-current", cwd=repo).stdout.strip(), "ongoing-plan")


if __name__ == "__main__":
    unittest.main(verbosity=2)
