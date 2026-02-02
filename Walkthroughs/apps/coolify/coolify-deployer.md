# Coolify deployer script

Wrapper around Coolify's official installer that you can run inside the `vm-coolify` guest.

## What it does
1. Fails fast without root or `curl`, warns if run on the Proxmox host, and surfaces low RAM/disk warnings (target: ≥2 GB RAM, ~20 GB free).
2. Lets you set Docker address pool, registry, auto-updates, and optionally pin a Coolify version before invoking the upstream installer.
3. Can preseed the initial Coolify root user via prompts or env vars (username, email, password) so you can log in immediately after install.
4. Downloads `https://cdn.coollabs.io/coolify/install.sh` to `/tmp` and runs it with the chosen environment; Coolify logs end up in `/data/coolify/source/installation-*.log`.


## Getting the script onto the VM (when you can't paste)
On the VM:
1) `nano /root/coolify-deployer.sh`, paste, `Ctrl+O` to save, `Enter`, `Ctrl+X` to exit.  
2) `chmod +x /root/coolify-deployer.sh`  
3) Run it:

```bash
sudo /root/coolify-deployer.sh

# OR with flags
sudo /root/coolify-deployer.sh -y --autoupdate false --pool-base 10.250.0.0/16 --pool-size 24

# OR preseed the root user via env vars
COOLIFY_ROOT_USERNAME=malik \
COOLIFY_ROOT_EMAIL=malikhqtech@gmail.com \
COOLIFY_ROOT_PASSWORD='mypass' \
sudo /root/coolify-deployer.sh -y
```
## Options and env
- `--version <v>` pin Coolify version (default: latest from CDN).
- `--registry <url>` registry for images (default `ghcr.io`).
- `--pool-base <cidr>` and `--pool-size <n>` Docker address pool (defaults: `10.0.0.0/8`, `24`).
- `--force-pool-override` rewrite Docker pool even if already configured.
- `--autoupdate <true|false>` toggle Coolify auto-updates (default `true`).
- `-y` skip the confirmation prompt.
- Env: `COOLIFY_ROOT_USERNAME`, `COOLIFY_ROOT_EMAIL`, `COOLIFY_ROOT_PASSWORD` to seed the first user; `COOLIFY_VERSION`, `COOLIFY_REGISTRY`, `COOLIFY_POOL_BASE`, `COOLIFY_POOL_SIZE`, `COOLIFY_AUTOUPDATE`, `COOLIFY_FORCE_POOL_OVERRIDE` mirror the flags.

> Note: Root password seeding is passed via environment to the upstream installer; avoid reusing secrets from other systems.

## After install
- Health check: `docker ps | grep coolify`, `docker inspect --format '{{.State.Health.Status}}' coolify`, `docker logs coolify --tail 50`.
- Logs: latest installer log is in `/data/coolify/source/installation-*.log`; upgrade logs `/data/coolify/source/upgrade-*.log`.
- Login: browse to `http://<vm-ip>:8000` (or your domain). Use the seeded root user if provided; otherwise create the first admin in the UI.
- Domains/SSL: point DNS to the VM, set the domain in Coolify settings, request a cert (ports 80/443 must reach the VM).
- Email: add SMTP in Settings and send a test.
- Backups: copy `/data/coolify/source/.env` somewhere safe and include `/data/coolify` in VM backups/snapshots.
- Remote deployments: add Coolify’s SSH key to target hosts (guide: `Walkthroughs/apps/coolify/coolify <-> Vm ssh.md`).

## If the URL doesn’t open
From the Coolify VM:
```bash
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | rg -i 'coolify|traefik'
ss -lntp | rg -E ':8000|:80|:443'
curl -I http://127.0.0.1:8000
```

From your laptop (replace `VM_IP`):
```bash
curl -I http://VM_IP:8000
```

Common fixes:
- Wrong IP/port: Coolify UI is `http://<vm-ip>:8000` by default. If you set a domain/SSL, use `https://<domain>`.
- VM firewall: allow inbound TCP `8000`, `80`, `443` in the VM and any Proxmox firewall rules.
- Containers not healthy: check `docker logs coolify --tail 200` and the latest installer log in `/data/coolify/source/installation-*.log`.
