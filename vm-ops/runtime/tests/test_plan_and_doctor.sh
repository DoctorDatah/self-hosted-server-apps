#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

./runtime/vmcx doctor --ci >/dev/null
./runtime/vmcx plan --alias n8n-app-deploy --exec-mode ssh >/dev/null

echo "runtime smoke tests passed"
