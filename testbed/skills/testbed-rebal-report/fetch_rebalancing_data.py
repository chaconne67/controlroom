"""서류21 리밸런싱 데이터 생성 — 서버 SSH 조회 + JSON 저장
사용: python fetch_rebalancing_data.py list-schedules --recipe kr
      python fetch_rebalancing_data.py fetch --recipe kr --schedule-id 28
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent


def load_env():
    """환경변수 로드 (~/.env 파일 지원)"""
    env_path = Path.home() / '.env'
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, _, val = line.partition('=')
                os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def get_base_dir():
    return Path(os.environ.get(
        'TESTBED_DOC_DIR',
        r'C:\Users\chaconne\Google Drive 스트리밍\내 드라이브\MOA\테스트베드2차\준비서류',
    ))


def get_remote_host():
    return os.environ.get('FUNDKEEPER_HOST', 'root@49.247.38.186')


def get_remote_project():
    return os.environ.get('FUNDKEEPER_PROJECT', '/home/work/fundkeeper')


def load_recipe_config():
    """recipe_config.json 로드"""
    config_path = SCRIPT_DIR / 'rebalancing_report_config.json'
    with open(config_path, encoding='utf-8') as f:
        config = json.load(f)
    for key, recipe in config.items():
        recipe.setdefault('dir', recipe['name'])
        recipe.setdefault('file_prefix', f'({recipe["name"]})')
    return config


def get_json_path(recipe_dir, schedule_id):
    """데이터 JSON 파일 경로"""
    return recipe_dir / f'rebalancing_data_{schedule_id}.json'


# ===== SSH =====

def run_server_command(cmd_args):
    """SSH로 서버의 TestBed2 CLI를 호출하고 JSON 결과 파싱"""
    host = get_remote_host()
    project = get_remote_project()

    cmd = f'ssh {host} "cd {project} && python xmodules/test_bed/test_bed.py {cmd_args}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)

    stderr = result.stderr or ''
    if result.returncode != 0:
        print(f'[ERROR] SSH 명령 실패 (returncode={result.returncode})')
        print(f'stderr: {stderr[:500]}')
        sys.exit(1)

    output = result.stdout or ''
    match = re.search(r'===JSON_START===\n(.*?)\n===JSON_END===', output, re.DOTALL)
    if not match:
        print(f'[ERROR] 서버 출력에서 JSON을 찾을 수 없음')
        print(f'stdout: {output[:500]}')
        print(f'stderr: {stderr[:500]}')
        sys.exit(1)

    return json.loads(match.group(1))


def fetch_schedules(recipe=None, limit=10):
    """서버에서 스케줄 목록 조회"""
    args = '스케줄목록'
    if recipe:
        args += f' --group {recipe}'
    args += f' --limit {limit}'
    return run_server_command(args)


def fetch_data_from_server(schedule_id, recipe):
    """SSH로 서버의 TestBed2 CLI를 호출하여 리밸런싱 데이터 추출"""
    print(f'서버 데이터 조회 중... (schedule_id={schedule_id}, recipe={recipe})')
    return run_server_command(
        f'리밸런싱리포트 --schedule {schedule_id} --group {recipe}'
    )


# ===== 커맨드 =====

def cmd_list_schedules(args, recipe_config):
    """스케줄 목록 출력"""
    schedules = fetch_schedules(recipe=args.recipe, limit=args.limit or 10)
    print(f'\n{"ID":>4}  {"코드":<10}  {"rday":<12}  {"tday":<12}  {"market"}')
    print('-' * 55)
    for s in schedules:
        print(f'{s["id"]:>4}  {s["code"]:<10}  {s["rday"]:<12}  {s.get("tday") or "":<12}  {s["market"]}')
    print()


def cmd_fetch(args, recipe_config):
    """서버에서 데이터 생성 후 JSON 파일로 저장"""
    config = recipe_config[args.recipe]
    base_dir = get_base_dir()
    recipe_dir = base_dir / config['dir']

    data = fetch_data_from_server(args.schedule_id, args.recipe)
    json_path = get_json_path(recipe_dir, args.schedule_id)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'\n=== 데이터 저장 완료 ===')
    print(f'  {json_path}')


def main():
    load_env()
    recipe_config = load_recipe_config()

    parser = argparse.ArgumentParser(description='서류21 리밸런싱 데이터 생성')
    sub = parser.add_subparsers(dest='action', required=True)

    # list-schedules
    sp_list = sub.add_parser('list-schedules', help='스케줄 목록 조회')
    sp_list.add_argument('--recipe', choices=list(recipe_config.keys()), help='레시피로 필터')
    sp_list.add_argument('--limit', type=int, default=10)

    # fetch
    sp_fetch = sub.add_parser('fetch', help='서버에서 데이터 생성 → JSON 저장')
    sp_fetch.add_argument('--recipe', required=True, choices=list(recipe_config.keys()))
    sp_fetch.add_argument('--schedule-id', required=True, type=int)

    args = parser.parse_args()

    if args.action == 'list-schedules':
        cmd_list_schedules(args, recipe_config)
    elif args.action == 'fetch':
        cmd_fetch(args, recipe_config)


if __name__ == '__main__':
    main()
