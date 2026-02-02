# n8n (Coolify)

Repo-managed compose and env defaults for deploying n8n via Coolify.

## Files
- `docker-compose.yml` - main app definition
- `.env.example` - non-secret defaults to copy into `.env`

## Quick start
1) Copy `.env.example` to `.env` and edit as needed.
2) In Coolify, add secrets in the UI:
   - `N8N_ENCRYPTION_KEY` (required)
   - `SERVICE_PASSWORD_N8N` (if using runners)
3) Deploy with the repo in Coolify.

## Notes
- Persisted data lives in the `n8n-data` volume.
- Avoid defining the same env var in both `.env` and Coolify UI unless intentionally overriding.
