# Proxmox Lid Keepalive

Prevents a Proxmox laptop host from suspending or hibernating when the lid closes. The companion script `proxmox-lid-keepalive.sh` writes systemd drop-ins to ignore lid events, disables sleep/hibernate paths, masks related targets, and restarts `systemd-logind`.

## What it does

- Tells `systemd-logind` to ignore lid switch actions (on AC, docked, or otherwise) and idle actions.
- Creates `/etc/systemd/sleep.conf.d/00-no-suspend.conf` with `AllowSuspend/Hibernation/HybridSleep/SuspendThenHibernate=no`.
- Masks sleep-related targets: `sleep.target`, `suspend.target`, `hibernate.target`, `hybrid-sleep.target`, `suspend-then-hibernate.target`.
- Restarts `systemd-logind` and prints current lid policy plus masked target summary.

## Usage

1. Run on your Proxmox host as root:

   ```bash
   chmod +x "/root/self-hosted-server-apps/Home Server Setup/LID Keep Alive/proxmox-lid-keepalive.sh"
   "/root/self-hosted-server-apps/Home Server Setup/LID Keep Alive/proxmox-lid-keepalive.sh"
```

2. Confirm the prompt. The script creates drop-ins under `/etc/systemd/logind.conf.d/` and `/etc/systemd/sleep.conf.d/`, then masks the sleep targets.
3. Close the lid and ensure the host stays reachable (no suspend/hibernate).

## Verify

- Check effective policies:

  ```bash
  loginctl show-logind -p HandleLidSwitch -p HandleLidSwitchExternalPower -p HandleLidSwitchDocked -p IdleAction
  systemctl list-unit-files --type=target | grep -E 'sleep|suspend|hibernate'
  ```

## Revert (undo keepalive)

```bash
sudo rm -f /etc/systemd/logind.conf.d/ignore-lid.conf
sudo rm -f /etc/systemd/sleep.conf.d/00-no-suspend.conf
sudo systemctl unmask sleep.target suspend.target hibernate.target hybrid-sleep.target suspend-then-hibernate.target
sudo systemctl restart systemd-logind
```

## Notes

- Requires systemd (default on Proxmox). If `systemctl` is unavailable, the script exits.
- By masking sleep targets and disabling suspend/hibernate, you intentionally lose lid-triggered sleep; unmask to restore normal laptop behavior.
