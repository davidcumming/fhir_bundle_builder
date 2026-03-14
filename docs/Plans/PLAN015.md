1. Repo assessment

- The current repo already supports targeted `resource_construction` retries by deterministic build-step subset:
  - `repair_decision` emits `recommended_resource_construction_repair_directive`
  - `repair_execution` applies that directive
  - `resource_construction` reruns only targeted steps and preserves full step history for downstream bundle finalization
- The remaining coarse area is in workflow validation:
  - [validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/validation_builder.py) still exposes one grouped section-entry rule: `bundle.section_entry_content_present`
  - that helper currently validates all three section-entry resources together:
    - `MedicationRequest`
    - `AllergyIntolerance`
    - `Condition`
- Repair routing is still correspondingly coarse:
  - [repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/repair_decision_builder.py) maps `bundle.section_entry_content_present` to all three section-entry steps together
- Current repo maturity is now sufficient to split this safely:
  - each section-entry resource already has its own build step
  - each has its own deterministic enrichment logic in [resource_construction_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/resource_construction_builder.py)
  - current targeted retry machinery already unions multiple resource-construction findings into one ordered directive
- The main constraint now is to improve precision without inventing a generic validation-rule or repair framework.
- Other grouped findings should still remain grouped for now:
  - `bundle.required_sections_present` still maps to one Composition finalization step
  - `bundle.references_aligned_to_entry_fullurls` is still a bundle-finalization coherence rule, not a section-entry content rule

2. Proposed slice scope

- Replace the single grouped section-entry content rule with three resource-specific workflow validation rules.
- Recommended exact new codes:
  - `bundle.medicationrequest_placeholder_content_present`
  - `bundle.allergyintolerance_placeholder_content_present`
  - `bundle.condition_placeholder_content_present`
- Remove `bundle.section_entry_content_present` from active workflow validation and repair-decision mapping in this slice.
- Keep the retry target model unchanged:
  - still `resource_construction`
  - still step-subset directives
  - still single bounded retry pass
- Keep current grouped behavior only where the repo is still truly grouped:
  - Composition section presence remains grouped under `bundle.required_sections_present`
  - no change to bundle-level identity/fullUrl/reference validation
  - no change to support-resource or Composition content rules

3. Proposed narrower section-entry validation / repair approach

- Split the current grouped validation into three resource-specific checks in `validation_builder`:
  - `bundle.medicationrequest_placeholder_content_present`
    - validate deterministic placeholder content only, not clinical correctness
    - exact fields for this slice:
      - `status == "draft"`
      - `intent == "proposal"`
      - `medicationCodeableConcept.text` present
  - `bundle.allergyintolerance_placeholder_content_present`
    - exact fields:
      - `clinicalStatus.coding[0].code == "active"`
      - `verificationStatus.coding[0].code == "unconfirmed"`
      - `code.text` present
  - `bundle.condition_placeholder_content_present`
    - exact fields:
      - `clinicalStatus.coding[0].code == "active"`
      - `verificationStatus.coding[0].code == "provisional"`
      - `code.text` present
- Keep naming honest:
  - use `placeholder_content_present` rather than implying true clinical validity
- Repair-decision mapping should become one-step-per-code:
  - `bundle.medicationrequest_placeholder_content_present` -> `["build-medicationrequest-1"]`, `["medicationrequest-1"]`
  - `bundle.allergyintolerance_placeholder_content_present` -> `["build-allergyintolerance-1"]`, `["allergyintolerance-1"]`
  - `bundle.condition_placeholder_content_present` -> `["build-condition-1"]`, `["condition-1"]`
- When multiple section-entry findings occur together:
  - keep the existing union behavior
  - resulting directive should include only the affected section-entry steps, in stable build-plan order
- `repair_execution` should not need behavioral redesign:
  - its current directive-consumption path should already handle narrower single-step directives
  - this slice should prove that via tests rather than new retry-architecture code
- What remains intentionally grouped or deferred after this slice:
  - `bundle.required_sections_present` stays grouped because the repo still attaches all Composition sections in one `finalize-composition-1` step
  - no per-element section-entry patching
  - no dynamic multiplicity support
  - no generic rule DSL

4. File-level change plan

- Update [validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/validation_builder.py)
  - replace the grouped section-entry check and helper with three resource-specific checks/helpers
  - update `checks_run` to include the three new codes and remove the old grouped one
- Update [repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/repair_decision_builder.py)
  - replace the grouped route/directive mapping with three resource-specific mappings
  - preserve existing union and build-plan ordering logic
- Update tests:
  - [test_psca_validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_validation_builder.py)
  - [test_psca_repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_repair_decision_builder.py)
  - [test_psca_repair_execution_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_repair_execution_builder.py)
- Update docs:
  - [README.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md)
  - [docs/development-plan.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md)
- No model changes are required unless implementation reveals a naming/inspectability gap.
- No workflow-orchestration changes are required unless implementation reveals a broken assumption in current directive consumption.

5. Step-by-step implementation plan

1. Update workflow validation to replace `bundle.section_entry_content_present` with the three new resource-specific codes.
2. Add three narrow helper checks in `validation_builder.py`, each scoped to one resource type and one existing deterministic enrichment policy.
3. Remove the old grouped section-entry check from `checks_run` and findings emission.
4. Update `repair_decision_builder.py`:
   - add the three new codes to `_FINDING_ROUTE_MAP`
   - add the three new codes to `_RESOURCE_CONSTRUCTION_DIRECTIVE_MAP`
   - remove the old grouped section-entry mapping
5. Keep current directive union behavior unchanged so multiple section-entry failures still produce a multi-step directive automatically.
6. Update validation tests:
   - happy path should contain none of the new section-entry error codes
   - breaking only `MedicationRequest` should emit only `bundle.medicationrequest_placeholder_content_present`
   - breaking only `AllergyIntolerance` should emit only `bundle.allergyintolerance_placeholder_content_present`
   - breaking only `Condition` should emit only `bundle.condition_placeholder_content_present`
   - a combined multi-resource break should emit only the affected codes
7. Update repair-decision tests:
   - one-resource section-entry failure should yield a one-step directive
   - combined section-entry failures should yield only the affected build steps in stable order
   - remove or replace the old test that expected the grouped trio for a single missing section-entry field
8. Update repair-execution tests:
   - break only one section-entry resource and assert only that one build step reruns
   - keep one combined test proving multi-resource union still works when more than one section-entry resource is broken
   - confirm `execution_scope == "targeted_repair"` remains unchanged
9. Update README and development-plan wording to reflect that section-entry validation/repair is now resource-specific rather than always grouped.
10. Run the test suite and confirm no other grouped code assumptions were accidentally left behind.

6. Definition of Done

- Workflow validation no longer emits `bundle.section_entry_content_present`.
- Workflow validation now emits resource-specific section-entry codes:
  - `bundle.medicationrequest_placeholder_content_present`
  - `bundle.allergyintolerance_placeholder_content_present`
  - `bundle.condition_placeholder_content_present`
- `repair_decision` maps each new code to the matching single build step and placeholder.
- A single broken section-entry resource leads to a single-step `resource_construction` repair directive.
- Multiple broken section-entry resources still union deterministically into a multi-step directive in build-plan order.
- `repair_execution` visibly reruns only the affected section-entry step(s) in Dev UI through:
  - applied repair directive
  - rerun step results
  - regenerated placeholder ids
- What should still remain grouped or deferred:
  - Composition required-sections repair
  - bundle-level reference/fullUrl alignment
  - dynamic multiplicity of section entries
  - any element-level patch semantics

7. Risks / notes

- The main real risk is naming drift: if the new codes overclaim “clinical content” rather than deterministic placeholder content, the slice becomes semantically sloppy. Keep `placeholder_content_present` in the code names/messages.
- Another real risk is leaving stale grouped-code references in tests or docs after replacing the old section-entry rule.
- A smaller risk is assuming single-resource narrowing is available everywhere. It is only safe here because each of the three section-entry resources already has a distinct build step and separate deterministic enrichment logic.
- `bundle.required_sections_present` should not be split in this slice; the current repo still attaches all Composition sections in one finalize step.

8. Targeted `docs/development-plan.md` updates after implementation

- In Section 8, change `Current Focus` from narrower section-entry validation/repair to the next bounded realism or validation-hardening slice.
- In Section 9, replace `Next Planned Slice` with a bounded follow-on such as: “Deepen Organization/provider-role realism or further narrow grouped Composition section validation where current build-step structure safely supports it.”
- In Section 10, update the Phase 8 note to say section-entry validation and repair are now resource-specific for the fixed PS-CA section-entry trio.
- In Section 12, refine the repair-directive assumption to note that section-entry narrowing now operates at single-resource build-step granularity where each resource already has its own stable build step.
- In Section 13, replace the current grouped section-entry risk with the next real remaining grouping risk, likely that Composition required-sections validation is still grouped because finalization remains a single step.
- In Section 16, update the immediate next objective away from section-entry validation granularity and toward the next narrow realism or remaining grouped-validation slice.
