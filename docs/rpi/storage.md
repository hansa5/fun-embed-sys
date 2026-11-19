# Raspberry Pi storage for app data

## SSD inventory and app layout

The Pi `Hansa.local` has a **PNY CS900 500 GB SSD** at `/dev/sda` (465.8 GiB
reported by Linux). The EFI partition `/dev/sda1` (200 MB, VFAT, UUID
`67E3-17ED`) is not used by the app. The former data partition `/dev/sda2`
(465.6 GB, VFAT label `SAMAN`, UUID `9941-07F1`) was approved for formatting
as ext4 because its prior filesystem cannot reliably host this Linux app's
environment and SQLite data. After migration, identify it by its new ext4 UUID
with `lsblk -f`; do not rely on `/dev/sda` numbering.

The migration has not run yet: `/dev/sda2` remains VFAT and unmounted until the
helper is run interactively on the Pi.

Mount the ext4 data partition persistently at `/mnt/saman-ssd`. The repository
checkout is:

```text
/mnt/saman-ssd/git_repo/fun-embed-sys
```

## One-time migration

The migration helper is `migrate-to-ssd.sh`. Run it from the existing SD
checkout in a Pi terminal with `sudo bash migrate-to-ssd.sh`. Do not pull the
new app revision into the old checkout first: its database default changes to
`<repo>/data`, while the running legacy app still uses the existing home data
file. The helper clones current `master` directly onto the SSD and copies the
live database to it. It verifies the PNY device and expected old
filesystem UUID, asks for the exact confirmation `ERASE SAMAN`, stops the
existing user service, backs up the SQLite database to the SD card, formats
only the approved data partition, adds its new UUID to `/etc/fstab`, clones
the current GitHub branch to the SSD, builds the app, restores the database,
updates the user service override, installs both Codex skills, restarts the
app, and checks `/api/health`. The previous SD checkout and database remain as
rollback copies. If a step fails, the helper attempts to restore the old
service override and restart the SD app.

The Pi requires an interactive sudo password for partition and system mount
changes, so Codex cannot run this helper through the current non-interactive
SSH channel. Do not paste your sudo password into chat; run the helper in a
terminal on the Pi.

The Pi boots from its 59 GB microSD (`/dev/mmcblk0p2`); this SSD hosts the app
checkout and app data. Mount options and UUID are recorded in `/etc/fstab`;
the user service checks for an ext4 mount at the SSD mountpoint before start.

## SQLite wheel database location

Wheel-cycle records use SQLite and default to a `data` directory at the root of
the repository:

```text
/mnt/saman-ssd/git_repo/fun-embed-sys/data/wheel.sqlite3
```

The default follows the repository root on both the Pi and development
machines. `FUN_EMBED_DB_PATH` can override it with an absolute path. The
`/data/` directory is ignored by Git so the private database and backups are
never committed.

Keep the Pi running one app process for this SQLite file; do not place it on a
network share or open it directly from another device. Back up the database
with the app stopped or use SQLite's online backup support.

## Re-check storage

Disk names can change after reconnects. Before mounting, use the filesystem
UUID or label rather than assuming `/dev/sda` remains the SSD:

```sh
lsblk -f
findmnt
df -hT
```

Verify the device, filesystem UUID, and mount before changing `/etc/fstab` or
moving the checkout. The ext4 filesystem UUID differs from the previous VFAT
UUID `9941-07F1`.
