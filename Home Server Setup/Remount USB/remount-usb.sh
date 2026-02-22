#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
DEFAULT_MOUNTPOINT="/mnt/usb-iso"
DEFAULT_LABEL="usb-iso"
NO_PROMPT="${NO_PROMPT:-false}"

usage() {
  cat <<USAGE
Usage:
  $SCRIPT_NAME [MOUNTPOINT] [DEVICE]
  $SCRIPT_NAME --kill [MOUNTPOINT] [DEVICE]
  $SCRIPT_NAME --label LABEL [MOUNTPOINT]

Examples:
  $SCRIPT_NAME
  $SCRIPT_NAME /mnt/usb-iso
  $SCRIPT_NAME /mnt/usb-iso /dev/sdb1
  $SCRIPT_NAME --kill /mnt/usb-iso /dev/sdb1
  $SCRIPT_NAME --label usb-iso /mnt/usb-iso

Notes:
- By default the script prefers the device with label "usb-iso".
- If DEVICE is omitted, the script will try label first, then the current
  mount backing MOUNTPOINT. If there is a mismatch, it will ask which to use.
- Use --kill to terminate processes holding the mount if unmount fails.
USAGE
}

KILL_PROCS=false
LABEL=""
ARGS=()
for arg in "$@"; do
  if [[ "$arg" == "--kill" ]]; then
    KILL_PROCS=true
  elif [[ "$arg" == "--label" ]]; then
    LABEL="__EXPECT__"
  else
    ARGS+=("$arg")
  fi
done

if [[ "${LABEL}" == "__EXPECT__" ]]; then
  if [[ ${#ARGS[@]} -eq 0 ]]; then
    echo "ERROR: --label requires a value." >&2
    usage
    exit 1
  fi
  LABEL="${ARGS[0]}"
  ARGS=("${ARGS[@]:1}")
fi

MOUNTPOINT="${ARGS[0]:-$DEFAULT_MOUNTPOINT}"
DEVICE="${ARGS[1]:-}"
LABEL="${LABEL:-$DEFAULT_LABEL}"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $EUID -ne 0 ]]; then
  if command -v sudo >/dev/null 2>&1; then
    exec sudo -E bash "$0" "$@"
  else
    echo "ERROR: Must be run as root (sudo not found)." >&2
    exit 1
  fi
fi

mkdir -p "$MOUNTPOINT"

if mountpoint -q "$MOUNTPOINT"; then
  if ! umount "$MOUNTPOINT"; then
    if $KILL_PROCS; then
      if command -v fuser >/dev/null 2>&1; then
        fuser -km "$MOUNTPOINT" || true
      elif command -v lsof >/dev/null 2>&1; then
        lsof +f -- "$MOUNTPOINT" || true
        echo "ERROR: lsof is present, but no automatic kill; stop the PIDs above and retry." >&2
        exit 1
      else
        echo "ERROR: Neither fuser nor lsof is available to locate busy processes." >&2
        exit 1
      fi
      umount "$MOUNTPOINT"
    else
      echo "ERROR: $MOUNTPOINT is busy. Re-run with --kill or stop the holding process." >&2
      exit 1
    fi
  fi
fi

LABEL_DEVICE=""
MOUNT_DEVICE=""

if [[ -e "/dev/disk/by-label/$LABEL" ]]; then
  LABEL_DEVICE="/dev/disk/by-label/$LABEL"
fi

MOUNT_DEVICE="$(findmnt -no SOURCE --target "$MOUNTPOINT" 2>/dev/null || true)"

if [[ -z "$DEVICE" ]]; then
  if [[ -n "$LABEL_DEVICE" && -n "$MOUNT_DEVICE" && "$LABEL_DEVICE" != "$MOUNT_DEVICE" && "$NO_PROMPT" != "true" ]]; then
    echo "WARNING: $MOUNTPOINT is currently mounted from $MOUNT_DEVICE"
    echo "Label '$LABEL' points to $LABEL_DEVICE"
    echo "Choose device to remount:"
    echo "1) Use label device ($LABEL_DEVICE)"
    echo "2) Use current mount device ($MOUNT_DEVICE)"
    read -r -p "Select [1/2] (default 1): " choice
    if [[ "$choice" == "2" ]]; then
      DEVICE="$MOUNT_DEVICE"
    else
      DEVICE="$LABEL_DEVICE"
    fi
  elif [[ -n "$LABEL_DEVICE" ]]; then
    DEVICE="$LABEL_DEVICE"
  else
    DEVICE="$MOUNT_DEVICE"
  fi
fi

if [[ -z "$DEVICE" ]]; then
  echo "ERROR: Device not specified and could not be detected. Provide DEVICE." >&2
  usage
  exit 1
fi

mount "$DEVICE" "$MOUNTPOINT"

echo "Remounted $DEVICE at $MOUNTPOINT"
