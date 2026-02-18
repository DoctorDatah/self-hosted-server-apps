# Proxmox External HDD as NAS with Samba (Step-by-Step, with Why)

## Goal
Use an external HDD connected to your Proxmox host as network storage that other devices can access over SMB (and optionally NFS).

This guide is written for the exact scenario you have now:
- Disk: `/dev/sdc1`
- Filesystem: `ntfs`
- Label: `WareHouse`
- UUID: `F474B7AA74B76DCC`

## Before You Start

### Why this matters
Most storage mistakes happen from selecting the wrong disk or formatting a disk that still has data. We verify first, then choose a safe path.

### Requirements
- Shell access to Proxmox host as `root`
- External HDD connected to Proxmox
- A local Linux user for file ownership and SMB login (example: `malik`)
- Your LAN subnet (example: `192.168.1.0/24`)

### Safety backup
```bash
cp /etc/fstab /etc/fstab.bak.$(date +%F-%H%M%S)
```
Why: if an `fstab` line is wrong, this gives you a known-good rollback file.

## Step 1) Confirm the correct disk
```bash
lsblk -o NAME,SIZE,FSTYPE,LABEL,UUID,MOUNTPOINT,MODEL
fdisk -l /dev/sdc
blkid /dev/sdc1
```
Why: we confirm device name, filesystem type, and UUID.  
We will use `UUID` (stable) instead of `/dev/sdc1` (can change after reboot/replug).

Expected for your disk:
- TYPE: `ntfs`
- UUID: `F474B7AA74B76DCC`

## Step 2) Choose your storage path

### Path A (recommended now): Keep existing data
Use this if the drive already contains files you want to keep.
Implementation details and commands: see `Step 3) Path A - Keep existing data (NTFS, no wipe)`.

### Path B: Reformat to ext4
Use this only if you want a Linux-native filesystem and can erase the drive.
Implementation details and commands: see `Step 4) Path B - Reformat to ext4 (destructive)`.

After completing either Step 3 or Step 4, continue to Step 5.

## Step 3) Path A - Keep existing data (NTFS, no wipe)

### A.1 Install NTFS support
```bash
apt-get update
apt-get install -y ntfs-3g
```
Why: Proxmox/Debian needs NTFS userspace tools for reliable NTFS operations.

### A.2 Create mountpoint and mount now
```bash
mkdir -p /mnt/nas
mount -t ntfs3 /dev/sdc1 /mnt/nas
df -h | grep /mnt/nas
```
Why: test live mount first before making it persistent.

### A.3 Persist mount in `/etc/fstab`
Add this line:
```fstab
UUID=F474B7AA74B76DCC /mnt/nas ntfs3 defaults,nofail,uid=1000,gid=1000,umask=002 0 0
```
Why:
- `nofail`: host still boots even if drive is disconnected.
- `uid/gid`: files map to your Linux user/group.
- `umask=002`: group write access (good for shared NAS usage).

### A.4 Validate `fstab`
```bash
umount /mnt/nas
mount -a
df -h | grep /mnt/nas
touch /mnt/nas/.write_test && ls -l /mnt/nas/.write_test
```
Why: confirms auto-mount and write permissions are correct.

## Step 4) Path B - Reformat to ext4 (destructive)
Do this only if you want to erase the disk.

### B.1 Unmount and prepare disk
```bash
umount /dev/sdc1 2>/dev/null || true
```

### B.2 Repartition and format
```bash
parted /dev/sdc -- mklabel gpt
parted /dev/sdc -- mkpart primary ext4 0% 100%
mkfs.ext4 -L nas_data /dev/sdc1
```

### B.3 Mount and verify UUID
```bash
mkdir -p /mnt/nas
mount /dev/sdc1 /mnt/nas
blkid /dev/sdc1
```

### B.4 Persist mount in `/etc/fstab`
Then add:
```fstab
UUID=<new-uuid> /mnt/nas ext4 defaults,nofail 0 2
```
Quick config commands:
```bash
NEW_UUID=$(blkid -s UUID -o value /dev/sdc1)
cp /etc/fstab /etc/fstab.bak.$(date +%F-%H%M%S)
echo "UUID=${NEW_UUID} /mnt/nas ext4 defaults,nofail 0 2" >> /etc/fstab
tail -n 5 /etc/fstab
```
How to get and use `<new-uuid>`:
```bash
# Get the UUID value (example output: a1b2c3d4-...)
blkid /dev/sdc1
# or only the UUID value:
blkid -s UUID -o value /dev/sdc1
```

1. Copy the UUID from the command output.
2. Open `/etc/fstab`:
```bash
nano /etc/fstab
```
3. Replace `<new-uuid>` with your real UUID, save, and exit.
4. Quick sanity check:
```bash
tail -n 5 /etc/fstab
```
You should see a line like:
```fstab
UUID=a1b2c3d4-... /mnt/nas ext4 defaults,nofail 0 2
```

### B.5 Validate `fstab`
```bash
umount /mnt/nas
mount -a
df -h | grep /mnt/nas
touch /mnt/nas/.write_test && ls -l /mnt/nas/.write_test
```
Why ext4: better Linux permissions/ownership semantics than NTFS.

## Step 5) Configure SMB (Windows/macOS/Linux clients)

### What is Samba?
Samba is an open-source software suite that allows Linux and Unix systems to share files and printers using the SMB/CIFS protocol.

SMB (Server Message Block) is the same network file-sharing protocol used by Windows.

That is why Windows PCs can access shared folders from a Linux machine running Samba as if they were Windows shares.

In simple terms:

Samba makes a Linux machine behave like a Windows file server on your network.

### Why install Samba in this Proxmox + NAS setup?
You mounted your NAS at:
```text
/mnt/nas
```

That mount makes the storage:
- Available to the Proxmox host only
- Not automatically available to other devices on your LAN

Mounting = local access  
Samba = network sharing

### What Samba does here
When you install Samba and configure it to share `/mnt/nas`, it:
- Publishes `/mnt/nas` over the network
- Makes it accessible from Windows PCs
- Makes it accessible from macOS devices
- Makes it accessible from other Linux machines
- Can be accessed by smart TVs or media boxes that support SMB

After Samba is set up, devices can access it like:
```text
\\<proxmox-ip>\NAS
```

### Visual overview
Without Samba:
```text
NAS -> Proxmox -> (local only)
```

With Samba:
```text
NAS -> Proxmox -> Samba -> All LAN devices
```

### When you would not need Samba
You do not need Samba if:
- Only Proxmox VMs/containers need the storage locally
- You are using NFS instead for network sharing
- Clients access a separate NAS device directly

### Summary
| Component | Purpose |
| --- | --- |
| Mount `/mnt/nas` | Makes NAS storage local to Proxmox |
| Samba | Shares that storage to other devices on the LAN |
| SMB protocol | Enables Windows-style network sharing |

### 5.1 Install Samba
```bash
apt-get install -y samba
cp /etc/samba/smb.conf /etc/samba/smb.conf.bak.$(date +%F-%H%M%S)
```
Why: Samba exposes your mounted folder as a LAN share.

### 5.2 Add SMB share config
Edit `/etc/samba/smb.conf` and append:
```ini
[NAS]
   path = /mnt/nas
   browseable = yes
   read only = no
   guest ok = no
   valid users = malik
   create mask = 0664
   directory mask = 0775
```
Why:
- `guest ok = no`: requires authentication.
- `valid users`: only allowed account(s).
- `mask` values: sane default permissions for shared files/folders.

### 5.3 Create Samba password and restart
```bash
smbpasswd -a malik
systemctl enable --now smbd
```
Why: Linux account and Samba password DB are separate.

### 5.4 Access from clients
- Windows: `\\<proxmox-ip>\NAS`
- macOS/Linux: `smb://<proxmox-ip>/NAS`

## Step 6) Optional NFS share (best for Linux-only clients)

### 6.1 Install and export
```bash
apt-get install -y nfs-kernel-server
```
Add to `/etc/exports`:
```exports
/mnt/nas 192.168.1.0/24(rw,sync,no_subtree_check)
```
Apply:
```bash
exportfs -ra
systemctl enable --now nfs-kernel-server
```
Why: NFS is usually lighter/faster in Linux-to-Linux environments.

## Step 7) Optional: Register `/mnt/nas` in Proxmox UI storage list
1. Datacenter -> Storage -> Add -> Directory
2. Directory: `/mnt/nas`
3. Content: pick needed types (`ISO`, `Backup`, `Disk image`, etc.)
4. Node: your Proxmox node
5. Save

Why: makes the path visible and manageable in Proxmox UI.

## Step 8) Health checks and troubleshooting

### Quick checks
```bash
findmnt /mnt/nas
ls -la /mnt/nas
test -w /mnt/nas && echo "Writable OK"
systemctl status smbd --no-pager
systemctl status nfs-kernel-server --no-pager
```

### If mount fails on reboot
- Boot shell, run `mount -a`, read error.
- Fix `/etc/fstab` typo.
- Restore backup if needed:
```bash
cp /etc/fstab.bak.<timestamp> /etc/fstab
```

### If SMB login fails
- Confirm Linux user exists: `id malik`
- Reset Samba password: `smbpasswd -a malik`
- Check service logs: `journalctl -u smbd -n 100 --no-pager`

## Step 9) Architecture note
Running NAS directly on Proxmox host is common for homelabs and is simple.  
For stricter isolation, use a dedicated NAS VM/LXC or separate NAS appliance.
