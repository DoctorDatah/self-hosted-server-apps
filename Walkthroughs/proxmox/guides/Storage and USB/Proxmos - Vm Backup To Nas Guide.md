# Proxmos - VM Backup To NAS Guide

## Goal
Use your mounted NAS path (`/mnt/nas`) as Proxmox backup storage for VM/CT backups (`vzdump`).

## Prerequisites
- NAS mount is already working on Proxmox host (`/mnt/nas`).
- You can write to `/mnt/nas`.
- Proxmox web UI access.

Quick checks:
```bash
findmnt /mnt/nas
test -w /mnt/nas && echo "write ok"
```

## Step 1) Add NAS as backup storage in Proxmox UI
1. Open Proxmox UI.
2. Go to `Datacenter -> Storage -> Add -> Directory`.
3. Fill:
- `ID`: `WD-NAS-Backup`
- `Directory`: `/mnt/nas`
- `Content`: select `VZDump backup file` (optionally `ISO`, `Container template`)
- `Nodes`: choose your node
4. Click `Add`.

Why: this makes `/mnt/nas` an official backup target in Proxmox.

## Step 2) Create scheduled backup job
1. Go to `Datacenter -> Backup -> Add`.
2. Set:
- `Node`: your Proxmox node
- `Storage`: `WD-NAS-Backup`
- `Selection mode`: `All` or selected VM - Manual App Deployment (Inside VM)/CTs
- `Schedule`: example `02:00` daily
- `Mode`: `Snapshot` (recommended)
- `Compression`: `zstd` (recommended)
3. Configure retention (examples):
- keep-last: `7`
- keep-weekly: `4`
- keep-monthly: `3`
4. Save.

Why: scheduled backups ensure consistent protection without manual runs.

## Step 3) Run one manual backup now (smoke test)
Option A (UI):
1. Open a VM -> `Backup` tab -> `Backup now`.
2. Use storage `WD-NAS-Backup`.

Option B (CLI):
```bash
vzdump 100 --storage WD-NAS-Backup --mode snapshot --compress zstd
```
Replace `100` with your VMID.

## Step 4) Confirm backup files exist
```bash
ls -lh /mnt/nas/dump/
```
Expected filename pattern:
```text
vzdump-qemu-<vmid>-YYYY_MM_DD-... .zst
```

## Step 5) Test restore once (required)
1. In Proxmox UI, open `WD-NAS-Backup` storage.
2. Select one backup file.
3. Click `Restore`.
4. Restore to a test VMID.
5. Boot and verify OS/app starts.

Why: backups are only trustworthy after a successful restore test.

## Optional CLI examples
Backup multiple VMs:
```bash
vzdump 100 103 104 --storage WD-NAS-Backup --mode snapshot --compress zstd
```

Backup all guests on node:
```bash
vzdump --all 1 --storage WD-NAS-Backup --mode snapshot --compress zstd
```

## Monitoring and troubleshooting
Check last tasks:
```bash
pvesh get /nodes/$(hostname)/tasks --output-format json | head
```

Common checks:
```bash
findmnt /mnt/nas
systemctl status smbd --no-pager
journalctl -u pvedaemon -n 100 --no-pager
```

## Important limitation
If NAS disk is directly attached to the same Proxmox host, this is not full disaster protection.

Add one more copy off-host for real resilience:
- rsync to another machine/NAS
- Proxmox Backup Server on separate host
- cloud backup target
