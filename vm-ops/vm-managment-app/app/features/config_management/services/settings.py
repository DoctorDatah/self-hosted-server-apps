#!/usr/bin/env python3
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from zoneinfo import ZoneInfo, available_timezones


DEFAULT_TIMEZONE = "UTC"
DEFAULT_PREFERRED_CONFIG_BRANCH = ""
OLD_CONFIG_BRANCH_PREFIX = "config_update/update-"
NEW_CONFIG_BRANCH_PREFIX = "config_update/"


class SettingsError(Exception):
    pass


def _normalize_preferred_config_branch(branch_name: str) -> str:
    raw = str(branch_name or "").strip()
    if not raw:
        return ""
    if raw.startswith(OLD_CONFIG_BRANCH_PREFIX):
        stamp = raw[len(OLD_CONFIG_BRANCH_PREFIX) :]
        try:
            parsed = datetime.strptime(stamp, "%Y%m%d-%H%M%S")
        except ValueError:
            return ""
        return f"{NEW_CONFIG_BRANCH_PREFIX}{parsed.strftime('%B-%d-%Y--%I-%M-%p')}"

    if not raw.startswith(NEW_CONFIG_BRANCH_PREFIX):
        return raw

    stamp = raw[len(NEW_CONFIG_BRANCH_PREFIX) :]
    for fmt in ("%B-%d-%Y--%I-%M-%p", "%B-%d-%Y--%I-%M%p", "%B-%d-%Y--%I:%M:%p"):
        try:
            parsed = datetime.strptime(stamp, fmt)
            return f"{NEW_CONFIG_BRANCH_PREFIX}{parsed.strftime('%B-%d-%Y--%I-%M-%p')}"
        except ValueError:
            continue
    return raw


def _settings_path(repo_root: Path) -> Path:
    return repo_root / "vm-managment-app" / "app-data" / "settings.json"


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _validate_timezone(tz_name: str) -> str:
    value = (tz_name or "").strip() or DEFAULT_TIMEZONE
    try:
        ZoneInfo(value)
    except Exception as exc:  # noqa: BLE001
        raise SettingsError(f"Invalid timezone: {value}") from exc
    return value


def load_settings(repo_root: Path) -> Dict[str, Any]:
    path = _settings_path(repo_root)
    if not path.exists():
        return {
            "timezone": DEFAULT_TIMEZONE,
            "preferred_config_branch": DEFAULT_PREFERRED_CONFIG_BRANCH,
        }

    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "timezone": DEFAULT_TIMEZONE,
            "preferred_config_branch": DEFAULT_PREFERRED_CONFIG_BRANCH,
        }

    if not isinstance(parsed, dict):
        return {
            "timezone": DEFAULT_TIMEZONE,
            "preferred_config_branch": DEFAULT_PREFERRED_CONFIG_BRANCH,
        }

    timezone_name = parsed.get("timezone", DEFAULT_TIMEZONE)
    try:
        parsed["timezone"] = _validate_timezone(str(timezone_name))
    except SettingsError:
        parsed["timezone"] = DEFAULT_TIMEZONE
    current_branch = str(parsed.get("preferred_config_branch", "") or "").strip()
    normalized_branch = _normalize_preferred_config_branch(current_branch)
    parsed["preferred_config_branch"] = normalized_branch

    if normalized_branch != current_branch:
        try:
            _atomic_write(path, json.dumps(parsed, indent=2) + "\n")
        except Exception:
            pass
    return parsed


def get_timezone(repo_root: Path) -> str:
    return str(load_settings(repo_root).get("timezone", DEFAULT_TIMEZONE))


def get_preferred_config_branch(repo_root: Path) -> str:
    return str(load_settings(repo_root).get("preferred_config_branch", "") or "").strip()


def save_settings(
    repo_root: Path,
    timezone_name: str,
    preferred_config_branch: str = "",
) -> Dict[str, Any]:
    payload = {
        "timezone": _validate_timezone(timezone_name),
        "preferred_config_branch": _normalize_preferred_config_branch(str(preferred_config_branch or "").strip()),
    }
    _atomic_write(_settings_path(repo_root), json.dumps(payload, indent=2) + "\n")
    return payload


def save_timezone(repo_root: Path, tz_name: str) -> Dict[str, Any]:
    current = load_settings(repo_root)
    return save_settings(
        repo_root,
        timezone_name=tz_name,
        preferred_config_branch=str(current.get("preferred_config_branch", "") or ""),
    )


def save_preferred_config_branch(repo_root: Path, branch_name: str) -> Dict[str, Any]:
    current = load_settings(repo_root)
    return save_settings(
        repo_root,
        timezone_name=str(current.get("timezone", DEFAULT_TIMEZONE)),
        preferred_config_branch=branch_name,
    )


def all_timezones() -> List[str]:
    return sorted(list(available_timezones()))


def now_in_timezone(tz_name: str) -> datetime:
    return datetime.now(ZoneInfo(_validate_timezone(tz_name)))


def format_iso_datetime(iso_text: str, tz_name: str) -> str:
    raw = (iso_text or "").strip()
    if not raw:
        return "-"
    normalized = raw.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return raw
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    out = dt.astimezone(ZoneInfo(_validate_timezone(tz_name)))
    return out.strftime("%Y-%m-%d %H:%M:%S %Z")
