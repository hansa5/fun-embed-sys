# Documentation browser

This directory contains the Raspberry Pi and embedded-systems guides. The
Streamlit app discovers every non-hidden Markdown file recursively, so new
`.md` files and nested README files appear in the file picker automatically.
Relative links between Markdown guides open the linked document in the app.

## Run on a Raspberry Pi

For Raspberry Pi OS package installation, safe GitHub access, cloning and
pulling updates, virtual environment setup, and running Streamlit as a
localhost-only user service, follow the [Pi deployment guide](rpi/streamlit_app.md).

## Run on a laptop

From the repository root, install `docs/requirements.txt` in a virtual
environment, then run:

```sh
streamlit run docs/app.py
```

Streamlit prints the local URL in the terminal.
