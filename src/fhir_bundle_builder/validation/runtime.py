"""Runtime standards-validator config and resolver helpers."""

from __future__ import annotations

import os

from .matchbox import (
    MatchboxStandardsValidator,
    MatchboxStandardsValidatorUnavailableError,
)
from .models import (
    StandardsValidationConfig,
    StandardsValidationRequest,
    StandardsValidationResult,
    ValidationFinding,
)
from .standards import (
    LocalCandidateBundleScaffoldStandardsValidator,
    StandardsValidator,
    status_from_findings,
)

ENV_VALIDATOR_MODE = "FHIR_BUNDLE_BUILDER_STANDARDS_VALIDATOR_MODE"
ENV_MATCHBOX_BASE_URL = "FHIR_BUNDLE_BUILDER_MATCHBOX_BASE_URL"
ENV_MATCHBOX_TIMEOUT_SECONDS = "FHIR_BUNDLE_BUILDER_MATCHBOX_TIMEOUT_SECONDS"


class MatchboxWithLocalFallbackStandardsValidator:
    """Attempt Matchbox first and fall back to local scaffold validation."""

    validator_id = "matchbox_with_local_fallback_standards_validator"

    def __init__(
        self,
        config: StandardsValidationConfig,
        matchbox_validator: StandardsValidator | None = None,
        local_validator: StandardsValidator | None = None,
    ) -> None:
        self._config = config
        self._matchbox_validator = matchbox_validator or MatchboxStandardsValidator(
            base_url=config.matchbox_base_url or "",
            timeout_seconds=config.timeout_seconds,
        )
        self._local_validator = local_validator or LocalCandidateBundleScaffoldStandardsValidator()

    async def validate(self, request: StandardsValidationRequest) -> StandardsValidationResult:
        if not self._config.matchbox_base_url:
            return await self._fallback_result(
                request,
                "Matchbox mode was requested but FHIR_BUNDLE_BUILDER_MATCHBOX_BASE_URL is not set.",
            )

        try:
            result = await self._matchbox_validator.validate(request)
        except MatchboxStandardsValidatorUnavailableError as exc:
            return await self._fallback_result(request, str(exc))

        return result.model_copy(
            update={
                "requested_validator_mode": "matchbox",
                "attempted_validator_ids": [self._matchbox_validator.validator_id],
                "external_validation_executed": True,
                "fallback_used": False,
            }
        )

    async def _fallback_result(
        self,
        request: StandardsValidationRequest,
        reason: str,
    ) -> StandardsValidationResult:
        local_result = await self._local_validator.validate(request)
        fallback_finding = ValidationFinding(
            channel="standards",
            severity="warning",
            code="matchbox.unavailable_fallback_local",
            location="Bundle",
            message=(
                "Matchbox validation could not be used, so the workflow fell back to the local "
                f"candidate bundle scaffold validator. Reason: {reason}"
            ),
        )
        findings = [*local_result.findings, fallback_finding]
        deferred_areas = [
            *local_result.deferred_areas,
            "Local fallback validation is not equivalent to external Matchbox profile/conformance validation.",
        ]
        return local_result.model_copy(
            update={
                "requested_validator_mode": "matchbox",
                "attempted_validator_ids": [
                    self._matchbox_validator.validator_id,
                    self._local_validator.validator_id,
                ],
                "external_validation_executed": False,
                "fallback_used": True,
                "status": status_from_findings(findings),
                "findings": findings,
                "deferred_areas": _dedupe(deferred_areas),
            }
        )


def load_standards_validation_config_from_env() -> StandardsValidationConfig:
    """Load the narrow runtime config for standards validation."""

    mode = os.getenv(ENV_VALIDATOR_MODE, "local_scaffold").strip() or "local_scaffold"
    if mode not in {"local_scaffold", "matchbox"}:
        mode = "local_scaffold"

    raw_timeout = os.getenv(ENV_MATCHBOX_TIMEOUT_SECONDS, "10.0").strip() or "10.0"
    try:
        timeout_seconds = float(raw_timeout)
    except ValueError:
        timeout_seconds = 10.0

    base_url = os.getenv(ENV_MATCHBOX_BASE_URL)
    return StandardsValidationConfig(
        mode=mode,
        matchbox_base_url=base_url.strip() if isinstance(base_url, str) and base_url.strip() else None,
        timeout_seconds=timeout_seconds,
    )


def build_standards_validator(config: StandardsValidationConfig) -> StandardsValidator:
    """Build the active runtime validator from the narrow config policy."""

    if config.mode == "matchbox":
        return MatchboxWithLocalFallbackStandardsValidator(config)
    return LocalCandidateBundleScaffoldStandardsValidator()


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered
