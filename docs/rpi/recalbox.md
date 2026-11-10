# Recalbox notes

Personal setup and troubleshooting notes for Recalbox on a Raspberry Pi.
Menu names and file locations can vary by Recalbox release; check the
[official Recalbox documentation](https://wiki.recalbox.com/) for the version
you are using.

## SSH access

Enable SSH using the Recalbox settings for your release, then connect with:

```sh
ssh root@recalbox.local
```

The login method and credentials depend on the installed release and its
configuration. Do not rely on default credentials: set a unique password,
never publish it in documentation, and do not expose the SSH service directly
to the public internet.

## Dashboard

On the same local network, open `http://recalbox.local/` in a browser. If the
hostname does not resolve, use the device's IP address.

## Wi-Fi configuration

If supported by your release, edit the configuration file over SSH:

```sh
nano /recalbox/share/system/recalbox.conf
```

Set the relevant entries for your own wireless network, for example:

```ini
wifi.enabled=1
wifi.ssid=YOUR_WIFI_NAME
wifi.key=YOUR_WIFI_PASSWORD
```

Treat this file as sensitive because it contains the Wi-Fi password. Confirm
the exact setting names and reload/reboot behavior in the documentation for
your Recalbox release.

## Controller configuration not persisting

If controller mappings reset after reboot:

1. Check that the Recalbox share storage is writable:

   ```sh
   mount | grep '/recalbox/share'
   ```

2. If the share is mounted read-only, investigate the filesystem or storage
   issue before remounting it. A temporary remount may help diagnose the
   problem, but it does not fix the underlying cause:

   ```sh
   mount -o remount,rw /recalbox/share
   ```

3. Restart Recalbox and test whether a small configuration change persists.

Avoid deleting controller configuration files as a first step. If a reset is
necessary, back up the relevant files and follow the instructions for your
Recalbox version.

## Useful commands and links

Check a file's MD5 checksum:

```sh
md5sum path/to/file
```

Discover devices on a network you own or are authorized to administer (replace
the example subnet with your local network's CIDR):

```sh
nmap -sn 192.168.1.0/24
```

- [Recalbox documentation](https://wiki.recalbox.com/)
- [Add themes to EmulationStation](https://wiki.recalbox.com/en/tutorials/frontend-customization/add-themes-into-emulationstation)
