#!/usr/bin/env python3
import json
from typing import Any, Dict


def format_plan(plan: Dict[str, Any]) -> str:
    out = {
        "target_id": plan["target_id"],
        "alias": plan.get("alias"),
        "stages": plan["stages"],
        "exec_mode": plan["exec_mode"],
        "resolved_params": plan["resolved_params"],
        "config_sources": plan["config_sources"],
        "policy_notes": plan.get("policy_notes", []),
    }
    return json.dumps(out, indent=2, sort_keys=True)
