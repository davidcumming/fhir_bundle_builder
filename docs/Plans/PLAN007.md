## 1. Repo assessment

- The validation stage is still a pure stub in [executors.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/executors.py). It accepts `CandidateBundleResult` and emits `ValidationReportStub` with one canned informational finding and `outcome="placeholder_pass_with_warnings"`.
- The current validation models in [models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py) are too weak for the next slice. `ValidationFindingStub` only has `severity`, `location`, `message`, and `repair_target`; `ValidationReportStub` only has `outcome` and `findings`. There is no standards/workflow split, no validator identity, no overall summary, and no provenance beyond `source_refs`.
- The candidate-bundle stage is now strong enough to validate against. `CandidateBundleResult` already contains:
  - a real `Bundle`-shaped scaffold under `candidate_bundle.fhir_bundle`
  - deterministic `entry_assembly`
  - explicit deferred bundle fields
  - evidence linking back to bundle finalization, construction, build plan, and schematic
- The validation slice can rely on existing upstream artifacts without rereading raw PS-CA source files:
  - `CandidateBundleResult` for the actual bundle scaffold
  - `BundleSchematic` for required entries and expected Composition semantics
  - `NormalizedBuildRequest` for specification identity/version when preparing a standards-validation request
- There is no existing validator interface or validation package in the repo today. A search across `src/` and `docs/` shows only the stub report model and the guidance-level references to deterministic validation and a validation layer.
- The current workflow smoke test in [test_psca_bundle_builder_workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py) only asserts the placeholder `validation_report.outcome`. There is no direct unit test for validation logic or a standards-validator boundary yet.
- `docs/development-plan.md` now marks Phase 6 complete and sets validation as the current focus. The most relevant prior plan record is `docs/Plans/PLAN006.md`, because it established the real candidate bundle scaffold that validation should consume.
- Constraints that matter now:
  - keep validation deterministic
  - keep the standards validator behind a pluggable boundary
  - do not bind the stage to Matchbox-specific payloads
  - keep repair-routing out of scope
  - keep the validation foundation narrow and inspectable

## 2. Proposed slice scope

- Replace `ValidationReportStub` with the first real structured validation artifact.
- Keep this slice narrow:
  - define a pluggable standards-validator interface
  - implement one local standards-validator adapter that performs only narrow scaffold-shape checks
  - implement deterministic workflow/business-rule checks over the candidate bundle scaffold and schematic expectations
  - merge both channels into one inspectable validation stage artifact
- Recommended scope for standards validation in this slice:
  - local-only “candidate bundle scaffold shape” checks
  - no real FHIR profile validation
  - no terminology validation
  - no network calls
- Recommended scope for workflow/business-rule validation in this slice:
  - candidate bundle is `Bundle`-shaped
  - bundle `type` is `document`
  - required entries from the schematic are present
  - `Composition` is first
  - `Composition.type.coding[0]` matches `http://loinc.org|60591-5`
  - required sections exist for medications, allergies, and problems
  - deferred bundle fields `identifier`, `timestamp`, and `entry.fullUrl` are still explicitly tracked
- Out of scope after this slice:
  - Matchbox integration
  - full FHIR conformance validation
  - repair-routing logic
  - arbitrary-spec validation abstractions
  - any LLM-based judgment

## 3. Proposed validation approach

- Add a small validation package under `src/fhir_bundle_builder/validation/` to hold the pluggable standards-validator boundary and shared validation types.
- Use this standards-validator interface:
  - `StandardsValidationRequest`
    - `bundle_id`
    - `bundle_json`
    - `bundle_profile_url`
    - `specification_package_id`
    - `specification_version`
  - `StandardsValidator` protocol/interface
    - `validator_id: str`
    - `async validate(request: StandardsValidationRequest) -> StandardsValidationResult`
- Choose an async interface now. That keeps the local implementation simple while matching the future network-bound Matchbox integration path.
- Implement one local standards validator for this slice, for example `LocalCandidateBundleScaffoldStandardsValidator`.
  - What it validates:
    - top-level `resourceType == "Bundle"`
    - bundle `id` exists
    - `meta.profile[0]` exists
    - bundle `type` exists
    - `entry` exists and is a list
    - each entry has `resource.resourceType`
    - each entry resource has `id`
  - What it explicitly does not validate:
    - profile conformance
    - slicing/cardinality
    - terminology bindings
    - invariants
    - external package resolution
  - Its happy-path result should still be `passed_with_warnings`, because it must emit a warning that external standards/profile validation was not executed yet.
- Replace the stub validation models with these real types:
  - `ValidationSeverity = "information" | "warning" | "error"`
  - `ValidationStatus = "passed" | "passed_with_warnings" | "failed"`
  - `ValidationFinding`
    - `channel`: `standards | workflow`
    - `severity`
    - `code`
    - `location`
    - `message`
  - `StandardsValidationResult`
    - `validator_id`
    - `status`
    - `checks_run`
    - `findings`
    - `deferred_areas`
  - `WorkflowValidationResult`
    - `status`
    - `checks_run`
    - `findings`
    - `deferred_areas`
  - `ValidationEvidence`
    - `source_candidate_bundle_stage_id`
    - `source_schematic_stage_id`
    - `source_build_plan_stage_id`
    - `source_resource_construction_stage_id`
    - `validated_bundle_id`
    - `source_refs`
  - `ValidationReport`
    - `overall_status`
    - `standards_validation`
    - `workflow_validation`
    - `error_count`
    - `warning_count`
    - `information_count`
    - `deferred_validation_areas`
    - `evidence`
- Put workflow/business-rule validation in a dedicated builder, for example `build_psca_validation_report(candidate_bundle, schematic, normalized_request, standards_validator) -> ValidationReport`.
- Recommended workflow/business-rule findings in this slice:
  - error if bundle `type != "document"`
  - error if any `bundle_scaffold.required_entry_placeholder_ids` are absent from `entry_assembly`
  - error if the first assembled entry is not `composition-1`
  - error if the first entry’s resource is not `Composition`
  - error if Composition type system/code are not `http://loinc.org` / `60591-5`
  - error if required section titles/codes for medications, allergies, and problems are missing from the Composition scaffold
  - warning if expected deferred bundle fields are not explicitly tracked
  - information if those deferred bundle fields are present and still intentionally deferred
- Overall-status rule should be deterministic:
  - `failed` if any error exists in either channel
  - otherwise `passed_with_warnings` if any warning exists in either channel
  - otherwise `passed`
- Expected happy-path result for this slice:
  - `standards_validation.status = "passed_with_warnings"`
  - `workflow_validation.status = "passed"`
  - `overall_status = "passed_with_warnings"`
- Keep naming honest:
  - standards channel should call itself local scaffold validation, not conformance validation
  - overall report should say the candidate bundle scaffold passed narrow local checks, not full FHIR validation

## 4. File-level change plan

- Create [src/fhir_bundle_builder/validation/__init__.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/validation/__init__.py)
  - package marker and narrow exports
- Create [src/fhir_bundle_builder/validation/models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/validation/models.py)
  - shared validation-channel types and the standards-validation request type
- Create [src/fhir_bundle_builder/validation/standards.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/validation/standards.py)
  - `StandardsValidator` interface plus the local scaffold validator implementation
- Create [src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/validation_builder.py)
  - workflow/business-rule checks and assembly of the final `ValidationReport`
- Update [src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py)
  - replace `ValidationFindingStub` and `ValidationReportStub` with the real validation report type
- Update [src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/executors.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/executors.py)
  - make `validation` call the builder with the local standards validator
  - keep `repair_decision` stubbed, but update its input type to the new validation artifact
- Add [tests/test_psca_validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_validation_builder.py)
  - direct deterministic coverage for both validation channels and overall status
- Update [tests/test_psca_bundle_builder_workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py)
  - assert the richer validation artifact shape and expected happy-path statuses/findings
- Update [README.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md)
  - describe the richer validation-stage output visible in Dev UI
- Update [docs/development-plan.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md)
  - targeted phase/focus/status changes after implementation succeeds

## 5. Step-by-step implementation plan

1. Define the shared validation models and the standards-validator request/interface first so the workflow layer and local validator share one stable contract.
2. Replace `ValidationFindingStub` / `ValidationReportStub` in the workflow models with the real validation report type that references the shared channel-result models.
3. Implement the local standards validator adapter with these exact checks:
   - `Bundle.resourceType == "Bundle"`
   - `Bundle.id` exists
   - `Bundle.meta.profile[0]` exists
   - `Bundle.type` exists
   - `Bundle.entry` exists and is a list
   - every `entry.resource.resourceType` exists
   - every `entry.resource.id` exists
   - always add one warning stating that external standards/profile validation has not been executed
4. Implement the workflow/business-rule validator inside `validation_builder.py` using only:
   - `CandidateBundleResult`
   - `BundleSchematic`
   - `NormalizedBuildRequest`
   Do not re-read PS-CA raw files.
5. Use these exact workflow checks:
   - `bundle.type == "document"`
   - `bundle_scaffold.required_entry_placeholder_ids` are present in `entry_assembly`
   - first `entry_assembly.placeholder_id == "composition-1"`
   - first `entry.resource.resourceType == "Composition"`
   - Composition summary type system/code match `http://loinc.org` / `60591-5`
   - Composition includes sections corresponding to `medications`, `allergies`, and `problems`
   - `candidate_bundle.deferred_paths` contains `identifier`, `timestamp`, and `entry.fullUrl`
6. Build the final `ValidationReport` by:
   - running the standards validator
   - running workflow-rule validation
   - concatenating their deferred areas into `deferred_validation_areas`
   - computing `error_count`, `warning_count`, `information_count`
   - computing `overall_status` from the deterministic status rule above
   - populating evidence from `candidate_bundle.evidence`
7. Wire the local standards validator into the `validation` executor as the default implementation for this slice.
8. Keep `repair_decision` as a stub, but update its text so it refers to structured validation output rather than a placeholder-only report.
9. Add a direct validation-builder test for the happy path that asserts:
   - `standards_validation.validator_id == "local_candidate_bundle_scaffold_validator"`
   - `standards_validation.status == "passed_with_warnings"`
   - `workflow_validation.status == "passed"`
   - `overall_status == "passed_with_warnings"`
   - there is a warning about external standards/profile validation not being executed
   - there is an informational workflow finding confirming deferred bundle fields are explicitly tracked
10. Add one direct failure-path test by mutating the candidate bundle scaffold so `Composition` is not first or one required section is missing, and assert:
   - `workflow_validation.status == "failed"`
   - `overall_status == "failed"`
   - the failing rule emits a stable `code`
11. Update the workflow smoke test so it asserts:
   - the validation stage emits the real report type
   - happy-path status values match the expected split between standards/workflow channels
   - validation still runs end to end before `repair_decision`
12. Update README and development-plan wording after the implementation is green.

## 6. Definition of Done

- The `validation` stage no longer emits a stub-only placeholder report; it emits a real structured validation artifact.
- The validation artifact clearly distinguishes:
  - stage-level validation metadata
  - standards-validation results
  - workflow/business-rule validation results
  - overall summary/status
  - deferred validation areas
  - provenance/evidence
- A pluggable standards-validator interface exists in the codebase and the workflow uses a local implementation of it.
- The local standards validator is honest and narrow:
  - it validates only candidate bundle scaffold shape basics
  - it explicitly reports that external profile/conformance validation has not been executed
- Deterministic workflow/business-rule validation runs against the candidate bundle scaffold and catches:
  - wrong bundle type
  - missing required entries
  - wrong first entry
  - wrong Composition summary type
  - missing required sections
  - missing explicit deferred bundle fields
- Dev UI shows a richer validation-stage output with clearly separated channels and an overall result.
- The workflow still runs end to end after this slice.
- What remains intentionally stubbed after this slice:
  - Matchbox integration
  - full profile/conformance validation
  - terminology validation
  - repair-routing logic
  - arbitrary-IG validation support

## 7. Risks / notes

- The main scope risk is letting the local standards validator drift into a fake “full conformance” validator. It should stay explicitly limited to bundle-scaffold shape checks.
- The other real risk is duplicating the same check in both channels. The standards channel should own neutral scaffold-shape checks; the workflow channel should own document/workflow-specific expectations.
- Using an async validator interface is an intentional choice to avoid redesign when Matchbox becomes the first real external implementation.
- The expected happy-path overall status should remain `passed_with_warnings`, not `passed`, because no external profile/conformance validation has run yet.

## 8. Targeted `docs/development-plan.md` updates after implementation

- In Section 8, change `Current Focus` from validation foundation to the first bounded repair-routing foundation using the structured validation artifact.
- In Section 9, replace `Next Planned Slice` with a bounded Phase 7 follow-on such as: “Implement the first repair-decision and repair-routing foundation against the structured validation report.”
- In Section 10, keep `Phase 7: Validation and Repair Routing Foundation` as `In Progress` unless the implementation also delivers meaningful repair-routing behavior.
- In Section 10, mark only the validation portion of Phase 7 as proven by notes/status text; do not mark the whole phase `Completed` unless repair routing is also materially implemented.
- In Section 12, add or refine the assumption that the first validation slice intentionally uses a local scaffold-shape standards validator and defers full external conformance validation to a later Matchbox-backed implementation.
- In Section 13, add one concise risk only if observed during implementation: the initial workflow/business-rule checks may still need one follow-up refinement before they are sufficient to drive repair routing cleanly.
- In Section 16, update the immediate next objective to point at consuming the structured validation artifact for repair decision/routing rather than building validation itself.
