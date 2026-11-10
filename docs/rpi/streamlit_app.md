# Run the documentation app on Salman

This guide installs and runs the Streamlit Markdown browser on Salman
(`hansa.local`). The app reads every non-hidden Markdown file under `docs/`,
including Markdown files added later. It binds to `127.0.0.1` on the Pi, so it
is not exposed to the local network or internet. Use an SSH tunnel to view it
from the laptop.

The examples assume the checkout is at
`~/Documents/git_repo/fun-embed-sys` and the Pi account is `saman`. Change the
path or account name if your setup differs.

## 1. Install Raspberry Pi OS packages

Connect from the laptop and update the Pi's package index:

```sh
ssh saman@hansa.local
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip openssh-client
```

These are operating-system packages. The Streamlit Python package will be
installed later inside a project virtual environment, not into system Python.

## 2. Give the Pi read-only access to GitHub

Do not copy the laptop's personal access token or private SSH key to the Pi.
The laptop uses its PAT locally for GitHub pushes. For a private repository,
give the Pi a separate, repository-scoped, read-only deploy key. If the
repository is public, anonymous HTTPS clone and pull need no credentials and
this section can be skipped.

On the Pi, generate a dedicated key pair. Use a passphrase if you can unlock
the key through an SSH agent when needed:

```sh
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_fun_embed -C "hansa-fun-embed-readonly"
cat ~/.ssh/id_ed25519_fun_embed.pub
```

Copy only the `.pub` output. In the repository on GitHub, open **Settings >
Deploy keys > Add deploy key**, give it a name such as `Salman read-only`,
paste the public key, and leave **Allow write access** unchecked. Never upload
or share the private key file.

To use this dedicated key without changing other SSH keys on the Pi, add a
host alias to `~/.ssh/config` (create the file if needed):

```sshconfig
Host github-fun-embed
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_fun_embed
    IdentitiesOnly yes
```

Protect the SSH files and test the GitHub connection:

```sh
chmod 700 ~/.ssh
chmod 600 ~/.ssh/config ~/.ssh/id_ed25519_fun_embed
ssh -T git@github-fun-embed
```

At first connection, verify GitHub's displayed SSH host fingerprint against
[GitHub's published fingerprints](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints)
before accepting it. A read-only deploy key allows the Pi to fetch and pull
this repository; it does not allow pushes.

## 3. Clone or update the checkout

Create the standard project directory and clone with the dedicated SSH alias:

```sh
mkdir -p ~/Documents/git_repo
cd ~/Documents/git_repo
git clone git@github-fun-embed:hansa5/fun-embed-sys.git
cd fun-embed-sys
```

If the repository is public and you chose to skip the deploy key, use this
clone URL instead:

```sh
git clone https://github.com/hansa5/fun-embed-sys.git
```

For future updates, make sure the working tree is clean, then pull the pushed
branch with fast-forward only:

```sh
cd ~/Documents/git_repo/fun-embed-sys
git status --short --branch
git pull --ff-only origin master
```

If you edit files directly on the Pi, commit or save those changes elsewhere
before pulling. Do not use `git reset --hard` to get around a dirty tree. Pull
only after the laptop has pushed the desired commit.

## 4. Create an isolated Python environment

From the repository root on the Pi:

```sh
cd ~/Documents/git_repo/fun-embed-sys
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r docs/requirements.txt
```

When `docs/requirements.txt` changes, pull the new commit and repeat the last
install command. Do not use `sudo pip` or install Streamlit into the system
Python environment.

## 5. Run Streamlit as a user service

Create a user service file:

```sh
mkdir -p ~/.config/systemd/user
nano ~/.config/systemd/user/fun-embed-docs.service
```

Paste this unit, updating `WorkingDirectory` and `ExecStart` if the checkout is
in a different location:

```ini
[Unit]
Description=Fun Embedded Systems documentation browser
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=%h/Documents/git_repo/fun-embed-sys
ExecStart=%h/Documents/git_repo/fun-embed-sys/.venv/bin/streamlit run docs/app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

Enable and start the service for the current user:

```sh
systemctl --user daemon-reload
systemctl --user enable --now fun-embed-docs.service
systemctl --user status fun-embed-docs.service
```

To have the user service start at boot even before `saman` logs in, enable
lingering once:

```sh
sudo loginctl enable-linger saman
```

View logs or restart after an app update:

```sh
journalctl --user -u fun-embed-docs.service -f
systemctl --user restart fun-embed-docs.service
```

## 6. Open it from the laptop

The service listens only on the Pi's loopback interface. On the laptop, open an
SSH tunnel and leave that terminal running:

```sh
ssh -L 8501:127.0.0.1:8501 saman@hansa.local
```

Open <http://localhost:8501> in a laptop browser. Stop the tunnel with
`Ctrl+C`. To stop the app service on the Pi, run
`systemctl --user stop fun-embed-docs.service`.

## Updating the app

1. On the laptop, commit and push the app or documentation changes to `master`.
   Keep the PAT on the laptop and supply it only to the local push operation;
   never send it through SSH or store it on the Pi.
2. On the Pi, run `git pull --ff-only origin master` from the checkout.
3. If dependencies changed, run
   `.venv/bin/python -m pip install -r docs/requirements.txt`.
4. Restart the service with
   `systemctl --user restart fun-embed-docs.service`.

See [GitHub setup for the laptop and Raspberry Pi](../github_setup.md) for
SSH keys, deploy keys, GitHub CLI, and PAT handling.
