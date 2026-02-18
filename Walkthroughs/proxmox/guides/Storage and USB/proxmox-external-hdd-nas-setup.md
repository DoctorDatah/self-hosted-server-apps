# Proxmox External HDD NAS Setup Script Guide

## Script
- `Walkthroughs/proxmox/scripts/proxmox-external-hdd-nas-setup.sh`

## What this script configures
1. Mounts an external disk partition to a mountpoint.
2. Writes persistent mount config to `/etc/fstab` using UUID.
3. Optionally configures Samba share.
4. Optionally configures NFS export.
5. Validates mount and write access.

## Requirements
- Run on Proxmox host (not inside VM).
- Run as `root`.
- External disk connected.
- You know target partition (example: `/dev/sdc1`).

## Run
```bash
sudo bash Walkthroughs/proxmox/scripts/proxmox-external-hdd-nas-setup.sh
```

## Prompt-by-prompt usage

### 1) Continue?
- `y` to proceed.
- `n` to exit.

### 2) Enter target partition device
Example: `/dev/sdc1`

How to find it:
```bash
lsblk -o NAME,SIZE,FSTYPE,LABEL,UUID,MOUNTPOINT,MODEL
```

### 3) Enter mount point
Default: `/mnt/nas`

### 4) Enter A or B
- `A` = keep existing data (non-destructive path)
- `B` = reformat to ext4 (destructive path)

## Path A details (keep data)
- Installs `ntfs-3g`
- Mounts with `ntfs3`
- Writes `/etc/fstab` entry like:
```fstab
UUID=<uuid> /mnt/nas ntfs3 defaults,nofail,uid=1000,gid=1000,umask=002 0 0
```

Use this when disk has data you want to keep.

## Path B details (reformat)
- Confirms destructive action
- Asks parent disk (example `/dev/sdc`)
- Repartitions and formats ext4
- Writes `/etc/fstab` entry like:
```fstab
UUID=<uuid> /mnt/nas ext4 defaults,nofail 0 2
```

Use this when you want clean Linux-native ext4 and accept data loss.

## Samba section
Prompt: `Configure Samba share? [Y/n]`

If yes, prompts:
- Linux user allowed for Samba share (default: `root`)
- Samba share name (default: `WD-NAS`)

It writes share config to `/etc/samba/smb.conf`, enables `smbd`, and can set Samba password.

Client access format:
```text
\\<proxmox-ip>\WD-NAS
```

## NFS section
Prompt: `Configure NFS export too? [y/N]`

If yes:
- Script auto-detects host IPv4 subnet and uses that as default CIDR.
- If subnet cannot be detected, script fails fast with an error.
- Writes export entry to `/etc/exports` and enables `nfs-kernel-server`.

Example export:
```exports
/mnt/nas 192.168.88.0/24(rw,sync,no_subtree_check)
```

## What files are modified
- `/etc/fstab`
- `/etc/samba/smb.conf` (if Samba enabled)
- `/etc/exports` (if NFS enabled)

Script creates timestamped backups before edits.

## After script completes
Verify quickly:
```bash
findmnt /mnt/nas
test -w /mnt/nas && echo "write ok"
systemctl status smbd --no-pager
systemctl status nfs-server --no-pager
```

## Connect from macOS (SMB)
### Finder method
1. Open Finder.
2. Press `Cmd + K` (Go -> Connect to Server).
3. Enter:
```text
smb://192.168.88.13/WD-NAS
```
4. Click Connect.
5. Sign in with:
- Username: `root`
- Password: Samba password you set with `smbpasswd`

### Terminal method
```bash
mkdir -p ~/mnt/wd-nas
mount_smbfs //root@192.168.88.13/WD-NAS ~/mnt/wd-nas
```

### If macOS connection fails
Check on Proxmox host:
```bash
systemctl status smbd --no-pager
testparm -s
smbpasswd -a root
```

## Rerun behavior
- Safe to rerun for updates.
- Existing mount/export entries for same mountpoint are replaced.
- Path B will reformat again if selected.

## Recommended choices for your current setup
- Path: `B` (if you want ext4 and no old data)
- Samba: `y`
- Samba user: `root`
- Share name: `WD-NAS`
- NFS: `y` only if Linux clients need NFS; otherwise `n`


## Architecture note
Running NAS directly on Proxmox host is common for homelabs and is simple.  
For stricter isolation, use a dedicated NAS VM/LXC or separate NAS appliance.
