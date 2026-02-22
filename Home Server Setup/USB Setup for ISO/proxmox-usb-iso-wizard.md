# Proxmox USB ISO Wizard

This wizard script prepares a USB drive (or any block device) to host ISO images for Proxmox. It can list devices, optionally wipe/format them, mount the target, make the mount persistent, build the Proxmox ISO directory structure, optionally fetch an Ubuntu ISO, and ensure a Proxmox storage entry is configured for ISO content.

## What the script does

1. **Environment validation** – Confirms it is running as root and that `lsblk`, `blkid`, `pvesm`, and `mkfs.ext4` are installed.
2. **Device discovery** – Lists partitions and whole disks that already contain a filesystem (skips loop devices). Displays size, transport, model/label, filesystem type, UUID/PARTUUID, and mountpoint for easy selection.
3. **Optional wipe/format** – Lets you reformat the selected device/partition as ext4 after a double-confirmation prompt. Whole-disk formatting requires an explicit `YES` confirmation.
4. **Mounting** – Mounts the selection to `/mnt/usb-iso` by default (customizable), with a prompt to unmount/remount if it is already mounted elsewhere.
5. **Persistence** – Optionally backs up `/etc/fstab`, removes existing entries for the chosen mountpoint, and writes a new line using `UUID` or `PARTUUID`, then reloads systemd and tests `mount -a`.
6. **ISO directory layout** – Creates `<mount>/template/iso` (Proxmox’s expected ISO folder) and can move any `*.iso` files from the mount root into that directory.
7. **Optional Ubuntu ISO download** – Downloads Ubuntu Server or Desktop 24.04.3 ISO directly into the ISO folder via `wget -c`.
8. **Proxmox storage alignment** – Sets an existing storage ID (default `USB-ISO`) to ISO-only content via `pvesm set`, or guides you to create it in `/etc/pve/storage.cfg` or the UI. Shows `pvesm list` output for verification.

## Usage

1. Copy the script to your Proxmox host (or keep it in-place if already there).
2. Run as root:

   ```bash
   sudo ./proxmox-usb-iso-wizard.sh
   ```

3. Follow the prompts:
   - Choose the device/partition number from the presented table.
   - Decide whether to wipe/format as ext4 (dangerous—erases all data).
   - Confirm or customize the mount point.
   - Choose whether to persist the mount in `/etc/fstab` (recommended).
   - Optionally move existing ISOs into `<mount>/template/iso`.
   - Optionally download an Ubuntu ISO into the same folder.
   - Confirm or override the Proxmox storage ID to align with the mounted path.

## Safety notes

- **Data loss warning:** The wipe/format step permanently erases the target device. The script requires explicit confirmation (`WIPE-<device>` and `YES` for whole-disk) before formatting proceeds.
- **Run on Proxmox:** The script expects `pvesm` and `/etc/pve/storage.cfg` and should be executed directly on a Proxmox host.
- **Backups:** It automatically backs up `/etc/fstab` before writing any persistent mount entry (`/etc/fstab.bak.<timestamp>`).

## Typical use cases

- **Prepare a USB stick for ISO storage** – Format and mount a USB drive, make the mount persistent, and build the `/template/iso` folder so Proxmox can use it immediately.
- **Consolidate existing ISO files** – Move loose ISO files from the mount root into the Proxmox ISO directory structure and expose them via `pvesm list`.
- **Offline-friendly ISO staging** – Download Ubuntu Server or Desktop ISO straight into the correct path, ready for VM installs without additional transfers.
- **Repoint a storage ID to a new device** – Align an existing `dir` storage entry (default `USB-ISO`) to ISO-only content after swapping the underlying USB or directory.

## Tips

- After completion, refresh the storage in the Proxmox UI: **Datacenter → Storage → <storage ID> → Content → Refresh**.
- When creating a VM, the ISO picker looks in `<mount>/template/iso` for available images.
- If persistence fails (e.g., missing UUID), you can still mount manually or re-run the script after fixing the filesystem.
