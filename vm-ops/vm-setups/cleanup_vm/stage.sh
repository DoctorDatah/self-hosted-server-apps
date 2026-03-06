#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../_common/params.sh"

FULL_CLEAN="$(vmcx_param_bool full_clean false)"
REMOVE_CONTAINERS="$(vmcx_param_bool remove_containers true)"
REMOVE_VOLUMES="$(vmcx_param_bool remove_volumes false)"
REMOVE_IMAGES="$(vmcx_param_bool remove_images false)"
REMOVE_NETWORKS="$(vmcx_param_bool remove_networks false)"
REMOVE_APP_DATA="$(vmcx_param_bool remove_app_data false)"
REMOVE_REPO_FOLDERS="$(vmcx_param_bool remove_repo_folders false)"
UNINSTALL_CODEX="$(vmcx_param_bool uninstall_codex false)"
REMOVE_NODE="$(vmcx_param_bool remove_node false)"
CLEAN_TMP="$(vmcx_param_bool clean_tmp true)"
APP_DATA_PATH="$(vmcx_param_get app_data_path /data/coolify)"

if [[ "$FULL_CLEAN" == "true" ]]; then
  REMOVE_CONTAINERS=true
  REMOVE_VOLUMES=true
  REMOVE_IMAGES=true
  REMOVE_NETWORKS=true
  REMOVE_APP_DATA=true
  REMOVE_REPO_FOLDERS=true
  UNINSTALL_CODEX=true
  REMOVE_NODE=true
  CLEAN_TMP=true
fi

run_root() {
  if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
    "$@"
  else
    sudo "$@"
  fi
}

echo "[cleanup_vm] target=${VMCX_TARGET_ID:-unknown} mode=${VMCX_EXEC_MODE:-unknown} full_clean=$FULL_CLEAN"

if command -v docker >/dev/null 2>&1; then
  if [[ "$REMOVE_CONTAINERS" == "true" ]]; then
    while IFS= read -r cid; do
      [[ -z "$cid" ]] && continue
      if ! docker rm -f "$cid" >/dev/null 2>&1; then
        run_root docker rm -f "$cid" >/dev/null 2>&1 || true
      fi
    done < <(docker ps -aq 2>/dev/null || true)
  fi

  if [[ "$REMOVE_VOLUMES" == "true" ]]; then
    while IFS= read -r vid; do
      [[ -z "$vid" ]] && continue
      if ! docker volume rm -f "$vid" >/dev/null 2>&1; then
        run_root docker volume rm -f "$vid" >/dev/null 2>&1 || true
      fi
    done < <(docker volume ls -q 2>/dev/null || true)
  fi

  if [[ "$REMOVE_IMAGES" == "true" ]]; then
    while IFS= read -r iid; do
      [[ -z "$iid" ]] && continue
      if ! docker image rm -f "$iid" >/dev/null 2>&1; then
        run_root docker image rm -f "$iid" >/dev/null 2>&1 || true
      fi
    done < <(docker image ls -q 2>/dev/null || true)
  fi

  if [[ "$REMOVE_NETWORKS" == "true" ]]; then
    while IFS= read -r nname; do
      [[ -z "$nname" ]] && continue
      if ! docker network rm "$nname" >/dev/null 2>&1; then
        run_root docker network rm "$nname" >/dev/null 2>&1 || true
      fi
    done < <(docker network ls --format '{{.Name}}' 2>/dev/null | grep -v -E '^(bridge|host|none)$' || true)
  fi
else
  echo "[cleanup_vm] docker not found; skipping docker cleanup"
fi

if [[ "$REMOVE_APP_DATA" == "true" ]]; then
  run_root rm -rf "$APP_DATA_PATH"
fi

if [[ "$UNINSTALL_CODEX" == "true" ]]; then
  if command -v npm >/dev/null 2>&1; then
    run_root npm uninstall -g @openai/codex || true
  fi
fi

if [[ "$REMOVE_NODE" == "true" ]]; then
  run_root apt-get remove -y nodejs npm || true
  run_root apt-get autoremove -y || true
fi

if [[ "$REMOVE_REPO_FOLDERS" == "true" ]]; then
  run_root rm -rf /home/malik/self-hosted-server-apps /root/self-hosted-server-apps
fi

if [[ "$CLEAN_TMP" == "true" ]]; then
  find /tmp -maxdepth 1 -type f -name 'vmcx-*' -delete 2>/dev/null || true
fi

echo "[cleanup_vm] complete"
