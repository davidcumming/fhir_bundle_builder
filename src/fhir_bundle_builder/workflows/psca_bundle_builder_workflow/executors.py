"""Deterministic placeholder executors for the PS-CA workflow skeleton."""

from __future__ import annotations

from typing import Any

from agent_framework import WorkflowContext, executor

from fhir_bundle_builder.specifications.psca import PscaAssetQuery, PscaAssetRepository

from .models import (
    BuildPlanStep,
    BuildPlanStub,
    BundleSchematicStub,
    CandidateBundleEntry,
    CandidateBundleStub,
    NormalizedBuildRequest,
    PlaceholderResourceBuildResult,
    RepairDecisionStub,
    ResourceConstructionStageResult,
    ResourcePlaceholder,
    SpecificationAssetContext,
    ValidationFindingStub,
    ValidationReportStub,
    WorkflowBuildInput,
    WorkflowDefaults,
    WorkflowSkeletonRunResult,
)

WORKFLOW_NAME = "PS-CA Bundle Builder Skeleton"
WORKFLOW_VERSION = "0.1.0"
STAGE_ORDER = [
    "request_normalization",
    "specification_asset_retrieval",
    "bundle_schematic",
    "build_plan",
    "resource_construction",
    "bundle_finalization",
    "validation",
    "repair_decision",
]

_PSCA_ASSET_REPOSITORY = PscaAssetRepository()


def _store_artifact(ctx: WorkflowContext[Any], key: str, artifact: Any) -> None:
    ctx.set_state(key, artifact)


def _get_artifact(ctx: WorkflowContext[Any], key: str) -> Any:
    artifact = ctx.get_state(key)
    if artifact is None:
        raise RuntimeError(f"Missing workflow state for '{key}'.")
    return artifact


@executor(id="request_normalization", input=WorkflowBuildInput, output=NormalizedBuildRequest)
async def request_normalization(message: WorkflowBuildInput, ctx: WorkflowContext[NormalizedBuildRequest]) -> None:
    _store_artifact(ctx, "workflow_input", message)
    normalized = NormalizedBuildRequest(
        stage_id="request_normalization",
        status="placeholder_complete",
        summary="Validated the top-level workflow input and applied skeleton defaults.",
        placeholder_note="Uses deterministic defaults only; no profile retrieval or request interpretation is implemented yet.",
        source_refs=[],
        specification=message.specification,
        patient_profile=message.patient_profile,
        provider_profile=message.provider_profile,
        request=message.request,
        workflow_defaults=WorkflowDefaults(
            bundle_type="document",
            specification_mode="normalized-asset-foundation",
            validation_mode="placeholder",
            resource_construction_mode="placeholder",
        ),
        run_label=f"{message.request.scenario_label}:{message.specification.package_id}:{message.specification.version}",
    )
    _store_artifact(ctx, "normalized_request", normalized)
    await ctx.send_message(normalized)


@executor(
    id="specification_asset_retrieval",
    input=NormalizedBuildRequest,
    output=SpecificationAssetContext,
)
async def specification_asset_retrieval(
    message: NormalizedBuildRequest,
    ctx: WorkflowContext[SpecificationAssetContext],
) -> None:
    workflow_input = ctx.get_state("workflow_input")
    normalized_assets = _PSCA_ASSET_REPOSITORY.load_foundation_context(
        PscaAssetQuery(
            package_id=message.specification.package_id,
            version=message.specification.version,
            include_example_inventory=workflow_input.workflow_options.include_example_bundle_inventory,
            selected_example_bundle_filename=workflow_input.workflow_options.example_bundle_filename,
        )
    )

    context = SpecificationAssetContext(
        stage_id="specification_asset_retrieval",
        status="placeholder_complete",
        summary="Loaded the first normalized PS-CA asset context through the specification retrieval boundary.",
        placeholder_note="This is the foundation normalization slice only; deeper profile semantics, terminology, and dependency extraction are still deferred.",
        source_refs=normalized_assets.source_refs,
        normalized_assets=normalized_assets,
    )
    _store_artifact(ctx, "specification_asset_context", context)
    await ctx.send_message(context)


@executor(id="bundle_schematic", input=SpecificationAssetContext, output=BundleSchematicStub)
async def bundle_schematic(
    message: SpecificationAssetContext,
    ctx: WorkflowContext[BundleSchematicStub],
) -> None:
    example_types = message.normalized_assets.selected_bundle_example.entry_resource_types
    composition_profile_url = message.normalized_assets.selected_profiles.composition.url
    placeholder_resources = [
        ResourcePlaceholder(
            logical_id=f"{resource_type.lower()}-{index}",
            resource_type=resource_type,
            role="example-derived-placeholder",
            profile_hint=composition_profile_url if resource_type == "Composition" else None,
        )
        for index, resource_type in enumerate(example_types[:8], start=1)
    ]
    schematic = BundleSchematicStub(
        stage_id="bundle_schematic",
        status="placeholder_complete",
        summary="Created a structured placeholder bundle scaffold from the inspected package metadata.",
        placeholder_note="This is a schematic stub only; no real PS-CA section logic or profile reasoning is implemented.",
        source_refs=message.source_refs,
        bundle_type="document",
        composition_profile_url=composition_profile_url,
        placeholder_resources=placeholder_resources,
        schematic_notes=[
            "Bundle type is fixed to 'document' for the first workflow slice.",
            "Placeholder resources are derived from the normalized selected bundle example.",
        ],
    )
    _store_artifact(ctx, "bundle_schematic", schematic)
    await ctx.send_message(schematic)


@executor(id="build_plan", input=BundleSchematicStub, output=BuildPlanStub)
async def build_plan(message: BundleSchematicStub, ctx: WorkflowContext[BuildPlanStub]) -> None:
    steps: list[BuildPlanStep] = []
    prior_step_id: str | None = None
    for sequence, placeholder in enumerate(message.placeholder_resources, start=1):
        step_id = f"build-{placeholder.logical_id}"
        depends_on = [prior_step_id] if prior_step_id and placeholder.resource_type != "Composition" else []
        steps.append(
            BuildPlanStep(
                step_id=step_id,
                sequence=sequence,
                resource_type=placeholder.resource_type,
                depends_on=depends_on,
                build_purpose=f"Emit inspectable placeholder output for {placeholder.resource_type}.",
                optional=False,
            )
        )
        prior_step_id = step_id

    plan = BuildPlanStub(
        stage_id="build_plan",
        status="placeholder_complete",
        summary="Derived a simple ordered placeholder build plan from the bundle schematic.",
        placeholder_note="Dependency handling is intentionally simplistic and deterministic for this workflow-shape slice.",
        source_refs=message.source_refs,
        plan_basis="example-derived-placeholder-sequence",
        steps=steps,
    )
    _store_artifact(ctx, "build_plan", plan)
    await ctx.send_message(plan)


@executor(
    id="resource_construction",
    input=BuildPlanStub,
    output=ResourceConstructionStageResult,
)
async def resource_construction(
    message: BuildPlanStub,
    ctx: WorkflowContext[ResourceConstructionStageResult],
) -> None:
    built_resources = [
        PlaceholderResourceBuildResult(
            step_id=step.step_id,
            resource_type=step.resource_type,
            placeholder_resource_id=f"{step.resource_type.lower()}-{step.sequence}",
            build_status="placeholder_created",
            assumptions=[
                "No clinical content was generated in this slice.",
                "Resource payloads are represented only by typed placeholder metadata.",
            ],
        )
        for step in message.steps
    ]
    result = ResourceConstructionStageResult(
        stage_id="resource_construction",
        status="placeholder_complete",
        summary="Produced placeholder per-resource build results for the ordered plan.",
        placeholder_note="This stage demonstrates ordered execution only; it does not build real FHIR resources yet.",
        source_refs=message.source_refs,
        built_resources=built_resources,
        unresolved_items=[
            "No element-level construction has been implemented.",
            "No reference registry or bundle patching logic exists yet.",
        ],
    )
    _store_artifact(ctx, "resource_construction", result)
    await ctx.send_message(result)


@executor(id="bundle_finalization", input=ResourceConstructionStageResult, output=CandidateBundleStub)
async def bundle_finalization(
    message: ResourceConstructionStageResult,
    ctx: WorkflowContext[CandidateBundleStub],
) -> None:
    normalized_request = _get_artifact(ctx, "normalized_request")
    entries = [
        CandidateBundleEntry(
            full_url=f"urn:uuid:{resource.placeholder_resource_id}",
            resource_type=resource.resource_type,
            placeholder_resource_id=resource.placeholder_resource_id,
        )
        for resource in message.built_resources
    ]
    candidate = CandidateBundleStub(
        stage_id="bundle_finalization",
        status="placeholder_complete",
        summary="Assembled a candidate bundle stub from the placeholder resource outputs.",
        placeholder_note="The candidate bundle contains inspectable placeholder entries only; it is not a valid PS-CA bundle.",
        source_refs=message.source_refs,
        bundle_id=f"{normalized_request.specification.package_id}-{normalized_request.request.scenario_label}",
        bundle_type=normalized_request.workflow_defaults.bundle_type,
        entry_count=len(entries),
        entries=entries,
    )
    _store_artifact(ctx, "candidate_bundle", candidate)
    await ctx.send_message(candidate)


@executor(id="validation", input=CandidateBundleStub, output=ValidationReportStub)
async def validation(message: CandidateBundleStub, ctx: WorkflowContext[ValidationReportStub]) -> None:
    report = ValidationReportStub(
        stage_id="validation",
        status="placeholder_warning",
        summary="Emitted a deterministic placeholder validation report for the candidate bundle stub.",
        placeholder_note="Validation logic is not implemented yet; findings here are explanatory placeholders only.",
        source_refs=message.source_refs,
        outcome="placeholder_pass_with_warnings",
        findings=[
            ValidationFindingStub(
                severity="information",
                location="Bundle",
                message="Validation is stubbed for the workflow skeleton slice; no structural or profile checks were executed.",
                repair_target="future-validation-logic",
            )
        ],
    )
    _store_artifact(ctx, "validation_report", report)
    await ctx.send_message(report)


@executor(
    id="repair_decision",
    input=ValidationReportStub,
    workflow_output=WorkflowSkeletonRunResult,
)
async def repair_decision(
    message: ValidationReportStub,
    ctx: WorkflowContext[Any, WorkflowSkeletonRunResult],
) -> None:
    decision = RepairDecisionStub(
        stage_id="repair_decision",
        status="placeholder_complete",
        summary="Marked the workflow slice complete because the goal is inspectable workflow shape, not bundle correctness.",
        placeholder_note="Future slices will replace this with structured repair routing driven by real validation output.",
        source_refs=message.source_refs,
        decision="complete_for_slice",
        next_stage="none",
        rationale="The first implementation slice is successful once the workflow runs end-to-end in Dev UI with inspectable structured artifacts.",
    )
    _store_artifact(ctx, "repair_decision", decision)
    await ctx.yield_output(
        WorkflowSkeletonRunResult(
            workflow_name=WORKFLOW_NAME,
            workflow_version=WORKFLOW_VERSION,
            stage_order=STAGE_ORDER,
            normalized_request=_get_artifact(ctx, "normalized_request"),
            specification_asset_context=_get_artifact(ctx, "specification_asset_context"),
            bundle_schematic=_get_artifact(ctx, "bundle_schematic"),
            build_plan=_get_artifact(ctx, "build_plan"),
            resource_construction=_get_artifact(ctx, "resource_construction"),
            candidate_bundle=_get_artifact(ctx, "candidate_bundle"),
            validation_report=_get_artifact(ctx, "validation_report"),
            repair_decision=decision,
        )
    )
