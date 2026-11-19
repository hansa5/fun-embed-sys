# Raspberry Pi storage for app data

## SSD inventory and app layout

The Pi `Hansa.local` has a **PNY CS900 500 GB SSD** at `/dev/sda` (465.8 GiB
reported by Linux). The EFI partition `/dev/sda1` (200 MB, VFAT, UUID
`67E3-17ED`) is not used by the app. The former data partition `/dev/sda2`
(465.6 GB, VFAT label `SAMAN`, UUID `9941-07F1`) was approved for formatting
as ext4 because its prior filesystem cannot reliably host this Linux app's
environment and SQLite data. After migration, identify it by its new ext4 UUID
with `lsblk -f`; do not rely on `/dev/sda` numbering.

Mount the ext4 data partition persistently at `/mnt/saman-ssd`. The repository
checkout is:

```text
/mnt/saman-ssd/git_repo/fun-embed-sys
```

The Pi boots from its 59 GB microSD (`/dev/mmcblk0p2`); this SSD hosts the app
checkout and app data. Mount options, UUID, and the service dependency on the
mount are recorded in `/etc/fstab` and the user service override after setup.

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
