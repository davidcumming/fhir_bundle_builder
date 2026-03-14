"""Direct tests for deterministic PS-CA resource scaffold construction."""

from __future__ import annotations

from fhir_bundle_builder.specifications.psca import PscaAssetQuery, PscaAssetRepository
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.build_plan_builder import (
    build_psca_build_plan,
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

    construction = build_psca_resource_construction_result(plan, schematic)

    assert construction.construction_mode == "deterministic_scaffold_only"
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
    assert medication["subject"]["reference"] == "Patient/patient-1"
    assert allergy["patient"]["reference"] == "Patient/patient-1"
    assert condition["subject"]["reference"] == "Patient/patient-1"

    composition_scaffold = steps["build-composition-1-scaffold"].resource_scaffold.fhir_scaffold
    assert composition_scaffold["type"]["coding"][0]["system"] == "http://loinc.org"
    assert composition_scaffold["type"]["coding"][0]["code"] == "60591-5"
    assert composition_scaffold["subject"]["reference"] == "Patient/patient-1"
    assert composition_scaffold["author"][0]["reference"] == "PractitionerRole/practitionerrole-1"
    assert composition_scaffold["section"] == []

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
