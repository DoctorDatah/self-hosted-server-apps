#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
SOURCE_DIR="$REPO_ROOT/vm-codex/skills"
DEST_DIR="${CODEX_HOME:-$HOME/.codex}/skills"

ONLY=""
LIST_ONLY=0
DRY_RUN=0

usage() {
  cat <<'USAGE'
Usage: ./vm-codex/tools/install_skills.sh [options]

Options:
  --list              List installable vm-codex skills from repo
  --only <csv>        Install only selected skills (comma-separated)
  --dest <path>       Override destination skills directory
  --dry-run           Print operations without writing files
  -h, --help          Show help
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --list)
      LIST_ONLY=1
      ;;
    --only)
      shift
      ONLY="${1-}"
      ;;
    --dest)
      shift
      DEST_DIR="${1-}"
      ;;
    --dry-run)
      DRY_RUN=1
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

if [[ ! -d "$SOURCE_DIR" ]]; then
  echo "Source skills directory not found: $SOURCE_DIR" >&2
  exit 1
fi

ALL_SKILLS=()
while IFS= read -r skill; do
  [[ -n "$skill" ]] && ALL_SKILLS+=("$skill")
done < <(
  find "$SOURCE_DIR" -mindepth 1 -maxdepth 1 -type d -name 'vm-codex-*' \
    -exec test -f '{}/SKILL.md' ';' -print | sed 's#.*/##' | sort
)

if [[ ${#ALL_SKILLS[@]} -eq 0 ]]; then
  echo "No vm-codex skills found in $SOURCE_DIR" >&2
  exit 1
fi

if [[ $LIST_ONLY -eq 1 ]]; then
  printf '%s\n' "${ALL_SKILLS[@]}"
  exit 0
fi

SELECTED=()
if [[ -z "$ONLY" ]]; then
  SELECTED=("${ALL_SKILLS[@]}")
else
  IFS=',' read -r -a req <<< "$ONLY"
  for item in "${req[@]}"; do
    name="${item// /}"
    [[ -z "$name" ]] && continue
    found=0
    for skill in "${ALL_SKILLS[@]}"; do
      if [[ "$skill" == "$name" ]]; then
        found=1
        SELECTED+=("$name")
        break
      fi
    done
    if [[ $found -eq 0 ]]; then
      echo "Unknown skill in --only: $name" >&2
      exit 1
    fi
  done
fi

if [[ ${#SELECTED[@]} -eq 0 ]]; then
  echo "No skills selected." >&2
  exit 1
fi

if [[ $DRY_RUN -eq 1 ]]; then
  echo "[dry-run] destination: $DEST_DIR"
  for skill in "${SELECTED[@]}"; do
    echo "[dry-run] sync $SOURCE_DIR/$skill -> $DEST_DIR/$skill"
  done
  exit 0
fi

mkdir -p "$DEST_DIR"

for skill in "${SELECTED[@]}"; do
  src="$SOURCE_DIR/$skill"
  dst="$DEST_DIR/$skill"
  mkdir -p "$dst"

  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete "$src/" "$dst/"
  else
    rm -rf "$dst"
    cp -R "$src" "$dst"
  fi
  echo "Installed: $skill -> $dst"
done

echo "Skill installation complete."
