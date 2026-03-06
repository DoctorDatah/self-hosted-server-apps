#!/usr/bin/env bash
set -euo pipefail

TARGET=""
BACKUP_ROOT=""
SOURCES=""

usage() {
  cat <<'USAGE'
Usage: backup_app.sh --target <id> --backup-root <path> --sources <csv>
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
    --sources)
      shift
      SOURCES="${1-}"
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

if [[ -z "$TARGET" || -z "$BACKUP_ROOT" || -z "$SOURCES" ]]; then
  echo "target/backup-root/sources are required" >&2
  exit 1
fi

mkdir -p "$BACKUP_ROOT"
STAMP=$(date -u +"%Y%m%dT%H%M%SZ")
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
  echo "No valid backup sources found" >&2
  exit 1
fi

tar -czf "$ARTIFACT" "${EXISTING[@]}"
sha256sum "$ARTIFACT" > "$ARTIFACT.sha256"
{
  echo "target=$TARGET"
  echo "timestamp=$STAMP"
  echo "sources=${EXISTING[*]}"
  echo "artifact=$ARTIFACT"
} > "$MANIFEST"

echo "Backup created: $ARTIFACT"
