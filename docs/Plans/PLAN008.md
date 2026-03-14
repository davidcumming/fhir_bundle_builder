## 1. Repo assessment

- The `repair_decision` stage is still a stub in [executors.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/executors.py). It accepts the real `ValidationReport` but always emits `RepairDecisionStub` with `decision="complete_for_slice"` and `next_stage="none"`.
- The current repair model in [models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py) is too weak for routing. `RepairDecisionStub` only has:
  - `decision: "complete_for_slice"`
  - `next_stage: "none"`
  - `rationale`
  It cannot represent per-finding routing, route targets, deferred external dependencies, or “no repair needed but external validation still pending.”
- The validation artifact is now rich enough to drive deterministic routing without redesign:
  - `ValidationReport.overall_status`
  - separate `standards_validation` and `workflow_validation`
  - stable `ValidationFinding` fields: `channel`, `severity`, `code`, `location`, `message`
  - `deferred_validation_areas`
  - `ValidationEvidence`
- The current workflow/business-rule findings already use stable codes that can support routing now:
  - `bundle.type_is_document`
  - `bundle.required_entries_present`
  - `bundle.composition_first_placeholder`
  - `bundle.first_entry_is_composition`
  - `bundle.composition_type_matches_psca_summary`
  - `bundle.required_sections_present`
  - `bundle.deferred_fields_recorded`
- The standards-validation channel also has a stable code:
  - `external_profile_validation_deferred`
- The current tests cover validation and workflow execution but do not assert any routing behavior yet. The workflow smoke test only checks that the stub repair decision is still `complete_for_slice`.
- `docs/development-plan.md` now sets repair routing as the current focus and Phase 7 is already `In Progress`. `docs/Plans/PLAN007.md` is the relevant prior plan record because it established the structured validation report this slice should consume.
- Constraints that matter now:
  - keep routing deterministic and inspectable
  - target the smallest reasonable workflow layer
  - do not execute repairs
  - do not redesign the loop/orchestrator
  - do not add a broad generic repair framework

## 2. Proposed slice scope

- Replace `RepairDecisionStub` with the first real structured repair-decision artifact.
- Keep this slice narrow:
  - classify findings into a small repair-target taxonomy
  - emit per-finding routing recommendations
  - emit one overall routing recommendation for the run
  - explicitly separate internal actionable issues from deferred external standards-validation dependency
- Recommended routing taxonomy for this slice:
  - `none_required`
  - `resource_construction`
  - `bundle_finalization`
  - `build_plan_or_schematic`
  - `standards_validation_external`
  - `human_intervention`
- Recommended overall decision states:
  - `complete_no_repair_needed`
  - `repair_recommended`
  - `external_validation_pending`
  - `human_review_recommended`
- Keep actual retry/re-execution out of scope. The result should be recommendation-only.
- Out of scope after this slice:
  - automatic retries
  - mutating earlier artifacts
  - iteration counters/history
  - generalized repair orchestration
  - arbitrary-IG repair semantics

## 3. Proposed repair-decision approach

- Add a dedicated deterministic builder, for example `build_psca_repair_decision(validation_report) -> RepairDecisionResult`, and keep the executor thin.
- Replace the current repair model with this contract:
  - `RepairDecisionResult`
    - `overall_decision`
    - `recommended_target`
    - `recommended_next_stage`
    - `finding_routes`
    - `deferred_external_dependencies`
    - `evidence`
    - `rationale`
  - `RepairRouteTarget`
    - `none_required`
    - `resource_construction`
    - `bundle_finalization`
    - `build_plan_or_schematic`
    - `standards_validation_external`
    - `human_intervention`
  - `RepairFindingRoute`
    - `channel`
    - `severity`
    - `finding_code`
    - `route_target`
    - `recommended_next_stage`
    - `actionable`
    - `reason`
  - `RepairDecisionEvidence`
    - `source_validation_stage_id`
    - `source_overall_validation_status`
    - `routed_finding_codes`
    - `source_refs`
- Recommended route mapping from existing finding codes:
  - `external_profile_validation_deferred`
    - `route_target = standards_validation_external`
    - `recommended_next_stage = none`
    - `actionable = false`
    - reason: external standards validation has not run yet; this is not an internal repair
  - `bundle.type_is_document`
    - `route_target = bundle_finalization`
    - `recommended_next_stage = bundle_finalization`
    - `actionable = true`
  - `bundle.required_entries_present`
    - `route_target = bundle_finalization`
    - `recommended_next_stage = bundle_finalization`
    - `actionable = true`
  - `bundle.composition_first_placeholder`
    - `route_target = bundle_finalization`
    - `recommended_next_stage = bundle_finalization`
    - `actionable = true`
  - `bundle.first_entry_is_composition`
    - `route_target = bundle_finalization`
    - `recommended_next_stage = bundle_finalization`
    - `actionable = true`
  - `bundle.composition_type_matches_psca_summary`
    - `route_target = resource_construction`
    - `recommended_next_stage = resource_construction`
    - `actionable = true`
  - `bundle.required_sections_present`
    - `route_target = resource_construction`
    - `recommended_next_stage = resource_construction`
    - `actionable = true`
  - `bundle.deferred_fields_recorded`
    - if severity is `information`: `none_required`, non-actionable
    - if severity is `warning`: `bundle_finalization`, actionable
- Fallback routing rule:
  - any unknown `error` finding -> `human_intervention`
  - any unknown `warning` finding from `standards` -> `standards_validation_external`
  - any unknown `warning` finding from `workflow` -> `human_intervention`
  - informational findings default to `none_required`
- Overall-decision rule should be deterministic:
  - if any actionable internal repair route exists:
    - `overall_decision = repair_recommended`
    - `recommended_target` is chosen by severity/priority
  - else if no internal repair is needed but any `standards_validation_external` route exists:
    - `overall_decision = external_validation_pending`
    - `recommended_target = standards_validation_external`
  - else if all findings are informational/non-actionable:
    - `overall_decision = complete_no_repair_needed`
    - `recommended_target = none_required`
  - else if routing cannot safely classify an error:
    - `overall_decision = human_review_recommended`
    - `recommended_target = human_intervention`
- Recommended target-priority rule when multiple internal routes exist:
  1. `build_plan_or_schematic`
  2. `resource_construction`
  3. `bundle_finalization`
  4. `standards_validation_external`
  5. `none_required`
  This preserves the “smallest reasonable stage” principle while still allowing clearly structural issues to route higher if needed.
- For this slice, the current codebase likely will not emit `build_plan_or_schematic` findings yet. Keep that route in the enum and evidence model now so the next validation expansions do not require redesign.
- The current happy path should produce:
  - one non-actionable `standards_validation_external` route for `external_profile_validation_deferred`
  - one non-actionable `none_required` route for `bundle.deferred_fields_recorded`
  - `overall_decision = external_validation_pending`
  - `recommended_target = standards_validation_external`
  - `recommended_next_stage = none`
- Keep naming honest:
  - this stage makes a repair decision and routing recommendation
  - it does not execute repair

## 4. File-level change plan

- Update [src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py)
  - replace `RepairDecisionStub` with the real repair-decision models and keep `WorkflowSkeletonRunResult.repair_decision` pointing at the new type
- Create [src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/repair_decision_builder.py)
  - deterministic per-finding routing and overall decision logic
- Update [src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/executors.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/executors.py)
  - make `repair_decision` call the new builder
- Add [tests/test_psca_repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_repair_decision_builder.py)
  - direct deterministic coverage for routing logic and overall decision
- Update [tests/test_psca_bundle_builder_workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py)
  - assert the richer repair artifact shape and the expected happy-path routing decision
- Update [README.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md)
  - describe the richer repair-decision-stage output visible in Dev UI
- Update [docs/development-plan.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md)
  - targeted phase/focus/status changes after implementation succeeds

## 5. Step-by-step implementation plan

1. Replace the stub repair model first so the builder, executor, and smoke test all target one stable repair-decision contract.
2. Implement `build_psca_repair_decision(validation_report)` as a deterministic router over existing `ValidationFinding` records only. Do not re-read raw bundle artifacts.
3. Encode the exact per-code mappings above, with a small helper table keyed by finding `code`.
4. Implement fallback logic for unknown codes using `channel` plus `severity`:
   - unknown workflow `error` -> `human_intervention`
   - unknown workflow `warning` -> `human_intervention`
   - unknown standards `warning` -> `standards_validation_external`
   - informational -> `none_required`
5. Implement overall-decision synthesis:
   - compute per-finding routes
   - collect actionable internal routes
   - collect external-dependency routes
   - choose `recommended_target` from the priority order above
   - derive `recommended_next_stage`
6. For `recommended_next_stage`, use:
   - `resource_construction` for `resource_construction`
   - `bundle_finalization` for `bundle_finalization`
   - `build_plan` for `build_plan_or_schematic`
   - `none` for `none_required` and `standards_validation_external`
   - `none` for `human_intervention` in this slice, because no user-intervention stage exists yet
7. Build the repair-decision evidence from the validation report:
   - `validation.stage_id`
   - `validation.overall_status`
   - all routed finding codes
   - `source_refs`
8. Add a direct happy-path test that asserts:
   - `overall_decision == "external_validation_pending"`
   - `recommended_target == "standards_validation_external"`
   - the route for `external_profile_validation_deferred` is non-actionable and external
   - the route for `bundle.deferred_fields_recorded` is `none_required`
9. Add a direct failure-path test by constructing a validation report with:
   - one workflow `error` for `bundle.required_sections_present`
   - assert `overall_decision == "repair_recommended"`
   - assert `recommended_target == "resource_construction"`
   - assert the per-finding route points to `resource_construction`
10. Add one direct bundle-finalization-path test with a workflow `error` for `bundle.type_is_document` or `bundle.first_entry_is_composition` and assert routing goes to `bundle_finalization`.
11. Update the workflow smoke test so it asserts:
   - the repair stage emits the real repair-decision type
   - the current happy path yields `external_validation_pending`
   - no internal repair is recommended for the current validation result
12. Update README and development-plan wording after the implementation is green.

## 6. Definition of Done

- The `repair_decision` stage no longer emits a placeholder-only completion record; it emits a real structured repair-decision artifact.
- The repair artifact clearly distinguishes:
  - stage-level repair metadata
  - per-finding routing decisions
  - overall decision/status
  - deferred external dependencies
  - provenance/evidence
- Routing is deterministic and driven from structured validation findings, not message parsing or free-form reasoning.
- The stage can route at least to:
  - `none_required`
  - `resource_construction`
  - `bundle_finalization`
  - `build_plan_or_schematic`
  - `standards_validation_external`
  - `human_intervention`
- The current happy path yields:
  - no internal repair required
  - external standards validation still pending
  - an explicit routing recommendation reflecting that state
- Dev UI shows a richer repair-decision output that another engineer can inspect without reading source first.
- The workflow still runs end to end after this slice.
- What remains intentionally stubbed after this slice:
  - actual repair execution
  - mutation/retry loops
  - user-intervention workflow handling
  - broader repair history/iteration state
  - arbitrary-IG repair semantics

## 7. Risks / notes

- The main risk is routing too high in the workflow by default. The mapping should prefer the smallest reasonable stage and only escalate to `build_plan_or_schematic` or `human_intervention` when the finding truly cannot be safely handled lower.
- Another real risk is overloading the current validation codes with routing semantics they do not yet support. This slice should route only from stable existing codes and use a conservative fallback for unknown ones.
- The happy-path recommendation being `external_validation_pending` is intentional. It distinguishes “no internal repair needed” from “workflow is fully complete,” which will matter once Matchbox or another real standards validator is added.
- `human_intervention` should remain rare in this slice because the current finding set is small and deterministic.

## 8. Targeted `docs/development-plan.md` updates after implementation

- In Section 8, change `Current Focus` from repair-routing foundation to the first bounded repair-execution or targeted retry foundation using the structured repair decision.
- In Section 9, replace `Next Planned Slice` with a bounded follow-on such as: “Implement the first repair execution/retry foundation for bundle-finalization and resource-construction targets using the structured repair decision.”
- In Section 10, keep `Phase 7: Validation and Repair Routing Foundation` as `In Progress` unless the implementation also introduces meaningful repair execution behavior.
- In Section 10, update the Phase 7 notes/status to reflect that validation plus repair decision/routing now exist, but actual repair execution remains pending.
- In Section 12, add or refine the assumption that the first repair slice is recommendation-only and does not mutate workflow state or automatically rerun prior stages.
- In Section 13, add one concise risk only if observed during implementation: current validation finding codes may need one follow-up normalization step before they can support deeper repair execution without ad hoc mapping.
- In Section 16, update the immediate next objective to point at acting on structured repair recommendations rather than producing them.
