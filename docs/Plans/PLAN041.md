1. Repo assessment

- The current Dev UI wrapper flow already exposes the core artifacts needed to derive clearer readiness and failure interpretation:
  - authored patient/provider records
  - patient/provider refinement results
  - authored-input preparation with nested mapping results and compact workflow-input summary
  - final nested [`WorkflowSkeletonRunResult`](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py)
- The wrapper flow already has compact scan summaries for:
  - authored patient overview
  - authored provider overview
  - refinement overview
  - preparation overview
  - final demo summary
- What the current demo flow already shows well:
  - rich vs thin provider path
  - mapped/unmapped field counts at preparation time
  - edited/not-edited status
  - validation status and candidate bundle size in the final summary
- What failure/readiness interpretation is still weak:
  - there is no explicit pre-run readiness summary before the wrapper invokes the core workflow
  - unresolved authoring gaps and unmapped facts are visible, but not interpreted as “ready” versus “ready with limitations”
  - the final summary does not clearly distinguish:
    - structurally successful runs with low concern
    - successful runs with upstream limitations
    - successful runs where standards validation was deferred or fallback-based
    - incomplete/failed runs
  - repair/validation metadata exists downstream, but the wrapper does not currently turn it into a user-facing interpretation layer
- Constraints that matter now:
  - preserve all underlying full artifacts
  - do not change authoring, refinement, orchestration, validation, repair, or workflow semantics
  - keep the flow runnable even when readiness is limited
  - keep all new summaries derived/read-only inside the existing wrapper workflow

2. Proposed thin failure-handling / run-readiness scope

- Add one compact pre-run readiness summary at the `authored_bundle_preparation` stage.
- Add one richer final interpretation summary at the `bundle_builder_run` stage.
- Refine stage `summary` and `placeholder_note` text so limitation and deferred-validation states are obvious.
- Exact questions this slice should answer:
  - before run:
    - is this authored-input scenario ready to run cleanly, or ready with limitations?
    - are limitations coming from thin provider context, unresolved authored gaps, or unmapped authored facts?
  - after run:
    - did the run succeed with low concern?
    - did it succeed but remain limited by thin/unmapped/gap conditions?
    - did it succeed but still depend on deferred/fallback external standards validation?
    - did it fail or remain incomplete?
- Stages affected:
  - `authored_bundle_preparation`
  - `bundle_builder_run`
  - small summary-text refinement for `provider_authoring` and `authored_record_refinement` when limitations remain visible upstream
- What should remain deferred:
  - automatic run blocking
  - alerting/notification systems
  - validation redesign
  - new repair logic
  - any new workflow stage or domain behavior

3. Proposed summary/refinement architecture

- Keep the readiness/finality summary layer inside the existing wrapper workflow package:
  - [`models.py`](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_authored_bundle_demo_workflow/models.py)
  - [`executors.py`](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_authored_bundle_demo_workflow/executors.py)
- Add these new compact derived summary models:
  - `AuthoredBundleRunReadinessSummary`
    - `readiness_level`: `ready` | `ready_with_limitations`
    - `provider_path_mode`: `rich` | `thin`
    - `patient_unresolved_gap_count`
    - `provider_unresolved_gap_count`
    - `patient_unmapped_field_count`
    - `provider_unmapped_field_count`
    - `has_selected_provider_role_relationship`
    - `limitation_labels: list[str]`
  - `AuthoredBundleRunInterpretationSummary`
    - `interpretation_level`: `success_low_concern` | `success_with_limitations` | `success_external_validation_deferred` | `failure_or_incomplete`
    - `provider_path_mode`
    - `workflow_validation_status`
    - `overall_validation_status`
    - `standards_fallback_used`
    - `deferred_validation_area_count`
    - `repair_decision`
    - `repair_execution_outcome`
    - `limitation_labels: list[str]`
- Add these fields to wrapper artifacts:
  - `AuthoredBundleDemoStageResult.readiness_summary`
  - `AuthoredBundleDemoStageResult.run_interpretation_summary`
  - `AuthoredBundleDemoFinalSummary` enriched with:
    - `readiness_level`
    - `final_interpretation_level`
    - `standards_fallback_used`
    - `deferred_validation_area_count`
    - `patient_unresolved_gap_count`
    - `provider_unresolved_gap_count`
- Which stages expose which summaries:
  - `provider_authoring`
    - only refined stage text when thin-path or provider gaps are obvious
  - `authored_record_refinement`
    - refined stage text when edits still leave unresolved gaps
  - `authored_bundle_preparation`
    - expose `readiness_summary`
    - stage summary should explicitly call out `ready` vs `ready_with_limitations`
  - `bundle_builder_run`
    - expose `run_interpretation_summary`
    - enrich `final_summary`
- How limited/thin/deferred/warning states should be surfaced:
  - `thin provider path`
    - derived from existing provider-path logic already used in wrapper summaries
    - included in readiness and final interpretation summaries
  - `unresolved authoring gaps`
    - derived from effective patient/provider authored records
    - surfaced as counts plus short labels like `patient_gaps_remain`, `provider_gaps_remain`
  - `unmapped facts`
    - derived from `preparation.patient_mapping.unmapped_fields` and `preparation.provider_mapping.unmapped_fields`
    - surfaced as counts plus short labels like `patient_unmapped_facts`, `provider_unmapped_facts`
  - `deferred/fallback standards validation`
    - derived from `validation_report.standards_validation.fallback_used`
    - derived from `validation_report.deferred_validation_areas` and/or `standards_validation.deferred_areas`
    - surfaced as `external_validation_deferred` when present
  - `failure/incomplete`
    - derived from failed validation states and/or repair execution outcomes like `deferred` or `unsupported` when the run is not fully resolved
- Classification rules should be explicit and deterministic:
  - readiness:
    - `ready` when provider path is rich, unresolved gap counts are zero, and unmapped field counts are zero
    - `ready_with_limitations` otherwise
  - final interpretation precedence:
    1. `failure_or_incomplete` if workflow/overall validation is not passing or repair execution indicates unresolved incomplete outcome
    2. `success_external_validation_deferred` if standards fallback was used, deferred validation areas remain, or repair decision is `external_validation_pending`
    3. `success_with_limitations` if run passed but thin path, unresolved gaps, or unmapped facts remain
    4. `success_low_concern` otherwise
- The flow should remain runnable despite limited readiness.
  - readiness is advisory only
  - no blocking gate should be added in this slice
- Full artifacts remain visible:
  - keep existing authored records, refinement results, preparation, validation report, repair decision, repair execution, and workflow output unchanged
  - summaries are additive only

4. File-level change plan

- Update [models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_authored_bundle_demo_workflow/models.py)
  - add `AuthoredBundleRunReadinessSummary`
  - add `AuthoredBundleRunInterpretationSummary`
  - add optional readiness/finality summary fields to `AuthoredBundleDemoStageResult`
  - enrich `AuthoredBundleDemoFinalSummary`
- Update [executors.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_authored_bundle_demo_workflow/executors.py)
  - add pure helper functions to derive readiness and final interpretation from existing artifacts
  - refine stage `summary` and `placeholder_note` text at preparation and final-run stages
  - lightly refine upstream stage text when thin/gap states remain obvious
- Update [test_psca_authored_bundle_demo_workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_authored_bundle_demo_workflow.py)
  - assert readiness and final interpretation summaries for the canonical rich and thin scenarios
  - assert deferred/fallback external-validation signaling when present in the nested workflow result
- Update [README.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md)
  - document the new readiness and final interpretation summaries
- Update [development-plan.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md)
  - move focus to failure-handling/run-readiness summary refinement

5. Step-by-step implementation plan

1. Add the two new derived summary models to the wrapper workflow models.
2. Enrich `AuthoredBundleDemoFinalSummary` with readiness/finality fields instead of creating a second final summary object.
3. Add pure helper functions in `executors.py` for:
   - deriving limitation labels from effective authored records and preparation results
   - deriving `AuthoredBundleRunReadinessSummary`
   - deriving `AuthoredBundleRunInterpretationSummary`
4. Implement readiness derivation in the preparation stage.
   - use effective refined records plus preparation unmapped-field counts
   - classify `ready` vs `ready_with_limitations`
   - include short limitation labels such as:
     - `thin_provider_path`
     - `patient_gaps_remain`
     - `provider_gaps_remain`
     - `patient_unmapped_facts`
     - `provider_unmapped_facts`
5. Refine the `authored_bundle_preparation` stage text.
   - summary should start with `Ready to run` or `Ready to run with limitations`
   - placeholder note should mention the dominant limitation class when present
6. Implement final interpretation derivation in the final run stage.
   - read from:
     - `validation_report`
     - `repair_decision`
     - `repair_execution`
     - preparation/readiness context
   - apply the explicit precedence rules above
7. Refine the `bundle_builder_run` stage text.
   - summary should clearly say one of:
     - `Run completed with low concern`
     - `Run completed with limitations`
     - `Run completed but external validation remains deferred`
     - `Run incomplete or failed`
   - placeholder note should mention the primary reason when not low-concern
8. Lightly refine upstream `provider_authoring` and `authored_record_refinement` notes so thin-path and unresolved-gap signals are easier to spot before preparation.
9. Update the wrapper smoke tests.
   - rich canonical scenario:
     - assert readiness summary exists
     - assert provider path is `rich`
     - assert final interpretation is derived consistently from current standards-validation behavior
     - if deferred/fallback validation is present in current nested result, assert `success_external_validation_deferred`
   - thin canonical scenario:
     - assert readiness is `ready_with_limitations`
     - assert limitation labels include thin-path and provider unmapped/gap visibility
     - assert final interpretation is not `success_low_concern`
10. Update README and development plan after tests are green.

6. Definition of Done

- The existing wrapper flow and stage sequence remain unchanged.
- Before the wrapper invokes the core workflow, the preparation stage exposes a clear typed readiness summary.
- After the core workflow completes, the final stage exposes a clear typed run-interpretation summary that distinguishes:
  - success with low concern
  - success with limitations
  - success with deferred/fallback external validation
  - failure or incomplete run
- Stage text now makes limitation states easier to understand without opening every nested artifact.
- Full underlying authored, preparation, validation, repair, and workflow artifacts remain visible and unchanged in role.
- The flow remains runnable even when readiness is limited.
- Tests prove the canonical rich and thin demo scenarios surface different readiness/finality interpretations in a stable way.
- What becomes clearer in the demo flow:
  - whether a scenario is ready to run cleanly
  - whether thin provider context or unmapped facts are limiting trust
  - whether a successful run is still warning-bearing or externally deferred
- Still out of scope:
  - run blocking
  - alerting systems
  - validation redesign
  - repair redesign
  - new workflow stages
  - separate frontend architecture

7. Risks / notes

- The main risk is turning readiness summaries into a de facto enforcement engine. Keep them advisory-only in this slice.
- A second risk is duplicating downstream business logic in wrapper summary helpers. Final interpretation should derive directly from existing validation/repair artifacts, not invent new semantics.
- A third risk is unstable tests if deferred/fallback standards validation depends on environment. The implementation should assert against the actual nested workflow-result fields produced by the canonical scenarios, not hardcode assumptions beyond the explicit interpretation precedence.
- A fourth risk is overcompressing nuance into one label. Preserve short limitation labels plus the full underlying artifacts.

8. Targeted `docs/development-plan.md` updates after implementation

- Section 8 `Current Focus`
  - change to: implement a thin failure-handling and run-readiness summary refinement pass for the Dev UI authored-input wrapper flow so demo runs are easier to trust and interpret
- Section 9 `Next Planned Slice`
  - change to: after run-readiness/finality refinement, decide whether to add one more narrow demo-usability pass or return to a workflow-quality/documentation-focused slice
- Section 10 Phase 8 note
  - append that the Dev UI authored-input demo flow now includes derived pre-run readiness and final run-interpretation summaries without changing the underlying workflow behavior
- Section 12 `Known Early Assumptions`
  - add that wrapper-level readiness summaries are advisory only and do not block execution in the first slice
  - add that final interpretation labels are derived from existing validation, repair, and standards-validation artifacts rather than new workflow semantics
- Section 13 `Known Early Risks`
  - add that readiness/finality summaries may become an alternate enforcement layer unless they remain strictly derived and non-blocking
  - add that environment-sensitive standards-validation fallback/deferred behavior may make summary expectations brittle unless tests assert directly on produced nested artifacts
- Section 16 `Immediate Next Objective`
  - update to: complete the thin failure-handling and run-readiness summary refinement pass and prove the authored-input demo flow surfaces ready, limited, deferred, and incomplete outcomes clearly while keeping the full underlying artifacts visible
