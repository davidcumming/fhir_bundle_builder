1. Repo assessment

- The current Dev UI wrapper flow already exposes the right core artifacts:
  - authored patient record
  - authored provider record
  - patient/provider refinement results
  - authored-input preparation with mapping results and compact workflow-input summary
  - final nested `WorkflowSkeletonRunResult`
- The current wrapper workflow stages are:
  - `patient_authoring`
  - `provider_authoring`
  - `authored_record_refinement`
  - `authored_bundle_preparation`
  - `bundle_builder_run`
- What the current demo flow already shows well:
  - full typed artifacts remain visible
  - original versus refined authored records are preserved
  - final run summary already exposes validation status, candidate bundle size, and whether a selected provider-role relationship exists
- What is still hard to interpret quickly:
  - stage `summary` and `placeholder_note` text is generic and does not reflect run-specific outcomes
  - there is no compact authored-record overview for quick scanning of counts, gaps, or edited-field presence
  - the refinement stage exposes the full refinement result, but not a small delta-oriented summary
  - the preparation stage exposes mapping results and a workflow-input summary, but not an at-a-glance mapped-vs-unmapped overview
  - the final summary is still too thin to quickly answer “rich vs thin provider path” and “what happened upstream”
- Constraints that matter now:
  - preserve the full underlying artifacts
  - do not change authoring, refinement, orchestration, or workflow semantics
  - keep this inside the existing Dev UI wrapper flow
  - summary models must remain derived/read-only and not become alternate sources of truth

2. Proposed thin demo-UX polish scope

- Add a small set of compact typed summary models to make the existing demo flow easier to scan in Dev UI.
- Refine stage `summary` and `placeholder_note` strings so they reflect actual run outcomes, not only static slice framing.
- Exact compact summaries to add:
  - authored patient overview
  - authored provider overview
  - refinement delta overview
  - preparation/mapping overview
  - richer final run overview
- Usability questions this slice should answer at a glance:
  - what was authored for the patient and provider
  - whether review/edit changed anything, and how much
  - whether provider context is rich or thin
  - what mapped into workflow input versus what stayed unmapped
  - whether the final run passed validation and how large the candidate bundle is
- What should remain deferred:
  - layout redesign
  - graph/visualization work
  - new workflow stages
  - new domain/business rules
  - replacing full artifacts with summaries only

3. Proposed summary/refinement architecture

- Keep the summary layer in the existing wrapper workflow package under `src/fhir_bundle_builder/workflows/psca_authored_bundle_demo_workflow/`.
- Add summary models in `models.py` rather than a separate subsystem, because this is wrapper-workflow presentation polish, not a new domain layer.
- Add these compact summary types:
  - `AuthoredPatientRecordOverview`
    - patient display name
    - condition/medication/allergy counts
    - unresolved gap count
    - whether residence/smoking facts are present
  - `AuthoredProviderRecordOverview`
    - provider display name
    - organization count
    - relationship count
    - provider path mode: `rich` or `thin`
    - unresolved gap count
  - `AuthoredRecordRefinementOverview`
    - patient edits applied flag
    - provider edits applied flag
    - patient edited field count
    - provider edited field count
    - patient/provider refined-record ids
  - `AuthoredBundlePreparationOverview`
    - mapped patient counts
    - mapped provider counts
    - patient unmapped field count
    - provider unmapped field count
    - provider path mode: `rich` or `thin`
    - selected-relationship flag
  - refine `AuthoredBundleDemoFinalSummary`
    - keep current fields
    - add provider path mode
    - add patient/provider unmapped field counts
    - add patient/provider edits-applied flags
- Which stages should expose which summaries:
  - `patient_authoring`
    - patient authored-record overview
  - `provider_authoring`
    - provider authored-record overview, including explicit rich/thin indicator
  - `authored_record_refinement`
    - refinement overview plus updated authored patient/provider overviews
  - `authored_bundle_preparation`
    - preparation overview plus existing full preparation artifact
  - `bundle_builder_run`
    - richer final summary plus full workflow output
- How rich/thin provider path should be surfaced:
  - derive it from the effective authored provider record and/or mapped provider context
  - recommend exact rule:
    - `rich` when at least one organization and one provider-role relationship exist
    - `thin` otherwise
- How mapped/unmapped facts should be surfaced:
  - keep full `patient_mapping.unmapped_fields` and `provider_mapping.unmapped_fields`
  - add counts and short summary text in the preparation overview and stage summary
  - do not collapse unmapped field names into opaque prose only
- How real artifacts remain visible:
  - summary models are additional fields on the stage and final result, not replacements
  - keep existing `patient_record`, `provider_record`, `patient_refinement`, `provider_refinement`, `preparation`, and `workflow_output` untouched

4. File-level change plan

- Update `/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_authored_bundle_demo_workflow/models.py`
  - add the compact summary models
  - add optional summary fields to `AuthoredBundleDemoStageResult`
  - enrich `AuthoredBundleDemoFinalSummary`
- Update `/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_authored_bundle_demo_workflow/executors.py`
  - compute the compact summaries
  - refine stage `summary` and `placeholder_note` text to reflect actual outcomes
- Update `/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_authored_bundle_demo_workflow.py`
  - assert the new summaries exist and reflect rich/thin, mapped/unmapped, and edited/not-edited status
- Update `/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md`
  - describe the improved scanability of the Dev UI demo flow
- Update `/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md`
  - move current focus from refinement capability to demo-UX/stage-summary polish

5. Step-by-step implementation plan

1. Add compact summary models to the wrapper workflow models.
2. Add small pure helper functions in `executors.py` for:
   - provider path mode derivation
   - authored patient overview construction
   - authored provider overview construction
   - refinement overview construction
   - preparation overview construction
3. Expand `AuthoredBundleDemoStageResult` to carry:
   - patient overview
   - provider overview
   - refinement overview
   - preparation overview
4. Refine `patient_authoring` stage output.
   - summary should mention patient name and authored clinical counts
   - placeholder note should remain bounded but more concrete
5. Refine `provider_authoring` stage output.
   - summary should mention provider display label and whether the path is currently rich or thin
   - placeholder note should explicitly mention when org/relationship are absent
6. Refine `authored_record_refinement` stage output.
   - summary should say whether edits were applied and how many fields changed
   - include updated authored overviews plus refinement overview
7. Refine `authored_bundle_preparation` stage output.
   - summary should mention mapped counts, unmapped counts, and rich/thin provider path
   - include preparation overview alongside the existing full preparation artifact
8. Enrich the final summary in `bundle_builder_run`.
   - keep validation and bundle-entry count
   - add provider path mode
   - add mapped/unmapped visibility via counts
   - add edit-applied flags
9. Update the wrapper-flow smoke tests.
   - rich path should assert:
     - provider path mode is `rich`
     - patient/provider summaries are populated
     - refinement overview reports edits
     - preparation overview reports mapped counts and zero-or-low unmapped visibility as expected
   - thin-provider path should assert:
     - provider path mode is `thin`
     - unmapped field counts are surfaced
     - final summary preserves thin-path status
10. Update README and development plan after tests are green.

6. Definition of Done

- The existing Dev UI wrapper flow remains the same flow and the same stage sequence.
- Each wrapper stage now has clearer run-specific `summary` text and more useful `placeholder_note` text.
- The wrapper flow exposes compact typed summaries that make it easier to scan:
  - what was authored
  - what changed during refinement
  - what mapped versus remained unmapped
  - whether provider context is rich or thin
  - whether the final run passed and how large the bundle is
- Full underlying artifacts remain visible and unchanged in role.
- The demo flow becomes easier to explain live without opening every nested artifact manually.
- Tests prove the summary layer is present and meaningful for both:
  - rich provider-context path
  - thin provider-context path
- Still out of scope:
  - UI redesign
  - new authoring semantics
  - new orchestration behavior
  - new workflow stages
  - separate frontend stack

7. Risks / notes

- The main risk is turning summaries into an alternate source of truth. Keep them strictly derived from existing artifacts.
- A second risk is overdoing string-heavy presentation logic. Prefer compact typed summaries plus short stage text.
- A third risk is duplicating business rules in summary helpers. Rich/thin and mapped/unmapped indicators should derive from existing authored/preparation artifacts, not new semantic branches.
- A fourth risk is hiding important detail behind oversimplified summaries. Full nested artifacts must remain present and easy to inspect.

8. Targeted `docs/development-plan.md` updates after implementation

- Section 8 `Current Focus`
  - change to: implement a thin demo-UX polish / stage-summary refinement pass for the Dev UI authored-input wrapper flow so the existing end-to-end path is easier to understand at a glance
- Section 9 `Next Planned Slice`
  - change to: after demo-UX/stage-summary refinement, decide whether to add one more narrow Dev UI usability pass or return to a workflow-quality/documentation-focused slice
- Section 10 Phase 8 note
  - append that the Dev UI authored-input demo flow now includes compact derived summaries for authoring, refinement, preparation, and final run interpretation without changing the underlying workflow artifacts
- Section 12 `Known Early Assumptions`
  - add that demo-UX polish should add compact derived summaries around existing artifacts rather than replacing those artifacts
  - add that rich/thin provider-path visibility in the wrapper flow should be derived from existing authored/preparation artifacts, not new provider business logic
- Section 13 `Known Early Risks`
  - add that summary-oriented polish may become an alternate presentation-layer source of truth unless summary models remain strictly derived from existing typed artifacts
  - add that overcompressing mapped/unmapped or refinement detail could make the demo easier to scan but less trustworthy
- Section 16 `Immediate Next Objective`
  - update to: complete the thin demo-UX polish / stage-summary refinement pass and prove the authored-input demo flow is easier to interpret quickly while keeping the full underlying artifacts visible
