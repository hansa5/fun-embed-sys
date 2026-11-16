# Documentation browser

This directory contains the Raspberry Pi and embedded-systems guides. The
React app discovers every non-hidden Markdown file recursively, so new `.md`
files and nested README files appear in its searchable navigation. Relative
links between Markdown guides open the linked document in the app.

## Run on a Raspberry Pi

Start with the [Raspberry Pi environment setup](rpi/environment_setup.md),
then follow the [Pi web app guide](rpi/web_app.md) to run the docs
browser as a boot-enabled service. For secure remote access, see
[Tailscale setup](tailscale/README.md).

## Run on a laptop

From the repository root, run `./install.sh` to prepare the `uv` environment,
then start the app with:

```sh
./run-app.sh
```

The app prints its URL in the terminal. The React development server is
available with `npm run dev` from `frontend/`; it proxies API requests to the
FastAPI backend on port 8501.
