1. Repo assessment

- The repo already has the upstream provider-side inputs needed for this slice:
  - `NormalizedBuildRequest.provider_context`
  - normalized provider identity
  - optional selected organization
  - optional selected provider-role relationship
  - explicit `normalization_mode` distinguishing legacy provider-profile fallback from richer selected-context modes
- Provider-context-aware schematic provenance already exists and is inspectable:
  - provider id/display name/source type
  - selected organization id/display name
  - selected provider-role relationship id/role label
- `resource_construction` already consumes that context honestly for the support-resource fields it can populate today:
  - `Practitioner.identifier[0].value`
  - `Practitioner.name[0].text`
  - `Organization.identifier[0].system/value`
  - `Organization.name`
  - `PractitionerRole.identifier[0].system/value`
  - `PractitionerRole.code[0].text`
- The current gap is not missing support-resource enrichment. It is that provider-context alignment is still implicit and asymmetric in validation:
  - `bundle.practitioner_identity_content_present` is mostly structural and non-empty, not exact provider-context alignment
  - `bundle.organization_identity_content_present` and `bundle.practitionerrole_relationship_identity_present` already bake exact selected-context matching into generic “content present” findings
  - `bundle.practitionerrole_author_context_present` similarly mixes structural presence with exact expected role-label matching
- The repo now has explicit patient-context alignment validation and evidence, but no parallel provider-context alignment layer in `ValidationEvidence`.
- Repair ownership is already in the right place and should not move:
  - practitioner -> `build-practitioner-1`
  - organization -> `build-organization-1`
  - practitioner role identity/author context -> `build-practitionerrole-1`
- Constraints that matter now:
  - no new provider-selection logic
  - no broader Organization or PractitionerRole semantics
  - no generic provider-alignment framework
  - no validation-architecture redesign
  - keep support-resource construction behavior unchanged

2. Proposed slice scope

- Keep support-resource construction behavior unchanged.
- Keep provider semantics bounded to the current normalized provider/org/role context only.
- Add explicit provider-context-to-bundle alignment hardening in workflow validation.
- Split current provider-side validation behavior into two layers:
  - structural/scaffold correctness
  - exact alignment to normalized provider context or current fallback policy
- Add a small provider-context alignment evidence summary to `ValidationEvidence` so Dev UI can show what validation expected from normalized provider context.
- Do not change:
  - request normalization behavior
  - schematic planning
  - build plan
  - bundle finalization
  - standards validator
  - repair execution behavior

3. Proposed provider-context-to-bundle alignment hardening approach

- Add explicit provider-context alignment findings while narrowing existing support-resource findings to structural meaning only.
- Recommended new workflow finding codes:
  - `bundle.practitioner_identity_aligned_to_context`
  - `bundle.organization_identity_aligned_to_context`
  - `bundle.practitionerrole_relationship_identity_aligned_to_context`
  - `bundle.practitionerrole_author_context_aligned_to_context`
- Narrow the meaning of existing structural finding codes:
  - `bundle.practitioner_identity_content_present`
    - require `active == true`
    - require non-empty `identifier[0].value`
    - require non-empty `name[0].text`
    - do not require exact equality here
  - `bundle.organization_identity_content_present`
    - only when `selected_organization` exists
    - require non-empty `identifier[0].system`
    - require non-empty `identifier[0].value`
    - require non-empty `name`
    - do not require exact equality here
  - `bundle.practitionerrole_relationship_identity_present`
    - only when `selected_provider_role_relationship` exists
    - require non-empty `identifier[0].system`
    - require non-empty `identifier[0].value`
    - do not require exact equality here
  - `bundle.practitionerrole_author_context_present`
    - require non-empty `code[0].text`
    - do not require exact equality here
- Add gated alignment checks:
  - run `bundle.practitioner_identity_aligned_to_context` only if `bundle.practitioner_identity_content_present` passed
  - run `bundle.organization_identity_aligned_to_context` only if `bundle.organization_identity_content_present` passed
  - run `bundle.practitionerrole_relationship_identity_aligned_to_context` only if `bundle.practitionerrole_relationship_identity_present` passed
  - run `bundle.practitionerrole_author_context_aligned_to_context` only if `bundle.practitionerrole_author_context_present` passed
- Exact alignment behavior:
  - practitioner alignment
    - exact provider id match
    - exact practitioner display-name match
  - organization alignment
    - exact identifier system match to `SELECTED_PROVIDER_ORGANIZATION_IDENTIFIER_SYSTEM`
    - exact identifier value match to selected organization id
    - exact name match to selected organization display name
  - practitioner role relationship identity alignment
    - exact identifier system match to `SELECTED_PROVIDER_ROLE_RELATIONSHIP_IDENTIFIER_SYSTEM`
    - exact identifier value match to selected relationship id
  - practitioner role author-context alignment
    - exact `code[0].text` match to deterministic expected role label
    - selected relationship label when present
    - fallback `"document-author"` when no selected relationship exists
- Add a small provider-context alignment evidence model, parallel to the patient-side one, not a generic engine.
- Recommended evidence shape:
  - `ProviderContextAlignmentEvidence`
    - `normalization_mode`
    - `provider_id`
    - `provider_display_name`
    - `organization_alignment_mode`
    - `selected_organization_identifier_system_expected`
    - `selected_organization_id_expected`
    - `selected_organization_display_name_expected`
    - `practitionerrole_alignment_mode`
    - `selected_provider_role_relationship_identifier_system_expected`
    - `selected_provider_role_relationship_id_expected`
    - `expected_role_label`
  - alignment-mode values should stay narrow and explicit:
    - `structured_provider_context`
    - `fallback_placeholder`
    - `not_applicable`
- Evidence population rules:
  - practitioner identity evidence always reflects normalized provider identity
  - organization evidence uses `structured_provider_context` when a selected organization exists, otherwise `not_applicable`
  - practitioner role relationship identity evidence uses `structured_provider_context` when a selected relationship exists, otherwise `not_applicable`
  - practitioner role author-context evidence uses:
    - `structured_provider_context` when selected relationship exists
    - `fallback_placeholder` when role label comes from current legacy placeholder policy
- Repair ownership should stay exactly where it is today:
  - practitioner alignment -> `build-practitioner-1`
  - organization alignment -> `build-organization-1`
  - practitioner role relationship identity alignment -> `build-practitionerrole-1`
  - practitioner role author-context alignment -> `build-practitionerrole-1`
- What remains intentionally deferred:
  - Organization telecom/address/type alignment
  - broader PractitionerRole specialty/telecom/availability semantics
  - provider graph semantics beyond selected org/relationship
  - provider-selection intelligence
  - generic provider-alignment infrastructure

4. File-level change plan

- Update [models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/validation/models.py)
  - add `ProviderContextAlignmentEvidence`
  - extend `ValidationEvidence` with `provider_context_alignment`
- Update [validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/validation_builder.py)
  - split provider structural checks from exact provider-context alignment checks
  - add the new provider-context alignment finding codes
  - gate alignment checks on structural success
  - populate provider-context alignment evidence from normalized provider context and current fallback policy
- Update [repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/repair_decision_builder.py)
  - route the new provider-context alignment findings to existing support-resource build steps
  - add directive-map entries so retry targeting stays narrow
- Update tests:
  - [test_psca_validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_validation_builder.py)
  - [test_psca_repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_repair_decision_builder.py)
  - [test_psca_repair_execution_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_repair_execution_builder.py) only for narrow routing smoke coverage
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

1. Add `ProviderContextAlignmentEvidence` to validation models and expose it through `ValidationEvidence`.
2. In `validation_builder.py`, add helper functions that compute deterministic expected provider-side values from `normalized_request.provider_context`:
   - expected practitioner id and display name
   - expected organization identifier system/id/name when selected organization exists
   - expected practitioner role identifier system/id when selected relationship exists
   - expected practitioner role label from selected relationship or fallback `"document-author"`
3. Populate provider-context alignment evidence from those helpers, using explicit alignment-mode values.
4. Refactor `bundle.practitioner_identity_content_present` into a structural-only check.
5. Add `bundle.practitioner_identity_aligned_to_context` as an exact provider-context match check, gated on structural success.
6. Refactor `bundle.organization_identity_content_present` into a structural-only check that still runs only when selected organization context exists.
7. Add `bundle.organization_identity_aligned_to_context` as an exact selected-organization alignment check, gated on structural success.
8. Refactor `bundle.practitionerrole_relationship_identity_present` into a structural-only check that still runs only when selected relationship exists.
9. Add `bundle.practitionerrole_relationship_identity_aligned_to_context` as an exact selected-relationship identifier check, gated on structural success.
10. Refactor `bundle.practitionerrole_author_context_present` into a structural-only non-empty role-label check.
11. Add `bundle.practitionerrole_author_context_aligned_to_context` as an exact role-label alignment check, gated on structural success, using selected relationship label or fallback placeholder policy.
12. Update `repair_decision_builder.py` so the new provider alignment findings map to:
    - `build-practitioner-1`
    - `build-organization-1`
    - `build-practitionerrole-1`
13. Update validation tests for these cases:
    - explicit provider-context happy path:
      - no new provider-alignment findings
      - validation evidence shows structured provider-context expectations
    - legacy provider-profile mode:
      - practitioner evidence still populated
      - organization alignment evidence is `not_applicable`
      - practitioner role author-context evidence shows `fallback_placeholder`
      - no organization/relationship alignment finding on happy path
    - wrong practitioner identifier or display name with fields still present:
      - `bundle.practitioner_identity_aligned_to_context`
      - not `bundle.practitioner_identity_content_present`
    - missing practitioner identifier/name:
      - structural finding only
      - alignment finding suppressed
    - wrong organization identifier system/value/name with fields present:
      - `bundle.organization_identity_aligned_to_context`
      - not `bundle.organization_identity_content_present`
    - missing organization identifier/name with selected organization present:
      - structural finding only
      - alignment finding suppressed
    - wrong practitioner role relationship identifier with fields present:
      - `bundle.practitionerrole_relationship_identity_aligned_to_context`
    - wrong practitioner role label with field present:
      - `bundle.practitionerrole_author_context_aligned_to_context`
      - not `bundle.practitionerrole_author_context_present`
    - missing practitioner role label:
      - structural finding only
      - alignment finding suppressed
14. Update repair-decision tests so the new provider alignment findings route to the existing owning build steps.
15. Add one or two repair-execution smoke tests only if needed to prove those findings still trigger the current targeted `resource_construction` retry path.
16. Update workflow smoke assertions so Dev UI-visible validation evidence now includes provider-context alignment expectations and modes.
17. Update README and `docs/development-plan.md` after tests are green.

6. Definition of Done

- The workflow still produces the same support resources it produces today.
- Workflow validation now explicitly separates:
  - structural support-resource correctness
  - exact alignment to normalized provider context or current fallback provider-role policy
- New provider-context alignment findings exist for:
  - Practitioner identity
  - Organization identity when selected organization context exists
  - PractitionerRole relationship identity when selected relationship context exists
  - PractitionerRole author-context role label
- Existing provider-side “content present” findings remain, but their meaning is narrowed to structural presence/correctness only.
- Alignment findings are gated so missing-field faults do not also produce duplicate exact-alignment findings.
- Dev UI can now show a validation-stage provider-context alignment summary with:
  - normalization mode
  - expected practitioner identity values
  - expected organization identity values when applicable
  - expected practitioner role relationship identity when applicable
  - expected role label and whether it came from structured provider context or fallback placeholder policy
- Repair ownership remains narrow and unchanged in shape:
  - practitioner alignment -> `build-practitioner-1`
  - organization alignment -> `build-organization-1`
  - practitioner role alignment -> `build-practitionerrole-1`
- What remains bounded or deferred:
  - broader Organization and PractitionerRole semantics
  - provider-selection logic
  - generic provider-alignment engines
  - non-deterministic provider reasoning

7. Risks / notes

- The main real risk is duplicate findings after splitting structural and alignment checks. Gating must suppress alignment findings when structural prerequisites fail.
- A second real risk is preserving clear legacy semantics. The evidence and finding language must say explicitly when the expected `PractitionerRole.code[0].text` came from fallback placeholder policy rather than selected relationship context.
- A third real risk is creating two sources of truth for expected provider-side values. Validation checks and validation evidence should use the same helper functions.
- A fourth real risk is overreaching into broader provider semantics. This slice should stay limited to the exact provider/org/role identity fields the workflow already populates deterministically.

8. Targeted `docs/development-plan.md` updates after implementation

- In Section 8, move `Current Focus` away from provider-context-to-bundle alignment hardening and toward the next bounded follow-on after explicit provider-context alignment validation exists.
- In Section 9, set `Next Planned Slice` to the next narrow decision after this hardening, likely whether another support-resource hardening slice is justified or whether the next bounded effort should return to a different workflow area.
- In Section 10, update the phase note to say the workflow now explicitly distinguishes structural support-resource correctness from deterministic provider-context alignment for the fields it can honestly populate.
- In Section 12, refine the provider-context assumption to say validation now checks both structural presence and explicit normalized provider-context alignment for Practitioner identity, selected Organization identity, and selected/fallback PractitionerRole author context.
- In Section 13, replace the current provider-side risk wording with the next real remaining risk: deterministic provider identity alignment is now hardened, but broader Organization and PractitionerRole semantics remain intentionally deferred.
- In Section 16, update the immediate next objective away from provider-context alignment hardening and toward the next bounded post-hardening decision without adding provider-selection logic or broader provider semantics.
