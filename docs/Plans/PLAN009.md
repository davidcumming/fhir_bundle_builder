## 1. Repo assessment

- The workflow is still a simple linear chain in [workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/workflow.py): `request_normalization -> specification_asset_retrieval -> bundle_schematic -> build_plan -> resource_construction -> bundle_finalization -> validation -> repair_decision`.
- `repair_decision` is now real and deterministic, but it is still terminal. In [executors.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/executors.py) it yields the final `WorkflowSkeletonRunResult`, so the workflow currently has no stage that can act on the recommendation.
- The current repair artifact in [models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py) is recommendation-only. It already contains the inputs needed for execution:
  - `overall_decision`
  - `recommended_target`
  - `recommended_next_stage`
  - per-finding routes
  - evidence back to validation
- The current upstream builders are pure deterministic transforms and can be safely reused for bounded retry execution without invoking the framework recursively:
  - `build_psca_candidate_bundle_result(...)`
  - `build_psca_validation_report(...)`
  - `build_psca_repair_decision(...)`
  - `build_psca_resource_construction_result(...)`
- Workflow state is already explicit and stage-scoped through `_store_artifact` / `_get_artifact`, so a retry stage can read prior artifacts directly from state without changing earlier stages.
- The current happy path does not naturally produce an actionable internal repair target. The smoke test proves:
  - `validation_report.overall_status == "passed_with_warnings"`
  - `repair_decision.overall_decision == "external_validation_pending"`
  This means executed retry behavior will need direct builder tests against intentionally broken artifacts, not only the normal workflow smoke path.
- The current routing map sends actionable internal findings to two layers:
  - `bundle_finalization`
  - `resource_construction`
  but only bundle-finalization retry is actually mature enough to execute safely right now.
- The main constraints now are:
  - add a real action-taking stage without introducing a loop engine
  - keep retry bounded to one deterministic pass
  - preserve the original recommendation artifact and expose retry results separately
  - avoid retrying layers that have no meaningful repair hooks yet

## 2. Proposed slice scope

- Add one new terminal workflow stage: `repair_execution`.
- Keep `repair_decision` as a normal stage output, not the final workflow output.
- Introduce the first real `RepairExecutionResult` artifact that classifies the recommendation as:
  - `executed`
  - `deferred`
  - `not_needed`
  - `unsupported`
- Recommended retry scope for this slice:
  - support actual execution only for `bundle_finalization`
  - explicitly defer `standards_validation_external`
  - treat `none_required` as no-op
  - explicitly mark `resource_construction`, `build_plan_or_schematic`, and `human_intervention` as unsupported in this slice
- Do not support recursive retries or a second repair pass. One bounded retry attempt maximum.
- Do not mutate upstream artifacts in place. Preserve the original first-pass artifacts and attach regenerated artifacts only under the new `repair_execution` stage result.

## 3. Proposed repair-execution approach

- Add a dedicated deterministic builder, for example `build_psca_repair_execution_result(...)`, and keep the new executor thin.
- Make `repair_execution` the new terminal stage. `repair_decision` should change from `workflow_output` to `output=RepairDecisionResult`.
- Recommended artifact contract:
  - `RepairExecutionResult`
    - `execution_mode = "single_targeted_retry_pass"`
    - `execution_outcome`
    - `retry_eligible`
    - `requested_target`
    - `executed_target`
    - `recommended_next_stage`
    - `attempt_count`
    - `rerun_stage_ids`
    - `regenerated_artifact_keys`
    - `post_retry_candidate_bundle`
    - `post_retry_validation_report`
    - `post_retry_repair_decision`
    - `deferred_reason`
    - `unsupported_reason`
    - `evidence`
    - `rationale`
  - `RepairExecutionEvidence`
    - `source_repair_decision_stage_id`
    - `source_validation_stage_id`
    - `source_recommended_target`
    - `source_overall_decision`
    - `rerun_stage_ids`
    - `regenerated_artifact_keys`
    - `source_refs`
- Recommended execution-outcome rules:
  - `executed`
    - only when `repair_decision.overall_decision == "repair_recommended"` and `recommended_target == "bundle_finalization"`
  - `deferred`
    - when `recommended_target == "standards_validation_external"`
  - `not_needed`
    - when `recommended_target == "none_required"`
  - `unsupported`
    - when `recommended_target` is `resource_construction`, `build_plan_or_schematic`, or `human_intervention`
- Recommended target support for this slice:
  - `bundle_finalization` is eligible now because it is the narrowest mature repair layer and already rebuilds a full candidate bundle from stable upstream inputs (`resource_construction`, `bundle_schematic`, `normalized_request`).
  - `resource_construction` should be explicitly unsupported now because the current construction layer has no targeted repair directive model; rerunning it would be a broad whole-stage rebuild with no narrower repair hook and little decision value for this slice.
- Exact rerun behavior for supported retry:
  1. read `normalized_request`, `bundle_schematic`, and `resource_construction` from workflow state
  2. rerun `build_psca_candidate_bundle_result(...)`
  3. rerun `build_psca_validation_report(...)`
  4. rerun `build_psca_repair_decision(...)`
  5. stop
- No second retry pass, even if `post_retry_repair_decision` still recommends internal repair. The new artifact should expose that post-retry state but not act on it again.
- Preserve Dev UI inspectability by keeping:
  - original `candidate_bundle`, `validation_report`, and `repair_decision` at top level in the final run result
  - regenerated artifacts nested inside `repair_execution`
- Recommended status behavior for the new stage:
  - `placeholder_complete` for `executed` and `not_needed`
  - `placeholder_warning` for `deferred` and `unsupported`
- Recommended final-run contract change:
  - extend `WorkflowSkeletonRunResult` with `repair_execution`
  - keep all existing first-pass artifact fields unchanged

## 4. File-level change plan

- Update [src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py)
  - add `RepairExecutionResult` and `RepairExecutionEvidence`
  - add retry outcome / mode literals
  - extend `WorkflowSkeletonRunResult` with `repair_execution`
- Create [src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/repair_execution_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/repair_execution_builder.py)
  - deterministic single-pass retry execution logic
- Update [src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/executors.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/executors.py)
  - change `repair_decision` to a normal stage output
  - add new `repair_execution` executor
  - wire retry execution through the existing builders and state artifacts
- Update [src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/workflow.py)
  - append `repair_execution` to the chain
- Add [tests/test_psca_repair_execution_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_repair_execution_builder.py)
  - direct deterministic coverage for executed, deferred, and unsupported outcomes
- Update [tests/test_psca_bundle_builder_workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py)
  - assert the new terminal stage and happy-path deferred outcome
- Update [README.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md)
  - document the new repair-execution stage output
- Update [docs/development-plan.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md)
  - targeted phase/focus/status changes after implementation succeeds

## 5. Step-by-step implementation plan

1. Extend the models first:
   - add `RepairExecutionResult`
   - add `RepairExecutionEvidence`
   - add `RepairExecutionOutcome` and `RepairExecutionMode`
   - extend `WorkflowSkeletonRunResult`
2. Implement `build_psca_repair_execution_result(...)` with this exact input set:
   - `repair_decision`
   - `normalized_request`
   - `bundle_schematic`
   - `resource_construction`
   - `standards_validator`
3. Encode this exact retry policy in the builder:
   - `max_attempts = 1`
   - `supported_targets = ["bundle_finalization"]`
   - no recursive re-entry
4. Implement deterministic outcome classification:
   - `standards_validation_external -> deferred`
   - `none_required -> not_needed`
   - `bundle_finalization + repair_recommended -> executed`
   - `resource_construction -> unsupported`
   - `build_plan_or_schematic -> unsupported`
   - `human_intervention -> unsupported`
5. For the executed path, rerun exactly:
   - `bundle_finalization`
   - `validation`
   - `repair_decision`
   and record:
   - `attempt_count = 1`
   - `rerun_stage_ids = ["bundle_finalization", "validation", "repair_decision"]`
   - `regenerated_artifact_keys = ["candidate_bundle", "validation_report", "repair_decision"]`
6. Do not overwrite first-pass top-level artifacts. Put the regenerated artifacts under:
   - `repair_execution.post_retry_candidate_bundle`
   - `repair_execution.post_retry_validation_report`
   - `repair_execution.post_retry_repair_decision`
7. Refactor workflow wiring:
   - change `repair_decision` executor to `output=RepairDecisionResult`
   - add `repair_execution` as the terminal executor with `workflow_output=WorkflowSkeletonRunResult`
   - append `repair_execution` to `STAGE_ORDER`
8. Add direct repair-execution tests:
   - happy-path current workflow recommendation:
     - build the normal validation + repair decision
     - assert `execution_outcome == "deferred"`
     - assert `requested_target == "standards_validation_external"`
     - assert no stages rerun
   - supported retry path:
     - intentionally break the candidate bundle artifact so validation routes to `bundle_finalization`
     - run repair decision
     - run repair execution with the original `resource_construction`
     - assert retry is executed
     - assert rerun stages are `bundle_finalization`, `validation`, `repair_decision`
     - assert post-retry validation returns to `passed_with_warnings`
     - assert post-retry repair decision returns to `external_validation_pending`
   - unsupported path:
     - intentionally break the Composition section state so validation routes to `resource_construction`
     - assert `execution_outcome == "unsupported"`
     - assert no stages rerun
9. Update the workflow smoke test to assert:
   - `stage_order` now includes `repair_execution`
   - original `repair_decision` still exists and remains `external_validation_pending`
   - `repair_execution.execution_outcome == "deferred"`
   - `repair_execution.requested_target == "standards_validation_external"`
   - `repair_execution.post_retry_candidate_bundle is None`
10. Update README and development-plan wording after tests are green.

## 6. Definition of Done

- The workflow has a new real `repair_execution` stage after `repair_decision`.
- The final workflow output includes both:
  - the original structured `repair_decision`
  - a new structured `repair_execution` artifact
- The new stage clearly distinguishes:
  - executed retry
  - deferred external dependency
  - no-op / not-needed
  - unsupported target
- Retry execution is deterministic and bounded:
  - one attempt maximum
  - no recursive loops
  - only `bundle_finalization` is internally retryable in this slice
- When `bundle_finalization` retry is executed, the stage reruns:
  - bundle finalization
  - validation
  - repair decision
  and exposes the regenerated artifacts explicitly.
- The current happy path remains non-executing:
  - original `repair_decision` is still `external_validation_pending`
  - `repair_execution` reports `deferred`
  - no internal retry occurs
- Dev UI shows a new terminal stage with:
  - retry eligibility/outcome
  - rerun stage list
  - regenerated artifacts when executed
  - deferred or unsupported reasons when not executed
- What remains intentionally unsupported after this slice:
  - retry for `resource_construction`
  - retry for `build_plan_or_schematic`
  - retry for `human_intervention`
  - retry for `standards_validation_external`
  - multi-pass retry loops
  - automatic mutation of upstream artifacts
  - generalized repair engine behavior

## 7. Risks / notes

- The main scope risk is supporting `resource_construction` too early. The current construction layer does not yet have targeted repair hooks, so retrying it now would widen the slice without adding a trustworthy repair boundary.
- The current happy path will not exercise executed retry in the full workflow run. That is expected; executed retry should be proven with direct builder tests against intentionally broken artifacts until richer internal failure paths exist naturally.
- The retry stage must preserve the original first-pass artifacts. Replacing them at top level would make Dev UI inspection worse and blur “recommendation” versus “post-retry result.”
- The single-pass stop rule is important. If the post-retry repair decision still recommends repair, the stage must expose that state and stop rather than silently chaining another pass.

## 8. Targeted `docs/development-plan.md` updates after implementation

- In Section 8, change `Current Focus` from repair execution foundation to the next bounded Phase 8 slice that proves a more meaningful end-to-end PS-CA workflow using the completed validation/repair foundation.
- In Section 9, replace `Next Planned Slice` with a bounded follow-on such as: “Implement the first narrow end-to-end PS-CA quality slice with more meaningful resource/data-element content while preserving deterministic validation and bounded repair execution.”
- In Section 10, mark `Phase 7: Validation and Repair Routing Foundation` as `Completed` only if this slice lands with:
  - structured validation
  - structured repair decision
  - one bounded internal retry execution path
  - inspectable retry results in Dev UI
- In Section 10, move `Phase 8: Minimal End-to-End PS-CA Workflow` to `In Progress` only if the next follow-on slice is approved immediately afterward.
- In Section 12, add or refine the assumption that the first repair-execution slice is a single-pass retry foundation that supports only `bundle_finalization` as an internal executable target.
- In Section 13, add one concise risk only if it is observed during implementation: the current workflow may not naturally produce internal actionable repair recommendations yet, so executed retry behavior is primarily demonstrated through targeted tests until richer construction slices exist.
- In Section 16, update the immediate next objective to point at using the completed repair foundation to prove a more meaningful end-to-end PS-CA generation path rather than broadening retry orchestration.
