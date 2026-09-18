#!/usr/bin/env python3
"""Add/remove manifest placements. Sources are physical folders; no links or index tricks."""
import argparse
import json
from pathlib import Path
import sys
from controlroom import validate

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['add', 'rm'])
    parser.add_argument('skill')
    parser.add_argument('--global', dest='global_profile', action='store_true')
    parser.add_argument('--project', action='append', default=[])
    args = parser.parse_args()
    path = ROOT / '.controlroom/manifests/skills.json'
    original = path.read_bytes()
    data = json.loads(original)
    try:
        if not args.global_profile and not args.project:
            raise RuntimeError('Select --global or --project <name>')
        candidates = [ROOT / '.controlroom/skills' / args.skill, *ROOT.glob(f'*/skills/{args.skill}')]
        candidates = [p for p in candidates if (p / 'SKILL.md').is_file()]
        if len(candidates) != 1:
            raise RuntimeError('Expected exactly one physical source with SKILL.md')
        data['sources'][args.skill] = candidates[0].relative_to(ROOT).as_posix()
        profiles = [data['profiles']['global']] if args.global_profile else []
        for name in args.project:
            if not (ROOT / name).is_dir() or name.startswith('.') or '/' in name or chr(92) in name:
                raise RuntimeError(f'Unknown project: {name}')
            profiles.append(data['profiles']['projects'].setdefault(name, []))
        for names in profiles:
            if args.action == 'add' and args.skill not in names:
                names.append(args.skill)
                names.sort()
            if args.action == 'rm' and args.skill in names:
                names.remove(args.skill)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + chr(10), encoding='utf-8')
        validate(ROOT)
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        path.write_bytes(original)
        print(f'[error] {error}', file=sys.stderr)
        return 1
    print('Manifest updated. Run check-skill-deps.py, then kitpush.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
