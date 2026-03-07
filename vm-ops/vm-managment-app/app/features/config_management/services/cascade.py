#!/usr/bin/env python3
from typing import List, Tuple

from . import config_store, validators
from .config_store import ConfigBundle
from .integrity import IntegrityError, build_delete_impact_report, summarize_dependents


def preview_cascade(
    bundle: ConfigBundle,
    repo_root,
    entity_type: str,
    entity_id: str,
    cascade: bool,
) -> Tuple[ConfigBundle, List[str], List[str], object]:
    report = build_delete_impact_report(bundle, repo_root, entity_type, entity_id)

    should_block = bool(report.blockers) and not cascade
    if should_block:
        return bundle, [], [], report

    candidate = config_store.clone_bundle(bundle)
    changed_parts: List[str] = []

    if entity_type == "machine":
        config_store.delete_machine(candidate, entity_id)
        changed_parts.append("machines")

        deps = summarize_dependents(report)
        for operation_id in deps.get("operation", []):
            config_store.delete_operation(candidate, operation_id)
        if deps.get("operation"):
            changed_parts.append("operations")

    elif entity_type == "operation":
        config_store.delete_operation(candidate, entity_id)
        changed_parts.append("operations")

    elif entity_type == "rule":
        config_store.delete_rule(candidate, entity_id)
        changed_parts.append("rules")

    else:
        raise IntegrityError("Unsupported entity for cascade in v1", code="unsupported_entity")

    validation_errors = validators.validate_bundle(candidate, repo_root)
    if validation_errors:
        raise IntegrityError(
            "Cascade result failed validation: " + " | ".join(validation_errors),
            code="cascade_invalid",
        )

    uniq_parts: List[str] = []
    for part in changed_parts:
        if part not in uniq_parts:
            uniq_parts.append(part)

    return candidate, uniq_parts, validation_errors, report
