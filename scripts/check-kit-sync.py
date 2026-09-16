#!/usr/bin/env python3
"""Disposable Git integration checks for kitpull and kitpush."""

from __future__ import annotations

from contextlib import contextmanager
import os
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
ALIASES = ROOT / "shell" / "kit-aliases.sh"


def find_bash() -> str:
    found = shutil.which("bash")
    if found:
        return found
    if os.name == "nt":
        git = shutil.which("git")
        if git:
            candidate = Path(git).resolve().parents[1] / "bin" / "bash.exe"
            if candidate.is_file():
                return str(candidate)
    return "bash"


BASH = find_bash()


def run(
    *args: str | Path,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [str(arg) for arg in args],
        cwd=cwd,
        env=env,
        input=input_text,
        text=True,
        errors="backslashreplace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and result.returncode:
        raise AssertionError(
            f"command failed ({result.returncode}): {' '.join(map(str, args))}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


@contextmanager
def preserve_windows_installer_path(home: Path):
    """Remove only installer PATH entries absent before this temporary install."""
    import winreg

    def normalized(entry: str) -> str:
        return os.path.normcase(entry.rstrip("\\/"))

    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE
    ) as key:
        try:
            before, _ = winreg.QueryValueEx(key, "Path")
            existed = True
        except FileNotFoundError:
            before, existed = "", False
        git = shutil.which("git.exe") or shutil.which("git")
        if not git:
            raise AssertionError("Windows installer test requires Git")
        candidates = (home / ".local" / "bin", Path(git).parent)
        original = {normalized(entry) for entry in before.split(";")}
        added = {normalized(str(entry)) for entry in candidates} - original
        try:
            yield
        finally:
            try:
                current, value_type = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                current, value_type = "", winreg.REG_EXPAND_SZ
            entries = current.split(";")
            kept = [entry for entry in entries if normalized(entry) not in added]
            if kept != entries:
                restored = ";".join(kept)
                if not existed and not restored:
                    winreg.DeleteValue(key, "Path")
                else:
                    winreg.SetValueEx(key, "Path", 0, value_type, restored)


class KitFixture:
    def __init__(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="kmh-agent-kit-sync-")
        self.root = Path(self.temp.name)
        self.remote = self.root / "origin.git"
        self.seed = self.root / "seed"
        self.clone_count = 0
        run("git", "init", "--bare", "--initial-branch=main", self.remote)
        run("git", "init", "--initial-branch=main", self.seed)
        self._configure(self.seed)
        self._write_baseline()
        run("git", "add", "-A", cwd=self.seed)
        run("git", "commit", "-m", "baseline", cwd=self.seed)
        run("git", "remote", "add", "origin", self.remote, cwd=self.seed)
        run("git", "push", "-u", "origin", "main", cwd=self.seed)

    def close(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def _configure(repo: Path) -> None:
        run("git", "config", "user.name", "Kit Test", cwd=repo)
        run("git", "config", "user.email", "kit-test@example.invalid", cwd=repo)

    def _write_baseline(self) -> None:
        paths = {
            "README.md": "baseline\n",
            "common.txt": "base\n",
            "manifests/windows-control-projects.tsv": "# directory\tkind\ttarget\n",
            "gbrain-cards/main.md": "main\n",
            "gbrain-cards/windows-control.md": "windows-control\n",
            "gbrain-cards/rndlog.md": "rndlog\n",
            "projects/ceoloan/AGENTS.md": "ceoloan\n",
            "projects/rndlog/AGENTS.md": "rndlog\n",
        }
        for relative, content in paths.items():
            path = self.seed / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

        shutil.copy2(ROOT / ".gitattributes", self.seed / ".gitattributes")
        aliases = self.seed / "shell" / "kit-aliases.sh"
        aliases.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ALIASES, aliases)
        installer = self.seed / "install.sh"
        installer.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                set -euo pipefail
                git -C "$(cd "$(dirname "$0")" && pwd)" config --local kmh-agent-kit.agent "$1"
                printf '%s\\n' "$1" >> "$HOME/install.log"
                """
            ),
            encoding="utf-8",
        )
        installer.chmod(0o755)

    def clone(self, agent: str = "main") -> tuple[Path, Path]:
        self.clone_count += 1
        home = self.root / f"home-{self.clone_count}"
        repo = home / "kmh-agent-kit"
        home.mkdir()
        run("git", "clone", self.remote, repo)
        self._configure(repo)
        run("git", "remote", "set-url", "origin", "https://github.com/chaconne67/controlroom.git", cwd=repo)
        run("git", "config", f"url.{self.remote.as_uri()}.insteadOf", "https://github.com/chaconne67/controlroom.git", cwd=repo)
        run("git", "config", "--local", "kmh-agent-kit.agent", agent, cwd=repo)
        return home, repo

    def kit(
        self, home: Path, command: str, *, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.update({"HOME": str(home), "GIT_TERMINAL_PROMPT": "0"})
        return run(
            "bash",
            "--noprofile",
            "--norc",
            "-c",
            f'. "$HOME/kmh-agent-kit/shell/kit-aliases.sh"; {command}',
            env=env,
            check=check,
        )


class KitSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = KitFixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def test_pull_repairs_upstream_fast_forwards_and_installs(self) -> None:
        home, repo = self.fixture.clone()
        _, writer = self.fixture.clone()
        run("git", "branch", "--unset-upstream", cwd=repo)
        (writer / "README.md").write_text("remote update\n", encoding="utf-8")
        run("git", "add", "README.md", cwd=writer)
        run("git", "commit", "-m", "remote update", cwd=writer)
        run("git", "push", cwd=writer)

        self.fixture.kit(home, "kitpull")

        self.assertEqual((repo / "README.md").read_text(encoding="utf-8"), "remote update\n")
        upstream = run(
            "git", "rev-parse", "--abbrev-ref", "@{upstream}", cwd=repo
        ).stdout.strip()
        self.assertEqual(upstream, "origin/main")
        self.assertEqual((home / "install.log").read_text(encoding="utf-8"), "main\n")

    def test_standalone_commands_use_same_pull_and_push_paths(self) -> None:
        home, repo = self.fixture.clone()
        command_dir = home / ".local" / "bin"
        command_dir.mkdir(parents=True)
        pull_command = command_dir / "kitpull"
        push_command = command_dir / "kitpush"
        pull_command.symlink_to(repo / "shell" / "kit-aliases.sh")
        push_command.symlink_to(repo / "shell" / "kit-aliases.sh")
        pull_command.chmod(0o755)
        env = os.environ.copy()
        env.update({"HOME": str(home), "GIT_TERMINAL_PROMPT": "0"})

        run(pull_command, env=env)
        (repo / "README.md").write_text("standalone push\n", encoding="utf-8")
        run(push_command, "standalone command", env=env)

        self.assertEqual(
            (home / "install.log").read_text(encoding="utf-8"), "main\n" * 3
        )
        remote_text = run(
            "git", "--git-dir", self.fixture.remote, "show", "main:README.md"
        ).stdout
        self.assertEqual(remote_text, "standalone push\n")

    def test_raw_bash_installer_clones_then_runs_checked_out_installer(self) -> None:
        home = self.fixture.root / "bootstrap-home"
        home.mkdir()
        env = os.environ.copy()
        env.update(
            {
                "HOME": str(home),
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": f"url.file://{self.fixture.remote}.insteadOf",
                "GIT_CONFIG_VALUE_0": "https://github.com/chaconne67/controlroom.git",
                "GIT_TERMINAL_PROMPT": "0",
            }
        )

        run(
            "bash",
            "-s",
            "--",
            "sam",
            cwd=self.fixture.root,
            env=env,
            input_text=(ROOT / "install.sh").read_text(encoding="utf-8"),
        )

        checkout = home / "controlroom"
        self.assertTrue((checkout / ".git").is_dir())
        self.assertEqual((home / "install.log").read_text(encoding="utf-8"), "sam\n")

    def test_git_bash_installer_dispatches_to_powershell_with_agent(self) -> None:
        fake_bin = self.fixture.root / "fake-bin"
        fake_bin.mkdir()
        scripts = {
            "uname": "#!/usr/bin/env bash\nprintf 'MINGW64_NT-10.0\\n'\n",
            "cygpath": "#!/usr/bin/env bash\nprintf '%s\\n' \"${!#}\"\n",
            "powershell.exe": (
                "#!/usr/bin/env bash\n"
                "printf '%s\\0' \"$@\" > \"$HOME/powershell-args\"\n"
            ),
        }
        for name, content in scripts.items():
            path = fake_bin / name
            path.write_text(content, encoding="utf-8")
            path.chmod(0o755)
        home = self.fixture.root / "windows-home"
        home.mkdir()
        env = os.environ.copy()
        env.update({"HOME": str(home), "PATH": f"{fake_bin}:{env['PATH']}"})

        run("bash", ROOT / "install.sh", "gram17", env=env)

        arguments = (home / "powershell-args").read_bytes().rstrip(b"\0").split(b"\0")
        decoded = [argument.decode("utf-8") for argument in arguments]
        self.assertEqual(decoded[-2:], ["-Agent", "gram17"])
        self.assertIn("-File", decoded)
        self.assertIn(str(ROOT / "install.ps1"), decoded)

    def test_posix_installer_adds_global_commands_and_preserves_hermes_skills(self) -> None:
        home = self.fixture.root / "posix-home"
        repo = home / "kmh-agent-kit"
        home.mkdir()
        shutil.copytree(
            ROOT,
            repo,
            symlinks=True,
            ignore=shutil.ignore_patterns(".git", "__pycache__"),
        )
        run("git", "init", "--initial-branch=main", repo)
        fake_bin = self.fixture.root / "darwin-bin"
        fake_bin.mkdir()
        fake_uname = fake_bin / "uname"
        fake_uname.write_text("#!/usr/bin/env bash\nprintf 'Darwin\\n'\n", encoding="utf-8")
        fake_uname.chmod(0o755)

        policy = home / "agent-policy.toml"
        policy.write_text("# test policy\n", encoding="utf-8")
        wrapper = home / ".local" / "bin" / "gbrain-sam"
        wrapper.parent.mkdir(parents=True)
        wrapper.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        wrapper.chmod(0o755)
        personal_skill = home / ".hermes" / "skills" / "code-review"
        personal_skill.mkdir(parents=True)
        (personal_skill / "PERSONAL.txt").write_text("keep\n", encoding="utf-8")
        legacy_skill = home / ".codex" / "skills" / "preflight" / "SKILL.md"
        legacy_skill.parent.mkdir(parents=True)
        legacy_skill.write_text("legacy preflight\n", encoding="utf-8")
        env = os.environ.copy()
        env.update(
            {
                "HOME": str(home),
                "GBRAIN_POLICY_FILE": str(policy),
                "PATH": f"{fake_bin}:{env['PATH']}",
            }
        )

        run(repo / "install.sh", "sam", env=env)
        backups_after_first_install = set(home.glob(".kmh-agent-kit-backup-*"))
        run(repo / "install.sh", "sam", env=env)
        self.assertEqual(
            set(home.glob(".kmh-agent-kit-backup-*")), backups_after_first_install
        )

        self.assertEqual((personal_skill / "PERSONAL.txt").read_text(), "keep\n")
        self.assertFalse(personal_skill.is_symlink())
        self.assertFalse(legacy_skill.parent.exists())
        legacy_backups = list(
            home.glob(".kmh-agent-kit-backup-*/.codex_skills_preflight/SKILL.md")
        )
        self.assertEqual(len(legacy_backups), 1)
        self.assertEqual(legacy_backups[0].read_text(), "legacy preflight\n")
        self.assertTrue((home / ".agents" / "skills" / "preflight").is_symlink())
        self.assertTrue((home / ".hermes" / "skills" / "code-review-loop").is_symlink())
        self.assertEqual(
            (home / ".local" / "bin" / "kitpull").resolve(),
            (repo / "shell" / "kit-aliases.sh").resolve(),
        )
        self.assertIn('*":$HOME/.local/bin:"*', (home / ".zshrc").read_text())
        self.assertEqual((home / ".zshrc").read_text().count("kmh-agent-kit command path"), 1)
        self.assertIn(
            '*":$HOME/.local/bin:"*',
            (home / ".bash_profile").read_text(),
        )
        saved = run(
            "git", "config", "--local", "--get", "kmh-agent-kit.agent", cwd=repo
        ).stdout.strip()
        self.assertEqual(saved, "sam")

    def test_pull_and_push_reject_detached_or_non_main_branch(self) -> None:
        home, repo = self.fixture.clone()
        run("git", "checkout", "--detach", cwd=repo)
        detached = self.fixture.kit(home, "kitpull", check=False)
        self.assertNotEqual(detached.returncode, 0)
        self.assertIn("detached HEAD", detached.stderr)

        run("git", "switch", "-c", "feature", cwd=repo)
        feature = self.fixture.kit(home, "kitpush", check=False)
        self.assertNotEqual(feature.returncode, 0)
        self.assertIn("main 브랜치", feature.stderr)

    def test_pull_rejects_in_progress_git_operation_from_any_directory(self) -> None:
        home, repo = self.fixture.clone()
        merge_head = repo / ".git" / "MERGE_HEAD"
        merge_head.write_text("0" * 40 + "\n", encoding="ascii")

        blocked = self.fixture.kit(home, "kitpull", check=False)

        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("MERGE_HEAD", blocked.stderr)

    def test_non_main_agent_can_push_only_its_domain(self) -> None:
        home, repo = self.fixture.clone("rndlog")
        forbidden = repo / "projects" / "ceoloan" / "AGENTS.md"
        forbidden.write_text("forbidden\n", encoding="utf-8")
        rejected = self.fixture.kit(home, "kitpush", check=False)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("push 범위 밖 변경", rejected.stderr)

        forbidden.write_text("ceoloan\n", encoding="utf-8")
        allowed = repo / "projects" / "rndlog" / "AGENTS.md"
        allowed.write_text("allowed\n", encoding="utf-8")
        self.fixture.kit(home, 'kitpush "rndlog update"')
        remote_text = run(
            "git", "--git-dir", self.fixture.remote, "show", "main:projects/rndlog/AGENTS.md"
        ).stdout
        self.assertEqual(remote_text, "allowed\n")

    def test_main_pushes_all_domains_and_another_clone_pulls(self) -> None:
        home_a, repo_a = self.fixture.clone()
        home_b, repo_b = self.fixture.clone()
        target = repo_a / "projects" / "ceoloan" / "AGENTS.md"
        target.write_text("central update\n", encoding="utf-8")

        self.fixture.kit(home_a, 'kitpush "central update"')
        self.fixture.kit(home_b, "kitpull")

        pulled = repo_b / "projects" / "ceoloan" / "AGENTS.md"
        self.assertEqual(pulled.read_text(encoding="utf-8"), "central update\n")

    def test_windows_control_pushes_all_domains_and_another_clone_pulls(self) -> None:
        home_a, repo_a = self.fixture.clone("windows-control")
        home_b, repo_b = self.fixture.clone()
        paths = [
            "projects/ceoloan/AGENTS.md",
            "projects/exdigm/AGENTS.md",
            "projects/fundkeeper/AGENTS.md",
            "projects/rndlog/AGENTS.md",
            "projects/ziin/AGENTS.md",
            "skills/domains/rndlog/rndlog-design-system/SKILL.md",
            "skills/domains/rndlog/rndlog/SKILL.md",
        ]
        for relative in paths:
            target = repo_a / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("control tower update\n", encoding="utf-8")
        run("git", "add", paths[0], cwd=repo_a)

        self.fixture.kit(home_a, 'kitpush "control tower update"')
        self.fixture.kit(home_b, "kitpull")

        for relative in paths:
            with self.subTest(path=relative):
                self.assertEqual(
                    (repo_b / relative).read_text(encoding="utf-8"),
                    "control tower update\n",
                )
        self.assertEqual(run("git", "status", "--porcelain", cwd=repo_a).stdout, "")
        self.assertEqual(
            (home_a / "install.log").read_text(encoding="utf-8"),
            "windows-control\n" * 2,
        )

    def test_push_rebases_non_conflicting_remote_change(self) -> None:
        home_a, repo_a = self.fixture.clone()
        home_b, repo_b = self.fixture.clone()
        (repo_a / "README.md").write_text("from a\n", encoding="utf-8")
        (repo_b / "common.txt").write_text("from b\n", encoding="utf-8")

        self.fixture.kit(home_a, 'kitpush "change a"')
        self.fixture.kit(home_b, 'kitpush "change b"')

        self.assertEqual(
            run("git", "--git-dir", self.fixture.remote, "show", "main:README.md").stdout,
            "from a\n",
        )
        self.assertEqual(
            run("git", "--git-dir", self.fixture.remote, "show", "main:common.txt").stdout,
            "from b\n",
        )
        merge_commits = run(
            "git", "--git-dir", self.fixture.remote, "rev-list", "--merges", "main"
        ).stdout.strip()
        self.assertEqual(merge_commits, "")

    def test_rebase_conflict_aborts_without_losing_local_commit(self) -> None:
        home_a, repo_a = self.fixture.clone()
        home_b, repo_b = self.fixture.clone()
        (repo_a / "common.txt").write_text("remote\n", encoding="utf-8")
        (repo_b / "common.txt").write_text("local\n", encoding="utf-8")
        self.fixture.kit(home_a, 'kitpush "remote side"')

        conflicted = self.fixture.kit(home_b, 'kitpush "local side"', check=False)

        self.assertNotEqual(conflicted.returncode, 0)
        self.assertIn("로컬 커밋은 보존", conflicted.stderr)
        self.assertEqual((repo_b / "common.txt").read_text(encoding="utf-8"), "local\n")
        self.assertEqual(run("git", "status", "--porcelain", cwd=repo_b).stdout, "")
        self.assertFalse((repo_b / ".git" / "rebase-merge").exists())
        self.assertEqual(
            run("git", "--git-dir", self.fixture.remote, "show", "main:common.txt").stdout,
            "remote\n",
        )


class EntryPointDocumentationTests(unittest.TestCase):
    def test_readme_has_separate_primary_commands_for_each_os(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        onboarding = (ROOT / "docs" / "onboarding-new-server.md").read_text(
            encoding="utf-8"
        )
        command = 'git clone https://github.com/chaconne67/controlroom.git ~/controlroom'
        self.assertIn(command, readme)
        self.assertIn(command, onboarding)
        self.assertIn('controlroom pull', readme)
        self.assertIn('controlroom push', readme)

        manifest = ROOT / "manifests" / "windows-control-projects.tsv"
        rows = [
            line.split("\t")
            for line in manifest.read_text(encoding="utf-8").splitlines()
            if line and not line.startswith("#")
        ]
        self.assertEqual(
            [row[0] for row in rows],
            ["ceoloan", "exdigm", "fundkeeper", "rndlog", "ziin", "venture"],
        )


@unittest.skipUnless(os.name == "nt", "Requires Windows PowerShell and Git Bash")
class WindowsInstallerTests(unittest.TestCase):
    def test_real_windows_installer_help(self) -> None:
        result = run(BASH, ROOT / "install.sh", "--help")
        self.assertIn("최초 설치 또는 재연결", result.stdout)
        self.assertIn("kitpush", result.stdout)

    def test_windows_control_restores_project_entrypoints_and_preserves_existing_work(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kmh-control-room-") as temp_dir, \
                preserve_windows_installer_path(Path(temp_dir) / "home"):
            temp = Path(temp_dir)
            home = temp / "home"
            repo = home / "kmh-agent-kit"
            home.mkdir()
            shutil.copytree(
                ROOT,
                repo,
                symlinks=True,
                ignore=shutil.ignore_patterns(".git", "__pycache__"),
            )
            run("git", "init", "--initial-branch=main", repo)

            # Git for Windows의 기본 core.symlinks=false 체크아웃도 함께 재현한다.
            for profile_entry, target_text in (
                (
                    repo / "codex" / "skills" / "check-master-plan",
                    "../../skills/common/check-master-plan",
                ),
                (
                    repo / "projects" / "ceoloan" / "skills" / "cretop",
                    "../../../skills/domains/ceoloan/cretop",
                ),
            ):
                profile_entry.unlink()
                profile_entry.write_text(target_text, encoding="utf-8")

            preserved = home / "projects" / "rndlog" / "keep.txt"
            preserved.parent.mkdir(parents=True)
            preserved.write_text("keep\n", encoding="utf-8")
            legacy_skill = home / ".codex" / "skills" / "preflight" / "SKILL.md"
            legacy_skill.parent.mkdir(parents=True)
            legacy_skill.write_text("legacy preflight\n", encoding="utf-8")

            # Old Hermes junctions pointed at the profile's relative symlink.
            # Repair kit-owned links, but preserve private and foreign skills.
            import _winapi

            hermes_skills = home / ".hermes" / "skills"
            hermes_skills.mkdir(parents=True)
            managed_skill = hermes_skills / "agent-script-role"
            _winapi.CreateJunction(
                str(repo / "codex" / "skills" / managed_skill.name), str(managed_skill)
            )
            private_skill = hermes_skills / "preflight" / "SKILL.md"
            private_skill.parent.mkdir()
            private_skill.write_text("private skill\n", encoding="utf-8")
            foreign_source = repo / "skills-external" / "smart-ux"
            foreign_source.mkdir(parents=True)
            (foreign_source / "SKILL.md").write_text("foreign skill\n", encoding="utf-8")
            foreign_link = hermes_skills / "smart-ux"
            _winapi.CreateJunction(str(foreign_source), str(foreign_link))

            venture_seed = temp / "venture-seed"
            venture_origin = temp / "venture.git"
            run("git", "init", "--initial-branch=main", venture_seed)
            run("git", "config", "user.name", "Kit Test", cwd=venture_seed)
            run("git", "config", "user.email", "kit-test@example.invalid", cwd=venture_seed)
            (venture_seed / "AGENTS.md").write_text("venture agent\n", encoding="utf-8")
            (venture_seed / "CLAUDE.md").write_text("venture claude\n", encoding="utf-8")
            (venture_seed / ".gitignore").write_text(".agents/\n.claude/\n", encoding="utf-8")
            skill = venture_seed / "skills" / "venture"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("venture skill\n", encoding="utf-8")
            retired_skill = skill.with_name("retired")
            retired_skill.mkdir()
            (retired_skill / "SKILL.md").write_text("retired skill\n", encoding="utf-8")
            run("git", "add", "-A", cwd=venture_seed)
            run("git", "commit", "-m", "venture baseline", cwd=venture_seed)
            run("git", "clone", "--bare", venture_seed, venture_origin)

            profile_names = ("ceoloan", "exdigm", "fundkeeper", "rndlog", "ziin")
            custom_project = temp / "custom projects" / "exdigm"
            custom_project.mkdir(parents=True)
            run("git", "config", "--local", "kmh-agent-kit.project.exdigm",
                custom_project, cwd=repo)

            fake_bin = temp / "bin"
            fake_bin.mkdir()
            (fake_bin / "ssh.cmd").write_text("@echo off\r\nexit /b 0\r\n", encoding="utf-8")
            bash_environment = temp / "bash-environment"
            bash_environment.write_text(
                'export PATH="$(cygpath -u "$TEST_FIXTURE_BIN"):$PATH"\n', encoding="utf-8"
            )
            git_usr_bin = run(BASH, "-c", "cygpath -w /usr/bin").stdout.strip()
            env = os.environ.copy()
            env.update(
                {
                    "USERPROFILE": str(home),
                    "HOME": str(home),
                    "LOCALAPPDATA": str(home / "AppData" / "Local"),
                    "CLAUDE_HOME": str(home / ".claude"),
                    "CODEX_HOME": str(home / ".codex"),
                    "HERMES_HOME": str(home / ".hermes"),
                    "PATH": str(fake_bin) + os.pathsep + git_usr_bin + os.pathsep + env["PATH"],
                    "BASH_ENV": str(bash_environment),
                    "TEST_FIXTURE_BIN": str(fake_bin),
                    "GIT_CONFIG_COUNT": "1",
                    "GIT_CONFIG_KEY_0": f"url.{venture_origin.as_uri()}.insteadOf",
                    "GIT_CONFIG_VALUE_0": "https://github.com/chaconne67/venture.git",
                    "GIT_TERMINAL_PROMPT": "0",
                }
            )
            powershell = shutil.which("powershell.exe") or "powershell.exe"
            command = (
                powershell,
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                repo / "install.ps1",
                "-Agent",
                "windows-control",
            )

            run(*command, env=env)
            for tool_home in (".agents", ".claude"):
                self.assertTrue(os.path.samefile(
                    home / "projects" / "venture" / tool_home / "skills" / "venture",
                    home / "projects" / "venture" / "skills" / "venture",
                ))
            self.assertEqual(
                os.readlink(managed_skill).removeprefix("\\\\?\\"),
                str((repo / "skills" / "common" / managed_skill.name).resolve()),
            )
            self.assertEqual(
                (managed_skill / "SKILL.md").read_bytes(),
                (repo / "skills" / "common" / managed_skill.name / "SKILL.md").read_bytes(),
            )
            managed_link_mtime = managed_skill.lstat().st_mtime_ns
            docs_link = custom_project / "docs"
            docs_link_mtime = docs_link.lstat().st_mtime_ns
            self.assertTrue(os.path.samefile(
                docs_link, repo / "projects" / "exdigm" / "docs"
            ))
            backups_after_first_install = set(home.glob(".kmh-agent-kit-backup-*"))
            wrappers: dict[str, Path] = {}
            wrapper_contents: dict[str, bytes] = {}
            wrapper_mtimes: dict[str, int] = {}
            self.assertTrue((home / ".local/bin/controlroom.cmd").is_file())
            for name in ("kitpull", "kitpush"):
                wrapper = home / ".local" / "bin" / f"{name}.cmd"
                lines = wrapper.read_text(encoding="utf-8").splitlines()
                self.assertEqual(len(lines), 1)
                wrappers[name] = wrapper
            invocation = wrappers["kitpush"].read_text(encoding="utf-8").strip().removeprefix("@")
            legacy_push = (
                "@echo off\r\n"
                'set "PATH=C:\\Program Files\\Git\\cmd;%PATH%"\r\n'
                f"{invocation}\r\n"
            )
            wrappers["kitpush"].write_bytes(legacy_push.encode("utf-8"))
            for name, wrapper in wrappers.items():
                os.utime(wrapper, (946684800, 946684800))
                wrapper_contents[name] = wrapper.read_bytes()
                wrapper_mtimes[name] = wrapper.stat().st_mtime_ns
            venture = home / "projects" / "venture"
            (venture / "AGENTS.md").write_text("local venture work\n", encoding="utf-8")
            skill_mtimes = {
                tool_home: (venture / tool_home / "skills" / "venture").lstat().st_mtime_ns
                for tool_home in (".agents", ".claude")
            }
            (venture / "skills" / "retired" / "SKILL.md").unlink()
            (venture / "skills" / "retired").rmdir()
            added_skill = venture / "skills" / "added"
            added_skill.mkdir()
            (added_skill / "SKILL.md").write_text("added skill\n", encoding="utf-8")
            private_project_skill = venture / ".agents" / "skills" / "private" / "SKILL.md"
            private_project_skill.parent.mkdir()
            private_project_skill.write_text("private project skill\n", encoding="utf-8")
            venture_status = run("git", "status", "--porcelain=v1", cwd=venture).stdout
            run(*command, env=env)
            self.assertEqual(run("git", "status", "--porcelain=v1", cwd=venture).stdout,
                             venture_status)
            self.assertEqual(private_project_skill.read_text(), "private project skill\n")
            for tool_home in (".agents", ".claude"):
                live_skills = venture / tool_home / "skills"
                self.assertEqual((live_skills / "venture").lstat().st_mtime_ns,
                                 skill_mtimes[tool_home])
                self.assertFalse((live_skills / "retired").exists())
                self.assertTrue(os.path.samefile(live_skills / "added", added_skill))
            self.assertEqual(managed_skill.lstat().st_mtime_ns, managed_link_mtime)
            self.assertEqual(docs_link.lstat().st_mtime_ns, docs_link_mtime)
            self.assertFalse((home / "projects" / "exdigm").exists())
            self.assertEqual(private_skill.read_text(encoding="utf-8"), "private skill\n")
            self.assertTrue(os.path.samefile(foreign_source, foreign_link))
            self.assertEqual(
                (foreign_link / "SKILL.md").read_text(encoding="utf-8"), "foreign skill\n"
            )
            self.assertEqual(
                set(home.glob(".kmh-agent-kit-backup-*")), backups_after_first_install
            )

            for name, action in (("kitpull", "pull"), ("kitpush", "push")):
                wrapper = wrappers[name]
                self.assertEqual(wrapper.read_bytes(), wrapper_contents[name])
                self.assertIn(f" {action} %*", wrapper.read_text(encoding="utf-8"))
                self.assertEqual(wrapper.stat().st_mtime_ns, wrapper_mtimes[name])

            for profile, skill in (
                ("claude", "humanize-korean"),
                ("projects/fundkeeper", "testbed"),
            ):
                self.assertTrue((repo / profile / "skills" / skill / "SKILL.md").is_file())
            self.assertTrue(
                os.path.samefile(
                    home / ".agents" / "skills" / "check-master-plan",
                    repo / "skills" / "common" / "check-master-plan",
                )
            )
            self.assertTrue(
                os.path.samefile(
                    home / "projects" / "ceoloan" / ".agents" / "skills" / "cretop",
                    repo / "skills" / "domains" / "ceoloan" / "cretop",
                )
            )

            self.assertFalse(legacy_skill.parent.exists())
            legacy_backups = list(
                home.glob(".kmh-agent-kit-backup-*/.codex_skills_preflight/SKILL.md")
            )
            self.assertEqual(len(legacy_backups), 1)
            self.assertEqual(legacy_backups[0].read_text(), "legacy preflight\n")
            self.assertTrue((home / ".agents" / "skills" / "preflight").is_dir())

            for profile in profile_names:
                with self.subTest(profile=profile):
                    project = custom_project if profile == "exdigm" else home / "projects" / profile
                    canonical_docs = repo / "projects" / profile / "docs"
                    self.assertTrue(os.path.samefile(project / "docs", canonical_docs))
                    self.assertEqual((project / "docs" / "README.md").read_bytes(),
                                     (canonical_docs / "README.md").read_bytes())
                    self.assertTrue(project.is_dir())
                    saved = run(
                        "git",
                        "config",
                        "--local",
                        "--get",
                        f"kmh-agent-kit.project.{profile}",
                        cwd=repo,
                    ).stdout.strip()
                    self.assertEqual(Path(saved).resolve(), project.resolve())
                    source_agents = repo / "projects" / profile / "AGENTS.md"
                    if source_agents.is_file():
                        self.assertTrue(os.path.samefile(source_agents, project / "AGENTS.md"))
                    source_claude = repo / "projects" / profile / "CLAUDE.md"
                    if source_claude.is_file():
                        expected = source_claude.resolve()
                        self.assertTrue(os.path.samefile(expected, project / "CLAUDE.md"))
                    source_skills = repo / "projects" / profile / "skills"
                    if source_skills.is_dir():
                        for source_skill in source_skills.iterdir():
                            for tool_home in ".agents", ".claude":
                                live_skill = project / tool_home / "skills" / source_skill.name
                                self.assertTrue((live_skill / "SKILL.md").is_file())

            self.assertEqual(preserved.read_text(encoding="utf-8"), "keep\n")
            self.assertTrue((venture / ".git").is_dir())
            self.assertEqual(
                (venture / "AGENTS.md").read_text(encoding="utf-8"),
                "local venture work\n",
            )

            # Installed CMD -> real installer -> commit/push -> independent writer -> pull.
            for checkout in (repo, venture):
                KitFixture._configure(checkout)
                run("git", "add", "-A", cwd=checkout)
                run("git", "commit", "-m", "Windows checkpoint baseline", cwd=checkout)
            control_origin = temp / "controlroom.git"
            run("git", "clone", "--bare", repo, control_origin)
            run("git", "remote", "add", "origin",
                "https://github.com/chaconne67/controlroom.git", cwd=repo)
            run("git", "config", f"url.{control_origin.as_uri()}.insteadOf",
                "https://github.com/chaconne67/controlroom.git", cwd=repo)
            checkpoint = repo / "checkpoint.txt"
            checkpoint.write_text("CMD push checkpoint\n", encoding="utf-8")
            cmd_exe = shutil.which("cmd.exe") or "cmd.exe"
            run(cmd_exe, "/d", "/c", wrappers["kitpush"], "Windows CMD checkpoint",
                env=env)
            self.assertEqual(run("git", "--git-dir", control_origin,
                                 "show", "main:checkpoint.txt").stdout,
                             "CMD push checkpoint\n")
            self.assertEqual(run("git", "rev-parse", "HEAD", cwd=venture).stdout,
                             run("git", "--git-dir", venture_origin, "rev-parse", "main").stdout)
            receiver = temp / "receiver"
            run("git", "clone", control_origin, receiver)
            self.assertEqual((receiver / "checkpoint.txt").read_text(),
                             "CMD push checkpoint\n")
            KitFixture._configure(receiver)
            (receiver / "checkpoint.txt").write_text("independent pull checkpoint\n",
                                                     encoding="utf-8")
            run("git", "add", "checkpoint.txt", cwd=receiver)
            run("git", "commit", "-m", "independent update", cwd=receiver)
            run("git", "push", cwd=receiver)
            run(cmd_exe, "/d", "/c", wrappers["kitpull"], env=env)
            self.assertEqual(checkpoint.read_text(), "independent pull checkpoint\n")
            for checkout in (repo, venture):
                self.assertEqual(run("git", "status", "--porcelain", cwd=checkout).stdout, "")

            # An ordinary docs directory belongs to the user, even when install fails.
            protected_docs = home / "projects" / "rndlog" / "docs"
            protected_docs.rmdir()  # Remove this test's junction only.
            protected_docs.mkdir()
            protected_file = protected_docs / "keep.txt"
            protected_file.write_bytes(b"uncommitted planning\n")
            blocked = run(*command, env=env, check=False)
            self.assertNotEqual(blocked.returncode, 0)
            self.assertEqual(protected_file.read_bytes(), b"uncommitted planning\n")
            self.assertEqual(set(home.glob(".kmh-agent-kit-backup-*")),
                             backups_after_first_install)
            self.assertTrue((home / "projects/_control-docs").samefile(repo / "projects"))
            self.assertFalse((home / "projects/_control-docs/.git").exists())


@unittest.skipIf(os.name == "nt", "Requires a native POSIX installer host")
class PosixControlRoomInstallerTests(unittest.TestCase):
    def test_control_room_reconnects_custom_project_docs_and_preserves_work(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kmh-posix-control-") as temp_dir:
            temp = Path(temp_dir)
            home = temp / "home"
            repo = home / "kmh-agent-kit"
            home.mkdir()
            shutil.copytree(ROOT, repo, symlinks=True,
                            ignore=shutil.ignore_patterns(".git", "__pycache__"))
            run("git", "init", "--initial-branch=main", repo)
            custom_project = temp / "custom projects" / "exdigm"
            custom_project.mkdir(parents=True)
            run("git", "config", "--local", "kmh-agent-kit.project.exdigm",
                custom_project, cwd=repo)

            docs_repo = repo / "projects"
            venture = home / "projects" / "venture"
            for checkout, remote in ((venture, "venture"),):
                run("git", "init", "--initial-branch=main", checkout)
                run("git", "remote", "add", "origin",
                    f"https://github.com/chaconne67/{remote}.git", cwd=checkout)
            profiles = ("ceoloan", "exdigm", "fundkeeper", "rndlog", "ziin")
            for profile in profiles:
                document = docs_repo / profile / "docs" / "README.md"
                document.parent.mkdir(parents=True, exist_ok=True)
                document.write_text(f"{profile} planning\n", encoding="utf-8")
            pending_code = venture / "keep.txt"
            pending_code.write_bytes(b"uncommitted code\n")
            project_skill = venture / "skills" / "venture"
            project_skill.mkdir(parents=True)
            (project_skill / "SKILL.md").write_text("venture skill\n", encoding="utf-8")
            (venture / ".gitignore").write_text(".agents/\n.claude/\n", encoding="utf-8")
            statuses = {checkout: run("git", "status", "--porcelain=v1",
                                      cwd=checkout).stdout
                        for checkout in (venture,)}

            fake_bin = temp / "bin"
            fake_bin.mkdir()
            ssh = fake_bin / "ssh"
            ssh.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            ssh.chmod(0o755)
            env = os.environ.copy()
            env.update(HOME=str(home), CLAUDE_HOME=str(home / ".claude"),
                       CODEX_HOME=str(home / ".codex"), HERMES_HOME=str(home / ".hermes"),
                       PATH=str(fake_bin) + os.pathsep + env["PATH"])
            command = (BASH, repo / "install.sh", "windows-control")
            run(*command, env=env)
            for tool_home in (".agents", ".claude"):
                live_skill = venture / tool_home / "skills" / "venture"
                self.assertTrue(live_skill.is_symlink())
                self.assertTrue(live_skill.samefile(project_skill))
            backups = set(home.glob(".kmh-agent-kit-backup-*"))
            docs_link_mtime = (custom_project / "docs").lstat().st_mtime_ns
            run(*command, env=env)
            self.assertEqual(set(home.glob(".kmh-agent-kit-backup-*")), backups)
            self.assertEqual((custom_project / "docs").lstat().st_mtime_ns, docs_link_mtime)
            self.assertFalse((home / "projects" / "exdigm").exists())
            for profile in profiles:
                project = custom_project if profile == "exdigm" else home / "projects" / profile
                saved = run("git", "config", "--local", "--get",
                            f"kmh-agent-kit.project.{profile}", cwd=repo).stdout.strip()
                self.assertEqual(Path(saved), project.resolve())
                self.assertTrue((project / "docs").is_symlink())
                self.assertTrue((project / "docs").samefile(docs_repo / profile / "docs"))
                self.assertTrue((project / "AGENTS.md").samefile(
                    repo / "projects" / profile / "AGENTS.md"))
            self.assertEqual(pending_code.read_bytes(), b"uncommitted code\n")

            protected_docs = home / "projects" / "rndlog" / "docs"
            protected_docs.unlink()  # Remove this test's symlink only.
            protected_docs.mkdir()
            marker = protected_docs / "keep.txt"
            marker.write_bytes(b"uncommitted planning\n")
            result = run(*command, env=env, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(marker.read_bytes(), b"uncommitted planning\n")
            self.assertEqual(set(home.glob(".kmh-agent-kit-backup-*")), backups)
            for checkout, status in statuses.items():
                self.assertEqual(run("git", "status", "--porcelain=v1",
                                     cwd=checkout).stdout, status)


class GBrainAccessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="kmh-gbrain-access-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.policy = self.root / "policy.toml"
        self.policy.write_text(textwrap.dedent('''\
            [defaults]
            common_direct_write = false
            [guardrails]
            common_write_prefixes = ["agent", "reference", "shared/common"]
            [agents.sample]
            private_source = "sample"
            private_prefix = "agents/sample/private"
            read_sources = ["default", "sample"]
            write_sources = ["sample"]
            common_write = false
        '''), encoding="utf-8")
        self.log = self.root / "calls.jsonl"
        self.mock = self.root / "mock-cli"
        self.mock.write_text(textwrap.dedent('''\
            #!/usr/bin/env python3
            import json, os, sys
            args = sys.argv[1:]
            source = os.environ.get("GBRAIN_SOURCE", "")
            for flag in ("--source", "--source-id"):
                if flag in args:
                    source = args[args.index(flag) + 1]
            body = ""
            if "--stdin" in args:
                body = sys.stdin.read()
            if "--file" in args:
                with open(args[args.index("--file") + 1]) as f:
                    body = f.read()
            with open(os.environ["TEST_CALLS"], "a") as f:
                f.write(json.dumps({"source": source, "args": args, "body": body}) + "\\n")
            if os.environ.get("TEST_FAIL_SOURCE") == source:
                print("backend unavailable", file=sys.stderr)
                sys.exit(23)
            print("document available")
        '''), encoding="utf-8")
        self.mock.chmod(0o755)
        self.env = os.environ.copy()
        self.env.update(GBRAIN_POLICY_FILE=str(self.policy),
                        GBRAIN_CLI_WRAPPER=str(self.mock), TEST_CALLS=str(self.log))
        self.wrapper = ROOT / "gbrain/bin/gbrain-agent"

    def invoke(self, *args: str, **kwargs) -> subprocess.CompletedProcess[str]:
        return run("bash", self.wrapper, "sample", *args, env=self.env, **kwargs)

    def calls(self) -> list[dict]:
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def test_private_lookup_keeps_existing_source(self) -> None:
        self.invoke("get", "agents/sample/private/page")
        self.assertEqual(self.calls()[0]["source"], "sample")

    def test_shared_lookup_uses_explicit_source(self) -> None:
        self.invoke("--source", "default", "get", "agent/protocol")
        self.assertEqual(self.calls()[0]["source"], "default")

    def test_list_and_explicit_query_use_selected_source(self) -> None:
        self.invoke("list")
        self.invoke("--source", "default", "list", "--tag", "incident", "-n", "80")
        self.invoke("--source", "default", "query", "topic")
        self.assertEqual([call["source"] for call in self.calls()], ["sample", "default", "default"])
        self.assertEqual(self.calls()[1]["args"], ["list", "--limit", "80", "--tag", "incident"])
        result = self.invoke("--source", "default", "list", "--source-id", "other", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.calls()), 3)

    def test_private_notes_keep_prefix_and_unprefixed_agent_conventions(self) -> None:
        self.invoke("note", "page", "한글 기록")
        self.assertIn("agents/sample/private/page", self.calls()[0]["args"])
        self.assertIn("visibility: private", self.calls()[0]["body"])
        self.policy.write_text(self.policy.read_text().replace('private_prefix = "agents/sample/private"', ''))
        self.invoke("note", "knowledge/page", "기존 경로")
        self.assertIn("knowledge/page", self.calls()[1]["args"])

    def test_other_private_source_is_rejected(self) -> None:
        result = self.invoke("--source", "other-agent", "get", "page", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.calls(), [])

    def test_all_query_stays_in_authorized_sources(self) -> None:
        self.invoke("query-all", "topic")
        self.assertEqual([call["source"] for call in self.calls()], ["default", "sample"])

    def test_partial_query_failure_is_not_reported_as_success(self) -> None:
        self.env["TEST_FAIL_SOURCE"] = "default"
        result = self.invoke("query", "topic", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual([call["source"] for call in self.calls()], ["default", "sample"])

    def test_private_input_and_prefix_are_preserved(self) -> None:
        body = "한글 기록\nsecond line\n"
        self.invoke("put", "agents/sample/private/page", "-", input_text=body)
        self.assertEqual(self.calls()[0]["source"], "sample")
        self.assertEqual(self.calls()[0]["body"], body)
        self.log.unlink()
        result = self.invoke("put", "agents/other/private/page", "-", input_text=body, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.calls(), [])

    def test_shared_write_requires_policy_permission(self) -> None:
        result = self.invoke("--source", "default", "put", "reference/page", "-", input_text="body", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.calls(), [])

    def test_allowed_shared_write_uses_common_source_and_prefix(self) -> None:
        text = self.policy.read_text().replace("common_direct_write = false", "common_direct_write = true")
        text = text.replace("common_write = false", "common_write = true")
        text = text.replace('write_sources = ["sample"]', 'write_sources = ["default", "sample"]')
        self.policy.write_text(text)
        self.invoke("--source", "default", "put", "reference/page", "-", input_text="body")
        self.assertEqual(self.calls()[0]["source"], "default")
        self.log.unlink()
        result = self.invoke("--source", "default", "put", "agents/other/private/page", "-", input_text="body", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.calls(), [])

    def test_new_agent_registration_enables_shared_writes(self) -> None:
        self.policy.write_text(self.policy.read_text().replace("common_direct_write = false", "common_direct_write = true"))
        installer = (ROOT / "install.sh").read_text()
        function = "append_policy_blocks() {" + installer.split("append_policy_blocks() {", 1)[1].split("\n}\n", 1)[0] + "\n}"
        env = self.env | {"policy_file": str(self.policy), "stamp": "test"}
        run("bash", "-c", function + '\nappend_policy_blocks fresh "$1" yes yes', "test", self.root / "fresh", env=env)
        run("bash", self.wrapper, "fresh", "--source", "default", "put", "reference/page", "-", env=env, input_text="shared knowledge")
        self.assertEqual(self.calls()[0]["source"], "default")

    def test_proxy_forwards_file_and_stdin_with_source_selection(self) -> None:
        fake_bin = self.root / "bin"
        fake_bin.mkdir()
        ssh = fake_bin / "ssh"
        ssh.write_text('#!/usr/bin/env bash\nprintf "%s\\n" "$@" > "$TEST_SSH_ARGS"\ncat > "$TEST_SSH_BODY"\n')
        ssh.chmod(0o755)
        args_file, body_file = self.root / "ssh-args", self.root / "ssh-body"
        env = self.env | {"PATH": str(fake_bin) + os.pathsep + self.env["PATH"],
                          "TEST_SSH_ARGS": str(args_file), "TEST_SSH_BODY": str(body_file)}
        body = "literal $value and 한글\n"
        input_file = self.root / "input with spaces.md"
        input_file.write_text(body, encoding="utf-8")
        for file in (str(input_file), "-"):
            with self.subTest(file=file):
                run("bash", ROOT / "gbrain/bin/gbrain-remote-proxy", "sample", "--source", "default",
                    "put", "reference/page", file, env=env, input_text=body if file == "-" else "")
                self.assertEqual(body_file.read_text(encoding="utf-8"), body)
                self.assertIn("--source default put reference/page -", args_file.read_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
