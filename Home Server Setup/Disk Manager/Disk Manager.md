# Disk Manager

A terminal-based disk management tool for Linux guests and libvirt hosts. It helps you inspect disks, mount/unmount filesystems, format partitions, resize filesystems, edit `/etc/fstab`, and (optionally) manage libvirt VM disks. It includes safety checks to block destructive actions on the root disk unless you explicitly override them.

## How to Run

1. Open a terminal.
2. Ensure the script is executable:

```bash
chmod +x "/root/self-hosted-server-apps/Home Server Setup/Disk Manager/Disk Manager.sh"
```

3. Run the script (as root):

```bash
"/root/self-hosted-server-apps/Home Server Setup/Disk Manager/Disk Manager.sh"

```

## What It Does

- Shows disk and filesystem status (`lsblk`, `df`, `blkid`, `/etc/fstab`).
- Mounts, unmounts, and remounts devices.
- Creates GPT partition tables and full-disk partitions.
- Formats partitions as `ext4` or `xfs`.
- Grows or shrinks `ext4` filesystems and grows `xfs` filesystems.
- Wipes filesystem signatures and removes partitions (destructive).
- Provides a built-in help/knowledge base for disk basics.
- If `virsh` and `qemu-img` are available, it can list VMs and attach/detach or resize qcow2 disks.

## Safety Notes

- Destructive operations require typed confirmation.
- Root disk operations are blocked by default unless you enable root override in **Settings**.
- `/etc/fstab` is backed up before edits.
- A dry-run mode is available in **Settings** to preview commands without executing them.

## Requirements

- Run as root (no `sudo` needed if you are already root).
- Core tools: `lsblk`, `findmnt`, `mount`, `umount`, `e2fsck`, `resize2fs`, `xfs_growfs`, `parted`, `blkid`, `wipefs`.
- Optional (for hypervisor menu): `virsh`, `qemu-img`.
