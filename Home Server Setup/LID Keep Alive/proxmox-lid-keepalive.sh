#!/usr/bin/env bash
set -euo pipefail

say(){ echo -e "\n==> $*"; }
ok(){ echo "[OK] $*"; }
warn(){ echo "[WARN] $*"; }
die(){ echo "[ERROR] $*" >&2; exit 1; }

need_root(){
  [[ "${EUID}" -eq 0 ]] || die "Run as root (sudo)."
}

ask_yes_no(){
  local __var="$1" __prompt="$2" __default="$3" reply
  local hint
  if [[ "${__default,,}" == "y" ]]; then
    hint="Y/n"
  else
    hint="y/N"
  fi
  read -r -p "$__prompt [$hint]: " reply
  reply="${reply:-$__default}"
  case "${reply,,}" in
    y|yes) printf -v "$__var" "y" ;;
    n|no)  printf -v "$__var" "n" ;;
    *)     die "Please answer y or n." ;;
  esac
}

write_file(){
  local path="$1" content="$2"
  local dir
  dir="$(dirname "$path")"
  mkdir -p "$dir"
  printf "%s" "$content" >"$path"
}

LOGIND_DROPIN="/etc/systemd/logind.conf.d/ignore-lid.conf"
SLEEP_DROPIN="/etc/systemd/sleep.conf.d/00-no-suspend.conf"
MASK_TARGETS=(sleep.target suspend.target hibernate.target hybrid-sleep.target suspend-then-hibernate.target)

need_root
command -v systemctl >/dev/null 2>&1 || die "systemctl not found (are you on systemd/Proxmox?)."

echo "Proxmox Keepalive: ignore laptop lid + block suspend/hibernate"
echo "This will:"
echo " - Tell systemd-logind to ignore lid close events"
echo " - Disable suspend/hibernate paths"
echo " - Mask sleep-related systemd targets for extra safety"
ask_yes_no CONTINUE "Proceed?" "y"
[[ "$CONTINUE" == "y" ]] || die "Aborted."

# ---------- logind lid handling ----------
say "Configuring systemd-logind lid handling"
write_file "$LOGIND_DROPIN" "\
[Login]
HandleLidSwitch=ignore
HandleLidSwitchExternalPower=ignore
HandleLidSwitchDocked=ignore
IdleAction=ignore
LidSwitchIgnoreInhibited=no
"
ok "Wrote $LOGIND_DROPIN"

# ---------- sleep/hibernate policies ----------
say "Disabling suspend/hibernate entries in systemd-sleep"
write_file "$SLEEP_DROPIN" "\
[Sleep]
AllowSuspend=no
AllowHibernation=no
AllowHybridSleep=no
AllowSuspendThenHibernate=no
SuspendState=
HibernateState=
HybridSleepState=
"
ok "Wrote $SLEEP_DROPIN"

# ---------- mask dangerous targets ----------
say "Masking sleep-related targets (prevents accidental activation)"
for t in "${MASK_TARGETS[@]}"; do
  systemctl mask "$t" >/dev/null 2>&1 && ok "Masked $t" || warn "Could not mask $t"
done

# ---------- reload services ----------
say "Reloading systemd-logind to apply changes"
systemctl restart systemd-logind || warn "Could not restart systemd-logind (restart manually if needed)"

# ---------- status summary ----------
if command -v loginctl >/dev/null 2>&1; then
  say "Current logind lid policy (loginctl show-logind)"
  loginctl show-logind -p HandleLidSwitch -p HandleLidSwitchExternalPower -p HandleLidSwitchDocked -p IdleAction 2>/dev/null || true
fi

say "Target masks (systemctl list-unit-files | grep -E 'sleep|suspend')"
systemctl list-unit-files --type=target 2>/dev/null | grep -E 'sleep|suspend|hibernate' || true

say "Done. Close the lid to confirm Proxmox stays online."
