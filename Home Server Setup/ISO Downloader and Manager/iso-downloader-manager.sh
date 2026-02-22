#!/usr/bin/env bash
set -euo pipefail

# ISO Downloader and Manager for Proxmox
# - Lists mountable disks/partitions
# - Optional wipe/format to ext4
# - Mounts to a chosen mountpoint (default /mnt/usb-iso)
# - Creates <mount>/template/iso
# - Downloads a user-specified ISO into that folder
# - Shows pvesm list for a chosen storage ID

DEFAULT_MNT="/mnt/usb-iso"
DEFAULT_STORAGE_ID_USB="USB-ISO"
DEFAULT_LOCAL_ISO_DIR="/var/lib/vz/template/iso"
DEFAULT_STORAGE_ID_LOCAL="local"

require() { command -v "$1" >/dev/null || { echo "ERROR: $1 not found"; exit 1; }; }
require wget; require pvesm

if [[ $EUID -ne 0 ]]; then
  echo "ERROR: Run as root."
  exit 1
fi

read -rp "Store ISO in Proxmox local storage ($DEFAULT_LOCAL_ISO_DIR)? (Y/n): " USE_LOCAL
USE_LOCAL="${USE_LOCAL:-y}"

if [[ "${USE_LOCAL,,}" == "y" ]]; then
  ISO_DIR="$DEFAULT_LOCAL_ISO_DIR"
  MNT="/var/lib/vz"
  STORAGE_ID_DEFAULT="$DEFAULT_STORAGE_ID_LOCAL"
  mkdir -p "$ISO_DIR"
  echo "Using local storage ISO directory: $ISO_DIR"
else
  require lsblk; require blkid; require mkfs.ext4

  echo "==> Detecting mountable devices..."
  mapfile -t DEVICES < <(lsblk -rpn -o NAME,TYPE,FSTYPE | awk '($2=="part") || ($2=="disk" && $3!="") {print $1}')
  if [[ ${#DEVICES[@]} -eq 0 ]]; then
    echo "No mountable partitions/disks found."
    exit 1
  fi

  printf "%-4s %-14s %-8s %-8s %-10s %-14s %-36s %-36s %s\n" "No." "DEVICE" "SIZE" "TYPE" "TRAN" "FSTYPE" "UUID" "PARTUUID" "MOUNTPOINT"
  echo "----------------------------------------------------------------------------------------------------------------------------------"
  i=0
  for dev in "${DEVICES[@]}"; do
    ((++i))
    dtype="$(lsblk -ndo TYPE "$dev" 2>/dev/null || true)"
    parent="$dev"
    if [[ "$dtype" == "part" ]]; then
      pkname="$(lsblk -ndo PKNAME "$dev" 2>/dev/null || echo "${dev#/dev/}")"
      parent="/dev/$pkname"
    fi
    printf "%-4s %-14s %-8s %-8s %-10s %-14s %-36s %-36s %s\n" \
      "$i" "$dev" \
      "$(lsblk -ndo SIZE "$dev" 2>/dev/null || echo "?")" \
      "${dtype:-}" \
      "$(lsblk -ndo TRAN "$parent" 2>/dev/null || echo "")" \
      "$(lsblk -ndo FSTYPE "$dev" 2>/dev/null || echo "")" \
      "$(lsblk -ndo UUID "$dev" 2>/dev/null || echo "")" \
      "$(lsblk -ndo PARTUUID "$dev" 2>/dev/null || echo "")" \
      "$(lsblk -ndo MOUNTPOINT "$dev" 2>/dev/null || echo "")"
  done

  read -rp "Pick a device number (1-$i): " PICK
  if ! [[ "$PICK" =~ ^[0-9]+$ ]] || (( PICK < 1 || PICK > i )); then
    echo "Invalid selection."
    exit 1
  fi
  SEL_DEV="${DEVICES[$((PICK-1))]}"
  echo "Selected: $SEL_DEV"

  read -rp "Wipe/format $SEL_DEV as ext4? (y/N): " WIPE
  if [[ "${WIPE,,}" == "y" ]]; then
    echo "Type WIPE-$SEL_DEV to confirm:"
    read -r CONFIRM
    if [[ "$CONFIRM" != "WIPE-$SEL_DEV" ]]; then
      echo "Cancelled."
      exit 1
    fi
    umount "$SEL_DEV" 2>/dev/null || true
    echo "Formatting $SEL_DEV as ext4..."
    mkfs.ext4 -F "$SEL_DEV"
  fi

  read -rp "Mount point [default: $DEFAULT_MNT]: " MNT
  MNT="${MNT:-$DEFAULT_MNT}"
  mkdir -p "$MNT"
  umount "$SEL_DEV" 2>/dev/null || true
  mount "$SEL_DEV" "$MNT"

  ISO_DIR="$MNT/template/iso"
  mkdir -p "$ISO_DIR"

  echo "Mount info:"
  findmnt "$SEL_DEV" || true
  echo "ISO directory: $ISO_DIR"

  STORAGE_ID_DEFAULT="$DEFAULT_STORAGE_ID_USB"
fi

read -rp "Proxmox storage ID to use (for pvesm list) [$STORAGE_ID_DEFAULT]: " STORAGE_ID
STORAGE_ID="${STORAGE_ID:-$STORAGE_ID_DEFAULT}"

read -rp "Delete an existing ISO first? (y/N): " DEL_EXISTING
if [[ "${DEL_EXISTING,,}" == "y" ]]; then
  mapfile -t ISOS < <(find "$ISO_DIR" -type f -name "*.iso" 2>/dev/null || true)
  if [[ ${#ISOS[@]} -eq 0 ]]; then
    echo "No ISO files found under $ISO_DIR."
  else
    echo "Select an ISO to delete:"
    i=0
    for iso in "${ISOS[@]}"; do
      ((++i))
      rel="${iso#$ISO_DIR/}"
      printf "%-4s %s\n" "$i" "$rel"
    done
    read -rp "Pick a number (1-$i), or press Enter to skip: " DEL_PICK
    if [[ -n "${DEL_PICK:-}" ]]; then
      if ! [[ "$DEL_PICK" =~ ^[0-9]+$ ]] || (( DEL_PICK < 1 || DEL_PICK > i )); then
        echo "Invalid selection. Skipping delete."
      else
        DEL_FILE="${ISOS[$((DEL_PICK-1))]}"
        read -rp "Delete '$DEL_FILE'? (y/N): " CONF_DEL
        if [[ "${CONF_DEL,,}" == "y" ]]; then
          rm -f "$DEL_FILE"
          echo "Deleted: $DEL_FILE"
        else
          echo "Delete canceled."
        fi
      fi
    fi
  fi
fi

echo "Choose OS family:"
echo "  1) Ubuntu"
echo "  2) Debian"
echo "  3) Other"
read -rp "Select (1/2/3): " OS_CHOICE
case "$OS_CHOICE" in
  1) OS_NAME="ubuntu" ;;
  2) OS_NAME="debian" ;;
  3)
    read -rp "Enter OS name (e.g., alma, rocky, windows): " OS_NAME
    OS_NAME="${OS_NAME:-misc}"
    ;;
  *)
    echo "Invalid choice. Defaulting to ubuntu."
    OS_NAME="ubuntu"
    ;;
esac

read -rp "Enter OS version (e.g., 24.04.3, 12.5). Leave blank for 'latest': " OS_VER
OS_VER="${OS_VER:-latest}"

TARGET_DIR="$ISO_DIR/$OS_NAME/$OS_VER"
mkdir -p "$TARGET_DIR"
echo "ISO target directory: $TARGET_DIR"

read -rp "ISO download URL (e.g., https://releases.ubuntu.com/24.04.1/ubuntu-24.04.1-live-server-amd64.iso): " ISO_URL
if [[ -z "${ISO_URL:-}" ]]; then
  echo "No URL provided."
  exit 1
fi

BASE_URL="${ISO_URL%%\?*}"
ISO_FILE="$(basename "$BASE_URL")"
if [[ "$ISO_FILE" != *.iso ]]; then
  echo "⚠ URL basename '$ISO_FILE' is not a .iso; this may be a landing/thank-you page."
  echo "   Source: $BASE_URL"
  read -rp "Continue anyway? (y/N): " CONT
  if [[ "${CONT,,}" != "y" ]]; then
    echo "Cancelled."
    exit 1
  fi
fi

TARGET_PATH="$TARGET_DIR/$ISO_FILE"
echo "Downloading to $TARGET_PATH ..."
wget -c --content-disposition --trust-server-names -O "$TARGET_PATH" "$ISO_URL"

echo "Download complete. Verifying..."
ls -lh "$TARGET_PATH"

if command -v file >/dev/null 2>&1; then
  MIME_LINE="$(file --mime-type -b "$TARGET_PATH" 2>/dev/null || true)"
  if [[ -n "${MIME_LINE:-}" && "$MIME_LINE" != application/x-iso9660-image && "$MIME_LINE" != application/octet-stream ]]; then
    echo "WARNING: Downloaded file MIME type is '$MIME_LINE' (may be HTML instead of an ISO)."
  fi
fi

echo "Proxmox storage view (if storage ID is configured):"
if grep -qE "^dir:\s*$STORAGE_ID\b" /etc/pve/storage.cfg 2>/dev/null; then
  pvesm list "$STORAGE_ID"
else
  echo "Storage '$STORAGE_ID' not found. Configure it to point to $MNT."
  read -rp "Create storage '$STORAGE_ID' now (pvesm add dir ...)? (y/N): " ADD_STORE
  if [[ "${ADD_STORE,,}" == "y" ]]; then
    pvesm add dir "$STORAGE_ID" --path "$MNT" --content iso
    echo "Created. Listing content:"
    pvesm list "$STORAGE_ID" || true
  else
    echo "Run manually: pvesm add dir $STORAGE_ID --path $MNT --content iso"
  fi
fi
