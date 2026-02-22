# USB ISO Downloader Script

This script guides you through selecting a disk/partition, optionally wiping/formatting it, mounting it for ISO storage, and downloading an ISO directly into the Proxmox-recognized path.

## What it does

1. **Device selection** – Lists mountable disks/partitions (excluding loop) and prompts you to pick one.
2. **Optional wipe/format** – Offers an ext4 format step with explicit confirmation (`WIPE-<device>`).
3. **Mounting** – Mounts the chosen device to a user-specified path (default `/mnt/usb-iso`), then creates `<mount>/template/iso` (the path Proxmox scans for ISOs).
4. **ISO download** – Prompts for an ISO URL and downloads it via `wget -c` into `<mount>/template/iso`.
5. **Verification** – Shows the downloaded file and runs `pvesm list <storage-id>` so you can confirm visibility in Proxmox.

## Usage

```bash
sudo ./usb-iso-downloader.sh
```

Follow the prompts:
- Pick the target device number.
- Decide whether to wipe/format as ext4.
- Confirm or change the mount point.
- Provide the Proxmox storage ID (default `USB-ISO`) for the visibility check.
- Paste the ISO download URL (e.g., an Ubuntu LTS ISO).

After completion, refresh the storage in the Proxmox UI to see the ISO under the chosen storage ID. If your storage isn’t configured yet, point it to the mount path you used (e.g., `/mnt/usb-iso`) with content type `ISO` only.
