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
        finding.code == "bundle.references_aligned_to_entry_fullurls" and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )


async def test_psca_validation_builder_fails_when_required_section_is_missing() -> None:
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
    assert report.overall_status == "failed"
    assert any(
        finding.code == "bundle.required_sections_present" and finding.severity == "error"
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
        finding.code == "bundle.composition_enriched_content_present" and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )
    assert any(
        finding.code == "bundle.patient_identity_content_present" and finding.severity == "error"
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
        finding.code == "bundle.references_aligned_to_entry_fullurls" and finding.severity == "error"
        for finding in report.workflow_validation.findings
    )


def _build_validation_inputs() -> tuple[NormalizedBuildRequest, object, object]:
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
            profile_id="patient-validation-test",
            display_name="Validation Test Patient",
        ),
        provider_profile=ProfileReferenceInput(
            profile_id="provider-validation-test",
            display_name="Validation Test Provider",
        ),
        request=BundleRequestInput(
            request_text="Create a deterministic validation report for testing.",
            scenario_label="pytest-validation",
        ),
        workflow_defaults=WorkflowDefaults(
            bundle_type="document",
            specification_mode="normalized-asset-foundation",
            validation_mode="foundational_dual_channel",
            resource_construction_mode="deterministic_content_enriched_foundation",
        ),
        run_label="pytest-validation:ca.infoway.io.psca:2.1.1-DFT",
    )
    construction = build_psca_resource_construction_result(plan, schematic, normalized_request)
    candidate_bundle = build_psca_candidate_bundle_result(construction, schematic, normalized_request)
    return normalized_request, schematic, candidate_bundle
