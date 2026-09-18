#!/usr/bin/env bash
set -euo pipefail

home_dir="${HOME:?HOME is required}"
wrapper="${GBRAIN_ENV_WRAPPER:-$home_dir/.gbrain/bin/gbrain_with_google_env.sh}"
port="${GBRAIN_HTTP_PORT:-3131}"
bind="${GBRAIN_HTTP_BIND:-127.0.0.1}"

exec "$wrapper" serve --http --port "$port" --bind "$bind" --suppress-bootstrap-token
