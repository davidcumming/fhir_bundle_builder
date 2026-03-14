"""Deterministic PS-CA repair decision and routing foundation."""

from __future__ import annotations

from fhir_bundle_builder.validation.models import ValidationFinding

from .models import (
    RepairDecisionEvidence,
    RepairDecisionResult,
    RepairFindingRoute,
    ResourceConstructionRepairDirective,
    ValidationReport,
)

_FINDING_ROUTE_MAP: dict[str, tuple[str, str, bool, str]] = {
    "external_profile_validation_deferred": (
        "standards_validation_external",
        "none",
        False,
        "External standards validation has not run yet; this is a dependency gap rather than an internal repair target.",
    ),
    "bundle.type_is_document": (
        "bundle_finalization",
        "bundle_finalization",
        True,
        "Bundle type is set during candidate bundle assembly, so repair should revisit bundle finalization.",
    ),
    "bundle.required_entries_present": (
        "bundle_finalization",
        "bundle_finalization",
        True,
        "Missing required entries indicate candidate bundle assembly needs to be corrected.",
    ),
    "bundle.identifier_present": (
        "bundle_finalization",
        "bundle_finalization",
        True,
        "Bundle identifier policy is applied during candidate bundle assembly.",
    ),
    "bundle.timestamp_present": (
        "bundle_finalization",
        "bundle_finalization",
        True,
        "Bundle timestamp policy is applied during candidate bundle assembly.",
    ),
    "bundle.entry_fullurls_present": (
        "bundle_finalization",
        "bundle_finalization",
        True,
        "Bundle entry fullUrls are assigned during candidate bundle assembly.",
    ),
    "bundle.composition_first_placeholder": (
        "bundle_finalization",
        "bundle_finalization",
        True,
        "Composition ordering is determined during bundle finalization.",
    ),
    "bundle.first_entry_is_composition": (
        "bundle_finalization",
        "bundle_finalization",
        True,
        "First-entry resource shape is determined during bundle finalization.",
    ),
    "bundle.composition_type_matches_psca_summary": (
        "resource_construction",
        "resource_construction",
        True,
        "Composition type coding originates in resource construction.",
    ),
    "bundle.composition_enriched_content_present": (
        "resource_construction",
        "resource_construction",
        True,
        "Composition deterministic content is populated during resource construction.",
    ),
    "bundle.patient_identity_content_present": (
        "resource_construction",
        "resource_construction",
        True,
        "Patient identity placeholder content is populated during resource construction.",
    ),
    "bundle.practitioner_identity_content_present": (
        "resource_construction",
        "resource_construction",
        True,
        "Practitioner identity placeholder content is populated during resource construction.",
    ),
    "bundle.practitionerrole_author_context_present": (
        "resource_construction",
        "resource_construction",
        True,
        "PractitionerRole author-context placeholder content is populated during resource construction.",
    ),
    "bundle.section_entry_content_present": (
        "resource_construction",
        "resource_construction",
        True,
        "Section-entry placeholder content is populated during resource construction.",
    ),
    "bundle.required_sections_present": (
        "resource_construction",
        "resource_construction",
        True,
        "Required Composition sections are attached during resource construction.",
    ),
    "bundle.references_aligned_to_entry_fullurls": (
        "bundle_finalization",
        "bundle_finalization",
        True,
        "Bundle reference alignment to deterministic fullUrls is performed during candidate bundle assembly.",
    ),
}

_TARGET_PRIORITY = {
    "build_plan_or_schematic": 0,
    "resource_construction": 1,
    "bundle_finalization": 2,
    "standards_validation_external": 3,
    "none_required": 4,
}

_RESOURCE_CONSTRUCTION_DIRECTIVE_MAP: dict[str, tuple[list[str], list[str], str]] = {
    "bundle.patient_identity_content_present": (
        ["build-patient-1"],
        ["patient-1"],
        "Rerun the patient anchor step to restore deterministic patient identity content.",
    ),
    "bundle.practitioner_identity_content_present": (
        ["build-practitioner-1"],
        ["practitioner-1"],
        "Rerun the practitioner support step to restore deterministic practitioner identity content.",
    ),
    "bundle.practitionerrole_author_context_present": (
        ["build-practitionerrole-1"],
        ["practitionerrole-1"],
        "Rerun the practitioner-role support step to restore the deterministic author-context label.",
    ),
    "bundle.composition_type_matches_psca_summary": (
        ["build-composition-1-scaffold", "finalize-composition-1"],
        ["composition-1"],
        "Rerun the composition scaffold and finalize steps to restore deterministic composition type and section attachment state.",
    ),
    "bundle.composition_enriched_content_present": (
        ["build-composition-1-scaffold", "finalize-composition-1"],
        ["composition-1"],
        "Rerun the composition scaffold and finalize steps to restore deterministic composition content and final section state.",
    ),
    "bundle.required_sections_present": (
        ["finalize-composition-1"],
        ["composition-1"],
        "Rerun composition finalization to reattach the deterministic required sections.",
    ),
    "bundle.section_entry_content_present": (
        [
            "build-medicationrequest-1",
            "build-allergyintolerance-1",
            "build-condition-1",
        ],
        ["medicationrequest-1", "allergyintolerance-1", "condition-1"],
        "Rerun the grouped section-entry construction steps because the current validation finding is still aggregated across all section-entry resources.",
    ),
}

_RESOURCE_CONSTRUCTION_STEP_ORDER = {
    "build-patient-1": 1,
    "build-practitioner-1": 2,
    "build-organization-1": 3,
    "build-practitionerrole-1": 4,
    "build-composition-1-scaffold": 5,
    "build-medicationrequest-1": 6,
    "build-allergyintolerance-1": 7,
    "build-condition-1": 8,
    "finalize-composition-1": 9,
}


def build_psca_repair_decision(validation_report: ValidationReport) -> RepairDecisionResult:
    """Build the first real repair-decision artifact from structured validation findings."""

    all_findings = [
        *validation_report.standards_validation.findings,
        *validation_report.workflow_validation.findings,
    ]
    finding_routes = [_route_finding(finding) for finding in all_findings]

    human_routes = [
        route
        for route in finding_routes
        if route.route_target == "human_intervention" and route.actionable
    ]
    internal_routes = [
        route
        for route in finding_routes
        if route.actionable and route.route_target in {"resource_construction", "bundle_finalization", "build_plan_or_schematic"}
    ]
    external_routes = [
        route
        for route in finding_routes
        if route.route_target == "standards_validation_external"
    ]

    if human_routes:
        overall_decision = "human_review_recommended"
        recommended_target = "human_intervention"
        recommended_next_stage = "none"
        rationale = "At least one validation finding could not be safely mapped to an internal repair layer, so human review is recommended."
    elif internal_routes:
        selected_route = min(internal_routes, key=lambda route: _TARGET_PRIORITY[route.route_target])
        overall_decision = "repair_recommended"
        recommended_target = selected_route.route_target
        recommended_next_stage = selected_route.recommended_next_stage
        rationale = (
            "Structured validation findings indicate an actionable internal repair target. "
            f"The smallest recommended stage to revisit is '{selected_route.recommended_next_stage}'."
        )
    elif external_routes:
        overall_decision = "external_validation_pending"
        recommended_target = "standards_validation_external"
        recommended_next_stage = "none"
        rationale = "No internal repair is currently recommended, but external standards validation is still pending."
    else:
        overall_decision = "complete_no_repair_needed"
        recommended_target = "none_required"
        recommended_next_stage = "none"
        rationale = "No actionable repair is currently recommended from the structured validation findings."

    recommended_resource_construction_repair_directive = None
    if recommended_target == "resource_construction":
        recommended_resource_construction_repair_directive = _build_resource_construction_repair_directive(
            finding_routes
        )

    return RepairDecisionResult(
        stage_id="repair_decision",
        status="placeholder_complete",
        summary="Derived a deterministic repair-routing recommendation from the structured validation report.",
        placeholder_note="This stage recommends the next workflow layer to revisit but does not execute any repair or retry behavior yet.",
        source_refs=validation_report.source_refs,
        overall_decision=overall_decision,
        recommended_target=recommended_target,
        recommended_next_stage=recommended_next_stage,
        recommended_resource_construction_repair_directive=recommended_resource_construction_repair_directive,
        finding_routes=finding_routes,
        deferred_external_dependencies=_dedupe(
            [
                route.reason
                for route in finding_routes
                if route.route_target == "standards_validation_external"
            ]
        ),
        evidence=RepairDecisionEvidence(
            source_validation_stage_id=validation_report.stage_id,
            source_overall_validation_status=validation_report.overall_status,
            routed_finding_codes=[route.finding_code for route in finding_routes],
            source_refs=validation_report.source_refs,
        ),
        rationale=rationale,
    )


def _route_finding(finding: ValidationFinding) -> RepairFindingRoute:
    mapped = _FINDING_ROUTE_MAP.get(finding.code)
    if mapped is not None:
        route_target, next_stage, actionable, reason = mapped
        return RepairFindingRoute(
            channel=finding.channel,
            severity=finding.severity,
            finding_code=finding.code,
            route_target=route_target,
            recommended_next_stage=next_stage,
            actionable=actionable,
            reason=reason,
        )

    if finding.code == "bundle.deferred_fields_recorded":
        if finding.severity == "warning":
            return RepairFindingRoute(
                channel=finding.channel,
                severity=finding.severity,
                finding_code=finding.code,
                route_target="bundle_finalization",
                recommended_next_stage="bundle_finalization",
                actionable=True,
                reason="Missing deferred-field tracking belongs to candidate bundle assembly.",
            )
        return RepairFindingRoute(
            channel=finding.channel,
            severity=finding.severity,
            finding_code=finding.code,
            route_target="none_required",
            recommended_next_stage="none",
            actionable=False,
            reason="Deferred bundle fields are explicitly recorded; no repair is needed for this informational finding.",
        )

    if finding.severity == "information":
        return RepairFindingRoute(
            channel=finding.channel,
            severity=finding.severity,
            finding_code=finding.code,
            route_target="none_required",
            recommended_next_stage="none",
            actionable=False,
            reason="Informational findings do not require repair routing in this slice.",
        )

    if finding.channel == "standards" and finding.severity == "warning":
        return RepairFindingRoute(
            channel=finding.channel,
            severity=finding.severity,
            finding_code=finding.code,
            route_target="standards_validation_external",
            recommended_next_stage="none",
            actionable=False,
            reason="Standards-channel warnings without a local internal mapping are treated as external validation dependencies.",
        )

    return RepairFindingRoute(
        channel=finding.channel,
        severity=finding.severity,
        finding_code=finding.code,
        route_target="human_intervention",
        recommended_next_stage="none",
        actionable=True,
        reason="This finding does not have a safe deterministic internal repair mapping in the current slice.",
    )


def _build_resource_construction_repair_directive(
    finding_routes: list[RepairFindingRoute],
) -> ResourceConstructionRepairDirective | None:
    target_routes = [
        route
        for route in finding_routes
        if route.actionable and route.route_target == "resource_construction"
    ]
    if not target_routes:
        return None

    trigger_finding_codes: list[str] = []
    target_step_ids: list[str] = []
    target_placeholder_ids: list[str] = []
    rationale_parts: list[str] = []
    for route in target_routes:
        mapped = _RESOURCE_CONSTRUCTION_DIRECTIVE_MAP.get(route.finding_code)
        if mapped is None:
            continue
        step_ids, placeholder_ids, rationale = mapped
        if route.finding_code not in trigger_finding_codes:
            trigger_finding_codes.append(route.finding_code)
        for step_id in step_ids:
            if step_id not in target_step_ids:
                target_step_ids.append(step_id)
        for placeholder_id in placeholder_ids:
            if placeholder_id not in target_placeholder_ids:
                target_placeholder_ids.append(placeholder_id)
        if rationale not in rationale_parts:
            rationale_parts.append(rationale)

    if not target_step_ids:
        return None

    target_step_ids.sort(key=lambda step_id: _RESOURCE_CONSTRUCTION_STEP_ORDER[step_id])

    return ResourceConstructionRepairDirective(
        directive_basis="validation_finding_code_map",
        scope="build_step_subset",
        trigger_finding_codes=trigger_finding_codes,
        target_step_ids=target_step_ids,
        target_placeholder_ids=target_placeholder_ids,
        rationale=" ".join(rationale_parts),
    )


def _dedupe(values: list[str]) -> list[str]:
    ordered: list[str] = []
    for value in values:
        if value not in ordered:
            ordered.append(value)
    return ordered
