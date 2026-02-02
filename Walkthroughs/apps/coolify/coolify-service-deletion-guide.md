# Coolify Service Deletion Guide

What gets deleted, what stays, and how to fully clean your server after deleting a service in Coolify.

---

## 1) What "Delete Service" does in Coolify
When you delete a service from the Coolify dashboard, Coolify will:
- Stop the Docker container(s).
- Remove the Docker container(s) from the server.
- Remove the Docker network created for the service.
- Remove the Docker Compose stack (if used).

Result: the application is no longer running and containers are gone from the server.

---

## 2) What Coolify does NOT delete (important)
To protect your data, Coolify intentionally keeps persistent storage.

These are NOT deleted:
- Docker volumes
- Host bind-mounted folders
- Database data
- Docker images (usually)

Implications:
- Database data still exists.
- Disk space may not be fully freed.
- Re-deploying may reuse old data.

---

## 3) Common examples

### Example: app + database
If you deleted a service that included:
- a web app container
- a PostgreSQL / MySQL container

Then:
- containers are deleted
- database data still exists in a Docker volume

### Example: app with bind mount
If your app used:
```yaml
volumes:
  - /data/myapp:/app/data
```
Then:
- `/data/myapp` still exists on the server
- files are untouched

---

## 4) How to check what is left on the server

List remaining Docker volumes:
```bash
docker volume ls
```

Inspect a volume:
```bash
docker volume inspect <volume_name>
```

---

## 5) How to manually delete leftover data (safe)

Remove a specific Docker volume:
```bash
docker volume rm <volume_name>
```
Tip: Coolify volume names often include the service name.

Remove unused volumes only:
```bash
docker volume prune
```
This removes only volumes not used by any container.

---

## 6) Full cleanup (advanced, dangerous)
WARNING: This deletes everything unused by Docker.
```bash
docker system prune -a
```
This removes:
- stopped containers
- unused images
- unused networks
- unused volumes

Use only if you understand the impact.

---

## 7) Best-practice recommendations
- Always confirm whether a service uses volumes or bind mounts.
- Never blindly prune on a production server.
- Backup database volumes before deleting.
- For databases, delete volumes only when you are sure.

---

## 8) TL;DR

| Component  | Deleted by Coolify |
| ---------- | ------------------ |
| Containers | Yes                |
| Networks   | Yes                |
| Volumes    | No                 |
| Host files | No                 |
| Images     | Usually no         |

---

If you want, I can add:
- a database-specific cleanup guide
- steps to map volume names to services
- a safe disk-space cleanup checklist
