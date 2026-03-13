"""Deterministic placeholder executors for the PS-CA workflow skeleton."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_framework import WorkflowContext, executor

from .models import (
    BuildPlanStep,
    BuildPlanStub,
    BundleSchematicStub,
    CandidateBundleEntry,
    CandidateBundleStub,
    ExampleBundleInventory,
    NormalizedBuildRequest,
    PlaceholderResourceBuildResult,
    RepairDecisionStub,
    ResourceConstructionStageResult,
    ResourcePlaceholder,
    ResourceTypeSummary,
    SpecificationAssetContextStub,
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

_REPO_ROOT = Path(__file__).resolve().parents[4]
_PACKAGE_ROOT = _REPO_ROOT / "fhir" / "ca.infoway.io.psca-2.1.1-dft"
_PACKAGE_JSON = _PACKAGE_ROOT / "package.json"
_INDEX_JSON = _PACKAGE_ROOT / ".index.json"
_BUNDLE_PROFILE = _PACKAGE_ROOT / "structuredefinition-profile-bundle-ca-ps.json"
_COMPOSITION_PROFILE = _PACKAGE_ROOT / "structuredefinition-profile-composition-ca-ps.json"


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _relative_ref(path: Path) -> str:
    return path.relative_to(_REPO_ROOT).as_posix()


def _store_artifact(ctx: WorkflowContext[Any], key: str, artifact: Any) -> None:
    ctx.set_state(key, artifact)


def _get_artifact(ctx: WorkflowContext[Any], key: str) -> Any:
    artifact = ctx.get_state(key)
    if artifact is None:
        raise RuntimeError(f"Missing workflow state for '{key}'.")
    return artifact


def _profile_summary(path: Path) -> ResourceTypeSummary:
    payload = _read_json(path)
    return ResourceTypeSummary(
        resource_type=payload["type"],
        profile_id=payload["id"],
        profile_url=payload["url"],
        filename=path.name,
    )


def _load_example_bundle_inventory(example_filename: str) -> ExampleBundleInventory:
    example_path = _PACKAGE_ROOT / "examples" / example_filename
    payload = _read_json(example_path)
    entry_types = [entry.get("resource", {}).get("resourceType", "Unknown") for entry in payload.get("entry", [])]
    return ExampleBundleInventory(
        filename=example_filename,
        entry_count=len(entry_types),
        entry_resource_types=entry_types,
    )


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
            specification_mode="raw-package-stub",
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
    output=SpecificationAssetContextStub,
)
async def specification_asset_retrieval(
    message: NormalizedBuildRequest,
    ctx: WorkflowContext[SpecificationAssetContextStub],
) -> None:
    package_payload = _read_json(_PACKAGE_JSON)
    index_payload = _read_json(_INDEX_JSON)
    bundle_profile = _profile_summary(_BUNDLE_PROFILE)
    composition_profile = _profile_summary(_COMPOSITION_PROFILE)
    example_inventory = None
    # Read the example bundle only when requested in the structured top-level options.
    workflow_input = ctx.get_state("workflow_input")
    if workflow_input and workflow_input.workflow_options.include_example_bundle_inventory:
        example_inventory = _load_example_bundle_inventory(workflow_input.workflow_options.example_bundle_filename)

    context = SpecificationAssetContextStub(
        stage_id="specification_asset_retrieval",
        status="placeholder_complete",
        summary="Loaded a minimal deterministic PS-CA package context from the repo.",
        placeholder_note="This stage reads raw package files directly for inspectability; normalized workflow assets are intentionally deferred to the next slice.",
        source_refs=[
            _relative_ref(_PACKAGE_JSON),
            _relative_ref(_INDEX_JSON),
            _relative_ref(_BUNDLE_PROFILE),
            _relative_ref(_COMPOSITION_PROFILE),
        ]
        + (
            [f"fhir/ca.infoway.io.psca-2.1.1-dft/examples/{example_inventory.filename}"]
            if example_inventory
            else []
        ),
        package_root=_relative_ref(_PACKAGE_ROOT),
        package_name=package_payload["name"],
        package_version=package_payload["version"],
        fhir_version=package_payload["fhirVersions"][0],
        canonical_url=package_payload["canonical"],
        index_entry_count=len(index_payload["files"]),
        bundle_profile=bundle_profile,
        composition_profile=composition_profile,
        example_bundle_inventory=example_inventory,
    )
    _store_artifact(ctx, "specification_asset_context", context)
    await ctx.send_message(context)


@executor(id="bundle_schematic", input=SpecificationAssetContextStub, output=BundleSchematicStub)
async def bundle_schematic(
    message: SpecificationAssetContextStub,
    ctx: WorkflowContext[BundleSchematicStub],
) -> None:
    example_types = message.example_bundle_inventory.entry_resource_types if message.example_bundle_inventory else []
    placeholder_resources = [
        ResourcePlaceholder(
            logical_id=f"{resource_type.lower()}-{index}",
            resource_type=resource_type,
            role="example-derived-placeholder",
            profile_hint=message.composition_profile.profile_url if resource_type == "Composition" else None,
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
        composition_profile_url=message.composition_profile.profile_url,
        placeholder_resources=placeholder_resources,
        schematic_notes=[
            "Bundle type is fixed to 'document' for the first workflow slice.",
            "Placeholder resources are derived from the selected example bundle inventory.",
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
