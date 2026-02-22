#!/usr/bin/env bash
set -euo pipefail

say(){ echo -e "\n==> $*"; }
ok(){ echo "[OK] $*"; }
warn(){ echo "[WARN] $*"; }
die(){ echo "[ERROR] $*" >&2; exit 1; }

need_root(){
  [[ "${EUID}" -eq 0 ]] || die "Run as root (sudo)."
}

read_default(){
  local __var="$1" __prompt="$2" __default="$3" val
  read -r -p "$__prompt (default: $__default): " val
  val="${val:-$__default}"
  printf -v "$__var" "%s" "$val"
}

ask_yes_no(){
  local __var="$1" __prompt="$2" __default="$3" reply hint
  if [[ "${__default,,}" == "y" ]]; then hint="Y/n"; else hint="y/N"; fi
  read -r -p "$__prompt [$hint]: " reply
  reply="${reply:-$__default}"
  case "${reply,,}" in
    y|yes) printf -v "$__var" "y" ;;
    n|no)  printf -v "$__var" "n" ;;
    *) die "Please answer y or n." ;;
  esac
}

choose_path(){
  local choice
  while true; do
    echo
    echo "Choose storage path:"
    echo "  A) Keep existing data (non-destructive, NTFS/etc)"
    echo "  B) Reformat to ext4 (destructive)"
    read -r -p "Enter A or B: " choice
    case "${choice^^}" in
      A|B)
        printf "%s" "${choice^^}"
        return 0
        ;;
      *)
        warn "Invalid choice. Enter A or B."
        ;;
    esac
  done
}

backup_file(){
  local path="$1"
  [[ -f "$path" ]] || return 0
  cp "$path" "${path}.bak.$(date +%F-%H%M%S)"
}

set_fstab_entry(){
  local mount_point="$1" entry="$2" tmp
  tmp="$(mktemp)"

  awk -v mp="$mount_point" '
    /^[[:space:]]*#/ { print; next }
    NF == 0 { print; next }
    $2 == mp { next }
    { print }
  ' /etc/fstab > "$tmp"

  printf "%s\n" "$entry" >> "$tmp"
  cat "$tmp" > /etc/fstab
  rm -f "$tmp"
}

set_exports_entry(){
  local mount_point="$1" entry="$2" tmp
  tmp="$(mktemp)"

  if [[ -f /etc/exports ]]; then
    awk -v mp="$mount_point" '
      /^[[:space:]]*#/ { print; next }
      NF == 0 { print; next }
      $1 == mp { next }
      { print }
    ' /etc/exports > "$tmp"
  fi

  printf "%s\n" "$entry" >> "$tmp"
  cat "$tmp" > /etc/exports
  rm -f "$tmp"
}

configure_samba(){
  local mount_point="$1" smb_user="$2" share_name="$3" block_start block_end smb_conf tmp
  block_start="# BEGIN CODEX_NAS_SHARE_${share_name}"
  block_end="# END CODEX_NAS_SHARE_${share_name}"
  smb_conf="/etc/samba/smb.conf"

  say "Installing Samba"
  apt-get install -y samba
  backup_file "$smb_conf"

  if [[ ! -f "$smb_conf" ]]; then
    cat > "$smb_conf" <<'CONF'
[global]
   workgroup = WORKGROUP
   server role = standalone server
   map to guest = bad user
CONF
  fi

  tmp="$(mktemp)"
  awk -v s="$block_start" -v e="$block_end" '
    $0==s {skip=1; next}
    $0==e {skip=0; next}
    skip!=1 {print}
  ' "$smb_conf" > "$tmp"

  {
    cat "$tmp"
    echo
    echo "$block_start"
    echo "[$share_name]"
    echo "   path = $mount_point"
    echo "   browseable = yes"
    echo "   read only = no"
    echo "   guest ok = no"
    echo "   valid users = $smb_user"
    echo "   create mask = 0664"
    echo "   directory mask = 0775"
    echo "$block_end"
  } > "$smb_conf"
  rm -f "$tmp"

  systemctl enable --now smbd

  if id "$smb_user" >/dev/null 2>&1; then
    ask_yes_no SET_SMB_PASS "Set/Update Samba password now for user '$smb_user'?" "y"
    if [[ "$SET_SMB_PASS" == "y" ]]; then
      smbpasswd -a "$smb_user"
    fi
  else
    warn "Linux user '$smb_user' does not exist. Create it first, then run: smbpasswd -a $smb_user"
  fi

  ok "Samba share configured: [$share_name] -> $mount_point"
}

configure_nfs(){
  local mount_point="$1" subnet="$2"
  local entry="$mount_point ${subnet}(rw,sync,no_subtree_check)"

  say "Installing NFS server"
  apt-get install -y nfs-kernel-server
  backup_file /etc/exports
  set_exports_entry "$mount_point" "$entry"
  exportfs -ra
  systemctl enable --now nfs-kernel-server
  ok "NFS export configured: $entry"
}

detect_default_nfs_subnet(){
  # Prefer the first global IPv4 on a non-loopback interface and convert to /24 CIDR.
  # Fail fast if no usable subnet can be detected.
  local ip addr
  ip="$(ip -o -4 addr show scope global 2>/dev/null | awk 'NR==1{print $4}')"
  if [[ -n "${ip:-}" ]]; then
    addr="${ip%%/*}"
    if [[ "$addr" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
      printf "%s.%s.%s.0/24" "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}" "${BASH_REMATCH[3]}"
      return 0
    fi
  fi
  die "Could not auto-detect NFS subnet from host IPv4. Set a global IPv4 address first, or skip NFS."
}

main(){
  local path_choice part_dev disk_dev disk_default mount_point uuid fstab_entry parent_name nfs_default_subnet

  need_root

  say "Proxmox External HDD NAS Setup (interactive)"
  echo "This script helps you configure either:"
  echo " - Path A: keep existing data"
  echo " - Path B: reformat disk to ext4 (destructive)"

  ask_yes_no CONTINUE "Continue?" "y"
  [[ "$CONTINUE" == "y" ]] || die "Aborted."

  say "Current block devices"
  lsblk -o NAME,SIZE,FSTYPE,LABEL,UUID,MOUNTPOINT,MODEL

  read_default part_dev "Enter target partition device" "/dev/sdc1"
  [[ -b "$part_dev" ]] || die "Device not found: $part_dev"

  read_default mount_point "Enter mount point" "/mnt/nas"
  mkdir -p "$mount_point"

  backup_file /etc/fstab

  path_choice="$(choose_path)"

  if [[ "$path_choice" == "A" ]]; then
    say "Path A selected: keep existing data"
    apt-get update
    apt-get install -y ntfs-3g

    mount -t ntfs3 "$part_dev" "$mount_point"
    uuid="$(blkid -s UUID -o value "$part_dev")"
    [[ -n "$uuid" ]] || die "Could not read UUID for $part_dev"

    fstab_entry="UUID=$uuid $mount_point ntfs3 defaults,nofail,uid=1000,gid=1000,umask=002 0 0"
    set_fstab_entry "$mount_point" "$fstab_entry"

  else
    say "Path B selected: reformat to ext4 (destructive)"
    ask_yes_no CONFIRM_ERASE "This will erase data on the target disk. Continue?" "n"
    [[ "$CONFIRM_ERASE" == "y" ]] || die "Aborted before destructive operations."

    parent_name="$(lsblk -no PKNAME "$part_dev" 2>/dev/null | head -n1 || true)"
    if [[ -n "$parent_name" ]]; then
      disk_default="/dev/${parent_name}"
    else
      disk_default="$(printf "%s" "$part_dev" | sed -E 's/p?[0-9]+$//')"
    fi

    read_default disk_dev "Enter parent disk for repartition (example: /dev/sdc)" "$disk_default"
    [[ -b "$disk_dev" ]] || die "Disk not found: $disk_dev"

    umount "$part_dev" 2>/dev/null || true
    parted "$disk_dev" -- mklabel gpt
    parted "$disk_dev" -- mkpart primary ext4 0% 100%
    mkfs.ext4 -L nas_data "$part_dev"

    mount "$part_dev" "$mount_point"
    uuid="$(blkid -s UUID -o value "$part_dev")"
    [[ -n "$uuid" ]] || die "Could not read UUID for $part_dev"

    fstab_entry="UUID=$uuid $mount_point ext4 defaults,nofail 0 2"
    set_fstab_entry "$mount_point" "$fstab_entry"
  fi

  say "Validating mount"
  umount "$mount_point" 2>/dev/null || true
  mount -a
  findmnt "$mount_point"
  touch "$mount_point/.write_test"
  ok "Mount writable: $mount_point"

  ask_yes_no DO_SAMBA "Configure Samba share?" "y"
  if [[ "$DO_SAMBA" == "y" ]]; then
    read_default SMB_USER "Linux user allowed for Samba share" "root"
    read_default SHARE_NAME "Samba share name" "WD-NAS"
    configure_samba "$mount_point" "$SMB_USER" "$SHARE_NAME"
  fi

  ask_yes_no DO_NFS "Configure NFS export too?" "n"
  if [[ "$DO_NFS" == "y" ]]; then
    nfs_default_subnet="$(detect_default_nfs_subnet)"
    read_default NFS_SUBNET "NFS subnet CIDR" "$nfs_default_subnet"
    configure_nfs "$mount_point" "$NFS_SUBNET"
  fi

  echo
  ok "Setup complete"
  echo "Mount point: $mount_point"
  echo "Device: $part_dev"
  echo "fstab entry:"
  grep -E "[[:space:]]$mount_point[[:space:]]" /etc/fstab || true

  if [[ "${DO_SAMBA:-n}" == "y" ]]; then
    echo "SMB access: \\\\<proxmox-ip>\\${SHARE_NAME}"
  fi

  if [[ "${DO_NFS:-n}" == "y" ]]; then
    echo "NFS export configured in /etc/exports for subnet: ${NFS_SUBNET}"
  fi

  echo "If needed in Proxmox UI: Datacenter -> Storage -> Add -> Directory -> $mount_point"
}

main "$@"
