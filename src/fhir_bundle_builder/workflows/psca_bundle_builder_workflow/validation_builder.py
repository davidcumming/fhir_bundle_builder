"""Deterministic PS-CA validation foundation over the candidate bundle scaffold."""

from __future__ import annotations

from fhir_bundle_builder.validation import (
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
    ValidationReport,
)


async def build_psca_validation_report(
    candidate_bundle: CandidateBundleResult,
    schematic: BundleSchematic,
    normalized_request: NormalizedBuildRequest,
    standards_validator: StandardsValidator,
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
    workflow_result = _build_workflow_validation_result(candidate_bundle, schematic)

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
            source_refs=candidate_bundle.source_refs,
        ),
    )


def _build_workflow_validation_result(
    candidate_bundle: CandidateBundleResult,
    schematic: BundleSchematic,
) -> WorkflowValidationResult:
    bundle = candidate_bundle.candidate_bundle.fhir_bundle
    entry_assembly = candidate_bundle.entry_assembly
    findings: list[ValidationFinding] = []
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
        "bundle.practitioner_identity_content_present",
        "bundle.practitionerrole_author_context_present",
        "bundle.medicationrequest_placeholder_content_present",
        "bundle.allergyintolerance_placeholder_content_present",
        "bundle.condition_placeholder_content_present",
        "bundle.composition_medications_section_present",
        "bundle.composition_allergies_section_present",
        "bundle.composition_problems_section_present",
        "bundle.practitionerrole_practitioner_reference_aligned",
        "bundle.practitionerrole_organization_reference_aligned",
        "bundle.medicationrequest_subject_reference_aligned",
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
    if patient.get("active") is not True or not identifier_value or not patient_name_text:
        findings.append(
            _workflow_error(
                "bundle.patient_identity_content_present",
                "Bundle.entry[1].resource",
                "Expected Patient enriched content to include active=true, identifier[0].value, and name[0].text.",
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
    if practitioner.get("active") is not True or not practitioner_identifier_value or not practitioner_name_text:
        findings.append(
            _workflow_error(
                "bundle.practitioner_identity_content_present",
                "Bundle.entry[3].resource",
                "Expected Practitioner enriched content to include active=true, identifier[0].value, and name[0].text.",
            )
        )

    practitioner_role = _find_resource_by_type(bundle, "PractitionerRole")
    role_code = practitioner_role.get("code") if isinstance(practitioner_role, dict) else None
    role_text = (
        role_code[0].get("text")
        if isinstance(role_code, list) and role_code and isinstance(role_code[0], dict)
        else None
    )
    if role_text != "document-author":
        findings.append(
            _workflow_error(
                "bundle.practitionerrole_author_context_present",
                "Bundle.entry[2].resource.code[0].text",
                "Expected PractitionerRole to include the deterministic author-context label 'document-author'.",
            )
        )

    if not _medicationrequest_placeholder_content_present(bundle):
        findings.append(
            _workflow_error(
                "bundle.medicationrequest_placeholder_content_present",
                "Bundle.entry[5].resource",
                "Expected MedicationRequest placeholder content to include status='draft', intent='proposal', and medicationCodeableConcept.text.",
            )
        )

    if not _allergyintolerance_placeholder_content_present(bundle):
        findings.append(
            _workflow_error(
                "bundle.allergyintolerance_placeholder_content_present",
                "Bundle.entry[6].resource",
                "Expected AllergyIntolerance placeholder content to include fixed clinical/verification status codes and code.text.",
            )
        )

    if not _condition_placeholder_content_present(bundle):
        findings.append(
            _workflow_error(
                "bundle.condition_placeholder_content_present",
                "Bundle.entry[7].resource",
                "Expected Condition placeholder content to include fixed clinical/verification status codes and code.text.",
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
                    "section block with matching title, LOINC code, and first entry reference."
                ),
            )
        )

    if not _practitionerrole_practitioner_reference_aligned(bundle, full_urls_by_placeholder_id):
        findings.append(
            _workflow_error(
                "bundle.practitionerrole_practitioner_reference_aligned",
                "Bundle.entry[2].resource.practitioner.reference",
                "Expected PractitionerRole.practitioner.reference to align to the Practitioner bundle entry fullUrl.",
            )
        )

    if not _practitionerrole_organization_reference_aligned(bundle, full_urls_by_placeholder_id):
        findings.append(
            _workflow_error(
                "bundle.practitionerrole_organization_reference_aligned",
                "Bundle.entry[2].resource.organization.reference",
                "Expected PractitionerRole.organization.reference to align to the Organization bundle entry fullUrl.",
            )
        )

    if not _medicationrequest_subject_reference_aligned(bundle, full_urls_by_placeholder_id):
        findings.append(
            _workflow_error(
                "bundle.medicationrequest_subject_reference_aligned",
                "Bundle.entry[5].resource.subject.reference",
                "Expected MedicationRequest.subject.reference to align to the Patient bundle entry fullUrl.",
            )
        )

    if not _allergyintolerance_patient_reference_aligned(bundle, full_urls_by_placeholder_id):
        findings.append(
            _workflow_error(
                "bundle.allergyintolerance_patient_reference_aligned",
                "Bundle.entry[6].resource.patient.reference",
                "Expected AllergyIntolerance.patient.reference to align to the Patient bundle entry fullUrl.",
            )
        )

    if not _condition_subject_reference_aligned(bundle, full_urls_by_placeholder_id):
        findings.append(
            _workflow_error(
                "bundle.condition_subject_reference_aligned",
                "Bundle.entry[7].resource.subject.reference",
                "Expected Condition.subject.reference to align to the Patient bundle entry fullUrl.",
            )
        )

    section_entry_alignment_codes = {
        "medications": "bundle.composition_medications_section_entry_reference_aligned",
        "allergies": "bundle.composition_allergies_section_entry_reference_aligned",
        "problems": "bundle.composition_problems_section_entry_reference_aligned",
    }
    for section_scaffold in schematic.section_scaffolds:
        if _composition_section_entry_reference_aligned(
            sections,
            section_scaffold,
            full_urls_by_placeholder_id,
        ):
            continue
        findings.append(
            _workflow_error(
                section_entry_alignment_codes[section_scaffold.section_key],
                "Bundle.entry[0].resource.section.entry[0].reference",
                (
                    f"Expected the Composition '{section_scaffold.section_key}' section entry reference "
                    "to align exactly to the deterministic bundle entry fullUrl."
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
        first_entry = entry[0] if isinstance(entry, list) and entry else {}
        entry_reference = first_entry.get("reference") if isinstance(first_entry, dict) else None
        expected_reference = None
        if expected_entry_placeholder_ids:
            expected_reference = f"urn:uuid:"  # prefix match only after finalization
        if (
            title == expected_title
            and loinc_code == expected_code
            and isinstance(entry_reference, str)
            and bool(entry_reference)
            and (
                expected_reference is None
                or entry_reference.startswith(expected_reference)
            )
        ):
            return section
    return None


def _entry_fullurls_present(bundle: dict[str, object]) -> bool:
    entries = bundle.get("entry", [])
    if not isinstance(entries, list):
        return False
    return all(isinstance(entry, dict) and bool(entry.get("fullUrl")) for entry in entries)


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
) -> bool:
    medication = _find_resource_by_type(bundle, "MedicationRequest")
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
    expected_reference = _expected_full_url(
        full_urls_by_placeholder_id,
        section_scaffold.entry_placeholder_ids[0],
    )
    if expected_reference is None:
        return True
    entry_reference = _first_list_item(matching_section.get("entry"))
    actual_reference = entry_reference.get("reference") if isinstance(entry_reference, dict) else None
    if not isinstance(actual_reference, str) or not actual_reference or not actual_reference.startswith("urn:uuid:"):
        return True
    return actual_reference == expected_reference


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


def _medicationrequest_placeholder_content_present(bundle: dict[str, object]) -> bool:
    medication = _find_resource_by_type(bundle, "MedicationRequest")
    return (
        medication.get("status") == "draft"
        and medication.get("intent") == "proposal"
        and isinstance(medication.get("medicationCodeableConcept"), dict)
        and bool(medication["medicationCodeableConcept"].get("text"))
    )


def _allergyintolerance_placeholder_content_present(bundle: dict[str, object]) -> bool:
    allergy = _find_resource_by_type(bundle, "AllergyIntolerance")
    allergy_clinical = _first_coding(allergy.get("clinicalStatus"))
    allergy_verification = _first_coding(allergy.get("verificationStatus"))
    return (
        allergy_clinical.get("code") == "active"
        and allergy_verification.get("code") == "unconfirmed"
        and isinstance(allergy.get("code"), dict)
        and bool(allergy["code"].get("text"))
    )


def _condition_placeholder_content_present(bundle: dict[str, object]) -> bool:
    condition = _find_resource_by_type(bundle, "Condition")
    condition_clinical = _first_coding(condition.get("clinicalStatus"))
    condition_verification = _first_coding(condition.get("verificationStatus"))
    return (
        condition_clinical.get("code") == "active"
        and condition_verification.get("code") == "provisional"
        and isinstance(condition.get("code"), dict)
        and bool(condition["code"].get("text"))
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
