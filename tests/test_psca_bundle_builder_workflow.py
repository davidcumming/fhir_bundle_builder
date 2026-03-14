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
    assert final_output.stage_order[-1] == "repair_execution"
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
    assert final_output.resource_construction.construction_mode == "deterministic_content_enriched"
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
    assert final_output.resource_construction.step_results[0].resource_scaffold.fhir_scaffold["identifier"][0]["value"] == "patient-smoke-test"
    assert final_output.resource_construction.step_results[0].resource_scaffold.fhir_scaffold["name"][0]["text"] == "Smoke Test Patient"
    assert final_output.resource_construction.step_results[1].resource_scaffold.fhir_scaffold["active"] is True
    assert final_output.resource_construction.step_results[1].resource_scaffold.fhir_scaffold["identifier"][0]["value"] == "provider-smoke-test"
    assert final_output.resource_construction.step_results[1].resource_scaffold.fhir_scaffold["name"][0]["text"] == "Smoke Test Provider"
    assert final_output.resource_construction.step_results[2].resource_scaffold.fhir_scaffold == {
        "resourceType": "Organization",
        "id": "organization-1",
        "meta": {"profile": [final_output.bundle_schematic.resource_placeholders[2].profile_url]},
    }
    assert final_output.resource_construction.step_results[3].resource_scaffold.fhir_scaffold["code"][0]["text"] == "document-author"
    assert final_output.resource_construction.step_results[4].resource_scaffold.fhir_scaffold["status"] == "final"
    assert final_output.resource_construction.step_results[4].resource_scaffold.fhir_scaffold["title"] == (
        "PS-CA document bundle skeleton - pytest-smoke"
    )
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
    assert (
        final_output.candidate_bundle.candidate_bundle.fhir_bundle["identifier"]["system"]
        == "urn:fhir-bundle-builder:candidate-bundle-identifier"
    )
    assert final_output.candidate_bundle.candidate_bundle.fhir_bundle["timestamp"].endswith("Z")
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
    full_urls = [
        entry["fullUrl"] for entry in final_output.candidate_bundle.candidate_bundle.fhir_bundle["entry"]
    ]
    assert all(full_url.startswith("urn:uuid:") for full_url in full_urls)
    assert [entry.full_url for entry in final_output.candidate_bundle.entry_assembly] == full_urls
    assert final_output.candidate_bundle.candidate_bundle.fhir_bundle["entry"][0]["resource"]["status"] == "final"
    assert final_output.candidate_bundle.candidate_bundle.fhir_bundle["entry"][0]["resource"]["title"] == (
        "PS-CA document bundle skeleton - pytest-smoke"
    )
    assert (
        final_output.candidate_bundle.candidate_bundle.fhir_bundle["entry"][0]["resource"]["subject"]["reference"]
        == full_urls[1]
    )
    assert (
        final_output.candidate_bundle.candidate_bundle.fhir_bundle["entry"][0]["resource"]["author"][0]["reference"]
        == full_urls[2]
    )
    assert final_output.candidate_bundle.candidate_bundle.fhir_bundle["entry"][1]["resource"]["name"][0]["text"] == "Smoke Test Patient"
    assert final_output.candidate_bundle.candidate_bundle.fhir_bundle["entry"][2]["resource"]["code"][0]["text"] == "document-author"
    assert (
        final_output.candidate_bundle.candidate_bundle.fhir_bundle["entry"][2]["resource"]["practitioner"]["reference"]
        == full_urls[3]
    )
    assert (
        final_output.candidate_bundle.candidate_bundle.fhir_bundle["entry"][2]["resource"]["organization"]["reference"]
        == full_urls[4]
    )
    assert final_output.candidate_bundle.candidate_bundle.fhir_bundle["entry"][3]["resource"]["identifier"][0]["value"] == "provider-smoke-test"
    assert final_output.candidate_bundle.candidate_bundle.fhir_bundle["entry"][3]["resource"]["name"][0]["text"] == "Smoke Test Provider"
    assert "name" not in final_output.candidate_bundle.candidate_bundle.fhir_bundle["entry"][4]["resource"]
    assert final_output.candidate_bundle.candidate_bundle.fhir_bundle["entry"][5]["resource"]["status"] == "draft"
    assert (
        final_output.candidate_bundle.candidate_bundle.fhir_bundle["entry"][6]["resource"]["code"]["text"]
        == f"{final_output.bundle_schematic.section_scaffolds[1].title} placeholder for pytest-smoke"
    )
    assert (
        final_output.candidate_bundle.candidate_bundle.fhir_bundle["entry"][7]["resource"]["code"]["text"]
        == f"{final_output.bundle_schematic.section_scaffolds[2].title} placeholder for pytest-smoke"
    )
    assert final_output.candidate_bundle.candidate_bundle.deferred_paths == []
    assert len(final_output.candidate_bundle.candidate_bundle.fhir_bundle["entry"][0]["resource"]["section"]) == 3
    assert final_output.validation_report.overall_status == "passed_with_warnings"
    assert final_output.validation_report.standards_validation.validator_id == "local_candidate_bundle_scaffold_validator"
    assert final_output.validation_report.standards_validation.status == "passed_with_warnings"
    assert final_output.validation_report.standards_validation.requested_validator_mode == "local_scaffold"
    assert final_output.validation_report.standards_validation.attempted_validator_ids == [
        "local_candidate_bundle_scaffold_validator"
    ]
    assert final_output.validation_report.standards_validation.external_validation_executed is False
    assert final_output.validation_report.standards_validation.fallback_used is False
    assert final_output.validation_report.workflow_validation.status == "passed"
    assert any(
        finding.code == "external_profile_validation_deferred"
        for finding in final_output.validation_report.standards_validation.findings
    )
    assert not any(
        finding.code == "bundle.deferred_fields_recorded"
        for finding in final_output.validation_report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.practitioner_identity_content_present"
        for finding in final_output.validation_report.workflow_validation.findings
    )
    assert final_output.repair_decision.overall_decision == "external_validation_pending"
    assert final_output.repair_decision.recommended_target == "standards_validation_external"
    assert final_output.repair_decision.recommended_next_stage == "none"
    assert any(
        route.finding_code == "external_profile_validation_deferred"
        and route.route_target == "standards_validation_external"
        and route.actionable is False
        for route in final_output.repair_decision.finding_routes
    )
    assert not any(
        route.finding_code == "bundle.deferred_fields_recorded"
        for route in final_output.repair_decision.finding_routes
    )
    assert final_output.repair_execution.execution_outcome == "deferred"
    assert final_output.repair_execution.requested_target == "standards_validation_external"
    assert final_output.repair_execution.retry_eligible is False
    assert final_output.repair_execution.attempt_count == 0
    assert final_output.repair_execution.post_retry_resource_construction is None
    assert final_output.repair_execution.post_retry_candidate_bundle is None

    completed_executors = [
        event.executor_id
        for event in result
        if event.type == "executor_completed" and getattr(event, "executor_id", None) is not None
    ]
    assert completed_executors == final_output.stage_order
