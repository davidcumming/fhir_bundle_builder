"""Direct tests for deterministic PS-CA validation foundation."""

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
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.validation_builder import (
    build_psca_validation_report,
)


async def test_psca_validation_builder_happy_path_reports_split_channels() -> None:
    normalized_request, schematic, candidate_bundle = _build_validation_inputs()

    report = await build_psca_validation_report(
        candidate_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert report.standards_validation.validator_id == "local_candidate_bundle_scaffold_validator"
    assert report.standards_validation.status == "passed_with_warnings"
    assert report.standards_validation.requested_validator_mode == "local_scaffold"
    assert report.standards_validation.attempted_validator_ids == [
        "local_candidate_bundle_scaffold_validator"
    ]
    assert report.standards_validation.external_validation_executed is False
    assert report.standards_validation.fallback_used is False
    assert report.workflow_validation.status == "passed"
    assert report.overall_status == "passed_with_warnings"
    assert report.evidence.patient_context_alignment.normalization_mode == "patient_context_explicit"
    assert report.evidence.patient_context_alignment.patient_id == "patient-validation-test"
    assert report.evidence.patient_context_alignment.display_name == "Validation Test Patient"
    assert report.evidence.patient_context_alignment.administrative_gender_expected == "female"
    assert report.evidence.patient_context_alignment.birth_date_expected == "1985-02-14"
    assert [
        (
            expectation.placeholder_id,
            expectation.resource_type,
            expectation.alignment_mode,
            expectation.expected_text,
        )
        for expectation in report.evidence.patient_context_alignment.section_entry_expectations
    ] == [
        (
            "medicationrequest-1",
            "MedicationRequest",
            "structured_patient_context",
            "Atorvastatin 20 MG oral tablet",
        ),
        (
            "allergyintolerance-1",
            "AllergyIntolerance",
            "structured_patient_context",
            "Peanut allergy",
        ),
        (
            "condition-1",
            "Condition",
            "structured_patient_context",
            "Type 2 diabetes mellitus",
        ),
    ]
    assert report.evidence.provider_context_alignment.normalization_mode == (
        "provider_context_single_relationship"
    )
    assert report.evidence.provider_context_alignment.provider_id == "provider-validation-test"
    assert (
        report.evidence.provider_context_alignment.provider_display_name
        == "Validation Test Provider"
    )
    assert report.evidence.provider_context_alignment.organization_alignment_mode == (
        "structured_provider_context"
    )
    assert (
        report.evidence.provider_context_alignment.selected_organization_identifier_system_expected
        == SELECTED_PROVIDER_ORGANIZATION_IDENTIFIER_SYSTEM
    )
    assert report.evidence.provider_context_alignment.selected_organization_id_expected == (
        "org-validation-test"
    )
    assert (
        report.evidence.provider_context_alignment.selected_organization_display_name_expected
        == "Validation Test Organization"
    )
    assert report.evidence.provider_context_alignment.practitionerrole_alignment_mode == (
        "structured_provider_context"
    )
    assert (
        report.evidence.provider_context_alignment.selected_provider_role_relationship_identifier_system_expected
        == SELECTED_PROVIDER_ROLE_RELATIONSHIP_IDENTIFIER_SYSTEM
    )
    assert (
        report.evidence.provider_context_alignment.selected_provider_role_relationship_id_expected
        == "provider-role-validation-1"
    )
    assert report.evidence.provider_context_alignment.expected_role_label == "attending-physician"
    traceability = {
        summary.placeholder_id: summary
        for summary in report.evidence.placeholder_traceability_summaries
    }
    assert traceability["composition-1"].bundle_entry_sequence == 1
    assert traceability["composition-1"].bundle_entry_path == "entry[0].resource"
    assert "bundle.composition_core_scaffold_content_present" in traceability["composition-1"].workflow_check_codes
    assert traceability["patient-1"].workflow_check_codes == [
        "bundle.patient_identity_content_present",
        "bundle.patient_identity_aligned_to_context",
    ]
    assert "bundle.practitioner_identity_aligned_to_context" in traceability["practitioner-1"].workflow_check_codes
    assert "bundle.organization_identity_aligned_to_context" in traceability["organization-1"].workflow_check_codes
    assert (
        "bundle.practitionerrole_author_context_aligned_to_context"
        in traceability["practitionerrole-1"].workflow_check_codes
    )
    assert (
        "bundle.medicationrequest_placeholder_text_aligned_to_context"
        in traceability["medicationrequest-1"].workflow_check_codes
    )
    assert any(
        driving_input.source_artifact
        == "normalized_request.patient_context.planned_medication_entries[0]"
        for driving_input in traceability["medicationrequest-1"].driving_inputs
    )
    assert any(
        finding.code == "external_profile_validation_deferred"
        for finding in report.standards_validation.findings
    )
    assert not any(
        finding.code == "bundle.identifier_present" and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.practitionerrole_practitioner_reference_aligned" and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.practitionerrole_organization_reference_aligned" and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.medicationrequest_subject_reference_aligned" and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.allergyintolerance_patient_reference_aligned" and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.condition_subject_reference_aligned" and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.practitionerrole_relationship_identity_present" and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.practitioner_identity_aligned_to_context" and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.organization_identity_aligned_to_context" and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.practitionerrole_relationship_identity_aligned_to_context"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.practitionerrole_author_context_aligned_to_context"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.composition_medications_section_entry_reference_aligned" and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.medications_bundle_entries_aligned_to_plan" and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.patient_identity_aligned_to_context" and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.medicationrequest_placeholder_text_aligned_to_context"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.allergyintolerance_placeholder_text_aligned_to_context"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.condition_placeholder_text_aligned_to_context"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.composition_allergies_section_entry_reference_aligned" and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.composition_problems_section_entry_reference_aligned" and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_medications_section_is_missing() -> None:
    normalized_request, schematic, candidate_bundle = _build_validation_inputs()
    broken_bundle = deepcopy(candidate_bundle)
    composition = broken_bundle.candidate_bundle.fhir_bundle["entry"][0]["resource"]
    composition["section"] = composition["section"][1:]

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert report.workflow_validation.status == "failed"
    assert report.overall_status == "failed"
    assert any(
        finding.code == "bundle.composition_medications_section_present"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.composition_allergies_section_present"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.composition_problems_section_present"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_allergies_and_problems_sections_are_missing() -> None:
    normalized_request, schematic, candidate_bundle = _build_validation_inputs()
    broken_bundle = deepcopy(candidate_bundle)
    composition = broken_bundle.candidate_bundle.fhir_bundle["entry"][0]["resource"]
    composition["section"] = composition["section"][:1]

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert report.workflow_validation.status == "failed"
    assert any(
        finding.code == "bundle.composition_allergies_section_present"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert any(
        finding.code == "bundle.composition_problems_section_present"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.composition_medications_section_present"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_composition_or_patient_content_is_missing() -> None:
    normalized_request, schematic, candidate_bundle = _build_validation_inputs()
    broken_bundle = deepcopy(candidate_bundle)
    composition = broken_bundle.candidate_bundle.fhir_bundle["entry"][0]["resource"]
    patient = broken_bundle.candidate_bundle.fhir_bundle["entry"][1]["resource"]
    composition.pop("title", None)
    patient["name"] = []

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert report.workflow_validation.status == "failed"
    assert any(
        finding.code == "bundle.composition_core_scaffold_content_present" and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert any(
        finding.code == "bundle.patient_identity_content_present" and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_patient_context_demographics_are_missing() -> None:
    normalized_request, schematic, candidate_bundle = _build_validation_inputs()
    broken_bundle = deepcopy(candidate_bundle)
    patient = broken_bundle.candidate_bundle.fhir_bundle["entry"][1]["resource"]
    patient.pop("gender", None)

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert report.workflow_validation.status == "failed"
    assert any(
        finding.code == "bundle.patient_identity_content_present" and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.patient_identity_aligned_to_context"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_patient_identity_values_do_not_align_to_context() -> None:
    normalized_request, schematic, candidate_bundle = _build_validation_inputs()
    broken_bundle = deepcopy(candidate_bundle)
    patient = broken_bundle.candidate_bundle.fhir_bundle["entry"][1]["resource"]
    patient["identifier"][0]["value"] = "wrong-patient-id"
    patient["name"][0]["text"] = "Wrong Patient"

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert any(
        finding.code == "bundle.patient_identity_aligned_to_context" and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.patient_identity_content_present"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_composition_subject_reference_is_not_aligned() -> None:
    normalized_request, schematic, candidate_bundle = _build_validation_inputs()
    broken_bundle = deepcopy(candidate_bundle)
    composition = broken_bundle.candidate_bundle.fhir_bundle["entry"][0]["resource"]
    composition["subject"]["reference"] = "Patient/patient-1"

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert report.workflow_validation.status == "failed"
    assert any(
        finding.code == "bundle.composition_subject_reference_aligned" and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.composition_medications_section_entry_reference_aligned"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_composition_author_reference_is_not_aligned() -> None:
    normalized_request, schematic, candidate_bundle = _build_validation_inputs()
    broken_bundle = deepcopy(candidate_bundle)
    composition = broken_bundle.candidate_bundle.fhir_bundle["entry"][0]["resource"]
    composition["author"][0]["reference"] = "PractitionerRole/practitionerrole-1"

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert report.workflow_validation.status == "failed"
    assert any(
        finding.code == "bundle.composition_author_reference_aligned" and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.composition_medications_section_entry_reference_aligned"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_practitioner_or_practitionerrole_content_is_missing() -> None:
    normalized_request, schematic, candidate_bundle = _build_validation_inputs()
    broken_bundle = deepcopy(candidate_bundle)
    practitioner = broken_bundle.candidate_bundle.fhir_bundle["entry"][3]["resource"]
    practitioner_role = broken_bundle.candidate_bundle.fhir_bundle["entry"][2]["resource"]
    practitioner["identifier"] = []
    practitioner_role["code"] = []

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert report.workflow_validation.status == "failed"
    assert any(
        finding.code == "bundle.practitioner_identity_content_present" and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert any(
        finding.code == "bundle.practitionerrole_author_context_present" and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.practitioner_identity_aligned_to_context"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.practitionerrole_author_context_aligned_to_context"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_selected_organization_content_is_missing() -> None:
    normalized_request, schematic, candidate_bundle = _build_validation_inputs()
    broken_bundle = deepcopy(candidate_bundle)
    organization = broken_bundle.candidate_bundle.fhir_bundle["entry"][4]["resource"]
    organization["identifier"][0].pop("system", None)

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert report.workflow_validation.status == "failed"
    assert any(
        finding.code == "bundle.organization_identity_content_present" and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.organization_identity_aligned_to_context"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_practitionerrole_relationship_identity_is_missing() -> None:
    normalized_request, schematic, candidate_bundle = _build_validation_inputs()
    broken_bundle = deepcopy(candidate_bundle)
    practitioner_role = broken_bundle.candidate_bundle.fhir_bundle["entry"][2]["resource"]
    practitioner_role["identifier"][0].pop("value", None)

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert report.workflow_validation.status == "failed"
    assert any(
        finding.code == "bundle.practitionerrole_relationship_identity_present" and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.practitionerrole_author_context_present"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.practitionerrole_relationship_identity_aligned_to_context"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_does_not_require_organization_identity_in_legacy_mode() -> None:
    normalized_request, schematic, candidate_bundle = _build_validation_inputs(legacy_provider_context=True)
    broken_bundle = deepcopy(candidate_bundle)
    organization = broken_bundle.candidate_bundle.fhir_bundle["entry"][4]["resource"]
    organization.pop("identifier", None)
    organization.pop("name", None)

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert not any(
        finding.code == "bundle.organization_identity_content_present"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.practitionerrole_relationship_identity_present"
        for finding in report.workflow_validation.findings
    )
    assert report.evidence.provider_context_alignment.normalization_mode == "legacy_provider_profile"
    assert report.evidence.provider_context_alignment.organization_alignment_mode == "not_applicable"
    assert report.evidence.provider_context_alignment.practitionerrole_alignment_mode == (
        "fallback_placeholder"
    )
    assert report.evidence.provider_context_alignment.expected_role_label == "document-author"
    traceability = {
        summary.placeholder_id: summary
        for summary in report.evidence.placeholder_traceability_summaries
    }
    assert any(
        driving_input.source_artifact == "bundle_schematic.resource_placeholders[practitionerrole-1]"
        and driving_input.source_detail == "role"
        for driving_input in traceability["practitionerrole-1"].driving_inputs
    )
    assert "bundle.practitionerrole_author_context_aligned_to_context" in traceability[
        "practitionerrole-1"
    ].workflow_check_codes
    assert not any(
        finding.code == "bundle.organization_identity_aligned_to_context"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.practitionerrole_relationship_identity_aligned_to_context"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_practitioner_identity_is_not_aligned_to_context() -> None:
    normalized_request, schematic, candidate_bundle = _build_validation_inputs()
    broken_bundle = deepcopy(candidate_bundle)
    practitioner = broken_bundle.candidate_bundle.fhir_bundle["entry"][3]["resource"]
    practitioner["identifier"][0]["value"] = "wrong-provider-id"
    practitioner["name"][0]["text"] = "Wrong Provider"

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert any(
        finding.code == "bundle.practitioner_identity_aligned_to_context"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.practitioner_identity_content_present"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_selected_organization_identity_is_not_aligned_to_context() -> None:
    normalized_request, schematic, candidate_bundle = _build_validation_inputs()
    broken_bundle = deepcopy(candidate_bundle)
    organization = broken_bundle.candidate_bundle.fhir_bundle["entry"][4]["resource"]
    organization["identifier"][0]["value"] = "wrong-org-id"
    organization["name"] = "Wrong Organization"

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert any(
        finding.code == "bundle.organization_identity_aligned_to_context"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.organization_identity_content_present"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_practitionerrole_relationship_identity_is_not_aligned_to_context() -> None:
    normalized_request, schematic, candidate_bundle = _build_validation_inputs()
    broken_bundle = deepcopy(candidate_bundle)
    practitioner_role = broken_bundle.candidate_bundle.fhir_bundle["entry"][2]["resource"]
    practitioner_role["identifier"][0]["value"] = "wrong-relationship-id"

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert any(
        finding.code == "bundle.practitionerrole_relationship_identity_aligned_to_context"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.practitionerrole_relationship_identity_present"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_practitionerrole_author_context_is_not_aligned_to_context() -> None:
    normalized_request, schematic, candidate_bundle = _build_validation_inputs()
    broken_bundle = deepcopy(candidate_bundle)
    practitioner_role = broken_bundle.candidate_bundle.fhir_bundle["entry"][2]["resource"]
    practitioner_role["code"][0]["text"] = "wrong-role-label"

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert any(
        finding.code == "bundle.practitionerrole_author_context_aligned_to_context"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.practitionerrole_author_context_present"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_medicationrequest_placeholder_content_is_missing() -> None:
    normalized_request, schematic, candidate_bundle = _build_validation_inputs()
    broken_bundle = deepcopy(candidate_bundle)
    medication = broken_bundle.candidate_bundle.fhir_bundle["entry"][5]["resource"]
    medication.pop("medicationCodeableConcept", None)

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert report.workflow_validation.status == "failed"
    assert any(
        finding.code == "bundle.medicationrequest_placeholder_content_present"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.medicationrequest_placeholder_text_aligned_to_context"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.allergyintolerance_placeholder_content_present"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.condition_placeholder_content_present"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_medicationrequest_text_is_not_aligned_to_context() -> None:
    normalized_request, schematic, candidate_bundle = _build_validation_inputs()
    broken_bundle = deepcopy(candidate_bundle)
    medication = broken_bundle.candidate_bundle.fhir_bundle["entry"][5]["resource"]
    medication["medicationCodeableConcept"]["text"] = "Wrong medication text"

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert any(
        finding.code == "bundle.medicationrequest_placeholder_text_aligned_to_context"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.medicationrequest_placeholder_content_present"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_allergyintolerance_placeholder_content_is_missing() -> None:
    normalized_request, schematic, candidate_bundle = _build_validation_inputs()
    broken_bundle = deepcopy(candidate_bundle)
    allergy = broken_bundle.candidate_bundle.fhir_bundle["entry"][6]["resource"]
    allergy["code"]["text"] = ""

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert report.workflow_validation.status == "failed"
    assert any(
        finding.code == "bundle.allergyintolerance_placeholder_content_present"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.allergyintolerance_placeholder_text_aligned_to_context"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.medicationrequest_placeholder_content_present"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.condition_placeholder_content_present"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_allergyintolerance_text_is_not_aligned_to_context() -> None:
    normalized_request, schematic, candidate_bundle = _build_validation_inputs()
    broken_bundle = deepcopy(candidate_bundle)
    allergy = broken_bundle.candidate_bundle.fhir_bundle["entry"][6]["resource"]
    allergy["code"]["text"] = "Wrong allergy text"

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert any(
        finding.code == "bundle.allergyintolerance_placeholder_text_aligned_to_context"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.allergyintolerance_placeholder_content_present"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_condition_placeholder_content_is_missing() -> None:
    normalized_request, schematic, candidate_bundle = _build_validation_inputs()
    broken_bundle = deepcopy(candidate_bundle)
    condition = broken_bundle.candidate_bundle.fhir_bundle["entry"][7]["resource"]
    condition["code"]["text"] = ""

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert report.workflow_validation.status == "failed"
    assert any(
        finding.code == "bundle.condition_placeholder_content_present"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.condition_placeholder_text_aligned_to_context"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.medicationrequest_placeholder_content_present"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.allergyintolerance_placeholder_content_present"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_condition_text_is_not_aligned_to_context() -> None:
    normalized_request, schematic, candidate_bundle = _build_validation_inputs()
    broken_bundle = deepcopy(candidate_bundle)
    condition = broken_bundle.candidate_bundle.fhir_bundle["entry"][7]["resource"]
    condition["code"]["text"] = "Wrong condition text"

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert any(
        finding.code == "bundle.condition_placeholder_text_aligned_to_context"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.condition_placeholder_content_present"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_multiple_section_entry_resources_are_missing() -> None:
    normalized_request, schematic, candidate_bundle = _build_validation_inputs()
    broken_bundle = deepcopy(candidate_bundle)
    medication = broken_bundle.candidate_bundle.fhir_bundle["entry"][5]["resource"]
    condition = broken_bundle.candidate_bundle.fhir_bundle["entry"][7]["resource"]
    medication.pop("medicationCodeableConcept", None)
    condition["code"]["text"] = ""

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert report.workflow_validation.status == "failed"
    assert any(
        finding.code == "bundle.medicationrequest_placeholder_content_present"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert any(
        finding.code == "bundle.condition_placeholder_content_present"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.medicationrequest_placeholder_text_aligned_to_context"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.condition_placeholder_text_aligned_to_context"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.allergyintolerance_placeholder_content_present"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_bundle_identity_fields_are_missing() -> None:
    normalized_request, schematic, candidate_bundle = _build_validation_inputs()
    broken_bundle = deepcopy(candidate_bundle)
    broken_bundle.candidate_bundle.fhir_bundle.pop("identifier", None)
    broken_bundle.candidate_bundle.fhir_bundle.pop("timestamp", None)
    broken_bundle.candidate_bundle.fhir_bundle["entry"][0].pop("fullUrl", None)

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert report.overall_status == "failed"
    assert any(
        finding.code == "bundle.identifier_present" and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert any(
        finding.code == "bundle.timestamp_present" and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert any(
        finding.code == "bundle.entry_fullurls_present" and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_references_do_not_align_to_fullurls() -> None:
    normalized_request, schematic, candidate_bundle = _build_validation_inputs()
    broken_bundle = deepcopy(candidate_bundle)
    practitioner_role = broken_bundle.candidate_bundle.fhir_bundle["entry"][2]["resource"]
    practitioner_role["organization"]["reference"] = "Organization/organization-1"

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert report.workflow_validation.status == "failed"
    assert any(
        finding.code == "bundle.practitionerrole_organization_reference_aligned" and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.practitionerrole_practitioner_reference_aligned"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_practitionerrole_practitioner_reference_is_not_aligned() -> None:
    normalized_request, schematic, resource_construction, candidate_bundle = _build_validation_artifacts()
    broken_bundle = deepcopy(candidate_bundle)
    practitioner_role = broken_bundle.candidate_bundle.fhir_bundle["entry"][2]["resource"]
    practitioner_role["practitioner"]["reference"] = "Practitioner/practitioner-1"

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
        resource_construction,
    )

    assert report.workflow_validation.status == "failed"
    assert any(
        finding.code == "bundle.practitionerrole_practitioner_reference_aligned"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.practitionerrole_organization_reference_aligned"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_medicationrequest_subject_reference_is_not_aligned() -> None:
    normalized_request, schematic, resource_construction, candidate_bundle = _build_validation_artifacts()
    broken_bundle = deepcopy(candidate_bundle)
    medication = broken_bundle.candidate_bundle.fhir_bundle["entry"][5]["resource"]
    medication["subject"]["reference"] = "Patient/patient-1"

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
        resource_construction,
    )

    assert report.workflow_validation.status == "failed"
    assert any(
        finding.code == "bundle.medicationrequest_subject_reference_aligned"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.allergyintolerance_patient_reference_aligned"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.condition_subject_reference_aligned"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_allergyintolerance_patient_reference_is_not_aligned() -> None:
    normalized_request, schematic, resource_construction, candidate_bundle = _build_validation_artifacts()
    broken_bundle = deepcopy(candidate_bundle)
    allergy = broken_bundle.candidate_bundle.fhir_bundle["entry"][6]["resource"]
    allergy["patient"]["reference"] = "Patient/patient-1"

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
        resource_construction,
    )

    assert report.workflow_validation.status == "failed"
    assert any(
        finding.code == "bundle.allergyintolerance_patient_reference_aligned"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.medicationrequest_subject_reference_aligned"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.condition_subject_reference_aligned"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_condition_subject_reference_is_not_aligned() -> None:
    normalized_request, schematic, resource_construction, candidate_bundle = _build_validation_artifacts()
    broken_bundle = deepcopy(candidate_bundle)
    condition = broken_bundle.candidate_bundle.fhir_bundle["entry"][7]["resource"]
    condition["subject"]["reference"] = "Patient/patient-1"

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
        resource_construction,
    )

    assert report.workflow_validation.status == "failed"
    assert any(
        finding.code == "bundle.condition_subject_reference_aligned"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.medicationrequest_subject_reference_aligned"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.allergyintolerance_patient_reference_aligned"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_medications_section_entry_reference_is_not_aligned() -> None:
    normalized_request, schematic, candidate_bundle = _build_validation_inputs()
    broken_bundle = deepcopy(candidate_bundle)
    composition = broken_bundle.candidate_bundle.fhir_bundle["entry"][0]["resource"]
    wrong_full_url = broken_bundle.candidate_bundle.fhir_bundle["entry"][6]["fullUrl"]
    composition["section"][0]["entry"][0]["reference"] = wrong_full_url

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert report.workflow_validation.status == "failed"
    assert any(
        finding.code == "bundle.composition_medications_section_entry_reference_aligned"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.composition_medications_section_present"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.medications_bundle_entries_aligned_to_plan"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_medication_bundle_entries_do_not_match_plan() -> None:
    normalized_request, schematic, candidate_bundle = _build_validation_inputs(
        medication_texts=[
            "Atorvastatin 20 MG oral tablet",
            "Metformin 500 MG oral tablet",
        ]
    )
    broken_bundle = deepcopy(candidate_bundle)
    broken_bundle.entry_assembly[5], broken_bundle.entry_assembly[6] = (
        broken_bundle.entry_assembly[6],
        broken_bundle.entry_assembly[5],
    )
    broken_bundle.evidence.assembled_medication_placeholder_ids = [
        "medicationrequest-2",
        "medicationrequest-1",
    ]
    broken_bundle.candidate_bundle.fhir_bundle["entry"][5], broken_bundle.candidate_bundle.fhir_bundle["entry"][6] = (
        broken_bundle.candidate_bundle.fhir_bundle["entry"][6],
        broken_bundle.candidate_bundle.fhir_bundle["entry"][5],
    )

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert any(
        finding.code == "bundle.medications_bundle_entries_aligned_to_plan"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.composition_medications_section_entry_reference_aligned"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_second_planned_medication_bundle_entry_is_missing() -> None:
    normalized_request, schematic, candidate_bundle = _build_validation_inputs(
        medication_texts=[
            "Atorvastatin 20 MG oral tablet",
            "Metformin 500 MG oral tablet",
        ]
    )
    broken_bundle = deepcopy(candidate_bundle)
    broken_bundle.entry_assembly = [
        entry for entry in broken_bundle.entry_assembly if entry.placeholder_id != "medicationrequest-2"
    ]
    broken_bundle.evidence.assembled_medication_placeholder_ids = ["medicationrequest-1"]
    broken_bundle.candidate_bundle.fhir_bundle["entry"] = [
        entry
        for entry in broken_bundle.candidate_bundle.fhir_bundle["entry"]
        if entry["resource"]["id"] != "medicationrequest-2"
    ]
    broken_bundle.candidate_bundle.entry_count -= 1

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert any(
        finding.code == "bundle.medications_bundle_entries_aligned_to_plan"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.composition_medications_section_entry_reference_aligned"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_allergies_section_entry_reference_is_not_aligned() -> None:
    normalized_request, schematic, candidate_bundle = _build_validation_inputs()
    broken_bundle = deepcopy(candidate_bundle)
    composition = broken_bundle.candidate_bundle.fhir_bundle["entry"][0]["resource"]
    wrong_full_url = broken_bundle.candidate_bundle.fhir_bundle["entry"][7]["fullUrl"]
    composition["section"][1]["entry"][0]["reference"] = wrong_full_url

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert report.workflow_validation.status == "failed"
    assert any(
        finding.code == "bundle.composition_allergies_section_entry_reference_aligned"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.composition_allergies_section_present"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_problems_section_entry_reference_is_not_aligned() -> None:
    normalized_request, schematic, candidate_bundle = _build_validation_inputs()
    broken_bundle = deepcopy(candidate_bundle)
    composition = broken_bundle.candidate_bundle.fhir_bundle["entry"][0]["resource"]
    wrong_full_url = broken_bundle.candidate_bundle.fhir_bundle["entry"][5]["fullUrl"]
    composition["section"][2]["entry"][0]["reference"] = wrong_full_url

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert report.workflow_validation.status == "failed"
    assert any(
        finding.code == "bundle.composition_problems_section_entry_reference_aligned"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.composition_problems_section_present"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_multiple_composition_section_entry_references_are_not_aligned() -> None:
    normalized_request, schematic, candidate_bundle = _build_validation_inputs()
    broken_bundle = deepcopy(candidate_bundle)
    composition = broken_bundle.candidate_bundle.fhir_bundle["entry"][0]["resource"]
    composition["section"][0]["entry"][0]["reference"] = broken_bundle.candidate_bundle.fhir_bundle["entry"][6]["fullUrl"]
    composition["section"][2]["entry"][0]["reference"] = broken_bundle.candidate_bundle.fhir_bundle["entry"][5]["fullUrl"]

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert report.workflow_validation.status == "failed"
    assert set(finding.code for finding in report.workflow_validation.findings if finding.severity == "error") >= {
        "bundle.composition_medications_section_entry_reference_aligned",
        "bundle.composition_problems_section_entry_reference_aligned",
    }
    assert not any(
        finding.code == "bundle.composition_allergies_section_entry_reference_aligned"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_lets_section_presence_own_missing_composition_section_blocks() -> None:
    normalized_request, schematic, candidate_bundle = _build_validation_inputs()
    broken_bundle = deepcopy(candidate_bundle)
    composition = broken_bundle.candidate_bundle.fhir_bundle["entry"][0]["resource"]
    composition["section"] = composition["section"][:2]

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert report.workflow_validation.status == "failed"
    assert any(
        finding.code == "bundle.composition_problems_section_present"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.composition_problems_section_entry_reference_aligned"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_does_not_spray_specific_reference_findings_when_fullurls_are_missing() -> None:
    normalized_request, schematic, candidate_bundle = _build_validation_inputs()
    broken_bundle = deepcopy(candidate_bundle)
    broken_bundle.candidate_bundle.fhir_bundle["entry"][2].pop("fullUrl", None)

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert report.workflow_validation.status == "failed"
    assert any(
        finding.code == "bundle.entry_fullurls_present" and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.practitionerrole_practitioner_reference_aligned"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.practitionerrole_organization_reference_aligned"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.medicationrequest_subject_reference_aligned"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.allergyintolerance_patient_reference_aligned"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.condition_subject_reference_aligned"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.composition_medications_section_entry_reference_aligned"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.composition_allergies_section_entry_reference_aligned"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.composition_problems_section_entry_reference_aligned"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_practitionerrole_practitioner_source_contribution_is_not_aligned() -> None:
    normalized_request, schematic, resource_construction, _ = _build_validation_artifacts()
    broken_construction = _mutate_resource_construction_reference(
        resource_construction,
        "practitionerrole-1",
        "practitioner.reference",
        "Practitioner/wrong-practitioner",
    )
    broken_bundle = build_psca_candidate_bundle_result(broken_construction, schematic, normalized_request)

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
        broken_construction,
    )

    assert any(
        finding.code == "bundle.practitionerrole_practitioner_reference_contribution_aligned"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.practitionerrole_practitioner_reference_aligned"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_practitionerrole_organization_source_contribution_is_not_aligned() -> None:
    normalized_request, schematic, resource_construction, _ = _build_validation_artifacts()
    broken_construction = _mutate_resource_construction_reference(
        resource_construction,
        "practitionerrole-1",
        "organization.reference",
        "Organization/wrong-organization",
    )
    broken_bundle = build_psca_candidate_bundle_result(broken_construction, schematic, normalized_request)

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
        broken_construction,
    )

    assert any(
        finding.code == "bundle.practitionerrole_organization_reference_contribution_aligned"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.practitionerrole_organization_reference_aligned"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_medicationrequest_subject_source_contribution_is_not_aligned() -> None:
    normalized_request, schematic, resource_construction, _ = _build_validation_artifacts()
    broken_construction = _mutate_resource_construction_reference(
        resource_construction,
        "medicationrequest-1",
        "subject.reference",
        "Patient/wrong-patient",
    )
    broken_bundle = build_psca_candidate_bundle_result(broken_construction, schematic, normalized_request)

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
        broken_construction,
    )

    assert any(
        finding.code == "bundle.medicationrequest_subject_reference_contribution_aligned"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.medicationrequest_subject_reference_aligned"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_allergyintolerance_patient_source_contribution_is_not_aligned() -> None:
    normalized_request, schematic, resource_construction, _ = _build_validation_artifacts()
    broken_construction = _mutate_resource_construction_reference(
        resource_construction,
        "allergyintolerance-1",
        "patient.reference",
        "Patient/wrong-patient",
    )
    broken_bundle = build_psca_candidate_bundle_result(broken_construction, schematic, normalized_request)

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
        broken_construction,
    )

    assert any(
        finding.code == "bundle.allergyintolerance_patient_reference_contribution_aligned"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.allergyintolerance_patient_reference_aligned"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_condition_subject_source_contribution_is_not_aligned() -> None:
    normalized_request, schematic, resource_construction, _ = _build_validation_artifacts()
    broken_construction = _mutate_resource_construction_reference(
        resource_construction,
        "condition-1",
        "subject.reference",
        "Patient/wrong-patient",
    )
    broken_bundle = build_psca_candidate_bundle_result(broken_construction, schematic, normalized_request)

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
        broken_construction,
    )

    assert any(
        finding.code == "bundle.condition_subject_reference_contribution_aligned"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.condition_subject_reference_aligned"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_second_medicationrequest_placeholder_content_is_missing() -> None:
    normalized_request, schematic, _, candidate_bundle = _build_validation_artifacts(
        medication_texts=[
            "Atorvastatin 20 MG oral tablet",
            "Metformin 500 MG oral tablet",
        ]
    )
    broken_bundle = deepcopy(candidate_bundle)
    broken_bundle.candidate_bundle.fhir_bundle["entry"][6]["resource"]["medicationCodeableConcept"]["text"] = ""

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert any(
        finding.code == "bundle.medicationrequest_2_placeholder_content_present"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.medicationrequest_2_placeholder_text_aligned_to_context"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_second_medicationrequest_text_is_not_aligned_to_context() -> None:
    normalized_request, schematic, _, candidate_bundle = _build_validation_artifacts(
        medication_texts=[
            "Atorvastatin 20 MG oral tablet",
            "Metformin 500 MG oral tablet",
        ]
    )
    broken_bundle = deepcopy(candidate_bundle)
    broken_bundle.candidate_bundle.fhir_bundle["entry"][6]["resource"]["medicationCodeableConcept"]["text"] = (
        "Wrong second medication text"
    )

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert any(
        finding.code == "bundle.medicationrequest_2_placeholder_text_aligned_to_context"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.medicationrequest_2_placeholder_content_present"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_second_medicationrequest_subject_source_contribution_is_not_aligned() -> None:
    normalized_request, schematic, construction, candidate_bundle = _build_validation_artifacts(
        medication_texts=[
            "Atorvastatin 20 MG oral tablet",
            "Metformin 500 MG oral tablet",
        ]
    )
    broken_construction = _mutate_resource_construction_reference(
        construction,
        "medicationrequest-2",
        "subject.reference",
        "Patient/wrong-patient",
    )

    report = await build_psca_validation_report(
        candidate_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
        broken_construction,
    )

    assert any(
        finding.code == "bundle.medicationrequest_2_subject_reference_contribution_aligned"
        and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.medicationrequest_2_subject_reference_aligned"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_keeps_medication_sibling_content_checks_placeholder_aware() -> None:
    normalized_request, schematic, _, candidate_bundle = _build_validation_artifacts(
        medication_texts=[
            "Atorvastatin 20 MG oral tablet",
            "Metformin 500 MG oral tablet",
        ]
    )
    broken_bundle = deepcopy(candidate_bundle)
    medicationrequest_1 = _bundle_entry_resource_by_id(
        broken_bundle.candidate_bundle.fhir_bundle,
        "medicationrequest-1",
    )
    medicationrequest_2 = _bundle_entry_resource_by_id(
        broken_bundle.candidate_bundle.fhir_bundle,
        "medicationrequest-2",
    )
    medicationrequest_1["medicationCodeableConcept"]["text"] = "Metformin 500 MG oral tablet"
    medicationrequest_2["medicationCodeableConcept"]["text"] = "Atorvastatin 20 MG oral tablet"

    report = await build_psca_validation_report(
        broken_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    finding_codes = {finding.code for finding in report.workflow_validation.findings}
    assert "bundle.medicationrequest_placeholder_text_aligned_to_context" in finding_codes
    assert "bundle.medicationrequest_2_placeholder_text_aligned_to_context" in finding_codes
    assert "bundle.medicationrequest_placeholder_content_present" not in finding_codes
    assert "bundle.medicationrequest_2_placeholder_content_present" not in finding_codes


async def test_psca_validation_builder_exposes_fallback_alignment_expectations_in_legacy_patient_mode() -> None:
    repository = PscaAssetRepository()
    normalized_assets = repository.load_foundation_context(PscaAssetQuery())
    normalized_request = build_psca_normalized_request(
        WorkflowBuildInput(
            specification=SpecificationSelection(),
            patient_profile=ProfileReferenceInput(
                profile_id="patient-validation-legacy",
                display_name="Legacy Validation Patient",
                source_type="patient_management",
            ),
            provider_profile=ProfileReferenceInput(
                profile_id="provider-validation-test",
                display_name="Validation Test Provider",
            ),
            provider_context=ProviderContextInput(
                provider=ProviderIdentityInput(
                    provider_id="provider-validation-test",
                    display_name="Validation Test Provider",
                    source_type="provider_management",
                ),
                organizations=[
                    ProviderOrganizationInput(
                        organization_id="org-validation-test",
                        display_name="Validation Test Organization",
                    )
                ],
                provider_role_relationships=[
                    ProviderRoleRelationshipInput(
                        relationship_id="provider-role-validation-1",
                        organization_id="org-validation-test",
                        role_label="attending-physician",
                    )
                ],
            ),
            request=BundleRequestInput(
                request_text="Create a deterministic validation report for legacy patient fallback testing.",
                scenario_label="pytest-validation",
            ),
        )
    )
    schematic = build_psca_bundle_schematic(normalized_assets, normalized_request)
    plan = build_psca_build_plan(schematic)
    construction = build_psca_resource_construction_result(plan, schematic, normalized_request)
    candidate_bundle = build_psca_candidate_bundle_result(construction, schematic, normalized_request)

    report = await build_psca_validation_report(
        candidate_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    expectations = report.evidence.patient_context_alignment.section_entry_expectations
    assert report.evidence.patient_context_alignment.normalization_mode == "legacy_patient_profile"
    assert all(expectation.alignment_mode == "fallback_placeholder" for expectation in expectations)
    assert not any(
        finding.code == "bundle.medicationrequest_placeholder_text_aligned_to_context"
        for finding in report.workflow_validation.findings
    )


def _build_validation_inputs(
    *,
    legacy_provider_context: bool = False,
    medication_texts: list[str] | None = None,
) -> tuple[NormalizedBuildRequest, object, object]:
    repository = PscaAssetRepository()
    normalized_assets = repository.load_foundation_context(PscaAssetQuery())
    medication_texts = medication_texts or ["Atorvastatin 20 MG oral tablet"]
    normalized_request = build_psca_normalized_request(
        WorkflowBuildInput(
            specification=SpecificationSelection(),
            patient_profile=ProfileReferenceInput(
                profile_id="patient-validation-test",
                display_name="Validation Test Patient",
            ),
            patient_context=PatientContextInput(
                patient=PatientIdentityInput(
                    patient_id="patient-validation-test",
                    display_name="Validation Test Patient",
                    source_type="patient_management",
                    administrative_gender="female",
                    birth_date="1985-02-14",
                ),
                medications=[
                    PatientMedicationInput(
                        medication_id=f"med-validation-{index}",
                        display_text=display_text,
                    )
                    for index, display_text in enumerate(medication_texts, start=1)
                ],
                allergies=[
                    PatientAllergyInput(
                        allergy_id="alg-validation-1",
                        display_text="Peanut allergy",
                    )
                ],
                conditions=[
                    PatientConditionInput(
                        condition_id="cond-validation-1",
                        display_text="Type 2 diabetes mellitus",
                    )
                ],
            ),
            provider_profile=ProfileReferenceInput(
                profile_id="provider-validation-test",
                display_name="Validation Test Provider",
            ),
            provider_context=(
                None
                if legacy_provider_context
                else ProviderContextInput(
                    provider=ProviderIdentityInput(
                        provider_id="provider-validation-test",
                        display_name="Validation Test Provider",
                        source_type="provider_management",
                    ),
                    organizations=[
                        ProviderOrganizationInput(
                            organization_id="org-validation-test",
                            display_name="Validation Test Organization",
                        )
                    ],
                    provider_role_relationships=[
                        ProviderRoleRelationshipInput(
                            relationship_id="provider-role-validation-1",
                            organization_id="org-validation-test",
                            role_label="attending-physician",
                        )
                    ],
                )
            ),
            request=BundleRequestInput(
                request_text="Create a deterministic validation report for testing.",
                scenario_label="pytest-validation",
            ),
        )
    )
    schematic = build_psca_bundle_schematic(normalized_assets, normalized_request)
    plan = build_psca_build_plan(schematic)
    construction = build_psca_resource_construction_result(plan, schematic, normalized_request)
    candidate_bundle = build_psca_candidate_bundle_result(construction, schematic, normalized_request)
    return normalized_request, schematic, candidate_bundle


def _build_validation_artifacts(
    *,
    legacy_provider_context: bool = False,
    medication_texts: list[str] | None = None,
) -> tuple[NormalizedBuildRequest, object, object, object]:
    repository = PscaAssetRepository()
    normalized_assets = repository.load_foundation_context(PscaAssetQuery())
    medication_texts = medication_texts or ["Atorvastatin 20 MG oral tablet"]
    normalized_request = build_psca_normalized_request(
        WorkflowBuildInput(
            specification=SpecificationSelection(),
            patient_profile=ProfileReferenceInput(
                profile_id="patient-validation-test",
                display_name="Validation Test Patient",
            ),
            patient_context=PatientContextInput(
                patient=PatientIdentityInput(
                    patient_id="patient-validation-test",
                    display_name="Validation Test Patient",
                    source_type="patient_management",
                    administrative_gender="female",
                    birth_date="1985-02-14",
                ),
                medications=[
                    PatientMedicationInput(
                        medication_id=f"med-validation-{index}",
                        display_text=display_text,
                    )
                    for index, display_text in enumerate(medication_texts, start=1)
                ],
                allergies=[
                    PatientAllergyInput(
                        allergy_id="alg-validation-1",
                        display_text="Peanut allergy",
                    )
                ],
                conditions=[
                    PatientConditionInput(
                        condition_id="cond-validation-1",
                        display_text="Type 2 diabetes mellitus",
                    )
                ],
            ),
            provider_profile=ProfileReferenceInput(
                profile_id="provider-validation-test",
                display_name="Validation Test Provider",
            ),
            provider_context=(
                None
                if legacy_provider_context
                else ProviderContextInput(
                    provider=ProviderIdentityInput(
                        provider_id="provider-validation-test",
                        display_name="Validation Test Provider",
                        source_type="provider_management",
                    ),
                    organizations=[
                        ProviderOrganizationInput(
                            organization_id="org-validation-test",
                            display_name="Validation Test Organization",
                        )
                    ],
                    provider_role_relationships=[
                        ProviderRoleRelationshipInput(
                            relationship_id="provider-role-validation-1",
                            organization_id="org-validation-test",
                            role_label="attending-physician",
                        )
                    ],
                )
            ),
            request=BundleRequestInput(
                request_text="Create a deterministic validation report for testing.",
                scenario_label="pytest-validation",
            ),
        )
    )
    schematic = build_psca_bundle_schematic(normalized_assets, normalized_request)
    plan = build_psca_build_plan(schematic)
    construction = build_psca_resource_construction_result(plan, schematic, normalized_request)
    candidate_bundle = build_psca_candidate_bundle_result(construction, schematic, normalized_request)
    return normalized_request, schematic, construction, candidate_bundle


def _mutate_resource_construction_reference(
    resource_construction,
    placeholder_id: str,
    reference_path: str,
    new_reference: str,
):
    broken_construction = deepcopy(resource_construction)
    registry_entry = next(
        entry for entry in broken_construction.resource_registry if entry.placeholder_id == placeholder_id
    )
    _set_nested_reference_value(
        registry_entry.current_scaffold.fhir_scaffold,
        reference_path,
        new_reference,
    )
    for step_result in [*broken_construction.step_results, *broken_construction.step_result_history]:
        if step_result.target_placeholder_id != placeholder_id:
            continue
        for contribution in step_result.reference_contributions:
            if contribution.reference_path == reference_path:
                contribution.reference_value = new_reference
    return broken_construction


def _set_nested_reference_value(root: dict[str, object], path: str, value: str) -> None:
    segments = path.split(".")
    current = root
    for segment in segments[:-1]:
        current = current[segment]
    current[segments[-1]] = value


def _bundle_entry_resource_by_id(bundle: dict[str, object], placeholder_id: str) -> dict[str, object]:
    entries = bundle.get("entry", [])
    if not isinstance(entries, list):
        raise ValueError("Expected Bundle.entry to be a list.")
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        resource = entry.get("resource")
        if isinstance(resource, dict) and resource.get("id") == placeholder_id:
            return resource
    raise ValueError(f"Expected bundle entry resource '{placeholder_id}' to be present.")
