#!/usr/bin/env bash
set -euo pipefail

home_dir="${HOME:?HOME is required}"
env_file="${KMH_AGENT_ENV_FILE:-$home_dir/.gbrain/provider.env}"
gbrain_cli="${GBRAIN_CLI:-$home_dir/.bun/bin/gbrain}"
bun_bin="${BUN_BIN:-$home_dir/.bun/bin}"

if [ ! -x "$gbrain_cli" ]; then
  echo "gbrain CLI not found: $gbrain_cli" >&2
  exit 1
fi

if [ ! -f "$env_file" ]; then
  echo "env file not found: $env_file" >&2
  exit 1
fi

gemini_key="$(grep -m1 '^GEMINI_API_KEY=' "$env_file" | cut -d= -f2- || true)"
gemini_key="${gemini_key%\"}"
gemini_key="${gemini_key#\"}"
gemini_key="${gemini_key%\'}"
gemini_key="${gemini_key#\'}"

if [ -z "$gemini_key" ]; then
  echo "GEMINI_API_KEY not found in $env_file" >&2
  exit 1
fi

export GOOGLE_GENERATIVE_AI_API_KEY="$gemini_key"
export PATH="$bun_bin:$PATH"
unset DATABASE_URL OPENAI_API_KEY OPENROUTER_API_KEY

cd "${GBRAIN_SAFE_CWD:-$home_dir}"
exec "$gbrain_cli" "$@"
