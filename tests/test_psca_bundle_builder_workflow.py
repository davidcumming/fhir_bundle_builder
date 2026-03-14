"""Smoke tests for the PS-CA workflow skeleton."""

from __future__ import annotations

from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.models import (
    BundleRequestInput,
    ProfileReferenceInput,
    SpecificationSelection,
    WorkflowBuildInput,
    WorkflowSkeletonRunResult,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.workflow import workflow


async def test_psca_bundle_builder_workflow_smoke() -> None:
    message = WorkflowBuildInput(
        specification=SpecificationSelection(),
        patient_profile=ProfileReferenceInput(
            profile_id="patient-smoke-test",
            display_name="Smoke Test Patient",
        ),
        provider_profile=ProfileReferenceInput(
            profile_id="provider-smoke-test",
            display_name="Smoke Test Provider",
        ),
        request=BundleRequestInput(
            request_text="Create a deterministic placeholder PS-CA workflow run for testing.",
            scenario_label="pytest-smoke",
        ),
    )

    result = await workflow.run(message=message, include_status_events=True)
    outputs = result.get_outputs()

    assert workflow.input_types == [WorkflowBuildInput]
    assert len(outputs) == 1

    final_output = outputs[0]
    assert isinstance(final_output, WorkflowSkeletonRunResult)
    assert final_output.workflow_name == "PS-CA Bundle Builder Skeleton"
    assert final_output.normalized_request.request.scenario_label == "pytest-smoke"
    assert final_output.specification_asset_context.normalized_assets.package_summary.package_id == "ca.infoway.io.psca"
    assert final_output.specification_asset_context.normalized_assets.package_summary.index_entry_count > 0
    assert len(final_output.specification_asset_context.normalized_assets.workflow_profile_inventory) == 6
    assert final_output.specification_asset_context.normalized_assets.selected_profiles.bundle.profile_id == "bundle-ca-ps"
    assert final_output.specification_asset_context.normalized_assets.selected_bundle_example.filename == "Bundle1Example.json"
    assert len(final_output.specification_asset_context.normalized_assets.composition_section_definitions) >= 3
    assert final_output.bundle_schematic.bundle_scaffold.bundle_type == "document"
    assert final_output.bundle_schematic.composition_scaffold.expected_type_code == "60591-5"
    assert [section.section_key for section in final_output.bundle_schematic.section_scaffolds] == [
        "medications",
        "allergies",
        "problems",
    ]
    assert {placeholder.placeholder_id for placeholder in final_output.bundle_schematic.resource_placeholders} == {
        "patient-1",
        "practitioner-1",
        "organization-1",
        "practitionerrole-1",
        "condition-1",
        "medicationrequest-1",
        "allergyintolerance-1",
        "composition-1",
    }
    assert any(
        relationship.relationship_id == "composition-subject" and relationship.target_id == "patient-1"
        for relationship in final_output.bundle_schematic.relationships
    )
    assert final_output.candidate_bundle.entry_count == len(final_output.resource_construction.built_resources)
    assert final_output.build_plan.plan_basis == "schematic-derived-placeholder-sequence"
    assert final_output.validation_report.outcome == "placeholder_pass_with_warnings"
    assert final_output.repair_decision.decision == "complete_for_slice"

    completed_executors = [
        event.executor_id
        for event in result
        if event.type == "executor_completed" and getattr(event, "executor_id", None) is not None
    ]
    assert completed_executors == final_output.stage_order
