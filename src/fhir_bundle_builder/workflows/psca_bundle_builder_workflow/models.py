"""Typed models for the PS-CA workflow skeleton."""

from __future__ import annotations

from typing import Any
from typing import Literal

from pydantic import BaseModel, Field

from fhir_bundle_builder.specifications.psca import PscaNormalizedAssetContext
from fhir_bundle_builder.validation.models import (
    StandardsValidationResult,
    ValidationChannel,
    ValidationEvidence,
    ValidationSeverity,
    ValidationStatus,
    WorkflowValidationResult,
)


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
    validation_mode: Literal["foundational_dual_channel"]
    resource_construction_mode: Literal["deterministic_content_enriched_foundation"]


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


class BundleScaffold(BaseModel):
    """Bundle-level scaffold for the schematic artifact."""

    profile_url: str
    bundle_type: str
    required_entry_placeholder_ids: list[str]
    required_later_fields: list[str] = Field(default_factory=list)


class CompositionScaffold(BaseModel):
    """Composition-level scaffold for the schematic artifact."""

    placeholder_id: str
    profile_url: str
    expected_type_system: str
    expected_type_code: str
    expected_type_display: str
    required_later_fields: list[str] = Field(default_factory=list)


class SectionScaffold(BaseModel):
    """One explicit Composition section scaffold."""

    section_key: str
    slice_name: str
    title: str
    loinc_code: str
    required: bool
    allowed_resource_types: list[str] = Field(default_factory=list)
    entry_placeholder_ids: list[str] = Field(default_factory=list)


class ResourcePlaceholder(BaseModel):
    """Placeholder bundle component required by the schematic."""

    placeholder_id: str
    resource_type: str
    role: str
    profile_url: str | None = None
    required: bool = True
    section_keys: list[str] = Field(default_factory=list)
    required_later_fields: list[str] = Field(default_factory=list)


class SchematicRelationship(BaseModel):
    """Explicit relationship captured in the schematic."""

    relationship_id: str
    relationship_type: str
    source_id: str
    target_id: str
    reference_path: str | None = None
    description: str


class SchematicEvidence(BaseModel):
    """Provenance captured for the generated schematic."""

    selected_example_filename: str
    selected_example_section_titles: list[str] = Field(default_factory=list)
    selected_example_entry_resource_types: list[str] = Field(default_factory=list)
    used_profile_ids: list[str] = Field(default_factory=list)
    used_section_slice_names: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)


class BundleSchematic(StageArtifact):
    """Structured PS-CA bundle scaffold for downstream planning."""

    generation_basis: Literal["deterministic_psca_foundation_rules"]
    bundle_scaffold: BundleScaffold
    composition_scaffold: CompositionScaffold
    section_scaffolds: list[SectionScaffold]
    resource_placeholders: list[ResourcePlaceholder]
    relationships: list[SchematicRelationship]
    evidence: SchematicEvidence
    omitted_optional_sections: list[str] = Field(default_factory=list)


BuildStepKind = Literal[
    "anchor_resource",
    "support_resource",
    "section_entry_resource",
    "composition_scaffold",
    "composition_finalize",
]
BuildStepDependencyType = Literal[
    "requires_reference_handle",
    "requires_scaffold_ready",
    "requires_section_entries_attached",
]


class BuildStepDependency(BaseModel):
    """Explicit prerequisite relationship for one build step."""

    prerequisite_step_id: str
    dependency_type: BuildStepDependencyType
    reason: str


class BuildStepInput(BaseModel):
    """Expected input context for one build step."""

    input_key: str
    input_type: str
    required: bool
    description: str


class BuildStepOutput(BaseModel):
    """Expected output artifact from one build step."""

    output_key: str
    output_type: str
    description: str


class BuildPlanStep(BaseModel):
    """Ordered resource build step derived from the schematic."""

    step_id: str
    sequence: int
    step_kind: BuildStepKind
    target_placeholder_id: str
    resource_type: str
    profile_url: str | None = None
    owning_section_key: str | None = None
    build_purpose: str
    dependencies: list[BuildStepDependency] = Field(default_factory=list)
    expected_inputs: list[BuildStepInput] = Field(default_factory=list)
    expected_outputs: list[BuildStepOutput] = Field(default_factory=list)
    optional: bool = False


class BuildPlanEvidence(BaseModel):
    """Provenance for the build plan artifact."""

    source_schematic_stage_id: str
    source_schematic_generation_basis: str
    planned_placeholder_ids: list[str] = Field(default_factory=list)
    planned_section_keys: list[str] = Field(default_factory=list)
    relationship_ids_used: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)


class BuildPlan(StageArtifact):
    """Structured PS-CA build plan for downstream resource construction."""

    plan_basis: Literal["deterministic_schematic_dependency_plan"]
    composition_strategy: Literal["two_step_scaffold_then_finalize"]
    steps: list[BuildPlanStep]
    deferred_items: list[str] = Field(default_factory=list)
    evidence: BuildPlanEvidence


ResourceConstructionMode = Literal["deterministic_content_enriched"]
ResourceConstructionExecutionScope = Literal["full_build", "targeted_repair"]
ResourceConstructionRepairDirectiveScope = Literal["build_step_subset"]
ResourceConstructionRepairDirectiveBasis = Literal["validation_finding_code_map"]
ResourceConstructionExecutionStatus = Literal["scaffold_created", "scaffold_updated"]
ReferenceContributionStatus = Literal["applied"]
ResourceScaffoldState = Literal[
    "base_scaffold_created",
    "references_attached",
    "composition_scaffold_created",
    "sections_attached",
]


class ReferenceContribution(BaseModel):
    """Reference field contribution applied while constructing a scaffold."""

    reference_path: str
    target_placeholder_id: str
    reference_value: str
    status: ReferenceContributionStatus


class DeterministicValueEvidence(BaseModel):
    """Provenance for one deterministic populated field."""

    target_path: str
    source_artifact: str
    source_detail: str


class ResourceConstructionRepairDirective(BaseModel):
    """Deterministic directive for narrowing resource construction repair."""

    directive_basis: ResourceConstructionRepairDirectiveBasis
    scope: ResourceConstructionRepairDirectiveScope
    trigger_finding_codes: list[str] = Field(default_factory=list)
    target_step_ids: list[str] = Field(default_factory=list)
    target_placeholder_ids: list[str] = Field(default_factory=list)
    rationale: str


class ResourceScaffoldArtifact(BaseModel):
    """Partial FHIR-shaped scaffold for a constructed placeholder resource."""

    placeholder_id: str
    resource_type: str
    profile_url: str | None = None
    scaffold_state: ResourceScaffoldState
    fhir_scaffold: dict[str, Any]
    populated_paths: list[str] = Field(default_factory=list)
    deferred_paths: list[str] = Field(default_factory=list)
    source_step_ids: list[str] = Field(default_factory=list)


class ResourceConstructionStepResult(BaseModel):
    """Per-step construction result aligned to the build plan."""

    step_id: str
    step_kind: BuildStepKind
    resource_type: str
    target_placeholder_id: str
    execution_status: ResourceConstructionExecutionStatus
    resource_scaffold: ResourceScaffoldArtifact
    reference_contributions: list[ReferenceContribution] = Field(default_factory=list)
    deterministic_value_evidence: list[DeterministicValueEvidence] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    unresolved_fields: list[str] = Field(default_factory=list)


class ResourceRegistryEntry(BaseModel):
    """Latest scaffold state for a constructed placeholder resource."""

    placeholder_id: str
    resource_type: str
    latest_step_id: str
    current_scaffold: ResourceScaffoldArtifact


class ResourceConstructionEvidence(BaseModel):
    """Provenance for the resource construction stage."""

    source_build_plan_stage_id: str
    source_build_plan_basis: str
    source_schematic_stage_id: str
    planned_step_ids: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)


class ResourceConstructionStageResult(StageArtifact):
    """Structured scaffold-oriented outputs from the resource construction stage."""

    construction_mode: ResourceConstructionMode
    execution_scope: ResourceConstructionExecutionScope = "full_build"
    applied_repair_directive: ResourceConstructionRepairDirective | None = None
    regenerated_placeholder_ids: list[str] = Field(default_factory=list)
    reused_placeholder_ids: list[str] = Field(default_factory=list)
    step_results: list[ResourceConstructionStepResult]
    step_result_history: list[ResourceConstructionStepResult] = Field(default_factory=list)
    resource_registry: list[ResourceRegistryEntry]
    deferred_items: list[str] = Field(default_factory=list)
    unresolved_items: list[str] = Field(default_factory=list)
    evidence: ResourceConstructionEvidence


CandidateBundleAssemblyMode = Literal["deterministic_registry_bundle_scaffold"]
CandidateBundleState = Literal["candidate_scaffold_assembled"]


class BundleEntryAssemblyResult(BaseModel):
    """Deterministic assembly metadata for one bundle entry."""

    sequence: int
    placeholder_id: str
    resource_type: str
    full_url: str
    required_by_bundle_scaffold: bool
    source_registry_step_id: str
    scaffold_state: ResourceScaffoldState
    entry_path: str


class CandidateBundleArtifact(BaseModel):
    """Candidate bundle scaffold assembled from constructed resource scaffolds."""

    bundle_id: str
    profile_url: str
    bundle_type: str
    bundle_state: CandidateBundleState
    entry_count: int
    fhir_bundle: dict[str, Any]
    populated_paths: list[str] = Field(default_factory=list)
    deferred_paths: list[str] = Field(default_factory=list)
    deterministic_value_evidence: list[DeterministicValueEvidence] = Field(default_factory=list)


class CandidateBundleEvidence(BaseModel):
    """Provenance for the candidate bundle stage."""

    source_resource_construction_stage_id: str
    source_schematic_stage_id: str
    source_build_plan_stage_id: str
    required_entry_placeholder_ids: list[str] = Field(default_factory=list)
    ordered_placeholder_ids: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)


class CandidateBundleResult(StageArtifact):
    """Structured bundle-finalization artifact for the candidate bundle scaffold."""

    assembly_mode: CandidateBundleAssemblyMode
    candidate_bundle: CandidateBundleArtifact
    entry_assembly: list[BundleEntryAssemblyResult]
    deferred_items: list[str] = Field(default_factory=list)
    unresolved_items: list[str] = Field(default_factory=list)
    evidence: CandidateBundleEvidence


class ValidationReport(StageArtifact):
    """Structured validation report with separated standards and workflow channels."""

    overall_status: ValidationStatus
    standards_validation: StandardsValidationResult
    workflow_validation: WorkflowValidationResult
    error_count: int
    warning_count: int
    information_count: int
    deferred_validation_areas: list[str] = Field(default_factory=list)
    evidence: ValidationEvidence


RepairOverallDecision = Literal[
    "complete_no_repair_needed",
    "repair_recommended",
    "external_validation_pending",
    "human_review_recommended",
]
RepairRouteTarget = Literal[
    "none_required",
    "resource_construction",
    "bundle_finalization",
    "build_plan_or_schematic",
    "standards_validation_external",
    "human_intervention",
]
RepairRecommendedNextStage = Literal["none", "resource_construction", "bundle_finalization", "build_plan"]


class RepairFindingRoute(BaseModel):
    """Deterministic routing recommendation for one validation finding."""

    channel: ValidationChannel
    severity: ValidationSeverity
    finding_code: str
    route_target: RepairRouteTarget
    recommended_next_stage: RepairRecommendedNextStage
    actionable: bool
    reason: str


class RepairDecisionEvidence(BaseModel):
    """Provenance for the repair decision stage."""

    source_validation_stage_id: str
    source_overall_validation_status: ValidationStatus
    routed_finding_codes: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)


class RepairDecisionResult(StageArtifact):
    """Structured repair decision and routing recommendation."""

    overall_decision: RepairOverallDecision
    recommended_target: RepairRouteTarget
    recommended_next_stage: RepairRecommendedNextStage
    recommended_resource_construction_repair_directive: ResourceConstructionRepairDirective | None = None
    finding_routes: list[RepairFindingRoute] = Field(default_factory=list)
    deferred_external_dependencies: list[str] = Field(default_factory=list)
    evidence: RepairDecisionEvidence
    rationale: str


RepairExecutionMode = Literal["single_targeted_retry_pass"]
RepairExecutionOutcome = Literal["executed", "deferred", "not_needed", "unsupported"]


class RepairExecutionEvidence(BaseModel):
    """Provenance for the repair execution stage."""

    source_repair_decision_stage_id: str
    source_validation_stage_id: str
    source_recommended_target: RepairRouteTarget
    source_overall_decision: RepairOverallDecision
    rerun_stage_ids: list[str] = Field(default_factory=list)
    regenerated_artifact_keys: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)


class RepairExecutionResult(StageArtifact):
    """Structured retry execution result for one bounded repair pass."""

    execution_mode: RepairExecutionMode
    execution_outcome: RepairExecutionOutcome
    retry_eligible: bool
    requested_target: RepairRouteTarget
    executed_target: RepairRouteTarget | None = None
    recommended_next_stage: RepairRecommendedNextStage
    attempt_count: int
    rerun_stage_ids: list[str] = Field(default_factory=list)
    regenerated_artifact_keys: list[str] = Field(default_factory=list)
    applied_resource_construction_repair_directive: ResourceConstructionRepairDirective | None = None
    post_retry_resource_construction: ResourceConstructionStageResult | None = None
    post_retry_candidate_bundle: CandidateBundleResult | None = None
    post_retry_validation_report: ValidationReport | None = None
    post_retry_repair_decision: RepairDecisionResult | None = None
    deferred_reason: str | None = None
    unsupported_reason: str | None = None
    evidence: RepairExecutionEvidence
    rationale: str


class WorkflowSkeletonRunResult(BaseModel):
    """Final nested output yielded by the skeleton workflow."""

    workflow_name: str
    workflow_version: str
    stage_order: list[str]
    normalized_request: NormalizedBuildRequest
    specification_asset_context: SpecificationAssetContext
    bundle_schematic: BundleSchematic
    build_plan: BuildPlan
    resource_construction: ResourceConstructionStageResult
    candidate_bundle: CandidateBundleResult
    validation_report: ValidationReport
    repair_decision: RepairDecisionResult
    repair_execution: RepairExecutionResult
