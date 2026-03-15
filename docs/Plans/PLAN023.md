# Non-Composition Exact Reference Ownership Reassessment

**Summary**
- The repo should **not** move the current non-Composition exact `urn:uuid:` alignment findings themselves to `resource_construction`.
- The narrow, correct slice is to **add a preceding source-reference-contribution validation layer** for the same five paths, route those new findings to `resource_construction`, and keep the existing exact fullUrl findings `bundle_finalization`-owned.
- This gives precise ownership without introducing a generic reference graph engine: source-local placeholder reference failures become `resource_construction` problems; final `urn:uuid:` rewrite failures remain `bundle_finalization` problems.

## 1. Repo assessment
- The current non-Composition exact-alignment findings are already split in [validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/validation_builder.py):
  - `bundle.practitionerrole_practitioner_reference_aligned`
  - `bundle.practitionerrole_organization_reference_aligned`
  - `bundle.medicationrequest_subject_reference_aligned`
  - `bundle.allergyintolerance_patient_reference_aligned`
  - `bundle.condition_subject_reference_aligned`
- All five currently route to `bundle_finalization` in [repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/repair_decision_builder.py).
- `resource_construction` already records deterministic source-reference provenance for these paths:
  - `build-practitionerrole-1` contributes:
    - `practitioner.reference -> practitioner-1`
    - `organization.reference -> organization-1`
  - `build-medicationrequest-1` contributes:
    - `subject.reference -> patient-1`
  - `build-allergyintolerance-1` contributes:
    - `patient.reference -> patient-1`
  - `build-condition-1` contributes:
    - `subject.reference -> patient-1`
- `bundle_finalization` still rewrites all of those references generically from `ReferenceContribution` records to final `urn:uuid:` fullUrls in [bundle_finalization_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/bundle_finalization_builder.py).
- Current artifact maturity is better than when the original ownership decision was made:
  - `resource_construction` keeps `resource_registry`
  - `resource_construction.step_result_history` preserves the latest `ReferenceContribution` records
  - `repair_execution` already supports both `resource_construction` and `bundle_finalization` retry paths
  - the `validation` executor can already read workflow state, so it can be given `resource_construction` without changing the stage graph
- The current gap is specific:
  - validation only inspects the final candidate bundle, so it cannot distinguish:
    - wrong local placeholder-style reference contribution from `resource_construction`
    - correct local contribution but wrong final fullUrl rewrite in `bundle_finalization`
- Because of that, the current exact fullUrl findings are still honestly bundle-finalization-owned today.
- The repo now has enough deterministic artifacts to refine attribution safely, but only by adding a source-contribution check layer rather than reassigning the existing exact fullUrl findings directly.

## 2. Proposed slice scope
- Keep the current five exact fullUrl findings in place and keep them `bundle_finalization`-owned.
- Add five new **source-reference-contribution** findings for the same paths:
  - `bundle.practitionerrole_practitioner_reference_contribution_aligned`
  - `bundle.practitionerrole_organization_reference_contribution_aligned`
  - `bundle.medicationrequest_subject_reference_contribution_aligned`
  - `bundle.allergyintolerance_patient_reference_contribution_aligned`
  - `bundle.condition_subject_reference_contribution_aligned`
- Route those five new source-contribution findings to `resource_construction` using existing step boundaries:
  - both PractitionerRole reference-contribution findings -> `build-practitionerrole-1`
  - MedicationRequest subject contribution -> `build-medicationrequest-1`
  - AllergyIntolerance patient contribution -> `build-allergyintolerance-1`
  - Condition subject contribution -> `build-condition-1`
- Suppress the existing exact fullUrl finding for a path when the source-contribution finding for that same path already failed.
- Keep this slice narrow:
  - no bundle-finalization redesign
  - no generic provenance engine
  - no element-level patching
  - no model expansion beyond what is needed to thread `resource_construction` into validation

## 3. Proposed non-Composition exact fullUrl ownership approach
- Ownership should become **split by failure class**, not by resource class:
  - **source-local reference contribution failures** -> `resource_construction`
  - **final exact fullUrl rewrite failures** -> `bundle_finalization`
- The existing exact fullUrl findings should remain unchanged in meaning:
  - they still validate final `urn:uuid:` alignment in the assembled candidate bundle
  - they remain honest only as `bundle_finalization` findings
- New source-contribution findings should validate deterministic local placeholder-style references before fullUrl rewrite:
  - `PractitionerRole.practitioner.reference == "Practitioner/practitioner-1"`
  - `PractitionerRole.organization.reference == "Organization/organization-1"`
  - `MedicationRequest.subject.reference == "Patient/patient-1"`
  - `AllergyIntolerance.patient.reference == "Patient/patient-1"`
  - `Condition.subject.reference == "Patient/patient-1"`
- Source-contribution validation should use both existing artifacts from `resource_construction`:
  - the latest scaffold in `resource_registry`
  - the latest `ReferenceContribution` entry in `step_result_history`
- Recommended gating behavior:
  - if bundle `entry.fullUrl` values are missing, keep `bundle.entry_fullurls_present` as the owner and suppress the existing exact fullUrl findings, as today
  - if the source-contribution check for a path fails, emit only the new source-contribution finding for that path and suppress the exact fullUrl finding
  - if the source-contribution check for a path passes but the final bundle reference is wrong, emit the existing exact fullUrl finding
- This gives a precise, inspectable attribution chain:
  - local reference generation is wrong -> rerun the resource-construction step that owns that path
  - local reference generation is correct but final fullUrl is wrong -> rerun only bundle finalization
- What remains intentionally deferred:
  - generic provenance modeling for future resource types
  - generic graph-based ownership inference
  - element-level repair semantics
  - revisiting Composition section-entry ownership, which is already in a better place because those paths have section-specific finalize steps

## 4. File-level change plan
- Update [validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/validation_builder.py)
  - accept `ResourceConstructionStageResult`
  - add five source-contribution checks
  - gate the existing exact fullUrl findings so they only fire when source contribution is already correct
- Update [executors.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/executors.py)
  - make the `validation` executor pull `resource_construction` from workflow state and pass it into `build_psca_validation_report(...)`
- Update [repair_execution_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/repair_execution_builder.py)
  - pass the post-retry `resource_construction` result into validation during retry execution
- Update [repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/repair_decision_builder.py)
  - add the five new source-contribution finding routes
  - map them to the existing resource-construction step subset directives
  - keep the existing exact fullUrl routes on `bundle_finalization`
- Update tests:
  - [test_psca_validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_validation_builder.py)
  - [test_psca_repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_repair_decision_builder.py)
  - [test_psca_repair_execution_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_repair_execution_builder.py)
  - [test_psca_bundle_builder_workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py) only if visible validation findings or inspectability assertions need updating
- Update docs:
  - [README.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md)
  - [docs/development-plan.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md)
- No changes to:
  - `bundle_finalization_builder.py`
  - `resource_construction_builder.py`
  - workflow graph shape
  - models, unless implementation needs one very small helper type alias and nothing more

## 5. Step-by-step implementation plan
1. Extend `build_psca_validation_report(...)` and `_build_workflow_validation_result(...)` to accept `resource_construction`.
2. Add a small validation helper that resolves the current local reference value for one placeholder/path from:
   - `resource_registry.current_scaffold.fhir_scaffold`
   - matching `ReferenceContribution` data from `step_result_history`
3. Implement five source-contribution checks:
   - PractitionerRole practitioner
   - PractitionerRole organization
   - MedicationRequest subject
   - AllergyIntolerance patient
   - Condition subject
4. Add five new workflow finding codes to `checks_run`.
5. Gate the existing exact fullUrl checks:
   - only emit them when expected entry fullUrls are assessable
   - only emit them when the matching source-contribution check already passed
6. Update the `validation` executor to load `resource_construction` from state and pass it into validation.
7. Update retry execution so post-retry validation also receives the post-retry `resource_construction` result.
8. Update repair routing:
   - add the five new source-contribution codes to `_FINDING_ROUTE_MAP`
   - map them to `resource_construction`
   - add directive mappings:
     - PractitionerRole contribution findings -> `["build-practitionerrole-1"]`
     - MedicationRequest subject contribution -> `["build-medicationrequest-1"]`
     - AllergyIntolerance patient contribution -> `["build-allergyintolerance-1"]`
     - Condition subject contribution -> `["build-condition-1"]`
   - leave the existing exact fullUrl codes on `bundle_finalization`
9. Update validation tests:
   - break only the local `PractitionerRole.practitioner` reference contribution -> only `bundle.practitionerrole_practitioner_reference_contribution_aligned`
   - break only the local `PractitionerRole.organization` reference contribution -> only `bundle.practitionerrole_organization_reference_contribution_aligned`
   - break only the local `MedicationRequest.subject` reference contribution -> only `bundle.medicationrequest_subject_reference_contribution_aligned`
   - break only the local `AllergyIntolerance.patient` reference contribution -> only `bundle.allergyintolerance_patient_reference_contribution_aligned`
   - break only the local `Condition.subject` reference contribution -> only `bundle.condition_subject_reference_contribution_aligned`
   - break only the final bundle fullUrl reference while leaving source contribution correct -> existing exact fullUrl finding only
   - missing `fullUrl` still stays owned by `bundle.entry_fullurls_present`
10. Update repair-decision tests:
   - each new contribution finding routes to `resource_construction`
   - the corresponding directive targets only the owning build step
   - combined contribution findings union in build-plan order
   - combined exact fullUrl findings still keep `bundle_finalization` ownership
11. Update repair-execution tests:
   - one source-contribution failure reruns only the owning resource-construction step and then downstream bundle finalization/validation/repair decision
   - one exact fullUrl failure still reruns only bundle finalization/validation/repair decision
   - combined contribution + exact fullUrl mutation on the same path should prefer the source-contribution route because the exact check is suppressed until source is correct
12. Update docs to explain the refined ownership split and why exact fullUrl findings still remain bundle-finalization-owned.
13. Run the full test suite and confirm the old non-Composition exact fullUrl tests still pass with the new paired source-contribution layer.

## 6. Definition of Done
- The five current non-Composition exact fullUrl findings have been explicitly reviewed and remain `bundle_finalization`-owned.
- Validation now also emits five new source-contribution findings for the same paths when local placeholder-style references are wrong.
- Dev UI now makes the ownership distinction visible:
  - source-reference contribution failure
  - final exact fullUrl rewrite failure
- A wrong local non-Composition reference now routes to targeted `resource_construction` repair using the existing owning step:
  - `build-practitionerrole-1`
  - `build-medicationrequest-1`
  - `build-allergyintolerance-1`
  - `build-condition-1`
- A wrong final `urn:uuid:` reference with correct local source contribution still routes to `bundle_finalization`.
- Existing exact fullUrl findings no longer overclaim ownership when the true fault is in source-reference generation.
- What remains unchanged or deferred:
  - the exact fullUrl rewrite logic itself
  - the `bundle_finalization` retry path
  - generic provenance or graph ownership infrastructure
  - arbitrary future-resource ownership logic

## 7. Risks / notes
- The main real risk is duplicating ownership findings for the same path. The exact fullUrl check must be suppressed whenever the source-contribution check already failed.
- A second real risk is reading stale construction state during retry validation. Post-retry validation must use the post-retry `resource_construction` artifact, not the pre-retry one.
- A third real risk is overextending the pattern into a generic engine. This slice should stay hard-coded to the current five non-Composition paths only.
- A fourth real risk is weakening the honesty of the exact fullUrl codes. They should stay bundle-finalization-owned because they still describe the final assembled bundle, not local scaffold state.

## 8. Targeted `docs/development-plan.md` updates after implementation
- In Section 8, change `Current Focus` away from non-Composition exact fullUrl ownership reassessment to the next bounded realism or validation/repair slice.
- In Section 9, replace `Next Planned Slice` with the next bounded follow-on after this ownership refinement, likely a realism slice or another remaining grouped-validation gap.
- In Section 10, update the Phase 8 note to say non-Composition reference ownership is now split between source-reference contribution validation in `resource_construction` and exact fullUrl rewrite validation in `bundle_finalization`.
- In Section 12, refine the repair assumption to say current repo maturity now supports attribution of the current non-Composition reference paths at two layers: source contribution vs final rewrite.
- In Section 13, replace the current non-Composition ownership risk with the next real remaining risk: this ownership split is still intentionally hard-coded to the current fixed PS-CA reference paths and does not yet generalize to arbitrary future resource graphs.
- In Section 16, update the immediate next objective away from non-Composition exact fullUrl ownership reassessment and toward the next bounded realism or remaining ownership/validation refinement slice.
