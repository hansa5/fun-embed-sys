#!/usr/bin/env bash
set -euo pipefail

if ! command -v tailscale >/dev/null 2>&1; then
  if [[ "$EUID" -eq 0 ]]; then
    curl -fsSL https://tailscale.com/install.sh | sh
  else
    echo "Install Tailscale's Debian package with sudo first, or run this script as root." >&2
    echo "Official instructions: https://tailscale.com/docs/install/linux" >&2
    exit 1
  fi
fi

if [[ "$EUID" -ne 0 ]]; then
  echo "Run with sudo: sudo ./install-tailnet.sh [port]" >&2
  exit 1
fi

port="${1:-${TAILNET_SERVE_PORT:-8501}}"
systemctl enable --now tailscaled
if ! tailscale ip -4 >/dev/null 2>&1; then
  echo "Authenticate this Pi to your tailnet using the URL below." >&2
  tailscale up
  echo "After sign-in completes, rerun: sudo ./install-tailnet.sh $port" >&2
  exit 2
fi
tailscale serve --bg "http://127.0.0.1:${port}"
echo "Tailnet-only HTTPS Serve is configured for local port ${port}."
tailscale serve status
