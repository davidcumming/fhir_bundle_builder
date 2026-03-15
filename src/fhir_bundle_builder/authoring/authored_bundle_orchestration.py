"""Thin orchestration helpers from authored records into the existing workflow."""

from __future__ import annotations

from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.models import (
    ProfileReferenceInput,
    WorkflowBuildInput,
    WorkflowSkeletonRunResult,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.workflow import workflow

from .authored_bundle_models import (
    AuthoredBundleBuildInput,
    AuthoredBundleBuildPreparation,
    AuthoredBundleBuildRunResult,
    AuthoredBundleWorkflowInputSummary,
)
from .patient_mapper import map_authored_patient_to_patient_context
from .provider_mapper import map_authored_provider_to_provider_context


def prepare_authored_bundle_build_input(
    authored_input: AuthoredBundleBuildInput,
) -> AuthoredBundleBuildPreparation:
    """Compose authored patient/provider records into a workflow-ready build input."""

    patient_mapping = map_authored_patient_to_patient_context(authored_input.patient_record)
    provider_mapping = map_authored_provider_to_provider_context(authored_input.provider_record)

    workflow_input = WorkflowBuildInput(
        specification=authored_input.specification,
        patient_profile=ProfileReferenceInput(
            profile_id=authored_input.patient_record.patient.patient_id,
            display_name=authored_input.patient_record.patient.display_name,
            source_type="patient_management",
        ),
        patient_context=patient_mapping.patient_context,
        provider_profile=ProfileReferenceInput(
            profile_id=authored_input.provider_record.provider.provider_id,
            display_name=authored_input.provider_record.provider.display_name,
            source_type="provider_management",
        ),
        provider_context=provider_mapping.provider_context,
        request=authored_input.request,
        workflow_options=authored_input.workflow_options,
    )

    return AuthoredBundleBuildPreparation(
        source_patient_record_id=authored_input.patient_record.record_id,
        source_provider_record_id=authored_input.provider_record.record_id,
        patient_mapping=patient_mapping,
        provider_mapping=provider_mapping,
        workflow_input=workflow_input,
        workflow_input_summary=AuthoredBundleWorkflowInputSummary(
            patient_id=patient_mapping.patient_context.patient.patient_id,
            provider_id=provider_mapping.provider_context.provider.provider_id,
            mapped_condition_count=patient_mapping.mapped_condition_count,
            mapped_medication_count=patient_mapping.mapped_medication_count,
            mapped_allergy_count=patient_mapping.mapped_allergy_count,
            mapped_organization_count=provider_mapping.mapped_organization_count,
            mapped_provider_role_relationship_count=provider_mapping.mapped_provider_role_relationship_count,
            has_selected_provider_role_relationship=provider_mapping.has_selected_provider_role_relationship,
            scenario_label=authored_input.request.scenario_label,
        ),
    )


async def run_authored_bundle_build(
    authored_input: AuthoredBundleBuildInput,
) -> AuthoredBundleBuildRunResult:
    """Run the existing workflow from one composed authored-input request."""

    preparation = prepare_authored_bundle_build_input(authored_input)
    run_result = await workflow.run(message=preparation.workflow_input, include_status_events=True)
    outputs = run_result.get_outputs()
    workflow_output = outputs[0]
    if not isinstance(workflow_output, WorkflowSkeletonRunResult):
        raise TypeError(
            "Expected the authored bundle orchestration helper to receive a WorkflowSkeletonRunResult "
            f"but got {type(workflow_output).__name__}."
        )

    return AuthoredBundleBuildRunResult(
        preparation=preparation,
        workflow_output=workflow_output,
    )
