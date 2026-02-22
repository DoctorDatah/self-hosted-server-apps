# 🚀 Proxmox Homelab Setup Guide

---

## 💽 Part 1 — Installing Proxmox

1. Download Proxmox ISO
2. Download **Rufus**
3. Insert USB into your PC
4. In Rufus:

   * Select the USB device
   * Select the Proxmox ISO
   * Click **Start** → wait until finished
5. Insert USB into the target server/PC
6. Boot menu using **F2 / F8 / F12**
7. Select USB
8. Choose **PVE Graphical Install**
9. Agree to terms
10. Select install disk → choose **XFS**
11. Set:

* Country, timezone, keyboard
* Root password + email
* Hostname + static IP

12. Install → reboot

---

## 🌐 Part 2 — Accessing Web UI

* Open browser → go to `https://<Proxmox-IP>:8006`
* Click **Advanced → Proceed**
* Login as:

  * User: `root`
  * Password: the one you created

---

## 📦 Part 3 — Fix Subscription Pop-up (Optional)

*(Only if you want to hide the warning permanently — it will return after updates if not patched again)*

```bash
cp /usr/share/javascript/proxmox-widget-toolkit/proxmoxlib.js /usr/share/javascript/proxmox-widget-toolkit/lib-bk.js
nano /usr/share/javascript/proxmox-widget-toolkit/proxmoxlib.js
```

* Find subscription alert function → comment it out
* Save and exit
* Restart proxy:

```bash
systemctl restart pveproxy
```

---

## 🔄 Part 4 — Enable Free Updates

1. Go to **Datacenter → Updates → Repositories**
2. Disable:

   * Enterprise repo
   * Ceph enterprise repo
3. Add:

   * `No-Subscription`
   * `Ceph No-Subscription`
4. Go to **Updates → Refresh → Upgrade → Reboot**

---

## 🗄 Part 5 — Adding Storage (USB or HDD)

### Understand the drives:

| Drive          | Meaning                                          |
| -------------- | ------------------------------------------------ |
| `/dev/nvme0n1` | Main SSD — Proxmox system is installed here      |
| `/dev/sdb`     | 8GB USB you plugged in (partition = `/dev/sdb1`) |

---

### 📁 What does **mount** mean?

> Mounting = making a drive appear as a folder so Proxmox/Linux can use the files.

---

### 🔌 Mount your 8GB USB for ISO storage (without wiping)

```bash
mkdir -p /mnt/usb-iso
mount /dev/sdb1 /mnt/usb-iso
```

---

### 🔁 Auto-mount on reboot

```bash
nano /etc/fstab
```

Add this line:

```
/dev/sdb1  /mnt/usb-iso  vfat  defaults,nofail  0  2
```

Save and exit.

---

### 📂 Part 6 — Why your ISO wasn’t showing?

> Because Proxmox only scans for ISO files inside:

```
/mnt/usb-iso/template/iso/
```

But your ISO was here instead:

```
/mnt/usb-iso/*.iso  ❌ (wrong)
```

So you moved it correctly using:

```bash
mkdir -p /mnt/usb-iso/template/iso
mv /mnt/usb-iso/*.iso /mnt/usb-iso/template/iso/
```

---

### ✔ Verify ISO is visible to Proxmox

```bash
pvesm list USB-ISO
ls -lh /mnt/usb-iso/template/iso/
```

---

## 🧪 Part 7 — Creating a VM from your ISO

1. Open Proxmox UI
2. Go **Create VM**
3. OS → select storage **USB-ISO**
4. Choose:

   * CPU: 2 cores
   * RAM: 2–4GB
   * Disk: 20–40GB
5. Start VM → open **Console** → install Ubuntu normally

---

## 🏠 Part 8 — What is NAS Storage and do you need it now?

| NAS                    | Purpose                                                            |
| ---------------------- | ------------------------------------------------------------------ |
| Network storage device | Stores ISOs, backups, VM disks, containers safely over the network |

**You don’t need it to install Proxmox**, but you can add it later for:

* ISO libraries
* Backups
* Restores
* Templates

---

## 🧱 How to get a NAS (future plan)

### 2 paths:

1. **Reuse a spare PC** → install:

   * TrueNAS
   * OpenMediaVault
   * Unraid (paid but easy)
2. **Buy a NAS box**:

   * Synology (DS223 / DS224+ / DS423+)
   * QNAP (TS-233 / TS-262)
   * TerraMaster (F2-223 / F4-223)

---

## 🔗 Part 9 — How Proxmox connects to NAS

| Protocol | Best for you                       |
| -------- | ---------------------------------- |
| SMB/CIFS | works with Windows & Proxmox       |
| NFS      | fastest and best for Linux/VM labs |

---

### Add NAS to Proxmox (when ready)

1. **Datacenter → Storage → Add → SMB/CIFS or NFS**
2. Enter NAS IP + credentials + shared folder
3. Enable content type you want (ISO, backup, etc)
4. Click **Add**

---

# 🎯 Final takeaway

✔ You can use USB or HDD now without wiping
✔ Your ISO wasn’t showing because it was in the wrong folder
✔ Mounting = connecting a drive to a folder
✔ NAS = network storage you can build later using spare hardware or a NAS box

---

If you want, next I can generate this into a:

📄 **PDF**,
🧾 **short checklist**,
or
📊 **network diagram**

Just tell me which one! 💪
