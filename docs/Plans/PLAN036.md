1. Repo assessment

- The repo already has the core upstream/downstream pieces needed for this slice:
  - bounded upstream authored-record contracts in `/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/authoring/`
  - deterministic patient and provider mappers into:
    - `PatientContextInput`
    - `ProviderContextInput`
  - a stable downstream workflow entrypoint in [`workflow.py`](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/workflow.py)
  - a stable top-level workflow request contract in [`models.py`](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py)
- What authoring and workflow capabilities already exist:
  - `PatientAuthoredRecord` plus deterministic mapper and tests
  - `ProviderAuthoredRecord` plus deterministic mapper and tests
  - current request normalization already accepts mapped `patient_context` and `provider_context`
  - current workflow tests prove patient-only and provider-only authored input compatibility separately
- What is missing for end-to-end authored-input execution:
  - no composed authored-input request type
  - no thin helper that takes one authored patient record plus one authored provider record and builds `WorkflowBuildInput`
  - no single inspectable result object that shows:
    - source authored record ids
    - both map results
    - unmapped authored facts
    - the final workflow-ready request
  - no single end-to-end harness test that drives the workflow from both authored records without hand-assembling workflow input
- The main current gap is fragmentation, not missing core capability:
  - today the repo can do the work, but callers/tests must manually stitch together patient/provider mapping and workflow request assembly
- Constraints that matter now:
  - do not change the deterministic workflow loop
  - do not move authoring logic into the workflow package
  - do not add UI, persistence, or live-model runtime behavior
  - keep the orchestration thin, typed, and inspectable
  - preserve the current honest mapping boundary, including unmapped authored facts

2. Proposed thin orchestration scope

- Add one thin authored-input orchestration layer that produces:
  - `AuthoredBundleBuildInput`
  - `AuthoredBundleBuildPreparation`
  - `AuthoredBundleWorkflowInputSummary`
  - `AuthoredBundleBuildRunResult`
  - one deterministic preparation helper
  - one thin async run helper
- Exact bounded outputs for this slice:
  - a composed authored-input contract containing:
    - one `PatientAuthoredRecord`
    - one `ProviderAuthoredRecord`
    - one `BundleRequestInput`
    - optional `SpecificationSelection`
    - optional `WorkflowOptionsInput`
  - a preparation result containing:
    - source patient/provider authored record ids
    - nested `PatientAuthoringMapResult`
    - nested `ProviderAuthoringMapResult`
    - fully built `WorkflowBuildInput`
    - compact workflow-input summary
  - a run result containing:
    - the preparation result
    - the final `WorkflowSkeletonRunResult`
- Authored-input contract to use:
  - use authored records directly, not authoring prompts
  - keep request/spec/workflow-options explicit so this stays a harness around the existing workflow input, not a new app request layer
- What should remain deferred:
  - multi-record selection
  - patient/provider storage or lookup
  - UI-level composition flows
  - live authoring/runtime integration
  - new workflow executors or a second Agent Framework workflow
  - generalized orchestration for arbitrary future modules

3. Proposed orchestration architecture

- Where the orchestration models/builders should live:
  - inside the existing upstream package at `/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/authoring/`
  - not inside `/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/`
  - reason: this is an upstream composition boundary around authored records and existing workflow input, not a workflow-stage redesign
- Recommended module split:
  - `authoring/authored_bundle_models.py`
    - composed authored-input and result contracts
  - `authoring/authored_bundle_orchestration.py`
    - deterministic preparation helper and thin async run helper
- How authored patient/provider records should be composed:
  - `AuthoredBundleBuildInput`
    - `patient_record: PatientAuthoredRecord`
    - `provider_record: ProviderAuthoredRecord`
    - `request: BundleRequestInput`
    - `specification: SpecificationSelection = default`
    - `workflow_options: WorkflowOptionsInput = default`
- How they should map into current `WorkflowBuildInput`:
  - call existing mappers first:
    - `map_authored_patient_to_patient_context(...)`
    - `map_authored_provider_to_provider_context(...)`
  - derive `patient_profile` deterministically from the authored patient identity:
    - `profile_id = patient_record.patient.patient_id`
    - `display_name = patient_record.patient.display_name`
    - `source_type = "patient_management"`
  - derive `provider_profile` deterministically from the authored provider identity:
    - `profile_id = provider_record.provider.provider_id`
    - `display_name = provider_record.provider.display_name`
    - `source_type = "provider_management"`
  - compose those into `WorkflowBuildInput` with the mapped contexts plus explicit request/spec/options
- How inspectability/provenance should be surfaced:
  - `AuthoredBundleBuildPreparation` should expose:
    - `source_patient_record_id`
    - `source_provider_record_id`
    - `patient_mapping`
    - `provider_mapping`
    - `workflow_input`
    - `workflow_input_summary`
  - `workflow_input_summary` should stay compact and deterministic, for example:
    - patient/provider ids
    - patient mapped counts
    - provider organization/relationship counts
    - whether a selected provider-role relationship is present
    - request scenario label
  - do not duplicate detailed authored evidence already stored on authored records; reference it via source record ids and nested map results
- Whether a demo entrypoint/helper should exist:
  - yes
  - add one thin async helper that invokes the current workflow directly:
    - build preparation
    - call `workflow.run(message=prepared.workflow_input, include_status_events=True)`
    - return `AuthoredBundleBuildRunResult`
  - do not create a new Agent Framework workflow or a CLI in this slice
- Defaults chosen for this slice:
  - preparation helper is deterministic only
  - run helper uses the existing workflow directly
  - `specification` and `workflow_options` default to existing workflow defaults unless explicitly provided
  - no additional authored-record selection abstraction beyond one patient record plus one provider record

4. File-level change plan

- Create [`authored_bundle_models.py`](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/authoring/authored_bundle_models.py)
  - define `AuthoredBundleBuildInput`, `AuthoredBundleWorkflowInputSummary`, `AuthoredBundleBuildPreparation`, and `AuthoredBundleBuildRunResult`
- Create [`authored_bundle_orchestration.py`](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/authoring/authored_bundle_orchestration.py)
  - implement:
    - deterministic preparation helper from authored records to `WorkflowBuildInput`
    - thin async run helper that calls the current workflow
- Update [`__init__.py`](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/authoring/__init__.py)
  - export the new orchestration contracts and helpers
- Add [`test_authored_bundle_orchestration.py`](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_authored_bundle_orchestration.py)
  - direct preparation and end-to-end orchestration coverage
- Update [`README.md`](/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md)
  - describe the new thin authored-input-to-workflow harness
- Update [`development-plan.md`](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md)
  - move focus from provider authoring foundation to thin authoring-to-bundle orchestration

5. Step-by-step implementation plan

1. Add the new authored-bundle orchestration models in the `authoring` package.
2. Define the composed input contract around existing authored records and existing workflow request/spec/options models.
3. Define the compact preparation result contract with:
   - source record ids
   - nested patient/provider map results
   - final `WorkflowBuildInput`
   - compact summary
4. Implement the deterministic preparation helper.
   - call existing patient/provider mappers
   - derive `patient_profile` and `provider_profile` from authored identities
   - construct `WorkflowBuildInput`
   - populate the compact summary from mapped counts and selection flags
5. Implement the thin async run helper.
   - accept `AuthoredBundleBuildInput`
   - call the preparation helper
   - invoke the existing `workflow.run(...)`
   - return the preparation plus final `WorkflowSkeletonRunResult`
6. Export the new contracts/helpers from `authoring.__init__`.
7. Add direct orchestration tests covering:
   - a rich authored patient + rich authored provider build preparation
   - correct nested map results
   - correct derived profile refs
   - correct workflow input summary
   - unmapped authored facts remain visible through nested map results
8. Add a thin-provider preparation test covering:
   - provider authored facts preserved
   - no organization/relationship invented
   - provider unmapped facts remain inspectable
   - resulting workflow input honestly reflects the thin provider path
9. Add one end-to-end async harness test covering:
   - authored patient record + authored provider record
   - orchestration helper builds the workflow input
   - helper runs the existing workflow without manual input assembly
   - final output reflects both authored contexts
10. Update README and development plan once tests pass.

6. Definition of Done

- It is now possible to take:
  - one `PatientAuthoredRecord`
  - one `ProviderAuthoredRecord`
  - one `BundleRequestInput`
  and deterministically prepare a full `WorkflowBuildInput` without hand-assembling workflow fields in tests or callers.
- It is now possible to run the existing deterministic workflow through one thin authored-input orchestration helper.
- The preparation result is inspectable and includes:
  - source authored record ids
  - patient/provider map results
  - unmapped authored facts
  - final workflow input
  - compact workflow input summary
- At least one end-to-end test proves the authored patient + authored provider path can drive a realistic workflow run as one coherent authored-input scenario.
- The workflow package and executor graph remain unchanged.
- What should now be possible for testing/demo:
  - author patient upstream
  - author provider upstream
  - compose those records into one authored bundle-build request
  - run the deterministic PS-CA workflow through a single reusable harness
  - inspect both the mapping boundary and final workflow output
- What remains out of scope:
  - UI tabs
  - persistence or reusable record storage
  - multi-record management/selection
  - live model-backed authoring runtime
  - provider research integration
  - any redesign of workflow stages or repair behavior

7. Risks / notes

- The main real risk is overgrowing this into a new app layer. Keep it to a thin preparation helper plus a thin run helper.
- A second real risk is hiding the mapping boundary. The orchestration result must expose the nested patient/provider map results rather than flattening everything into one opaque object.
- A third real risk is duplicating workflow logic. The orchestration layer must only compose existing mappers and call the existing workflow; it must not reimplement normalization or selection behavior.
- A fourth real risk is letting profile refs diverge from authored identities. The preparation helper should derive profile refs directly from the authored record identities so the top-level request stays coherent.
- A fifth real risk is adding a second workflow too early. This slice should remain a plain helper/harness, not a new Agent Framework workflow.

8. Targeted `docs/development-plan.md` updates after implementation

- Section 8 `Current Focus`
  - change to: implement the first thin authoring-to-bundle orchestration layer that composes authored patient/provider records into workflow-ready input and proves one coherent authored-input bundle-generation path
- Section 9 `Next Planned Slice`
  - change to: after thin authoring-to-bundle orchestration, decide whether to add a thin UI-facing authoring flow around the new harness or a bounded live authoring/runtime integration step
- Section 10 Phase 8 note
  - append that the repo now includes a thin authored-input orchestration layer that composes upstream authored records into deterministic workflow input and runs the existing workflow unchanged
- Section 12 `Known Early Assumptions`
  - add that the first authored-input orchestration slice is a thin helper/harness, not a new workflow or application layer
  - add that authored patient/provider records remain the upstream source of truth, while orchestration only composes existing mappers and existing workflow input types
  - add that profile refs in the composed workflow input are derived deterministically from authored record identities
- Section 13 `Known Early Risks`
  - add that authored-input orchestration may become an opaque mini-platform unless the composed result continues to expose nested patient/provider mapping outputs and unmapped authored facts
  - add that duplicating normalization or workflow behavior in the orchestration layer would undermine the current deterministic architecture
- Section 16 `Immediate Next Objective`
  - update to: complete the thin authoring-to-bundle orchestration layer and prove a full authored patient + authored provider path can drive the current bundle-builder workflow without manual workflow-input assembly
