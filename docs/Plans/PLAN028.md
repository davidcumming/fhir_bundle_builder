## 1. Repo assessment

- The two-medication path already exists end to end:
  - `NormalizedPatientContext.medications` preserves ordered structured medication input.
  - schematic planning conditionally emits `medicationrequest-1` and `medicationrequest-2`.
  - build planning conditionally emits `build-medicationrequest-2`.
  - resource construction builds both sibling `MedicationRequest` resources and the medications section can now attach two entries.
  - validation and repair routing already distinguish first vs second medication for content and subject-reference failures.
- The current weak point is not missing multiplicity support; it is **duplicated first-two selection logic** and **thin placeholder-specific provenance**:
  - the “first two medications in normalized list order” rule is re-derived in schematic generation, resource construction, and validation rather than normalized once upstream.
  - Dev UI evidence shows planned texts and counts, but not a clean placeholder-to-source-item mapping by `medication_id` and source index.
  - truncation when `available medication count > 2` is inspectable only indirectly, not as an explicit structured fact.
- The build-plan and repair boundaries are already mostly correct:
  - `build-medicationrequest-1` and `build-medicationrequest-2` own sibling resource content/source-reference failures.
  - `finalize-composition-1-medications-section` owns section-entry alignment and ordering.
- The current repo maturity supports a narrow hardening slice without redesign:
  - no need for a generic multiplicity engine
  - no need to expand allergies/problems
  - no need to change workflow orchestration
- What is still missing for this slice:
  - one authoritative normalized artifact for the bounded medication selection
  - stronger placeholder-specific provenance in schematic and construction artifacts
  - stronger tests that prove med1/med2 mapping stays stable and inspectable, especially when two or more medications are supplied

## 2. Proposed slice scope

- Keep multiplicity exactly as-is:
  - `0` or `1` medications -> plan `medicationrequest-1`
  - `2+` medications -> plan `medicationrequest-1` and `medicationrequest-2`
- Do not expand multiplicity beyond medications-only.
- Harden the existing path by adding:
  - one normalized bounded-medication selection artifact
  - placeholder-specific provenance for `medicationrequest-1` and `medicationrequest-2`
  - explicit structured overflow/deferred-count evidence when more than two medications are available
  - validation helpers that read the shared normalized mapping rather than recomputing selection rules locally
- Keep section ordering/ownership model unchanged:
  - sibling resource issues stay on their owning build steps
  - medications section entry alignment/order stays on `finalize-composition-1-medications-section`

## 3. Proposed medications-only hardening approach

- Add a medication-specific normalized mapping model in the workflow request layer, not a generic multiplicity abstraction.
- Recommended normalized additions:
  - `NormalizedPlannedMedicationEntry`
    - `placeholder_id`
    - `source_medication_index`
    - `medication_id`
    - `display_text`
  - `NormalizedPatientContext.planned_medication_entries: list[NormalizedPlannedMedicationEntry]`
  - `NormalizedPatientContext.deferred_additional_medication_count: int`
- Normalization rules:
  - `0` meds -> `planned_medication_entries = []`, deferred count `0`
  - `1` med -> one planned entry for `medicationrequest-1`
  - `2+` meds -> two planned entries for `medicationrequest-1` and `medicationrequest-2`, using indices `0` and `1`, deferred count `len(medications) - 2`
- Downstream hardening:
  - schematic builder should stop inferring first-two selection directly from raw list order and instead copy `planned_medication_entries`
  - resource construction should derive medication content/evidence from `planned_medication_entries`
  - validation should derive expected med1/med2 content from `planned_medication_entries`
- Provenance hardening:
  - schematic evidence should explicitly show, for each planned medication placeholder:
    - placeholder id
    - source medication index
    - `medication_id`
    - `display_text`
  - construction evidence should show the same mapping for each medication build step
  - schematic evidence should also explicitly expose deferred overflow count when `available_item_count > 2`
- Validation/repair hardening:
  - keep existing med1 and med2 finding ownership
  - strengthen placeholder-aware helper usage so med1/med2 checks reuse the normalized planned mapping
  - keep medications-section ordering validation on the finalize step, but make tests explicitly prove that swapping med1 and med2 content or section-entry order produces the correct failure class
- What remains intentionally deferred:
  - arbitrary-length medication planning
  - multiplicity for allergies/problems
  - generic sibling-resource provenance frameworks
  - redesign of bundle finalization or repair execution

## 4. File-level change plan

- Update [models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py)
  - add `NormalizedPlannedMedicationEntry`
  - extend `NormalizedPatientContext`
  - extend schematic evidence model with explicit planned-medication provenance and deferred-overflow count
- Update [request_normalization_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/request_normalization_builder.py)
  - normalize the bounded medication mapping once
  - populate `planned_medication_entries` and `deferred_additional_medication_count`
- Update [schematic_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/schematic_builder.py)
  - consume normalized planned medication entries
  - emit stronger medication placeholder provenance in schematic evidence
  - make truncation/deferred-overflow inspectable as structured evidence, not just summary text
- Update [resource_construction_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/resource_construction_builder.py)
  - use normalized planned medication entries for med1/med2 content and deterministic evidence
  - update medication-step assumptions so they accurately describe bounded two-entry behavior
- Update [validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/validation_builder.py)
  - use the shared normalized mapping for expected med1/med2 content
  - keep current finding codes, but remove local re-derivation of first-two selection
- Update tests:
  - [test_psca_request_normalization_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_request_normalization_builder.py)
  - [test_psca_bundle_schematic_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_schematic_builder.py)
  - [test_psca_resource_construction_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_resource_construction_builder.py)
  - [test_psca_validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_validation_builder.py)
  - [test_psca_repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_repair_decision_builder.py) only if route assertions need expanded sibling coverage
  - [test_psca_bundle_builder_workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py)
- Update docs:
  - [README.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md)
  - [docs/development-plan.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md)
- No planned code changes for:
  - [build_plan_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/build_plan_builder.py)
  - [bundle_finalization_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/bundle_finalization_builder.py)
  - [repair_execution_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/repair_execution_builder.py)
  - [repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/repair_decision_builder.py) unless a small test-driven clarification is needed

## 5. Step-by-step implementation plan

1. Add `NormalizedPlannedMedicationEntry` and the two new `NormalizedPatientContext` fields in `models.py`.
2. Implement a normalization helper in `request_normalization_builder.py` that derives the bounded planned-medication mapping once from the ordered medication list.
3. Preserve current multiplicity behavior while making normalization explicit:
   - no medications -> no planned entries
   - one medication -> planned `medicationrequest-1`
   - two or more medications -> planned `medicationrequest-1` and `medicationrequest-2`, deferred overflow count recorded
4. Update schematic medication evidence to copy from `planned_medication_entries` instead of recomputing first-two selection from raw list order.
5. Extend schematic medication evidence so Dev UI can show:
   - available medication count
   - planned placeholder count
   - per-placeholder source mapping
   - deferred additional medication count
6. Update `resource_construction_builder.py` medication helpers so `medicationrequest-1` and `medicationrequest-2` resolve from `planned_medication_entries` rather than raw list indexing.
7. Tighten medication-step evidence and assumptions:
   - expose source index and `medication_id`
   - explicitly state when only the first two medications are planned
8. Update validation helpers to use the normalized planned-medication mapping for med1 and med2 expected text.
9. Add or tighten tests for:
   - normalization of `planned_medication_entries` for `0`, `1`, `2`, and `3+` medication inputs
   - schematic evidence showing placeholder-specific provenance and deferred overflow count
   - construction evidence showing med1 maps to item 0 and med2 maps to item 1
   - validation catching sibling swap/content mismatch while still attributing med1 vs med2 correctly
   - workflow smoke proving the shared normalized mapping is visible and reused end to end
10. Update README and development plan wording after tests are green.

## 6. Definition of Done

- The bounded two-medication path still behaves exactly the same functionally, but now has one authoritative normalized selection artifact.
- `NormalizedPatientContext` explicitly records:
  - planned medication placeholder mappings for med1 and med2
  - deferred additional medication count beyond the first two items
- Dev UI visibly shows stronger medications-only provenance:
  - which normalized medication item maps to `medicationrequest-1`
  - which normalized medication item maps to `medicationrequest-2`
  - source indices and `medication_id`s
  - when additional medications were available but intentionally deferred
- Schematic and construction evidence no longer rely only on display-text summaries for same-type sibling medication resources.
- Validation for med1 and med2 uses the shared normalized mapping rather than independent local selection logic.
- Repair ownership remains narrow and unchanged in shape:
  - med1 issues -> `build-medicationrequest-1`
  - med2 issues -> `build-medicationrequest-2`
  - medications section ordering/alignment issues -> `finalize-composition-1-medications-section`
- What remains bounded or deferred:
  - multiplicity beyond two medications
  - multiplicity for allergies/problems
  - generic sibling-resource or multiplicity frameworks

## 7. Risks / notes

- The main real risk is introducing two competing sources of truth for planned medications. The normalized bounded mapping must become the only authoritative source for med1/med2 selection.
- A second real risk is over-generalizing the model. New types should stay medication-specific for this slice.
- A third real risk is stale assumptions text in construction or schematic artifacts. Any wording that still implies “exactly one medication item” must be corrected.
- A fourth real risk is proving ordering/content hardening only indirectly. Tests should explicitly cover sibling swap scenarios and overflow visibility, not just happy-path two-med execution.

## 8. Targeted `docs/development-plan.md` updates after implementation

- In Section 8, move `Current Focus` away from medications-only multiplicity hardening and toward the next bounded follow-on after sibling-medication provenance/alignment is hardened.
- In Section 9, set `Next Planned Slice` to a narrow decision such as whether allergies/problems should remain fixed while medication multiplicity stays bounded, or whether the next step should deepen standards/validation alignment for multi-entry medication sections.
- In Section 10, update the phase note to say bounded medications-only multiplicity now has explicit normalized first-two-item mapping, placeholder-specific provenance, and hardened sibling alignment behavior.
- In Section 12, refine the planning/provenance assumption to say the workflow now records an authoritative normalized mapping from the first two structured medication items to `medicationrequest-1` and `medicationrequest-2`, with overflow explicitly deferred.
- In Section 13, replace the current generic medication-multiplicity risk with the next real remaining risk: the two-medication path is now hardened, but broader multiplicity still requires coordinated expansion across planning, construction, validation, and repair.
- In Section 16, update the immediate next objective away from hardening the medications-only path and toward the next bounded decision about whether to keep other trio sections fixed or deepen medication-specific standards alignment further.
