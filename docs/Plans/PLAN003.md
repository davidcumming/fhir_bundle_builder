## First Real PS-CA Bundle Schematic Generation

### 1. Repo assessment

- The workflow now has a real specification boundary: [repository.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/specifications/psca/repository.py) returns `PscaNormalizedAssetContext`, and the retrieval stage emits `SpecificationAssetContext`.
- The current schematic stage in [executors.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/executors.py) is still placeholder logic. It only reads `selected_bundle_example.entry_resource_types` and turns them into a flat `placeholder_resources` list.
- The current schematic artifact in [models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py) is too weak for the next phase. `BundleSchematicStub` only has `bundle_type`, `composition_profile_url`, `placeholder_resources`, and notes. It does not distinguish bundle scaffold, Composition scaffold, sections, or relationships.
- The PS-CA spec layer currently exposes enough foundational profile summaries and selected-example summary to start, but it does not yet expose normalized section-definition hints from the Composition profile. That is the main missing input if the schematic stage is not supposed to re-read raw StructureDefinitions.
- The source artifacts already provide concrete deterministic evidence for a narrow first schematic:
  - `Bundle.type` is fixed to `document`
  - `Bundle.entry:composition` and `Bundle.entry:patient` are required
  - `Composition.type` is fixed-pattern `LOINC 60591-5`
  - `Composition.section:sectionMedications`, `sectionAllergies`, and `sectionProblems` are required (`min=1 max=1`)
  - `Bundle1Example.json` shows a coherent narrow example with `Composition`, `Patient`, `PractitionerRole`, `Organization`, `Condition`, `MedicationRequest`, `AllergyIntolerance`, and `Practitioner`
- Test coverage is still narrow: repository foundation tests plus one workflow smoke test. There is no direct test for schematic-generation logic.
- `docs/development-plan.md` already points at this slice as the current focus. `docs/Plans/PLAN001.md` and `docs/Plans/PLAN002.md` capture the prior two slices.
- The constraints that matter now are:
  - keep the schematic deterministic and inspectable
  - do not jump into build-order logic
  - do not jump into population logic
  - keep the section/resource scope intentionally small
  - keep the schematic artifact strong enough for the later build-planning slice

### 2. Proposed slice scope

- Replace `BundleSchematicStub` with the first real `BundleSchematic` artifact.
- Keep the schematic scope intentionally narrow:
  - bundle-level scaffold
  - Composition scaffold
  - required PS-CA sections only: medications, allergies/intolerances, problems
  - foundational resource placeholders needed to make those sections coherent: `Composition`, `Patient`, `PractitionerRole`, `Practitioner`, `Organization`, `MedicationRequest`, `AllergyIntolerance`, `Condition`
- Use explicit deterministic rules plus normalized evidence already available from the retrieval stage. Do not introduce model-driven inference.
- Keep these things intentionally out of scope after this slice:
  - optional sections such as procedures, immunizations, vitals, results, etc.
  - multiple resource placeholders per section
  - real build ordering
  - real resource content
  - deep reference resolution beyond schematic relationships
  - arbitrary-IG schematic generation

### 3. Proposed schematic-generation approach

- Add a dedicated deterministic schematic builder, for example `build_psca_bundle_schematic(normalized_assets) -> BundleSchematic`, so the executor stays thin.
- Extend the normalized PS-CA asset context minimally so the schematic builder does not need to inspect raw files:
  - add normalized `Composition` section-definition summaries for the required sections
  - enrich the selected example bundle summary with per-section entry resource-type evidence, not just section titles
- Recommended normalized additions in the PS-CA spec layer:
  - `PscaCompositionSectionDefinitionSummary`
    - `section_key`
    - `slice_name`
    - `title`
    - `loinc_code`
    - `required`
    - `allowed_entry_resource_types`
    - `source_profile_id`
  - `PscaBundleExampleSectionSummary`
    - `title`
    - `entry_resource_types`
- Drive the schematic from this narrow rule set:
  - Bundle rules from `bundle-ca-ps`:
    - `bundle_type=document`
    - include required bundle entry placeholders for `Composition` and `Patient`
  - Composition rules from `composition-ca-ps`:
    - use `Composition` profile URL from normalized assets
    - set expected Composition type code to `LOINC 60591-5`
    - create required sections for medications, allergies, problems from normalized section summaries
    - create subject relationship from Composition to Patient
  - Example evidence from selected bundle example:
    - choose `MedicationRequest` as the initial medication-section placeholder type
    - choose `AllergyIntolerance` for allergies
    - choose `Condition` for problems
    - use `PractitionerRole -> Practitioner + Organization` as the initial author-support pattern
- Recommended `BundleSchematic` artifact structure:
  - `bundle_scaffold`
    - bundle profile URL
    - fixed `bundle_type`
    - required-but-unpopulated fields such as identifier and timestamp
  - `composition_scaffold`
    - composition placeholder id
    - composition profile URL
    - expected type code `60591-5`
    - required-but-unpopulated fields such as status/title/date
  - `section_scaffolds`
    - one record each for medications, allergies, problems
    - include title, code, required flag, allowed resource types, and referenced placeholder ids
  - `resource_placeholders`
    - explicit placeholder records with logical ids, resource type, profile URL, role, and section membership where applicable
  - `relationships`
    - bundle-entry membership
    - composition.subject -> patient
    - composition.author -> practitioner role
    - practitioner role -> practitioner
    - practitioner role -> organization
    - composition.section[x].entry -> section resource placeholder
  - `evidence`
    - selected example filename
    - profile ids used
    - section slice names used
    - source refs already carried through the workflow
  - `omitted_optional_sections`
    - explicit list of optional PS-CA sections intentionally left out of this slice
- Keep naming honest:
  - use `scaffold`, `placeholder`, `expected`, or `required_later` for values not yet populated
  - do not emit partial FHIR resources and pretend they are final resources
- Keep the downstream build-planning boundary simple:
  - the schematic must still expose a flat list of resource placeholders plus explicit relationships so the next slice can derive build steps from it without redesign

### 4. File-level change plan

- Update [src/fhir_bundle_builder/specifications/psca/models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/specifications/psca/models.py)
  - add minimal section-definition and selected-example-section summary types
  - extend `PscaNormalizedAssetContext` with section-level hints needed by schematic generation
- Update [src/fhir_bundle_builder/specifications/psca/repository.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/specifications/psca/repository.py)
  - extract required section summaries from `composition-ca-ps`
  - enrich selected example bundle summary with per-section resource-type evidence
- Update [src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py)
  - replace `BundleSchematicStub` and the flat `ResourcePlaceholder` shape with real schematic models:
    - bundle scaffold
    - Composition scaffold
    - section scaffold
    - resource placeholder
    - relationship/evidence records
  - keep the final workflow output pointing at the new `BundleSchematic`
- Create [src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/schematic_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/schematic_builder.py)
  - deterministic PS-CA schematic-generation logic
- Update [src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/executors.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/executors.py)
  - make `bundle_schematic` call the builder
  - adapt `build_plan` to consume the new schematic artifact’s resource placeholders without adding new planning intelligence
- Update [tests/test_psca_asset_repository.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_asset_repository.py)
  - assert the new section-definition and example-section summary fields
- Add [tests/test_psca_bundle_schematic_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_schematic_builder.py)
  - direct deterministic coverage for the schematic builder
- Update [tests/test_psca_bundle_builder_workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py)
  - assert the real schematic artifact shape and the required placeholders/relationships
- Update [README.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md)
  - describe the richer schematic-stage output visible in Dev UI

### 5. Step-by-step implementation plan

1. Extend the PS-CA normalized asset models with only the section-level and example-section evidence needed for deterministic schematic generation.
2. Update `PscaAssetRepository` to populate those new fields from:
   - `structuredefinition-profile-composition-ca-ps.json`
   - the selected example bundle
3. Replace the workflow’s schematic stub models with a real structured `BundleSchematic` artifact and related submodels.
4. Implement a deterministic schematic builder that:
   - reads only normalized assets
   - creates the narrow scaffold described above
   - records omitted optional sections and evidence/provenance
5. Integrate that builder into the `bundle_schematic` executor and keep the executor itself as a thin adapter.
6. Update the placeholder build-plan executor just enough to read the new schematic resource placeholders as its input source; do not add build-order intelligence.
7. Add direct builder tests for:
   - required bundle and patient placeholders
   - required medications/allergies/problems sections
   - expected section-to-resource placeholder mapping
   - expected composition subject/author/supporting relationships
   - omitted optional sections remaining omitted
8. Update the workflow smoke test to assert the new real schematic artifact and ensure the workflow still runs end to end with the same executor sequence.
9. Update README wording and, after successful implementation, apply the targeted `docs/development-plan.md` updates.

### 6. Definition of Done

- The `bundle_schematic` stage no longer emits a generic placeholder list; it emits a real structured schematic artifact.
- The schematic artifact clearly distinguishes:
  - bundle-level scaffold
  - Composition scaffold
  - section scaffolds
  - resource placeholders
  - relationships/references
  - evidence/provenance
- The schematic uses normalized PS-CA assets as its input boundary, not ad hoc raw-file inspection in the executor.
- The schematic includes, at minimum:
  - `Bundle` scaffold with `document` type and required entry expectations
  - `Composition` scaffold with expected patient-summary type code
  - required section scaffolds for medications, allergies, and problems
  - placeholders for `Composition`, `Patient`, `PractitionerRole`, `Practitioner`, `Organization`, `MedicationRequest`, `AllergyIntolerance`, and `Condition`
  - explicit relationships linking Composition subject/author and section entries
- Dev UI shows a visibly richer schematic-stage output that another engineer can inspect without reading the source code first.
- The build-plan stage still remains stubbed, but it now receives a real schematic artifact as input.
- Test coverage includes repository, schematic builder, and end-to-end workflow checks.
- What remains stubbed after this slice:
  - build ordering
  - population of any FHIR resource content
  - optional sections beyond the three required ones
  - generalized schematic generation for arbitrary specs

### 7. Risks / notes

- The current normalized asset context is slightly too shallow for this slice as-is; the smallest acceptable extension is section-definition summaries plus richer selected-example section evidence.
- Choosing `MedicationRequest` rather than `MedicationStatement` for the medication section is an evidence-based narrow default from `Bundle1Example.json`, not a claim that all later PS-CA medication schematics should be limited to that type.
- The author support pattern `PractitionerRole -> Practitioner + Organization` is also an intentionally narrow default based on available normalized profiles and example evidence.
- The main scope risk is trying to include optional sections now because they are visible in the Composition differential. The slice should stop at the three required sections plus the minimal supporting author/subject placeholders.
- A secondary risk is making the schematic models too close to final FHIR resources. The artifact should remain a scaffold for later planning, not partial generated bundle content.

### 8. Targeted `docs/development-plan.md` updates after implementation

- In Section 8, change `Current Focus` from schematic generation to deriving the first real build-planning slice from the schematic artifact.
- In Section 9, replace `Next Planned Slice` with a bounded Phase 5 entry such as: “Implement the first PS-CA build-plan slice using the real bundle schematic artifact, without resource-population logic.”
- In Section 10, mark `Phase 4: Bundle Schematic Generation` as `Completed` only if the workflow emits the structured schematic artifact described above and Dev UI inspection is clear.
- In Section 10, keep `Phase 5: Build Planning` as the next active phase and move it to `In Progress` only if that follow-on slice is immediately approved.
- In Section 12, add or refine the assumption that the first real PS-CA schematic intentionally covers only required sections plus minimal subject/author support placeholders.
- In Section 13, add one concise risk only if it is observed during implementation: the initial schematic may still need one follow-up expansion slice before it covers enough optional PS-CA sections for broader scenarios.
- In Section 16, update the immediate next objective to point at deriving a structured build plan from the schematic artifact rather than building the schematic itself.
