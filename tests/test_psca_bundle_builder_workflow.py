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
    assert final_output.build_plan.plan_basis == "deterministic_schematic_dependency_plan"
    assert final_output.build_plan.composition_strategy == "two_step_scaffold_then_finalize"
    assert [step.step_id for step in final_output.build_plan.steps] == [
        "build-patient-1",
        "build-practitioner-1",
        "build-organization-1",
        "build-practitionerrole-1",
        "build-composition-1-scaffold",
        "build-medicationrequest-1",
        "build-allergyintolerance-1",
        "build-condition-1",
        "finalize-composition-1",
    ]
    assert [step.step_kind for step in final_output.build_plan.steps] == [
        "anchor_resource",
        "support_resource",
        "support_resource",
        "support_resource",
        "composition_scaffold",
        "section_entry_resource",
        "section_entry_resource",
        "section_entry_resource",
        "composition_finalize",
    ]
    assert [dependency.prerequisite_step_id for dependency in final_output.build_plan.steps[3].dependencies] == [
        "build-practitioner-1",
        "build-organization-1",
    ]
    assert [dependency.prerequisite_step_id for dependency in final_output.build_plan.steps[4].dependencies] == [
        "build-patient-1",
        "build-practitionerrole-1",
    ]
    assert [dependency.prerequisite_step_id for dependency in final_output.build_plan.steps[-1].dependencies] == [
        "build-composition-1-scaffold",
        "build-medicationrequest-1",
        "build-allergyintolerance-1",
        "build-condition-1",
    ]
    assert final_output.resource_construction.construction_mode == "deterministic_scaffold_only"
    assert [step.step_id for step in final_output.resource_construction.step_results] == [
        "build-patient-1",
        "build-practitioner-1",
        "build-organization-1",
        "build-practitionerrole-1",
        "build-composition-1-scaffold",
        "build-medicationrequest-1",
        "build-allergyintolerance-1",
        "build-condition-1",
        "finalize-composition-1",
    ]
    assert final_output.resource_construction.step_results[4].target_placeholder_id == "composition-1"
    assert final_output.resource_construction.step_results[4].execution_status == "scaffold_created"
    assert final_output.resource_construction.step_results[-1].target_placeholder_id == "composition-1"
    assert final_output.resource_construction.step_results[-1].execution_status == "scaffold_updated"
    assert {entry.placeholder_id for entry in final_output.resource_construction.resource_registry} == {
        "patient-1",
        "practitioner-1",
        "organization-1",
        "practitionerrole-1",
        "composition-1",
        "medicationrequest-1",
        "allergyintolerance-1",
        "condition-1",
    }
    assert final_output.candidate_bundle.assembly_mode == "deterministic_registry_bundle_scaffold"
    assert final_output.candidate_bundle.candidate_bundle.bundle_state == "candidate_scaffold_assembled"
    assert final_output.candidate_bundle.candidate_bundle.entry_count == 8
    assert [entry.placeholder_id for entry in final_output.candidate_bundle.entry_assembly] == [
        "composition-1",
        "patient-1",
        "practitionerrole-1",
        "practitioner-1",
        "organization-1",
        "medicationrequest-1",
        "allergyintolerance-1",
        "condition-1",
    ]
    assert final_output.candidate_bundle.candidate_bundle.fhir_bundle["resourceType"] == "Bundle"
    assert final_output.candidate_bundle.candidate_bundle.fhir_bundle["id"] == "ca.infoway.io.psca-pytest-smoke"
    assert final_output.candidate_bundle.candidate_bundle.fhir_bundle["meta"]["profile"] == [
        final_output.bundle_schematic.bundle_scaffold.profile_url
    ]
    assert final_output.candidate_bundle.candidate_bundle.fhir_bundle["type"] == "document"
    assert [
        entry["resource"]["resourceType"] for entry in final_output.candidate_bundle.candidate_bundle.fhir_bundle["entry"]
    ] == [
        "Composition",
        "Patient",
        "PractitionerRole",
        "Practitioner",
        "Organization",
        "MedicationRequest",
        "AllergyIntolerance",
        "Condition",
    ]
    assert final_output.candidate_bundle.candidate_bundle.deferred_paths == [
        "identifier",
        "timestamp",
        "entry.fullUrl",
    ]
    assert len(final_output.candidate_bundle.candidate_bundle.fhir_bundle["entry"][0]["resource"]["section"]) == 3
    assert final_output.validation_report.overall_status == "passed_with_warnings"
    assert final_output.validation_report.standards_validation.validator_id == "local_candidate_bundle_scaffold_validator"
    assert final_output.validation_report.standards_validation.status == "passed_with_warnings"
    assert final_output.validation_report.workflow_validation.status == "passed"
    assert any(
        finding.code == "external_profile_validation_deferred"
        for finding in final_output.validation_report.standards_validation.findings
    )
    assert any(
        finding.code == "bundle.deferred_fields_recorded"
        and finding.severity == "information"
        for finding in final_output.validation_report.workflow_validation.findings
    )
    assert final_output.repair_decision.decision == "complete_for_slice"

    completed_executors = [
        event.executor_id
        for event in result
        if event.type == "executor_completed" and getattr(event, "executor_id", None) is not None
    ]
    assert completed_executors == final_output.stage_order
