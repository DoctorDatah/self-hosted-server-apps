# walkthroughs

Curated homelab walkthroughs and helper scripts grouped by topic.

## Layout
- `apps/` – service-specific notes (Mattermost, OpenWebUI).
- `docker/` – container cleanup/reinstall steps.
- `hardware/` – HP server resource configuration reference.
- `homelab/` – general homelab knowledge base.
- `proxmox/guides/` – Proxmox docs plus the VM guide HTML/screenshots (enterprise repos, storage, USB NAS, Wi-Fi).
- `proxmox/scripts/` – executable helpers with companion docs (`hp-plan-deployer`, `proxmox-usb-iso-wizard`, `usb-iso-downloader`, `coolify-deployer`).

## Using these files
Open the markdown in the folder you need, or run the shell scripts in `proxmox/scripts/` (they are already executable and include walkthroughs alongside them).

### Quick start: Coolify deployer
Run inside the `vm-coolify` guest as root:
```bash
sudo ./proxmox/scripts/coolify-deployer.sh
# Non-interactive example with seeded user:
COOLIFY_ROOT_USERNAME=admin COOLIFY_ROOT_EMAIL=you@example.com COOLIFY_ROOT_PASSWORD='secret' \
sudo ./proxmox/scripts/coolify-deployer.sh -y --pool-base 10.250.0.0/16 --pool-size 24 --autoupdate false
```
