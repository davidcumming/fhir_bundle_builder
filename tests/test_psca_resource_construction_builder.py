"""Direct tests for deterministic PS-CA resource scaffold construction."""

from __future__ import annotations

from fhir_bundle_builder.specifications.psca import PscaAssetQuery, PscaAssetRepository
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.build_plan_builder import (
    build_psca_build_plan,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.models import (
    BundleRequestInput,
    NormalizedBuildRequest,
    ProfileReferenceInput,
    SpecificationSelection,
    WorkflowDefaults,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.resource_construction_builder import (
    build_psca_resource_construction_result,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.schematic_builder import (
    build_psca_bundle_schematic,
)


def test_psca_resource_construction_builder_generates_scaffolds_and_registry() -> None:
    repository = PscaAssetRepository()
    normalized_assets = repository.load_foundation_context(PscaAssetQuery())
    schematic = build_psca_bundle_schematic(normalized_assets)
    plan = build_psca_build_plan(schematic)
    normalized_request = NormalizedBuildRequest(
        stage_id="request_normalization",
        status="placeholder_complete",
        summary="Test normalized request.",
        placeholder_note="Test artifact.",
        source_refs=[],
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
            scenario_label="pytest-resource",
        ),
        workflow_defaults=WorkflowDefaults(
            bundle_type="document",
            specification_mode="normalized-asset-foundation",
            validation_mode="foundational_dual_channel",
            resource_construction_mode="deterministic_content_enriched_foundation",
        ),
        run_label="pytest-resource:ca.infoway.io.psca:2.1.1-DFT",
    )

    construction = build_psca_resource_construction_result(plan, schematic, normalized_request)

    assert construction.construction_mode == "deterministic_content_enriched"
    assert [step.step_id for step in construction.step_results] == [step.step_id for step in plan.steps]
    assert len(construction.step_results) == 9
    assert len(construction.resource_registry) == 8

    steps = {step.step_id: step for step in construction.step_results}
    registry = {entry.placeholder_id: entry for entry in construction.resource_registry}

    assert steps["build-composition-1-scaffold"].execution_status == "scaffold_created"
    assert steps["finalize-composition-1"].execution_status == "scaffold_updated"

    practitioner_role = registry["practitionerrole-1"].current_scaffold.fhir_scaffold
    assert practitioner_role["practitioner"]["reference"] == "Practitioner/practitioner-1"
    assert practitioner_role["organization"]["reference"] == "Organization/organization-1"

    medication = registry["medicationrequest-1"].current_scaffold.fhir_scaffold
    allergy = registry["allergyintolerance-1"].current_scaffold.fhir_scaffold
    condition = registry["condition-1"].current_scaffold.fhir_scaffold
    patient = registry["patient-1"].current_scaffold.fhir_scaffold
    section_titles = {section.section_key: section.title for section in schematic.section_scaffolds}
    assert medication["subject"]["reference"] == "Patient/patient-1"
    assert medication["status"] == "draft"
    assert medication["intent"] == "proposal"
    assert medication["medicationCodeableConcept"]["text"] == (
        f"{section_titles['medications']} placeholder for pytest-resource"
    )
    assert allergy["patient"]["reference"] == "Patient/patient-1"
    assert allergy["clinicalStatus"]["coding"][0]["code"] == "active"
    assert allergy["verificationStatus"]["coding"][0]["code"] == "unconfirmed"
    assert allergy["code"]["text"] == f"{section_titles['allergies']} placeholder for pytest-resource"
    assert condition["subject"]["reference"] == "Patient/patient-1"
    assert condition["clinicalStatus"]["coding"][0]["code"] == "active"
    assert condition["verificationStatus"]["coding"][0]["code"] == "provisional"
    assert condition["code"]["text"] == f"{section_titles['problems']} placeholder for pytest-resource"
    assert patient["active"] is True
    assert patient["identifier"][0]["value"] == "patient-resource-test"
    assert patient["name"][0]["text"] == "Resource Test Patient"

    composition_scaffold = steps["build-composition-1-scaffold"].resource_scaffold.fhir_scaffold
    assert composition_scaffold["type"]["coding"][0]["system"] == "http://loinc.org"
    assert composition_scaffold["type"]["coding"][0]["code"] == "60591-5"
    assert composition_scaffold["status"] == "final"
    assert composition_scaffold["title"] == "PS-CA document bundle skeleton - pytest-resource"
    assert composition_scaffold["subject"]["reference"] == "Patient/patient-1"
    assert composition_scaffold["author"][0]["reference"] == "PractitionerRole/practitionerrole-1"
    assert composition_scaffold["section"] == []
    assert steps["build-patient-1"].resource_scaffold.deferred_paths == ["gender", "birthDate"]
    assert any(
        evidence.target_path == "identifier[0].value" and evidence.source_detail == "patient_profile.profile_id"
        for evidence in steps["build-patient-1"].deterministic_value_evidence
    )
    assert any(
        evidence.target_path == "title" and evidence.source_detail == "bundle_intent + scenario_label"
        for evidence in steps["build-composition-1-scaffold"].deterministic_value_evidence
    )
    assert any(
        evidence.target_path == "medicationCodeableConcept.text"
        for evidence in steps["build-medicationrequest-1"].deterministic_value_evidence
    )

    finalized_composition = registry["composition-1"].current_scaffold
    assert finalized_composition.scaffold_state == "sections_attached"
    assert finalized_composition.source_step_ids == [
        "build-composition-1-scaffold",
        "finalize-composition-1",
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
