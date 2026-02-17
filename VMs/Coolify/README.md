# Coolify (Docker Compose)

Single-file compose for running Coolify on this VM.

## Files
- `docker-compose.yml` – full Coolify stack (app + postgres + redis + soketi)

## Required env
Create `VMs/.env` with the Coolify app variables, including:
- `COOLIFY_DB_USERNAME`
- `COOLIFY_DB_PASSWORD`
- `COOLIFY_DB_DATABASE` (optional, defaults to `coolify`)
- `COOLIFY_REDIS_PASSWORD`
- `COOLIFY_PUSHER_APP_ID`
- `COOLIFY_PUSHER_APP_KEY`
- `COOLIFY_PUSHER_APP_SECRET`

Optional overrides:
- `COOLIFY_APP_PORT` (defaults to `8000`)
- `COOLIFY_SOKETI_PORT` (defaults to `6001`)
- `COOLIFY_REGISTRY_URL`, `COOLIFY_LATEST_IMAGE`

## Run (on the VM)
```bash
sudo -E "/home/malik/self-hosted-server-apps/VMs/Coolify/coolify_env_setup.sh"
sudo docker compose -f "/home/malik/self-hosted-server-apps/VMs/Coolify/docker-compose.yml" up -d
```
Note: `coolify_env_setup.sh` writes `VMs/Coolify/.env` directly from Infisical.

## Network
This compose uses the shared `appnet` network (external). Ensure it exists first by running `VMs/Installations/install_all.sh`.
Run the Cloudflare tunnel setup after this so it can attach to `appnet`.
