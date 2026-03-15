"""Deterministic PS-CA validation foundation over the candidate bundle scaffold."""

from __future__ import annotations

from fhir_bundle_builder.validation import (
    PatientContextAlignmentEvidence,
    ProviderContextAlignmentEvidence,
    SectionEntryTextAlignmentExpectation,
    StandardsValidationRequest,
    StandardsValidator,
    ValidationEvidence,
    ValidationFinding,
    WorkflowValidationResult,
)

from .models import (
    BundleSchematic,
    CandidateBundleResult,
    NormalizedBuildRequest,
    ResourceConstructionStageResult,
    ValidationReport,
)
from .resource_construction_builder import (
    SELECTED_PROVIDER_ORGANIZATION_IDENTIFIER_SYSTEM,
    SELECTED_PROVIDER_ROLE_RELATIONSHIP_IDENTIFIER_SYSTEM,
)


async def build_psca_validation_report(
    candidate_bundle: CandidateBundleResult,
    schematic: BundleSchematic,
    normalized_request: NormalizedBuildRequest,
    standards_validator: StandardsValidator,
    resource_construction: ResourceConstructionStageResult | None = None,
) -> ValidationReport:
    """Build the first real validation report from the candidate bundle scaffold."""

    standards_result = await standards_validator.validate(
        StandardsValidationRequest(
            bundle_id=candidate_bundle.candidate_bundle.bundle_id,
            bundle_json=candidate_bundle.candidate_bundle.fhir_bundle,
            bundle_profile_url=candidate_bundle.candidate_bundle.profile_url,
            specification_package_id=normalized_request.specification.package_id,
            specification_version=normalized_request.specification.version,
        )
    )
    workflow_result = _build_workflow_validation_result(
        candidate_bundle,
        schematic,
        normalized_request,
        resource_construction,
    )

    all_findings = [*standards_result.findings, *workflow_result.findings]
    error_count = sum(1 for finding in all_findings if finding.severity == "error")
    warning_count = sum(1 for finding in all_findings if finding.severity == "warning")
    information_count = sum(1 for finding in all_findings if finding.severity == "information")

    return ValidationReport(
        stage_id="validation",
        status="placeholder_complete",
        summary="Validated the candidate bundle scaffold through a pluggable standards-validation boundary and deterministic workflow-rule checks.",
        placeholder_note="This slice keeps standards validation behind a pluggable boundary; local scaffold validation remains available and external validation is runtime-configurable.",
        source_refs=candidate_bundle.source_refs,
        overall_status=_status_from_results(standards_result.status, workflow_result.status),
        standards_validation=standards_result,
        workflow_validation=workflow_result,
        error_count=error_count,
        warning_count=warning_count,
        information_count=information_count,
        deferred_validation_areas=_dedupe(
            [*standards_result.deferred_areas, *workflow_result.deferred_areas]
        ),
        evidence=ValidationEvidence(
            source_candidate_bundle_stage_id=candidate_bundle.stage_id,
            source_schematic_stage_id=candidate_bundle.evidence.source_schematic_stage_id,
            source_build_plan_stage_id=candidate_bundle.evidence.source_build_plan_stage_id,
            source_resource_construction_stage_id=candidate_bundle.evidence.source_resource_construction_stage_id,
            validated_bundle_id=candidate_bundle.candidate_bundle.bundle_id,
            patient_context_alignment=_patient_context_alignment_evidence(
                normalized_request,
                schematic,
            ),
            provider_context_alignment=_provider_context_alignment_evidence(
                normalized_request,
            ),
            source_refs=candidate_bundle.source_refs,
        ),
    )


def _build_workflow_validation_result(
    candidate_bundle: CandidateBundleResult,
    schematic: BundleSchematic,
    normalized_request: NormalizedBuildRequest,
    resource_construction: ResourceConstructionStageResult | None,
) -> WorkflowValidationResult:
    bundle = candidate_bundle.candidate_bundle.fhir_bundle
    entry_assembly = candidate_bundle.entry_assembly
    findings: list[ValidationFinding] = []
    medication_placeholder_ids = _medication_placeholder_ids_from_schematic(schematic)
    checks_run = [
        "bundle.type_is_document",
        "bundle.required_entries_present",
        "bundle.identifier_present",
        "bundle.timestamp_present",
        "bundle.entry_fullurls_present",
        "bundle.composition_first_placeholder",
        "bundle.first_entry_is_composition",
        "bundle.composition_type_matches_psca_summary",
        "bundle.composition_core_scaffold_content_present",
        "bundle.composition_subject_reference_aligned",
        "bundle.composition_author_reference_aligned",
        "bundle.patient_identity_content_present",
        "bundle.patient_identity_aligned_to_context",
        "bundle.practitioner_identity_content_present",
        "bundle.practitioner_identity_aligned_to_context",
        "bundle.organization_identity_content_present",
        "bundle.organization_identity_aligned_to_context",
        "bundle.practitionerrole_relationship_identity_present",
        "bundle.practitionerrole_relationship_identity_aligned_to_context",
        "bundle.practitionerrole_author_context_present",
        "bundle.practitionerrole_author_context_aligned_to_context",
        "bundle.medicationrequest_placeholder_content_present",
        "bundle.medicationrequest_placeholder_text_aligned_to_context",
        *(
            [
                "bundle.medicationrequest_2_placeholder_content_present",
                "bundle.medicationrequest_2_placeholder_text_aligned_to_context",
            ]
            if len(medication_placeholder_ids) > 1
            else []
        ),
        "bundle.medications_bundle_entries_aligned_to_plan",
        "bundle.allergyintolerance_placeholder_content_present",
        "bundle.allergyintolerance_placeholder_text_aligned_to_context",
        "bundle.condition_placeholder_content_present",
        "bundle.condition_placeholder_text_aligned_to_context",
        "bundle.composition_medications_section_present",
        "bundle.composition_allergies_section_present",
        "bundle.composition_problems_section_present",
        "bundle.practitionerrole_practitioner_reference_contribution_aligned",
        "bundle.practitionerrole_organization_reference_contribution_aligned",
        "bundle.medicationrequest_subject_reference_contribution_aligned",
        *(
            ["bundle.medicationrequest_2_subject_reference_contribution_aligned"]
            if len(medication_placeholder_ids) > 1
            else []
        ),
        "bundle.allergyintolerance_patient_reference_contribution_aligned",
        "bundle.condition_subject_reference_contribution_aligned",
        "bundle.practitionerrole_practitioner_reference_aligned",
        "bundle.practitionerrole_organization_reference_aligned",
        "bundle.medicationrequest_subject_reference_aligned",
        *(
            ["bundle.medicationrequest_2_subject_reference_aligned"]
            if len(medication_placeholder_ids) > 1
            else []
        ),
        "bundle.allergyintolerance_patient_reference_aligned",
        "bundle.condition_subject_reference_aligned",
        "bundle.composition_medications_section_entry_reference_aligned",
        "bundle.composition_allergies_section_entry_reference_aligned",
        "bundle.composition_problems_section_entry_reference_aligned",
    ]

    if bundle.get("type") != "document":
        findings.append(
            _workflow_error(
                "bundle.type_is_document",
                "Bundle.type",
                "Expected candidate bundle type to equal 'document'.",
            )
        )

    assembled_placeholder_ids = [entry.placeholder_id for entry in entry_assembly]
    missing_required = [
        placeholder_id
        for placeholder_id in schematic.bundle_scaffold.required_entry_placeholder_ids
        if placeholder_id not in assembled_placeholder_ids
    ]
    if missing_required:
        findings.append(
            _workflow_error(
                "bundle.required_entries_present",
                "Bundle.entry",
                f"Missing required bundle scaffold placeholders: {', '.join(missing_required)}.",
            )
        )

    identifier = bundle.get("identifier")
    if not isinstance(identifier, dict) or not identifier.get("system") or not identifier.get("value"):
        findings.append(
            _workflow_error(
                "bundle.identifier_present",
                "Bundle.identifier",
                "Expected Bundle.identifier.system and Bundle.identifier.value to be present.",
            )
        )

    if not isinstance(bundle.get("timestamp"), str) or not bundle.get("timestamp"):
        findings.append(
            _workflow_error(
                "bundle.timestamp_present",
                "Bundle.timestamp",
                "Expected Bundle.timestamp to be present.",
            )
        )

    if not _entry_fullurls_present(bundle):
        findings.append(
            _workflow_error(
                "bundle.entry_fullurls_present",
                "Bundle.entry.fullUrl",
                "Expected every bundle entry to include a deterministic fullUrl.",
            )
        )

    if not entry_assembly or entry_assembly[0].placeholder_id != "composition-1":
        findings.append(
            _workflow_error(
                "bundle.composition_first_placeholder",
                "Bundle.entry[0]",
                "Expected the first assembled bundle entry placeholder to be 'composition-1'.",
            )
        )

    entries = bundle.get("entry", [])
    first_resource = None
    if isinstance(entries, list) and entries and isinstance(entries[0], dict):
        first_resource = entries[0].get("resource")
    if not isinstance(first_resource, dict) or first_resource.get("resourceType") != "Composition":
        findings.append(
            _workflow_error(
                "bundle.first_entry_is_composition",
                "Bundle.entry[0].resource.resourceType",
                "Expected the first bundle entry resource to be Composition.",
            )
        )

    composition = _find_composition_resource(bundle)
    expected_system = schematic.composition_scaffold.expected_type_system
    expected_code = schematic.composition_scaffold.expected_type_code
    actual_coding = _first_composition_coding(composition)
    if actual_coding.get("system") != expected_system or actual_coding.get("code") != expected_code:
        findings.append(
            _workflow_error(
                "bundle.composition_type_matches_psca_summary",
                "Bundle.entry[0].resource.type.coding[0]",
                f"Expected Composition type coding to equal {expected_system}|{expected_code}.",
            )
        )
    if not _composition_core_scaffold_content_present(composition):
        findings.append(
            _workflow_error(
                "bundle.composition_core_scaffold_content_present",
                "Bundle.entry[0].resource",
                "Expected Composition enriched content to include status='final' and a deterministic title.",
            )
        )
    full_urls_by_placeholder_id = _full_urls_by_placeholder_id(bundle)
    if not _composition_subject_reference_aligned(composition, full_urls_by_placeholder_id):
        findings.append(
            _workflow_error(
                "bundle.composition_subject_reference_aligned",
                "Bundle.entry[0].resource.subject.reference",
                "Expected Composition.subject.reference to align to the Patient bundle entry fullUrl.",
            )
        )
    if not _composition_author_reference_aligned(composition, full_urls_by_placeholder_id):
        findings.append(
            _workflow_error(
                "bundle.composition_author_reference_aligned",
                "Bundle.entry[0].resource.author[0].reference",
                "Expected Composition.author[0].reference to align to the PractitionerRole bundle entry fullUrl.",
            )
        )

    patient = _find_resource_by_type(bundle, "Patient")
    expected_patient = normalized_request.patient_context.patient
    patient_identifier = patient.get("identifier") if isinstance(patient, dict) else None
    patient_name = patient.get("name") if isinstance(patient, dict) else None
    identifier_value = (
        patient_identifier[0].get("value")
        if isinstance(patient_identifier, list) and patient_identifier and isinstance(patient_identifier[0], dict)
        else None
    )
    patient_name_text = (
        patient_name[0].get("text")
        if isinstance(patient_name, list) and patient_name and isinstance(patient_name[0], dict)
        else None
    )
    patient_gender = patient.get("gender") if isinstance(patient, dict) else None
    patient_birth_date = patient.get("birthDate") if isinstance(patient, dict) else None
    patient_identity_content_present = (
        patient.get("active") is True
        and isinstance(identifier_value, str)
        and bool(identifier_value)
        and isinstance(patient_name_text, str)
        and bool(patient_name_text)
        and (
            expected_patient.administrative_gender is None
            or (isinstance(patient_gender, str) and bool(patient_gender))
        )
        and (
            expected_patient.birth_date is None
            or (isinstance(patient_birth_date, str) and bool(patient_birth_date))
        )
    )
    if not patient_identity_content_present:
        findings.append(
            _workflow_error(
                "bundle.patient_identity_content_present",
                "Bundle.entry[1].resource",
                "Expected Patient enriched content to include active=true, identifier[0].value, and name[0].text, plus gender/birthDate fields when normalized patient context supplies them.",
            )
        )
    elif (
        identifier_value != expected_patient.patient_id
        or patient_name_text != expected_patient.display_name
        or (
            expected_patient.administrative_gender is not None
            and patient_gender != expected_patient.administrative_gender
        )
        or (expected_patient.birth_date is not None and patient_birth_date != expected_patient.birth_date)
    ):
        findings.append(
            _workflow_error(
                "bundle.patient_identity_aligned_to_context",
                "Bundle.entry[1].resource",
                "Expected Patient identity content to align exactly to normalized patient context for identifier, name, and optional demographic values when supplied.",
            )
        )

    practitioner = _find_resource_by_type(bundle, "Practitioner")
    practitioner_identifier = practitioner.get("identifier") if isinstance(practitioner, dict) else None
    practitioner_name = practitioner.get("name") if isinstance(practitioner, dict) else None
    practitioner_identifier_value = (
        practitioner_identifier[0].get("value")
        if isinstance(practitioner_identifier, list)
        and practitioner_identifier
        and isinstance(practitioner_identifier[0], dict)
        else None
    )
    practitioner_name_text = (
        practitioner_name[0].get("text")
        if isinstance(practitioner_name, list) and practitioner_name and isinstance(practitioner_name[0], dict)
        else None
    )
    practitioner_identity_content_present = (
        practitioner.get("active") is True
        and isinstance(practitioner_identifier_value, str)
        and bool(practitioner_identifier_value)
        and isinstance(practitioner_name_text, str)
        and bool(practitioner_name_text)
    )
    if not practitioner_identity_content_present:
        findings.append(
            _workflow_error(
                "bundle.practitioner_identity_content_present",
                "Bundle.entry[3].resource",
                "Expected Practitioner enriched content to include active=true, identifier[0].value, and name[0].text.",
            )
        )
    elif not _practitioner_identity_aligned_to_context(
        practitioner_identifier_value,
        practitioner_name_text,
        normalized_request,
    ):
        findings.append(
            _workflow_error(
                "bundle.practitioner_identity_aligned_to_context",
                "Bundle.entry[3].resource",
                "Expected Practitioner identity content to align exactly to normalized provider context for identifier and display name.",
            )
        )

    organization = _find_resource_by_type(bundle, "Organization")
    selected_organization = normalized_request.provider_context.selected_organization
    organization_identifier = organization.get("identifier") if isinstance(organization, dict) else None
    organization_identifier_value = (
        organization_identifier[0].get("value")
        if isinstance(organization_identifier, list)
        and organization_identifier
        and isinstance(organization_identifier[0], dict)
        else None
    )
    organization_identifier_system = (
        organization_identifier[0].get("system")
        if isinstance(organization_identifier, list)
        and organization_identifier
        and isinstance(organization_identifier[0], dict)
        else None
    )
    organization_name = organization.get("name") if isinstance(organization, dict) else None
    organization_identity_content_present = (
        selected_organization is None
        or (
            isinstance(organization_identifier_system, str)
            and bool(organization_identifier_system)
            and isinstance(organization_identifier_value, str)
            and bool(organization_identifier_value)
            and isinstance(organization_name, str)
            and bool(organization_name)
        )
    )
    if not organization_identity_content_present:
        findings.append(
            _workflow_error(
                "bundle.organization_identity_content_present",
                "Bundle.entry[4].resource",
                "Expected Organization enriched content to include non-empty identifier[0].system, identifier[0].value, and name when normalized provider context supplies a selected organization.",
            )
        )
    elif selected_organization is not None and not _organization_identity_aligned_to_context(
        organization_identifier_system,
        organization_identifier_value,
        organization_name,
        normalized_request,
    ):
        findings.append(
            _workflow_error(
                "bundle.organization_identity_aligned_to_context",
                "Bundle.entry[4].resource",
                "Expected Organization identity content to align exactly to the selected normalized provider organization context.",
            )
        )

    practitioner_role = _find_resource_by_type(bundle, "PractitionerRole")
    practitioner_role_identifier = practitioner_role.get("identifier") if isinstance(practitioner_role, dict) else None
    practitioner_role_identifier_value = (
        practitioner_role_identifier[0].get("value")
        if isinstance(practitioner_role_identifier, list)
        and practitioner_role_identifier
        and isinstance(practitioner_role_identifier[0], dict)
        else None
    )
    practitioner_role_identifier_system = (
        practitioner_role_identifier[0].get("system")
        if isinstance(practitioner_role_identifier, list)
        and practitioner_role_identifier
        and isinstance(practitioner_role_identifier[0], dict)
        else None
    )
    selected_relationship = normalized_request.provider_context.selected_provider_role_relationship
    practitionerrole_relationship_identity_present = (
        selected_relationship is None
        or (
            isinstance(practitioner_role_identifier_system, str)
            and bool(practitioner_role_identifier_system)
            and isinstance(practitioner_role_identifier_value, str)
            and bool(practitioner_role_identifier_value)
        )
    )
    if not practitionerrole_relationship_identity_present:
        findings.append(
            _workflow_error(
                "bundle.practitionerrole_relationship_identity_present",
                "Bundle.entry[2].resource.identifier[0]",
                "Expected PractitionerRole to include non-empty identifier[0].system and identifier[0].value when normalized provider context supplies a selected provider-role relationship.",
            )
        )
    elif selected_relationship is not None and not _practitionerrole_relationship_identity_aligned_to_context(
        practitioner_role_identifier_system,
        practitioner_role_identifier_value,
        normalized_request,
    ):
        findings.append(
            _workflow_error(
                "bundle.practitionerrole_relationship_identity_aligned_to_context",
                "Bundle.entry[2].resource.identifier[0]",
                "Expected PractitionerRole relationship identity content to align exactly to the selected normalized provider-role relationship context.",
            )
        )

    role_code = practitioner_role.get("code") if isinstance(practitioner_role, dict) else None
    role_text = (
        role_code[0].get("text")
        if isinstance(role_code, list) and role_code and isinstance(role_code[0], dict)
        else None
    )
    expected_role_text = _expected_practitioner_role_text(normalized_request)
    practitionerrole_author_context_present = isinstance(role_text, str) and bool(role_text)
    if not practitionerrole_author_context_present:
        findings.append(
            _workflow_error(
                "bundle.practitionerrole_author_context_present",
                "Bundle.entry[2].resource.code[0].text",
                "Expected PractitionerRole to include a non-empty deterministic author-context label in code[0].text.",
            )
        )
    elif role_text != expected_role_text:
        findings.append(
            _workflow_error(
                "bundle.practitionerrole_author_context_aligned_to_context",
                "Bundle.entry[2].resource.code[0].text",
                f"Expected PractitionerRole author-context label to align exactly to the deterministic provider-context expectation '{expected_role_text}'.",
            )
        )

    medicationrequest_1_content_present = _medicationrequest_placeholder_content_present(
        bundle,
        normalized_request,
        schematic,
        "medicationrequest-1",
    )
    if not medicationrequest_1_content_present:
        findings.append(
            _workflow_error(
                "bundle.medicationrequest_placeholder_content_present",
                "Bundle.entry.resource[id='medicationrequest-1']",
                "Expected MedicationRequest content to include status='draft', intent='proposal', and a non-empty medicationCodeableConcept.text value.",
            )
        )
    elif not _medicationrequest_placeholder_text_aligned_to_context(
        bundle,
        normalized_request,
        schematic,
        "medicationrequest-1",
    ):
        findings.append(
            _workflow_error(
                "bundle.medicationrequest_placeholder_text_aligned_to_context",
                "Bundle.entry.resource[id='medicationrequest-1'].medicationCodeableConcept.text",
                "Expected MedicationRequest text content to align exactly to the deterministic normalized patient-context expectation or fallback placeholder policy.",
            )
        )
    if len(medication_placeholder_ids) > 1:
        medicationrequest_2_content_present = _medicationrequest_placeholder_content_present(
            bundle,
            normalized_request,
            schematic,
            "medicationrequest-2",
        )
        if not medicationrequest_2_content_present:
            findings.append(
                _workflow_error(
                    "bundle.medicationrequest_2_placeholder_content_present",
                    "Bundle.entry.resource[id='medicationrequest-2']",
                    "Expected the second MedicationRequest content to include status='draft', intent='proposal', and a non-empty medicationCodeableConcept.text value.",
                )
            )
        elif not _medicationrequest_placeholder_text_aligned_to_context(
            bundle,
            normalized_request,
            schematic,
            "medicationrequest-2",
        ):
            findings.append(
                _workflow_error(
                    "bundle.medicationrequest_2_placeholder_text_aligned_to_context",
                    "Bundle.entry.resource[id='medicationrequest-2'].medicationCodeableConcept.text",
                    "Expected the second MedicationRequest text content to align exactly to the authoritative bounded medication mapping.",
                )
            )
    medications_bundle_entries_aligned = _medications_bundle_entries_aligned_to_plan(
        candidate_bundle,
        schematic,
    )
    if not medications_bundle_entries_aligned:
        findings.append(
            _workflow_error(
                "bundle.medications_bundle_entries_aligned_to_plan",
                "Bundle.entry",
                "Expected final bundle-entry assembly to contain exactly the planned MedicationRequest placeholders in scaffold order, with matching resource ids, MedicationRequest resource types, and non-empty fullUrls.",
            )
        )

    allergy_content_present = _allergyintolerance_placeholder_content_present(bundle, normalized_request, schematic)
    if not allergy_content_present:
        findings.append(
            _workflow_error(
                "bundle.allergyintolerance_placeholder_content_present",
                "Bundle.entry[6].resource",
                "Expected AllergyIntolerance content to include fixed clinical/verification status codes and a non-empty code.text value.",
            )
        )
    elif not _allergyintolerance_placeholder_text_aligned_to_context(bundle, normalized_request, schematic):
        findings.append(
            _workflow_error(
                "bundle.allergyintolerance_placeholder_text_aligned_to_context",
                "Bundle.entry[6].resource.code.text",
                "Expected AllergyIntolerance text content to align exactly to the deterministic normalized patient-context expectation or fallback placeholder policy.",
            )
        )

    condition_content_present = _condition_placeholder_content_present(bundle, normalized_request, schematic)
    if not condition_content_present:
        findings.append(
            _workflow_error(
                "bundle.condition_placeholder_content_present",
                "Bundle.entry[7].resource",
                "Expected Condition content to include fixed clinical/verification status codes and a non-empty code.text value.",
            )
        )
    elif not _condition_placeholder_text_aligned_to_context(bundle, normalized_request, schematic):
        findings.append(
            _workflow_error(
                "bundle.condition_placeholder_text_aligned_to_context",
                "Bundle.entry[7].resource.code.text",
                "Expected Condition text content to align exactly to the deterministic normalized patient-context expectation or fallback placeholder policy.",
            )
        )

    sections = composition.get("section", []) if isinstance(composition, dict) else []
    section_code_by_key = {
        "medications": "bundle.composition_medications_section_present",
        "allergies": "bundle.composition_allergies_section_present",
        "problems": "bundle.composition_problems_section_present",
    }
    for section_scaffold in schematic.section_scaffolds:
        if _composition_section_present(sections, section_scaffold):
            continue
        findings.append(
            _workflow_error(
                section_code_by_key[section_scaffold.section_key],
                "Bundle.entry[0].resource.section",
                (
                    f"Expected Composition to include the deterministic '{section_scaffold.section_key}' "
                    "section block with matching title, LOINC code, and the planned section-entry count."
                ),
            )
        )

    practitionerrole_practitioner_source_ok = _reference_contribution_aligned(
        resource_construction,
        "practitionerrole-1",
        "practitioner.reference",
        "practitioner-1",
    )
    if not practitionerrole_practitioner_source_ok:
        findings.append(
            _workflow_error(
                "bundle.practitionerrole_practitioner_reference_contribution_aligned",
                "resource_construction.practitionerrole-1.practitioner.reference",
                "Expected PractitionerRole.practitioner.reference to remain aligned to the deterministic local Practitioner placeholder reference before bundle fullUrl rewriting.",
            )
        )
    elif not _practitionerrole_practitioner_reference_aligned(bundle, full_urls_by_placeholder_id):
        findings.append(
            _workflow_error(
                "bundle.practitionerrole_practitioner_reference_aligned",
                "Bundle.entry[2].resource.practitioner.reference",
                "Expected PractitionerRole.practitioner.reference to align to the Practitioner bundle entry fullUrl.",
            )
        )

    practitionerrole_organization_source_ok = _reference_contribution_aligned(
        resource_construction,
        "practitionerrole-1",
        "organization.reference",
        "organization-1",
    )
    if not practitionerrole_organization_source_ok:
        findings.append(
            _workflow_error(
                "bundle.practitionerrole_organization_reference_contribution_aligned",
                "resource_construction.practitionerrole-1.organization.reference",
                "Expected PractitionerRole.organization.reference to remain aligned to the deterministic local Organization placeholder reference before bundle fullUrl rewriting.",
            )
        )
    elif not _practitionerrole_organization_reference_aligned(bundle, full_urls_by_placeholder_id):
        findings.append(
            _workflow_error(
                "bundle.practitionerrole_organization_reference_aligned",
                "Bundle.entry[2].resource.organization.reference",
                "Expected PractitionerRole.organization.reference to align to the Organization bundle entry fullUrl.",
            )
        )

    medicationrequest_subject_source_ok = _reference_contribution_aligned(
        resource_construction,
        "medicationrequest-1",
        "subject.reference",
        "patient-1",
    )
    if not medicationrequest_subject_source_ok:
        findings.append(
            _workflow_error(
                "bundle.medicationrequest_subject_reference_contribution_aligned",
                "resource_construction.medicationrequest-1.subject.reference",
                "Expected MedicationRequest.subject.reference to remain aligned to the deterministic local Patient placeholder reference before bundle fullUrl rewriting.",
            )
        )
    elif not _medicationrequest_subject_reference_aligned(bundle, full_urls_by_placeholder_id):
        findings.append(
            _workflow_error(
                "bundle.medicationrequest_subject_reference_aligned",
                "Bundle.entry.resource[id='medicationrequest-1'].subject.reference",
                "Expected MedicationRequest.subject.reference to align to the Patient bundle entry fullUrl.",
            )
        )
    if len(medication_placeholder_ids) > 1:
        medicationrequest_2_subject_source_ok = _reference_contribution_aligned(
            resource_construction,
            "medicationrequest-2",
            "subject.reference",
            "patient-1",
        )
        if not medicationrequest_2_subject_source_ok:
            findings.append(
                _workflow_error(
                    "bundle.medicationrequest_2_subject_reference_contribution_aligned",
                    "resource_construction.medicationrequest-2.subject.reference",
                    "Expected the second MedicationRequest.subject.reference to remain aligned to the deterministic local Patient placeholder reference before bundle fullUrl rewriting.",
                )
            )
        elif not _medicationrequest_subject_reference_aligned(
            bundle,
            full_urls_by_placeholder_id,
            "medicationrequest-2",
        ):
            findings.append(
                _workflow_error(
                    "bundle.medicationrequest_2_subject_reference_aligned",
                    "Bundle.entry.resource[id='medicationrequest-2'].subject.reference",
                    "Expected the second MedicationRequest.subject.reference to align to the Patient bundle entry fullUrl.",
                )
            )

    allergyintolerance_patient_source_ok = _reference_contribution_aligned(
        resource_construction,
        "allergyintolerance-1",
        "patient.reference",
        "patient-1",
    )
    if not allergyintolerance_patient_source_ok:
        findings.append(
            _workflow_error(
                "bundle.allergyintolerance_patient_reference_contribution_aligned",
                "resource_construction.allergyintolerance-1.patient.reference",
                "Expected AllergyIntolerance.patient.reference to remain aligned to the deterministic local Patient placeholder reference before bundle fullUrl rewriting.",
            )
        )
    elif not _allergyintolerance_patient_reference_aligned(bundle, full_urls_by_placeholder_id):
        findings.append(
            _workflow_error(
                "bundle.allergyintolerance_patient_reference_aligned",
                "Bundle.entry[6].resource.patient.reference",
                "Expected AllergyIntolerance.patient.reference to align to the Patient bundle entry fullUrl.",
            )
        )

    condition_subject_source_ok = _reference_contribution_aligned(
        resource_construction,
        "condition-1",
        "subject.reference",
        "patient-1",
    )
    if not condition_subject_source_ok:
        findings.append(
            _workflow_error(
                "bundle.condition_subject_reference_contribution_aligned",
                "resource_construction.condition-1.subject.reference",
                "Expected Condition.subject.reference to remain aligned to the deterministic local Patient placeholder reference before bundle fullUrl rewriting.",
            )
        )
    elif not _condition_subject_reference_aligned(bundle, full_urls_by_placeholder_id):
        findings.append(
            _workflow_error(
                "bundle.condition_subject_reference_aligned",
                "Bundle.entry[7].resource.subject.reference",
                "Expected Condition.subject.reference to align to the Patient bundle entry fullUrl.",
            )
        )

    entry_fullurls_unique = _entry_fullurls_unique(bundle)

    section_entry_alignment_codes = {
        "medications": "bundle.composition_medications_section_entry_reference_aligned",
        "allergies": "bundle.composition_allergies_section_entry_reference_aligned",
        "problems": "bundle.composition_problems_section_entry_reference_aligned",
    }
    for section_scaffold in schematic.section_scaffolds:
        if not entry_fullurls_unique:
            continue
        if (
            section_scaffold.section_key == "medications"
            and not medications_bundle_entries_aligned
        ):
            continue
        if _composition_section_entry_reference_aligned(
            sections,
            section_scaffold,
            full_urls_by_placeholder_id,
        ):
            continue
        findings.append(
            _workflow_error(
                section_entry_alignment_codes[section_scaffold.section_key],
                f"Bundle.entry[0].resource.section[{section_scaffold.section_key}].entry.reference",
                (
                    f"Expected the Composition '{section_scaffold.section_key}' section entry reference "
                    "set to align exactly to the deterministic bundle entry fullUrls in scaffold order."
                ),
            )
        )

    return WorkflowValidationResult(
        status=_status_from_findings(findings),
        checks_run=checks_run,
        findings=findings,
        deferred_areas=[
            "Repair execution beyond one bounded retry pass is deferred.",
            "No terminology or full external conformance validation is performed in workflow-rule validation.",
        ],
    )


def _find_composition_resource(bundle: dict[str, object]) -> dict[str, object]:
    return _find_resource_by_type(bundle, "Composition")


def _find_resource_by_placeholder_id(bundle: dict[str, object], placeholder_id: str) -> dict[str, object]:
    entries = bundle.get("entry", [])
    if not isinstance(entries, list):
        return {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        resource = entry.get("resource")
        if isinstance(resource, dict) and resource.get("id") == placeholder_id:
            return resource
    return {}


def _find_resource_by_type(bundle: dict[str, object], resource_type: str) -> dict[str, object]:
    entries = bundle.get("entry", [])
    if not isinstance(entries, list):
        return {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        resource = entry.get("resource")
        if isinstance(resource, dict) and resource.get("resourceType") == resource_type:
            return resource
    return {}


def _first_composition_coding(composition: dict[str, object]) -> dict[str, object]:
    type_value = composition.get("type")
    if not isinstance(type_value, dict):
        return {}
    coding = type_value.get("coding")
    if not isinstance(coding, list) or not coding:
        return {}
    first = coding[0]
    return first if isinstance(first, dict) else {}


def _composition_core_scaffold_content_present(composition: dict[str, object]) -> bool:
    return (
        isinstance(composition, dict)
        and composition.get("status") == "final"
        and isinstance(composition.get("title"), str)
        and bool(composition.get("title"))
    )


def _composition_subject_reference_aligned(
    composition: dict[str, object],
    full_urls_by_placeholder_id: dict[str, str],
) -> bool:
    expected_reference = full_urls_by_placeholder_id.get("patient-1")
    if not isinstance(expected_reference, str) or not expected_reference:
        return True
    subject = composition.get("subject") if isinstance(composition, dict) else None
    return (
        isinstance(subject, dict)
        and subject.get("reference") == expected_reference
    )


def _composition_author_reference_aligned(
    composition: dict[str, object],
    full_urls_by_placeholder_id: dict[str, str],
) -> bool:
    expected_reference = full_urls_by_placeholder_id.get("practitionerrole-1")
    if not isinstance(expected_reference, str) or not expected_reference:
        return True
    author = _first_list_item(composition.get("author")) if isinstance(composition, dict) else {}
    return (
        isinstance(author, dict)
        and author.get("reference") == expected_reference
    )


def _expected_practitioner_role_text(normalized_request: NormalizedBuildRequest) -> str:
    selected_relationship = normalized_request.provider_context.selected_provider_role_relationship
    if selected_relationship is not None:
        return selected_relationship.role_label
    return "document-author"


def _composition_section_present(
    sections: object,
    section_scaffold: object,
) -> bool:
    return _matching_composition_section_block(sections, section_scaffold) is not None


def _matching_composition_section_block(
    sections: object,
    section_scaffold: object,
) -> dict[str, object] | None:
    expected_title = getattr(section_scaffold, "title", None)
    expected_code = getattr(section_scaffold, "loinc_code", None)
    expected_entry_placeholder_ids = getattr(section_scaffold, "entry_placeholder_ids", [])
    if not isinstance(sections, list):
        return None
    for section in sections:
        if not isinstance(section, dict):
            continue
        title = section.get("title")
        code = section.get("code")
        coding = code.get("coding", []) if isinstance(code, dict) else []
        first_coding = coding[0] if isinstance(coding, list) and coding else {}
        loinc_code = first_coding.get("code") if isinstance(first_coding, dict) else None
        entry = section.get("entry")
        entry_references = (
            [item.get("reference") for item in entry if isinstance(item, dict)]
            if isinstance(entry, list)
            else []
        )
        if (
            title == expected_title
            and loinc_code == expected_code
            and len(entry_references) == len(expected_entry_placeholder_ids)
            and all(isinstance(reference, str) and bool(reference) for reference in entry_references)
        ):
            return section
    return None


def _entry_fullurls_present(bundle: dict[str, object]) -> bool:
    entries = bundle.get("entry", [])
    if not isinstance(entries, list):
        return False
    return all(isinstance(entry, dict) and bool(entry.get("fullUrl")) for entry in entries)


def _entry_fullurls_unique(bundle: dict[str, object]) -> bool:
    entries = bundle.get("entry", [])
    if not isinstance(entries, list):
        return False
    full_urls = [entry.get("fullUrl") for entry in entries if isinstance(entry, dict)]
    if any(not isinstance(full_url, str) or not full_url for full_url in full_urls):
        return False
    return len(full_urls) == len(set(full_urls))


def _medications_bundle_entries_aligned_to_plan(
    candidate_bundle: CandidateBundleResult,
    schematic: BundleSchematic,
) -> bool:
    planned_placeholder_ids = list(candidate_bundle.evidence.planned_medication_placeholder_ids)
    if not planned_placeholder_ids:
        planned_placeholder_ids = _medication_placeholder_ids_from_schematic(schematic)

    assembled_placeholder_ids = list(candidate_bundle.evidence.assembled_medication_placeholder_ids)
    if not assembled_placeholder_ids:
        assembled_placeholder_ids = [
            entry.placeholder_id
            for entry in candidate_bundle.entry_assembly
            if entry.placeholder_id.startswith("medicationrequest-")
        ]

    if assembled_placeholder_ids != planned_placeholder_ids:
        return False

    entries = candidate_bundle.candidate_bundle.fhir_bundle.get("entry", [])
    if not isinstance(entries, list):
        return False

    entry_lookup: dict[str, dict[str, object]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        resource = entry.get("resource")
        if not isinstance(resource, dict):
            continue
        resource_id = resource.get("id")
        if isinstance(resource_id, str):
            entry_lookup[resource_id] = entry

    for placeholder_id in planned_placeholder_ids:
        entry = entry_lookup.get(placeholder_id)
        if not isinstance(entry, dict) or not entry.get("fullUrl"):
            return False
        resource = entry.get("resource")
        if not isinstance(resource, dict):
            return False
        if resource.get("id") != placeholder_id or resource.get("resourceType") != "MedicationRequest":
            return False
    return True


def _expected_full_url(
    full_urls_by_placeholder_id: dict[str, str],
    placeholder_id: str,
) -> str | None:
    expected = full_urls_by_placeholder_id.get(placeholder_id)
    if not isinstance(expected, str) or not expected:
        return None
    return expected


def _reference_target_aligned(
    actual_reference_parent: object,
    full_urls_by_placeholder_id: dict[str, str],
    placeholder_id: str,
) -> bool:
    expected_reference = _expected_full_url(full_urls_by_placeholder_id, placeholder_id)
    if expected_reference is None:
        return True
    return (
        isinstance(actual_reference_parent, dict)
        and actual_reference_parent.get("reference") == expected_reference
    )


def _reference_contribution_aligned(
    resource_construction: ResourceConstructionStageResult | None,
    source_placeholder_id: str,
    reference_path: str,
    target_placeholder_id: str,
) -> bool:
    if resource_construction is None:
        return True

    registry_entry = next(
        (
            entry
            for entry in resource_construction.resource_registry
            if entry.placeholder_id == source_placeholder_id
        ),
        None,
    )
    if registry_entry is None:
        return True

    expected_reference = _expected_local_reference_for_placeholder(target_placeholder_id)
    actual_scaffold_reference = _nested_reference_value(
        registry_entry.current_scaffold.fhir_scaffold,
        reference_path,
    )
    if actual_scaffold_reference != expected_reference:
        return False

    step_results = (
        resource_construction.step_result_history
        if resource_construction.step_result_history
        else resource_construction.step_results
    )
    source_step_ids = set(registry_entry.current_scaffold.source_step_ids)
    matching_contribution = None
    for step_result in step_results:
        if step_result.step_id not in source_step_ids:
            continue
        for contribution in step_result.reference_contributions:
            if contribution.reference_path == reference_path:
                matching_contribution = contribution

    return (
        matching_contribution is not None
        and matching_contribution.target_placeholder_id == target_placeholder_id
        and matching_contribution.reference_value == expected_reference
    )


def _nested_reference_value(root: object, path: str) -> str | None:
    current = root
    for segment in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(segment)
    return current if isinstance(current, str) else None


def _expected_local_reference_for_placeholder(placeholder_id: str) -> str:
    resource_key = placeholder_id.split("-", 1)[0]
    resource_type_by_key = {
        "patient": "Patient",
        "practitioner": "Practitioner",
        "organization": "Organization",
        "practitionerrole": "PractitionerRole",
        "medicationrequest": "MedicationRequest",
        "allergyintolerance": "AllergyIntolerance",
        "condition": "Condition",
        "composition": "Composition",
    }
    resource_type = resource_type_by_key.get(resource_key)
    if resource_type is None:
        raise ValueError(f"Unsupported placeholder id '{placeholder_id}' for local reference expectation.")
    return f"{resource_type}/{placeholder_id}"


def _practitionerrole_practitioner_reference_aligned(
    bundle: dict[str, object],
    full_urls_by_placeholder_id: dict[str, str],
) -> bool:
    practitioner_role = _find_resource_by_type(bundle, "PractitionerRole")
    return _reference_target_aligned(
        practitioner_role.get("practitioner"),
        full_urls_by_placeholder_id,
        "practitioner-1",
    )


def _practitionerrole_organization_reference_aligned(
    bundle: dict[str, object],
    full_urls_by_placeholder_id: dict[str, str],
) -> bool:
    practitioner_role = _find_resource_by_type(bundle, "PractitionerRole")
    return _reference_target_aligned(
        practitioner_role.get("organization"),
        full_urls_by_placeholder_id,
        "organization-1",
    )


def _medicationrequest_subject_reference_aligned(
    bundle: dict[str, object],
    full_urls_by_placeholder_id: dict[str, str],
    placeholder_id: str = "medicationrequest-1",
) -> bool:
    medication = _find_resource_by_placeholder_id(bundle, placeholder_id)
    return _reference_target_aligned(
        medication.get("subject"),
        full_urls_by_placeholder_id,
        "patient-1",
    )


def _allergyintolerance_patient_reference_aligned(
    bundle: dict[str, object],
    full_urls_by_placeholder_id: dict[str, str],
) -> bool:
    allergy = _find_resource_by_type(bundle, "AllergyIntolerance")
    return _reference_target_aligned(
        allergy.get("patient"),
        full_urls_by_placeholder_id,
        "patient-1",
    )


def _condition_subject_reference_aligned(
    bundle: dict[str, object],
    full_urls_by_placeholder_id: dict[str, str],
) -> bool:
    condition = _find_resource_by_type(bundle, "Condition")
    return _reference_target_aligned(
        condition.get("subject"),
        full_urls_by_placeholder_id,
        "patient-1",
    )


def _composition_section_entry_reference_aligned(
    sections: object,
    section_scaffold: object,
    full_urls_by_placeholder_id: dict[str, str],
) -> bool:
    matching_section = _matching_composition_section_block(sections, section_scaffold)
    if matching_section is None:
        return True
    expected_references = [
        _expected_full_url(full_urls_by_placeholder_id, placeholder_id)
        for placeholder_id in section_scaffold.entry_placeholder_ids
    ]
    if any(expected_reference is None for expected_reference in expected_references):
        return True
    entry_values = matching_section.get("entry")
    if not isinstance(entry_values, list) or len(entry_values) != len(expected_references):
        return True
    actual_references = [
        entry_value.get("reference")
        for entry_value in entry_values
        if isinstance(entry_value, dict)
    ]
    if len(actual_references) != len(expected_references):
        return True
    if any(
        not isinstance(actual_reference, str)
        or not actual_reference
        or not actual_reference.startswith("urn:uuid:")
        for actual_reference in actual_references
    ):
        return True
    return actual_references == expected_references


def _full_urls_by_placeholder_id(bundle: dict[str, object]) -> dict[str, str]:
    entries = bundle.get("entry", [])
    if not isinstance(entries, list):
        return {}
    values: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            return {}
        full_url = entry.get("fullUrl")
        resource = entry.get("resource")
        if not isinstance(full_url, str) or not isinstance(resource, dict):
            return {}
        resource_id = resource.get("id")
        if not isinstance(resource_id, str):
            return {}
        values[resource_id] = full_url
    return values


def _first_list_item(value: object) -> dict[str, object]:
    if not isinstance(value, list) or not value or not isinstance(value[0], dict):
        return {}
    return value[0]


def _workflow_error(code: str, location: str, message: str) -> ValidationFinding:
    return ValidationFinding(
        channel="workflow",
        severity="error",
        code=code,
        location=location,
        message=message,
    )


def _medicationrequest_placeholder_content_present(
    bundle: dict[str, object],
    normalized_request: NormalizedBuildRequest,
    schematic: BundleSchematic,
    placeholder_id: str = "medicationrequest-1",
) -> bool:
    medication = _find_resource_by_placeholder_id(bundle, placeholder_id)
    return (
        medication.get("status") == "draft"
        and medication.get("intent") == "proposal"
        and isinstance(medication.get("medicationCodeableConcept"), dict)
        and isinstance(medication["medicationCodeableConcept"].get("text"), str)
        and bool(medication["medicationCodeableConcept"].get("text"))
    )


def _allergyintolerance_placeholder_content_present(
    bundle: dict[str, object],
    normalized_request: NormalizedBuildRequest,
    schematic: BundleSchematic,
) -> bool:
    allergy = _find_resource_by_type(bundle, "AllergyIntolerance")
    allergy_clinical = _first_coding(allergy.get("clinicalStatus"))
    allergy_verification = _first_coding(allergy.get("verificationStatus"))
    return (
        allergy_clinical.get("code") == "active"
        and allergy_verification.get("code") == "unconfirmed"
        and isinstance(allergy.get("code"), dict)
        and isinstance(allergy["code"].get("text"), str)
        and bool(allergy["code"].get("text"))
    )


def _condition_placeholder_content_present(
    bundle: dict[str, object],
    normalized_request: NormalizedBuildRequest,
    schematic: BundleSchematic,
) -> bool:
    condition = _find_resource_by_type(bundle, "Condition")
    condition_clinical = _first_coding(condition.get("clinicalStatus"))
    condition_verification = _first_coding(condition.get("verificationStatus"))
    return (
        condition_clinical.get("code") == "active"
        and condition_verification.get("code") == "provisional"
        and isinstance(condition.get("code"), dict)
        and isinstance(condition["code"].get("text"), str)
        and bool(condition["code"].get("text"))
    )


def _medicationrequest_placeholder_text_aligned_to_context(
    bundle: dict[str, object],
    normalized_request: NormalizedBuildRequest,
    schematic: BundleSchematic,
    placeholder_id: str = "medicationrequest-1",
) -> bool:
    medication = _find_resource_by_placeholder_id(bundle, placeholder_id)
    return (
        isinstance(medication.get("medicationCodeableConcept"), dict)
        and medication["medicationCodeableConcept"].get("text")
        == _expected_medication_text(normalized_request, schematic, placeholder_id)
    )


def _allergyintolerance_placeholder_text_aligned_to_context(
    bundle: dict[str, object],
    normalized_request: NormalizedBuildRequest,
    schematic: BundleSchematic,
) -> bool:
    allergy = _find_resource_by_type(bundle, "AllergyIntolerance")
    return (
        isinstance(allergy.get("code"), dict)
        and allergy["code"].get("text") == _expected_allergy_text(normalized_request, schematic)
    )


def _condition_placeholder_text_aligned_to_context(
    bundle: dict[str, object],
    normalized_request: NormalizedBuildRequest,
    schematic: BundleSchematic,
) -> bool:
    condition = _find_resource_by_type(bundle, "Condition")
    return (
        isinstance(condition.get("code"), dict)
        and condition["code"].get("text") == _expected_condition_text(normalized_request, schematic)
    )


def _first_coding(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    coding = value.get("coding")
    if not isinstance(coding, list) or not coding:
        return {}
    first = coding[0]
    return first if isinstance(first, dict) else {}


def _status_from_findings(findings: list[ValidationFinding]) -> str:
    if any(finding.severity == "error" for finding in findings):
        return "failed"
    if any(finding.severity == "warning" for finding in findings):
        return "passed_with_warnings"
    return "passed"


def _status_from_results(standards_status: str, workflow_status: str) -> str:
    if "failed" in (standards_status, workflow_status):
        return "failed"
    if "passed_with_warnings" in (standards_status, workflow_status):
        return "passed_with_warnings"
    return "passed"


def _dedupe(values: list[str]) -> list[str]:
    ordered: list[str] = []
    for value in values:
        if value not in ordered:
            ordered.append(value)
    return ordered


def _patient_context_alignment_evidence(
    normalized_request: NormalizedBuildRequest,
    schematic: BundleSchematic,
) -> PatientContextAlignmentEvidence:
    patient = normalized_request.patient_context.patient
    return PatientContextAlignmentEvidence(
        normalization_mode=normalized_request.patient_context.normalization_mode,
        patient_id=patient.patient_id,
        display_name=patient.display_name,
        administrative_gender_expected=patient.administrative_gender,
        birth_date_expected=patient.birth_date,
        section_entry_expectations=[
            *_medication_alignment_expectations(normalized_request, schematic),
            _section_entry_text_alignment_expectation(
                normalized_request,
                schematic,
                "allergyintolerance-1",
                "AllergyIntolerance",
            ),
            _section_entry_text_alignment_expectation(
                normalized_request,
                schematic,
                "condition-1",
                "Condition",
            ),
        ],
    )


def _provider_context_alignment_evidence(
    normalized_request: NormalizedBuildRequest,
) -> ProviderContextAlignmentEvidence:
    provider_context = normalized_request.provider_context
    selected_organization = provider_context.selected_organization
    selected_relationship = provider_context.selected_provider_role_relationship
    return ProviderContextAlignmentEvidence(
        normalization_mode=provider_context.normalization_mode,
        provider_id=provider_context.provider.provider_id,
        provider_display_name=provider_context.provider.display_name,
        organization_alignment_mode=(
            "structured_provider_context"
            if selected_organization is not None
            else "not_applicable"
        ),
        selected_organization_identifier_system_expected=(
            SELECTED_PROVIDER_ORGANIZATION_IDENTIFIER_SYSTEM
            if selected_organization is not None
            else None
        ),
        selected_organization_id_expected=(
            selected_organization.organization_id if selected_organization is not None else None
        ),
        selected_organization_display_name_expected=(
            selected_organization.display_name if selected_organization is not None else None
        ),
        practitionerrole_alignment_mode=(
            "structured_provider_context"
            if selected_relationship is not None
            else "fallback_placeholder"
        ),
        selected_provider_role_relationship_identifier_system_expected=(
            SELECTED_PROVIDER_ROLE_RELATIONSHIP_IDENTIFIER_SYSTEM
            if selected_relationship is not None
            else None
        ),
        selected_provider_role_relationship_id_expected=(
            selected_relationship.relationship_id if selected_relationship is not None else None
        ),
        expected_role_label=_expected_practitioner_role_text(normalized_request),
    )


def _practitioner_identity_aligned_to_context(
    identifier_value: str | None,
    name_text: str | None,
    normalized_request: NormalizedBuildRequest,
) -> bool:
    provider = normalized_request.provider_context.provider
    return (
        identifier_value == provider.provider_id
        and name_text == provider.display_name
    )


def _organization_identity_aligned_to_context(
    identifier_system: str | None,
    identifier_value: str | None,
    name: str | None,
    normalized_request: NormalizedBuildRequest,
) -> bool:
    selected_organization = normalized_request.provider_context.selected_organization
    if selected_organization is None:
        return True
    return (
        identifier_system == SELECTED_PROVIDER_ORGANIZATION_IDENTIFIER_SYSTEM
        and identifier_value == selected_organization.organization_id
        and name == selected_organization.display_name
    )


def _practitionerrole_relationship_identity_aligned_to_context(
    identifier_system: str | None,
    identifier_value: str | None,
    normalized_request: NormalizedBuildRequest,
) -> bool:
    selected_relationship = normalized_request.provider_context.selected_provider_role_relationship
    if selected_relationship is None:
        return True
    return (
        identifier_system == SELECTED_PROVIDER_ROLE_RELATIONSHIP_IDENTIFIER_SYSTEM
        and identifier_value == selected_relationship.relationship_id
    )


def _expected_medication_text(
    normalized_request: NormalizedBuildRequest,
    schematic: BundleSchematic,
    placeholder_id: str = "medicationrequest-1",
) -> str:
    selected = _selected_medication_for_placeholder(normalized_request, placeholder_id)
    if selected is not None:
        return selected.display_text
    return _fallback_section_placeholder_text("medications", schematic, normalized_request)


def _expected_allergy_text(
    normalized_request: NormalizedBuildRequest,
    schematic: BundleSchematic,
) -> str:
    selected = normalized_request.patient_context.selected_allergy_for_single_entry
    if selected is not None:
        return selected.display_text
    return _fallback_section_placeholder_text("allergies", schematic, normalized_request)


def _expected_condition_text(
    normalized_request: NormalizedBuildRequest,
    schematic: BundleSchematic,
) -> str:
    selected = normalized_request.patient_context.selected_condition_for_single_entry
    if selected is not None:
        return selected.display_text
    return _fallback_section_placeholder_text("problems", schematic, normalized_request)


def _fallback_section_placeholder_text(
    section_key: str,
    schematic: BundleSchematic,
    normalized_request: NormalizedBuildRequest,
) -> str:
    for section in schematic.section_scaffolds:
        if section.section_key == section_key:
            return f"{section.title} placeholder for {normalized_request.request.scenario_label}"
    raise ValueError(f"Expected section scaffold '{section_key}' to be present.")


def _selected_medication_for_placeholder(
    normalized_request: NormalizedBuildRequest,
    placeholder_id: str,
):
    planned_entry = _planned_medication_entry_for_placeholder(normalized_request, placeholder_id)
    if planned_entry is not None:
        return normalized_request.patient_context.medications[planned_entry.source_medication_index]
    if placeholder_id == "medicationrequest-1":
        return normalized_request.patient_context.selected_medication_for_single_entry
    raise ValueError(f"Unsupported MedicationRequest placeholder id '{placeholder_id}'.")


def _medication_placeholder_ids_from_schematic(schematic: BundleSchematic) -> list[str]:
    for section in schematic.section_scaffolds:
        if section.section_key == "medications":
            return list(section.entry_placeholder_ids)
    raise ValueError("Expected medications section scaffold to be present.")


def _planned_medication_entry_for_placeholder(
    normalized_request: NormalizedBuildRequest,
    placeholder_id: str,
):
    for entry in normalized_request.patient_context.planned_medication_entries:
        if entry.placeholder_id == placeholder_id:
            return entry
    return None


def _medication_alignment_expectations(
    normalized_request: NormalizedBuildRequest,
    schematic: BundleSchematic,
) -> list[SectionEntryTextAlignmentExpectation]:
    expectations = [
        _section_entry_text_alignment_expectation(
            normalized_request,
            schematic,
            "medicationrequest-1",
            "MedicationRequest",
        )
    ]
    if any(entry.placeholder_id == "medicationrequest-2" for entry in normalized_request.patient_context.planned_medication_entries):
        expectations.append(
            _section_entry_text_alignment_expectation(
                normalized_request,
                schematic,
                "medicationrequest-2",
                "MedicationRequest",
            )
        )
    return expectations


def _section_entry_text_alignment_expectation(
    normalized_request: NormalizedBuildRequest,
    schematic: BundleSchematic,
    placeholder_id: str,
    resource_type: str,
) -> SectionEntryTextAlignmentExpectation:
    expected_text = _expected_text_for_placeholder(
        normalized_request,
        schematic,
        placeholder_id,
        resource_type,
    )
    source_artifact, source_detail = _expected_text_source(
        normalized_request,
        schematic,
        placeholder_id,
        resource_type,
    )
    return SectionEntryTextAlignmentExpectation(
        placeholder_id=placeholder_id,
        resource_type=resource_type,
        expected_text=expected_text,
        alignment_mode=_alignment_mode_for_placeholder(
            normalized_request,
            placeholder_id,
            resource_type,
        ),
        source_artifact=source_artifact,
        source_detail=source_detail,
    )


def _expected_text_for_placeholder(
    normalized_request: NormalizedBuildRequest,
    schematic: BundleSchematic,
    placeholder_id: str,
    resource_type: str,
) -> str:
    if resource_type == "MedicationRequest":
        return _expected_medication_text(normalized_request, schematic, placeholder_id)
    if resource_type == "AllergyIntolerance":
        return _expected_allergy_text(normalized_request, schematic)
    if resource_type == "Condition":
        return _expected_condition_text(normalized_request, schematic)
    raise ValueError(f"Unsupported resource type '{resource_type}' for patient-context alignment evidence.")


def _expected_text_source(
    normalized_request: NormalizedBuildRequest,
    schematic: BundleSchematic,
    placeholder_id: str,
    resource_type: str,
) -> tuple[str, str]:
    if resource_type == "MedicationRequest":
        planned_entry = _planned_medication_entry_for_placeholder(normalized_request, placeholder_id)
        if planned_entry is not None:
            return (
                f"normalized_request.patient_context.planned_medication_entries[{_planned_medication_entry_list_index(normalized_request, placeholder_id)}]",
                (
                    "display_text"
                    f" (placeholder_id={planned_entry.placeholder_id}, "
                    f"source_medication_index={planned_entry.source_medication_index}, "
                    f"medication_id={planned_entry.medication_id})"
                ),
            )
    if resource_type == "AllergyIntolerance" and normalized_request.patient_context.selected_allergy_for_single_entry is not None:
        return (
            "normalized_request.patient_context.selected_allergy_for_single_entry",
            "display_text",
        )
    if resource_type == "Condition" and normalized_request.patient_context.selected_condition_for_single_entry is not None:
        return (
            "normalized_request.patient_context.selected_condition_for_single_entry",
            "display_text",
        )
    section_key = _section_key_for_resource_type(resource_type)
    section_title = _section_title_for_key(schematic, section_key)
    return (
        f"bundle_schematic.section_scaffolds[{section_key}] + normalized_request.request",
        f"{section_title} + scenario_label",
    )


def _alignment_mode_for_placeholder(
    normalized_request: NormalizedBuildRequest,
    placeholder_id: str,
    resource_type: str,
) -> str:
    if resource_type == "MedicationRequest":
        return (
            "structured_patient_context"
            if _planned_medication_entry_for_placeholder(normalized_request, placeholder_id) is not None
            else "fallback_placeholder"
        )
    if resource_type == "AllergyIntolerance":
        return (
            "structured_patient_context"
            if normalized_request.patient_context.selected_allergy_for_single_entry is not None
            else "fallback_placeholder"
        )
    if resource_type == "Condition":
        return (
            "structured_patient_context"
            if normalized_request.patient_context.selected_condition_for_single_entry is not None
            else "fallback_placeholder"
        )
    raise ValueError(f"Unsupported resource type '{resource_type}' for alignment mode.")


def _planned_medication_entry_list_index(
    normalized_request: NormalizedBuildRequest,
    placeholder_id: str,
) -> int | None:
    for index, entry in enumerate(normalized_request.patient_context.planned_medication_entries):
        if entry.placeholder_id == placeholder_id:
            return index
    return None


def _section_key_for_resource_type(resource_type: str) -> str:
    section_key_by_resource_type = {
        "MedicationRequest": "medications",
        "AllergyIntolerance": "allergies",
        "Condition": "problems",
    }
    section_key = section_key_by_resource_type.get(resource_type)
    if section_key is None:
        raise ValueError(f"Unsupported resource type '{resource_type}' for section mapping.")
    return section_key


def _section_title_for_key(schematic: BundleSchematic, section_key: str) -> str:
    for section in schematic.section_scaffolds:
        if section.section_key == section_key:
            return section.title
    raise ValueError(f"Expected section scaffold '{section_key}' to be present.")
