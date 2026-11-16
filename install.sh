#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" != Linux ]] || ! command -v apt-get >/dev/null 2>&1; then
  echo "This installer supports Debian-based Linux, including Raspberry Pi OS." >&2
  exit 1
fi

missing=()
for package in git curl ca-certificates python3 python3-venv python3-dev build-essential pkg-config libffi-dev libssl-dev; do
  dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -q 'install ok installed' || missing+=("$package")
done
if ((${#missing[@]})); then
  if [[ "$EUID" -eq 0 ]]; then apt=(apt-get); else apt=(sudo apt-get); fi
  "${apt[@]}" update
  "${apt[@]}" install -y "${missing[@]}"
fi

if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"
command -v uv >/dev/null 2>&1 || { echo "uv was installed but is not on PATH." >&2; exit 1; }
uv sync --locked
echo "Environment ready. Run ./run-app.sh to start the default Streamlit app."
