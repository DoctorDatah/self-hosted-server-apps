# Coolify (Docker Compose)

Single-file compose for running Coolify on this host.

## Files
- `docker-compose.yml` – full Coolify stack (app + postgres + redis + soketi)

## Required env
Create `Apps/coolify/.env` with the Coolify app variables, including:
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

## Run
```bash
docker compose -f /Users/malikqayyum/self-hosted-server-apps/Apps/coolify/docker-compose.yml up -d
```

## Network
The compose creates a `coolify` network. Use this network in the Cloudflare tunnel setup if you want to proxy Coolify via cloudflared.
