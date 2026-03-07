#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../_common/params.sh"

REPO_PATH="$(vmcx_param_get repo_path "${VMCX_REPO_ROOT:-$PWD}")"
REPO_URL="$(vmcx_param_get repo_url "")"
BRANCH="$(vmcx_param_get branch main)"

if [[ ! -d "$REPO_PATH/.git" && -d "${VMCX_REPO_ROOT:-$PWD}/.git" ]]; then
  REPO_PATH="${VMCX_REPO_ROOT:-$PWD}"
fi

if [[ -n "$REPO_URL" ]]; then
  TOOL_PATH="${VMCX_REPO_ROOT:-$PWD}/tools/ensure_repo.sh"
  if [[ ! -x "$TOOL_PATH" ]]; then
    echo "Missing helper script: $TOOL_PATH" >&2
    exit 1
  fi

  echo "[repo_clone_or_update] ensuring repo via ensure_repo.sh"
  "$TOOL_PATH" "$REPO_URL" "$REPO_PATH" "$BRANCH"
  exit 0
fi

if [[ -d "$REPO_PATH/.git" ]]; then
  echo "[repo_clone_or_update] updating existing repo: $REPO_PATH"
  git -C "$REPO_PATH" fetch origin "$BRANCH" || true
  git -C "$REPO_PATH" checkout "$BRANCH" || true
  git -C "$REPO_PATH" pull --ff-only origin "$BRANCH" || true
  echo "[repo_clone_or_update] complete"
  exit 0
fi

echo "[repo_clone_or_update] no repo found at $REPO_PATH and no repo_url provided" >&2
echo "[repo_clone_or_update] pass --params '{"'"'repo_url'"'":"'"'https://...git'"'"}' for first clone" >&2
exit 1
