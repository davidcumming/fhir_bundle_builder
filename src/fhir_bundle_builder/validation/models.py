"""Shared validation types and request models."""

from __future__ import annotations

from typing import Any
from typing import Literal

from pydantic import BaseModel, Field

ValidationChannel = Literal["standards", "workflow"]
ValidationSeverity = Literal["information", "warning", "error"]
ValidationStatus = Literal["passed", "passed_with_warnings", "failed"]
StandardsValidatorMode = Literal["local_scaffold", "matchbox"]


class ValidationFinding(BaseModel):
    """One deterministic validation finding."""

    channel: ValidationChannel
    severity: ValidationSeverity
    code: str
    location: str
    message: str


class StandardsValidationRequest(BaseModel):
    """Validator-agnostic request for standards validation."""

    bundle_id: str
    bundle_json: dict[str, Any]
    bundle_profile_url: str
    specification_package_id: str
    specification_version: str


class StandardsValidationResult(BaseModel):
    """Result from the standards validation channel."""

    validator_id: str
    status: ValidationStatus
    requested_validator_mode: StandardsValidatorMode = "local_scaffold"
    attempted_validator_ids: list[str] = Field(default_factory=list)
    external_validation_executed: bool = False
    fallback_used: bool = False
    checks_run: list[str] = Field(default_factory=list)
    findings: list[ValidationFinding] = Field(default_factory=list)
    deferred_areas: list[str] = Field(default_factory=list)


class StandardsValidationConfig(BaseModel):
    """Runtime config for selecting the standards validator backend."""

    mode: StandardsValidatorMode = "local_scaffold"
    matchbox_base_url: str | None = None
    timeout_seconds: float = 10.0


class WorkflowValidationResult(BaseModel):
    """Result from deterministic workflow/business-rule validation."""

    status: ValidationStatus
    checks_run: list[str] = Field(default_factory=list)
    findings: list[ValidationFinding] = Field(default_factory=list)
    deferred_areas: list[str] = Field(default_factory=list)


class ValidationEvidence(BaseModel):
    """Provenance for the validation stage."""

    source_candidate_bundle_stage_id: str
    source_schematic_stage_id: str
    source_build_plan_stage_id: str
    source_resource_construction_stage_id: str
    validated_bundle_id: str
    source_refs: list[str] = Field(default_factory=list)
