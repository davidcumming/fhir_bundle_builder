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
ProviderContextAlignmentMode = Literal[
    "structured_provider_context",
    "fallback_placeholder",
    "not_applicable",
]


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


class TraceabilityDrivingInput(BaseModel):
    """One compact provenance pointer for a placeholder/resource trace summary."""

    source_artifact: str
    source_detail: str


class PlaceholderTraceabilitySummary(BaseModel):
    """Compact end-to-end trace summary for one current workflow placeholder/resource."""

    placeholder_id: str
    resource_type: str
    role: str
    section_keys: list[str] = Field(default_factory=list)
    driving_inputs: list[TraceabilityDrivingInput] = Field(default_factory=list)
    source_step_ids: list[str] = Field(default_factory=list)
    latest_step_id: str | None = None
    bundle_entry_sequence: int | None = None
    bundle_entry_path: str | None = None
    full_url: str | None = None
    workflow_check_codes: list[str] = Field(default_factory=list)


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


class ProviderContextAlignmentEvidence(BaseModel):
    """Expected support-resource content derived from normalized provider context."""

    normalization_mode: str
    provider_id: str
    provider_display_name: str
    organization_alignment_mode: ProviderContextAlignmentMode
    selected_organization_identifier_system_expected: str | None = None
    selected_organization_id_expected: str | None = None
    selected_organization_display_name_expected: str | None = None
    practitionerrole_alignment_mode: ProviderContextAlignmentMode
    selected_provider_role_relationship_identifier_system_expected: str | None = None
    selected_provider_role_relationship_id_expected: str | None = None
    expected_role_label: str


class ValidationEvidence(BaseModel):
    """Provenance for the validation stage."""

    source_candidate_bundle_stage_id: str
    source_schematic_stage_id: str
    source_build_plan_stage_id: str
    source_resource_construction_stage_id: str
    validated_bundle_id: str
    patient_context_alignment: PatientContextAlignmentEvidence
    provider_context_alignment: ProviderContextAlignmentEvidence
    placeholder_traceability_summaries: list[PlaceholderTraceabilitySummary] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
