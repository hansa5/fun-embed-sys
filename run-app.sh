#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  echo "Environment missing. Run ./install.sh first." >&2
  exit 1
fi

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8501}"
exec "$ROOT/.venv/bin/uvicorn" backend.main:app --host "$HOST" --port "$PORT" --proxy-headers
