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
        plan = self.plan(repo)
        plan.write_bytes(b'old local state\r\n')
        run('git', 'add', 'rndlog/docs/plan.md', cwd=repo)
        index = (repo / '.git/index').read_bytes()
        self.command(home)
        archive = self.fixture.archive(home)
        self.command(home, f'controlroom restore "{archive}"')
        self.assertEqual(plan.read_bytes(), b'old local state\r\n')
        self.assertEqual((repo / '.git/index').read_bytes(), index)

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
        self.command(home)
        self.assertEqual(run('git', 'branch', '--show-current', cwd=worktree).stdout.strip(), 'unfinished')
        self.assertEqual(run('git', 'diff', '--cached', '--binary', cwd=worktree).stdout, before)
        self.assertEqual(plan.read_bytes(), b'worktree local progress\r\n')

    def test_legacy_root_migration_repairs_existing_worktree(self):
        home, repo = self.fixture.clone('rndlog')
        worktree = home / 'existing-worktree'
        run('git', 'worktree', 'add', '-b', 'unfinished', worktree, cwd=repo)
        plan = worktree / 'rndlog/docs/plan.md'
        plan.write_bytes(b'worktree data\n')
        run('git', 'add', 'rndlog/docs/plan.md', cwd=worktree)
        before = run('git', 'diff', '--cached', '--binary', cwd=worktree).stdout
        legacy = home / 'kmh-agent-kit'
        repo.rename(legacy)
        run('git', 'worktree', 'repair', cwd=legacy)
        self.fixture.install(home, 'rndlog')
        self.assertFalse(legacy.exists())
        self.assertIn('/projects/.git/worktrees/', (worktree / '.git').read_text().replace(chr(92), '/'))
        self.assertEqual(run('git', 'branch', '--show-current', cwd=worktree).stdout.strip(), 'unfinished')
        self.assertEqual(run('git', 'diff', '--cached', '--binary', cwd=worktree).stdout, before)
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


if __name__ == '__main__':
    unittest.main(verbosity=2)
