## Provider Authoring Foundation

### 1. Repo assessment

- What exists now:
  - the repo has a clean downstream `provider_context` boundary in [`models.py`](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py)
  - `ProviderContextInput` currently supports only:
    - `provider`
    - `organizations`
    - `provider_role_relationships`
    - optional `selected_provider_role_relationship_id`
  - `request_normalization_builder.py` already defines the exact downstream behavior the authoring slice must feed:
    - no `provider_context` -> `legacy_provider_profile`
    - one relationship -> deterministic single-relationship selection
    - multiple relationships -> requires explicit selected relationship id
    - selected relationship must reference a known organization
- What provider-side capabilities already exist in the workflow:
  - deterministic consumption of provider id/display name
  - deterministic Organization enrichment only when a selected provider-role relationship resolves to a selected organization
  - deterministic PractitionerRole identifier and role-label enrichment only when a selected relationship exists
  - fallback to thinner support-resource behavior when richer provider context is absent
  - explicit provider-context alignment validation and provenance already exist downstream
- What is missing for upstream provider authoring:
  - no provider authoring models
  - no natural-language-to-provider-record boundary
  - no authored-record-to-`ProviderContextInput` mapper
  - no upstream provider authoring package yet, beyond the new patient authoring pattern to mirror
- Constraints that matter now:
  - the bundle-builder workflow must remain deterministic and downstream-only
  - no UI tabs
  - no internet-backed provider research
  - no live model integration in this slice
  - no generic provider directory platform
  - current workflow gets real provider-side value only when it receives both:
    - a selected relationship
    - an organization linked by that relationship
  - per your decision, this first slice must **not synthesize organizations or provider-role relationships** when the prompt only supplies role/location; those must become explicit authored facts plus unresolved gaps

### 2. Proposed provider authoring foundation scope

- Add a bounded provider authoring foundation that produces:
  - `ProviderAuthoringInput`
  - `ProviderAuthoredRecord`
  - `ProviderAuthoringMapResult`
  - a deterministic/demo provider authoring builder
  - a deterministic mapper into current `ProviderContextInput`
- Exact bounded outputs for this slice:
  - provider identity:
    - deterministic `provider_id`
    - authored `display_name`
  - authored provider facts:
    - optional administrative gender
    - optional specialty / role label
    - optional jurisdiction / location text
  - authored organizations:
    - bounded list of 0 or 1 authored organizations in this first slice
  - authored provider-role relationships:
    - bounded list of 0 or 1 authored relationships in this first slice
    - optional explicit selected relationship id
  - inspectability:
    - source/provenance per authored field/group
    - unresolved authoring gaps
    - unmapped-to-workflow field list
- How selected organization / role should be represented in this first slice:
  - `ProviderAuthoredRecord` should support:
    - `organizations: list[ProviderAuthoredOrganization]`
    - `provider_role_relationships: list[ProviderAuthoredRoleRelationship]`
    - `selected_provider_role_relationship_id: str | None`
  - first-slice builder should emit at most:
    - one organization
    - one relationship
    - one selected relationship id
  - if the prompt does not explicitly support an organization and linked relationship, the builder must emit:
    - `organizations = []`
    - `provider_role_relationships = []`
    - `selected_provider_role_relationship_id = None`
    - unresolved gaps for missing organization / relationship
- What should remain deferred:
  - provider search/research
  - multiple-organization authoring flows
  - sophisticated organization disambiguation
  - specialty normalization to controlled vocabularies
  - location normalization beyond simple text capture
  - UI/provider module UX
  - live model-backed authoring
  - persistence/database design

### 3. Proposed authoring architecture

- Where the authoring models/builders should live:
  - extend the existing upstream package at `/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/authoring/`
  - mirror the patient authoring pattern with provider-specific files
- Recommended module split:
  - `authoring/provider_models.py`
    - provider authoring contracts and evidence/map-result types
  - `authoring/provider_builder.py`
    - deterministic/demo natural-language transformer
  - `authoring/provider_mapper.py`
    - deterministic authored-record -> `ProviderContextInput` mapper
- How authored provider records should be structured:
  - `ProviderAuthoredRecord.provider`
    - `provider_id`
    - `display_name`
  - `ProviderAuthoredRecord.professional_facts`
    - optional `administrative_gender`
    - optional `specialty_or_role_label`
    - optional `jurisdiction_text`
  - `ProviderAuthoredRecord.organizations`
    - authored `organization_id`
    - `display_name`
    - `source_mode`
    - `source_note`
  - `ProviderAuthoredRecord.provider_role_relationships`
    - authored `relationship_id`
    - `organization_id`
    - `role_label`
    - `source_mode`
    - `source_note`
  - `ProviderAuthoredRecord.selected_provider_role_relationship_id`
  - `ProviderAuthoredRecord.unresolved_authoring_gaps`
    - explicit gaps such as missing organization, missing role relationship, missing named provider
  - `ProviderAuthoredRecord.authoring_evidence`
    - source prompt text
    - builder mode
    - extracted name
    - extracted gender
    - extracted role/specialty
    - extracted jurisdiction text
    - extracted organization name
    - applied scenario tags
- How they should map into current `provider_context`:
  - `provider.provider_id` -> `ProviderIdentityInput.provider_id`
  - `provider.display_name` -> `ProviderIdentityInput.display_name`
  - authored `organizations` -> `ProviderOrganizationInput[]`
  - authored `provider_role_relationships` -> `ProviderRoleRelationshipInput[]`
  - authored `selected_provider_role_relationship_id` -> `ProviderContextInput.selected_provider_role_relationship_id`
  - authored administrative gender, specialty text, and jurisdiction text do **not** map directly today and must be reported as unmapped unless they were used to support an explicit authored relationship label
- Transformation mode for this slice:
  - deterministic/demo hybrid, offline only
  - builder behavior should be:
    - deterministic extraction of:
      - provider name when present
      - gender when present
      - role/specialty text when present
      - jurisdiction/location text when present
      - organization name only when explicitly present
    - bounded authored display-name fallback when no human name is present:
      - use an honest generic label such as `"Authored Provider"` or `"Authored <Role>"`, with explicit scenario-template provenance
    - create authored organization/relationship only when explicitly supported by prompt text
    - never invent a provider directory or synthetic employer
- Inspectability/provenance to require:
  - builder mode explicit, e.g. `demo_template_authoring`
  - authored provider display name must record whether it was:
    - directly extracted
    - scenario-template fallback
  - organization and relationship items must record direct extraction vs scenario template
  - mapping result must explicitly list unmapped authored facts
  - compatibility with current workflow must be proven in tests
- Default assumptions chosen:
  - no second Agent Framework workflow in this slice
  - authored provider records may be slightly richer than current `provider_context`
  - first builder output is intentionally bounded to zero-or-one organization and zero-or-one relationship
  - no synthetic organization fallback in this slice

### 4. File-level change plan

- Create `/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/authoring/provider_models.py`
  - `ProviderAuthoringInput`, `ProviderAuthoredRecord`, authored provider/org/relationship types, evidence/gap/map-result models
- Create `/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/authoring/provider_builder.py`
  - deterministic/demo natural-language-to-authored-provider-record builder
- Create `/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/authoring/provider_mapper.py`
  - authored provider record -> `ProviderContextInput` mapper
- Update `/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/authoring/__init__.py`
  - export the provider authoring surface alongside patient authoring
- Add `/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_provider_authoring_builder.py`
  - fact extraction, authored-record validity, bounded organization/relationship behavior, unresolved-gap behavior
- Add `/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_provider_authoring_mapper.py`
  - mapping into `ProviderContextInput`, unmapped field reporting, selected-relationship behavior
- Update `/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_request_normalization_builder.py`
  - prove mapped authored provider records normalize cleanly through existing provider normalization
- Update `/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py`
  - add one compatibility smoke test showing an authored-record-derived `provider_context` can drive the existing workflow
- Update `/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md`
  - describe the bounded upstream provider authoring foundation and its offline/demo constraints
- Update `/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md`
  - move focus from patient authoring to provider authoring

### 5. Step-by-step implementation plan

1. Add provider authoring contracts to the `authoring` package.
2. Define authored provider identity, professional facts, organization, relationship, gap, evidence, and map-result models.
3. Implement deterministic provider id generation.
   - recommended default: slugified authored display label plus stable suffix from prompt text
4. Implement deterministic authored display-name behavior.
   - if prompt names a provider, use extracted name
   - otherwise use bounded generic label with explicit provenance, e.g. `"Authored Oncologist"` or `"Authored Provider"`
5. Implement the demo provider authoring builder.
   - parse prompt for:
     - provider name
     - gender
     - role/specialty
     - jurisdiction/location text
     - organization name only when explicitly present
   - add a small bounded scenario-tag layer for common phrases like `oncologist`, `family doctor`, `surgeon`
   - create 0 or 1 authored organization only when organization text is explicit
   - create 0 or 1 authored provider-role relationship only when both:
     - an organization is explicit
     - a role label is explicit or extractable
   - otherwise emit unresolved gaps for the missing organization / relationship
6. Implement the provider authored-record mapper into `ProviderContextInput`.
   - map only current workflow-supported fields
   - populate `selected_provider_role_relationship_id` only when a relationship exists
   - emit unmapped fields for authored gender, jurisdiction, and specialty facts that do not currently map directly
7. Add direct builder tests covering:
   - extracted named provider with explicit org + role produces one organization, one relationship, and a selected relationship id
   - role/location-only prompt like `"The provider is a female oncologist in BC."` produces:
     - provider identity
     - authored professional facts
     - no organization
     - no relationship
     - explicit unresolved gaps
   - deterministic ids and display labels
   - provenance labels for extracted vs fallback values
8. Add direct mapper tests covering:
   - fully authored provider record maps into `ProviderContextInput` with organization list, relationship list, and selected relationship id
   - role/location-only authored record maps honestly into a thinner provider context with unmapped authored facts recorded
9. Update request-normalization tests covering:
   - mapped authored provider record with one organization + one relationship normalizes to `provider_context_single_relationship` or `provider_context_explicit_selection` as appropriate
   - authored provider record with no relationship normalizes cleanly into the thin provider path
10. Add one workflow smoke test using authored provider context.
   - recommended scenario: named provider + explicit organization + explicit role, so the workflow proves full provider-context-driven enrichment still works when fed from authoring
11. Update README and development plan after tests are green.

### 6. Definition of Done

- It is now possible to take a bounded natural-language provider prompt and produce a structured `ProviderAuthoredRecord`.
- That authored record is inspectable and includes:
  - deterministic provider id
  - authored display name
  - professional facts
  - authored organizations when explicitly supported
  - authored provider-role relationships when explicitly supported
  - unresolved authoring gaps
  - authoring evidence/provenance
- It is now possible to map that authored record into the current `ProviderContextInput` without changing the bundle-builder workflow.
- Existing request normalization accepts the mapped provider context and preserves current downstream behavior.
- What should now be possible for workflow testing:
  - author a provider from bounded natural language
  - convert that authored record into current workflow input
  - run the deterministic workflow using authored provider input
  - exercise both:
    - thin provider mode when org/relationship are absent
    - richer selected-relationship mode when org/relationship are explicitly authored
- What should still remain out of scope:
  - provider UI tabs
  - provider research/search integration
  - synthetic directory/employer generation
  - multiple-organization authoring flows
  - live model-backed authoring
  - persistence/database work
  - generic provider platform design

### 7. Risks / notes

- The main real risk is accidental provider-directory invention. This slice must not synthesize organizations or relationships when they are not explicitly supported by the prompt.
- A second real risk is creating authored provider facts that look richer than what the workflow can consume. Specialty, jurisdiction, and gender must be preserved as authored facts but explicitly reported as unmapped when appropriate.
- A third real risk is forcing too much symmetry with patient authoring. Provider authoring should mirror the package pattern and inspectability approach, but not import patient-style complexity logic where it is not useful.
- A fourth real risk is misleading fallback display names. If the prompt does not provide a human name, any generic authored display label must be clearly provenance-tagged as a bounded fallback, not an extracted real-world identity.
- A fifth real risk is overvaluing organization-only authoring. In the current workflow, organization enrichment depends on a selected relationship, so tests and docs should make that dependency explicit.

### 8. Targeted `docs/development-plan.md` updates after implementation

- Section 8 `Current Focus`
  - change to: implement the first bounded provider authoring foundation that produces structured authored provider records and a clean mapping into the existing `provider_context` path
- Section 9 `Next Planned Slice`
  - change to: after provider authoring foundation, decide whether to add a bounded live authoring/runtime integration step or begin a thin UI-facing authoring flow around the new patient/provider authoring modules
- Section 10 Phase 8 note
  - append that the repo now includes a bounded upstream provider authoring foundation separate from deterministic bundle generation, mirroring the patient authoring boundary where appropriate
- Section 12 `Known Early Assumptions`
  - add that the first provider authoring slice uses a bounded offline/demo transformer rather than live model-backed authoring
  - add that authored provider facts may be preserved even when they do not yet map into current deterministic `provider_context`
  - add that the first provider authoring builder does not synthesize organizations or provider-role relationships when they are not explicit in the prompt
- Section 13 `Known Early Risks`
  - add that upstream provider authoring may drift into synthetic provider-directory behavior unless organization/relationship generation remains explicitly bounded
  - add that current workflow value from authored provider context is highest when prompts explicitly support a linked organization and role relationship
- Section 16 `Immediate Next Objective`
  - update to: complete the provider authoring foundation and prove authored-record compatibility with the current bundle-builder workflow before considering live provider authoring/runtime integration or UI-level provider flows
