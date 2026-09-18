#!/usr/bin/env python3
"""Disposable Git integration checks for kitpull and kitpush."""

from __future__ import annotations

from contextlib import contextmanager
import os
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import textwrap
import sys
import zipfile
from contextlib import ExitStack
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
    invocation = [str(arg) for arg in args]
    if os.name == 'nt' and len(args) == 4 and args[:3] == ('cmd.exe', '/d', '/c'):
        invocation = 'cmd.exe /d /c ' + str(args[3])
    result = subprocess.run(
        invocation,
        cwd=cwd,
        env=env,
        input=input_text,
        text=True,
        encoding="utf-8",
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
    """Real entrypoints and controller against file-only remotes and isolated homes."""
    def __init__(self):
        self.temp = tempfile.TemporaryDirectory(prefix='controlroom-sync-')
        self.root = Path(self.temp.name)
        self.remote = self.root / 'controlroom.git'
        self.product_remote = self.root / 'venture.git'
        self.seed = self.root / 'seed'
        self.clone_count = 0
        self.cleanups = ExitStack()
        run('git', 'init', '--initial-branch=main', self.seed)
        self._configure(self.seed)
        toolkit = self.seed / '.controlroom'
        for relative in ['install.ps1', 'install.sh', 'scripts/controlroom.py', 'shell/kit-aliases.sh', 'templates/main-server-project.md']:
            destination = toolkit / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, destination)
        contents = {'README.md': 'baseline\n', '.gitignore': '.env*\n*.pem\n/venture/\n**/.agents/\n**/.claude/\n',
                    '.gitattributes': '**/docs/** -text\n', '.controlroom/common.txt': 'base\n',
                    '.controlroom/codex/AGENTS.md': 'codex\n', '.controlroom/claude/CLAUDE.md': 'claude\n',
                    'rndlog/AGENTS.md': 'rndlog instructions\n', 'rndlog/CLAUDE.md': 'rndlog instructions\n',
                    'ceoloan/AGENTS.md': 'ceoloan instructions\n',
                    'rndlog/docs/plan.md': 'first step\r\n', 'ceoloan/docs/plan.md': 'ceoloan\n',
                    '.controlroom/skills/example/SKILL.md': 'common skill\n',
                    '.controlroom/skills/example/references/detail.md': 'supporting file\n',
                    'rndlog/skills/rndlog-example/SKILL.md': 'project skill\n'}
        for agent in ['main', 'windows-control', 'rndlog', 'gram17']:
            contents[f'.controlroom/gbrain-cards/{agent}.md'] = agent + '\n'
        for relative, content in contents.items():
            path = self.seed / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content.encode('utf-8'))
        manifest = {'sources': {'example': '.controlroom/skills/example', 'rndlog-example': 'rndlog/skills/rndlog-example'},
                    'profiles': {'global': ['example'], 'projects': {'rndlog': ['rndlog-example']}},
                    'depends_on': {'rndlog-example': ['example']}}
        (toolkit / 'manifests').mkdir()
        (toolkit / 'manifests/skills.json').write_text(json.dumps(manifest), encoding='utf-8')
        (toolkit / 'manifests/windows-control-projects.tsv').write_text('rndlog\tprofile\trndlog\nventure\tgit\tgit@github.com:chaconne67/venture.git\n')
        self.commit_seed('baseline')
        run('git', 'clone', '--bare', self.seed, self.remote)
        run('git', 'remote', 'add', 'origin', self.remote, cwd=self.seed)
        run('git', 'branch', '--set-upstream-to=origin/main', 'main', cwd=self.seed, check=False)
        product = self.root / 'product-seed'
        run('git', 'init', '--initial-branch=main', product)
        self._configure(product)
        (product / 'app.py').write_text('initial\n')
        (product / '.gitignore').write_text('.env*\ncompanies/\n.agents/\n.claude/\n')
        (product / 'skills/venture-example/references').mkdir(parents=True)
        (product / 'skills/venture-example/SKILL.md').write_bytes(b'Venture workflow\n')
        (product / 'skills/venture-example/references/detail.md').write_bytes(b'Venture reference\n')
        run('git', 'add', '-A', cwd=product)
        run('git', 'commit', '-m', 'baseline', cwd=product)
        run('git', 'clone', '--bare', product, self.product_remote)

    def close(self):
        self.cleanups.close()
        self.temp.cleanup()

    @staticmethod
    def _configure(repo):
        run('git', 'config', 'user.name', 'Controlroom Test', cwd=repo)
        run('git', 'config', 'user.email', 'controlroom-test@example.invalid', cwd=repo)

    def commit_seed(self, message, push=False):
        run('git', 'add', '-A', cwd=self.seed)
        run('git', 'commit', '-m', message, cwd=self.seed)
        if push:
            run('git', 'push', '-u', 'origin', 'main', cwd=self.seed)

    def env(self, home):
        env = dict(os.environ, HOME=str(home), USERPROFILE=str(home),
                   CODEX_HOME=str(home / '.codex'), CLAUDE_HOME=str(home / '.claude'),
                   HERMES_HOME=str(home / '.hermes'), LOCALAPPDATA=str(home / 'AppData/Local'),
                   GIT_TERMINAL_PROMPT='0', GIT_ALLOW_PROTOCOL='file',
                   GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_COUNT='2',
                   GIT_CONFIG_KEY_0=f'url.{self.remote.as_uri()}.insteadOf',
                   GIT_CONFIG_VALUE_0='git@github.com:chaconne67/controlroom.git',
                   GIT_CONFIG_KEY_1=f'url.{self.product_remote.as_uri()}.insteadOf',
                   GIT_CONFIG_VALUE_1='git@github.com:chaconne67/venture.git',
                   PYTHONUTF8='1')
        env['PATH'] = str(home / '.local/bin') + os.pathsep + env['PATH']
        return env

    def new_home(self, spaces=False):
        self.clone_count += 1
        home = self.root / (f'home-{self.clone_count}' + (' Korean 조정실' if spaces else ''))
        home.mkdir()
        if os.name == 'nt':
            self.cleanups.enter_context(preserve_windows_installer_path(home))
        return home

    def install(self, home, agent='windows-control', standalone=False, bash=False, workspace=None, main_server=False):
        installer = self.seed / '.controlroom' / ('install.ps1' if os.name == 'nt' and not bash else 'install.sh')
        if standalone:
            destination = home / installer.name
            shutil.copy2(installer, destination)
            installer = destination
        if os.name == 'nt' and not bash:
            options = ['-Workspace', workspace] if workspace else []
            if main_server:
                options += ['-MainServer']
            return run('powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', installer, '-Agent', agent, *options, env=self.env(home))
        options = ['--workspace', workspace] if workspace else []
        if main_server:
            options += ['--main-server']
        return run(BASH, '--noprofile', '--norc', installer, *options, agent, env=self.env(home))

    def clone(self, agent='main', spaces=False):
        home = self.new_home(spaces)
        self.install(home, agent)
        repo = home / 'projects'
        self._configure(repo)
        if (repo / 'venture/.git').is_dir():
            self._configure(repo / 'venture')
        return home, repo

    def kit(self, home, command, check=True):
        if os.name == 'nt':
            return run('cmd.exe', '/d', '/c', command, cwd=home, env=self.env(home), check=check)
        return run(BASH, '--noprofile', '--norc', '-c', command, cwd=home, env=self.env(home), check=check)

    def archive(self, home):
        archives = list((home / 'backups/controlroom').glob('*.zip'))
        return max(archives, key=lambda p: p.stat().st_mtime_ns)

    def backed_up(self, home, path, archive_path=None):
        with zipfile.ZipFile(archive_path or self.archive(home)) as archive:
            records = json.loads(archive.read('manifest.json'))['records']
            record = next(r for r in records if r['path'] == str(path))
            return archive.read(record['entry'])


class KitSyncTests(unittest.TestCase):
    def setUp(self):
        self.fixture = KitFixture()
        self.addCleanup(self.fixture.close)

    def test_pull_repairs_upstream_fast_forwards_and_installs(self):
        home, repo = self.fixture.clone()
        run('git', 'branch', '--unset-upstream', cwd=repo)
        (self.fixture.seed / 'README.md').write_text('remote update\n')
        self.fixture.commit_seed('remote update', True)
        self.fixture.kit(home, 'kitpull')
        self.assertEqual((repo / 'README.md').read_text(), 'remote update\n')
        self.assertEqual(run('git', 'rev-parse', '--abbrev-ref', '@{upstream}', cwd=repo).stdout.strip(), 'origin/main')
        self.fixture.kit(home, 'kitpull --verify')

    def test_standalone_commands_use_same_pull_and_push_paths(self):
        home, repo = self.fixture.clone(spaces=True)
        (repo / 'README.md').write_text('standalone\n')
        self.fixture.kit(home, 'kitpush "standalone checkpoint"')
        self.fixture.kit(home, 'kitpull')
        self.assertEqual((repo / 'README.md').read_text(), 'standalone\n')
        self.fixture.kit(home, 'kitpull --verify')

    def test_raw_bash_installer_clones_then_runs_checked_out_installer(self):
        home = self.fixture.new_home()
        run(BASH, '--noprofile', '--norc', '-s', '--', 'rndlog', env=self.fixture.env(home),
            input_text=(ROOT / 'install.sh').read_text(encoding='utf-8'))
        self.assertTrue((home / 'projects/.git').is_dir())
        self.assertEqual((home / '.gbrain-agent.md').read_text(), 'rndlog\n')
        self.fixture.kit(home, 'kitpull --verify')

    def test_git_bash_installer_uses_same_transaction_with_agent(self):
        home = self.fixture.new_home()
        self.fixture.install(home, 'gram17', bash=True)
        self.assertEqual((home / '.gbrain-agent.md').read_text(), 'gram17\n')
        self.assertTrue((home / '.local/bin/gbrain-gram17').is_file())
        self.fixture.kit(home, 'kitpull --verify')

    def test_installer_adds_global_commands_and_preserves_hermes_skills(self):
        home = self.fixture.new_home()
        command_dir = home / '.local/bin'
        command_dir.mkdir(parents=True)
        retired = [command_dir / name for name in ('controlroom', 'controlroom.cmd')]
        for path in retired:
            path.write_bytes(b'previous managed command\n')
        foreign = home / '.hermes/skills/example/SKILL.md'
        foreign.parent.mkdir(parents=True)
        foreign.write_text('foreign Hermes skill\n')
        private = home / '.codex/skills/.system/private/SKILL.md'
        private.parent.mkdir(parents=True)
        private.write_text('private system skill\n')
        self.fixture.install(home)
        self.assertEqual(foreign.read_text(), 'foreign Hermes skill\n')
        self.assertEqual(private.read_text(), 'private system skill\n')
        self.assertEqual((home / '.agents/skills/example/references/detail.md').read_text(), 'supporting file\n')
        for path in retired:
            self.assertFalse(path.exists())
            self.assertEqual(self.fixture.backed_up(home, path), b'previous managed command\n')
        for name in ('kitpull', 'kitpush'):
            self.assertIn(f'usage: {name}', self.fixture.kit(home, f'{name} --help').stdout)
        archives = list((home / 'backups/controlroom').iterdir())
        self.fixture.kit(home, 'kitpull --verify')
        self.assertEqual(list((home / 'backups/controlroom').iterdir()), archives)
        run(BASH, '--noprofile', '--norc', '-c',
            'set -e; controlroom() { return 99; }; alias controlroom=false; '
            '. "$HOME/projects/.controlroom/shell/kit-aliases.sh"; '
            'kitpull --verify; ! declare -F controlroom; ! alias controlroom 2>/dev/null',
            cwd=home, env=self.fixture.env(home))
        if os.name == 'nt':
            result = run('powershell.exe', '-NoProfile', '-Command',
                         'kitpull --help; kitpush --help; exit $LASTEXITCODE', env=self.fixture.env(home))
            self.assertIn('usage: kitpull', result.stdout)
            self.assertIn('usage: kitpush', result.stdout)

    def test_push_rejects_detached_or_non_main_branch_pull_archives_and_updates(self):
        home, repo = self.fixture.clone()
        for arguments in [('checkout', '--detach'), ('checkout', '-b', 'unfinished')]:
            run('git', *arguments, cwd=repo)
            self.assertNotEqual(self.fixture.kit(home, 'kitpush', False).returncode, 0)
            previous = (repo / '.git/HEAD').read_bytes()
            self.fixture.kit(home, 'kitpull')
            self.assertEqual(self.fixture.backed_up(home, repo / '.git/HEAD'), previous)
            self.assertEqual(run('git', 'branch', '--show-current', cwd=repo).stdout.strip(), 'main')

    def test_pull_archives_in_progress_git_operation_and_updates(self):
        home, repo = self.fixture.clone()
        head = run('git', 'rev-parse', 'HEAD', cwd=repo).stdout.strip()
        marker = repo / '.git/MERGE_HEAD'
        marker.write_bytes((head + '\n').encode())
        self.fixture.kit(home, 'kitpull')
        self.assertFalse(marker.exists())
        self.assertEqual(self.fixture.backed_up(home, marker), (head + '\n').encode())

    def test_non_main_agent_can_push_only_its_domain(self):
        home, repo = self.fixture.clone('rndlog')
        (repo / 'rndlog/docs/plan.md').write_text('own plan\n')
        self.fixture.kit(home, 'kitpush')
        (repo / 'ceoloan/AGENTS.md').write_text('foreign instructions\n')
        before = run('git', 'rev-parse', 'HEAD', cwd=repo).stdout
        self.assertNotEqual(self.fixture.kit(home, 'kitpush', False).returncode, 0)
        self.assertEqual(run('git', 'rev-parse', 'HEAD', cwd=repo).stdout, before)

    def test_main_pushes_all_domains_and_another_clone_pulls(self):
        self._central_round_trip('main')

    def test_windows_control_pushes_all_domains_and_another_clone_pulls(self):
        self._central_round_trip('windows-control')

    def _central_round_trip(self, role):
        a, ra = self.fixture.clone(role)
        b, rb = self.fixture.clone('rndlog')
        (ra / 'ceoloan/docs/plan.md').write_text('central plan\n')
        (ra / '.controlroom/common.txt').write_text('updated tool\n')
        self.fixture.kit(a, 'kitpush')
        self.fixture.kit(b, 'kitpull')
        self.assertEqual((rb / 'ceoloan/docs/plan.md').read_text(), 'central plan\n')
        self.assertEqual((rb / '.controlroom/common.txt').read_text(), 'updated tool\n')

    def test_push_rebases_non_conflicting_remote_change(self):
        a, ra = self.fixture.clone('rndlog')
        b, rb = self.fixture.clone('rndlog')
        (ra / 'README.md').write_text('remote readme\n')
        self.fixture.kit(a, 'kitpush')
        (rb / '.controlroom/common.txt').write_text('local tools\n')
        self.fixture.kit(b, 'kitpush')
        self.assertEqual((rb / 'README.md').read_text(), 'remote readme\n')
        self.assertEqual((rb / '.controlroom/common.txt').read_text(), 'local tools\n')

    def test_rebase_conflict_aborts_without_losing_local_commit(self):
        a, ra = self.fixture.clone('rndlog')
        b, rb = self.fixture.clone('rndlog')
        (ra / 'README.md').write_text('A\n')
        self.fixture.kit(a, 'kitpush')
        (rb / 'README.md').write_text('B\n')
        self.assertNotEqual(self.fixture.kit(b, 'kitpush', False).returncode, 0)
        self.assertEqual((rb / 'README.md').read_text(), 'B\n')
        self.assertEqual(run('git', 'rev-list', '--left-right', '--count', 'HEAD...origin/main', cwd=rb).stdout.strip(), '1\t1')
        self.assertFalse((rb / '.git/rebase-merge').exists())


class EntryPointDocumentationTests(unittest.TestCase):
    def test_readme_has_separate_primary_commands_for_each_os(self):
        readme = (ROOT.parent / 'README.md').read_text(encoding='utf-8')
        onboarding = (ROOT / 'docs/onboarding-new-server.md').read_text(encoding='utf-8')
        for text in (readme, onboarding):
            self.assertIn('install.ps1', text)
            self.assertIn('install.sh', text)
            self.assertIn('~/projects', text)
            self.assertIn('kitpull', text)
            self.assertIn('kitpush', text)
            self.assertNotIn('gh auth', text)
            self.assertNotIn('curl ', text)
            self.assertNotIn('Invoke-RestMethod', text)
            for action in ('pull', 'push', 'verify', 'restore'):
                self.assertNotIn('controlroom ' + action, text)
        self.assertEqual((ROOT / 'manifests/windows-control-projects.tsv').read_text().count('venture\tgit\t'), 1)


@unittest.skipUnless(os.name == 'nt', 'Native PowerShell installer contract')
class WindowsInstallerTests(unittest.TestCase):
    def setUp(self):
        self.fixture = KitFixture()
        self.addCleanup(self.fixture.close)

    def test_readme_ssh_one_liner_without_gh_in_current_shell(self):
        home = self.fixture.new_home(True)
        env = self.fixture.env(home)
        env['PATH'] = os.pathsep.join(p for p in env['PATH'].split(os.pathsep)[1:]
                                      if not (Path(p) / 'gh.exe').is_file())
        for key in ('GH_TOKEN', 'GITHUB_TOKEN', 'GH_ENTERPRISE_TOKEN', 'GITHUB_ENTERPRISE_TOKEN'):
            env.pop(key, None)
        readme = (ROOT.parent / 'README.md').read_text(encoding='utf-8')
        command = re.search(r'```powershell\n([^\n]+)\n```', readme)[1]
        self.assertIn(command, (ROOT / 'docs/onboarding-new-server.md').read_text(encoding='utf-8'))
        verify = r'''
foreach ($name in @('kitpull', 'kitpush')) {
    $expected = Join-Path $env:USERPROFILE ('.local\bin\' + $name + '.cmd')
    if ((Get-Command $name).Source -ne $expected) { throw 'Wrong command path' }
}
kitpull --verify
if ($LASTEXITCODE) { throw 'Verification failed' }
kitpush --help
if ($LASTEXITCODE) { throw 'Command dispatch failed' }
'''
        result = run('powershell.exe', '-NoProfile', '-Command',
                     "$ErrorActionPreference='Stop'; if (Get-Command gh -ErrorAction SilentlyContinue) { throw 'gh must be absent' }; "
                     + command + '\n' + verify + command + '\n' + verify, env=env)
        self.assertEqual(result.stdout.count('Physical layout and installed contents verified.'), 2)
        self.assertEqual(result.stdout.count('usage: kitpush'), 2)

        failed_home = self.fixture.new_home()
        # No rewrite is available and file is the only allowed transport: clone must fail.
        failed_env = self.fixture.env(failed_home) | {'GIT_CONFIG_COUNT': '0'}
        result = run('powershell.exe', '-NoProfile', '-Command', command, env=failed_env, check=False)
        self.assertNotEqual(result.returncode, 0)
        for relative in ('projects', '.codex', 'backups'):
            self.assertFalse((failed_home / relative).exists())

    def test_readme_cmd_one_liner_registers_commands_in_current_cmd(self):
        home = self.fixture.new_home(True)
        env = self.fixture.env(home)
        env['PATH'] = os.pathsep.join(p for p in env['PATH'].split(os.pathsep)[1:]
                                      if not (Path(p) / 'gh.exe').is_file())
        readme = (ROOT.parent / 'README.md').read_text(encoding='utf-8')
        command = re.search(r'```cmd\n([^\n]+)\n```', readme)[1]
        self.assertIn(command, (ROOT / 'docs/onboarding-new-server.md').read_text(encoding='utf-8'))
        result = run('cmd.exe', '/d', '/c', command
                     + ' && where kitpull && where kitpush && kitpull --verify && kitpush --help', env=env)
        self.assertIn(str(home / '.local/bin/kitpull.cmd'), result.stdout)
        self.assertIn(str(home / '.local/bin/kitpush.cmd'), result.stdout)
        self.assertIn('Physical layout and installed contents verified.', result.stdout)
        self.assertIn('usage: kitpush', result.stdout)

    def test_downloaded_powershell_installer_exposes_commands_in_current_shell(self):
        home = self.fixture.new_home(True)
        env = self.fixture.env(home)
        env['PATH'] = os.pathsep.join(env['PATH'].split(os.pathsep)[1:])
        env['CONTROLROOM_TEST_INSTALLER'] = str(self.fixture.seed / '.controlroom/install.ps1')
        command = '''$ErrorActionPreference = 'Stop'
& ([scriptblock]::Create((Get-Content -LiteralPath $env:CONTROLROOM_TEST_INSTALLER -Raw).TrimStart([char]0xFEFF))) -Agent windows-control
foreach ($name in @('kitpull', 'kitpush')) {
    $expected = Join-Path $env:USERPROFILE ('.local\\bin\\' + $name + '.cmd')
    if ((Get-Command $name).Source -ne $expected) { throw 'Command resolved outside the new installation' }
}
kitpull --verify
if ($LASTEXITCODE -ne 0) { throw 'Verification failed' }
kitpush --help
if ($LASTEXITCODE -ne 0) { throw 'Command dispatch failed' }
Write-Output 'CURRENT_SHELL_COMMANDS_READY'
'''
        result = run('powershell.exe', '-NoProfile', '-Command', command, env=env)
        self.assertIn('CURRENT_SHELL_COMMANDS_READY', result.stdout)
        self.assertIn('usage: kitpush', result.stdout)

    def test_real_windows_installer_help(self):
        result = run('powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ROOT / 'install.ps1', '-Help')
        self.assertIn('usage:', result.stdout)
        result = run(BASH, ROOT / 'install.sh', '--help')
        self.assertIn('usage:', result.stdout)

    def test_windows_control_restores_project_entrypoints_and_preserves_existing_work(self):
        home = self.fixture.new_home(True)
        docs = home / 'projects/rndlog/docs'
        docs.mkdir(parents=True)
        (docs / 'plan.md').write_text('old local plan\n')
        (docs / 'old-only.txt').write_bytes(b'unique old data\n')
        private_shell = b'# private shell config\r\nexport EXAMPLE=1\r\n'
        (home / '.bashrc').write_bytes(private_shell)
        self.fixture.install(home, standalone=True)
        self.assertEqual((docs / 'plan.md').read_bytes(), b'first step\r\n')
        self.assertFalse((docs / 'old-only.txt').exists())
        self.assertEqual(self.fixture.backed_up(home, docs / 'old-only.txt'), b'unique old data\n')
        self.assertFalse(docs.is_junction())
        self.assertTrue((home / 'projects/.git').is_dir())
        self.assertTrue((home / '.bashrc').read_bytes().startswith(private_shell))
        self.fixture.kit(home, 'kitpull --verify')
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as key:
            self.assertIn(str(home / '.local/bin'), winreg.QueryValueEx(key, 'Path')[0].split(';'))

    def test_locked_file_restores_previous_installation(self):
        home, repo = self.fixture.clone()
        before = run('git', 'rev-parse', 'HEAD', cwd=repo).stdout
        plan = repo / 'rndlog/docs/plan.md'
        plan.write_bytes(b'local work\r\n')
        (self.fixture.seed / '.controlroom/common.txt').write_text('new tools\n')
        self.fixture.commit_seed('updated tools', True)
        lock = home / 'lock.ps1'
        ready = home / 'lock-ready'
        release = home / 'lock-release'
        lock.write_text("$f=[IO.File]::Open($env:CODEX_HOME+'\\AGENTS.md','Open','Read','Read'); "
                        "[IO.File]::WriteAllText($env:USERPROFILE+'\\lock-ready','ready'); "
                        "try { while(-not (Test-Path -LiteralPath ($env:USERPROFILE+'\\lock-release'))) { Start-Sleep -Milliseconds 100 } } finally { $f.Dispose() }")
        process = subprocess.Popen(['powershell.exe', '-NoProfile', '-File', str(lock)], env=self.fixture.env(home),
                                   creationflags=subprocess.CREATE_NO_WINDOW, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            import time
            deadline = time.monotonic() + 15
            while not ready.exists() and time.monotonic() < deadline:
                time.sleep(.1)
            self.assertTrue(ready.exists())
            result = self.fixture.kit(home, 'kitpull', False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Previous state restored', result.stdout)
            self.assertEqual(run('git', 'rev-parse', 'HEAD', cwd=repo).stdout, before)
            self.assertEqual(plan.read_bytes(), b'local work\r\n')
            self.assertEqual((repo / '.controlroom/common.txt').read_text(), 'base\n')
        finally:
            release.touch()
            process.communicate(timeout=15)


@unittest.skipIf(os.name == 'nt', 'Native POSIX installer contract')
class PosixControlRoomInstallerTests(unittest.TestCase):
    def test_readme_one_liner_exposes_commands_in_current_shell(self):
        fixture = KitFixture()
        self.addCleanup(fixture.close)
        home = fixture.new_home(True)
        env = fixture.env(home)
        env['PATH'] = os.pathsep.join(env['PATH'].split(os.pathsep)[1:])
        readme = (ROOT.parent / 'README.md').read_text(encoding='utf-8')
        command = next(line for line in readme.splitlines() if line.startswith('d=') and '--main-server' not in line)
        self.assertIn(command, (ROOT / 'docs/onboarding-new-server.md').read_text(encoding='utf-8'))
        command += ' && test "$(type -t kitpull)" = function && kitpull --verify && kitpush --help'
        command = 'gh() { echo "gh must not run" >&2; return 99; }; ' + command
        result = run(BASH, '--noprofile', '--norc', '-c', command, env=env)
        self.assertIn('Physical layout and installed contents verified.', result.stdout)
        self.assertIn('usage: kitpush', result.stdout)

    def test_downloaded_script_string_does_not_use_core_from_current_directory(self):
        fixture = KitFixture()
        self.addCleanup(fixture.close)
        home = fixture.new_home(True)
        project = home / 'projects/rndlog'
        run('git', 'init', '--initial-branch=main', project)
        (project / 'app.py').write_bytes(b'existing code\n')
        decoy = fixture.root / 'old-toolkit'
        (decoy / 'scripts').mkdir(parents=True)
        (decoy / 'scripts/controlroom.py').write_text('raise SystemExit("Old local core must not run")\n')
        script = (fixture.seed / '.controlroom/install.sh').read_text(encoding='utf-8')
        run(BASH, '--noprofile', '--norc', '-c', script, '--', '--main-server',
            cwd=decoy, env=fixture.env(home))
        self.assertTrue((home / '.local/share/controlroom/source/.git').is_dir())
        self.assertFalse((home / 'projects/.git').exists())
        self.assertEqual((project / 'app.py').read_bytes(), b'existing code\n')
        fixture.kit(home, 'kitpull --verify')

    def test_control_room_replaces_docs_and_preserves_archived_work(self):
        fixture = KitFixture()
        self.addCleanup(fixture.close)
        home = fixture.new_home(True)
        docs = home / 'projects/rndlog/docs'
        docs.mkdir(parents=True)
        (docs / 'plan.md').write_text('old work\n')
        result = fixture.install(home, standalone=True)
        self.assertEqual((docs / 'plan.md').read_bytes(), b'first step\r\n', result.stdout + result.stderr)
        self.assertEqual(fixture.backed_up(home, docs / 'plan.md'), b'old work\n')
        self.assertFalse(docs.is_symlink())
        fixture.kit(home, 'kitpull --verify')


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
