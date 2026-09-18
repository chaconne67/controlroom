#!/usr/bin/env python3
"""Check physical sources, profile scope, dependencies, and system skill availability."""
import json
import os
from pathlib import Path
import sys
from controlroom import validate

ROOT = Path(__file__).resolve().parents[2]


def main():
    try:
        data = validate(ROOT)
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        print(f'[error] {error}')
        return 1
    visible = set(data['profiles']['global'])
    for project, names in sorted(data['profiles']['projects'].items()):
        visible.update(names)
        domains = {data['sources'][name].split('/')[0] for name in names if not data['sources'][name].startswith('.controlroom/')}
        if len(domains) > 1:
            print(f'[warn] {project}: multiple source domains: {", ".join(sorted(domains))}')
    for name in sorted(set(data['sources']) - visible):
        print(f'[warn] No profile uses {name}')
    codex = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex')))
    if (codex / 'skills').is_dir():
        for item in json.loads((ROOT / '.controlroom/manifests/base-skills.json').read_text(encoding='utf-8')):
            if item.get('kind') == 'system_skill' and not (codex / 'skills/.system' / item['name']).is_dir():
                print(f'[warn] Codex system skill missing: {item["name"]}: {item.get("install_hint", "")}')
    print(f'Passed: {len(data["sources"])} physical sources, {len(data["profiles"]["global"])} global skills')
    for project, names in sorted(data['profiles']['projects'].items()):
        print(f'  {project}: {len(names)} project skills')
    return 0


if __name__ == '__main__':
    sys.exit(main())
