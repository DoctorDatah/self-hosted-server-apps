# Not Properly working at the moment
# Netdata Proxmox Monitor Setup

This script installs Netdata on a Proxmox host, locks the Netdata UI to localhost, creates a Proxmox API token for the built-in Proxmox collector, wires up Nginx with Basic Auth, and verifies connectivity end to end.

## What the script does

1. Installs prerequisites: `curl`, `ca-certificates`, `nginx`, `apache2-utils`, `jq`, plus Netdata via the official kickstart.
2. Binds the Netdata web server to `127.0.0.1` and force-enables the `go.d` plugin.
3. Creates (or reuses) a Proxmox user/role/ACL (defaults: `netdata@pam` with role `Netdata-Monitor` having `Sys.Audit VM.Audit`).
4. Creates a fresh Proxmox API token, captures the secret from the JSON output (handles both `secret` and `value` keys), and validates it against `/api2/json/version`.
5. Writes `/etc/netdata/go.d/proxmox.conf` using the token, restarts Netdata, and tails recent Netdata logs for collector hints.
6. Configures an Nginx reverse proxy at a configurable path (default `/netdata`) with HTTP Basic Auth.

## Usage

1. Copy `netdata-proxmox-monitor.sh` to your Proxmox host (or run in place) and make it executable:

   ```bash
   chmod +x "/root/self-hosted-server-apps/Home Server Setup/Guides/netdata/netdata-proxmox-monitor.sh"
   "/root/self-hosted-server-apps/Home Server Setup/Guides/netdata/netdata-proxmox-monitor.sh"
```

2. Follow the prompts:
   - Proxmox monitoring user (default `netdata@pam`) and role name.
   - Token base name (script appends a timestamp for uniqueness).
   - Netdata path behind Nginx (default `/netdata`).
   - Netdata dashboard username/password for Basic Auth.

3. When it finishes, visit `http://<PROXMOX_IP>/<path>/` (e.g., `http://10.0.0.2/netdata/`) and log in with the credentials you set.

## Notes and tips

- Run as root; the script exits otherwise.
- The Netdata UI is bound to localhost; access is only via the Nginx reverse proxy with Basic Auth.
- Token parsing now accepts either `secret` or `value` in Proxmox JSON output to avoid “secret missing” errors.
- For inside-VM visibility (processes, filesystems, services), install Netdata inside each VM separately using the Netdata kickstart command shown at the end of the script.
- Logs: if charts do not appear, re-run the script tail output or check `journalctl -u netdata -n 120`.
