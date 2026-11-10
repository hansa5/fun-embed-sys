# Install Raspberry Pi OS

Use [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to install
Raspberry Pi OS on a microSD card. The [Raspberry Pi operating-system
downloads](https://www.raspberrypi.com/software/operating-systems/) page also
provides images for manual installation.

> **Warning:** Writing an image erases the selected card. Check the target
> device carefully before starting.

## What you need

- A Raspberry Pi and a compatible power supply
- A microSD card supported by your Pi
- A computer with an SD card reader
- A network connection for downloading the operating system

## Install with Raspberry Pi Imager

1. Download and install Raspberry Pi Imager on your computer.
2. Insert the microSD card and open Imager.
3. Select the Raspberry Pi model, operating system, and the correct storage
   device.
4. Open the customization settings before writing:
   - Set a hostname, such as `mediaserver` or `raspberrypi`.
   - Create a username and a strong password. Do not reuse example
     credentials from a guide.
   - Configure wireless LAN if the Pi will use Wi-Fi.
   - Set the locale and time zone.
   - Enable SSH if you plan to administer the Pi remotely. Prefer
     authentication with an SSH key when available.
5. Review the selected storage device, then write the image and wait for
   verification to finish.
6. Safely eject the card, insert it into the Pi, connect the network and power,
   and allow it to boot.

Customization screen labels may change between Imager versions. If a setting
is not available there, complete it on the Pi with a monitor and keyboard or
follow the relevant [general setup guide](general.md).

## First connection

From another computer on the same network, connect using the account created
in Imager:

```sh
ssh your-user@your-hostname.local
```

For example, if you chose hostname `mediaserver` and username `piuser`:

```sh
ssh piuser@mediaserver.local
```

If `.local` names do not resolve on your network, find the Pi's IP address
using your router or the [network discovery notes](general.md#find-the-ip-address).
For a media-server walkthrough, continue to [Raspberry Pi media server](media_server.md).

## Related guides

- [General setup and SSH](general.md)
- [Raspberry Pi media server](media_server.md)
- [Raspberry Pi software downloads](https://www.raspberrypi.com/software/operating-systems/)
