# Repo + UI Config in Coolify (Practical Guide)

How to mix repo-managed config with Coolify UI secrets safely, with clear override rules and reliable backups.

---

## 1) What belongs in Git vs the Coolify UI

Put in the repo (Git):
- Non-secret env vars (timezone, feature flags, performance toggles).
- App definition: `docker-compose.yml`, volumes, healthchecks, networks, ports.
- Safe defaults that work everywhere.

Put in the Coolify UI:
- Secrets (passwords, tokens, API keys, encryption keys).
- Environment-specific overrides (prod vs dev domains, SMTP creds, webhook URLs).

---

## 2) The only merge rule you need
Treat Coolify UI env vars as overrides for repo defaults.

So:
- repo = defaults
- UI = overrides + secrets

Avoid defining the same key in both places unless you are intentionally overriding.

---

## 3) Recommended repo layout
```
apps/
  n8n/
    docker-compose.yml
    .env.example
    README.md
```
- `.env.example` is committed (no secrets).
- Real `.env` is not committed (optional if you prefer UI for secrets).

---

## 4) Gold standard Compose pattern (repo)
```yaml
services:
  n8n:
    image: n8nio/n8n:2.1.5

    # Repo-managed defaults (bulk)
    env_file:
      - .env

    # Secrets expected from Coolify UI
    environment:
      - N8N_ENCRYPTION_KEY
      - SERVICE_PASSWORD_N8N

    volumes:
      - n8n-data:/home/node/.n8n

    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://127.0.0.1:5678/ >/dev/null 2>&1 || exit 1"]
      interval: 10s
      timeout: 10s
      retries: 10

volumes:
  n8n-data:
```

---

## 5) `.env` strategy (repo-managed bulk)

Example `.env.example`:
```env
# Non-secret defaults
GENERIC_TIMEZONE=UTC
TZ=UTC
N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=false
N8N_PROXY_HOPS=1

# Optional: URLs can be per-environment in UI instead
# N8N_EDITOR_BASE_URL=https://n8n.yourdomain.com
# WEBHOOK_URL=https://n8n.yourdomain.com
# N8N_HOST=n8n.yourdomain.com
# N8N_PROTOCOL=https
```

Where to store the real `.env`:
- Best for most setups: keep it out of Git, store secrets in Coolify UI.
- Private repo only: commit `.env` (not recommended).
- Advanced: encrypt with SOPS/age and decrypt on deploy.

---

## 6) Adding secrets in Coolify UI
In the app settings:
- Environment Variables section.
- Add secret keys there.

For n8n:
- Required: `N8N_ENCRYPTION_KEY`
- If using runners: `SERVICE_PASSWORD_N8N` or `N8N_RUNNERS_AUTH_TOKEN`
- If using DB: `DB_POSTGRESDB_PASSWORD` and related DB vars

---

## 7) URLs and domains (avoid mismatch)
For n8n, these must match your public URL:
- `N8N_EDITOR_BASE_URL`
- `WEBHOOK_URL`
- `N8N_HOST`
- `N8N_PROTOCOL`

Where to put them:
- Multiple environments: put URLs in the UI (per environment).
- Single environment: put URLs in `.env` or UI, but not both.

---

## 8) Verify the final env inside the container
In Coolify -> Terminal:
```bash
printenv | sort | grep -E 'N8N_|WEBHOOK_URL|TZ|GENERIC_TIMEZONE'
```

---

## 9) Backups and restores (what actually matters)
For n8n, persist:
- `/home/node/.n8n` (volume)

Backups should include:
- persistent volumes
- DB volumes (if DB runs on the same server)

Restore rule:
1) restore volumes
2) redeploy

---

## 10) Safe operating checklist

Deployment:
- [ ] Compose file in Git
- [ ] Persistent storage attached
- [ ] Secrets in UI (not in Git)
- [ ] Healthcheck works
- [ ] No unnecessary exposed ports

Backups:
- [ ] Backups enabled for all volumes
- [ ] Backups stored off the VM
- [ ] Retention set (7–30 days)
- [ ] Restore tested once

Changes:
- Non-secrets -> Git + redeploy
- Secrets -> UI + redeploy
- Never edit the same key in both

---

## 11) Common mistakes
- Duplicating `WEBHOOK_URL` in repo and UI (pick one location).
- Missing `N8N_ENCRYPTION_KEY` (breaks credential decryption on restore).
- No persistent volume (redeploy = data loss).
- Expecting backups to include container images (they do not).

---

## Recommended split (simple and safe)
Repo `.env`:
- timezone
- proxy hops
- permission flags

Coolify UI:
- `N8N_ENCRYPTION_KEY`
- passwords/tokens
- `WEBHOOK_URL` + base URL (if you have dev/prod)

If you share your env list (redact secrets), I can help place each var.
