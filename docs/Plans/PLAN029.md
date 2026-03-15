# Medication-Specific Standards/Validation Alignment Hardening

**Summary**
- Keep medications-only multiplicity exactly as it is: up to two planned `MedicationRequest` entries, no allergies/problems expansion.
- Harden the current two-medication path in two narrow ways:
  - add one medication-specific **workflow** validation for final bundle-entry coherence against the planned medication placeholders
  - add two small **local standards** shape checks for duplicate `Bundle.entry.fullUrl` and duplicate `Bundle.entry.resource.id`, because same-type sibling medication entries make those failures more plausible now
- Keep current repair boundaries:
  - bundle-entry/final-bundle coherence failures -> `bundle_finalization`
  - medications section block/content/reference failures -> existing `finalize-composition-1-medications-section`
- Add a small candidate-bundle evidence improvement so Dev UI shows planned vs assembled medication placeholder ids directly.

## 1. Repo assessment

- The repo already has the right upstream bounded-medication inputs:
  - `NormalizedPatientContext.planned_medication_entries`
  - `NormalizedPatientContext.deferred_additional_medication_count`
- Schematic provenance already records:
  - planned medication display texts
  - planned medication placeholder count
  - placeholder-specific planned medication provenance
  - deferred medication overflow count
- Build planning and resource construction already support:
  - `build-medicationrequest-1`
  - `build-medicationrequest-2`
  - one medications section finalize step
  - deterministic ordered `Composition.section[medications].entry[]` attachment
- Candidate bundle finalization already assembles:
  - deterministic `entry_assembly`
  - deterministic bundle-entry ordering from schematic `bundle_entry` relationships
  - deterministic `fullUrl`s for both sibling medication resources when planned
- Workflow validation is already fairly strong for medications:
  - med1/med2 placeholder content checks
  - med1/med2 subject-reference contribution checks
  - med1/med2 exact fullUrl reference checks
  - medications section presence check
  - medications section exact entry-reference alignment check in scaffold order
- Repair routing is already mostly correct:
  - med1/med2 resource issues -> `build-medicationrequest-1` / `build-medicationrequest-2`
  - medications section entry-reference issues -> `finalize-composition-1-medications-section`
- The current fragile gap is narrower than the previous slice:
  - there is still no explicit validation that the **planned medication placeholders** are actually present in the **final candidate bundle entry assembly** in the expected order when one vs two meds are planned
  - if a planned medication bundle entry is missing or the final medication bundle-entry order drifts, current section-entry exact-alignment logic can suppress itself because expected fullUrls are no longer fully resolvable
  - the local standards validator still only checks generic scaffold shape and does not protect against duplicate `entry.fullUrl` or duplicate `resource.id`, which are now more relevant because same-type sibling `MedicationRequest` entries exist
  - Dev UI exposes raw `entry_assembly`, but does not yet expose a small medication-specific planned-vs-assembled bundle-entry summary
- Constraints that matter now:
  - no generic multiplicity engine
  - no Matchbox customization or profile-specific rule authoring
  - no multiplicity changes for allergies/problems
  - no redesign of workflow stages or retry orchestration

## 2. Proposed slice scope

- Keep medications multiplicity rule unchanged:
  - `0` or `1` structured medications -> `medicationrequest-1`
  - `2+` structured medications -> `medicationrequest-1`, `medicationrequest-2`
- Add one new medication-specific **workflow validation** for final bundle-entry coherence:
  - planned medication placeholder ids from schematic / normalized mapping
  - assembled medication placeholder ids in candidate bundle entry assembly
  - expected order must match exactly
  - both planned medication resources must exist as bundle entries with `resourceType = MedicationRequest`
- Add two narrow **local standards** checks:
  - `Bundle.entry.fullUrl` values must be unique
  - `Bundle.entry.resource.id` values must be unique
- Add one small **candidate-bundle evidence** improvement:
  - explicit planned medication placeholder ids
  - explicit assembled medication placeholder ids
- Keep existing medications section checks and repair ownership in place.
- Do not change:
  - normalized medication selection rules
  - build-plan step structure
  - resource-construction medications section finalization logic
  - Matchbox adapter behavior

## 3. Proposed medication-specific standards/validation hardening approach

- Add a new workflow finding code:
  - `bundle.medications_bundle_entries_aligned_to_plan`
- This new check should validate, when the medications section scaffold exists:
  - the planned medication placeholder ids are exactly `section_scaffold.entry_placeholder_ids`
  - the assembled medication placeholder ids are exactly the medication placeholders found in `candidate_bundle.entry_assembly`, in order
  - each planned medication placeholder is present in the final bundle with:
    - matching `resource.id`
    - `resourceType == "MedicationRequest"`
    - non-empty `fullUrl`
- Ownership for this new finding should be:
  - `bundle_finalization`
  - reason: this is a final bundle-entry assembly / ordering problem, not a section-finalize scaffold problem
- Keep the existing medications section findings unchanged in meaning:
  - `bundle.composition_medications_section_present`
    - still owned by `finalize-composition-1-medications-section`
    - continues to own section block title/code/entry-count presence
  - `bundle.composition_medications_section_entry_reference_aligned`
    - still owned by `finalize-composition-1-medications-section`
    - continues to own exact section-entry fullUrl alignment
- Add honest gating:
  - if `bundle.medications_bundle_entries_aligned_to_plan` fails, suppress `bundle.composition_medications_section_entry_reference_aligned`
  - reason: section-entry exact fullUrl alignment should not claim ownership when the expected medication bundle entries/fullUrls are not reliably present
- Add two local standards finding codes in the local scaffold validator:
  - `bundle.entry_fullurls_unique`
  - `bundle.entry_resource_ids_unique`
- These standards findings should route to:
  - `bundle_finalization`
  - reason: duplicate bundle entry ids/fullUrls are candidate-bundle assembly faults
- Add one small inspectability enhancement in candidate-bundle evidence:
  - `planned_medication_placeholder_ids`
  - `assembled_medication_placeholder_ids`
- What remains intentionally deferred:
  - arbitrary-length medication validation
  - allergies/problems multiplicity
  - generic section cardinality engines
  - Matchbox-side medication-specific rule tuning
  - generic standards/workflow ownership inference frameworks

## 4. File-level change plan

- Update [models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py)
  - extend `CandidateBundleEvidence` with planned vs assembled medication placeholder ids
- Update [bundle_finalization_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/bundle_finalization_builder.py)
  - populate those medication-specific evidence fields from schematic + entry assembly
- Update [validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/validation_builder.py)
  - add `bundle.medications_bundle_entries_aligned_to_plan`
  - gate medications section exact-alignment finding on that new bundle-entry coherence check
- Update [validation/standards.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/validation/standards.py)
  - add unique `fullUrl` and unique `resource.id` checks
- Update [repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/repair_decision_builder.py)
  - map the new workflow medication bundle-entry coherence finding to `bundle_finalization`
  - map the two new standards duplicate-entry findings to `bundle_finalization`
- Update tests:
  - [test_psca_bundle_finalization_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_finalization_builder.py)
  - [test_psca_validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_validation_builder.py)
  - [test_psca_repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_repair_decision_builder.py)
  - [test_psca_repair_execution_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_repair_execution_builder.py)
  - [test_psca_bundle_builder_workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py)
  - [test_matchbox_standards_validator.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_matchbox_standards_validator.py) only if shared standards-result expectations or check lists need updating
- Update docs:
  - [README.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md)
  - [docs/development-plan.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md)

## 5. Step-by-step implementation plan

1. Extend `CandidateBundleEvidence` with `planned_medication_placeholder_ids` and `assembled_medication_placeholder_ids`.
2. In `bundle_finalization_builder.py`, derive:
   - planned medication placeholder ids from the medications section scaffold
   - assembled medication placeholder ids from `entry_assembly`
   - populate both on the candidate-bundle evidence
3. In `validation_builder.py`, add a helper that:
   - reads planned medication placeholder ids from schematic
   - reads assembled medication placeholder ids from candidate-bundle evidence or `entry_assembly`
   - verifies exact ordered alignment
   - verifies each planned medication placeholder resolves to a bundle entry resource with `resourceType == MedicationRequest` and a non-empty `fullUrl`
4. Add new workflow finding code `bundle.medications_bundle_entries_aligned_to_plan` to `checks_run`.
5. Emit that finding when planned vs assembled medication bundle entries drift.
6. Gate `bundle.composition_medications_section_entry_reference_aligned` so it only runs when medication bundle-entry coherence already passed.
7. In `validation/standards.py`, add:
   - duplicate `entry.fullUrl` detection
   - duplicate `entry.resource.id` detection
   - corresponding `checks_run` entries and standards findings
8. In `repair_decision_builder.py`, add explicit routes:
   - `bundle.medications_bundle_entries_aligned_to_plan` -> `bundle_finalization`
   - `bundle.entry_fullurls_unique` -> `bundle_finalization`
   - `bundle.entry_resource_ids_unique` -> `bundle_finalization`
9. Update validation tests for medication-specific coherence:
   - one-med happy path -> no new finding
   - two-med happy path -> no new finding
   - swap medication bundle entries in final bundle assembly -> only `bundle.medications_bundle_entries_aligned_to_plan`
   - remove `medicationrequest-2` bundle entry when two are planned -> `bundle.medications_bundle_entries_aligned_to_plan`
   - break only medications section entry references while bundle entries remain correct -> existing `bundle.composition_medications_section_entry_reference_aligned` only
   - if medication bundle-entry coherence fails, the section-entry exact-alignment finding is suppressed
10. Update standards validator tests:
    - duplicate `entry.fullUrl` yields `bundle.entry_fullurls_unique`
    - duplicate `resource.id` yields `bundle.entry_resource_ids_unique`
11. Update repair-decision tests:
    - new workflow coherence finding routes to `bundle_finalization`
    - new standards duplicate-entry findings route to `bundle_finalization`
12. Update repair-execution tests:
    - a medication bundle-entry coherence failure reruns only `bundle_finalization`
    - a standards duplicate-entry error also recommends `bundle_finalization`
13. Update workflow smoke assertions:
    - candidate-bundle evidence shows planned vs assembled medication placeholder ids
    - happy path remains unchanged otherwise
14. Update README and `docs/development-plan.md` after tests are green.

## 6. Definition of Done

- The workflow still supports only bounded medications-only multiplicity up to two entries.
- The candidate bundle now exposes, in Dev UI, a direct medication-specific finalization summary:
  - planned medication placeholder ids
  - assembled medication placeholder ids
- Workflow validation now explicitly protects final medication bundle-entry coherence with:
  - `bundle.medications_bundle_entries_aligned_to_plan`
- Existing medications section findings remain in place, but exact section-entry fullUrl alignment no longer overclaims ownership when the real failure is missing/misordered medication bundle entries.
- Local standards validation now protects:
  - unique `Bundle.entry.fullUrl`
  - unique `Bundle.entry.resource.id`
- Repair ownership is explicit and narrow:
  - medication bundle-entry coherence failures -> `bundle_finalization`
  - duplicate bundle entry ids/fullUrls -> `bundle_finalization`
  - medications section block or exact section-entry reference failures -> existing medications section finalize step
- What remains bounded or deferred:
  - multiplicity beyond two medications
  - allergies/problems multiplicity
  - Matchbox-side medication-specific conformance hardening
  - generic section-validation engines

## 7. Risks / notes

- The main real risk is duplicating failure signals for the same underlying issue. The new medication bundle-entry coherence finding must suppress the downstream medications section exact-alignment finding when final bundle-entry expectations are not available.
- A second real risk is letting the local standards validator drift into workflow-specific medication planning logic. Standards checks here must stay neutral scaffold-shape checks only.
- A third real risk is routing new standards errors to human intervention by default. If the local standards validator gains duplicate-entry checks, `repair_decision_builder.py` must map them explicitly to `bundle_finalization`.
- A fourth real risk is over-expanding candidate-bundle evidence. Add only the small medication-specific planned-vs-assembled placeholder lists; do not turn evidence into a generic section-inventory framework.

## 8. Targeted `docs/development-plan.md` updates after implementation

- In Section 8, move `Current Focus` away from medication-specific standards/validation hardening and toward the next bounded post-hardening decision.
- In Section 9, set `Next Planned Slice` to the next narrow choice after this hardening, likely whether allergies/problems should remain fixed or whether medication-specific standards alignment should deepen further without adding multiplicity elsewhere.
- In Section 10, update the phase note to say the bounded medications-only path now has explicit final bundle-entry coherence validation and narrow standards-side duplicate-entry protection.
- In Section 12, refine the medication planning/validation assumption to say the workflow now validates both the authoritative first-two-item mapping and the final candidate-bundle medication entry assembly against that bounded plan.
- In Section 13, replace the current medication hardening risk with the next real remaining risk: the medications path is now structurally hardened for up to two entries, but broader multi-entry support still requires coordinated expansion across planning, construction, validation, and repair.
- In Section 16, update the immediate next objective away from medication-specific standards/validation hardening and toward the next bounded decision on whether other trio sections stay fixed or whether medication-specific hardening should continue in a still-narrow form.
