#!/usr/bin/env bash
# One implementation; no fallback repository roots or asset links.
controlroom_home="${HOME:?HOME is required}"
unalias kitpull kitpush controlroom 2>/dev/null || true
controlroom() { "$controlroom_home/.local/bin/controlroom" "$@"; }
kitpull() { controlroom pull "$@"; }
kitpush() { controlroom push "$@"; }
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  case "$(basename "$0")" in
    kitpull) controlroom pull "$@" ;;
    kitpush) controlroom push "$@" ;;
    *) controlroom "$@" ;;
  esac
fi
