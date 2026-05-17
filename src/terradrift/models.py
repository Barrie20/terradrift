"""Pydantic models for findings, modules, and drift events.

Real-world analogy: these are the "lab forms" we fill in for each scan.
Every misconfiguration becomes a Finding. Every Finding may later become
a Drift event when it is fixed or regresses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from terradrift.taxonomy import Category


class Finding(BaseModel):
    """A single misconfiguration detected at a single commit."""

    rule_id: str = Field(..., description="e.g. CKV_AWS_20")
    category: Category
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    file_path: str
    resource_address: str = Field(..., description="e.g. aws_s3_bucket.public")
    line_start: int
    line_end: int
    commit_sha: str
    detected_at: datetime
    message: str


class ModuleSnapshot(BaseModel):
    """A repository snapshot at a specific commit."""

    repo: str = Field(..., description="owner/name")
    commit_sha: str
    committed_at: datetime
    findings: list[Finding] = Field(default_factory=list)


class DriftEvent(BaseModel):
    """A change in finding state across two adjacent commits."""

    repo: str
    rule_id: str
    resource_address: str
    event: Literal["INTRODUCED", "FIXED", "REGRESSED"]
    from_sha: str
    to_sha: str
    days_alive: float = 0.0
