"""Deterministic single-pass repair execution for PS-CA workflow retries."""

from __future__ import annotations

from fhir_bundle_builder.validation import StandardsValidator

from .bundle_finalization_builder import build_psca_candidate_bundle_result
from .medication_request_agent import apply_medication_request_agent_to_construction_result
from .models import (
    BuildPlan,
    BundleSchematic,
    CandidateBundleResult,
    NormalizedBuildRequest,
    RepairDecisionResult,
    RepairExecutionEvidence,
    RepairExecutionResult,
    ResourceConstructionRepairDirective,
    ResourceConstructionStageResult,
    ValidationReport,
    WorkflowEffectiveOutcome,
)
from .repair_decision_builder import build_psca_repair_decision
from .resource_construction_builder import build_psca_resource_construction_result
from .validation_builder import build_psca_validation_report

_SUPPORTED_RETRY_TARGETS = {"resource_construction", "bundle_finalization"}
_BUNDLE_FINALIZATION_RETRY_STAGE_IDS = ["bundle_finalization", "validation", "repair_decision"]
_BUNDLE_FINALIZATION_REGENERATED_ARTIFACT_KEYS = ["candidate_bundle", "validation_report", "repair_decision"]
_RESOURCE_CONSTRUCTION_RETRY_STAGE_IDS = [
    "resource_construction",
    "bundle_finalization",
    "validation",
    "repair_decision",
]
_RESOURCE_CONSTRUCTION_REGENERATED_ARTIFACT_KEYS = [
    "resource_construction",
    "candidate_bundle",
    "validation_report",
    "repair_decision",
]


def build_psca_workflow_effective_outcome(
    resource_construction: ResourceConstructionStageResult,
    candidate_bundle: CandidateBundleResult,
    validation_report: ValidationReport,
    repair_decision: RepairDecisionResult,
    repair_execution: RepairExecutionResult,
) -> WorkflowEffectiveOutcome:
    """Resolve the canonical effective final artifact set after bounded retry execution."""

    if repair_execution.execution_outcome != "executed":
        return WorkflowEffectiveOutcome(
            artifact_source="initial_run",
            resource_construction=resource_construction,
            candidate_bundle=candidate_bundle,
            validation_report=validation_report,
            repair_decision=repair_decision,
        )

    if repair_execution.post_retry_candidate_bundle is None:
        raise RuntimeError("Executed retry is missing post-retry candidate bundle output.")
    if repair_execution.post_retry_validation_report is None:
        raise RuntimeError("Executed retry is missing post-retry validation report output.")
    if repair_execution.post_retry_repair_decision is None:
        raise RuntimeError("Executed retry is missing post-retry repair decision output.")

    if repair_execution.executed_target == "bundle_finalization":
        effective_resource_construction = resource_construction
    elif repair_execution.executed_target == "resource_construction":
        if repair_execution.post_retry_resource_construction is None:
            raise RuntimeError("Executed resource-construction retry is missing post-retry resource construction output.")
        effective_resource_construction = repair_execution.post_retry_resource_construction
    else:
        raise RuntimeError(
            f"Executed retry target '{repair_execution.executed_target}' does not have an effective-outcome resolution policy."
        )

    return WorkflowEffectiveOutcome(
        artifact_source="post_retry",
        resource_construction=effective_resource_construction,
        candidate_bundle=repair_execution.post_retry_candidate_bundle,
        validation_report=repair_execution.post_retry_validation_report,
        repair_decision=repair_execution.post_retry_repair_decision,
    )


async def build_psca_repair_execution_result(
    repair_decision: RepairDecisionResult,
    normalized_request: NormalizedBuildRequest,
    build_plan: BuildPlan,
    schematic: BundleSchematic,
    resource_construction: ResourceConstructionStageResult,
    standards_validator: StandardsValidator,
) -> RepairExecutionResult:
    """Execute one bounded retry pass from a structured repair recommendation."""

    requested_target = repair_decision.recommended_target
    evidence = RepairExecutionEvidence(
        source_repair_decision_stage_id=repair_decision.stage_id,
        source_validation_stage_id=repair_decision.evidence.source_validation_stage_id,
        source_recommended_target=requested_target,
        source_overall_decision=repair_decision.overall_decision,
        source_refs=repair_decision.source_refs,
    )

    if requested_target == "standards_validation_external":
        return RepairExecutionResult(
            stage_id="repair_execution",
            status="placeholder_warning",
            summary="Did not execute an internal retry because the current recommendation depends on external standards validation.",
            placeholder_note="This stage performs only bounded internal retries; external standards validation remains a deferred dependency.",
            source_refs=repair_decision.source_refs,
            execution_mode="single_targeted_retry_pass",
            execution_outcome="deferred",
            retry_eligible=False,
            requested_target=requested_target,
            executed_target=None,
            recommended_next_stage=repair_decision.recommended_next_stage,
            attempt_count=0,
            post_retry_resource_construction=None,
            deferred_reason="External standards validation has not been executed yet, so no internal retry is attempted in this slice.",
            evidence=evidence,
            rationale="The repair recommendation points to an external standards-validation dependency rather than an internal retryable workflow layer.",
        )

    if requested_target == "none_required":
        return RepairExecutionResult(
            stage_id="repair_execution",
            status="placeholder_complete",
            summary="No retry was executed because the repair recommendation indicates no internal repair is needed.",
            placeholder_note="This stage performs a bounded retry only when the repair decision recommends a supported internal target.",
            source_refs=repair_decision.source_refs,
            execution_mode="single_targeted_retry_pass",
            execution_outcome="not_needed",
            retry_eligible=False,
            requested_target=requested_target,
            executed_target=None,
            recommended_next_stage=repair_decision.recommended_next_stage,
            attempt_count=0,
            post_retry_resource_construction=None,
            evidence=evidence,
            rationale="The repair recommendation indicates no internal retry is needed for the current run.",
        )

    if repair_decision.overall_decision == "repair_recommended" and requested_target in _SUPPORTED_RETRY_TARGETS:
        if requested_target == "resource_construction":
            applied_repair_directive = repair_decision.recommended_resource_construction_repair_directive
            post_retry_resource_construction = build_psca_resource_construction_result(
                build_plan,
                schematic,
                normalized_request,
                prior_result=resource_construction,
                repair_directive=applied_repair_directive,
            )
            post_retry_resource_construction = await apply_medication_request_agent_to_construction_result(
                post_retry_resource_construction,
                normalized_request,
            )
            return await _build_executed_retry_result(
                repair_decision=repair_decision,
                normalized_request=normalized_request,
                schematic=schematic,
                construction_result=post_retry_resource_construction,
                standards_validator=standards_validator,
                rerun_stage_ids=_RESOURCE_CONSTRUCTION_RETRY_STAGE_IDS,
                regenerated_artifact_keys=_RESOURCE_CONSTRUCTION_REGENERATED_ARTIFACT_KEYS,
                summary=(
                    "Executed one bounded internal retry pass from resource construction and "
                    "regenerated all downstream artifacts."
                ),
                placeholder_note=(
                    "This stage reruns resource construction and its downstream stages once, "
                    "then stops even if the post-retry decision still recommends repair."
                ),
                rationale=(
                    "The repair recommendation targeted resource construction, so the retry "
                    "reran that deterministic stage and all of its downstream artifacts."
                ),
                applied_resource_construction_repair_directive=applied_repair_directive,
                post_retry_resource_construction=post_retry_resource_construction,
            )

        return await _build_executed_retry_result(
            repair_decision=repair_decision,
            normalized_request=normalized_request,
            schematic=schematic,
            construction_result=resource_construction,
            standards_validator=standards_validator,
            rerun_stage_ids=_BUNDLE_FINALIZATION_RETRY_STAGE_IDS,
            regenerated_artifact_keys=_BUNDLE_FINALIZATION_REGENERATED_ARTIFACT_KEYS,
            summary="Executed one bounded internal retry pass and regenerated downstream artifacts from the supported repair target.",
            placeholder_note="This stage reruns only the supported downstream slice once and stops even if the post-retry decision still recommends repair.",
            rationale="The repair recommendation targeted bundle finalization, which remains a supported internal retry layer in this slice.",
            applied_resource_construction_repair_directive=None,
            post_retry_resource_construction=None,
        )

    return RepairExecutionResult(
        stage_id="repair_execution",
        status="placeholder_warning",
        summary="Did not execute a retry because the current repair recommendation targets an unsupported internal layer for this slice.",
        placeholder_note="This stage supports only single-pass resource-construction and bundle-finalization retries; broader retry orchestration remains deferred.",
        source_refs=repair_decision.source_refs,
        execution_mode="single_targeted_retry_pass",
        execution_outcome="unsupported",
        retry_eligible=False,
        requested_target=requested_target,
        executed_target=None,
        recommended_next_stage=repair_decision.recommended_next_stage,
        attempt_count=0,
        post_retry_resource_construction=None,
        unsupported_reason=(
            f"Automatic retry for target '{requested_target}' is not supported in this slice; "
            "only resource_construction and bundle_finalization retries are executable."
        ),
        evidence=evidence,
        rationale="The repair recommendation points to a workflow layer that is intentionally unsupported for automatic retry in this bounded slice.",
    )


async def _build_executed_retry_result(
    repair_decision: RepairDecisionResult,
    normalized_request: NormalizedBuildRequest,
    schematic: BundleSchematic,
    construction_result: ResourceConstructionStageResult,
    standards_validator: StandardsValidator,
    rerun_stage_ids: list[str],
    regenerated_artifact_keys: list[str],
    summary: str,
    placeholder_note: str,
    rationale: str,
    applied_resource_construction_repair_directive: ResourceConstructionRepairDirective | None,
    post_retry_resource_construction: ResourceConstructionStageResult | None,
) -> RepairExecutionResult:
    post_retry_candidate_bundle = build_psca_candidate_bundle_result(
        construction_result,
        schematic,
        normalized_request,
    )
    post_retry_validation_report = await build_psca_validation_report(
        post_retry_candidate_bundle,
        schematic,
        normalized_request,
        standards_validator,
        construction_result,
    )
    post_retry_repair_decision = build_psca_repair_decision(post_retry_validation_report)

    return RepairExecutionResult(
        stage_id="repair_execution",
        status="placeholder_complete",
        summary=summary,
        placeholder_note=placeholder_note,
        source_refs=repair_decision.source_refs,
        execution_mode="single_targeted_retry_pass",
        execution_outcome="executed",
        retry_eligible=True,
        requested_target=repair_decision.recommended_target,
        executed_target=repair_decision.recommended_target,
        recommended_next_stage=repair_decision.recommended_next_stage,
        attempt_count=1,
        rerun_stage_ids=list(rerun_stage_ids),
        regenerated_artifact_keys=list(regenerated_artifact_keys),
        applied_resource_construction_repair_directive=applied_resource_construction_repair_directive,
        post_retry_resource_construction=post_retry_resource_construction,
        post_retry_candidate_bundle=post_retry_candidate_bundle,
        post_retry_validation_report=post_retry_validation_report,
        post_retry_repair_decision=post_retry_repair_decision,
        evidence=RepairExecutionEvidence(
            source_repair_decision_stage_id=repair_decision.stage_id,
            source_validation_stage_id=repair_decision.evidence.source_validation_stage_id,
            source_recommended_target=repair_decision.recommended_target,
            source_overall_decision=repair_decision.overall_decision,
            rerun_stage_ids=list(rerun_stage_ids),
            regenerated_artifact_keys=list(regenerated_artifact_keys),
            source_refs=repair_decision.source_refs,
        ),
        rationale=rationale,
    )
