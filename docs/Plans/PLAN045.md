## First Core Workflow-Quality Hardening Slice: Effective Final Outcome Surfacing After Bounded Retry

### 1. Repo assessment

- The core workflow is already strong at:
  - deterministic staged execution from normalized request through repair execution
  - explicit typed artifacts for schematic, plan, construction, bundle, validation, repair decision, and retry execution
  - bounded retry semantics that are already narrow, testable, and inspectable
  - honest handling of deferred external validation and bounded provider/patient semantics
- The strongest remaining narrow quality gap is:
  - after a bounded retry executes, the core workflow still exposes the original first-pass `resource_construction`, `candidate_bundle`, `validation_report`, and `repair_decision` as the top-level run artifacts, while the corrected post-retry artifacts remain nested under `repair_execution`
- Why this gap should come next:
  - it is a real trust/maintainability issue in the **core workflow contract**, not a wrapper concern
  - it forces downstream readers to manually reconstruct the “effective final state” from retry internals
  - it does not require new domain behavior, broader semantics, or redesign of the workflow loop
  - it directly improves the truthfulness of the final run output while preserving inspectability of the original first-pass artifacts
- Constraints that matter now:
  - preserve the original stage artifacts for inspectability
  - do not change validation, repair-decision, or retry semantics
  - keep bounded retry single-pass
  - keep the change additive and typed

### 2. Proposed first narrow core workflow-quality hardening scope

- Implement one bounded slice: **effective final outcome surfacing after bounded retry**.
- Exact slice:
  - add an explicit typed “effective final outcome” artifact to the core workflow run result
  - populate it from original artifacts when no retry executes
  - populate it from post-retry artifacts when a bounded retry executes
- Why this is the best first Phase 9 slice:
  - it improves trust in the core workflow’s final output without changing the workflow’s business behavior
  - it closes a current interpretability gap at the precise point where workflow quality matters most: the final artifact set after repair execution
  - it uses the retry machinery the repo already has, rather than expanding workflow breadth
- What should remain deferred:
  - multi-pass or recursive retry loops
  - new retry targets
  - validation/repair policy changes
  - standards-validation expansion
  - wrapper/demo changes
  - replacing original first-pass artifacts with post-retry artifacts

### 3. Proposed hardening architecture

- Add one new additive typed model to the core workflow models:
  - `WorkflowEffectiveOutcome`
- Recommended shape:
  - `artifact_source: Literal["initial_run", "post_retry"]`
  - `resource_construction: ResourceConstructionStageResult`
  - `candidate_bundle: CandidateBundleResult`
  - `validation_report: ValidationReport`
  - `repair_decision: RepairDecisionResult`
- Add `effective_outcome: WorkflowEffectiveOutcome` to `WorkflowSkeletonRunResult`.
- Keep existing contracts unchanged in role:
  - `resource_construction`, `candidate_bundle`, `validation_report`, and `repair_decision` continue to represent the original first-pass stage artifacts
  - `repair_execution` continues to hold the retry-execution artifact and any nested post-retry artifacts
- Add one pure helper in the core workflow package, preferably in `repair_execution_builder.py`, to derive the effective final outcome from:
  - original first-pass artifacts
  - `RepairExecutionResult`
- Helper rules should be explicit:
  - `execution_outcome != "executed"` -> `artifact_source="initial_run"` and use original artifacts
  - executed `bundle_finalization` retry -> preserve original `resource_construction`, promote post-retry bundle/validation/repair-decision artifacts
  - executed `resource_construction` retry -> promote post-retry `resource_construction`, bundle, validation, and repair-decision artifacts
- Trust safeguard:
  - if `execution_outcome == "executed"` but required post-retry artifacts are missing, raise a runtime error instead of silently falling back to originals
- Keep the slice bounded:
  - no new workflow stages
  - no changes to retry routing
  - no changes to validation finding semantics
  - only final-output surfacing and minimal docs alignment

### 4. File-level change plan

- Update `/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py`
  - add `WorkflowEffectiveOutcome`
  - add `effective_outcome` to `WorkflowSkeletonRunResult`
- Update `/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/repair_execution_builder.py`
  - add the pure helper that resolves the effective final artifact set from first-pass artifacts plus `RepairExecutionResult`
- Update `/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/executors.py`
  - populate `effective_outcome` when yielding `WorkflowSkeletonRunResult`
- Update `/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_repair_execution_builder.py`
  - add direct tests for effective-outcome resolution in no-retry and executed-retry cases
- Update `/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py`
  - keep the current happy-path assertions
  - add workflow-level coverage proving the final run result exposes post-retry effective artifacts when a retry executes
- Update `/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md`
  - note that the final nested run result now exposes an effective final outcome view in addition to the original first-pass artifacts
- Update `/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/operator-guidance.md`
  - clarify how to interpret original first-pass artifacts versus the new effective final outcome in the core workflow
- Update `/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md`
  - move current focus to this first narrow Phase 9 hardening slice

### 5. Step-by-step implementation plan

1. Add `WorkflowEffectiveOutcome` to the core workflow models and attach it to `WorkflowSkeletonRunResult`.
2. Implement a pure helper in `repair_execution_builder.py` to select the effective final artifacts.
3. Make the helper strict about executed retries.
   - if retry execution says `executed`, require the needed post-retry artifacts to exist
   - do not silently downgrade to first-pass artifacts
4. Update `executors.py` so the final `WorkflowSkeletonRunResult` always includes:
   - original first-pass artifacts
   - `repair_execution`
   - `effective_outcome`
5. Add builder-level tests in `tests/test_psca_repair_execution_builder.py`.
   - one no-retry/deferred case should resolve to `artifact_source="initial_run"`
   - one executed `resource_construction` retry case should resolve to `artifact_source="post_retry"` and use post-retry artifacts
6. Add one workflow-level retry-path test in `tests/test_psca_bundle_builder_workflow.py`.
   - monkeypatch the first-pass bundle-finalization builder reference inside `executors.py` to emit a broken initial candidate bundle
   - let `repair_execution_builder.py` use the real unpatched builder for the retry
   - assert:
     - original top-level `candidate_bundle` is broken
     - original top-level `repair_decision` is `repair_recommended`
     - `repair_execution.execution_outcome == "executed"`
     - `effective_outcome.artifact_source == "post_retry"`
     - `effective_outcome.candidate_bundle` is corrected
     - `effective_outcome.validation_report` is passing-with-warnings
     - `effective_outcome.repair_decision.overall_decision == "external_validation_pending"`
7. Update the existing happy-path workflow smoke test to assert:
   - `effective_outcome.artifact_source == "initial_run"`
   - `effective_outcome.validation_report` matches the current first-pass report semantics
8. Update README and operator guidance with short, truthful interpretation notes.
9. Update `docs/development-plan.md` after tests are green.

### 6. Definition of Done

- The core workflow run result exposes a typed effective final outcome without removing the original first-pass artifacts.
- A consumer of `WorkflowSkeletonRunResult` can now read one canonical final artifact set after bounded retry execution.
- Original first-pass artifacts remain visible and unchanged in role.
- Executed retries no longer require downstream consumers to manually interpret nested `repair_execution.post_retry_*` artifacts to understand final workflow state.
- Workflow-level trust is improved because the final run contract now distinguishes:
  - original first-pass artifacts
  - effective final artifacts after the single bounded retry pass
- Tests prove:
  - no-retry runs resolve to `initial_run`
  - executed retries resolve to `post_retry`
  - the effective outcome surfaces corrected post-retry artifacts while preserving originals
- Still out of scope:
  - multi-pass retry loops
  - retry-policy changes
  - broader standards-validation behavior
  - wrapper/demo changes
  - domain/semantic expansion

### 7. Risks / notes

- The main risk is accidentally replacing original first-pass artifacts instead of adding an effective final view. Preserve both.
- A second risk is silently falling back to original artifacts when an executed retry is missing post-retry outputs. Treat that as an internal error instead.
- A third risk is over-expanding this into broader retry redesign. Keep it strictly to final-output surfacing.
- A fourth risk is brittle workflow-level retry testing. The monkeypatch should target only the first-pass executor path so the retry path still exercises the real builder code.

### 8. Targeted `docs/development-plan.md` updates after implementation

- Section 8 `Current Focus`
  - change to: implement the first narrow Phase 9 core workflow-quality hardening slice by surfacing an explicit effective final outcome after bounded retry execution
- Section 9 `Next Planned Slice`
  - change to: after effective-final-outcome hardening, choose the next narrow core workflow-quality slice rather than returning to wrapper/demo consolidation
- Section 10 `Phase 8` note
  - append that the core workflow now preserves original first-pass artifacts while also surfacing an explicit effective final artifact set after bounded retry execution
- Section 12 `Known Early Assumptions`
  - add that the core workflow should preserve original first-pass stage artifacts for inspectability while exposing a separate effective final outcome when a bounded retry executes
  - add that effective final outcome surfacing is additive only and does not redefine retry semantics or introduce multi-pass repair
- Section 13 `Known Early Risks`
  - add that consumers may misread first-pass artifacts as the final workflow state unless the run result exposes an explicit effective final outcome after retry
  - add that additive final-outcome surfacing can become misleading if executed retries are allowed to omit required post-retry artifacts without failing loudly
- Section 16 `Immediate Next Objective`
  - update to: complete the first narrow core workflow-quality hardening slice by making the final core workflow output trustworthy to interpret after bounded retry execution while preserving the original first-pass artifacts
