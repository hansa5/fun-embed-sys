# Run the documentation app on Salman

This guide deploys the Markdown browser to Salman (`hansa.local`). It also
describes the reusable scripts for running other Streamlit or Flask apps on a
Raspberry Pi. The app binds to loopback by default; use Tailscale Serve for
private access away from home.

## Install and update the checkout

The Pi checkout is `~/Documents/git_repo/fun-embed-sys` for account `saman`.
Keep the laptop's GitHub token and private SSH keys on the laptop. The public
repository can be pulled over HTTPS without credentials. For a private repo,
give the Pi its own read-only deploy key as described in
[GitHub setup](../github_setup.md).

On the Pi:

```sh
cd ~/Documents/git_repo/fun-embed-sys
git status --short --branch
git pull --ff-only origin master
./install.sh
```

The environment installer uses Debian packages plus Astral's `uv` to create
and maintain `.venv` from the root `pyproject.toml` and `uv.lock`. See the
[Raspberry Pi environment setup](environment_setup.md) guide to add packages,
run Flask, or adjust the app settings.

Start the docs app interactively with:

```sh
./run-app.sh
```

It is available on the Pi at `http://127.0.0.1:8501`. To view from a laptop on
the home network, open an SSH tunnel:

```sh
ssh -L 8501:127.0.0.1:8501 saman@hansa.local
```

Then browse to <http://localhost:8501>. For secure access from outside home,
see [Tailscale setup](../tailscale/README.md); install and connect the
Tailscale app on each viewing device, then use the Serve HTTPS address in the
regular browser.

## Keep it running across restarts

Install the system service once, after `./install.sh`:

```sh
sudo ./install-service.sh
```

`fun-embed-app.service` starts at boot without waiting for a user login and
restarts automatically if the app exits. Inspect or restart it with:

```sh
sudo systemctl status fun-embed-app
sudo journalctl -u fun-embed-app -f
sudo systemctl restart fun-embed-app
```

The configuration is `/etc/default/fun-embed-app`. Its default launches
`docs/app.py` with Streamlit at `127.0.0.1:8501`. To switch to a Flask app,
set `APP_KIND=flask`, set `FLASK_TARGET=module:object`, and set `PORT`; install
the same project dependencies with `./install.sh`, then restart the service.
Flask runs through Waitress rather than its development server.

## Deploying later updates

1. Commit and push changes from the laptop.
2. On Salman, run `git pull --ff-only origin master`.
3. Run `./install.sh` if `pyproject.toml` or `uv.lock` changed.
4. Restart with `sudo systemctl restart fun-embed-app`.

The app discovers Markdown files recursively under `docs/`, so newly added
guides are picked up automatically after the page reloads.
