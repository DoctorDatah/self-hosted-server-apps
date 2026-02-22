#!/usr/bin/env bash
set -euo pipefail

# VM Disk Manager
# How to run:
#   sudo ./vm-disk-manager.sh
# Required tools:
#   coreutils, util-linux (lsblk, findmnt, mount, umount), e2fsprogs (e2fsck, resize2fs),
#   xfsprogs (xfs_growfs), parted, blkid, wipefs
# Optional tools for Hypervisor menu:
#   virsh, qemu-img
# Safety notes:
#   - Detects root disk and blocks destructive ops unless override is enabled.
#   - All destructive operations require typed confirmation.
#   - /etc/fstab is backed up before edits.
#   - Dry-run mode is supported for all commands.

SCRIPT_NAME="$(basename "$0")"
LOG_FILE="/var/log/vm-disk-manager.log"
DRY_RUN=false
VERBOSE=false
ROOT_OVERRIDE=false
NO_COLOR=false

trap 'on_exit $?' EXIT
trap 'on_interrupt' INT TERM

on_exit() {
  local code="$1"
  if [[ $code -ne 0 ]]; then
    print_error "Exited with code $code"
  fi
}

on_interrupt() {
  print_error "Interrupted."
  exit 130
}

# ---------- Core Helpers ----------
run_cmd() {
  local cmd=("$@")
  log_action "RUN: ${cmd[*]}"
  if $VERBOSE; then
    echo ">> ${cmd[*]}"
  fi
  if $DRY_RUN; then
    return 0
  fi
  "${cmd[@]}"
}

require_root() {
  if [[ $EUID -ne 0 ]]; then
    print_error "This script must be run as root."
    exit 1
  fi
}

confirm_yesno() {
  local prompt="$1"
  local ans
  while true; do
    read -r -p "$prompt [y/n]: " ans
    case "${ans,,}" in
      y|yes) return 0 ;;
      n|no) return 1 ;;
      ?) echo "Enter y or n." ;;
      h|H) echo "Help: confirm or cancel this action." ;;
      *) echo "Invalid input." ;;
    esac
  done
}

confirm_typed() {
  local expected="$1"
  local ans
  read -r -p "Type exactly '$expected' to confirm: " ans
  [[ "$ans" == "$expected" ]]
}

log_action() {
  local msg="$1"
  local ts
  ts="$(date '+%Y-%m-%d %H:%M:%S')"
  if ! $DRY_RUN; then
    echo "[$ts] $msg" >> "$LOG_FILE" 2>/dev/null || true
  fi
}

print_error() {
  local msg="$1"
  if ! $NO_COLOR; then
    echo -e "\033[31mERROR:\033[0m $msg" >&2
  else
    echo "ERROR: $msg" >&2
  fi
}

print_success() {
  local msg="$1"
  if ! $NO_COLOR; then
    echo -e "\033[32mOK:\033[0m $msg"
  else
    echo "OK: $msg"
  fi
}

pause_screen() {
  read -r -p "Press Enter to continue..."
}

# ---------- Utility ----------
have_cmd() { command -v "$1" >/dev/null 2>&1; }

validate_device() {
  local dev="$1"
  [[ -b "$dev" ]]
}

is_mounted() {
  local dev="$1"
  findmnt -rn -S "$dev" >/dev/null 2>&1
}

get_mountpoint() {
  local dev="$1"
  findmnt -rn -S "$dev" -o TARGET 2>/dev/null || true
}

lsblk_summary() {
  run_cmd lsblk -o NAME,SIZE,TYPE,FSTYPE,LABEL,UUID,MOUNTPOINT
}

df_summary() {
  run_cmd df -hT
}

blkid_summary() {
  run_cmd blkid
}

fstab_show() {
  run_cmd sed -n '1,200p' /etc/fstab
}

get_root_source() {
  findmnt -rn -o SOURCE /
}

get_root_disk() {
  local root_src
  root_src="$(get_root_source)"
  lsblk -no PKNAME "$root_src" 2>/dev/null | sed 's#^#/dev/#' || true
}

guard_root_disk() {
  local dev="$1"
  local root_disk
  root_disk="$(get_root_disk)"
  if [[ -n "$root_disk" && "$dev" == "$root_disk" && "$ROOT_OVERRIDE" == "false" ]]; then
    print_error "Operation blocked: $dev is the root disk. Enable override in Settings."
    return 1
  fi
  if [[ -n "$root_disk" && "$dev" == "$root_disk" && "$ROOT_OVERRIDE" == "true" ]]; then
    print_error "Root disk override is enabled. Triple confirmation required."
    confirm_yesno "Proceed with root disk operation?" || return 1
    confirm_yesno "Are you absolutely sure?" || return 1
    confirm_typed "$dev" || return 1
  fi
  return 0
}

show_root_disk() {
  local root_src root_disk
  root_src="$(get_root_source)"
  root_disk="$(get_root_disk)"
  echo "Root filesystem source: $root_src"
  if [[ -n "$root_disk" ]]; then
    echo "Root disk: $root_disk"
  else
    echo "Root disk: unknown"
  fi
}

show_before_after_lsblk() {
  echo "Before:"
  lsblk_summary
  echo "After:"
  lsblk_summary
}

backup_fstab() {
  local ts
  ts="$(date '+%Y%m%d-%H%M%S')"
  run_cmd cp /etc/fstab "/etc/fstab.bak.$ts"
}

safe_prompt() {
  local msg="$1"
  local ans
  while true; do
    read -r -p "$msg " ans
    case "$ans" in
      ?) echo "Tip: provide the requested value, or H for Help." ;;
      H|h) echo "Open Help Center from main menu for detailed guidance." ;;
      *) echo "$ans"; return 0 ;;
    esac
  done
}

# ---------- Guest Features ----------
mount_wizard() {
  local dev mp
  dev="$(safe_prompt "Enter device path (e.g. /dev/sdb1):")"
  if [[ ! -b "$dev" ]]; then
    print_error "Device not found: $dev"
    return
  fi
  if is_mounted "$dev"; then
    print_error "$dev is already mounted at $(get_mountpoint "$dev")"
    return
  fi
  mp="$(safe_prompt "Enter mountpoint (e.g. /mnt/data):")"
  run_cmd mkdir -p "$mp"
  run_cmd mount "$dev" "$mp"
  print_success "Mounted $dev at $mp"
}

unmount_device() {
  local dev
  dev="$(safe_prompt "Enter device path to unmount:")"
  if [[ ! -b "$dev" ]]; then
    print_error "Device not found: $dev"
    return
  fi
  if ! is_mounted "$dev"; then
    print_error "$dev is not mounted."
    return
  fi
  run_cmd umount "$dev"
  print_success "Unmounted $dev"
}

remount_device() {
  local dev mode mp
  dev="$(safe_prompt "Enter device path to remount:")"
  if [[ ! -b "$dev" ]]; then
    print_error "Device not found: $dev"
    return
  fi
  if ! is_mounted "$dev"; then
    print_error "$dev is not mounted."
    return
  fi
  mp="$(get_mountpoint "$dev")"
  mode="$(safe_prompt "Enter mode ro or rw:")"
  if [[ "$mode" != "ro" && "$mode" != "rw" ]]; then
    print_error "Invalid mode."
    return
  fi
  run_cmd mount -o "remount,$mode" "$mp"
  print_success "Remounted $dev $mode"
}

add_fstab_entry() {
  local dev uuid mp fstype opts
  dev="$(safe_prompt "Enter device path to add to fstab:")"
  if [[ ! -b "$dev" ]]; then
    print_error "Device not found: $dev"
    return
  fi
  uuid="$(blkid -s UUID -o value "$dev" 2>/dev/null || true)"
  if [[ -z "$uuid" ]]; then
    print_error "No UUID found for $dev."
    return
  fi
  mp="$(safe_prompt "Enter mountpoint:")"
  fstype="$(safe_prompt "Enter filesystem type (ext4/xfs):")"
  opts="$(safe_prompt "Enter mount options (default: defaults):")"
  opts="${opts:-defaults}"
  backup_fstab
  run_cmd mkdir -p "$mp"
  echo "UUID=$uuid $mp $fstype $opts 0 2" | run_cmd tee -a /etc/fstab >/dev/null
  print_success "Added fstab entry for $dev"
}

remove_fstab_entry() {
  local pattern tmp
  pattern="$(safe_prompt "Enter UUID or mountpoint to remove from fstab:")"
  backup_fstab
  tmp="$(mktemp)"
  run_cmd awk -v pat="$pattern" '$0 !~ pat {print}' /etc/fstab | run_cmd tee "$tmp" >/dev/null
  run_cmd cp "$tmp" /etc/fstab
  run_cmd rm -f "$tmp"
  print_success "Removed matching fstab entries."
}

create_gpt() {
  local dev
  dev="$(safe_prompt "Enter disk (e.g. /dev/sdb):")"
  if [[ ! -b "$dev" ]]; then
    print_error "Disk not found."
    return
  fi
  guard_root_disk "$dev" || return
  if is_mounted "$dev"; then
    print_error "Disk is mounted. Unmount first."
    return
  fi
  confirm_typed "$dev" || { print_error "Confirmation failed."; return; }
  show_before_after_lsblk
  run_cmd parted -s "$dev" mklabel gpt
  print_success "Created GPT on $dev"
}

create_full_partition() {
  local dev
  dev="$(safe_prompt "Enter disk (e.g. /dev/sdb):")"
  if [[ ! -b "$dev" ]]; then
    print_error "Disk not found."
    return
  fi
  guard_root_disk "$dev" || return
  if is_mounted "$dev"; then
    print_error "Disk is mounted. Unmount first."
    return
  fi
  confirm_typed "$dev" || { print_error "Confirmation failed."; return; }
  show_before_after_lsblk
  run_cmd parted -s "$dev" mkpart primary 1MiB 100%
  print_success "Created partition on $dev"
}

format_ext4() {
  local dev label
  dev="$(safe_prompt "Enter partition (e.g. /dev/sdb1):")"
  if [[ ! -b "$dev" ]]; then
    print_error "Partition not found."
    return
  fi
  guard_root_disk "$dev" || return
  if is_mounted "$dev"; then
    print_error "Partition is mounted. Unmount first."
    return
  fi
  label="$(safe_prompt "Enter label (optional):")"
  confirm_typed "$dev" || { print_error "Confirmation failed."; return; }
  show_before_after_lsblk
  if [[ -n "$label" ]]; then
    run_cmd mkfs.ext4 -L "$label" "$dev"
  else
    run_cmd mkfs.ext4 "$dev"
  fi
  print_success "Formatted $dev as ext4"
}

format_xfs() {
  local dev label
  dev="$(safe_prompt "Enter partition (e.g. /dev/sdb1):")"
  if [[ ! -b "$dev" ]]; then
    print_error "Partition not found."
    return
  fi
  guard_root_disk "$dev" || return
  if is_mounted "$dev"; then
    print_error "Partition is mounted. Unmount first."
    return
  fi
  label="$(safe_prompt "Enter label (optional):")"
  confirm_typed "$dev" || { print_error "Confirmation failed."; return; }
  show_before_after_lsblk
  if [[ -n "$label" ]]; then
    run_cmd mkfs.xfs -L "$label" "$dev"
  else
    run_cmd mkfs.xfs "$dev"
  fi
  print_success "Formatted $dev as xfs"
}

ext4_grow() {
  local dev
  dev="$(safe_prompt "Enter ext4 partition to grow (e.g. /dev/sdb1):")"
  if [[ ! -b "$dev" ]]; then
    print_error "Device not found."
    return
  fi
  if is_mounted "$dev"; then
    run_cmd resize2fs "$dev"
  else
    run_cmd e2fsck -f "$dev"
    run_cmd resize2fs "$dev"
  fi
  print_success "Resized ext4 on $dev"
}

ext4_shrink() {
  local dev size
  dev="$(safe_prompt "Enter ext4 partition to shrink:")"
  if [[ ! -b "$dev" ]]; then
    print_error "Device not found."
    return
  fi
  if is_mounted "$dev"; then
    print_error "ext4 shrink requires unmounted filesystem."
    return
  fi
  size="$(safe_prompt "Enter new size (e.g. 20G):")"
  confirm_typed "$dev" || { print_error "Confirmation failed."; return; }
  run_cmd e2fsck -f "$dev"
  run_cmd resize2fs "$dev" "$size"
  print_success "Shrank ext4 on $dev"
}

xfs_grow() {
  local mp
  mp="$(safe_prompt "Enter mountpoint of xfs filesystem:")"
  if ! findmnt -rn -T "$mp" >/dev/null 2>&1; then
    print_error "Mountpoint not found."
    return
  fi
  run_cmd xfs_growfs "$mp"
  print_success "Grew xfs at $mp"
}

xfs_shrink_block() {
  print_error "XFS does not support shrinking. Back up, recreate filesystem, and restore."
}

delete_partition() {
  local dev
  dev="$(safe_prompt "Enter partition to delete (e.g. /dev/sdb1):")"
  if [[ ! -b "$dev" ]]; then
    print_error "Partition not found."
    return
  fi
  guard_root_disk "$dev" || return
  if is_mounted "$dev"; then
    print_error "Partition is mounted. Unmount first."
    return
  fi
  confirm_typed "$dev" || { print_error "Confirmation failed."; return; }
  show_before_after_lsblk
  run_cmd wipefs -a "$dev"
  print_success "Deleted partition signatures on $dev"
}

wipefs_all() {
  local dev
  dev="$(safe_prompt "Enter device to wipefs -a:")"
  if [[ ! -b "$dev" ]]; then
    print_error "Device not found."
    return
  fi
  guard_root_disk "$dev" || return
  if is_mounted "$dev"; then
    print_error "Device is mounted. Unmount first."
    return
  fi
  confirm_typed "$dev" || { print_error "Confirmation failed."; return; }
  show_before_after_lsblk
  run_cmd wipefs -a "$dev"
  print_success "Wiped signatures on $dev"
}

# ---------- Hypervisor ----------
hypervisor_available() {
  have_cmd virsh && have_cmd qemu-img
}

hv_list_vms() {
  run_cmd virsh list --all
}

hv_show_vm_disks() {
  local vm
  vm="$(safe_prompt "Enter VM name:")"
  run_cmd virsh domblklist "$vm"
}

hv_create_qcow2() {
  local path size
  path="$(safe_prompt "Enter qcow2 path (e.g. /var/lib/libvirt/images/data.qcow2):")"
  size="$(safe_prompt "Enter size (e.g. 20G):")"
  run_cmd qemu-img create -f qcow2 "$path" "$size"
  print_success "Created $path"
}

hv_resize_qcow2() {
  local path size
  path="$(safe_prompt "Enter qcow2 path:")"
  size="$(safe_prompt "Enter new size (e.g. 40G or +10G):")"
  run_cmd qemu-img resize "$path" "$size"
  print_success "Resized $path"
}

suggest_next_target() {
  local vm="$1"
  local used targets
  used="$(virsh domblklist "$vm" 2>/dev/null | awk 'NR>2 {print $1}' | tr -d '\r')"
  targets=("vdb" "vdc" "vdd" "vde" "vdf" "vdg" "vdh" "vdi" "vdj")
  for t in "${targets[@]}"; do
    if ! echo "$used" | grep -q "^$t$"; then
      echo "$t"
      return
    fi
  done
  echo ""
}

hv_attach_disk() {
  local vm path target
  vm="$(safe_prompt "Enter VM name:")"
  path="$(safe_prompt "Enter disk path (qcow2 or block device):")"
  run_cmd virsh domblklist "$vm"
  target="$(suggest_next_target "$vm")"
  echo "Suggested target: ${target:-none}"
  target="$(safe_prompt "Enter target (e.g. vdb):")"
  confirm_yesno "Attach $path to $vm as $target?" || return
  run_cmd virsh attach-disk "$vm" "$path" "$target" --persistent
  print_success "Attached disk."
  echo "Guest rescan suggestion: run 'echo 1 > /sys/class/block/${target}/device/rescan' or rescan with udev."
}

hv_detach_disk() {
  local vm target
  vm="$(safe_prompt "Enter VM name:")"
  run_cmd virsh domblklist "$vm"
  target="$(safe_prompt "Enter target to detach (e.g. vdb):")"
  confirm_yesno "Detach $target from $vm?" || return
  run_cmd virsh detach-disk "$vm" "$target" --persistent
  print_success "Detached disk."
}

# ---------- Knowledge Base ----------
kb_topics=(
  "What is /"
  "What is /dev"
  "What is mount"
  "What is ext4"
  "What is xfs"
  "What is GPT"
  "What is fstab"
  "What is UUID"
  "What does formatting mean"
  "What is libvirt / virsh"
)

kb_show_topic() {
  local topic="$1"
  case "$topic" in
    "What is /")
      cat <<'EOF'
/ is the root of the filesystem tree.
Everything on Linux appears under /.
Example: /home, /etc, /var are all folders under /.
The root filesystem is usually on a disk or partition and is mounted at /.
EOF
      ;;
    "What is /dev")
      cat <<'EOF'
/dev contains device files that represent hardware.
A disk might be /dev/sda, and a partition might be /dev/sda1.
These are not regular files; they are interfaces to devices.
EOF
      ;;
    "What is mount")
      cat <<'EOF'
Mounting connects a device or filesystem to a directory.
After mounting, files on the device appear under the mountpoint.
Unmounting safely disconnects it.
EOF
      ;;
    "What is ext4")
      cat <<'EOF'
ext4 is a common Linux filesystem.
It supports large files, journaling, and good performance.
Most Linux distributions can read and write ext4.
EOF
      ;;
    "What is xfs")
      cat <<'EOF'
xfs is a high-performance Linux filesystem.
It handles large files and parallel IO well.
xfs can grow while mounted, but cannot shrink.
EOF
      ;;
    "What is GPT")
      cat <<'EOF'
GPT is a modern partition table format.
It supports large disks and many partitions.
It is the standard on most modern systems.
EOF
      ;;
    "What is fstab")
      cat <<'EOF'
/etc/fstab lists filesystems to mount at boot.
Each line defines a device, mountpoint, type, and options.
Editing fstab affects automatic mounting.
EOF
      ;;
    "What is UUID")
      cat <<'EOF'
UUID is a unique identifier for a filesystem.
Using UUID in fstab is stable even if device names change.
You can find UUIDs with blkid.
EOF
      ;;
    "What does formatting mean")
      cat <<'EOF'
Formatting creates a filesystem on a partition.
It erases existing data on that partition.
After formatting, you can mount and store files.
EOF
      ;;
    "What is libvirt / virsh")
      cat <<'EOF'
libvirt is a management layer for virtualization.
virsh is the command-line tool for libvirt.
It can list VMs, attach disks, and inspect VM devices.
EOF
      ;;
    *)
      print_error "Topic not found."
      ;;
  esac
}

kb_beginner_path() {
  cat <<'EOF'
Beginner Path
1) Learn about / and /dev
2) Learn what mount means
3) Learn ext4 and xfs
4) Learn fstab and UUID
5) Learn formatting basics
6) Learn libvirt / virsh if you manage VMs
EOF
}

kb_browse_topics() {
  local i=1
  for t in "${kb_topics[@]}"; do
    echo "$i) $t"
    i=$((i+1))
  done
  echo "0) Back"
  read -r -p "Select topic: " choice
  if [[ "$choice" == "0" ]]; then
    return
  fi
  if [[ "$choice" =~ ^[0-9]+$ ]] && ((choice>=1 && choice<=${#kb_topics[@]})); then
    kb_show_topic "${kb_topics[choice-1]}"
  else
    print_error "Invalid selection."
  fi
}

kb_search() {
  local q
  q="$(safe_prompt "Enter search term:")"
  local i=1
  local found=false
  for t in "${kb_topics[@]}"; do
    if [[ "${t,,}" == *"${q,,}"* ]]; then
      echo "$i) $t"
      found=true
    fi
    i=$((i+1))
  done
  if ! $found; then
    print_error "No topics matched."
  fi
}

kb_glossary() {
  cat <<'EOF'
Glossary
- Disk: Physical storage device.
- Partition: A slice of a disk.
- Filesystem: Structure that stores files on a partition.
- Mountpoint: Directory where a filesystem is attached.
- UUID: Unique ID for a filesystem.
- fstab: Boot-time mount configuration.
- libvirt: Virtualization management layer.
EOF
}

# ---------- Menus ----------
main_menu() {
  while true; do
    clear || true
    echo "VM Disk Manager"
    echo "1) Guest: View & Status"
    echo "2) Guest: Mount Operations"
    echo "3) Guest: Provision / Format"
    echo "4) Guest: Resize Filesystem"
    echo "5) Guest: Destructive Operations"
    echo "6) Knowledge Base / Help Center"
    echo "7) Hypervisor (libvirt)"
    echo "8) Settings"
    echo "9) Exit"
    read -r -p "Select: " choice
    case "$choice" in
      1) menu_guest_view ;;
      2) menu_guest_mount ;;
      3) menu_guest_provision ;;
      4) menu_guest_resize ;;
      5) menu_guest_destructive ;;
      6) menu_kb ;;
      7) menu_hypervisor ;;
      8) menu_settings ;;
      9) exit 0 ;;
      *) print_error "Invalid option."; pause_screen ;;
    esac
  done
}

menu_guest_view() {
  while true; do
    clear || true
    echo "Guest: View & Status"
    echo "1) lsblk summary"
    echo "2) df -hT"
    echo "3) blkid"
    echo "4) show fstab entries"
    echo "5) detect root disk"
    echo "0) Back"
    echo "M) Main menu"
    read -r -p "Select: " choice
    case "$choice" in
      1) lsblk_summary ;;
      2) df_summary ;;
      3) blkid_summary ;;
      4) fstab_show ;;
      5) show_root_disk ;;
      0) return ;;
      M|m) return ;;
      *) print_error "Invalid option." ;;
    esac
    pause_screen
  done
}

menu_guest_mount() {
  while true; do
    clear || true
    echo "Guest: Mount Operations"
    echo "1) Mount wizard"
    echo "2) Unmount"
    echo "3) Remount ro/rw"
    echo "4) Add fstab entry"
    echo "5) Remove fstab entry"
    echo "0) Back"
    echo "M) Main menu"
    read -r -p "Select: " choice
    case "$choice" in
      1) mount_wizard ;;
      2) unmount_device ;;
      3) remount_device ;;
      4) add_fstab_entry ;;
      5) remove_fstab_entry ;;
      0) return ;;
      M|m) return ;;
      *) print_error "Invalid option." ;;
    esac
    pause_screen
  done
}

menu_guest_provision() {
  while true; do
    clear || true
    echo "Guest: Provision / Format"
    echo "1) Create GPT partition table"
    echo "2) Create single partition using full disk"
    echo "3) Format ext4"
    echo "4) Format xfs"
    echo "0) Back"
    echo "M) Main menu"
    read -r -p "Select: " choice
    case "$choice" in
      1) create_gpt ;;
      2) create_full_partition ;;
      3) format_ext4 ;;
      4) format_xfs ;;
      0) return ;;
      M|m) return ;;
      *) print_error "Invalid option." ;;
    esac
    pause_screen
  done
}

menu_guest_resize() {
  while true; do
    clear || true
    echo "Guest: Resize Filesystem"
    echo "1) ext4 grow"
    echo "2) ext4 shrink"
    echo "3) xfs grow"
    echo "4) xfs shrink (blocked)"
    echo "0) Back"
    echo "M) Main menu"
    read -r -p "Select: " choice
    case "$choice" in
      1) ext4_grow ;;
      2) ext4_shrink ;;
      3) xfs_grow ;;
      4) xfs_shrink_block ;;
      0) return ;;
      M|m) return ;;
      *) print_error "Invalid option." ;;
    esac
    pause_screen
  done
}

menu_guest_destructive() {
  while true; do
    clear || true
    echo "Guest: Destructive Operations"
    echo "1) Delete partition"
    echo "2) wipefs -a"
    echo "0) Back"
    echo "M) Main menu"
    read -r -p "Select: " choice
    case "$choice" in
      1) delete_partition ;;
      2) wipefs_all ;;
      0) return ;;
      M|m) return ;;
      *) print_error "Invalid option." ;;
    esac
    pause_screen
  done
}

menu_kb() {
  while true; do
    clear || true
    echo "Knowledge Base / Help Center"
    echo "1) Beginner Path"
    echo "2) Browse Topics"
    echo "3) Search"
    echo "4) Glossary"
    echo "0) Back"
    echo "M) Main menu"
    read -r -p "Select: " choice
    case "$choice" in
      1) kb_beginner_path ;;
      2) kb_browse_topics ;;
      3) kb_search ;;
      4) kb_glossary ;;
      0) return ;;
      M|m) return ;;
      *) print_error "Invalid option." ;;
    esac
    pause_screen
  done
}

menu_hypervisor() {
  if ! hypervisor_available; then
    print_error "Hypervisor tools not available (virsh and qemu-img required)."
    pause_screen
    return
  fi
  while true; do
    clear || true
    echo "Hypervisor (libvirt)"
    echo "1) List VMs"
    echo "2) Show VM disks"
    echo "3) Create qcow2 disk"
    echo "4) Resize qcow2 disk"
    echo "5) Attach disk to VM"
    echo "6) Detach disk from VM"
    echo "0) Back"
    echo "M) Main menu"
    read -r -p "Select: " choice
    case "$choice" in
      1) hv_list_vms ;;
      2) hv_show_vm_disks ;;
      3) hv_create_qcow2 ;;
      4) hv_resize_qcow2 ;;
      5) hv_attach_disk ;;
      6) hv_detach_disk ;;
      0) return ;;
      M|m) return ;;
      *) print_error "Invalid option." ;;
    esac
    pause_screen
  done
}

menu_settings() {
  while true; do
    clear || true
    echo "Settings"
    echo "1) Toggle dry-run mode (current: $DRY_RUN)"
    echo "2) Toggle verbose logging (current: $VERBOSE)"
    echo "3) Toggle root-disk override (current: $ROOT_OVERRIDE)"
    echo "4) Show current configuration"
    echo "0) Back"
    echo "M) Main menu"
    read -r -p "Select: " choice
    case "$choice" in
      1) DRY_RUN=$([[ "$DRY_RUN" == "true" ]] && echo "false" || echo "true") ;;
      2) VERBOSE=$([[ "$VERBOSE" == "true" ]] && echo "false" || echo "true") ;;
      3)
        if [[ "$ROOT_OVERRIDE" == "false" ]]; then
          print_error "Enabling root override is dangerous."
          confirm_yesno "Enable root override?" && ROOT_OVERRIDE=true
        else
          ROOT_OVERRIDE=false
        fi
        ;;
      4)
        echo "DRY_RUN=$DRY_RUN"
        echo "VERBOSE=$VERBOSE"
        echo "ROOT_OVERRIDE=$ROOT_OVERRIDE"
        echo "LOG_FILE=$LOG_FILE"
        ;;
      0) return ;;
      M|m) return ;;
      *) print_error "Invalid option." ;;
    esac
    pause_screen
  done
}

# ---------- Entry ----------
require_root
main_menu

# Basic test plan:
# 1) Run in dry-run and validate all menus navigate safely.
# 2) Guest view commands display expected output.
# 3) Attempt mount/unmount with a test USB disk.
# 4) Add and remove an fstab entry and verify backup file created.
# 5) Format a test partition and verify with lsblk/blkid.
# 6) ext4 grow and shrink on a test disk (unmounted for shrink).
# 7) xfs grow on a mounted xfs filesystem.
# 8) Destructive operations blocked on root disk unless override enabled.
# 9) Hypervisor menu lists VMs and shows disks when virsh is present.
# 10) Attach and detach a qcow2 disk to a test VM in dry-run and real mode.
