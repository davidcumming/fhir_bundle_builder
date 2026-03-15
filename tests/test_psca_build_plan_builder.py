"""Direct tests for deterministic PS-CA build-plan generation."""

from __future__ import annotations

from fhir_bundle_builder.specifications.psca import PscaAssetQuery, PscaAssetRepository
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.models import (
    BundleRequestInput,
    PatientAllergyInput,
    PatientConditionInput,
    PatientContextInput,
    PatientIdentityInput,
    PatientMedicationInput,
    ProfileReferenceInput,
    SpecificationSelection,
    WorkflowBuildInput,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.request_normalization_builder import (
    build_psca_normalized_request,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.build_plan_builder import (
    build_psca_build_plan,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.schematic_builder import (
    build_psca_bundle_schematic,
)


def test_psca_build_plan_builder_generates_expected_order_and_dependencies() -> None:
    repository = PscaAssetRepository()
    normalized_assets = repository.load_foundation_context(PscaAssetQuery())
    normalized_request = build_psca_normalized_request(
        WorkflowBuildInput(
            specification=SpecificationSelection(),
            patient_profile=ProfileReferenceInput(
                profile_id="patient-plan-test",
                display_name="Plan Test Patient",
            ),
            patient_context=PatientContextInput(
                patient=PatientIdentityInput(
                    patient_id="patient-plan-test",
                    display_name="Plan Test Patient",
                    source_type="patient_management",
                ),
                medications=[
                    PatientMedicationInput(
                        medication_id="med-plan-1",
                        display_text="Atorvastatin 20 MG oral tablet",
                    )
                ],
                allergies=[
                    PatientAllergyInput(
                        allergy_id="alg-plan-1",
                        display_text="Peanut allergy",
                    )
                ],
                conditions=[
                    PatientConditionInput(
                        condition_id="cond-plan-1",
                        display_text="Type 2 diabetes mellitus",
                    )
                ],
            ),
            provider_profile=ProfileReferenceInput(
                profile_id="provider-plan-test",
                display_name="Plan Test Provider",
            ),
            request=BundleRequestInput(
                request_text="Create a deterministic build plan for testing.",
                scenario_label="pytest-build-plan",
            ),
        )
    )
    schematic = build_psca_bundle_schematic(normalized_assets, normalized_request)

    plan = build_psca_build_plan(schematic)

    assert plan.plan_basis == "deterministic_schematic_dependency_plan"
    assert plan.composition_strategy == "scaffold_then_incremental_section_finalize"
    assert [step.step_id for step in plan.steps] == [
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

    steps = {step.step_id: step for step in plan.steps}
    assert steps["build-patient-1"].step_kind == "anchor_resource"
    assert steps["build-practitionerrole-1"].step_kind == "support_resource"
    assert steps["build-composition-1-scaffold"].step_kind == "composition_scaffold"
    assert steps["finalize-composition-1-medications-section"].step_kind == "composition_finalize"
    assert steps["finalize-composition-1-allergies-section"].step_kind == "composition_finalize"
    assert steps["finalize-composition-1-problems-section"].step_kind == "composition_finalize"

    assert [dependency.prerequisite_step_id for dependency in steps["build-practitionerrole-1"].dependencies] == [
        "build-practitioner-1",
        "build-organization-1",
    ]
    assert [dependency.prerequisite_step_id for dependency in steps["build-composition-1-scaffold"].dependencies] == [
        "build-patient-1",
        "build-practitionerrole-1",
    ]
    assert [
        dependency.prerequisite_step_id
        for dependency in steps["finalize-composition-1-medications-section"].dependencies
    ] == [
        "build-composition-1-scaffold",
        "build-medicationrequest-1",
    ]
    assert [
        dependency.prerequisite_step_id
        for dependency in steps["finalize-composition-1-allergies-section"].dependencies
    ] == [
        "finalize-composition-1-medications-section",
        "build-allergyintolerance-1",
    ]
    assert [
        dependency.prerequisite_step_id
        for dependency in steps["finalize-composition-1-problems-section"].dependencies
    ] == [
        "finalize-composition-1-allergies-section",
        "build-condition-1",
    ]

    assert steps["build-medicationrequest-1"].owning_section_key == "medications"
    assert steps["build-allergyintolerance-1"].owning_section_key == "allergies"
    assert steps["build-condition-1"].owning_section_key == "problems"
    assert [
        section.entry_placeholder_ids for section in schematic.section_scaffolds
    ] == [["medicationrequest-1"], ["allergyintolerance-1"], ["condition-1"]]

    assert steps["build-patient-1"].target_placeholder_id == "patient-1"
    assert steps["build-composition-1-scaffold"].target_placeholder_id == "composition-1"
    assert steps["finalize-composition-1-medications-section"].target_placeholder_id == "composition-1"
    assert steps["finalize-composition-1-allergies-section"].target_placeholder_id == "composition-1"
    assert steps["finalize-composition-1-problems-section"].target_placeholder_id == "composition-1"
    assert steps["finalize-composition-1-medications-section"].owning_section_key == "medications"
    assert steps["finalize-composition-1-allergies-section"].owning_section_key == "allergies"
    assert steps["finalize-composition-1-problems-section"].owning_section_key == "problems"

    assert any(
        output.output_key == "composition_scaffold_ready:composition-1"
        for output in steps["build-composition-1-scaffold"].expected_outputs
    )
    assert [input_spec.input_key for input_spec in steps["build-practitionerrole-1"].expected_inputs] == [
        "normalized_request",
        "practitioner_placeholder",
        "reference_handle:practitioner-1",
        "reference_handle:organization-1",
    ]
    assert any(
        output.output_key == "composition_section_attached:composition-1:medications"
        for output in steps["finalize-composition-1-medications-section"].expected_outputs
    )
    assert any(
        output.output_key == "composition_section_attached:composition-1:allergies"
        for output in steps["finalize-composition-1-allergies-section"].expected_outputs
    )
    assert any(
        output.output_key == "composition_section_attached:composition-1:problems"
        for output in steps["finalize-composition-1-problems-section"].expected_outputs
    )
    assert plan.evidence.relationship_ids_used == [
        "composition-subject",
        "composition-author",
        "practitionerrole-practitioner",
        "practitionerrole-organization",
        "section-entry-medications",
        "section-entry-allergies",
        "section-entry-problems",
    ]


def test_psca_build_plan_builder_adds_second_medication_step_when_two_medications_are_available() -> None:
    repository = PscaAssetRepository()
    normalized_assets = repository.load_foundation_context(PscaAssetQuery())
    normalized_request = build_psca_normalized_request(
        WorkflowBuildInput(
            specification=SpecificationSelection(),
            patient_profile=ProfileReferenceInput(
                profile_id="patient-plan-two-meds",
                display_name="Plan Two Meds Patient",
            ),
            patient_context=PatientContextInput(
                patient=PatientIdentityInput(
                    patient_id="patient-plan-two-meds",
                    display_name="Plan Two Meds Patient",
                    source_type="patient_management",
                ),
                medications=[
                    PatientMedicationInput(
                        medication_id="med-plan-1",
                        display_text="Atorvastatin 20 MG oral tablet",
                    ),
                    PatientMedicationInput(
                        medication_id="med-plan-2",
                        display_text="Metformin 500 MG oral tablet",
                    ),
                ],
                allergies=[],
                conditions=[],
            ),
            provider_profile=ProfileReferenceInput(
                profile_id="provider-plan-two-meds",
                display_name="Plan Two Meds Provider",
            ),
            request=BundleRequestInput(
                request_text="Create a deterministic two-medication build plan for testing.",
                scenario_label="pytest-build-plan-two-meds",
            ),
        )
    )
    schematic = build_psca_bundle_schematic(normalized_assets, normalized_request)

    plan = build_psca_build_plan(schematic)
    steps = {step.step_id: step for step in plan.steps}

    assert [step.step_id for step in plan.steps] == [
        "build-patient-1",
        "build-practitioner-1",
        "build-organization-1",
        "build-practitionerrole-1",
        "build-composition-1-scaffold",
        "build-medicationrequest-1",
        "build-medicationrequest-2",
        "build-allergyintolerance-1",
        "build-condition-1",
        "finalize-composition-1-medications-section",
        "finalize-composition-1-allergies-section",
        "finalize-composition-1-problems-section",
    ]
    assert [
        section.entry_placeholder_ids for section in schematic.section_scaffolds
    ] == [["medicationrequest-1", "medicationrequest-2"], ["allergyintolerance-1"], ["condition-1"]]
    assert [
        dependency.prerequisite_step_id
        for dependency in steps["finalize-composition-1-medications-section"].dependencies
    ] == [
        "build-composition-1-scaffold",
        "build-medicationrequest-1",
        "build-medicationrequest-2",
    ]
    assert [input_spec.input_key for input_spec in steps["finalize-composition-1-medications-section"].expected_inputs] == [
        "composition_scaffold_ready:composition-1",
        "section_scaffold:medications",
        "reference_handle:medicationrequest-1",
        "reference_handle:medicationrequest-2",
    ]
    assert "medicationrequest-2" in plan.evidence.planned_placeholder_ids
    assert "section-entry-medications-2" in plan.evidence.relationship_ids_used
