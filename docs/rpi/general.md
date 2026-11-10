# General Raspberry Pi setup

Common setup and troubleshooting notes for Raspberry Pi. For a new device,
start with [Install Raspberry Pi OS](os_install.md).

## Identify the model and operating system

Run these commands in a terminal on the Pi or in an SSH session:

```sh
# Kernel and architecture
uname -a

# Raspberry Pi model
tr -d '\0' </sys/firmware/devicetree/base/model
printf '\n'

# OS release
cat /etc/os-release
```

## Enable SSH

SSH can be enabled in Raspberry Pi Imager's customization settings before
first boot. On an already running Pi, use:

```sh
sudo raspi-config
```

Select **Interface Options** (or the equivalent menu in your OS version),
then enable **SSH**. Connect from another computer on the same network:

```sh
ssh your-user@your-hostname.local
```

Use the username you created during OS setup. Do not put account passwords in
scripts, documentation, or shell commands. For a server reachable outside
your home network, use a VPN or another secure access method rather than
exposing SSH directly to the internet.

## Find the IP address

- **On the Pi:** run `hostname -I` or `ip addr`.
- **In your router:** look for the Pi under connected devices or DHCP leases;
  it may appear under its configured hostname.
- **From another device:** try `ping your-hostname.local`, if your network
  supports mDNS. If you use a network-discovery tool, scan only networks you
  own or are authorized to administer.

An IP address assigned by DHCP can change. If you need a predictable address,
set a DHCP reservation in your router rather than hard-coding an address that
may conflict with another device.

## WLAN USB adapters

See the [eLinux USB Wi-Fi adapter list](https://elinux.org/RPi_USB_Wi-Fi_Adapters)
for adapter compatibility notes. This setup has used a TP-Link `TL-WN723N v3`
with a Realtek `RTL8188EUS` chipset. Driver support depends on the Raspberry
Pi OS release and kernel; check the current OS documentation if the adapter
is not detected.

## Related guides

- [Install Raspberry Pi OS](os_install.md)
- [Raspberry Pi media server](media_server.md)
- [Raspberry Pi Foundation documentation](https://www.raspberrypi.com/documentation/)

## Manual first setup from an SD card

This section is for a Raspberry Pi OS image written to a microSD card without
using Raspberry Pi Imager's preconfigured settings. It assumes you can attach a
monitor and keyboard for the first boot. Raspberry Pi OS does not have a
universal default `pi` account: create a user during first boot if prompted.

1. Write Raspberry Pi OS to the microSD card using Raspberry Pi Imager or
   another image writer. Eject the card safely, insert it into the Pi, and
   connect a monitor, keyboard, Ethernet (optional), and power.
2. Complete the first-boot wizard. Set your country, language, time zone, a
   unique hostname, a username, and a strong password. Record the username;
   you will use it for SSH. Do not reuse credentials shown in examples.
3. Connect to Wi-Fi from the desktop network menu, or open a terminal and run
   `sudo raspi-config`. Use **System Options > Wireless LAN** to enter the
   network name (SSID) and password. Menu names can vary slightly by OS
   release. Reboot if prompted.
4. In `sudo raspi-config`, use **System Options > Hostname** to set or change
   the device name. Choose a simple name such as `labpi` (letters, digits, and
   hyphens; do not include `.local`). Reboot if prompted.
5. In `sudo raspi-config`, choose **Interface Options > SSH**, select **Yes**
   to enable the SSH server, then exit. On Raspberry Pi OS releases where the
   menu differs, use the equivalent SSH setting. Reboot if needed.
6. Find the Pi's address with `hostname -I`, or check the router's DHCP client
   list. From a laptop on the same network, connect with:

   ```sh
   ssh YOUR_USERNAME@labpi.local
   ```

   Replace `YOUR_USERNAME` and `labpi` with the values you chose. If
   `labpi.local` does not resolve, use the Pi's IP address instead, for example
   `ssh YOUR_USERNAME@192.168.1.42`.

### Set up SSH key login from the laptop

On the laptop, create a key pair if you do not already have one. Keep the
private key (`id_ed25519`) on the laptop and never copy or share it. Add the
public key to the Pi:

```sh
ssh-keygen -t ed25519 -C "laptop-to-labpi"
ssh-copy-id YOUR_USERNAME@labpi.local
```

If `ssh-copy-id` is unavailable, print the public key with
`cat ~/.ssh/id_ed25519.pub`, connect to the Pi using your password, and append
the public key as one line to `~/.ssh/authorized_keys` on the Pi. Then test
from the laptop:

```sh
ssh YOUR_USERNAME@labpi.local
```

The key should let you log in without entering the Pi account password. Keep
password authentication enabled until key login works. If you later choose to
disable password-based SSH, first confirm you have working key access and a
local recovery method. Do not expose SSH directly to the public internet; use
a trusted VPN for remote access.

## Install and use Codex CLI on Raspberry Pi

Codex CLI can run in a terminal on the Pi and work with files on the Pi. The
Pi needs internet access. Start from an SSH session from the laptop, or use the
Pi's local terminal. Install Node.js/npm if using the npm option; alternatively
use the official standalone Linux installer:

```sh
curl -fsSL https://chatgpt.com/codex/install.sh | sh
```

Or, with Node.js and npm installed:

```sh
npm install -g @openai/codex
```

Confirm it is on the path and launch it in a project directory:

```sh
codex --version
mkdir -p ~/projects
cd ~/projects
codex
```

For sign-in, choose **Sign in with ChatGPT** and complete the browser flow. On
a headless Pi accessed over SSH, use device-code sign-in if available:

```sh
codex login --device-auth
```

Open the displayed URL on the laptop, sign in, then enter the one-time code
shown by the CLI. Device-code login may need to be enabled in ChatGPT account
security settings or by a workspace administrator. Check the result with
`codex login status`.

If device-code sign-in is unavailable, forward the CLI's local browser
callback over SSH. From a laptop terminal, open the tunnel:

```sh
ssh -L 1455:localhost:1455 YOUR_USERNAME@labpi.local
```

In that SSH session, run `codex login`. Open the sign-in URL it prints in the
laptop browser and finish the login. Keep the SSH tunnel open until login
completes. Treat Codex's local authentication cache as a password; do not
commit or share it.

### Use the Pi from the laptop and pair a phone

Use SSH from the laptop to open Codex running on the Pi:

```sh
ssh YOUR_USERNAME@labpi.local
cd ~/projects/YOUR_PROJECT
codex
```

The QR-code phone pairing described by OpenAI is a separate feature in the
ChatGPT desktop app. To pair it, install and sign in to the ChatGPT desktop app
on the laptop, open **Settings > Connections > Control this Mac or PC**, choose
**Set up** or **Add**, and scan the displayed QR code with the ChatGPT mobile
app. Select the laptop in the mobile app. Keep the laptop awake, online, and
signed in to the same account and workspace as the phone. This connects the
phone to Remote tasks on the laptop; the QR pairing does not connect the phone
directly to the Pi's Codex CLI. Use the SSH steps above when you want a terminal
on the laptop to control Codex on the Pi.

For current installation and authentication details, see the [Codex CLI
quickstart](https://developers.openai.com/codex/cli), [Codex authentication
guide](https://learn.chatgpt.com/docs/auth), and [Working on your
phone](https://developers.openai.com/training/walkthroughs/working-on-your-phone).
