"""Typed models for the thin Dev UI-facing authored-input demo workflow."""

from __future__ import annotations

from pydantic import BaseModel, Field

from fhir_bundle_builder.authoring import (
    AuthoredBundleBuildPreparation,
    PatientAuthoringInput,
    PatientAuthoredRecord,
    ProviderAuthoringInput,
    ProviderAuthoredRecord,
)
from fhir_bundle_builder.validation.models import ValidationStatus
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.models import (
    BundleRequestInput,
    SpecificationSelection,
    StageArtifact,
    WorkflowOptionsInput,
    WorkflowSkeletonRunResult,
)


class AuthoredBundleDemoInput(BaseModel):
    """Top-level Dev UI input for the authored-input demo flow."""

    patient_authoring: PatientAuthoringInput
    provider_authoring: ProviderAuthoringInput
    request: BundleRequestInput
    specification: SpecificationSelection = Field(default_factory=SpecificationSelection)
    workflow_options: WorkflowOptionsInput = Field(default_factory=WorkflowOptionsInput)


class AuthoredBundleDemoFinalSummary(BaseModel):
    """Compact final summary for quick Dev UI inspection."""

    scenario_label: str
    patient_record_id: str
    provider_record_id: str
    overall_validation_status: ValidationStatus
    workflow_validation_status: ValidationStatus
    candidate_bundle_entry_count: int
    has_selected_provider_role_relationship: bool


class AuthoredBundleDemoStageResult(StageArtifact):
    """Progressive wrapper-workflow stage artifact."""

    demo_input: AuthoredBundleDemoInput
    patient_record: PatientAuthoredRecord | None = None
    provider_record: ProviderAuthoredRecord | None = None
    preparation: AuthoredBundleBuildPreparation | None = None
    workflow_output: WorkflowSkeletonRunResult | None = None
    final_summary: AuthoredBundleDemoFinalSummary | None = None


class AuthoredBundleDemoRunResult(BaseModel):
    """Final nested output for the authored-input demo workflow."""

    workflow_name: str
    workflow_version: str
    stage_order: list[str]
    demo_input: AuthoredBundleDemoInput
    patient_record: PatientAuthoredRecord
    provider_record: ProviderAuthoredRecord
    preparation: AuthoredBundleBuildPreparation
    final_summary: AuthoredBundleDemoFinalSummary
    workflow_output: WorkflowSkeletonRunResult
