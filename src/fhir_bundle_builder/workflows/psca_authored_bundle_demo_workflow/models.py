"""Typed models for the thin Dev UI-facing authored-input demo workflow."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from fhir_bundle_builder.authoring import (
    AuthoredBundleBuildPreparation,
    PatientAuthoringInput,
    PatientAuthoredRecord,
    PatientAuthoredRecordRefinementResult,
    PatientAuthoredRecordReviewEditInput,
    ProviderAuthoringInput,
    ProviderAuthoredRecord,
    ProviderAuthoredRecordRefinementResult,
    ProviderAuthoredRecordReviewEditInput,
)
from fhir_bundle_builder.validation.models import ValidationStatus
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.models import (
    BundleRequestInput,
    SpecificationSelection,
    StageArtifact,
    WorkflowOptionsInput,
    WorkflowSkeletonRunResult,
)

ProviderPathMode = Literal["rich", "thin"]


class AuthoredBundleDemoInput(BaseModel):
    """Top-level Dev UI input for the authored-input demo flow."""

    patient_authoring: PatientAuthoringInput
    provider_authoring: ProviderAuthoringInput
    patient_review_edits: PatientAuthoredRecordReviewEditInput | None = None
    provider_review_edits: ProviderAuthoredRecordReviewEditInput | None = None
    request: BundleRequestInput
    specification: SpecificationSelection = Field(default_factory=SpecificationSelection)
    workflow_options: WorkflowOptionsInput = Field(default_factory=WorkflowOptionsInput)


class AuthoredPatientRecordOverview(BaseModel):
    """Compact authored patient summary for quick Dev UI scanning."""

    display_name: str
    condition_count: int
    medication_count: int
    allergy_count: int
    unresolved_gap_count: int
    has_residence_text: bool
    has_smoking_status_text: bool


class AuthoredProviderRecordOverview(BaseModel):
    """Compact authored provider summary for quick Dev UI scanning."""

    display_name: str
    organization_count: int
    provider_role_relationship_count: int
    provider_path_mode: ProviderPathMode
    unresolved_gap_count: int


class AuthoredRecordRefinementOverview(BaseModel):
    """Compact delta summary for authored-record refinement."""

    patient_edits_applied: bool
    provider_edits_applied: bool
    patient_edited_field_count: int
    provider_edited_field_count: int
    patient_refined_record_id: str
    provider_refined_record_id: str


class AuthoredBundlePreparationOverview(BaseModel):
    """Compact mapping/preparation summary for quick Dev UI scanning."""

    mapped_condition_count: int
    mapped_medication_count: int
    mapped_allergy_count: int
    mapped_organization_count: int
    mapped_provider_role_relationship_count: int
    patient_unmapped_field_count: int
    provider_unmapped_field_count: int
    provider_path_mode: ProviderPathMode
    has_selected_provider_role_relationship: bool


class AuthoredBundleDemoFinalSummary(BaseModel):
    """Compact final summary for quick Dev UI inspection."""

    scenario_label: str
    patient_record_id: str
    provider_record_id: str
    provider_path_mode: ProviderPathMode
    overall_validation_status: ValidationStatus
    workflow_validation_status: ValidationStatus
    candidate_bundle_entry_count: int
    patient_unmapped_field_count: int
    provider_unmapped_field_count: int
    patient_edits_applied: bool
    provider_edits_applied: bool
    has_selected_provider_role_relationship: bool


class AuthoredBundleDemoStageResult(StageArtifact):
    """Progressive wrapper-workflow stage artifact."""

    demo_input: AuthoredBundleDemoInput
    original_patient_record: PatientAuthoredRecord | None = None
    original_provider_record: ProviderAuthoredRecord | None = None
    patient_record: PatientAuthoredRecord | None = None
    provider_record: ProviderAuthoredRecord | None = None
    patient_overview: AuthoredPatientRecordOverview | None = None
    provider_overview: AuthoredProviderRecordOverview | None = None
    patient_refinement: PatientAuthoredRecordRefinementResult | None = None
    provider_refinement: ProviderAuthoredRecordRefinementResult | None = None
    refinement_overview: AuthoredRecordRefinementOverview | None = None
    preparation: AuthoredBundleBuildPreparation | None = None
    preparation_overview: AuthoredBundlePreparationOverview | None = None
    workflow_output: WorkflowSkeletonRunResult | None = None
    final_summary: AuthoredBundleDemoFinalSummary | None = None


class AuthoredBundleDemoRunResult(BaseModel):
    """Final nested output for the authored-input demo workflow."""

    workflow_name: str
    workflow_version: str
    stage_order: list[str]
    demo_input: AuthoredBundleDemoInput
    original_patient_record: PatientAuthoredRecord
    original_provider_record: ProviderAuthoredRecord
    patient_record: PatientAuthoredRecord
    provider_record: ProviderAuthoredRecord
    patient_overview: AuthoredPatientRecordOverview
    provider_overview: AuthoredProviderRecordOverview
    patient_refinement: PatientAuthoredRecordRefinementResult
    provider_refinement: ProviderAuthoredRecordRefinementResult
    refinement_overview: AuthoredRecordRefinementOverview
    preparation: AuthoredBundleBuildPreparation
    preparation_overview: AuthoredBundlePreparationOverview
    final_summary: AuthoredBundleDemoFinalSummary
    workflow_output: WorkflowSkeletonRunResult
