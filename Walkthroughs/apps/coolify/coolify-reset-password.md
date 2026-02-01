# Coolify Password Reset Helper

Script: `apps/coolify/coolify-reset-password.sh`

Resets a Coolify user’s password by executing inside the Coolify container. It auto-detects the container, locates the Laravel app directory, tries the official artisan reset/update commands, and falls back to a tinker-based update.

## Prerequisites
- Run on the host where Coolify’s Docker container is running (Ubuntu OK).
- Docker daemon running and you have permission (use `sudo` if needed).

## Usage
```bash
# interactive (prompts for password)
sudo ./apps/coolify/coolify-reset-password.sh -e you@example.com

# non-interactive
sudo COOLIFY_EMAIL=you@example.com COOLIFY_PASSWORD='NewPass123' ./apps/coolify/coolify-reset-password.sh -y
```
Options:
- `-e, --email` (required unless `COOLIFY_EMAIL` set)
- `-p, --password` (or `COOLIFY_PASSWORD`; otherwise prompts)
- `-c, --container` override container name (auto-detects `coolify` or similar)
- `-y, --yes` skip confirmation

## What it does
1) Validates Docker access and ensures the container is running.  
2) Finds the Coolify app directory (looks for `artisan`).  
3) Tries `php artisan user:reset-password ...`, then `user:update ...`; if both fail, runs a tinker snippet to bcrypt and save the new password.  
4) Exits with `[OK]` on success or an error on failure.

## Troubleshooting
- If you see `There are no commands defined in the "user" namespace.`, your Coolify build lacks the `user:*` artisan commands. The script will still reset the password via the tinker fallback; the warnings are harmless.
- If it says “Could not auto-detect Coolify container,” pass `-c <container-name>`.
- If Docker isn’t running or you lack permission, start Docker or use `sudo`.
- On failures, check `docker logs <container>` for Laravel errors.
