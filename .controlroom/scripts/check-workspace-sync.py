#!/usr/bin/env python3
"""Two actual control rooms: latest contents apply after verified backups."""
import importlib.util
import json
import os
from pathlib import Path
import unittest
import zipfile
from unittest.mock import patch
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('kit_checks', ROOT / 'scripts/check-kit-sync.py')
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)
run = checks.run


class WorkspaceSyncTests(unittest.TestCase):
    def setUp(self):
        self.fixture = checks.KitFixture()
        self.addCleanup(self.fixture.close)

    def command(self, home, command='controlroom pull', check=True):
        return self.fixture.kit(home, command, check)

    def device(self, spaces=False):
        return self.fixture.clone('windows-control', spaces)

    def plan(self, repo):
        return repo / 'rndlog/docs/plan.md'

    def test_server_workspace_override_keeps_operating_repositories(self):
        home = self.fixture.new_home(True)
        workspace = home / 'controlroom-workspaces'
        baseline = {}
        for name in ('ceoloan', 'fundkeeper', 'rndlog', 'ziin'):
            code = home / 'projects' / name
            run('git', 'init', '--initial-branch=main', code)
            self.fixture._configure(code)
            (code / 'app.py').write_bytes(b'operating code\n')
            run('git', 'add', 'app.py', cwd=code)
            run('git', 'commit', '-m', 'operating baseline', cwd=code)
            (code / '.env').write_bytes(b'SYNTHETIC=preserve\r\n')
            baseline[code] = ((code / '.git/index').read_bytes(),
                              run('git', 'rev-parse', 'HEAD', cwd=code).stdout,
                              run('git', 'status', '--porcelain', cwd=code).stdout)
        self.fixture.install(home, standalone=True, workspace=workspace)
        self.fixture._configure(workspace)
        self.assertTrue((workspace / '.git').is_dir())
        self.assertTrue((workspace / 'venture/.git').is_dir())
        self.assertFalse((home / 'projects/.git').exists())
        self.command(home, 'controlroom verify')
        self.plan(workspace).write_bytes(b'server plan\n')
        self.command(home, 'controlroom push "server checkpoint"')
        self.fixture.install(home, bash=True, workspace=workspace)
        # An installed entrypoint also infers its physical root without flags.
        run(checks.BASH, '--noprofile', '--norc', workspace / '.controlroom/install.sh',
            'windows-control', env=self.fixture.env(home))
        self.command(home, 'kitpull')
        self.assertEqual(self.plan(workspace).read_bytes(), b'server plan\n')
        for tool in ('.agents', '.claude'):
            skill = workspace / 'venture' / tool / 'skills/venture-example'
            self.assertFalse(checks.os.path.islink(skill))
            self.assertEqual((skill / 'SKILL.md').read_bytes(), b'Venture workflow\n')
            self.assertEqual((skill / 'references/detail.md').read_bytes(), b'Venture reference\n')
        for code, expected in baseline.items():
            self.assertEqual(((code / '.git/index').read_bytes(),
                              run('git', 'rev-parse', 'HEAD', cwd=code).stdout,
                              run('git', 'status', '--porcelain', cwd=code).stdout), expected)
            self.assertEqual((code / 'app.py').read_bytes(), b'operating code\n')
            self.assertEqual((code / '.env').read_bytes(), b'SYNTHETIC=preserve\r\n')

    def test_pull_uses_existing_same_repository_ssh_authentication(self):
        home, repo = self.device()
        for target, remote, name in [(repo, self.fixture.remote, 'controlroom'),
                                      (repo / 'venture', self.fixture.product_remote, 'venture')]:
            origin = f'git@github.com:chaconne67/{name}.git'
            run('git', 'remote', 'set-url', 'origin', origin, cwd=target)
            run('git', 'config', f'url.{remote.as_uri()}.insteadOf', origin, cwd=target)
        (self.fixture.seed / '.controlroom/common.txt').write_bytes(b'updated through SSH\n')
        self.fixture.commit_seed('SSH update', True)
        self.command(home)
        self.assertEqual((repo / '.controlroom/common.txt').read_bytes(), b'updated through SSH\n')
        for target, name in [(repo, 'controlroom'), (repo / 'venture', 'venture')]:
            self.assertEqual(run('git', 'config', '--get', 'remote.origin.url', cwd=target).stdout.strip(),
                             f'git@github.com:chaconne67/{name}.git')
        self.command(home, 'controlroom verify')

    def test_two_devices_round_trip_tools_planning_and_code(self):
        a, ra = self.device(True)
        b, rb = self.device()
        self.plan(ra).write_bytes('다음 단계\r\n검증\n'.encode())
        (ra / '.controlroom/common.txt').write_text('new tools\n')
        code = a / 'projects/venture'
        (code / 'app.py').write_text('committed code\n')
        run('git', 'add', 'app.py', cwd=code)
        run('git', 'commit', '-m', 'code', cwd=code)
        self.command(a, 'controlroom push "A checkpoint"')
        self.command(b)
        self.assertEqual(self.plan(ra).read_bytes(), self.plan(rb).read_bytes())
        self.assertEqual((rb / '.controlroom/common.txt').read_text(), 'new tools\n')
        self.assertEqual((b / 'projects/venture/app.py').read_text(), 'committed code\n')
        self.plan(rb).write_bytes(b'B next step\n')
        self.command(b, 'kitpush "compatibility alias"')
        self.command(a, 'kitpull')
        self.assertEqual(self.plan(ra).read_bytes(), b'B next step\n')
        for repo in (ra, rb):
            self.assertEqual(run('git', 'status', '--porcelain', cwd=repo).stdout, '')

    def test_dirty_product_code_preserved_and_planning_saved(self):
        home, repo = self.device()
        code = repo / 'venture'
        (code / 'app.py').write_text('unfinished\n')
        (code / 'private.txt').write_text('keep\n')
        run('git', 'add', 'app.py', cwd=code)
        staged = run('git', 'diff', '--cached', '--binary', cwd=code).stdout
        self.plan(repo).write_bytes(b'saved plan\n')
        (repo / '.env').write_text('SYNTHETIC=value\n')
        self.command(home, 'controlroom push')
        self.assertEqual(run('git', 'diff', '--cached', '--binary', cwd=code).stdout, staged)
        self.assertEqual((code / 'private.txt').read_text(), 'keep\n')
        self.assertEqual(run('git', '--git-dir', self.fixture.remote, 'show', 'main:rndlog/docs/plan.md').stdout, 'saved plan\n')
        self.assertNotIn('.env', run('git', '--git-dir', self.fixture.remote, 'ls-tree', '--name-only', 'main').stdout.splitlines())

    def test_dirty_plan_archived_and_latest_applied(self):
        a, ra = self.device()
        b, rb = self.device()
        (rb / '.controlroom/common.txt').write_text('remote tools\n')
        self.plan(rb).write_bytes(b'latest plan\n')
        self.command(b, 'controlroom push')
        before = (ra / '.git/HEAD').read_bytes()
        self.plan(ra).write_bytes(b'local unfinished plan\r\n')
        unique = ra / 'rndlog/docs/.old-hidden'
        unique.write_bytes(b'hidden local work\0')
        run('git', 'add', 'rndlog/docs/plan.md', cwd=ra)
        index = (ra / '.git/index').read_bytes()
        self.command(a)
        self.assertEqual(self.plan(ra).read_bytes(), b'latest plan\n')
        self.assertFalse(unique.exists())
        for path, expected in [(self.plan(ra), b'local unfinished plan\r\n'), (unique, b'hidden local work\0'), (ra / '.git/HEAD', before), (ra / '.git/index', index)]:
            self.assertEqual(self.fixture.backed_up(a, path), expected)
        self.assertEqual((ra / '.controlroom/common.txt').read_text(), 'remote tools\n')

    def test_plan_conflict_aborts_and_preserves_both_commits(self):
        a, ra = self.device()
        b, rb = self.device()
        self.plan(ra).write_bytes(b'A decision\n')
        self.command(a, 'controlroom push')
        self.plan(rb).write_bytes(b'B decision\n')
        self.assertNotEqual(self.command(b, 'controlroom push', False).returncode, 0)
        self.assertEqual(self.plan(rb).read_bytes(), b'B decision\n')
        self.assertFalse((rb / '.git/rebase-merge').exists())
        self.assertEqual(run('git', 'rev-list', '--left-right', '--count', 'HEAD...origin/main', cwd=rb).stdout.strip(), '1\t1')

    def test_wrong_main_origin_prevents_private_document_upload(self):
        home, repo = self.device()
        self.plan(repo).write_bytes(b'private plan\n')
        run('git', 'remote', 'set-url', 'origin', 'https://github.com/chaconne67/kmh-agent-kit.git', cwd=repo)
        self.assertNotEqual(self.command(home, 'controlroom push', False).returncode, 0)
        self.assertEqual(self.plan(repo).read_bytes(), b'private plan\n')
        self.assertEqual(run('git', '--git-dir', self.fixture.remote, 'show', 'main:rndlog/docs/plan.md').stdout, 'first step\n')

    def test_separate_main_push_destination_rejected_before_commit(self):
        home, repo = self.device()
        self.plan(repo).write_bytes(b'private plan\n')
        before = run('git', 'rev-parse', 'HEAD', cwd=repo).stdout
        run('git', 'config', 'remote.origin.pushurl', 'https://github.com/unrelated/repo.git', cwd=repo)
        self.assertNotEqual(self.command(home, 'controlroom push', False).returncode, 0)
        self.assertEqual(run('git', 'rev-parse', 'HEAD', cwd=repo).stdout, before)

    def test_received_missing_source_fails_before_mutation(self):
        home, repo = self.device()
        before = run('git', 'rev-parse', 'HEAD', cwd=repo).stdout
        run('git', 'rm', '.controlroom/skills/example/SKILL.md', cwd=self.fixture.seed)
        self.fixture.commit_seed('missing required skill', True)
        result = self.command(home, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Invalid physical skill source', result.stderr)
        self.assertEqual(run('git', 'rev-parse', 'HEAD', cwd=repo).stdout, before)

    def test_unavailable_product_remote_keeps_published_planning(self):
        home, repo = self.device()
        self.plan(repo).write_bytes(b'checkpoint\n')
        self.fixture.product_remote = self.fixture.root / 'missing.git'
        self.assertNotEqual(self.command(home, 'controlroom push', False).returncode, 0)
        self.assertEqual(run('git', '--git-dir', self.fixture.remote, 'show', 'main:rndlog/docs/plan.md').stdout, 'checkpoint\n')

    def test_other_product_branch_archived_and_latest_main_applied(self):
        home, repo = self.device()
        code = repo / 'venture'
        run('git', 'checkout', '-b', 'ongoing', cwd=code)
        (code / 'app.py').write_bytes(b'unfinished code\n')
        (code / '.env').write_text('SYNTHETIC=keep\n')
        (code / 'local-runtime.txt').write_text('local runtime\n')
        run('git', 'config', 'credential.helper', 'synthetic-helper', cwd=code)
        old_head = (code / '.git/HEAD').read_bytes()
        self.command(home)
        self.assertEqual(run('git', 'branch', '--show-current', cwd=code).stdout.strip(), 'main')
        self.assertEqual((code / 'app.py').read_text(), 'initial\n')
        self.assertEqual(self.fixture.backed_up(home, code / 'app.py'), b'unfinished code\n')
        self.assertEqual(self.fixture.backed_up(home, code / '.git/HEAD'), old_head)
        self.assertEqual((code / '.env').read_text(), 'SYNTHETIC=keep\n')
        self.assertEqual((code / 'local-runtime.txt').read_text(), 'local runtime\n')
        self.assertEqual(run('git', 'config', 'credential.helper', cwd=code).stdout.strip(), 'synthetic-helper')

    def test_explicit_restore_recovers_docs_and_git_index(self):
        home, repo = self.device()
        if os.name != 'nt':
            (repo / 'rndlog/docs').chmod(0o700)
            (repo / '.controlroom/common.txt').chmod(0o444)
        plan = self.plan(repo)
        plan.write_bytes(b'old local state\r\n')
        run('git', 'add', 'rndlog/docs/plan.md', cwd=repo)
        index = (repo / '.git/index').read_bytes()
        self.command(home)
        archive = self.fixture.archive(home)
        self.command(home, f'controlroom restore "{archive}"')
        self.assertEqual(plan.read_bytes(), b'old local state\r\n')
        self.assertEqual((repo / '.git/index').read_bytes(), index)
        if os.name != 'nt':
            self.assertEqual((repo / 'rndlog/docs').stat().st_mode & 0o777, 0o700)
            self.assertEqual((repo / '.controlroom/common.txt').stat().st_mode & 0o777, 0o444)

    def test_product_failure_before_backup_preserves_all_local_state(self):
        home, repo = self.device()
        self.plan(repo).write_bytes(b'ongoing local plan\n')
        before = run('git', 'rev-parse', 'HEAD', cwd=repo).stdout
        self.fixture.product_remote = self.fixture.root / 'missing.git'
        result = self.command(home, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.plan(repo).read_bytes(), b'ongoing local plan\n')
        self.assertEqual(run('git', 'rev-parse', 'HEAD', cwd=repo).stdout, before)

    def test_existing_worktree_branch_and_staging_survive_pull(self):
        home, repo = self.device()
        worktree = home / 'unfinished-worktree'
        run('git', 'worktree', 'add', '-b', 'unfinished', worktree, cwd=repo)
        plan = worktree / 'rndlog/docs/plan.md'
        plan.write_bytes(b'worktree local progress\r\n')
        run('git', 'add', 'rndlog/docs/plan.md', cwd=worktree)
        before = run('git', 'diff', '--cached', '--binary', cwd=worktree).stdout
        staged = run('git', 'show', ':rndlog/docs/plan.md', cwd=worktree).stdout
        self.command(home)
        self.assertEqual(run('git', 'branch', '--show-current', cwd=worktree).stdout.strip(), 'unfinished')
        self.assertEqual(run('git', 'diff', '--cached', '--binary', cwd=worktree).stdout, before)
        self.assertEqual(run('git', 'show', ':rndlog/docs/plan.md', cwd=worktree).stdout, staged)
        self.assertEqual(plan.read_bytes(), b'worktree local progress\r\n')

    def test_legacy_root_migration_repairs_existing_worktree(self):
        home, repo = self.fixture.clone('rndlog')
        worktree = home / 'existing-worktree'
        run('git', 'worktree', 'add', '-b', 'unfinished', worktree, cwd=repo)
        plan = worktree / 'rndlog/docs/plan.md'
        plan.write_bytes(b'worktree data\n')
        run('git', 'add', 'rndlog/docs/plan.md', cwd=worktree)
        before = run('git', 'diff', '--cached', '--binary', cwd=worktree).stdout
        staged = run('git', 'show', ':rndlog/docs/plan.md', cwd=worktree).stdout
        legacy = home / 'kmh-agent-kit'
        repo.rename(legacy)
        run('git', 'worktree', 'repair', cwd=legacy)
        self.fixture.install(home, 'rndlog')
        self.assertFalse(legacy.exists())
        self.assertIn('/projects/.git/worktrees/', (worktree / '.git').read_text().replace(chr(92), '/'))
        self.assertEqual(run('git', 'branch', '--show-current', cwd=worktree).stdout.strip(), 'unfinished')
        self.assertEqual(run('git', 'diff', '--cached', '--binary', cwd=worktree).stdout, before)
        self.assertEqual(run('git', 'show', ':rndlog/docs/plan.md', cwd=worktree).stdout, staged)
        self.assertEqual(plan.read_bytes(), b'worktree data\n')

    def test_rollback_preserves_concurrent_changes_to_unmanaged_runtime_data(self):
        home, repo = self.device()
        runtime = repo / 'venture/local-runtime.txt'
        runtime.write_bytes(b'before backup\n')
        spec = importlib.util.spec_from_file_location('controlroom_core', ROOT / 'scripts/controlroom.py')
        core = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(core)
        copy = shutil.copy2
        def failure(source, destination, *args, **kwargs):
            if Path(destination) == home / '.codex/AGENTS.md':
                runtime.write_bytes(b'written by another process during apply\n')
                raise OSError('Synthetic OS failure replacing an instruction file')
            return copy(source, destination, *args, **kwargs)
        with patch.dict(os.environ, self.fixture.env(home)), patch.object(sys, 'argv',
                ['controlroom', '--home', str(home), 'install', '--source', str(self.fixture.seed)]), patch.object(shutil, 'copy2', side_effect=failure):
            self.assertEqual(core.main(), 1)
        self.assertEqual(runtime.read_bytes(), b'written by another process during apply\n')
        self.assertEqual(self.fixture.backed_up(home, runtime), b'before backup\n')


class MainServerTests(unittest.TestCase):
    def setUp(self):
        self.fixture = checks.KitFixture()
        self.addCleanup(self.fixture.close)

    def server(self):
        home = self.fixture.new_home(True)
        for name in ('rndlog', 'ceoloan', 'venture'):
            code = home / 'projects' / name
            branch = 'master' if name == 'ceoloan' else 'main'
            run('git', 'init', '--initial-branch=' + branch, code)
            self.fixture._configure(code)
            run('git', 'remote', 'add', 'product', 'https://example.invalid/' + name, cwd=code)
            for relative, content in {'app.py': b'operating code\n', 'docs/plan.md': b'product document\r\n',
                                      'AGENTS.md': b'# Existing product rules\r\nKeep the deployment contract.\r\n',
                                      'CLAUDE.md': b'# Existing Claude rules\n',
                                      'skills/local-skill/SKILL.md': b'local project skill\n',
                                      '.gitignore': b'.agents/\n.claude/\n.env\n'}.items():
                path = code / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
            run('git', 'add', '-A', cwd=code)
            run('git', 'commit', '-m', 'product baseline', cwd=code)
            (code / 'app.py').write_bytes(b'staged code\n')
            run('git', 'add', 'app.py', cwd=code)
            (code / 'app.py').write_bytes(b'unstaged work\n')
            (code / '.env').write_bytes(b'SYNTHETIC=preserve\n')
            (code / 'untracked.txt').write_bytes(b'untracked customer work\n')
            private = code / '.agents/skills/user-skill/SKILL.md'
            private.parent.mkdir(parents=True)
            private.write_bytes(b'user-owned skill\n')
        (home / 'controlroom').mkdir()
        (home / 'controlroom/keep.txt').write_bytes(b'legacy work\n')
        # Main mode must not contact the Venture product remote, even on push.
        self.fixture.product_remote = self.fixture.root / 'unavailable-product.git'
        return home

    def protected(self, home):
        paths = {}
        for item in (home / 'projects').rglob('*'):
            relative = item.relative_to(home / 'projects')
            if len(relative.parts) > 1 and relative.parts[1] in ('AGENTS.md', 'CLAUDE.md', '.agents', '.claude'):
                continue
            if item.is_file():
                paths[relative.as_posix()] = item.read_bytes()
        return paths

    def test_main_server_install_pull_verify_push_preserve_product_repositories(self):
        home = self.server()
        before = self.protected(home)
        original = (home / 'projects/rndlog/AGENTS.md').read_bytes()
        self.fixture.install(home, standalone=True, main_server=True)
        source = home / '.local/share/controlroom/source'
        self.fixture._configure(source)
        self.assertTrue((source / '.git').is_dir())
        self.assertFalse((home / 'projects/.git').exists())
        self.assertFalse((source / 'venture/.git').exists())
        self.assertEqual(self.protected(home), before)
        self.assertEqual((home / 'controlroom/keep.txt').read_bytes(), b'legacy work\n')
        self.assertTrue((home / 'projects/rndlog/AGENTS.md').read_bytes().startswith(original))
        self.assertEqual((home / 'projects/rndlog/.agents/skills/rndlog-example/SKILL.md').read_bytes(), b'project skill\n')
        self.assertEqual((home / 'projects/venture/.claude/skills/local-skill/SKILL.md').read_bytes(), b'local project skill\n')
        self.fixture.kit(home, 'controlroom verify')

        # A profile/source removed upstream is pruned only from managed placements.
        manifest_path = self.fixture.seed / '.controlroom/manifests/skills.json'
        data = json.loads(manifest_path.read_text())
        data['profiles']['projects']['rndlog'] = []
        del data['sources']['rndlog-example']
        del data['depends_on']['rndlog-example']
        shutil.rmtree(self.fixture.seed / 'rndlog/skills/rndlog-example')
        manifest_path.write_text(json.dumps(data))
        self.fixture.commit_seed('remove centrally managed project skill', True)
        self.fixture.kit(home, 'controlroom pull')
        self.fixture.kit(home, 'controlroom verify')
        self.assertFalse((home / 'projects/rndlog/.agents/skills/rndlog-example').exists())
        self.assertEqual((home / 'projects/rndlog/.agents/skills/user-skill/SKILL.md').read_bytes(), b'user-owned skill\n')
        self.assertEqual((home / 'projects/rndlog/AGENTS.md').read_bytes().count(b'<!-- controlroom:main-server:begin -->'), 1)
        (source / '.controlroom/common.txt').write_bytes(b'agent tool change\n')
        self.fixture.kit(home, 'controlroom push "main agent assets"')
        self.assertEqual(self.protected(home), before)
        self.assertTrue((home / 'projects/rndlog/AGENTS.md').read_bytes().startswith(original))
        self.assertEqual(run('git', '--git-dir', self.fixture.remote, 'show', 'main:.controlroom/common.txt').stdout, 'agent tool change\n')

    def test_main_server_failure_restores_instructions_and_leaves_code_untouched(self):
        home = self.server()
        before = self.protected(home)
        instructions = {path: path.read_bytes() for path in (home / 'projects').glob('*/AGENTS.md')}
        instructions.update({path: path.read_bytes() for path in (home / 'projects').glob('*/CLAUDE.md')})
        spec = importlib.util.spec_from_file_location('main_server_core', ROOT / 'scripts/controlroom.py')
        core = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(core)
        write = Path.write_bytes
        def failure(path, content):
            if path == home / 'projects/rndlog/CLAUDE.md':
                raise OSError('Synthetic failure writing a managed project instruction')
            return write(path, content)
        with patch.dict(os.environ, self.fixture.env(home)), patch.object(sys, 'argv',
                ['controlroom', '--home', str(home), '--main-server', 'install', '--source', str(self.fixture.seed)]), patch.object(Path, 'write_bytes', failure):
            self.assertEqual(core.main(), 1)
        self.assertEqual(self.protected(home), before)
        for path, content in instructions.items():
            self.assertEqual(path.read_bytes(), content)
        self.assertFalse((home / 'projects/rndlog/.agents/skills/rndlog-example').exists())
        self.assertEqual((home / 'projects/rndlog/.agents/skills/user-skill/SKILL.md').read_bytes(), b'user-owned skill\n')

    def test_custom_project_root_local_skills_and_saved_install_mode(self):
        home = self.server()
        before = self.protected(home)
        project_root = home / 'operating projects'
        (home / 'projects').rename(project_root)
        local = project_root / 'rndlog/skills/rndlog-example/SKILL.md'
        local.parent.mkdir()
        local.write_bytes(b'project-owned override\n')
        if os.name != 'nt':
            (project_root / 'venture/.agents/skills/local-skill').symlink_to('../../skills/local-skill', target_is_directory=True)
        self.fixture.install(home, standalone=True, workspace=project_root, main_server=True)
        source = home / '.local/share/controlroom/source'
        # Re-enter the installed core without mode/root flags, as an existing install does.
        run(sys.executable, source / '.controlroom/scripts/controlroom.py', 'install', env=self.fixture.env(home))
        self.fixture.kit(home, 'controlroom verify')
        self.assertFalse((home / 'projects').exists())
        self.assertEqual(local.read_bytes(), b'project-owned override\n')
        for tool in ('.agents', '.claude'):
            target = project_root / 'rndlog' / tool / 'skills/rndlog-example/SKILL.md'
            self.assertEqual(target.read_bytes(), local.read_bytes())
        self.assertEqual((project_root / 'venture/skills/local-skill/SKILL.md').read_bytes(), b'local project skill\n')
        self.assertFalse((project_root / 'venture/.agents/skills/local-skill').is_symlink())
        for relative, content in before.items():
            self.assertEqual((project_root / relative).read_bytes(), content)


if __name__ == '__main__':
    unittest.main(verbosity=2)
