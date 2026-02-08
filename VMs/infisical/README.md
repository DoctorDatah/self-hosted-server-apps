# Infisical (VM)

Use Infisical CLI on the VM to fetch Cloudflare secrets into:
`VMs/Cloudflare Tunnel - via Docker/.infisical.cloudflare.env`

## Install CLI
```bash
sudo -E "/home/malik/self-hosted-server-apps/VMs/infisical/install_and_authenticate.sh"
```

## One-time setup
1) Add your Infisical token:
```bash
echo 'INFISICAL_TOKEN=your_token_here' | sudo tee /etc/infisical.env
```

2) Add your Infisical Project ID:
```bash
echo 'your_project_id_here' | sudo tee /etc/infisical.project
```

## Fetch Cloudflare env
```bash
sudo -E "/home/malik/self-hosted-server-apps/VMs/Cloudflare Tunnel - via Docker/fetch_cloudflare_env.sh"
```
