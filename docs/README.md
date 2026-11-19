# Stock analysis and project guides

The app opens on Stock Analysis. Select the Docs tab in the left sidebar to
expand the searchable guide list. It discovers every non-hidden Markdown file
recursively, so new `.md` files and nested README files appear automatically.
Read [the stock analysis guide](trading/README.md) for explanations of the
chart, company metrics, reports, dividends, and data limits. The new
[Wheel Strategy guide](trading/wheel-strategy.md) describes its SQLite-backed
state machine, recorded transitions, alerts, and data limits.

This directory also contains the Raspberry Pi and embedded-systems guides.
Relative links between Markdown guides open the linked document in the app.

## Run on a Raspberry Pi

Start with the [Raspberry Pi environment setup](rpi/environment_setup.md),
then follow the [Pi web app guide](rpi/web_app.md) to run the app as a
boot-enabled service. For secure remote access, see
[Tailscale setup](tailscale/README.md). The [Pi storage notes](rpi/storage.md)
document the attached SSD and wheel database path.

## Run on a laptop

From the repository root, run `./install.sh` to prepare the `uv` environment,
then start the app with:

```sh
./run-app.sh
```

The app prints its URL in the terminal. The React development server is
available with `npm run dev` from `frontend/`; it proxies API requests to the
FastAPI backend on port 8501.
