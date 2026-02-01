# GitHub Actions runner keep-alive (systemd watchdog)

This script installs/starts a self-hosted GitHub Actions runner as a systemd service, disables sleep (optional), and adds a watchdog timer so the runner restarts if it dies. It accepts a relative `RUNNER_DIR` (e.g., `./actions-runner`) and resolves it to an absolute path.

- Script: `apps/github-runner/keep-runner-alive.sh`
- Runs on: the machine hosting the runner (Ubuntu/systemd)
- Needs: root (`sudo`)

## Quick start

```bash
chmod +x keep-runner-alive.sh
sudo ./keep-runner-alive.sh ./actions-runner
```

Alternate (env var style):

```bash
sudo env RUNNER_DIR=./actions-runner bash ./keep-runner-alive.sh
```

> Tip: Passing the path as an argument is more reliable than relying on sudo to preserve env vars.

## What it sets up

- Installs and starts the runner service via `svc.sh`.
- Detects the runner unit (chooses the active `actions.runner.*.service`; falls back to the first).
- Enables the runner at boot.
- Optional: masks sleep/hibernate targets (`DISABLE_SLEEP=true`, default).
- Watchdog timer (`actions-runner-watchdog.timer`) that restarts the runner if it is not active.
- Optional network keepalive timer (`net-keepalive.timer`) that pings a host to keep outbound connectivity warm.

## Inputs (env vars)

- `RUNNER_DIR` or first CLI arg: runner folder (can be relative).
- `DISABLE_SLEEP` (default `true`): mask sleep/hibernate targets.
- `ENABLE_NET_KEEPALIVE` (default `true`): create ping timer.
- `NET_KEEPALIVE_HOST` (default `github.com`): host to ping.

Example with tweaks:

```bash
sudo DISABLE_SLEEP=false ENABLE_NET_KEEPALIVE=true NET_KEEPALIVE_HOST=1.1.1.1 \
  ./keep-runner-alive.sh ./actions-runner
```

## Verify it’s online

```bash
systemctl status actions.runner.* --no-pager
systemctl status actions-runner-watchdog.timer --no-pager
systemctl list-timers --all | grep -E 'actions-runner-watchdog|net-keepalive'
journalctl -u actions.runner.* -n 200 --no-pager
```

## Common fixes

- Runner shows “Offline” in GitHub: ensure sleep is masked and the service is active:

  ```bash
  systemctl is-active actions.runner.*
  sudo systemctl restart actions.runner.*
  ```

- Multiple runners on the same host: the script picks the active one; pass a specific unit to `systemctl restart <unit>` if you want to target a different runner.

## Notes

- Requires systemd; if `systemctl` is missing, the script exits.
- The watchdog/keepalive timers live under `/etc/systemd/system/` and are enabled automatically.
