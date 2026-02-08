# Coolify: UI Works but Terminal WebSocket Fails (Cloudflare)

## Symptom
You can open Coolify at `https://coolify.arshware.com`, but the Terminal shows
**"Terminal websocket connection lost"** or keeps reconnecting.

## Why this happens
Cloudflare can proxy normal HTTPS to your domain, so the UI loads.
But the Terminal and realtime features use **WebSockets** (`/terminal/ws` and `/app/*`).
Those WebSockets require **end-to-end TLS** and **valid proxy routes**.

If your server can’t get a valid certificate (or the proxy routes were never generated),
WebSockets fail even though the UI loads.

Common root cause in home/lab setups:
- Port 80 is not reachable from the internet, so Let’s Encrypt HTTP-01 fails.

## Option A (Recommended if you can open ports): Port Forwarding

### 1) Router/NAT rules
Log into your router and add these port forward rules:
- TCP 80  -> 192.168.88.7:80
- TCP 443 -> 192.168.88.7:443

If you have a different LAN IP for the VM, use that instead.

### 2) Verify the VM is listening
On the VM:
```bash
sudo ss -lntp | grep ':80\|:443'
```
You should see listeners on 0.0.0.0:80 and 0.0.0.0:443 (docker-proxy).

### 3) Verify from outside your network
From a device NOT on your LAN (phone on mobile data):
```bash
curl -I http://coolify.arshware.com/.well-known/acme-challenge/test
```
Expected: **404** (from your server). If you can’t connect, port 80 is still blocked.

### 4) Let’s Encrypt + Proxy reload
After port forwarding works:
1) In Coolify UI, set the domain for the instance/server to `coolify.arshware.com`
2) Enable HTTPS / Let’s Encrypt
3) Reload/Apply Proxy

Then verify proxy config exists:
```bash
sudo ls -la /data/coolify/proxy/dynamic
```
You should see new `.yaml` files (not just the default 503).

## Option B: DNS-01 (Keep Cloudflare orange cloud)
If your ISP blocks port 80 or you don’t want to open ports:
- Use DNS-01 challenge with a Cloudflare API token
- Let’s Encrypt validates via DNS, not HTTP

High-level steps:
1) Create a Cloudflare API token with **Zone DNS Edit** permissions
2) Configure Traefik/Coolify to use DNS challenge
3) Reload proxy

## Option C: Cloudflare Tunnel (No open ports)
- Run `cloudflared` and expose Coolify via the tunnel
- Cloudflare handles TLS

## Troubleshooting checks
- DNS record resolves to your public IP
- Cloudflare proxy is **grey (DNS only)** during HTTP-01 issuance
- Port 80 reachable from outside
- `/data/coolify/proxy/dynamic` contains non-default routes
