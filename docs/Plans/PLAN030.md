1. Repo assessment

- The repo already has the upstream patient-context inputs needed for this slice:
  - `NormalizedBuildRequest.patient_context`
  - exact patient identity/demographic fields
  - single-entry condition/allergy selections
  - authoritative bounded medication mapping in `planned_medication_entries`
- `resource_construction` already consumes that context honestly for the fields the workflow can populate:
  - `Patient.identifier[0].value`, `Patient.name[0].text`, optional `gender`, optional `birthDate`
  - `MedicationRequest.medicationCodeableConcept.text` for `medicationrequest-1` and `medicationrequest-2`
  - `AllergyIntolerance.code.text`
  - `Condition.code.text`
  - deterministic per-field source evidence already exists in resource-construction step results
- The current gap is not missing enrichment. It is that validation still treats patient-context alignment mostly as generic “content present”:
  - `bundle.patient_identity_content_present`
  - `bundle.medicationrequest_placeholder_content_present`
  - `bundle.medicationrequest_2_placeholder_content_present`
  - `bundle.allergyintolerance_placeholder_content_present`
  - `bundle.condition_placeholder_content_present`
- Those checks already compare exact expected values in many cases, but the repo does not clearly distinguish:
  - scaffold/field presence and fixed deterministic codes
  - exact alignment to normalized patient context or fallback placeholder policy
- That means patient-context alignment is still implicit:
  - Dev UI can infer it by reading normalized request + resource-construction evidence
  - validation does not expose a separate patient-context alignment story
  - repair findings do not clearly say “the structure is present but the patient-context-driven value is wrong”
- The bounded medications-only multiplicity path is structurally hardened already:
  - med1/med2 mapping is authoritative upstream
  - bundle-entry coherence has its own validation finding
  - this slice does not need more multiplicity work
- Constraints that matter now:
  - no multiplicity expansion beyond current medications-only path
  - no semantic clinical correctness engine
  - no redesign of validation architecture
  - preserve current repair ownership by build step

2. Proposed slice scope

- Keep construction behavior unchanged.
- Keep multiplicity unchanged:
  - one or two medications only, per the existing bounded rule
  - allergies/problems remain one entry
- Add explicit patient-context-to-bundle alignment hardening in the validation stage.
- Split current validation behavior into two layers for the current honest fields:
  - structural/scaffold correctness
  - exact patient-context alignment
- Add a small validation-evidence summary so Dev UI shows what the validation stage expected from normalized patient context and whether each expectation came from:
  - structured patient context
  - fallback placeholder policy
- Do not change:
  - request normalization logic
  - schematic planning rules
  - build-plan structure
  - bundle-finalization structure
  - standards-validator behavior

3. Proposed patient-context-to-bundle content alignment hardening approach

- Add explicit workflow finding codes for alignment, while keeping the current content-present findings for structural checks.
- Recommended new workflow finding codes:
  - `bundle.patient_identity_aligned_to_context`
  - `bundle.medicationrequest_placeholder_text_aligned_to_context`
  - `bundle.medicationrequest_2_placeholder_text_aligned_to_context`
  - `bundle.allergyintolerance_placeholder_text_aligned_to_context`
  - `bundle.condition_placeholder_text_aligned_to_context`
- Narrow the meaning of existing structural codes:
  - `bundle.patient_identity_content_present`
    - require `active == true`
    - require non-empty `identifier[0].value`
    - require non-empty `name[0].text`
    - when normalized patient context supplies gender or birth date, require those fields to be present and non-empty
    - do not require exact equality here
  - `bundle.medicationrequest_placeholder_content_present` and `bundle.medicationrequest_2_placeholder_content_present`
    - require `status == draft`
    - require `intent == proposal`
    - require non-empty `medicationCodeableConcept.text`
    - do not require exact expected text here
  - `bundle.allergyintolerance_placeholder_content_present`
    - require the current fixed status codes
    - require non-empty `code.text`
    - do not require exact expected text here
  - `bundle.condition_placeholder_content_present`
    - require the current fixed status codes
    - require non-empty `code.text`
    - do not require exact expected text here
- Add gated alignment checks:
  - only run `bundle.patient_identity_aligned_to_context` if `bundle.patient_identity_content_present` passed
  - only run the new text-alignment checks if the corresponding structural content check passed
  - this prevents duplicate findings for the same missing-field fault and keeps repair precision narrow
- Exact alignment behavior:
  - `bundle.patient_identity_aligned_to_context`
    - exact match of patient id and display name
    - exact match of gender/birthDate when those values were supplied upstream
  - medication/alergy/condition text-alignment findings
    - exact match to the deterministic expected text already derived from:
      - `planned_medication_entries` for med1/med2
      - selected single-entry allergy/condition when available
      - section-title fallback when structured single-entry consumption does not apply
- Add a small validation-evidence summary, not a generic engine.
- Recommended validation-evidence additions:
  - `PatientContextAlignmentEvidence`
    - `normalization_mode`
    - `patient_id`
    - `display_name`
    - `administrative_gender_expected: str | None`
    - `birth_date_expected: str | None`
    - `section_entry_expectations: list[SectionEntryTextAlignmentExpectation]`
  - `SectionEntryTextAlignmentExpectation`
    - `placeholder_id`
    - `resource_type`
    - `expected_text`
    - `alignment_mode: Literal["structured_patient_context", "fallback_placeholder"]`
    - `source_artifact`
    - `source_detail`
- Populate validation evidence directly from `normalized_request` plus schematic fallback policy, not from the candidate bundle.
- Repair ownership should stay exactly with current resource-construction owners:
  - `bundle.patient_identity_aligned_to_context` -> `build-patient-1`
  - med1 text alignment -> `build-medicationrequest-1`
  - med2 text alignment -> `build-medicationrequest-2`
  - allergy text alignment -> `build-allergyintolerance-1`
  - condition text alignment -> `build-condition-1`
- Keep the current medication bundle-entry coherence finding and ownership unchanged.
- Keep this slice intentionally deferred from:
  - broader clinical truth/terminology validation
  - allergies/problems multiplicity
  - arbitrary-length medication alignment
  - generic patient-context alignment frameworks

4. File-level change plan

- Update [models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py)
  - add the small validation-evidence models for patient-context alignment expectations
  - extend `ValidationEvidence` with that summary
- Update [validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/validation_builder.py)
  - split structural checks from exact patient-context alignment checks
  - add the new workflow finding codes
  - gate alignment checks on structural success
  - populate validation evidence from normalized patient context and fallback policy
- Update [repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/repair_decision_builder.py)
  - route the new patient-context alignment findings to the existing owning resource-construction build steps
  - add directive-map entries so repair directives stay precise
- Update tests:
  - [test_psca_validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_validation_builder.py)
  - [test_psca_repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_repair_decision_builder.py)
  - [test_psca_repair_execution_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_repair_execution_builder.py) only for one or two narrow routing smoke cases
  - [test_psca_bundle_builder_workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py)
- Update docs:
  - [README.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md)
  - [docs/development-plan.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md)
- No planned code changes for:
  - request normalization
  - schematic builder
  - build-plan builder
  - resource-construction builder
  - bundle-finalization builder
  - standards validator

5. Step-by-step implementation plan

1. Add the validation-evidence models for patient-context alignment expectations in `models.py`.
2. Extend `ValidationEvidence` to carry that patient-context alignment summary.
3. In `validation_builder.py`, add helpers that compute:
   - expected patient identity values from `normalized_request.patient_context.patient`
   - expected section-entry texts for `medicationrequest-1`, `medicationrequest-2`, `allergyintolerance-1`, and `condition-1`
   - alignment mode for each expected text:
     - `structured_patient_context`
     - `fallback_placeholder`
4. Populate the new validation evidence summary from those helpers.
5. Refactor `bundle.patient_identity_content_present` to check structural presence only.
6. Add `bundle.patient_identity_aligned_to_context` for exact patient-context value matching, gated on structural success.
7. Refactor the existing medication/allergy/condition placeholder content checks so they verify fixed structural fields plus non-empty text only.
8. Add the new text-alignment workflow findings for med1, med2, allergy, and condition, each gated on the matching structural content check.
9. Reuse the existing bounded medication mapping helpers for med1/med2 expected text so the authoritative first-two-item mapping remains the single source of truth.
10. Update `repair_decision_builder.py` so each new alignment finding maps to the existing owning build step and participates in the current step-subset directive flow.
11. Update validation tests for these cases:
    - explicit patient context happy path:
      - no new alignment findings
      - validation evidence shows structured patient-context expectations
    - legacy patient-profile mode:
      - text expectations for section entries show `fallback_placeholder`
      - no structured-alignment finding on happy path
    - wrong patient display name or patient id with fields still present:
      - `bundle.patient_identity_aligned_to_context` only
      - not `bundle.patient_identity_content_present`
    - missing patient gender when normalized context supplied it:
      - `bundle.patient_identity_content_present`
      - alignment finding suppressed
    - wrong med1 text with field present:
      - `bundle.medicationrequest_placeholder_text_aligned_to_context`
      - not `bundle.medicationrequest_placeholder_content_present`
    - wrong med2 text with field present in the two-medication path:
      - `bundle.medicationrequest_2_placeholder_text_aligned_to_context`
    - wrong allergy text with field present:
      - `bundle.allergyintolerance_placeholder_text_aligned_to_context`
    - wrong condition text with field present:
      - `bundle.condition_placeholder_text_aligned_to_context`
    - missing section-entry text field:
      - structural content finding only
      - alignment finding suppressed
    - swapped med1/med2 text with both placeholders present:
      - placeholder-specific med1 and/or med2 alignment findings, while bundle-entry coherence remains a separate concern
12. Update repair-decision tests so the new alignment findings route to:
    - `build-patient-1`
    - `build-medicationrequest-1`
    - `build-medicationrequest-2`
    - `build-allergyintolerance-1`
    - `build-condition-1`
13. Update one or two repair-execution tests only if needed to prove those new alignment findings still trigger the existing narrow resource-construction retry path.
14. Update workflow smoke assertions so Dev UI-visible validation evidence now shows:
    - patient normalization mode
    - expected patient identity values/presence
    - per-placeholder expected text and alignment mode
15. Update README and `docs/development-plan.md` after tests are green.

6. Definition of Done

- The workflow still generates the same bounded set of resources it generates today.
- Workflow validation now explicitly separates:
  - structural/scaffold correctness
  - exact alignment to normalized patient context or fallback placeholder policy
- New alignment findings exist for:
  - Patient identity
  - MedicationRequest med1 text
  - MedicationRequest med2 text when planned
  - AllergyIntolerance text
  - Condition text
- Existing generic content findings remain, but their meaning is narrowed to structural correctness.
- Alignment findings are gated so missing-field faults do not also produce duplicate exact-alignment findings.
- Dev UI can now show a validation-stage patient-context alignment summary with:
  - normalization mode
  - expected patient identity values/presence
  - per-placeholder expected text
  - whether each expected text came from structured patient context or fallback placeholder policy
- Repair ownership remains narrow and unchanged in shape:
  - patient alignment -> `build-patient-1`
  - med1 alignment -> `build-medicationrequest-1`
  - med2 alignment -> `build-medicationrequest-2`
  - allergy alignment -> `build-allergyintolerance-1`
  - condition alignment -> `build-condition-1`
- What remains bounded or deferred:
  - semantic clinical correctness
  - multiplicity expansion beyond the current medications-only path
  - broader patient-context reasoning or graph alignment
  - allergies/problems multiplicity
  - arbitrary-length medication alignment

7. Risks / notes

- The main real risk is duplicate findings after splitting structural and alignment checks. Gating must suppress alignment findings when structural prerequisites already failed.
- A second real risk is creating two sources of truth for expected patient-context values. Validation evidence and validation checks should be derived from the same helper functions.
- A third real risk is over-generalizing the evidence model into a generic clinical alignment engine. Keep it tightly scoped to the current Patient plus trio text fields.
- A fourth real risk is muddying legacy fallback semantics. The validation evidence and finding messages must say explicitly when the expected value came from fallback placeholder policy rather than structured patient-context consumption.

8. Targeted `docs/development-plan.md` updates after implementation

- In Section 8, move `Current Focus` away from patient-context-to-bundle alignment hardening and toward the next bounded follow-on after explicit patient-context alignment validation exists.
- In Section 9, set `Next Planned Slice` to the next narrow decision after this hardening, likely whether medication-specific hardening should continue or whether another bounded patient-context-aware slice is now safer.
- In Section 10, update the phase note to say the workflow now explicitly distinguishes structural bundle correctness from deterministic patient-context alignment for the fields it can honestly populate.
- In Section 12, refine the patient-context assumption to say validation now checks both structural presence and explicit normalized patient-context alignment for Patient identity and current section-entry display text fields.
- In Section 13, replace the current next-risk wording with the new remaining risk: the workflow now hardens deterministic patient-context alignment for current honest fields, but broader semantic clinical correctness and broader multiplicity remain intentionally deferred.
- In Section 16, update the immediate next objective away from patient-context alignment hardening and toward the next bounded post-hardening decision, without broadening multiplicity or introducing semantic clinical reasoning.
