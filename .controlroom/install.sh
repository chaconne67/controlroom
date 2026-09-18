#!/usr/bin/env bash
set -euo pipefail
# Both OS entrypoints use the same physical layout and verified backup/update code.
source_file="${BASH_SOURCE[0]:-}"
repo_dir="$(cd "$(dirname "${source_file:-.}")" && pwd)"
home_dir="${HOME:?HOME is required}"
gbrain_home="${GBRAIN_HOME:-$home_dir/.gbrain}"
policy_file="${GBRAIN_POLICY_FILE:-$gbrain_home/memory/agent-policy.toml}"
gbrain_cli="${GBRAIN_CLI_WRAPPER:-$gbrain_home/bin/gbrain_with_google_env.sh}"
gbrain_host="${GBRAIN_HOST:-chaconne@49.247.45.243}"
stamp="$(date +%Y%m%d-%H%M%S)"
die() { echo "[error] $*" >&2; exit 64; }
validate_agent_name() { [[ "$1" =~ ^[a-z0-9]([a-z0-9-]{0,30}[a-z0-9])?$ ]] || die "Invalid role: $1"; }
python_command() {
  if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; raise SystemExit(sys.version_info < (3,12))' 2>/dev/null; then printf '%s\n' python3;
  elif command -v python >/dev/null 2>&1 && python -c 'import sys; raise SystemExit(sys.version_info < (3,12))' 2>/dev/null; then printf '%s\n' python;
  elif command -v py >/dev/null 2>&1 && py -3 -c 'import sys; raise SystemExit(sys.version_info < (3,12))' 2>/dev/null; then printf '%s\n' py;
  else die "Python 3.12 or newer is required."; fi
}
python_name="$(python_command)"
python_args=(-X utf8)
[ "$python_name" != py ] || python_args=(-3 -X utf8)
core_args=(--home "$home_dir")
while [ "$#" -gt 0 ]; do
  case "$1" in
    --workspace)
      [ "$#" -ge 2 ] || die 'Expected a workspace root.'
      core_args+=(--workspace "$2"); shift 2 ;;
    --main-server) core_args+=(--main-server); shift ;;
    *) break ;;
  esac
done
core() { "$python_name" "${python_args[@]}" "$repo_dir/scripts/controlroom.py" "${core_args[@]}" "$@"; }
if [ ! -f "$repo_dir/scripts/controlroom.py" ]; then
  command -v git >/dev/null 2>&1 || die "Git is required."
  bootstrap_parent="$(cd "${TMPDIR:-/tmp}" && pwd -P)"
  bootstrap_dir="$(mktemp -d "$bootstrap_parent/controlroom-XXXXXX")"
  cleanup_bootstrap() {
    case "$bootstrap_dir" in "$bootstrap_parent"/controlroom-*) rm -rf -- "$bootstrap_dir" ;; *) die 'Unsafe temporary directory.' ;; esac
  }
  trap cleanup_bootstrap EXIT
  git clone --branch main --single-branch https://github.com/chaconne67/controlroom.git "$bootstrap_dir/incoming"
  repo_dir="$bootstrap_dir/incoming/.controlroom"
  core install "${1:-windows-control}" --source "$bootstrap_dir/incoming"
  exit $?
fi
install_agent() { core install "$1" --source "$repo_dir/.."; }
install_file() { [ ! -e "$2" ] || cp -a "$2" "$2.backup-$stamp"; mkdir -p "$(dirname "$2")"; cp -a "$1" "$2"; }
link_entry() { install_file "$1" "$2"; }

render_agent_card() {
  local agent_name="$1"
  printf '%s\n' "- 너는 GBrain 공간 \`$agent_name\`을 쓰는 에이전트다. GBrain 본체는 중앙 서버(\`chaconne@49.247.45.243\`)에 있고, 로컬 \`gbrain-$agent_name\`은 중앙의 정책 래퍼를 호출한다."
  printf '%s\n' "- 작업 전 \`gbrain-$agent_name query \"작업 주제\"\`로 공용 지식과 자기 공간을 함께 조회한다. 명령 문법은 \`gbrain-$agent_name help\`로 확인한다."
  printf '%s\n' "- 공용 본문은 \`gbrain-$agent_name --source default get <slug>\`, 공용 목록은 \`gbrain-$agent_name --source default list\`로 읽는다. \`--source\`를 생략한 get·list·쓰기는 자기 공간을 사용한다."
  printf '%s\n' "- 사적 기록은 \`gbrain-$agent_name note\` 또는 \`put\`으로 저장한다. 쓰기는 \`$agent_name\` 소스의 \`agents/$agent_name/private/\` 아래로 제한된다."
  printf '%s\n' "- 공용 기록은 \`gbrain-$agent_name --source default put <slug> <file.md|->\` 또는 \`gbrain-$agent_name --source default note <slug> <본문>\`으로 직접 저장한다. 허용 경로는 \`policy\`의 \`common_write_prefixes\`를 따른다. 기존 공용 페이지를 바꾸기 전에는 본문을 읽고 필요한 부분만 갱신한다."
  printf '%s\n' "- GBrain을 읽지 못하면 프로젝트 판단이 필요한 작업은 중단하고 연결 실패를 보고한다. 단순 상태 확인은 진행할 수 있지만 GBrain 미조회 사실을 함께 알린다."
  printf '%s\n' "- 코드와 GBrain이 다르면 현재 코드를 기준으로 검증한다. 여러 에이전트가 쓸 확정 지식은 공용에, 프로젝트·기기 고유 기록은 자기 공간에 갱신한다."
}

create_agent_card() {
  local agent_name="$1"
  local card="$repo_dir/gbrain-cards/$agent_name.md"
  if [ -f "$card" ]; then
    echo "기존 GBrain 카드 유지: $card"
    return 1
  fi

  local card_tmp="$card.new-$stamp-$$"
  render_agent_card "$agent_name" > "$card_tmp"
  mv "$card_tmp" "$card"
  echo "GBrain 카드 생성: $card"
  return 0
}

source_path_for_agent() {
  local agent_name="$1"
  "$gbrain_cli" sources list --json | python3 -c '
import json, sys
agent = sys.argv[1]
for source in json.load(sys.stdin).get("sources", []):
    if source.get("id") == agent:
        print(source.get("local_path") or "")
        raise SystemExit(0)
raise SystemExit(1)
' "$agent_name"
}

validate_existing_policy_block() {
  local agent_name="$1" block_type="$2"
  shift 2
  local block expected_line
  block="$(sed -n "/^\[$block_type\.$agent_name\]$/,/^\[/p" "$policy_file")"
  [ -z "$block" ] && return 1
  for expected_line in "$@"; do
    grep -Fqx "$expected_line" <<<"$block" ||
      die "기존 [$block_type.$agent_name] 정책이 예상 값과 다릅니다. 자동으로 덮어쓰지 않습니다: $expected_line"
  done
}

append_policy_blocks() {
  local agent_name="$1" source_dir="$2" add_source_block="$3" add_agent_block="$4"
  local policy_tmp="$policy_file.new-$stamp-$$"
  cp -a "$policy_file" "$policy_tmp"

  if [ "$add_source_block" = yes ]; then
    cat >> "$policy_tmp" <<EOF

[sources.$agent_name]
label = "$agent_name private memory"
path = "$source_dir"
slug_prefixes = ["agents/$agent_name/private"]
visibility = "private"
EOF
  fi

  if [ "$add_agent_block" = yes ]; then
    cat >> "$policy_tmp" <<EOF

[agents.$agent_name]
label = "$agent_name"
private_source = "$agent_name"
private_prefix = "agents/$agent_name/private"
read_sources = ["default", "$agent_name"]
read_prefixes = [
  "agent",
  "feedback",
  "project",
  "reference",
  "incident",
  "shared/common",
  "agents/$agent_name/private"
]
write_sources = ["default", "$agent_name"]
write_prefixes = ["agent", "feedback", "project", "reference", "incident", "shared/common", "agents/$agent_name/private"]
common_write = true
can_promote = false
EOF
  fi

  cp -a "$policy_file" "$policy_file.backup-$stamp-$$"
  mv "$policy_tmp" "$policy_file"
}

verify_default_source() {
  local current_json
  "$gbrain_cli" sources default default >/dev/null
  current_json="$("$gbrain_cli" sources current --json)"
  python3 -c '
import json, sys
current = json.load(sys.stdin)
if current.get("source_id") != "default" or current.get("tier") != "brain_default":
    raise SystemExit(f"default source verification failed: {current}")
' <<<"$current_json"
  GBRAIN_SOURCE=default "$gbrain_cli" get agent/gbrain-operating-protocol >/dev/null
}

register_agent_central() {
  local agent_name="$1"
  validate_agent_name "$agent_name"
  [ -f "$policy_file" ] || die "이 명령은 중앙 GBrain 정책 파일이 있는 서버에서만 실행할 수 있습니다: $policy_file"
  [ -x "$gbrain_cli" ] || die "GBrain 실행 파일이 없습니다: $gbrain_cli"
  command -v flock >/dev/null 2>&1 || die "flock 명령이 필요합니다."

  local lock_file="$policy_file.lock"
  exec {policy_lock_fd}>"$lock_file"
  flock -x "$policy_lock_fd"

  local source_dir="$gbrain_home/agent-sources/$agent_name"
  local source_block=no agent_block=no
  if validate_existing_policy_block "$agent_name" sources \
    "path = \"$source_dir\"" \
    "slug_prefixes = [\"agents/$agent_name/private\"]" \
    'visibility = "private"'; then
    source_block=yes
  fi
  if validate_existing_policy_block "$agent_name" agents \
    "private_source = \"$agent_name\"" \
    "private_prefix = \"agents/$agent_name/private\"" \
    "read_sources = [\"default\", \"$agent_name\"]" \
    '  "agent",' \
    '  "feedback",' \
    '  "project",' \
    '  "reference",' \
    '  "incident",' \
    '  "shared/common",' \
    "  \"agents/$agent_name/private\"" \
    "write_sources = [\"default\", \"$agent_name\"]" \
    "write_prefixes = [\"agent\", \"feedback\", \"project\", \"reference\", \"incident\", \"shared/common\", \"agents/$agent_name/private\"]" \
    'common_write = true' \
    'can_promote = false'; then
    agent_block=yes
  fi

  local source_exists=no source_path=""
  if source_path="$(source_path_for_agent "$agent_name")"; then
    source_exists=yes
    if [ "$source_path" != "$source_dir" ] && { [ "$source_block" = no ] || [ "$agent_block" = no ]; }; then
      die "기존 GBrain 소스 경로가 예상과 달라 자동 정책 등록을 중단합니다: ${source_path:-경로 없음}"
    fi
  fi

  if [ "$source_exists" = no ]; then
    mkdir -p "$source_dir"
    "$gbrain_cli" sources add "$agent_name" --path "$source_dir" --name "$agent_name private memory" --no-federated
    echo "GBrain 공간 생성: $agent_name"
  else
    echo "기존 GBrain 공간 유지: $agent_name"
  fi

  verify_default_source

  if [ "$source_block" = no ] || [ "$agent_block" = no ]; then
    append_policy_blocks "$agent_name" "$source_dir" \
      "$([ "$source_block" = no ] && echo yes || echo no)" \
      "$([ "$agent_block" = no ] && echo yes || echo no)"
    echo "GBrain 정책 등록: $agent_name"
  else
    echo "기존 GBrain 정책 유지: $agent_name"
  fi

  install_file "$repo_dir/gbrain/bin/gbrain-agent" "$gbrain_home/bin/gbrain-agent"
  chmod 755 "$gbrain_home/bin/gbrain-agent"
  mkdir -p "$home_dir/.local/bin"
  link_entry "$gbrain_home/bin/gbrain-agent" "$home_dir/.local/bin/gbrain-$agent_name"
  "$home_dir/.local/bin/gbrain-$agent_name" policy >/dev/null
  echo "중앙 GBrain 등록 완료: $agent_name"
}

register_agent() {
  local agent_name="$1"
  if [ -f "$policy_file" ]; then
    register_agent_central "$agent_name"
  else
    ssh -o BatchMode=yes -o ConnectTimeout=10 "$gbrain_host" \
      "/home/chaconne/kmh-agent-kit/install.sh --register-agent $agent_name"
  fi
}

show_new_agent_dry_run() {
  local agent_name="$1"
  validate_agent_name "$agent_name"
  cat <<EOF
[dry-run] 신규 에이전트: $agent_name
[dry-run] GBrain 소스: $agent_name
[dry-run] 전용 경로: agents/$agent_name/private
[dry-run] 카드: $repo_dir/gbrain-cards/$agent_name.md
[dry-run] 중앙 등록: $gbrain_host
[dry-run] 설치 명령: ./install.sh $agent_name
EOF
  echo
  echo "[dry-run] 생성 카드 미리보기"
  render_agent_card "$agent_name"
}

add_new_agent() {
  local agent_name="$1"
  validate_agent_name "$agent_name"

  local card_created=no
  if create_agent_card "$agent_name"; then
    card_created=yes
  fi

  if ! register_agent "$agent_name"; then
    if [ "$card_created" = yes ]; then
      unlink "$repo_dir/gbrain-cards/$agent_name.md"
    fi
    die "중앙 GBrain 등록에 실패했습니다. 로컬 신규 카드는 되돌렸습니다."
  fi

  install_agent "$agent_name"
  echo "에이전트 등록·설치 완료: $agent_name"
  if [ "$card_created" = yes ]; then
    echo "새 카드를 공유하려면 kmh-agent-kit에서 커밋·push하세요: gbrain-cards/$agent_name.md"
  fi
}


case "${1:-}" in
  --new)
    if [ "$#" -eq 3 ] && [ "$3" = --dry-run ]; then show_new_agent_dry_run "$2";
    elif [ "$#" -eq 2 ]; then add_new_agent "$2";
    else die 'Usage: install.sh --new <role> [--dry-run]'; fi ;;
  --register-agent) [ "$#" -eq 2 ] || die 'Expected one role'; register_agent_central "$2" ;;
  --gbrain) [ "$#" -eq 2 ] || die 'Expected one role'; core install "$2" ;;
  --project) die 'Projects are physical folders under ~/projects. Use controlroom pull to update them.' ;;
  -h|--help) core install --help ;;
  '') core install ;;
  --*) die "Unknown option: $1" ;;
  *) [ "$#" -eq 1 ] || die 'Expected one role'; core install "$1" ;;
esac
