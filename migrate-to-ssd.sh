#!/usr/bin/env bash
set -Eeuo pipefail

# One-time Saman Pi migration. Run from the SD checkout as:
#   sudo bash migrate-to-ssd.sh
# Formatting the approved SAMAN partition erases its contents.

if [[ ${EUID} -ne 0 ]]; then
  echo "Run this migration with sudo: sudo bash migrate-to-ssd.sh" >&2
  exit 1
fi

APP_USER=saman
APP_HOME=/home/saman
OLD_CHECKOUT="$APP_HOME/Documents/git_repo/fun-embed-sys"
OLD_DB="$APP_HOME/.local/share/fun-embed-sys/wheel.sqlite3"
MOUNT_POINT=/mnt/saman-ssd
NEW_REPO="$MOUNT_POINT/git_repo/fun-embed-sys"
SERVICE=fun-embed-docs.service
SERVICE_OVERRIDE="$APP_HOME/.config/systemd/user/$SERVICE.d/override.conf"
APP_UID="$(id -u "$APP_USER")"
RUNTIME_DIR="/run/user/$APP_UID"
BACKUP_SUFFIX="$(date -u +%Y%m%dT%H%M%SZ)"
DB_BACKUP="$APP_HOME/.local/share/fun-embed-sys/wheel.sqlite3.pre-ssd-$BACKUP_SUFFIX"
OVERRIDE_BACKUP="$SERVICE_OVERRIDE.pre-ssd-$BACKUP_SUFFIX"
FSTAB_BACKUP="/etc/fstab.pre-fun-embed-ssd-$BACKUP_SUFFIX"
LEGACY_UUID=9941-07F1
EXPECTED_REMOTE=https://github.com/hansa5/fun-embed-sys.git
APP_STOPPED=0
OVERRIDE_UPDATED=0
COMPLETE=0

as_saman() {
  runuser -u "$APP_USER" -- env HOME="$APP_HOME" \
    PATH="$APP_HOME/.local/bin:/usr/local/bin:/usr/bin:/bin" "$@"
}

user_systemctl() {
  as_saman env XDG_RUNTIME_DIR="$RUNTIME_DIR" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=$RUNTIME_DIR/bus" \
    /usr/bin/systemctl --user "$@"
}

rollback_service() {
  local result=$?
  if [[ $COMPLETE -eq 1 ]]; then return "$result"; fi
  echo "Migration did not finish. The SD checkout and original database were preserved." >&2
  if [[ $OVERRIDE_UPDATED -eq 1 && -f $OVERRIDE_BACKUP ]]; then
    cp -a "$OVERRIDE_BACKUP" "$SERVICE_OVERRIDE" || true
    user_systemctl daemon-reload || true
  fi
  if [[ $APP_STOPPED -eq 1 ]]; then user_systemctl restart "$SERVICE" || true; fi
  return "$result"
}
trap rollback_service EXIT

if [[ ! -d $OLD_CHECKOUT/.git ]]; then
  echo "Expected the existing SD checkout at $OLD_CHECKOUT; stopping." >&2
  exit 1
fi
if [[ ! -f $SERVICE_OVERRIDE || ! -f $OLD_DB ]]; then
  echo "Expected service override or SQLite database is missing; stopping." >&2
  exit 1
fi
if [[ -e $NEW_REPO ]]; then
  echo "Destination already exists: $NEW_REPO. Inspect it; the script will not overwrite it." >&2
  exit 1
fi

DEVICE=
FORMAT_REQUIRED=0
if [[ -e "/dev/disk/by-uuid/$LEGACY_UUID" ]]; then
  DEVICE="$(readlink -f "/dev/disk/by-uuid/$LEGACY_UUID")"
  fstype="$(blkid -o value -s TYPE "$DEVICE")"
  label="$(blkid -o value -s LABEL "$DEVICE")"
  if [[ $fstype != vfat || $label != SAMAN ]]; then
    echo "The legacy UUID exists but is not the expected SAMAN VFAT partition; stopping." >&2
    exit 1
  fi
  FORMAT_REQUIRED=1
elif [[ -e /dev/disk/by-label/FUNEMBED ]]; then
  DEVICE="$(readlink -f /dev/disk/by-label/FUNEMBED)"
  [[ "$(blkid -o value -s TYPE "$DEVICE")" == ext4 ]] || { echo "FUNEMBED label is not ext4." >&2; exit 1; }
else
  echo "Could not identify the approved SSD partition by its old UUID or new label." >&2
  exit 1
fi

MOUNTED_AT="$(findmnt -rn -S "$DEVICE" -o TARGET || true)"
if [[ -n $MOUNTED_AT && $MOUNTED_AT != "$MOUNT_POINT" ]]; then
  echo "The SSD partition is mounted at '$MOUNTED_AT', not $MOUNT_POINT; stopping." >&2
  exit 1
fi
if [[ -n $MOUNTED_AT && "$(findmnt -n -o FSTYPE --target "$MOUNTED_AT")" != ext4 ]]; then
  echo "The mounted SSD is not ext4; stopping." >&2
  exit 1
fi
if [[ -z $MOUNTED_AT ]] && findmnt -rn -M "$MOUNT_POINT" >/dev/null; then
  echo "Another filesystem is mounted at $MOUNT_POINT; stopping." >&2
  exit 1
fi
parent="$(lsblk -no PKNAME "$DEVICE" | xargs)"
model="$(lsblk -dn -o MODEL "/dev/$parent" | xargs)"
[[ $model == *"PNY CS900"* ]] || { echo "Expected the PNY CS900 SSD; detected '$model'. Stopping." >&2; exit 1; }

mkdir -p "$MOUNT_POINT"
if [[ -z $MOUNTED_AT ]] && find "$MOUNT_POINT" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
  echo "$MOUNT_POINT is not empty and is not mounted; stopping to avoid masking data." >&2
  exit 1
fi
if [[ -n $MOUNTED_AT ]] && find "$MOUNT_POINT" -mindepth 1 -maxdepth 1 ! -name lost+found ! -name git_repo -print -quit | grep -q .; then
  echo "$MOUNT_POINT contains unexpected files; stopping without changing them." >&2
  exit 1
fi
if [[ -L "$MOUNT_POINT/git_repo" || ( -e "$MOUNT_POINT/git_repo" && ! -d "$MOUNT_POINT/git_repo" ) ]]; then
  echo "$MOUNT_POINT/git_repo exists but is not a normal directory; stopping." >&2
  exit 1
fi
expected_fstab_source="UUID=$(blkid -o value -s UUID "$DEVICE")"
fstab_entry="$(awk -v target="$MOUNT_POINT" '$2 == target { print $1 "|" $3 }' /etc/fstab)"
if [[ -n $fstab_entry && $fstab_entry != "$expected_fstab_source|ext4" ]]; then
  echo "An unexpected /etc/fstab entry exists for $MOUNT_POINT; stopping." >&2
  exit 1
fi

if [[ $FORMAT_REQUIRED -eq 1 ]]; then
  echo "About to erase $DEVICE ($model, VFAT label SAMAN, UUID $LEGACY_UUID)."
  read -r -p 'Type ERASE SAMAN to confirm the approved format: ' confirmation
  [[ $confirmation == 'ERASE SAMAN' ]] || { echo "Confirmation did not match; stopping." >&2; exit 1; }
fi

user_systemctl stop "$SERVICE"
APP_STOPPED=1

# Keep an independent on-SD SQLite backup before formatting or changing paths.
mkdir -p "$(dirname "$DB_BACKUP")"
as_saman /usr/bin/python3 -c 'import sqlite3,sys; src=sqlite3.connect(sys.argv[1]); dst=sqlite3.connect(sys.argv[2]); src.backup(dst); dst.close(); src.close()' "$OLD_DB" "$DB_BACKUP"
chown "$APP_USER:$APP_USER" "$DB_BACKUP"

if [[ $FORMAT_REQUIRED -eq 1 ]]; then
  mkfs.ext4 -F -L FUNEMBED "$DEVICE"
fi
new_uuid="$(blkid -o value -s UUID "$DEVICE")"
[[ -n $new_uuid ]] || { echo "Could not read the new ext4 UUID." >&2; exit 1; }

if [[ -z $fstab_entry ]]; then
  cp -a /etc/fstab "$FSTAB_BACKUP"
  printf 'UUID=%s %s ext4 defaults,noatime,nofail,x-systemd.device-timeout=10s 0 2\n' "$new_uuid" "$MOUNT_POINT" >> /etc/fstab
fi
if [[ -z $MOUNTED_AT ]]; then mount "$MOUNT_POINT"; fi
[[ "$(findmnt -n -o FSTYPE --target "$MOUNT_POINT")" == ext4 ]] || { echo "The SSD did not mount as ext4." >&2; exit 1; }
chown "$APP_USER:$APP_USER" "$MOUNT_POINT"

mkdir -p "$MOUNT_POINT/git_repo"
if [[ -n "$(find "$MOUNT_POINT/git_repo" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
  echo "$MOUNT_POINT/git_repo is not empty; stopping without changing its contents." >&2
  exit 1
fi
chown "$APP_USER:$APP_USER" "$MOUNT_POINT/git_repo"
as_saman git clone --branch master "$EXPECTED_REMOTE" "$NEW_REPO"
[[ "$(git -C "$NEW_REPO" remote get-url origin)" == "$EXPECTED_REMOTE" ]] || { echo "Unexpected origin in SSD checkout." >&2; exit 1; }
as_saman env HOME="$APP_HOME" PATH="$APP_HOME/.local/bin:/usr/local/bin:/usr/bin:/bin" \
  /bin/bash -c "cd '$NEW_REPO' && ./install.sh"

mkdir -p "$NEW_REPO/data"
chown "$APP_USER:$APP_USER" "$NEW_REPO/data"
as_saman /usr/bin/python3 -c 'import sqlite3,sys; src=sqlite3.connect(sys.argv[1]); dst=sqlite3.connect(sys.argv[2]); src.backup(dst); dst.close(); src.close()' "$DB_BACKUP" "$NEW_REPO/data/wheel.sqlite3"
integrity="$(as_saman /usr/bin/python3 -c 'import sqlite3,sys; c=sqlite3.connect("file:"+sys.argv[1]+"?mode=ro",uri=True); print(c.execute("PRAGMA integrity_check").fetchone()[0]); c.close()' "$NEW_REPO/data/wheel.sqlite3")"
[[ $integrity == ok ]] || { echo "Copied SQLite database failed integrity check: $integrity" >&2; exit 1; }

mkdir -p "$(dirname "$SERVICE_OVERRIDE")"
cp -a "$SERVICE_OVERRIDE" "$OVERRIDE_BACKUP"
OVERRIDE_UPDATED=1
cat > "$SERVICE_OVERRIDE" <<EOF
[Service]
WorkingDirectory=$NEW_REPO
ExecStart=
ExecStart=$NEW_REPO/run-app.sh
Environment=
ExecStartPre=/usr/bin/findmnt -rn -M $MOUNT_POINT -t ext4
EOF
chown "$APP_USER:$APP_USER" "$SERVICE_OVERRIDE"
user_systemctl daemon-reload
user_systemctl restart "$SERVICE"

for attempt in $(seq 1 20); do
  if curl -fsS http://127.0.0.1:8501/api/health; then break; fi
  if [[ $attempt -eq 20 ]]; then echo "App health check did not pass." >&2; exit 1; fi
  sleep 1
done

as_saman mkdir -p "$APP_HOME/.codex/skills/pi-direct-deploy" "$APP_HOME/.codex/skills/pi-github-sync"
as_saman cp "$NEW_REPO/skills/pi-direct-deploy/SKILL.md" "$APP_HOME/.codex/skills/pi-direct-deploy/SKILL.md"
as_saman cp "$NEW_REPO/skills/pi-github-sync/SKILL.md" "$APP_HOME/.codex/skills/pi-github-sync/SKILL.md"
/bin/bash "$NEW_REPO/install-market-monitor.sh"
echo
echo "SSD mount: $(findmnt -n -o SOURCE,FSTYPE --target "$NEW_REPO")"
echo "Repository: $NEW_REPO"
echo "Database: $NEW_REPO/data/wheel.sqlite3 (integrity: $integrity)"
echo "Preserved SD database backup: $DB_BACKUP"
echo "Preserved SD checkout: $OLD_CHECKOUT"
echo "Deployed commit: $(git -C "$NEW_REPO" rev-parse HEAD)"
echo "Service: $(user_systemctl is-active "$SERVICE")"
COMPLETE=1
trap - EXIT
