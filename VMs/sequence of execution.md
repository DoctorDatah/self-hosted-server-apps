# Sequence of Execution (VM)

## 0) Repo clone / pull

### Get git PAT from either cellphone password or from infisical github folder 

```bash
sudo apt-get update && sudo apt-get install -y git
```
```bash
sudo -u malik git config --global credential.helper store
```
```bash
sudo -u malik git clone https://github.com/DoctorDatah/self-hosted-server-apps /home/malik/self-hosted-server-apps
```


## 1) Installation of libraries and packages (includes Infisical CLI)
```bash
sudo -E "/home/malik/self-hosted-server-apps/VMs/Installations/install_all.sh"
```
After install, log out (comand: exit ) and log back in as `malik` so the docker group change applies.

## 2) Infisical variables fetch (writes VMs/.env + app-specific .env files)
```bash
sudo -E "/home/malik/self-hosted-server-apps/VMs/Infisical Variables/fetch_infisical_env.sh"
```
### Note Get the Infisical Token from Infisical folder in homelab project

## 3) App deployment (like Coolify, etc)
```bash
sudo docker compose -f "/home/malik/self-hosted-server-apps/VMs/Coolify/docker-compose.yml" up -d
```

## 4) Cloudflare tunnel container
```bash
sudo -E "/home/malik/self-hosted-server-apps/VMs/Cloudflare Tunnel - via Docker/cloudflare_install_and_setup.sh"
```

## 5) Optional cleanup (dangerous)
```bash
sudo -E "/home/malik/self-hosted-server-apps/VMs/Cleanup/cleanup_vm.sh"
```

## Note
Infisical fetch writes `VMs/.env` and also overwrites app-specific `.env` files for Coolify and Cloudflare.
