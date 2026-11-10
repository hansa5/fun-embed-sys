# Raspberry Pi media server

This guide covers a basic Plex media server: install Raspberry Pi OS, connect
over SSH, mount a USB drive at a stable path, and copy media to it. Replace
`piuser`, `mediaserver`, and example file paths with your own values.

For general OS installation and SSH setup, see [Install Raspberry Pi OS](os_install.md)
and [General setup](general.md). The original [Pimylifeup Plex guide](https://pimylifeup.com/raspberry-pi-plex-server/)
is a useful additional reference; use Plex's current official instructions for
installation steps that depend on the OS release.

## 1. Install and prepare Raspberry Pi OS

1. Install Raspberry Pi OS using the [OS installation guide](os_install.md).
   In Raspberry Pi Imager's customization settings, set a hostname (for
   example, `mediaserver`), create your own user, configure Wi-Fi if needed,
   and enable SSH.
2. Connect to the Pi from a computer on the same network:

   ```sh
   ssh piuser@mediaserver.local
   ```

   If `.local` name resolution is unavailable, use the Pi's IP address instead.
3. Update the Pi, then reboot if the upgrade requests it:

   ```sh
   sudo apt update
   sudo apt full-upgrade
   sudo reboot
   ```

   Reconnect over SSH after it starts again.

## 2. Identify and prepare the media drive

Connect the USB SSD or hard drive, then identify its partition, filesystem,
and UUID:

```sh
lsblk -o NAME,SIZE,FSTYPE,LABEL,UUID,MOUNTPOINTS
```

Use the partition (for example, `/dev/sda1`), not the whole disk (`/dev/sda`).
Device names such as `/dev/sda1` can change between boots, so use the UUID in
the persistent mount configuration below. Do not format a drive that contains
files you want to keep; formatting erases its data.

This example assumes the partition is already formatted as `ext4`. If yours
uses another filesystem, use the filesystem shown by `lsblk` and check its
mount options before copying the example. In particular, filesystems such as
exFAT do not store Linux ownership and permissions in the same way as ext4.

## 3. Mount the drive at the same path on every boot

Choose a permanent mount point. This guide uses `/srv/media`:

```sh
sudo mkdir -p /srv/media
sudo blkid /dev/sda1
```

Copy the `UUID` value for the correct partition from the output. Edit the
filesystem table:

```sh
sudo nano /etc/fstab
```

Add one line at the end, replacing `YOUR-UUID` with the actual UUID. Keep
`ext4` only if that is the drive's filesystem:

```fstab
UUID=YOUR-UUID /srv/media ext4 defaults,nofail,x-systemd.device-timeout=10 0 2
```

`nofail` lets the Pi finish booting if the drive is disconnected; the mount
will be unavailable until the drive is connected and mounted. Do not add a
duplicate entry if this drive is already listed in `/etc/fstab`.

Check the configuration and mount it now:

```sh
sudo findmnt --verify
sudo systemctl daemon-reload
sudo mount -a
findmnt /srv/media
df -h /srv/media
```

Confirm that `findmnt` shows the expected drive at `/srv/media`. Reboot to
verify that it mounts automatically:

```sh
sudo reboot
```

Reconnect and run `findmnt /srv/media` again. If it is not mounted, check the
UUID, filesystem type, and `/etc/fstab` entry before trying again. Do not copy
files into `/srv/media` until you have confirmed the drive is mounted; otherwise
the files may be written to the Pi's SD card instead.

```sh
ssh plex@mediaserver.local
sudo mount /dev/sda1 /media/plex/PLEXMEDIA
systemctl daemon-reload
```
## 4. Allow Plex and your SSH user to access the media

Install Plex using the current instructions from
[Plex Support](https://support.plex.tv/articles/200264746-quick-start-step-1-installation/).
The following permission example is for an ext4 drive and a Plex installation
that runs as the `plex` user:

```sh
sudo usermod -aG plex "$USER"
sudo chown -R "$USER":plex /srv/media
sudo chmod -R g+rwX /srv/media
sudo find /srv/media -type d -exec chmod g+s {} +
```

The ownership and permission commands may take a while for a large library.
Reconnect over SSH after `usermod` so the new group membership takes effect.
If Plex uses a different service account, or the drive uses exFAT/NTFS, check
the Plex and filesystem documentation rather than applying these ext4
commands unchanged.

## 5. Copy files from your computer

Create a destination directory on the Pi (change `piuser` if necessary):

```sh
ssh plex@mediaserver.local 'mkdir -p /srv/media/Movies'
```

Copy one file:

```sh
scp "/home/youruser/Videos/Example Movie.mp4" \
  piuser@mediaserver.local:"/srv/media/Movies/"
```

Copy a directory and its contents:

```sh
scp -r "/home/youruser/Videos/Season 02" \
  piuser@mediaserver.local:"/srv/media/TV Shows/"
```

These `scp` commands run on your computer, not in the SSH session on the Pi.
Keep paths with spaces quoted. Confirm the copy on the Pi with `ls` before
adding or refreshing the Plex library.

## 6. Open Plex

From a browser on your local network, open:

```text
http://mediaserver.local:32400/web
```

If the hostname does not resolve, substitute the Pi's IP address. In Plex,
create libraries that point to folders under `/srv/media`.

## Further reading

- [Raspberry Pi OS installation](os_install.md)
- [General Raspberry Pi setup and SSH](general.md)
- [Plex installation quick start](https://support.plex.tv/articles/200264746-quick-start-step-1-installation/)
- [Pimylifeup: Raspberry Pi Plex server](https://pimylifeup.com/raspberry-pi-plex-server/)
