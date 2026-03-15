"""Smoke tests for the canonical authored-input demo workflow scenarios."""

from __future__ import annotations

from fhir_bundle_builder.workflows.psca_authored_bundle_demo_workflow import (
    build_rich_reviewed_demo_input,
    build_thin_provider_demo_input,
)
from fhir_bundle_builder.workflows.psca_authored_bundle_demo_workflow.models import AuthoredBundleDemoInput, AuthoredBundleDemoRunResult
from fhir_bundle_builder.workflows.psca_authored_bundle_demo_workflow.workflow import workflow


async def test_psca_authored_bundle_demo_workflow_smoke_rich_path() -> None:
    result = await workflow.run(
        message=build_rich_reviewed_demo_input(),
        include_status_events=True,
    )
    final_output = result.get_outputs()[0]

    assert workflow.input_types == [AuthoredBundleDemoInput]
    assert isinstance(final_output, AuthoredBundleDemoRunResult)
    assert final_output.workflow_name == "PS-CA Authored Bundle Demo Flow"
    assert final_output.stage_order == [
        "patient_authoring",
        "provider_authoring",
        "authored_record_refinement",
        "authored_bundle_preparation",
        "bundle_builder_run",
    ]
    assert final_output.original_patient_record.patient.display_name == "Nora Field"
    assert final_output.patient_refinement.edits_applied is True
    assert final_output.patient_record.patient.display_name == "Nora Field Reviewed"
    assert final_output.patient_overview.display_name == "Nora Field Reviewed"
    assert final_output.patient_overview.condition_count == 1
    assert final_output.patient_overview.medication_count == 1
    assert final_output.patient_overview.allergy_count == 1
    assert final_output.provider_record.provider.display_name == "Maya Chen"
    assert final_output.provider_overview.display_name == "Maya Chen"
    assert final_output.provider_overview.provider_path_mode == "rich"
    assert final_output.provider_overview.organization_count == 1
    assert final_output.provider_overview.provider_role_relationship_count == 1
    assert final_output.provider_refinement.edits_applied is True
    assert final_output.refinement_overview.patient_edits_applied is True
    assert final_output.refinement_overview.provider_edits_applied is True
    assert final_output.refinement_overview.patient_edited_field_count == 2
    assert final_output.refinement_overview.provider_edited_field_count == 1
    assert final_output.provider_record.provider_role_relationships[0].role_label == "medical oncologist"
    assert final_output.preparation.workflow_input_summary.scenario_label == "rich-reviewed-demo"
    assert final_output.preparation.workflow_input_summary.mapped_condition_count == 1
    assert final_output.preparation.workflow_input_summary.mapped_medication_count == 1
    assert final_output.preparation.workflow_input_summary.mapped_allergy_count == 1
    assert final_output.preparation.workflow_input_summary.mapped_organization_count == 1
    assert final_output.preparation.workflow_input_summary.mapped_provider_role_relationship_count == 1
    assert final_output.preparation_overview.provider_path_mode == "rich"
    assert final_output.preparation_overview.patient_unmapped_field_count == 2
    assert final_output.preparation_overview.provider_unmapped_field_count == 2
    assert final_output.final_summary.candidate_bundle_entry_count == 8
    assert final_output.final_summary.provider_path_mode == "rich"
    assert final_output.final_summary.patient_unmapped_field_count == 2
    assert final_output.final_summary.provider_unmapped_field_count == 2
    assert final_output.final_summary.patient_edits_applied is True
    assert final_output.final_summary.provider_edits_applied is True
    assert final_output.final_summary.has_selected_provider_role_relationship is True
    assert final_output.workflow_output.normalized_request.patient_context.patient.patient_id == (
        final_output.patient_record.patient.patient_id
    )
    assert final_output.workflow_output.normalized_request.provider_context.provider.provider_id == (
        final_output.provider_record.provider.provider_id
    )
    assert final_output.workflow_output.validation_report.workflow_validation.status == "passed"


async def test_psca_authored_bundle_demo_workflow_smoke_thin_provider_path() -> None:
    result = await workflow.run(
        message=build_thin_provider_demo_input(),
        include_status_events=True,
    )
    final_output = result.get_outputs()[0]

    assert isinstance(final_output, AuthoredBundleDemoRunResult)
    assert final_output.original_provider_record.provider.display_name == "Authored Oncologist"
    assert final_output.provider_refinement.edits_applied is True
    assert final_output.provider_record.provider.display_name == "Dr. Rowan Park"
    assert final_output.provider_overview.provider_path_mode == "thin"
    assert final_output.provider_overview.organization_count == 0
    assert final_output.provider_overview.provider_role_relationship_count == 0
    assert final_output.refinement_overview.provider_edits_applied is True
    assert final_output.refinement_overview.provider_edited_field_count == 1
    assert sorted(gap.gap_code for gap in final_output.provider_record.unresolved_authoring_gaps) == [
        "missing_organization",
        "missing_provider_role_relationship",
    ]
    assert final_output.preparation.provider_mapping.unmapped_fields == [
        "professional_facts.administrative_gender",
        "professional_facts.jurisdiction_text",
        "professional_facts.specialty_or_role_label",
    ]
    assert final_output.preparation.workflow_input.provider_context is not None
    assert final_output.preparation.workflow_input.provider_context.organizations == []
    assert final_output.preparation.workflow_input.provider_context.provider_role_relationships == []
    assert final_output.preparation_overview.provider_path_mode == "thin"
    assert final_output.preparation_overview.patient_unmapped_field_count == 1
    assert final_output.preparation_overview.provider_unmapped_field_count == 3
    assert final_output.preparation.workflow_input_summary.has_selected_provider_role_relationship is False
    assert final_output.final_summary.provider_path_mode == "thin"
    assert final_output.final_summary.patient_unmapped_field_count == 1
    assert final_output.final_summary.provider_unmapped_field_count == 3
    assert final_output.final_summary.patient_edits_applied is False
    assert final_output.final_summary.provider_edits_applied is True
    assert final_output.final_summary.has_selected_provider_role_relationship is False
    assert final_output.workflow_output.normalized_request.provider_context.selected_provider_role_relationship is None
    assert final_output.workflow_output.normalized_request.provider_context.selected_organization is None
    assert final_output.workflow_output.validation_report.workflow_validation.status == "passed"
