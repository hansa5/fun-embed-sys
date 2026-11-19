# Run the stock analysis app on Saman

The app uses React for the responsive stock dashboard and FastAPI for market
data, earnings dates, options, and the Docs viewer. The dashboard includes
historical charts, company metrics, financial statements, dividends, and an
SQLite-backed Wheel Strategy tracker. See the
[stock analysis guide](../trading/README.md) for data-source and interpretation
notes and the [Wheel Strategy guide](../trading/wheel-strategy.md) for state
transitions and alert behavior. The Docs tab reads Markdown files recursively
from `docs/`.

The server listens on `0.0.0.0:8501` by default, so devices on your local
network can open <http://hansa.local:8501>. Use Tailscale for private access
when away from home; do not configure router port forwarding for this app.

## Install or update on the Pi

For Codex deployment workflows, see [Codex skills for Raspberry Pi](codex_skills.md).

The SSD-backed checkout for account `saman` is
`/mnt/saman-ssd/git_repo/fun-embed-sys`. Keep the laptop's GitHub token and
private SSH keys on the laptop. This public repository can be pulled over
HTTPS without credentials.

```sh
cd /mnt/saman-ssd/git_repo/fun-embed-sys
git status --short --branch
git pull --ff-only origin master
./install.sh
```

The installer prepares Python dependencies from `pyproject.toml` and
`uv.lock`, installs Node.js/npm in the current user's local data directory if
needed, runs `npm ci`, and builds the React assets into the ignored
`frontend/dist/` directory. Vite requires Node.js 20.19+ or 22.12+.

## Start it manually

```sh
./run-app.sh
```

The FastAPI server serves both the API and the built React app on port 8501.
Override the listener or port when needed:

```sh
HOST=127.0.0.1 PORT=8502 ./run-app.sh
```

Check the API with `curl http://127.0.0.1:8501/api/health`. Open the UI at
`http://hansa.local:8501` from a device on your home network.

For frontend development, run `npm run dev` inside `frontend/` while
`./run-app.sh` runs the API. Vite serves the UI on port 5173 and proxies `/api`
requests to port 8501.

## Start at boot and restart after failures

Install the system service once after dependencies are ready:

```sh
sudo ./install-service.sh
```

It enables `fun-embed-app.service` at boot and restarts the process after
failures. The default settings are `HOST=0.0.0.0` and `PORT=8501` in
`/etc/default/fun-embed-app`.

```sh
sudo systemctl status fun-embed-app
sudo journalctl -u fun-embed-app -f
sudo systemctl restart fun-embed-app
```

After pulling code changes, run `./install.sh` to rebuild the frontend and
sync Python packages, then restart the service. If it does not respond, check
the service and logs first; `curl http://127.0.0.1:8501/api/health` checks the
backend independently of the browser.

Wheel records default to `data/wheel.sqlite3` under the repository root, which
is `/mnt/saman-ssd/git_repo/fun-embed-sys/data/wheel.sqlite3` on the Pi. The
`/data/` directory is excluded from Git. Set `FUN_EMBED_DB_PATH` only when you
need a different location. Read the [Pi storage notes](storage.md) for the SSD
mount and filesystem UUID.

## Add dependencies

- Python packages go in `pyproject.toml`; use `uv add package`, then commit
  `pyproject.toml` and `uv.lock`.
- Frontend packages go in `frontend/package.json`; use `npm install package`
  from `frontend/`, then commit `package.json` and `package-lock.json`.
- Run `./install.sh` after pulling dependency changes on the Pi.

## Tailscale access

Use the [Tailscale guide](../tailscale/README.md) to install and authenticate
Tailscale, then publish the local app privately with Tailscale Serve.
