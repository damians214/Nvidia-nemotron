"""Strict persisted contracts for the hackathon investigation pipeline."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


def uid() -> str:
    return str(uuid4())


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Check(Record):
    id: str = Field(default_factory=uid)
    name: str
    executed: bool = False
    passed: bool | None = None
    status: Literal["PASS", "FAIL", "NOT_RUN", "INCONCLUSIVE"] = "NOT_RUN"
    details: str = ""
    duration_ms: int = 0
    candidate_hash: str | None = None

    @model_validator(mode="after")
    def consistent(self):
        if self.status in {"PASS", "FAIL"}:
            if not self.executed or self.passed is not (self.status == "PASS"):
                raise ValueError("Conclusive checks require execution and a matching boolean")
        elif self.passed is not None:
            raise ValueError("Incomplete checks cannot have a pass/fail boolean")
        return self


class Policies(Record):
    no_new_imports: bool = True
    minimal_diff: bool = True
    max_changed_lines: int = Field(default=24, ge=1, le=192)


class Finding(Record):
    id: str = Field(default_factory=uid)
    rule_id: str
    severity: str
    raw_severity: str
    file: str
    line: int
    end_line: int
    message: str
    scanner: str = "OpenGrep"
    scan_id: str
    fingerprint: str


class Scan(Record):
    id: str = Field(default_factory=uid)
    executed: bool = False
    status: Literal["PASS", "NOT_RUN", "INCONCLUSIVE"] = "NOT_RUN"
    tool_version: str = ""
    binary_hash: str = ""
    rules_hash: str = ""
    config_hash: str = ""
    command: list[str] = Field(default_factory=list)
    raw_hash: str = ""
    raw_json: str = ""
    findings: list[Finding] = Field(default_factory=list)
    scanned: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    exit_code: int | None = None
    duration_ms: int = 0


class Review(Record):
    verdict: Literal["ACCEPT", "REJECT", "UNCERTAIN"]
    evidence_refs: list[str] = Field(min_length=1)
    concerns: list[str]
    uncertainty: str


class Candidate(Record):
    id: str = Field(default_factory=uid)
    attempt: int
    relative_path: str
    original_hash: str
    patched_text: str
    candidate_hash: str
    diff: str
    original_text: str = ""
    generation_request_id: str | None = None
    created_at: str = Field(default_factory=now)
    checks: list[Check] = Field(default_factory=list)
    rescan: Scan = Field(default_factory=Scan)
    comparison: str = "NOT_RUN"
    review: Review | None = None
    review_request_id: str | None = None
    status: Literal["PROPOSED", "REJECTED", "READY", "INCONCLUSIVE"] = "PROPOSED"


class Event(Record):
    run_id: str
    sequence: int
    step_id: str = Field(default_factory=uid)
    timestamp: str = Field(default_factory=now)
    stage: str
    action: str
    status: str
    detail: str
    duration_ms: int = 0
    evidence_refs: list[str] = Field(default_factory=list)


class ToolReceipt(Record):
    call_id: str
    name: str
    request_id: str
    timestamp: str = Field(default_factory=now)
    parameters: dict = Field(default_factory=dict)
    result_hash: str
    status: Literal["PASS", "FAIL"]
    source_refs: list[str] = Field(default_factory=list)
    duration_ms: int


State = Literal["IDLE", "COPYING", "SCANNING", "AWAITING_SELECTION", "INVESTIGATING",
                "PATCHING", "SYNTAX_CHECK", "RESCANNING", "REVIEWING",
                "READY_FOR_HUMAN_REVIEW", "FAILED", "CANCELED", "INCONCLUSIVE"]
TERMINAL = {"READY_FOR_HUMAN_REVIEW", "FAILED", "CANCELED", "INCONCLUSIVE"}


class Run(Record):
    schema_version: str = "1.0"
    id: str = Field(default_factory=uid)
    mode: Literal["LIVE", "RECORDED_TEST"] = "LIVE"
    repository_id: str
    state: State = "IDLE"
    created_at: str = Field(default_factory=now)
    updated_at: str = Field(default_factory=now)
    model_id: str = ""
    policies: Policies = Field(default_factory=Policies)
    manifest: dict[str, str] = Field(default_factory=dict)
    exclusions: list[str] = Field(default_factory=list)
    original_unchanged: bool | None = None
    baseline_scan: Scan = Field(default_factory=Scan)
    finding_id: str | None = None
    candidates: list[Candidate] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    tool_receipts: list[ToolReceipt] = Field(default_factory=list)
    model_requests: int = 0
    tool_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    usage_estimated: bool = False
    usage_unknown_requests: int = 0
    outcome: str = ""
    error: str | None = None


class BackendError(Exception):
    """A user-safe error. Do not include provider response bodies or secrets."""


class Canceled(BackendError):
    pass


class ProviderTransientError(BackendError):
    pass
