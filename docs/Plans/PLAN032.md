1. Repo assessment

- The repo already has the raw ingredients for end-to-end traceability:
  - stable `placeholder_id`s in schematic, build plan, resource construction, candidate bundle, validation, and repair
  - stable `step_id`s in build planning and resource construction
  - structured normalized patient/provider context with stable upstream ids
  - deterministic value evidence in `resource_construction`
  - deterministic `entry_assembly` in `bundle_finalization`
  - explicit patient/provider alignment evidence in `validation`
- The previous slice improved provider-side correctness and evidence, but it did not solve the main observability gap: lineage is still fragmented across artifacts.
- Today, an engineer can reconstruct “where did this resource come from?” but only by manually correlating:
  - normalized request context
  - schematic placeholders and roles
  - build-plan target placeholder ids
  - resource-construction step results and registry entries
  - candidate-bundle entry assembly
  - validation evidence and finding codes
- The current most useful stable traceability key is the existing `placeholder_id`:
  - it is already present in the schematic
  - it maps directly to build-plan target placeholders
  - it maps directly to registry entries and bundle entry resource ids
  - it already underpins repair targeting
- What is missing for this slice is not more provenance generation. It is one compact, carried-forward summary that makes current provenance easy to follow end to end without reading five separate artifacts.
- Constraints that matter now:
  - no new generation logic
  - no workflow-loop redesign
  - no generic provenance platform
  - no broad schema churn across every stage
  - keep this bounded to current PS-CA placeholders/resources the workflow already builds honestly

2. Proposed slice scope

- Add one compact placeholder-scoped traceability summary keyed by existing `placeholder_id`.
- Carry that summary forward only through the later artifacts where it adds real debugging value:
  - `resource_construction`
  - `candidate_bundle`
  - `validation`
- Do not change:
  - request normalization behavior
  - schematic planning behavior
  - build-plan step behavior
  - resource-construction content behavior
  - bundle-finalization assembly behavior
  - validation decisions or repair routing behavior
- Keep the traceability scope bounded to the current bundle-entry placeholders/resources:
  - `composition-1`
  - `patient-1`
  - `practitionerrole-1`
  - `practitioner-1`
  - `organization-1`
  - `medicationrequest-1`
  - `medicationrequest-2` when present
  - `allergyintolerance-1`
  - `condition-1`

3. Proposed end-to-end traceability / provenance hardening approach

- Recommended traceability unit: one placeholder/resource traceability summary keyed by `placeholder_id`.
- Add one compact shared model, for example `PlaceholderTraceabilitySummary`, with only the fields needed to answer the current debugging questions:
  - `placeholder_id`
  - `resource_type`
  - `role`
  - `section_keys`
  - `driving_inputs`
  - `source_step_ids`
  - `latest_step_id`
  - `bundle_entry_sequence`
  - `bundle_entry_path`
  - `full_url`
  - `workflow_check_codes`
- Keep the “driving inputs” small and structured, not field-exhaustive:
  - derive them from existing deterministic value evidence as deduped `(source_artifact, source_detail)` pairs
  - include fallback provenance honestly when content came from section scaffold + request rather than structured patient/provider context
  - include planned-medication mapping provenance when relevant, so `medicationrequest-1` and `medicationrequest-2` clearly show which normalized medication item drove them
- Carry the same summary forward across stages:
  - `resource_construction.evidence`
    - populate placeholder/resource identity, role, section keys, driving inputs, source step ids, latest step id
    - no bundle-entry or validation fields yet
  - `candidate_bundle.evidence`
    - copy the construction summary by placeholder id
    - add bundle-entry sequence, entry path, and fullUrl
  - `validation.evidence`
    - copy the candidate-bundle summary by placeholder id
    - add applicable workflow check codes for that placeholder/resource
- Keep traceability summary generation deterministic:
  - use schematic placeholders for `role` and `section_keys`
  - use resource-registry/current scaffold `source_step_ids` and `latest_step_id`
  - use candidate `entry_assembly` for bundle placement/fullUrl
  - use a small explicit placeholder-to-workflow-check map in validation for current PS-CA resources only
- Recommended validation linkage:
  - `patient-1` -> patient identity and related subject-reference checks
  - `practitioner-1` -> practitioner identity and practitionerrole practitioner-reference checks
  - `organization-1` -> organization identity and practitionerrole organization-reference checks
  - `practitionerrole-1` -> relationship identity, author-context, and author/reference checks
  - `medicationrequest-1` / `medicationrequest-2` -> placeholder content/alignment/reference checks and medication bundle-entry coherence where relevant
  - `allergyintolerance-1` / `condition-1` -> content/alignment/reference checks
  - `composition-1` -> scaffold, section, subject, and author checks
- What remains intentionally deferred:
  - generic provenance for arbitrary future resources
  - graph rendering or UI visualization features
  - provenance for every individual field in every artifact
  - standards-channel provenance beyond current validator outputs
  - new workflow decisions or new content generation

4. File-level change plan

- Update [models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py)
  - add the compact placeholder traceability models
  - extend `ResourceConstructionEvidence`
  - extend `CandidateBundleEvidence`
- Update [validation/models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/validation/models.py)
  - extend `ValidationEvidence` with the carried-forward placeholder traceability summaries
- Update [resource_construction_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/resource_construction_builder.py)
  - build the initial placeholder traceability summaries from schematic metadata, registry/source step ids, and deterministic value evidence
- Update [bundle_finalization_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/bundle_finalization_builder.py)
  - enrich the carried-forward summaries with entry assembly sequence/path/fullUrl
- Update [validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/validation_builder.py)
  - copy the candidate-bundle traceability summaries into validation evidence
  - add the current placeholder-specific workflow check-code index
- Update tests:
  - [test_psca_resource_construction_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_resource_construction_builder.py)
  - [test_psca_bundle_finalization_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_finalization_builder.py)
  - [test_psca_validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_validation_builder.py)
  - [test_psca_bundle_builder_workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py)
- Update docs:
  - [README.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md)
  - [docs/development-plan.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md)
- No planned code changes for:
  - request normalization
  - schematic builder
  - build-plan builder
  - repair decision
  - repair execution
  - standards validator

5. Step-by-step implementation plan

1. Add the compact traceability models to workflow models, using `placeholder_id` as the stable cross-stage key.
2. Extend `ResourceConstructionEvidence` with a list of placeholder traceability summaries.
3. In `resource_construction_builder.py`, add a helper that builds one summary per current bundle-entry placeholder/resource using:
   - schematic placeholder `role`
   - schematic `section_keys`
   - registry/current scaffold `source_step_ids`
   - registry `latest_step_id`
   - deduped deterministic-value source references from the placeholder’s contributing step results
4. Keep “driving inputs” narrow and deterministic:
   - use existing `DeterministicValueEvidence.source_artifact` and `source_detail`
   - do not invent new reasoning-derived provenance
5. Extend `CandidateBundleEvidence` with the same carried-forward traceability summaries.
6. In `bundle_finalization_builder.py`, enrich each summary with:
   - `bundle_entry_sequence`
   - `bundle_entry_path`
   - `full_url`
   using `entry_assembly`
7. Extend `ValidationEvidence` with the same carried-forward traceability summaries.
8. In `validation_builder.py`, add a small explicit helper that maps current placeholders to applicable workflow finding codes.
9. Populate validation-stage traceability by copying the candidate-bundle summaries and appending those `workflow_check_codes`.
10. Keep current patient/provider alignment evidence unchanged, but let the new placeholder traceability summaries complement it rather than replace it.
11. Update direct tests for `resource_construction`:
    - traceability summary exists for current placeholders
    - practitioner/organization/practitionerrole summaries show provider-context driving inputs
    - medication summary shows authoritative planned-medication mapping provenance
    - fallback placeholders show scaffold/request fallback provenance
12. Update direct tests for `bundle_finalization`:
    - carried-forward traceability summaries include entry sequence/path/fullUrl
    - med2 traceability appears only when the bounded second medication exists
13. Update direct tests for `validation`:
    - traceability summaries are present in validation evidence
    - placeholder-specific workflow check codes are populated deterministically
    - patient/provider alignment evidence still coexists cleanly with the new summary
14. Update workflow smoke assertions so Dev UI-visible outputs show:
    - resource-construction traceability summaries
    - candidate-bundle traceability summaries
    - validation traceability summaries with workflow check codes
15. Update README and development plan after tests are green.

6. Definition of Done

- The workflow still behaves exactly the same functionally.
- A compact placeholder/resource traceability summary now exists and is keyed by stable `placeholder_id`.
- Dev UI can now show, for each current bundle-entry placeholder/resource:
  - what resource it is
  - what role/section it belongs to
  - which normalized or fallback inputs drove it
  - which build/resource-construction step ids produced it
  - where it landed in the candidate bundle
  - which workflow validation checks currently apply to it
- `resource_construction` exposes the initial traceability summary.
- `candidate_bundle` carries that summary forward and adds bundle-entry placement/fullUrl information.
- `validation` carries that summary forward and adds placeholder-specific workflow check codes.
- The traceability summary is deterministic and stable for:
  - patient/support resources
  - bounded med1/med2 resources
  - allergy/problem resources
  - composition
- What remains bounded or deferred:
  - generic provenance for arbitrary future resources
  - field-by-field provenance for every bundle element
  - UI graphing/visualization
  - new generation logic or new multiplicity behavior

7. Risks / notes

- The main real risk is overbuilding a generic provenance framework. Keep the summary explicitly placeholder-scoped and limited to current PS-CA bundle-entry resources.
- A second real risk is duplicating too much existing deterministic value evidence. The new summary should aggregate and point to current evidence, not replace or restate every field-level provenance row.
- A third real risk is inconsistent trace generation across stages. Candidate-bundle and validation summaries should be copied forward from the same placeholder key, not rebuilt from scratch with different rules.
- A fourth real risk is making composition traceability misleading. Composition should show the scaffold/finalize step lineage it actually has today, not imply richer causal reasoning than the workflow currently performs.

8. Targeted `docs/development-plan.md` updates after implementation

- In Section 8, move `Current Focus` away from end-to-end traceability/provenance hardening and toward the next bounded follow-on after cross-stage placeholder traceability is inspectable.
- In Section 9, set `Next Planned Slice` to the next narrow decision after traceability hardening, likely whether another observability/hardening slice is justified or whether the next bounded effort should return to a different workflow area.
- In Section 10, update the phase note to say the workflow now carries a compact placeholder-scoped traceability summary from resource construction through candidate bundle and validation for the current PS-CA bundle-entry resources.
- In Section 12, refine the inspectability assumption to say stable placeholder ids now act as the bounded end-to-end traceability key across normalized context, construction, bundle assembly, and validation.
- In Section 13, replace the current observability risk wording with the next real remaining risk: traceability is now compact and cross-stage for current placeholders/resources, but broader generic provenance and richer future-resource coverage remain intentionally deferred.
- In Section 16, update the immediate next objective away from traceability hardening and toward the next bounded post-hardening decision without widening into generic provenance infrastructure or new generation behavior.
