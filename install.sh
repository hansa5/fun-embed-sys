#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" != Linux ]] || ! command -v apt-get >/dev/null 2>&1; then
  echo "This installer supports Debian-based Linux, including Raspberry Pi OS." >&2
  exit 1
fi

missing=()
for package in git curl ca-certificates python3 python3-venv python3-dev build-essential pkg-config; do
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

node_compatible() {
  command -v node >/dev/null 2>&1 && node -e 'const [major, minor] = process.versions.node.split(".").map(Number); if (!(major > 20 || (major === 20 && minor >= 19) || (major === 22 && minor >= 12))) process.exit(1)' >/dev/null 2>&1
}

if ! node_compatible; then
  node_version=22.23.5
  case "$(uname -m)" in
    x86_64) node_arch=x64 ;;
    aarch64|arm64) node_arch=arm64 ;;
    armv7l) node_arch=armv7l ;;
    *) echo "No official Node.js binary is configured for $(uname -m)." >&2; exit 1 ;;
  esac
  node_file="node-v${node_version}-linux-${node_arch}.tar.xz"
  node_base="https://nodejs.org/dist/v${node_version}"
  node_home="${HOME}/.local/share/fun-embed-sys"
  mkdir -p "$node_home"
  if [[ ! -x "$node_home/node-v${node_version}-linux-${node_arch}/bin/node" ]]; then
    temp_dir="$(mktemp -d)"
    trap 'rm -rf "$temp_dir"' EXIT
    curl -fsSL "$node_base/$node_file" -o "$temp_dir/$node_file"
    curl -fsSL "$node_base/SHASUMS256.txt" | awk -v file="$node_file" '$2 == file { print $1 "  " file }' > "$temp_dir/SHASUMS256.txt"
    (cd "$temp_dir" && sha256sum --check SHASUMS256.txt)
    tar -xJf "$temp_dir/$node_file" -C "$node_home"
  fi
  export PATH="$node_home/node-v${node_version}-linux-${node_arch}/bin:$PATH"
fi

(cd "$ROOT/frontend" && if [[ -f package-lock.json ]]; then npm ci; else npm install; fi && npm run build)
echo "Environment ready. Run ./run-app.sh to start the React + FastAPI app."
