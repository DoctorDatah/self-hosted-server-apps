#!/usr/bin/env python3
import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .io_utils import ConfigError, deep_merge, load_data_file


class ResolutionError(Exception):
    pass


def parse_csv(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_params_json(params_json: Optional[str]) -> Dict[str, Any]:
    if not params_json:
        return {}
    try:
        data = json.loads(params_json)
    except json.JSONDecodeError as exc:
        raise ResolutionError(f"Invalid --params JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ResolutionError("--params must decode to an object")
    return data


def repo_root_from_script(script_path: Path) -> Path:
    return script_path.resolve().parents[1]


def load_inventory(repo_root: Path) -> Dict[str, Dict[str, Any]]:
    inventory_dir = repo_root / "inventory"
    targets = load_data_file(inventory_dir / "targets.yaml").get("targets", {})
    groups = load_data_file(inventory_dir / "groups.yaml").get("groups", {})
    aliases = load_data_file(inventory_dir / "aliases.yaml").get("aliases", {})
    if not isinstance(targets, dict) or not isinstance(groups, dict) or not isinstance(aliases, dict):
        raise ConfigError("inventory files must contain top-level maps")
    return {"targets": targets, "groups": groups, "aliases": aliases}


def load_policy(repo_root: Path) -> Dict[str, Any]:
    return load_data_file(repo_root / "policies" / "local-policy.yaml")


def load_stage_meta(repo_root: Path, stage_id: str) -> Dict[str, Any]:
    return load_data_file(repo_root / "stages" / stage_id / "stage.yaml")


def resolve_target_from_selector(selector: str) -> str:
    selector = selector.strip()
    if selector.startswith("target_id="):
        return selector.split("=", 1)[1].strip()
    raise ResolutionError(f"Unsupported alias target_selector: {selector}")


def load_profile(repo_root: Path, profile_kind: str, profile_name: str) -> Dict[str, Any]:
    if not profile_name:
        return {}
    if profile_kind == "base":
        path = repo_root / "profiles" / "base" / f"{profile_name}.yaml"
    else:
        path = repo_root / "profiles" / "overlays" / f"{profile_name}.yaml"
    if not path.exists():
        return {}
    return load_data_file(path)


def resolve_secret(repo_root: Path, ref: str) -> str:
    if ref.startswith("env://"):
        env_key = ref.split("env://", 1)[1]
        value = os.getenv(env_key)
        if not value:
            raise ResolutionError(f"Missing environment secret: {env_key}")
        return value

    if ref.startswith("infisical://"):
        resolver = repo_root / "tools" / "infisical_resolve.sh"
        proc = subprocess.run(
            ["bash", str(resolver), ref],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            raise ResolutionError(proc.stderr.strip() or f"Failed to resolve secret ref: {ref}")
        value = proc.stdout.strip()
        if not value:
            raise ResolutionError(f"Empty secret value for ref: {ref}")
        return value

    raise ResolutionError(f"Unsupported secret reference: {ref}")


def _resolve_exec_mode(target: Dict[str, Any], requested: str) -> str:
    if requested in {"local", "ssh"}:
        return requested
    if requested != "auto":
        raise ResolutionError(f"Invalid exec mode: {requested}")
    target_mode = target.get("exec_mode", "local")
    if target_mode not in {"local", "ssh"}:
        raise ResolutionError(f"Invalid target exec_mode for target: {target_mode}")
    return target_mode


def _resolve_stages(
    stages_csv: Optional[str],
    alias: Optional[Dict[str, Any]],
) -> List[str]:
    explicit = parse_csv(stages_csv)
    if explicit:
        return explicit
    if alias:
        default_stages = alias.get("default_stages", [])
        if not isinstance(default_stages, list):
            raise ResolutionError("alias default_stages must be a list")
        return [str(s) for s in default_stages]
    return []


def _resolve_target_and_alias(
    inventory: Dict[str, Dict[str, Any]],
    target_id: Optional[str],
    alias_name: Optional[str],
) -> Tuple[str, Optional[Dict[str, Any]]]:
    aliases = inventory["aliases"]
    if alias_name:
        alias = aliases.get(alias_name)
        if not alias:
            raise ResolutionError(f"Unknown alias: {alias_name}")
        alias_target = resolve_target_from_selector(str(alias.get("target_selector", "")))
        if target_id and target_id != alias_target:
            raise ResolutionError("Cannot set --target that conflicts with --alias target_selector")
        target_id = alias_target
        return target_id, alias

    if not target_id:
        raise ResolutionError("One of --target or --alias is required")
    return target_id, None


def build_plan(
    *,
    repo_root: Path,
    inventory: Dict[str, Dict[str, Any]],
    policy: Dict[str, Any],
    target_id: Optional[str],
    alias_name: Optional[str],
    stages_csv: Optional[str],
    params_json: Optional[str],
    exec_mode: str,
    operation: str,
) -> Dict[str, Any]:
    target_id, alias = _resolve_target_and_alias(inventory, target_id, alias_name)
    target = inventory["targets"].get(target_id)
    if not target:
        raise ResolutionError(f"Unknown target: {target_id}")
    target = {**target, "target_id": target_id}

    stages = _resolve_stages(stages_csv, alias)
    if not stages:
        raise ResolutionError("No stages resolved. Provide --stages or an alias with default_stages")

    resolved_mode = _resolve_exec_mode(target, exec_mode)
    cli_params = parse_params_json(params_json)

    base_profile = load_profile(repo_root, "base", str(target.get("base_profile", "default")))
    role_overlay = load_profile(repo_root, "overlay", str(target.get("role_overlay", "")))
    target_overlay = load_profile(repo_root, "overlay", str(target.get("target_overlay", "")))
    alias_defaults = alias.get("default_params", {}) if alias else {}

    if not isinstance(alias_defaults, dict):
        raise ResolutionError("alias default_params must be an object")

    merged_config = deep_merge(base_profile, role_overlay)
    merged_config = deep_merge(merged_config, target_overlay)
    profile_vars = merged_config.get("vars", {}) if isinstance(merged_config.get("vars"), dict) else {}
    target_vars = target.get("vars", {}) if isinstance(target.get("vars"), dict) else {}
    resolved_params = deep_merge(profile_vars, target_vars)
    resolved_params = deep_merge(resolved_params, alias_defaults)
    resolved_params = deep_merge(resolved_params, cli_params)

    stage_meta: Dict[str, Dict[str, Any]] = {}
    policy_rules = policy.get("rules", {}) if isinstance(policy, dict) else {}
    enabled_stages = [str(s) for s in target.get("enabled_stages", [])]
    env_name = str(target.get("environment", ""))
    policy_notes = []

    for stage_id in stages:
        if stage_id not in enabled_stages:
            raise ResolutionError(f"Stage {stage_id} is not enabled for target {target_id}")
        meta = load_stage_meta(repo_root, stage_id)
        stage_meta[stage_id] = meta

        required = meta.get("required_params", [])
        if not isinstance(required, list):
            raise ResolutionError(f"stage {stage_id}: required_params must be a list")
        missing = [p for p in required if p not in resolved_params]
        if missing:
            raise ResolutionError(
                f"stage {stage_id} missing required params: {', '.join(missing)}"
            )

        rule = policy_rules.get(stage_id, {})
        if not isinstance(rule, dict):
            raise ResolutionError(f"policy rule for {stage_id} must be an object")

        allowed_envs = rule.get("allowed_environments")
        if isinstance(allowed_envs, list) and env_name not in [str(x) for x in allowed_envs]:
            raise ResolutionError(
                f"Policy denies stage {stage_id} in environment {env_name}"
            )

        if rule.get("requires_confirmation", False):
            policy_notes.append(f"{stage_id} requires confirmation")

    return {
        "operation": operation,
        "target_id": target_id,
        "target": target,
        "alias": alias_name,
        "stages": stages,
        "exec_mode": resolved_mode,
        "resolved_params": resolved_params,
        "merged_config": merged_config,
        "stage_meta": stage_meta,
        "policy_notes": policy_notes,
        "config_sources": {
            "base_profile": target.get("base_profile", "default"),
            "role_overlay": target.get("role_overlay", ""),
            "target_overlay": target.get("target_overlay", ""),
            "alias": alias_name or "",
            "cli_params": bool(cli_params),
        },
    }


def render_exact_command(plan: Dict[str, Any]) -> str:
    parts = ["vmcx", plan["operation"]]
    if plan.get("alias"):
        parts.extend(["--alias", str(plan["alias"])])
    else:
        parts.extend(["--target", str(plan["target_id"])])
    parts.extend(["--stages", ",".join(plan["stages"])])
    if plan.get("resolved_params"):
        parts.extend(["--params", json.dumps(plan["resolved_params"], separators=(",", ":"))])
    parts.extend(["--exec-mode", str(plan["exec_mode"])])
    if plan["operation"] == "run":
        parts.append("--confirm")
    return " ".join(shlex.quote(p) for p in parts)
