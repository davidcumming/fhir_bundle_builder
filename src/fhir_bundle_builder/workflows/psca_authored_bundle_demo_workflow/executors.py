"""Thin Dev UI wrapper executors for authored-input bundle demonstration."""

from __future__ import annotations

from typing import Any

from agent_framework import WorkflowContext, executor

from fhir_bundle_builder.authoring import (
    AuthoredBundleBuildInput,
    build_patient_authored_record,
    build_provider_authored_record,
    prepare_authored_bundle_build_input,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.workflow import workflow as bundle_builder_workflow

from .models import (
    AuthoredBundleDemoFinalSummary,
    AuthoredBundleDemoInput,
    AuthoredBundleDemoRunResult,
    AuthoredBundleDemoStageResult,
)

WORKFLOW_NAME = "PS-CA Authored Bundle Demo Flow"
WORKFLOW_VERSION = "0.1.0"
STAGE_ORDER = [
    "patient_authoring",
    "provider_authoring",
    "authored_bundle_preparation",
    "bundle_builder_run",
]


def _store_artifact(ctx: WorkflowContext[Any], key: str, artifact: Any) -> None:
    ctx.set_state(key, artifact)


def _get_artifact(ctx: WorkflowContext[Any], key: str) -> Any:
    artifact = ctx.get_state(key)
    if artifact is None:
        raise RuntimeError(f"Missing workflow state for '{key}'.")
    return artifact


@executor(
    id="patient_authoring",
    input=AuthoredBundleDemoInput,
    output=AuthoredBundleDemoStageResult,
)
async def patient_authoring(
    message: AuthoredBundleDemoInput,
    ctx: WorkflowContext[AuthoredBundleDemoStageResult],
) -> None:
    patient_record = build_patient_authored_record(message.patient_authoring)
    _store_artifact(ctx, "demo_input", message)
    _store_artifact(ctx, "patient_record", patient_record)
    await ctx.send_message(
        AuthoredBundleDemoStageResult(
            stage_id="patient_authoring",
            status="placeholder_complete",
            summary="Built a bounded authored patient record from natural-language input for the Dev UI demo flow.",
            placeholder_note=(
                "This wrapper flow still uses the existing offline/demo patient authoring foundation and "
                "does not introduce persistence, live model-backed authoring, or UI-managed patient libraries."
            ),
            source_refs=["authoring.patient_builder"],
            demo_input=message,
            patient_record=patient_record,
        )
    )


@executor(
    id="provider_authoring",
    input=AuthoredBundleDemoStageResult,
    output=AuthoredBundleDemoStageResult,
)
async def provider_authoring(
    message: AuthoredBundleDemoStageResult,
    ctx: WorkflowContext[AuthoredBundleDemoStageResult],
) -> None:
    provider_record = build_provider_authored_record(message.demo_input.provider_authoring)
    _store_artifact(ctx, "provider_record", provider_record)
    await ctx.send_message(
        AuthoredBundleDemoStageResult(
            stage_id="provider_authoring",
            status="placeholder_complete",
            summary="Built a bounded authored provider record from natural-language input for the Dev UI demo flow.",
            placeholder_note=(
                "This wrapper flow still uses the existing offline/demo provider authoring foundation and "
                "does not invent provider-directory data, persistence, or research-backed enrichment."
            ),
            source_refs=["authoring.provider_builder"],
            demo_input=message.demo_input,
            patient_record=_get_artifact(ctx, "patient_record"),
            provider_record=provider_record,
        )
    )


@executor(
    id="authored_bundle_preparation",
    input=AuthoredBundleDemoStageResult,
    output=AuthoredBundleDemoStageResult,
)
async def authored_bundle_preparation(
    message: AuthoredBundleDemoStageResult,
    ctx: WorkflowContext[AuthoredBundleDemoStageResult],
) -> None:
    preparation = prepare_authored_bundle_build_input(
        AuthoredBundleBuildInput(
            patient_record=_get_artifact(ctx, "patient_record"),
            provider_record=_get_artifact(ctx, "provider_record"),
            request=message.demo_input.request,
            specification=message.demo_input.specification,
            workflow_options=message.demo_input.workflow_options,
        )
    )
    _store_artifact(ctx, "preparation", preparation)
    await ctx.send_message(
        AuthoredBundleDemoStageResult(
            stage_id="authored_bundle_preparation",
            status="placeholder_complete",
            summary="Prepared one deterministic workflow-ready request from the authored patient and provider records.",
            placeholder_note=(
                "This wrapper flow composes the existing authored-input orchestration helper into the Dev UI path "
                "without widening the core bundle-builder workflow input contract."
            ),
            source_refs=[
                "authoring.patient_mapper",
                "authoring.provider_mapper",
                "authoring.authored_bundle_orchestration",
            ],
            demo_input=message.demo_input,
            patient_record=_get_artifact(ctx, "patient_record"),
            provider_record=_get_artifact(ctx, "provider_record"),
            preparation=preparation,
        )
    )


@executor(
    id="bundle_builder_run",
    input=AuthoredBundleDemoStageResult,
    workflow_output=AuthoredBundleDemoRunResult,
)
async def bundle_builder_run(
    message: AuthoredBundleDemoStageResult,
    ctx: WorkflowContext[Any, AuthoredBundleDemoRunResult],
) -> None:
    patient_record = _get_artifact(ctx, "patient_record")
    provider_record = _get_artifact(ctx, "provider_record")
    preparation = _get_artifact(ctx, "preparation")
    run_result = await bundle_builder_workflow.run(
        message=preparation.workflow_input,
        include_status_events=True,
    )
    outputs = run_result.get_outputs()
    workflow_output = outputs[0]
    final_summary = AuthoredBundleDemoFinalSummary(
        scenario_label=preparation.workflow_input.request.scenario_label,
        patient_record_id=patient_record.record_id,
        provider_record_id=provider_record.record_id,
        overall_validation_status=workflow_output.validation_report.overall_status,
        workflow_validation_status=workflow_output.validation_report.workflow_validation.status,
        candidate_bundle_entry_count=workflow_output.candidate_bundle.candidate_bundle.entry_count,
        has_selected_provider_role_relationship=(
            workflow_output.normalized_request.provider_context.selected_provider_role_relationship is not None
        ),
    )
    await ctx.yield_output(
        AuthoredBundleDemoRunResult(
            workflow_name=WORKFLOW_NAME,
            workflow_version=WORKFLOW_VERSION,
            stage_order=STAGE_ORDER,
            demo_input=message.demo_input,
            patient_record=patient_record,
            provider_record=provider_record,
            preparation=preparation,
            final_summary=final_summary,
            workflow_output=workflow_output,
        )
    )
