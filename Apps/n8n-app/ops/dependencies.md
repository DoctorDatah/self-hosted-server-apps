# Dependency Pins (n8n app)

## Summary
- Single source of truth for pinned versions used by Compose and CI.
- Update values here first, then re-deploy.

## Pin Table
| Key | Value | Notes |
| --- | --- | --- |
| CLOUDFLARE_IMAGE | cloudflare/cloudflared | Container image name. |
| CLOUDFLARE_IMAGE_TAG | TBD | Pin to a specific cloudflared image tag. |
| CLOUDFLARE_CLIENT_VERSION | TBD | Pin to a specific cloudflared client version for CI. |
| N8N_IMAGE | n8nio/n8n | Container image name. |
| N8N_IMAGE_TAG | TBD | Pin to a specific n8n image tag. |
| POSTGRES_IMAGE | postgres | Container image name. |
| POSTGRES_IMAGE_TAG | TBD | Pin to a specific Postgres image tag. |
| INFISICAL_CLI_VERSION | TBD | Pin to a specific Infisical CLI version. |
