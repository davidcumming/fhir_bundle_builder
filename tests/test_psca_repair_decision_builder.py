"""Direct tests for deterministic PS-CA repair routing."""

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
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.repair_decision_builder import (
    build_psca_repair_decision,
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


async def test_psca_repair_decision_happy_path_routes_to_external_validation_pending() -> None:
    report = await _build_validation_report()

    decision = build_psca_repair_decision(report)

    assert decision.overall_decision == "external_validation_pending"
    assert decision.recommended_target == "standards_validation_external"
    assert decision.recommended_next_stage == "none"
    assert any(
        route.finding_code == "external_profile_validation_deferred"
        and route.route_target == "standards_validation_external"
        and route.actionable is False
        for route in decision.finding_routes
    )
    assert any(
        route.finding_code == "bundle.deferred_fields_recorded"
        and route.route_target == "none_required"
        and route.actionable is False
        for route in decision.finding_routes
    )


async def test_psca_repair_decision_routes_missing_sections_to_resource_construction() -> None:
    report = await _build_validation_report(mutator=_remove_required_section)

    decision = build_psca_repair_decision(report)

    assert decision.overall_decision == "repair_recommended"
    assert decision.recommended_target == "resource_construction"
    assert decision.recommended_next_stage == "resource_construction"
    assert any(
        route.finding_code == "bundle.required_sections_present"
        and route.route_target == "resource_construction"
        and route.actionable is True
        for route in decision.finding_routes
    )


async def test_psca_repair_decision_routes_bundle_shape_errors_to_bundle_finalization() -> None:
    report = await _build_validation_report(mutator=_break_bundle_type)

    decision = build_psca_repair_decision(report)

    assert decision.overall_decision == "repair_recommended"
    assert decision.recommended_target == "bundle_finalization"
    assert decision.recommended_next_stage == "bundle_finalization"
    assert any(
        route.finding_code == "bundle.type_is_document"
        and route.route_target == "bundle_finalization"
        and route.actionable is True
        for route in decision.finding_routes
    )


async def _build_validation_report(mutator=None):
    repository = PscaAssetRepository()
    normalized_assets = repository.load_foundation_context(PscaAssetQuery())
    schematic = build_psca_bundle_schematic(normalized_assets)
    plan = build_psca_build_plan(schematic)
    construction = build_psca_resource_construction_result(plan, schematic)
    normalized_request = NormalizedBuildRequest(
        stage_id="request_normalization",
        status="placeholder_complete",
        summary="Test normalized request.",
        placeholder_note="Test artifact.",
        source_refs=[],
        specification=SpecificationSelection(),
        patient_profile=ProfileReferenceInput(
            profile_id="patient-repair-test",
            display_name="Repair Test Patient",
        ),
        provider_profile=ProfileReferenceInput(
            profile_id="provider-repair-test",
            display_name="Repair Test Provider",
        ),
        request=BundleRequestInput(
            request_text="Create a deterministic repair decision for testing.",
            scenario_label="pytest-repair",
        ),
        workflow_defaults=WorkflowDefaults(
            bundle_type="document",
            specification_mode="normalized-asset-foundation",
            validation_mode="foundational_dual_channel",
            resource_construction_mode="scaffold_only_foundation",
        ),
        run_label="pytest-repair:ca.infoway.io.psca:2.1.1-DFT",
    )
    candidate_bundle = build_psca_candidate_bundle_result(construction, schematic, normalized_request)
    if mutator is not None:
        candidate_bundle = mutator(candidate_bundle)
    return await build_psca_validation_report(
        candidate_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )


def _remove_required_section(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    composition = broken_bundle.candidate_bundle.fhir_bundle["entry"][0]["resource"]
    composition["section"] = composition["section"][:2]
    return broken_bundle


def _break_bundle_type(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    broken_bundle.candidate_bundle.fhir_bundle["type"] = "collection"
    return broken_bundle
