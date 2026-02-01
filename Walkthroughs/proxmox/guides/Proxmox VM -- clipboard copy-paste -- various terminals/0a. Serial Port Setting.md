
## ✅ The correct Proxmox settings (this _is_ COM1)

### **Add the serial port like this:**

**Proxmox UI → VM → Hardware → Add → Serial Port**

Set:

- **Device**: `Serial Port`
    
- **Serial Port**: `0`
    
- **Use as console**: ✅ **YES**
    
- **Mode**: `Socket` (default, don’t change)
    

👉 **Serial Port `0` = `ttyS0` = COM1**

That’s the mapping:

`Serial Port 0  →  ttyS0  →  COM1 Serial Port 1  →  ttyS1  →  COM2`

![https://forum.proxmox.com/data/attachments/52/52831-d3baca142118b1a30ab1ece54ff5ae5c.jpg?hash=07rKFCEYsa](https://forum.proxmox.com/data/attachments/52/52831-d3baca142118b1a30ab1ece54ff5ae5c.jpg?hash=07rKFCEYsa)

![https://krisnet.de/dev/random/img/serial-port-webui.png](https://krisnet.de/dev/random/img/serial-port-webui.png)

---

## ⚠️ Common mistake (very important)

If you:

- add **Serial Port 0**
    
- but **do NOT check “Use as console”**
    

👉 the **Serial Console tab will be blank** even if Ubuntu is configured correctly.

---

## ✅ After adding the serial port

Now continue **inside Ubuntu** (via SSH / Termius):

`sudo sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT="/&console=ttyS0,115200 /' /etc/default/grub echo "ttyS0" | sudo tee -a /etc/securetty sudo update-grub sudo reboot`

---

## ✅ After reboot

- Go to **VM → Console → Serial Console**
    
- You should see:
    
    - GRUB output
        
    - kernel boot messages
        
    - login prompt