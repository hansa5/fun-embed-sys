#!/usr/bin/env bash
set -Eeuo pipefail

APP_USER=saman
APP_HOME=/home/saman
UNIT_SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/systemd/user"
UNIT_DEST="$APP_HOME/.config/systemd/user"
install -d -o "$APP_USER" -g "$APP_USER" "$UNIT_DEST"
install -o "$APP_USER" -g "$APP_USER" -m 0644 "$UNIT_SOURCE/fun-embed-market-monitor.service" "$UNIT_DEST/"
install -o "$APP_USER" -g "$APP_USER" -m 0644 "$UNIT_SOURCE/fun-embed-market-monitor.timer" "$UNIT_DEST/"
uid="$(id -u "$APP_USER")"
runuser -u "$APP_USER" -- env HOME="$APP_HOME" XDG_RUNTIME_DIR="/run/user/$uid" \
  DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$uid/bus" \
  /usr/bin/systemctl --user daemon-reload
runuser -u "$APP_USER" -- env HOME="$APP_HOME" XDG_RUNTIME_DIR="/run/user/$uid" \
  DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$uid/bus" \
  /usr/bin/systemctl --user enable --now fun-embed-market-monitor.timer
