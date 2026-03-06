#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../_common/params.sh"

TARGET="${VMCX_TARGET_ID:-unknown-target}"
APP_ID="$(vmcx_param_get app_id unknown-app)"
BACKUP_ROOT="$(vmcx_param_get backup_root "${VMCX_REPO_ROOT:-$PWD}/local-state/backups")"
RESTORE_ROOT="$(vmcx_param_get restore_root "${VMCX_REPO_ROOT:-$PWD}/local-state/restore/${TARGET}")"
RESTORE_TARGET_TYPE="$(vmcx_param_get restore_target_type staging)"
BACKUP_ID="$(vmcx_param_get backup_id "")"
FORCE="$(vmcx_param_bool force false)"

if [[ "$RESTORE_TARGET_TYPE" != "staging" ]]; then
  echo "restore-target-type must be staging" >&2
  exit 1
fi
if [[ -z "$TARGET" || -z "$BACKUP_ROOT" || -z "$RESTORE_ROOT" ]]; then
  echo "target/backup-root/restore-root required" >&2
  exit 1
fi

if [[ -n "$BACKUP_ID" ]]; then
  if [[ "$BACKUP_ID" == *.tar.gz ]]; then
    LATEST="$BACKUP_ID"
  else
    LATEST="$BACKUP_ROOT/${TARGET}-${BACKUP_ID}.tar.gz"
  fi
else
  LATEST=$(ls -1t "$BACKUP_ROOT"/${TARGET}-*.tar.gz 2>/dev/null | head -n1 || true)
fi

if [[ -z "$LATEST" || ! -f "$LATEST" ]]; then
  echo "No backup artifact found for target: $TARGET" >&2
  exit 1
fi

if [[ ! -f "$LATEST.sha256" ]]; then
  echo "Missing checksum file for $LATEST" >&2
  exit 1
fi

if command -v sha256sum >/dev/null 2>&1; then
  sha256sum -c "$LATEST.sha256"
elif command -v shasum >/dev/null 2>&1; then
  expected=$(awk '{print $1}' "$LATEST.sha256")
  actual=$(shasum -a 256 "$LATEST" | awk '{print $1}')
  if [[ "$expected" != "$actual" ]]; then
    echo "Checksum mismatch for $LATEST" >&2
    exit 1
  fi
else
  echo "ERROR: sha256sum/shasum not found" >&2
  exit 1
fi

if [[ "$FORCE" != "true" && -d "$RESTORE_ROOT" ]]; then
  if [[ -n "$(find "$RESTORE_ROOT" -mindepth 1 -print -quit 2>/dev/null || true)" ]]; then
    echo "Restore root is not empty: $RESTORE_ROOT (set force=true to continue)" >&2
    exit 1
  fi
fi

mkdir -p "$RESTORE_ROOT"
tar -xzf "$LATEST" -C "$RESTORE_ROOT"

if [[ -n "${VMCX_RUN_DIR:-}" ]]; then
  mkdir -p "${VMCX_RUN_DIR}/manifests"
  {
    echo "target=$TARGET"
    echo "app_id=$APP_ID"
    echo "artifact=$LATEST"
    echo "restore_root=$RESTORE_ROOT"
    echo "status=ok"
  } > "${VMCX_RUN_DIR}/manifests/restore-manifest.txt"
fi

echo "Restore complete to: $RESTORE_ROOT"
