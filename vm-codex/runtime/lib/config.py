from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .common import deep_merge, load_yaml


def resolve_effective_config(root: Path, target: Dict[str, Any], alias_defaults: Dict[str, Any] | None = None) -> Dict[str, Any]:
    alias_defaults = alias_defaults or {}

    base_name = target.get("base_profile", "default")
    role_overlay = target.get("role_overlay")
    target_overlay = target.get("target_overlay")

    sources: List[str] = []

    base_path = root / "vm-codex" / "profiles" / "base" / f"{base_name}.yaml"
    cfg = load_yaml(base_path)
    sources.append(str(base_path))

    if role_overlay:
        role_path = root / "vm-codex" / "profiles" / "overlays" / f"{role_overlay}.yaml"
        if role_path.exists():
            cfg = deep_merge(cfg, load_yaml(role_path))
            sources.append(str(role_path))

    if target_overlay:
        target_path = root / "vm-codex" / "profiles" / "overlays" / f"{target_overlay}.yaml"
        if target_path.exists():
            cfg = deep_merge(cfg, load_yaml(target_path))
            sources.append(str(target_path))

    req_sources: List[str] = []
    req = {}

    req_global = root / "vm-codex" / "requirements" / "global.yaml"
    req = deep_merge(req, load_yaml(req_global))
    req_sources.append(str(req_global))

    role = target.get("role")
    if role:
        req_role = root / "vm-codex" / "requirements" / "roles" / f"{role}.yaml"
        if req_role.exists():
            req = deep_merge(req, load_yaml(req_role))
            req_sources.append(str(req_role))

    req_target = root / "vm-codex" / "requirements" / "targets" / f"{target.get('target_id')}.yaml"
    if req_target.exists():
        req = deep_merge(req, load_yaml(req_target))
        req_sources.append(str(req_target))

    if alias_defaults:
        req = deep_merge(req, {"alias_defaults": alias_defaults})

    return {
        "config": cfg,
        "requirements": req,
        "config_sources": sources,
        "requirements_sources": req_sources,
    }
