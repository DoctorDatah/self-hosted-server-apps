#!/usr/bin/env python3
import hashlib
import json
import os
import shutil
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from . import config_store


class BackupError(Exception):
    pass


def _backup_root(repo_root: Path) -> Path:
    # Backups are intentionally git-tracked so operators can commit them.
    return repo_root / "vm-configs" / "config-backups"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _backup_id(tz_name: str = "UTC") -> str:
    try:
        now = datetime.now(ZoneInfo((tz_name or "").strip() or "UTC"))
    except Exception:
        now = _now_utc()
    suffix = uuid.uuid4().hex[:6]
    return f"cfg-{now.strftime('%B-%d-%Y--%I-%M-%p')}-{suffix}"


def _status_file(paths: config_store.ConfigPaths) -> Path:
    return _backup_root(paths.repo_root) / "status.json"


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


def _backup_files(paths: config_store.ConfigPaths) -> Dict[str, Path]:
    files: Dict[str, Path] = {
        "vm-machines.yaml": paths.machines_path,
    }
    if paths.operations_path.exists():
        files["vm-operations.yaml"] = paths.operations_path
    if paths.rules_path.exists():
        files["vm-env-rules.yaml"] = paths.rules_path
    return files


def _hash_payload(parts: List[tuple[str, str]]) -> str:
    h = hashlib.sha256()
    for name, text in parts:
        h.update(name.encode("utf-8"))
        h.update(b"\n")
        h.update(text.encode("utf-8"))
        h.update(b"\n---\n")
    return h.hexdigest()


def _current_config_fingerprint(paths: config_store.ConfigPaths) -> str:
    files = _backup_files(paths)
    parts: List[tuple[str, str]] = []
    for name, path in files.items():
        if not path.exists():
            raise BackupError(f"Missing config file for fingerprint: {path}")
        parts.append((name, path.read_text(encoding="utf-8")))
    return _hash_payload(parts)


def _backup_dir_fingerprint(backup_dir: Path) -> str:
    names = [name for name in ["vm-machines.yaml", "vm-operations.yaml", "vm-env-rules.yaml"] if (backup_dir / name).exists()]
    if not names:
        return ""
    parts: List[tuple[str, str]] = []
    for name in names:
        fp = backup_dir / name
        parts.append((name, fp.read_text(encoding="utf-8")))
    return _hash_payload(parts)


def _load_status(paths: config_store.ConfigPaths) -> Dict[str, Any]:
    status_path = _status_file(paths)
    if not status_path.exists():
        return {}
    try:
        data = json.loads(status_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def _save_status(paths: config_store.ConfigPaths, payload: Dict[str, Any]) -> None:
    _atomic_write(_status_file(paths), json.dumps(payload, indent=2) + "\n")


def create_backup(
    paths: config_store.ConfigPaths,
    label: str = "",
    remark: str = "",
    tz_name: str = "UTC",
) -> Dict[str, Any]:
    root = _backup_root(paths.repo_root)
    root.mkdir(parents=True, exist_ok=True)

    backup_id = _backup_id(tz_name=tz_name)
    backup_dir = root / backup_id
    backup_dir.mkdir(parents=True, exist_ok=False)

    files = _backup_files(paths)
    captured: List[Dict[str, Any]] = []
    for name, src in files.items():
        if not src.exists():
            raise BackupError(f"Cannot backup missing config file: {src}")
        text = src.read_text(encoding="utf-8")
        (backup_dir / name).write_text(text, encoding="utf-8")
        captured.append(
            {
                "name": name,
                "bytes": len(text.encode("utf-8")),
                "source": str(src.relative_to(paths.repo_root)),
            }
        )

    now = _now_utc()
    config_fingerprint = _current_config_fingerprint(paths)
    metadata = {
        "backup_id": backup_id,
        "created_at": now.isoformat(),
        "created_at_epoch": int(now.timestamp()),
        "label": (label or "").strip(),
        "remark": (remark or "").strip(),
        "config_fingerprint": config_fingerprint,
        "files": captured,
    }
    (backup_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    status_doc = _load_status(paths)
    status_doc["last_backup"] = {
        "backup_id": backup_id,
        "created_at": metadata["created_at"],
        "created_at_epoch": metadata["created_at_epoch"],
        "label": metadata["label"],
        "remark": metadata["remark"],
        "config_fingerprint": config_fingerprint,
    }
    _save_status(paths, status_doc)
    return metadata


def _load_metadata(path: Path) -> Dict[str, Any]:
    meta_path = path / "metadata.json"
    if not meta_path.exists():
        ts = int(path.stat().st_mtime)
        return {
            "backup_id": path.name,
            "created_at": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
            "created_at_epoch": ts,
            "label": "",
            "remark": "",
            "files": [],
        }

    try:
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BackupError(f"Invalid backup metadata: {meta_path}: {exc}") from exc

    if not isinstance(metadata, dict):
        raise BackupError(f"Backup metadata must be an object: {meta_path}")

    metadata.setdefault("backup_id", path.name)
    metadata.setdefault("created_at_epoch", int(path.stat().st_mtime))
    metadata.setdefault(
        "created_at",
        datetime.fromtimestamp(int(metadata["created_at_epoch"]), tz=timezone.utc).isoformat(),
    )
    metadata.setdefault("label", "")
    metadata.setdefault("remark", "")
    metadata.setdefault("config_fingerprint", "")
    metadata.setdefault("files", [])
    metadata["label"] = str(metadata.get("label", "") or "")
    metadata["remark"] = str(metadata.get("remark", "") or "")
    try:
        metadata["created_at_epoch"] = int(metadata.get("created_at_epoch", 0))
    except Exception:
        metadata["created_at_epoch"] = int(path.stat().st_mtime)
    if not metadata.get("config_fingerprint"):
        metadata["config_fingerprint"] = _backup_dir_fingerprint(path)
    return metadata


def _day_range(date_str: str, tz_name: str = "UTC") -> Tuple[int, int]:
    try:
        day = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=ZoneInfo(tz_name))
    except ValueError as exc:
        raise BackupError(f"Invalid date format '{date_str}'. Expected YYYY-MM-DD.") from exc
    start = int(day.astimezone(timezone.utc).timestamp())
    end = int((day + timedelta(days=1)).astimezone(timezone.utc).timestamp()) - 1
    return (start, end)


def list_backups(
    paths: config_store.ConfigPaths,
    label_query: str = "",
    date_exact: str = "",
    date_from: str = "",
    date_to: str = "",
    last_n: Optional[int] = None,
    tz_name: str = "UTC",
) -> List[Dict[str, Any]]:
    root = _backup_root(paths.repo_root)
    if not root.exists():
        return []

    records: List[Dict[str, Any]] = []
    for child in root.iterdir():
        if not child.is_dir():
            continue
        try:
            metadata = _load_metadata(child)
            metadata["backup_path"] = str(child.relative_to(paths.repo_root))
            records.append(metadata)
        except BackupError:
            continue

    records.sort(
        key=lambda x: (int(x.get("created_at_epoch", 0)), str(x.get("backup_id", ""))),
        reverse=True,
    )

    query = (label_query or "").strip().lower()
    if query:
        records = [
            r
            for r in records
            if query in str(r.get("label", "")).lower()
            or query in str(r.get("backup_id", "")).lower()
            or query in str(r.get("remark", "")).lower()
        ]

    if date_exact:
        start, end = _day_range(date_exact, tz_name=tz_name)
        records = [r for r in records if start <= int(r.get("created_at_epoch", 0)) <= end]
    else:
        if date_from:
            start, _ = _day_range(date_from, tz_name=tz_name)
            records = [r for r in records if int(r.get("created_at_epoch", 0)) >= start]
        if date_to:
            _, end = _day_range(date_to, tz_name=tz_name)
            records = [r for r in records if int(r.get("created_at_epoch", 0)) <= end]

    if last_n is not None and last_n > 0:
        records = records[:last_n]

    return records


def delete_backup(paths: config_store.ConfigPaths, backup_id: str) -> Dict[str, Any]:
    bid = (backup_id or "").strip()
    if not bid:
        raise BackupError("backup_id is required")
    if Path(bid).name != bid or "/" in bid or "\\" in bid:
        raise BackupError("backup_id contains invalid path characters")

    root = _backup_root(paths.repo_root)
    backup_dir = root / bid
    if not backup_dir.exists() or not backup_dir.is_dir():
        raise BackupError(f"Backup not found: {bid}")

    removed_files = 0
    for child in backup_dir.rglob("*"):
        if child.is_file():
            removed_files += 1

    shutil.rmtree(backup_dir)

    status_doc = _load_status(paths)
    changed = False
    last_backup = status_doc.get("last_backup", {})
    if isinstance(last_backup, dict) and str(last_backup.get("backup_id", "")) == bid:
        status_doc.pop("last_backup", None)
        changed = True
    last_restore = status_doc.get("last_restore", {})
    if isinstance(last_restore, dict) and str(last_restore.get("backup_id", "")) == bid:
        status_doc.pop("last_restore", None)
        changed = True
    if changed:
        _save_status(paths, status_doc)

    return {
        "backup_id": bid,
        "removed_path": str(backup_dir.relative_to(paths.repo_root)),
        "removed_files": removed_files,
    }


def cleanup_backups_before_last_n(paths: config_store.ConfigPaths, keep_last_n: int) -> Dict[str, Any]:
    keep_n = int(keep_last_n)
    if keep_n <= 0:
        raise BackupError("keep_last_n must be greater than 0")

    all_records = list_backups(paths)
    total_before = len(all_records)
    if total_before <= keep_n:
        return {
            "keep_last_n": keep_n,
            "total_before": total_before,
            "total_after": total_before,
            "deleted_count": 0,
            "deleted_backup_ids": [],
        }

    to_delete = all_records[keep_n:]
    deleted_ids: List[str] = []
    for record in to_delete:
        bid = str(record.get("backup_id", "")).strip()
        if not bid:
            continue
        root = _backup_root(paths.repo_root)
        backup_dir = root / bid
        if backup_dir.exists() and backup_dir.is_dir():
            shutil.rmtree(backup_dir)
            deleted_ids.append(bid)

    status_doc = _load_status(paths)
    changed = False
    remaining = list_backups(paths)
    remaining_ids = {str(x.get("backup_id", "")).strip() for x in remaining}

    last_backup = status_doc.get("last_backup", {})
    if isinstance(last_backup, dict):
        lbid = str(last_backup.get("backup_id", "")).strip()
        if lbid and lbid not in remaining_ids:
            if remaining:
                latest = remaining[0]
                status_doc["last_backup"] = {
                    "backup_id": latest.get("backup_id", ""),
                    "created_at": latest.get("created_at", ""),
                    "created_at_epoch": int(latest.get("created_at_epoch", 0) or 0),
                    "label": latest.get("label", ""),
                    "remark": latest.get("remark", ""),
                    "config_fingerprint": latest.get("config_fingerprint", ""),
                }
            else:
                status_doc.pop("last_backup", None)
            changed = True

    last_restore = status_doc.get("last_restore", {})
    if isinstance(last_restore, dict):
        lrid = str(last_restore.get("backup_id", "")).strip()
        if lrid and lrid not in remaining_ids:
            status_doc.pop("last_restore", None)
            changed = True

    if changed:
        _save_status(paths, status_doc)

    return {
        "keep_last_n": keep_n,
        "total_before": total_before,
        "total_after": len(remaining),
        "deleted_count": len(deleted_ids),
        "deleted_backup_ids": deleted_ids,
    }


def restore_backup(paths: config_store.ConfigPaths, backup_id: str) -> Dict[str, Any]:
    bid = (backup_id or "").strip()
    if not bid:
        raise BackupError("backup_id is required")

    root = _backup_root(paths.repo_root)
    backup_dir = root / bid
    if not backup_dir.exists() or not backup_dir.is_dir():
        raise BackupError(f"Backup not found: {bid}")

    files = _backup_files(paths)
    staged: Dict[str, str] = {}
    # vm-machines.yaml remains the only mandatory file.
    required_names = ["vm-machines.yaml"]
    optional_names = ["vm-operations.yaml", "vm-env-rules.yaml"]
    names_to_restore: List[str] = []
    for name in required_names:
        src = backup_dir / name
        if not src.exists():
            raise BackupError(f"Backup is missing required file: {name}")
        names_to_restore.append(name)
    for name in optional_names:
        if (backup_dir / name).exists():
            names_to_restore.append(name)

    for name in names_to_restore:
        src = backup_dir / name
        text = src.read_text(encoding="utf-8")
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise BackupError(f"Backup file is invalid JSON-compatible YAML: {name}: {exc}") from exc
        if not isinstance(parsed, dict):
            raise BackupError(f"Backup file top-level must be an object: {name}")
        staged[name] = text

    destination_map = {
        "vm-machines.yaml": paths.machines_path,
        "vm-operations.yaml": paths.operations_path,
        "vm-env-rules.yaml": paths.rules_path,
    }
    restored_paths: List[Path] = []
    for name in names_to_restore:
        dest = destination_map[name]
        _atomic_write(dest, staged[name])
        restored_paths.append(dest)

    metadata = _load_metadata(backup_dir)
    restored_at = _now_utc()
    status_doc = _load_status(paths)
    status_doc["last_restore"] = {
        "backup_id": metadata.get("backup_id", bid),
        "restored_at": restored_at.isoformat(),
        "restored_at_epoch": int(restored_at.timestamp()),
        "label": metadata.get("label", ""),
        "remark": metadata.get("remark", ""),
        "config_fingerprint": metadata.get("config_fingerprint", ""),
    }
    _save_status(paths, status_doc)

    return {
        "backup": metadata,
        "restored_files": [str(path.relative_to(paths.repo_root)) for path in restored_paths],
    }


def get_backup_status(paths: config_store.ConfigPaths) -> Dict[str, Any]:
    records = list_backups(paths)
    status_doc = _load_status(paths)

    try:
        current_fingerprint = _current_config_fingerprint(paths)
    except BackupError:
        current_fingerprint = ""

    latest = records[0] if records else None
    matching = [
        r
        for r in records
        if r.get("config_fingerprint") and r.get("config_fingerprint") == current_fingerprint
    ]
    latest_matching = matching[0] if matching else None

    last_restore = status_doc.get("last_restore", {})
    if not isinstance(last_restore, dict):
        last_restore = {}

    if not records:
        state = "not_backed_up"
        summary = "Current configuration has not been backed up yet."
    elif latest_matching:
        restored_id = str(last_restore.get("backup_id", "")).strip()
        if restored_id and restored_id == str(latest_matching.get("backup_id", "")):
            state = "backed_up_restored"
            summary = f"Configuration matches restored backup {restored_id}."
        else:
            state = "backed_up"
            summary = f"Configuration is backed up (matching backup: {latest_matching.get('backup_id', '-')})."
    else:
        state = "not_backed_up"
        summary = "Configuration changed since the last matching backup. Create a new backup."

    return {
        "state": state,
        "summary": summary,
        "latest_backup_id": latest.get("backup_id") if latest else None,
        "latest_backup_created_at": latest.get("created_at") if latest else None,
        "latest_matching_backup_id": latest_matching.get("backup_id") if latest_matching else None,
        "latest_matching_backup_created_at": latest_matching.get("created_at") if latest_matching else None,
        "last_restore_backup_id": last_restore.get("backup_id"),
        "last_restore_at": last_restore.get("restored_at"),
    }
