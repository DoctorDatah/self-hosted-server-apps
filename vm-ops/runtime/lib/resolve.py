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


def _normalize_machine_exec_mode(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if raw in {"vm-remote-ssh", "ssh"}:
        return "vm-remote-ssh"
    if raw in {"vm-local", "local", ""}:
        return "vm-local"
    raise ResolutionError(f"Invalid target exec_mode for target: {value}")


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


def _load_optional_data_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return load_data_file(path)


def _group_members(raw_group: Any) -> List[str]:
    if isinstance(raw_group, list):
        return [str(x) for x in raw_group]
    if isinstance(raw_group, dict):
        members = raw_group.get("members", [])
        if isinstance(members, list):
            return [str(x) for x in members]
    return []


def _normalize_target(machine_id: str, machine: Dict[str, Any]) -> Dict[str, Any]:
    raw_type = str(machine.get("target_type", machine.get("type", "vm")))
    canonical_type = "host" if raw_type in {"host", "host-vm"} else "vm"

    enabled = machine.get("enabled_setups", machine.get("enabled_stages", []))
    if not isinstance(enabled, list):
        enabled = []

    labels = machine.get("labels", [])
    if not isinstance(labels, list):
        labels = []

    params = machine.get("params", machine.get("vars", {}))
    if not isinstance(params, dict):
        params = {}

    defaults = machine.get("defaults", {})
    if not isinstance(defaults, dict):
        defaults = {}

    groups = machine.get("groups", [])
    if not isinstance(groups, list):
        groups = []

    return {
        # Runtime uses canonical target_type values for stage compatibility.
        "target_type": canonical_type,
        # Keep raw type visible for UI/listing compatibility.
        "vm_type": raw_type,
        "environment": machine.get("environment", machine.get("env", "")),
        "labels": [str(x) for x in labels],
        "enabled_stages": [str(x) for x in enabled],
        "exec_mode": _normalize_machine_exec_mode(machine.get("exec_mode", "vm-local")),
        "repo_path": machine.get("repo_path", "/opt/vm-ops"),
        "ssh": machine.get("ssh", {}),
        "params": params,
        # Keep vars for stage/runtime compatibility.
        "vars": params,
        "defaults": defaults,
        "groups": [str(x) for x in groups],
        "set_of_operations": machine.get("set_of_operations", machine.get("operation_sets", {})),
        "target_id": machine_id,
    }


def _normalize_setups(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str):
        return [x.strip() for x in value.split(",") if x.strip()]
    return []


def _merge_alias(aliases: Dict[str, Dict[str, Any]], alias_name: str, alias_data: Dict[str, Any]) -> None:
    aliases[str(alias_name)] = alias_data


def _aliases_from_machine_sets(targets: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    aliases: Dict[str, Dict[str, Any]] = {}
    plain_name_candidates: Dict[str, Dict[str, Any]] = {}
    plain_name_collisions: set[str] = set()

    for machine_id, target in targets.items():
        raw_sets = target.get("set_of_operations", target.get("operation_sets", {}))
        if not raw_sets:
            continue
        if not isinstance(raw_sets, dict):
            raise ConfigError(
                f"vm-machines.yaml: machine {machine_id} set_of_operations must be an object"
            )

        for set_name_raw, set_cfg in raw_sets.items():
            set_name = str(set_name_raw).strip()
            if not set_name:
                continue
            if not isinstance(set_cfg, dict):
                raise ConfigError(
                    f"vm-machines.yaml: machine {machine_id} set_of_operations {set_name} must be an object"
                )

            setups = _normalize_setups(set_cfg.get("setups", set_cfg.get("default_stages", [])))
            if not setups:
                raise ConfigError(
                    f"vm-machines.yaml: machine {machine_id} set_of_operations {set_name} must define non-empty setups"
                )

            params = set_cfg.get("params", set_cfg.get("default_params", {}))
            if not isinstance(params, dict):
                raise ConfigError(
                    f"vm-machines.yaml: machine {machine_id} set_of_operations {set_name} params must be an object"
                )

            requires_confirmation = bool(set_cfg.get("requires_confirmation", True))
            description = str(set_cfg.get("description", "")).strip() or (
                f"{set_name} on {machine_id}"
            )

            alias_data = {
                "target_selector": f"target_id={machine_id}",
                "default_stages": setups,
                "default_params": params,
                "requires_confirmation": requires_confirmation,
                "description": description,
            }

            # Always expose a machine-scoped alias key.
            scoped_alias = f"{machine_id}--{set_name}"
            _merge_alias(aliases, scoped_alias, alias_data)

            # Also expose plain set name when globally unique.
            if set_name in plain_name_candidates:
                plain_name_collisions.add(set_name)
            else:
                plain_name_candidates[set_name] = alias_data

    for set_name, alias_data in plain_name_candidates.items():
        if set_name in plain_name_collisions:
            continue
        _merge_alias(aliases, set_name, alias_data)

    return aliases


def load_inventory(repo_root: Path) -> Dict[str, Dict[str, Any]]:
    config_dir = repo_root / "vm-configs"
    machines_cfg = load_data_file(config_dir / "vm-machines.yaml")
    operations_cfg = _load_optional_data_file(config_dir / "vm-operations.yaml")

    raw_machines = machines_cfg.get("machines", machines_cfg.get("targets", {}))
    if not isinstance(raw_machines, dict):
        raise ConfigError("vm-machines.yaml: machines must be a map")

    targets: Dict[str, Dict[str, Any]] = {}
    for machine_id, machine in raw_machines.items():
        if not isinstance(machine, dict):
            raise ConfigError(f"vm-machines.yaml: machine {machine_id} must be an object")
        targets[str(machine_id)] = _normalize_target(str(machine_id), machine)

    groups: Dict[str, Dict[str, Any]] = {}

    explicit_groups = machines_cfg.get("groups", {})
    if explicit_groups and not isinstance(explicit_groups, dict):
        raise ConfigError("vm-machines.yaml: groups must be a map")
    for name, raw_group in (explicit_groups or {}).items():
        groups[str(name)] = {"members": _group_members(raw_group)}

    operations_groups = operations_cfg.get("groups", {})
    if operations_groups and not isinstance(operations_groups, dict):
        raise ConfigError("vm-operations.yaml: groups must be a map")
    for name, raw_group in (operations_groups or {}).items():
        members = _group_members(raw_group)
        if str(name) not in groups:
            groups[str(name)] = {"members": []}
        for member in members:
            if member not in groups[str(name)]["members"]:
                groups[str(name)]["members"].append(member)

    # Derive groups from machine-level group tags.
    for machine_id, target in targets.items():
        for group_name in target.get("groups", []):
            groups.setdefault(group_name, {"members": []})
            if machine_id not in groups[group_name]["members"]:
                groups[group_name]["members"].append(machine_id)

    aliases: Dict[str, Dict[str, Any]] = {}

    # Legacy alias source (optional): vm-operations.yaml
    raw_operations = operations_cfg.get("operations", operations_cfg.get("aliases", {}))
    if raw_operations:
        if not isinstance(raw_operations, dict):
            raise ConfigError("vm-operations.yaml: operations must be a map")
        for op_id, op in raw_operations.items():
            if not isinstance(op, dict):
                raise ConfigError(f"vm-operations.yaml: operation {op_id} must be an object")

            target_selector = str(op.get("target_selector", "")).strip()
            machine_id = str(op.get("machine", "")).strip()
            if not target_selector:
                if not machine_id:
                    raise ConfigError(
                        f"vm-operations.yaml: operation {op_id} must define machine or target_selector"
                    )
                target_selector = f"target_id={machine_id}"

            setups = op.get("setups", op.get("default_stages", []))
            if not isinstance(setups, list):
                raise ConfigError(f"vm-operations.yaml: operation {op_id} setups must be a list")

            params = op.get("params", op.get("default_params", {}))
            if not isinstance(params, dict):
                raise ConfigError(f"vm-operations.yaml: operation {op_id} params must be an object")

            aliases[str(op_id)] = {
                "target_selector": target_selector,
                "default_stages": [str(x) for x in setups],
                "default_params": params,
                "requires_confirmation": op.get("requires_confirmation", True),
                "description": op.get("description", ""),
            }

    # Machine-first alias source: vm-machines.yaml -> set_of_operations
    machine_set_aliases = _aliases_from_machine_sets(targets)
    aliases.update(machine_set_aliases)

    return {"targets": targets, "groups": groups, "aliases": aliases}


def load_policy(repo_root: Path) -> Dict[str, Any]:
    return _load_optional_data_file(repo_root / "vm-configs" / "vm-env-rules.yaml")


def load_stage_meta(repo_root: Path, stage_id: str) -> Dict[str, Any]:
    return load_data_file(repo_root / "vm-setups" / stage_id / "stage.yaml")


def resolve_target_from_selector(selector: str) -> str:
    selector = selector.strip()
    if selector.startswith("target_id="):
        return selector.split("=", 1)[1].strip()
    raise ResolutionError(f"Unsupported alias target_selector: {selector}")


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
    requested_raw = str(requested or "").strip().lower()
    if requested_raw in {"local", "vm-local"}:
        return "local"
    if requested_raw in {"ssh", "vm-remote-ssh"}:
        return "ssh"
    if requested_raw != "auto":
        raise ResolutionError(f"Invalid exec mode: {requested}")
    target_mode = _normalize_machine_exec_mode(target.get("exec_mode", "vm-local"))
    return "ssh" if target_mode == "vm-remote-ssh" else "local"


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

    machine_params = target.get("params", target.get("vars", {}))
    if not isinstance(machine_params, dict):
        machine_params = {}
    machine_defaults = target.get("defaults", {})
    if not isinstance(machine_defaults, dict):
        machine_defaults = {}

    alias_defaults = alias.get("default_params", {}) if alias else {}
    if not isinstance(alias_defaults, dict):
        raise ResolutionError("alias default_params must be an object")

    # In lite mode params flow is simple: machine params -> operation params -> CLI params.
    resolved_params = deep_merge(machine_params, alias_defaults)
    resolved_params = deep_merge(resolved_params, cli_params)
    merged_config = deep_merge(machine_defaults, {"vars": machine_params})

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
            "mode": "lite",
            "machine": target_id,
            "operation": alias_name or "",
            "cli_params": bool(cli_params),
        },
    }


def render_exact_command(plan: Dict[str, Any]) -> str:
    resolved_mode = str(plan.get("exec_mode", "local"))
    mode_for_cli = "vm-remote-ssh" if resolved_mode == "ssh" else "vm-local"
    parts = ["vmcx", plan["operation"]]
    if plan.get("alias"):
        parts.extend(["--alias", str(plan["alias"])])
    else:
        parts.extend(["--target", str(plan["target_id"])])
    parts.extend(["--stages", ",".join(plan["stages"])])
    if plan.get("resolved_params"):
        parts.extend(["--params", json.dumps(plan["resolved_params"], separators=(",", ":"))])
    parts.extend(["--exec-mode", mode_for_cli])
    if plan["operation"] == "run":
        parts.append("--confirm")
    return " ".join(shlex.quote(p) for p in parts)
