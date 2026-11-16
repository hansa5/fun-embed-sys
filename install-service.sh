#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ "$EUID" -ne 0 ]]; then
  echo "Run with sudo: sudo ./install-service.sh" >&2
  exit 1
fi
service_user="${SUDO_USER:-}"
if [[ -z "$service_user" || "$service_user" == root ]]; then
  echo "Run this script through sudo from the normal account that owns the checkout." >&2
  exit 1
fi
if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  echo "Environment missing. Run ./install.sh as $service_user first." >&2
  exit 1
fi
service_group="$(id -gn "$service_user")"
unit=/etc/systemd/system/fun-embed-app.service
env_file=/etc/default/fun-embed-app
if [[ ! -e "$env_file" ]]; then
  cat > "$env_file" <<'ENVVARS'
HOST=0.0.0.0
PORT=8501
ENVVARS
fi
cat > "$unit" <<UNIT
[Unit]
Description=Fun Embedded Systems web application
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=$service_user
Group=$service_group
WorkingDirectory=$ROOT
EnvironmentFile=-$env_file
ExecStart=$ROOT/run-app.sh
Restart=always
RestartSec=5
StartLimitIntervalSec=0

[Install]
WantedBy=multi-user.target
UNIT
service_uid="$(id -u "$service_user")"
if [[ -S "/run/user/$service_uid/bus" ]]; then
  runuser -u "$service_user" -- env \
    XDG_RUNTIME_DIR="/run/user/$service_uid" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$service_uid/bus" \
    systemctl --user disable --now fun-embed-docs.service 2>/dev/null || true
fi
systemctl daemon-reload
systemctl enable --now fun-embed-app.service
systemctl --no-pager --full status fun-embed-app.service
