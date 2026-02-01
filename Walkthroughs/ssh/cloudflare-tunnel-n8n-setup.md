# Cloudflare tunnel auto-setup script (n8n + SSH)

This helper drives the full server-side setup from the guide: installs Cloudflare’s agent, creates the `n8n_vm_app_tunnel`, wires DNS routes for the app and SSH, writes `/etc/cloudflared/config.yml`, and installs/starts the systemd service.

Use it on the Ubuntu VM that hosts n8n (port 5678) and SSH (22). You will still sign in to Cloudflare in the browser when prompted.

## What it does
- Installs `cloudflared` via apt if missing.
- Runs `cloudflared tunnel login` (browser auth).
- Creates the tunnel if it does not already exist.
- Adds DNS routes for the app domain and SSH domain.
- Copies credentials into `/etc/cloudflared/`, sets permissions, and renders `config.yml`.
- Installs/enables/restarts the `cloudflared` systemd service.
- Probes `http://localhost:<port>` to confirm n8n responds locally.

## Inputs (prompted)
- Tunnel name (default: `n8n_vm_app_tunnel`)
- App domain (default: `n8napp.arshware.com`)
- SSH domain (default: `ssh.arshware.com`)
- Local app port (default: `5678`)

## Run it
```bash
chmod +x ssh/cloudflare-tunnel-n8n-setup.sh
./ssh/cloudflare-tunnel-n8n-setup.sh
```

Follow the prompts, approve the Cloudflare login in your browser, and watch the steps complete. If a tunnel or DNS route already exists, the script skips it gracefully and continues.

## After it finishes
- Verify `systemctl status cloudflared` shows **active (running)**.
- On your Mac, add the SSH config snippet printed at the end (it auto-fills the `cloudflared` path with `$(which cloudflared)`):

```sshconfig
Host ssh.arshware.com
  User malik
  IdentityFile ~/.ssh/id_rsa
  ProxyCommand $(which cloudflared) access ssh --hostname %h
```

Then connect with `ssh malik@ssh.arshware.com`.

## Troubleshooting
- Logs: `sudo journalctl -u cloudflared -n 200 --no-pager`
- Validate n8n: `curl -I http://localhost:5678`
- If DNS changes are slow, confirm the CNAMEs in the Cloudflare dashboard and wait for propagation.
