# Codex skills for Raspberry Pi deployment

This project has two deployment workflows:

- **Laptop to Pi:** [`skills/pi-github-sync`](../../skills/pi-github-sync/SKILL.md) is the `pi-github-sync` skill installed at `~/.codex/skills/pi-github-sync/SKILL.md`. It reviews and commits requested laptop changes, pushes to GitHub, then fast-forward pulls and rebuilds on the selected Pi.
- **Develop on the Pi:** [`skills/pi-direct-deploy`](../../skills/pi-direct-deploy/SKILL.md) is for Codex running in the Raspberry Pi checkout. It edits there, pushes the requested commit from the Pi, then rebuilds, restarts the existing app service, and checks the health endpoint.

Use the second workflow when the files are being edited directly on the Pi. Use the first when the source changes are made on the laptop. Both workflows preserve unrelated changes, avoid force pushes, and keep credentials out of Git. Read the [web app deployment guide](web_app.md) for the service units, installer, and health check.
