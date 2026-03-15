1. Repo assessment

- The current repo has already narrowed Composition construction to section-specific finalize steps:
  - `finalize-composition-1-medications-section`
  - `finalize-composition-1-allergies-section`
  - `finalize-composition-1-problems-section`
- The remaining grouped rule is [validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/validation_builder.py):
  - `bundle.composition_section_entry_references_aligned`
- That grouped helper currently:
  - iterates `schematic.section_scaffolds`
  - checks `Composition.section[index].entry[0].reference == expected fullUrl(entry_placeholder_id)`
  - returns one combined failure if any required section-entry exact fullUrl is wrong
- Current ownership split is now clear:
  - `resource_construction` section-finalize steps create the local section-entry reference for exactly one Composition section at a time
  - [resource_construction_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/resource_construction_builder.py) records one `ReferenceContribution` per finalize step at:
    - `section[{index}].entry[0].reference`
  - `bundle_finalization` rewrites that contributed local reference to the final `entry.fullUrl`
- This is more precise than the non-Composition alignment case:
  - each failing Composition section-entry exact fullUrl path already maps to one existing finalize step
  - targeted `resource_construction` retry for those finalize steps already exists and is tested
- The repo now supports a safe narrower executable path here without new orchestration:
  - `repair_decision` can already emit step-subset directives
  - `repair_execution` can already rerun targeted `resource_construction` and then downstream `bundle_finalization`
- What is missing for this slice:
  - section-specific exact fullUrl alignment finding codes for Composition section entries
  - section-specific repair-decision mapping for those findings
  - tests proving one bad section-entry fullUrl routes to one finalize step
- Main constraint:
  - exact-alignment findings must not duplicate existing section-presence findings
  - if a section block is missing or malformed, the existing `bundle.composition_*_section_present` rules should own that failure
  - if bundle `entry.fullUrl` values are missing, `bundle.entry_fullurls_present` should own that failure

2. Proposed slice scope

- Split `bundle.composition_section_entry_references_aligned` into three section-specific workflow findings:
  - `bundle.composition_medications_section_entry_reference_aligned`
  - `bundle.composition_allergies_section_entry_reference_aligned`
  - `bundle.composition_problems_section_entry_reference_aligned`
- Remove the grouped `bundle.composition_section_entry_references_aligned` code from active validation and repair routing.
- Route the three new codes to `resource_construction`, not `bundle_finalization`.
- Use existing section-specific finalize steps as the executable repair target:
  - medications -> `finalize-composition-1-medications-section`
  - allergies -> `finalize-composition-1-allergies-section`
  - problems -> `finalize-composition-1-problems-section`
- No build-plan change.
- No new stage.
- No bundle-finalization redesign.
- No generic reference engine.
- What remains intentionally deferred after this slice:
  - non-Composition exact fullUrl alignment remains bundle-finalization-owned
  - no attempt to infer root cause between bad local reference contribution vs bad final rewrite outside these Composition section-finalize-owned paths
  - no arbitrary/dynamic section multiplicity

3. Proposed narrower Composition section-entry exact fullUrl alignment / repair approach

- Validation split:
  - `bundle.composition_medications_section_entry_reference_aligned`
    - validate exact final `urn:uuid:` alignment for the medications section entry reference
  - `bundle.composition_allergies_section_entry_reference_aligned`
    - validate exact final `urn:uuid:` alignment for the allergies section entry reference
  - `bundle.composition_problems_section_entry_reference_aligned`
    - validate exact final `urn:uuid:` alignment for the problems section entry reference
- Recommended validation behavior:
  - find the matching section block by section scaffold metadata, not by raw index alone
  - match by deterministic section identity:
    - section title
    - section LOINC code
  - once the section block is found, compare `entry[0].reference` to the expected bundle `fullUrl`
- Important precondition behavior:
  - if the expected `fullUrl` for the entry placeholder is unavailable, return “not assessable” and emit no section-entry exact-alignment finding
  - if the matching section block is absent, emit no section-entry exact-alignment finding
  - let these existing rules own those failures instead:
    - `bundle.entry_fullurls_present`
    - `bundle.composition_medications_section_present`
    - `bundle.composition_allergies_section_present`
    - `bundle.composition_problems_section_present`
- Repair mapping:
  - `bundle.composition_medications_section_entry_reference_aligned`
    - target step ids: `["finalize-composition-1-medications-section"]`
    - target placeholders: `["composition-1"]`
  - `bundle.composition_allergies_section_entry_reference_aligned`
    - target step ids: `["finalize-composition-1-allergies-section"]`
    - target placeholders: `["composition-1"]`
  - `bundle.composition_problems_section_entry_reference_aligned`
    - target step ids: `["finalize-composition-1-problems-section"]`
    - target placeholders: `["composition-1"]`
- Why these can move to `resource_construction` safely:
  - each exact failing path is already owned by one section-finalize step in `resource_construction`
  - rerunning that finalize step plus downstream `bundle_finalization` is already supported
  - this is narrower than the previous grouped rule and still deterministic
- What should remain grouped after this slice:
  - nothing from the old `bundle.composition_section_entry_references_aligned` rule
  - grouped handling remains elsewhere only where the repo still truly has grouped ownership

4. File-level change plan

- Update [validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/validation_builder.py)
  - replace the grouped Composition section-entry exact-alignment check with three section-specific checks
  - add a helper that finds a matching Composition section block by scaffold metadata
  - keep exact-alignment helpers quiet when the section block or expected fullUrl is not assessable
- Update [repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/repair_decision_builder.py)
  - remove the grouped Composition section-entry exact-alignment route
  - add three new route mappings to `resource_construction`
  - add three new `ResourceConstructionRepairDirective` mappings to the corresponding finalize steps
- Update tests:
  - [test_psca_validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_validation_builder.py)
  - [test_psca_repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_repair_decision_builder.py)
  - [test_psca_repair_execution_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_repair_execution_builder.py)
  - [test_psca_bundle_builder_workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py) only if surfaced finding-name assertions need it
- Update docs:
  - [README.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md)
  - [docs/development-plan.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md)
- No model changes required.
- No `build_plan_builder.py` changes required.
- No `bundle_finalization_builder.py` changes required.

5. Step-by-step implementation plan

1. Replace the grouped `bundle.composition_section_entry_references_aligned` entry in `checks_run` with the three new section-specific codes.
2. Add a helper that resolves the matching Composition section block for one `SectionScaffold` using deterministic title + LOINC code matching.
3. Add a helper for one section-specific exact fullUrl alignment check:
   - resolve expected entry fullUrl from placeholder id
   - return `True` if expected fullUrl is unavailable
   - return `True` if the matching section block is not present
   - return `False` only when the matching section exists and `entry[0].reference` is wrong
4. Emit one finding per section:
   - medications
   - allergies
   - problems
5. Remove the old grouped Composition section-entry exact-alignment finding emission.
6. Update `repair_decision_builder.py`:
   - add the three new codes to `_FINDING_ROUTE_MAP`
   - route them to `resource_construction`
   - add three directive-map entries to `_RESOURCE_CONSTRUCTION_DIRECTIVE_MAP`
   - remove the old grouped Composition section-entry exact-alignment route
7. Keep `_RESOURCE_CONSTRUCTION_STEP_ORDER` unchanged because the needed finalize step ids already exist there.
8. Update validation tests:
   - wrong medications section entry fullUrl -> only `bundle.composition_medications_section_entry_reference_aligned`
   - wrong allergies section entry fullUrl -> only `bundle.composition_allergies_section_entry_reference_aligned`
   - wrong problems section entry fullUrl -> only `bundle.composition_problems_section_entry_reference_aligned`
   - two wrong section entry fullUrls -> exactly those two findings
   - missing section block should still be owned by `bundle.composition_*_section_present`, not the new exact-alignment code
   - missing `entry.fullUrl` should still be owned by `bundle.entry_fullurls_present`, not the new exact-alignment codes
9. Update repair-decision tests:
   - each new section-entry exact-alignment code routes to `resource_construction`
   - each produces a single-step directive for the matching finalize step
   - combined section-entry exact-alignment failures union into the matching finalize-step list in plan order
10. Update repair-execution tests:
    - break only one section-entry exact fullUrl in the candidate bundle
    - assert:
      - `requested_target == "resource_construction"`
      - `execution_scope == "targeted_repair"`
      - rerun step ids contain only the matching finalize step
      - downstream `bundle_finalization` reruns and validation returns to `passed_with_warnings`
    - add one combined test for two section-entry exact-alignment failures yielding two finalize steps
11. Update README and development plan wording to reflect:
    - section-specific Composition section-entry exact fullUrl findings
    - targeted finalize-step repair for those findings
    - unchanged non-Composition bundle-finalization-owned exact-alignment behavior
12. Run the full test suite and confirm no stale references to `bundle.composition_section_entry_references_aligned` remain.

6. Definition of Done

- `bundle.composition_section_entry_references_aligned` is no longer emitted.
- Workflow validation now emits:
  - `bundle.composition_medications_section_entry_reference_aligned`
  - `bundle.composition_allergies_section_entry_reference_aligned`
  - `bundle.composition_problems_section_entry_reference_aligned`
- A wrong exact fullUrl in one Composition section entry produces only the matching section-specific finding.
- Missing section blocks or missing bundle `fullUrl`s do not spray the new exact-alignment findings.
- `repair_decision` maps each new section-specific exact-alignment finding to `resource_construction`.
- The resulting repair directive targets only the matching finalize step:
  - medications -> medications finalize
  - allergies -> allergies finalize
  - problems -> problems finalize
- `repair_execution` visibly reruns:
  - the targeted Composition finalize step subset
  - then downstream `bundle_finalization`, `validation`, and `repair_decision`
- Dev UI now shows:
  - section-specific Composition section-entry exact fullUrl findings
  - section-specific `resource_construction` directives for those findings
  - narrower finalize-step rerun lists for those repairs
- What still remains grouped or deferred:
  - non-Composition exact fullUrl alignment remains bundle-finalization-owned
  - no generic section/reference engine
  - no dynamic multiplicity support

7. Risks / notes

- The main real risk is duplicate findings if exact section-entry alignment is checked when the section block itself is missing. The new helpers should treat missing sections as “owned elsewhere.”
- A second real risk is accidental raw-index coupling. Matching the section block by title + LOINC code is safer than relying only on position.
- A third real risk is consistency drift with non-Composition exact-alignment routing. This slice should document clearly that Composition section-entry alignment can move to `resource_construction` because each failing path already has a dedicated section-finalize step.
- This slice should not broaden into revisiting all exact fullUrl ownership rules across the workflow.

8. Targeted `docs/development-plan.md` updates after implementation

- In Section 8, change `Current Focus` from the remaining grouped Composition section-entry exact fullUrl alignment to the next bounded realism or remaining grouped-validation slice.
- In Section 9, replace `Next Planned Slice` with a bounded follow-on such as: “Deepen Organization/provider-role realism or revisit whether non-Composition exact fullUrl alignment can later narrow beyond bundle-finalization ownership.”
- In Section 10, update the Phase 8 note to say Composition section-entry exact fullUrl alignment is now section-specific and can trigger section-specific finalize-step repair.
- In Section 12, refine the repair assumption to say existing Composition section-finalize step boundaries are now sufficient for section-specific exact fullUrl alignment repair.
- In Section 13, replace the current grouped Composition section-entry alignment risk with the next real remaining risk: non-Composition exact fullUrl alignment is still bundle-finalization-owned because the repo does not yet distinguish source reference contribution defects from final rewrite defects there.
- In Section 16, update the immediate next objective away from grouped Composition section-entry exact fullUrl alignment and toward the next narrow realism or remaining exact-alignment ownership slice.
