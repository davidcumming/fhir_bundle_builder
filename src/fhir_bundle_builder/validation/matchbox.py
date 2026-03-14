"""Matchbox-backed standards validation adapter."""

from __future__ import annotations

from typing import Any

import httpx

from .models import (
    StandardsValidationRequest,
    StandardsValidationResult,
    ValidationFinding,
)
from .standards import status_from_findings


class MatchboxStandardsValidatorUnavailableError(RuntimeError):
    """Raised when Matchbox cannot be used for transport/config reasons."""


class MatchboxStandardsValidator:
    """Narrow Matchbox adapter behind the standards-validator protocol."""

    validator_id = "matchbox_standards_validator"

    def __init__(self, base_url: str, timeout_seconds: float = 10.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    async def validate(self, request: StandardsValidationRequest) -> StandardsValidationResult:
        if not self._base_url:
            raise MatchboxStandardsValidatorUnavailableError(
                "Matchbox base URL is not configured."
            )

        payload = await self._post_validate(request)
        findings = _parse_matchbox_payload(payload)

        return StandardsValidationResult(
            validator_id=self.validator_id,
            status=status_from_findings(findings),
            requested_validator_mode="matchbox",
            attempted_validator_ids=[self.validator_id],
            external_validation_executed=True,
            fallback_used=False,
            checks_run=["matchbox.fhir_validate_operation"],
            findings=findings,
            deferred_areas=[],
        )

    async def _post_validate(self, request: StandardsValidationRequest) -> Any:
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(
                    f"{self._base_url}/$validate",
                    params={
                        "profile": request.bundle_profile_url,
                        "ig": f"{request.specification_package_id}#{request.specification_version}",
                    },
                    headers={
                        "Accept": "application/fhir+json",
                        "Content-Type": "application/fhir+json",
                    },
                    json=request.bundle_json,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as exc:
            raise MatchboxStandardsValidatorUnavailableError(
                f"Matchbox request failed: {exc}"
            ) from exc
        except ValueError as exc:
            raise MatchboxStandardsValidatorUnavailableError(
                "Matchbox returned an unparseable response payload."
            ) from exc


def _parse_matchbox_payload(payload: Any) -> list[ValidationFinding]:
    outcomes: list[dict[str, Any]]
    if isinstance(payload, dict):
        outcomes = [payload]
    elif isinstance(payload, list):
        outcomes = [item for item in payload if isinstance(item, dict)]
        if len(outcomes) != len(payload):
            raise MatchboxStandardsValidatorUnavailableError(
                "Matchbox returned a payload list containing non-object items."
            )
    else:
        raise MatchboxStandardsValidatorUnavailableError(
            "Matchbox returned an unsupported response payload shape."
        )

    findings: list[ValidationFinding] = []
    for outcome_index, outcome in enumerate(outcomes):
        if outcome.get("resourceType") not in {None, "OperationOutcome"} and "issue" not in outcome:
            raise MatchboxStandardsValidatorUnavailableError(
                "Matchbox returned a non-OperationOutcome payload."
            )
        issues = outcome.get("issue", [])
        if not isinstance(issues, list):
            raise MatchboxStandardsValidatorUnavailableError(
                "Matchbox OperationOutcome.issue was not a list."
            )
        for issue_index, issue in enumerate(issues):
            if not isinstance(issue, dict):
                raise MatchboxStandardsValidatorUnavailableError(
                    "Matchbox OperationOutcome.issue contained a non-object item."
                )
            findings.append(
                ValidationFinding(
                    channel="standards",
                    severity=_map_issue_severity(issue.get("severity")),
                    code=_issue_code(issue),
                    location=_issue_location(issue, outcome_index, issue_index),
                    message=_issue_message(issue, issue_index),
                )
            )
    return findings


def _map_issue_severity(raw_severity: Any) -> str:
    if raw_severity in {"fatal", "error"}:
        return "error"
    if raw_severity == "warning":
        return "warning"
    return "information"


def _issue_code(issue: dict[str, Any]) -> str:
    code = issue.get("code")
    if isinstance(code, str) and code:
        return f"matchbox.{code}"
    return "matchbox.issue"


def _issue_location(issue: dict[str, Any], outcome_index: int, issue_index: int) -> str:
    expression = issue.get("expression")
    if isinstance(expression, list) and expression and isinstance(expression[0], str) and expression[0]:
        return expression[0]
    location = issue.get("location")
    if isinstance(location, list) and location and isinstance(location[0], str) and location[0]:
        return location[0]
    return f"OperationOutcome[{outcome_index}].issue[{issue_index}]"


def _issue_message(issue: dict[str, Any], issue_index: int) -> str:
    diagnostics = issue.get("diagnostics")
    if isinstance(diagnostics, str) and diagnostics:
        return diagnostics
    details = issue.get("details")
    if isinstance(details, dict):
        text = details.get("text")
        if isinstance(text, str) and text:
            return text
    return f"Matchbox reported validation issue {issue_index}."
