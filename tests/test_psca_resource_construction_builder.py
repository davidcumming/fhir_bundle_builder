"""Direct tests for deterministic PS-CA resource scaffold construction."""

from __future__ import annotations

from fhir_bundle_builder.specifications.psca import PscaAssetQuery, PscaAssetRepository
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.build_plan_builder import (
    build_psca_build_plan,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.models import (
    BundleRequestInput,
    NormalizedBuildRequest,
    PatientAllergyInput,
    PatientConditionInput,
    PatientContextInput,
    PatientIdentityInput,
    PatientMedicationInput,
    ProfileReferenceInput,
    ResourceConstructionRepairDirective,
    SpecificationSelection,
    WorkflowBuildInput,
    ProviderContextInput,
    ProviderIdentityInput,
    ProviderOrganizationInput,
    ProviderRoleRelationshipInput,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.request_normalization_builder import (
    build_psca_normalized_request,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.resource_construction_builder import (
    SELECTED_PROVIDER_ORGANIZATION_IDENTIFIER_SYSTEM,
    SELECTED_PROVIDER_ROLE_RELATIONSHIP_IDENTIFIER_SYSTEM,
    build_psca_resource_construction_result,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.schematic_builder import (
    build_psca_bundle_schematic,
)


def test_psca_resource_construction_builder_generates_scaffolds_and_registry() -> None:
    repository = PscaAssetRepository()
    normalized_assets = repository.load_foundation_context(PscaAssetQuery())
    normalized_request = _build_normalized_request("pytest-resource")
    schematic = build_psca_bundle_schematic(normalized_assets, normalized_request)
    plan = build_psca_build_plan(schematic)

    construction = build_psca_resource_construction_result(plan, schematic, normalized_request)

    assert construction.construction_mode == "deterministic_content_enriched"
    assert [step.step_id for step in construction.step_results] == [step.step_id for step in plan.steps]
    assert len(construction.step_results) == 11
    assert len(construction.resource_registry) == 8

    steps = {step.step_id: step for step in construction.step_results}
    registry = {entry.placeholder_id: entry for entry in construction.resource_registry}

    assert steps["build-composition-1-scaffold"].execution_status == "scaffold_created"
    assert steps["finalize-composition-1-medications-section"].execution_status == "scaffold_updated"
    assert steps["finalize-composition-1-allergies-section"].execution_status == "scaffold_updated"
    assert steps["finalize-composition-1-problems-section"].execution_status == "scaffold_updated"

    practitioner_role = registry["practitionerrole-1"].current_scaffold.fhir_scaffold
    practitioner = registry["practitioner-1"].current_scaffold.fhir_scaffold
    organization = registry["organization-1"].current_scaffold.fhir_scaffold
    assert practitioner_role["practitioner"]["reference"] == "Practitioner/practitioner-1"
    assert practitioner_role["organization"]["reference"] == "Organization/organization-1"
    assert practitioner_role["identifier"][0]["system"] == SELECTED_PROVIDER_ROLE_RELATIONSHIP_IDENTIFIER_SYSTEM
    assert practitioner_role["identifier"][0]["value"] == "provider-role-1"
    assert practitioner_role["code"][0]["text"] == "attending-physician"
    assert practitioner["active"] is True
    assert practitioner["identifier"][0]["value"] == "provider-resource-test"
    assert practitioner["name"][0]["text"] == "Resource Test Provider"
    assert organization["identifier"][0]["system"] == SELECTED_PROVIDER_ORGANIZATION_IDENTIFIER_SYSTEM
    assert organization["identifier"][0]["value"] == "org-resource-test"
    assert organization["name"] == "Resource Test Organization"

    medication = registry["medicationrequest-1"].current_scaffold.fhir_scaffold
    allergy = registry["allergyintolerance-1"].current_scaffold.fhir_scaffold
    condition = registry["condition-1"].current_scaffold.fhir_scaffold
    patient = registry["patient-1"].current_scaffold.fhir_scaffold
    assert medication["subject"]["reference"] == "Patient/patient-1"
    assert medication["status"] == "draft"
    assert medication["intent"] == "proposal"
    assert medication["medicationCodeableConcept"]["text"] == "Atorvastatin 20 MG oral tablet"
    assert allergy["patient"]["reference"] == "Patient/patient-1"
    assert allergy["clinicalStatus"]["coding"][0]["code"] == "active"
    assert allergy["verificationStatus"]["coding"][0]["code"] == "unconfirmed"
    assert allergy["code"]["text"] == "Peanut allergy"
    assert condition["subject"]["reference"] == "Patient/patient-1"
    assert condition["clinicalStatus"]["coding"][0]["code"] == "active"
    assert condition["verificationStatus"]["coding"][0]["code"] == "provisional"
    assert condition["code"]["text"] == "Type 2 diabetes mellitus"
    assert patient["active"] is True
    assert patient["identifier"][0]["value"] == "patient-resource-test"
    assert patient["name"][0]["text"] == "Resource Test Patient"
    assert patient["gender"] == "female"
    assert patient["birthDate"] == "1985-02-14"

    composition_scaffold = steps["build-composition-1-scaffold"].resource_scaffold.fhir_scaffold
    assert composition_scaffold["type"]["coding"][0]["system"] == "http://loinc.org"
    assert composition_scaffold["type"]["coding"][0]["code"] == "60591-5"
    assert composition_scaffold["status"] == "final"
    assert composition_scaffold["title"] == "PS-CA document bundle skeleton - pytest-resource"
    assert composition_scaffold["subject"]["reference"] == "Patient/patient-1"
    assert composition_scaffold["author"][0]["reference"] == "PractitionerRole/practitionerrole-1"
    assert composition_scaffold["section"] == []
    assert steps["build-patient-1"].resource_scaffold.deferred_paths == []
    assert steps["build-practitioner-1"].resource_scaffold.deferred_paths == ["telecom", "address", "qualification"]
    assert steps["build-organization-1"].resource_scaffold.deferred_paths == []
    assert steps["build-practitionerrole-1"].resource_scaffold.deferred_paths == [
        "specialty",
        "telecom",
        "period",
        "availableTime",
    ]
    assert any(
        evidence.target_path == "identifier[0].value" and evidence.source_detail == "patient.patient_id"
        for evidence in steps["build-patient-1"].deterministic_value_evidence
    )
    assert any(
        evidence.target_path == "gender" and evidence.source_detail == "patient.administrative_gender"
        for evidence in steps["build-patient-1"].deterministic_value_evidence
    )
    assert any(
        evidence.target_path == "birthDate" and evidence.source_detail == "patient.birth_date"
        for evidence in steps["build-patient-1"].deterministic_value_evidence
    )
    assert any(
        evidence.target_path == "identifier[0].value" and evidence.source_detail == "provider.provider_id"
        for evidence in steps["build-practitioner-1"].deterministic_value_evidence
    )
    assert any(
        evidence.target_path == "name[0].text" and evidence.source_detail == "provider.display_name"
        for evidence in steps["build-practitioner-1"].deterministic_value_evidence
    )
    assert any(
        evidence.target_path == "identifier[0].system"
        and evidence.source_detail == "fixed selected provider-role relationship identifier system"
        for evidence in steps["build-practitionerrole-1"].deterministic_value_evidence
    )
    assert any(
        evidence.target_path == "identifier[0].value" and evidence.source_detail == "relationship_id"
        for evidence in steps["build-practitionerrole-1"].deterministic_value_evidence
    )
    assert any(
        evidence.target_path == "code[0].text" and evidence.source_detail == "role_label"
        for evidence in steps["build-practitionerrole-1"].deterministic_value_evidence
    )
    assert any(
        evidence.target_path == "identifier[0].system"
        and evidence.source_detail == "fixed selected provider organization identifier system"
        for evidence in steps["build-organization-1"].deterministic_value_evidence
    )
    assert any(
        evidence.target_path == "identifier[0].value" and evidence.source_detail == "organization_id"
        for evidence in steps["build-organization-1"].deterministic_value_evidence
    )
    assert any(
        evidence.target_path == "title" and evidence.source_detail == "bundle_intent + scenario_label"
        for evidence in steps["build-composition-1-scaffold"].deterministic_value_evidence
    )
    assert any(
        evidence.target_path == "medicationCodeableConcept.text"
        and evidence.source_detail == "display_text"
        for evidence in steps["build-medicationrequest-1"].deterministic_value_evidence
    )
    assert any(
        evidence.target_path == "code.text" and evidence.source_detail == "display_text"
        for evidence in steps["build-allergyintolerance-1"].deterministic_value_evidence
    )
    assert any(
        evidence.target_path == "code.text" and evidence.source_detail == "display_text"
        for evidence in steps["build-condition-1"].deterministic_value_evidence
    )

    finalized_composition = registry["composition-1"].current_scaffold
    assert finalized_composition.scaffold_state == "sections_attached"
    assert finalized_composition.source_step_ids == [
        "build-composition-1-scaffold",
        "finalize-composition-1-medications-section",
        "finalize-composition-1-allergies-section",
        "finalize-composition-1-problems-section",
    ]
    assert [section["title"] for section in finalized_composition.fhir_scaffold["section"]] == [
        section.title for section in schematic.section_scaffolds
    ]
    assert [
        section["entry"][0]["reference"] for section in finalized_composition.fhir_scaffold["section"]
    ] == [
        "MedicationRequest/medicationrequest-1",
        "AllergyIntolerance/allergyintolerance-1",
        "Condition/condition-1",
    ]
    assert (
        finalized_composition.fhir_scaffold["section"][0]["code"]["coding"][0]["display"]
        == schematic.section_scaffolds[0].title
    )


def test_psca_resource_construction_builder_keeps_organization_thin_in_legacy_provider_profile_mode() -> None:
    repository = PscaAssetRepository()
    normalized_assets = repository.load_foundation_context(PscaAssetQuery())
    normalized_request = _build_legacy_normalized_request("pytest-resource-legacy")
    schematic = build_psca_bundle_schematic(normalized_assets, normalized_request)
    plan = build_psca_build_plan(schematic)

    construction = build_psca_resource_construction_result(plan, schematic, normalized_request)
    registry = {entry.placeholder_id: entry for entry in construction.resource_registry}
    organization = registry["organization-1"].current_scaffold.fhir_scaffold
    practitioner_role = registry["practitionerrole-1"].current_scaffold.fhir_scaffold

    assert "identifier" not in organization
    assert "name" not in organization
    assert "identifier" not in practitioner_role
    assert practitioner_role["code"][0]["text"] == "document-author"
    assert "gender" not in registry["patient-1"].current_scaffold.fhir_scaffold
    assert "birthDate" not in registry["patient-1"].current_scaffold.fhir_scaffold
    assert (
        registry["medicationrequest-1"].current_scaffold.fhir_scaffold["medicationCodeableConcept"]["text"]
        == "Medication Summary section placeholder for pytest-resource-legacy"
    )
    assert construction.step_results[2].resource_scaffold.deferred_paths == ["identifier", "name"]


def test_psca_resource_construction_builder_supports_targeted_patient_repair() -> None:
    repository = PscaAssetRepository()
    normalized_assets = repository.load_foundation_context(PscaAssetQuery())
    normalized_request = _build_normalized_request("pytest-targeted-patient")
    schematic = build_psca_bundle_schematic(normalized_assets, normalized_request)
    plan = build_psca_build_plan(schematic)
    full_result = build_psca_resource_construction_result(plan, schematic, normalized_request)
    repair_directive = ResourceConstructionRepairDirective(
        directive_basis="validation_finding_code_map",
        scope="build_step_subset",
        trigger_finding_codes=["bundle.patient_identity_content_present"],
        target_step_ids=["build-patient-1"],
        target_placeholder_ids=["patient-1"],
        rationale="Rerun the patient anchor step to restore deterministic patient identity content.",
    )

    targeted_result = build_psca_resource_construction_result(
        plan,
        schematic,
        normalized_request,
        prior_result=full_result,
        repair_directive=repair_directive,
    )

    assert targeted_result.execution_scope == "targeted_repair"
    assert targeted_result.applied_repair_directive == repair_directive
    assert [step.step_id for step in targeted_result.step_results] == ["build-patient-1"]
    assert targeted_result.regenerated_placeholder_ids == ["patient-1"]
    assert "patient-1" not in targeted_result.reused_placeholder_ids
    assert set(targeted_result.reused_placeholder_ids) == {
        "practitioner-1",
        "organization-1",
        "practitionerrole-1",
        "composition-1",
        "medicationrequest-1",
        "allergyintolerance-1",
        "condition-1",
    }
    registry = {entry.placeholder_id: entry for entry in targeted_result.resource_registry}
    assert set(registry) == {
        "patient-1",
        "practitioner-1",
        "organization-1",
        "practitionerrole-1",
        "composition-1",
        "medicationrequest-1",
        "allergyintolerance-1",
        "condition-1",
    }
    assert registry["patient-1"].latest_step_id == "build-patient-1"
    assert registry["patient-1"].current_scaffold.fhir_scaffold["name"][0]["text"] == "Resource Test Patient"
    assert registry["composition-1"].current_scaffold.source_step_ids == [
        "build-composition-1-scaffold",
        "finalize-composition-1-medications-section",
        "finalize-composition-1-allergies-section",
        "finalize-composition-1-problems-section",
    ]


def test_psca_resource_construction_builder_supports_targeted_composition_section_repair() -> None:
    repository = PscaAssetRepository()
    normalized_assets = repository.load_foundation_context(PscaAssetQuery())
    normalized_request = _build_normalized_request("pytest-targeted-composition")
    schematic = build_psca_bundle_schematic(normalized_assets, normalized_request)
    plan = build_psca_build_plan(schematic)
    full_result = build_psca_resource_construction_result(plan, schematic, normalized_request)
    repair_directive = ResourceConstructionRepairDirective(
        directive_basis="validation_finding_code_map",
        scope="build_step_subset",
        trigger_finding_codes=["bundle.composition_allergies_section_present"],
        target_step_ids=["finalize-composition-1-allergies-section"],
        target_placeholder_ids=["composition-1"],
        rationale="Rerun allergies section finalization to reattach the deterministic allergies section block.",
    )

    targeted_result = build_psca_resource_construction_result(
        plan,
        schematic,
        normalized_request,
        prior_result=full_result,
        repair_directive=repair_directive,
    )

    assert targeted_result.execution_scope == "targeted_repair"
    assert targeted_result.applied_repair_directive == repair_directive
    assert [step.step_id for step in targeted_result.step_results] == [
        "finalize-composition-1-allergies-section"
    ]
    assert targeted_result.regenerated_placeholder_ids == ["composition-1"]
    assert "composition-1" not in targeted_result.reused_placeholder_ids
    registry = {entry.placeholder_id: entry for entry in targeted_result.resource_registry}
    assert len(registry["composition-1"].current_scaffold.fhir_scaffold["section"]) == 3
    assert [
        section["title"] for section in registry["composition-1"].current_scaffold.fhir_scaffold["section"]
    ] == [section.title for section in schematic.section_scaffolds]
    assert registry["composition-1"].current_scaffold.source_step_ids == [
        "build-composition-1-scaffold",
        "finalize-composition-1-medications-section",
        "finalize-composition-1-allergies-section",
        "finalize-composition-1-problems-section",
    ]


def _build_normalized_request(scenario_label: str) -> NormalizedBuildRequest:
    return build_psca_normalized_request(
        WorkflowBuildInput(
            specification=SpecificationSelection(),
            patient_profile=ProfileReferenceInput(
                profile_id="patient-resource-test",
                display_name="Resource Test Patient",
            ),
            patient_context=PatientContextInput(
                patient=PatientIdentityInput(
                    patient_id="patient-resource-test",
                    display_name="Resource Test Patient",
                    source_type="patient_management",
                    administrative_gender="female",
                    birth_date="1985-02-14",
                ),
                medications=[
                    PatientMedicationInput(
                        medication_id="med-1",
                        display_text="Atorvastatin 20 MG oral tablet",
                    )
                ],
                allergies=[
                    PatientAllergyInput(
                        allergy_id="alg-1",
                        display_text="Peanut allergy",
                    )
                ],
                conditions=[
                    PatientConditionInput(
                        condition_id="cond-1",
                        display_text="Type 2 diabetes mellitus",
                    )
                ],
            ),
            provider_profile=ProfileReferenceInput(
                profile_id="provider-resource-test",
                display_name="Resource Test Provider",
            ),
            provider_context=ProviderContextInput(
                provider=ProviderIdentityInput(
                    provider_id="provider-resource-test",
                    display_name="Resource Test Provider",
                    source_type="provider_management",
                ),
                organizations=[
                    ProviderOrganizationInput(
                        organization_id="org-resource-test",
                        display_name="Resource Test Organization",
                    )
                ],
                provider_role_relationships=[
                    ProviderRoleRelationshipInput(
                        relationship_id="provider-role-1",
                        organization_id="org-resource-test",
                        role_label="attending-physician",
                    )
                ],
            ),
            request=BundleRequestInput(
                request_text="Create a deterministic resource construction result for testing.",
                scenario_label=scenario_label,
            ),
        )
    )


def _build_legacy_normalized_request(scenario_label: str) -> NormalizedBuildRequest:
    return build_psca_normalized_request(
        WorkflowBuildInput(
            specification=SpecificationSelection(),
            patient_profile=ProfileReferenceInput(
                profile_id="patient-resource-test",
                display_name="Resource Test Patient",
            ),
            provider_profile=ProfileReferenceInput(
                profile_id="provider-resource-test",
                display_name="Resource Test Provider",
            ),
            request=BundleRequestInput(
                request_text="Create a deterministic resource construction result for testing.",
                scenario_label=scenario_label,
            ),
        )
    )
