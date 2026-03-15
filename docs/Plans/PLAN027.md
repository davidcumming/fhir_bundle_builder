## 1. Repo assessment

- `NormalizedPatientContext` already carries the full ordered medication list in [models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py), and [request_normalization_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/request_normalization_builder.py) preserves that list without collapsing multi-item input.
- The current hard lock is in [schematic_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/schematic_builder.py): medications always get exactly `["medicationrequest-1"]`, one section-entry relationship, and one bundle-entry relationship.
- [build_plan_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/build_plan_builder.py) then hard-codes `build-medicationrequest-1` and a medications finalize step that expects only one medication reference handle.
- [resource_construction_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/resource_construction_builder.py) can already build a section-entry scaffold generically, but Composition medications-section finalization still attaches only `entry[0]`.
- [bundle_finalization_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/bundle_finalization_builder.py) is mostly relationship-driven already; it should not need a design change if upstream artifacts expose a second medication placeholder.
- [validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/validation_builder.py) and [repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/repair_decision_builder.py) still assume one medication placeholder, one MedicationRequest resource, and one medications-section entry reference.
- The repo already has the maturity needed for a bounded medications-only expansion: fixed ids, targeted step-subset repair, deterministic patient context, and section-specific Composition finalize ownership.
- What is missing is a narrow explicit two-medication path across schematic, plan, construction, section-finalization, validation, and repair. Allergies and problems should stay fixed at one entry.

## 2. Proposed slice scope

- Add a bounded medications-only multiplicity rule and keep everything else fixed.
- Recommended rule:
  - `0` structured medications: plan `["medicationrequest-1"]`
  - `1` structured medication: plan `["medicationrequest-1"]`
  - `2+` structured medications: plan `["medicationrequest-1", "medicationrequest-2"]`
- Use the first two normalized medication items in list order when `2+` items are available.
- Keep allergies and problems unchanged at one placeholder, one build step, and one section entry.
- Do not change request normalization, workflow orchestration, or bundle-finalization architecture.
- Do not add arbitrary-length multiplicity or a generic multiplicity engine.

## 3. Proposed medications-only multiplicity approach

- Keep the multiplicity policy explicit and medication-specific inside the schematic/build-plan layer.
- Add one new fixed placeholder id and one new fixed build step id:
  - `medicationrequest-2`
  - `build-medicationrequest-2`
- Keep one medications section finalize step:
  - `finalize-composition-1-medications-section`
  - update it to attach one or two `Composition.section[medications].entry[]` references in scaffold order, not just `entry[0]`
- Use existing normalized medication list order as the source of truth:
  - `medicationrequest-1` uses `patient_context.medications[0]` when present, otherwise current fallback text
  - `medicationrequest-2` uses `patient_context.medications[1]` when present
  - items after index `1` remain visible in schematic evidence as available-but-unplanned
- Keep request normalization unchanged; no new upstream patient model is required for this slice.
- Make schematic evidence honest about the bounded rule:
  - update medication section `planned_placeholder_count` to `1` or `2`
  - add a small evidence field for planned medication display texts, since current `selected_single_entry_display_text` is not enough for two planned meds
  - add a new medications planning disposition such as `bounded_two_entry_selected_first_two`
  - retain current fixed-single-entry dispositions for allergies and problems
- Update validation and repair with the smallest safe asymmetry:
  - keep existing singular medication findings scoped to `medicationrequest-1`
  - add parallel `medicationrequest-2` finding codes only for the second placeholder
  - make medications-section Composition validation plural-aware so it checks one or two expected entries in order
- Keep [repair_execution_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/repair_execution_builder.py) unchanged in logic; it already reruns whatever build steps the repair directive names.

## 4. File-level change plan

- Update [models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py)
  - extend schematic section evidence with a bounded medication planned-text field and the new medications planning disposition literal
- Update [schematic_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/schematic_builder.py)
  - plan one or two medication placeholders
  - add `medicationrequest-2` bundle/section relationships when applicable
  - record available count, planned count, planned medication texts, and bounded-truncation stance
- Update [build_plan_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/build_plan_builder.py)
  - conditionally add `build-medicationrequest-2`
  - update medications finalize-step prerequisites and evidence for one or two medication handles
- Update [resource_construction_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/resource_construction_builder.py)
  - build `medicationrequest-2` content from the second normalized medication item
  - make Composition medications-section finalization attach one or two entries and emit matching evidence/reference contributions
- Update [validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/validation_builder.py)
  - validate medication content/reference alignment for one or two placeholders
  - make medications-section Composition checks plural-aware
- Update [repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/repair_decision_builder.py)
  - add second-medication routes/directives
  - keep medications-section findings routed to the single medications finalize step
- Update tests:
  - [test_psca_bundle_schematic_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_schematic_builder.py)
  - [test_psca_build_plan_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_build_plan_builder.py)
  - [test_psca_resource_construction_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_resource_construction_builder.py)
  - [test_psca_bundle_finalization_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_finalization_builder.py)
  - [test_psca_validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_validation_builder.py)
  - [test_psca_repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_repair_decision_builder.py)
  - [test_psca_repair_execution_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_repair_execution_builder.py)
  - [test_psca_bundle_builder_workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py)
- Update docs:
  - [README.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md)
  - [docs/development-plan.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md)

## 5. Step-by-step implementation plan

1. Extend the schematic evidence model so medications can record one or two planned display texts and the new bounded-two-entry disposition.
2. Update schematic generation so medications section planning becomes:
   - one placeholder for `0` or `1` meds
   - two placeholders for `2+` meds
   - first two normalized medications selected in order
   - extras beyond two recorded as available but not planned
3. Add `medicationrequest-2` placeholder, section-entry relationship, and bundle-entry relationship when the schematic chooses two medication placeholders.
4. Update build-plan generation to add `build-medicationrequest-2` only when that placeholder exists, and make the medications finalize step depend on both medication build steps when present.
5. Update section-entry resource construction so `medicationrequest-1` and `medicationrequest-2` each pull the correct deterministic medication text, while legacy/fallback behavior remains for the one-placeholder path.
6. Update Composition medications-section finalize logic to emit `entry[0]` and optionally `entry[1]`, plus matching populated paths, deterministic evidence, and local reference contributions.
7. Leave bundle finalization logic intact unless implementation reveals a true gap; update only tests if entry ordering/count assertions change.
8. Update validation:
   - keep existing medication-1 content and reference checks
   - add medication-2 content, source-reference-contribution, and exact fullUrl checks
   - change medications-section presence/exact-alignment checks to validate one or two entries in scaffold order
9. Update repair routing:
   - existing medication-1 findings keep targeting `build-medicationrequest-1`
   - new medication-2 findings target `build-medicationrequest-2`
   - medications-section findings still target `finalize-composition-1-medications-section`
   - combined medication-1 and medication-2 failures union into ordered step-subset retries
10. Update end-to-end and direct tests for three cases:
    - `0` meds: still one medication placeholder with fallback text
    - `1` med: one placeholder with structured medication text
    - `2+` meds: exactly two placeholders/steps/resources using the first two normalized items, with available count still reflecting the full list
11. Update README and development plan once tests are green.

## 6. Definition of Done

- The workflow supports bounded medications-only multiplicity with exactly this rule:
  - `0` or `1` normalized medications -> one planned medication placeholder
  - `2+` normalized medications -> two planned medication placeholders using the first two items in order
- The schematic and Dev UI visibly show:
  - available medication count
  - planned medication placeholder count
  - planned medication display texts for one or two entries
  - that only the first two items are planned when more than two are available
- New fixed ids exist and are used deterministically:
  - `medicationrequest-2`
  - `build-medicationrequest-2`
- Build planning, resource construction, Composition medications-section finalization, validation, and repair all work for one or two medication entries.
- The candidate bundle can include a second MedicationRequest entry and a second medications-section Composition entry when planned.
- Allergies and problems remain fixed to one placeholder and one step.
- Request normalization, bundle-finalization architecture, retry orchestration, and non-medication multiplicity remain deferred.

## 7. Risks / notes

- The main real risk is accidental drift into a generic multiplicity engine. Keep the logic explicitly medication-only and hard-coded to `-1` and `-2`.
- A second real risk is ambiguous medication validation once there are two resources of the same type. Validation must stop relying on “find the MedicationRequest by type” for medication checks and instead use placeholder-aware expectations.
- A third real risk is Composition medications-section finalization. That step is currently the main single-entry assumption outside the planner and must be updated carefully so evidence, reference contributions, and section-entry alignment all stay consistent.
- A fourth real risk is silent truncation. When `available_item_count > 2`, schematic summary/evidence must explicitly say that only the first two medications are planned in this bounded slice.

## 8. Targeted `docs/development-plan.md` updates after implementation

- In Section 8, move `Current Focus` away from “decide whether a very small bounded multi-entry expansion is justified” to the next bounded follow-on after medications-only multiplicity is in place.
- In Section 9, set `Next Planned Slice` to either “deepen medication multiplicity validation/repair alignment” or “decide whether allergies/problems should remain fixed while medication multiplicity matures,” not a generic multi-entry engine.
- In Section 10, update the phase note to say the workflow now supports a bounded medications-only expansion of up to two entries while allergies and problems remain fixed at one.
- In Section 12, refine the planning assumption to say normalized patient context now affects medication placeholder count, but only through an explicit bounded rule using at most the first two medications.
- In Section 13, replace the current fixed-planning risk with the next real remaining risk: medications now have a bounded two-entry path, but broader multi-entry support still requires coordinated changes and remains intentionally deferred.
- In Section 16, update the immediate next objective away from “whether any trio section can safely gain a minimal multiplicity expansion” and toward the next bounded medication follow-on or a decision about whether allergies/problems should stay fixed.
