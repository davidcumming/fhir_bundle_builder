"""Typed models for the PS-CA workflow skeleton."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from fhir_bundle_builder.specifications.psca import PscaNormalizedAssetContext


class SpecificationSelection(BaseModel):
    """Top-level selection of the target implementation guide."""

    package_id: str = Field(
        default="ca.infoway.io.psca",
        description="FHIR package identifier for the target implementation guide.",
    )
    version: str = Field(
        default="2.1.1-DFT",
        description="Package version for the selected implementation guide.",
    )
    fhir_version: str = Field(
        default="4.0.1",
        description="FHIR core version expected by this package.",
    )


class ProfileReferenceInput(BaseModel):
    """Structured placeholder reference for a reusable profile."""

    profile_id: str = Field(
        ...,
        description="Stable identifier for the selected reusable profile.",
    )
    display_name: str = Field(
        ...,
        description="Human-readable label shown in Dev UI and traces.",
    )
    source_type: Literal["stub"] = Field(
        default="stub",
        description="Current profile source type for this workflow skeleton.",
    )


class BundleRequestInput(BaseModel):
    """Structured request details for the workflow run."""

    request_text: str = Field(
        ...,
        description="Natural-language request describing the intended PS-CA bundle scenario.",
    )
    bundle_intent: str = Field(
        default="PS-CA document bundle skeleton",
        description="Short label for the requested bundle intent.",
    )
    scenario_label: str = Field(
        default="initial-dev-ui-slice",
        description="Scenario label to make repeated Dev UI runs easier to identify.",
    )


class WorkflowOptionsInput(BaseModel):
    """Options that affect inspectability of the workflow run."""

    include_example_bundle_inventory: bool = Field(
        default=True,
        description="Whether to inspect one PS-CA example bundle and expose its entry inventory.",
    )
    example_bundle_filename: str = Field(
        default="Bundle1Example.json",
        description="The example bundle file to inspect for placeholder planning.",
    )
    emit_placeholder_warnings: bool = Field(
        default=True,
        description="Whether placeholder artifacts should include explicit stub warnings.",
    )


class WorkflowBuildInput(BaseModel):
    """Structured top-level workflow input."""

    specification: SpecificationSelection = Field(default_factory=SpecificationSelection)
    patient_profile: ProfileReferenceInput = Field(
        default_factory=lambda: ProfileReferenceInput(
            profile_id="patient-profile-stub",
            display_name="Default patient profile stub",
        )
    )
    provider_profile: ProfileReferenceInput = Field(
        default_factory=lambda: ProfileReferenceInput(
            profile_id="provider-profile-stub",
            display_name="Default provider profile stub",
        )
    )
    request: BundleRequestInput = Field(
        default_factory=lambda: BundleRequestInput(
            request_text="Create a placeholder PS-CA bundle workflow run for Dev UI inspection."
        )
    )
    workflow_options: WorkflowOptionsInput = Field(default_factory=WorkflowOptionsInput)


class StageArtifact(BaseModel):
    """Common inspectability fields for all stage artifacts."""

    stage_id: str
    status: Literal["placeholder_complete", "placeholder_warning"]
    summary: str
    placeholder_note: str
    source_refs: list[str] = Field(default_factory=list)


class WorkflowDefaults(BaseModel):
    """Defaults chosen during request normalization."""

    bundle_type: str
    specification_mode: Literal["normalized-asset-foundation"]
    validation_mode: Literal["placeholder"]
    resource_construction_mode: Literal["placeholder"]


class NormalizedBuildRequest(StageArtifact):
    """Deterministic normalized workflow request."""

    specification: SpecificationSelection
    patient_profile: ProfileReferenceInput
    provider_profile: ProfileReferenceInput
    request: BundleRequestInput
    workflow_defaults: WorkflowDefaults
    run_label: str


class SpecificationAssetContext(StageArtifact):
    """Workflow wrapper around the first normalized PS-CA asset context."""

    normalized_assets: PscaNormalizedAssetContext


class ResourcePlaceholder(BaseModel):
    """Placeholder bundle component for the skeleton schematic."""

    logical_id: str
    resource_type: str
    role: str
    profile_hint: str | None = None


class BundleSchematicStub(StageArtifact):
    """Structured bundle scaffold placeholder."""

    bundle_type: str
    composition_profile_url: str
    placeholder_resources: list[ResourcePlaceholder]
    schematic_notes: list[str]


class BuildPlanStep(BaseModel):
    """Ordered resource build step."""

    step_id: str
    sequence: int
    resource_type: str
    depends_on: list[str] = Field(default_factory=list)
    build_purpose: str
    optional: bool = False


class BuildPlanStub(StageArtifact):
    """Ordered placeholder build plan."""

    plan_basis: Literal["example-derived-placeholder-sequence"]
    steps: list[BuildPlanStep]


class PlaceholderResourceBuildResult(BaseModel):
    """Per-resource placeholder output for the construction stage."""

    step_id: str
    resource_type: str
    placeholder_resource_id: str
    build_status: Literal["placeholder_created"]
    assumptions: list[str] = Field(default_factory=list)


class ResourceConstructionStageResult(StageArtifact):
    """Placeholder outputs from the resource construction stage."""

    built_resources: list[PlaceholderResourceBuildResult]
    unresolved_items: list[str]


class CandidateBundleEntry(BaseModel):
    """Placeholder entry in the candidate bundle stub."""

    full_url: str
    resource_type: str
    placeholder_resource_id: str


class CandidateBundleStub(StageArtifact):
    """Bundle-in-progress / finalization placeholder artifact."""

    bundle_id: str
    bundle_type: str
    entry_count: int
    entries: list[CandidateBundleEntry]


class ValidationFindingStub(BaseModel):
    """Placeholder validation finding."""

    severity: Literal["information"]
    location: str
    message: str
    repair_target: Literal["future-validation-logic"]


class ValidationReportStub(StageArtifact):
    """Structured placeholder validation report."""

    outcome: Literal["placeholder_pass_with_warnings"]
    findings: list[ValidationFindingStub]


class RepairDecisionStub(StageArtifact):
    """Structured placeholder repair decision."""

    decision: Literal["complete_for_slice"]
    next_stage: Literal["none"]
    rationale: str


class WorkflowSkeletonRunResult(BaseModel):
    """Final nested output yielded by the skeleton workflow."""

    workflow_name: str
    workflow_version: str
    stage_order: list[str]
    normalized_request: NormalizedBuildRequest
    specification_asset_context: SpecificationAssetContext
    bundle_schematic: BundleSchematicStub
    build_plan: BuildPlanStub
    resource_construction: ResourceConstructionStageResult
    candidate_bundle: CandidateBundleStub
    validation_report: ValidationReportStub
    repair_decision: RepairDecisionStub
