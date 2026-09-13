#!/usr/bin/env bash

# kmh-agent-kit 일상 동기화 명령.
# 최초 설치가 Git 로컬 설정에 저장한 등록 이름으로 공용 자산과 해당 도메인을 자동 선택한다.

unalias kitpull kitpush 2>/dev/null || true
unset -f kitpull kitpush 2>/dev/null || true

_kit_registered_agent() {
  local kit="$HOME/kmh-agent-kit"
  local agent card

  [ -d "$kit/.git" ] || { echo "ERROR: kmh-agent-kit 저장소가 없습니다: $kit" >&2; return 1; }
  agent="$(git -C "$kit" config --local --get kmh-agent-kit.agent 2>/dev/null || true)"

  # 기존 설치는 저장값이 없으므로 현재 카드에서 한 번만 복구한다.
  if [ -z "$agent" ]; then
    card="$(readlink "$HOME/.gbrain-agent.md" 2>/dev/null || true)"
    if [ -n "$card" ] && [[ "$card" != /* ]] && [[ ! "$card" =~ ^[A-Za-z]:[/\\] ]]; then
      card="$(cd "$(dirname "$HOME/.gbrain-agent.md")" 2>/dev/null && cd "$(dirname "$card")" 2>/dev/null && printf '%s/%s\n' "$PWD" "$(basename "$card")" || true)"
    fi
    case "$card" in
      "$kit"/gbrain-cards/*.md)
        agent="$(basename "$card" .md)"
        git -C "$kit" config --local kmh-agent-kit.agent "$agent" || return 1
        echo "기존 GBrain 카드에서 등록 이름 복구: $agent" >&2
        ;;
      *)
        echo "ERROR: 등록 이름이 없습니다. 최초 설치 명령을 실행하세요: $kit/install.sh <등록 이름>" >&2
        return 1
        ;;
    esac
  fi

  [[ "$agent" =~ ^[a-z0-9]([a-z0-9-]{0,30}[a-z0-9])?$ ]] || {
    echo "ERROR: 잘못된 등록 이름: $agent" >&2
    return 1
  }
  [ -f "$kit/gbrain-cards/$agent.md" ] || {
    echo "ERROR: 등록 이름에 해당하는 GBrain 카드가 없습니다: $agent" >&2
    return 1
  }
  printf '%s\n' "$agent"
}

_kit_domain_for_agent() {
  local agent="$1"
  case "$agent" in
    main|windows-control) printf '\n' ;;
    fundkeeper) printf '%s\n' fundkeeper ;;
    *) printf '%s\n' "$agent" ;;
  esac
}

_kit_path_allowed() {
  local path="$1" agent="$2" domain="$3"

  [[ "$agent" = main || "$agent" = windows-control ]] && return 0
  case "$path" in
    gbrain-cards/*) [ "$path" = "gbrain-cards/$agent.md" ] ;;
    skills/domains/*) [ -n "$domain" ] && [[ "$path" == "skills/domains/$domain/"* ]] ;;
    projects/*) [ -n "$domain" ] && [[ "$path" == "projects/$domain/"* ]] ;;
    *) return 0 ;;
  esac
}

_kit_assert_push_scope() {
  local kit="$1" agent="$2" domain="$3" remote_ref="$4"
  local path invalid=no

  while IFS= read -r -d '' path; do
    [ -n "$path" ] || continue
    if ! _kit_path_allowed "$path" "$agent" "$domain"; then
      printf 'ERROR: 현재 등록(%s)의 push 범위 밖 변경: %s\n' "$agent" "$path" >&2
      invalid=yes
    fi
  done < <({
    git -C "$kit" diff --name-only --no-renames -z
    git -C "$kit" diff --cached --name-only --no-renames -z
    git -C "$kit" ls-files --others --exclude-standard -z
    git -C "$kit" log --format= --name-only --no-renames -z "$remote_ref"..HEAD --
  })

  if [ "$invalid" = yes ]; then
    echo "ERROR: 공용 파일과 매칭 도메인${domain:+($domain)}만 kitpush할 수 있습니다." >&2
    return 1
  fi
}

_kit_assert_main_path() {
  local kit="$1" branch state git_path

  branch="$(git -C "$kit" symbolic-ref --quiet --short HEAD 2>/dev/null || true)"
  if [ "$branch" != main ]; then
    if [ -z "$branch" ]; then
      echo "ERROR: $kit 가 detached HEAD 상태입니다. main 브랜치로 복구한 뒤 다시 실행하세요." >&2
    else
      echo "ERROR: kitpull·kitpush는 main 브랜치에서만 실행합니다. 저장소: $kit, 현재 브랜치: $branch" >&2
    fi
    return 1
  fi

  for state in rebase-merge rebase-apply MERGE_HEAD CHERRY_PICK_HEAD REVERT_HEAD; do
    git_path="$(git -C "$kit" rev-parse --git-path "$state")"
    case "$git_path" in
      /*|[A-Za-z]:/*) ;;
      *) git_path="$kit/$git_path" ;;
    esac
    if [ -e "$git_path" ]; then
      echo "ERROR: 진행 중인 Git 작업($state)을 먼저 끝내거나 취소하세요." >&2
      return 1
    fi
  done
}

_kit_fetch_main() {
  local kit="$1"

  git -C "$kit" fetch --quiet --prune origin || return 1
  git -C "$kit" show-ref --verify --quiet refs/remotes/origin/main || {
    echo "ERROR: 원격 origin/main 브랜치가 없습니다." >&2
    return 1
  }
  git -C "$kit" branch --set-upstream-to=origin/main main >/dev/null || return 1
}

_kit_worktree_dirty() {
  [ -n "$(git -C "$1" status --porcelain=v1 --untracked-files=normal)" ]
}

# The installer restores repositories; only kitpull/kitpush synchronize them.
_kit_native_path() {
  case "$1" in
    [A-Za-z]:[\\/]*) cygpath -u -- "$1" ;;
    *) printf '%s\n' "$1" ;;
  esac
}

_kit_control_repositories() {
  local kit="$1" home="$2" manifest directory kind target extra
  manifest="$kit/manifests/windows-control-projects.tsv"
  [ -f "$manifest" ] || { echo "ERROR: 프로젝트 목록이 없습니다: $manifest" >&2; return 1; }
  while IFS=$'\t' read -r directory kind target extra || [ -n "${directory:-}" ]; do
    case "$directory" in ''|\#*) continue ;; esac
    [[ "$directory" =~ ^[A-Za-z0-9_-]+$ ]] && [ -n "${target:-}" ] && [ -z "${extra:-}" ] || {
      echo "ERROR: 프로젝트 목록의 디렉터리 또는 필드가 올바르지 않습니다." >&2; return 1;
    }
    case "$kind" in
      profile) continue ;;
      git|docs)
        [[ "$target" =~ ^https://github\.com/[^/[:space:]]+/[^/[:space:]]+\.git$ ]] || {
          echo "ERROR: 프로젝트 목록에는 GitHub HTTPS 저장소 주소를 사용합니다: $directory" >&2; return 1;
        }
        printf '%s\t%s\t%s\n' "$home/projects/$directory" "$kind" "$target"
        ;;
      *) echo "ERROR: 알 수 없는 프로젝트 복원 방식: $kind" >&2; return 1 ;;
    esac
  done < "$manifest"
}

_kit_github_repository() {
  local remote="$1"
  case "$remote" in
    https://github.com/*) remote="${remote#https://github.com/}" ;;
    git@github.com:*) remote="${remote#git@github.com:}" ;;
    ssh://git@github.com/*) remote="${remote#ssh://git@github.com/}" ;;
    *) return 1 ;;
  esac
  printf '%s\n' "${remote%.git}"
}

_kit_assert_control_repository() {
  local repo="$1" expected="$2" actual wanted found
  [ -d "$repo" ] && [ -e "$repo/.git" ] && git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
    echo "ERROR: 기존 폴더를 보존했습니다. Git 저장소인지 확인하세요: $repo" >&2; return 1;
  }
  actual="$(git -C "$repo" config --get remote.origin.url)" || return 1
  wanted="$(_kit_github_repository "$expected")" || return 1
  found="$(_kit_github_repository "$actual")" || {
    echo "ERROR: origin이 등록된 GitHub 저장소와 다릅니다: $repo" >&2; return 1;
  }
  [ "$wanted" = "$found" ] || {
    echo "ERROR: origin이 등록된 GitHub 저장소와 다릅니다: $repo" >&2; return 1;
  }
  while IFS= read -r actual; do
    found="$(_kit_github_repository "$actual")" || found=''
    [ "$wanted" = "$found" ] || {
      echo "ERROR: origin의 별도 push 주소가 등록된 저장소와 다릅니다: $repo" >&2; return 1;
    }
  done < <(git -C "$repo" config --get-all remote.origin.pushurl)
}

_kit_restore_control_repositories() {
  local kit home rows repo kind target
  kit="$(_kit_native_path "$1")" || return 1
  home="$(_kit_native_path "$2")" || return 1
  rows="$(_kit_control_repositories "$kit" "$home")" || return 1
  [ -n "$rows" ] || return 0
  mkdir -p "$home/projects" || return 1
  while IFS=$'\t' read -r repo kind target; do
    if [ -e "$repo" ] || [ -L "$repo" ]; then
      _kit_assert_control_repository "$repo" "$target" || return 1
      printf '프로젝트 저장소 보존: %s\n' "$repo"
    else
      if ! git clone --branch main --single-branch "$target" "$repo"; then
        printf 'ERROR: 저장소 복원 실패: %s. Git 읽기 인증과 연결을 확인한 뒤 같은 설치 명령을 다시 실행하세요.\n' "$repo" >&2
        return 1
      fi
      _kit_assert_control_repository "$repo" "$target" || return 1
    fi
  done <<< "$rows"
}

_kit_pull_control_repository() {
  local repo="$1" ahead behind
  _kit_assert_main_path "$repo" || return 1
  if _kit_worktree_dirty "$repo"; then
    printf 'ERROR: 로컬 작업을 보존했습니다: %s. 문서는 kitpush, 코드는 해당 프로젝트에서 검토·커밋한 뒤 다시 받으세요.\n' "$repo" >&2
    return 1
  fi
  _kit_fetch_main "$repo" || return 1
  read -r ahead behind < <(git -C "$repo" rev-list --left-right --count HEAD...origin/main)
  if [ "$ahead" -gt 0 ]; then
    printf 'ERROR: 아직 전송하지 않은 커밋을 보존했습니다: %s. kitpush로 저장한 뒤 다시 받으세요.\n' "$repo" >&2
    return 1
  fi
  if [ "$behind" -gt 0 ]; then
    git -C "$repo" merge --ff-only origin/main || return 1
  fi
}

_kit_push_control_repository() {
  local repo="$1" kind="$2" message="$3" pending=no
  _kit_assert_main_path "$repo" || return 1
  _kit_fetch_main "$repo" || return 1
  if [ "$kind" = docs ]; then
    git -C "$repo" status --short
    git -C "$repo" add -A || return 1
    git -C "$repo" diff --cached --quiet || git -C "$repo" commit -m "$message" || return 1
  elif _kit_worktree_dirty "$repo"; then
    pending=yes
  fi
  if ! git -C "$repo" merge-base --is-ancestor origin/main HEAD; then
    if _kit_worktree_dirty "$repo"; then
      printf 'ERROR: 원격 변경과 로컬 작업이 함께 있어 보존했습니다: %s. 프로젝트에서 변경을 검토·커밋한 뒤 다시 저장하세요.\n' "$repo" >&2
      return 1
    fi
    if ! git -C "$repo" rebase origin/main; then
      git -C "$repo" rebase --abort >/dev/null 2>&1 || true
      printf 'ERROR: 충돌을 취소하고 로컬 커밋을 보존했습니다: %s. 충돌 내용을 정리한 뒤 kitpush를 다시 실행하세요.\n' "$repo" >&2
      return 1
    fi
  fi
  git -C "$repo" push origin main:main || return 1
  if [ "$pending" = yes ]; then
    printf 'ERROR: 커밋은 전송했지만 미커밋 코드·자료는 이 기기에 남아 있습니다: %s. 코드 저장소는 자동 stage하지 않습니다.\n' "$repo" >&2
    return 1
  fi
}

_kit_sync_control_repositories() {
  local kit="$1" agent="$2" action="$3" message="${4:-Update control-room documents}"
  local home rows repo kind target failed=0
  [ "$agent" = windows-control ] || return 0
  home="$(_kit_native_path "$HOME")" || return 1
  rows="$(_kit_control_repositories "$kit" "$home")" || return 1
  [ -n "$rows" ] || return 0
  while IFS=$'\t' read -r repo kind target; do
    if ! _kit_assert_control_repository "$repo" "$target"; then
      failed=1
      continue
    fi
    if (
      case "$action" in
        pull) _kit_pull_control_repository "$repo" ;;
        push) _kit_push_control_repository "$repo" "$kind" "$message" ;;
        *) return 64 ;;
      esac
    ); then
      printf '동기화 완료: %s\n' "$repo"
    else
      printf '동기화 미완료: %s\n' "$repo" >&2
      failed=1
    fi
  done <<< "$rows"
  [ "$failed" -eq 0 ] || return 1
  # Validate links against the source state that was actually received/rebased.
  _kit_run_installer "$kit" "$agent"
}

_kit_run_installer() {
  local kit="$1" agent="$2"
  "$kit/install.sh" "$agent"
}

kitpull() {
  local kit="$HOME/kmh-agent-kit"
  local agent counts ahead behind

  agent="$(_kit_registered_agent)" || return 1
  _kit_assert_main_path "$kit" || return 1
  if _kit_worktree_dirty "$kit"; then
    echo "ERROR: 로컬 변경이 있습니다. 먼저 kitpush를 실행하세요." >&2
    return 1
  fi

  _kit_fetch_main "$kit" || return 1
  read -r ahead behind < <(git -C "$kit" rev-list --left-right --count HEAD...origin/main)
  if [ "$ahead" -gt 0 ]; then
    echo "ERROR: 아직 push하지 않은 로컬 커밋이 있습니다. kitpush를 실행하세요." >&2
    return 1
  fi
  if [ "$behind" -gt 0 ]; then
    git -C "$kit" merge --ff-only origin/main || return 1
  fi

  _kit_run_installer "$kit" "$agent" || return 1
  _kit_sync_control_repositories "$kit" "$agent" pull
}

kitpush() {
  local kit="$HOME/kmh-agent-kit"
  local agent domain message

  agent="$(_kit_registered_agent)" || return 1
  domain="$(_kit_domain_for_agent "$agent")"
  message="${1:-Update $agent agent kit}"

  _kit_assert_main_path "$kit" || return 1
  _kit_fetch_main "$kit" || return 1
  _kit_assert_push_scope "$kit" "$agent" "$domain" origin/main || return 1

  _kit_run_installer "$kit" "$agent" || return 1
  _kit_assert_push_scope "$kit" "$agent" "$domain" origin/main || return 1
  git -C "$kit" status --short
  git -C "$kit" add -A || return 1
  _kit_assert_push_scope "$kit" "$agent" "$domain" origin/main || return 1
  git -C "$kit" diff --cached --quiet || git -C "$kit" commit -m "$message" || return 1

  if ! git -C "$kit" merge-base --is-ancestor origin/main HEAD; then
    if ! git -C "$kit" rebase origin/main; then
      git -C "$kit" rebase --abort >/dev/null 2>&1 || true
      echo "ERROR: 원격 변경과 충돌했습니다. 로컬 커밋은 보존했습니다. 충돌 내용을 정리한 뒤 kitpush를 다시 실행하세요." >&2
      return 1
    fi
  fi

  _kit_assert_push_scope "$kit" "$agent" "$domain" origin/main || return 1
  _kit_run_installer "$kit" "$agent" || return 1
  if ! git -C "$kit" push origin main:main; then
    echo "ERROR: push 중 원격이 다시 변경됐을 수 있습니다. kitpush를 다시 실행하세요." >&2
    return 1
  fi
  _kit_sync_control_repositories "$kit" "$agent" push "$message"
}

_kit_dispatch() {
  local command_name="$(basename "$0")"
  case "$command_name" in
    kitpull) kitpull "$@" ;;
    kitpush) kitpush "$@" ;;
    *)
      case "${1:-}" in
        pull) shift; kitpull "$@" ;;
        push) shift; kitpush "$@" ;;
        restore-repositories) shift; [ "$#" -eq 2 ] || return 64; _kit_restore_control_repositories "$@" ;;
        *)
          echo "ERROR: 사용법: kitpull | kitpush [커밋 메시지]" >&2
          return 64
          ;;
      esac
      ;;
  esac
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  _kit_dispatch "$@"
fi
