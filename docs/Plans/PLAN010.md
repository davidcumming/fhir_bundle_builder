## 1. Repo assessment

- The workflow is now structurally complete through bounded retry execution, but the actual candidate bundle content is still mostly scaffold-level.
- The main content gap is in [resource_construction_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/resource_construction_builder.py):
  - `Patient`, `Practitioner`, and `Organization` are still base metadata only
  - `Composition` has type/subject/author/sections, but still defers `status`, `title`, and `date`
  - section-entry resources (`MedicationRequest`, `AllergyIntolerance`, `Condition`) only carry subject/patient references plus base metadata
- The current `NormalizedBuildRequest` is thin but still useful for deterministic enrichment:
  - `patient_profile.profile_id`
  - `patient_profile.display_name`
  - `provider_profile.profile_id`
  - `provider_profile.display_name`
  - `request.bundle_intent`
  - `request.scenario_label`
  - `request.request_text` exists, but should not be parsed for this slice
- The normalized PS-CA assets are also thin, but the schematic already materializes the parts that matter now:
  - section titles and LOINC codes
  - expected Composition summary type
  - selected section-entry resource types
  - profile URLs
- The current bundle-finalization layer intentionally still defers `Bundle.identifier`, `Bundle.timestamp`, and `entry.fullUrl`, and validation explicitly treats that as expected. There is no stable deterministic bundle-level policy in the repo yet, so bundle-level enrichment should stay out of scope for this slice.
- The current validation and repair layers are ready to absorb a small content-enrichment expansion:
  - validation already checks bundle structure and Composition sections
  - repair routing already supports `resource_construction` as a target
  - repair execution still does not support `resource_construction`, which is acceptable for this slice
- The key constraint now is to improve end-to-end usefulness without inventing a generic field-population engine or parsing free text.

## 2. Proposed slice scope

- Recommend enriching:
  - `Composition`
  - `Patient`
  - all three current section-entry resources:
    - `MedicationRequest`
    - `AllergyIntolerance`
    - `Condition`
- Recommend not enriching in this slice:
  - `Practitioner`
  - `Organization`
  - `PractitionerRole`
  - bundle-level deferred fields (`identifier`, `timestamp`, `entry.fullUrl`)
- Reason for that boundary:
  - `Composition`, `Patient`, and the three section-entry resources are already the most user-visible clinical core of the current PS-CA candidate bundle
  - they can be enriched from existing structured inputs without inventing provider/org semantics or bundle identity policy
  - support-resource enrichment is possible later, but current provider input does not cleanly distinguish practitioner vs organization data
- Recommended deterministic fields for this slice:
  - `Composition`
    - `status = "final"`
    - `title = "{bundle_intent} - {scenario_label}"`
    - keep `date` deferred
    - add section code `display` from `SectionScaffold.title`
  - `Patient`
    - `active = true`
    - `identifier[0].value = patient_profile.profile_id`
    - `name[0].text = patient_profile.display_name`
    - keep `gender` and `birthDate` deferred
  - `MedicationRequest`
    - `status = "draft"`
    - `intent = "proposal"`
    - `medicationCodeableConcept.text = "{section title} placeholder for {scenario_label}"`
  - `AllergyIntolerance`
    - `clinicalStatus.coding[0] = allergyintolerance-clinical|active`
    - `verificationStatus.coding[0] = allergyintolerance-verification|unconfirmed`
    - `code.text = "{section title} placeholder for {scenario_label}"`
  - `Condition`
    - `clinicalStatus.coding[0] = condition-clinical|active`
    - `verificationStatus.coding[0] = condition-ver-status|provisional`
    - `code.text = "{section title} placeholder for {scenario_label}"`
- Keep intentionally deferred after this slice:
  - `Composition.date`
  - bundle identifier/timestamp/fullUrl policy
  - practitioner / organization / practitioner role content
  - full demographic population
  - terminology-rich coding beyond the small fixed status systems/codes above
  - parsing or interpreting `request_text`

## 3. Proposed content-enrichment approach

- Keep the enrichment inside `resource_construction`; do not add a new workflow stage.
- Change the construction boundary from scaffold-only to deterministic content-enriched scaffolds:
  - update `WorkflowDefaults.resource_construction_mode`
  - update `ResourceConstructionMode`
- Change the construction builder signature to accept the normalized request:
  - `build_psca_resource_construction_result(plan, schematic, normalized_request)`
- Do not add a direct `SpecificationAssetContext` dependency to resource construction in this slice.
  - The useful normalized-asset hints already needed here are already materialized into the schematic.
  - That keeps the enrichment boundary tight and avoids a redundant builder dependency.
- Add a small typed provenance model for enriched values, for example:
  - `DeterministicValueEvidence`
    - `target_path`
    - `source_artifact`
    - `source_detail`
  - attach it to `ResourceConstructionStepResult`
- Use a tiny local deterministic content policy inside `resource_construction_builder.py`, not a new generic engine:
  - derive patient label/id from `NormalizedBuildRequest`
  - derive Composition title from `bundle_intent` + `scenario_label`
  - derive section-entry placeholder text from `SectionScaffold.title` + `scenario_label`
  - derive fixed status codes from local constants
- Update `build_plan_builder.py` so the steps that now consume `NormalizedBuildRequest` declare that explicitly in `expected_inputs`:
  - `build-composition-1-scaffold`
  - `build-medicationrequest-1`
  - `build-allergyintolerance-1`
  - `build-condition-1`
- Update validation only where it protects the new enriched value:
  - add deterministic workflow checks for:
    - Composition core content present
    - Patient identity content present
    - section-entry content fields present
  - keep the checks grouped and narrow
  - route any failures from those new codes to `resource_construction` in `repair_decision_builder.py`
- Leave `bundle_finalization_builder.py` unchanged unless a tiny display-path update is needed in tests; it already copies the latest enriched resource scaffolds forward.

## 4. File-level change plan

- Update [src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py)
  - add the deterministic field-value provenance model
  - attach it to `ResourceConstructionStepResult`
  - update construction mode literals/default naming
- Update [src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/resource_construction_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/resource_construction_builder.py)
  - accept `NormalizedBuildRequest`
  - add narrow per-resource enrichment logic
  - emit populated paths, deferred paths, and deterministic value provenance for enriched fields
- Update [src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/executors.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/executors.py)
  - pass `normalized_request` into resource construction
  - update normalization defaults for the new construction mode string
- Update [src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/build_plan_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/build_plan_builder.py)
  - align expected inputs with the new deterministic enrichment dependencies
- Update [src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/validation_builder.py)
  - add narrow enriched-content workflow checks
- Update [src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/repair_decision_builder.py)
  - route the new enriched-content validation codes to `resource_construction`
- Update tests:
  - [tests/test_psca_resource_construction_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_resource_construction_builder.py)
  - [tests/test_psca_validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_validation_builder.py)
  - [tests/test_psca_repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_repair_decision_builder.py)
  - [tests/test_psca_bundle_builder_workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py)
- Update [README.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md) and [docs/development-plan.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md)

## 5. Step-by-step implementation plan

1. Update the workflow and construction model contract first:
   - add deterministic value provenance
   - rename the construction mode away from scaffold-only
2. Refactor the resource construction builder interface to accept `normalized_request`.
3. Implement a tiny internal enrichment policy in the builder with fixed helpers for:
   - Composition
   - Patient
   - MedicationRequest
   - AllergyIntolerance
   - Condition
4. Apply exact deterministic enrichment values:
   - Composition `status`, `title`, section code `display`
   - Patient `active`, `identifier[0].value`, `name[0].text`
   - MedicationRequest `status`, `intent`, `medicationCodeableConcept.text`
   - AllergyIntolerance `clinicalStatus`, `verificationStatus`, `code.text`
   - Condition `clinicalStatus`, `verificationStatus`, `code.text`
5. Reduce deferred paths only for the fields actually populated in this slice.
6. Record per-field provenance for enriched paths using the new step-result evidence field.
7. Update the build-plan expected-input metadata so it matches the real runtime inputs for enriched steps.
8. Add workflow validation checks for the new content:
   - Composition enriched fields present
   - Patient enriched identity fields present
   - section-entry enriched content fields present
9. Add repair-routing map entries for those new validation codes to `resource_construction`.
10. Update tests:
   - resource construction unit test:
     - assert enriched field values for Composition, Patient, MedicationRequest, AllergyIntolerance, and Condition
     - assert reduced deferred paths
     - assert deterministic value provenance entries
   - validation unit test:
     - happy path still yields `passed_with_warnings`
     - mutated Composition title or Patient name causes workflow validation failure
     - mutated section-entry content causes workflow validation failure
   - repair decision unit test:
     - new enriched-content validation code routes to `resource_construction`
   - workflow smoke test:
     - assert new construction mode
     - assert candidate bundle contains the enriched fields
     - assert validation/repair still land on the same happy-path outcome
11. Update README and development-plan text after tests are green.

## 6. Definition of Done

- The candidate bundle is materially more useful than the current scaffold-only output.
- `resource_construction` now produces content-enriched scaffolds for:
  - `Composition`
  - `Patient`
  - `MedicationRequest`
  - `AllergyIntolerance`
  - `Condition`
- The enriched scaffolds clearly show:
  - newly populated deterministic fields
  - reduced deferred paths
  - explicit provenance for enriched values
- The final candidate bundle in Dev UI visibly includes:
  - `Composition.status = final`
  - a deterministic Composition title
  - a Patient identifier and human-readable name
  - placeholder clinical content text/status fields in the three section-entry resources
- Validation still runs and now protects the enriched content with deterministic workflow checks.
- Repair routing still works and routes enriched-content failures to `resource_construction`.
- What remains intentionally deferred:
  - `Bundle.identifier`
  - `Bundle.timestamp`
  - `Bundle.entry.fullUrl`
  - `Composition.date`
  - practitioner / organization / practitioner role content enrichment
  - generic data-element construction
  - parsing clinical meaning from `request_text`

## 7. Risks / notes

- The main risk is over-claiming realism. The enriched section-entry content must stay explicitly placeholder-oriented and deterministic, not pretend to be clinically sourced data.
- The second risk is accidentally widening into bundle-level identity policy. The repo still intentionally treats bundle identifier/timestamp/fullUrl as deferred, and this slice should not reopen that policy surface.
- The third real risk is adding too many validation codes. Keep the new checks few and high-signal so repair routing remains stable and understandable.
- The current provider input is not rich enough to support a clean author/support enrichment slice yet. That is why Practitioner/Organization/PractitionerRole should stay out of scope here.

## 8. Targeted `docs/development-plan.md` updates after implementation

- In Section 8, change `Current Focus` from the first narrow end-to-end PS-CA quality slice to the next bounded content-quality slice that deepens supporting author/provider content or bundle identity policy without broadening into a generic engine.
- In Section 9, replace `Next Planned Slice` with a bounded follow-on such as: “Implement the next narrow deterministic content-enrichment slice for supporting author resources and any stable bundle-level identity/fullUrl policy.”
- In Section 10, keep `Phase 8: Minimal End-to-End PS-CA Workflow` as `In Progress`.
- In Section 10, add a short Phase 8 note that the workflow now produces the first meaningfully content-enriched PS-CA candidate bundle path for Composition, Patient, and section-entry resources.
- In Section 12, add or refine the assumption that the first meaningful content slice uses deterministic placeholder content from normalized request labels and schematic section metadata rather than free-text clinical synthesis.
- In Section 13, add one concise risk only if it is observed during implementation: deterministic placeholder clinical text may still be too synthetic for later quality goals and may require a follow-on profile-backed context slice.
- In Section 16, update the immediate next objective to point at expanding end-to-end content quality in a narrow way rather than broadening workflow orchestration.
