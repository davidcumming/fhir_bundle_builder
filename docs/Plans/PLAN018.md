1. Repo assessment

- The remaining grouped reference-alignment rule is still [validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/validation_builder.py): `bundle.references_aligned_to_entry_fullurls`.
- After the Composition scaffold/content split, that rule now appears to cover three different ownership patterns:
  - `PractitionerRole.practitioner` and `PractitionerRole.organization`
  - `MedicationRequest.subject`, `AllergyIntolerance.patient`, and `Condition.subject`
  - Composition section-entry references inside `section[x].entry[0].reference`
- The current resource-construction step boundaries are already separate for the non-Composition cases:
  - `build-practitionerrole-1`
  - `build-medicationrequest-1`
  - `build-allergyintolerance-1`
  - `build-condition-1`
- But the current validation rule is specifically about final `entry.fullUrl` alignment in the assembled candidate bundle, and that final rewrite is performed in [bundle_finalization_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/bundle_finalization_builder.py), not in resource construction.
- The current repair routing in [repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/repair_decision_builder.py) still sends the entire grouped rule to `bundle_finalization`.
- Current repo maturity supports narrower findings safely, but not narrower executable repair for these alignment cases:
  - the smallest honest executable stage remains `bundle_finalization`
  - no current artifact distinguishes “wrong local reference contribution” from “wrong final fullUrl rewrite”
- Current tests already prove:
  - grouped reference alignment routes to `bundle_finalization`
  - Composition subject/author were already split out of the grouped rule in the previous slice
- What is missing for this slice:
  - resource-specific non-Composition alignment finding codes
  - narrower routing evidence for those codes
  - a clearer residual grouped rule for Composition section-entry reference alignment, if retained

2. Proposed slice scope

- Replace the broad non-Composition portion of `bundle.references_aligned_to_entry_fullurls` with five narrower workflow findings:
  - `bundle.practitionerrole_practitioner_reference_aligned`
  - `bundle.practitionerrole_organization_reference_aligned`
  - `bundle.medicationrequest_subject_reference_aligned`
  - `bundle.allergyintolerance_patient_reference_aligned`
  - `bundle.condition_subject_reference_aligned`
- Remove those five cases from the current grouped rule.
- Keep Composition section-entry fullUrl alignment intentionally grouped for now under one new honest residual rule:
  - `bundle.composition_section_entry_references_aligned`
- Remove `bundle.references_aligned_to_entry_fullurls` entirely rather than leaving a misleading code name for a smaller residual scope.
- Keep repair target/execution unchanged for all of these new alignment findings:
  - route to `bundle_finalization`
  - no new `resource_construction` directive mapping
- No build-step split.
- No resource-construction refactor.
- No bundle-finalization redesign.

3. Proposed narrower non-Composition reference-alignment / repair approach

- Validation split:
  - `bundle.practitionerrole_practitioner_reference_aligned`
    - checks `PractitionerRole.practitioner.reference == fullUrl(practitioner-1)`
  - `bundle.practitionerrole_organization_reference_aligned`
    - checks `PractitionerRole.organization.reference == fullUrl(organization-1)`
  - `bundle.medicationrequest_subject_reference_aligned`
    - checks `MedicationRequest.subject.reference == fullUrl(patient-1)`
  - `bundle.allergyintolerance_patient_reference_aligned`
    - checks `AllergyIntolerance.patient.reference == fullUrl(patient-1)`
  - `bundle.condition_subject_reference_aligned`
    - checks `Condition.subject.reference == fullUrl(patient-1)`
- Residual grouped rule to keep for now:
  - `bundle.composition_section_entry_references_aligned`
    - checks each required Composition section entry reference aligns to the expected entry fullUrl for:
      - medications
      - allergies
      - problems
- Ownership/routing decision:
  - all five new non-Composition alignment findings should still route to `bundle_finalization`
  - the residual grouped Composition section-entry alignment finding should also route to `bundle_finalization`
- Reason:
  - the validation is about final candidate-bundle fullUrl alignment
  - current repo does not separate “resource constructed the wrong placeholder target/path” from “bundle finalization rewrote the final reference incorrectly”
  - the smallest honest executable repair layer is therefore still `bundle_finalization`
- Important implementation guard:
  - if the bundle’s `entry.fullUrl` set is incomplete or unreadable, the new specific alignment helpers should not all cascade into extra findings
  - in those cases, let `bundle.entry_fullurls_present` or `bundle.required_entries_present` own the failure
- What remains intentionally grouped after this slice:
  - Composition section-entry exact fullUrl alignment
  - any deeper distinction between local reference contribution generation vs final fullUrl rewrite
  - any generic reference-graph or element-level engine

4. File-level change plan

- Update [validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/validation_builder.py)
  - replace the current grouped non-Composition alignment logic with five specific checks
  - add one residual grouped Composition section-entry alignment check
  - update `checks_run`
- Update [repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/repair_decision_builder.py)
  - remove `bundle.references_aligned_to_entry_fullurls`
  - add the five new non-Composition codes plus the residual Composition section-entry code to `_FINDING_ROUTE_MAP`
  - route all of them to `bundle_finalization`
  - do not add them to `_RESOURCE_CONSTRUCTION_DIRECTIVE_MAP`
- Update tests:
  - [test_psca_validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_validation_builder.py)
  - [test_psca_repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_repair_decision_builder.py)
  - [test_psca_repair_execution_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_repair_execution_builder.py)
  - [test_psca_bundle_builder_workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py) only if visible checks/finding assertions need it
- Update docs:
  - [README.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md)
  - [docs/development-plan.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md)

5. Step-by-step implementation plan

1. Refactor workflow validation so the old grouped code is removed from `checks_run`.
2. Add a reusable helper that resolves expected bundle `fullUrl`s by placeholder id and returns “not assessable” cleanly when entry fullUrls are missing.
3. Implement five narrow non-Composition alignment helpers:
   - PractitionerRole practitioner
   - PractitionerRole organization
   - MedicationRequest subject
   - AllergyIntolerance patient
   - Condition subject
4. Add one residual grouped helper for Composition section-entry exact fullUrl alignment.
5. Replace the old grouped finding emission with:
   - five resource-specific non-Composition findings
   - one residual grouped Composition section-entry finding
6. Update repair routing:
   - remove `bundle.references_aligned_to_entry_fullurls` from `_FINDING_ROUTE_MAP`
   - add the six new codes
   - route all six to `bundle_finalization`
   - keep `recommended_next_stage = "bundle_finalization"`
   - leave `_RESOURCE_CONSTRUCTION_DIRECTIVE_MAP` unchanged
7. Update validation tests:
   - PractitionerRole practitioner misaligned -> only `bundle.practitionerrole_practitioner_reference_aligned`
   - PractitionerRole organization misaligned -> only `bundle.practitionerrole_organization_reference_aligned`
   - MedicationRequest subject misaligned -> only `bundle.medicationrequest_subject_reference_aligned`
   - AllergyIntolerance patient misaligned -> only `bundle.allergyintolerance_patient_reference_aligned`
   - Condition subject misaligned -> only `bundle.condition_subject_reference_aligned`
   - Composition section-entry misalignment -> only `bundle.composition_section_entry_references_aligned`
   - missing `fullUrl` should still be owned primarily by `bundle.entry_fullurls_present`, without spraying all five new specific findings
8. Update repair-decision tests:
   - each new non-Composition alignment code routes to `bundle_finalization`
   - combined non-Composition alignment failures still recommend `bundle_finalization`
   - residual Composition section-entry alignment failure also routes to `bundle_finalization`
9. Update repair-execution tests:
   - break one PractitionerRole or section-entry-patient reference in the candidate bundle
   - assert `repair_execution` reruns only the existing bundle-finalization retry path
   - no `resource_construction` directive is applied
10. Update README and development plan wording to reflect:
   - narrower non-Composition alignment findings
   - unchanged bundle-finalization ownership for executable repair
   - remaining grouped Composition section-entry alignment
11. Run the test suite and confirm no stale references to `bundle.references_aligned_to_entry_fullurls` remain.

6. Definition of Done

- `bundle.references_aligned_to_entry_fullurls` is no longer emitted.
- Workflow validation now emits:
  - `bundle.practitionerrole_practitioner_reference_aligned`
  - `bundle.practitionerrole_organization_reference_aligned`
  - `bundle.medicationrequest_subject_reference_aligned`
  - `bundle.allergyintolerance_patient_reference_aligned`
  - `bundle.condition_subject_reference_aligned`
  - `bundle.composition_section_entry_references_aligned`
- The five non-Composition alignment cases are now individually inspectable in Dev UI.
- `repair_decision` routes each of those five new non-Composition findings to `bundle_finalization`.
- Executable repair does not become more granular for these cases:
  - the path remains the existing `bundle_finalization -> validation -> repair_decision` retry
- The residual grouped area after this slice is explicit and honest:
  - Composition section-entry exact fullUrl alignment remains grouped
- No new build steps, no new directive model, and no orchestration changes are introduced.

7. Risks / notes

- The main real risk is overclaiming executable precision. These new findings can narrow safely, but the executable repair layer remains `bundle_finalization`.
- Another real risk is cascading noisy findings when `entry.fullUrl` generation itself is broken. The new specific helpers should short-circuit when expected fullUrls are unavailable.
- A third risk is misrouting these findings to `resource_construction`. Current repo maturity does not support proving whether the fault is in reference contribution generation or final rewrite, so `bundle_finalization` remains the honest target.
- Composition section-entry alignment should stay grouped in this slice to avoid mixing two scope changes at once.

8. Targeted `docs/development-plan.md` updates after implementation

- In Section 8, change `Current Focus` from narrower non-Composition reference-alignment validation to the next bounded realism or remaining grouped-validation slice.
- In Section 9, replace `Next Planned Slice` with a bounded follow-on such as: “Deepen Organization/provider-role realism or narrow the remaining grouped Composition section-entry exact fullUrl alignment.”
- In Section 10, update the Phase 8 note to say non-Composition reference-alignment validation is now resource-specific, while executable repair still remains bundle-finalization-owned.
- In Section 12, refine the current assumption to say non-Composition reference-alignment findings can narrow safely without changing the current executable repair boundary.
- In Section 13, replace the current risk with the next real one: exact reference-alignment findings are narrower, but current repo maturity still cannot distinguish bad source reference contributions from bad final fullUrl rewrite, so those failures remain bundle-finalization-owned.
- In Section 16, update the immediate next objective away from non-Composition reference-alignment narrowing and toward the next narrow realism or remaining grouped-reference slice.
