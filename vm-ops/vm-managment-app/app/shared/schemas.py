#!/usr/bin/env python3
from typing import Any, Dict, List, Literal, Optional

try:
    from pydantic import BaseModel, Field
except Exception:  # noqa: BLE001
    import copy

    class BaseModel:  # type: ignore[override]
        def __init__(self, **kwargs: Any) -> None:
            annotations = getattr(self, "__annotations__", {})
            for key in annotations.keys():
                if key in kwargs:
                    setattr(self, key, kwargs[key])
                elif hasattr(self.__class__, key):
                    value = getattr(self.__class__, key)
                    resolved = value() if callable(value) else value
                    setattr(self, key, copy.deepcopy(resolved))
                else:
                    setattr(self, key, None)

        def dict(self) -> Dict[str, Any]:
            return dict(self.__dict__)

        def model_dump(self) -> Dict[str, Any]:
            return self.dict()

    def Field(default: Any = None, default_factory=None):  # type: ignore[override]
        if default_factory is not None:
            return default_factory()
        return default

EntityType = Literal["machine", "operation", "rule", "setup_ref"]


class GitPrepareRequest(BaseModel):
    branch_name: Optional[str] = None
    commit_message: Optional[str] = None


class GitPrepareResponse(BaseModel):
    branch: str
    commit_sha: str
    changed_files: List[str] = Field(default_factory=list)
    next_commands: List[str] = Field(default_factory=list)


class AppStatusResponse(BaseModel):
    branch: str
    is_clean: bool
    changed_files: List[str] = Field(default_factory=list)
    staged_files: List[str] = Field(default_factory=list)
    validation_errors: List[str] = Field(default_factory=list)


class DependencyNode(BaseModel):
    entity_type: EntityType
    entity_id: str


class DependencyEdge(BaseModel):
    from_entity_type: EntityType
    from_entity_id: str
    to_entity_type: EntityType
    to_entity_id: str
    relation: str


class IntegrityViolation(BaseModel):
    code: str
    message: str
    entity_type: EntityType
    entity_id: str


class CascadePlan(BaseModel):
    entity_type: EntityType
    entity_id: str
    requires_cascade: bool = False
    removed_machines: List[str] = Field(default_factory=list)
    removed_operations: List[str] = Field(default_factory=list)
    removed_rules: List[str] = Field(default_factory=list)


class DeleteImpactReport(BaseModel):
    entity_type: EntityType
    entity_id: str
    direct_dependents: List[DependencyNode] = Field(default_factory=list)
    transitive_dependents: List[DependencyNode] = Field(default_factory=list)
    affected_files: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    blockers: List[IntegrityViolation] = Field(default_factory=list)
    cascade_plan: CascadePlan


class DeletePreviewRequest(BaseModel):
    entity_type: EntityType
    entity_id: str
    cascade: bool = False


class DeleteApplyRequest(BaseModel):
    entity_type: EntityType
    entity_id: str
    cascade: bool = True
    confirm: bool = False


class RealtimeEventPayload(BaseModel):
    event: str
    version: int
    timestamp: float
    data: Dict[str, object] = Field(default_factory=dict)


def model_to_dict(model: BaseModel) -> Dict[str, object]:
    if hasattr(model, "model_dump"):
        return model.model_dump()  # type: ignore[return-value]
    return model.dict()  # type: ignore[return-value]
