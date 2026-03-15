"""Thin Dev UI wrapper executors for authored-input bundle demonstration."""

from __future__ import annotations

from typing import Any

from agent_framework import WorkflowContext, executor

from fhir_bundle_builder.authoring import (
    AuthoredBundleBuildInput,
    AuthoredBundleBuildPreparation,
    PatientAuthoredRecord,
    PatientAuthoredRecordRefinementResult,
    ProviderAuthoredRecord,
    ProviderAuthoredRecordRefinementResult,
    apply_patient_authored_record_review_edits,
    apply_provider_authored_record_review_edits,
    build_patient_authored_record,
    build_provider_authored_record,
    prepare_authored_bundle_build_input,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.workflow import workflow as bundle_builder_workflow

from .models import (
    AuthoredBundlePreparationOverview,
    AuthoredBundleDemoFinalSummary,
    AuthoredBundleDemoInput,
    AuthoredBundleDemoRunResult,
    AuthoredBundleDemoStageResult,
    AuthoredPatientRecordOverview,
    AuthoredProviderRecordOverview,
    AuthoredRecordRefinementOverview,
    ProviderPathMode,
)

WORKFLOW_NAME = "PS-CA Authored Bundle Demo Flow"
WORKFLOW_VERSION = "0.2.0"
STAGE_ORDER = [
    "patient_authoring",
    "provider_authoring",
    "authored_record_refinement",
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


def _provider_path_mode_from_record(record: ProviderAuthoredRecord) -> ProviderPathMode:
    return "rich" if record.organizations and record.provider_role_relationships else "thin"


def _provider_path_mode_from_preparation(preparation: AuthoredBundleBuildPreparation) -> ProviderPathMode:
    return (
        "rich"
        if preparation.provider_mapping.mapped_organization_count > 0
        and preparation.provider_mapping.mapped_provider_role_relationship_count > 0
        else "thin"
    )


def _build_patient_overview(record: PatientAuthoredRecord) -> AuthoredPatientRecordOverview:
    return AuthoredPatientRecordOverview(
        display_name=record.patient.display_name,
        condition_count=len(record.conditions),
        medication_count=len(record.medications),
        allergy_count=len(record.allergies),
        unresolved_gap_count=len(record.unresolved_authoring_gaps),
        has_residence_text=record.background_facts.residence_text is not None,
        has_smoking_status_text=record.background_facts.smoking_status_text is not None,
    )


def _build_provider_overview(record: ProviderAuthoredRecord) -> AuthoredProviderRecordOverview:
    return AuthoredProviderRecordOverview(
        display_name=record.provider.display_name,
        organization_count=len(record.organizations),
        provider_role_relationship_count=len(record.provider_role_relationships),
        provider_path_mode=_provider_path_mode_from_record(record),
        unresolved_gap_count=len(record.unresolved_authoring_gaps),
    )


def _build_refinement_overview(
    patient_refinement: PatientAuthoredRecordRefinementResult,
    provider_refinement: ProviderAuthoredRecordRefinementResult,
) -> AuthoredRecordRefinementOverview:
    return AuthoredRecordRefinementOverview(
        patient_edits_applied=patient_refinement.edits_applied,
        provider_edits_applied=provider_refinement.edits_applied,
        patient_edited_field_count=len(patient_refinement.edited_field_paths),
        provider_edited_field_count=len(provider_refinement.edited_field_paths),
        patient_refined_record_id=patient_refinement.refined_record_id,
        provider_refined_record_id=provider_refinement.refined_record_id,
    )


def _build_preparation_overview(
    preparation: AuthoredBundleBuildPreparation,
) -> AuthoredBundlePreparationOverview:
    return AuthoredBundlePreparationOverview(
        mapped_condition_count=preparation.patient_mapping.mapped_condition_count,
        mapped_medication_count=preparation.patient_mapping.mapped_medication_count,
        mapped_allergy_count=preparation.patient_mapping.mapped_allergy_count,
        mapped_organization_count=preparation.provider_mapping.mapped_organization_count,
        mapped_provider_role_relationship_count=preparation.provider_mapping.mapped_provider_role_relationship_count,
        patient_unmapped_field_count=len(preparation.patient_mapping.unmapped_fields),
        provider_unmapped_field_count=len(preparation.provider_mapping.unmapped_fields),
        provider_path_mode=_provider_path_mode_from_preparation(preparation),
        has_selected_provider_role_relationship=preparation.provider_mapping.has_selected_provider_role_relationship,
    )


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
    patient_overview = _build_patient_overview(patient_record)
    _store_artifact(ctx, "demo_input", message)
    _store_artifact(ctx, "original_patient_record", patient_record)
    _store_artifact(ctx, "patient_record", patient_record)
    _store_artifact(ctx, "patient_overview", patient_overview)
    await ctx.send_message(
        AuthoredBundleDemoStageResult(
            stage_id="patient_authoring",
            status="placeholder_complete",
            summary=(
                f"Authored patient '{patient_overview.display_name}' with "
                f"{patient_overview.condition_count} condition(s), "
                f"{patient_overview.medication_count} medication(s), and "
                f"{patient_overview.allergy_count} allergy/allergies."
            ),
            placeholder_note=(
                "Built from the existing offline/demo patient authoring foundation. "
                f"Background facts present: residence={patient_overview.has_residence_text}, "
                f"smoking={patient_overview.has_smoking_status_text}. "
                f"Unresolved authored-gap count: {patient_overview.unresolved_gap_count}."
            ),
            source_refs=["authoring.patient_builder"],
            demo_input=message,
            original_patient_record=patient_record,
            patient_record=patient_record,
            patient_overview=patient_overview,
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
    provider_overview = _build_provider_overview(provider_record)
    _store_artifact(ctx, "original_provider_record", provider_record)
    _store_artifact(ctx, "provider_record", provider_record)
    _store_artifact(ctx, "provider_overview", provider_overview)
    await ctx.send_message(
        AuthoredBundleDemoStageResult(
            stage_id="provider_authoring",
            status="placeholder_complete",
            summary=(
                f"Authored provider '{provider_overview.display_name}' on the "
                f"{provider_overview.provider_path_mode} provider path with "
                f"{provider_overview.organization_count} organization(s) and "
                f"{provider_overview.provider_role_relationship_count} relationship(s)."
            ),
            placeholder_note=(
                "Built from the existing offline/demo provider authoring foundation. "
                + (
                    "A linked organization and provider-role relationship are present for richer downstream support-resource context."
                    if provider_overview.provider_path_mode == "rich"
                    else "No linked organization/provider-role relationship was authored, so downstream preparation will remain on the thin provider path unless refinement adds one."
                )
            ),
            source_refs=["authoring.provider_builder"],
            demo_input=message.demo_input,
            original_patient_record=_get_artifact(ctx, "original_patient_record"),
            original_provider_record=provider_record,
            patient_record=_get_artifact(ctx, "patient_record"),
            provider_record=provider_record,
            patient_overview=_get_artifact(ctx, "patient_overview"),
            provider_overview=provider_overview,
        )
    )


@executor(
    id="authored_record_refinement",
    input=AuthoredBundleDemoStageResult,
    output=AuthoredBundleDemoStageResult,
)
async def authored_record_refinement(
    message: AuthoredBundleDemoStageResult,
    ctx: WorkflowContext[AuthoredBundleDemoStageResult],
) -> None:
    patient_refinement = apply_patient_authored_record_review_edits(
        _get_artifact(ctx, "original_patient_record"),
        message.demo_input.patient_review_edits,
    )
    provider_refinement = apply_provider_authored_record_review_edits(
        _get_artifact(ctx, "original_provider_record"),
        message.demo_input.provider_review_edits,
    )
    _store_artifact(ctx, "patient_refinement", patient_refinement)
    _store_artifact(ctx, "provider_refinement", provider_refinement)
    _store_artifact(ctx, "patient_record", patient_refinement.refined_record)
    _store_artifact(ctx, "provider_record", provider_refinement.refined_record)
    patient_overview = _build_patient_overview(patient_refinement.refined_record)
    provider_overview = _build_provider_overview(provider_refinement.refined_record)
    refinement_overview = _build_refinement_overview(patient_refinement, provider_refinement)
    _store_artifact(ctx, "patient_overview", patient_overview)
    _store_artifact(ctx, "provider_overview", provider_overview)
    _store_artifact(ctx, "refinement_overview", refinement_overview)
    await ctx.send_message(
        AuthoredBundleDemoStageResult(
            stage_id="authored_record_refinement",
            status="placeholder_complete",
            summary=(
                "Applied authored-record refinement with "
                f"{refinement_overview.patient_edited_field_count} edited patient field(s) and "
                f"{refinement_overview.provider_edited_field_count} edited provider field(s); "
                f"effective provider path is now {provider_overview.provider_path_mode}."
            ),
            placeholder_note=(
                "Refinement stays on authored records only. "
                f"Patient edits applied={refinement_overview.patient_edits_applied}; "
                f"provider edits applied={refinement_overview.provider_edits_applied}. "
                "Mapped contexts and downstream workflow behavior remain unchanged."
            ),
            source_refs=["authoring.authored_record_refinement"],
            demo_input=message.demo_input,
            original_patient_record=_get_artifact(ctx, "original_patient_record"),
            original_provider_record=_get_artifact(ctx, "original_provider_record"),
            patient_record=patient_refinement.refined_record,
            provider_record=provider_refinement.refined_record,
            patient_overview=patient_overview,
            provider_overview=provider_overview,
            patient_refinement=patient_refinement,
            provider_refinement=provider_refinement,
            refinement_overview=refinement_overview,
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
    preparation_overview = _build_preparation_overview(preparation)
    _store_artifact(ctx, "preparation_overview", preparation_overview)
    await ctx.send_message(
        AuthoredBundleDemoStageResult(
            stage_id="authored_bundle_preparation",
            status="placeholder_complete",
            summary=(
                "Prepared one deterministic workflow-ready request with "
                f"{preparation_overview.mapped_condition_count}/{preparation_overview.mapped_medication_count}/"
                f"{preparation_overview.mapped_allergy_count} mapped patient item counts and "
                f"{preparation_overview.mapped_organization_count} organization(s), "
                f"{preparation_overview.mapped_provider_role_relationship_count} provider relationship(s) "
                f"on the {preparation_overview.provider_path_mode} provider path."
            ),
            placeholder_note=(
                "This wrapper flow still composes the existing authored-input orchestration helper only. "
                f"Unmapped authored facts: patient={preparation_overview.patient_unmapped_field_count}, "
                f"provider={preparation_overview.provider_unmapped_field_count}. "
                f"Selected provider-role relationship present={preparation_overview.has_selected_provider_role_relationship}."
            ),
            source_refs=[
                "authoring.patient_mapper",
                "authoring.provider_mapper",
                "authoring.authored_bundle_orchestration",
            ],
            demo_input=message.demo_input,
            original_patient_record=_get_artifact(ctx, "original_patient_record"),
            original_provider_record=_get_artifact(ctx, "original_provider_record"),
            patient_record=_get_artifact(ctx, "patient_record"),
            provider_record=_get_artifact(ctx, "provider_record"),
            patient_overview=_get_artifact(ctx, "patient_overview"),
            provider_overview=_get_artifact(ctx, "provider_overview"),
            patient_refinement=_get_artifact(ctx, "patient_refinement"),
            provider_refinement=_get_artifact(ctx, "provider_refinement"),
            refinement_overview=_get_artifact(ctx, "refinement_overview"),
            preparation=preparation,
            preparation_overview=preparation_overview,
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
    original_patient_record = _get_artifact(ctx, "original_patient_record")
    original_provider_record = _get_artifact(ctx, "original_provider_record")
    patient_record = _get_artifact(ctx, "patient_record")
    patient_refinement = _get_artifact(ctx, "patient_refinement")
    provider_record = _get_artifact(ctx, "provider_record")
    provider_refinement = _get_artifact(ctx, "provider_refinement")
    preparation = _get_artifact(ctx, "preparation")
    patient_overview = _get_artifact(ctx, "patient_overview")
    provider_overview = _get_artifact(ctx, "provider_overview")
    refinement_overview = _get_artifact(ctx, "refinement_overview")
    preparation_overview = _get_artifact(ctx, "preparation_overview")
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
        provider_path_mode=preparation_overview.provider_path_mode,
        overall_validation_status=workflow_output.validation_report.overall_status,
        workflow_validation_status=workflow_output.validation_report.workflow_validation.status,
        candidate_bundle_entry_count=workflow_output.candidate_bundle.candidate_bundle.entry_count,
        patient_unmapped_field_count=preparation_overview.patient_unmapped_field_count,
        provider_unmapped_field_count=preparation_overview.provider_unmapped_field_count,
        patient_edits_applied=patient_refinement.edits_applied,
        provider_edits_applied=provider_refinement.edits_applied,
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
            original_patient_record=original_patient_record,
            original_provider_record=original_provider_record,
            patient_record=patient_record,
            provider_record=provider_record,
            patient_overview=patient_overview,
            provider_overview=provider_overview,
            patient_refinement=patient_refinement,
            provider_refinement=provider_refinement,
            refinement_overview=refinement_overview,
            preparation=preparation,
            preparation_overview=preparation_overview,
            final_summary=final_summary,
            workflow_output=workflow_output,
        )
    )
