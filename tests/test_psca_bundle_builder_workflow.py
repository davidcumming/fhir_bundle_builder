"""Smoke tests for the PS-CA workflow skeleton."""

from __future__ import annotations

import pytest

from fhir_bundle_builder.authoring import (
    PatientAuthoringInput,
    ProviderAuthoringInput,
    build_patient_authored_record,
    build_provider_authored_record,
    map_authored_patient_to_patient_context,
    map_authored_provider_to_provider_context,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow import executors as workflow_executors
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow import medication_request_agent as medication_agent_module
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.bundle_finalization_builder import (
    build_psca_candidate_bundle_result as build_real_candidate_bundle_result,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.models import (
    BundleRequestInput,
    PatientAllergyInput,
    PatientConditionInput,
    PatientContextInput,
    PatientIdentityInput,
    PatientMedicationInput,
    ProfileReferenceInput,
    ProviderContextInput,
    ProviderIdentityInput,
    ProviderOrganizationInput,
    ProviderRoleRelationshipInput,
    SpecificationSelection,
    WorkflowBuildInput,
    WorkflowOptionsInput,
    WorkflowSkeletonRunResult,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.openai_gateway import (
    OpenAIGatewayConfig,
    OpenAIJSONCompletionResponse,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.resource_construction_builder import (
    SELECTED_PROVIDER_ORGANIZATION_IDENTIFIER_SYSTEM,
    SELECTED_PROVIDER_ROLE_RELATIONSHIP_IDENTIFIER_SYSTEM,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.workflow import workflow


async def test_psca_bundle_builder_workflow_smoke() -> None:
    message = WorkflowBuildInput(
        specification=SpecificationSelection(),
        patient_profile=ProfileReferenceInput(
            profile_id="patient-smoke-test",
            display_name="Smoke Test Patient",
        ),
        patient_context=PatientContextInput(
            patient=PatientIdentityInput(
                patient_id="patient-smoke-test",
                display_name="Smoke Test Patient",
                source_type="patient_management",
                administrative_gender="female",
                birth_date="1985-02-14",
            ),
            medications=[
                PatientMedicationInput(
                    medication_id="med-smoke-1",
                    display_text="Atorvastatin 20 MG oral tablet",
                )
            ],
            allergies=[
                PatientAllergyInput(
                    allergy_id="alg-smoke-1",
                    display_text="Peanut allergy",
                )
            ],
            conditions=[
                PatientConditionInput(
                    condition_id="cond-smoke-1",
                    display_text="Type 2 diabetes mellitus",
                )
            ],
        ),
        provider_profile=ProfileReferenceInput(
            profile_id="provider-smoke-test",
            display_name="Smoke Test Provider",
        ),
        provider_context=ProviderContextInput(
            provider=ProviderIdentityInput(
                provider_id="provider-smoke-test",
                display_name="Smoke Test Provider",
                source_type="provider_management",
            ),
            organizations=[
                ProviderOrganizationInput(
                    organization_id="org-smoke-test-1",
                    display_name="Smoke Test Organization One",
                ),
                ProviderOrganizationInput(
                    organization_id="org-smoke-test-2",
                    display_name="Smoke Test Organization Two",
                ),
            ],
            provider_role_relationships=[
                ProviderRoleRelationshipInput(
                    relationship_id="provider-role-smoke-1",
                    organization_id="org-smoke-test-1",
                    role_label="document-author",
                ),
                ProviderRoleRelationshipInput(
                    relationship_id="provider-role-smoke-2",
                    organization_id="org-smoke-test-2",
                    role_label="attending-physician",
                ),
            ],
            selected_provider_role_relationship_id="provider-role-smoke-2",
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
    assert final_output.normalized_request.patient_context.normalization_mode == "patient_context_explicit"
    assert final_output.normalized_request.patient_context.patient.patient_id == "patient-smoke-test"
    assert final_output.normalized_request.patient_context.selected_medication_for_single_entry is not None
    assert (
        final_output.normalized_request.patient_context.selected_medication_for_single_entry.display_text
        == "Atorvastatin 20 MG oral tablet"
    )
    assert [
        (entry.placeholder_id, entry.source_medication_index, entry.medication_id)
        for entry in final_output.normalized_request.patient_context.planned_medication_entries
    ] == [("medicationrequest-1", 0, "med-smoke-1")]
    assert final_output.normalized_request.patient_context.deferred_additional_medication_count == 0
    assert final_output.normalized_request.provider_context.normalization_mode == "provider_context_explicit_selection"
    assert final_output.normalized_request.provider_context.selected_provider_role_relationship is not None
    assert (
        final_output.normalized_request.provider_context.selected_provider_role_relationship.relationship_id
        == "provider-role-smoke-2"
    )
    assert final_output.normalized_request.provider_context.selected_organization is not None
    assert (
        final_output.normalized_request.provider_context.selected_organization.organization_id
        == "org-smoke-test-2"
    )
    assert final_output.specification_asset_context.normalized_assets.package_summary.package_id == "ca.infoway.io.psca"
    assert final_output.specification_asset_context.normalized_assets.package_summary.index_entry_count > 0
    assert len(final_output.specification_asset_context.normalized_assets.workflow_profile_inventory) == 6
    assert final_output.specification_asset_context.normalized_assets.selected_profiles.bundle.profile_id == "bundle-ca-ps"
    assert final_output.specification_asset_context.normalized_assets.selected_bundle_example.filename == "Bundle1Example.json"
    assert len(final_output.specification_asset_context.normalized_assets.composition_section_definitions) >= 3
    assert final_output.bundle_schematic.bundle_scaffold.bundle_type == "document"
    assert final_output.bundle_schematic.composition_scaffold.expected_type_code == "60591-5"
    assert (
        final_output.bundle_schematic.evidence.patient_context.normalization_mode
        == "patient_context_explicit"
    )
    assert final_output.bundle_schematic.evidence.patient_context.patient_id == "patient-smoke-test"
    assert final_output.bundle_schematic.evidence.patient_context.administrative_gender_present is True
    assert final_output.bundle_schematic.evidence.patient_context.birth_date_present is True
    assert (
        final_output.bundle_schematic.evidence.provider_context.normalization_mode
        == "provider_context_explicit_selection"
    )
    assert (
        final_output.bundle_schematic.evidence.provider_context.selected_provider_role_relationship_id
        == "provider-role-smoke-2"
    )
    assert (
        final_output.bundle_schematic.evidence.provider_context.selected_organization_id
        == "org-smoke-test-2"
    )
    clinical_section_contexts = {
        context.section_key: context
        for context in final_output.bundle_schematic.evidence.clinical_section_contexts
    }
    assert clinical_section_contexts["medications"].available_item_count == 1
    assert (
        clinical_section_contexts["medications"].selected_single_entry_display_text
        == "Atorvastatin 20 MG oral tablet"
    )
    assert clinical_section_contexts["medications"].planned_entry_display_texts == [
        "Atorvastatin 20 MG oral tablet"
    ]
    assert [
        (entry.placeholder_id, entry.source_medication_index, entry.medication_id)
        for entry in clinical_section_contexts["medications"].planned_medication_entries
    ] == [("medicationrequest-1", 0, "med-smoke-1")]
    assert clinical_section_contexts["medications"].planned_placeholder_count == 1
    assert clinical_section_contexts["medications"].deferred_additional_item_count == 0
    assert clinical_section_contexts["medications"].planning_disposition == "fixed_single_entry_selected_item"
    assert clinical_section_contexts["allergies"].planned_placeholder_count == 1
    assert clinical_section_contexts["problems"].planned_placeholder_count == 1
    assert "explicit structured patient/clinical context" in final_output.bundle_schematic.summary
    assert "supports at most two medication placeholders" in final_output.bundle_schematic.placeholder_note
    assert "explicitly selected provider-role relationship context" in final_output.bundle_schematic.summary
    assert "explicitly selected provider-role relationship" in final_output.bundle_schematic.placeholder_note
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
    assert any(
        placeholder.placeholder_id == "practitionerrole-1" and placeholder.role == "attending-physician"
        for placeholder in final_output.bundle_schematic.resource_placeholders
    )
    assert final_output.build_plan.plan_basis == "deterministic_schematic_dependency_plan"
    assert final_output.build_plan.composition_strategy == "scaffold_then_incremental_section_finalize"
    assert [step.step_id for step in final_output.build_plan.steps] == [
        "build-patient-1",
        "build-practitioner-1",
        "build-organization-1",
        "build-practitionerrole-1",
        "build-composition-1-scaffold",
        "build-medicationrequest-1",
        "build-allergyintolerance-1",
        "build-condition-1",
        "finalize-composition-1-medications-section",
        "finalize-composition-1-allergies-section",
        "finalize-composition-1-problems-section",
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
        "composition_finalize",
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
    assert [
        dependency.prerequisite_step_id
        for dependency in final_output.build_plan.steps[-3].dependencies
    ] == [
        "build-composition-1-scaffold",
        "build-medicationrequest-1",
    ]
    assert [
        dependency.prerequisite_step_id
        for dependency in final_output.build_plan.steps[-2].dependencies
    ] == [
        "finalize-composition-1-medications-section",
        "build-allergyintolerance-1",
    ]
    assert [dependency.prerequisite_step_id for dependency in final_output.build_plan.steps[-1].dependencies] == [
        "finalize-composition-1-allergies-section",
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
        "finalize-composition-1-medications-section",
        "finalize-composition-1-allergies-section",
        "finalize-composition-1-problems-section",
    ]
    assert final_output.resource_construction.step_results[4].target_placeholder_id == "composition-1"
    assert final_output.resource_construction.step_results[4].execution_status == "scaffold_created"
    assert final_output.resource_construction.step_results[-3].target_placeholder_id == "composition-1"
    assert final_output.resource_construction.step_results[-3].execution_status == "scaffold_updated"
    assert final_output.resource_construction.step_results[-2].target_placeholder_id == "composition-1"
    assert final_output.resource_construction.step_results[-2].execution_status == "scaffold_updated"
    assert final_output.resource_construction.step_results[-1].target_placeholder_id == "composition-1"
    assert final_output.resource_construction.step_results[-1].execution_status == "scaffold_updated"
    assert final_output.resource_construction.step_results[0].resource_scaffold.fhir_scaffold["identifier"][0]["value"] == "patient-smoke-test"
    assert final_output.resource_construction.step_results[0].resource_scaffold.fhir_scaffold["name"][0]["text"] == "Smoke Test Patient"
    assert final_output.resource_construction.step_results[0].resource_scaffold.fhir_scaffold["gender"] == "female"
    assert final_output.resource_construction.step_results[0].resource_scaffold.fhir_scaffold["birthDate"] == "1985-02-14"
    assert final_output.resource_construction.step_results[1].resource_scaffold.fhir_scaffold["active"] is True
    assert final_output.resource_construction.step_results[1].resource_scaffold.fhir_scaffold["identifier"][0]["value"] == "provider-smoke-test"
    assert final_output.resource_construction.step_results[1].resource_scaffold.fhir_scaffold["name"][0]["text"] == "Smoke Test Provider"
    assert final_output.resource_construction.step_results[2].resource_scaffold.fhir_scaffold == {
        "resourceType": "Organization",
        "id": "organization-1",
        "meta": {"profile": [final_output.bundle_schematic.resource_placeholders[2].profile_url]},
        "identifier": [
            {
                "system": SELECTED_PROVIDER_ORGANIZATION_IDENTIFIER_SYSTEM,
                "value": "org-smoke-test-2",
            }
        ],
        "name": "Smoke Test Organization Two",
    }
    assert (
        final_output.resource_construction.step_results[3].resource_scaffold.fhir_scaffold["identifier"][0]["system"]
        == SELECTED_PROVIDER_ROLE_RELATIONSHIP_IDENTIFIER_SYSTEM
    )
    assert (
        final_output.resource_construction.step_results[3].resource_scaffold.fhir_scaffold["identifier"][0]["value"]
        == "provider-role-smoke-2"
    )
    assert final_output.resource_construction.step_results[3].resource_scaffold.fhir_scaffold["code"][0]["text"] == "attending-physician"
    assert final_output.resource_construction.step_results[4].resource_scaffold.fhir_scaffold["status"] == "final"
    assert final_output.resource_construction.step_results[4].resource_scaffold.fhir_scaffold["title"] == (
        "PS-CA document bundle skeleton - pytest-smoke"
    )
    assert (
        final_output.resource_construction.step_results[5].resource_scaffold.fhir_scaffold["medicationCodeableConcept"]["text"]
        == "Atorvastatin 20 MG oral tablet"
    )
    assert final_output.resource_construction.step_results[6].resource_scaffold.fhir_scaffold["code"]["text"] == "Peanut allergy"
    assert (
        final_output.resource_construction.step_results[7].resource_scaffold.fhir_scaffold["code"]["text"]
        == "Type 2 diabetes mellitus"
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
    construction_traceability = {
        summary.placeholder_id: summary
        for summary in final_output.resource_construction.evidence.placeholder_traceability_summaries
    }
    assert construction_traceability["composition-1"].latest_step_id == "finalize-composition-1-problems-section"
    assert construction_traceability["medicationrequest-1"].source_step_ids == ["build-medicationrequest-1"]
    assert any(
        driving_input.source_artifact
        == "normalized_request.patient_context.planned_medication_entries[0]"
        for driving_input in construction_traceability["medicationrequest-1"].driving_inputs
    )
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
    assert final_output.candidate_bundle.candidate_bundle.fhir_bundle["entry"][2]["resource"]["code"][0]["text"] == "attending-physician"
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
    assert (
        final_output.candidate_bundle.candidate_bundle.fhir_bundle["entry"][4]["resource"]["identifier"][0]["value"]
        == "org-smoke-test-2"
    )
    assert (
        final_output.candidate_bundle.candidate_bundle.fhir_bundle["entry"][4]["resource"]["name"]
        == "Smoke Test Organization Two"
    )
    assert final_output.candidate_bundle.candidate_bundle.fhir_bundle["entry"][5]["resource"]["status"] == "draft"
    assert (
        final_output.candidate_bundle.candidate_bundle.fhir_bundle["entry"][5]["resource"]["medicationCodeableConcept"]["text"]
        == "Atorvastatin 20 MG oral tablet"
    )
    assert (
        final_output.candidate_bundle.candidate_bundle.fhir_bundle["entry"][6]["resource"]["code"]["text"]
        == "Peanut allergy"
    )
    assert (
        final_output.candidate_bundle.candidate_bundle.fhir_bundle["entry"][7]["resource"]["code"]["text"]
        == "Type 2 diabetes mellitus"
    )
    assert final_output.candidate_bundle.candidate_bundle.deferred_paths == []
    assert final_output.candidate_bundle.evidence.planned_medication_placeholder_ids == [
        "medicationrequest-1"
    ]
    assert final_output.candidate_bundle.evidence.assembled_medication_placeholder_ids == [
        "medicationrequest-1"
    ]
    candidate_traceability = {
        summary.placeholder_id: summary
        for summary in final_output.candidate_bundle.evidence.placeholder_traceability_summaries
    }
    assert candidate_traceability["composition-1"].bundle_entry_sequence == 1
    assert candidate_traceability["patient-1"].bundle_entry_sequence == 2
    assert candidate_traceability["medicationrequest-1"].bundle_entry_path == "entry[5].resource"
    assert candidate_traceability["medicationrequest-1"].full_url == full_urls[5]
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
    assert (
        final_output.validation_report.evidence.patient_context_alignment.normalization_mode
        == "patient_context_explicit"
    )
    assert final_output.validation_report.evidence.patient_context_alignment.patient_id == "patient-smoke-test"
    assert (
        final_output.validation_report.evidence.patient_context_alignment.display_name
        == "Smoke Test Patient"
    )
    assert (
        final_output.validation_report.evidence.patient_context_alignment.administrative_gender_expected
        == "female"
    )
    assert (
        final_output.validation_report.evidence.patient_context_alignment.birth_date_expected
        == "1985-02-14"
    )
    assert [
        (
            expectation.placeholder_id,
            expectation.alignment_mode,
            expectation.expected_text,
        )
        for expectation in final_output.validation_report.evidence.patient_context_alignment.section_entry_expectations
    ] == [
        (
            "medicationrequest-1",
            "structured_patient_context",
            "Atorvastatin 20 MG oral tablet",
        ),
        (
            "allergyintolerance-1",
            "structured_patient_context",
            "Peanut allergy",
        ),
        (
            "condition-1",
            "structured_patient_context",
            "Type 2 diabetes mellitus",
        ),
    ]
    assert (
        final_output.validation_report.evidence.provider_context_alignment.normalization_mode
        == "provider_context_explicit_selection"
    )
    assert (
        final_output.validation_report.evidence.provider_context_alignment.provider_id
        == "provider-smoke-test"
    )
    assert (
        final_output.validation_report.evidence.provider_context_alignment.provider_display_name
        == "Smoke Test Provider"
    )
    assert (
        final_output.validation_report.evidence.provider_context_alignment.organization_alignment_mode
        == "structured_provider_context"
    )
    assert (
        final_output.validation_report.evidence.provider_context_alignment.selected_organization_identifier_system_expected
        == SELECTED_PROVIDER_ORGANIZATION_IDENTIFIER_SYSTEM
    )
    assert (
        final_output.validation_report.evidence.provider_context_alignment.selected_organization_id_expected
        == "org-smoke-test-2"
    )
    assert (
        final_output.validation_report.evidence.provider_context_alignment.selected_organization_display_name_expected
        == "Smoke Test Organization Two"
    )
    assert (
        final_output.validation_report.evidence.provider_context_alignment.practitionerrole_alignment_mode
        == "structured_provider_context"
    )
    assert (
        final_output.validation_report.evidence.provider_context_alignment.selected_provider_role_relationship_identifier_system_expected
        == SELECTED_PROVIDER_ROLE_RELATIONSHIP_IDENTIFIER_SYSTEM
    )
    assert (
        final_output.validation_report.evidence.provider_context_alignment.selected_provider_role_relationship_id_expected
        == "provider-role-smoke-2"
    )
    assert (
        final_output.validation_report.evidence.provider_context_alignment.expected_role_label
        == "attending-physician"
    )
    validation_traceability = {
        summary.placeholder_id: summary
        for summary in final_output.validation_report.evidence.placeholder_traceability_summaries
    }
    assert validation_traceability["composition-1"].bundle_entry_sequence == 1
    assert (
        "bundle.practitioner_identity_aligned_to_context"
        in validation_traceability["practitioner-1"].workflow_check_codes
    )
    assert (
        "bundle.organization_identity_aligned_to_context"
        in validation_traceability["organization-1"].workflow_check_codes
    )
    assert (
        "bundle.medicationrequest_placeholder_text_aligned_to_context"
        in validation_traceability["medicationrequest-1"].workflow_check_codes
    )
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
    assert not any(
        finding.code == "bundle.practitioner_identity_aligned_to_context"
        for finding in final_output.validation_report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.organization_identity_aligned_to_context"
        for finding in final_output.validation_report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.practitionerrole_relationship_identity_aligned_to_context"
        for finding in final_output.validation_report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.practitionerrole_author_context_aligned_to_context"
        for finding in final_output.validation_report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.patient_identity_aligned_to_context"
        for finding in final_output.validation_report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.medicationrequest_placeholder_text_aligned_to_context"
        for finding in final_output.validation_report.workflow_validation.findings
    )
    assert final_output.repair_decision.overall_decision == "external_validation_pending"
    assert final_output.repair_decision.recommended_target == "standards_validation_external"
    assert final_output.repair_decision.recommended_next_stage == "none"
    assert final_output.repair_decision.recommended_resource_construction_repair_directive is None
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
    assert final_output.repair_execution.post_retry_resource_construction is None
    assert final_output.repair_execution.applied_resource_construction_repair_directive is None
    assert final_output.repair_execution.execution_outcome == "deferred"
    assert final_output.repair_execution.requested_target == "standards_validation_external"
    assert final_output.repair_execution.retry_eligible is False
    assert final_output.repair_execution.attempt_count == 0
    assert final_output.repair_execution.post_retry_resource_construction is None
    assert final_output.repair_execution.post_retry_candidate_bundle is None
    assert final_output.effective_outcome.artifact_source == "initial_run"
    assert final_output.effective_outcome.resource_construction == final_output.resource_construction
    assert final_output.effective_outcome.candidate_bundle == final_output.candidate_bundle
    assert final_output.effective_outcome.validation_report == final_output.validation_report
    assert final_output.effective_outcome.repair_decision == final_output.repair_decision

    completed_executors = [
        event.executor_id
        for event in result
        if event.type == "executor_completed" and getattr(event, "executor_id", None) is not None
    ]
    assert completed_executors == final_output.stage_order


async def test_psca_bundle_builder_workflow_surfaces_effective_post_retry_outcome(monkeypatch) -> None:
    def _build_broken_initial_candidate_bundle(message, schematic, normalized_request):
        candidate = build_real_candidate_bundle_result(message, schematic, normalized_request)
        broken_candidate = candidate.model_copy(deep=True)
        broken_candidate.candidate_bundle.fhir_bundle["type"] = "collection"
        return broken_candidate

    monkeypatch.setattr(
        workflow_executors,
        "build_psca_candidate_bundle_result",
        _build_broken_initial_candidate_bundle,
    )

    message = WorkflowBuildInput(
        specification=SpecificationSelection(),
        patient_profile=ProfileReferenceInput(
            profile_id="patient-smoke-test",
            display_name="Smoke Test Patient",
        ),
        patient_context=PatientContextInput(
            patient=PatientIdentityInput(
                patient_id="patient-smoke-test",
                display_name="Smoke Test Patient",
                source_type="patient_management",
                administrative_gender="female",
                birth_date="1985-02-14",
            ),
            medications=[
                PatientMedicationInput(
                    medication_id="med-smoke-1",
                    display_text="Atorvastatin 20 MG oral tablet",
                )
            ],
            allergies=[
                PatientAllergyInput(
                    allergy_id="alg-smoke-1",
                    display_text="Peanut allergy",
                )
            ],
            conditions=[
                PatientConditionInput(
                    condition_id="cond-smoke-1",
                    display_text="Type 2 diabetes mellitus",
                )
            ],
        ),
        provider_profile=ProfileReferenceInput(
            profile_id="provider-smoke-test",
            display_name="Smoke Test Provider",
        ),
        provider_context=ProviderContextInput(
            provider=ProviderIdentityInput(
                provider_id="provider-smoke-test",
                display_name="Smoke Test Provider",
                source_type="provider_management",
            ),
            organizations=[
                ProviderOrganizationInput(
                    organization_id="org-smoke-test-1",
                    display_name="Smoke Test Organization One",
                ),
                ProviderOrganizationInput(
                    organization_id="org-smoke-test-2",
                    display_name="Smoke Test Organization Two",
                ),
            ],
            provider_role_relationships=[
                ProviderRoleRelationshipInput(
                    relationship_id="provider-role-smoke-1",
                    organization_id="org-smoke-test-1",
                    role_label="document-author",
                ),
                ProviderRoleRelationshipInput(
                    relationship_id="provider-role-smoke-2",
                    organization_id="org-smoke-test-2",
                    role_label="attending-physician",
                ),
            ],
            selected_provider_role_relationship_id="provider-role-smoke-2",
        ),
        request=BundleRequestInput(
            request_text="Create a deterministic placeholder PS-CA workflow run for retry testing.",
            scenario_label="pytest-smoke-retry-effective-outcome",
        ),
    )

    result = await workflow.run(message=message, include_status_events=True)
    final_output = result.get_outputs()[0]

    assert isinstance(final_output, WorkflowSkeletonRunResult)
    assert final_output.candidate_bundle.candidate_bundle.fhir_bundle["type"] == "collection"
    assert final_output.validation_report.overall_status == "failed"
    assert final_output.repair_decision.overall_decision == "repair_recommended"
    assert final_output.repair_decision.recommended_target == "bundle_finalization"
    assert final_output.repair_execution.execution_outcome == "executed"
    assert final_output.repair_execution.executed_target == "bundle_finalization"
    assert final_output.repair_execution.post_retry_candidate_bundle is not None
    assert final_output.repair_execution.post_retry_validation_report is not None
    assert final_output.repair_execution.post_retry_repair_decision is not None
    assert final_output.effective_outcome.artifact_source == "post_retry"
    assert final_output.effective_outcome.resource_construction == final_output.resource_construction
    assert final_output.effective_outcome.candidate_bundle == final_output.repair_execution.post_retry_candidate_bundle
    assert final_output.effective_outcome.validation_report == final_output.repair_execution.post_retry_validation_report
    assert final_output.effective_outcome.repair_decision == final_output.repair_execution.post_retry_repair_decision
    assert final_output.effective_outcome.candidate_bundle.candidate_bundle.fhir_bundle["type"] == "document"
    assert final_output.effective_outcome.validation_report.overall_status == "passed_with_warnings"
    assert final_output.effective_outcome.repair_decision.overall_decision == "external_validation_pending"


async def test_psca_bundle_builder_workflow_supports_bounded_two_medication_path() -> None:
    message = WorkflowBuildInput(
        specification=SpecificationSelection(),
        patient_profile=ProfileReferenceInput(
            profile_id="patient-smoke-two-meds",
            display_name="Smoke Two Meds Patient",
        ),
        patient_context=PatientContextInput(
            patient=PatientIdentityInput(
                patient_id="patient-smoke-two-meds",
                display_name="Smoke Two Meds Patient",
                source_type="patient_management",
            ),
            medications=[
                PatientMedicationInput(
                    medication_id="med-smoke-1",
                    display_text="Atorvastatin 20 MG oral tablet",
                ),
                PatientMedicationInput(
                    medication_id="med-smoke-2",
                    display_text="Metformin 500 MG oral tablet",
                ),
            ],
            allergies=[],
            conditions=[],
        ),
        provider_profile=ProfileReferenceInput(
            profile_id="provider-smoke-two-meds",
            display_name="Smoke Two Meds Provider",
        ),
        request=BundleRequestInput(
            request_text="Create a deterministic bounded two-medication workflow run for testing.",
            scenario_label="pytest-smoke-two-meds",
        ),
    )

    result = await workflow.run(message=message, include_status_events=True)
    final_output = result.get_outputs()[0]
    clinical_section_contexts = {
        context.section_key: context
        for context in final_output.bundle_schematic.evidence.clinical_section_contexts
    }
    medication_steps = [
        step.step_id
        for step in final_output.build_plan.steps
        if step.step_id.startswith("build-medicationrequest-")
    ]
    candidate_entries = final_output.candidate_bundle.candidate_bundle.fhir_bundle["entry"]

    assert clinical_section_contexts["medications"].available_item_count == 2
    assert clinical_section_contexts["medications"].planned_placeholder_count == 2
    assert clinical_section_contexts["medications"].planned_entry_display_texts == [
        "Atorvastatin 20 MG oral tablet",
        "Metformin 500 MG oral tablet",
    ]
    assert [
        (entry.placeholder_id, entry.source_medication_index, entry.medication_id)
        for entry in final_output.normalized_request.patient_context.planned_medication_entries
    ] == [
        ("medicationrequest-1", 0, "med-smoke-1"),
        ("medicationrequest-2", 1, "med-smoke-2"),
    ]
    assert final_output.normalized_request.patient_context.deferred_additional_medication_count == 0
    assert [
        (entry.placeholder_id, entry.source_medication_index, entry.medication_id)
        for entry in clinical_section_contexts["medications"].planned_medication_entries
    ] == [
        ("medicationrequest-1", 0, "med-smoke-1"),
        ("medicationrequest-2", 1, "med-smoke-2"),
    ]
    assert clinical_section_contexts["medications"].deferred_additional_item_count == 0
    assert clinical_section_contexts["medications"].planning_disposition == "bounded_two_entry_selected_first_two"
    assert medication_steps == ["build-medicationrequest-1", "build-medicationrequest-2"]
    assert "medicationrequest-2" in {
        placeholder.placeholder_id for placeholder in final_output.bundle_schematic.resource_placeholders
    }
    assert final_output.candidate_bundle.candidate_bundle.entry_count == 9
    assert [entry.placeholder_id for entry in final_output.candidate_bundle.entry_assembly][5:7] == [
        "medicationrequest-1",
        "medicationrequest-2",
    ]
    assert final_output.candidate_bundle.evidence.planned_medication_placeholder_ids == [
        "medicationrequest-1",
        "medicationrequest-2",
    ]
    assert final_output.candidate_bundle.evidence.assembled_medication_placeholder_ids == [
        "medicationrequest-1",
        "medicationrequest-2",
    ]
    assert {
        summary.placeholder_id for summary in final_output.candidate_bundle.evidence.placeholder_traceability_summaries
    } >= {"medicationrequest-1", "medicationrequest-2"}
    assert [
        (
            expectation.placeholder_id,
            expectation.alignment_mode,
            expectation.expected_text,
        )
        for expectation in final_output.validation_report.evidence.patient_context_alignment.section_entry_expectations
    ] == [
        (
            "medicationrequest-1",
            "structured_patient_context",
            "Atorvastatin 20 MG oral tablet",
        ),
        (
            "medicationrequest-2",
            "structured_patient_context",
            "Metformin 500 MG oral tablet",
        ),
        (
            "allergyintolerance-1",
            "fallback_placeholder",
            "Allergies and Intolerances placeholder for pytest-smoke-two-meds",
        ),
        (
            "condition-1",
            "fallback_placeholder",
            "Active Problems placeholder for pytest-smoke-two-meds",
        ),
    ]
    assert candidate_entries[5]["resource"]["medicationCodeableConcept"]["text"] == (
        "Atorvastatin 20 MG oral tablet"
    )
    assert candidate_entries[6]["resource"]["medicationCodeableConcept"]["text"] == (
        "Metformin 500 MG oral tablet"
    )
    validation_traceability = {
        summary.placeholder_id: summary
        for summary in final_output.validation_report.evidence.placeholder_traceability_summaries
    }
    assert validation_traceability["medicationrequest-2"].bundle_entry_sequence == 7
    assert (
        "bundle.medicationrequest_2_placeholder_text_aligned_to_context"
        in validation_traceability["medicationrequest-2"].workflow_check_codes
    )
    assert candidate_entries[0]["resource"]["section"][0]["entry"] == [
        {"reference": candidate_entries[5]["fullUrl"]},
        {"reference": candidate_entries[6]["fullUrl"]},
    ]


async def test_psca_bundle_builder_workflow_preserves_current_bounded_scope_after_traceability_hardening() -> None:
    message = WorkflowBuildInput(
        specification=SpecificationSelection(),
        patient_profile=ProfileReferenceInput(
            profile_id="patient-smoke-bounded-scope",
            display_name="Smoke Bounded Scope Patient",
        ),
        patient_context=PatientContextInput(
            patient=PatientIdentityInput(
                patient_id="patient-smoke-bounded-scope",
                display_name="Smoke Bounded Scope Patient",
                source_type="patient_management",
            ),
            medications=[
                PatientMedicationInput(
                    medication_id="med-bounded-1",
                    display_text="Atorvastatin 20 MG oral tablet",
                ),
                PatientMedicationInput(
                    medication_id="med-bounded-2",
                    display_text="Metformin 500 MG oral tablet",
                ),
                PatientMedicationInput(
                    medication_id="med-bounded-3",
                    display_text="Lisinopril 10 MG oral tablet",
                ),
            ],
            allergies=[
                PatientAllergyInput(
                    allergy_id="alg-bounded-1",
                    display_text="Peanut allergy",
                ),
                PatientAllergyInput(
                    allergy_id="alg-bounded-2",
                    display_text="Latex allergy",
                ),
            ],
            conditions=[
                PatientConditionInput(
                    condition_id="cond-bounded-1",
                    display_text="Type 2 diabetes mellitus",
                ),
                PatientConditionInput(
                    condition_id="cond-bounded-2",
                    display_text="Hypertension",
                ),
            ],
        ),
        provider_profile=ProfileReferenceInput(
            profile_id="provider-smoke-bounded-scope",
            display_name="Smoke Bounded Scope Provider",
        ),
        provider_context=ProviderContextInput(
            provider=ProviderIdentityInput(
                provider_id="provider-smoke-bounded-scope",
                display_name="Smoke Bounded Scope Provider",
                source_type="provider_management",
            ),
            organizations=[
                ProviderOrganizationInput(
                    organization_id="org-bounded-1",
                    display_name="Smoke Bounded Scope Organization",
                )
            ],
            provider_role_relationships=[
                ProviderRoleRelationshipInput(
                    relationship_id="provider-role-bounded-1",
                    organization_id="org-bounded-1",
                    role_label="attending-physician",
                )
            ],
            selected_provider_role_relationship_id="provider-role-bounded-1",
        ),
        request=BundleRequestInput(
            request_text="Create a deterministic bounded-scope workflow run for testing.",
            scenario_label="pytest-smoke-bounded-scope",
        ),
    )

    result = await workflow.run(message=message, include_status_events=True)
    final_output = result.get_outputs()[0]

    clinical_section_contexts = {
        context.section_key: context
        for context in final_output.bundle_schematic.evidence.clinical_section_contexts
    }
    schematic_placeholder_ids = {
        placeholder.placeholder_id for placeholder in final_output.bundle_schematic.resource_placeholders
    }
    build_step_ids = [step.step_id for step in final_output.build_plan.steps]
    registry_ids = {entry.placeholder_id for entry in final_output.resource_construction.resource_registry}
    candidate_entry_ids = [entry.placeholder_id for entry in final_output.candidate_bundle.entry_assembly]
    validation_traceability = {
        summary.placeholder_id: summary
        for summary in final_output.validation_report.evidence.placeholder_traceability_summaries
    }

    assert final_output.normalized_request.patient_context.deferred_additional_medication_count == 1
    assert clinical_section_contexts["medications"].planned_placeholder_count == 2
    assert clinical_section_contexts["medications"].deferred_additional_item_count == 1
    assert clinical_section_contexts["medications"].planning_disposition == "bounded_two_entry_selected_first_two"
    assert clinical_section_contexts["allergies"].available_item_count == 2
    assert clinical_section_contexts["allergies"].selected_single_entry_display_text is None
    assert clinical_section_contexts["allergies"].planned_placeholder_count == 1
    assert clinical_section_contexts["allergies"].planning_disposition == "fixed_single_entry_multiple_items_deferred"
    assert clinical_section_contexts["problems"].available_item_count == 2
    assert clinical_section_contexts["problems"].selected_single_entry_display_text is None
    assert clinical_section_contexts["problems"].planned_placeholder_count == 1
    assert clinical_section_contexts["problems"].planning_disposition == "fixed_single_entry_multiple_items_deferred"
    assert schematic_placeholder_ids >= {
        "medicationrequest-1",
        "medicationrequest-2",
        "allergyintolerance-1",
        "condition-1",
    }
    assert "allergyintolerance-2" not in schematic_placeholder_ids
    assert "condition-2" not in schematic_placeholder_ids
    assert "medicationrequest-3" not in schematic_placeholder_ids
    assert "build-medicationrequest-2" in build_step_ids
    assert "build-allergyintolerance-2" not in build_step_ids
    assert "build-condition-2" not in build_step_ids
    assert "medicationrequest-3" not in registry_ids
    assert candidate_entry_ids.count("allergyintolerance-1") == 1
    assert candidate_entry_ids.count("condition-1") == 1
    assert "allergyintolerance-2" not in candidate_entry_ids
    assert "condition-2" not in candidate_entry_ids
    assert "medicationrequest-3" not in candidate_entry_ids
    assert final_output.candidate_bundle.evidence.planned_medication_placeholder_ids == [
        "medicationrequest-1",
        "medicationrequest-2",
    ]
    assert final_output.candidate_bundle.evidence.assembled_medication_placeholder_ids == [
        "medicationrequest-1",
        "medicationrequest-2",
    ]
    assert {
        "telecom",
        "address",
        "qualification",
    }.issubset(final_output.resource_construction.step_results[1].resource_scaffold.deferred_paths)
    assert {
        "specialty",
        "telecom",
        "period",
        "availableTime",
    }.issubset(final_output.resource_construction.step_results[3].resource_scaffold.deferred_paths)
    assert (
        final_output.validation_report.evidence.provider_context_alignment.organization_alignment_mode
        == "structured_provider_context"
    )
    assert (
        final_output.validation_report.evidence.provider_context_alignment.practitionerrole_alignment_mode
        == "structured_provider_context"
    )
    assert (
        "bundle.organization_identity_aligned_to_context"
        in validation_traceability["organization-1"].workflow_check_codes
    )
    assert (
        "bundle.practitionerrole_author_context_aligned_to_context"
        in validation_traceability["practitionerrole-1"].workflow_check_codes
    )


async def test_psca_bundle_builder_workflow_accepts_authored_patient_context_mapping() -> None:
    authored = build_patient_authored_record(
        PatientAuthoringInput(
            authoring_text=(
                "The patient's name is Nora Field. She is a female age 55 who lives in Red Deer, Alberta. "
                "She has diabetes, takes metformin, and has a peanut allergy."
            ),
            complexity_level="medium",
            scenario_label="pytest-authored-workflow",
        )
    )
    mapped = map_authored_patient_to_patient_context(authored)

    result = await workflow.run(
        message=WorkflowBuildInput(
            specification=SpecificationSelection(),
            patient_profile=ProfileReferenceInput(
                profile_id="patient-profile-authored-workflow",
                display_name="Authored Workflow Patient",
            ),
            patient_context=mapped.patient_context,
            provider_profile=ProfileReferenceInput(
                profile_id="provider-authored-workflow",
                display_name="Authored Workflow Provider",
            ),
            request=BundleRequestInput(
                request_text="Create a deterministic bundle from authored patient context.",
                scenario_label="pytest-authored-workflow",
            ),
        ),
        include_status_events=True,
    )
    final_output = result.get_outputs()[0]

    assert final_output.normalized_request.patient_context.patient.patient_id == authored.patient.patient_id
    assert final_output.normalized_request.patient_context.patient.display_name == "Nora Field"
    assert final_output.resource_construction.step_results[0].resource_scaffold.fhir_scaffold["name"][0]["text"] == (
        "Nora Field"
    )
    assert (
        final_output.resource_construction.step_results[5].resource_scaffold.fhir_scaffold["medicationCodeableConcept"]["text"]
        == "Metformin 500 MG oral tablet"
    )
    assert final_output.resource_construction.step_results[6].resource_scaffold.fhir_scaffold["code"]["text"] == (
        "Peanut allergy"
    )
    assert final_output.resource_construction.step_results[7].resource_scaffold.fhir_scaffold["code"]["text"] == (
        "Type 2 diabetes mellitus"
    )
    assert final_output.validation_report.workflow_validation.status == "passed"


async def test_psca_bundle_builder_workflow_accepts_authored_provider_context_mapping() -> None:
    authored = build_provider_authored_record(
        ProviderAuthoringInput(
            authoring_text=(
                "The provider's name is Maya Chen. "
                "She is a female oncologist at Fraser Cancer Clinic."
            ),
            scenario_label="pytest-authored-provider-workflow",
        )
    )
    mapped = map_authored_provider_to_provider_context(authored)

    result = await workflow.run(
        message=WorkflowBuildInput(
            specification=SpecificationSelection(),
            patient_profile=ProfileReferenceInput(
                profile_id="patient-profile-authored-provider-workflow",
                display_name="Authored Provider Workflow Patient",
            ),
            provider_profile=ProfileReferenceInput(
                profile_id="provider-profile-authored-provider-workflow",
                display_name="Authored Provider Workflow Provider",
            ),
            provider_context=mapped.provider_context,
            request=BundleRequestInput(
                request_text="Create a deterministic bundle from authored provider context.",
                scenario_label="pytest-authored-provider-workflow",
            ),
        ),
        include_status_events=True,
    )
    final_output = result.get_outputs()[0]

    assert final_output.normalized_request.provider_context.provider.provider_id == authored.provider.provider_id
    assert final_output.normalized_request.provider_context.provider.display_name == "Maya Chen"
    assert final_output.normalized_request.provider_context.selected_provider_role_relationship is not None
    assert (
        final_output.normalized_request.provider_context.selected_provider_role_relationship.role_label
        == "oncologist"
    )
    assert final_output.normalized_request.provider_context.selected_organization is not None
    assert final_output.normalized_request.provider_context.selected_organization.display_name == (
        "Fraser Cancer Clinic"
    )
    assert final_output.resource_construction.step_results[1].resource_scaffold.fhir_scaffold["name"][0]["text"] == (
        "Maya Chen"
    )
    assert (
        final_output.resource_construction.step_results[2].resource_scaffold.fhir_scaffold["name"]
        == "Fraser Cancer Clinic"
    )
    assert (
        final_output.resource_construction.step_results[3].resource_scaffold.fhir_scaffold["code"][0]["text"]
        == "oncologist"
    )
    assert final_output.validation_report.workflow_validation.status == "passed"


class _WorkflowFakeMedicationGateway:
    def __init__(self, config: OpenAIGatewayConfig) -> None:
        self._config = config

    @property
    def model_name(self) -> str:
        return self._config.model_name

    async def create_json_completion(self, **_: object) -> OpenAIJSONCompletionResponse:
        raw_text = (
            '{"resourceType":"MedicationRequest","id":"medicationrequest-1","status":"draft",'
            '"intent":"proposal","subject":{"reference":"Patient/patient-1"},'
            '"medicationCodeableConcept":{"text":"Atorvastatin 20 MG oral tablet"}}'
        )
        return OpenAIJSONCompletionResponse(
            response_id="resp_workflow_test_123",
            raw_text=raw_text,
            raw_response_json={"id": "resp_workflow_test_123", "choices": [{"message": {"content": raw_text}}]},
        )


async def test_psca_bundle_builder_workflow_runs_medication_request_agent_when_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("FHIR_BUNDLE_BUILDER_MEDICATION_AGENT_MODEL", "gpt-test")
    monkeypatch.setattr(
        medication_agent_module,
        "OpenAIChatCompletionsGateway",
        _WorkflowFakeMedicationGateway,
    )

    message = WorkflowBuildInput(
        specification=SpecificationSelection(),
        patient_profile=ProfileReferenceInput(
            profile_id="patient-smoke-test-agent",
            display_name="Smoke Test Patient Agent",
        ),
        patient_context=PatientContextInput(
            patient=PatientIdentityInput(
                patient_id="patient-smoke-test-agent",
                display_name="Smoke Test Patient Agent",
                source_type="patient_management",
                administrative_gender="female",
                birth_date="1985-02-14",
            ),
            medications=[
                PatientMedicationInput(
                    medication_id="med-smoke-1",
                    display_text="Atorvastatin 20 MG oral tablet",
                )
            ],
            allergies=[
                PatientAllergyInput(
                    allergy_id="alg-smoke-1",
                    display_text="Peanut allergy",
                )
            ],
            conditions=[
                PatientConditionInput(
                    condition_id="cond-smoke-1",
                    display_text="Type 2 diabetes mellitus",
                )
            ],
        ),
        provider_profile=ProfileReferenceInput(
            profile_id="provider-smoke-test-agent",
            display_name="Smoke Test Provider Agent",
        ),
        provider_context=ProviderContextInput(
            provider=ProviderIdentityInput(
                provider_id="provider-smoke-test-agent",
                display_name="Smoke Test Provider Agent",
                source_type="provider_management",
            ),
            organizations=[
                ProviderOrganizationInput(
                    organization_id="org-smoke-test-agent",
                    display_name="Smoke Test Organization Agent",
                )
            ],
            provider_role_relationships=[
                ProviderRoleRelationshipInput(
                    relationship_id="provider-role-smoke-agent",
                    organization_id="org-smoke-test-agent",
                    role_label="attending-physician",
                )
            ],
        ),
        request=BundleRequestInput(
            request_text="Create a PS-CA workflow run with one agent-backed medication request.",
            scenario_label="pytest-smoke-agent",
        ),
        workflow_options=WorkflowOptionsInput(
            medication_request_generation_mode="agent_required",
        ),
    )

    result = await workflow.run(message=message, include_status_events=True)
    final_output = result.get_outputs()[0]

    medication_step = next(
        step
        for step in final_output.resource_construction.step_results
        if step.step_id == "build-medicationrequest-1"
    )
    assert final_output.normalized_request.workflow_defaults.medication_request_generation_mode == (
        "agent_required"
    )
    assert final_output.resource_construction.evidence.agent_step_ids == ["build-medicationrequest-1"]
    assert medication_step.medication_agent_trace is not None
    assert medication_step.medication_agent_trace.status == "accepted"
    assert medication_step.medication_agent_trace.provider == "openai"
    assert medication_step.medication_agent_trace.model_name == "gpt-test"
    assert (
        medication_step.resource_scaffold.fhir_scaffold["medicationCodeableConcept"]["text"]
        == "Atorvastatin 20 MG oral tablet"
    )
    medication_entry = next(
        entry
        for entry in final_output.candidate_bundle.candidate_bundle.fhir_bundle["entry"]
        if entry["resource"]["id"] == "medicationrequest-1"
    )
    assert medication_entry["resource"]["medicationCodeableConcept"]["text"] == (
        "Atorvastatin 20 MG oral tablet"
    )
    assert final_output.validation_report.workflow_validation.status == "passed"


async def test_psca_bundle_builder_workflow_fails_clearly_when_agent_mode_lacks_model_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("FHIR_BUNDLE_BUILDER_MEDICATION_AGENT_MODEL", raising=False)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        await workflow.run(
            message=WorkflowBuildInput(
                specification=SpecificationSelection(),
                patient_profile=ProfileReferenceInput(
                    profile_id="patient-smoke-test-agent-fail",
                    display_name="Smoke Test Patient Agent Fail",
                ),
                patient_context=PatientContextInput(
                    patient=PatientIdentityInput(
                        patient_id="patient-smoke-test-agent-fail",
                        display_name="Smoke Test Patient Agent Fail",
                        source_type="patient_management",
                    ),
                    medications=[
                        PatientMedicationInput(
                            medication_id="med-smoke-1",
                            display_text="Atorvastatin 20 MG oral tablet",
                        )
                    ],
                ),
                provider_profile=ProfileReferenceInput(
                    profile_id="provider-smoke-test-agent-fail",
                    display_name="Smoke Test Provider Agent Fail",
                ),
                request=BundleRequestInput(
                    request_text="Create a PS-CA workflow run with one agent-backed medication request.",
                    scenario_label="pytest-smoke-agent-fail",
                ),
                workflow_options=WorkflowOptionsInput(
                    medication_request_generation_mode="agent_required",
                ),
            ),
            include_status_events=True,
        )
