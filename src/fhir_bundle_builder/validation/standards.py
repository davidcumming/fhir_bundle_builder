"""Pluggable standards validation interface and local scaffold validator."""

from __future__ import annotations

from typing import Protocol

from .models import (
    StandardsValidationRequest,
    StandardsValidationResult,
    ValidationFinding,
)


class StandardsValidator(Protocol):
    """Minimal async validator boundary for standards/profile validation."""

    validator_id: str

    async def validate(self, request: StandardsValidationRequest) -> StandardsValidationResult:
        """Validate the given bundle request."""


class LocalCandidateBundleScaffoldStandardsValidator:
    """Local narrow validator for candidate bundle scaffold shape only."""

    validator_id = "local_candidate_bundle_scaffold_validator"

    async def validate(self, request: StandardsValidationRequest) -> StandardsValidationResult:
        findings: list[ValidationFinding] = []
        bundle = request.bundle_json

        self._require(bundle.get("resourceType") == "Bundle", findings, "bundle.resource_type", "Bundle", "Expected Bundle.resourceType to equal 'Bundle'.")
        self._require(bool(bundle.get("id")), findings, "bundle.id_present", "Bundle.id", "Expected Bundle.id to be present.")

        meta = bundle.get("meta")
        profile = meta.get("profile", []) if isinstance(meta, dict) else []
        self._require(
            isinstance(profile, list) and bool(profile) and isinstance(profile[0], str) and bool(profile[0]),
            findings,
            "bundle.meta_profile_present",
            "Bundle.meta.profile[0]",
            "Expected Bundle.meta.profile[0] to be present.",
        )
        self._require(bool(bundle.get("type")), findings, "bundle.type_present", "Bundle.type", "Expected Bundle.type to be present.")

        entries = bundle.get("entry")
        entries_is_list = isinstance(entries, list)
        self._require(entries_is_list, findings, "bundle.entry_list", "Bundle.entry", "Expected Bundle.entry to be present as a list.")

        if entries_is_list:
            for index, entry in enumerate(entries):
                resource = entry.get("resource") if isinstance(entry, dict) else None
                self._require(
                    isinstance(resource, dict) and bool(resource.get("resourceType")),
                    findings,
                    "bundle.entry_resource_type_present",
                    f"Bundle.entry[{index}].resource.resourceType",
                    "Expected Bundle.entry resourceType to be present.",
                )
                self._require(
                    isinstance(resource, dict) and bool(resource.get("id")),
                    findings,
                    "bundle.entry_resource_id_present",
                    f"Bundle.entry[{index}].resource.id",
                    "Expected Bundle.entry resource id to be present.",
                )

        findings.append(
            ValidationFinding(
                channel="standards",
                severity="warning",
                code="external_profile_validation_deferred",
                location="Bundle",
                message="External standards/profile validation was not executed in this slice; only local candidate bundle scaffold checks ran.",
            )
        )

        return StandardsValidationResult(
            validator_id=self.validator_id,
            status=_status_from_findings(findings),
            checks_run=[
                "bundle.resource_type",
                "bundle.id_present",
                "bundle.meta_profile_present",
                "bundle.type_present",
                "bundle.entry_list",
                "bundle.entry_resource_type_present",
                "bundle.entry_resource_id_present",
            ],
            findings=findings,
            deferred_areas=[
                "Full profile/conformance validation is deferred to a later external validator implementation.",
                "Terminology, invariants, and slicing/cardinality validation are deferred.",
            ],
        )

    def _require(
        self,
        condition: bool,
        findings: list[ValidationFinding],
        code: str,
        location: str,
        message: str,
    ) -> None:
        if not condition:
            findings.append(
                ValidationFinding(
                    channel="standards",
                    severity="error",
                    code=code,
                    location=location,
                    message=message,
                )
            )


def _status_from_findings(findings: list[ValidationFinding]) -> str:
    if any(finding.severity == "error" for finding in findings):
        return "failed"
    if any(finding.severity == "warning" for finding in findings):
        return "passed_with_warnings"
    return "passed"
