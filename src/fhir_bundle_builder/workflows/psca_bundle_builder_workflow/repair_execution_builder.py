"""Deterministic single-pass repair execution for PS-CA workflow retries."""

from __future__ import annotations

from fhir_bundle_builder.validation import StandardsValidator

from .bundle_finalization_builder import build_psca_candidate_bundle_result
from .models import (
    BundleSchematic,
    NormalizedBuildRequest,
    RepairDecisionResult,
    RepairExecutionEvidence,
    RepairExecutionResult,
    ResourceConstructionStageResult,
)
from .repair_decision_builder import build_psca_repair_decision
from .validation_builder import build_psca_validation_report

_SUPPORTED_RETRY_TARGETS = {"bundle_finalization"}
_RETRY_STAGE_IDS = ["bundle_finalization", "validation", "repair_decision"]
_REGENERATED_ARTIFACT_KEYS = ["candidate_bundle", "validation_report", "repair_decision"]


async def build_psca_repair_execution_result(
    repair_decision: RepairDecisionResult,
    normalized_request: NormalizedBuildRequest,
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
            evidence=evidence,
            rationale="The repair recommendation indicates no internal retry is needed for the current run.",
        )

    if repair_decision.overall_decision == "repair_recommended" and requested_target in _SUPPORTED_RETRY_TARGETS:
        post_retry_candidate_bundle = build_psca_candidate_bundle_result(
            resource_construction,
            schematic,
            normalized_request,
        )
        post_retry_validation_report = await build_psca_validation_report(
            post_retry_candidate_bundle,
            schematic,
            normalized_request,
            standards_validator,
        )
        post_retry_repair_decision = build_psca_repair_decision(post_retry_validation_report)

        return RepairExecutionResult(
            stage_id="repair_execution",
            status="placeholder_complete",
            summary="Executed one bounded internal retry pass and regenerated downstream artifacts from the supported repair target.",
            placeholder_note="This stage reruns only the supported downstream slice once and stops even if the post-retry decision still recommends repair.",
            source_refs=repair_decision.source_refs,
            execution_mode="single_targeted_retry_pass",
            execution_outcome="executed",
            retry_eligible=True,
            requested_target=requested_target,
            executed_target=requested_target,
            recommended_next_stage=repair_decision.recommended_next_stage,
            attempt_count=1,
            rerun_stage_ids=list(_RETRY_STAGE_IDS),
            regenerated_artifact_keys=list(_REGENERATED_ARTIFACT_KEYS),
            post_retry_candidate_bundle=post_retry_candidate_bundle,
            post_retry_validation_report=post_retry_validation_report,
            post_retry_repair_decision=post_retry_repair_decision,
            evidence=RepairExecutionEvidence(
                source_repair_decision_stage_id=repair_decision.stage_id,
                source_validation_stage_id=repair_decision.evidence.source_validation_stage_id,
                source_recommended_target=requested_target,
                source_overall_decision=repair_decision.overall_decision,
                rerun_stage_ids=list(_RETRY_STAGE_IDS),
                regenerated_artifact_keys=list(_REGENERATED_ARTIFACT_KEYS),
                source_refs=repair_decision.source_refs,
            ),
            rationale="The repair recommendation targeted bundle finalization, which is the only supported internal retry layer in this slice.",
        )

    return RepairExecutionResult(
        stage_id="repair_execution",
        status="placeholder_warning",
        summary="Did not execute a retry because the current repair recommendation targets an unsupported internal layer for this slice.",
        placeholder_note="This stage supports only one bundle-finalization retry pass; broader retry orchestration remains deferred.",
        source_refs=repair_decision.source_refs,
        execution_mode="single_targeted_retry_pass",
        execution_outcome="unsupported",
        retry_eligible=False,
        requested_target=requested_target,
        executed_target=None,
        recommended_next_stage=repair_decision.recommended_next_stage,
        attempt_count=0,
        unsupported_reason=(
            f"Automatic retry for target '{requested_target}' is not supported in this slice; "
            "only bundle_finalization retries are executable."
        ),
        evidence=evidence,
        rationale="The repair recommendation points to a workflow layer that is intentionally unsupported for automatic retry in this bounded slice.",
    )
