#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: ensure_repo.sh <repo_url> <repo_path> [branch]" >&2
  exit 2
fi

repo_url="$1"
repo_path="$2"
branch="${3:-main}"

if [[ ! -d "$repo_path/.git" ]]; then
  mkdir -p "$(dirname "$repo_path")"
  git clone --branch "$branch" "$repo_url" "$repo_path"
else
  git -C "$repo_path" fetch origin "$branch"
  git -C "$repo_path" checkout "$branch"
  git -C "$repo_path" pull --ff-only origin "$branch"
fi

echo "repo ready: $repo_path@$branch"
