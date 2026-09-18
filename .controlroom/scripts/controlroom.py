#!/usr/bin/env python3
"""Controlroom's single install/update path. Python standard library only."""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid
import zipfile

ORIGIN = 'https://github.com/chaconne67/controlroom.git'
CENTRAL = {'main', 'windows-control'}
TOOLKIT = '.controlroom'
MEMORY_TASK = 'GBrain-Controlroom-Memory-Distill'


def run(*args, cwd=None, check=True):
    result = subprocess.run([str(a) for a in args], cwd=cwd, text=True,
                            encoding='utf-8', errors='replace', capture_output=True)
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f'{args[0]} failed')
    return result


def git(root, *args, check=True):
    return run('git', '-C', root, *args, check=check)


def exists(path):
    return os.path.lexists(path)


def linked(path):
    return path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction())


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def remove(path, home):
    # Check the lexical entry before removal; never follow a junction into its target.
    path = Path(os.path.abspath(path))
    if path == home or home not in path.parents:
        raise RuntimeError(f'Outside the approved workspace: {path}')
    if path.is_symlink():
        path.unlink()
    elif hasattr(path, 'is_junction') and path.is_junction():
        path.rmdir()
    elif path.is_dir():
        def writable_delete(func, name, error):
            os.chmod(name, stat.S_IWRITE | stat.S_IREAD)
            func(name)
        shutil.rmtree(path, onexc=writable_delete)
    elif exists(path):
        if os.name == 'nt' and not path.stat().st_mode & stat.S_IWRITE:
            path.chmod(path.stat().st_mode | stat.S_IWRITE)
        path.unlink()


def physical_parent(path, home):
    for parent in path.parents:
        if parent == home:
            return
        if linked(parent):
            raise RuntimeError(f'Linked parent must be migrated before use: {parent}')
    raise RuntimeError(f'Outside the approved workspace: {path}')


def scheduled_task():
    if os.name != 'nt':
        return None
    script = "[Console]::OutputEncoding=[Text.UTF8Encoding]::new(); $t=Get-ScheduledTask -ErrorAction Stop | Where-Object TaskName -eq '" + MEMORY_TASK + "'; if($t) { Export-ScheduledTask -TaskName $t.TaskName }"
    result = run('powershell.exe', '-NoProfile', '-Command', script)
    return result.stdout.strip() or None


def write_scheduled_task(xml, folder):
    with tempfile.TemporaryDirectory(prefix='task-', dir=folder) as temporary:
        path = Path(temporary) / 'task.xml'
        path.write_text(xml, encoding='utf-16')
        run('schtasks.exe', '/Create', '/TN', MEMORY_TASK, '/XML', path, '/F')


class Transaction:
    """Snapshot all declared targets before the first mutation; verify and restore."""
    def __init__(self, home, targets, archive_units=()):
        self.home = home
        self.targets = []
        self.archive_targets = []
        for items, result in [(list(targets), self.targets), (list(targets) + list(archive_units), self.archive_targets)]:
            ordered = sorted(set(Path(os.path.abspath(p)) for p in items), key=lambda p: len(p.parts))
            for path in ordered:
                if path == home or home not in path.parents:
                    raise RuntimeError(f'Outside the approved workspace: {path}')
                if not any(parent == path or parent in path.parents for parent in result):
                    physical_parent(path, home)
                    result.append(path)
        self.records = []
        self.archive = None
        self.registry = None
        self.task = None
        if os.name == 'nt':
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as key:
                try:
                    value, kind = winreg.QueryValueEx(key, 'Path')
                    self.registry = [value, kind]
                except FileNotFoundError:
                    self.registry = []
            xml = scheduled_task()
            if xml and any(str(home / name / 'gbrain/bin/memory_distill_controlroom.py') in xml for name in ('controlroom', 'kmh-agent-kit')):
                self.task = xml

    def backup(self):
        folder = self.home / 'backups/controlroom'
        folder.mkdir(parents=True, exist_ok=True)
        self.archive = folder / (datetime.now().strftime('%Y%m%d-%H%M%S-') + uuid.uuid4().hex[:8] + '.zip')
        inodes = {}
        try:
            with zipfile.ZipFile(self.archive, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
                def pack(path, label):
                    record = {'path': str(path), 'entry': label, 'restore': any(path == root or root in path.parents for root in self.targets)}
                    self.records.append(record)
                    if not exists(path):
                        record['kind'] = 'missing'
                    elif linked(path):
                        record.update(kind='junction' if not path.is_symlink() else 'link',
                                      target=os.readlink(path), directory=path.is_dir())
                    elif path.is_dir():
                        entries = sorted(path.iterdir())
                        record.update(kind='dir', mode=stat.S_IMODE(path.stat().st_mode), children=sorted(p.name for p in entries))
                        for item in entries:
                            pack(item, label + '/' + item.name)
                    else:
                        before = path.stat()
                        record.update(kind='file', mode=stat.S_IMODE(before.st_mode), size=before.st_size)
                        key = (before.st_dev, before.st_ino)
                        if before.st_nlink > 1 and key in inodes:
                            record['hardlink'] = inodes[key]
                        inodes[key] = str(path)
                        hasher = hashlib.sha256()
                        remaining = before.st_size
                        with path.open('rb') as source, archive.open(label, 'w', force_zip64=True) as target:
                            while remaining and (block := source.read(min(1024 * 1024, remaining))):
                                target.write(block)
                                hasher.update(block)
                                remaining -= len(block)
                        record['size'] = before.st_size - remaining
                        record['sha256'] = hasher.hexdigest()
                        after = path.stat()
                        if record['restore'] and (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
                            raise RuntimeError(f'Changed during backup: {path}')
                for index, path in enumerate(self.archive_targets):
                    pack(path, f'files/{index}')
                collected = {r['path'] for r in self.records}
                for index, path in enumerate(self.targets):
                    if str(path) not in collected:
                        pack(path, f'targets/{index}')
                archive.writestr('manifest.json', json.dumps({'records': self.records, 'targets': [str(p) for p in self.targets], 'registry': self.registry, 'task': self.task}, ensure_ascii=False))
            with zipfile.ZipFile(self.archive) as archive:
                if archive.testzip() is not None:
                    raise RuntimeError('Backup CRC verification failed')
                for record in self.records:
                    if record['kind'] == 'file':
                        with archive.open(record['entry']) as stream:
                            if hashlib.file_digest(stream, 'sha256').hexdigest() != record['sha256']:
                                raise RuntimeError(f"Backup verification failed: {record['path']}")
                        path = Path(record['path'])
                        if record['restore'] and (not path.is_file() or digest(path) != record['sha256']):
                            raise RuntimeError(f'Changed before apply: {path}')
                    elif record['restore'] and record['kind'] in {'link', 'junction'}:
                        if not linked(Path(record['path'])) or os.readlink(record['path']) != record['target']:
                            raise RuntimeError(f"Changed before apply: {record['path']}")
                    elif record['restore'] and record['kind'] == 'missing' and exists(record['path']):
                        raise RuntimeError(f"Changed before apply: {record['path']}")
                    elif record['restore'] and record['kind'] == 'dir':
                        path = Path(record['path'])
                        if linked(path) or not path.is_dir() or sorted(p.name for p in path.iterdir()) != record['children']:
                            raise RuntimeError(f'Changed before apply: {path}')
            print(f'Backup verified: {self.archive}', flush=True)
        except BaseException:
            if self.archive.exists():
                self.archive.unlink()
            raise

    def restore(self):
        original = {record['path']: record for record in self.records}
        def clean(path):
            if str(path) not in original or original[str(path)]['kind'] == 'missing':
                remove(path, self.home)
            elif path.is_dir() and not linked(path):
                for item in path.iterdir():
                    clean(item)
        for path in self.targets:
            if exists(path):
                clean(path)
        with zipfile.ZipFile(self.archive) as archive:
            for record in self.records:
                if not record.get('restore', True):
                    continue
                path = Path(record['path'])
                kind = record['kind']
                if kind == 'missing':
                    if exists(path):
                        remove(path, self.home)
                    continue
                if kind == 'dir':
                    if exists(path) and (linked(path) or not path.is_dir()):
                        remove(path, self.home)
                    path.mkdir(parents=True, exist_ok=True)
                    continue
                path.parent.mkdir(parents=True, exist_ok=True)
                if kind in {'link', 'junction'}:
                    if linked(path) and os.readlink(path) == record['target']:
                        continue
                    if exists(path):
                        remove(path, self.home)
                    if kind == 'junction' and os.name == 'nt':
                        target = record['target'].removeprefix('\\\\?\\')
                        run('cmd.exe', '/d', '/c', 'mklink', '/J', path, target)
                    else:
                        path.symlink_to(record['target'], target_is_directory=record['directory'])
                    continue
                hardlink = Path(record['hardlink']) if record.get('hardlink') else None
                same_link = not hardlink or (exists(path) and hardlink.exists() and path.stat().st_ino == hardlink.stat().st_ino and path.stat().st_dev == hardlink.stat().st_dev)
                if path.is_file() and not linked(path) and digest(path) == record['sha256'] and same_link:
                    continue
                if exists(path):
                    remove(path, self.home)
                if record.get('hardlink') and Path(record['hardlink']).exists():
                    os.link(record['hardlink'], path)
                else:
                    with archive.open(record['entry']) as source, path.open('wb') as target:
                        shutil.copyfileobj(source, target)
                    path.chmod(record['mode'])
        if self.registry is not None:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment', 0, winreg.KEY_SET_VALUE) as key:
                if self.registry:
                    winreg.SetValueEx(key, 'Path', 0, self.registry[1], self.registry[0])
                else:
                    try:
                        winreg.DeleteValue(key, 'Path')
                    except FileNotFoundError:
                        pass
        if self.task and scheduled_task() != self.task:
            write_scheduled_task(self.task, self.home / '.local/share/controlroom/tmp')
        for record in self.records:
            if not record.get('restore', True):
                continue
            path, kind = Path(record['path']), record['kind']
            if kind == 'missing':
                correct = not exists(path)
            elif kind in {'link', 'junction'}:
                correct = linked(path) and os.readlink(path) == record['target']
            elif kind == 'dir':
                correct = path.is_dir() and not linked(path) and sorted(p.name for p in path.iterdir()) == record['children']
            else:
                correct = path.is_file() and not linked(path) and digest(path) == record['sha256']
            if not correct:
                raise RuntimeError(f'Restored state did not match: {path}')
        print(f'Previous state restored from: {self.archive}', flush=True)


def manifest(root):
    return json.loads((root / TOOLKIT / 'manifests/skills.json').read_text(encoding='utf-8'))


def project_names(root, data):
    names = set(data['profiles']['projects'])
    names |= {p.split('/')[0] for p in data['sources'].values() if not p.startswith('.controlroom/')}
    for relative in git(root, 'ls-files', '-z', check=False).stdout.split('\0'):
        parts = Path(relative).parts
        if len(parts) > 1 and not parts[0].startswith('.') and parts[0] != 'venture' and parts[1] in {'docs', 'skills', 'AGENTS.md', 'CLAUDE.md'}:
            names.add(parts[0])
    return names


def validate(root):
    data = manifest(root)
    paths = data['sources']
    for name in data['profiles']['projects']:
        if not re.fullmatch(r'[A-Za-z0-9_-]+', name):
            raise RuntimeError(f'Invalid project directory: {name}')
    units = [root / TOOLKIT, root / '.github']
    units += [root / name / unit for name in project_names(root, data) for unit in ('docs', 'skills', 'AGENTS.md', 'CLAUDE.md')]
    for unit in units:
        if linked(unit) or (unit.is_dir() and any(linked(p) for p in unit.rglob('*'))):
            raise RuntimeError(f'Managed source must contain physical entries: {unit}')
    for name, relative in paths.items():
        path = root / relative
        if name != path.name or Path(relative).is_absolute() or '..' in Path(relative).parts or linked(path) or not (path / 'SKILL.md').is_file():
            raise RuntimeError(f'Invalid physical skill source: {name}: {relative}')
        for item in path.rglob('*'):
            if linked(item):
                raise RuntimeError(f'Skill source contains a link: {item}')
    for relative in ('install.ps1', 'install.sh', 'scripts/controlroom.py', 'codex/AGENTS.md', 'claude/CLAUDE.md', 'shell/kit-aliases.sh', 'manifests/windows-control-projects.tsv'):
        if not (root / TOOLKIT / relative).is_file():
            raise RuntimeError(f'Missing installation source: {relative}')
    actual = {p.parent.relative_to(root).as_posix() for p in (root / TOOLKIT / 'skills').glob('*/SKILL.md')}
    actual |= {p.parent.relative_to(root).as_posix() for p in root.glob('*/skills/*/SKILL.md')}
    if actual != set(paths.values()):
        raise RuntimeError('Skill sources and manifest differ')
    for name, dependencies in data['depends_on'].items():
        if any(n not in paths for n in [name, *dependencies]):
            raise RuntimeError(f'Unknown dependency source: {name}')
    profiles = data['profiles']
    global_names = set(profiles['global'])
    for name in global_names:
        if not paths[name].startswith('.controlroom/skills/'):
            raise RuntimeError(f'Project skill in global profile: {name}')
    for names in [global_names, *(set(names) | global_names for names in profiles['projects'].values())]:
        for name in names:
            if name not in paths:
                raise RuntimeError(f'Unknown skill: {name}')
            for dependency in data['depends_on'].get(name, []):
                if dependency not in names:
                    raise RuntimeError(f'Missing dependency: {name} -> {dependency}')
    return data


def repositories(root):
    path = root / TOOLKIT / 'manifests/windows-control-projects.tsv'
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line or line.startswith('#'):
            continue
        name, kind, target = line.split('\t')
        if not re.fullmatch(r'[A-Za-z0-9_-]+', name):
            raise RuntimeError('Invalid project directory')
        if kind == 'git':
            if not re.fullmatch(r'https://github\.com/[^/]+/[^/]+\.git', target):
                raise RuntimeError('Invalid project origin')
            yield name, target
        elif kind != 'profile':
            raise RuntimeError('Invalid project kind')


def config(root):
    if not (root / '.git').exists():
        return []
    result = git(root, 'config', '--local', '--null', '--list', check=False)
    return [tuple(item.split('\n', 1)) for item in result.stdout.split('\0') if '\n' in item]


def clone(url, destination, existing=None):
    args = ['git']
    if existing and (existing / '.git').exists():
        for key, value in config(existing):
            if key.startswith('url.') and key.endswith('.insteadof'):
                args.extend(['-c', f'{key}={value}'])
    args.extend(['clone', '--no-hardlinks', '--branch', 'main', '--single-branch', url, str(destination)])
    run(*args)


def preserve_worktrees(source, existing):
    if not (existing / '.git').exists():
        return []
    registered = git(existing, 'worktree', 'list', '--porcelain', '-z').stdout
    paths, commits = [], []
    for block in registered.split('\0\0'):
        fields = dict(item.split(' ', 1) for item in block.split('\0') if ' ' in item)
        if 'worktree' in fields and Path(fields['worktree']).resolve() != existing.resolve():
            paths.append(Path(fields['worktree']))
            commits.append(fields['HEAD'])
    if not paths:
        return []
    refs = git(existing, 'for-each-ref', '--format=%(refname)', 'refs/heads', 'refs/tags').stdout.splitlines()
    refs = [f'+{ref}:{ref}' for ref in refs if ref != 'refs/heads/main']
    if refs:
        git(source, 'fetch', '--quiet', '--no-tags', str(existing), *refs)
    for commit in commits:
        if git(source, 'cat-file', '-e', commit + '^{commit}', check=False).returncode:
            git(source, 'fetch', '--quiet', '--no-tags', str(existing), commit)
    common = Path(git(existing, 'rev-parse', '--git-common-dir').stdout.strip())
    if not common.is_absolute():
        common = existing / common
    # Staged worktree blobs may be unreachable from every branch/tag.
    for item in (common / 'objects').rglob('*'):
        destination = source / '.git/objects' / item.relative_to(common / 'objects')
        if item.is_file() and not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, destination)
    if (common / 'worktrees').is_dir():
        shutil.copytree(common / 'worktrees', source / '.git/worktrees', dirs_exist_ok=True)
    return paths


def agent_for(root):
    for key in ('controlroom.agent', 'kmh-agent-kit.agent'):
        result = git(root, 'config', '--local', '--get', key, check=False)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    return 'windows-control'


def global_homes(home):
    hermes = Path(os.environ.get('HERMES_HOME', str(Path(os.environ.get('LOCALAPPDATA', str(home))) / 'hermes' if os.name == 'nt' else str(home / '.hermes'))))
    return {'claude': Path(os.environ.get('CLAUDE_HOME', str(home / '.claude'))),
            'codex': Path(os.environ.get('CODEX_HOME', str(home / '.codex'))),
            'agents': home / '.agents', 'hermes': hermes}


def replace(source, destination, home):
    if exists(destination):
        remove(destination, home)
    if source is not None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, destination, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        else:
            shutil.copy2(source, destination)


def shell_content(path, marker, line):
    content = path.read_bytes().decode('utf-8') if path.is_file() else ''
    # Replace only our installer block, keeping other shell configuration.
    content = re.sub(r'(?m)^# kmh-agent-kit aliases\r?\n[^\r\n]*\r?\n?', '', content)
    pattern = r'(?m)^# ' + re.escape(marker) + r'\r?\n[^\r\n]*'
    block = '# ' + marker + '\n' + line
    if re.search(pattern, content):
        return re.sub(pattern, lambda match: block, content)
    return content.rstrip('\n') + '\n\n' + block + '\n'


def apply(source, home, agent, products, preserve_config=None, legacy_cleanup=True, refresh_only=False, worktrees=()):
    workspace = home / 'projects'
    if source.resolve() == workspace.resolve() or not (source / '.git').is_dir():
        raise RuntimeError('Installation requires an independent prepared Git clone')
    data = validate(source)
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,31}', agent) or not (source / TOOLKIT / 'gbrain-cards' / (agent + '.md')).is_file():
        raise RuntimeError(f'Unknown registered role: {agent}')
    old_config = preserve_config if preserve_config is not None else config(workspace)
    previous_profiles = next((json.loads(value) for key, value in old_config if key == 'controlroom.installedprofiles'), {'global': [], 'projects': {}, 'hermes': []})
    copies = [] if refresh_only else [(source / TOOLKIT, workspace / TOOLKIT), (source / '.git', workspace / '.git')]
    for name in ('.github', 'README.md', '.gitignore', '.gitattributes'):
        if not refresh_only and (source / name).exists():
            copies.append((source / name, workspace / name))
    for project_name in project_names(source, data):
        project = source / project_name
        if not refresh_only and project.is_dir():
            for name in ('docs', 'skills', 'AGENTS.md', 'CLAUDE.md'):
                if (project / name).exists():
                    copies.append((project / name, workspace / project.name / name))
    if not refresh_only and (workspace / '.git').exists():
        previous_units = set()
        for relative in git(workspace, 'ls-files', '-z').stdout.split('\0'):
            parts = Path(relative).parts
            if len(parts) > 1 and not parts[0].startswith('.') and parts[0] != 'venture' and parts[1] in {'docs', 'skills', 'AGENTS.md', 'CLAUDE.md'}:
                previous_units.add(Path(*parts[:2]))
        for unit in sorted(previous_units):
            if not exists(source / unit):
                copies.append((None, workspace / unit))
    product_config = {name: config(workspace / name) for name in products}
    for name, stage in products.items():
        target = workspace / name
        copies.append((stage / '.git', target / '.git'))
        incoming = set(git(stage, 'ls-files', '-z').stdout.split('\0')) - {''}
        previous = (set(git(target, 'ls-files', '-z').stdout.split('\0')) - {''}) if (target / '.git').exists() else set()
        for relative in sorted(incoming | previous):
            if '..' in Path(relative).parts or Path(relative).is_absolute():
                raise RuntimeError('Unsafe tracked product path')
            if Path(relative).name.startswith('.env') or Path(relative).suffix in {'.pem', '.key', '.p12', '.pfx'}:
                continue
            if any(linked(parent) for parent in (target / relative).parents if parent != target and target in parent.parents):
                continue
            copies.append((stage / relative if relative in incoming else None, target / relative))
        for skill in sorted((stage / 'skills').glob('*/SKILL.md')):
            for tool in ('.agents', '.claude'):
                copies.append((skill.parent, target / tool / 'skills' / skill.parent.name))
    homes = global_homes(home)
    copies.extend([(source / TOOLKIT / 'codex/AGENTS.md', homes['codex'] / 'AGENTS.md'),
                   (source / TOOLKIT / 'claude/CLAUDE.md', homes['claude'] / 'CLAUDE.md'),
                   (source / TOOLKIT / 'gbrain-cards' / (agent + '.md'), home / '.gbrain-agent.md')])
    hermes_owned = []
    legacy_roots = [str(home / 'controlroom'), str(home / 'kmh-agent-kit'), str(workspace / TOOLKIT)]
    def owned_link(path):
        if not linked(path):
            return False
        target = os.readlink(path).removeprefix('\\\\?\\')
        target = os.path.abspath(path.parent / target)
        return any(os.path.normcase(target).startswith(os.path.normcase(root + os.sep)) for root in legacy_roots)
    for name in data['profiles']['global']:
        for tool in ('agents', 'claude', 'hermes'):
            destination = homes[tool] / 'skills' / name
            if tool == 'hermes' and exists(destination) and name not in previous_profiles.get('hermes', []) and not owned_link(destination):
                continue
            if tool == 'hermes':
                hermes_owned.append(name)
            copies.append((source / data['sources'][name], destination))
    for name in set(previous_profiles.get('global', [])) - set(data['profiles']['global']):
        for tool in ('agents', 'claude'):
            copies.append((None, homes[tool] / 'skills' / name))
    for name in set(previous_profiles.get('hermes', [])) - set(hermes_owned):
        copies.append((None, homes['hermes'] / 'skills' / name))
    for project, names in data['profiles']['projects'].items():
        for name in names:
            for tool in ('.agents', '.claude'):
                copies.append((source / data['sources'][name], workspace / project / tool / 'skills' / name))
    for project, names in previous_profiles.get('projects', {}).items():
        for name in set(names) - set(data['profiles']['projects'].get(project, [])):
            for tool in ('.agents', '.claude'):
                copies.append((None, workspace / project / tool / 'skills' / name))
    legacy = [home / 'controlroom', home / 'kmh-agent-kit', workspace / '_control-docs'] if legacy_cleanup else []
    # Remove old managed skill placements without touching system/plugin/user assets.
    for folder in [homes['codex'] / 'skills', *(homes[tool] / 'skills' for tool in ('agents', 'claude', 'hermes')), *(workspace / project / tool / 'skills' for project in data['profiles']['projects'] for tool in ('.codex', '.agents', '.claude'))]:
        if folder.is_dir():
            for entry in folder.iterdir():
                if owned_link(entry) and not any(destination == entry for _, destination in copies):
                    copies.append((None, entry))
    command_dir = home / '.local/bin'
    command_names = ('controlroom', 'kitpull', 'kitpush')
    files = {command_dir / (name + '.cmd' if os.name == 'nt' else name): '' for name in command_names}
    for name in command_names:
        action = 'pull ' if name == 'kitpull' else 'push ' if name == 'kitpush' else ''
        script = workspace / TOOLKIT / 'scripts/controlroom.py'
        if os.name == 'nt':
            files[command_dir / (name + '.cmd')] = f'@"{sys.executable}" -X utf8 "{script}" --home "{home}" {action}%*\r\n'
        files[command_dir / name] = f'#!/usr/bin/env bash\nexec "{Path(sys.executable).as_posix()}" -X utf8 "{script.as_posix()}" --home "{home.as_posix()}" {action}"$@"\n'
    proxy_roles = {agent} if agent not in CENTRAL else set()
    if command_dir.is_dir():
        for entry in command_dir.glob('gbrain-*'):
            if entry.is_file() and not linked(entry):
                content = entry.read_text(encoding='utf-8', errors='replace')
                role = entry.name.removesuffix('.cmd').removeprefix('gbrain-')
                if 'gbrain-remote-proxy' in content and ('kmh-agent-kit/gbrain' in content or 'controlroom/gbrain' in content) and (source / TOOLKIT / 'gbrain-cards' / (role + '.md')).is_file():
                    proxy_roles.add(role)
    for proxy_role in sorted(proxy_roles):
        proxy = workspace / TOOLKIT / 'gbrain/bin/gbrain-remote-proxy'
        files[command_dir / ('gbrain-' + proxy_role)] = f'#!/usr/bin/env bash\nexec bash "{proxy.as_posix()}" {proxy_role} "$@"\n'
        if os.name == 'nt':
            bash = Path(shutil.which('git')).resolve().parents[1] / 'bin/bash.exe'
            files[command_dir / ('gbrain-' + proxy_role + '.cmd')] = f'@"{bash}" --noprofile --norc "{proxy}" {proxy_role} %*\r\n'
    for name in ('.bashrc', '.zshrc'):
        path = home / name
        files[path] = shell_content(path, 'controlroom commands', '[ -f "$HOME/projects/.controlroom/shell/kit-aliases.sh" ] && . "$HOME/projects/.controlroom/shell/kit-aliases.sh"')
    path = home / '.bash_profile'
    files[path] = shell_content(path, 'load ~/.bashrc for kmh-agent-kit', '[ -f "$HOME/.bashrc" ] && . "$HOME/.bashrc"')
    tx = Transaction(home, [destination for _, destination in copies] + list(files) + legacy + ([workspace / '.git/config'] if refresh_only else []) + [path / '.git' for _, paths in worktrees for path in paths], archive_units=[workspace / name for name in products])
    tx.backup()
    try:
        for original, destination in copies:
            replace(original, destination, home)
            if original is not None:
                verify_copy(original, destination)
        restored_keys = set()
        for key, value in old_config:
            if key.startswith(('url.', 'user.', 'credential.', 'kmh-agent-kit.', 'controlroom.')) or (key.startswith('branch.') and not key.startswith('branch.main.')):
                if key not in restored_keys:
                    git(workspace, 'config', '--local', '--unset-all', key, check=False)
                    restored_keys.add(key)
                git(workspace, 'config', '--local', '--add', key, value)
        git(workspace, 'remote', 'set-url', 'origin', ORIGIN)
        git(workspace, 'config', '--local', 'controlroom.agent', agent)
        installed_profiles = dict(data['profiles'], hermes=hermes_owned)
        git(workspace, 'config', '--local', 'controlroom.installedProfiles', json.dumps(installed_profiles, ensure_ascii=False))
        git(workspace, 'branch', '--set-upstream-to=origin/main', 'main')
        for name, stage in products.items():
            target = workspace / name
            for key, value in product_config[name]:
                if not key.startswith(('core.', 'branch.main.', 'remote.')):
                    git(target, 'config', '--local', '--add', key, value)
        for path, content in files.items():
            if exists(path):
                remove(path, home)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content.encode('utf-8'))
            path.chmod(0o755)
        if os.name == 'nt':
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment', 0, winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE) as key:
                try:
                    value, kind = winreg.QueryValueEx(key, 'Path')
                except FileNotFoundError:
                    value, kind = '', winreg.REG_EXPAND_SZ
                entries = value.split(';') if value else []
                if os.path.normcase(str(command_dir)) not in {os.path.normcase(p.rstrip('\\/')) for p in entries}:
                    entries.append(str(command_dir))
                    winreg.SetValueEx(key, 'Path', 0, kind, ';'.join(entries))
        for original, destination in copies:
            if original is not None:
                if destination.name != '.git':
                    verify_copy(original, destination)
            elif exists(destination):
                raise RuntimeError(f'Removed managed entry remains: {destination}')
        verify(workspace, home, agent)
        for root, paths in worktrees:
            git(root, 'worktree', 'repair', *paths)
            for path in paths:
                if Path(git(path, 'rev-parse', '--git-common-dir').stdout.strip()).resolve() != (root / '.git').resolve():
                    raise RuntimeError(f'Existing worktree repair failed: {path}')
        if tx.task:
            xml = tx.task
            for name in ('controlroom', 'kmh-agent-kit'):
                xml = xml.replace(str(home / name / 'gbrain/bin/memory_distill_controlroom.py'), str(workspace / TOOLKIT / 'gbrain/bin/memory_distill_controlroom.py'))
            write_scheduled_task(xml, home / '.local/share/controlroom/tmp')
            if str(workspace / TOOLKIT / 'gbrain/bin/memory_distill_controlroom.py') not in scheduled_task():
                raise RuntimeError('Existing memory task path migration failed')
        for path in legacy:
            if exists(path):
                remove(path, home)
    except BaseException:
        try:
            tx.restore()
        except BaseException as error:
            raise RuntimeError(f'Rollback incomplete: {error}. Recovery archive: {tx.archive}') from error
        raise
    print(f'Applied and verified: {workspace}', flush=True)


def verify_copy(source, target):
    if linked(target) or not exists(target):
        raise RuntimeError(f'Copy must be physical: {target}')
    if source.is_dir():
        def items(folder):
            return {p.relative_to(folder).as_posix(): p for p in folder.rglob('*') if '__pycache__' not in p.parts and p.suffix != '.pyc'}
        originals, installed = items(source), items(target)
        if originals.keys() != installed.keys():
            raise RuntimeError(f'Copied contents differ: {target}')
        for name, path in originals.items():
            if linked(installed[name]) or (path.is_file() and digest(path) != digest(installed[name])):
                raise RuntimeError(f'Copied content differs: {installed[name]}')
    elif digest(source) != digest(target):
        raise RuntimeError(f'Copied content differs: {target}')


def verify(workspace, home, agent):
    data = validate(workspace)
    homes = global_homes(home)
    for relative, target in [('codex/AGENTS.md', homes['codex'] / 'AGENTS.md'), ('claude/CLAUDE.md', homes['claude'] / 'CLAUDE.md'), ('gbrain-cards/' + agent + '.md', home / '.gbrain-agent.md')]:
        if linked(target) or digest(workspace / TOOLKIT / relative) != digest(target):
            raise RuntimeError(f'Installed instructions do not match: {target}')
    for project, names in data['profiles']['projects'].items():
        docs = workspace / project / 'docs'
        if linked(docs):
            raise RuntimeError(f'Project docs must be a physical directory: {docs}')
        for name in names:
            source = workspace / data['sources'][name]
            for tool in ('.claude', '.agents'):
                target = workspace / project / tool / 'skills' / name
                if linked(target) or not target.is_dir():
                    raise RuntimeError(f'Installed skill must be a physical directory: {target}')
                verify_copy(source, target)
    installed = dict(config(workspace)).get('controlroom.installedprofiles', '{}')
    hermes_owned = set(json.loads(installed).get('hermes', []))
    for name in data['profiles']['global']:
        for tool in ('agents', 'claude', 'hermes'):
            if tool == 'hermes' and name not in hermes_owned:
                continue
            target = homes[tool] / 'skills' / name
            verify_copy(workspace / data['sources'][name], target)


def update(home, agent=None, prepared=None):
    workspace = home / 'projects'
    role = agent or agent_for(workspace)
    cache = home / '.local/share/controlroom/tmp'
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='update-', dir=cache) as temporary:
        temporary = Path(temporary)
        source = temporary / 'incoming'
        if prepared is None:
            clone(ORIGIN, source, workspace)
        else:
            validate(prepared)
            run('git', 'clone', '--no-hardlinks', str(prepared), str(source))
            git(source, 'branch', '-M', 'main')
            for item in prepared.iterdir():
                if item.name == TOOLKIT or item.name in {'.github', 'README.md', '.gitignore', '.gitattributes'}:
                    replace(item, source / item.name, home)
                elif item.name in project_names(prepared, manifest(prepared)):
                    for name in ('docs', 'skills', 'AGENTS.md', 'CLAUDE.md'):
                        if (item / name).exists():
                            replace(item / name, source / item.name / name, home)
        validate(source)
        existing = next((path for path in (workspace, home / 'kmh-agent-kit', home / 'controlroom') if (path / '.git').exists()), workspace)
        worktrees = [(workspace, preserve_worktrees(source, existing))]
        products = {}
        if role in CENTRAL:
            for name, origin in repositories(source):
                stage = temporary / name
                clone(origin, stage, workspace / name)
                products[name] = stage
                worktrees.append((workspace / name, preserve_worktrees(stage, workspace / name)))
        previous = config(existing)
        apply(source, home, role, products, preserve_config=previous, worktrees=[(root, paths) for root, paths in worktrees if paths])


def restore_archive(home, path):
    folder = home / 'backups/controlroom'
    if folder not in path.resolve().parents:
        raise RuntimeError('Recovery archive must be in ~/backups/controlroom')
    with zipfile.ZipFile(path) as archive:
        saved = json.loads(archive.read('manifest.json'))
        if archive.testzip() is not None:
            raise RuntimeError('Recovery archive failed verification')
        for record in saved['records']:
            if record['kind'] == 'file':
                with archive.open(record['entry']) as stream:
                    if hashlib.file_digest(stream, 'sha256').hexdigest() != record['sha256']:
                        raise RuntimeError('Recovery file failed verification')
    tx = Transaction(home, [Path(p) for p in saved.get('targets', [r['path'] for r in saved['records']])])
    tx.archive, tx.records, tx.registry = path, saved['records'], saved['registry']
    tx.task = saved.get('task')
    tx.restore()


def github_repository(url):
    for prefix in ('https://github.com/', 'git@github.com:', 'ssh://git@github.com/'):
        if url.startswith(prefix):
            return url[len(prefix):].removesuffix('.git')
    return None


def check_origin(root, expected):
    urls = [git(root, 'config', '--get', 'remote.origin.url').stdout.strip()]
    urls += git(root, 'config', '--get-all', 'remote.origin.pushurl', check=False).stdout.splitlines()
    if any(github_repository(url) != github_repository(expected) for url in urls):
        raise RuntimeError(f'origin or push destination is not the registered repository: {root}')


def check_main(root):
    if git(root, 'symbolic-ref', '--quiet', '--short', 'HEAD', check=False).stdout.strip() != 'main':
        raise RuntimeError(f'Push requires main branch (main 브랜치): {root}')
    for marker in ('MERGE_HEAD', 'rebase-merge', 'rebase-apply', 'CHERRY_PICK_HEAD', 'REVERT_HEAD'):
        result = git(root, 'rev-parse', '--git-path', marker).stdout.strip()
        if (root / result).exists():
            raise RuntimeError(f'Git operation in progress: {marker}')


def allowed(path, role, projects):
    parts = Path(path).parts
    if path in {'README.md', '.gitignore', '.gitattributes'} or path.startswith('.github/'):
        return True
    if parts and parts[0] == TOOLKIT:
        return role in CENTRAL or not path.startswith('.controlroom/gbrain-cards/') or path == f'.controlroom/gbrain-cards/{role}.md'
    return len(parts) > 1 and parts[0] in projects and (role in CENTRAL or parts[0] == role) and parts[1] in {'docs', 'skills', 'AGENTS.md', 'CLAUDE.md'}


def push(home, message):
    root = home / 'projects'
    role = agent_for(root)
    check_origin(root, ORIGIN)
    check_main(root)
    data = validate(root)
    projects = {p.name for p in root.iterdir() if p.is_dir() and not p.name.startswith('.') and p.name != 'venture'}
    git(root, 'fetch', '--quiet', '--prune', 'origin')
    paths = set()
    for arguments in [('diff', '--name-only', '--no-renames', '-z'), ('diff', '--cached', '--name-only', '--no-renames', '-z'), ('ls-files', '--others', '--exclude-standard', '-z'), ('diff', '--name-only', '--no-renames', '-z', 'origin/main...HEAD')]:
        paths.update(p for p in git(root, *arguments).stdout.split('\0') if p)
    for path in paths:
        if not allowed(path, role, projects):
            raise RuntimeError(f'push 범위 밖 변경: {role}: {path}')
    if paths:
        git(root, 'add', '-A', '--', *sorted(paths))
    if git(root, 'diff', '--cached', '--quiet', check=False).returncode == 1:
        git(root, 'commit', '-m', message or 'Update controlroom assets')
    if git(root, 'rebase', 'origin/main', check=False).returncode:
        git(root, 'rebase', '--abort')
        raise RuntimeError('Rebase conflict; 로컬 커밋은 보존했습니다.')
    git(root, 'push', 'origin', 'main')
    print('Controlroom changes published; refreshing installed instructions and skills.', flush=True)
    cache = home / '.local/share/controlroom/tmp'
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='refresh-', dir=cache) as temporary:
        source = Path(temporary) / 'incoming'
        run('git', 'clone', '--no-hardlinks', str(root), str(source))
        apply(source, home, role, {}, legacy_cleanup=False, refresh_only=True)
    if role in CENTRAL:
        for name, expected in repositories(root):
            product = root / name
            check_origin(product, expected)
            check_main(product)
            git(product, 'fetch', '--quiet', '--prune', 'origin')
            behind = int(git(product, 'rev-list', '--count', 'HEAD..origin/main').stdout)
            if behind and git(product, 'status', '--porcelain').stdout:
                raise RuntimeError(f'Product work preserved; resolve remote changes before pushing: {product}')
            if behind and git(product, 'rebase', 'origin/main', check=False).returncode:
                git(product, 'rebase', '--abort')
                raise RuntimeError(f'Product conflict; local commits preserved: {product}')
            git(product, 'push', 'origin', 'main')
    print('Controlroom changes and reviewed product commits published.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    own_workspace = Path(__file__).resolve().parents[2]
    default_home = own_workspace.parent if own_workspace.name == 'projects' else Path(os.environ.get('USERPROFILE' if os.name == 'nt' else 'HOME', str(Path.home())))
    parser.add_argument('--home', type=Path, default=default_home)
    sub = parser.add_subparsers(dest='action', required=True)
    for action in ('install', 'pull'):
        command = sub.add_parser(action)
        command.add_argument('agent', nargs='?')
        if action == 'install':
            command.add_argument('--source', type=Path)
    command = sub.add_parser('push')
    command.add_argument('message', nargs='?', default='')
    command = sub.add_parser('verify')
    command = sub.add_parser('restore')
    command.add_argument('archive', type=Path)
    args = parser.parse_args()
    home = Path(os.path.abspath(args.home))
    try:
        if args.action in {'install', 'pull'}:
            update(home, args.agent, getattr(args, 'source', None))
        elif args.action == 'push':
            push(home, args.message)
        elif args.action == 'verify':
            verify(home / 'projects', home, agent_for(home / 'projects'))
            print('Physical layout and installed contents verified.')
        elif args.action == 'restore':
            restore_archive(home, args.archive)
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f'[error] {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
