## 1. Repo assessment

- The workflow now has a real `resource_construction` stage, and [resource_construction_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/resource_construction_builder.py) produces 9 ordered step results plus 8 registry entries keyed by placeholder id.
- The `bundle_finalization` stage in [executors.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/executors.py) is still a stub. It currently just converts `resource_registry` into a flat list of `CandidateBundleEntry` records and wraps them in `CandidateBundleStub`.
- The current finalization artifact in [models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py) is too weak for the next slice. `CandidateBundleStub` only has `bundle_id`, `bundle_type`, `entry_count`, and a flat `entries` list. It does not contain a real FHIR `Bundle` scaffold, bundle-level deferred fields, entry assembly provenance, or stage-level finalization evidence.
- The current `BundleSchematic` already exposes the key assembly inputs this slice needs:
  - `bundle_scaffold.profile_url`
  - `bundle_scaffold.bundle_type`
  - `bundle_scaffold.required_entry_placeholder_ids`
  - ordered `bundle_entry` relationships inside `relationships`
- The current `ResourceConstructionStageResult` already exposes the key runtime inputs this slice needs:
  - `resource_registry[*].placeholder_id`
  - `resource_registry[*].latest_step_id`
  - `resource_registry[*].current_scaffold`
  - finalized `composition-1` scaffold with 3 attached sections
- The current `BuildPlan` should influence this slice only lightly. It is already reflected indirectly in construction evidence and latest-step provenance, so finalization does not need to re-derive entry order from plan steps.
- The workflow smoke test in [test_psca_bundle_builder_workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py) currently proves only that `candidate_bundle` has 8 entries and the `Composition` scaffold has 3 sections. There is no direct test for bundle finalization logic yet.
- `docs/development-plan.md` already sets this as the current focus. `docs/Plans/PLAN005.md` is the relevant prior plan record because it established the construction registry that this slice should now consume.
- The constraints that matter now are:
  - keep finalization deterministic and inspectable
  - assemble from registry/scaffold artifacts, not raw PS-CA files
  - create a real candidate bundle scaffold without pretending it is validated
  - keep validation and repair stubbed
  - avoid a broad generic bundle assembly framework

## 2. Proposed slice scope

- Replace `CandidateBundleStub` with the first real structured candidate-bundle / bundle-finalization artifact.
- Keep this slice narrow:
  - assemble one real `Bundle`-shaped candidate scaffold from the existing registry
  - enforce required document bundle expectations already present in the schematic
  - produce explicit entry assembly metadata and provenance
  - keep validation unchanged except for consuming the richer finalization artifact
- Recommended artifact strategy:
  - stage artifact: `CandidateBundleResult`
  - nested candidate-bundle payload: `CandidateBundleArtifact`
- In-scope assembled resources:
  - `Composition`
  - `Patient`
  - `PractitionerRole`
  - `Practitioner`
  - `Organization`
  - `MedicationRequest`
  - `AllergyIntolerance`
  - `Condition`
- Out of scope after this slice:
  - full validation
  - bundle identifier population
  - bundle timestamp population
  - `entry.fullUrl` strategy
  - deep reference consistency repair
  - arbitrary-IG bundle assembly behavior

## 3. Proposed bundle-finalization approach

- Add a dedicated deterministic builder, for example `build_psca_candidate_bundle_result(construction, schematic, normalized_request) -> CandidateBundleResult`, and keep the executor thin.
- Replace the current finalization models with this contract:
  - `CandidateBundleResult`
    - `assembly_mode`: `deterministic_registry_bundle_scaffold`
    - `candidate_bundle`
    - `entry_assembly`
    - `deferred_items`
    - `unresolved_items`
    - `evidence`
  - `CandidateBundleArtifact`
    - `bundle_id`
    - `profile_url`
    - `bundle_type`
    - `bundle_state`: `candidate_scaffold_assembled`
    - `entry_count`
    - `fhir_bundle`
    - `populated_paths`
    - `deferred_paths`
  - `BundleEntryAssemblyResult`
    - `sequence`
    - `placeholder_id`
    - `resource_type`
    - `required_by_bundle_scaffold`
    - `source_registry_step_id`
    - `scaffold_state`
    - `entry_path`
  - `CandidateBundleEvidence`
    - `source_resource_construction_stage_id`
    - `source_schematic_stage_id`
    - `source_build_plan_stage_id`
    - `required_entry_placeholder_ids`
    - `ordered_placeholder_ids`
    - `source_refs`
- Build the actual candidate bundle scaffold as a partial FHIR `Bundle` dictionary:
  - `resourceType = "Bundle"`
  - `id = f"{package_id}-{scenario_label}"`
  - `meta.profile = [bundle_scaffold.profile_url]`
  - `type = bundle_scaffold.bundle_type`
  - `entry = [{"resource": <registry scaffold>}, ...]`
- Do not include `Bundle.identifier`, `Bundle.timestamp`, or `entry.fullUrl` in this slice. Track them explicitly as deferred bundle-level fields instead. This keeps the bundle scaffold valid in shape without inventing premature placeholder policies.
- Derive entry order from `bundle_schematic.relationships` where `relationship_type == "bundle_entry"`, preserving relationship order from the schematic. For the current repo state, that yields:
  1. `composition-1`
  2. `patient-1`
  3. `practitionerrole-1`
  4. `practitioner-1`
  5. `organization-1`
  6. `medicationrequest-1`
  7. `allergyintolerance-1`
  8. `condition-1`
- Finalization guardrails should be explicit and deterministic:
  - fail if any `bundle_scaffold.required_entry_placeholder_ids` are missing from the registry
  - fail if any placeholder referenced by a `bundle_entry` relationship is missing from the registry
  - fail if `composition-1` is present but not in scaffold state `sections_attached`
- The assembled candidate bundle should include every registry entry referenced by a bundle-entry relationship. This slice should not invent extra entries beyond what the schematic declares.
- Keep the distinction honest:
  - `CandidateBundleArtifact` is a bundle scaffold / candidate bundle
  - it is not a final validated bundle
- Reason to keep a typed stage artifact rather than exposing only raw `Bundle` JSON:
  - validation will need bundle-level deferred fields, entry provenance, and source stage evidence
  - Dev UI inspection is clearer when the FHIR-shaped bundle sits inside a stage artifact with explicit assembly metadata
  - later slices can add bundle-in-progress state without redesigning the finalization interface
- Validation should continue to be stubbed, but its input type should change to the richer `CandidateBundleResult`. It can still emit the same placeholder finding while now referring to a real candidate bundle scaffold.

## 4. File-level change plan

- Update [src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py)
  - replace `CandidateBundleEntry` and `CandidateBundleStub` with the real candidate-bundle finalization models
  - keep `WorkflowSkeletonRunResult.candidate_bundle` as the top-level field name, but change its type to the new stage artifact
- Create [src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/bundle_finalization_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/bundle_finalization_builder.py)
  - deterministic registry-to-bundle assembly logic
- Update [src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/executors.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/executors.py)
  - make `bundle_finalization` call the new builder
  - make `validation` consume the richer finalization artifact while remaining stubbed
- Add [tests/test_psca_bundle_finalization_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_finalization_builder.py)
  - direct deterministic coverage for bundle assembly
- Update [tests/test_psca_bundle_builder_workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py)
  - assert the richer candidate-bundle artifact shape and real `Bundle` scaffold contents
- Update [README.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md)
  - describe the richer bundle-finalization-stage output visible in Dev UI
- Update [docs/development-plan.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md)
  - targeted phase/focus/status updates after implementation succeeds

## 5. Step-by-step implementation plan

1. Replace the current candidate-bundle models with the real finalization artifact contract first so the builder, executor, validation stub, and tests all target one stable shape.
2. Implement `build_psca_candidate_bundle_result` to:
   - accept `ResourceConstructionStageResult`, `BundleSchematic`, and `NormalizedBuildRequest`
   - derive ordered placeholder ids from schematic `bundle_entry` relationships
   - validate required-entry presence and finalized `Composition` state
   - assemble a FHIR-shaped `Bundle` scaffold from the latest registry scaffolds
   - emit entry assembly details, deferred fields, unresolved items, and evidence
3. Use these exact bundle scaffold rules:
   - `Bundle.resourceType = "Bundle"`
   - `Bundle.id = f"{package_id}-{scenario_label}"`
   - `Bundle.meta.profile[0] = bundle_scaffold.profile_url`
   - `Bundle.type = bundle_scaffold.bundle_type`
   - `Bundle.entry[i].resource = registry_entry.current_scaffold.fhir_scaffold`
   - omit `identifier`, `timestamp`, and `fullUrl` from the FHIR bundle itself and record them in `deferred_paths`
4. Use these exact entry-order rules:
   - iterate `bundle_schematic.relationships` in existing order
   - take only relationships with `relationship_type == "bundle_entry"`
   - use each relationship’s `target_id` as the ordered placeholder id
   - mark `required_by_bundle_scaffold=True` when the placeholder id is in `bundle_scaffold.required_entry_placeholder_ids`
5. Populate candidate-bundle evidence from existing stage artifacts:
   - `construction.stage_id`
   - `construction.evidence.source_build_plan_stage_id`
   - `schematic.stage_id`
   - `bundle_scaffold.required_entry_placeholder_ids`
   - ordered placeholder ids
   - shared `source_refs`
6. Wire the builder into the `bundle_finalization` executor and keep the executor itself thin.
7. Change the stub `validation` executor input type to the new `CandidateBundleResult`, but keep its behavior placeholder-only.
8. Add a direct builder test that asserts:
   - `candidate_bundle.candidate_bundle.fhir_bundle["resourceType"] == "Bundle"`
   - bundle `id`, `meta.profile`, and `type` are populated deterministically
   - entry order is exactly `composition, patient, practitionerrole, practitioner, organization, medicationrequest, allergyintolerance, condition`
   - `Composition` is first and already contains 3 section entries
   - required placeholders from `bundle_scaffold.required_entry_placeholder_ids` are marked and present
   - deferred bundle paths include `identifier` and `timestamp`
9. Add one direct failure-path test:
   - if `composition-1` is removed from the registry or not in `sections_attached` state, the builder raises a clear `ValueError`
10. Update the workflow smoke test so it asserts:
   - `candidate_bundle.assembly_mode == "deterministic_registry_bundle_scaffold"`
   - `candidate_bundle.candidate_bundle.bundle_state == "candidate_scaffold_assembled"`
   - `candidate_bundle.candidate_bundle.entry_count == 8`
   - the nested FHIR bundle has `resourceType`, `id`, `meta.profile`, `type`, and ordered `entry.resource` values
   - validation still runs after bundle finalization with the richer artifact in place
11. Update README wording and then apply the targeted development-plan updates.

## 6. Definition of Done

- The `bundle_finalization` stage no longer emits a flat placeholder-entry list; it emits a real structured finalization artifact.
- The stage artifact clearly distinguishes:
  - stage-level finalization metadata
  - the candidate bundle scaffold
  - entry assembly details
  - unresolved/deferred bundle fields
  - provenance/evidence
- The candidate bundle contains a real FHIR `Bundle`-shaped scaffold with:
  - `resourceType = "Bundle"`
  - deterministic `id`
  - `meta.profile`
  - `type = "document"`
  - ordered `entry.resource` items assembled from the current resource registry
- Entry ordering is deterministic and driven by the schematic’s `bundle_entry` relationships, not by registry insertion order.
- Required document entries are explicitly enforced:
  - finalized `Composition`
  - `Patient`
- Supporting and section-entry resources already constructed are included in the candidate bundle scaffold.
- Dev UI shows a richer bundle-finalization output that another engineer can inspect without reading source first.
- Validation and repair remain stubbed after this slice.
- What still remains intentionally stubbed after this slice:
  - `Bundle.identifier`
  - `Bundle.timestamp`
  - `entry.fullUrl`
  - deep reference consistency repair
  - full validation logic
  - repair routing logic
  - arbitrary-IG bundle assembly

## 7. Risks / notes

- The main scope risk is drifting into validation or reference-repair work. This slice should stop at deterministic assembly of a candidate bundle scaffold.
- The main modeling risk is over-claiming completeness. The artifact should keep “candidate” and “scaffold” language explicit.
- The current bundle entry order should come from schematic `bundle_entry` relationships, not from resource-construction registry order. That is the key decision that keeps assembly grounded in the structural artifact rather than execution history.
- Omitting `identifier`, `timestamp`, and `fullUrl` is intentional. Adding placeholder values now would create policy surface that this slice does not need and validation would later have to unwind.

## 8. Targeted `docs/development-plan.md` updates after implementation

- In Section 8, change `Current Focus` from bundle finalization to the first bounded validation foundation using the real candidate bundle scaffold.
- In Section 9, replace `Next Planned Slice` with a bounded Phase 7 entry such as: “Implement the first validation foundation against the real candidate bundle scaffold, without repair routing intelligence.”
- In Section 10, keep `Phase 6: Resource Construction Foundation` as `In Progress` unless the implementation also satisfies its existing exit criterion about writing resource results back into a meaningful bundle-in-progress artifact.
- In Section 10, mark `Phase 6` as `Completed` only if this slice plus the prior construction slice together now clearly prove resource results are being written into a real candidate bundle scaffold.
- In Section 10, move `Phase 7: Validation and Repair Routing Foundation` to `In Progress` only if the follow-on validation slice is approved immediately afterward.
- In Section 12, add or refine the assumption that the first bundle-finalization slice intentionally omits bundle `identifier`, `timestamp`, and `entry.fullUrl` while still producing a real candidate `Bundle` scaffold.
- In Section 13, add one concise risk only if observed during implementation: the initial bundle-finalization artifact may need one additional narrowing/expansion slice before it is sufficient for meaningful validation output beyond placeholder findings.
- In Section 16, update the immediate next objective to point at validating the real candidate bundle scaffold rather than assembling it.
