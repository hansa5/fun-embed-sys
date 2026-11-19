---
name: pi-direct-deploy
description: Develop Fun Embed Project directly in its Raspberry Pi checkout, push the requested changes to GitHub, rebuild the app, and restart and verify its service. Use when Codex is running on the Pi; use pi-github-sync for laptop-to-Pi deployment.
---

# Develop and deploy from the Pi

Use this workflow when the requested Fun Embed changes are being made in the Pi's own checkout. Confirm the host, repository root, branch, and `origin` before changing files. The usual checkout on Saman (`Hansa.local`) is `/mnt/saman-ssd/git_repo/fun-embed-sys`; verify `/mnt/saman-ssd` is mounted from the PNY SSD before editing or installing. Do not assume the path if the current environment differs. The legacy SD-card checkout may remain at `~/Documents/git_repo/fun-embed-sys` as a rollback copy; do not use it as the deployed checkout.

## Edit and review

1. Inspect `git status --short --branch`, the current branch, and `git remote -v`. Preserve unrelated user changes. Do not reset, clean, or overwrite them.
2. Make the requested app changes in this Pi checkout. Follow `docs/rpi/web_app.md` for the service and environment. The SQLite database defaults to `data/wheel.sqlite3` under this checkout; verify that path resolves to the mounted SSD. Keep credentials, `.env` files, tokens, local databases, and generated build output out of Git.
3. Review the diff and selected file list. Run `git diff --check` and the production frontend build when frontend files changed. Run syntax validation for backend changes. Do not add or run tests unless requested.
4. Stage only the requested changes, inspect the staged diff, and commit with a concise message. Push the current branch to `origin` without force. Do not push if unrelated or ambiguous changes are mixed into the staged diff.

## Redeploy on the same Pi

After the push succeeds, run `./install.sh` from the SSD-backed repository root to synchronize dependencies and rebuild the frontend. Inspect which existing service is installed and active. Prefer `fun-embed-app.service`; if the legacy user service `fun-embed-docs.service` is active instead, restart that unit. Confirm the service depends on `/mnt/saman-ssd` so it cannot silently run from the SD-card mountpoint when the SSD is absent. Restart only the existing service, then check its status and `curl -fsS http://127.0.0.1:8501/api/health`. Confirm the deployed checkout and `data/wheel.sqlite3` resolve onto the SSD and that the checkout points at the pushed commit.

If installation, restart, or health verification fails, inspect logs and report the point of failure. Do not silently edit service configuration, install a new service, force-push, or discard local work. Ask before changes that erase data or alter system configuration.

## Scope

This workflow publishes the requested commit to the configured GitHub remote and redeploys the current Pi checkout. Do not modify another Pi or deploy another project unless asked. Keep SSH keys and GitHub credentials on the device where they are already configured; never copy laptop tokens or private keys to the Pi.
