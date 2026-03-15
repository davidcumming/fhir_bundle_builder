"""Direct tests for deterministic PS-CA repair routing."""

from __future__ import annotations

from copy import deepcopy

from fhir_bundle_builder.specifications.psca import PscaAssetQuery, PscaAssetRepository
from fhir_bundle_builder.validation import LocalCandidateBundleScaffoldStandardsValidator
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.build_plan_builder import (
    build_psca_build_plan,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.bundle_finalization_builder import (
    build_psca_candidate_bundle_result,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.models import (
    BundleRequestInput,
    NormalizedBuildRequest,
    ProfileReferenceInput,
    ProviderContextInput,
    ProviderIdentityInput,
    ProviderOrganizationInput,
    ProviderRoleRelationshipInput,
    SpecificationSelection,
    WorkflowBuildInput,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.repair_decision_builder import (
    build_psca_repair_decision,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.request_normalization_builder import (
    build_psca_normalized_request,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.resource_construction_builder import (
    build_psca_resource_construction_result,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.schematic_builder import (
    build_psca_bundle_schematic,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.validation_builder import (
    build_psca_validation_report,
)


async def test_psca_repair_decision_happy_path_routes_to_external_validation_pending() -> None:
    report = await _build_validation_report()

    decision = build_psca_repair_decision(report)

    assert decision.overall_decision == "external_validation_pending"
    assert decision.recommended_target == "standards_validation_external"
    assert decision.recommended_next_stage == "none"
    assert any(
        route.finding_code == "external_profile_validation_deferred"
        and route.route_target == "standards_validation_external"
        and route.actionable is False
        for route in decision.finding_routes
    )
    assert not any(
        route.finding_code == "bundle.deferred_fields_recorded"
        for route in decision.finding_routes
    )


async def test_psca_repair_decision_routes_missing_sections_to_resource_construction() -> None:
    report = await _build_validation_report(mutator=_remove_required_section)

    decision = build_psca_repair_decision(report)

    assert decision.overall_decision == "repair_recommended"
    assert decision.recommended_target == "resource_construction"
    assert decision.recommended_next_stage == "resource_construction"
    assert any(
        route.finding_code == "bundle.composition_problems_section_present"
        and route.route_target == "resource_construction"
        and route.actionable is True
        for route in decision.finding_routes
    )
    assert decision.recommended_resource_construction_repair_directive is not None
    assert decision.recommended_resource_construction_repair_directive.target_step_ids == [
        "finalize-composition-1-problems-section"
    ]
    assert decision.recommended_resource_construction_repair_directive.target_placeholder_ids == [
        "composition-1"
    ]


async def test_psca_repair_decision_routes_enriched_content_failures_to_resource_construction() -> None:
    report = await _build_validation_report(mutator=_remove_patient_name)

    decision = build_psca_repair_decision(report)

    assert decision.overall_decision == "repair_recommended"
    assert decision.recommended_target == "resource_construction"
    assert any(
        route.finding_code == "bundle.patient_identity_content_present"
        and route.route_target == "resource_construction"
        and route.actionable is True
        for route in decision.finding_routes
    )
    assert decision.recommended_resource_construction_repair_directive is not None
    assert decision.recommended_resource_construction_repair_directive.target_step_ids == [
        "build-patient-1"
    ]
    assert decision.recommended_resource_construction_repair_directive.target_placeholder_ids == [
        "patient-1"
    ]


async def test_psca_repair_decision_routes_support_resource_failures_to_resource_construction() -> None:
    report = await _build_validation_report(mutator=_remove_practitioner_identity)

    decision = build_psca_repair_decision(report)

    assert decision.overall_decision == "repair_recommended"
    assert decision.recommended_target == "resource_construction"
    assert any(
        route.finding_code == "bundle.practitioner_identity_content_present"
        and route.route_target == "resource_construction"
        and route.actionable is True
        for route in decision.finding_routes
    )
    assert decision.recommended_resource_construction_repair_directive is not None
    assert decision.recommended_resource_construction_repair_directive.target_step_ids == [
        "build-practitioner-1"
    ]


async def test_psca_repair_decision_routes_organization_identity_failures_to_resource_construction() -> None:
    report = await _build_validation_report(mutator=_remove_organization_identity)

    decision = build_psca_repair_decision(report)

    assert decision.overall_decision == "repair_recommended"
    assert decision.recommended_target == "resource_construction"
    assert any(
        route.finding_code == "bundle.organization_identity_content_present"
        and route.route_target == "resource_construction"
        and route.actionable is True
        for route in decision.finding_routes
    )
    assert decision.recommended_resource_construction_repair_directive is not None
    assert decision.recommended_resource_construction_repair_directive.target_step_ids == [
        "build-organization-1"
    ]
    assert decision.recommended_resource_construction_repair_directive.target_placeholder_ids == [
        "organization-1"
    ]


async def test_psca_repair_decision_routes_composition_title_failure_to_scaffold_plus_finalize_subset() -> None:
    report = await _build_validation_report(mutator=_remove_composition_title)

    decision = build_psca_repair_decision(report)

    assert decision.recommended_target == "resource_construction"
    assert any(
        route.finding_code == "bundle.composition_core_scaffold_content_present"
        and route.route_target == "resource_construction"
        and route.actionable is True
        for route in decision.finding_routes
    )
    assert decision.recommended_resource_construction_repair_directive is not None
    assert decision.recommended_resource_construction_repair_directive.target_step_ids == [
        "build-composition-1-scaffold",
        "finalize-composition-1-medications-section",
        "finalize-composition-1-allergies-section",
        "finalize-composition-1-problems-section",
    ]
    assert decision.recommended_resource_construction_repair_directive.target_placeholder_ids == [
        "composition-1"
    ]


async def test_psca_repair_decision_routes_composition_subject_failure_to_scaffold_plus_finalize_subset() -> None:
    report = await _build_validation_report(mutator=_break_composition_subject_reference)

    decision = build_psca_repair_decision(report)

    assert decision.recommended_target == "resource_construction"
    assert any(
        route.finding_code == "bundle.composition_subject_reference_aligned"
        and route.route_target == "resource_construction"
        and route.actionable is True
        for route in decision.finding_routes
    )
    assert decision.recommended_resource_construction_repair_directive is not None
    assert decision.recommended_resource_construction_repair_directive.target_step_ids == [
        "build-composition-1-scaffold",
        "finalize-composition-1-medications-section",
        "finalize-composition-1-allergies-section",
        "finalize-composition-1-problems-section",
    ]


async def test_psca_repair_decision_routes_composition_author_failure_to_scaffold_plus_finalize_subset() -> None:
    report = await _build_validation_report(mutator=_break_composition_author_reference)

    decision = build_psca_repair_decision(report)

    assert decision.recommended_target == "resource_construction"
    assert any(
        route.finding_code == "bundle.composition_author_reference_aligned"
        and route.route_target == "resource_construction"
        and route.actionable is True
        for route in decision.finding_routes
    )
    assert decision.recommended_resource_construction_repair_directive is not None
    assert decision.recommended_resource_construction_repair_directive.target_step_ids == [
        "build-composition-1-scaffold",
        "finalize-composition-1-medications-section",
        "finalize-composition-1-allergies-section",
        "finalize-composition-1-problems-section",
    ]


async def test_psca_repair_decision_dedupes_combined_composition_scaffold_failures_to_one_step_subset() -> None:
    report = await _build_validation_report(mutator=_remove_composition_title_and_break_author_reference)

    decision = build_psca_repair_decision(report)

    assert decision.recommended_target == "resource_construction"
    assert decision.recommended_resource_construction_repair_directive is not None
    assert set(decision.recommended_resource_construction_repair_directive.trigger_finding_codes) == {
        "bundle.composition_core_scaffold_content_present",
        "bundle.composition_author_reference_aligned",
    }
    assert decision.recommended_resource_construction_repair_directive.target_step_ids == [
        "build-composition-1-scaffold",
        "finalize-composition-1-medications-section",
        "finalize-composition-1-allergies-section",
        "finalize-composition-1-problems-section",
    ]


async def test_psca_repair_decision_routes_medicationrequest_placeholder_failures_to_one_step_directive() -> None:
    report = await _build_validation_report(mutator=_remove_medicationrequest_content)

    decision = build_psca_repair_decision(report)

    assert decision.recommended_target == "resource_construction"
    assert decision.recommended_resource_construction_repair_directive is not None
    assert decision.recommended_resource_construction_repair_directive.target_step_ids == [
        "build-medicationrequest-1",
    ]
    assert decision.recommended_resource_construction_repair_directive.target_placeholder_ids == [
        "medicationrequest-1",
    ]
    assert decision.recommended_resource_construction_repair_directive.trigger_finding_codes == [
        "bundle.medicationrequest_placeholder_content_present"
    ]


async def test_psca_repair_decision_unions_multiple_resource_construction_findings_in_plan_order() -> None:
    report = await _build_validation_report(mutator=_remove_patient_name_and_required_section)

    decision = build_psca_repair_decision(report)

    assert decision.recommended_target == "resource_construction"
    assert decision.recommended_resource_construction_repair_directive is not None
    assert set(decision.recommended_resource_construction_repair_directive.trigger_finding_codes) == {
        "bundle.patient_identity_content_present",
        "bundle.composition_problems_section_present",
    }
    assert decision.recommended_resource_construction_repair_directive.target_step_ids == [
        "build-patient-1",
        "finalize-composition-1-problems-section",
    ]
    assert decision.recommended_resource_construction_repair_directive.target_placeholder_ids == [
        "patient-1",
        "composition-1",
    ]


async def test_psca_repair_decision_unions_multiple_missing_composition_sections_in_plan_order() -> None:
    report = await _build_validation_report(mutator=_remove_allergies_and_problems_sections)

    decision = build_psca_repair_decision(report)

    assert decision.recommended_target == "resource_construction"
    assert decision.recommended_resource_construction_repair_directive is not None
    assert decision.recommended_resource_construction_repair_directive.target_step_ids == [
        "finalize-composition-1-allergies-section",
        "finalize-composition-1-problems-section",
    ]
    assert decision.recommended_resource_construction_repair_directive.target_placeholder_ids == [
        "composition-1",
    ]
    assert set(decision.recommended_resource_construction_repair_directive.trigger_finding_codes) == {
        "bundle.composition_allergies_section_present",
        "bundle.composition_problems_section_present",
    }


async def test_psca_repair_decision_unions_multiple_section_entry_failures_in_plan_order() -> None:
    report = await _build_validation_report(mutator=_remove_medicationrequest_and_condition_content)

    decision = build_psca_repair_decision(report)

    assert decision.recommended_target == "resource_construction"
    assert decision.recommended_resource_construction_repair_directive is not None
    assert decision.recommended_resource_construction_repair_directive.target_step_ids == [
        "build-medicationrequest-1",
        "build-condition-1",
    ]
    assert decision.recommended_resource_construction_repair_directive.target_placeholder_ids == [
        "medicationrequest-1",
        "condition-1",
    ]
    assert set(decision.recommended_resource_construction_repair_directive.trigger_finding_codes) == {
        "bundle.medicationrequest_placeholder_content_present",
        "bundle.condition_placeholder_content_present",
    }


async def test_psca_repair_decision_routes_bundle_shape_errors_to_bundle_finalization() -> None:
    report = await _build_validation_report(mutator=_break_bundle_type)

    decision = build_psca_repair_decision(report)

    assert decision.overall_decision == "repair_recommended"
    assert decision.recommended_target == "bundle_finalization"
    assert decision.recommended_next_stage == "bundle_finalization"
    assert any(
        route.finding_code == "bundle.type_is_document"
        and route.route_target == "bundle_finalization"
        and route.actionable is True
        for route in decision.finding_routes
    )


async def test_psca_repair_decision_routes_bundle_identity_failures_to_bundle_finalization() -> None:
    report = await _build_validation_report(mutator=_remove_bundle_identifier)

    decision = build_psca_repair_decision(report)

    assert decision.overall_decision == "repair_recommended"
    assert decision.recommended_target == "bundle_finalization"
    assert any(
        route.finding_code == "bundle.identifier_present"
        and route.route_target == "bundle_finalization"
        and route.actionable is True
        for route in decision.finding_routes
    )


async def test_psca_repair_decision_routes_practitionerrole_practitioner_reference_alignment_to_bundle_finalization() -> None:
    report = await _build_validation_report(mutator=_break_practitionerrole_practitioner_reference)

    decision = build_psca_repair_decision(report)

    assert decision.recommended_target == "bundle_finalization"
    assert any(
        route.finding_code == "bundle.practitionerrole_practitioner_reference_aligned"
        and route.route_target == "bundle_finalization"
        and route.actionable is True
        for route in decision.finding_routes
    )
    assert decision.recommended_resource_construction_repair_directive is None


async def test_psca_repair_decision_routes_practitionerrole_organization_reference_alignment_to_bundle_finalization() -> None:
    report = await _build_validation_report(mutator=_break_practitionerrole_organization_reference)

    decision = build_psca_repair_decision(report)

    assert decision.recommended_target == "bundle_finalization"
    assert any(
        route.finding_code == "bundle.practitionerrole_organization_reference_aligned"
        and route.route_target == "bundle_finalization"
        and route.actionable is True
        for route in decision.finding_routes
    )
    assert decision.recommended_resource_construction_repair_directive is None


async def test_psca_repair_decision_routes_medicationrequest_subject_reference_alignment_to_bundle_finalization() -> None:
    report = await _build_validation_report(mutator=_break_medicationrequest_subject_reference)

    decision = build_psca_repair_decision(report)

    assert decision.recommended_target == "bundle_finalization"
    assert any(
        route.finding_code == "bundle.medicationrequest_subject_reference_aligned"
        and route.route_target == "bundle_finalization"
        and route.actionable is True
        for route in decision.finding_routes
    )
    assert decision.recommended_resource_construction_repair_directive is None


async def test_psca_repair_decision_routes_allergyintolerance_patient_reference_alignment_to_bundle_finalization() -> None:
    report = await _build_validation_report(mutator=_break_allergyintolerance_patient_reference)

    decision = build_psca_repair_decision(report)

    assert decision.recommended_target == "bundle_finalization"
    assert any(
        route.finding_code == "bundle.allergyintolerance_patient_reference_aligned"
        and route.route_target == "bundle_finalization"
        and route.actionable is True
        for route in decision.finding_routes
    )
    assert decision.recommended_resource_construction_repair_directive is None


async def test_psca_repair_decision_routes_condition_subject_reference_alignment_to_bundle_finalization() -> None:
    report = await _build_validation_report(mutator=_break_condition_subject_reference)

    decision = build_psca_repair_decision(report)

    assert decision.recommended_target == "bundle_finalization"
    assert any(
        route.finding_code == "bundle.condition_subject_reference_aligned"
        and route.route_target == "bundle_finalization"
        and route.actionable is True
        for route in decision.finding_routes
    )
    assert decision.recommended_resource_construction_repair_directive is None


async def test_psca_repair_decision_routes_medications_section_entry_reference_alignment_to_resource_construction() -> None:
    report = await _build_validation_report(mutator=_break_medications_section_entry_reference)

    decision = build_psca_repair_decision(report)

    assert decision.recommended_target == "resource_construction"
    assert any(
        route.finding_code == "bundle.composition_medications_section_entry_reference_aligned"
        and route.route_target == "resource_construction"
        and route.actionable is True
        for route in decision.finding_routes
    )
    assert decision.recommended_resource_construction_repair_directive is not None
    assert decision.recommended_resource_construction_repair_directive.target_step_ids == [
        "finalize-composition-1-medications-section"
    ]


async def test_psca_repair_decision_routes_allergies_section_entry_reference_alignment_to_resource_construction() -> None:
    report = await _build_validation_report(mutator=_break_allergies_section_entry_reference)

    decision = build_psca_repair_decision(report)

    assert decision.recommended_target == "resource_construction"
    assert any(
        route.finding_code == "bundle.composition_allergies_section_entry_reference_aligned"
        and route.route_target == "resource_construction"
        and route.actionable is True
        for route in decision.finding_routes
    )
    assert decision.recommended_resource_construction_repair_directive is not None
    assert decision.recommended_resource_construction_repair_directive.target_step_ids == [
        "finalize-composition-1-allergies-section"
    ]


async def test_psca_repair_decision_routes_problems_section_entry_reference_alignment_to_resource_construction() -> None:
    report = await _build_validation_report(mutator=_break_problems_section_entry_reference)

    decision = build_psca_repair_decision(report)

    assert decision.recommended_target == "resource_construction"
    assert any(
        route.finding_code == "bundle.composition_problems_section_entry_reference_aligned"
        and route.route_target == "resource_construction"
        and route.actionable is True
        for route in decision.finding_routes
    )
    assert decision.recommended_resource_construction_repair_directive is not None
    assert decision.recommended_resource_construction_repair_directive.target_step_ids == [
        "finalize-composition-1-problems-section"
    ]


async def test_psca_repair_decision_unions_multiple_composition_section_entry_reference_alignment_failures_in_plan_order() -> None:
    report = await _build_validation_report(mutator=_break_medications_and_problems_section_entry_references)

    decision = build_psca_repair_decision(report)

    assert decision.recommended_target == "resource_construction"
    assert decision.recommended_resource_construction_repair_directive is not None
    assert decision.recommended_resource_construction_repair_directive.target_step_ids == [
        "finalize-composition-1-medications-section",
        "finalize-composition-1-problems-section",
    ]
    assert set(decision.recommended_resource_construction_repair_directive.trigger_finding_codes) == {
        "bundle.composition_medications_section_entry_reference_aligned",
        "bundle.composition_problems_section_entry_reference_aligned",
    }


async def test_psca_repair_decision_keeps_combined_non_composition_reference_alignment_failures_at_bundle_finalization() -> None:
    report = await _build_validation_report(mutator=_break_practitionerrole_and_condition_references)

    decision = build_psca_repair_decision(report)

    assert decision.recommended_target == "bundle_finalization"
    assert decision.recommended_next_stage == "bundle_finalization"
    assert set(route.finding_code for route in decision.finding_routes if route.route_target == "bundle_finalization") >= {
        "bundle.practitionerrole_practitioner_reference_aligned",
        "bundle.condition_subject_reference_aligned",
    }
    assert decision.recommended_resource_construction_repair_directive is None


async def _build_validation_report(mutator=None):
    repository = PscaAssetRepository()
    normalized_assets = repository.load_foundation_context(PscaAssetQuery())
    normalized_request = build_psca_normalized_request(
        WorkflowBuildInput(
            specification=SpecificationSelection(),
            patient_profile=ProfileReferenceInput(
                profile_id="patient-repair-test",
                display_name="Repair Test Patient",
            ),
            provider_profile=ProfileReferenceInput(
                profile_id="provider-repair-test",
                display_name="Repair Test Provider",
            ),
            provider_context=ProviderContextInput(
                provider=ProviderIdentityInput(
                    provider_id="provider-repair-test",
                    display_name="Repair Test Provider",
                    source_type="provider_management",
                ),
                organizations=[
                    ProviderOrganizationInput(
                        organization_id="org-repair-test",
                        display_name="Repair Test Organization",
                    )
                ],
                provider_role_relationships=[
                    ProviderRoleRelationshipInput(
                        relationship_id="provider-role-repair-1",
                        organization_id="org-repair-test",
                        role_label="attending-physician",
                    )
                ],
            ),
            request=BundleRequestInput(
                request_text="Create a deterministic repair decision for testing.",
                scenario_label="pytest-repair",
            ),
        )
    )
    schematic = build_psca_bundle_schematic(normalized_assets, normalized_request)
    plan = build_psca_build_plan(schematic)
    construction = build_psca_resource_construction_result(plan, schematic, normalized_request)
    candidate_bundle = build_psca_candidate_bundle_result(construction, schematic, normalized_request)
    if mutator is not None:
        candidate_bundle = mutator(candidate_bundle)
    return await build_psca_validation_report(
        candidate_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )


def _remove_required_section(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    composition = broken_bundle.candidate_bundle.fhir_bundle["entry"][0]["resource"]
    composition["section"] = composition["section"][:2]
    return broken_bundle


def _remove_allergies_and_problems_sections(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    composition = broken_bundle.candidate_bundle.fhir_bundle["entry"][0]["resource"]
    composition["section"] = composition["section"][:1]
    return broken_bundle


def _break_bundle_type(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    broken_bundle.candidate_bundle.fhir_bundle["type"] = "collection"
    return broken_bundle


def _remove_patient_name(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    patient = broken_bundle.candidate_bundle.fhir_bundle["entry"][1]["resource"]
    patient["name"] = []
    return broken_bundle


def _remove_composition_title(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    composition = broken_bundle.candidate_bundle.fhir_bundle["entry"][0]["resource"]
    composition.pop("title", None)
    return broken_bundle


def _break_composition_subject_reference(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    composition = broken_bundle.candidate_bundle.fhir_bundle["entry"][0]["resource"]
    composition["subject"]["reference"] = "Patient/patient-1"
    return broken_bundle


def _break_composition_author_reference(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    composition = broken_bundle.candidate_bundle.fhir_bundle["entry"][0]["resource"]
    composition["author"][0]["reference"] = "PractitionerRole/practitionerrole-1"
    return broken_bundle


def _remove_composition_title_and_break_author_reference(candidate_bundle):
    broken_bundle = _remove_composition_title(candidate_bundle)
    return _break_composition_author_reference(broken_bundle)


def _remove_practitioner_identity(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    practitioner = broken_bundle.candidate_bundle.fhir_bundle["entry"][3]["resource"]
    practitioner["identifier"] = []
    return broken_bundle


def _remove_organization_identity(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    organization = broken_bundle.candidate_bundle.fhir_bundle["entry"][4]["resource"]
    organization.pop("identifier", None)
    return broken_bundle


def _remove_bundle_identifier(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    broken_bundle.candidate_bundle.fhir_bundle.pop("identifier", None)
    return broken_bundle


def _break_practitionerrole_practitioner_reference(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    practitioner_role = broken_bundle.candidate_bundle.fhir_bundle["entry"][2]["resource"]
    practitioner_role["practitioner"]["reference"] = "Practitioner/practitioner-1"
    return broken_bundle


def _break_practitionerrole_organization_reference(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    practitioner_role = broken_bundle.candidate_bundle.fhir_bundle["entry"][2]["resource"]
    practitioner_role["organization"]["reference"] = "Organization/organization-1"
    return broken_bundle


def _break_medicationrequest_subject_reference(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    medication = broken_bundle.candidate_bundle.fhir_bundle["entry"][5]["resource"]
    medication["subject"]["reference"] = "Patient/patient-1"
    return broken_bundle


def _break_allergyintolerance_patient_reference(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    allergy = broken_bundle.candidate_bundle.fhir_bundle["entry"][6]["resource"]
    allergy["patient"]["reference"] = "Patient/patient-1"
    return broken_bundle


def _break_condition_subject_reference(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    condition = broken_bundle.candidate_bundle.fhir_bundle["entry"][7]["resource"]
    condition["subject"]["reference"] = "Patient/patient-1"
    return broken_bundle


def _break_medications_section_entry_reference(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    composition = broken_bundle.candidate_bundle.fhir_bundle["entry"][0]["resource"]
    wrong_full_url = broken_bundle.candidate_bundle.fhir_bundle["entry"][6]["fullUrl"]
    composition["section"][0]["entry"][0]["reference"] = wrong_full_url
    return broken_bundle


def _break_allergies_section_entry_reference(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    composition = broken_bundle.candidate_bundle.fhir_bundle["entry"][0]["resource"]
    wrong_full_url = broken_bundle.candidate_bundle.fhir_bundle["entry"][7]["fullUrl"]
    composition["section"][1]["entry"][0]["reference"] = wrong_full_url
    return broken_bundle


def _break_problems_section_entry_reference(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    composition = broken_bundle.candidate_bundle.fhir_bundle["entry"][0]["resource"]
    wrong_full_url = broken_bundle.candidate_bundle.fhir_bundle["entry"][5]["fullUrl"]
    composition["section"][2]["entry"][0]["reference"] = wrong_full_url
    return broken_bundle


def _break_medications_and_problems_section_entry_references(candidate_bundle):
    broken_bundle = _break_medications_section_entry_reference(candidate_bundle)
    return _break_problems_section_entry_reference(broken_bundle)


def _break_practitionerrole_and_condition_references(candidate_bundle):
    broken_bundle = _break_practitionerrole_practitioner_reference(candidate_bundle)
    return _break_condition_subject_reference(broken_bundle)


def _remove_medicationrequest_content(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    medication = broken_bundle.candidate_bundle.fhir_bundle["entry"][5]["resource"]
    medication["medicationCodeableConcept"]["text"] = ""
    return broken_bundle


def _remove_medicationrequest_and_condition_content(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    medication = broken_bundle.candidate_bundle.fhir_bundle["entry"][5]["resource"]
    condition = broken_bundle.candidate_bundle.fhir_bundle["entry"][7]["resource"]
    medication["medicationCodeableConcept"]["text"] = ""
    condition["code"]["text"] = ""
    return broken_bundle


def _remove_patient_name_and_required_section(candidate_bundle):
    broken_bundle = _remove_patient_name(candidate_bundle)
    return _remove_required_section(broken_bundle)
