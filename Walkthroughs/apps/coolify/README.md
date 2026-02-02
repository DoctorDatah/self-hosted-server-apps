# Coolify

Docs and pointers for running Coolify in this homelab.

## Deploy Coolify
- Script lives at `proxmox/scripts/coolify-deployer.sh` with its doc `proxmox/scripts/coolify-deployer.md`.
- Run inside the `vm-coolify` guest as root:
```bash
sudo ./proxmox/scripts/coolify-deployer.sh
```

## Add a remote server for deployments
- See `apps/coolify/proxmox-vm-to-coolify.md` for connecting a Proxmox VM to Coolify.
- General SSH key instructions: `apps/coolify/coolify <-> Vm ssh.md`.

## Post-install basics
- Health/logs: `/data/coolify/source/installation-*.log`, `docker logs coolify`.
- Access UI at `http://<vm-ip>:8000`, set domain/SSL, configure SMTP, and back up `/data/coolify/source/.env`.

## Reset forgotten password
- Run inside the Coolify host (where Docker runs):
```bash
sudo ./apps/coolify/coolify-reset-password.sh -e you@example.com -p 'NewPass123'
```
- The script auto-detects the Coolify container, runs the artisan reset/update command, and falls back to a tinker-based reset if needed.

## Keep a GitHub Actions runner alive
- Script and guide moved to `apps/github-runner/keep-runner-alive.sh` + `apps/github-runner/keep-runner-alive.md`.
- Run as root on the runner box (supports relative paths like `./actions-runner`):
```bash
sudo ./apps/github-runner/keep-runner-alive.sh ./actions-runner
```
