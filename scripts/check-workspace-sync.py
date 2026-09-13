#!/usr/bin/env python3
"""Unified planning and tools share one Git history; product code stays separate."""
from __future__ import annotations
import importlib.util
import os
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('kit_checks',ROOT/'scripts/check-kit-sync.py')
checks=importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)
run=checks.run

class WorkspaceSyncTests(unittest.TestCase):
    def setUp(self):
        self.fixture=checks.KitFixture()
        self.addCleanup(self.fixture.close)
        seed=self.fixture.root/'venture-seed'
        self.remote=self.fixture.root/'venture.git'
        run('git','init','--initial-branch=main',seed)
        self.fixture._configure(seed)
        (seed/'app.py').write_text('initial\n')
        run('git','add','-A',cwd=seed)
        run('git','commit','-m','baseline',cwd=seed)
        run('git','clone','--bare',seed,self.remote)
        plan=self.fixture.seed/'projects/sample/docs/plan.md'
        plan.parent.mkdir(parents=True)
        plan.write_bytes(b'first step\r\n')
        (self.fixture.seed/'projects/.gitattributes').write_text('**/docs/** -text\n')
        (self.fixture.seed/'.gitignore').write_text('.env*\n*.pem\n')
        (self.fixture.seed/'manifests/windows-control-projects.tsv').write_text('venture\tgit\thttps://github.com/chaconne67/venture.git\n')
        (self.fixture.seed/'install.sh').write_text(
            '#!/usr/bin/env bash\nset -euo pipefail\n'
            'kit="$(cd "$(dirname "$0")" && pwd)"\n'
            '. "$kit/shell/kit-aliases.sh"\n'
            '_kit_restore_control_repositories "$kit" "$HOME"\n'
            '[ -f "$kit/projects/sample/docs/plan.md" ] || { echo "missing planning source" >&2; exit 1; }\n'
            'printf "%s\\n" "$1" >> "$HOME/install.log"\n')
        (self.fixture.seed/'install.sh').chmod(0o755)
        run('git','add','-A',cwd=self.fixture.seed)
        run('git','commit','-m','unified workspace',cwd=self.fixture.seed)
        run('git','push',cwd=self.fixture.seed)

    def command(self,home,command='controlroom pull',check=True):
        env=dict(os.environ,HOME=str(home),GIT_TERMINAL_PROMPT='0',GIT_ALLOW_PROTOCOL='file',
                 GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0=f'url.{self.remote.as_uri()}.insteadOf',
                 GIT_CONFIG_VALUE_0='https://github.com/chaconne67/venture.git')
        return run(checks.BASH,'--noprofile','--norc','-c',
                   '. "$HOME/controlroom/shell/kit-aliases.sh"; '+command,env=env,check=check)

    def device(self,spaces=False):
        home,old=self.fixture.clone('windows-control')
        repo=old.with_name('controlroom')
        old.rename(repo)
        if spaces:
            other=home.with_name(home.name+' Korean 조정실')
            home.rename(other)
            home,repo=other,other/'controlroom'
        self.command(home)
        self.fixture._configure(home/'projects/venture')
        return home,repo

    def plan(self,repo): return repo/'projects/sample/docs/plan.md'

    def test_two_devices_round_trip_tools_planning_and_code(self):
        a,ra=self.device(True); b,rb=self.device()
        self.plan(ra).write_bytes('다음 단계\r\n검증\n'.encode())
        (ra/'common.txt').write_text('new tools\n')
        code=a/'projects/venture'
        (code/'app.py').write_text('committed code\n')
        run('git','add','app.py',cwd=code); run('git','commit','-m','code',cwd=code)
        self.command(a,'controlroom push "A checkpoint"'); self.command(b)
        self.assertEqual(self.plan(ra).read_bytes(),self.plan(rb).read_bytes())
        self.assertEqual((rb/'common.txt').read_text(),'new tools\n')
        self.assertEqual((b/'projects/venture/app.py').read_text(),'committed code\n')
        self.plan(rb).write_bytes(b'B next step\n')
        self.command(b,'kitpush "compatibility alias"'); self.command(a,'kitpull')
        self.assertEqual(self.plan(ra).read_bytes(),b'B next step\n')
        for repo in (ra,rb): self.assertEqual(run('git','status','--porcelain',cwd=repo).stdout,'')

    def test_dirty_product_code_preserved_and_planning_saved(self):
        home,repo=self.device(); code=home/'projects/venture'
        (code/'app.py').write_text('unfinished\n'); (code/'private.txt').write_text('keep\n')
        run('git','add','app.py',cwd=code)
        staged=run('git','diff','--cached','--binary',cwd=code).stdout
        self.plan(repo).write_bytes(b'saved plan\n')
        (repo/'.env').write_text('SYNTHETIC=value\n')
        result=self.command(home,'controlroom push',False)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(run('git','diff','--cached','--binary',cwd=code).stdout,staged)
        self.assertEqual((code/'private.txt').read_text(),'keep\n')
        self.assertEqual(run('git','--git-dir',self.fixture.remote,'show','main:projects/sample/docs/plan.md').stdout,'saved plan\n')
        self.assertNotIn('.env',run('git','--git-dir',self.fixture.remote,'ls-tree','--name-only','main').stdout.splitlines())

    def test_dirty_plan_blocks_pull_before_any_remote_update(self):
        a,ra=self.device(); b,rb=self.device()
        (rb/'common.txt').write_text('remote tools\n'); self.command(b,'controlroom push')
        before=run('git','rev-parse','HEAD',cwd=ra).stdout
        self.plan(ra).write_bytes(b'local unfinished plan\n')
        self.assertNotEqual(self.command(a,check=False).returncode,0)
        self.assertEqual(run('git','rev-parse','HEAD',cwd=ra).stdout,before)
        self.assertEqual(self.plan(ra).read_bytes(),b'local unfinished plan\n')

    def test_plan_conflict_aborts_and_preserves_both_commits(self):
        a,ra=self.device(); b,rb=self.device()
        self.plan(ra).write_bytes(b'A decision\n'); self.command(a,'controlroom push')
        self.plan(rb).write_bytes(b'B decision\n')
        self.assertNotEqual(self.command(b,'controlroom push',False).returncode,0)
        self.assertEqual(self.plan(rb).read_bytes(),b'B decision\n')
        self.assertFalse((rb/'.git/rebase-merge').exists())
        self.assertEqual(run('git','rev-list','--left-right','--count','HEAD...origin/main',cwd=rb).stdout.strip(),'1\t1')

    def test_wrong_main_origin_prevents_private_document_upload(self):
        home,repo=self.device(); self.plan(repo).write_bytes(b'private plan\n')
        run('git','remote','set-url','origin','https://github.com/chaconne67/kmh-agent-kit.git',cwd=repo)
        self.assertNotEqual(self.command(home,'controlroom push',False).returncode,0)
        self.assertEqual(self.plan(repo).read_bytes(),b'private plan\n')
        self.assertEqual(run('git','--git-dir',self.fixture.remote,'show','main:projects/sample/docs/plan.md').stdout,'first step\n')

    def test_separate_main_push_destination_rejected_before_commit(self):
        home,repo=self.device(); self.plan(repo).write_bytes(b'private plan\n')
        before=run('git','rev-parse','HEAD',cwd=repo).stdout
        run('git','config','remote.origin.pushurl','https://github.com/unrelated/repo.git',cwd=repo)
        self.assertNotEqual(self.command(home,'controlroom push',False).returncode,0)
        self.assertEqual(run('git','rev-parse','HEAD',cwd=repo).stdout,before)

    def test_received_missing_document_fails_installer(self):
        home,repo=self.device(); seed=self.fixture.seed
        run('git','rm','projects/sample/docs/plan.md',cwd=seed)
        run('git','commit','-m','remove required planning source',cwd=seed); run('git','push',cwd=seed)
        result=self.command(home,check=False)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('missing planning source',result.stderr)

    def test_unavailable_product_remote_keeps_published_planning(self):
        home,repo=self.device(); self.plan(repo).write_bytes(b'checkpoint\n')
        self.remote=self.fixture.root/'missing.git'
        self.assertNotEqual(self.command(home,'controlroom push',False).returncode,0)
        self.assertEqual(run('git','--git-dir',self.fixture.remote,'show','main:projects/sample/docs/plan.md').stdout,'checkpoint\n')

    def test_other_product_branch_preserved(self):
        home,_=self.device(); code=home/'projects/venture'
        run('git','checkout','-b','ongoing',cwd=code)
        self.assertNotEqual(self.command(home,check=False).returncode,0)
        self.assertEqual(run('git','branch','--show-current',cwd=code).stdout.strip(),'ongoing')

if __name__=='__main__': unittest.main(verbosity=2)
