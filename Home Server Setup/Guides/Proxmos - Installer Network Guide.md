# Proxmox VE Installer — Network & IP Setup Guide

Use this when the installer UI doesn’t auto-fill an IP. You’ll confirm the NIC, test DHCP, optionally set a temporary static IP, and then enter the same details back in the installer UI before finishing the install.

---

## 1) Open a real installer terminal

From the installer screen press:

```
Ctrl + Alt + F2   (or F3/F4 if needed)
```

You’re in a real shell when the prompt responds to commands.

---

## 2) List all NICs

```bash
ls /sys/class/net
```

Look for:

* `lo` → ignore
* `wlo*` → Wi-Fi (ignore for management)
* `eno1` / `eth0` / `enp*s0` → likely your wired Ethernet NIC

---

## 3) Confirm the wired NIC link is UP

```bash
ip -c link | grep -i "up"
```

Healthy example:

```
eno1: <...> state UP
```

If it shows `DOWN`, bring it up:

```bash
ip link set eno1 up
```

---

## 4) Test DHCP manually

Confirm your router is handing out IPs:

```bash
udhcpc -i eno1
```

If successful, you’ll see a lease message with an IP.

---

## 5) (Optional) Assign a temporary static IP in the terminal

```bash
ip addr add 192.168.1.10/24 dev eno1
ip route add default via 192.168.1.1
echo "nameserver 192.168.1.1" > /etc/resolv.conf
```

Verify:

```bash
ip a | grep -i "inet "
ip route | grep default
```

---

## 6) Switch back to the installer UI

You can and should enter the same IP, gateway, DNS, and management interface in the UI.

Return to the UI:

```
Ctrl + Alt + F1
```

---

## 7) Fill out the network screen in the installer

Pick the wired interface you identified (e.g., `NIC0 (E10)` for Ethernet; ignore Wi-Fi).

Enter:

| Field | Value |
| --- | --- |
| **IP Address** | Your chosen free LAN IP |
| **Subnet Mask** | `255.255.255.0` (or `/24`) |
| **Gateway** | Your router LAN IP |
| **DNS** | Router IP is fine, or your preferred DNS |

---

## 8) Finish install and connect

After install and reboot, open the Proxmox UI:

```
https://<your_IP>:8006
```

Login:

```
User: root
Password: (your installer password)
```

---

## Key notes

* Link up doesn’t show an IP until it’s assigned.
* Static IP assignment is safe for the LAN.
* NIC names may differ between shell and UI—that’s normal.
* You can always return to the installer UI to enter or correct the network config before finishing the install.
