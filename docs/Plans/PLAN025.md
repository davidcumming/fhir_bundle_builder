## 1. Repo assessment

- The patient side is still thin in [models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py):
  - `WorkflowBuildInput` only has `patient_profile`
  - `NormalizedBuildRequest` only has `patient_profile`
  - there is no patient-side equivalent to `provider_context`
- Request normalization in [request_normalization_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/request_normalization_builder.py) currently only expands provider data.
  - `patient_profile` is passed through unchanged
  - there is no normalized patient/clinical context or patient-side selection summary
- Current deterministic construction in [resource_construction_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/resource_construction_builder.py) is still patient-clinically shallow:
  - `Patient` only uses `patient_profile.profile_id` and `display_name`
  - `MedicationRequest`, `AllergyIntolerance`, and `Condition` still derive their text from `SectionScaffold.title + scenario_label`
  - no structured patient clinical data is available to those resources
- The schematic layer in [schematic_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/schematic_builder.py) still assumes one entry per required section and does not consume patient-clinical context.
- Validation in [validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/validation_builder.py) already has the right narrow hooks:
  - `bundle.patient_identity_content_present`
  - resource-specific placeholder-content checks for `MedicationRequest`, `AllergyIntolerance`, and `Condition`
  - these can be deepened without adding new repair targets
- Repair routing already has the right ownership in [repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/repair_decision_builder.py):
  - patient identity routes to `build-patient-1`
  - the three section-entry content findings already route to their own `resource_construction` steps
- Tests still assume thin patient input:
  - [test_psca_request_normalization_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_request_normalization_builder.py)
  - [test_psca_resource_construction_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_resource_construction_builder.py)
  - [test_psca_validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_validation_builder.py)
  - [test_psca_bundle_builder_workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py)
- What changed since the previous slice:
  - provider-side normalized context, schematic provenance, and support-resource identity realism are in place
  - patient-side input remains the obvious unmatched gap
- The key constraint now is that the workflow still plans exactly one `MedicationRequest`, one `AllergyIntolerance`, and one `Condition`, so this slice cannot honestly consume arbitrary-length clinical lists as multiple resources yet.

## 2. Proposed slice scope

- Add an optional top-level `patient_context` while keeping `patient_profile` as a legacy compatibility path.
- Introduce one small explicit patient/clinical profile model, not a generic clinical graph:
  - patient identity
  - narrow structured lists for the current clinical trio:
    - conditions
    - medications
    - allergies
- Normalize that into a workflow-ready `NormalizedPatientContext` inside `NormalizedBuildRequest`.
- Immediate consumption in this slice:
  - `Patient` identity and optional demographic basics
  - section-entry display text for the current single `MedicationRequest`, `AllergyIntolerance`, and `Condition` placeholders, but only when a deterministic one-item selection exists
  - Dev UI inspectability through `request_normalization` and resource-construction evidence
- Keep intentionally out of scope:
  - dynamic section counts or multiple section-entry resources
  - patient-context-aware schematic expansion
  - generic clinical terminology modeling
  - patient management CRUD or persistence
  - free-text clinical synthesis or reasoning

## 3. Proposed patient input model expansion / richer clinical profile approach

- Add these new typed input models in [models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py):
  - `PatientIdentityInput`
    - `patient_id: str`
    - `display_name: str`
    - `source_type: Literal["stub", "patient_management"] = "stub"`
    - `administrative_gender: Literal["female", "male", "other", "unknown"] | None = None`
    - `birth_date: str | None = None`
  - `PatientConditionInput`
    - `condition_id: str`
    - `display_text: str`
  - `PatientMedicationInput`
    - `medication_id: str`
    - `display_text: str`
  - `PatientAllergyInput`
    - `allergy_id: str`
    - `display_text: str`
  - `PatientContextInput`
    - `patient: PatientIdentityInput`
    - `conditions: list[PatientConditionInput]`
    - `medications: list[PatientMedicationInput]`
    - `allergies: list[PatientAllergyInput]`
- Add a normalized workflow-facing model:
  - `NormalizedPatientContext`
    - `patient: PatientIdentityInput`
    - copied `conditions`, `medications`, `allergies`
    - `selected_condition_for_single_entry: PatientConditionInput | None`
    - `selected_medication_for_single_entry: PatientMedicationInput | None`
    - `selected_allergy_for_single_entry: PatientAllergyInput | None`
    - `normalization_mode: Literal["legacy_patient_profile", "patient_context_explicit"]`
- Extend public workflow types:
  - `WorkflowBuildInput`
    - keep `patient_profile`
    - add `patient_context: PatientContextInput | None = None`
  - `NormalizedBuildRequest`
    - keep `patient_profile` as the compatibility view
    - add `patient_context: NormalizedPatientContext`
- Compatibility and normalization rules:
  - if `patient_context` is present, it is authoritative
  - derive compatibility `patient_profile` from `patient_context.patient`
  - if `patient_context` is absent, synthesize `NormalizedPatientContext` from legacy `patient_profile`
  - for each current clinical trio list:
    - if list length is exactly `1`, populate the corresponding `selected_*_for_single_entry`
    - if list length is `0` or `>1`, leave the selected item `None`
    - do not error on multiple items; keep the full list inspectable and explicitly defer broader consumption
- Immediate downstream consumption:
  - `Patient`
    - source `identifier[0].value` and `name[0].text` from `normalized_request.patient_context.patient`
    - populate `gender` when `administrative_gender` is present
    - populate `birthDate` when `birth_date` is present
  - `MedicationRequest`
    - when `selected_medication_for_single_entry` exists, set `medicationCodeableConcept.text` from `display_text`
    - otherwise keep the current section-title placeholder fallback
  - `AllergyIntolerance`
    - when `selected_allergy_for_single_entry` exists, set `code.text` from `display_text`
    - otherwise keep the current fallback
  - `Condition`
    - when `selected_condition_for_single_entry` exists, set `code.text` from `display_text`
    - otherwise keep the current fallback
- Validation changes:
  - keep `bundle.patient_identity_content_present`, but make it conditional on optional patient-context fields:
    - always require `active`, `identifier[0].value`, `name[0].text`
    - additionally require `gender` only when `administrative_gender` is present
    - additionally require `birthDate` only when `birth_date` is present
  - keep existing section-entry content finding codes, but make their expected text dynamic:
    - selected structured clinical item text when a single item is available
    - section-title placeholder fallback otherwise
- What remains deferred after this slice:
  - schematic assumptions/counts from patient context
  - multiple resources per section
  - structured dosage, severity, onset, verification source, coding systems, or clinical timelines
  - stronger clinical-profile-to-section alignment rules beyond the one current resource per section

## 4. File-level change plan

- Update [models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py)
  - add patient identity and clinical-profile input models
  - add `NormalizedPatientContext`
  - extend `WorkflowBuildInput` and `NormalizedBuildRequest`
  - expand `ProfileReferenceInput.source_type` to include `patient_management` for honest compatibility derivation
- Update [request_normalization_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/request_normalization_builder.py)
  - add deterministic patient-context normalization alongside the existing provider-context normalization
  - derive compatibility `patient_profile` from normalized patient identity
  - update request-normalization summary/placeholder note to mention richer patient context
- Update [resource_construction_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/resource_construction_builder.py)
  - source `Patient` from normalized patient context
  - populate optional `gender` and `birthDate`
  - use selected single-item clinical profile entries for section-entry text when available
  - update deterministic evidence and assumptions accordingly
- Update [validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/validation_builder.py)
  - make patient identity validation conditional on optional gender/birth date
  - make section-entry expected text dynamic from normalized patient context
- Update tests:
  - [test_psca_request_normalization_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_request_normalization_builder.py)
  - [test_psca_resource_construction_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_resource_construction_builder.py)
  - [test_psca_validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_validation_builder.py)
  - [test_psca_bundle_builder_workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py)
- Update docs:
  - [README.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md)
  - [docs/development-plan.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md)
- No changes needed in this slice to:
  - [build_plan_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/build_plan_builder.py)
  - [schematic_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/schematic_builder.py)
  - [repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/repair_decision_builder.py)
  - existing routing codes already match the owning steps

## 5. Step-by-step implementation plan

1. Add the new patient/clinical input models and `NormalizedPatientContext` to `models.py`.
2. Extend `WorkflowBuildInput` with optional `patient_context` and `NormalizedBuildRequest` with normalized patient context.
3. Implement `_normalize_patient_context(...)` in [request_normalization_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/request_normalization_builder.py):
   - legacy `patient_profile` fallback
   - authoritative `patient_context`
   - compatibility `patient_profile` derivation
   - deterministic single-entry selection for the current trio
4. Update request-normalization text so Dev UI shows that both provider and patient context are now normalized upstream.
5. Update `Patient` construction:
   - id/name from normalized patient identity
   - add `gender` and `birthDate` when supplied
   - add corresponding deterministic-value evidence and reduce deferred paths only for fields actually populated
6. Update section-entry construction:
   - `MedicationRequest.medicationCodeableConcept.text`
   - `AllergyIntolerance.code.text`
   - `Condition.code.text`
   - use selected structured clinical item text when a single item is deterministically available
   - otherwise preserve the current section-title placeholder text
7. Update validation helpers so expected patient and section-entry content comes from normalized patient context when present, otherwise the legacy fallback path stays valid.
8. Update normalization tests:
   - legacy `patient_profile` only -> `legacy_patient_profile`
   - explicit `patient_context` -> compatibility `patient_profile` derived correctly
   - exactly one medication/allergy/condition -> corresponding selected single-entry fields populated
   - multiple items in a list -> selected single-entry field remains `None`, full list preserved, no normalization error
9. Update construction tests:
   - rich patient context populates `Patient.gender` and `Patient.birthDate` when provided
   - rich patient context with one medication/allergy/condition item populates the three current section-entry text fields from structured input
   - legacy mode still uses section-title placeholder text
10. Update validation tests:
    - missing `gender` or `birthDate` only fails when the normalized patient context supplied those values
    - wrong section-entry text fails the existing resource-specific content finding when a selected clinical item exists
    - legacy mode still validates against the current placeholder text behavior
11. Update the workflow smoke test:
    - switch the main smoke path to pass `patient_context`
    - assert normalized patient context is visible in `request_normalization`
    - assert `Patient` and the three section-entry resources reflect the richer structured input where deterministically consumable
12. Update README and `docs/development-plan.md` once tests are green.

## 6. Definition of Done

- `WorkflowBuildInput` supports an optional richer `patient_context` with patient identity and narrow structured clinical-profile lists.
- `NormalizedBuildRequest` exposes an inspectable `patient_context` with:
  - normalized patient identity
  - the full copied clinical lists
  - single-entry selections for the current trio when deterministically available
  - a patient normalization mode
- Legacy callers/tests using only `patient_profile` still work.
- `Patient` construction now uses normalized patient context and can populate:
  - `identifier[0].value`
  - `name[0].text`
  - `gender` when supplied
  - `birthDate` when supplied
- The current single `MedicationRequest`, `AllergyIntolerance`, and `Condition` can now use structured clinical item text when exactly one item exists in the corresponding normalized list.
- Dev UI now visibly shows richer patient/clinical context in `request_normalization`, and resource-construction evidence shows when text came from structured clinical profile input instead of section-title fallback.
- Validation protects only fields the workflow can now honestly populate.
- What remains deferred:
  - patient-context-aware schematic assumptions
  - multiple resources per section
  - deeper clinical semantics beyond the current trio’s display text and basic patient demographics
  - any patient master-data or clinical reasoning engine

## 7. Risks / notes

- The main real risk is overreaching from a single planned placeholder per section. Multiple medications/allergies/conditions should remain inspectable but not automatically collapsed into one chosen item unless the list length is exactly one.
- A second real risk is drifting between compatibility `patient_profile` and authoritative `patient_context`. `patient_context` should win whenever both are supplied.
- A third real risk is overclaiming clinical realism. The new trio item models should stay text-oriented and narrow; do not introduce speculative clinical coding or reasoning.
- A fourth real risk is leaking this slice into schematic/planning redesign. Current one-entry-per-section planning should remain unchanged in this iteration.

## 8. Targeted `docs/development-plan.md` updates after implementation

- In Section 8, change `Current Focus` from the generic next realism/validation slice to the next bounded follow-on after structured patient/clinical context exists upstream.
- In Section 9, set `Next Planned Slice` to a patient-context consumption slice such as: “Use normalized patient/clinical context in schematic assumptions and revisit whether one-entry-per-section planning should remain fixed.”
- In Section 10, update the Phase 8 note to state that the workflow now accepts structured patient/clinical context, normalizes it deterministically, and uses the current single-entry selections for richer patient and section-entry content where the workflow can consume them honestly.
- In Section 12, add/refine the patient-side assumption to say the workflow now accepts explicit patient/clinical context, but current planning still assumes one section-entry resource per required section.
- In Section 13, replace the current generic next-risk wording with the real remaining risk: richer patient clinical context is now available upstream, but the workflow still plans only one entry per section, so multi-item profile content is inspectable yet only partially consumable.
- In Section 16, update the immediate next objective away from patient input expansion and toward the next bounded patient-context-aware schematic/planning or content-alignment slice.
