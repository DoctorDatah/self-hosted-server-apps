# Coolify Troubleshooting (HTTP 500)

Run these commands on the VM to diagnose a 500 error.

```bash
cd /home/malik/self-hosted-server-apps/VM - Manual App Deployment (Inside VM)/Coolify

sudo docker compose ps
sudo docker compose logs --tail=200 coolify
sudo docker compose logs --tail=200 postgres
sudo docker compose logs --tail=200 redis
sudo docker compose logs --tail=200 soketi
sudo curl -i http://127.0.0.1:8000/api/health

sudo ls -la /home/malik/self-hosted-server-apps/VM - Manual App Deployment (Inside VM)/Coolify/.env
sudo docker network ls | grep appnet
sudo curl -i http://127.0.0.1:8000/
```

If `docker compose logs` complains about service names, use:

```bash
sudo docker compose ps
```

Then re-run logs with the service names shown in the `SERVICE` column.
