from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .common import render_template, to_csv


def _normalize_stage_params(stages: List[str], params: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    if not params:
        return {stage: {} for stage in stages}

    # Stage-scoped style: {"app_deploy": {"section": "app"}}
    if all(isinstance(v, dict) for v in params.values()):
        scoped = {stage: dict(params.get(stage, {})) for stage in stages}
        return scoped

    # Flat style applies to first stage.
    out = {stage: {} for stage in stages}
    out[stages[0]] = dict(params)
    return out


def build_plan(
    root: Path,
    target: Dict[str, Any],
    stages: List[str],
    merged: Dict[str, Any],
    cli_params: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    cli_params = cli_params or {}
    config = merged["config"]
    requirements = merged["requirements"]

    stage_cfg = config.get("stage_config", {})
    target_vars = dict(target.get("vars", {}))
    req_defaults = dict(requirements.get("defaults", {}))
    alias_defaults = dict((requirements.get("alias_defaults") or {}).get("default_params", {}))

    stage_params = _normalize_stage_params(stages, cli_params)

    stage_plans: List[Dict[str, Any]] = []
    preflight_failed = False

    for stage in stages:
        if stage not in target.get("enabled_stages", []):
            raise ValueError(f"Stage '{stage}' is not enabled for target '{target.get('target_id')}'")

        st = stage_cfg.get(stage)
        if not st:
            raise ValueError(f"Stage '{stage}' is missing from stage_config")

        params = {}
        params.update(alias_defaults.get(stage, {}))
        params.update(stage_params.get(stage, {}))

        context = {
            "target_id": target.get("target_id"),
            "target_type": target.get("target_type"),
            "env": target.get("env"),
            "role": target.get("role"),
            **target_vars,
            **req_defaults,
            **params,
        }
        context["backup_sources_csv"] = to_csv(context.get("backup_sources", []))
        install_only = str(context.get("install_only", "")).strip()
        context["install_only_suffix"] = f" --only {install_only}" if install_only else ""
        context["restore_target_type"] = context.get("restore_target_type", "staging")

        preflight = []
        for required in st.get("preflight", {}).get("required_files", []):
            resolved = render_template(required, context)
            exists = (root / resolved).exists()
            preflight.append({"type": "required_file", "path": resolved, "ok": exists})
            if not exists:
                preflight_failed = True

        commands: List[str] = []
        if "commands_by_section" in st:
            section = context.get("section", req_defaults.get("deploy_section", "all"))
            selected = st.get("commands_by_section", {}).get(section)
            if not selected:
                raise ValueError(f"Unknown section '{section}' for stage '{stage}'")
            commands = [render_template(cmd, context) for cmd in selected]
        else:
            commands = [render_template(cmd, context) for cmd in st.get("commands", [])]

        stage_plans.append(
            {
                "stage": stage,
                "risk": st.get("risk", "medium"),
                "params": params,
                "context": context,
                "preflight": preflight,
                "commands": commands,
            }
        )

    return {
        "target": target,
        "stages": stages,
        "stage_plans": stage_plans,
        "preflight_failed": preflight_failed,
        "effective_config_sources": merged["config_sources"],
        "effective_requirements_sources": merged["requirements_sources"],
    }
