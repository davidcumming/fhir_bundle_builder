"""Direct tests for deterministic PS-CA repair execution."""

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
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.repair_execution_builder import (
    build_psca_repair_execution_result,
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


async def test_psca_repair_execution_happy_path_is_deferred_external_dependency() -> None:
    artifacts = await _build_repair_inputs()

    execution = await build_psca_repair_execution_result(
        artifacts["repair_decision"],
        artifacts["normalized_request"],
        artifacts["schematic"],
        artifacts["resource_construction"],
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert execution.execution_outcome == "deferred"
    assert execution.requested_target == "standards_validation_external"
    assert execution.retry_eligible is False
    assert execution.attempt_count == 0
    assert execution.rerun_stage_ids == []
    assert execution.post_retry_candidate_bundle is None


async def test_psca_repair_execution_reruns_bundle_finalization_once() -> None:
    artifacts = await _build_repair_inputs(mutator=_break_bundle_type)

    execution = await build_psca_repair_execution_result(
        artifacts["repair_decision"],
        artifacts["normalized_request"],
        artifacts["schematic"],
        artifacts["resource_construction"],
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert execution.execution_outcome == "executed"
    assert execution.requested_target == "bundle_finalization"
    assert execution.executed_target == "bundle_finalization"
    assert execution.retry_eligible is True
    assert execution.attempt_count == 1
    assert execution.rerun_stage_ids == ["bundle_finalization", "validation", "repair_decision"]
    assert execution.regenerated_artifact_keys == ["candidate_bundle", "validation_report", "repair_decision"]
    assert execution.post_retry_candidate_bundle is not None
    assert execution.post_retry_candidate_bundle.candidate_bundle.fhir_bundle["type"] == "document"
    assert execution.post_retry_validation_report is not None
    assert execution.post_retry_validation_report.overall_status == "passed_with_warnings"
    assert execution.post_retry_repair_decision is not None
    assert execution.post_retry_repair_decision.overall_decision == "external_validation_pending"


async def test_psca_repair_execution_marks_resource_construction_retry_as_unsupported() -> None:
    artifacts = await _build_repair_inputs(mutator=_remove_required_section)

    execution = await build_psca_repair_execution_result(
        artifacts["repair_decision"],
        artifacts["normalized_request"],
        artifacts["schematic"],
        artifacts["resource_construction"],
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert execution.execution_outcome == "unsupported"
    assert execution.requested_target == "resource_construction"
    assert execution.retry_eligible is False
    assert execution.attempt_count == 0
    assert execution.rerun_stage_ids == []
    assert execution.post_retry_candidate_bundle is None
    assert execution.unsupported_reason is not None


async def _build_repair_inputs(mutator=None):
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
            profile_id="patient-retry-test",
            display_name="Retry Test Patient",
        ),
        provider_profile=ProfileReferenceInput(
            profile_id="provider-retry-test",
            display_name="Retry Test Provider",
        ),
        request=BundleRequestInput(
            request_text="Create a deterministic repair execution test run.",
            scenario_label="pytest-retry",
        ),
        workflow_defaults=WorkflowDefaults(
            bundle_type="document",
            specification_mode="normalized-asset-foundation",
            validation_mode="foundational_dual_channel",
            resource_construction_mode="deterministic_content_enriched_foundation",
        ),
        run_label="pytest-retry:ca.infoway.io.psca:2.1.1-DFT",
    )
    resource_construction = build_psca_resource_construction_result(plan, schematic, normalized_request)
    candidate_bundle = build_psca_candidate_bundle_result(resource_construction, schematic, normalized_request)
    if mutator is not None:
        candidate_bundle = mutator(candidate_bundle)
    validation_report = await build_psca_validation_report(
        candidate_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
    )
    repair_decision = build_psca_repair_decision(validation_report)
    return {
        "normalized_request": normalized_request,
        "schematic": schematic,
        "resource_construction": resource_construction,
        "candidate_bundle": candidate_bundle,
        "validation_report": validation_report,
        "repair_decision": repair_decision,
    }


def _break_bundle_type(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    broken_bundle.candidate_bundle.fhir_bundle["type"] = "collection"
    return broken_bundle


def _remove_required_section(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    composition = broken_bundle.candidate_bundle.fhir_bundle["entry"][0]["resource"]
    composition["section"] = composition["section"][:2]
    return broken_bundle
