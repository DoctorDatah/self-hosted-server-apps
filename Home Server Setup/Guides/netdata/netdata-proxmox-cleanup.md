# Netdata Proxmox Cleanup / Uninstall

Use this script to undo the Netdata + Proxmox setup deployed by `netdata-proxmox-monitor.sh`. It can delete API tokens, optionally remove the Proxmox user/role, drop the Netdata collector config, stop/purge Netdata, and remove the Nginx reverse-proxy site.

## What it removes (based on prompts)

- Proxmox tokens for the given user whose token IDs start with the provided base (default `netdata`).
- Optionally the Proxmox role (`Netdata-Monitor`) and user (`netdata@pam`).
- Netdata Proxmox collector config files: `/etc/netdata/go.d/proxmox.conf` and `/etc/netdata/netdata.conf.d/plugins.conf`.
- Stops/disables Netdata; optional `apt purge netdata`.
- Nginx site + Basic Auth file: `/etc/nginx/sites-available/netdata`, `/etc/nginx/sites-enabled/netdata`, `/etc/nginx/.htpasswd-netdata`; optional `apt purge nginx apache2-utils`.

## Usage

1. Copy to your Proxmox host and run as root:

   ```bash
   chmod +x "/root/self-hosted-server-apps/Home Server Setup/Guides/netdata/netdata-proxmox-cleanup.sh"
   "/root/self-hosted-server-apps/Home Server Setup/Guides/netdata/netdata-proxmox-cleanup.sh"
```

2. Follow the prompts:
   - User/role/token base to target (defaults match the deploy script).
   - Whether to delete tokens, role, and user.
   - Whether to remove Netdata config and stop/disable the service (default yes).
   - Whether to purge Netdata and/or Nginx packages (default no, to avoid breaking other uses).

3. Watch for `[WARN]` lines; you may need to manually fix remaining tokens/ACLs or Nginx config if reload fails.

## Notes

- Token deletion uses both `pveum user token del` and `pveum user token delete` to cover CLI variants.
- If `jq` is missing, token discovery falls back to parsing the tabular `pveum user token list` output.
- The script does not attempt to rewrite `/etc/netdata/netdata.conf`; if you manually bound Netdata to localhost elsewhere, adjust it yourself if needed.***
