# Cloudflare Tunnel Setup (n8n VM + SSH)

Great — since the one-liner works, here is your **full updated guide** with the correct macOS path auto-injected using `$(which cloudflared)` so it works for you reliably.

---

## Fixed values

* **Tunnel name:** `n8n_vm_app_tunnel`
* **Domains:**

  * App → `n8napp.arshware.com` → `localhost:5678`
  * SSH → `ssh.arshware.com` → `localhost:22`
* **Local app port:** `5678`

---

## Server (VM) Setup

### 1) Install cloudflared (Ubuntu)

```bash
sudo apt update
sudo apt install -y cloudflared
```

### 2) Login to Cloudflare (normal user)

```bash
cloudflared tunnel login
```

Authorize in browser.

### 3) Create the tunnel

```bash
cloudflared tunnel create n8n_vm_app_tunnel
```

### 4) Route both domains

```bash
cloudflared tunnel route dns n8n_vm_app_tunnel n8napp.arshware.com
cloudflared tunnel route dns n8n_vm_app_tunnel ssh.arshware.com
```

### 5) Move credentials for root/systemd

```bash
sudo mkdir -p /etc/cloudflared
sudo cp ~/.cloudflared/*.json /etc/cloudflared/
sudo chmod 600 /etc/cloudflared/*.json
sudo chown root:root /etc/cloudflared/*.json
```

### 6) Create/Edit tunnel config

```bash
sudo nano /etc/cloudflared/config.yml
```

Paste this:

```yaml
tunnel: n8n_vm_app_tunnel
credentials-file: /etc/cloudflared/YOUR-UUID.json

ingress:
  - hostname: ssh.arshware.com
    service: tcp://localhost:22
  - hostname: n8napp.arshware.com
    service: http://localhost:5678
  - service: http_status:404
```

> ⚠ Replace `YOUR-UUID.json` with the actual filename inside `/etc/cloudflared/`

Save and exit.

### 7) Install & start system service

```bash
sudo cloudflared service install
sudo systemctl enable cloudflared
sudo systemctl restart cloudflared
sudo systemctl status cloudflared --no-pager
```

Must show `active (running)`.

### 8) Verify local n8n is alive

```bash
curl -I http://localhost:5678
```

---

## Mac Local SSH Setup

### 9) Add tunnel host to SSH config

```bash
nano ~/.ssh/config
```

Paste this block exactly (uses your installed path automatically):

```sshconfig
Host ssh.arshware.com
  User malik
  IdentityFile ~/.ssh/id_rsa
  ProxyCommand $(which cloudflared) access ssh --hostname %h
```

Save and exit.

### 10) Connect normally from Mac

```bash
ssh malik@ssh.arshware.com
```

If Cloudflare Access is enabled, it will ask for login + MFA, then open SSH.

---

## Optional Hardening on the VM (Recommended)

```bash
sudo ufw deny 22/tcp        # keep SSH hidden from public internet
sudo ufw allow 443/tcp      # allow Cloudflare return traffic
sudo ufw allow out 7844/tcp # cloudflared outbound tunnel port
sudo ufw enable
sudo ufw reload
```

---

## How it works

```
Internet → Cloudflare Edge (TLS) → Tunnel → VM Localhost
                                     ├─ n8n App (5678)
                                     └─ SSH (22)
```

No port-forwarding, no public SSH exposure, encrypted & optionally MFA protected.

---

## Troubleshooting

* Logs:

```bash
sudo journalctl -u cloudflared -n 200 --no-pager
```

* Restart n8n if needed:

```bash
sudo systemctl restart n8n
# or if Docker:
docker restart n8n
```

---
