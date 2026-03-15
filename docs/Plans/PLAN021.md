1. Repo assessment

- The repo now has rich normalized provider context in [models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py):
  - `NormalizedBuildRequest.provider_context`
  - provider identity
  - organization list
  - provider-role relationship list
  - `selected_provider_role_relationship`
  - `selected_organization`
  - `normalization_mode`
- That context is created deterministically in [request_normalization_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/request_normalization_builder.py) and is already consumed meaningfully in `resource_construction`.
- The schematic layer currently drops that context completely:
  - [schematic_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/schematic_builder.py) only accepts `PscaNormalizedAssetContext`
  - it builds support-resource placeholders from spec/example evidence only
  - `practitionerrole-1.role` is still hard-coded to `document-author`
  - `organization-1` and `practitionerrole-1` placeholders do not reflect selected provider/org/role context
  - `BundleSchematic.summary`, `placeholder_note`, and `SchematicEvidence` contain no provider-context provenance
- The current schematic artifact shape is narrow:
  - `ResourcePlaceholder` only has `placeholder_id`, `resource_type`, `role`, `profile_url`, `required`, `section_keys`, `required_later_fields`
  - `SchematicEvidence` only records spec/example provenance
  - there is no explicit selected-context metadata field anywhere in `BundleSchematic`
- The workflow stage boundary is the main structural gap:
  - `request_normalization` stores `normalized_request` in workflow state
  - `bundle_schematic` executor currently receives only `SpecificationAssetContext`
  - so provider context is available in the workflow, but not passed into schematic generation
- The current tests confirm that gap:
  - [test_psca_bundle_schematic_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_schematic_builder.py) only exercises spec-driven schematic output
  - [test_psca_build_plan_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_build_plan_builder.py) and several downstream tests call `build_psca_bundle_schematic(...)` without normalized request context
  - [test_psca_bundle_builder_workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py) now verifies rich normalized provider context and richer downstream support resources, but not richer schematic evidence
- What is missing for this slice:
  - explicit schematic evidence about which normalized provider/org/role context was used
  - a schematic summary/assumption signal showing whether the run used legacy fallback vs deterministic selected relationship context
  - a minimal placeholder-level reflection of selected provider-role context
- Constraints that matter now:
  - no new selection intelligence
  - no patient-specific org/role matching
  - no broad placeholder/schema redesign unless it clearly buys inspectability
  - keep downstream behavior stable unless richer schematic evidence directly justifies a change

2. Proposed slice scope

- Make the schematic layer provider-context-aware by consuming `NormalizedBuildRequest` in schematic generation.
- Keep the slice narrow:
  - add explicit selected provider/org/role context evidence to the schematic artifact
  - update schematic summary/notes to reflect the normalization mode used
  - make the `PractitionerRole` placeholder role more specific when a selected provider-role relationship exists
- Do not redesign the schematic into a generic provider graph.
- Do not add new org/role selection heuristics.
- Do not change build-plan ordering or repair architecture.
- Do not move more provider logic into schematic than the repo can already support deterministically.
- Keep these intentionally deferred:
  - patient-scenario-specific org/role selection
  - copying the full provider organization list into schematic planning structures beyond inspectable evidence
  - broader support-resource field planning in schematic
  - any generic provider-context propagation engine

3. Proposed provider-context-aware schematic approach

- Change schematic generation to use both:
  - normalized spec assets
  - normalized request context
- Recommended builder signature:
  - `build_psca_bundle_schematic(normalized_assets, normalized_request)`
- Keep executor graph unchanged:
  - `bundle_schematic` still follows `specification_asset_retrieval`
  - the executor should fetch `normalized_request` from workflow state and pass it into the builder explicitly
- Add one new explicit evidence model in [models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py):
  - `SchematicProviderContextEvidence`
  - recommended fields:
    - `normalization_mode`
    - `provider_id`
    - `provider_display_name`
    - `provider_source_type`
    - `selected_organization_id: str | None`
    - `selected_organization_display_name: str | None`
    - `selected_provider_role_relationship_id: str | None`
    - `selected_provider_role_label: str | None`
- Extend `SchematicEvidence` with:
  - `provider_context: SchematicProviderContextEvidence`
- Populate that evidence by copying from `normalized_request.provider_context`, not by recomputing selection logic in the schematic builder.
- Update schematic summary / placeholder note deterministically based on `normalization_mode`:
  - `legacy_provider_profile`
    - say the schematic used legacy provider-profile fallback and selected support-resource context remains limited
  - `provider_context_single_relationship`
    - say the schematic used the deterministically selected single provider-role relationship
  - `provider_context_explicit_selection`
    - say the schematic used the explicitly selected provider-role relationship and organization context
- Minimal placeholder-context enhancement:
  - keep `Practitioner` and `Organization` placeholder ids/types unchanged
  - keep `organization-1.role` as the generic support role
  - update `practitionerrole-1.role` to:
    - selected role label when `selected_provider_role_relationship` exists
    - otherwise fall back to `document-author`
- Reason for only changing `PractitionerRole` placeholder role:
  - it improves support-resource placeholder inspectability with almost no schema expansion
  - it avoids duplicating Organization data into multiple artifact locations
  - Organization/provider identity details can remain in schematic evidence rather than generic placeholder fields
- Downstream changes:
  - `build_plan_builder.py` should not change behavior
  - `resource_construction_builder.py` should not change behavior
  - validation/repair should not change behavior
  - only tests and Dev UI expectations should expand to show the richer schematic artifact

4. File-level change plan

- Update [models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py)
  - add `SchematicProviderContextEvidence`
  - extend `SchematicEvidence` with provider-context evidence
- Update [schematic_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/schematic_builder.py)
  - accept `NormalizedBuildRequest`
  - populate provider-context evidence
  - make summary/placeholder note mode-aware
  - set `practitionerrole-1.role` from selected role label when available
- Update [executors.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/executors.py)
  - fetch `normalized_request` from state inside `bundle_schematic`
  - pass it into the schematic builder
- Update tests:
  - [test_psca_bundle_schematic_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_schematic_builder.py)
  - [test_psca_build_plan_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_build_plan_builder.py)
  - [test_psca_bundle_builder_workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py)
  - any other tests that call `build_psca_bundle_schematic(...)` directly should be adjusted to pass a normalized request, even if their assertions stay the same
- Update docs:
  - [README.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md)
  - [docs/development-plan.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md)

5. Step-by-step implementation plan

1. Add `SchematicProviderContextEvidence` to the workflow models and attach it to `SchematicEvidence`.
2. Change `build_psca_bundle_schematic(...)` to require `NormalizedBuildRequest`.
3. In the schematic builder, derive one deterministic provider-context evidence object directly from `normalized_request.provider_context`.
4. Update `BundleSchematic.summary` and `placeholder_note` to mention which normalization mode supplied provider context.
5. Update the `practitionerrole-1` placeholder role:
   - selected role label when available
   - `document-author` fallback in legacy/no-selected-role cases
6. Leave `organization-1` and `practitioner-1` placeholder structural shape unchanged.
7. Update the `bundle_schematic` executor to fetch `normalized_request` from workflow state and pass it into the builder.
8. Update direct schematic-builder tests:
   - build a normalized request with explicit selected relationship
   - assert provider-context evidence values
   - assert `practitionerrole-1.role` reflects selected role label
   - add one legacy-mode assertion showing fallback evidence and placeholder role
9. Update build-plan tests only as needed for the new schematic-builder signature; build-plan behavior should remain unchanged.
10. Update workflow smoke test:
   - assert bundle schematic now exposes selected provider/org/role evidence
   - assert the schematic summary or placeholder note reflects explicit selection mode
   - assert `practitionerrole-1` placeholder role reflects the selected role label
11. Update any other direct schematic-builder call sites in downstream tests so they pass a normalized request fixture.
12. Update README and development plan wording after tests are green.

6. Definition of Done

- `BundleSchematic` now records explicit selected provider/org/role context in its evidence.
- That evidence is visible in Dev UI and includes:
  - normalization mode
  - provider identity
  - selected organization, when available
  - selected provider-role relationship id and role label, when available
- `bundle_schematic` summary / placeholder note now states whether the run used:
  - legacy provider-profile fallback
  - deterministic single-relationship selection
  - explicit selected provider-role relationship
- `practitionerrole-1.role` in the schematic reflects the selected role label when a selected provider-role relationship exists.
- Legacy-mode schematic generation still works and still falls back to `document-author`.
- Build-plan behavior is unchanged:
  - same step ids
  - same ordering
  - same dependencies
- Resource construction, validation, and repair behavior are unchanged in this slice.
- Dev UI now visibly shows richer provider-context-aware schematic provenance before resource construction begins.
- What remains deferred:
  - org/role selection heuristics
  - patient-specific org matching
  - broader placeholder schema for provider directory data
  - schematic-driven changes to build planning or resource construction behavior

7. Risks / notes

- The main real risk is duplicating provider-context truth. The schematic should copy selected-context values from `normalized_request.provider_context` directly, not re-derive them.
- A second real risk is overloading `ResourcePlaceholder.role`. Limit the dynamic placeholder-role change to `PractitionerRole`; do not turn placeholder roles into a generic metadata channel.
- A third real risk is widening the executor boundary too far. The clean move is to keep the stage graph unchanged and pass `normalized_request` from workflow state into the schematic builder.
- A fourth real risk is mixing evidence with planning logic. This slice should improve inspectability first; it should not quietly introduce new planning behavior.

8. Targeted `docs/development-plan.md` updates after implementation

- In Section 8, change `Current Focus` away from provider-context-aware schematic generation to the next bounded realism/quality slice.
- In Section 9, keep or refine `Next Planned Slice` to the next real bounded item, likely revisiting non-Composition exact fullUrl ownership unless a more urgent realism slice supersedes it.
- In Section 10, update the Phase 8 note to say the schematic layer now records selected normalized provider/org/role context and exposes that provenance before resource construction begins.
- In Section 12, refine the provider-related assumption to say normalized selected provider/org/role context is now available in both request normalization and schematic evidence, while patient-scenario-specific selection remains deferred.
- In Section 13, replace the old provider-input limitation risk with the next real risk: provider context now exists in both normalized request and schematic evidence, so those two artifacts must stay copy-aligned and not drift.
- In Section 16, update the immediate next objective away from provider-context-aware schematic wiring and toward the next bounded realism or remaining exact-alignment ownership slice.
