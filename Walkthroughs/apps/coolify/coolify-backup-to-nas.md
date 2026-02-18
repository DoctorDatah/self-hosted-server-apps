# Coolify Backup To NAS Guide

## Goal
Back up Coolify config and app data to your NAS mounted on `/mnt/nas`.

There are two safe approaches. You can use both.

## Recommended strategy (high level)
1. **VM-level backup** (full recovery) via Proxmox `vzdump` to NAS.
2. **App-level backup** (databases + volumes) for services deployed by Coolify.

Use both for best recovery options.

## Part A) VM-level backup (Recommended)
If Coolify runs inside a VM, the simplest and most reliable backup is Proxmox `vzdump` to NAS.

Follow:
- `Walkthroughs/proxmox/guides/Storage and USB/Proxmos - Vm Backup To Nas Guide.md`

This captures the entire Coolify VM (config + app data + volumes) in one file.

## Part B) App-level backup for Coolify deployments (n8n, Mattermost, etc.)
Coolify does not automatically back up application files or volumes. For each app you must back up:

1. **Database** (Postgres/MySQL/Mongo) via Coolify DB backups
2. **Volumes/files** via NAS sync (rsync/restic)

If your apps run on a **separate VM** (not the Coolify VM), run all app-level backups on that app VM instead. Coolify does not back up volumes on other VMs.

### Step B1) Pick the correct VM for app backups
- If the app runs on the **Coolify VM**, follow the steps below on that VM.
- If the app runs on a **separate app VM**, follow the same steps **on that app VM**.

### Step B2) Mount NAS inside the target app VM
Pick one method.

#### B1.A) NFS (best for Linux VM)
```bash
apt-get update
apt-get install -y nfs-common
mkdir -p /mnt/nas
mount -t nfs 192.168.88.13:/mnt/nas /mnt/nas
```
Persist in `/etc/fstab`:
```fstab
192.168.88.13:/mnt/nas /mnt/nas nfs defaults,nofail 0 0
```

#### B1.B) SMB (if you only exposed SMB)
```bash
apt-get update
apt-get install -y cifs-utils
mkdir -p /mnt/nas
```
Create credentials file:
```bash
cat > /root/.smbcreds <<'CREDS'
username=root
password=<your-smb-password>
CREDS
chmod 600 /root/.smbcreds
```
Mount:
```bash
mount -t cifs //192.168.88.13/WD-NAS /mnt/nas -o credentials=/root/.smbcreds,uid=0,gid=0,iocharset=utf8,file_mode=0660,dir_mode=0770
```
Persist in `/etc/fstab`:
```fstab
//192.168.88.13/WD-NAS /mnt/nas cifs credentials=/root/.smbcreds,uid=0,gid=0,iocharset=utf8,file_mode=0660,dir_mode=0770,nofail 0 0
```

### Step B3) Back up Coolify core data to NAS (only on the Coolify VM)
Coolify stores its state and data under `/data/coolify`. This includes Coolify configuration and core volumes.

Create backup folder on NAS:
```bash
mkdir -p /mnt/nas/backup/coolify
```

Run a sync:
```bash
rsync -aH --delete /data/coolify/ /mnt/nas/backup/coolify/
```

### Step B4) Schedule daily backups (cron)
```bash
crontab -e
```
Add:
```cron
0 2 * * * rsync -aH --delete /data/coolify/ /mnt/nas/backup/coolify/
```

### Step B5) App-specific backups (n8n, Mattermost examples)
#### Example: n8n
Typical n8n setup uses:
- Database: PostgreSQL (if configured)
- Volume: `/home/node/.n8n` (workflow/config)

Backups to perform:
1. If DB runs in Docker, run a `pg_dump` from the DB container and save to `/mnt/nas`.
2. Back up the n8n volume path to NAS (rsync).

#### Example: Mattermost
Typical Mattermost setup uses:
- Database: PostgreSQL
- Files/Uploads: Mattermost data directory (uploads, config)

Backups to perform:
1. If DB runs in Docker, run a `pg_dump` from the DB container and save to `/mnt/nas`.
2. Back up the Mattermost data volume/path to NAS (rsync).

### Step B6) How to find app volumes in Coolify
1. Open the application in Coolify UI.
2. Go to `Storage/Volumes` for that app.
3. Note the host path or volume name.

If you prefer CLI:
```bash
docker inspect <container_name> --format '{{json .Mounts}}' | jq .
```

### Step B6.1) Database dumps from Docker (examples)
PostgreSQL:
```bash
docker exec -t <pg_container> pg_dump -U <db_user> <db_name> > /mnt/nas/backup/db/<db_name>_$(date +%F).sql
```

MySQL/MariaDB:
```bash
docker exec -t <mysql_container> mysqldump -u <db_user> -p'<db_pass>' <db_name> > /mnt/nas/backup/db/<db_name>_$(date +%F).sql
```

MongoDB:
```bash
docker exec -t <mongo_container> mongodump --archive > /mnt/nas/backup/db/mongo_$(date +%F).archive
```

### Step B7) Recommended app backup pattern
- Database backups: daily
- Volume backups: daily (or more if files change often)

### Step B8) Restore order (apps)
1. Restore volumes/files
2. Restore database backup
3. Restart app

## Part C) Restore Coolify core (file-level)
1. Stop Coolify:
```bash
docker stop coolify
```
2. Restore files:
```bash
rsync -aH /mnt/nas/backup/coolify/ /data/coolify/
```
3. Start Coolify:
```bash
docker start coolify
```

## Notes
- File-level backups are great for quick restores.
- VM backups are still the safest full recovery option.
- Use both if you want fast restores plus full disaster recovery.
