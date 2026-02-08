# Infisical Secret References (n8n app)

## Notes
- This file contains **references only** (no secret values).
- Secrets are stored in Infisical under the path `/n8n`.

## Required Secrets
| Key | Purpose |
| --- | --- |
| CLOUDFLARE_CLIENT_ID | Cloudflare Access service token client ID for CI tunnel access. |
| CLOUDFLARE_CLIENT_SECRET | Cloudflare Access service token client secret for CI tunnel access. |
| CLOUDFLARE_TUNNEL_TOKEN | Tunnel token used by cloudflared on the VM. |
| N8N_ENCRYPTION_KEY | n8n encryption key for credentials. |
| POSTGRES_DB | Postgres database name. |
| POSTGRES_USER | Postgres user for n8n. |
| POSTGRES_PASSWORD | Postgres password for n8n. |
| N8N_HOST | Public hostname for n8n (used in URLs). |
| N8N_PROTOCOL | http or https (match Cloudflare ingress). |
| N8N_PORT | External port for n8n UI (usually 5678). |
| WEBHOOK_URL | Public webhook base URL for n8n. |
| N8N_EDITOR_BASE_URL | Public editor base URL for n8n. |
