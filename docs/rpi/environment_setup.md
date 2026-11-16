# Raspberry Pi application environment

This guide prepares Debian-based Raspberry Pi OS for the Python applications
in this repository. The root `install.sh` installs required operating-system
build tools when needed, installs Astral's `uv`, and synchronizes the project
environment into `.venv` from `pyproject.toml` and `uv.lock`.

## Requirements

- Raspberry Pi OS or another Debian-based Linux distribution.
- A network connection for package downloads.
- A normal account with `sudo` access for missing apt packages.
- Git access to this repository. Keep any laptop GitHub token on the laptop;
  do not copy it onto the Pi.

## Install

Clone the repository if needed, then run:

```sh
git clone https://github.com/hansa5/fun-embed-sys.git
cd fun-embed-sys
./install.sh
```

The script uses apt for Git, curl, certificates, Python, virtual environment
support, and native build tools. It installs `uv` in the current user's local
bin directory and runs `uv sync`, which creates `.venv` and installs the
locked dependencies. It does not install Python packages globally.

## Add or change Python packages

The editable dependency list is in the root `pyproject.toml`. From the repo
root, add packages with `uv add`, for example:

```sh
uv add requests
uv add --dev ruff
```

Commit both `pyproject.toml` and `uv.lock`. On each Pi, pull the change and run
`./install.sh` again. Remove a dependency with `uv remove package-name`.

The initial dependencies include Streamlit for the Markdown browser and Flask
plus Waitress for optional Flask apps. Waitress serves Flask apps as a
production WSGI server; Flask's built-in development server is not used for
the boot service.

## Start an application

The default command starts the docs browser on loopback at port 8501:

```sh
./run-app.sh
```

To select a different Streamlit file or port:

```sh
STREAMLIT_APP=path/to/app.py PORT=8502 ./run-app.sh
```

To run a Flask application whose WSGI object is `app` in `app.py`:

```sh
APP_KIND=flask FLASK_TARGET=app:app PORT=5000 ./run-app.sh
```

`HOST` defaults to `127.0.0.1` so the app is not exposed on the local network.
Tailscale Serve can securely proxy this local listener to devices in your
tailnet. See [Tailscale setup](../tailscale/README.md).

## Start automatically at boot and recover after crashes

After installing dependencies, create the system-level service:

```sh
sudo ./install-service.sh
```

This installs and enables `fun-embed-app.service`, which starts at boot without
requiring an interactive login and automatically restarts the app after an
exit. Its settings are in `/etc/default/fun-embed-app`; edit that file to
choose Streamlit or Flask, app path, host, or port, then restart:

```sh
sudo systemctl restart fun-embed-app
sudo systemctl status fun-embed-app
sudo journalctl -u fun-embed-app -f
```

After a reboot, check `sudo systemctl status fun-embed-app` and the journal if
the app does not respond. For code updates, use `git pull --ff-only`, rerun
`./install.sh` if dependencies changed, then restart the service.

## Further reading

- [GitHub setup and credentials](../github_setup.md)
- [Tailscale installation and private browser access](../tailscale/README.md)
