# ISO Downloader and Manager

This script manages ISO files for Proxmox. It can download ISOs to local storage or a mounted disk, organize them by OS/version, and optionally delete existing ISOs.

## What it does

1. **Local vs disk storage** – Prompts whether to use Proxmox local ISO storage (`/var/lib/vz/template/iso`) or a disk/partition.
2. **Device selection (if not local)** – Lists mountable disks/partitions and prompts you to pick one.
3. **Optional wipe/format (if not local)** – Offers ext4 format with explicit confirmation (`WIPE-<device>`).
4. **Mounting (if not local)** – Mounts the device to a path (default `/mnt/usb-iso`) and creates `<mount>/template/iso`.
5. **ISO management** – Optional delete of an existing ISO.
6. **Foldering by OS/version** – Prompts for OS family (Ubuntu/Debian/Other) and version to store under `<iso-root>/<os>/<version>/`.
7. **ISO download** – Prompts for an ISO URL and downloads it to the chosen folder.
8. **Verification** – Shows the downloaded file and runs `pvesm list <storage-id>` to confirm visibility.

## Usage

```bash
chmod +x "/root/self-hosted-server-apps/Home Server Setup/ISO Downloader and Manager/iso-downloader-manager.sh"
"/root/self-hosted-server-apps/Home Server Setup/ISO Downloader and Manager/iso-downloader-manager.sh"
```

Follow the prompts:
- Choose local storage or a disk/partition.
- If using a disk: pick the device, choose whether to wipe/format, and confirm the mount point.
- Optionally delete an existing ISO.
- Choose OS family (Ubuntu or Debian) and enter a version.
- Provide the Proxmox storage ID (default `local` for local storage or `USB-ISO` for a disk).
- Pick an ISO URL from the list (from `iso-url.txt`) or paste a custom URL.

After completion, refresh the storage in the Proxmox UI to see the ISO under the chosen storage ID. If your storage isn’t configured yet, point it to the mount path you used (e.g., `/mnt/usb-iso`) with content type `ISO` only.

## ISO URL list

Edit `iso-url.txt` to add or remove ISO download links. Lines starting with `#` are ignored.
