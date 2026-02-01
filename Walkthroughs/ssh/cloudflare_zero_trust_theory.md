# Theoretical Robust & Private Access Model

This note captures the theory behind using Cloudflare Tunnel and Access to keep a VM reachable without exposing it to the internet.

## Constraints and questions
- Internal IP rotates and breaks SSH.
- App remains reachable through Cloudflare Tunnel.
- SSH currently depends on the fragile internal IP.
- Concern: tunneling SSH might expose the VM to the internet.
- Belief: an internal IP feels safer because an attacker must already be inside the network.
- Requests: understand the science, how most people solve this, and how to achieve a private, robust, hack-resistant setup.

## Why the app stays up while SSH breaks
- **Host reachability vs. service routing:** SSH relies on the changing internal IP; the app is served through Cloudflare Tunnel to `localhost`.
- **Process binding:** running services can stay bound to all interfaces or `localhost` even after IP rotation.
- **Caching:** DNS, ARP, and routing caches can preserve reachability temporarily.
- **Tunnel path:** the tunnel forwards traffic to `localhost`, not to the rotating internal IP.

Result: the tunnel keeps the app reachable; SSH tied to the internal IP fails.

## What Cloudflare Tunnel does (and does not) do
- The VM initiates an **outbound encrypted connection** from `cloudflared` to Cloudflare.
- Users connect: **User → Cloudflare → encrypted tunnel → cloudflared → localhost service on the VM**.
- Cloudflare acts as a public gateway and identity enforcer; it does **not** open inbound ports on the VM.
- Security implications:
  - Port scans cannot see the VM.
  - Port 22 is unreachable unless explicitly tunneled.
  - Brute force is blocked when Access enforces identity/MFA before SSH is proxied.
  - Attacks hit Cloudflare’s edge, not the VM.
  - Internal IP rotation becomes irrelevant once SSH is tunneled.

## Security model: internal IP vs. tunnel + Access
### Internal IP only
- Hidden but fragile (IP rotation).
- No identity enforcement or MFA.
- Limited auditing.
- Compromise anywhere on the internal network enables lateral movement to SSH.

### Tunnel + Cloudflare Access
- VM remains hidden; no open inbound ports.
- Identity-based access with MFA and audit trail.
- No brute-force surface on the VM.
- Internal IP can rotate without impact.

Conclusion: the identity-gated tunnel provides stronger security than relying on IP secrecy alone.

## Robustness principles for rotating-IP environments
1. Use DNS or a gateway as the stable identity.
2. Terminate reachability at a proxy/load balancer/tunnel.
3. Enforce authentication at the gateway.
4. Run services on `localhost` or all interfaces; avoid IP coupling.
5. Refresh stale routing state with health checks or restarts as needed.
6. Never depend on internal IPs for human or automation access.
7. Use outbound-only encrypted tunnels.
8. Prefer gateways that support MFA and auditing.
9. Avoid direct host exposure whenever possible.

## What most people do (common patterns)
- Cloudflare Zero Trust SSH over Tunnel.
- Identity-aware gateways (e.g., Teleport, Vault SSH CA).
- Service mesh sidecars (Envoy/Istio) for identity and routing.
- Ephemeral SSH certificates instead of static keys.
- Bastions only when tunnels or Zero Trust are unavailable.
- Port 22 is never opened to the internet; outbound connectivity is preferred.
- IPs are treated as disposable; identity and gateway policies define access.

## Takeaway
- Cloudflare is public; the VM is not.
- The tunnel is a private bridge; only Cloudflare can enter.
- Cloudflare Access enforces authentication before relaying SSH.
- Internal IP rotation stops mattering once SSH is tunneled.
- The attack surface moves to the identity-aware gateway, improving security.
