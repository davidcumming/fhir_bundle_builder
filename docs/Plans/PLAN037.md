1. Repo assessment

- Summary:
  - The repo already has the domain contracts and deterministic helpers needed for an end-to-end authored-input demo.
  - What it does not have is a UI host beyond Dev UI, so the thinnest honest “UI-facing flow” is a new Dev UI workflow/entity that wraps the existing authoring and orchestration layers.
- What exists now:
  - bounded upstream patient authoring and provider authoring modules in `/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/authoring/`
  - thin authored-input orchestration in:
    - [`authored_bundle_models.py`](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/authoring/authored_bundle_models.py)
    - [`authored_bundle_orchestration.py`](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/authoring/authored_bundle_orchestration.py)
  - the existing deterministic PS-CA workflow exposed through Dev UI via:
    - [`entities/psca_bundle_builder_workflow/`](/Users/davidcumming/coding_projects/fhir_bundle_builder/entities/psca_bundle_builder_workflow)
- What building blocks already exist for a thin UI flow:
  - `PatientAuthoringInput` with natural-language text plus complexity
  - `ProviderAuthoringInput` with natural-language text
  - `AuthoredBundleBuildPreparation` with mapping and workflow-input summary
  - `WorkflowSkeletonRunResult` with the full downstream output
  - Dev UI directory-discoverable entity export pattern already in use
- What is missing for a usable end-to-end demo:
  - no second Dev UI-facing flow that starts from authoring text instead of prebuilt structured contexts
  - no single UI-oriented input shape for:
    - patient authoring text
    - provider authoring text
    - request/scenario
  - no staged review surface that exposes:
    - authored patient record
    - authored provider record
    - preparation summary
    - final workflow result
- Constraints that matter now:
  - no separate frontend stack exists in the repo
  - Dev UI is the only current interactive surface and already matches the “canvas pattern”
  - existing authoring and orchestration contracts should remain the source of truth
  - the current bundle-builder workflow input must stay unchanged

2. Proposed thin UI-facing flow scope

- Add one new Dev UI-facing demo workflow around the existing foundations.
- Exact bounded inputs to expose:
  - `patient_authoring: PatientAuthoringInput`
  - `provider_authoring: ProviderAuthoringInput`
  - `request: BundleRequestInput`
  - optional `specification: SpecificationSelection`
  - optional `workflow_options: WorkflowOptionsInput`
- Exact bounded outputs/review surfaces to expose:
  - stage 1: authored patient record
  - stage 2: authored provider record
  - stage 3: authored-input preparation result, including mapping summary
  - stage 4: final workflow result summary plus nested existing `WorkflowSkeletonRunResult`
- User flow to support:
  - enter patient authoring text and complexity
  - enter provider authoring text
  - enter request/scenario text
  - run the thin demo workflow in Dev UI
  - inspect authored records, preparation summary, and final workflow output on the canvas
- What should remain deferred:
  - separate patient/provider tabs
  - persistence or record library behavior
  - polished product shell/navigation
  - live authoring/runtime integration
  - internet-backed provider lookup
  - any change to the existing bundle-builder workflow contract

3. Proposed UI/integration architecture

- Where the thin UI flow should live:
  - create a new wrapper workflow package under `/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/`
  - export it through a second entity under `/Users/davidcumming/coding_projects/fhir_bundle_builder/entities/`
  - recommended workflow name: `PS-CA Authored Bundle Demo Flow`
- Why a second Dev UI workflow is the right host:
  - there is no existing web app/component layer to extend
  - widening the existing bundle-builder workflow input to accept authoring prompts would blur current domain boundaries
  - a wrapper workflow preserves:
    - authoring upstream
    - orchestration in the middle
    - deterministic bundle generation downstream
- How it should call existing authoring and orchestration helpers:
  - stage `patient_authoring`
    - call `build_patient_authored_record(...)`
  - stage `provider_authoring`
    - call `build_provider_authored_record(...)`
  - stage `authored_bundle_preparation`
    - call `prepare_authored_bundle_build_input(...)`
  - stage `bundle_builder_run`
    - invoke the existing workflow directly using `preparation.workflow_input`
    - do not rework the existing workflow or existing orchestration contracts
- What state/results it should show:
  - use one progressive typed stage artifact that carries forward:
    - original demo input
    - optional authored patient record
    - optional authored provider record
    - optional preparation result
    - optional final workflow output
    - optional compact final output summary
  - recommended model pattern:
    - reuse the existing `StageArtifact` shape for `stage_id`, `status`, `summary`, `placeholder_note`, `source_refs`
    - add the optional payload fields above
- How inspectability should be preserved:
  - show actual authored records, not reduced text summaries
  - show actual `AuthoredBundleBuildPreparation`, not a rederived UI-only summary
  - add only one small final output summary model for quick scanning in Dev UI, while preserving the full nested workflow output
- Whether a single page/view is sufficient:
  - yes
  - one Dev UI workflow entity is sufficient for this slice
  - do not add a separate frontend app, router, or tab system

4. File-level change plan

- Create `/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_authored_bundle_demo_workflow/models.py`
  - top-level demo input model
  - progressive stage artifact/state model
  - compact final output summary model
- Create `/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_authored_bundle_demo_workflow/executors.py`
  - narrow executors for patient authoring, provider authoring, preparation, and workflow run
- Create `/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_authored_bundle_demo_workflow/workflow.py`
  - the wrapper workflow graph
- Create `/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_authored_bundle_demo_workflow/__init__.py`
  - export the new workflow
- Create:
  - `/Users/davidcumming/coding_projects/fhir_bundle_builder/entities/psca_authored_bundle_demo_workflow/__init__.py`
  - `/Users/davidcumming/coding_projects/fhir_bundle_builder/entities/psca_authored_bundle_demo_workflow/workflow.py`
  - directory-discoverable Dev UI export for the new demo flow
- Add `/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_authored_bundle_demo_workflow.py`
  - smoke/integration coverage for the new flow
- Update `/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md`
  - document the second Dev UI entity and the demo flow
- Update `/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md`
  - move current focus from orchestration to thin UI-facing flow

5. Step-by-step implementation plan

1. Define the new demo workflow input model.
   - reuse existing nested models for patient authoring, provider authoring, request, specification, and workflow options
2. Define one progressive stage artifact/state model for the wrapper workflow.
   - include optional authored patient/provider records
   - include optional preparation result
   - include optional final workflow output
   - include a compact final output summary
3. Implement `patient_authoring` executor.
   - accept top-level demo input
   - build `PatientAuthoredRecord`
   - return stage artifact with patient record populated
4. Implement `provider_authoring` executor.
   - accept prior stage artifact
   - build `ProviderAuthoredRecord`
   - return stage artifact with both authored records populated
5. Implement `authored_bundle_preparation` executor.
   - construct `AuthoredBundleBuildInput` from:
     - authored patient record
     - authored provider record
     - request/spec/options from the top-level demo input
   - call `prepare_authored_bundle_build_input(...)`
   - return stage artifact with preparation populated
6. Implement `bundle_builder_run` executor.
   - invoke the existing bundle-builder workflow using `preparation.workflow_input`
   - capture the final `WorkflowSkeletonRunResult`
   - derive a compact summary with:
     - scenario label
     - patient/provider ids
     - workflow validation status
     - candidate bundle entry count
     - whether a selected provider-role relationship was present
7. Wire the new wrapper workflow as a simple sequential chain:
   - `patient_authoring`
   - `provider_authoring`
   - `authored_bundle_preparation`
   - `bundle_builder_run`
8. Export the new workflow through a new Dev UI entity package.
9. Add smoke coverage for the rich path.
   - named patient with medium complexity
   - named provider with explicit organization and role
   - assert all four stages populate their intended review artifacts
   - assert final workflow output is valid and uses authored data
10. Add smoke coverage for the thin-provider path.
   - provider prompt with role/location but no organization
   - assert provider gaps remain visible
   - assert preparation shows no organization/relationship invention
   - assert the final workflow still runs through the thin provider path
11. Update README and development plan after tests are green.

6. Definition of Done

- A second Dev UI workflow entity exists for the thin authored demo flow.
- In Dev UI, a user can:
  - enter patient authoring text plus complexity
  - enter provider authoring text
  - enter request/scenario text
  - run one authored-input demo flow end to end
- The canvas visibly shows:
  - authored patient record
  - authored provider record
  - authored-input preparation/mapping summary
  - final workflow output summary and nested workflow result
- The new flow calls existing builders/helpers rather than reimplementing:
  - patient authoring
  - provider authoring
  - authored-input preparation
  - deterministic bundle generation
- The existing bundle-builder workflow remains unchanged.
- What should now be possible in a demo flow:
  - demonstrate authored-input-to-bundle generation without hand-building structured workflow inputs
  - inspect the major upstream/downstream integration boundary in Dev UI
  - show both rich provider-context and thin provider-context scenarios
- What remains out of scope:
  - full product shell
  - multi-tab patient/provider management
  - persistence/record libraries
  - live model-backed authoring
  - provider research integration
  - separate frontend framework adoption

7. Risks / notes

- The main real risk is accidentally using Dev UI as a product shell. This slice should stay explicitly demo-oriented and workflow-hosted.
- A second real risk is reimplementing orchestration logic inside the wrapper workflow. It should call existing authoring and preparation helpers, not duplicate them.
- A third real risk is hiding truthful edge cases. The thin-provider scenario must visibly preserve gaps and unmapped facts rather than smoothing them over in the demo UI.
- A fourth real risk is overcomplicating stage models. Use one progressive artifact model unless a clear need for separate stage models emerges during implementation.
- A fifth real risk is creating confusion between the two workflows. Docs and names should clearly distinguish:
  - the core deterministic bundle-builder workflow
  - the thin authored-input demo flow that wraps it

8. Targeted `docs/development-plan.md` updates after implementation

- Section 8 `Current Focus`
  - change to: implement the first thin UI-facing authoring flow around the existing authoring foundations and authored-input orchestration helper
- Section 9 `Next Planned Slice`
  - change to: after the thin UI-facing flow, decide whether to deepen UI structure slightly around the demo flow or defer UI expansion and return to a narrower workflow-quality slice
- Section 10 Phase 8 note
  - append that the repo now includes a second Dev UI-facing demo workflow that wraps upstream authoring and authored-input preparation around the unchanged deterministic bundle-builder workflow
- Section 12 `Known Early Assumptions`
  - add that the first UI-facing slice is hosted in Dev UI rather than a separate frontend stack
  - add that the UI-facing flow is a wrapper around existing authored-record, orchestration, and workflow contracts rather than a new source of truth
  - add that one narrow demo flow is sufficient for the first UI-facing proof point, and separate tabs remain deferred
- Section 13 `Known Early Risks`
  - add that the thin UI-facing flow may drift into a broader product shell unless it stays hosted as a narrow Dev UI demo workflow
  - add that widening the existing bundle-builder workflow input to accept authoring prompts would blur domain boundaries and should remain avoided
- Section 16 `Immediate Next Objective`
  - update to: complete the thin UI-facing authored demo flow and prove the authored patient-plus-provider path can be exercised end to end in Dev UI without changing the underlying workflow or orchestration contracts
