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
        finding.code == "bundle.composition_medications_section_entry_reference_aligned" and finding.severity == "error"
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
        finding.code == "bundle.allergyintolerance_placeholder_content_present"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.condition_placeholder_content_present"
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
        finding.code == "bundle.medicationrequest_placeholder_content_present"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.condition_placeholder_content_present"
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
        finding.code == "bundle.medicationrequest_placeholder_content_present"
        for finding in report.workflow_validation.findings
    )
    assert not any(
        finding.code == "bundle.allergyintolerance_placeholder_content_present"
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


def _build_validation_inputs(
    *,
    legacy_provider_context: bool = False,
) -> tuple[NormalizedBuildRequest, object, object]:
    repository = PscaAssetRepository()
    normalized_assets = repository.load_foundation_context(PscaAssetQuery())
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
                        medication_id="med-validation-1",
                        display_text="Atorvastatin 20 MG oral tablet",
                    )
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
) -> tuple[NormalizedBuildRequest, object, object, object]:
    repository = PscaAssetRepository()
    normalized_assets = repository.load_foundation_context(PscaAssetQuery())
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
                        medication_id="med-validation-1",
                        display_text="Atorvastatin 20 MG oral tablet",
                    )
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
