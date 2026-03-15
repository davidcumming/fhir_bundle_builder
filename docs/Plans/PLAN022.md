# Deeper Organization / PractitionerRole Realism Slice

**Summary**
- The current repo can already populate richer support resources from normalized provider context, but the actual structured inputs still only provide `organization_id`, `organization display_name`, `provider-role relationship_id`, and `role_label`.
- The narrow next step is to deepen deterministic identity realism, not broad semantic realism: make `Organization.identifier` fully structured and add deterministic `PractitionerRole.identifier` from the selected provider-role relationship.
- No new upstream models, no new selection heuristics, and no workflow-loop changes are needed for this slice.

## 1. Repo assessment
- `NormalizedBuildRequest.provider_context` already contains everything this slice can honestly use today:
  - `selected_organization.organization_id`
  - `selected_organization.display_name`
  - `selected_provider_role_relationship.relationship_id`
  - `selected_provider_role_relationship.role_label`
- `resource_construction_builder.py` currently builds:
  - `Organization.identifier[0].value` and `Organization.name` when a selected organization exists
  - `PractitionerRole.practitioner.reference`
  - `PractitionerRole.organization.reference`
  - `PractitionerRole.code[0].text`
- `validation_builder.py` currently protects:
  - `bundle.organization_identity_content_present` for organization id value + name
  - `bundle.practitionerrole_author_context_present` for role label text
- `repair_decision_builder.py` already has the correct repair boundaries:
  - `bundle.organization_identity_content_present -> resource_construction -> build-organization-1`
  - `bundle.practitionerrole_author_context_present -> resource_construction -> build-practitionerrole-1`
- The main realism gap is now specific and narrow:
  - `Organization.identifier` lacks a deterministic `system`
  - `PractitionerRole` still has no deterministic identifier even though the normalized selected relationship has `relationship_id`
- The main constraint is upstream data shape:
  - there is still no structured source for organization telecom/address/type
  - there is still no structured source for PractitionerRole specialty/telecom/period/availableTime/coded taxonomy
- This means the repo can support deeper deterministic identity realism now, but not broader directory-style realism.

## 2. Proposed slice scope
- Deepen `Organization` realism by making the selected-organization identifier fully structured:
  - add `Organization.identifier[0].system`
  - keep `Organization.identifier[0].value`
  - keep `Organization.name`
- Deepen `PractitionerRole` realism by adding deterministic selected-relationship identity:
  - add `PractitionerRole.identifier[0].system`
  - add `PractitionerRole.identifier[0].value`
  - keep existing `PractitionerRole.code[0].text`
  - keep existing practitioner/organization references
- Reuse existing normalized provider context and existing schematic/request provenance.
- Add validation only for fields the repo can now truly populate.
- Keep repair routing narrow and unchanged in shape:
  - Organization identity stays owned by `build-organization-1`
  - new PractitionerRole relationship identity stays owned by `build-practitionerrole-1`
- Intentionally defer:
  - Organization telecom, address, type, partOf, endpoint
  - PractitionerRole specialty, telecom, period, availableTime, coded role taxonomy
  - any new provider-selection logic
  - any new upstream provider/org/role model expansion

## 3. Proposed deeper Organization / PractitionerRole realism approach
- Add two fixed deterministic identifier-system constants and use them consistently in construction and validation:
  - `urn:fhir-bundle-builder:selected-provider-organization-identifier`
  - `urn:fhir-bundle-builder:selected-provider-role-relationship-identifier`
- `Organization` construction:
  - when `selected_organization` exists, populate:
    - `identifier[0].system = urn:fhir-bundle-builder:selected-provider-organization-identifier`
    - `identifier[0].value = selected_organization.organization_id`
    - `name = selected_organization.display_name`
  - legacy mode remains unchanged and continues to leave Organization thin
- `PractitionerRole` construction:
  - when `selected_provider_role_relationship` exists, populate:
    - `identifier[0].system = urn:fhir-bundle-builder:selected-provider-role-relationship-identifier`
    - `identifier[0].value = selected_provider_role_relationship.relationship_id`
    - `code[0].text = selected_provider_role_relationship.role_label`
  - when no selected relationship exists, keep the current fallback behavior:
    - no identifier
    - `code[0].text = placeholder.role`
- Deterministic provenance / inspectability:
  - extend `deterministic_value_evidence` for `build-organization-1` to include `identifier[0].system`
  - extend `deterministic_value_evidence` for `build-practitionerrole-1` to include `identifier[0].system` and `identifier[0].value`
  - update assumptions text so Dev UI explains that Organization identity comes from selected organization context and PractitionerRole identity comes from the selected provider-role relationship
- Validation changes:
  - keep `bundle.organization_identity_content_present`, but expand it to require:
    - `identifier[0].system`
    - `identifier[0].value`
    - `name`
    - only when `selected_organization` exists
  - add `bundle.practitionerrole_relationship_identity_present`
    - require `identifier[0].system` and `identifier[0].value`
    - only when `selected_provider_role_relationship` exists
  - keep `bundle.practitionerrole_author_context_present` focused only on `code[0].text`
- Repair routing changes:
  - keep `bundle.organization_identity_content_present -> resource_construction -> build-organization-1`
  - add `bundle.practitionerrole_relationship_identity_present -> resource_construction -> build-practitionerrole-1`
- What remains deferred:
  - anything beyond deterministic identity-style enrichment for Organization and PractitionerRole
  - any field that would require new upstream structure or interpretation

## 4. File-level change plan
- Update [/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/resource_construction_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/resource_construction_builder.py)
  - add the two fixed identifier-system constants
  - populate richer Organization and PractitionerRole identifier fields
  - add deterministic evidence and updated assumptions
- Update [/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/validation_builder.py)
  - expand organization identity validation
  - add the new PractitionerRole relationship-identity validation
  - import the shared constants from `resource_construction_builder.py` so validation and construction do not drift
- Update [/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/repair_decision_builder.py)
  - add route/directive mapping for `bundle.practitionerrole_relationship_identity_present`
  - keep Organization mapping but update rationale text to reflect fully structured identifier content
- Update tests:
  - [/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_resource_construction_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_resource_construction_builder.py)
  - [/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_validation_builder.py)
  - [/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_repair_decision_builder.py)
  - [/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_repair_execution_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_repair_execution_builder.py)
  - [/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py)
- Update docs:
  - [/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md)
  - [/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md)
- No model changes.
- No schematic changes.
- No build-plan changes.

## 5. Step-by-step implementation plan
1. Add the two fixed identifier-system constants in `resource_construction_builder.py`.
2. Update `build-organization-1` so selected-organization mode populates `identifier[0].system` in addition to the current value and name.
3. Update `build-practitionerrole-1` so selected-relationship mode populates `identifier[0].system` and `identifier[0].value` before applying the existing role label.
4. Extend deterministic value evidence and assumptions for both support-resource steps.
5. Expand `bundle.organization_identity_content_present` so it validates identifier system + value + name when selected organization context exists.
6. Add `bundle.practitionerrole_relationship_identity_present` so it validates PractitionerRole identifier system + value when selected relationship context exists.
7. Update `repair_decision_builder.py`:
   - add `bundle.practitionerrole_relationship_identity_present`
   - route it to `resource_construction`
   - map it to `["build-practitionerrole-1"]`
   - keep Organization routing on `["build-organization-1"]`
8. Update construction tests:
   - rich provider-context path asserts Organization identifier system/value and name
   - rich provider-context path asserts PractitionerRole identifier system/value and role text
   - legacy path still asserts Organization remains thin and PractitionerRole has no identifier
9. Update validation tests:
   - removing Organization identifier system fails `bundle.organization_identity_content_present`
   - removing PractitionerRole identifier value fails `bundle.practitionerrole_relationship_identity_present`
   - legacy mode does not require Organization identity or PractitionerRole relationship identity
10. Update repair-decision tests:
   - new PractitionerRole relationship-identity finding routes to `resource_construction`
   - targeted directive is `["build-practitionerrole-1"]`
   - Organization route still targets `["build-organization-1"]`
11. Update repair-execution tests:
   - break only PractitionerRole identifier content
   - assert targeted retry reruns only `build-practitionerrole-1`
   - update the existing Organization identity retry test so it can fail on the expanded identifier contract
12. Update the workflow smoke test:
   - assert final `Organization.identifier[0].system`
   - assert final `PractitionerRole.identifier[0].system`
   - assert final `PractitionerRole.identifier[0].value`
13. Update README and development plan wording after tests are green.
14. Run the full test suite and confirm there are no stale expectations that Organization identity means only identifier value + name.

## 6. Definition of Done
- `Organization` now carries a fully structured deterministic identifier when selected organization context exists:
  - `identifier[0].system`
  - `identifier[0].value`
  - `name`
- `PractitionerRole` now carries a deterministic identifier when selected provider-role relationship context exists:
  - `identifier[0].system`
  - `identifier[0].value`
- `PractitionerRole.code[0].text` still carries the deterministic selected role label.
- Dev UI now visibly shows richer support-resource construction evidence for:
  - Organization identifier system/value and name
  - PractitionerRole identifier system/value and role label
- Validation now protects:
  - expanded Organization identity content
  - PractitionerRole relationship identity content
  - existing PractitionerRole author-context label
- Repair routing/execution now supports the new PractitionerRole identity failure path through the existing `build-practitionerrole-1` targeted retry.
- Legacy provider-profile mode still works and still avoids requiring fields that cannot be populated honestly.
- What remains deferred:
  - Organization telecom/address/type/endpoint
  - PractitionerRole specialty/telecom/period/availableTime/coded role taxonomy
  - any new provider-selection logic or upstream model expansion

## 7. Risks / notes
- The main real risk is overclaiming Organization realism. With the current upstream shape, the only honest Organization expansion is a fully structured identifier, not broader directory fields.
- A second real risk is conflating PractitionerRole identity with role semantics. The new identifier must validate the selected relationship id only; `code[0].text` remains a separate role-label check.
- A third real risk is drift between construction and validation constants. Validation should import the same identifier-system constants instead of duplicating literals.
- A fourth real risk is breaking legacy mode. Both Organization and PractitionerRole identity checks must stay conditional on selected normalized provider context.

## 8. Targeted `docs/development-plan.md` updates after implementation
- In Section 8, change `Current Focus` from deeper support-resource realism planning to the next bounded realism or exact-alignment ownership slice.
- In Section 9, set `Next Planned Slice` to the next bounded item after this one, likely revisiting whether non-Composition exact fullUrl alignment can narrow further beyond bundle-finalization ownership.
- In Section 10, update the Phase 8 note to state that support-resource realism now includes structured Organization identifier content and PractitionerRole relationship identity derived from normalized provider context.
- In Section 12, refine the provider-context assumption to say the current normalized provider/org/role input is sufficient for deterministic support-resource identity enrichment, but not for broader Organization or PractitionerRole semantic enrichment.
- In Section 13, replace the current provider-context drift risk with the next real remaining risk: support-resource realism is now deeper, but broader fields still remain deferred because upstream provider context does not yet carry authoritative telecom, address, specialty, or availability structure.
- In Section 16, update the immediate next objective away from deeper Organization / PractitionerRole identity realism and toward the next bounded realism or remaining repair-ownership slice.
