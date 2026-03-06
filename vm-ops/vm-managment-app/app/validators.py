#!/usr/bin/env python3
import json
from pathlib import Path
from typing import Any, Dict, List, Set

from .config_store import ConfigBundle


def _is_bool(value: Any) -> bool:
    return isinstance(value, bool)


def available_setup_ids(repo_root: Path) -> Set[str]:
    setups_dir = repo_root / "vm-setups"
    ids: Set[str] = set()
    if not setups_dir.exists():
        return ids
    for child in setups_dir.iterdir():
        if not child.is_dir():
            continue
        if child.name.startswith("_"):
            continue
        if (child / "stage.yaml").exists():
            ids.add(child.name)
    return ids


def validate_bundle(bundle: ConfigBundle, repo_root: Path) -> List[str]:
    errors: List[str] = []
    setup_ids = available_setup_ids(repo_root)

    machines = bundle.machines_doc.get("machines", {})
    groups = bundle.machines_doc.get("groups", {})
    operations = bundle.operations_doc.get("operations", {})
    rules = bundle.rules_doc.get("rules", {})

    if not isinstance(machines, dict):
        return ["machines must be an object"]
    if not isinstance(groups, dict):
        errors.append("groups must be an object")
    if not isinstance(operations, dict):
        errors.append("operations must be an object")
    if not isinstance(rules, dict):
        errors.append("rules must be an object")

    for machine_id, machine in machines.items():
        if not isinstance(machine, dict):
            errors.append(f"machine {machine_id} must be an object")
            continue

        env = str(machine.get("env", "")).strip()
        if not env:
            errors.append(f"machine {machine_id} missing env")

        enabled = machine.get("enabled_setups", machine.get("enabled_stages", []))
        if not isinstance(enabled, list) or not enabled:
            errors.append(f"machine {machine_id} must define non-empty enabled_setups")
        else:
            for setup_id in enabled:
                sid = str(setup_id)
                if sid not in setup_ids:
                    errors.append(f"machine {machine_id} references unknown setup: {sid}")

        exec_mode = str(machine.get("exec_mode", "local"))
        if exec_mode == "ssh":
            ssh = machine.get("ssh", {})
            if not isinstance(ssh, dict):
                errors.append(f"machine {machine_id} ssh must be an object")
            else:
                if not str(ssh.get("host", "")).strip():
                    errors.append(f"machine {machine_id} missing ssh.host for ssh mode")
                if not str(ssh.get("user", "")).strip():
                    errors.append(f"machine {machine_id} missing ssh.user for ssh mode")
                port = ssh.get("port", 22)
                try:
                    p = int(port)
                    if p <= 0:
                        raise ValueError("port must be positive")
                except Exception:
                    errors.append(f"machine {machine_id} has invalid ssh.port: {port}")

        if "params" in machine and not isinstance(machine.get("params"), dict):
            errors.append(f"machine {machine_id} params must be an object")
        if "defaults" in machine and not isinstance(machine.get("defaults"), dict):
            errors.append(f"machine {machine_id} defaults must be an object")

        if "labels" in machine and not isinstance(machine.get("labels"), list):
            errors.append(f"machine {machine_id} labels must be an array")
        if "groups" in machine and not isinstance(machine.get("groups"), list):
            errors.append(f"machine {machine_id} groups must be an array")

    if isinstance(groups, dict):
        for group_name, members in groups.items():
            if not isinstance(members, list):
                errors.append(f"group {group_name} must be an array")
                continue
            if not members:
                errors.append(f"group {group_name} has no members")
            for machine_id in members:
                if str(machine_id) not in machines:
                    errors.append(f"group {group_name} references unknown machine: {machine_id}")

    if isinstance(operations, dict):
        for operation_id, op in operations.items():
            if not isinstance(op, dict):
                errors.append(f"operation {operation_id} must be an object")
                continue

            machine_id = str(op.get("machine", "")).strip()
            if not machine_id:
                errors.append(f"operation {operation_id} missing machine")
            elif machine_id not in machines:
                errors.append(f"operation {operation_id} references unknown machine: {machine_id}")

            setups = op.get("setups", op.get("default_stages", []))
            if not isinstance(setups, list) or not setups:
                errors.append(f"operation {operation_id} must define non-empty setups")
            else:
                for setup_id in setups:
                    sid = str(setup_id)
                    if sid not in setup_ids:
                        errors.append(f"operation {operation_id} references unknown setup: {sid}")

                if machine_id in machines:
                    machine_enabled = machines[machine_id].get("enabled_setups", machines[machine_id].get("enabled_stages", []))
                    if isinstance(machine_enabled, list):
                        for sid in [str(x) for x in setups]:
                            if sid not in [str(x) for x in machine_enabled]:
                                errors.append(
                                    f"operation {operation_id} setup {sid} is not enabled on machine {machine_id}"
                                )

            params = op.get("params", op.get("default_params", {}))
            if not isinstance(params, dict):
                errors.append(f"operation {operation_id} params must be an object")

            requires_confirmation = op.get("requires_confirmation", True)
            if not _is_bool(requires_confirmation):
                errors.append(f"operation {operation_id} requires_confirmation must be boolean")

    if isinstance(rules, dict):
        for setup_id, rule in rules.items():
            sid = str(setup_id)
            if sid not in setup_ids:
                errors.append(f"rule references unknown setup: {sid}")
                continue
            if not isinstance(rule, dict):
                errors.append(f"rule for {sid} must be an object")
                continue

            allowed_envs = rule.get("allowed_environments", [])
            if allowed_envs and not isinstance(allowed_envs, list):
                errors.append(f"rule for {sid} allowed_environments must be an array")
            elif isinstance(allowed_envs, list):
                for env in allowed_envs:
                    if str(env) not in {"dev", "stage", "prod"}:
                        errors.append(f"rule for {sid} has invalid environment: {env}")

            if "requires_confirmation" in rule and not _is_bool(rule.get("requires_confirmation")):
                errors.append(f"rule for {sid} requires_confirmation must be boolean")

    return errors


def pretty_errors(errors: List[str]) -> str:
    if not errors:
        return ""
    return "\n".join(f"- {e}" for e in errors)


def parse_json_text(raw: str, label: str) -> Dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        return {}
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} is not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value
