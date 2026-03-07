#!/usr/bin/env python3
from dataclasses import dataclass
from typing import Dict, List

from ..shared.schemas import DependencyEdge, DependencyNode


@dataclass
class DependencyGraph:
    nodes: List[DependencyNode]
    edges: List[DependencyEdge]


def build_dependency_graph(bundle: object, setup_ids: List[str]) -> DependencyGraph:
    machines_doc = getattr(bundle, "machines_doc", {})
    operations_doc = getattr(bundle, "operations_doc", {})
    rules_doc = getattr(bundle, "rules_doc", {})

    machines = machines_doc.get("machines", {}) if isinstance(machines_doc, dict) else {}
    operations = operations_doc.get("operations", {}) if isinstance(operations_doc, dict) else {}
    rules = rules_doc.get("rules", {}) if isinstance(rules_doc, dict) else {}

    nodes: List[DependencyNode] = []
    edges: List[DependencyEdge] = []

    for machine_id in sorted(machines.keys()):
        nodes.append(DependencyNode(entity_type="machine", entity_id=str(machine_id)))

    for operation_id, op in sorted(operations.items()):
        nodes.append(DependencyNode(entity_type="operation", entity_id=str(operation_id)))
        machine_id = str(op.get("machine", "")).strip()
        if machine_id:
            edges.append(
                DependencyEdge(
                    from_entity_type="machine",
                    from_entity_id=machine_id,
                    to_entity_type="operation",
                    to_entity_id=str(operation_id),
                    relation="operation.machine",
                )
            )

    for setup_id in sorted(setup_ids):
        nodes.append(DependencyNode(entity_type="setup_ref", entity_id=str(setup_id)))

    for machine_id, machine in machines.items():
        enabled = machine.get("enabled_setups", machine.get("enabled_stages", []))
        if not isinstance(enabled, list):
            continue
        for sid in enabled:
            edges.append(
                DependencyEdge(
                    from_entity_type="setup_ref",
                    from_entity_id=str(sid),
                    to_entity_type="machine",
                    to_entity_id=str(machine_id),
                    relation="machine.enabled_setups",
                )
            )

    for operation_id, op in operations.items():
        setups = op.get("setups", op.get("default_stages", []))
        if not isinstance(setups, list):
            continue
        for sid in setups:
            edges.append(
                DependencyEdge(
                    from_entity_type="setup_ref",
                    from_entity_id=str(sid),
                    to_entity_type="operation",
                    to_entity_id=str(operation_id),
                    relation="operation.setups",
                )
            )

    for setup_id in sorted(rules.keys()):
        edges.append(
            DependencyEdge(
                from_entity_type="setup_ref",
                from_entity_id=str(setup_id),
                to_entity_type="rule",
                to_entity_id=str(setup_id),
                relation="rule.setup",
            )
        )

    return DependencyGraph(nodes=nodes, edges=edges)


def direct_dependents(graph: DependencyGraph, entity_type: str, entity_id: str) -> List[DependencyNode]:
    deps: Dict[str, DependencyNode] = {}
    for edge in graph.edges:
        if edge.from_entity_type == entity_type and edge.from_entity_id == entity_id:
            key = f"{edge.to_entity_type}:{edge.to_entity_id}"
            deps[key] = DependencyNode(entity_type=edge.to_entity_type, entity_id=edge.to_entity_id)
    return sorted(deps.values(), key=lambda n: (n.entity_type, n.entity_id))
