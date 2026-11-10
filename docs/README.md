# Documentation browser

This directory contains the Raspberry Pi and embedded-systems guides. The
Streamlit app discovers every non-hidden Markdown file recursively, so new
`.md` files and nested README files appear in the file picker automatically.
Relative links between Markdown guides open the linked document in the app.

## Run on a Raspberry Pi

From the repository root on the Pi, create a virtual environment and install
the app dependency:

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r docs/requirements.txt
streamlit run docs/app.py --server.address 127.0.0.1 --server.port 8501
```

The app listens only on the Pi's loopback interface. To view it in a browser on
the laptop, keep the app running and open an SSH tunnel in another laptop
terminal:

```sh
ssh -L 8501:127.0.0.1:8501 saman@hansa.local
```

Then visit <http://localhost:8501> on the laptop. Stop the tunnel with
`Ctrl+C`; stop Streamlit with `Ctrl+C` in its terminal.

## Run on a laptop

From the repository root, install `docs/requirements.txt` in a virtual
environment, then run:

```sh
streamlit run docs/app.py
```

Streamlit prints the local URL in the terminal.
