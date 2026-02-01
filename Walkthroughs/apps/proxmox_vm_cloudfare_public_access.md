# Cloudflare Tunnel Setup (n8n VM)

This guide publishes the n8n VM app through a Cloudflare Tunnel using fixed values.

## Fixed values
- Tunnel name: `n8n_vm_app_tunnel`
- Public domain: `n8napp.arshware.com`
- Local app port: `5678`

## Steps

1) Install cloudflared (Ubuntu)
```bash
sudo apt update
sudo apt install -y cloudflared
```

2) Login to Cloudflare (run as your normal user)
```bash
cloudflared tunnel login
```
Open the provided link and authorize your account.

3) Create the tunnel
```bash
cloudflared tunnel create n8n_vm_app_tunnel
```

4) Route the domain to the tunnel (creates DNS CNAME)
```bash
cloudflared tunnel route dns n8n_vm_app_tunnel n8napp.arshware.com
```

5) Move tunnel credentials so systemd (root) can read them
```bash
sudo mkdir -p /etc/cloudflared
sudo cp ~/.cloudflared/*.json /etc/cloudflared/
sudo chmod 600 /etc/cloudflared/*.json
sudo chown root:root /etc/cloudflared/*.json
```

6) Create or edit the tunnel config
```bash
sudo nano /etc/cloudflared/config.yml
```
Paste this (swap `YOUR-UUID.json` for the actual filename in `/etc/cloudflared/`):
```yaml
tunnel: n8n_vm_app_tunnel
credentials-file: /etc/cloudflared/YOUR-UUID.json

ingress:
  - hostname: n8napp.arshware.com
    service: http://localhost:5678
  - service: http_status:404
```

7) Install and start the tunnel as a service (auto-start on reboot)
```bash
sudo cloudflared service install
sudo systemctl enable cloudflared
sudo systemctl restart cloudflared
sudo systemctl status cloudflared --no-pager
```
Status should show `active (running)`.

8) Verify the n8n app is reachable locally
```bash
curl -I http://localhost:5678
```

9) Open the app publicly
```
https://n8napp.arshware.com
```

## How it works
```
GitHub Actions / Internet
        |
Cloudflare Edge (TLS, routing)
        |
cloudflared tunnel (running on your VM)
        |
n8n app on localhost:5678
```
No port-forwarding is required; Cloudflare handles TLS and routing.

## Troubleshooting
- View tunnel logs:
```bash
sudo journalctl -u cloudflared -n 200 --no-pager
```
- Restart n8n if needed:
```bash
sudo systemctl restart n8n  # if installed as a service
# or
docker restart n8n          # if running in Docker
```

## Optional hardening
```bash
sudo ufw allow 5678/tcp   # local app port
sudo ufw allow 443/tcp    # Cloudflare tunnel outbound return traffic
sudo ufw enable
```

If you want, I can also provide:
- A GitHub Actions workflow for deploying to this VM via SSH.
- A backup script for the tunnel config and credentials.
