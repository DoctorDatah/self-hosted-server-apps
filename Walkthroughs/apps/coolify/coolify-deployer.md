# Coolify deployer script

Wrapper around Coolify's official installer that you can run inside the `vm-coolify` guest.

## What it does
1. Fails fast without root or `curl`, warns if run on the Proxmox host, and surfaces low RAM/disk warnings (target: ≥2 GB RAM, ~20 GB free).
2. Lets you set Docker address pool, registry, auto-updates, and optionally pin a Coolify version before invoking the upstream installer.
3. Can preseed the initial Coolify root user via prompts or env vars (username, email, password) so you can log in immediately after install.
4. Downloads `https://cdn.coollabs.io/coolify/install.sh` to `/tmp` and runs it with the chosen environment; Coolify logs end up in `/data/coolify/source/installation-*.log`.

## Usage

```bash
sudo ./coolify-deployer.sh
sudo ./coolify-deployer.sh -y --autoupdate false --pool-base 10.250.0.0/16 --pool-size 24
COOLIFY_ROOT_USERNAME=admin COOLIFY_ROOT_EMAIL=you@example.com COOLIFY_ROOT_PASSWORD='secret' sudo ./coolify-deployer.sh -y
```

### Getting the script onto the VM (when you can't paste)
- From your laptop/desktop to the VM (replace `<vm-ip>`):  
  `scp proxmox/scripts/coolify-deployer.{sh,md} root@<vm-ip>:/root/`
- Then on the VM:  
  `chmod +x /root/coolify-deployer.sh && sudo /root/coolify-deployer.sh`
- Copy/paste with nano inside the VM:  
  1) Copy `proxmox/scripts/coolify-deployer.sh` on your machine (e.g., `cat proxmox/scripts/coolify-deployer.sh | pbcopy` on macOS).  
  2) `ssh root@<vm-ip>`  
  3) `nano /root/coolify-deployer.sh`, paste, `Ctrl+O` to save, `Enter`, `Ctrl+X` to exit.  
  4) `chmod +x /root/coolify-deployer.sh && sudo /root/coolify-deployer.sh`

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
- Remote deployments: add Coolify’s SSH key to target hosts (guide: `apps/coolify/ssh-remote-server.md`).
