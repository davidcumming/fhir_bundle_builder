## Thin Authored-Record Review/Edit Refinement

### 1. Repo assessment

- The repo already has the full authored-input pipeline:
  - patient and provider authored-record builders in the upstream `authoring` package
  - deterministic authored-record-to-context mappers
  - a thin authored-input orchestration helper that prepares `WorkflowBuildInput`
  - a Dev UI wrapper workflow that authors patient/provider records and then runs the unchanged deterministic bundle-builder workflow
- The current demo flow can already:
  - accept `PatientAuthoringInput`
  - accept `ProviderAuthoringInput`
  - build `PatientAuthoredRecord` and `ProviderAuthoredRecord`
  - prepare workflow input
  - run the existing workflow end to end
- What is missing for usable review/edit:
  - no structured edit contract for authored patient/provider records
  - no explicit refinement step between authoring and orchestration
  - no preserved view of original-authored versus edited-authored records
  - no edit provenance/result object showing what changed before preparation
- Constraints that matter now:
  - edits must apply to authored records, not mapped `patient_context` / `provider_context`
  - orchestration and the core workflow should remain unchanged
  - the Dev UI wrapper stays the only UI host in this slice
  - this must not become CRUD, persistence, or arbitrary JSON editing

### 2. Proposed thin review/edit scope

- Add one bounded structured review/edit step inside the existing Dev UI wrapper flow.
- Editable patient fields in this slice:
  - `patient.display_name`
  - `patient.administrative_gender`
  - `patient.age_years`
  - `patient.birth_date`
  - `background_facts.residence_text`
  - `background_facts.smoking_status_text`
  - full replacement of authored `conditions` as a bounded list of display texts
  - full replacement of authored `medications` as a bounded list of display texts
  - full replacement of authored `allergies` as a bounded list of display texts
- Editable provider fields in this slice:
  - `provider.display_name`
  - `professional_facts.administrative_gender`
  - `professional_facts.specialty_or_role_label`
  - `professional_facts.jurisdiction_text`
  - optional singular authored organization display name
  - optional singular authored provider-role label
  - optional selected-relationship presence/value for the first-slice zero-or-one relationship shape
- Not editable in this slice:
  - `record_id`
  - `patient_id`
  - `provider_id`
  - authoring evidence payloads
  - mapped contexts
  - workflow input or workflow internals
  - free-form JSON/opaque patching
- Review/edit behavior to support:
  - author record
  - inspect authored record
  - optionally apply bounded structured edits
  - inspect original versus effective edited record
  - continue into unchanged preparation and workflow run using the effective edited record
- Deferred:
  - persistence/record libraries
  - reusable CRUD/editor framework
  - conversational revision loops
  - internet-backed refinement
  - broad multi-record management

### 3. Proposed edit/refinement architecture

- Put the refinement contracts and helpers in the upstream `authoring` package, because refinement is still an authored-record concern.
- Add a small refinement module pair:
  - `authored_record_refinement_models.py`
  - `authored_record_refinement.py`
- Use bounded patch models, not full-record replacement and not generic patch syntax.
  - `PatientAuthoredRecordReviewEditInput`
  - `ProviderAuthoredRecordReviewEditInput`
- Patient list editing should use bounded full-list replacement, not per-item operation DSL.
  - Input stays simple and UI-friendly.
  - The helper rebuilds edited item lists deterministically from the supplied display texts.
- Provider editing should stay narrower than patient editing.
  - Because the first provider authoring slice is already bounded to zero-or-one organization and zero-or-one relationship, the review edit model should expose singular optional organization/relationship edits rather than a generic list editor.
- Add deterministic refinement helpers:
  - `apply_patient_authored_record_review_edits(...)`
  - `apply_provider_authored_record_review_edits(...)`
- Refinement helper behavior:
  - return the original record unchanged when no edits are provided
  - produce a refined authored record when edits are present
  - preserve business identity fields (`patient_id`, `provider_id`)
  - generate a distinct refined `record_id`
  - rebuild edited authored items with explicit manual-review provenance
  - recompute unresolved gaps using the same bounded gap policy already used by the authoring builders, so edited records stay honest
- Preserve inspectability with explicit refinement result objects rather than mutating evidence models.
  - `PatientAuthoredRecordRefinementResult`
  - `ProviderAuthoredRecordRefinementResult`
  - include:
    - `source_record_id`
    - `refined_record_id`
    - `edits_applied`
    - `edited_field_paths`
    - original record
    - effective refined record
- Adjust the current Dev UI wrapper workflow, not the core workflow:
  - extend top-level demo input with optional:
    - `patient_review_edits`
    - `provider_review_edits`
  - add a new stage between `provider_authoring` and `authored_bundle_preparation`
    - `authored_record_refinement`
  - keep `patient_record` / `provider_record` on the stage artifact as the effective records used downstream
  - add original-record and refinement-result fields so the canvas shows both original and edited views
- Orchestration remains unchanged.
  - It should consume the effective refined records exactly the same way it already consumes authored records today.

### 4. File-level change plan

- Create [authored_record_refinement_models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/authoring/authored_record_refinement_models.py)
  - review-edit input models and refinement result models
- Create [authored_record_refinement.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/authoring/authored_record_refinement.py)
  - deterministic patient/provider refinement helpers
- Update [__init__.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/authoring/__init__.py)
  - export the new refinement contracts/helpers
- Update [models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_authored_bundle_demo_workflow/models.py)
  - add optional review-edit inputs to the top-level demo input
  - add original-record and refinement-result fields to the stage/final result models
- Update [executors.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_authored_bundle_demo_workflow/executors.py)
  - add the refinement executor
  - route preparation to use the effective edited records
- Update [workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_authored_bundle_demo_workflow/workflow.py)
  - insert the new refinement stage into the sequential chain
- Add [test_authored_record_refinement.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_authored_record_refinement.py)
  - direct patient/provider refinement helper coverage
- Update [test_psca_authored_bundle_demo_workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_authored_bundle_demo_workflow.py)
  - edited-record path coverage through the Dev UI wrapper flow
- Update [README.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md)
  - document the new bounded review/edit step
- Update [development-plan.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md)
  - move focus from thin demo flow to thin review/edit refinement

### 5. Step-by-step implementation plan

1. Define the bounded patient/provider review-edit input models in the `authoring` package.
2. Define refinement result models that preserve:
   - original record
   - effective refined record
   - edited field paths
   - source/refined record ids
3. Extract or reuse the current bounded gap-recalculation rules from patient/provider authoring so refinement can keep `unresolved_authoring_gaps` honest after edits.
4. Implement patient refinement helper.
   - apply scalar edits
   - rebuild edited conditions/medications/allergies lists deterministically
   - mark edited items with manual-review provenance
5. Implement provider refinement helper.
   - apply scalar professional-fact edits
   - apply bounded zero-or-one organization/relationship edits
   - keep selected-relationship behavior coherent with the edited provider record
6. Export the new refinement helpers/contracts from `authoring.__init__`.
7. Extend the Dev UI wrapper input model with optional `patient_review_edits` and `provider_review_edits`.
8. Extend the wrapper stage/result models to preserve:
   - original patient/provider records
   - effective edited patient/provider records
   - refinement results
9. Implement `authored_record_refinement` executor.
   - consume the authored records from the first two stages
   - apply optional edits
   - return a stage artifact that exposes both original and effective records
10. Update the preparation executor to use the effective refined records, not the original authored records, while leaving orchestration unchanged.
11. Insert the refinement stage into the wrapper workflow sequence before preparation.
12. Add direct refinement tests covering:
   - no-op edit path returns the original record effectively unchanged
   - patient scalar edits
   - patient clinical-list replacement
   - provider scalar edits
   - provider thin-path refinement without inventing org/relationship
   - provider explicit org/relationship refinement path
13. Update wrapper-flow tests covering:
   - rich authored patient/provider path with edits applied before preparation
   - thin-provider path with visible preserved gaps after edits
   - final workflow run using the edited records cleanly
14. Update README and development plan after tests are green.

### 6. Definition of Done

- The Dev UI demo flow now supports a bounded review/edit step between authoring and preparation.
- A user can:
  - author one patient record
  - author one provider record
  - inspect both structured authored records
  - apply bounded structured edits
  - continue into the unchanged preparation and deterministic workflow run using the edited records
- The demo flow visibly preserves:
  - original authored patient/provider records
  - effective edited patient/provider records
  - refinement result metadata showing what changed
- Orchestration still maps authored records exactly once, after refinement.
- The core bundle-builder workflow remains unchanged.
- New tests prove:
  - deterministic refinement behavior
  - honest gap handling after edits
  - end-to-end edited-record execution through the existing demo flow
- Still out of scope:
  - persistence
  - reusable record management
  - broad CRUD
  - free-form JSON editing
  - conversational revision loops
  - core workflow redesign

### 7. Risks / notes

- The main risk is drifting into a generic editor platform. Keep edits narrowly typed and limited to source-authored fields only.
- A second risk is editing derived/downstream artifacts. The implementation must not allow edits against mapped contexts or workflow inputs.
- A third risk is losing provenance. Original authored records and effective edited records must both remain visible in the wrapper flow.
- A fourth risk is making provider editing too generic. Keep provider refinement aligned to the existing first-slice zero-or-one organization/relationship shape.
- A fifth risk is stale unresolved-gap data after edits. Refinement must reuse the existing bounded gap policy rather than leaving original gaps untouched.

### 8. Targeted `docs/development-plan.md` updates after implementation

- Section 8 `Current Focus`
  - change to: implement a thin authored-record review/edit refinement step inside the Dev UI demo flow so users can correct structured authored patient/provider records before orchestration and workflow run
- Section 9 `Next Planned Slice`
  - change to: after thin review/edit refinement, decide whether to add a slightly richer demo UX pass or return focus to a narrower workflow-quality/documentation slice
- Section 10 Phase 8 note
  - append that the Dev UI authored-input demo flow now supports bounded structured refinement of authored patient/provider records before preparation and deterministic workflow execution
- Section 12 `Known Early Assumptions`
  - add that review/edit is applied to authored records only, not mapped contexts or workflow internals
  - add that the first refinement slice uses bounded typed patch models rather than full-record replacement or free-form JSON editing
  - add that provider refinement remains aligned to the current zero-or-one organization/relationship authored shape
- Section 13 `Known Early Risks`
  - add that review/edit refinement may drift into CRUD/platform work unless the editable surface stays tightly bounded
  - add that failing to recompute or reconcile unresolved gaps after edits would make refined authored records misleading
- Section 16 `Immediate Next Objective`
  - update to: complete the thin authored-record review/edit refinement step and prove edited patient/provider authored records can continue through the existing preparation and deterministic workflow path unchanged downstream
