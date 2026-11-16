#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  echo "Environment missing. Run ./install.sh first." >&2
  exit 1
fi

APP_KIND="${APP_KIND:-streamlit}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8501}"
case "$APP_KIND" in
  streamlit)
    STREAMLIT_APP="${STREAMLIT_APP:-docs/app.py}"
    exec "$ROOT/.venv/bin/streamlit" run "$STREAMLIT_APP" \
      --server.address "$HOST" --server.port "$PORT" \
      --server.headless true --browser.gatherUsageStats false
    ;;
  flask)
    FLASK_TARGET="${FLASK_TARGET:-app:app}"
    exec "$ROOT/.venv/bin/waitress-serve" --listen="${HOST}:${PORT}" "$FLASK_TARGET"
    ;;
  *) echo "APP_KIND must be 'streamlit' or 'flask'." >&2; exit 2 ;;
esac
