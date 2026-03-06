#!/usr/bin/env bash
set -euo pipefail

TARGET=""
BACKUP_ROOT=""
RESTORE_ROOT=""
RESTORE_TARGET_TYPE="staging"

usage() {
  cat <<'USAGE'
Usage: restore_app.sh --target <id> --backup-root <path> --restore-root <path> --restore-target-type staging
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      shift
      TARGET="${1-}"
      ;;
    --backup-root)
      shift
      BACKUP_ROOT="${1-}"
      ;;
    --restore-root)
      shift
      RESTORE_ROOT="${1-}"
      ;;
    --restore-target-type)
      shift
      RESTORE_TARGET_TYPE="${1-}"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
  shift
done

if [[ "$RESTORE_TARGET_TYPE" != "staging" ]]; then
  echo "restore-target-type must be staging" >&2
  exit 1
fi
if [[ -z "$TARGET" || -z "$BACKUP_ROOT" || -z "$RESTORE_ROOT" ]]; then
  echo "target/backup-root/restore-root required" >&2
  exit 1
fi

LATEST=$(ls -1t "$BACKUP_ROOT"/${TARGET}-*.tar.gz 2>/dev/null | head -n1 || true)
if [[ -z "$LATEST" ]]; then
  echo "No backup artifact found for target: $TARGET" >&2
  exit 1
fi

if [[ ! -f "$LATEST.sha256" ]]; then
  echo "Missing checksum file for $LATEST" >&2
  exit 1
fi

sha256sum -c "$LATEST.sha256"
mkdir -p "$RESTORE_ROOT"
tar -xzf "$LATEST" -C "$RESTORE_ROOT"

echo "Restore complete to: $RESTORE_ROOT"
