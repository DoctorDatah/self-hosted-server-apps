# Sequence of Execution (VM)

## 1) Repo clone / pull

### Get git PAT from either cellphone password or from infisical github folder 

```bash
sudo apt-get update && sudo apt-get install -y git
sudo -u malik git config --global credential.helper store
sudo -u malik git clone https://github.com/DoctorDatah/self-hosted-server-apps /home/malik/self-hosted-server-apps
```

## 2) Installation of libraries and packages (includes Infisical CLI)
```bash
sudo -E "/home/malik/self-hosted-server-apps/VM - CICD App Deployment/Installations/install_all.sh"
```

## 3) Coolify 

### Coolify env setup
```bash
sudo -E "/home/malik/self-hosted-server-apps/VM - CICD App Deployment/Coolify/coolify_env_setup.sh"
```
#### Note Get the Infisical Token from Infisical folder in homelab project
#### Ideal do not fetch all folders (select N ) and then specify the folder /coolify only

### Coolify deployment
```bash
sudo docker compose -f "/home/malik/self-hosted-server-apps/VM - CICD App Deployment/Coolify/docker-compose.yml" up -d
```
Note: If you change DB/Redis secrets after the first run, recreate volumes (`docker compose down -v`) or Coolify will fail auth.

## 4) Cloudflare

### Cloudflare env setup
```bash
sudo -E "/home/malik/self-hosted-server-apps/VM - CICD App Deployment/Cloudflare/cloudflare_env_setup.sh"
```
#### Note Get the Infisical Token from Infisical folder in homelab project
#### Ideal do not fetch all folders (select N ) and then specify the folder /cloudflare only


### Cloudflare tunnel container
```bash
sudo -E "/home/malik/self-hosted-server-apps/VM - CICD App Deployment/Cloudflare/cloudflare_install_and_setup.sh"
```

## 0) Optional cleanup (dangerous) (Do not do it when you have the funtional app - it wipes/deletes the databases)
```bash
sudo -E "/home/malik/self-hosted-server-apps/VM - CICD App Deployment/Cleanup/cleanup_vm.sh"
```