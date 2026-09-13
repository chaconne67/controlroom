#!/usr/bin/env bash
set -euo pipefail

# kmh-agent-kit installer — 전역 자산, GBrain 카드, 프로젝트 프로필을 한 경로로 연결한다.
# raw URL로 실행하면 저장소를 준비한 뒤 체크아웃된 설치기로 이어간다.

installer_source="${BASH_SOURCE[0]:-}"
repo_dir="$(cd "$(dirname "${installer_source:-.}")" && pwd)"
home_dir="${HOME:?HOME is required}"
claude_home="${CLAUDE_HOME:-$home_dir/.claude}"
codex_home="${CODEX_HOME:-$home_dir/.codex}"
agents_home="$home_dir/.agents"
hermes_home="${HERMES_HOME:-$home_dir/.hermes}"
gbrain_home="${GBRAIN_HOME:-$home_dir/.gbrain}"
policy_file="${GBRAIN_POLICY_FILE:-$gbrain_home/memory/agent-policy.toml}"
gbrain_cli="${GBRAIN_CLI_WRAPPER:-$gbrain_home/bin/gbrain_with_google_env.sh}"
gbrain_host="${GBRAIN_HOST:-chaconne@49.247.45.243}"
stamp="$(date +%Y%m%d-%H%M%S)"
backup_root="$home_dir/.kmh-agent-kit-backup-$stamp"

die() {
  echo "[error] $*" >&2
  exit 64
}

bootstrap_checkout() {
  local checkout="$home_dir/kmh-agent-kit"
  command -v git >/dev/null 2>&1 || die "Git을 먼저 설치해야 합니다. kitpush에 Git이 필요합니다."

  if [ -e "$checkout" ] && [ ! -d "$checkout/.git" ]; then
    die "설치 경로가 이미 있지만 Git 저장소가 아닙니다: $checkout"
  fi

  if [ -d "$checkout/.git" ]; then
    [ -z "$(git -C "$checkout" status --porcelain=v1 --untracked-files=normal)" ] ||
      die "기존 키트에 로컬 변경이 있어 자동 설치를 중단합니다: $checkout"
    git -C "$checkout" fetch --prune origin
    git -C "$checkout" show-ref --verify --quiet refs/remotes/origin/main ||
      die "원격 origin/main 브랜치가 없습니다."
    if git -C "$checkout" show-ref --verify --quiet refs/heads/main; then
      git -C "$checkout" checkout main
    else
      git -C "$checkout" checkout -b main --track origin/main
    fi
    git -C "$checkout" merge --ff-only origin/main
  else
    git clone --branch main --single-branch https://github.com/chaconne67/kmh-agent-kit.git "$checkout"
  fi

  [ -x "$checkout/install.sh" ] || chmod u+x "$checkout/install.sh"
  exec "$checkout/install.sh" "$@"
}

if [ -z "$installer_source" ] || [ ! -d "$repo_dir/.git" ] || [ ! -f "$repo_dir/manifests/skills.json" ]; then
  bootstrap_checkout "$@"
fi

show_usage() {
  cat <<'EOF'
KMH Agent Kit (Windows Git Bash·macOS·Linux·WSL)

새로운 프로젝트 역할을 처음 등록:
  ./install.sh --new abc-project
  ./install.sh --new abc-project --dry-run

이미 등록된 역할을 설치 — 해당 등록 이름 하나만 사용:
  ./install.sh main
  ./install.sh sam

중앙 조정실 프로젝트 프로필만 연결:
  ./install.sh --project ~/projects/rndlog rndlog
  ./install.sh --project ~/projects/ceoloan ceoloan

최초 설치 후 키트를 설치한 장비에서 동일:
  kitpull
  kitpush

그 외:
  ./install.sh                         공용 스킬·전역 지침만 설치
  ./install.sh --project ~/projects/exdigm exdigm
  ./install.sh --help
EOF
}

run_windows_installer() {
  case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*) ;;
    *) return 0 ;;
  esac

  command -v powershell.exe >/dev/null 2>&1 || die "Windows PowerShell을 찾지 못했습니다."
  command -v cygpath >/dev/null 2>&1 || die "Git Bash의 cygpath를 찾지 못했습니다."

  local ps_script
  local -a ps_args=()
  ps_script="$(cygpath -aw "$repo_dir/install.ps1")"
  case "${1:-}" in
    "")
      [ "$#" -eq 0 ] || die "인수가 올바르지 않습니다. ./install.sh --help"
      ;;
    -h|--help)
      [ "$#" -eq 1 ] || die "도움말에는 추가 인수를 사용할 수 없습니다."
      ps_args=(-Help)
      ;;
    --project)
      [ "$#" -eq 3 ] || die "사용법: ./install.sh --project ~/projects/exdigm exdigm"
      ps_args=(-Project "$(cygpath -aw "$2")" -ProfileName "$3")
      ;;
    --gbrain)
      [ "$#" -eq 2 ] || die "사용법: ./install.sh --gbrain gram17"
      ps_args=(-Agent "$2")
      ;;
    --new|--register-agent)
      die "$1 명령은 중앙 Linux 환경에서만 실행할 수 있습니다."
      ;;
    --*)
      die "알 수 없는 옵션: $1. ./install.sh --help"
      ;;
    *)
      [ "$#" -eq 1 ] || die "등록 이름은 하나만 입력합니다. ./install.sh --help"
      ps_args=(-Agent "$1")
      ;;
  esac

  exec powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "$ps_script" "${ps_args[@]}"
}

validate_agent_name() {
  local agent_name="$1"
  [[ "$agent_name" =~ ^[a-z0-9]([a-z0-9-]{0,30}[a-z0-9])?$ ]] ||
    die "에이전트 이름은 영문 소문자·숫자·중간 하이픈으로 된 1~32자여야 합니다: $agent_name"
}

backup_entry() {
  local path="$1" flat
  mkdir -p "$backup_root"
  flat="${path#"$home_dir"/}"
  flat="${flat//\//_}"
  mv "$path" "$backup_root/$flat"
  echo "기존 항목 백업: $path"
}

# 링크가 아닌 기존 항목은 백업한 뒤 연결한다. 이미 올바른 링크면 그대로 둔다.
link_entry() {
  local target="$1" link="$2"
  if [ -L "$link" ]; then
    [ "$(readlink "$link")" = "$target" ] && return 0
    unlink "$link"
  elif [ -e "$link" ]; then
    backup_entry "$link"
  fi
  mkdir -p "$(dirname "$link")"
  ln -s "$target" "$link"
}

link_profile() {
  local profile="$1" live="$2" preserve_existing="${3:-no}"
  mkdir -p "$live"
  local entry live_entry current_target
  for entry in "$profile"/*; do
    [ -e "$entry" ] || continue
    live_entry="$live/$(basename "$entry")"
    if [ "$preserve_existing" = yes ] && { [ -e "$live_entry" ] || [ -L "$live_entry" ]; }; then
      current_target="$(readlink "$live_entry" 2>/dev/null || true)"
      case "$current_target" in
        "$profile"/*) ;;
        *)
          echo "Hermes 기존 스킬 유지: $live_entry"
          continue
          ;;
      esac
    fi
    link_entry "$entry" "$live_entry"
  done
  for live_entry in "$live"/*; do
    [ -L "$live_entry" ] || continue
    case "$(readlink "$live_entry")" in
      "$profile"/*) [ -e "$live_entry" ] || unlink "$live_entry" ;;
    esac
  done
}

remove_kit_skill_links() {
  local live="$1"
  [ -d "$live" ] || return 0
  local entry target resolved
  for entry in "$live"/*; do
    [ -L "$entry" ] || continue
    target="$(readlink "$entry")"
    resolved="$(readlink -f "$entry" 2>/dev/null || true)"
    case "$target:$resolved" in
      "$repo_dir/codex/skills/"*:*|"$repo_dir/claude/skills/"*:*|*:"$repo_dir/skills/"*)
        unlink "$entry"
        echo "이전 Codex 사용자 스킬 링크 제거: $entry"
        ;;
    esac
  done
}

migrate_legacy_global_skill_copies() {
  local live_root source name live_entry target resolved
  for live_root in "$codex_home/skills" "$agents_home/skills" "$claude_home/skills"; do
    for source in "$repo_dir"/skills/common/* "$repo_dir"/skills/domains/*/*; do
      [ -d "$source" ] || continue
      name="$(basename "$source")"
      live_entry="$live_root/$name"
      { [ -e "$live_entry" ] || [ -L "$live_entry" ]; } || continue

      target="$(readlink "$live_entry" 2>/dev/null || true)"
      resolved="$(readlink -f "$live_entry" 2>/dev/null || true)"
      case "$target:$resolved" in
        "$repo_dir/codex/skills/"*:*|"$repo_dir/claude/skills/"*:*|*:"$repo_dir/skills/"*)
          unlink "$live_entry"
          ;;
        *)
          backup_entry "$live_entry"
          ;;
      esac
      echo "이전 사용자 스킬 이전: $live_entry"
    done
  done
}

backup_if_exists() {
  local path="$1"
  if [ -e "$path" ] && [ ! -L "$path" ]; then
    cp -a "$path" "$path.backup-$stamp"
  fi
}

install_file() {
  local src="$1" dst="$2"
  cmp -s "$src" "$dst" 2>/dev/null && return 0
  mkdir -p "$(dirname "$dst")"
  backup_if_exists "$dst"
  cp -a "$src" "$dst"
}

append_shell_line() {
  local file="$1" marker="$2" line="$3"
  if grep -Fxq "# $marker" "$file" 2>/dev/null; then
    local tmp="$file.kmh-agent-kit-$$"
    awk -v marker="# $marker" -v replacement="$line" '
      $0 == marker {
        print
        if ((getline) >= 0) print replacement
        next
      }
      { print }
    ' "$file" > "$tmp"
    if ! cmp -s "$tmp" "$file"; then
      cp "$tmp" "$file"
      echo "${file}의 $marker 갱신"
    fi
    rm -f "$tmp"
    return 0
  fi
  printf '\n# %s\n%s\n' "$marker" "$line" >> "$file"
  echo "${file}에 $marker 추가"
}

install_shell_commands() {
  local command_dir="$home_dir/.local/bin"
  mkdir -p "$command_dir"
  link_entry "$repo_dir/shell/kit-aliases.sh" "$command_dir/kitpull"
  link_entry "$repo_dir/shell/kit-aliases.sh" "$command_dir/kitpush"

  append_shell_line "$home_dir/.bashrc" "kmh-agent-kit aliases" \
    "[ -f \"$repo_dir/shell/kit-aliases.sh\" ] && . \"$repo_dir/shell/kit-aliases.sh\""
  append_shell_line "$home_dir/.bashrc" "kmh-agent-kit command path" \
    'case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) export PATH="$HOME/.local/bin:$PATH" ;; esac'
  append_shell_line "$home_dir/.profile" "kmh-agent-kit command path" \
    'case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) export PATH="$HOME/.local/bin:$PATH" ;; esac'
  append_shell_line "$home_dir/.bash_profile" "kmh-agent-kit command path" \
    'case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) export PATH="$HOME/.local/bin:$PATH" ;; esac'
  append_shell_line "$home_dir/.zshrc" "kmh-agent-kit command path" \
    'case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) export PATH="$HOME/.local/bin:$PATH" ;; esac'
}

install_global() {
  local agent_name="${1:-}"
  migrate_legacy_global_skill_copies
  remove_kit_skill_links "$codex_home/skills"
  link_profile "$repo_dir/claude/skills" "$claude_home/skills"
  link_profile "$repo_dir/codex/skills" "$agents_home/skills"
  link_profile "$repo_dir/codex/skills" "$hermes_home/skills" yes
  link_entry "$repo_dir/claude/CLAUDE.md" "$claude_home/CLAUDE.md"
  link_entry "$repo_dir/codex/AGENTS.md" "$codex_home/AGENTS.md"

  if [ "$agent_name" = main ]; then
    mkdir -p "$gbrain_home/bin" "$gbrain_home/logs" "$home_dir/.config/systemd/user"
    install_file "$repo_dir/gbrain/bin/gbrain_with_google_env.sh" "$gbrain_home/bin/gbrain_with_google_env.sh"
    install_file "$repo_dir/gbrain/bin/gbrain_http_with_google_env.sh" "$gbrain_home/bin/gbrain_http_with_google_env.sh"
    install_file "$repo_dir/gbrain/bin/memory_distill.py" "$gbrain_home/bin/memory_distill.py"
    install_file "$repo_dir/gbrain/bin/gbrain-agent" "$gbrain_home/bin/gbrain-agent"
    chmod 700 "$gbrain_home/bin/gbrain_with_google_env.sh" "$gbrain_home/bin/gbrain_http_with_google_env.sh" "$gbrain_home/bin/memory_distill.py"
    chmod 755 "$gbrain_home/bin/gbrain-agent"

    if [ -f "$policy_file" ]; then
      mkdir -p "$home_dir/.local/bin"
      link_entry "$gbrain_home/bin/gbrain-agent" "$home_dir/.local/bin/gbrain-agent"
      local registered_agent
      while IFS= read -r registered_agent; do
        if sed -n "/^\[agents\.$registered_agent\]$/,/^\[/p" "$policy_file" | grep -q '^private_source'; then
          link_entry "$gbrain_home/bin/gbrain-agent" "$home_dir/.local/bin/gbrain-$registered_agent"
        fi
      done < <(sed -n 's/^\[agents\.\([A-Za-z0-9_-]*\)\]$/\1/p' "$policy_file")
    fi

    install_file "$repo_dir/gbrain/systemd/gbrain-http.service" "$home_dir/.config/systemd/user/gbrain-http.service"
    install_file "$repo_dir/gbrain/systemd/gbrain-memory-distill.service" "$home_dir/.config/systemd/user/gbrain-memory-distill.service"
    install_file "$repo_dir/gbrain/systemd/gbrain-memory-distill.timer" "$home_dir/.config/systemd/user/gbrain-memory-distill.timer"
  fi

  install_shell_commands

  if command -v python3 >/dev/null 2>&1; then
    python3 "$repo_dir/scripts/check-skill-deps.py"
  else
    echo "[warning] python3 미발견 — 스킬 의존성 검사를 건너뜁니다." >&2
  fi

  if [ "$agent_name" = main ] && command -v systemctl >/dev/null 2>&1 && [ -x "${GBRAIN_CLI:-$home_dir/.bun/bin/gbrain}" ]; then
    systemctl --user daemon-reload || true
    systemctl --user enable --now gbrain-http.service || true
    systemctl --user enable --now gbrain-memory-distill.timer || true
  fi
}

control_room_docs_source() {
  local rows checkout kind target
  rows="$(_kit_control_repositories "$repo_dir" "$home_dir")" || return 1
  while IFS=$'\t' read -r checkout kind target; do
    [ "${kind:-}" = docs ] || continue
    printf '%s/%s/docs\n' "$checkout" "$1"
    return 0
  done <<< "$rows"
}

install_project_profile() {
  local project_path="$1" profile_name="$2"
  local profile="$repo_dir/projects/$profile_name"
  validate_agent_name "$profile_name"
  [ -d "$profile" ] || die "프로젝트 프로필이 없습니다: $profile"
  [ -d "$project_path" ] || die "프로젝트 폴더가 없습니다: $project_path"
  local docs_source
  docs_source="$(control_room_docs_source "$profile_name")"
  if [ -d "$docs_source" ] && [ -e "$project_path/docs" ] && [ ! -L "$project_path/docs" ]; then
    die "기존 문서 경로를 보존했습니다. 원본을 확인한 뒤 연결하세요: $project_path/docs"
  fi
  remove_kit_skill_links "$project_path/.codex/skills"
  [ -d "$profile/skills" ] && link_profile "$profile/skills" "$project_path/.claude/skills"
  [ -d "$profile/skills" ] && link_profile "$profile/skills" "$project_path/.agents/skills"
  [ -f "$profile/CLAUDE.md" ] && link_entry "$profile/CLAUDE.md" "$project_path/CLAUDE.md"
  [ -f "$profile/AGENTS.md" ] && link_entry "$profile/AGENTS.md" "$project_path/AGENTS.md"
  if [ -d "$docs_source" ]; then
    link_entry "$docs_source" "$project_path/docs"
  fi
  echo "프로젝트 프로필 연결: $profile_name → $project_path"
}

register_project_profile() {
  local project_path="$1" profile_name="$2" absolute_path
  absolute_path="$(cd "$project_path" && pwd -P)"
  git -C "$repo_dir" config --local --replace-all "kmh-agent-kit.project.$profile_name" "$absolute_path"
  echo "프로젝트 프로필 등록: $profile_name → $absolute_path"
}

restore_control_room_projects() {
  local manifest="$repo_dir/manifests/windows-control-projects.tsv"
  local projects_root="$home_dir/projects"
  local directory kind target extra project_path
  [ -f "$manifest" ] || die "조정실 프로젝트 계약이 없습니다: $manifest"
  _kit_restore_control_repositories "$repo_dir" "$home_dir" || die "조정실 저장소 복원 실패"

  while IFS=$'\t' read -r directory kind target extra; do
    [ -n "${directory:-}" ] || continue
    case "$directory" in \#*) continue ;; esac
    [ -z "${extra:-}" ] && [ -n "${kind:-}" ] && [ -n "${target:-}" ] ||
      die "프로젝트 계약 형식 오류: $manifest"
    [[ "$directory" =~ ^[A-Za-z0-9_-]+$ ]] || die "프로젝트 폴더 이름이 잘못되었습니다: $directory"
    case "$kind" in
      profile)
        validate_agent_name "$target"
        [ -d "$repo_dir/projects/$target" ] || die "프로젝트 프로필이 없습니다: $target"
        project_path="$(git -C "$repo_dir" config --local --get "kmh-agent-kit.project.$target" || true)"
        project_path="${project_path:-$projects_root/$directory}"
        if [ -e "$project_path" ] && [ ! -d "$project_path" ]; then
          die "프로젝트 경로가 폴더가 아닙니다: $project_path"
        fi
        if [ ! -d "$project_path" ]; then
          mkdir -p "$project_path"
          echo "프로젝트 폴더 생성: $project_path"
        fi
        register_project_profile "$project_path" "$target"
        ;;
      git|docs) ;;
      *) die "알 수 없는 프로젝트 복원 방식: $kind" ;;
    esac
  done < "$manifest"
}

register_known_projects() {
  local agent_name="$1" profile profile_name project_path
  case "$agent_name" in
    windows-control)
      restore_control_room_projects
      ;;
    main)
      for profile in "$repo_dir"/projects/*; do
        [ -d "$profile" ] || continue
        profile_name="$(basename "$profile")"
        project_path="$home_dir/projects/$profile_name"
        if [ -d "$project_path" ]; then
          register_project_profile "$project_path" "$profile_name"
        fi
      done
      ;;
    fundkeeper)
      if [ -d "$home_dir/fundkeeper" ]; then
        register_project_profile "$home_dir/fundkeeper" fundkeeper
      fi
      ;;
    *)
      if [ -d "$repo_dir/projects/$agent_name" ] && [ -d "$home_dir/$agent_name" ]; then
        register_project_profile "$home_dir/$agent_name" "$agent_name"
      fi
      ;;
  esac
  return 0
}

install_registered_projects() {
  local key project_path profile_name
  while read -r key project_path; do
    [ -n "${key:-}" ] || continue
    profile_name="${key##*.}"
    if [ ! -d "$repo_dir/projects/$profile_name" ]; then
      echo "[warning] 등록된 프로젝트 프로필이 없어 건너뜁니다: $profile_name" >&2
      continue
    fi
    if [ ! -d "$project_path" ]; then
      echo "[warning] 등록된 프로젝트 경로가 없어 건너뜁니다: $project_path" >&2
      continue
    fi
    install_project_profile "$project_path" "$profile_name"
  done < <(git -C "$repo_dir" config --local --get-regexp '^kmh-agent-kit\.project\.' 2>/dev/null || true)
}

install_gbrain_card() {
  local agent_name="$1"
  local card="$repo_dir/gbrain-cards/$agent_name.md"
  [ -f "$card" ] || die "GBrain 카드가 없습니다. 신규라면 실행하세요: ./install.sh --new $agent_name"
  link_entry "$card" "$home_dir/.gbrain-agent.md"

  if [ ! -f "$policy_file" ] && [ "$agent_name" != "main" ] && [ "$agent_name" != "windows-control" ]; then
    mkdir -p "$home_dir/.local/bin"
    link_entry "$repo_dir/gbrain/bin/gbrain-remote-proxy" "$home_dir/.local/bin/gbrain-$agent_name"
  fi
  echo "GBrain 카드 연결: $agent_name"
}

verify_agent_install() {
  local agent_name="$1"
  local expected_card="$repo_dir/gbrain-cards/$agent_name.md"
  [ "$(readlink "$home_dir/.gbrain-agent.md" 2>/dev/null || true)" = "$expected_card" ] ||
    die "GBrain 카드 링크 검증에 실패했습니다: $agent_name"

  if [ "$agent_name" = "main" ]; then
    [ -x "$gbrain_cli" ] || die "중앙 GBrain 실행 파일이 없습니다: $gbrain_cli"
    GBRAIN_SOURCE=default "$gbrain_cli" get agent/gbrain-operating-protocol >/dev/null
  elif [ "$agent_name" = "windows-control" ]; then
    verify_control_room_projects
    ssh "$gbrain_host" '/home/chaconne/.gbrain/bin/gbrain_with_google_env.sh get agent/gbrain-operating-protocol --source default' >/dev/null
  else
    local wrapper="$home_dir/.local/bin/gbrain-$agent_name"
    [ -x "$wrapper" ] || die "GBrain 래퍼가 없습니다: $wrapper"
    "$wrapper" policy >/dev/null
    "$wrapper" --source default get agent/gbrain-operating-protocol >/dev/null
  fi
}

verify_control_room_projects() {
  local manifest="$repo_dir/manifests/windows-control-projects.tsv"
  local directory kind target extra project_path saved_path expected_path docs_source file
  while IFS=$'\t' read -r directory kind target extra; do
    [ -n "${directory:-}" ] || continue
    case "$directory" in \#*) continue ;; esac
    project_path="$home_dir/projects/$directory"
    if [ "$kind" = git ] || [ "$kind" = docs ]; then
      [ -d "$project_path/.git" ] || die "프로젝트 Git 검증 실패: $project_path"
      continue
    fi
    saved_path="$(git -C "$repo_dir" config --local --get "kmh-agent-kit.project.$target" || true)"
    [ -n "$saved_path" ] && [ -d "$saved_path" ] || die "프로젝트 등록 경로 검증 실패: $target"
    project_path="$saved_path"
    expected_path="$(cd "$project_path" && pwd -P)"
    [ "$saved_path" = "$expected_path" ] || die "프로젝트 등록 검증 실패: $target"
    for file in CLAUDE.md AGENTS.md; do
      [ -f "$repo_dir/projects/$target/$file" ] || continue
      [ "$(readlink "$project_path/$file" 2>/dev/null || true)" = "$repo_dir/projects/$target/$file" ] ||
        die "프로젝트 지침 링크 검증 실패: $project_path/$file"
    done
    docs_source="$(control_room_docs_source "$target")"
    [ -d "$docs_source" ] || die "프로젝트 문서 원본이 없습니다: $docs_source"
    [ "$(readlink "$project_path/docs" 2>/dev/null || true)" = "$docs_source" ] ||
      die "프로젝트 문서 링크 검증 실패: $project_path/docs"
  done < "$manifest"
}

install_agent() {
  local agent_name="$1"
  validate_agent_name "$agent_name"
  [ -f "$repo_dir/gbrain-cards/$agent_name.md" ] ||
    die "등록되지 않은 에이전트입니다. 신규 추가: ./install.sh --new $agent_name"
  git -C "$repo_dir" rev-parse --git-dir >/dev/null 2>&1 ||
    die "kmh-agent-kit Git 저장소에서 실행해야 합니다: $repo_dir"

  install_global "$agent_name"
  install_gbrain_card "$agent_name"
  register_known_projects "$agent_name"
  install_registered_projects
  verify_agent_install "$agent_name"
  git -C "$repo_dir" config --local kmh-agent-kit.agent "$agent_name"

  echo "설치 완료: $agent_name"
  echo "장비 등록 이름 저장: $agent_name (이후 kitpull·kitpush가 자동 사용)"
  if [ -d "$backup_root" ]; then
    echo "기존 파일 백업: $backup_root"
  fi
}

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

run_windows_installer "$@"
. "$repo_dir/shell/kit-aliases.sh"

case "${1:-}" in
  "")
    [ "$#" -eq 0 ] || die "인수가 올바르지 않습니다. ./install.sh --help"
    install_global ""
    echo "공용 설치 완료. 전체 설치 명령은 ./install.sh --help에서 서버별로 확인하세요."
    ;;
  -h|--help)
    [ "$#" -eq 1 ] || die "도움말에는 추가 인수를 사용할 수 없습니다."
    show_usage
    ;;
  --project)
    [ "$#" -eq 3 ] || die "사용법: ./install.sh --project ~/projects/exdigm exdigm"
    install_project_profile "$2" "$3"
    register_project_profile "$2" "$3"
    ;;
  --gbrain)
    [ "$#" -eq 2 ] || die "사용법: ./install.sh --gbrain rndlog"
    install_agent "$2"
    ;;
  --new)
    if [ "$#" -eq 3 ] && [ "$3" = "--dry-run" ]; then
      show_new_agent_dry_run "$2"
    elif [ "$#" -eq 2 ]; then
      add_new_agent "$2"
    else
      die "사용법: ./install.sh --new abc-project [--dry-run]"
    fi
    ;;
  --register-agent)
    [ "$#" -eq 2 ] || die "내부 사용법: ./install.sh --register-agent abc-project"
    register_agent_central "$2"
    ;;
  --*)
    die "알 수 없는 옵션: $1. ./install.sh --help"
    ;;
  *)
    [ "$#" -eq 1 ] || die "등록 이름은 하나만 입력합니다. ./install.sh --help"
    install_agent "$1"
    ;;
esac
