## 1. Repo assessment

- The repo now has rich normalized patient context in [models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py):
  - `NormalizedBuildRequest.patient_context`
  - patient identity
  - optional `administrative_gender` / `birth_date`
  - lists of conditions, medications, and allergies
  - deterministic `selected_*_for_single_entry` fields
  - `normalization_mode`
- That context is created deterministically in [request_normalization_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/request_normalization_builder.py) and is already consumed in `resource_construction`.
- The schematic layer still drops patient context completely:
  - [schematic_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/schematic_builder.py) records provider-context evidence only
  - `BundleSchematic.summary`, `placeholder_note`, and `SchematicEvidence` contain no patient-context provenance
  - there is no explicit artifact telling Dev UI whether the run used legacy patient-profile fallback, explicit single-entry clinical selections, or explicit multi-item lists that are not yet fully consumable
- The current schematic/build-plan path is structurally fixed to one entry per required section:
  - `SectionScaffold.entry_placeholder_ids` contains exactly one placeholder id per section
  - `build_plan_builder.py` hard-codes `medicationrequest-1`, `allergyintolerance-1`, and `condition-1`
  - downstream `resource_construction`, `bundle_finalization`, validation, repair routing, and tests all assume those exact fixed placeholder ids and one step per trio resource
- That means current repo maturity does **not** safely support even a “small” multiplicity change without touching many more layers than this slice allows.
- What is missing for this slice:
  - patient-context-aware schematic provenance
  - explicit schematic inspectability around section-level available item counts vs current planned placeholder counts
  - an honest schematic-level statement that one-entry-per-section remains fixed for now
- Constraints that matter now:
  - no broad redesign of schematic/build-plan/resource-construction
  - no arbitrary multi-entry planning
  - no hidden partial multiplicity behavior
  - keep deterministic inspectability first

## 2. Proposed slice scope

- Make the schematic layer patient-context-aware by consuming `NormalizedBuildRequest.patient_context`.
- Keep one-entry-per-section **unchanged** in this slice.
- Add explicit schematic evidence and summary text that:
  - records normalized patient context used for the run
  - records section-level available item counts for medications, allergies, and problems
  - records whether each section currently has:
    - legacy fallback
    - single-entry structured item available and consumable
    - multiple items available but still deferred under fixed single-entry planning
- Do **not** change:
  - placeholder counts
  - build-plan step counts
  - resource-construction step structure
  - validation/repair ownership
- This is the smaller, safer move the current codebase supports.

## 3. Proposed patient-context-aware schematic / one-entry-per-section approach

- Add new schematic evidence models in [models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py):
  - `SchematicPatientContextEvidence`
    - `normalization_mode`
    - `patient_id`
    - `patient_display_name`
    - `patient_source_type`
    - `administrative_gender_present: bool`
    - `birth_date_present: bool`
  - `SchematicClinicalSectionContextEvidence`
    - `section_key`
    - `available_item_count`
    - `selected_single_entry_display_text: str | None`
    - `planned_placeholder_count: int`
    - `planning_disposition: Literal[...]`
- Recommended `planning_disposition` values:
  - `legacy_profile_fallback`
  - `fixed_single_entry_no_structured_items`
  - `fixed_single_entry_selected_item`
  - `fixed_single_entry_multiple_items_deferred`
- Extend `SchematicEvidence` with:
  - `patient_context: SchematicPatientContextEvidence`
  - `clinical_section_contexts: list[SchematicClinicalSectionContextEvidence]`
- Populate that evidence by copying from `normalized_request.patient_context`, not by recomputing or inferring clinical meaning.
- Keep `SectionScaffold` and `ResourcePlaceholder` structural shape unchanged.
- Keep section placeholder counts unchanged:
  - medications -> `["medicationrequest-1"]`
  - allergies -> `["allergyintolerance-1"]`
  - problems -> `["condition-1"]`
- Keep `build_psca_build_plan(schematic)` unchanged in behavior.
- Update schematic summary / placeholder note to mention patient-context mode and current fixed planning stance:
  - legacy mode:
    - schematic records legacy patient-profile fallback only
  - explicit patient context with single-item selections:
    - schematic records structured patient context and notes the current fixed one-entry-per-section plan can consume those single items
  - explicit patient context with multiple items in one or more lists:
    - schematic records available structured clinical counts, but states planning remains fixed to one entry per required section and multi-item expansion is deferred
- Downstream stages should not change immediately:
  - `build_plan_builder.py` behavior stays the same
  - `resource_construction_builder.py` behavior stays the same
  - validation/repair stay the same
- The only immediate downstream adjustments should be tests and docs to show the richer schematic provenance and the explicit “planning remains fixed” decision.

## 4. File-level change plan

- Update [models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py)
  - add patient-context schematic evidence models
  - extend `SchematicEvidence`
- Update [schematic_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/schematic_builder.py)
  - build patient-context evidence
  - build section-level clinical context evidence for medications/allergies/problems
  - update summary / placeholder note text
  - keep placeholder counts and relationships unchanged
- Update tests:
  - [test_psca_bundle_schematic_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_schematic_builder.py)
  - [test_psca_build_plan_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_build_plan_builder.py)
  - [test_psca_bundle_builder_workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py)
- Update docs:
  - [README.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md)
  - [docs/development-plan.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md)
- No changes in this slice to:
  - `request_normalization_builder.py`
  - `build_plan_builder.py`
  - `resource_construction_builder.py`
  - `validation_builder.py`
  - `repair_decision_builder.py`

## 5. Step-by-step implementation plan

1. Add `SchematicPatientContextEvidence` and `SchematicClinicalSectionContextEvidence` to `models.py`.
2. Extend `SchematicEvidence` to include patient-context evidence and section-level clinical context evidence.
3. In `schematic_builder.py`, add a helper that copies patient identity/provenance from `normalized_request.patient_context`.
4. Add a second helper that produces three deterministic section-context evidence objects:
   - medications from `normalized_request.patient_context.medications`
   - allergies from `normalized_request.patient_context.allergies`
   - problems from `normalized_request.patient_context.conditions`
5. For each section evidence object, set:
   - `available_item_count`
   - `selected_single_entry_display_text`
   - `planned_placeholder_count = len(section.entry_placeholder_ids)` which should remain `1`
   - `planning_disposition` from the normalized context and item count
6. Update `BundleSchematic.summary` to mention:
   - provider-context summary as today
   - patient-context summary for legacy vs explicit context
   - whether any section is in `multiple_items_deferred`
7. Update `BundleSchematic.placeholder_note` to explicitly state that the workflow still plans one placeholder per required section in this slice.
8. Keep all placeholder ids, section scaffold counts, relationships, and bundle-plan prerequisites unchanged.
9. Update schematic-builder tests:
   - explicit patient context with exactly one item in each trio list:
     - assert patient-context evidence values
     - assert section evidence counts are `1`
     - assert dispositions are `fixed_single_entry_selected_item`
     - assert placeholder counts still remain `1`
   - explicit patient context with multiple items in at least one list:
     - assert `available_item_count > 1`
     - assert `selected_single_entry_display_text is None`
     - assert disposition is `fixed_single_entry_multiple_items_deferred`
     - assert schematic still contains only one placeholder for that section
   - legacy patient-profile mode:
     - assert `legacy_profile_fallback`
10. Update build-plan tests only as needed to prove no multiplicity change:
    - with richer patient context present, build-plan step ids and count remain unchanged
11. Update workflow smoke test:
    - assert schematic evidence now includes patient-context provenance
    - assert schematic section evidence shows available trio counts
    - assert one-entry-per-section still remains fixed in the schematic/build plan
12. Update README and `docs/development-plan.md` after tests are green.

## 6. Definition of Done

- `BundleSchematic` now records structured patient-context provenance in its evidence.
- Dev UI visibly shows:
  - patient normalization mode
  - patient identity provenance
  - whether demographic basics were present upstream
  - section-level available item counts for medications, allergies, and problems
  - whether each section currently uses:
    - legacy fallback
    - single-item structured context
    - multiple-items-deferred under fixed single-entry planning
- The repo makes an explicit, inspectable decision that one-entry-per-section remains fixed in this slice.
- `SectionScaffold.entry_placeholder_ids`, `ResourcePlaceholder` counts, and build-plan step counts remain unchanged.
- `resource_construction`, validation, repair routing, and retry behavior remain unchanged in this slice.
- What remains deferred:
  - multi-entry section planning
  - dynamic placeholder counts
  - patient-context-driven build-plan multiplicity
  - broader clinical reasoning or generic planning engines

## 7. Risks / notes

- The main real risk is accidental hidden multiplicity semantics. If counts > 1 are recorded in schematic evidence, the artifact text must also say those extra items are not yet planned into additional placeholders.
- A second real risk is duplicating truth between `NormalizedPatientContext` and schematic evidence. The schematic should copy, not reinterpret, selected-item and count information.
- A third real risk is overloading section scaffolds with planning policy. Keep structural planning unchanged and put the new patient-context explanation in schematic evidence/summary rather than reshaping core planning objects prematurely.
- A fourth real risk is implying patient-context-aware planning exists when it does not. Wording should say the schematic records available context and current fixed planning disposition, not that it “selects” or “plans” arbitrary clinical entries.

## 8. Targeted `docs/development-plan.md` updates after implementation

- In Section 8, change `Current Focus` away from patient-context-aware schematic assumptions / one-entry-per-section reassessment to the next bounded patient-context consumption slice.
- In Section 9, replace `Next Planned Slice` with the next real bounded follow-on, likely: “Decide whether a very small bounded multi-entry expansion is justified for one fixed trio section, or keep planning fixed and deepen content-alignment validation instead.”
- In Section 10, update the Phase 8 note to say the schematic layer now records patient-context provenance and explicitly documents current fixed one-entry-per-required-section planning despite richer upstream clinical lists.
- In Section 12, refine the patient-side assumption to say normalized patient context is now available in both request normalization and schematic evidence, but build planning still intentionally remains fixed to one entry per required trio section.
- In Section 13, replace the current generic patient-context risk with the next real remaining risk: richer patient clinical lists are now visible upstream and in schematic evidence, but the workflow still cannot safely expand placeholder multiplicity without coordinated changes across planning, construction, validation, and repair.
- In Section 16, update the immediate next objective away from patient-context-aware schematic wiring and toward the next bounded decision on whether any trio section can safely gain a minimal multiplicity expansion or whether the next step should instead deepen content-alignment/validation around the current fixed plan.
