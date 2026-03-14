# PS-CA Asset Retrieval And Normalization Foundation

## 1. Repo assessment

- The first slice is now in place: Python project packaging, workflow entity discovery, typed workflow artifacts, deterministic placeholder executors, smoke test, and README run instructions are present.
- The current retrieval behavior is still embedded in [executors.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/executors.py): the `specification_asset_retrieval` executor reads `package.json`, `.index.json`, two specific `StructureDefinition` files, and an example bundle directly from disk.
- The current normalized shape is not yet a real specification layer. `ResourceTypeSummary`, `ExampleBundleInventory`, and `SpecificationAssetContextStub` still live in the workflow model file at [models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py), so the workflow owns both orchestration and spec-file inspection concerns.
- The project/package structure has no dedicated specification-knowledge module yet; everything PS-CA-specific is inside the workflow package.
- Test coverage is still one end-to-end smoke test in [test_psca_bundle_builder_workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py). There is no direct coverage for retrieval, normalization, or clear failure behavior.
- The PS-CA package gives enough real source material for a narrow normalization slice: 87 indexed artifacts, 35 `StructureDefinition`s, 16 examples, and clear foundational profiles for `bundle`, `composition`, `patient`, `practitioner`, `practitionerrole`, and `organization`.
- `docs/development-plan.md` already positions this exact slice as the current focus, and `docs/Plans/PLAN001.md` records the prior workflow-skeleton plan. No Phase 3 implementation note exists yet.
- What is missing for this slice is a stable retrieval boundary, first normalized PS-CA asset models, executor integration through that boundary, and tests that prove the boundary rather than just the workflow shell.

## 2. Proposed slice scope

- Summary: move PS-CA file inspection out of the workflow executor into a small deterministic specification module, and replace the current stub retrieval artifact with the first real normalized asset context.
- Keep this slice runtime-only. Do not introduce persisted normalized asset files, a generic ingestion engine, or a background import workflow yet.
- Normalize only what the current workflow can actually carry and inspect: package metadata summary, workflow-scope profile inventory, selected foundational profile summaries, example inventory summary, and one selected example bundle summary.
- Keep `bundle_schematic`, `build_plan`, `resource_construction`, `validation`, and `repair_decision` behavior stubbed. They should only adapt to the new normalized asset fields, not gain new domain intelligence.
- Keep the supported package scope fixed to the bundled PS-CA package and version already in the repo. The code should be shaped for future additional specs, but this slice should not pretend to solve arbitrary-IG support end to end.

## 3. Proposed asset retrieval and normalization approach

- Add a dedicated boundary under a new PS-CA specification module: `PscaAssetRepository`.
- Give that boundary one public entrypoint: `load_foundation_context(query: PscaAssetQuery) -> PscaNormalizedAssetContext`.
- `PscaAssetQuery` should contain only the inputs this slice needs: `package_id`, `version`, `include_example_inventory`, and `selected_example_bundle_filename`.
- `PscaNormalizedAssetContext` should contain:
  - `package_summary`
  - `workflow_profile_inventory`
  - `selected_profiles`
  - `example_inventory`
  - `selected_bundle_example`
  - `normalization_level`
  - `source_refs`
- `package_summary` should include `package_id`, `version`, `fhir_version`, `canonical_url`, `index_entry_count`, `structure_definition_count`, `example_count`, and package root reference.
- `workflow_profile_inventory` should be a list of `PscaWorkflowProfileSummary` records limited to the initial workflow scope: `bundle`, `composition`, `patient`, `practitioner`, `practitioner_role`, and `organization`.
- Each `PscaWorkflowProfileSummary` should expose only stable summary fields needed now: `role`, `profile_id`, `resource_type`, `url`, `title`, `base_definition`, `snapshot_element_count`, `differential_element_count`, `must_support_count`, and `source_filename`.
- `selected_bundle_example` should be a small normalized summary, not raw FHIR JSON. It should include `filename`, `bundle_type`, `entry_resource_types`, and `composition_section_titles`.
- The workflow artifact should be renamed from `SpecificationAssetContextStub` to `SpecificationAssetContext` and should wrap `normalized_assets: PscaNormalizedAssetContext` while keeping the existing inspectability metadata (`stage_id`, `status`, `summary`, `placeholder_note`, `source_refs`).
- The retrieval executor should become a thin adapter: build query from workflow input, call repository, wrap result in `SpecificationAssetContext`, store it in workflow state, and emit it.
- The schematic executor should consume only `normalized_assets.selected_bundle_example` and `normalized_assets.selected_profiles` for the same placeholder behavior it has today. No new schematic rules belong in this slice.
- Failure behavior should be deterministic and explicit. If the requested package/version, selected example bundle, or required foundational profile is missing, the repository should raise a clear error and the workflow should fail at the retrieval stage.

## 4. File-level change plan

- Create [src/fhir_bundle_builder/specifications/__init__.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/specifications/__init__.py) to establish a non-workflow specification layer.
- Create [src/fhir_bundle_builder/specifications/psca/__init__.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/specifications/psca/__init__.py) to make PS-CA a dedicated module boundary.
- Create [src/fhir_bundle_builder/specifications/psca/models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/specifications/psca/models.py) for `PscaAssetQuery`, `PscaPackageSummary`, `PscaWorkflowProfileSummary`, `PscaExampleSummary`, `PscaBundleExampleSummary`, and `PscaNormalizedAssetContext`.
- Create [src/fhir_bundle_builder/specifications/psca/repository.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/specifications/psca/repository.py) for deterministic filesystem-backed loading and normalization of the bundled PS-CA package.
- Update [src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py) to replace `SpecificationAssetContextStub` and the embedded spec-summary types with a workflow artifact that carries `PscaNormalizedAssetContext`.
- Update [src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/executors.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/executors.py) to remove raw JSON-reading helpers from the executor and route retrieval through `PscaAssetRepository`.
- Update [src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/workflow.py) only if renamed artifact types or imports require it.
- Add [tests/test_psca_asset_repository.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_asset_repository.py) for direct repository coverage.
- Update [tests/test_psca_bundle_builder_workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py) so the smoke test asserts the new normalized asset context shape rather than the old stub fields.
- Update [README.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md) only to describe the richer retrieval-stage output in Dev UI; the run flow should stay the same.

## 5. Step-by-step implementation plan

1. Define the PS-CA specification-layer models first so the retrieval boundary and workflow artifact contracts are fixed before wiring code.
2. Implement `PscaAssetRepository` against the bundled package files, with private helpers for package metadata, `.index.json`, foundational profile summaries, example inventory, and selected example bundle summary.
3. Replace the workflow-layer stub asset types with the new normalized context wrapper and update the retrieval executor to use the repository boundary.
4. Update the schematic executor to read the new normalized fields while preserving today’s placeholder behavior and stage order.
5. Add repository-focused tests for the happy path and for clear failure on a missing requested example bundle or required foundational profile.
6. Update the existing workflow smoke test to assert that the retrieval artifact now carries normalized package metadata, scoped profile summaries, and selected example bundle data.
7. Update README wording for Dev UI inspectability and, after implementation succeeds, apply the targeted status/focus changes in `docs/development-plan.md`.

## 6. Definition of Done

- The workflow no longer performs ad hoc PS-CA file inspection inside `specification_asset_retrieval`; that executor uses a dedicated retrieval boundary.
- A typed `PscaNormalizedAssetContext` exists and is the first real workflow-usable PS-CA asset contract in the codebase.
- The retrieval stage output now includes normalized package metadata, workflow-scope profile inventory, selected foundational profile summaries, example inventory, and selected example bundle summary.
- The workflow still runs end to end in the same stage order, and Dev UI inspectability is preserved.
- The schematic stage still behaves as a placeholder, but it consumes the normalized context rather than direct file-derived fields.
- Test coverage now includes direct retrieval/normalization tests plus the updated workflow smoke path.
- What remains intentionally stubbed: terminology normalization, full `StructureDefinition` parsing, dependency extraction, schematic rules, build-plan intelligence, and arbitrary-spec support.

## 7. Risks / notes

- Recommended default: runtime normalization on demand, not persisted asset generation. That is the smallest decision-complete path for this slice.
- Recommended initial profile scope: `bundle`, `composition`, `patient`, `practitioner`, `practitioner_role`, and `organization`. Keep `condition`, `medicationrequest`, and `allergyintolerance` visible only through the example inventory for now.
- The main risk is scope drift into a full ingestion framework. This slice should stop at summary extraction and typed normalization.
- The other meaningful risk is naming churn: replacing `SpecificationAssetContextStub` with a real `SpecificationAssetContext` will touch tests and downstream placeholder executors, but that rename is worth doing now so later slices are not built on a “stub” type name.

## 8. Targeted `docs/development-plan.md` updates after implementation

- In Section 8, change `Current Focus` from proving the initial asset retrieval boundary to using the normalized PS-CA asset context for the first real schematic-generation slice.
- In Section 9, replace `Next Planned Slice` with a narrower Phase 4 entry such as: “Implement the first real PS-CA bundle schematic generation path using the normalized asset context produced by the retrieval boundary.”
- In Section 10, mark `Phase 3: Specification Ingestion and Asset Normalization` as `Completed` only if this slice delivers the retrieval boundary, normalized asset context, and workflow integration described above.
- In Section 10, keep `Phase 4: Bundle Schematic Generation` as the next active phase, and move it to `In Progress` only if the follow-on work is approved immediately after this slice.
- In Section 12, add or refine the assumption that the initial normalized PS-CA asset scope is intentionally limited to package metadata, selected foundational profiles, and example summaries rather than full IG normalization.
- In Section 13, add one concise risk only if observed during implementation: the foundational normalized asset scope may still be too shallow for later schematic logic and may need one additional narrowing/expansion slice before full Phase 4 work.
- In Section 16, update the immediate next objective to point at consuming normalized assets for schematic generation rather than creating the retrieval boundary itself.
