#!/usr/bin/env python3
import copy
import difflib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class ConfigPaths:
    repo_root: Path
    vm_configs_dir: Path
    machines_path: Path
    operations_path: Path
    rules_path: Path


@dataclass
class ConfigBundle:
    machines_doc: Dict[str, Any]
    operations_doc: Dict[str, Any]
    rules_doc: Dict[str, Any]
    machines_text: str
    operations_text: str
    rules_text: str


class ConfigStoreError(Exception):
    pass


def find_repo_root(start: Optional[Path] = None) -> Path:
    current = (start or Path(__file__).resolve()).resolve()
    candidates = [current] + list(current.parents)
    for candidate in candidates:
        if (candidate / "runtime" / "vmcx").exists() and (candidate / "vm-configs").exists():
            return candidate
    raise ConfigStoreError("Could not locate repo root (expected runtime/vmcx and vm-configs)")


def get_paths(repo_root: Optional[Path] = None) -> ConfigPaths:
    root = (repo_root or find_repo_root()).resolve()
    cfg_dir = root / "vm-configs"
    return ConfigPaths(
        repo_root=root,
        vm_configs_dir=cfg_dir,
        machines_path=cfg_dir / "vm-machines.yaml",
        operations_path=cfg_dir / "vm-operations.yaml",
        rules_path=cfg_dir / "vm-env-rules.yaml",
    )


def _read_json_doc(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise ConfigStoreError(f"Missing config file: {path}")
    raw = path.read_text(encoding="utf-8")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigStoreError(f"Invalid JSON-compatible YAML in {path}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ConfigStoreError(f"Top-level object must be a map: {path}")
    return parsed


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def dump_doc(doc: Dict[str, Any]) -> str:
    return json.dumps(doc, indent=2, sort_keys=False) + "\n"


def load_bundle(paths: ConfigPaths) -> ConfigBundle:
    machines_doc = _read_json_doc(paths.machines_path)
    operations_doc = _read_json_doc(paths.operations_path)
    rules_doc = _read_json_doc(paths.rules_path)

    machines_doc.setdefault("machines", {})
    machines_doc.setdefault("groups", {})
    operations_doc.setdefault("operations", {})
    rules_doc.setdefault("rules", {})

    for key, doc in [
        ("machines", machines_doc),
        ("groups", machines_doc),
        ("operations", operations_doc),
        ("rules", rules_doc),
    ]:
        if not isinstance(doc.get(key), dict):
            raise ConfigStoreError(f"{key} must be a map")

    return ConfigBundle(
        machines_doc=machines_doc,
        operations_doc=operations_doc,
        rules_doc=rules_doc,
        machines_text=_read_text(paths.machines_path),
        operations_text=_read_text(paths.operations_path),
        rules_text=_read_text(paths.rules_path),
    )


def clone_bundle(bundle: ConfigBundle) -> ConfigBundle:
    return ConfigBundle(
        machines_doc=copy.deepcopy(bundle.machines_doc),
        operations_doc=copy.deepcopy(bundle.operations_doc),
        rules_doc=copy.deepcopy(bundle.rules_doc),
        machines_text=bundle.machines_text,
        operations_text=bundle.operations_text,
        rules_text=bundle.rules_text,
    )


def _write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def save_bundle(paths: ConfigPaths, bundle: ConfigBundle, parts: Iterable[str]) -> None:
    selected = set(parts)
    if "machines" in selected:
        _write_atomic(paths.machines_path, dump_doc(bundle.machines_doc))
    if "operations" in selected:
        _write_atomic(paths.operations_path, dump_doc(bundle.operations_doc))
    if "rules" in selected:
        _write_atomic(paths.rules_path, dump_doc(bundle.rules_doc))


def render_diff(old_text: str, new_text: str, label: str) -> str:
    if old_text == new_text:
        return "No changes."
    diff = difflib.unified_diff(
        old_text.splitlines(),
        new_text.splitlines(),
        fromfile=f"{label} (current)",
        tofile=f"{label} (proposed)",
        lineterm="",
    )
    return "\n".join(diff)


def split_csv_values(raw: str) -> List[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def parse_json_field(raw: str, default: Any) -> Any:
    text = (raw or "").strip()
    if not text:
        return copy.deepcopy(default)
    value = json.loads(text)
    return value


def build_groups_from_machines(machines: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
    groups: Dict[str, List[str]] = {}
    for machine_id, machine in machines.items():
        raw_groups = machine.get("groups", [])
        if not isinstance(raw_groups, list):
            continue
        for group_name in [str(g) for g in raw_groups if str(g).strip()]:
            groups.setdefault(group_name, [])
            if machine_id not in groups[group_name]:
                groups[group_name].append(machine_id)
    return groups


def upsert_machine(
    bundle: ConfigBundle,
    machine_id: str,
    machine_payload: Dict[str, Any],
    original_machine_id: Optional[str] = None,
) -> None:
    machines = bundle.machines_doc.setdefault("machines", {})
    if not isinstance(machines, dict):
        raise ConfigStoreError("machines must be a map")

    if original_machine_id and original_machine_id != machine_id:
        raise ConfigStoreError("Renaming machine_id is not supported. Delete and recreate instead.")

    machines[machine_id] = machine_payload
    bundle.machines_doc["groups"] = build_groups_from_machines(machines)


def delete_machine(bundle: ConfigBundle, machine_id: str) -> None:
    machines = bundle.machines_doc.setdefault("machines", {})
    if machine_id in machines:
        del machines[machine_id]
    bundle.machines_doc["groups"] = build_groups_from_machines(machines)


def upsert_operation(
    bundle: ConfigBundle,
    operation_id: str,
    operation_payload: Dict[str, Any],
    original_operation_id: Optional[str] = None,
) -> None:
    operations = bundle.operations_doc.setdefault("operations", {})
    if not isinstance(operations, dict):
        raise ConfigStoreError("operations must be a map")

    if original_operation_id and original_operation_id != operation_id:
        raise ConfigStoreError("Renaming operation_id is not supported. Delete and recreate instead.")

    operations[operation_id] = operation_payload


def delete_operation(bundle: ConfigBundle, operation_id: str) -> None:
    operations = bundle.operations_doc.setdefault("operations", {})
    if operation_id in operations:
        del operations[operation_id]


def upsert_rule(
    bundle: ConfigBundle,
    setup_id: str,
    rule_payload: Dict[str, Any],
    original_setup_id: Optional[str] = None,
) -> None:
    rules = bundle.rules_doc.setdefault("rules", {})
    if not isinstance(rules, dict):
        raise ConfigStoreError("rules must be a map")

    if original_setup_id and original_setup_id != setup_id:
        raise ConfigStoreError("Renaming setup_id is not supported. Delete and recreate instead.")

    rules[setup_id] = rule_payload


def delete_rule(bundle: ConfigBundle, setup_id: str) -> None:
    rules = bundle.rules_doc.setdefault("rules", {})
    if setup_id in rules:
        del rules[setup_id]
