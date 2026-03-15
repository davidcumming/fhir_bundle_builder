"""Typed contracts for the thin authored-input bundle-build orchestration layer."""

from __future__ import annotations

from pydantic import BaseModel, Field

from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.models import (
    BundleRequestInput,
    SpecificationSelection,
    WorkflowBuildInput,
    WorkflowOptionsInput,
    WorkflowSkeletonRunResult,
)

from .patient_models import PatientAuthoredRecord, PatientAuthoringMapResult
from .provider_models import ProviderAuthoredRecord, ProviderAuthoringMapResult


class AuthoredBundleBuildInput(BaseModel):
    """Composed authored-input request for one bundle-generation run."""

    patient_record: PatientAuthoredRecord
    provider_record: ProviderAuthoredRecord
    request: BundleRequestInput
    specification: SpecificationSelection = Field(default_factory=SpecificationSelection)
    workflow_options: WorkflowOptionsInput = Field(default_factory=WorkflowOptionsInput)


class AuthoredBundleWorkflowInputSummary(BaseModel):
    """Compact deterministic summary of the composed workflow input."""

    patient_id: str
    provider_id: str
    mapped_condition_count: int
    mapped_medication_count: int
    mapped_allergy_count: int
    mapped_organization_count: int
    mapped_provider_role_relationship_count: int
    has_selected_provider_role_relationship: bool
    scenario_label: str


class AuthoredBundleBuildPreparation(BaseModel):
    """Inspectable preparation result before workflow execution."""

    source_patient_record_id: str
    source_provider_record_id: str
    patient_mapping: PatientAuthoringMapResult
    provider_mapping: ProviderAuthoringMapResult
    workflow_input: WorkflowBuildInput
    workflow_input_summary: AuthoredBundleWorkflowInputSummary


class AuthoredBundleBuildRunResult(BaseModel):
    """Thin authored-input orchestration result around the existing workflow."""

    preparation: AuthoredBundleBuildPreparation
    workflow_output: WorkflowSkeletonRunResult
