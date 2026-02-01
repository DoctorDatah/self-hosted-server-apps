#!/usr/bin/env bash
set -euo pipefail

say(){ echo -e "\n==> $*"; }
ok(){ echo "[OK] $*"; }
warn(){ echo "[WARN] $*"; }
die(){ echo "[ERROR] $*" >&2; exit 1; }

trap 'echo; die "Aborted by user (signal)." ' INT TERM

usage(){
  cat <<'EOF'
Coolify password reset helper (runs inside the Coolify container).

Options:
  -e, --email       Email of the Coolify user to update (required if not set via COOLIFY_EMAIL)
  -p, --password    New password (or set COOLIFY_PASSWORD); prompts securely if omitted
  -c, --container   Container name to exec into (default: auto-detect running Coolify container)
  -y, --yes         Skip confirmation prompt
  -h, --help        Show this help

Examples:
  sudo ./coolify-reset-password.sh -e you@example.com -p 'NewPass123'
  COOLIFY_EMAIL=you@example.com COOLIFY_PASSWORD='NewPass123' ./coolify-reset-password.sh
EOF
}

prompt_confirm(){
  local reply
  read -r -p "$1 [y/N]: " reply
  case "${reply,,}" in
    y|yes) return 0 ;;
    *) return 1 ;;
  esac
}

prompt_password(){
  local __var="$1" __prompt="$2" val
  if command -v python3 >/dev/null 2>&1; then
    val="$(python3 - <<'PY' "$__prompt")" || die "Password prompt failed."
import getpass, sys
try:
    p = getpass.getpass(sys.argv[1])
    print(p)
except Exception:
    sys.exit(1)
PY
  else
    read -rsp "$__prompt" val || die "Password prompt failed."
    echo
  fi
  printf -v "$__var" "%s" "$val"
}

need_cmd(){ command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"; }

ensure_docker_running(){
  if ! docker info >/dev/null 2>&1; then
    die "Docker daemon is not running or you lack permission. Start Docker or run with sudo."
  fi
}

detect_container(){
  local names ps_out
  ps_out="$(docker ps --format '{{.Names}}' 2>/dev/null)" || return 1
  mapfile -t names <<<"$ps_out"
  [[ ${#names[@]} -gt 0 ]] || return 1
  for n in "${names[@]}"; do
    [[ "$n" == "coolify" ]] && { echo "$n"; return; }
  done
  for n in "${names[@]}"; do
    [[ "$n" =~ (^|[-_])coolify([-_]|$) ]] && { echo "$n"; return; }
  done
  return 1
}

find_app_dir(){
  docker exec "$1" sh -c '
    for d in /app /srv/coolify /var/www/html /opt/coolify /data/coolify/source; do
      if [ -f "$d/artisan" ]; then
        echo "$d"
        exit 0
      fi
    done
    exit 1
  ' || return 1
}

EMAIL="${COOLIFY_EMAIL:-}"
PASSWORD="${COOLIFY_PASSWORD:-}"
CONTAINER="${COOLIFY_CONTAINER:-}"
AUTO_CONFIRM="n"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -e|--email) EMAIL="$2"; shift 2 ;;
    -p|--password) PASSWORD="$2"; shift 2 ;;
    -c|--container) CONTAINER="$2"; shift 2 ;;
    -y|--yes) AUTO_CONFIRM="y"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown option: $1" ;;
  esac
done

need_cmd docker
ensure_docker_running

if [[ -z "$CONTAINER" ]]; then
  CONTAINER="$(detect_container)" || die "Could not auto-detect Coolify container; use --container <name>."
  ok "Auto-detected container: $CONTAINER"
fi

docker inspect "$CONTAINER" >/dev/null 2>&1 || die "Container $CONTAINER not found."
if [[ "$(docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null)" != "true" ]]; then
  die "Container $CONTAINER is not running."
fi

APP_DIR="$(find_app_dir "$CONTAINER" || true)"
[[ -n "$APP_DIR" ]] || die "Could not find Laravel artisan inside $CONTAINER. Set --container if you have a nonstandard layout."
ok "Found Coolify app dir: $APP_DIR"

docker exec "$CONTAINER" sh -c "command -v php >/dev/null" || die "PHP missing in container $CONTAINER."

if [[ -z "$EMAIL" ]]; then
  [[ -t 0 ]] || die "Email is required (set --email or COOLIFY_EMAIL when not running interactively)."
  read -r -p "Email of user to reset: " EMAIL
fi
[[ -n "$EMAIL" ]] || die "Email is required."

if [[ -z "$PASSWORD" ]]; then
  [[ -t 0 ]] || die "Password is required (set --password or COOLIFY_PASSWORD when not running interactively)."
  prompt_password PASSWORD "New password: "
  [[ -n "$PASSWORD" ]] || die "Password cannot be empty."
  prompt_password PASSWORD_CONFIRM "Confirm new password: "
  [[ "$PASSWORD" == "${PASSWORD_CONFIRM:-}" ]] || die "Passwords do not match."
fi

say "About to reset password for $EMAIL in container $CONTAINER (app dir $APP_DIR)"
[[ "$AUTO_CONFIRM" == "y" ]] || prompt_confirm "Proceed?" || die "Aborted."

TINKER_CODE="\\App\\Models\\User::where('email', getenv('EMAIL'))->update(['password' => Illuminate\\Support\\Facades\\Hash::make(getenv('PASSWORD'))]);"

say "Resetting password inside container (artisan reset -> update -> tinker fallback)"
RESET_SCRIPT='
set -Eeuo pipefail
cd "$APP_DIR" || exit 1
if php artisan user:reset-password --email "$EMAIL" --password "$PASSWORD"; then
  echo "[OK] user:reset-password succeeded"
  exit 0
else
  echo "[WARN] user:reset-password failed" >&2
fi

if php artisan user:update --email "$EMAIL" --password "$PASSWORD"; then
  echo "[OK] user:update succeeded"
  exit 0
else
  echo "[WARN] user:update failed" >&2
fi

php artisan tinker --execute "$TINKER_CODE"
'

if docker exec \
  -e EMAIL="$EMAIL" \
  -e PASSWORD="$PASSWORD" \
  -e APP_DIR="$APP_DIR" \
  -e TINKER_CODE="$TINKER_CODE" \
  "$CONTAINER" sh -c "$RESET_SCRIPT"
then
  ok "Password reset completed."
else
  die "All reset methods failed. Check container logs and try again."
fi
