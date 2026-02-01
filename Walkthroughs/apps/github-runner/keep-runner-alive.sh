#!/usr/bin/env bash
set -euo pipefail

# GitHub Actions self-hosted runner keep-alive helper.
# - Accepts RUNNER_DIR env var or first CLI arg (relative paths OK).
# - Resolves to an absolute path, installs/starts the runner service, and masks sleep targets (optional).
# - Adds a watchdog timer to restart the runner if it stops.
# - Optional network keepalive timer to keep outbound connectivity warm.

# --- Inputs ---
RUNNER_DIR_INPUT="${1:-${RUNNER_DIR:-}}"
DISABLE_SLEEP="${DISABLE_SLEEP:-true}"                  # true/false
ENABLE_NET_KEEPALIVE="${ENABLE_NET_KEEPALIVE:-true}"    # true/false
NET_KEEPALIVE_HOST="${NET_KEEPALIVE_HOST:-github.com}"  # ping host

need_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    echo "ERROR: run as root (use sudo)."
    exit 1
  fi
}

abs_path() {
  # Convert relative path to absolute path without requiring realpath to exist
  local p="$1"
  if command -v realpath >/dev/null 2>&1; then
    realpath "$p"
  else
    python3 - <<PY
import os, sys
print(os.path.abspath(sys.argv[1]))
PY
  fi
}

echo "==> GitHub Actions self-hosted runner keep-alive setup"
need_root

if [[ -z "${RUNNER_DIR_INPUT}" ]]; then
  echo "ERROR: RUNNER_DIR not provided."
  echo "Usage: sudo $0 /path/to/actions-runner"
  echo "   or: sudo RUNNER_DIR=/path/to/actions-runner $0"
  exit 1
fi

RUNNER_DIR="$(abs_path "${RUNNER_DIR_INPUT}")"

echo "    RUNNER_DIR=${RUNNER_DIR}"
echo "    DISABLE_SLEEP=${DISABLE_SLEEP}"
echo "    ENABLE_NET_KEEPALIVE=${ENABLE_NET_KEEPALIVE}"
echo "    NET_KEEPALIVE_HOST=${NET_KEEPALIVE_HOST}"
echo

if [[ ! -d "$RUNNER_DIR" ]]; then
  echo "ERROR: Runner directory not found: $RUNNER_DIR"
  exit 1
fi

if [[ ! -f "$RUNNER_DIR/svc.sh" || ! -f "$RUNNER_DIR/run.sh" ]]; then
  echo "ERROR: $RUNNER_DIR does not look like a GitHub runner directory."
  echo "Expected svc.sh and run.sh in that folder."
  exit 1
fi

# Make sure scripts are executable
chmod +x "$RUNNER_DIR"/*.sh || true

# =========================
# 1) Install & start runner as a service
# =========================
echo "==> Installing runner service (via svc.sh)"
cd "$RUNNER_DIR"
./svc.sh install
./svc.sh start || true

# Detect service name(s)
# Runner service names look like: actions.runner.<scope>.<name>.service
echo "==> Detecting installed runner systemd service(s)..."
mapfile -t RUNNER_SERVICES < <(systemctl list-unit-files --type=service \
  | awk '{print $1}' \
  | grep -E '^actions\.runner\..*\.service$' || true)

if [[ "${#RUNNER_SERVICES[@]}" -eq 0 ]]; then
  echo "ERROR: Could not find any actions.runner.*.service unit files."
  echo "Check install output above. Try:"
  echo "  systemctl list-unit-files | grep actions.runner"
  exit 1
fi

echo "Found runner service(s):"
printf "  - %s\n" "${RUNNER_SERVICES[@]}"

# If multiple, pick the one that is active; otherwise first
RUNNER_SERVICE=""
for s in "${RUNNER_SERVICES[@]}"; do
  if systemctl is-active --quiet "$s"; then
    RUNNER_SERVICE="$s"
    break
  fi
done
if [[ -z "$RUNNER_SERVICE" ]]; then
  RUNNER_SERVICE="${RUNNER_SERVICES[0]}"
fi

echo "==> Using runner service: $RUNNER_SERVICE"

# Ensure enabled at boot
systemctl enable "$RUNNER_SERVICE" >/dev/null 2>&1 || true

echo "==> Runner service status:"
systemctl status "$RUNNER_SERVICE" --no-pager || true

# =========================
# 2) Disable sleep/hibernate (optional)
# =========================
if [[ "$DISABLE_SLEEP" == "true" ]]; then
  echo "==> Disabling sleep/suspend/hibernate targets"
  systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target >/dev/null 2>&1 || true
fi

# =========================
# 3) Watchdog service + timer (restarts runner if down)
# =========================
echo "==> Creating watchdog service + timer"

cat >/etc/systemd/system/actions-runner-watchdog.service <<EOF
[Unit]
Description=Watchdog for GitHub Actions runner (restart if down)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/bin/bash -lc 'systemctl is-active --quiet ${RUNNER_SERVICE} || systemctl restart ${RUNNER_SERVICE}'
EOF

cat >/etc/systemd/system/actions-runner-watchdog.timer <<EOF
[Unit]
Description=Run GitHub Actions runner watchdog every 30s

[Timer]
OnBootSec=30s
OnUnitActiveSec=30s
AccuracySec=1s
Unit=actions-runner-watchdog.service

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now actions-runner-watchdog.timer

echo "==> Watchdog timer status:"
systemctl status actions-runner-watchdog.timer --no-pager || true

# =========================
# 4) Optional network keepalive timer (ping)
# =========================
if [[ "$ENABLE_NET_KEEPALIVE" == "true" ]]; then
  echo "==> Creating network keepalive (ping ${NET_KEEPALIVE_HOST})"

  cat >/etc/systemd/system/net-keepalive.service <<EOF
[Unit]
Description=Network keepalive ping

[Service]
Type=oneshot
ExecStart=/usr/bin/bash -lc 'ping -c 1 ${NET_KEEPALIVE_HOST} >/dev/null 2>&1 || true'
EOF

  cat >/etc/systemd/system/net-keepalive.timer <<EOF
[Unit]
Description=Run network keepalive every 60s

[Timer]
OnBootSec=60s
OnUnitActiveSec=60s
AccuracySec=5s
Unit=net-keepalive.service

[Install]
WantedBy=timers.target
EOF

  systemctl daemon-reload
  systemctl enable --now net-keepalive.timer

  echo "==> Network keepalive timer status:"
  systemctl status net-keepalive.timer --no-pager || true
fi

# =========================
# 5) Summary / verify
# =========================
echo
echo "==> DONE ✅"
echo "Runner service: $RUNNER_SERVICE"
echo
echo "Quick checks:"
echo "  systemctl status $RUNNER_SERVICE --no-pager"
echo "  systemctl status actions-runner-watchdog.timer --no-pager"
echo "  systemctl list-timers --all | grep -E 'actions-runner-watchdog|net-keepalive'"
echo "  journalctl -u $RUNNER_SERVICE -n 200 --no-pager"
