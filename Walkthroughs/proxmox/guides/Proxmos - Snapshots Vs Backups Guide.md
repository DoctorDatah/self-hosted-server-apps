# Proxmox Snapshots vs Backups

Short answer: **snapshots are fast + local; backups are slower + safer**.

---

## Snapshot (point-in-time state)
- Uses copy-on-write (ZFS, LVM-thin, qcow2).
- Captures VM state instantly; can optionally include RAM.

**Pros**
- ⚡ Seconds to create and rollback.
- Perfect before updates or risky config changes.

**Cons**
- ❌ Lives on the **same storage** (no disk-failure protection).
- ❌ Too many snapshots can hurt performance.
- ❌ Not ideal for long-term retention.

**Best for**
- “If this update breaks, I want to roll back fast.”

---

## Backup (full copy of VM data)
- Uses `vzdump` or Proxmox Backup Server (PBS).
- Stored on **separate storage** (HDD, NAS, PBS, or cloud).

**Pros**
- 🛡 Protects against disk failure, corruption, ransomware.
- 🕒 Designed for long-term retention.
- 📦 Restores to another node/cluster.

**Cons**
- ⏳ Slower than snapshots.
- ❌ Does not capture live RAM state.

**Best for**
- Disaster recovery and scheduled protection.

---

## Side-by-side

| Feature            | Snapshot    | Backup           |
| ------------------ | ----------- | ---------------- |
| Speed              | Very fast   | Slower           |
| Storage            | Same disk   | Separate storage |
| Disaster recovery  | ❌ No        | ✅ Yes            |
| Long-term use      | ❌ No        | ✅ Yes            |
| Performance impact | Can degrade | Minimal          |
| RAM state          | Optional    | ❌ No             |

---

## Best practice
✅ Snapshot before updates/experiments.  
✅ Schedule backups daily/weekly for real safety.
