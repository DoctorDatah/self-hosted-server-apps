# Rename your Cloudflare Tunnel domains (n8n VM + SSH)

Use these steps to swap the tunnel’s hostnames to new domains. Replace the example `myapp.newdomain.com` / `myssh.newdomain.com` with your choices.

---

## 1) Update DNS routing (Cloudflare side)

List existing routes:

```bash
cloudflared tunnel route dns list n8n_vm_app_tunnel
```

Remove old domains:

```bash
cloudflared tunnel route dns delete n8n_vm_app_tunnel ssh.arshware.com
cloudflared tunnel route dns delete n8n_vm_app_tunnel n8napp.arshware.com
```

Add your new domains:

```bash
cloudflared tunnel route dns n8n_vm_app_tunnel myapp.newdomain.com
cloudflared tunnel route dns n8n_vm_app_tunnel myssh.newdomain.com
```

---

## 2) Update tunnel config on the VM

Edit the ingress hostnames:

```bash
sudo nano /etc/cloudflared/config.yml
```

Set the new hosts:

```yaml
ingress:
  - hostname: myssh.newdomain.com
    service: tcp://localhost:22
  - hostname: myapp.newdomain.com
    service: http://localhost:5678
  - service: http_status:404
```

Save and exit.

---

## 3) Restart the tunnel

```bash
sudo systemctl restart cloudflared
sudo systemctl status cloudflared --no-pager
```

---

## 4) Update SSH config on your Mac (if SSH domain changed)

```bash
nano ~/.ssh/config
```

Replace host entry:

```sshconfig
Host myssh.newdomain.com
  User malik
  ProxyCommand $(which cloudflared) access ssh --hostname %h
```

Then connect:

```bash
ssh malik@myssh.newdomain.com
```

---

## Summary

| What                 | Where                          |
| -------------------- | ------------------------------ |
| Domain mapping       | `cloudflared tunnel route dns` |
| Tunnel ingress rules | `/etc/cloudflared/config.yml`  |
| Local SSH access     | `~/.ssh/config` on Mac         |

If you paste your new domains, I can generate the exact commands for you (tunnel name already known).
