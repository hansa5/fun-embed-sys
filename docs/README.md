# Documentation browser

This directory contains the Raspberry Pi and embedded-systems guides. The
Streamlit app discovers every non-hidden Markdown file recursively, so new
`.md` files and nested README files appear in the file picker automatically.
Relative links between Markdown guides open the linked document in the app.

## Run on a Raspberry Pi

Start with the [Raspberry Pi environment setup](rpi/environment_setup.md),
then follow the [Pi deployment guide](rpi/streamlit_app.md) to run the docs
browser as a boot-enabled service. For secure remote access, see
[Tailscale setup](tailscale/README.md).

## Run on a laptop

From the repository root, run `./install.sh` to prepare the `uv` environment,
then start the app with:

```sh
./run-app.sh
```

Streamlit prints the local URL in the terminal.
