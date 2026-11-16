# Tailscale access to Raspberry Pi applications

Tailscale connects your Pi and your trusted devices to a private tailnet. The
app can continue listening only on `127.0.0.1`; Tailscale Serve provides an
HTTPS address inside your tailnet. This does not expose the app to the public
internet and does not use Funnel.

## Install and authenticate Tailscale on the Pi

From the repository root on the Pi, run:

```sh
sudo ./install-tailnet.sh
```

The installer uses Tailscale's official Debian/Raspberry Pi OS installer if
the client is missing. If it says authentication is needed, run:

```sh
sudo tailscale up
```

Open the sign-in URL it prints, sign in to the tailnet you use on your phone
and laptop, then configure Serve:

```sh
sudo ./install-tailnet.sh
```

The script configures background Serve for the app on `127.0.0.1:8501` and
enables `tailscaled` at boot. If your app uses another port, pass it explicitly,
for example `sudo ./install-tailnet.sh 5000` for a Flask service set to port
5000 in `/etc/default/fun-embed-app`.

## Open the app

Install and sign in to Tailscale on the laptop and phone using the same
tailnet. On the Pi, check its DNS name and Serve address:

```sh
tailscale status
sudo tailscale serve status
```

Open the HTTPS Serve URL shown by the command in any regular browser on your
phone or laptop, such as Safari, Chrome, or Firefox. The Tailscale app must be
connected on that device so its browser traffic can reach the private tailnet.
You do not browse inside the Tailscale app itself.

## Boot and troubleshooting

The Pi application is managed by `fun-embed-app.service` and starts at boot.
`tailscaled` is enabled at boot, and background Serve configuration persists
across reboots. Check each layer independently:

```sh
sudo systemctl status fun-embed-app tailscaled
sudo journalctl -u fun-embed-app -n 100 --no-pager
tailscale status
sudo tailscale serve status
```

Restart the app with `sudo systemctl restart fun-embed-app`. To turn off
Tailscale Serve, run `sudo tailscale serve off`. To stop Tailscale on the Pi,
run `sudo tailscale down`.

The Serve URL requires the Pi and viewing device to be signed into the same
tailnet, and the tailnet's access policy must allow that connection. Never
configure `tailscale funnel` for this private app unless you deliberately
intend to publish it to the internet.

## References

- [Install Tailscale on Linux](https://tailscale.com/docs/install/linux)
- [Tailscale Serve](https://tailscale.com/docs/reference/tailscale-cli/serve)
- [Raspberry Pi application environment](../rpi/environment_setup.md)
