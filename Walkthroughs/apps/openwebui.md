## Open WebUI on Ubuntu Droplet (1GB RAM)

**Password Login - Admin Setup - API Keys - Swap Enabled - /var Install - No Reverse Proxy**

---

## 🔹 What this guide achieves

* Open WebUI runs **stably** on a **1GB RAM droplet**

* Uses **swap** to prevent crashes

* Installed cleanly under `/var/openwebui`

* **Password-protected login**

* **Admin account created correctly**

* **Public signup disabled**

* Ready for **API keys**

* Ready for **remote local models (Ollama)**

---

## ⚠️ Hardware reality (important)

Your droplet:

* 1 vCPU

* 1 GB RAM

This is:

* ✅ Enough for **Open WebUI**

* ❌ NOT enough for local LLMs

Local models must run on a **separate machine** (remote Ollama).

---

# PART 1 --- SYSTEM PREP (DO THIS FIRST)

## Step 1 --- Add swap (CRITICAL)

This prevents Open WebUI from crashing during startup.

```bash

fallocate -l 2G /swapfile

chmod 600 /swapfile

mkswap /swapfile

swapon /swapfile

echo '/swapfile none swap sw 0 0' >> /etc/fstab

```

Verify:

```bash

free -h

swapon --show

```

You should see ~2GB swap.

---

## Step 2 --- Install Docker + Compose (Ubuntu 24.04)

```bash

apt update

apt install -y docker.io docker-compose

systemctl enable --now docker

```

Verify:

```bash

docker --version

docker-compose --version

```

---

# PART 2 --- OPEN WEBUI INSTALL

## Step 3 --- Create app directory under `/var`

```bash

mkdir -p /var/openwebui

cd /var/openwebui

```

---

## Step 4 --- Create secret key

```bash

echo "WEBUI_SECRET_KEY=$(openssl rand -hex 32)" > .env

chmod 600 .env

```

⚠️ Do not delete this file later.

---

## Step 5 --- Create `docker-compose.yml` (FIRST BOOT MODE)

⚠️ **Signup must be ENABLED for first admin creation**

```bash

cat > docker-compose.yml <<'YAML'

services:

  open-webui:

    image: ghcr.io/open-webui/open-webui:main

    restart: always

    ports:

      - "8080:8080"

    environment:

      WEBUI_SECRET_KEY: ${WEBUI_SECRET_KEY}

      WEBUI_AUTH: "True"

      ENABLE_SIGNUP: "True"

    volumes:

      - openwebui_data:/app/backend/data

volumes:

  openwebui_data:

YAML

```

---

## Step 6 --- Start Open WebUI

```bash

docker-compose up -d

```

Wait **1--3 minutes** (first boot is slow).

Check:

```bash

docker-compose ps

curl -I http://127.0.0.1:8080

```

You should get `HTTP/1.1 200 OK` or a redirect.

---

# PART 3 --- CREATE ADMIN ACCOUNT (IMPORTANT)

## Step 7 --- Create the FIRST admin (browser)

Open:

```

http://YOUR_DROPLET_IP:8080

```

Fill:

* Name

* Email

* Password

Click:

**Create Admin Account**

✅ This account is now **ADMIN**

---

# PART 4 --- LOCK IT DOWN (SECURITY)

## Step 8 --- Disable public signup (REQUIRED)

Edit the file:

```bash

nano docker-compose.yml

```

Change:

```yaml

ENABLE_SIGNUP: "True"

```

to:

```yaml

ENABLE_SIGNUP: "False"

```

Save and exit:

* Ctrl + O

* Enter

* Ctrl + X

Restart:

```bash

docker-compose down

docker-compose up -d

```

---

## Step 9 --- Confirm login protection

Reload:

```

http://YOUR_DROPLET_IP:8080

```

✅ You should now see **login only**

❌ No signup allowed

---

# PART 5 --- ADD MODELS

## Step 10 --- Add API keys (cloud models)

In Open WebUI:

* Settings → Connections

* Add OpenAI / compatible providers

* Paste API keys

* Save

You can now chat using API models.

---

## Step 11 --- (Optional) Add LOCAL models via remote Ollama

Run Ollama on a **bigger machine** (8GB+ RAM).

Expose:

```

http://OLLAMA_HOST:11434

```

Edit compose:

```bash

nano /var/openwebui/docker-compose.yml

```

Add under `environment:`:

```yaml

OLLAMA_BASE_URL: http://OLLAMA_HOST:11434

```

Restart:

```bash

docker-compose down

docker-compose up -d

```

Now you can use:

* API models

* Local models

  in the same UI.

---

# PART 6 --- OPTIONAL SECURITY (RECOMMENDED)

## Step 12 --- Lock port 8080 to your IP

```bash

ufw allow from YOUR_IP to any port 8080 proto tcp

ufw deny 8080/tcp

ufw enable

ufw status verbose

```

Also check **DigitalOcean Firewall** if enabled.

---

# FINAL STATE CHECK

```bash

docker-compose ps

free -h

curl -I http://127.0.0.1:8080

```

You should see:

* Container **Up (healthy)**

* Swap active

* WebUI responding

---

## ✅ YOU ARE DONE

You now have:

* Stable Open WebUI

* Password-protected login

* Admin account

* Signup disabled

* API keys supported

* Local models supported (remote)

* Clean `/var` install

* Low-RAM safe configuration
