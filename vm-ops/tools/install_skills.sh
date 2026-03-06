#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
skills_src="$repo_root/ai-skills"
codex_home="${CODEX_HOME:-$HOME/.codex}"
skills_dst="$codex_home/skills"

mkdir -p "$skills_dst"
cp -R "$skills_src"/* "$skills_dst/"
echo "Installed vm-ops ai-skills to $skills_dst"
