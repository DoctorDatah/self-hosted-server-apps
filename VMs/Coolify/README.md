# Coolify (Docker Compose)

Single-file compose for running Coolify on this VM.

## Files
- `docker-compose.yml` – full Coolify stack (app + postgres + redis + soketi)

## Required env
Create `VMs/Coolify/.env` with the Coolify app variables, including:
- `DB_USERNAME`
- `DB_PASSWORD`
- `DB_DATABASE` (optional, defaults to `coolify`)
- `REDIS_PASSWORD`
- `PUSHER_APP_ID`
- `PUSHER_APP_KEY`
- `PUSHER_APP_SECRET`

Optional overrides:
- `APP_PORT` (defaults to `8000`)
- `SOKETI_PORT` (defaults to `6001`)
- `REGISTRY_URL`, `LATEST_IMAGE`

## Run (on the VM)
```bash
sudo docker compose -f "/home/malik/self-hosted-server-apps/VMs/Coolify/docker-compose.yml" up -d
```

## Network
The compose creates a `coolify` network. Use this network in the Cloudflare tunnel setup if you want to proxy Coolify via cloudflared.
