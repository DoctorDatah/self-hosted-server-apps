# Cloudflare Tunnel (VM SSH Only)

Dedicated setup for SSH access to the VM via Cloudflare Tunnel (no app routing).

## Quick Steps (Do This)
- Clone the repo to the VM (first time only)
- Update `config.yml` with your SSH hostname (e.g., `ssh.yourdomain.com`)
- Run `sudo -E "/home/malik/self-hosted-server-apps/VM - N8N/Cloudflare for VM/cloudflare_env_setup.sh"` (writes `.env` from Infisical)
- Run `sudo -E "/home/malik/self-hosted-server-apps/VM - N8N/Cloudflare for VM/cloudflare_install_and_setup.sh"`
- The installer can create the Cloudflare Access SSH app + allow policy for the hostname

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
- Optionally creates a Cloudflare Access SSH app + allow policy (email-based)
- Reads pinned image/tag from `requirements.txt`
- Uses `config.yml` as-is (SSH-only)
- Runs cloudflared via Docker Compose using `network_mode: host`

## Notes
- `config.yml` is SSH-only: `service: ssh://localhost:22`.
- With `network_mode: host`, `localhost:22` points to the VM’s SSH service.
- The API token must include:
  - **Account → Cloudflare Tunnel → Edit**
  - **Zone → DNS → Edit**
  - **Account → Access: Apps → Edit**
  - **Account → Access: Policies → Edit**
  If you want least-privilege, scope the token to the specific account and zone.
