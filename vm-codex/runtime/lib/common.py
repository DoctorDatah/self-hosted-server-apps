from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
from typing import Any, Dict

try:
    import yaml as _yaml
except Exception:  # pragma: no cover
    _yaml = None


class SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8")

    data = None
    if _yaml is not None:
        data = _yaml.safe_load(raw)
    else:
        # Accept JSON-formatted YAML files when PyYAML is unavailable.
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Fallback to Ruby YAML parser for offline environments.
            ruby_program = (
                "require 'yaml'; require 'json'; "
                "obj = YAML.safe_load(File.read(ARGV[0]), aliases: true); "
                "puts JSON.dump(obj)"
            )
            try:
                completed = subprocess.run(
                    ["ruby", "-e", ruby_program, str(path)],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except Exception as exc:  # pragma: no cover
                raise RuntimeError(
                    "Unable to parse YAML. Install PyYAML or ensure Ruby is available."
                ) from exc
            data = json.loads(completed.stdout or "{}")

    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in YAML file: {path}")
    return data


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(base)
    for key, value in override.items():
        if key in out and isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = deepcopy(value)
    return out


def render_template(text: str, context: Dict[str, Any]) -> str:
    return text.format_map(SafeDict(context))


def to_csv(values: Any) -> str:
    if isinstance(values, list):
        return ",".join(str(v) for v in values)
    if values is None:
        return ""
    return str(values)
