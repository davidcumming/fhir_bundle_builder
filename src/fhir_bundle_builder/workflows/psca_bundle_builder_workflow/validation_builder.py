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
        placeholder_note="This slice adds real validation structure, but full external profile/conformance validation and repair routing remain deferred.",
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
        "bundle.composition_first_placeholder",
        "bundle.first_entry_is_composition",
        "bundle.composition_type_matches_psca_summary",
        "bundle.required_sections_present",
        "bundle.deferred_fields_recorded",
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

    missing_sections: list[str] = []
    sections = composition.get("section", []) if isinstance(composition, dict) else []
    for section_scaffold in schematic.section_scaffolds:
        if not _has_matching_section(sections, section_scaffold.title, section_scaffold.loinc_code):
            missing_sections.append(section_scaffold.section_key)
    if missing_sections:
        findings.append(
            _workflow_error(
                "bundle.required_sections_present",
                "Bundle.entry[0].resource.section",
                f"Missing required Composition sections: {', '.join(missing_sections)}.",
            )
        )

    expected_deferred = {"identifier", "timestamp", "entry.fullUrl"}
    deferred_paths = set(candidate_bundle.candidate_bundle.deferred_paths)
    missing_deferred = sorted(expected_deferred - deferred_paths)
    if missing_deferred:
        findings.append(
            ValidationFinding(
                channel="workflow",
                severity="warning",
                code="bundle.deferred_fields_recorded",
                location="CandidateBundleArtifact.deferred_paths",
                message=f"Expected deferred bundle fields are missing from deferred_paths: {', '.join(missing_deferred)}.",
            )
        )
    else:
        findings.append(
            ValidationFinding(
                channel="workflow",
                severity="information",
                code="bundle.deferred_fields_recorded",
                location="CandidateBundleArtifact.deferred_paths",
                message="Expected deferred bundle fields are explicitly recorded for identifier, timestamp, and entry.fullUrl.",
            )
        )

    return WorkflowValidationResult(
        status=_status_from_findings(findings),
        checks_run=checks_run,
        findings=findings,
        deferred_areas=[
            "Repair-routing decisions are deferred to a later slice.",
            "No terminology or full external conformance validation is performed in workflow-rule validation.",
        ],
    )


def _find_composition_resource(bundle: dict[str, object]) -> dict[str, object]:
    entries = bundle.get("entry", [])
    if not isinstance(entries, list):
        return {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        resource = entry.get("resource")
        if isinstance(resource, dict) and resource.get("resourceType") == "Composition":
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


def _has_matching_section(sections: object, expected_title: str, expected_code: str) -> bool:
    if not isinstance(sections, list):
        return False
    for section in sections:
        if not isinstance(section, dict):
            continue
        title = section.get("title")
        code = section.get("code")
        coding = code.get("coding", []) if isinstance(code, dict) else []
        first_coding = coding[0] if isinstance(coding, list) and coding else {}
        loinc_code = first_coding.get("code") if isinstance(first_coding, dict) else None
        if title == expected_title and loinc_code == expected_code:
            return True
    return False


def _workflow_error(code: str, location: str, message: str) -> ValidationFinding:
    return ValidationFinding(
        channel="workflow",
        severity="error",
        code=code,
        location=location,
        message=message,
    )


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
