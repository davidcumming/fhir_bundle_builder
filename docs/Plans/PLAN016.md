1. Repo assessment

- The current repo already narrowed section-entry repair because each section-entry resource has its own build step and its own validation code.
- The main remaining grouped Composition area is real and easy to locate:
  - [validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/validation_builder.py) still uses one grouped rule: `bundle.required_sections_present`
  - it collects all missing section keys into one finding
  - [repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/repair_decision_builder.py) maps that grouped finding to the single step `finalize-composition-1`
- The current Composition construction path is still grouped in implementation, not just validation:
  - [build_plan_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/build_plan_builder.py) produces one Composition finalize step: `finalize-composition-1`
  - [resource_construction_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/resource_construction_builder.py) hardcodes one loop over `("medications", "allergies", "problems")` inside `_build_composition_finalize_result`
  - that single step attaches all three sections and all three section-entry references at once
- The schematic and planning layers are already mature enough to support a narrow split:
  - `SectionScaffold` already carries fixed metadata for `medications`, `allergies`, and `problems`
  - each section has exactly one `entry_placeholder_id`
  - the build plan already has separate section-entry steps for the three underlying resources
  - targeted retry/directive machinery already supports unions of multiple step ids in stable order
- The main implication is important:
  - splitting validation findings only would improve inspectability, but not executable repair precision, because all Composition section findings would still map to the same single finalize step
  - to improve real repair precision, the smallest honest move is to split Composition finalization into three narrow finalize steps, one per required section
- Other Composition-related grouped rules should remain grouped for now:
  - `bundle.composition_type_matches_psca_summary`
  - `bundle.composition_enriched_content_present`
  - bundle-level `bundle.references_aligned_to_entry_fullurls`

2. Proposed slice scope

- Implement narrower Composition section validation and repair by:
  - splitting grouped required-section validation into three section-specific findings
  - splitting the single Composition finalize step into three deterministic section-specific finalize steps
- Recommended exact new validation codes:
  - `bundle.composition_medications_section_present`
  - `bundle.composition_allergies_section_present`
  - `bundle.composition_problems_section_present`
- Recommended exact new build step ids:
  - `finalize-composition-1-medications-section`
  - `finalize-composition-1-allergies-section`
  - `finalize-composition-1-problems-section`
- Remove `bundle.required_sections_present` from active workflow validation and repair mapping in this slice.
- Replace the old single `finalize-composition-1` step with the three section-specific finalize steps.
- Keep the orchestration model unchanged:
  - same bounded retry model
  - same `resource_construction` directive model
  - same downstream rerun chain
- Keep intentionally grouped after this slice:
  - Composition scaffold/content checks (`type`, `status`, `title`, subject/author scaffold content)
  - bundle fullUrl/reference alignment
  - optional-section behavior
  - any dynamic multiplicity or generic section engine work

3. Proposed narrower Composition section validation / repair approach

- Choose the smaller safe move that actually improves repair precision:
  - not “findings only”
  - yes “split Composition finalization into three section-specific substeps”
- Rationale:
  - current repo already has fixed section scaffold metadata and one entry placeholder per required section
  - the current finalize logic is a simple hardcoded loop, so splitting it is local and deterministic
  - without step-splitting, repair directives cannot become narrower in execution
- New validation semantics:
  - validate deterministic section presence/block completeness, not semantic clinical correctness
  - each new rule should verify that the Composition contains the expected section block for that section with:
    - matching section title
    - matching section LOINC code
    - a present first `entry[0].reference`
- Recommended mapping:
  - `bundle.composition_medications_section_present`
    - repair target: `["finalize-composition-1-medications-section"]`
    - placeholder metadata: `["composition-1"]`
  - `bundle.composition_allergies_section_present`
    - repair target: `["finalize-composition-1-allergies-section"]`
    - placeholder metadata: `["composition-1"]`
  - `bundle.composition_problems_section_present`
    - repair target: `["finalize-composition-1-problems-section"]`
    - placeholder metadata: `["composition-1"]`
- New build-plan/finalization behavior:
  - keep `build-composition-1-scaffold` unchanged
  - replace one grouped finalize step with three ordered `composition_finalize` steps
  - each finalize step should use `owning_section_key` to attach or refresh exactly one required section block on the current Composition scaffold
  - each step should preserve previously attached sections already present in the registry scaffold
- Recommended dependency shape:
  - `finalize-composition-1-medications-section`
    - depends on `build-composition-1-scaffold`
    - depends on `build-medicationrequest-1`
  - `finalize-composition-1-allergies-section`
    - depends on `finalize-composition-1-medications-section`
    - depends on `build-allergyintolerance-1`
  - `finalize-composition-1-problems-section`
    - depends on `finalize-composition-1-allergies-section`
    - depends on `build-condition-1`
- Reason for chaining the finalize steps:
  - it makes incremental Composition buildup explicit in the inspectable build plan
  - it matches the current sequential builder execution model
  - it preserves full-build correctness while still allowing targeted rerun of one section step against a prior registry state
- Keep naming honest:
  - “section present” means deterministic section-block presence/completeness in the generated document, not full semantic section validity
- What remains intentionally grouped or deferred after this slice:
  - `bundle.composition_enriched_content_present` remains grouped at scaffold/content level
  - section ordering beyond the fixed current deterministic order remains implicit in the plan/build sequence rather than a separate validation rule
  - no generic section-editing or arbitrary section multiplicity

4. File-level change plan

- Update [build_plan_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/build_plan_builder.py)
  - replace `finalize-composition-1` with the three section-specific finalize steps
  - update Composition planning metadata and dependencies accordingly
- Update [models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py)
  - expand `BuildPlan.composition_strategy` to a new honest value for incremental section finalization
  - no broad model redesign
- Update [resource_construction_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/resource_construction_builder.py)
  - change Composition finalization from one hardcoded three-section loop to one-section-per-step behavior driven by `owning_section_key`
  - preserve existing registry/step-history behavior
- Update [validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/validation_builder.py)
  - replace `bundle.required_sections_present` with three section-specific Composition findings
- Update [repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/repair_decision_builder.py)
  - replace grouped Composition section route/directive mapping with three section-specific mappings
  - update `_RESOURCE_CONSTRUCTION_STEP_ORDER`
- Update tests:
  - [test_psca_build_plan_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_build_plan_builder.py)
  - [test_psca_resource_construction_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_resource_construction_builder.py)
  - [test_psca_validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_validation_builder.py)
  - [test_psca_repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_repair_decision_builder.py)
  - [test_psca_repair_execution_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_repair_execution_builder.py)
  - [test_psca_bundle_builder_workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py)
- Update docs:
  - [README.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md)
  - [docs/development-plan.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md)

5. Step-by-step implementation plan

1. Update `BuildPlan.composition_strategy` to a new explicit value such as `scaffold_then_incremental_section_finalize`.
2. Replace the single Composition finalize step in `build_plan_builder.py` with the three new section-specific finalize steps.
3. Set `owning_section_key` on each new finalize step so `resource_construction` can target the correct section deterministically.
4. Update step dependencies and step ordering so the three finalize steps build the Composition incrementally in the fixed section order.
5. Refactor `_build_composition_finalize_result(...)` in `resource_construction_builder.py`:
   - accept/use `step.owning_section_key`
   - attach or refresh only that one section block
   - preserve other already-attached sections from the prior Composition scaffold
   - emit only that section’s reference contribution and deterministic value evidence
6. Update resource-construction assumptions/summary text if needed so the artifact clearly reflects incremental section finalization.
7. Replace `bundle.required_sections_present` in `validation_builder.py` with the three new Composition section rules.
8. Add helper logic that validates one required section at a time against the current fixed section scaffold metadata.
9. Update `repair_decision_builder.py`:
   - add the three new Composition section codes to `_FINDING_ROUTE_MAP`
   - map each new code to its matching finalize step in `_RESOURCE_CONSTRUCTION_DIRECTIVE_MAP`
   - remove the old grouped `bundle.required_sections_present` mapping
   - expand `_RESOURCE_CONSTRUCTION_STEP_ORDER` for the new finalize step ids
10. Update build-plan tests:
    - assert the new step ids
    - assert the new Composition strategy value
    - assert section-specific finalize dependencies/order
11. Update resource-construction tests:
    - assert full-build Composition registry source steps now include scaffold + the three finalize steps
    - add targeted rerun tests proving one Composition section finalize step can rerun without rerunning the others
12. Update validation tests:
    - breaking only medications section -> only `bundle.composition_medications_section_present`
    - breaking only allergies section -> only `bundle.composition_allergies_section_present`
    - breaking only problems section -> only `bundle.composition_problems_section_present`
    - breaking two sections -> both findings, not the third
    - remove/replace the old grouped required-sections assertion
13. Update repair-decision tests:
    - one missing section -> one finalize-step directive
    - multiple missing sections -> union of only the affected finalize steps in stable order
14. Update repair-execution tests:
    - one missing section should rerun only its matching Composition finalize step
    - multiple missing sections should rerun only those matching finalize steps
    - keep `execution_scope == "targeted_repair"`
15. Update workflow smoke expectations:
    - new build-plan step order
    - new Composition source-step lineage
    - absence of the old grouped required-sections code on happy path
16. Update README and development plan text after tests are green.

6. Definition of Done

- Workflow validation no longer emits `bundle.required_sections_present`.
- Workflow validation now emits:
  - `bundle.composition_medications_section_present`
  - `bundle.composition_allergies_section_present`
  - `bundle.composition_problems_section_present`
- The build plan no longer contains a single grouped `finalize-composition-1` step.
- The build plan now contains three section-specific Composition finalize steps with explicit dependencies.
- `resource_construction` can rerun one Composition section finalize step without rerunning the other two.
- `repair_decision` maps each new section finding to its matching finalize step.
- Multiple missing Composition sections still union deterministically into a multi-step directive in plan order.
- Dev UI now visibly shows:
  - the incremental Composition finalization strategy in the build plan
  - three Composition section finalize steps instead of one grouped finalize step
  - section-specific validation findings
  - section-specific repair directives and narrower rerun step lists
- What should still remain grouped or deferred:
  - Composition scaffold/content rules (`type`, `status`, `title`)
  - bundle-level fullUrl/reference alignment
  - optional sections
  - generic section engines or element-level section editing

7. Risks / notes

- The main real risk is over-splitting semantics: if the new validation codes imply full semantic section correctness, the slice overclaims. Keep them about deterministic required section presence/block completeness only.
- Another real risk is losing earlier attached sections during incremental finalize reruns. The implementation must merge one section into the prior Composition scaffold, not rebuild the entire section array from scratch for every targeted rerun.
- A third risk is hidden sequencing. If the build plan is split but dependencies are not made explicit, the incremental finalize model becomes harder to inspect and easier to misread.
- This slice should not try to solve optional sections or multi-entry sections; the current schematic still models one required placeholder per fixed required section.

8. Targeted `docs/development-plan.md` updates after implementation

- In Section 8, change `Current Focus` from narrower Composition section validation/repair to the next bounded realism or validation-hardening slice.
- In Section 9, replace `Next Planned Slice` with a bounded follow-on such as: “Deepen Organization/provider-role realism or further narrow grouped Composition scaffold/content validation where current construction maturity safely supports it.”
- In Section 10, update the Phase 8 note to say required Composition section handling now uses incremental section-specific finalization and section-specific validation/repair for the fixed required trio.
- In Section 12, refine the repair/Composition assumption to note that required Composition sections now attach through deterministic section-specific finalize steps rather than one grouped finalize step.
- In Section 13, replace the current grouped Composition required-sections risk with the next real remaining Composition grouping risk, likely that Composition scaffold/content validation is still grouped at the resource level.
- In Section 16, update the immediate next objective away from required-section narrowing and toward the next narrow realism or remaining grouped Composition/content slice.
