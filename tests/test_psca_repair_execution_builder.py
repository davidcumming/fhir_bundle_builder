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
    PatientContextInput,
    PatientIdentityInput,
    PatientMedicationInput,
    ProfileReferenceInput,
    ProviderContextInput,
    ProviderIdentityInput,
    ProviderOrganizationInput,
    ProviderRoleRelationshipInput,
    RepairDecisionEvidence,
    RepairDecisionResult,
    SpecificationSelection,
    WorkflowBuildInput,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.repair_decision_builder import (
    build_psca_repair_decision,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.repair_execution_builder import (
    build_psca_repair_execution_result,
    build_psca_workflow_effective_outcome,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.request_normalization_builder import (
    build_psca_normalized_request,
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
        artifacts["build_plan"],
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

    effective_outcome = build_psca_workflow_effective_outcome(
        resource_construction=artifacts["resource_construction"],
        candidate_bundle=artifacts["candidate_bundle"],
        validation_report=artifacts["validation_report"],
        repair_decision=artifacts["repair_decision"],
        repair_execution=execution,
    )

    assert effective_outcome.artifact_source == "initial_run"
    assert effective_outcome.resource_construction == artifacts["resource_construction"]
    assert effective_outcome.candidate_bundle == artifacts["candidate_bundle"]
    assert effective_outcome.validation_report == artifacts["validation_report"]
    assert effective_outcome.repair_decision == artifacts["repair_decision"]


async def test_psca_repair_execution_reruns_bundle_finalization_once() -> None:
    artifacts = await _build_repair_inputs(mutator=_break_bundle_type)

    execution = await build_psca_repair_execution_result(
        artifacts["repair_decision"],
        artifacts["normalized_request"],
        artifacts["build_plan"],
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
    assert execution.post_retry_resource_construction is None
    assert execution.post_retry_candidate_bundle is not None
    assert execution.post_retry_candidate_bundle.candidate_bundle.fhir_bundle["type"] == "document"
    assert execution.post_retry_validation_report is not None
    assert execution.post_retry_validation_report.overall_status == "passed_with_warnings"
    assert execution.post_retry_repair_decision is not None
    assert execution.post_retry_repair_decision.overall_decision == "external_validation_pending"


async def test_psca_repair_execution_reruns_only_bundle_finalization_for_medication_bundle_entry_plan_alignment_failure() -> None:
    artifacts = await _build_repair_inputs(
        mutator=_swap_medication_bundle_entries,
        medication_texts=[
            "Atorvastatin 20 MG oral tablet",
            "Metformin 500 MG oral tablet",
        ],
    )

    execution = await build_psca_repair_execution_result(
        artifacts["repair_decision"],
        artifacts["normalized_request"],
        artifacts["build_plan"],
        artifacts["schematic"],
        artifacts["resource_construction"],
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert execution.execution_outcome == "executed"
    assert execution.requested_target == "bundle_finalization"
    assert execution.executed_target == "bundle_finalization"
    assert execution.rerun_stage_ids == ["bundle_finalization", "validation", "repair_decision"]
    assert execution.post_retry_validation_report is not None
    assert execution.post_retry_validation_report.overall_status == "passed_with_warnings"


async def test_psca_repair_execution_reruns_only_bundle_finalization_for_duplicate_entry_fullurl() -> None:
    artifacts = await _build_repair_inputs(mutator=_duplicate_bundle_entry_fullurl)

    execution = await build_psca_repair_execution_result(
        artifacts["repair_decision"],
        artifacts["normalized_request"],
        artifacts["build_plan"],
        artifacts["schematic"],
        artifacts["resource_construction"],
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert execution.execution_outcome == "executed"
    assert execution.requested_target == "bundle_finalization"
    assert execution.executed_target == "bundle_finalization"
    assert execution.rerun_stage_ids == ["bundle_finalization", "validation", "repair_decision"]
    assert execution.post_retry_validation_report is not None
    assert execution.post_retry_validation_report.overall_status == "passed_with_warnings"


async def test_psca_repair_execution_reruns_resource_construction_once() -> None:
    artifacts = await _build_repair_inputs(mutator=_remove_required_section)

    execution = await build_psca_repair_execution_result(
        artifacts["repair_decision"],
        artifacts["normalized_request"],
        artifacts["build_plan"],
        artifacts["schematic"],
        artifacts["resource_construction"],
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert execution.execution_outcome == "executed"
    assert execution.requested_target == "resource_construction"
    assert execution.executed_target == "resource_construction"
    assert execution.retry_eligible is True
    assert execution.attempt_count == 1
    assert execution.rerun_stage_ids == [
        "resource_construction",
        "bundle_finalization",
        "validation",
        "repair_decision",
    ]
    assert execution.regenerated_artifact_keys == [
        "resource_construction",
        "candidate_bundle",
        "validation_report",
        "repair_decision",
    ]
    assert execution.applied_resource_construction_repair_directive is not None
    assert execution.applied_resource_construction_repair_directive.target_step_ids == [
        "finalize-composition-1-problems-section"
    ]
    assert execution.post_retry_resource_construction is not None
    assert execution.post_retry_resource_construction.execution_scope == "targeted_repair"
    assert execution.post_retry_resource_construction.applied_repair_directive is not None
    assert [step.step_id for step in execution.post_retry_resource_construction.step_results] == [
        "finalize-composition-1-problems-section"
    ]
    assert execution.post_retry_resource_construction.regenerated_placeholder_ids == [
        "composition-1"
    ]
    assert execution.post_retry_resource_construction.resource_registry != []
    assert execution.post_retry_candidate_bundle is not None
    assert execution.post_retry_validation_report is not None
    assert execution.post_retry_validation_report.overall_status == "passed_with_warnings"
    assert execution.post_retry_repair_decision is not None
    assert execution.post_retry_repair_decision.overall_decision == "external_validation_pending"

    effective_outcome = build_psca_workflow_effective_outcome(
        resource_construction=artifacts["resource_construction"],
        candidate_bundle=artifacts["candidate_bundle"],
        validation_report=artifacts["validation_report"],
        repair_decision=artifacts["repair_decision"],
        repair_execution=execution,
    )

    assert effective_outcome.artifact_source == "post_retry"
    assert effective_outcome.resource_construction == execution.post_retry_resource_construction
    assert effective_outcome.candidate_bundle == execution.post_retry_candidate_bundle
    assert effective_outcome.validation_report == execution.post_retry_validation_report
    assert effective_outcome.repair_decision == execution.post_retry_repair_decision


async def test_psca_repair_execution_reruns_patient_step_for_patient_context_identity_alignment_failure() -> None:
    artifacts = await _build_repair_inputs(mutator=_misalign_patient_identity)

    execution = await build_psca_repair_execution_result(
        artifacts["repair_decision"],
        artifacts["normalized_request"],
        artifacts["build_plan"],
        artifacts["schematic"],
        artifacts["resource_construction"],
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert execution.execution_outcome == "executed"
    assert execution.requested_target == "resource_construction"
    assert execution.executed_target == "resource_construction"
    assert execution.applied_resource_construction_repair_directive is not None
    assert execution.applied_resource_construction_repair_directive.target_step_ids == [
        "build-patient-1"
    ]
    assert execution.applied_resource_construction_repair_directive.target_placeholder_ids == [
        "patient-1"
    ]
    assert execution.post_retry_validation_report is not None
    assert execution.post_retry_validation_report.overall_status == "passed_with_warnings"


async def test_psca_repair_execution_reruns_second_medication_step_for_patient_context_text_alignment_failure() -> None:
    artifacts = await _build_repair_inputs(
        mutator=_misalign_second_medication_text,
        medication_texts=[
            "Atorvastatin 20 MG oral tablet",
            "Metformin 500 MG oral tablet",
        ],
    )

    execution = await build_psca_repair_execution_result(
        artifacts["repair_decision"],
        artifacts["normalized_request"],
        artifacts["build_plan"],
        artifacts["schematic"],
        artifacts["resource_construction"],
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert execution.execution_outcome == "executed"
    assert execution.requested_target == "resource_construction"
    assert execution.executed_target == "resource_construction"
    assert execution.applied_resource_construction_repair_directive is not None
    assert execution.applied_resource_construction_repair_directive.target_step_ids == [
        "build-medicationrequest-2"
    ]
    assert execution.applied_resource_construction_repair_directive.target_placeholder_ids == [
        "medicationrequest-2"
    ]
    assert execution.post_retry_validation_report is not None
    assert execution.post_retry_validation_report.overall_status == "passed_with_warnings"


async def test_psca_repair_execution_reruns_only_missing_composition_section_steps_when_multiple_sections_fail() -> None:
    artifacts = await _build_repair_inputs(mutator=_remove_allergies_and_problems_sections)

    execution = await build_psca_repair_execution_result(
        artifacts["repair_decision"],
        artifacts["normalized_request"],
        artifacts["build_plan"],
        artifacts["schematic"],
        artifacts["resource_construction"],
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert execution.execution_outcome == "executed"
    assert execution.requested_target == "resource_construction"
    assert execution.applied_resource_construction_repair_directive is not None
    assert execution.applied_resource_construction_repair_directive.target_step_ids == [
        "finalize-composition-1-allergies-section",
        "finalize-composition-1-problems-section",
    ]
    assert execution.post_retry_resource_construction is not None
    assert execution.post_retry_resource_construction.execution_scope == "targeted_repair"
    assert [step.step_id for step in execution.post_retry_resource_construction.step_results] == [
        "finalize-composition-1-allergies-section",
        "finalize-composition-1-problems-section",
    ]
    assert execution.post_retry_resource_construction.regenerated_placeholder_ids == [
        "composition-1"
    ]
    assert execution.post_retry_validation_report is not None
    assert execution.post_retry_validation_report.overall_status == "passed_with_warnings"


async def test_psca_repair_execution_reruns_composition_scaffold_plus_finalize_subset_for_title_failure() -> None:
    artifacts = await _build_repair_inputs(mutator=_remove_composition_title)

    execution = await build_psca_repair_execution_result(
        artifacts["repair_decision"],
        artifacts["normalized_request"],
        artifacts["build_plan"],
        artifacts["schematic"],
        artifacts["resource_construction"],
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert execution.execution_outcome == "executed"
    assert execution.requested_target == "resource_construction"
    assert execution.applied_resource_construction_repair_directive is not None
    assert execution.applied_resource_construction_repair_directive.target_step_ids == [
        "build-composition-1-scaffold",
        "finalize-composition-1-medications-section",
        "finalize-composition-1-allergies-section",
        "finalize-composition-1-problems-section",
    ]
    assert execution.post_retry_resource_construction is not None
    assert execution.post_retry_resource_construction.execution_scope == "targeted_repair"
    assert [step.step_id for step in execution.post_retry_resource_construction.step_results] == [
        "build-composition-1-scaffold",
        "finalize-composition-1-medications-section",
        "finalize-composition-1-allergies-section",
        "finalize-composition-1-problems-section",
    ]
    assert execution.post_retry_validation_report is not None
    assert execution.post_retry_validation_report.overall_status == "passed_with_warnings"


async def test_psca_repair_execution_reruns_composition_scaffold_plus_finalize_subset_for_subject_failure() -> None:
    artifacts = await _build_repair_inputs(mutator=_break_composition_subject_reference)

    execution = await build_psca_repair_execution_result(
        artifacts["repair_decision"],
        artifacts["normalized_request"],
        artifacts["build_plan"],
        artifacts["schematic"],
        artifacts["resource_construction"],
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert execution.execution_outcome == "executed"
    assert execution.requested_target == "resource_construction"
    assert execution.applied_resource_construction_repair_directive is not None
    assert execution.applied_resource_construction_repair_directive.target_step_ids == [
        "build-composition-1-scaffold",
        "finalize-composition-1-medications-section",
        "finalize-composition-1-allergies-section",
        "finalize-composition-1-problems-section",
    ]
    assert execution.post_retry_resource_construction is not None
    assert execution.post_retry_resource_construction.execution_scope == "targeted_repair"
    assert [step.step_id for step in execution.post_retry_resource_construction.step_results] == [
        "build-composition-1-scaffold",
        "finalize-composition-1-medications-section",
        "finalize-composition-1-allergies-section",
        "finalize-composition-1-problems-section",
    ]
    assert execution.post_retry_validation_report is not None
    assert execution.post_retry_validation_report.overall_status == "passed_with_warnings"


async def test_psca_repair_execution_reruns_one_section_entry_step_for_single_resource_failure() -> None:
    artifacts = await _build_repair_inputs(mutator=_remove_medicationrequest_content)

    execution = await build_psca_repair_execution_result(
        artifacts["repair_decision"],
        artifacts["normalized_request"],
        artifacts["build_plan"],
        artifacts["schematic"],
        artifacts["resource_construction"],
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert execution.execution_outcome == "executed"
    assert execution.requested_target == "resource_construction"
    assert execution.applied_resource_construction_repair_directive is not None
    assert execution.applied_resource_construction_repair_directive.target_step_ids == [
        "build-medicationrequest-1",
    ]
    assert execution.post_retry_resource_construction is not None
    assert execution.post_retry_resource_construction.execution_scope == "targeted_repair"
    assert [step.step_id for step in execution.post_retry_resource_construction.step_results] == [
        "build-medicationrequest-1",
    ]
    assert execution.post_retry_resource_construction.regenerated_placeholder_ids == [
        "medicationrequest-1",
    ]
    assert execution.post_retry_validation_report is not None
    assert execution.post_retry_validation_report.overall_status == "passed_with_warnings"


async def test_psca_repair_execution_reruns_second_medication_step_for_second_medication_failure() -> None:
    artifacts = await _build_repair_inputs(
        mutator=_remove_second_medicationrequest_content,
        medication_texts=[
            "Atorvastatin 20 MG oral tablet",
            "Metformin 500 MG oral tablet",
        ],
    )

    execution = await build_psca_repair_execution_result(
        artifacts["repair_decision"],
        artifacts["normalized_request"],
        artifacts["build_plan"],
        artifacts["schematic"],
        artifacts["resource_construction"],
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert execution.execution_outcome == "executed"
    assert execution.requested_target == "resource_construction"
    assert execution.applied_resource_construction_repair_directive is not None
    assert execution.applied_resource_construction_repair_directive.target_step_ids == [
        "build-medicationrequest-2",
    ]
    assert execution.post_retry_resource_construction is not None
    assert [step.step_id for step in execution.post_retry_resource_construction.step_results] == [
        "build-medicationrequest-2",
    ]
    assert execution.post_retry_resource_construction.regenerated_placeholder_ids == [
        "medicationrequest-2",
    ]
    assert execution.post_retry_validation_report is not None
    assert execution.post_retry_validation_report.overall_status == "passed_with_warnings"


async def test_psca_repair_execution_reruns_only_build_organization_for_organization_identity_failure() -> None:
    artifacts = await _build_repair_inputs(mutator=_remove_organization_identity)

    execution = await build_psca_repair_execution_result(
        artifacts["repair_decision"],
        artifacts["normalized_request"],
        artifacts["build_plan"],
        artifacts["schematic"],
        artifacts["resource_construction"],
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert execution.execution_outcome == "executed"
    assert execution.requested_target == "resource_construction"
    assert execution.executed_target == "resource_construction"
    assert execution.applied_resource_construction_repair_directive is not None
    assert execution.applied_resource_construction_repair_directive.target_step_ids == [
        "build-organization-1"
    ]
    assert execution.post_retry_resource_construction is not None
    assert execution.post_retry_resource_construction.execution_scope == "targeted_repair"
    assert [step.step_id for step in execution.post_retry_resource_construction.step_results] == [
        "build-organization-1"
    ]
    assert execution.post_retry_resource_construction.regenerated_placeholder_ids == [
        "organization-1"
    ]
    assert execution.post_retry_validation_report is not None
    assert execution.post_retry_validation_report.overall_status == "passed_with_warnings"


async def test_psca_repair_execution_reruns_only_build_practitioner_for_practitioner_identity_alignment_failure() -> None:
    artifacts = await _build_repair_inputs(mutator=_misalign_practitioner_identity)

    execution = await build_psca_repair_execution_result(
        artifacts["repair_decision"],
        artifacts["normalized_request"],
        artifacts["build_plan"],
        artifacts["schematic"],
        artifacts["resource_construction"],
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert execution.execution_outcome == "executed"
    assert execution.requested_target == "resource_construction"
    assert execution.executed_target == "resource_construction"
    assert execution.applied_resource_construction_repair_directive is not None
    assert execution.applied_resource_construction_repair_directive.target_step_ids == [
        "build-practitioner-1"
    ]
    assert execution.post_retry_resource_construction is not None
    assert execution.post_retry_resource_construction.execution_scope == "targeted_repair"
    assert [step.step_id for step in execution.post_retry_resource_construction.step_results] == [
        "build-practitioner-1"
    ]
    assert execution.post_retry_resource_construction.regenerated_placeholder_ids == [
        "practitioner-1"
    ]
    assert execution.post_retry_validation_report is not None
    assert execution.post_retry_validation_report.overall_status == "passed_with_warnings"


async def test_psca_repair_execution_reruns_only_build_practitionerrole_for_relationship_identity_failure() -> None:
    artifacts = await _build_repair_inputs(mutator=_remove_practitionerrole_relationship_identity)

    execution = await build_psca_repair_execution_result(
        artifacts["repair_decision"],
        artifacts["normalized_request"],
        artifacts["build_plan"],
        artifacts["schematic"],
        artifacts["resource_construction"],
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert execution.execution_outcome == "executed"
    assert execution.requested_target == "resource_construction"
    assert execution.executed_target == "resource_construction"
    assert execution.applied_resource_construction_repair_directive is not None
    assert execution.applied_resource_construction_repair_directive.target_step_ids == [
        "build-practitionerrole-1"
    ]
    assert execution.post_retry_resource_construction is not None
    assert execution.post_retry_resource_construction.execution_scope == "targeted_repair"
    assert [step.step_id for step in execution.post_retry_resource_construction.step_results] == [
        "build-practitionerrole-1"
    ]
    assert execution.post_retry_resource_construction.regenerated_placeholder_ids == [
        "practitionerrole-1"
    ]
    assert execution.post_retry_validation_report is not None
    assert execution.post_retry_validation_report.overall_status == "passed_with_warnings"


async def test_psca_repair_execution_reruns_only_build_practitionerrole_for_author_context_alignment_failure() -> None:
    artifacts = await _build_repair_inputs(mutator=_misalign_practitionerrole_author_context)

    execution = await build_psca_repair_execution_result(
        artifacts["repair_decision"],
        artifacts["normalized_request"],
        artifacts["build_plan"],
        artifacts["schematic"],
        artifacts["resource_construction"],
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert execution.execution_outcome == "executed"
    assert execution.requested_target == "resource_construction"
    assert execution.executed_target == "resource_construction"
    assert execution.applied_resource_construction_repair_directive is not None
    assert execution.applied_resource_construction_repair_directive.target_step_ids == [
        "build-practitionerrole-1"
    ]
    assert execution.post_retry_resource_construction is not None
    assert execution.post_retry_resource_construction.execution_scope == "targeted_repair"
    assert [step.step_id for step in execution.post_retry_resource_construction.step_results] == [
        "build-practitionerrole-1"
    ]
    assert execution.post_retry_resource_construction.regenerated_placeholder_ids == [
        "practitionerrole-1"
    ]
    assert execution.post_retry_validation_report is not None
    assert execution.post_retry_validation_report.overall_status == "passed_with_warnings"


async def test_psca_repair_execution_unions_multiple_section_entry_steps_when_multiple_resources_fail() -> None:
    artifacts = await _build_repair_inputs(mutator=_remove_medicationrequest_and_condition_content)

    execution = await build_psca_repair_execution_result(
        artifacts["repair_decision"],
        artifacts["normalized_request"],
        artifacts["build_plan"],
        artifacts["schematic"],
        artifacts["resource_construction"],
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert execution.execution_outcome == "executed"
    assert execution.requested_target == "resource_construction"
    assert execution.applied_resource_construction_repair_directive is not None
    assert execution.applied_resource_construction_repair_directive.target_step_ids == [
        "build-medicationrequest-1",
        "build-condition-1",
    ]
    assert execution.post_retry_resource_construction is not None
    assert execution.post_retry_resource_construction.execution_scope == "targeted_repair"
    assert [step.step_id for step in execution.post_retry_resource_construction.step_results] == [
        "build-medicationrequest-1",
        "build-condition-1",
    ]
    assert execution.post_retry_resource_construction.regenerated_placeholder_ids == [
        "medicationrequest-1",
        "condition-1",
    ]
    assert execution.post_retry_validation_report is not None
    assert execution.post_retry_validation_report.overall_status == "passed_with_warnings"


async def test_psca_repair_execution_reruns_only_bundle_finalization_for_practitionerrole_reference_alignment_failure() -> None:
    artifacts = await _build_repair_inputs(mutator=_break_practitionerrole_practitioner_reference)

    execution = await build_psca_repair_execution_result(
        artifacts["repair_decision"],
        artifacts["normalized_request"],
        artifacts["build_plan"],
        artifacts["schematic"],
        artifacts["resource_construction"],
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert execution.execution_outcome == "executed"
    assert execution.requested_target == "bundle_finalization"
    assert execution.executed_target == "bundle_finalization"
    assert execution.applied_resource_construction_repair_directive is None
    assert execution.rerun_stage_ids == ["bundle_finalization", "validation", "repair_decision"]
    assert execution.post_retry_resource_construction is None
    assert execution.post_retry_validation_report is not None
    assert execution.post_retry_validation_report.overall_status == "passed_with_warnings"


async def test_psca_repair_execution_reruns_only_build_practitionerrole_for_practitioner_reference_contribution_failure() -> None:
    artifacts = await _build_repair_inputs(
        construction_mutator=_break_practitionerrole_practitioner_reference_contribution
    )

    execution = await build_psca_repair_execution_result(
        artifacts["repair_decision"],
        artifacts["normalized_request"],
        artifacts["build_plan"],
        artifacts["schematic"],
        artifacts["resource_construction"],
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert execution.execution_outcome == "executed"
    assert execution.requested_target == "resource_construction"
    assert execution.executed_target == "resource_construction"
    assert execution.applied_resource_construction_repair_directive is not None
    assert execution.applied_resource_construction_repair_directive.target_step_ids == [
        "build-practitionerrole-1"
    ]
    assert execution.rerun_stage_ids == ["resource_construction", "bundle_finalization", "validation", "repair_decision"]
    assert execution.post_retry_resource_construction is not None
    assert execution.post_retry_resource_construction.execution_scope == "targeted_repair"
    assert [step.step_id for step in execution.post_retry_resource_construction.step_results] == [
        "build-practitionerrole-1"
    ]
    assert execution.post_retry_validation_report is not None
    assert execution.post_retry_validation_report.overall_status == "passed_with_warnings"


async def test_psca_repair_execution_prefers_source_contribution_route_when_both_source_and_final_reference_are_wrong() -> None:
    artifacts = await _build_repair_inputs(
        mutator=_break_practitionerrole_practitioner_reference,
        construction_mutator=_break_practitionerrole_practitioner_reference_contribution,
    )

    execution = await build_psca_repair_execution_result(
        artifacts["repair_decision"],
        artifacts["normalized_request"],
        artifacts["build_plan"],
        artifacts["schematic"],
        artifacts["resource_construction"],
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert execution.execution_outcome == "executed"
    assert execution.requested_target == "resource_construction"
    assert execution.applied_resource_construction_repair_directive is not None
    assert execution.applied_resource_construction_repair_directive.target_step_ids == [
        "build-practitionerrole-1"
    ]
    assert execution.post_retry_resource_construction is not None
    assert [step.step_id for step in execution.post_retry_resource_construction.step_results] == [
        "build-practitionerrole-1"
    ]
    assert execution.post_retry_validation_report is not None
    assert execution.post_retry_validation_report.overall_status == "passed_with_warnings"


async def test_psca_repair_execution_reruns_only_targeted_section_finalize_for_allergies_section_entry_alignment_failure() -> None:
    artifacts = await _build_repair_inputs(mutator=_break_allergies_section_entry_reference)

    execution = await build_psca_repair_execution_result(
        artifacts["repair_decision"],
        artifacts["normalized_request"],
        artifacts["build_plan"],
        artifacts["schematic"],
        artifacts["resource_construction"],
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert execution.execution_outcome == "executed"
    assert execution.requested_target == "resource_construction"
    assert execution.executed_target == "resource_construction"
    assert execution.applied_resource_construction_repair_directive is not None
    assert execution.applied_resource_construction_repair_directive.target_step_ids == [
        "finalize-composition-1-allergies-section"
    ]
    assert execution.rerun_stage_ids == ["resource_construction", "bundle_finalization", "validation", "repair_decision"]
    assert execution.post_retry_resource_construction is not None
    assert execution.post_retry_resource_construction.execution_scope == "targeted_repair"
    assert [step.step_id for step in execution.post_retry_resource_construction.step_results] == [
        "finalize-composition-1-allergies-section"
    ]
    assert execution.post_retry_validation_report is not None
    assert execution.post_retry_validation_report.overall_status == "passed_with_warnings"


async def test_psca_repair_execution_unions_multiple_composition_section_entry_alignment_failures_in_plan_order() -> None:
    artifacts = await _build_repair_inputs(mutator=_break_medications_and_problems_section_entry_references)

    execution = await build_psca_repair_execution_result(
        artifacts["repair_decision"],
        artifacts["normalized_request"],
        artifacts["build_plan"],
        artifacts["schematic"],
        artifacts["resource_construction"],
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert execution.execution_outcome == "executed"
    assert execution.requested_target == "resource_construction"
    assert execution.applied_resource_construction_repair_directive is not None
    assert execution.applied_resource_construction_repair_directive.target_step_ids == [
        "finalize-composition-1-medications-section",
        "finalize-composition-1-problems-section",
    ]
    assert execution.post_retry_resource_construction is not None
    assert execution.post_retry_resource_construction.execution_scope == "targeted_repair"
    assert [step.step_id for step in execution.post_retry_resource_construction.step_results] == [
        "finalize-composition-1-medications-section",
        "finalize-composition-1-problems-section",
    ]
    assert execution.post_retry_validation_report is not None
    assert execution.post_retry_validation_report.overall_status == "passed_with_warnings"


async def test_psca_repair_execution_marks_build_plan_retry_as_unsupported() -> None:
    artifacts = await _build_repair_inputs()
    repair_decision = RepairDecisionResult(
        stage_id="repair_decision",
        status="placeholder_complete",
        summary="Synthetic unsupported retry target for testing.",
        placeholder_note="Test artifact.",
        source_refs=[],
        overall_decision="repair_recommended",
        recommended_target="build_plan_or_schematic",
        recommended_next_stage="build_plan",
        finding_routes=[],
        deferred_external_dependencies=[],
        evidence=RepairDecisionEvidence(
            source_validation_stage_id="validation",
            source_overall_validation_status="failed",
            routed_finding_codes=["synthetic.build_plan_retry"],
            source_refs=[],
        ),
        rationale="Synthetic unsupported target.",
    )

    execution = await build_psca_repair_execution_result(
        repair_decision,
        artifacts["normalized_request"],
        artifacts["build_plan"],
        artifacts["schematic"],
        artifacts["resource_construction"],
        LocalCandidateBundleScaffoldStandardsValidator(),
    )

    assert execution.execution_outcome == "unsupported"
    assert execution.requested_target == "build_plan_or_schematic"
    assert execution.retry_eligible is False
    assert execution.attempt_count == 0
    assert execution.rerun_stage_ids == []
    assert execution.post_retry_resource_construction is None
    assert execution.post_retry_candidate_bundle is None
    assert execution.unsupported_reason is not None


async def _build_repair_inputs(mutator=None, construction_mutator=None, medication_texts=None):
    repository = PscaAssetRepository()
    normalized_assets = repository.load_foundation_context(PscaAssetQuery())
    medication_texts = medication_texts or ["Atorvastatin 20 MG oral tablet"]
    normalized_request = build_psca_normalized_request(
        WorkflowBuildInput(
            specification=SpecificationSelection(),
            patient_profile=ProfileReferenceInput(
                profile_id="patient-retry-test",
                display_name="Retry Test Patient",
            ),
            patient_context=PatientContextInput(
                patient=PatientIdentityInput(
                    patient_id="patient-retry-test",
                    display_name="Retry Test Patient",
                    source_type="patient_management",
                ),
                medications=[
                    PatientMedicationInput(
                        medication_id=f"med-retry-{index}",
                        display_text=display_text,
                    )
                    for index, display_text in enumerate(medication_texts, start=1)
                ],
                allergies=[],
                conditions=[],
            ),
            provider_profile=ProfileReferenceInput(
                profile_id="provider-retry-test",
                display_name="Retry Test Provider",
            ),
            provider_context=ProviderContextInput(
                provider=ProviderIdentityInput(
                    provider_id="provider-retry-test",
                    display_name="Retry Test Provider",
                    source_type="provider_management",
                ),
                organizations=[
                    ProviderOrganizationInput(
                        organization_id="org-retry-test",
                        display_name="Retry Test Organization",
                    )
                ],
                provider_role_relationships=[
                    ProviderRoleRelationshipInput(
                        relationship_id="provider-role-retry-1",
                        organization_id="org-retry-test",
                        role_label="attending-physician",
                    )
                ],
            ),
            request=BundleRequestInput(
                request_text="Create a deterministic repair execution test run.",
                scenario_label="pytest-retry",
            ),
        )
    )
    schematic = build_psca_bundle_schematic(normalized_assets, normalized_request)
    plan = build_psca_build_plan(schematic)
    resource_construction = build_psca_resource_construction_result(plan, schematic, normalized_request)
    if construction_mutator is not None:
        resource_construction = construction_mutator(resource_construction)
    candidate_bundle = build_psca_candidate_bundle_result(resource_construction, schematic, normalized_request)
    if mutator is not None:
        candidate_bundle = mutator(candidate_bundle)
    validation_report = await build_psca_validation_report(
        candidate_bundle,
        schematic,
        normalized_request,
        LocalCandidateBundleScaffoldStandardsValidator(),
        resource_construction,
    )
    repair_decision = build_psca_repair_decision(validation_report)
    return {
        "normalized_request": normalized_request,
        "build_plan": plan,
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


def _swap_medication_bundle_entries(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    broken_bundle.entry_assembly[5], broken_bundle.entry_assembly[6] = (
        broken_bundle.entry_assembly[6],
        broken_bundle.entry_assembly[5],
    )
    broken_bundle.evidence.assembled_medication_placeholder_ids = [
        "medicationrequest-2",
        "medicationrequest-1",
    ]
    broken_bundle.candidate_bundle.fhir_bundle["entry"][5], broken_bundle.candidate_bundle.fhir_bundle["entry"][6] = (
        broken_bundle.candidate_bundle.fhir_bundle["entry"][6],
        broken_bundle.candidate_bundle.fhir_bundle["entry"][5],
    )
    return broken_bundle


def _duplicate_bundle_entry_fullurl(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    broken_bundle.candidate_bundle.fhir_bundle["entry"][6]["fullUrl"] = (
        broken_bundle.candidate_bundle.fhir_bundle["entry"][5]["fullUrl"]
    )
    return broken_bundle


def _misalign_patient_identity(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    patient = broken_bundle.candidate_bundle.fhir_bundle["entry"][1]["resource"]
    patient["identifier"][0]["value"] = "wrong-patient-id"
    patient["name"][0]["text"] = "Wrong Patient"
    return broken_bundle


def _misalign_practitioner_identity(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    practitioner = broken_bundle.candidate_bundle.fhir_bundle["entry"][3]["resource"]
    practitioner["identifier"][0]["value"] = "wrong-provider-id"
    practitioner["name"][0]["text"] = "Wrong Provider"
    return broken_bundle


def _misalign_second_medication_text(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    broken_bundle.candidate_bundle.fhir_bundle["entry"][6]["resource"]["medicationCodeableConcept"]["text"] = (
        "Wrong second medication text"
    )
    return broken_bundle


def _remove_required_section(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    composition = broken_bundle.candidate_bundle.fhir_bundle["entry"][0]["resource"]
    composition["section"] = composition["section"][:2]
    return broken_bundle


def _remove_allergies_and_problems_sections(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    composition = broken_bundle.candidate_bundle.fhir_bundle["entry"][0]["resource"]
    composition["section"] = composition["section"][:1]
    return broken_bundle


def _remove_medicationrequest_content(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    medication = broken_bundle.candidate_bundle.fhir_bundle["entry"][5]["resource"]
    medication["medicationCodeableConcept"]["text"] = ""
    return broken_bundle


def _remove_second_medicationrequest_content(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    medication = broken_bundle.candidate_bundle.fhir_bundle["entry"][6]["resource"]
    medication["medicationCodeableConcept"]["text"] = ""
    return broken_bundle


def _remove_organization_identity(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    organization = broken_bundle.candidate_bundle.fhir_bundle["entry"][4]["resource"]
    organization.pop("identifier", None)
    return broken_bundle


def _remove_practitionerrole_relationship_identity(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    practitioner_role = broken_bundle.candidate_bundle.fhir_bundle["entry"][2]["resource"]
    practitioner_role.pop("identifier", None)
    return broken_bundle


def _misalign_practitionerrole_author_context(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    practitioner_role = broken_bundle.candidate_bundle.fhir_bundle["entry"][2]["resource"]
    practitioner_role["code"][0]["text"] = "wrong-role-label"
    return broken_bundle


def _remove_medicationrequest_and_condition_content(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    medication = broken_bundle.candidate_bundle.fhir_bundle["entry"][5]["resource"]
    condition = broken_bundle.candidate_bundle.fhir_bundle["entry"][7]["resource"]
    medication["medicationCodeableConcept"]["text"] = ""
    condition["code"]["text"] = ""
    return broken_bundle


def _remove_composition_title(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    composition = broken_bundle.candidate_bundle.fhir_bundle["entry"][0]["resource"]
    composition.pop("title", None)
    return broken_bundle


def _break_composition_subject_reference(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    composition = broken_bundle.candidate_bundle.fhir_bundle["entry"][0]["resource"]
    composition["subject"]["reference"] = "Patient/patient-1"
    return broken_bundle


def _break_practitionerrole_practitioner_reference(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    practitioner_role = broken_bundle.candidate_bundle.fhir_bundle["entry"][2]["resource"]
    practitioner_role["practitioner"]["reference"] = "Practitioner/practitioner-1"
    return broken_bundle


def _break_practitionerrole_practitioner_reference_contribution(resource_construction):
    return _mutate_resource_construction_reference(
        resource_construction,
        "practitionerrole-1",
        "practitioner.reference",
        "Practitioner/wrong-practitioner",
    )


def _break_allergies_section_entry_reference(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    composition = broken_bundle.candidate_bundle.fhir_bundle["entry"][0]["resource"]
    wrong_full_url = broken_bundle.candidate_bundle.fhir_bundle["entry"][7]["fullUrl"]
    composition["section"][1]["entry"][0]["reference"] = wrong_full_url
    return broken_bundle


def _break_medications_and_problems_section_entry_references(candidate_bundle):
    broken_bundle = deepcopy(candidate_bundle)
    composition = broken_bundle.candidate_bundle.fhir_bundle["entry"][0]["resource"]
    composition["section"][0]["entry"][0]["reference"] = broken_bundle.candidate_bundle.fhir_bundle["entry"][6]["fullUrl"]
    composition["section"][2]["entry"][0]["reference"] = broken_bundle.candidate_bundle.fhir_bundle["entry"][5]["fullUrl"]
    return broken_bundle


def _mutate_resource_construction_reference(
    resource_construction,
    placeholder_id: str,
    reference_path: str,
    new_reference: str,
):
    broken_construction = deepcopy(resource_construction)
    registry_entry = next(
        entry for entry in broken_construction.resource_registry if entry.placeholder_id == placeholder_id
    )
    _set_nested_reference_value(
        registry_entry.current_scaffold.fhir_scaffold,
        reference_path,
        new_reference,
    )
    for step_result in [*broken_construction.step_results, *broken_construction.step_result_history]:
        if step_result.target_placeholder_id != placeholder_id:
            continue
        for contribution in step_result.reference_contributions:
            if contribution.reference_path == reference_path:
                contribution.reference_value = new_reference
    return broken_construction


def _set_nested_reference_value(root: dict[str, object], path: str, value: str) -> None:
    segments = path.split(".")
    current = root
    for segment in segments[:-1]:
        current = current[segment]
    current[segments[-1]] = value
