# Raspberry Pi application environment

This repository uses Python for the API and application logic, and React for
the browser interface. `./install.sh` installs OS prerequisites, synchronizes
Python packages with `uv`, installs the frontend packages with npm, and builds
the React app for FastAPI to serve.

## Requirements

- Raspberry Pi OS or another Debian-based Linux distribution.
- A network connection for package downloads.
- A normal account with `sudo` access when apt packages are missing.
- A supported Pi architecture (64-bit ARM is supported) and internet access.
- Git access to this repository. Keep laptop tokens on the laptop.

## Install

Clone the repository if needed, then run:

```sh
git clone https://github.com/hansa5/fun-embed-sys.git
cd fun-embed-sys
./install.sh
```

The installer uses apt for Git, curl, certificates, Python, venv and build
support. It installs Astral's `uv` and Node.js 22 in the current user's local
directories when needed, runs `uv sync --locked`, runs `npm ci`, then builds
the React frontend into `frontend/dist/`. Python dependencies stay in `.venv`;
frontend dependencies stay under `frontend/node_modules/`. Vite requires
Node.js 20.19+ or 22.12+.

## Add or change dependencies

For Python packages, edit the project with `uv add`, for example:

```sh
uv add fastapi
uv add --dev ruff
```

This updates `pyproject.toml` and `uv.lock`. For browser packages, from
`frontend/` run:

```sh
npm install package-name
```

This updates `package.json` and `package-lock.json`. Commit the lockfiles with
their manifests. On the Pi, pull the commit and rerun `./install.sh`.

If a future Python dependency needs native compilation, install its
documented system headers first, then rerun the installer.

## Run the application

```sh
./run-app.sh
```

This starts FastAPI on `0.0.0.0:8501` by default and serves the compiled React
interface plus the `/api` endpoints. Use `HOST=127.0.0.1` to restrict access
to the Pi itself, or `PORT=8502` to change ports:

```sh
HOST=127.0.0.1 PORT=8502 ./run-app.sh
```

For local frontend development, keep FastAPI running and launch Vite from
`frontend/`:

```sh
npm run dev
```

Vite listens on port 5173 and proxies `/api` requests to FastAPI on port 8501.

## Start at boot and recover after crashes

After installing dependencies, create the system service:

```sh
sudo ./install-service.sh
```

It enables `fun-embed-app.service` at boot without requiring an interactive
login and restarts the app after failures. Its environment file is
`/etc/default/fun-embed-app`:

```sh
sudo systemctl status fun-embed-app
sudo journalctl -u fun-embed-app -f
sudo systemctl restart fun-embed-app
```

The default listener is `0.0.0.0:8501` for home-network access. For access
outside home, use [Tailscale Serve](../tailscale/README.md) and keep router
port forwarding disabled.
