#!/usr/bin/env bash
# One implementation; no fallback repository roots or asset links.
controlroom_home="${HOME:?HOME is required}"
unalias kitpull kitpush controlroom 2>/dev/null || true
unset -f controlroom 2>/dev/null || true
kitpull() { "$controlroom_home/.local/bin/kitpull" "$@"; }
kitpush() { "$controlroom_home/.local/bin/kitpush" "$@"; }
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  case "$(basename "$0")" in
    kitpull) kitpull "$@" ;;
    kitpush) kitpush "$@" ;;
    *) printf '%s\n' 'Use kitpull or kitpush.' >&2; exit 64 ;;
  esac
fi
