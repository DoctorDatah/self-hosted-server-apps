# 🚀 Proxmox Virtualization — Resource & Storage Guide for Newcomers

---

## 1) 🖥 CPU (vCPUs / Cores)
- Assigning CPU cores sets a limit/permission, **not** a dedicated physical core.
- All running VMs share host CPUs through scheduling.
- **VM OFF** → 0% CPU used.
- **VM ON** → CPU load depends on activity.
- Safe to **oversubscribe** cores as long as not all VMs are maxed out simultaneously.

✔ Purely software-scheduled, not hardware-reserved when off

---

## 2) 🧠 RAM (Memory)
- RAM is allocated only while a VM is running.
- **VM OFF** → RAM is fully freed for the host/other VMs.
- Configured RAM is a **maximum**, not reserved when off.

Example:
- Host has 64 GB RAM
- 3 running VMs using 10 GB each → 30 GB used
- 7 VMs OFF (set to 32 GB each) → 0 GB used

✔ RAM is never reserved for powered-off VMs

---

## 3) 🗄 Storage (Virtual Disks) — The confusing part
**Key idea:** Disk size you assign ≠ disk space actually used on the host. Allocation strategy matters.

---

### 🟡 A. Thin-Provisioned Storage (Dynamic allocation)
**Common thin storage types**
- `qcow2` disk images
- ZFS storage
- LVM-thin pools
- Proxmox Directory storage using `qcow2`

**How it behaves**
- Creates a virtual disk that can grow to the size you set.
- Host only stores the data actually written.
- **VM OFF** → space stays used, but only for real data; not locked.
- Great for homelabs to save space.

**Example:** 500 GB `qcow2` disk with 25 GB used inside VM →
- ✔ Host space used = 25 GB
- ✔ Remaining 475 GB = free for other VMs
- ✔ Disk grows only when more data is written

**Analogy:** Reserving seats in a cinema but only paying for the ones people sit in.

---

### 🔴 B. Thick-Provisioned Storage (Fixed allocation)
**Common thick storage types**
- Raw disks on standard LVM
- Raw image files
- Block storage without thin pools

**How it behaves**
- Allocates the full disk size immediately on the host.
- **VM OFF** → space remains occupied; not locked, just fully allocated.
- Can waste space if the disk stays mostly empty.
- Sometimes slightly faster because there is no thin-provisioning overhead.

**Example:** 500 GB raw disk →
- ✔ Host space used = 500 GB even if VM uses only 25 GB
- ✖ Remaining 475 GB = unavailable because it is fully allocated

**Analogy:** A 500-page notebook—write 10 pages or 500, it still takes the same space in your bag.

---

## 4) 🧩 Where the difference really comes from

| Concept | Thin | Thick |
| --- | --- | --- |
| Caused by hardware? | ❌ No | ❌ No |
| Caused by software design/config? | ✅ Yes | ✅ Yes |
| Reserves resources when VM is OFF? | ❌ No CPU/RAM, ❌ No disk lock | ❌ No lock, but space already used |
| Host space usage | Only actual data | Full allocated size |
| Best for beginners? | ⭐ Yes | ⚠ Only if you understand space cost |

✔ Thin vs Thick is a **software/configuration-level architectural choice** driven by:
- Storage backend (ZFS, LVM, etc.)
- Disk format (`qcow2` vs `raw`)
- Whether the storage backend supports thin provisioning

---

## 5) 🔎 How to check what you’re using in Proxmox UI
1. Go to **Datacenter → Storage**.
2. Click your storage and check its type:
   - ZFS, LVM-thin, Directory with `qcow2` → **thin**
   - LVM (not thin), raw block → **thick**
3. For individual VM disks: **VM → Hardware → Hard Disk**.
   - Shows `qcow2` → thin
   - Raw on standard LVM → thick
   - On ZFS → thin by nature

---

## 6) 🧠 Beginner tips
- If unsure, choose **thin**.
- Best beginner storage picks:
  - `qcow2` on Directory storage
  - ZFS storage (popular for homelabs)
  - LVM-thin
- Avoid at first unless you have a reason:
  - Raw on normal LVM (thick, space heavy)

---

## 7) 🧮 Resource behavior summary

| VM state | CPU | RAM | Storage |
| --- | --- | --- | --- |
| ON | Uses CPU (shared scheduling) | Uses RAM | Uses disk space |
| OFF | 0% used | 0 GB used | Disk file remains, but not locked |

---

## 🎯 Final takeaway
- CPU & RAM are only consumed when VMs are running.
- Storage files remain on disk but are not locked.
- **Thin** = uses only real data; **Thick** = uses full allocated size.
- The difference is architectural and configuration-based in software, not hardware.

---

If you want, I can also provide a visual diagram, a cheat-sheet version, or a recommended storage plan based on your VM count.
