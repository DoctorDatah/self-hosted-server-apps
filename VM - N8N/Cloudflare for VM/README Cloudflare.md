# Cloudflare Tunnel (VM SSH Only)

Dedicated setup for SSH access to the VM via Cloudflare Tunnel (no app routing).

## Quick Steps (Do This)
- Clone the repo to the VM (first time only)
- Update `config.yml` with your SSH hostname (e.g., `ssh.yourdomain.com`)
- Run `sudo -E "/home/malik/self-hosted-server-apps/VM - N8N/Cloudflare for VM/cloudflare_env_setup.sh"` (writes `.env` from Infisical)
- Run `sudo -E "/home/malik/self-hosted-server-apps/VM - N8N/Cloudflare for VM/cloudflare_install_and_setup.sh"`
- Create a Cloudflare Access SSH app for the hostname

## Files (Hierarchy)
```
.
├─ docker-compose.yml                  # cloudflared service (host network)
├─ config.yml                          # SSH-only ingress config
├─ requirements.txt                    # pinned cloudflared image tag
├─ cloudflare_env_setup.sh             # writes .env from Infisical
├─ cloudflare_install_and_setup.sh     # create/verify tunnel + DNS and start
└─ 1. Setup Guide
   ├─ 1. repo-clone-guide.md           # clone/update the repo on the VM
   ├─ 2. cloudflare-tunnel-creation-guide.md
   └─ 5. cloudflare-troubleshooting-guide.md
```

## Usage (on the VM)
```bash
sudo -E "/home/malik/self-hosted-server-apps/VM - N8N/Cloudflare for VM/cloudflare_env_setup.sh"
sudo -E "/home/malik/self-hosted-server-apps/VM - N8N/Cloudflare for VM/cloudflare_install_and_setup.sh"
```
The env setup script writes `.env` in this folder before starting.

## What cloudflare_install_and_setup.sh does
- Checks Docker + Compose (errors if missing)
- Prompts for Cloudflare API setup (tunnel + DNS)
- Reads pinned image/tag from `requirements.txt`
- Uses `config.yml` as-is (SSH-only)
- Runs cloudflared via Docker Compose using `network_mode: host`

## Notes
- `config.yml` is SSH-only: `service: ssh://localhost:22`.
- With `network_mode: host`, `localhost:22` points to the VM’s SSH service.
- Protect the hostname with Cloudflare Access (recommended).
