#!/usr/bin/env bash
set -euo pipefail

# =========================
# Proxmox USB ISO Wizard
# =========================
# This script helps you:
# 1) Select a partition (or whole-disk filesystem) from a list
# 2) OPTIONAL: Wipe/format the selected device (DANGEROUS)
# 3) Mount it to /mnt/usb-iso (or a custom mountpoint)
# 4) Make it persist across reboots using UUID/PARTUUID in /etc/fstab
# 5) Create Proxmox ISO directory structure: <mount>/template/iso
# 6) Optionally download an Ubuntu ISO directly into that folder
# 7) Ensure Proxmox storage "USB-ISO" is configured for ISO content only
# 8) Show that Proxmox can see the ISO(s)

DEFAULT_MNT="/mnt/usb-iso"
DEFAULT_STORAGE="USB-ISO"
DEFAULT_LOCAL_ISO_DIR="/var/lib/vz/template/iso"

echo
echo "=============================="
echo " Proxmox USB ISO Setup Wizard "
echo "=============================="
echo

# -------------------------
# 0) Basic environment checks
# -------------------------
if [[ $EUID -ne 0 ]]; then
  echo "ERROR: Run as root."
  exit 1
fi

command -v lsblk >/dev/null || { echo "ERROR: lsblk not found"; exit 1; }
command -v blkid >/dev/null || { echo "ERROR: blkid not found"; exit 1; }
command -v pvesm >/dev/null || { echo "ERROR: pvesm not found (are you on Proxmox?)"; exit 1; }
command -v mkfs.ext4 >/dev/null || { echo "ERROR: mkfs.ext4 not found (install e2fsprogs)"; exit 1; }

echo "==> Detecting disks/partitions..."
echo

# -------------------------
# 1) Gather mountable devices list
# -------------------------
# Include:
# - partitions (TYPE=part)
# - whole disks that already have a filesystem (TYPE=disk + FSTYPE set)
# Exclude loop devices (TYPE=loop not included).
mapfile -t DEVICES < <(
  lsblk -rpn -o NAME,TYPE,FSTYPE | awk '($2=="part") || ($2=="disk" && $3!="") {print $1}'
)

if [[ ${#DEVICES[@]} -eq 0 ]]; then
  echo "No mountable partitions/disks detected."
  echo "Debug:"
  lsblk -rpn -o NAME,TYPE,SIZE,FSTYPE,MOUNTPOINT,MODEL,TRAN
  echo "Tip: Plug in the USB and run: dmesg | tail -50"
  exit 1
fi

# Print a friendly table
printf "%-4s %-14s %-6s %-8s %-12s %-10s %-14s %-36s %-36s %s\n" \
  "No." "DEVICE" "SIZE" "TYPE" "TRAN" "MODEL" "FSTYPE" "UUID" "PARTUUID" "MOUNTPOINT"
echo "----------------------------------------------------------------------------------------------------------------------------------------------------------------"

i=0
for dev in "${DEVICES[@]}"; do
  ((++i))  # IMPORTANT: avoid set -e exit on first iteration

  dtype="$(lsblk -ndo TYPE "$dev" 2>/dev/null || echo "")"

  # parent disk used for TRAN/MODEL
  parent="$dev"
  if [[ "$dtype" == "part" ]]; then
    pkname="$(lsblk -ndo PKNAME "$dev" 2>/dev/null || true)"
    if [[ -n "${pkname:-}" ]]; then
      parent="/dev/$pkname"
    else
      # fallback
      parent="${dev%[0-9]*}"
    fi
  fi

  size="$(lsblk -ndo SIZE "$dev" 2>/dev/null || echo "?")"
  fstype="$(lsblk -ndo FSTYPE "$dev" 2>/dev/null || echo "")"
  label="$(lsblk -ndo LABEL "$dev" 2>/dev/null || echo "")"
  uuid="$(lsblk -ndo UUID "$dev" 2>/dev/null || echo "")"
  partuuid="$(lsblk -ndo PARTUUID "$dev" 2>/dev/null || echo "")"
  mnt="$(lsblk -ndo MOUNTPOINT "$dev" 2>/dev/null || echo "")"

  tran="$(lsblk -ndo TRAN "$parent" 2>/dev/null || echo "")"
  model="$(lsblk -ndo MODEL "$parent" 2>/dev/null || echo "")"

  # show label in model column if model empty (USB sticks often have minimal model)
  if [[ -z "${model:-}" && -n "${label:-}" ]]; then
    model="$label"
  fi

  printf "%-4s %-14s %-6s %-8s %-12s %-10.10s %-14s %-36.36s %-36.36s %s\n" \
    "$i" "$dev" "${size:-?}" "${dtype:-}" "${tran:-}" "${model:-}" "${fstype:-}" "${uuid:-}" "${partuuid:-}" "${mnt:-}"
done

echo
read -rp "Pick a device number to use (1-$i): " PICK
if ! [[ "$PICK" =~ ^[0-9]+$ ]] || (( PICK < 1 || PICK > i )); then
  echo "Invalid selection."
  exit 1
fi

SEL_DEV="${DEVICES[$((PICK-1))]}"
SEL_TYPE="$(lsblk -ndo TYPE "$SEL_DEV" 2>/dev/null || true)"
SEL_SIZE="$(lsblk -ndo SIZE "$SEL_DEV" 2>/dev/null || true)"
SEL_FSTYPE="$(lsblk -ndo FSTYPE "$SEL_DEV" 2>/dev/null || true)"
SEL_LABEL="$(lsblk -ndo LABEL "$SEL_DEV" 2>/dev/null || true)"
SEL_UUID="$(lsblk -ndo UUID "$SEL_DEV" 2>/dev/null || true)"
SEL_PARTUUID="$(lsblk -ndo PARTUUID "$SEL_DEV" 2>/dev/null || true)"
SEL_MNT="$(lsblk -ndo MOUNTPOINT "$SEL_DEV" 2>/dev/null || true)"

# parent disk for info
SEL_PARENT="$SEL_DEV"
if [[ "$SEL_TYPE" == "part" ]]; then
  pkname="$(lsblk -ndo PKNAME "$SEL_DEV" 2>/dev/null || true)"
  if [[ -n "${pkname:-}" ]]; then
    SEL_PARENT="/dev/$pkname"
  fi
fi
SEL_TRAN="$(lsblk -ndo TRAN "$SEL_PARENT" 2>/dev/null || true)"
SEL_MODEL="$(lsblk -ndo MODEL "$SEL_PARENT" 2>/dev/null || true)"

echo
echo "Selected device: $SEL_DEV"
echo "  Type      : ${SEL_TYPE:-unknown}"
echo "  Size      : ${SEL_SIZE:-?}"
echo "  Transport : ${SEL_TRAN:-?}"
echo "  Model     : ${SEL_MODEL:-?}"
echo "  Label     : ${SEL_LABEL:-none}"
echo "  Filesystem: ${SEL_FSTYPE:-none}"
echo "  UUID      : ${SEL_UUID:-none}"
echo "  PARTUUID  : ${SEL_PARTUUID:-none}"
echo "  Mounted at: ${SEL_MNT:-no}"
echo

# -------------------------
# 1.5) OPTIONAL: wipe/format after selection
# -------------------------
echo "⚠ OPTIONAL WIPE/FORMAT"
echo "If you wipe this device, ALL data on $SEL_DEV will be permanently erased."
read -rp "Wipe and format $SEL_DEV as ext4 now? (y/N): " WIPE
if [[ "${WIPE,,}" == "y" ]]; then
  echo
  echo "Last chance: to confirm, type EXACTLY: WIPE-$SEL_DEV"
  read -rp "> " CONFIRM
  if [[ "$CONFIRM" != "WIPE-$SEL_DEV" ]]; then
    echo "Confirmation did not match. Skipping wipe."
  else
    echo "==> Unmounting (if mounted)..."
    umount "$SEL_DEV" 2>/dev/null || true
    if [[ -n "${SEL_MNT:-}" ]]; then
      umount "$SEL_MNT" 2>/dev/null || true
    fi

    # Extra warning if they picked a whole disk
    if [[ "${SEL_TYPE:-}" == "disk" ]]; then
      echo "NOTE: You selected a whole disk ($SEL_DEV). Formatting a whole disk is allowed, but uncommon."
      echo "      If you intended a partition, cancel and select e.g. /dev/sdX1 instead."
      read -rp "Proceed formatting whole disk $SEL_DEV as ext4? (type YES to continue): " YESDISK
      if [[ "$YESDISK" != "YES" ]]; then
        echo "Skipping wipe."
      else
        echo "==> Formatting $SEL_DEV as ext4..."
        mkfs.ext4 -F "$SEL_DEV"
        echo "✅ Formatted."
      fi
    else
      echo "==> Formatting $SEL_DEV as ext4..."
      mkfs.ext4 -F "$SEL_DEV"
      echo "✅ Formatted."
    fi

    # Refresh values after format (best-effort)
    SEL_FSTYPE="ext4"
    SEL_UUID="$(blkid -s UUID -o value "$SEL_DEV" 2>/dev/null || true)"
    SEL_PARTUUID="$(blkid -s PARTUUID -o value "$SEL_DEV" 2>/dev/null || true)"
    SEL_MNT=""
    echo
    echo "After format:"
    echo "  Filesystem: $SEL_FSTYPE"
    echo "  UUID      : ${SEL_UUID:-none}"
    echo "  PARTUUID  : ${SEL_PARTUUID:-none}"
    echo
  fi
fi

# -------------------------
# 2) Choose mount point and mount it
# -------------------------
read -rp "Mount point? [default: $DEFAULT_MNT] " MNT
MNT="${MNT:-$DEFAULT_MNT}"
mkdir -p "$MNT"

# If already mounted elsewhere, offer to remount
if [[ -n "${SEL_MNT:-}" ]]; then
  echo "This device is currently mounted at: $SEL_MNT"
  read -rp "Unmount it and mount to $MNT? (y/N): " UM
  if [[ "${UM,,}" == "y" ]]; then
    umount "$SEL_DEV" 2>/dev/null || umount "$SEL_MNT" 2>/dev/null || true
  else
    echo "Leaving it mounted as-is. Exiting."
    exit 0
  fi
fi

echo "==> Mounting $SEL_DEV -> $MNT"
mount "$SEL_DEV" "$MNT"

echo "==> Mounted OK:"
mount | grep -E " on $MNT " || true
echo

# -------------------------
# 3) Persist mount across reboots using UUID/PARTUUID
# -------------------------
read -rp "Make this mount persistent on reboot via /etc/fstab? (recommended) (y/N): " PERSIST
if [[ "${PERSIST,,}" == "y" ]]; then
  IDENT=""
  if [[ -n "${SEL_UUID:-}" ]]; then
    IDENT="UUID=$SEL_UUID"
  elif [[ -n "${SEL_PARTUUID:-}" ]]; then
    IDENT="PARTUUID=$SEL_PARTUUID"
  else
    echo "⚠ No UUID or PARTUUID available. Can't persist safely. You can still mount manually."
    exit 0
  fi

  if [[ -z "${SEL_FSTYPE:-}" ]]; then
    echo "⚠ Filesystem type not detected. Can't persist safely."
    exit 1
  fi

  echo "==> Backing up /etc/fstab..."
  cp /etc/fstab "/etc/fstab.bak.$(date +%F_%H%M%S)"

  echo "==> Removing any existing /etc/fstab lines for mountpoint $MNT (prevents duplicates)..."
  # Remove any non-comment line whose 2nd field equals the mountpoint (robust vs spacing)
  awk -v mnt="$MNT" '
    /^[[:space:]]*#/ { print; next }
    NF >= 2 && $2 == mnt { next }
    { print }
  ' /etc/fstab > /etc/fstab.new
  mv /etc/fstab.new /etc/fstab

  echo "==> Adding new fstab entry (uses $IDENT):"
  echo "$IDENT  $MNT  $SEL_FSTYPE  defaults,nofail,x-systemd.automount,x-systemd.device-timeout=10  0  2" >> /etc/fstab

  echo "==> Reload systemd and test mount -a..."
  systemctl daemon-reload
  umount "$MNT" 2>/dev/null || true
  mount -a

  if mount | grep -qE " on $MNT "; then
    echo "✅ Persistent mount works."
  else
    echo "❌ Persistent mount failed. Showing dmesg tail:"
    dmesg | tail -30
    exit 1
  fi
  echo
fi

# -------------------------
# 4) Create Proxmox ISO structure + move ISO files
# -------------------------
echo "==> Ensuring Proxmox ISO folder exists:"
ISO_DIR="$MNT/template/iso"
mkdir -p "$ISO_DIR"

read -rp "Move any *.iso found in $MNT root into $ISO_DIR ? (y/N): " MOVEISO
if [[ "${MOVEISO,,}" == "y" ]]; then
  shopt -s nullglob
  isos=("$MNT"/*.iso)
  if (( ${#isos[@]} > 0 )); then
    mv "$MNT"/*.iso "$ISO_DIR"/
    echo "✅ Moved ISO files into $ISO_DIR"
  else
    echo "No ISO files found in $MNT root."
  fi
  shopt -u nullglob
fi

echo
echo "==> Current ISO folder contents:"
ls -lh "$ISO_DIR" || true
echo

# -------------------------
# 5) Optional: download Ubuntu ISO (default to local storage)
# -------------------------
read -rp "Download Ubuntu ISO now? (y/N): " DL
if [[ "${DL,,}" == "y" ]]; then
  echo
  echo "Note: Default is local storage so VMs can boot even if the USB is unplugged."
  read -rp "Download location? [default: $DEFAULT_LOCAL_ISO_DIR] " DL_DIR
  DL_DIR="${DL_DIR:-$DEFAULT_LOCAL_ISO_DIR}"
  if [[ "$DL_DIR" != "$ISO_DIR" ]]; then
    echo "Using download directory: $DL_DIR"
  fi
  mkdir -p "$DL_DIR"

  echo "Choose Ubuntu ISO:"
  echo "  1) Ubuntu 24.04.3 Server (smaller, recommended for ~8GB USB)"
  echo "  2) Ubuntu 24.04.3 Desktop (larger)"
  read -rp "Select (1/2): " WHICH

  cd "$DL_DIR"
  if [[ "$WHICH" == "1" ]]; then
    URL="https://releases.ubuntu.com/noble/ubuntu-24.04.3-live-server-amd64.iso"
  else
    URL="https://releases.ubuntu.com/noble/ubuntu-24.04.3-desktop-amd64.iso"
  fi

  echo "Downloading: $URL"
  wget -c "$URL"
  echo "✅ Download complete."
  echo
fi

echo "==> ISO folder contents after download/move:"
ls -lh "$ISO_DIR" || true
echo

# -------------------------
# 6) Ensure Proxmox storage exists and is set to ISO-only
# -------------------------
read -rp "Proxmox Storage ID to use? [default: $DEFAULT_STORAGE] " STORAGE
STORAGE="${STORAGE:-$DEFAULT_STORAGE}"

DID_CREATE_STORAGE=0
if grep -qE "^dir:\s*$STORAGE\b" /etc/pve/storage.cfg; then
  echo "==> Storage '$STORAGE' exists. Setting content to ISO only..."
  pvesm set "$STORAGE" --content iso
else
  echo "⚠ Storage '$STORAGE' not found in /etc/pve/storage.cfg"
  read -rp "Create it now pointing to $MNT? (y/N): " ADD_STORAGE
  if [[ "${ADD_STORAGE,,}" == "y" ]]; then
    pvesm add dir "$STORAGE" --path "$MNT" --content iso
    echo "✅ Storage '$STORAGE' created."
    DID_CREATE_STORAGE=1
  else
    ADD_CMD="pvesm add dir $STORAGE --path $MNT --content iso"
    echo "Next step: run '$ADD_CMD', then rerun this storage check (or rerun the script)."
    echo "UI path: Datacenter -> Storage -> Add -> Directory (ID: $STORAGE, Directory: $MNT, Content: ISO)."
    echo
  fi
fi

echo "==> What Proxmox sees in storage '$STORAGE':"
if [[ "$DID_CREATE_STORAGE" -eq 1 ]] || grep -qE "^dir:\s*$STORAGE\b" /etc/pve/storage.cfg; then
  pvesm list "$STORAGE" || true
else
  echo "Storage '$STORAGE' still not present; list skipped."
fi

echo
echo "=============================="
echo "✅ DONE"
echo "=============================="
echo
echo "Next in Proxmox UI:"
echo "  1) Datacenter -> Storage -> $STORAGE -> Content -> Refresh"
echo "  2) Create VM -> OS -> ISO Image -> pick the Ubuntu ISO"
echo
echo "Tip: Proxmox scans ISO files from: $ISO_DIR"
