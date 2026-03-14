## 1. Repo assessment

- The workflow now has a real `BundleSchematic`, but the `build_plan` stage is still a stub in [executors.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/executors.py). It sorts `resource_placeholders` by resource type and creates a linear chain where every step depends on the prior step.
- The current build-plan artifact in [models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py) is too weak for the next phase. `BuildPlanStep` only has `step_id`, `sequence`, `resource_type`, `depends_on`, `build_purpose`, and `optional`. It does not capture placeholder mapping, step category, prerequisite rationale, expected inputs, or expected outputs.
- The current schematic is strong enough to drive a first real planner. It already exposes:
  - bundle scaffold with required entry placeholders
  - composition scaffold
  - section scaffolds with `section_key`, `slice_name`, and `entry_placeholder_ids`
  - resource placeholders with `placeholder_id`, `resource_type`, `role`, `profile_url`, and `required_later_fields`
  - relationships for `composition_subject`, `composition_author`, `practitionerrole-*`, and `composition_section_entry`
- A real workflow run confirms the current schematic shape is stable and narrow:
  - placeholders: `patient-1`, `practitioner-1`, `organization-1`, `practitionerrole-1`, `medicationrequest-1`, `allergyintolerance-1`, `condition-1`, `composition-1`
  - section scaffolds: medications, allergies, problems
  - relationship set is explicit enough to derive author/support and Composition prerequisites
- The current `resource_construction` and `bundle_finalization` stages are still stubbed and currently assume one build step maps cleanly to one resource placeholder. That assumption will break if the build plan introduces a two-step Composition path, so those stages will need narrow plumbing updates even though they remain stubbed.
- Current tests cover repository loading, schematic generation, and workflow smoke path. There is no direct test for build-planning logic yet.
- `docs/development-plan.md` now marks Phase 4 complete and sets Phase 5 as the current focus. `docs/Plans/PLAN003.md` captures the schematic-generation plan and is the most relevant prior plan record for this slice.
- The main constraints now are:
  - planning must be driven from the schematic, not raw spec files
  - planning must remain deterministic and inspectable
  - this slice must stop at ordering/prerequisites/outputs, not resource creation
  - the plan artifact should be strong enough to feed the next resource-construction slice without redesign

## 2. Proposed slice scope

- Replace `BuildPlanStub` with the first real `BuildPlan` artifact.
- Keep the planning scope narrow to the current schematic only:
  - `Patient`
  - `Practitioner`
  - `Organization`
  - `PractitionerRole`
  - section-entry placeholders for medications, allergies, and problems
  - `Composition` as a two-step planned target:
    - initial scaffold step
    - later composition-finalization step
- Do not add a build step for bundle assembly. `bundle_finalization` remains a later workflow concern and should stay explicitly deferred in this slice.
- Use deterministic rule application only. No LLM behavior, no prompt logic, and no re-reading raw PS-CA package files from the planner.
- Keep these things intentionally out of scope:
  - actual FHIR resource creation
  - element population logic
  - generated IDs or full reference resolution
  - validation/repair logic
  - optional PS-CA sections
  - generalized arbitrary-IG planning infrastructure

## 3. Proposed build-planning approach

- Add a dedicated deterministic builder, for example `build_psca_build_plan(schematic: BundleSchematic) -> BuildPlan`, so the executor stays thin.
- Rename the current stub types to real planning types:
  - `BuildPlan`
  - expanded `BuildPlanStep`
  - `BuildStepDependency`
  - `BuildStepInput`
  - `BuildStepOutput`
  - `BuildPlanEvidence`
- Recommended `BuildPlan` artifact shape:
  - `plan_basis`
    - `deterministic_schematic_dependency_plan`
  - `composition_strategy`
    - `two_step_scaffold_then_finalize`
  - `steps`
  - `deferred_items`
  - `evidence`
- Recommended `BuildPlanStep` shape:
  - `step_id`
  - `sequence`
  - `step_kind`
    - `anchor_resource`
    - `support_resource`
    - `section_entry_resource`
    - `composition_scaffold`
    - `composition_finalize`
  - `target_placeholder_id`
  - `resource_type`
  - `profile_url`
  - `owning_section_key` when applicable
  - `build_purpose`
  - `dependencies`
  - `expected_inputs`
  - `expected_outputs`
  - `optional`
- Recommended dependency/input/output submodels:
  - `BuildStepDependency`
    - `prerequisite_step_id`
    - `dependency_type`
    - `reason`
  - `BuildStepInput`
    - `input_key`
    - `input_type`
    - `required`
    - `description`
  - `BuildStepOutput`
    - `output_key`
    - `output_type`
    - `description`
- Use this narrow deterministic ordering logic:
  1. `build-patient-1`
     - first anchor resource
  2. `build-practitioner-1`
     - support resource
  3. `build-organization-1`
     - support resource
  4. `build-practitionerrole-1`
     - depends on practitioner and organization because the schematic already encodes those relationships
  5. `build-composition-1-scaffold`
     - depends on patient and practitionerrole because the schematic encodes `Composition.subject` and `Composition.author`
     - does not yet depend on section-entry resources
  6. `build-medicationrequest-1`
     - section-entry step for medications
     - hard-depends on patient only in this slice
  7. `build-allergyintolerance-1`
     - section-entry step for allergies
     - hard-depends on patient only
  8. `build-condition-1`
     - section-entry step for problems
     - hard-depends on patient only
  9. `finalize-composition-1`
     - depends on composition scaffold step plus all section-entry steps
     - represents attaching section entry references and completing section-level assembly
- Derivation rules should come primarily from the schematic:
  - `composition_subject` drives patient-before-composition
  - `composition_author` plus `practitionerrole-*` drive support ordering
  - `composition_section_entry` plus `section_scaffolds` drive section-entry planning
  - `resource_placeholders` drive placeholder-to-step mapping
- The planner should not invent hard prerequisites that are not justified by the schematic or the narrow planning rules. Example: `MedicationRequest` may later need richer requester logic, but in this slice that should be recorded as expected context or deferred detail, not a hard dependency unless it is already encoded in the schematic.
- Recommended expected outputs per step:
  - anchor/support/section-entry steps:
    - `resource_artifact:<placeholder_id>`
    - `reference_handle:<placeholder_id>`
  - composition scaffold step:
    - `resource_artifact:composition-1`
    - `reference_handle:composition-1`
    - `composition_scaffold_ready:composition-1`
  - composition finalize step:
    - `resource_artifact:composition-1:section-finalized`
    - `composition_sections_attached:composition-1`
- Recommended deferred items in the plan artifact:
  - bundle entry assembly remains outside build planning
  - no element-level population logic
  - no generated IDs/full reference patching
  - no validation-driven replanning
- Because the current workflow continues past `build_plan`, update the stub downstream behavior minimally:
  - `resource_construction` should consume `target_placeholder_id` instead of synthesizing placeholder ids from sequence
  - `bundle_finalization` should deduplicate by placeholder id so a two-step Composition plan does not create duplicate Composition bundle entries
- Keep naming honest:
  - `composition_scaffold`
  - `composition_finalize`
  - `expected_inputs`
  - `expected_outputs`
  - `deferred_items`

## 4. File-level change plan

- Update [src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py)
  - replace `BuildPlanStub` with real planning models
  - expand `BuildPlanStep` and add typed dependency/input/output/evidence models
  - keep the final workflow output pointing at the new `BuildPlan`
- Create [src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/build_plan_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/build_plan_builder.py)
  - deterministic PS-CA build-planning logic from `BundleSchematic`
- Update [src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/executors.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/executors.py)
  - make `build_plan` call the new builder
  - adapt `resource_construction` and `bundle_finalization` only as needed to preserve end-to-end workflow behavior with the richer plan artifact
- Add [tests/test_psca_build_plan_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_build_plan_builder.py)
  - direct deterministic coverage for build-plan generation
- Update [tests/test_psca_bundle_builder_workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py)
  - assert the new build-plan artifact shape, ordering, dependencies, and downstream deduped placeholder handling
- Update [README.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md)
  - describe the richer build-plan-stage output visible in Dev UI
- Update [docs/development-plan.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md)
  - targeted phase/status/focus changes after implementation succeeds

## 5. Step-by-step implementation plan

1. Replace the stub build-plan models with the real planning artifact contract first so the builder and executors are anchored to a stable typed shape.
2. Implement `build_psca_build_plan` as a deterministic planner that reads only the `BundleSchematic` and emits:
   - the exact nine-step sequence above
   - explicit dependency objects
   - expected inputs and outputs per step
   - plan evidence and deferred items
3. Integrate the planner into the `build_plan` executor and keep the executor itself as a thin adapter.
4. Update the still-stubbed `resource_construction` stage so its placeholder outputs are keyed from `target_placeholder_id` and remain compatible with the richer plan.
5. Update the still-stubbed `bundle_finalization` stage so it assembles candidate bundle entries from unique placeholder ids rather than one entry per build step.
6. Add a direct build-plan builder test that asserts:
   - exact step order
   - exact composition two-step strategy
   - practitionerrole depends on practitioner and organization
   - composition scaffold depends on patient and practitionerrole
   - composition finalize depends on composition scaffold plus all section-entry steps
   - section-entry steps map correctly to section keys and placeholders
7. Update the workflow smoke test so it asserts:
   - the new build-plan artifact shape
   - expected step kinds and `target_placeholder_id` values
   - candidate bundle entry count reflects unique placeholders rather than raw step count
8. Update README wording for Dev UI inspectability and then apply the targeted development-plan updates.

## 6. Definition of Done

- The `build_plan` stage no longer emits a simple linear placeholder list; it emits a real structured `BuildPlan` artifact.
- The build plan artifact clearly distinguishes:
  - plan metadata
  - ordered build steps
  - prerequisite relationships
  - expected step inputs/context
  - expected step outputs/artifacts
  - deferred items
  - provenance/evidence
- The plan is derived from the existing `BundleSchematic`, not from raw spec-file reinspection.
- The plan includes, at minimum, these ordered steps:
  - patient anchor
  - practitioner support
  - organization support
  - practitionerrole support
  - composition scaffold
  - medication section entry
  - allergy section entry
  - problem section entry
  - composition finalization
- The build plan shows explicit hard dependencies for:
  - practitionerrole on practitioner and organization
  - composition scaffold on patient and practitionerrole
  - composition finalization on composition scaffold and all section-entry steps
- Dev UI shows a visibly richer build-plan-stage artifact that another engineer can inspect without reading the source first.
- The workflow still runs end to end after the slice, even though:
  - resource construction remains stubbed
  - bundle finalization remains stubbed
  - validation and repair remain stubbed
- What still remains intentionally stubbed after this slice:
  - actual resource creation
  - data element population
  - generated IDs and full reference patching
  - bundle assembly intelligence beyond existing placeholder finalization
  - validation-driven replanning

## 7. Risks / notes

- The only meaningful modeling decision in this slice is whether `Composition` should stay one step or become two. Recommended default: split it now into scaffold and finalize, because that is the clearest deterministic shape and avoids redesign in the next resource-construction slice.
- The current schematic does not encode every future clinical dependency. The planner should therefore separate hard prerequisites from expected context and avoid inventing stronger dependencies than the artifact justifies.
- The main scope risk is expanding into resource-construction logic while trying to make the plan “realistic.” This slice should stop at planning metadata, ordering, and declared prerequisites/outputs.
- A smaller plumbing risk is downstream duplication once one placeholder maps to multiple steps. The plan should explicitly handle that in the stub `resource_construction` and `bundle_finalization` stages rather than leaving it implicit.

## 8. Targeted `docs/development-plan.md` updates after implementation

- In Section 8, change `Current Focus` from build planning to the first bounded resource-construction slice using the real build plan artifact.
- In Section 9, replace `Next Planned Slice` with a bounded Phase 6 entry such as: “Implement the first PS-CA resource-construction slice from the real build plan, without full bundle population.”
- In Section 10, mark `Phase 5: Build Planning` as `Completed` only if the workflow emits the structured build plan artifact described above and the plan is inspectable in Dev UI.
- In Section 10, keep `Phase 6: Resource Construction Foundation` as the next active phase and move it to `In Progress` only if that next slice is approved immediately after this one.
- In Section 12, add or refine the assumption that the first real build plan intentionally uses a two-step Composition strategy and a limited hard-dependency set derived from the current schematic.
- In Section 13, add one concise risk only if observed during implementation: the initial hard-dependency model for section-entry resources may still be too shallow and may require one follow-up refinement during the first resource-construction slice.
- In Section 16, update the immediate next objective to point at executing the first narrow resource-construction path from the structured build plan rather than deriving the plan itself.
