#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: ensure_repo.sh <repo_url> <repo_path> [branch]" >&2
  exit 2
fi

repo_url="$1"
repo_path="$2"
branch="${3:-main}"

repo_path="${repo_path%/}"
if [[ -z "$repo_path" || "$repo_path" == "." || "$repo_path" == "/" ]]; then
  echo "invalid repo_path: '$repo_path' (refusing to operate on root/current dir)" >&2
  exit 2
fi
repo_parent="$(dirname "$repo_path")"
repo_leaf="$(basename "$repo_path")"
git_worktree="$repo_path"
runtime_path="$repo_path"

monorepo_hint="false"
if [[ "$repo_leaf" == "vm-ops" && "$repo_url" == *"self-hosted-server-apps"* ]]; then
  monorepo_hint="true"
fi

if [[ -d "$repo_path/.git" ]]; then
  git_worktree="$repo_path"
elif [[ -d "$repo_parent/.git" && -d "$repo_path" ]]; then
  git_worktree="$repo_parent"
elif [[ "$monorepo_hint" == "true" ]]; then
  mkdir -p "$repo_parent"
  if [[ ! -d "$repo_parent/.git" ]]; then
    git clone --branch "$branch" "$repo_url" "$repo_parent"
  fi
  git_worktree="$repo_parent"
  if [[ -d "$repo_parent/vm-ops" ]]; then
    runtime_path="$repo_parent/vm-ops"
  fi
else
  mkdir -p "$repo_parent"
  git clone --branch "$branch" "$repo_url" "$repo_path"
  git_worktree="$repo_path"
fi

git -C "$git_worktree" fetch origin "$branch"
git -C "$git_worktree" checkout "$branch"
git -C "$git_worktree" pull --ff-only origin "$branch"

echo "repo ready: $git_worktree@$branch"
echo "runtime path: $runtime_path"
