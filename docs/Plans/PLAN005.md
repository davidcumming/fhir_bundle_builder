## 1. Repo assessment

- The workflow now has a real `BuildPlan`, but `resource_construction` in [executors.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/executors.py) is still a pure stub. It loops through plan steps and emits `PlaceholderResourceBuildResult` records with only `step_id`, `step_kind`, `resource_type`, `placeholder_resource_id`, and canned assumptions.
- The current construction-stage artifact in [models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py) is too weak for the next slice. `ResourceConstructionStageResult` only has `built_resources` and `unresolved_items`; it does not capture actual scaffold content, per-step warnings, reference contributions, or the latest scaffold state per placeholder.
- The current `BuildPlan` is strong enough to drive a first real constructor. It already provides:
  - ordered steps
  - step kinds
  - target placeholder ids
  - profile URLs
  - explicit dependencies
  - expected inputs and outputs
  - a two-step `Composition` strategy
- The current `BundleSchematic` also remains necessary because the constructor will need:
  - section scaffold titles/codes for `Composition` finalization
  - placeholder role metadata
  - relationship context for deterministic reference wiring
- A real workflow run shows the exact current downstream shape:
  - 9 build steps
  - 8 unique placeholder ids
  - `Composition` appears twice in step results (`build-composition-1-scaffold`, `finalize-composition-1`)
  - `candidate_bundle` already deduplicates by placeholder id
- The PS-CA spec layer likely does not need expansion for this slice. The current normalized assets already gave the schematic everything it needed, and the constructor should be driven by `BuildPlan` plus `BundleSchematic`, not raw spec files.
- Tests currently cover repository loading, schematic generation, build planning, and workflow smoke execution. There is no direct test for resource construction logic yet.
- `docs/development-plan.md` now marks Phase 5 complete and sets Phase 6 as the current focus. `docs/Plans/PLAN004.md` is the relevant prior plan record.
- The constraints that matter now are:
  - keep construction deterministic and inspectable
  - avoid full data-element population
  - preserve the distinction between a scaffold artifact and a valid final FHIR resource
  - support repeated steps against the same placeholder, especially `Composition`
  - avoid introducing a broad generic construction engine

## 2. Proposed slice scope

- Replace the current stubbed stage behavior with the first real scaffold-oriented `resource_construction` result.
- Recommended scope: construct shallow resource scaffolds for all currently planned placeholders, not just a subset.
  - This is still bounded because there are only 8 unique placeholders and the scaffolds stay intentionally shallow.
  - This avoids adding “not built in this slice” branches to the plan execution model and gives the next bundle-finalization slice a stable registry shape.
- Planned constructed placeholders:
  - `patient-1`
  - `practitioner-1`
  - `organization-1`
  - `practitionerrole-1`
  - `medicationrequest-1`
  - `allergyintolerance-1`
  - `condition-1`
  - `composition-1`
- Use scaffold-only construction, not full resource population.
- Keep these things intentionally out of scope:
  - full clinical element population
  - terminology-heavy coding
  - finalized IDs/UUIDs
  - full bundle-in-progress assembly intelligence
  - validation and repair logic
  - arbitrary-IG construction behavior

## 3. Proposed resource-construction approach

- Keep `resource_construction` as one executor for now, but make it a thin adapter over a dedicated deterministic builder, for example `build_psca_resource_construction_result(plan, schematic) -> ResourceConstructionStageResult`.
- Use `BuildPlan` as the primary input boundary and fetch `bundle_schematic` from workflow state as supporting context. No raw PS-CA file inspection should happen here.
- Introduce a real construction artifact shape:
  - `ResourceConstructionStageResult`
    - `construction_mode`: `deterministic_scaffold_only`
    - `step_results`
    - `resource_registry`
    - `deferred_items`
    - `unresolved_items`
    - `evidence`
  - `ResourceConstructionStepResult`
    - `step_id`
    - `step_kind`
    - `target_placeholder_id`
    - `execution_status`: `scaffold_created` or `scaffold_updated`
    - `resource_scaffold`
    - `reference_contributions`
    - `assumptions`
    - `warnings`
    - `unresolved_fields`
  - `ResourceScaffoldArtifact`
    - `placeholder_id`
    - `resource_type`
    - `profile_url`
    - `scaffold_state`
    - `fhir_scaffold`
    - `populated_paths`
    - `deferred_paths`
    - `source_step_ids`
  - `ReferenceContribution`
    - `reference_path`
    - `target_placeholder_id`
    - `reference_value`
    - `status`
  - `ResourceRegistryEntry`
    - `placeholder_id`
    - `resource_type`
    - `latest_step_id`
    - `current_scaffold`
- Recommended scaffold strategy:
  - All scaffolds are partial FHIR-shaped dictionaries, not claimed-valid resources.
  - Every scaffold uses deterministic placeholder ids as the resource `id`.
  - References use deterministic local references such as `Patient/patient-1`, `PractitionerRole/practitionerrole-1`, etc.
- Recommended minimal scaffold content per resource type:
  - Base for all resources:
    - `resourceType`
    - `id`
    - `meta.profile` when `profile_url` exists
  - `Patient`, `Practitioner`, `Organization`
    - base scaffold only
    - unresolved fields come from the placeholder and remain explicit
  - `PractitionerRole`
    - base scaffold
    - `practitioner.reference`
    - `organization.reference`
  - `MedicationRequest`
    - base scaffold
    - `subject.reference`
  - `AllergyIntolerance`
    - base scaffold
    - `patient.reference`
  - `Condition`
    - base scaffold
    - `subject.reference`
  - `Composition` scaffold step
    - base scaffold
    - `type.coding` from the schematic (`http://loinc.org`, `60591-5`)
    - `subject.reference`
    - `author[0].reference`
    - `section: []`
  - `Composition` finalize step
    - update the existing `composition-1` scaffold, not create a second resource
    - attach 3 section blocks from `bundle_schematic.section_scaffolds`
    - each section includes `title`, `code`, and `entry.reference`
- Step-result behavior:
  - 9 step results aligned exactly to the current `BuildPlan`
  - 8 registry entries keyed by unique placeholder id
  - all first-touch resources are `scaffold_created`
  - `finalize-composition-1` is `scaffold_updated`
- Recommended reason for introducing a scaffold model instead of emitting “final” FHIR JSON:
  - it preserves honesty about incompleteness
  - it gives later bundle finalization direct FHIR-shaped material to assemble
  - it avoids redesign when later slices add more populated fields and references
- Minimal downstream integration:
  - keep `bundle_finalization` stubbed, but change it to read the `resource_registry` instead of the step-results list
  - the candidate bundle should reflect the latest scaffold per placeholder, especially the finalized `Composition`
  - no new validation behavior in this slice

## 4. File-level change plan

- Update [src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py)
  - replace the placeholder construction result shapes with real scaffold-oriented construction models
  - keep `WorkflowSkeletonRunResult` pointing at the updated stage artifact
- Create [src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/resource_construction_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/resource_construction_builder.py)
  - deterministic scaffold construction and registry update logic
- Update [src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/executors.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/executors.py)
  - make `resource_construction` call the new builder
  - make `bundle_finalization` consume the new registry shape while remaining stubbed
- Add [tests/test_psca_resource_construction_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_resource_construction_builder.py)
  - direct deterministic coverage for construction logic and registry behavior
- Update [tests/test_psca_bundle_builder_workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py)
  - assert the new construction artifact shape and candidate-bundle behavior
- Update [README.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md)
  - describe the richer resource-construction-stage output visible in Dev UI
- Update [docs/development-plan.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md)
  - targeted phase/focus changes after implementation succeeds

## 5. Step-by-step implementation plan

1. Replace the current placeholder construction models with the real stage/result/scaffold/registry contracts first.
2. Implement `build_psca_resource_construction_result` to:
   - accept the current `BuildPlan`
   - read `bundle_schematic` from workflow state
   - dispatch each step to a narrow deterministic constructor/updater
   - produce 9 ordered step results and 8 registry entries
3. Implement the narrow constructor functions with explicit per-type logic:
   - base scaffold builder
   - patient/practitioner/organization builders
   - practitionerrole builder
   - medicationrequest/allergyintolerance/condition builders
   - composition scaffold builder
   - composition finalize updater
4. Encode deterministic references using placeholder-derived local references and record them as `reference_contributions`.
5. Populate unresolved/deferred fields explicitly from placeholder `required_later_fields` plus a small type-specific deferred set where needed.
6. Integrate the builder into the executor and keep the executor itself thin.
7. Update `bundle_finalization` so it builds the candidate bundle stub from `resource_registry.current_scaffold`, not from step results.
8. Add a direct construction-builder test that asserts:
   - 9 step results are produced in plan order
   - 8 unique registry entries exist
   - `PractitionerRole` scaffold contains practitioner and organization references
   - section-entry scaffolds contain patient references
   - `Composition` scaffold step sets type/subject/author
   - `finalize-composition-1` updates the same `composition-1` scaffold with 3 sections
9. Update the workflow smoke test to assert:
   - stage output now includes scaffold content and registry entries
   - `build-composition-1-scaffold` is `scaffold_created`
   - `finalize-composition-1` is `scaffold_updated`
   - `candidate_bundle` entries are sourced from the registry and include finalized `Composition`
10. Update README wording and then apply the targeted development-plan updates.

## 6. Definition of Done

- The `resource_construction` stage no longer emits placeholder-only records; it emits a real structured construction artifact.
- The stage artifact clearly distinguishes:
  - stage-level construction metadata
  - per-plan-step execution results
  - target placeholder identity
  - resource scaffold artifacts
  - unresolved/deferred fields
  - provenance/evidence
  - latest scaffold state per placeholder
- The construction stage is driven by the existing `BuildPlan` and `BundleSchematic`, not raw spec files.
- The stage produces:
  - 9 ordered step results
  - 8 unique registry entries
  - explicit scaffold creation for all current planned placeholders
  - explicit scaffold update behavior for the `Composition` finalization step
- The constructed scaffolds include, at minimum:
  - base FHIR-shaped metadata for all current placeholder resources
  - deterministic patient/author/support references where required
  - finalized Composition sections for medications, allergies, and problems
- Dev UI shows a visibly richer resource-construction-stage artifact that another engineer can inspect without reading source first.
- The workflow still runs end to end after the slice.
- What remains intentionally stubbed after this slice:
  - full clinical content population
  - full element-level construction
  - finalized ID generation
  - full bundle-in-progress management
  - full bundle finalization intelligence
  - validation and repair logic

## 7. Risks / notes

- The key scope control is to keep the scaffolds shallow while still covering all current planned placeholders. The slice should stop at deterministic skeleton content plus basic references.
- The main modeling risk is over-claiming validity. The scaffold artifact should always make clear that it is partial FHIR-shaped content, not a finished valid resource.
- The main workflow risk is the repeated `Composition` placeholder. The registry must always store the latest `composition-1` scaffold from `finalize-composition-1`, not the earlier scaffold snapshot.
- A smaller risk is introducing too much generic dispatch machinery. Keep the constructor as a narrow explicit dispatcher over the currently supported step/resource set.

## 8. Targeted `docs/development-plan.md` updates after implementation

- In Section 8, change `Current Focus` from resource construction to the first bounded bundle-finalization / bundle-in-progress slice using constructed resource scaffolds.
- In Section 9, replace `Next Planned Slice` with a bounded follow-on such as: “Implement the first bundle-finalization foundation using the constructed resource registry and scaffold artifacts, without full validation logic.”
- In Section 10, keep `Phase 6: Resource Construction Foundation` as `In Progress` unless the implementation also proves enough bundle-in-progress behavior to satisfy the existing exit criteria.
- In Section 10, mark `Phase 6` as `Completed` only if the slice delivers both real resource-construction artifacts and a meaningful bundle-in-progress update path.
- In Section 12, add or refine the assumption that the first construction slice uses partial FHIR-shaped scaffold artifacts and deterministic placeholder-derived local references rather than fully populated valid resources.
- In Section 13, add one concise risk only if it is observed during implementation: the initial scaffold registry may need one follow-up refinement before it is sufficient for real bundle-finalization and validation work.
- In Section 16, update the immediate next objective to point at turning constructed scaffolds into a real bundle-in-progress / candidate-bundle path rather than building the first construction artifact itself.
