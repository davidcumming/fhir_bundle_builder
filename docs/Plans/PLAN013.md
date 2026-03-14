## 1. Repo assessment

- The current retry foundation is real but still narrow:
  - `repair_decision` already routes meaningful workflow failures to `resource_construction` and bundle-shape failures to `bundle_finalization`.
  - `repair_execution` still supports only `bundle_finalization` in [repair_execution_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/repair_execution_builder.py).
- The current `resource_construction` path is now mature enough to rerun safely:
  - `build_psca_resource_construction_result(plan, schematic, normalized_request)` is a pure deterministic transform.
  - its only inputs are already stored in workflow state: `build_plan`, `bundle_schematic`, `normalized_request`.
- The current safe downstream chain is clear from builder signatures:
  - `resource_construction` rerun must be followed by:
    - `bundle_finalization`
    - `validation`
    - `repair_decision`
  - because `bundle_finalization` consumes `ResourceConstructionStageResult`, and validation/repair consume the finalized bundle.
- The main missing piece is artifact shape:
  - `RepairExecutionResult` currently has:
    - `post_retry_candidate_bundle`
    - `post_retry_validation_report`
    - `post_retry_repair_decision`
  - but no place to store a regenerated `ResourceConstructionStageResult`.
- Executor wiring is already compatible with this extension:
  - workflow state is explicit via `_store_artifact` / `_get_artifact`
  - `repair_execution` already resolves the shared standards validator, including Matchbox/local fallback, so post-retry validation can reuse the same runtime validator selection.
- Current tests already prove meaningful natural routing to `resource_construction` for:
  - `bundle.required_sections_present`
  - `bundle.composition_enriched_content_present`
  - `bundle.patient_identity_content_present`
  - `bundle.practitioner_identity_content_present`
  - `bundle.practitionerrole_author_context_present`
  - `bundle.section_entry_content_present`
- The current happy path still ends with:
  - `repair_decision.recommended_target == "standards_validation_external"`
  - `repair_execution.execution_outcome == "deferred"`
  so executed `resource_construction` retry still needs direct builder tests against intentionally broken artifacts.

## 2. Proposed slice scope

- Add one new executable internal retry target:
  - `resource_construction`
- Preserve the existing executable retry target:
  - `bundle_finalization`
- Keep the retry model bounded:
  - one retry attempt maximum
  - no recursive or multi-pass retry
  - no mutation of upstream request/spec assets
- Recommended supported targets after this slice:
  - `resource_construction`
  - `bundle_finalization`
- Recommended continued non-executable handling:
  - `standards_validation_external -> deferred`
  - `none_required -> not_needed`
  - `build_plan_or_schematic -> unsupported`
  - `human_intervention -> unsupported`
- Preserve the current top-level run result contract:
  - original first-pass `resource_construction`, `candidate_bundle`, `validation_report`, and `repair_decision` stay unchanged at top level
  - regenerated artifacts remain nested under `repair_execution`

## 3. Proposed `resource_construction` retry approach

- Extend `RepairExecutionResult` to carry the regenerated construction artifact:
  - add `post_retry_resource_construction: ResourceConstructionStageResult | None`
- Extend `build_psca_repair_execution_result(...)` inputs to include `build_plan`, while keeping the original first-pass `resource_construction` input for the existing `bundle_finalization` path.
- Keep one deterministic retry policy object in code, not a generic engine:
  - `supported_targets = {"resource_construction", "bundle_finalization"}`
  - `max_attempts = 1`
- Exact rerun behavior:
  - if `recommended_target == "bundle_finalization"`:
    - rerun `bundle_finalization`
    - rerun `validation`
    - rerun `repair_decision`
  - if `recommended_target == "resource_construction"`:
    - rerun `resource_construction`
    - rerun `bundle_finalization`
    - rerun `validation`
    - rerun `repair_decision`
- Exact builder inputs for `resource_construction` retry:
  - `build_plan`
  - `bundle_schematic`
  - `normalized_request`
- Recommended regenerated artifact storage under `repair_execution`:
  - `post_retry_resource_construction`
  - `post_retry_candidate_bundle`
  - `post_retry_validation_report`
  - `post_retry_repair_decision`
- Recommended rerun/evidence fields:
  - `rerun_stage_ids = ["resource_construction", "bundle_finalization", "validation", "repair_decision"]`
  - `regenerated_artifact_keys = ["resource_construction", "candidate_bundle", "validation_report", "repair_decision"]`
  - for the existing bundle-finalization path, keep:
    - `rerun_stage_ids = ["bundle_finalization", "validation", "repair_decision"]`
    - `regenerated_artifact_keys = ["candidate_bundle", "validation_report", "repair_decision"]`
- Keep stop behavior unchanged:
  - expose `post_retry_repair_decision`
  - do not act on it again, even if it still recommends repair
- Keep status behavior unchanged:
  - `placeholder_complete` for `executed` and `not_needed`
  - `placeholder_warning` for `deferred` and `unsupported`

## 4. File-level change plan

- Update [models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py)
  - add `post_retry_resource_construction` to `RepairExecutionResult`
  - no broader workflow-result redesign
- Update [repair_execution_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/repair_execution_builder.py)
  - add `resource_construction` support
  - add the `build_plan` input
  - factor the current downstream rerun logic so both executable targets share the same validation/repair tail
- Update [executors.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/executors.py)
  - load `build_plan` from workflow state in `repair_execution`
  - pass `build_plan` into `build_psca_repair_execution_result(...)`
- Update tests:
  - [tests/test_psca_repair_execution_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_repair_execution_builder.py)
  - [tests/test_psca_bundle_builder_workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py)
- Update docs:
  - [README.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md)
  - [docs/development-plan.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md)

## 5. Step-by-step implementation plan

1. Extend the retry artifact contract:
   - add `post_retry_resource_construction`
   - keep all existing retry fields intact
2. Update `build_psca_repair_execution_result(...)` signature to accept:
   - `repair_decision`
   - `normalized_request`
   - `build_plan`
   - `bundle_schematic`
   - original first-pass `resource_construction`
   - `standards_validator`
3. Change the supported-target set to include `resource_construction`.
4. Implement deterministic executed-path branching:
   - `bundle_finalization` path reuses the original first-pass `resource_construction`
   - `resource_construction` path reruns `build_psca_resource_construction_result(build_plan, schematic, normalized_request)` first
5. For `resource_construction` retry, rerun exactly:
   - `resource_construction`
   - `bundle_finalization`
   - `validation`
   - `repair_decision`
   and populate the nested post-retry artifacts.
6. Preserve the existing `bundle_finalization` retry path exactly as-is except for any light refactor needed to share code.
7. Keep all unsupported/deferred target handling explicit:
   - `standards_validation_external -> deferred`
   - `none_required -> not_needed`
   - `build_plan_or_schematic -> unsupported`
   - `human_intervention -> unsupported`
8. Update executor wiring so `repair_execution` pulls `build_plan` from workflow state and passes it to the builder.
9. Update direct retry tests:
   - keep current deferred happy-path test
   - keep current executed `bundle_finalization` test
   - replace the current `resource_construction` unsupported test with an executed `resource_construction` retry test using a naturally routed failure, such as:
     - missing Composition section
     - missing Patient name
     - missing Practitioner identifier
   - assert:
     - `execution_outcome == "executed"`
     - `requested_target == "resource_construction"`
     - `executed_target == "resource_construction"`
     - `attempt_count == 1`
     - `rerun_stage_ids == ["resource_construction", "bundle_finalization", "validation", "repair_decision"]`
     - `regenerated_artifact_keys == ["resource_construction", "candidate_bundle", "validation_report", "repair_decision"]`
     - `post_retry_resource_construction is not None`
     - `post_retry_validation_report.overall_status == "passed_with_warnings"`
     - `post_retry_repair_decision.overall_decision == "external_validation_pending"`
   - add one direct unsupported-target test using a synthetic `RepairDecisionResult` for `build_plan_or_schematic` or `human_intervention`, since the current validation paths do not naturally generate those targets
10. Update workflow smoke assertions only enough to prove:
   - default run remains deferred on external standards validation
   - original top-level artifacts remain unchanged
   - `repair_execution.post_retry_resource_construction is None` on the normal path
11. Update README and development-plan wording after tests are green.

## 6. Definition of Done

- `repair_execution` can now execute deterministic bounded retries for:
  - `bundle_finalization`
  - `resource_construction`
- The `resource_construction` retry path reruns exactly:
  - `resource_construction`
  - `bundle_finalization`
  - `validation`
  - `repair_decision`
- `RepairExecutionResult` exposes the regenerated artifacts for that path, including:
  - `post_retry_resource_construction`
  - `post_retry_candidate_bundle`
  - `post_retry_validation_report`
  - `post_retry_repair_decision`
- Original first-pass artifacts remain unchanged at top level in the final workflow result.
- Dev UI shows, for executed `resource_construction` retries:
  - requested target
  - executed target
  - retry eligibility
  - rerun stage ids
  - regenerated artifact keys
  - nested regenerated construction/bundle/validation/decision artifacts
- The default happy path remains non-executing:
  - `repair_decision.recommended_target == "standards_validation_external"`
  - `repair_execution.execution_outcome == "deferred"`
- Still unsupported or deferred after this slice:
  - `build_plan_or_schematic`
  - `human_intervention`
  - recursive/multi-pass retry loops
  - mutation of upstream request/spec inputs
  - generic retry-engine behavior

## 7. Risks / notes

- The main real risk is that `resource_construction` retry is still a whole-stage rebuild, not a narrower per-finding patch. That is acceptable here, but the docs/artifact wording should stay honest about it.
- A second real risk is losing inspectability if the regenerated construction artifact is not stored explicitly. This slice should not hide the rerun by exposing only the downstream bundle.
- A third risk is accidentally changing the current `bundle_finalization` retry semantics while generalizing the builder. Preserve that path’s current rerun chain and assertions.
- Because the normal workflow still ends in `standards_validation_external`, executed `resource_construction` retry will continue to be proven mainly through targeted tests, not through the default smoke path.

## 8. Targeted `docs/development-plan.md` updates after implementation

- In Section 8, change `Current Focus` from the post-Matchbox hardening slice to the next bounded realism/quality slice after the second internal retry path is available.
- In Section 9, replace `Next Planned Slice` with a bounded follow-on such as: “Deepen Organization/provider-role realism or narrow the first targeted repair directives within `resource_construction`.”
- In Section 10, keep `Phase 8: Minimal End-to-End PS-CA Workflow` as `In Progress`.
- In Section 10, update the Phase 8 note to state that bounded repair execution now supports both `bundle_finalization` and `resource_construction` as executable internal targets.
- In Section 12, refine the repair-execution assumption to say the bounded retry model is still single-pass but now supports both `bundle_finalization` and `resource_construction`.
- In Section 13, add one concise risk only if observed during implementation: the current `resource_construction` retry is a whole-stage deterministic rebuild and may later need narrower repair directives to avoid coarse retry behavior.
- In Section 16, update the immediate next objective to the next narrow realism/quality slice rather than further broadening retry orchestration.
