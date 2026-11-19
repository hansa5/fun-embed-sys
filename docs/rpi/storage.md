# Raspberry Pi storage for app data

## SSD inventory (checked 2026-11-18)

The Pi `Hansa.local` has a **PNY CS900 500 GB SSD** at `/dev/sda` (465.8 GiB
reported by Linux). It has two partitions:

| Partition | Size | Filesystem | Label | UUID | Mounted |
| --- | ---: | --- | --- | --- | --- |
| `/dev/sda1` | 200 MB | VFAT | `EFI` | `67E3-17ED` | No |
| `/dev/sda2` | 465.6 GB | VFAT | `SAMAN` | `9941-07F1` | No |

Neither partition appears in `/etc/fstab`; the Pi currently boots and runs the
app from its 59 GB microSD (`/dev/mmcblk0p2`). The SSD was identified
read-only. It was not mounted, changed, or formatted during setup.

## SQLite wheel database

Wheel-cycle records use SQLite and default to:

```text
~/.local/share/fun-embed-sys/wheel.sqlite3
```

Set `FUN_EMBED_DB_PATH` to an absolute path to use another filesystem. The
identified `SAMAN` partition is VFAT and currently unmounted. Before placing a
long-lived SQLite database there, inspect any existing contents and choose a
Linux filesystem and mount configuration that provide reliable locking and
durable writes. Ext4 is the preferred Linux filesystem for this database.
Reformatting `/dev/sda2` would erase its contents and requires explicit
approval; no formatting or mount changes are included in the app feature.

After the SSD has been safely prepared and persistently mounted (for example
at `/mnt/saman-ssd`), set the application environment to:

```text
FUN_EMBED_DB_PATH=/mnt/saman-ssd/fun-embed/wheel.sqlite3
```

The service account must be able to create and write the database directory.
Keep the Pi running one app process for this SQLite file; do not place the file
on a network share or open it directly from another device. Back up the
database file while the app is stopped, or use SQLite's online backup support.

## Re-check storage

Disk names can change after reconnects. Before mounting, use the filesystem
UUID or label rather than assuming `/dev/sda` remains the SSD:

```sh
lsblk -f
findmnt
df -hT
```

The current partitions have VFAT UUIDs rather than ext4 UUIDs. Verify the
device, filesystem, and existing contents before changing the partition or
editing `/etc/fstab`.
