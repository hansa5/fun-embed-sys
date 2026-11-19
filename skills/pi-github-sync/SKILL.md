---
name: pi-github-sync
description: Commit and push requested local repository changes, then fast-forward pull them on a selected Raspberry Pi over SSH. For the Fun Embed app, rebuild, restart the service, and verify it responds. Use for a laptop-to-GitHub-to-Pi sync; do not use for ordinary code edits.
---

# Sync a repository to a Raspberry Pi

Use this workflow only when the user asks to commit/push changes and update a Pi. A request to create or edit this skill alone does not authorize a repository push or remote Pi changes.

## Laptop: inspect, commit, and push

1. Locate the requested repository and confirm its root, current branch, and `origin` remote. Inspect `git status --short --branch`, the tracked diff, and relevant untracked filenames before staging anything. Preserve existing edits; do not reset, clean, or overwrite them.
2. Stage the changes the user asked to publish. If the user says “all changes,” include all intended source/documentation changes, including tracked deletions, but exclude credentials, keys, token files, `.env` files, build output, and other secret or unrelated material. Inspect suspicious untracked files by name only first; do not print their contents. In particular, exclude files named `git_token` or similar unless the user has established they are safe to publish. Tell the user which files were excluded.
3. Review the staged file list and diff for accidental secrets or unrelated changes. Run `git diff --cached --check`. If the staged content is ambiguous, contains secrets, or has changes outside the user's requested scope, stop and ask what to include. Never expose secret values in tool output.
4. Create a concise commit message describing the staged changes. Push the current branch to `origin` without force. If the push is rejected or the remote branch has new commits, stop and reconcile safely; never force-push to resolve it.
5. Report the commit hash and push result before proceeding to the Pi.

For HTTPS authentication, use an existing OS credential store when configured. If a PAT must be used, read it from the local secure store into a short-lived environment variable for the local push only, with a temporary askpass helper if Git needs it. Do not put the token in command arguments, logs, shell startup files, Git remotes, or persistent credential files. Never forward or copy the PAT to a Pi.

## Choose and update the Pi

Known devices in this project:

- **Saman** — `Hansa.local`, for trading and stock learning.
- **Plex** — `media-server.local`, for a media server on the local network.

Use the exact Pi named by the user. If they ask to update both, handle them separately. Discover SSH usernames, aliases, and checkout paths from the user's SSH config and project documentation. Do not guess a username or repository path; ask if it cannot be determined. Use the hostname as written, for example `ssh USER@Hansa.local`.

For Saman, the deployed Fun Embed checkout is `/mnt/saman-ssd/git_repo/fun-embed-sys`. Confirm `/mnt/saman-ssd` is mounted from the SSD before pulling or running `./install.sh`; stop if the mount is missing so a deploy cannot silently land on the SD card. The user service's `ExecStartPre` should enforce an ext4 mount at that mountpoint. The SQLite database defaults to `data/wheel.sqlite3` inside that checkout. The old `~/Documents/git_repo/fun-embed-sys` directory is a rollback copy, not the active deployment.

For the one-time initial move from the SD checkout, follow `docs/rpi/storage.md` and `migrate-to-ssd.sh`. Do not pull the new app revision into the legacy checkout before migration. If partition formatting or `/etc/fstab` changes need interactive sudo, do not ask for the user's password; transfer the helper to the existing checkout and have the user run it from a Pi terminal.

Before pulling, connect over SSH and confirm the Pi is reachable, the checkout is the intended repository, the Pi is on the same branch that was pushed, and its `origin` is the expected remote. Inspect its status. If the checkout is dirty, the branch differs, the remote differs, or the Pi is ahead/diverged, do not pull or overwrite anything; report the condition and ask how to proceed.

The Pi must authenticate to GitHub independently. For a private repository, prefer a unique repository-scoped read-only deploy key on that Pi; never send the laptop's PAT to the Pi. If no read access is configured, stop and explain that the Pi needs GitHub read access before pulling. For public repositories, use anonymous HTTPS if suitable. If the request also asks to install or run this project's apps, follow `docs/rpi/environment_setup.md` and `docs/rpi/web_app.md` for package setup and the system-level service. Only install the service or dependencies when the user explicitly requests deployment; do not copy local tokens to the Pi.

When the checkout is clean and aligned, update it with a fast-forward-only pull:

```sh
git pull --ff-only origin BRANCH
```

Verify the Pi's resulting commit matches the pushed commit. If SSH or the pull fails, leave the Pi untouched beyond read-only inspection and report that the GitHub push succeeded but the Pi update did not.

## Rebuild and restart Fun Embed Project

When the user requested that the Fun Embed app be updated or rerun on Saman's Pi, follow `docs/rpi/web_app.md` after the successful pull:

1. Run `./install.sh` from the repository root to synchronize locked dependencies and rebuild `frontend/dist/`.
2. Run `sudo bash install-market-monitor.sh` from the SSD repository root to install or refresh the scheduled 15-minute wheel monitor and daily market radar timer. Verify `systemctl --user is-active fun-embed-market-monitor.timer` and `systemctl --user list-timers fun-embed-market-monitor.timer`.
3. Inspect the current service manager before restarting. Prefer the installed system unit `fun-embed-app.service` (`sudo systemctl restart` and `sudo systemctl status`). This app may also use the legacy user unit `fun-embed-docs.service`; if that is the active unit instead, restart and inspect it with `systemctl --user`.
4. Confirm the app responds with `curl -fsS http://127.0.0.1:8501/api/health` and verify the checkout commit still matches the pushed commit.
5. If neither unit exists, do not create or enable a service unless the user explicitly requested service installation. If they asked only to rerun an existing app, report that no managed service is installed and ask how they want it run.

If the install, restart, or health check fails, inspect the relevant output and service logs without resetting the checkout or changing service configuration. Report what succeeded and where the deployment stopped.

## Boundaries

- Do not change SSH configuration, install software, reboot a Pi, or expose SSH to the internet as part of a normal sync. Only set up the docs app dependencies/service when the user explicitly requests that deployment.
- Never put a password, private key, access token, or credential file in a commit or in command output.
- Do not silently skip a safety check or replace a fast-forward pull with a reset, force-push, or destructive checkout.
