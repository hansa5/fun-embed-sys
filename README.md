# Fun Embedded Systems Projects

Notes and step-by-step guides for Raspberry Pi and other embedded-system
projects. The guides are plain Markdown and are intended to be readable in
GitHub now and usable as the source for a personal documentation site later.

## Raspberry Pi guides

- [Install Raspberry Pi OS](docs/rpi/os_install.md) — prepare a microSD card
  and complete the first boot.
- [General setup](docs/rpi/general.md) — SSH, network discovery, and useful
  system information.
- [Media server](docs/rpi/media_server.md) — set up Plex, mount a media drive
  persistently, and copy files over SSH.
- [Pi-hole and other projects](docs/rpi/pi-hole.md) — project references and
  starting points.
- [Recalbox](docs/rpi/recalbox.md) — network, controller, and troubleshooting
  notes.

## Getting started

1. Follow the [Raspberry Pi OS installation guide](docs/rpi/os_install.md).
2. Use the [general setup guide](docs/rpi/general.md) to enable and connect
   over SSH.
3. Choose a project guide above and replace example hostnames, usernames,
   device names, and network addresses with your own.

## Publishing these docs

GitHub renders these Markdown files directly. To publish them as a personal
website, enable GitHub Pages for this repository and choose a publishing
source, or add a documentation-site generator when you are ready. Review the
pages first and remove personal information, passwords, tokens, and private
network details before making the site public.

## Raspberry Pi inventory

| Name | Hostname | Purpose |
| --- | --- | --- |
| Saman | `Hansa.local` | Trading and stock learning |
| Plex | `media-server.local` | Media server on the local network |


## GitHub access

- [GitHub setup for the laptop and Raspberry Pi](docs/github_setup.md) — SSH keys, GitHub CLI, and safe handling of personal access tokens.


## Stock analysis workspace

The React + FastAPI app includes a responsive stock analysis dashboard with
popular ticker suggestions, historical price charts, company metrics,
financial statements, dividend history, an earnings calendar, and a SQLite-
backed Wheel Strategy tracker with explicit state changes and configurable
alerts. The strategy tracker does not place orders or connect to a brokerage.
The guides are grouped under one Docs tab in the left sidebar. Read the
[stock analysis guide](docs/trading/README.md), [Wheel Strategy guide](docs/trading/wheel-strategy.md),
and [Pi storage notes](docs/rpi/storage.md) for details.


## Run the docs browser on a Pi

See [Raspberry Pi environment setup](docs/rpi/environment_setup.md) for
dependencies and the `uv` environment, then [web app on Raspberry Pi](docs/rpi/web_app.md)
for deployment and automatic startup. The app listens on the local network at
`http://hansa.local:8501`. [Tailscale setup](docs/tailscale/README.md) explains
private HTTPS access from a phone or laptop.
