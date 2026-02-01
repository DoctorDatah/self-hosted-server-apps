# Mattermost on DigitalOcean (1 GB RAM) — Full Working Guide

This guide installs Mattermost Team Edition on a DigitalOcean Ubuntu droplet using Docker, optimized for 1 GB RAM, including swap.

It includes fixes for:
- Docker install issues
- Docker Compose availability
- PostgreSQL version mismatch
- Filestore permission errors
- Healthcheck failures
- “Connection refused” problems

---

## Server Assumptions

- DigitalOcean Droplet
- Ubuntu 20.04 / 22.04 / 24.04
- 1 GB RAM
- Logged in as root

---

## 1. Update System

```bash
apt update && apt -y upgrade
```

---

## 2. Install Docker (Simple & Reliable)

```bash
apt -y install docker.io
systemctl enable --now docker
docker --version
```

Test Docker:

```bash
docker run --rm hello-world
```

---

## 3. Install Docker Compose

```bash
curl -L https://github.com/docker/compose/releases/download/v2.27.0/docker-compose-linux-x86_64   -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
docker-compose --version
```

---

## 4. Add Swap (CRITICAL for 1 GB RAM)

```bash
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
free -h
```

---

## 5. Create Mattermost Directory

```bash
mkdir -p /opt/mattermost
cd /opt/mattermost
```

---

## 6. Create docker-compose.yml

```yaml
services:
  postgres:
    image: postgres:14
    restart: unless-stopped
    environment:
      POSTGRES_USER: mmuser
      POSTGRES_PASSWORD: STRONG_PASSWORD_HERE
      POSTGRES_DB: mattermost
    volumes:
      - ./volumes/db:/var/lib/postgresql/data

  mattermost:
    image: mattermost/mattermost-team-edition:latest
    restart: unless-stopped
    depends_on:
      - postgres
    environment:
      MM_SQLSETTINGS_DRIVERNAME: postgres
      MM_SQLSETTINGS_DATASOURCE: postgres://mmuser:STRONG_PASSWORD_HERE@postgres:5432/mattermost?sslmode=disable
    volumes:
      - ./volumes/app:/mattermost/data
    ports:
      - "8065:8065"
```

---

## 7. Fix Filestore Permissions

```bash
mkdir -p /opt/mattermost/volumes/app /opt/mattermost/volumes/db
chmod -R 755 /opt/mattermost/volumes
chown -R 2000:2000 /opt/mattermost/volumes/app
```

---

## 8. Start Mattermost

```bash
docker-compose up -d
docker-compose ps
```

---

## 9. Access Mattermost

Open in browser:

http://YOUR_DROPLET_IP:8065

---

## Useful Commands

Logs:
```bash
docker-compose logs -f
```

Restart:
```bash
docker-compose down
docker-compose up -d
```

Health:
```bash
docker inspect mattermost-mattermost-1 --format '{{.State.Health.Status}}'
```

---

## Done

Mattermost is now running on a 1 GB DigitalOcean droplet.
