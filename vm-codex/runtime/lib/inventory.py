from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .common import load_yaml


def load_inventory(root: Path) -> Dict[str, Any]:
    inv = load_yaml(root / "vm-codex" / "inventory" / "targets.yaml")
    targets = inv.get("targets", [])
    groups = inv.get("groups", [])
    return {
        "schema_version": inv.get("schema_version", 1),
        "targets": targets,
        "groups": groups,
    }


def list_targets(inventory: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(inventory.get("targets", []))


def get_target(inventory: Dict[str, Any], target_id: str) -> Dict[str, Any]:
    for target in inventory.get("targets", []):
        if target.get("target_id") == target_id:
            return target
    raise KeyError(f"Unknown target_id: {target_id}")


def list_groups(inventory: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(inventory.get("groups", []))


def _match_group(target: Dict[str, Any], group: Dict[str, Any]) -> bool:
    labels = set(target.get("labels", []))
    all_req = set(group.get("match_labels_all", []))
    any_req = set(group.get("match_labels_any", []))
    target_ids = set(group.get("target_ids", []))

    if target_ids and target.get("target_id") in target_ids:
        return True
    if all_req and not all_req.issubset(labels):
        return False
    if any_req and not labels.intersection(any_req):
        return False
    if all_req or any_req:
        return True
    return False


def resolve_group_targets(inventory: Dict[str, Any], group_name: str) -> List[Dict[str, Any]]:
    groups = inventory.get("groups", [])
    targets = inventory.get("targets", [])

    group = next((g for g in groups if g.get("name") == group_name), None)
    if group is None:
        # fallback: group name can also be a label
        matched = [t for t in targets if group_name in set(t.get("labels", []))]
        if not matched:
            raise KeyError(f"Unknown group: {group_name}")
        return matched

    matched = [target for target in targets if _match_group(target, group)]
    return matched


def load_aliases(root: Path) -> Dict[str, Any]:
    return load_yaml(root / "vm-codex" / "inventory" / "aliases.yaml")


def list_aliases(root: Path) -> List[Dict[str, Any]]:
    data = load_aliases(root)
    return list(data.get("aliases", []))


def get_alias(root: Path, alias_name: str) -> Dict[str, Any]:
    data = load_aliases(root)
    for item in data.get("aliases", []):
        if item.get("alias") == alias_name:
            return item
    raise KeyError(f"Unknown alias: {alias_name}")


def resolve_alias_selector(inventory: Dict[str, Any], selector: str) -> Dict[str, Any]:
    if selector.startswith("target_id="):
        target_id = selector.split("=", 1)[1]
        return {"mode": "target", "targets": [get_target(inventory, target_id)]}
    if selector.startswith("group="):
        group_name = selector.split("=", 1)[1]
        return {"mode": "group", "targets": resolve_group_targets(inventory, group_name), "group": group_name}
    raise ValueError(f"Unsupported alias selector: {selector}")
