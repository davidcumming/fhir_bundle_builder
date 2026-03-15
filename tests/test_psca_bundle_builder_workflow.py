"""Smoke tests for the PS-CA workflow skeleton."""

from __future__ import annotations

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
    WorkflowSkeletonRunResult,
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

    completed_executors = [
        event.executor_id
        for event in result
        if event.type == "executor_completed" and getattr(event, "executor_id", None) is not None
    ]
    assert completed_executors == final_output.stage_order


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
    assert candidate_entries[0]["resource"]["section"][0]["entry"] == [
        {"reference": candidate_entries[5]["fullUrl"]},
        {"reference": candidate_entries[6]["fullUrl"]},
    ]
