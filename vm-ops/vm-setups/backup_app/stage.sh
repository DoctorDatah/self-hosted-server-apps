#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../_common/params.sh"

TARGET="${VMCX_TARGET_ID:-unknown-target}"
APP_ID="$(vmcx_param_get app_id unknown-app)"
BACKUP_ROOT="$(vmcx_param_get backup_root "${VMCX_REPO_ROOT:-$PWD}/local-state/backups")"
SOURCES="$(vmcx_param_get sources "")"
BACKUP_PATHS="$(vmcx_param_get backup_paths "")"
BACKUP_ID="$(vmcx_param_get backup_id "")"

if [[ -z "$SOURCES" && -n "$BACKUP_PATHS" ]]; then
  SOURCES="$BACKUP_PATHS"
fi
if [[ -z "$SOURCES" ]]; then
  SOURCES="/var/lib/${APP_ID}"
fi

mkdir -p "$BACKUP_ROOT"

if [[ -n "$BACKUP_ID" ]]; then
  STAMP="$BACKUP_ID"
else
  STAMP=$(date -u +"%Y%m%dT%H%M%SZ")
fi

ARTIFACT="$BACKUP_ROOT/${TARGET}-${STAMP}.tar.gz"
MANIFEST="$BACKUP_ROOT/${TARGET}-${STAMP}.manifest.txt"

IFS=',' read -r -a arr <<< "$SOURCES"
EXISTING=()
for src in "${arr[@]}"; do
  s="${src// /}"
  [[ -z "$s" ]] && continue
  if [[ -e "$s" ]]; then
    EXISTING+=("$s")
  fi
done

if [[ ${#EXISTING[@]} -eq 0 ]]; then
  echo "No valid backup sources found. requested=$SOURCES" >&2
  exit 1
fi

echo "[backup_app] target=$TARGET app_id=$APP_ID"
echo "[backup_app] artifact=$ARTIFACT"
tar -czf "$ARTIFACT" "${EXISTING[@]}"

if command -v sha256sum >/dev/null 2>&1; then
  sha256sum "$ARTIFACT" > "$ARTIFACT.sha256"
elif command -v shasum >/dev/null 2>&1; then
  shasum -a 256 "$ARTIFACT" > "$ARTIFACT.sha256"
else
  echo "ERROR: sha256sum/shasum not found" >&2
  exit 1
fi

{
  echo "target=$TARGET"
  echo "app_id=$APP_ID"
  echo "timestamp=$STAMP"
  echo "sources=${EXISTING[*]}"
  echo "artifact=$ARTIFACT"
} > "$MANIFEST"

if [[ -n "${VMCX_RUN_DIR:-}" ]]; then
  mkdir -p "${VMCX_RUN_DIR}/manifests"
  cp "$MANIFEST" "${VMCX_RUN_DIR}/manifests/"
  cp "$ARTIFACT.sha256" "${VMCX_RUN_DIR}/manifests/"
fi

echo "Backup created: $ARTIFACT"
