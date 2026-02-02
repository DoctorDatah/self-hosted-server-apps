# Cloudflare Tunnel (VM)

Flat, self-contained setup to run Cloudflare Tunnel on a VM via Docker Compose.

## Files
- `docker-compose.yml` - cloudflared service
- `config.yml` - ingress config (no secrets)
- `requirements.txt` - pinned cloudflared image tag
- `install.sh` - start the tunnel
- `logs.sh` - follow logs
- `vm-requirements.txt` - pinned Docker packages for the VM
- `guides/repo-clone-guide.md` - clone/update the repo on the VM
- `guides/cloudflare-tunnel-creation-guide.md` - create the tunnel in Cloudflare
- `guides/cloudflare-install-guide.md` - install Docker (if needed) and start the tunnel

## Usage (on the VM)
```bash
export CLOUDFLARE_TUNNEL_TOKEN="your_token_here"
./install.sh
./logs.sh
```

## Notes
- Update `config.yml` with your hostname and service target.
- `CLOUDFLARE_TUNNEL_TOKEN` must be exported in the shell session.
