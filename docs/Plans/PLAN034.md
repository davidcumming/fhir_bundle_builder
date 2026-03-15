## Patient Authoring Foundation

### Summary

Build the first upstream patient-authoring foundation as a new bounded domain module, not as UI and not as a redesign of the existing PS-CA bundle workflow. The slice should add typed patient-authoring models, an offline/demo natural-language transformer, an explicit complexity policy, and a deterministic mapper into the current `PatientContextInput`.

The key decision is to use **contract + demo** now:
- natural-language input is accepted
- the output is a structured `PatientAuthoredRecord`
- the authoring transformer is **deterministic and bounded**, using light fact extraction plus a small scenario/template policy
- no live model/runtime integration is introduced in this slice
- the existing bundle-builder workflow remains deterministic and unchanged, consuming only mapped `patient_context`

### Important interfaces/types

- `PatientComplexityLevel = Literal["low", "medium", "high"]`
- `PatientAuthoringInput`
  - `authoring_text: str`
  - `complexity_level: PatientComplexityLevel`
  - optional `scenario_label: str`
- `PatientAuthoredRecord`
  - `record_id: str`
  - `patient` identity/demographics
  - `conditions`
  - `medications`
  - `allergies`
  - bounded structured background facts that are useful but not fully mappable yet
  - `complexity_policy_applied`
  - `unresolved_authoring_gaps`
  - `authoring_evidence`
- `map_authored_patient_to_patient_context(...) -> PatientAuthoringMapResult`
  - returns `PatientContextInput`
  - returns explicit unmapped/deferred authored fields so the boundary stays inspectable

## 1. Repo assessment

- What exists now:
  - the repo is strong on deterministic downstream workflow behavior
  - `WorkflowBuildInput.patient_context` is already a clean typed input boundary
  - `PatientContextInput` currently supports only:
    - patient identity
    - optional gender
    - optional birth date
    - bounded lists of conditions, medications, allergies
  - `request_normalization_builder.py` already gives the exact downstream normalization behavior the authoring slice must feed:
    - single-entry selection for condition/allergy when exactly one exists
    - first-two medication planning
    - explicit medication overflow deferral
- What patient-side capabilities already exist in the workflow:
  - deterministic consumption of patient identity/demographics
  - deterministic condition/allergy/medication text consumption
  - bounded multiplicity behavior already proven for current patient lists
  - explicit validation and traceability around those patient-driven fields
- What is missing for upstream authoring:
  - no authoring models
  - no natural-language-to-patient-record boundary
  - no complexity policy
  - no authored-record-to-`patient_context` mapper
  - no place in the repo yet for reusable upstream authoring logic outside the workflow package
- Constraints that matter now:
  - the bundle-builder workflow must stay deterministic and downstream-only
  - no provider authoring in this slice
  - no UI tabs
  - no live model integration in this slice
  - no generic patient-profile platform or persistence system
  - any authored field that cannot map cleanly now must be either retained as authored-only context or explicitly marked unmapped/deferred

## 2. Proposed patient authoring foundation scope

- Add a bounded patient authoring foundation that produces:
  - `PatientAuthoringInput`
  - `PatientComplexityLevel`
  - `PatientAuthoredRecord`
  - `PatientAuthoringMapResult`
  - a deterministic/demo authoring builder
  - a deterministic mapper into current `PatientContextInput`
- Exact bounded outputs for this slice:
  - patient identity:
    - display name
    - deterministic authored `patient_id`
    - optional administrative gender
    - optional `age_years`
    - optional `birth_date` only when explicitly available
  - patient background facts:
    - optional residence text
    - optional smoking-status text
  - authored clinical lists:
    - `conditions`
    - `medications`
    - `allergies`
  - inspectability:
    - applied complexity policy
    - item/source provenance
    - unresolved authoring gaps
    - unmapped-to-workflow field list
- Complexity meaning in this slice:
  - complexity is a **bounded target richness policy**, not a license for uncontrolled invention
  - it defines deterministic upper targets and history detail expectations
  - recommended exact policy:
    - `low`: brief history, target up to 1 condition, up to 1 medication, up to 0 allergies
    - `medium`: standard history, target up to 2 conditions, up to 2 medications, up to 1 allergy
    - `high`: richer history, target up to 3 conditions, up to 3 medications, up to 2 allergies
  - in this slice, the demo transformer may author fewer items than the target if the prompt does not honestly support them
  - when that happens, the record must expose the shortfall as `unresolved_authoring_gaps`
- What remains deferred:
  - provider authoring
  - UI tabs/modules
  - live model-backed authoring
  - persistence/database design
  - open-ended medical chart generation
  - generic long-term authoring platform
  - mapping of authored background facts like residence/smoking into the current bundle workflow beyond explicit “unmapped/deferred” reporting

## 3. Proposed authoring architecture

- Where the authoring models/builders should live:
  - add a new top-level bounded package under `src/fhir_bundle_builder/authoring/`
  - do not place this inside `workflows/psca_bundle_builder_workflow/`
  - reason: this is upstream reusable authoring logic, not bundle-generation logic
- Recommended module split:
  - `authoring/patient_models.py`
    - authoring input/output contracts and complexity policy types
  - `authoring/patient_builder.py`
    - deterministic/demo natural-language transformer
  - `authoring/patient_mapper.py`
    - deterministic authored-record -> `PatientContextInput` mapper
- How authored patient records should be structured:
  - `PatientAuthoredRecord.patient`
    - `patient_id`
    - `display_name`
    - `administrative_gender`
    - `age_years`
    - `birth_date`
  - `PatientAuthoredRecord.background_facts`
    - `residence_text`
    - `smoking_status_text`
  - `PatientAuthoredRecord.conditions / medications / allergies`
    - each item should carry:
      - stable authored item id
      - display text
      - `source_mode`
      - `source_note`
  - `PatientAuthoredRecord.complexity_policy_applied`
    - target counts + history detail level
  - `PatientAuthoredRecord.unresolved_authoring_gaps`
    - explicit list such as missing medications/allergies relative to target policy
  - `PatientAuthoredRecord.authoring_evidence`
    - source prompt text
    - builder mode
    - extracted demographic facts
    - applied scenario/template tags
- How they should map into current `patient_context`:
  - `patient.patient_id` -> `PatientIdentityInput.patient_id`
  - `patient.display_name` -> `PatientIdentityInput.display_name`
  - `patient.administrative_gender` -> `PatientIdentityInput.administrative_gender`
  - `patient.birth_date` -> `PatientIdentityInput.birth_date`
  - `age_years` does not map directly; leave unmapped unless birth date was explicitly resolved
  - authored `conditions` -> `PatientConditionInput[]`
  - authored `medications` -> `PatientMedicationInput[]`
  - authored `allergies` -> `PatientAllergyInput[]`
  - `background_facts` remain authored-only for now and must be listed in mapping evidence as unmapped
- Transformation mode for this slice:
  - **deterministic/demo hybrid, but offline**
  - recommended builder behavior:
    - deterministic extraction of simple demographic facts from free text
    - deterministic keyword/cue recognition for a small scenario tag set
    - deterministic authored-item generation from a bounded scenario/template library
    - no live LLM call and no hidden reasoning engine
  - this keeps the slice honest and testable while still accepting natural language
- Inspectability/provenance to require:
  - builder mode must be explicit, e.g. `demo_template_authoring`
  - every authored clinical item must declare whether it came from:
    - direct text extraction
    - scenario template
  - mapping result must show unmapped authored fields
  - compatibility with current bundle workflow must be proven in tests, not just assumed
- Default assumptions chosen:
  - no second Agent Framework workflow in this slice
  - the authoring foundation is a reusable domain module first
  - if a future live authoring workflow is added, it should wrap these same contracts rather than redefining them

## 4. File-level change plan

- Create `/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/authoring/__init__.py`
  - export the new authoring foundation surface
- Create `/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/authoring/patient_models.py`
  - `PatientComplexityLevel`, `PatientAuthoringInput`, `PatientAuthoredRecord`, evidence/mapping result types
- Create `/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/authoring/patient_builder.py`
  - deterministic/demo natural-language-to-authored-record builder
- Create `/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/authoring/patient_mapper.py`
  - authored-record -> `PatientContextInput` mapper
- Add `/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_patient_authoring_builder.py`
  - complexity policy, fact extraction, authored-record validity, unresolved-gap behavior
- Add `/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_patient_authoring_mapper.py`
  - mapping to `PatientContextInput`, unmapped field evidence, deterministic ids
- Update `/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_request_normalization_builder.py`
  - prove mapped authored patient records normalize cleanly through existing request normalization
- Update `/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py`
  - add one compatibility smoke test showing an authored-record-derived `patient_context` can drive the existing workflow
- Update `/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md`
  - describe the new upstream patient authoring foundation and its bounded status
- Update `/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md`
  - shift focus from consolidation/defer to patient authoring foundation

## 5. Step-by-step implementation plan

1. Add the new `authoring` package and define the typed patient authoring contracts.
2. Define the exact complexity policy model with fixed target counts and history-detail labels.
3. Define authored patient identity/background/item models and mapping-result evidence types.
4. Implement deterministic authored `patient_id` generation.
   - recommended default: slugified display name plus a short stable suffix derived from input text
   - keep it deterministic and local; no persistence lookup
5. Implement the demo authoring builder.
   - parse natural-language input for:
     - name
     - gender/sex
     - age
     - optional residence text
     - optional smoking text
   - assign bounded scenario tags using deterministic keyword checks
   - generate authored conditions/medications/allergies only from:
     - directly extracted facts
     - a small explicit scenario-template library
   - if the prompt does not honestly support the complexity target, emit unresolved gaps instead of inventing more content
6. Implement the authored-record mapper into `PatientContextInput`.
   - map only fields the current workflow can consume now
   - emit explicit unmapped/deferred authored field names for everything else
7. Add direct builder tests covering:
   - low / medium / high complexity policy objects
   - example natural-language prompt extraction for name, gender, age, residence, smoking
   - deterministic authored record ids
   - item provenance labels
   - unresolved-gap behavior when prompt support is insufficient
8. Add direct mapper tests covering:
   - authored identity -> `PatientIdentityInput`
   - authored lists -> patient clinical item lists
   - unmapped fields include `age_years`, `residence_text`, and `smoking_status_text` when present
9. Add request-normalization compatibility tests covering:
   - mapped authored record passes through current `build_psca_normalized_request`
   - multi-item authored medication lists still produce current bounded first-two planning
   - multi-item authored allergies/problems still preserve current fixed single-entry downstream behavior
10. Add one workflow smoke test using a mapped authored patient record as `patient_context` to prove the current PS-CA workflow still accepts it cleanly.
11. Update README and development plan once tests are green.

## 6. Definition of Done

- It is now possible to take a bounded natural-language patient prompt plus a chosen complexity level and produce a structured `PatientAuthoredRecord`.
- That authored record is inspectable and includes:
  - deterministic patient id
  - identity/demographic facts
  - authored clinical lists
  - complexity policy applied
  - item provenance
  - unresolved authoring gaps
- It is now possible to map that authored record into the current `PatientContextInput` without changing the bundle-builder workflow.
- Existing request normalization accepts the mapped patient context and behaves consistently with current downstream rules.
- At least one end-to-end workflow test proves the authoring foundation creates immediate workflow-testing value.
- What is now possible for workflow testing:
  - author a patient from bounded natural language
  - choose low/medium/high complexity
  - convert the result into current workflow input
  - run the existing deterministic workflow with that authored patient context
- What remains out of scope:
  - provider authoring
  - UI tabs
  - live model-backed authoring
  - persistence/database work
  - generic patient-authoring platform
  - broad medical reasoning or unconstrained chart generation

## 7. Risks / notes

- The main real risk is accidental drift into open-ended medical generation. The builder must stay template/cue bounded and expose gaps rather than invent unsupported facts.
- A second real risk is letting complexity imply guaranteed synthetic clinical richness. In this slice, complexity should define a target envelope plus explicit gaps, not force invention.
- A third real risk is coupling authored-record structure too tightly to the current bundle workflow. The mapper should be explicit and separate so authored records can remain slightly richer than current `patient_context`.
- A fourth real risk is hiding unmapped authored facts. Fields like age, residence, and smoking must be preserved in the authored record and explicitly reported as unmapped by the current workflow boundary rather than silently dropped.
- A fifth real risk is overbuilding a second workflow too early. This slice should deliver a reusable upstream module first; a dedicated authoring workflow can wrap it later if live authoring is added.

## 8. Targeted `docs/development-plan.md` updates after implementation

- Section 8 `Current Focus`
  - change to: implement the first bounded patient authoring foundation that produces structured authored patient records and a clean mapping into the existing `patient_context` path
- Section 9 `Next Planned Slice`
  - change to: after patient authoring foundation, decide whether to add a narrow provider authoring foundation or a bounded live authoring/runtime integration step for patient authoring
- Section 10 Phase 8 note
  - append that the repo now includes a bounded upstream patient authoring foundation separate from deterministic bundle generation, with a clean mapper into current workflow inputs
- Section 12 `Known Early Assumptions`
  - add that the first patient authoring slice uses a bounded offline/demo transformer rather than live model-backed authoring
  - add that authored patient records may contain some structured authored facts that are preserved but not yet mapped into the current workflow
  - add that complexity currently expresses bounded target richness, not unconstrained clinical synthesis
- Section 13 `Known Early Risks`
  - add that upstream authoring may drift into unconstrained medical invention unless the authoring contract, template library, and mapping boundary remain explicit
  - add that live model-backed authoring is intentionally deferred, so early value depends on keeping the demo transformer narrow and honest
- Section 16 `Immediate Next Objective`
  - update to: complete the patient authoring foundation and prove authored-record compatibility with the current bundle-builder workflow before considering provider authoring or UI-level authoring flows
