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

## 2) Coolify env setup
```bash
sudo -E "/home/malik/self-hosted-server-apps/VMs/Coolify/coolify_env_setup.sh"
```
### Note Get the Infisical Token from Infisical folder in homelab project

## 3) Coolify deployment
```bash
sudo docker compose -f "/home/malik/self-hosted-server-apps/VMs/Coolify/docker-compose.yml" up -d
```
Note: If you change DB/Redis secrets after the first run, recreate volumes (`docker compose down -v`) or Coolify will fail auth.

## 4) Cloudflare env setup
```bash
sudo -E "/home/malik/self-hosted-server-apps/VMs/Cloudflare/cloudflare_env_setup.sh"
```
### Note Get the Infisical Token from Infisical folder in homelab project

## 5) Cloudflare tunnel container
```bash
sudo -E "/home/malik/self-hosted-server-apps/VMs/Cloudflare/cloudflare_install_and_setup.sh"
```

## 6) Optional cleanup (dangerous)
```bash
sudo -E "/home/malik/self-hosted-server-apps/VMs/Cleanup/cleanup_vm.sh"
```

## Note
Coolify and Cloudflare each have their own Infisical env setup scripts now.
