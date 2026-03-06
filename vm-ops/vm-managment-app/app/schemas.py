#!/usr/bin/env python3
from typing import List, Optional

from pydantic import BaseModel, Field


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
