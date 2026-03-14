## 1. Repo assessment

- The bundle-finalization stage in [bundle_finalization_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/bundle_finalization_builder.py) already assembles a real `Bundle` scaffold, but it still intentionally defers:
  - `Bundle.identifier`
  - `Bundle.timestamp`
  - `Bundle.entry.fullUrl`
- The current candidate bundle policy is:
  - `Bundle.id = f"{package_id}-{scenario_label}"`
  - `Bundle.meta.profile[0]` from `bundle_schematic.bundle_scaffold.profile_url`
  - `Bundle.type` from `bundle_schematic.bundle_scaffold.bundle_type`
  - `entry[i].resource` copied directly from the latest registry scaffolds
  - `candidate_bundle.deferred_paths == ["identifier", "timestamp", "entry.fullUrl"]`
- The current resources still use deterministic relative local references such as:
  - `Patient/patient-1`
  - `PractitionerRole/practitionerrole-1`
  - `MedicationRequest/medicationrequest-1`
- The repo already has the information needed to make this slice deterministic:
  - `NormalizedBuildRequest.specification.package_id`
  - `NormalizedBuildRequest.specification.version`
  - `NormalizedBuildRequest.request.scenario_label`
  - `NormalizedBuildRequest.run_label`
  - ordered bundle entry placeholder ids from the schematic
  - deterministic reference provenance from `ResourceConstructionStepResult.reference_contributions`
  - `ResourceScaffoldArtifact.source_step_ids` to reconstruct the full reference set for a finalized resource like `Composition`
- Validation currently does not validate populated bundle identity fields; it only checks that their deferral is explicitly recorded via `bundle.deferred_fields_recorded`.
- Repair routing already maps bundle-shape issues to `bundle_finalization`, which is the correct repair layer for this slice too.
- The main constraint now is to add bundle identity realism without introducing persistence, publication URLs, or a broad lifecycle model.

## 2. Proposed slice scope

- Populate all three currently deferred bundle identity fields in `bundle_finalization`:
  - `Bundle.identifier`
  - `Bundle.timestamp`
  - `Bundle.entry.fullUrl`
- Keep the scope narrow:
  - do not change upstream `resource_construction` scaffolds
  - do not introduce persistence or server/public URLs
  - do not add generic identity engines
- Recommended exact policy boundary:
  - keep `Bundle.id` exactly as it is today
  - add a deterministic local candidate-bundle identifier beside it
  - generate deterministic `urn:uuid:` `entry.fullUrl` values
  - rewrite internal references only in the assembled candidate bundle copy so they align to those `fullUrl`s
- Reason for aligning internal references in this slice:
  - the repo already records deterministic reference paths via `reference_contributions`
  - aligning references at finalization keeps the policy coherent without widening `resource_construction`
  - leaving references relative while adding `fullUrl`s would preserve an avoidable inconsistency in the assembled bundle

## 3. Proposed bundle identity / timestamp / fullUrl approach

- Keep all policy logic inside `bundle_finalization_builder.py`.
- Reuse the existing `DeterministicValueEvidence` model for bundle-level provenance rather than inventing a second provenance shape.
- Recommended exact deterministic value formation:
  - `Bundle.id`
    - keep current policy: `f"{package_id}-{scenario_label}"`
  - `Bundle.identifier.system`
    - fixed local URI-like policy string: `urn:fhir-bundle-builder:candidate-bundle-identifier`
  - `Bundle.identifier.value`
    - deterministic UUIDv5 string derived from:
      - `package_id`
      - `version`
      - `scenario_label`
    - recommended seed string:
      - `urn:fhir-bundle-builder:candidate-bundle:{package_id}:{version}:{scenario_label}`
  - `Bundle.timestamp`
    - deterministic synthetic instant derived from the same bundle UUID seed
    - recommended policy:
      - fixed epoch: `2025-01-01T00:00:00Z`
      - offset seconds: first 8 hex chars of the bundle UUID interpreted as int, modulo one calendar year in seconds
      - render as UTC FHIR instant with trailing `Z`
    - this keeps identical inputs stable while avoiding a fake “current wall-clock” claim
  - `entry.fullUrl`
    - `urn:uuid:{uuid5(bundle_uuid, placeholder_id)}`
    - one deterministic fullUrl per placeholder id
- Reference alignment policy:
  - assembled candidate bundle resources should have reference fields rewritten from current relative values to the matching `entry.fullUrl`
  - do this only in the deep-copied resources inside `candidate_bundle.fhir_bundle`
  - leave upstream registry scaffolds unchanged
- Recommended implementation mechanism for reference rewriting:
  - build a `full_url_by_placeholder_id` map during bundle assembly
  - for each registry entry, aggregate `reference_contributions` across all `source_step_ids` that contributed to its current scaffold
  - rewrite each contributed `reference_path` in the deep-copied resource to the target placeholder’s `fullUrl`
  - if a contributed target placeholder has no `fullUrl`, raise `ValueError`
- Artifact/model changes:
  - add `full_url: str` to `BundleEntryAssemblyResult`
  - add `deterministic_value_evidence: list[DeterministicValueEvidence]` to `CandidateBundleArtifact`
- Validation changes:
  - remove the current “bundle identity fields are deferred” expectation
  - add deterministic checks:
    - `bundle.identifier_present`
    - `bundle.timestamp_present`
    - `bundle.entry_fullurls_present`
    - `bundle.references_aligned_to_entry_fullurls`
  - the local standards validator should also add narrow shape checks for:
    - `Bundle.identifier`
    - `Bundle.timestamp`
    - `entry.fullUrl`
- Repair routing changes:
  - new bundle identity/fullUrl findings should map to `bundle_finalization`
- What remains intentionally deferred after this slice:
  - persistent cross-run business identity
  - public/canonical URLs
  - publication/transport semantics
  - arbitrary-IG bundle identity policy

## 4. File-level change plan

- Update [bundle_finalization_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/bundle_finalization_builder.py)
  - add the deterministic identifier/timestamp/fullUrl policy
  - add reference-rewrite logic over the assembled bundle copy
  - emit bundle-level provenance and per-entry fullUrls
- Update [models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py)
  - extend `BundleEntryAssemblyResult` with `full_url`
  - extend `CandidateBundleArtifact` with `deterministic_value_evidence`
- Update [validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/validation_builder.py)
  - replace deferred-field validation with populated identity/fullUrl checks
- Update [validation/standards.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/validation/standards.py)
  - require `Bundle.identifier`, `Bundle.timestamp`, and `entry.fullUrl` in the local scaffold-shape validator
- Update [repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/repair_decision_builder.py)
  - map the new bundle identity/fullUrl findings to `bundle_finalization`
- Update tests:
  - [tests/test_psca_bundle_finalization_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_finalization_builder.py)
  - [tests/test_psca_validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_validation_builder.py)
  - [tests/test_psca_repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_repair_decision_builder.py)
  - [tests/test_psca_bundle_builder_workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py)
- Update [README.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md) and [docs/development-plan.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md)

## 5. Step-by-step implementation plan

1. Extend the candidate-bundle models first:
   - add `BundleEntryAssemblyResult.full_url`
   - add `CandidateBundleArtifact.deterministic_value_evidence`
2. Implement deterministic bundle identity helpers in `bundle_finalization_builder.py`:
   - bundle UUID seed from `package_id`, `version`, `scenario_label`
   - identifier object from that UUID
   - synthetic timestamp from that UUID
   - per-placeholder `urn:uuid:` fullUrls from that UUID
3. Update bundle assembly to populate:
   - `Bundle.identifier`
   - `Bundle.timestamp`
   - `entry[i].fullUrl`
   - candidate-bundle populated paths for those fields
4. Aggregate reference contributions using `current_scaffold.source_step_ids` and rewrite copied resource references to the new fullUrls.
5. Remove bundle-level deferred paths for `identifier`, `timestamp`, and `entry.fullUrl`.
6. Emit deterministic value provenance for:
   - `Bundle.identifier.system`
   - `Bundle.identifier.value`
   - `Bundle.timestamp`
   - each `entry[i].fullUrl`
7. Update the local standards validator to require those fields as part of the assembled bundle shape.
8. Replace the workflow deferred-field check with exact populated-field checks and a reference-alignment check.
9. Add repair-routing mappings for the new bundle identity/fullUrl validation codes to `bundle_finalization`.
10. Update tests:
   - bundle-finalization unit test:
     - assert `Bundle.identifier.system/value`
     - assert `Bundle.timestamp`
     - assert every `entry.fullUrl`
     - assert `entry_assembly.full_url` matches the bundle entries
     - assert internal references in `Composition`, `PractitionerRole`, and section-entry resources are rewritten to matching fullUrls
     - assert `candidate_bundle.deferred_paths == []`
   - validation unit test:
     - happy path remains `passed_with_warnings`
     - removing `Bundle.identifier`, `Bundle.timestamp`, or one `entry.fullUrl` fails validation
     - restoring relative references after finalization fails the alignment check
   - repair decision unit test:
     - one new bundle-identity finding routes to `bundle_finalization`
   - workflow smoke test:
     - assert populated bundle identity fields and fullUrls
     - assert no deferred-path informational finding remains for bundle-level deferrals
     - assert overall happy path still ends at `external_validation_pending` only because external standards validation remains deferred
11. Update README and development-plan wording after tests are green.

## 6. Definition of Done

- The candidate bundle now deterministically includes:
  - `Bundle.identifier`
  - `Bundle.timestamp`
  - `entry.fullUrl` for every entry
- `Bundle.id` remains the existing human-readable candidate bundle id.
- The assembled bundle’s internal references are aligned to deterministic `entry.fullUrl` values.
- `CandidateBundleArtifact` shows:
  - no bundle-level deferred paths for identifier/timestamp/fullUrl
  - explicit provenance for the deterministic bundle identity values
- Dev UI visibly shows:
  - bundle identifier system/value
  - deterministic timestamp
  - per-entry `fullUrl`
  - per-entry assembly metadata including the assigned `fullUrl`
- Validation now protects:
  - identifier presence
  - timestamp presence
  - fullUrl presence
  - reference/fullUrl alignment
- Repair routing sends bundle identity/fullUrl failures to `bundle_finalization`.
- What remains intentionally deferred:
  - persistent published identity
  - public or server-assigned URLs
  - transport/persistence semantics
  - arbitrary-IG bundle identity policy

## 7. Risks / notes

- The main risk is over-claiming the timestamp as a real generation time. This plan treats it as a deterministic synthetic candidate-bundle timestamp and should say so explicitly in code/docs.
- The second risk is rewriting references too broadly. The implementation should rewrite only reference paths already captured in deterministic `reference_contributions`, not run a generic recursive mutation pass.
- A third risk is coupling too much behavior to `run_label`. The policy should derive directly from structured request fields, not from display-oriented strings, except where `run_label` is already a stable composed artifact and intentionally used.
- This slice will likely eliminate the current `bundle.deferred_fields_recorded` happy-path informational finding. That is expected and should not be treated as a regression.

## 8. Targeted `docs/development-plan.md` updates after implementation

- In Section 8, change `Current Focus` from bundle identity/fullUrl policy to the next bounded end-to-end realism slice after bundle identity is complete.
- In Section 9, replace `Next Planned Slice` with a bounded follow-on such as: “Implement the next narrow end-to-end realism slice by deepening Organization/provider-role context or expanding repair execution for resource_construction.”
- In Section 10, keep `Phase 8: Minimal End-to-End PS-CA Workflow` as `In Progress`.
- In Section 10, add a short Phase 8 note that the workflow now produces a candidate bundle with deterministic bundle identity, timestamp, and fullUrl policy.
- In Section 12, replace the earlier assumption that identifier/timestamp/fullUrl remain deferred with a new assumption that the first bundle identity policy uses local deterministic UUID-based candidate identifiers and synthetic timestamps rather than persistent publication identity.
- In Section 13, add one concise risk only if observed during implementation: deterministic synthetic timestamps and local URN fullUrls may later need refinement when publication/persistence semantics are introduced.
- In Section 16, update the immediate next objective to the next narrow realism/quality slice rather than bundle identity policy.
