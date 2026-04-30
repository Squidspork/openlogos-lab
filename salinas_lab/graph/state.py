from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class SourceChannel(StrEnum):
    CLI = "cli"
    API = "api"
    DREAM = "dream"
    TELEGRAM = "telegram"
    EMAIL = "email"
    WEB = "web"
    IOS = "ios"


class ResearchMode(StrEnum):
    MANUAL = "manual"
    DREAM = "dream"


class ResearchDepth(StrEnum):
    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"


class DepartmentName(StrEnum):
    DIRECTOR = "director"
    OPPORTUNITY_DISCOVERY = "opportunity_discovery"
    SCIENTIFIC_INQUIRY = "scientific_inquiry"
    PRODUCT_APPLICATIONS = "product_applications"
    HUMAN_TESTING = "human_testing"
    RISK_ETHICS = "risk_ethics"
    PUBLICATIONS = "publications"


class ResearchRequest(BaseModel):
    prompt: str = Field(min_length=1)
    mode: ResearchMode = ResearchMode.MANUAL
    depth: ResearchDepth = ResearchDepth.STANDARD
    audience: str = "builder-founder"
    source_channel: SourceChannel = SourceChannel.CLI
    session_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    tags: list[str] = Field(default_factory=list)

    @field_validator("prompt")
    @classmethod
    def strip_prompt(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("prompt cannot be blank")
        return value


class EvidenceItem(BaseModel):
    title: str
    url: str | None = None
    note: str = ""
    source_type: str = "model"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class DepartmentFinding(BaseModel):
    department: DepartmentName
    actor: str
    summary: str
    findings: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    model: str | None = None


class AuditEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: uuid4().hex)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    session_id: str
    actor: str
    department: DepartmentName | None = None
    action: str
    input_summary: str = ""
    output_summary: str = ""
    source_channel: SourceChannel
    model: str | None = None
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    redactions_applied: list[str] = Field(default_factory=list)


class ReportArtifact(BaseModel):
    title: str
    abstract: str
    markdown: str
    path: Path | None = None


class SessionPaths(BaseModel):
    root: Path
    departments: Path
    evidence: Path
    report: Path
    audit: Path
    request: Path
    metadata: Path


class LabState(BaseModel):
    request: ResearchRequest
    paths: SessionPaths | None = None
    messages: list[dict[str, str]] = Field(default_factory=list)
    department_findings: dict[DepartmentName, DepartmentFinding] = Field(default_factory=dict)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    audit_events: list[str] = Field(default_factory=list)
    report: ReportArtifact | None = None
    status: Literal["created", "running", "completed", "failed"] = "created"

    def add_finding(self, finding: DepartmentFinding) -> None:
        self.department_findings[finding.department] = finding
        self.evidence.extend(finding.evidence)
        self.risks.extend(finding.risks)
