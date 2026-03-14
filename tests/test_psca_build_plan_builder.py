"""Direct tests for deterministic PS-CA build-plan generation."""

from __future__ import annotations

from fhir_bundle_builder.specifications.psca import PscaAssetQuery, PscaAssetRepository
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.build_plan_builder import (
    build_psca_build_plan,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.schematic_builder import (
    build_psca_bundle_schematic,
)


def test_psca_build_plan_builder_generates_expected_order_and_dependencies() -> None:
    repository = PscaAssetRepository()
    normalized_assets = repository.load_foundation_context(PscaAssetQuery())
    schematic = build_psca_bundle_schematic(normalized_assets)

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
