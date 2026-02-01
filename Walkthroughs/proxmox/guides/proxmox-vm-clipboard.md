# 📋 Proxmox VM clipboard guide (Web UI console)

How to get copy/paste working in the Proxmox **browser console** for Ubuntu VMs (and most other Linux guests).

## TL;DR — choose the right console for your VM

| Console type | Works in TTY-only VM? | Desktop required? | Clipboard quality |
| --- | --- | --- | --- |
| Serial console (xterm.js) | ✅ Yes | ❌ No | ⭐ Best for terminals |
| SPICE (QXL) | ❌ No | ✅ Yes | ⭐ Best for GUIs |
| VNC | ⚠️ Only in GUI session | ✅ Yes | ✅ Works in GUI, not TTY |
| Chrome extension | ✅ Yes | ❌ No | ✅ Works everywhere |

**If your VM is headless (no GUI):** use the **Serial console** (recommended) or the **Chrome extension**.

**If your VM has a desktop (GNOME/KDE/XFCE/etc.):** use **SPICE** for the smoothest clipboard and mouse integration.

---

## Option A — Serial console (works for headless servers)
Gives you a real terminal in the browser (xterm.js). Copy/paste behaves like any normal terminal.

1) Add a serial port to the VM (Proxmox UI → VM → **Hardware** → **Add → Serial Port** → COM1).
2) Inside Ubuntu, enable a serial console and reboot:
   ```bash
   sudo sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT="/&# console=ttyS0,115200 /' /etc/default/grub
   echo "ttyS0" | sudo tee -a /etc/securetty
   sudo update-grub
   sudo reboot
   ```
3) Use **Serial Console** tab in Proxmox. Paste with **Ctrl+V** (or right-click → Paste) and copy by selecting text.

---

## Option B — SPICE console (best for desktop VMs)
Full clipboard sync and better mouse handling for GUI workloads.

On the Proxmox host (replace `VMID`):
```bash
qm set VMID -vga qxl
qm set VMID -agent enabled=1
```

Inside the Ubuntu VM (desktop session):
```bash
sudo apt update
sudo apt install -y spice-vdagent
sudo reboot
```

In the Web UI: open the VM → **Console** → select **SPICE**. Paste with **Ctrl+Shift+V**.

---

## Option C — VNC console (GUI required)
Clipboard works only inside a running GUI session—not on the TTY login screen.

On the Proxmox host:
```bash
qm set VMID -vga std,clipboard=vnc
```

Inside Ubuntu **desktop** session:
```bash
sudo apt update
sudo apt install -y spice-vdagent spice-webdavd
sudo reboot
```

Use **Ctrl+Shift+V** to paste into the VNC console after clicking inside it.

---

## Option D — Chrome/Chromium extension (works even in TTY)
If you cannot change the console type, install the community extension that injects clipboard text into the Proxmox console.

- Chrome Web Store: `https://chromewebstore.google.com/detail/proxmox-console-extension/mnkdipbaleabnmdhikbhnkennhldlmaf`
- Source: `https://github.com/Flowgem/Proxmox-Console-Extension`

No guest-side packages are required. Paste using the extension’s action button.

---

## Quick troubleshooting
- Make sure you are in the right console: serial for TTY-only, SPICE/VNC for desktop sessions.
- For VNC/SPICE, confirm `spice-vdagent` is installed **inside the guest** and running.
- Reboot after changing VGA/agent settings so the VM picks up the new hardware.
- If paste still fails in VNC/SPICE, try **Ctrl+Shift+V**, not plain Ctrl+V.
- For serial console, ensure `console=ttyS0,115200` is present in `/etc/default/grub` and re-run `sudo update-grub`.
