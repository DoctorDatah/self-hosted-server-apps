#!/usr/bin/env python3
"""
Quick validation script for Codex skills.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml as _yaml
except Exception:  # pragma: no cover
    _yaml = None

MAX_SKILL_NAME_LENGTH = 64


def validate_skill(skill_path: Path) -> tuple[bool, str]:
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return False, "SKILL.md not found"

    content = skill_md.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return False, "No YAML frontmatter found"

    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return False, "Invalid frontmatter format"

    frontmatter_text = match.group(1)

    if _yaml is not None:
        try:
            frontmatter = _yaml.safe_load(frontmatter_text)
        except Exception as exc:
            return False, f"Invalid YAML in frontmatter: {exc}"
    else:
        # Fallback parser for simple key:value frontmatter when PyYAML is missing.
        frontmatter = {}
        for raw in frontmatter_text.splitlines():
            line = raw.strip()
            if not line or ":" not in line:
                continue
            key, value = line.split(":", 1)
            frontmatter[key.strip()] = value.strip().strip('"').strip("'")

    if not isinstance(frontmatter, dict):
        return False, "Frontmatter must be a YAML dictionary"

    allowed_properties = {"name", "description", "license", "allowed-tools", "metadata"}
    unexpected_keys = set(frontmatter.keys()) - allowed_properties
    if unexpected_keys:
        allowed = ", ".join(sorted(allowed_properties))
        unexpected = ", ".join(sorted(unexpected_keys))
        return (
            False,
            f"Unexpected key(s) in SKILL.md frontmatter: {unexpected}. Allowed properties are: {allowed}",
        )

    if "name" not in frontmatter:
        return False, "Missing 'name' in frontmatter"
    if "description" not in frontmatter:
        return False, "Missing 'description' in frontmatter"

    name = str(frontmatter.get("name", "")).strip()
    if not re.match(r"^[a-z0-9-]+$", name):
        return False, "Name should be hyphen-case (lowercase letters, digits, and hyphens only)"
    if name.startswith("-") or name.endswith("-") or "--" in name:
        return False, "Name cannot start/end with hyphen or contain consecutive hyphens"
    if len(name) > MAX_SKILL_NAME_LENGTH:
        return False, f"Name is too long ({len(name)} characters). Maximum is {MAX_SKILL_NAME_LENGTH}."

    description = str(frontmatter.get("description", "")).strip()
    if not description:
        return False, "Description cannot be empty"
    if "<" in description or ">" in description:
        return False, "Description cannot contain angle brackets (< or >)"
    if len(description) > 1024:
        return False, f"Description is too long ({len(description)} characters). Maximum is 1024."

    return True, "Skill is valid!"


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 vm-codex/tools/quick_validate.py <skill_directory>")
        return 1
    skill_dir = Path(sys.argv[1]).resolve()
    valid, message = validate_skill(skill_dir)
    print(message)
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
