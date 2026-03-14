1. Repo assessment

- The repo already narrowed Composition required-section repair as far as current section-finalize step boundaries safely allow:
  - `build-composition-1-scaffold`
  - `finalize-composition-1-medications-section`
  - `finalize-composition-1-allergies-section`
  - `finalize-composition-1-problems-section`
- The remaining grouped Composition area is now at the scaffold/content layer, not the section-presence layer:
  - [validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/validation_builder.py) still has:
    - `bundle.composition_type_matches_psca_summary`
    - `bundle.composition_enriched_content_present`
  - `bundle.composition_enriched_content_present` currently groups:
    - `status == "final"`
    - deterministic `title`
  - Composition `subject` and `author` are currently not validated as Composition-owned findings; they are only caught indirectly inside the broad bundle-level rule `bundle.references_aligned_to_entry_fullurls`
- The current build-step boundaries are already sufficient for narrower Composition scaffold/content findings:
  - `build-composition-1-scaffold` owns:
    - `type`
    - `status`
    - `title`
    - `subject.reference`
    - `author[0].reference`
    - empty `section = []`
  - section-finalize steps only own section-block attachment
- The key constraint is execution granularity:
  - a rerun of `build-composition-1-scaffold` alone would wipe attached sections back to `[]`
  - so any executable repair for scaffold-step Composition findings must still rerun:
    - `build-composition-1-scaffold`
    - all three Composition section-finalize steps
- That means this slice can safely narrow findings and repair evidence without splitting build steps further.
- The current grouped bundle reference rule should stay partly grouped, but it should stop owning Composition subject/author problems if this slice introduces Composition-specific subject/author reference findings.
- Tests currently cover:
  - grouped Composition type/content failures
  - section-specific required-section failures
  - repair routing/execution for section-specific finalize steps
- What is missing for this slice:
  - narrower Composition scaffold/content finding codes
  - narrower routing evidence for Composition subject/author problems
  - direct tests proving scaffold-level Composition issues route to `resource_construction` with the existing scaffold-plus-finalizers step subset

2. Proposed slice scope

- Keep `build-composition-1-scaffold` and the three section-finalize steps exactly as they are.
- Do not split build planning or resource construction further in this slice.
- Keep `bundle.composition_type_matches_psca_summary` unchanged:
  - it is already a single-purpose finding
  - splitting it further would not improve execution precision
- Replace the grouped `bundle.composition_enriched_content_present` rule with three narrower Composition scaffold/content rules:
  - `bundle.composition_core_scaffold_content_present`
  - `bundle.composition_subject_reference_aligned`
  - `bundle.composition_author_reference_aligned`
- Narrow the current broad bundle-level reference rule by removing Composition subject/author ownership from it.
- Keep the executable repair target unchanged:
  - still `resource_construction`
- For the new Composition scaffold/content findings, executable repair should use the existing step subset:
  - `build-composition-1-scaffold`
  - `finalize-composition-1-medications-section`
  - `finalize-composition-1-allergies-section`
  - `finalize-composition-1-problems-section`
- What remains intentionally grouped or deferred after this slice:
  - `bundle.references_aligned_to_entry_fullurls` for non-Composition reference alignment
  - Composition section-entry fullUrl alignment inside section blocks
  - any element-level Composition patching
  - any further split of `build-composition-1-scaffold`

3. Proposed narrower Composition scaffold/content validation / repair approach

- Validation split:
  - keep `bundle.composition_type_matches_psca_summary`
    - checks `type.coding[0].system` and `type.coding[0].code`
    - still routes to `resource_construction`
  - replace `bundle.composition_enriched_content_present` with:
    - `bundle.composition_core_scaffold_content_present`
      - checks `status == "final"`
      - checks non-empty deterministic `title`
    - `bundle.composition_subject_reference_aligned`
      - checks `Composition.subject.reference` matches the patient bundle entry fullUrl
    - `bundle.composition_author_reference_aligned`
      - checks `Composition.author[0].reference` matches the practitioner-role bundle entry fullUrl
- Reason for this split:
  - `status`/`title` are deterministic scaffold content
  - `subject`/`author` are also scaffold-owned, but today they are obscured inside a bundle-level grouped alignment rule
  - splitting them improves inspectability and repair routing honesty without needing new build steps
- Repair mapping:
  - all four scaffold-owned Composition findings map to the same existing step subset:
    - `bundle.composition_type_matches_psca_summary`
    - `bundle.composition_core_scaffold_content_present`
    - `bundle.composition_subject_reference_aligned`
    - `bundle.composition_author_reference_aligned`
    - all map to:
      - `build-composition-1-scaffold`
      - `finalize-composition-1-medications-section`
      - `finalize-composition-1-allergies-section`
      - `finalize-composition-1-problems-section`
    - placeholder ids:
      - `["composition-1"]`
- Why execution does not narrow further:
  - current repo maturity supports narrower findings
  - current repo does not safely support rerunning only the scaffold step, because that would remove sections until the finalize steps are replayed
  - splitting the scaffold step further would be a larger refactor than this slice needs
- Adjust `bundle.references_aligned_to_entry_fullurls` so it no longer checks:
  - `Composition.subject`
  - `Composition.author[0]`
- Keep `bundle.references_aligned_to_entry_fullurls` for:
  - `PractitionerRole.practitioner`
  - `PractitionerRole.organization`
  - section-entry patient/subject references
  - Composition section-entry references
- Naming intent:
  - these new rules validate deterministic scaffold content and deterministic reference alignment in the generated candidate bundle
  - they do not claim semantic clinical correctness

4. File-level change plan

- Update [validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/validation_builder.py)
  - replace `bundle.composition_enriched_content_present`
  - add the three new Composition scaffold/content checks
  - narrow `bundle.references_aligned_to_entry_fullurls` to exclude Composition subject/author
- Update [repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/repair_decision_builder.py)
  - add the three new codes to `_FINDING_ROUTE_MAP`
  - map them to the existing scaffold-plus-finalizers step subset in `_RESOURCE_CONSTRUCTION_DIRECTIVE_MAP`
  - remove the old `bundle.composition_enriched_content_present` mapping
- Update tests:
  - [test_psca_validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_validation_builder.py)
  - [test_psca_repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_repair_decision_builder.py)
  - [test_psca_repair_execution_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_repair_execution_builder.py)
  - [test_psca_bundle_builder_workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py) only if the checks list or visible output assertions need updating
- Update docs:
  - [README.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md)
  - [docs/development-plan.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md)
- No build-plan changes.
- No model changes required unless implementation reveals a missing inspectability field.

5. Step-by-step implementation plan

1. Update workflow validation:
   - remove `bundle.composition_enriched_content_present` from `checks_run`
   - add:
     - `bundle.composition_core_scaffold_content_present`
     - `bundle.composition_subject_reference_aligned`
     - `bundle.composition_author_reference_aligned`
2. Implement a small helper for Composition scaffold core content:
   - verify `status == "final"`
   - verify non-empty `title`
3. Implement small helpers for Composition subject/author alignment:
   - resolve expected bundle fullUrls by placeholder id
   - compare `subject.reference` to the patient fullUrl
   - compare `author[0].reference` to the practitioner-role fullUrl
4. Narrow `_references_aligned_to_entry_fullurls(...)`:
   - remove Composition subject/author checks from that grouped rule
   - leave the remaining non-Composition and section-entry alignment checks intact
5. Update repair routing:
   - add new Composition scaffold/content codes to `_FINDING_ROUTE_MAP`
   - add new directive mappings to `_RESOURCE_CONSTRUCTION_DIRECTIVE_MAP`
   - all new Composition scaffold/content codes should map to the existing scaffold-plus-three-finalizers step subset
6. Keep `bundle.composition_type_matches_psca_summary` unchanged except for any rationale text needed to clarify that rerunning the scaffold also requires replaying finalize steps.
7. Update validation tests:
   - missing `title` only -> `bundle.composition_core_scaffold_content_present` only
   - missing `subject.reference` only -> `bundle.composition_subject_reference_aligned` only
   - missing `author[0].reference` only -> `bundle.composition_author_reference_aligned` only
   - wrong `type` still -> `bundle.composition_type_matches_psca_summary`
   - subject/author-only failures should no longer rely on `bundle.references_aligned_to_entry_fullurls`
8. Update repair-decision tests:
   - `title` failure routes to `resource_construction`
   - `subject` failure routes to `resource_construction`
   - `author` failure routes to `resource_construction`
   - each yields the same scaffold-plus-finalizers step subset
   - combined scaffold-content failures dedupe to that same step subset once
9. Update repair-execution tests:
   - break only Composition `title`, assert rerun step ids are:
     - `build-composition-1-scaffold`
     - `finalize-composition-1-medications-section`
     - `finalize-composition-1-allergies-section`
     - `finalize-composition-1-problems-section`
   - break only `subject.reference`, assert the same rerun set
   - confirm `execution_scope == "targeted_repair"` remains unchanged
10. Update smoke/docs assertions only enough to reflect the new visible Composition scaffold/content finding names and the improved routing explanation.
11. Re-run the test suite and confirm no stale references to `bundle.composition_enriched_content_present` remain.

6. Definition of Done

- `bundle.composition_enriched_content_present` is no longer emitted.
- Workflow validation now emits:
  - `bundle.composition_core_scaffold_content_present`
  - `bundle.composition_subject_reference_aligned`
  - `bundle.composition_author_reference_aligned`
- `bundle.composition_type_matches_psca_summary` remains in place unchanged.
- Composition subject/author problems are no longer owned only by the grouped bundle reference-alignment rule.
- `repair_decision` maps the new Composition scaffold/content codes to `resource_construction`.
- Executable repair for the new Composition scaffold/content findings uses the existing safe step subset:
  - `build-composition-1-scaffold`
  - all three Composition section-finalize steps
- Dev UI now shows:
  - narrower Composition scaffold/content findings
  - clearer repair-routing evidence for title vs subject vs author problems
  - the same bounded targeted retry behavior, with the scaffold-plus-finalizers step subset when those findings occur
- What still remains grouped or deferred:
  - non-Composition bundle reference alignment
  - Composition section-entry fullUrl alignment
  - any further split of the scaffold step itself
  - generic Composition/data-element repair behavior

7. Risks / notes

- The main real risk is overpromising execution precision. The new findings can narrow safely, but executable repair for scaffold-step Composition issues still has to replay all section-finalize steps.
- Another real risk is duplicate findings if Composition subject/author checks are added without removing them from the grouped bundle reference rule.
- A smaller risk is naming drift. The new codes should describe deterministic scaffold content or deterministic reference alignment, not semantic document validity.
- This slice should not split `build-composition-1-scaffold`; the current repo does not need that refactor yet.

8. Targeted `docs/development-plan.md` updates after implementation

- In Section 8, change `Current Focus` from narrower Composition scaffold/content validation/repair to the next bounded realism or remaining grouped-validation slice.
- In Section 9, replace `Next Planned Slice` with a bounded follow-on such as: “Deepen Organization/provider-role realism or narrow the remaining grouped non-Composition reference-alignment validation.”
- In Section 10, update the Phase 8 note to say Composition scaffold/content validation now distinguishes core scaffold content and subject/author reference alignment, while executable repair still reuses the existing scaffold-plus-finalizers subset.
- In Section 12, refine the Composition assumption to say the current repo supports narrower Composition scaffold/content findings without further splitting the existing scaffold build step.
- In Section 13, replace the current grouped Composition scaffold/content risk with the next real remaining risk: scaffold-step Composition issues still share one executable repair subset because the scaffold step remains intentionally unsplit.
- In Section 16, update the immediate next objective away from Composition scaffold/content narrowing and toward the next narrow realism or remaining grouped-validation slice.
