#!/usr/bin/env python3
import json
from pathlib import Path
from typing import Any, Dict


class ConfigError(Exception):
    pass


def load_data_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"Missing file: {path}")
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"{path} is not valid JSON-compatible YAML. "
            "This scaffold expects .yaml files to use JSON syntax."
        ) from exc
    if not isinstance(data, dict):
        raise ConfigError(f"Top-level object must be a map: {path}")
    return data


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, data: Dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged
