#!/usr/bin/env python3
"""Run the existing daily memory pipeline on the control-room computer."""
import hashlib
import contextlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

import memory_distill as pipeline

SSH = shutil.which('ssh')
MAIN = 'chaconne@49.247.192.127'
GBRAIN_HOST = 'chaconne@49.247.45.243'
WRAPPER = '/home/chaconne/.gbrain/bin/gbrain_with_google_env.sh'
PROVIDER_FILE = '/srv/consolidation/data/gbrain-runtime/.gbrain/provider.env'


def ssh_args(host, command):
    if SSH is None:
        raise RuntimeError('OpenSSH client is required')
    return [SSH, '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
            '-o', 'ConnectTimeout=12', host, command]


def provider_key():
    # Read the existing server credential into process memory; never save it here.
    code = ('from pathlib import Path; '
            'lines=Path(' + repr(PROVIDER_FILE) + ').read_text().splitlines(); '
            'values=dict(line.split("=",1) for line in lines '
            'if "=" in line and not line.lstrip().startswith("#")); '
            'print(values.get("OPENROUTER_API_KEY", "").strip().strip(chr(34)).strip(chr(39)),end="")')
    result = subprocess.run(ssh_args(MAIN, shlex.join(['sudo', '-n', 'python3', '-c', code])),
                            capture_output=True, timeout=30,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    if result.returncode or not result.stdout.strip():
        raise RuntimeError('Server credential read failed; rc=%s' % result.returncode)
    return result.stdout.decode('utf-8').strip()


def run_gbrain(args, timeout=120):
    args = list(args)
    data = None
    if args and args[0] == 'capture' and '--file' in args and '--stdin' not in args:
        data = Path(args[args.index('--file') + 1]).read_bytes()
        args.append('--stdin')
    if '--source' not in args:
        args += ['--source', 'default']
    result = subprocess.run(ssh_args(GBRAIN_HOST, shlex.join([WRAPPER, *args])),
                            input=data, capture_output=True, timeout=timeout,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    return subprocess.CompletedProcess(result.args, result.returncode,
                                       result.stdout.decode('utf-8', errors='replace'),
                                       result.stderr.decode('utf-8', errors='replace'))


def write_gbrain_report(slug, report_path):
    result = run_gbrain(['capture', '--file', str(report_path), '--slug', slug,
                         '--type', 'report', '--quiet'])
    if result.returncode:
        raise RuntimeError('GBrain report delivery failed; rc=%s' % result.returncode)


def extract_user_messages(target_date):
    messages = []
    for path in pipeline.iter_codex_jsonl_files():
        canonical, legacy = [], []
        has_canonical = False
        with path.open(encoding='utf-8', errors='replace') as source:
            for line_no, line in enumerate(source, 1):
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = record.get('payload') or {}
                is_user = (record.get('type') == 'response_item'
                           and payload.get('type') == 'message' and payload.get('role') == 'user')
                has_canonical |= is_user
                if pipeline.local_date_from_timestamp(record.get('timestamp')) != target_date:
                    continue
                if is_user:
                    texts = [part['text'] for part in payload.get('content', [])
                             if part.get('type') == 'input_text' and isinstance(part.get('text'), str)
                             and not part['text'].startswith('# AGENTS.md instructions')]
                    text, output = '\n\n'.join(texts), canonical
                elif record.get('type') == 'event_msg' and payload.get('type') == 'user_message':
                    text, output = payload.get('message'), legacy
                else:
                    continue
                if not text or text.startswith('# AGENTS.md instructions'):
                    continue
                output.append({'timestamp': record.get('timestamp'), 'path': str(path),
                               'line': line_no, 'text': pipeline.redact(text).strip()})
        # Modern rollouts already contain the message; their event copy is not a second input.
        messages.extend(canonical if has_canonical else legacy)
    return messages


def main():
    pipeline.run_gbrain = run_gbrain
    pipeline.write_gbrain_report = write_gbrain_report
    pipeline.gbrain_available = lambda: SSH is not None
    pipeline.extract_user_messages = extract_user_messages
    if sys.argv[1:] == ['--preflight']:
        key = provider_key()
        result = run_gbrain(['get', 'agent/gbrain-operating-protocol'])
        if result.returncode:
            raise RuntimeError('GBrain protocol read failed; rc=%s' % result.returncode)
        files = pipeline.iter_codex_jsonl_files()
        today_count = len(pipeline.extract_user_messages(pipeline.today()))
        print(json.dumps({'kind': 'controlroom_memory_readonly_preflight',
                          'codex_home': str(pipeline.CODEX_HOME),
                          'input_files': len(files), 'today_user_messages': today_count,
                          'provider_key_available': bool(key),
                          'protocol_sha256': hashlib.sha256(result.stdout.encode()).hexdigest(),
                          'llm_calls': 0, 'gbrain_writes': 0}))
        return 0
    args = pipeline.build_parser().parse_args()
    if args.command == 'generate':
        credential = provider_key()
        pipeline.load_exdigm_env_value = lambda name: credential if name == 'OPENROUTER_API_KEY' else ''
    return args.func(args)


if __name__ == '__main__':
    if sys.argv[1:] == ['--scheduled']:
        directory = pipeline.GBRAIN_HOME / 'logs'
        directory.mkdir(parents=True, exist_ok=True)
        sys.argv[1:] = ['generate']
        with (directory / 'memory-distill-controlroom.log').open('a', encoding='utf-8') as log:
            with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                try:
                    raise SystemExit(main())
                except Exception:
                    import traceback
                    traceback.print_exc()
                    raise SystemExit(1)
    else:
        raise SystemExit(main())
