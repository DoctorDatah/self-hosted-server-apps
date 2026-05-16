# Cloudflare Tunnel — SSH (No ENV)

Runs a Cloudflare SSH tunnel on a VM via Docker Compose.
No `.env` file, no Infisical — credentials are prompted once and kept in session memory only.

Works for any number of VMs. Same code, same folder — just enter a different SSH domain each time.

## Quick Steps

1. Clone the repo on the VM
2. Run the install script — prompts for 3 values only:
   - Cloudflare Account ID
   - Cloudflare API Token
   - SSH domain (e.g. `ssh.hermes-dev.arshware.com`)
3. Everything else (Zone ID, tunnel name, DNS record, image) is derived automatically

```bash
sudo -E bash cloudflare_install_and_setup.sh
```

## Files

```
.
├── cloudflare_install_and_setup.sh   # main setup script
├── config.yml                        # ingress template (__SSH_DOMAIN__ placeholder)
├── config.generated.yml              # written at runtime — gitignored, never committed
├── docker-compose.yml                # cloudflared service (host networking)
├── requirements.txt                  # pinned cloudflared image tag
├── 1. Setup Guide/
│   ├── 2. cloudflare-tunnel-creation-guide.md   # where to find Account ID + API Token
│   └── 5. cloudflare-troubleshooting-guide.md
└── 2. Post Setup Guides/
    └── 4. mac-ssh-config-guide.md               # how to connect from Mac after setup
```

## How it works

- `config.yml` contains `__SSH_DOMAIN__` as a placeholder — the script replaces it with your actual SSH domain and writes `config.generated.yml` at runtime
- Tunnel token and ID are fetched from the Cloudflare API and exported as shell variables — docker compose reads them directly, nothing hits disk
- `docker-compose.yml` uses `network_mode: host` so `localhost:22` reaches the VM's SSH port from inside the container

## What the script does

1. Prompts for Account ID, API Token, SSH domain
2. Looks up Zone ID automatically from the domain
3. Derives tunnel name from the domain
4. Creates or reuses the Cloudflare tunnel
5. Creates the DNS CNAME record
6. Generates `config.generated.yml` from the template
7. Starts cloudflared via docker compose

## Stop / restart

```bash
sudo -E bash cloudflare_install_and_setup.sh --down   # stop
sudo -E bash cloudflare_install_and_setup.sh           # start (re-prompts, re-fetches token)
sudo -E bash cloudflare_install_and_setup.sh --pull    # pull latest image then start
```

## Multiple VMs

Each VM gets its own tunnel and DNS record — named automatically from the SSH domain:

| VM | SSH domain entered | Tunnel name auto-generated |
|---|---|---|
| hermes-dev | `ssh.hermes-dev.arshware.com` | `ssh-hermes-dev-arshware-com-tunnel` |
| hermes-prod | `ssh.hermes-prod.arshware.com` | `ssh-hermes-prod-arshware-com-tunnel` |
