#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: infisical_resolve.sh <ref>" >&2
  exit 2
fi

ref="$1"
if [[ "$ref" != infisical://* ]]; then
  echo "unsupported ref: $ref" >&2
  exit 2
fi

suffix="${ref#infisical://}"
key="INFISICAL_MOCK_$(echo "$suffix" | tr '[:lower:]/.-' '[:upper:]___')"

if [[ -n "${!key:-}" ]]; then
  printf '%s\n' "${!key}"
  exit 0
fi

if command -v infisical >/dev/null 2>&1; then
  # Expected format: infisical://project/path/to/secret
  project="${suffix%%/*}"
  secret_path="${suffix#*/}"
  infisical secrets get "$secret_path" --project "$project" --plain 2>/dev/null && exit 0
fi

echo "failed to resolve secret $ref (set $key or install infisical CLI)" >&2
exit 1
