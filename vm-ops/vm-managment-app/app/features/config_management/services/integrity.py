#!/usr/bin/env python3
from typing import Dict, List, Set, Tuple

from ....core.dependency_graph import build_dependency_graph, direct_dependents
from ....shared.schemas import (
    CascadePlan,
    DeleteImpactReport,
    DependencyNode,
    IntegrityViolation,
)
from . import validators
from .config_store import ConfigBundle


class IntegrityError(Exception):
    def __init__(self, message: str, code: str = "integrity_error") -> None:
        super().__init__(message)
        self.code = code


def _as_str_set(values: List[str]) -> Set[str]:
    return {str(v) for v in values}


def _ensure_entity_exists(bundle: ConfigBundle, entity_type: str, entity_id: str) -> None:
    machines = bundle.machines_doc.get("machines", {})
    operations = bundle.operations_doc.get("operations", {})
    rules = bundle.rules_doc.get("rules", {})

    if entity_type == "machine" and entity_id not in machines:
        raise IntegrityError(f"machine '{entity_id}' not found", code="not_found")
    if entity_type == "operation" and entity_id not in operations:
        raise IntegrityError(f"operation '{entity_id}' not found", code="not_found")
    if entity_type == "rule" and entity_id not in rules:
        raise IntegrityError(f"rule '{entity_id}' not found", code="not_found")


def _machine_dependents(bundle: ConfigBundle, machine_id: str) -> List[DependencyNode]:
    operations = bundle.operations_doc.get("operations", {})
    if not isinstance(operations, dict):
        return []
    deps: List[DependencyNode] = []
    for operation_id, op in operations.items():
        if not isinstance(op, dict):
            continue
        if str(op.get("machine", "")).strip() == machine_id:
            deps.append(DependencyNode(entity_type="operation", entity_id=str(operation_id)))
    return sorted(deps, key=lambda d: d.entity_id)


def _setup_dependents(bundle: ConfigBundle, setup_id: str) -> List[DependencyNode]:
    deps: List[DependencyNode] = []
    machines = bundle.machines_doc.get("machines", {})
    operations = bundle.operations_doc.get("operations", {})
    rules = bundle.rules_doc.get("rules", {})

    if isinstance(machines, dict):
        for machine_id, machine in machines.items():
            if not isinstance(machine, dict):
                continue
            enabled = machine.get("enabled_setups", machine.get("enabled_stages", []))
            if isinstance(enabled, list) and setup_id in _as_str_set([str(x) for x in enabled]):
                deps.append(DependencyNode(entity_type="machine", entity_id=str(machine_id)))

    if isinstance(operations, dict):
        for operation_id, op in operations.items():
            if not isinstance(op, dict):
                continue
            setups = op.get("setups", op.get("default_stages", []))
            if isinstance(setups, list) and setup_id in _as_str_set([str(x) for x in setups]):
                deps.append(DependencyNode(entity_type="operation", entity_id=str(operation_id)))

    if isinstance(rules, dict) and setup_id in rules:
        deps.append(DependencyNode(entity_type="rule", entity_id=setup_id))

    return sorted(deps, key=lambda d: (d.entity_type, d.entity_id))


def build_delete_impact_report(
    bundle: ConfigBundle,
    repo_root,
    entity_type: str,
    entity_id: str,
) -> DeleteImpactReport:
    _ensure_entity_exists(bundle, entity_type, entity_id)

    setup_ids = sorted(validators.available_setup_ids(repo_root))
    graph = build_dependency_graph(bundle, setup_ids)

    direct: List[DependencyNode] = []
    transitive: List[DependencyNode] = []
    affected_files: List[str] = []
    warnings: List[str] = []
    blockers: List[IntegrityViolation] = []

    if entity_type == "machine":
        direct = _machine_dependents(bundle, entity_id)
        transitive = list(direct)
        affected_files = ["vm-configs/vm-machines.yaml", "vm-configs/vm-operations.yaml"]
        warnings.append("Machine groups are recomputed from remaining machines.")
        if direct:
            blockers.append(
                IntegrityViolation(
                    code="dependent_operations",
                    message=(
                        f"Machine '{entity_id}' has dependent operations and cannot be deleted "
                        "without explicit cascade confirmation."
                    ),
                    entity_type="machine",
                    entity_id=entity_id,
                )
            )
    elif entity_type == "operation":
        direct = []
        transitive = []
        affected_files = ["vm-configs/vm-operations.yaml"]
    elif entity_type == "rule":
        direct = []
        transitive = []
        affected_files = ["vm-configs/vm-env-rules.yaml"]
    elif entity_type == "setup_ref":
        direct = _setup_dependents(bundle, entity_id)
        transitive = list(direct)
        affected_files = [
            "vm-configs/vm-machines.yaml",
            "vm-configs/vm-operations.yaml",
            "vm-configs/vm-env-rules.yaml",
        ]
        blockers.append(
            IntegrityViolation(
                code="unsupported_entity",
                message="Deleting setup references is not supported in v1.",
                entity_type="setup_ref",
                entity_id=entity_id,
            )
        )
    else:
        raise IntegrityError(f"Unsupported entity type: {entity_type}", code="bad_entity")

    if not direct and entity_type in {"machine", "operation", "rule", "setup_ref"}:
        direct = direct_dependents(graph, entity_type, entity_id)
        transitive = list(direct)

    cascade_plan = CascadePlan(
        entity_type=entity_type, entity_id=entity_id, requires_cascade=bool(blockers)
    )

    if entity_type == "machine":
        cascade_plan.removed_machines = [entity_id]
        cascade_plan.removed_operations = [d.entity_id for d in direct if d.entity_type == "operation"]
    elif entity_type == "operation":
        cascade_plan.removed_operations = [entity_id]
    elif entity_type == "rule":
        cascade_plan.removed_rules = [entity_id]

    return DeleteImpactReport(
        entity_type=entity_type, entity_id=entity_id,
        direct_dependents=direct,
        transitive_dependents=transitive,
        affected_files=affected_files,
        warnings=warnings,
        blockers=blockers,
        cascade_plan=cascade_plan,
    )


def summarize_dependents(report: DeleteImpactReport) -> Dict[str, List[str]]:
    result: Dict[str, List[str]] = {"machine": [], "operation": [], "rule": [], "setup_ref": []}
    for dep in report.direct_dependents:
        result.setdefault(dep.entity_type, [])
        result[dep.entity_type].append(dep.entity_id)
    return result
