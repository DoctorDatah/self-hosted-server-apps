## Clean wipe (delete everything Docker) + reinstall with Compose


⚠️ **This deletes ALL containers, images, volumes (data), networks, and Docker’s on-disk state.**


```bash
# 1) Stop services (ignore errors if not installed/running)
sudo systemctl stop docker containerd 2>/dev/null || true


# 2) Remove Docker packages (conflicting/unofficial packages included)
sudo apt-get remove -y $(dpkg --get-selections docker.io docker-compose docker-compose-v2 docker-doc podman-docker containerd runc 2>/dev/null | cut -f1) 2>/dev/null || true
sudo apt-get purge -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin docker.io docker-compose docker-compose-v2 2>/dev/null || true
sudo apt-get autoremove -y


# 3) Delete ALL Docker data on disk (this is the real "fresh start")
sudo rm -rf /var/lib/docker /var/lib/containerd


# 4) Install Docker Engine + Compose v2 plugin (Ubuntu repo method)
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin


# 5) Start + enable Docker
sudo systemctl enable --now docker


# 6) Verify
docker --version
docker compose version
docker ps
```


This gives you **Compose v2** (the modern command is `docker compose`, not `docker-compose`). ([Docker Documentation][2])


---


## How to “run docker” (start it) and test quickly


```bash
sudo systemctl start docker
docker run --rm hello-world
```


---


## Optional: run Docker without sudo


```bash
sudo usermod -aG docker $USER
newgrp docker
docker run --rm hello-world
```


---


### What “Docker Compose” means now


* ✅ **Use:** `docker compose up -d`
* 🚫 Old/deprecated: `docker-compose` (hyphen) (Compose v1 stopped receiving updates; v2 is the path forward). ([Docker Documentation][2])

