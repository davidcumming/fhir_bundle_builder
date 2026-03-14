"""Deterministic placeholder executors for the PS-CA workflow skeleton."""

from __future__ import annotations

from typing import Any

from agent_framework import WorkflowContext, executor

from fhir_bundle_builder.specifications.psca import PscaAssetQuery, PscaAssetRepository

from .models import (
    BuildPlan,
    BundleSchematic,
    CandidateBundleEntry,
    CandidateBundleStub,
    NormalizedBuildRequest,
    RepairDecisionStub,
    ResourceConstructionStageResult,
    SpecificationAssetContext,
    ValidationFindingStub,
    ValidationReportStub,
    WorkflowBuildInput,
    WorkflowDefaults,
    WorkflowSkeletonRunResult,
)
from .build_plan_builder import build_psca_build_plan
from .resource_construction_builder import build_psca_resource_construction_result
from .schematic_builder import build_psca_bundle_schematic

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
            resource_construction_mode="scaffold_only_foundation",
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


@executor(id="bundle_schematic", input=SpecificationAssetContext, output=BundleSchematic)
async def bundle_schematic(
    message: SpecificationAssetContext,
    ctx: WorkflowContext[BundleSchematic],
) -> None:
    schematic = build_psca_bundle_schematic(message.normalized_assets)
    _store_artifact(ctx, "bundle_schematic", schematic)
    await ctx.send_message(schematic)


@executor(id="build_plan", input=BundleSchematic, output=BuildPlan)
async def build_plan(message: BundleSchematic, ctx: WorkflowContext[BuildPlan]) -> None:
    plan = build_psca_build_plan(message)
    _store_artifact(ctx, "build_plan", plan)
    await ctx.send_message(plan)


@executor(
    id="resource_construction",
    input=BuildPlan,
    output=ResourceConstructionStageResult,
)
async def resource_construction(
    message: BuildPlan,
    ctx: WorkflowContext[ResourceConstructionStageResult],
) -> None:
    schematic = _get_artifact(ctx, "bundle_schematic")
    result = build_psca_resource_construction_result(message, schematic)
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
            full_url=f"urn:uuid:{resource.placeholder_id}",
            resource_type=resource.resource_type,
            placeholder_resource_id=resource.placeholder_id,
            scaffold_state=resource.current_scaffold.scaffold_state,
            resource_scaffold=resource.current_scaffold.fhir_scaffold,
        )
        for resource in message.resource_registry
    ]
    candidate = CandidateBundleStub(
        stage_id="bundle_finalization",
        status="placeholder_complete",
        summary="Assembled a candidate bundle stub from the latest scaffold tracked for each placeholder resource.",
        placeholder_note="The candidate bundle contains inspectable scaffold artifacts only; multiple plan steps may refine the same placeholder resource before final assembly logic exists.",
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
