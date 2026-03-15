"""Shared validation types and request models."""

from __future__ import annotations

from typing import Any
from typing import Literal

from pydantic import BaseModel, Field

ValidationChannel = Literal["standards", "workflow"]
ValidationSeverity = Literal["information", "warning", "error"]
ValidationStatus = Literal["passed", "passed_with_warnings", "failed"]
StandardsValidatorMode = Literal["local_scaffold", "matchbox"]
PatientContextAlignmentMode = Literal["structured_patient_context", "fallback_placeholder"]


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


class SectionEntryTextAlignmentExpectation(BaseModel):
    """Expected patient-context-derived text for one section-entry placeholder."""

    placeholder_id: str
    resource_type: str
    expected_text: str
    alignment_mode: PatientContextAlignmentMode
    source_artifact: str
    source_detail: str


class PatientContextAlignmentEvidence(BaseModel):
    """Expected bundle content derived from normalized patient context."""

    normalization_mode: str
    patient_id: str
    display_name: str
    administrative_gender_expected: str | None = None
    birth_date_expected: str | None = None
    section_entry_expectations: list[SectionEntryTextAlignmentExpectation] = Field(default_factory=list)


class ValidationEvidence(BaseModel):
    """Provenance for the validation stage."""

    source_candidate_bundle_stage_id: str
    source_schematic_stage_id: str
    source_build_plan_stage_id: str
    source_resource_construction_stage_id: str
    validated_bundle_id: str
    patient_context_alignment: PatientContextAlignmentEvidence
    source_refs: list[str] = Field(default_factory=list)
