"""Direct tests for Matchbox-backed standards validation."""

from __future__ import annotations

from typing import Any

import pytest

from fhir_bundle_builder.validation import (
    LocalCandidateBundleScaffoldStandardsValidator,
    MatchboxStandardsValidator,
    MatchboxStandardsValidatorUnavailableError,
    MatchboxWithLocalFallbackStandardsValidator,
    StandardsValidationConfig,
    StandardsValidationRequest,
)


async def test_matchbox_standards_validator_maps_operation_outcome(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> Any:
            return {
                "resourceType": "OperationOutcome",
                "issue": [
                    {
                        "severity": "warning",
                        "code": "structure",
                        "expression": ["Bundle.entry[0].resource"],
                        "diagnostics": "Example warning from Matchbox.",
                    },
                    {
                        "severity": "information",
                        "code": "informational",
                        "details": {"text": "Example informational note."},
                    },
                ],
            }

    class FakeAsyncClient:
        def __init__(self, timeout: float) -> None:
            captured["timeout"] = timeout

        async def __aenter__(self) -> FakeAsyncClient:
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, *, params: dict[str, str], headers: dict[str, str], json: dict[str, Any]) -> FakeResponse:
            captured["url"] = url
            captured["params"] = params
            captured["headers"] = headers
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr("fhir_bundle_builder.validation.matchbox.httpx.AsyncClient", FakeAsyncClient)

    request = StandardsValidationRequest(
        bundle_id="bundle-1",
        bundle_json={"resourceType": "Bundle", "id": "bundle-1"},
        bundle_profile_url="http://example.org/StructureDefinition/test-bundle",
        specification_package_id="ca.infoway.io.psca",
        specification_version="2.1.1-DFT",
    )

    result = await MatchboxStandardsValidator(
        base_url="https://matchbox.example/fhir",
        timeout_seconds=3.5,
    ).validate(request)

    assert captured["url"] == "https://matchbox.example/fhir/$validate"
    assert captured["params"] == {
        "profile": "http://example.org/StructureDefinition/test-bundle",
        "ig": "ca.infoway.io.psca#2.1.1-DFT",
    }
    assert captured["headers"]["Accept"] == "application/fhir+json"
    assert captured["json"] == {"resourceType": "Bundle", "id": "bundle-1"}
    assert result.validator_id == "matchbox_standards_validator"
    assert result.requested_validator_mode == "matchbox"
    assert result.attempted_validator_ids == ["matchbox_standards_validator"]
    assert result.external_validation_executed is True
    assert result.fallback_used is False
    assert result.status == "passed_with_warnings"
    assert result.findings[0].code == "matchbox.structure"
    assert result.findings[0].location == "Bundle.entry[0].resource"
    assert result.findings[1].message == "Example informational note."


async def test_matchbox_runtime_falls_back_to_local_scaffold_validator() -> None:
    class FailingMatchboxValidator:
        validator_id = "matchbox_standards_validator"

        async def validate(self, request: StandardsValidationRequest):
            raise MatchboxStandardsValidatorUnavailableError("Matchbox timed out.")

    validator = MatchboxWithLocalFallbackStandardsValidator(
        StandardsValidationConfig(
            mode="matchbox",
            matchbox_base_url="https://matchbox.example/fhir",
            timeout_seconds=5.0,
        ),
        matchbox_validator=FailingMatchboxValidator(),
        local_validator=LocalCandidateBundleScaffoldStandardsValidator(),
    )

    result = await validator.validate(
        StandardsValidationRequest(
            bundle_id="bundle-1",
            bundle_json={
                "resourceType": "Bundle",
                "id": "bundle-1",
                "identifier": {"system": "urn:test", "value": "bundle-1"},
                "timestamp": "2025-01-01T00:00:00Z",
                "meta": {"profile": ["http://example.org/StructureDefinition/test-bundle"]},
                "type": "document",
                "entry": [
                    {
                        "fullUrl": "urn:uuid:entry-1",
                        "resource": {"resourceType": "Patient", "id": "patient-1"},
                    }
                ],
            },
            bundle_profile_url="http://example.org/StructureDefinition/test-bundle",
            specification_package_id="ca.infoway.io.psca",
            specification_version="2.1.1-DFT",
        )
    )

    assert result.validator_id == "local_candidate_bundle_scaffold_validator"
    assert result.requested_validator_mode == "matchbox"
    assert result.attempted_validator_ids == [
        "matchbox_standards_validator",
        "local_candidate_bundle_scaffold_validator",
    ]
    assert result.external_validation_executed is False
    assert result.fallback_used is True
    assert any(
        finding.code == "matchbox.unavailable_fallback_local"
        for finding in result.findings
    )
    assert any(
        finding.code == "external_profile_validation_deferred"
        for finding in result.findings
    )
    assert any(
        "not equivalent to external Matchbox profile/conformance validation"
        in area
        for area in result.deferred_areas
    )


async def test_local_scaffold_validator_flags_duplicate_entry_fullurls() -> None:
    result = await LocalCandidateBundleScaffoldStandardsValidator().validate(
        StandardsValidationRequest(
            bundle_id="bundle-dup-fullurl",
            bundle_json={
                "resourceType": "Bundle",
                "id": "bundle-dup-fullurl",
                "identifier": {"system": "urn:test", "value": "bundle-dup-fullurl"},
                "timestamp": "2025-01-01T00:00:00Z",
                "meta": {"profile": ["http://example.org/StructureDefinition/test-bundle"]},
                "type": "document",
                "entry": [
                    {
                        "fullUrl": "urn:uuid:dup",
                        "resource": {"resourceType": "MedicationRequest", "id": "medicationrequest-1"},
                    },
                    {
                        "fullUrl": "urn:uuid:dup",
                        "resource": {"resourceType": "MedicationRequest", "id": "medicationrequest-2"},
                    },
                ],
            },
            bundle_profile_url="http://example.org/StructureDefinition/test-bundle",
            specification_package_id="ca.infoway.io.psca",
            specification_version="2.1.1-DFT",
        )
    )

    assert any(
        finding.code == "bundle.entry_fullurls_unique" and finding.severity == "error"
        for finding in result.findings
    )


async def test_local_scaffold_validator_flags_duplicate_entry_resource_ids() -> None:
    result = await LocalCandidateBundleScaffoldStandardsValidator().validate(
        StandardsValidationRequest(
            bundle_id="bundle-dup-id",
            bundle_json={
                "resourceType": "Bundle",
                "id": "bundle-dup-id",
                "identifier": {"system": "urn:test", "value": "bundle-dup-id"},
                "timestamp": "2025-01-01T00:00:00Z",
                "meta": {"profile": ["http://example.org/StructureDefinition/test-bundle"]},
                "type": "document",
                "entry": [
                    {
                        "fullUrl": "urn:uuid:med-1",
                        "resource": {"resourceType": "MedicationRequest", "id": "medicationrequest-1"},
                    },
                    {
                        "fullUrl": "urn:uuid:med-2",
                        "resource": {"resourceType": "MedicationRequest", "id": "medicationrequest-1"},
                    },
                ],
            },
            bundle_profile_url="http://example.org/StructureDefinition/test-bundle",
            specification_package_id="ca.infoway.io.psca",
            specification_version="2.1.1-DFT",
        )
    )

    assert any(
        finding.code == "bundle.entry_resource_ids_unique" and finding.severity == "error"
        for finding in result.findings
    )
