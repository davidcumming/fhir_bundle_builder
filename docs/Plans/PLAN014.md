1. Repo assessment

- The current repo already has the main seam needed for this slice:
  - `repair_decision` deterministically routes known workflow findings to `resource_construction`.
  - `repair_execution` can now execute `resource_construction`, but only as a whole-stage rebuild.
- The current `resource_construction` implementation is already step-structured, not monolithic:
  - build steps are explicit in `BuildPlanStep.step_id`.
  - `ResourceConstructionStepResult` is already step-scoped.
  - Composition is already split into:
    - `build-composition-1-scaffold`
    - `finalize-composition-1`
- That means the safest current narrowing unit is not “element patching” and not generic placeholder mutation. It is a deterministic subset of existing build-plan steps.
- The current validation codes that already route to `resource_construction` are meaningful enough to support a first directive map:
  - `bundle.composition_type_matches_psca_summary`
  - `bundle.composition_enriched_content_present`
  - `bundle.required_sections_present`
  - `bundle.patient_identity_content_present`
  - `bundle.practitioner_identity_content_present`
  - `bundle.practitionerrole_author_context_present`
  - `bundle.section_entry_content_present`
- The current key constraint is that validation codes are not all equally granular:
  - patient/practitioner/practitionerrole findings naturally map to one build step
  - Composition findings map to one or two Composition steps
  - `bundle.section_entry_content_present` is still grouped, so it cannot yet safely target one specific section-entry resource
- The current `resource_construction` artifact shape does not yet distinguish:
  - full build vs targeted repair rerun
  - applied repair directive
  - regenerated vs reused resources
- The current `repair_decision` artifact does not yet carry a structured `resource_construction` directive; it only carries the stage target.
- The current `repair_execution` artifact does not yet expose an applied directive; it only shows the coarse executed target plus rerun stages.
- Since the workflow happy path still lands on `standards_validation_external`, executed targeted repair must continue to be proven through direct unit tests against intentionally broken artifacts.

2. Proposed slice scope

- Introduce the first narrow structured repair-directive model for `resource_construction`.
- Recommended narrowing unit for this slice:
  - `build step subset`
  - not placeholder-only
  - not enrichment-category-only
  - not element patching
- Reason:
  - the repo already executes `resource_construction` as ordered build steps
  - Composition already spans two steps, so step-level targeting is cleaner than raw placeholder targeting
  - one current validation code (`bundle.section_entry_content_present`) is grouped across three resources, so step-subset directives can honestly target a small step set instead of pretending to know one exact placeholder
- Keep the retry model bounded:
  - still one retry attempt maximum
  - still no recursive loop
  - still no build-plan or schematic retry
- Keep the current executable retry targets unchanged at the stage level:
  - `bundle_finalization`
  - `resource_construction`
- Change only how `resource_construction` retry is executed:
  - full-stage rebuild becomes the fallback-free normal path only when no directive exists in older contexts
  - this new slice should use a targeted step-subset rerun for the known mapped `resource_construction` findings
- What should remain intentionally coarse or deferred after this slice:
  - `bundle.section_entry_content_present` still reruns all three section-entry build steps as a group
  - no element-level patching
  - no generic directive DSL
  - no arbitrary-resource repair semantics
  - no retry support for `build_plan_or_schematic` or `human_intervention`

3. Proposed `resource_construction` repair-directive approach

- Add a small typed directive model, for example:
  - `ResourceConstructionExecutionScope = Literal["full_build", "targeted_repair"]`
  - `ResourceConstructionRepairDirectiveScope = Literal["build_step_subset"]`
  - `ResourceConstructionRepairDirective`
    - `directive_basis = "validation_finding_code_map"`
    - `scope = "build_step_subset"`
    - `trigger_finding_codes`
    - `target_step_ids`
    - `target_placeholder_ids`
    - `rationale`
- Add the directive in two places:
  - `RepairDecisionResult.recommended_resource_construction_repair_directive: ResourceConstructionRepairDirective | None`
  - `RepairExecutionResult.applied_resource_construction_repair_directive: ResourceConstructionRepairDirective | None`
- Extend `ResourceConstructionStageResult` so the artifact itself shows whether it was a normal build or a targeted repair:
  - `execution_scope`
  - `applied_repair_directive`
  - `regenerated_placeholder_ids`
  - `reused_placeholder_ids`
- Recommended deterministic mapping from validation code to directive target step ids:
  - `bundle.patient_identity_content_present`
    - `["build-patient-1"]`
    - placeholder `["patient-1"]`
  - `bundle.practitioner_identity_content_present`
    - `["build-practitioner-1"]`
    - placeholder `["practitioner-1"]`
  - `bundle.practitionerrole_author_context_present`
    - `["build-practitionerrole-1"]`
    - placeholder `["practitionerrole-1"]`
  - `bundle.composition_type_matches_psca_summary`
    - `["build-composition-1-scaffold", "finalize-composition-1"]`
    - placeholder `["composition-1"]`
  - `bundle.composition_enriched_content_present`
    - `["build-composition-1-scaffold", "finalize-composition-1"]`
    - placeholder `["composition-1"]`
  - `bundle.required_sections_present`
    - `["finalize-composition-1"]`
    - placeholder `["composition-1"]`
  - `bundle.section_entry_content_present`
    - `["build-medicationrequest-1", "build-allergyintolerance-1", "build-condition-1"]`
    - placeholders `["medicationrequest-1", "allergyintolerance-1", "condition-1"]`
- If multiple mapped `resource_construction` findings are present in one decision:
  - union the step ids
  - union the placeholder ids
  - preserve stable build-plan order in the final directive
  - dedupe codes and targets
- Recommended construction rerun behavior:
  - keep `build_psca_resource_construction_result(...)` as the main builder
  - extend it with optional inputs:
    - `prior_result: ResourceConstructionStageResult | None = None`
    - `repair_directive: ResourceConstructionRepairDirective | None = None`
  - if no directive:
    - current full-build behavior remains unchanged
  - if directive is present:
    - require `prior_result`
    - seed the registry from `prior_result.resource_registry`
    - iterate `plan.steps` in normal order
    - rerun only steps whose `step_id` is in `directive.target_step_ids`
    - update registry entries only for rerun steps
    - leave all other registry entries reused from the prior result
    - emit `step_results` only for rerun steps
    - emit a complete final `resource_registry` combining reused and regenerated entries
- Recommended `repair_execution` behavior for `resource_construction` after this slice:
  - consume the structured directive from `repair_decision`
  - call targeted `resource_construction`
  - then rerun:
    - `bundle_finalization`
    - `validation`
    - `repair_decision`
  - store:
    - the applied directive on `repair_execution`
    - the targeted `post_retry_resource_construction`
    - the downstream regenerated artifacts
- Keep `bundle_finalization` retry behavior unchanged.
- Assumption/default chosen:
  - step-level narrowing is the first slice
  - placeholder ids remain inspectability metadata
  - execution primitive is step-subset rerun because that matches current repo maturity best

4. File-level change plan

- Update [models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py)
  - add `ResourceConstructionRepairDirective` and related literals
  - extend `ResourceConstructionStageResult`
  - extend `RepairDecisionResult`
  - extend `RepairExecutionResult`
- Update [resource_construction_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/resource_construction_builder.py)
  - add optional targeted-repair inputs
  - implement seeded-registry targeted step rerun
  - emit targeted repair evidence and regenerated/reused ids
- Update [repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/repair_decision_builder.py)
  - derive structured `resource_construction` directives from routed finding codes
- Update [repair_execution_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/repair_execution_builder.py)
  - consume the directive
  - execute targeted `resource_construction` rerun
  - preserve existing `bundle_finalization` retry behavior
- Update tests:
  - [tests/test_psca_resource_construction_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_resource_construction_builder.py)
  - [tests/test_psca_repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_repair_decision_builder.py)
  - [tests/test_psca_repair_execution_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_repair_execution_builder.py)
  - [tests/test_psca_bundle_builder_workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py)
- Update docs:
  - [README.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md)
  - [docs/development-plan.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md)

5. Step-by-step implementation plan

1. Extend the shared models first:
   - add the directive model and scope literals
   - add `execution_scope`, `applied_repair_directive`, `regenerated_placeholder_ids`, and `reused_placeholder_ids` to `ResourceConstructionStageResult`
   - add recommended/applied directive fields to `RepairDecisionResult` and `RepairExecutionResult`
2. Add deterministic directive mapping in `repair_decision_builder.py`:
   - build a small `_RESOURCE_CONSTRUCTION_DIRECTIVE_MAP`
   - derive a combined directive only when `recommended_target == "resource_construction"`
   - store it on `RepairDecisionResult`
3. Refactor `build_psca_resource_construction_result(...)`:
   - keep current full-build path as the default
   - add targeted repair mode with `prior_result` + `repair_directive`
   - seed registry from prior result
   - rerun only targeted step ids in build-plan order
   - keep step results limited to executed repair steps
   - return a full merged registry
4. Define exact targeted rerun semantics:
   - full build:
     - current behavior unchanged
   - targeted repair:
     - `construction_mode` stays deterministic content-enriched
     - `execution_scope = "targeted_repair"`
     - `applied_repair_directive` populated
     - `regenerated_placeholder_ids` derived from rerun steps
     - `reused_placeholder_ids` derived from untouched prior registry entries
5. Update `repair_execution_builder.py`:
   - for `resource_construction` target, require/use the directive from `repair_decision`
   - call targeted `build_psca_resource_construction_result(...)`
   - keep rerun chain:
     - `resource_construction`
     - `bundle_finalization`
     - `validation`
     - `repair_decision`
   - store the applied directive on the execution result
6. Preserve the existing `bundle_finalization` retry path exactly as-is except for any small refactor needed to share downstream code.
7. Add targeted unit tests for `resource_construction_builder.py`:
   - targeted patient repair reruns only `build-patient-1`
   - targeted required-sections repair reruns only `finalize-composition-1`
   - resulting registry is still complete
   - targeted stage artifact reports:
     - `execution_scope == "targeted_repair"`
     - correct directive
     - correct regenerated vs reused ids
8. Add directive-generation tests in `repair_decision_builder.py`:
   - patient finding -> patient step directive
   - required sections finding -> composition finalize directive
   - grouped section-entry content finding -> three-step directive
   - combined findings -> unioned, ordered directive
9. Add repair-execution tests:
   - keep current deferred happy path
   - keep current executed bundle-finalization retry
   - change executed `resource_construction` retry assertions to require:
     - applied directive present
     - `post_retry_resource_construction.execution_scope == "targeted_repair"`
     - rerun step results are limited to the directive target steps
     - downstream validation returns to `passed_with_warnings`
   - add one grouped section-entry repair test proving the directive reruns the three section-entry steps rather than the whole stage
10. Update workflow smoke assertions only enough to prove:
   - normal path still does not execute repair
   - no directive is applied on the happy path
   - top-level first-pass artifacts remain unchanged
11. Update README and development-plan wording after tests are green.

6. Definition of Done

- The repo contains a real structured `ResourceConstructionRepairDirective` model.
- `repair_decision` now emits a structured `resource_construction` directive when the recommended target is `resource_construction`.
- `repair_execution` uses that directive to run a narrower targeted `resource_construction` retry instead of always rebuilding the whole stage.
- Targeted rerun is visibly narrower in artifacts:
  - `post_retry_resource_construction.execution_scope == "targeted_repair"`
  - applied directive is present
  - regenerated placeholder ids are explicit
  - reused placeholder ids are explicit
  - `step_results` for targeted repair contain only rerun steps
- The downstream chain remains bounded and unchanged:
  - `bundle_finalization`
  - `validation`
  - `repair_decision`
- Dev UI now clearly shows:
  - the recommended `resource_construction` directive
  - the applied directive during retry
  - whether the rerun was full build or targeted repair
  - which resources/placeholders were regenerated vs reused
- What remains intentionally coarse or deferred:
  - `bundle.section_entry_content_present` still targets the full section-entry trio as one small group
  - no element-level patches
  - no generic repair DSL
  - no multi-pass retry loop
  - no retry support for `build_plan_or_schematic` or `human_intervention`

7. Risks / notes

- The main real risk is directive granularity mismatch. The current validation layer still has at least one grouped code (`bundle.section_entry_content_present`), so that case cannot yet narrow to one exact section-entry resource.
- A second real risk is stale reused registry state if targeted repair mode does not clearly seed from the prior result and then rerun step ids in stable plan order.
- A third risk is overcomplicating the directive model. This slice should stay at “build step subset” and avoid introducing category trees, patch semantics, or generic rule engines.
- Composition is the main reason placeholder-only directives are weaker than step-subset directives in the current repo: one placeholder spans two meaningful construction steps with different repair semantics.

8. Targeted `docs/development-plan.md` updates after implementation

- In Section 8, change `Current Focus` from the first narrow repair-directive slice to the next bounded realism/quality slice after targeted `resource_construction` repair directives exist.
- In Section 9, replace `Next Planned Slice` with a bounded follow-on such as: “Deepen Organization/provider-role realism or split grouped section-entry validation/repair into narrower resource-specific directives.”
- In Section 10, keep `Phase 8: Minimal End-to-End PS-CA Workflow` as `In Progress`.
- In Section 10, update the Phase 8 note to state that `resource_construction` retry now supports a first targeted repair-directive mode rather than only whole-stage rebuilds.
- In Section 12, add or refine an assumption that the first repair-directive slice narrows `resource_construction` by deterministic build-step subsets, not by generic element-level patching.
- In Section 13, add one concise risk only if observed during implementation: grouped validation codes, especially section-entry content, may need future splitting before repair directives can narrow to single-resource granularity.
- In Section 16, update the immediate next objective to the next narrow realism or validation-granularity slice, not broader retry orchestration.
