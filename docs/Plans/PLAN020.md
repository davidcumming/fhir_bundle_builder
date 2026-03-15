1. Repo assessment

- The current workflow input is still thin on the provider side:
  - [models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py) defines `WorkflowBuildInput.provider_profile` and `NormalizedBuildRequest.provider_profile` as `ProfileReferenceInput(profile_id, display_name, source_type="stub")`.
  - there is no richer provider/org/role input model yet.
- Request normalization is still executor-local and trivial:
  - [executors.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/executors.py) simply copies `provider_profile` into `NormalizedBuildRequest`.
  - there is no dedicated normalization builder or deterministic provider-context resolution step yet.
- Current support-resource construction is blocked specifically by the thin provider input:
  - [resource_construction_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/resource_construction_builder.py)
    - `Practitioner` uses `normalized_request.provider_profile.profile_id` and `display_name`
    - `Organization` remains base metadata only
    - `PractitionerRole` only carries references plus `code[0].text` from the placeholder role (`document-author`)
- Current validation mirrors that maturity:
  - [validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/validation_builder.py) protects:
    - `bundle.practitioner_identity_content_present`
    - `bundle.practitionerrole_author_context_present`
  - there is no `Organization` identity/content rule yet.
- The schematic and planning layers are already ready to consume richer provider context later without structural redesign:
  - [schematic_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/schematic_builder.py) already has placeholders and relationships for `Practitioner`, `Organization`, and `PractitionerRole`
  - [build_plan_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/build_plan_builder.py) already has separate build steps for those support resources
- Current tests and smoke path still assume the thin input:
  - [test_psca_bundle_builder_workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py) only passes `provider_profile`
  - [test_psca_resource_construction_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_resource_construction_builder.py) and validation/repair tests construct `NormalizedBuildRequest` directly with only `provider_profile`
- The docs already identify the real blocker:
  - [docs/development-plan.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md) explicitly says meaningful `Organization` identity and richer `PractitionerRole` context depend on future provider input expansion.
- What is missing for this slice:
  - a typed upstream provider/org/role model
  - deterministic normalization of that model into one selected organization/provider-role context
  - immediate consumption of that selected context in `Organization` and `PractitionerRole`
  - backward-compatible behavior for legacy `provider_profile` callers/tests

2. Proposed slice scope

- Add a new optional top-level `provider_context` input while keeping `provider_profile` as a legacy compatibility path for now.
- Introduce a small explicit provider/org/role structure, not a generic relationship graph:
  - provider identity
  - organization list
  - provider-role relationship list
  - explicit selected provider-role relationship id
- Normalize that into a workflow-ready selected context inside `NormalizedBuildRequest`.
- Immediate downstream consumption in this slice:
  - `Practitioner`
  - `Organization`
  - `PractitionerRole`
  - support-resource validation / repair routing
  - Dev UI inspectability of normalized provider context
- Keep these out of scope for this slice:
  - schematic-stage org/role selection heuristics
  - patient-specific org/role matching
  - provider management CRUD or persistence
  - generic provider directory abstractions
  - removal of the legacy `provider_profile` path

3. Proposed provider input model expansion approach

- Add these new typed input models in `models.py`:
  - `ProviderIdentityInput`
    - `provider_id: str`
    - `display_name: str`
    - `source_type: Literal["stub", "provider_management"] = "stub"`
  - `ProviderOrganizationInput`
    - `organization_id: str`
    - `display_name: str`
  - `ProviderRoleRelationshipInput`
    - `relationship_id: str`
    - `organization_id: str`
    - `role_label: str`
  - `ProviderContextInput`
    - `provider: ProviderIdentityInput`
    - `organizations: list[ProviderOrganizationInput]`
    - `provider_role_relationships: list[ProviderRoleRelationshipInput]`
    - `selected_provider_role_relationship_id: str | None = None`
- Add a normalized workflow-facing model:
  - `NormalizedProviderContext`
    - `provider: ProviderIdentityInput`
    - `organizations: list[ProviderOrganizationInput]`
    - `provider_role_relationships: list[ProviderRoleRelationshipInput]`
    - `selected_provider_role_relationship: ProviderRoleRelationshipInput | None`
    - `selected_organization: ProviderOrganizationInput | None`
    - `normalization_mode: Literal["legacy_provider_profile", "provider_context_single_relationship", "provider_context_explicit_selection"]`
- Extend public workflow-facing types:
  - `WorkflowBuildInput`
    - keep `provider_profile`
    - add `provider_context: ProviderContextInput | None = None`
  - `NormalizedBuildRequest`
    - keep `provider_profile` as a compatibility view
    - add `provider_context: NormalizedProviderContext`
- Deterministic normalization behavior:
  - if `provider_context` is present, it is authoritative
  - if `provider_context.selected_provider_role_relationship_id` is provided:
    - resolve that exact relationship
    - require that it exists
    - require that its `organization_id` resolves to a listed organization
  - if no explicit selected id is provided:
    - if there is exactly one provider-role relationship, select it deterministically
    - if there are multiple relationships, fail normalization rather than guess
  - if `provider_context` is absent:
    - build `NormalizedProviderContext` in `legacy_provider_profile` mode
    - use `provider_profile` to synthesize provider identity only
    - leave organizations and selected role/organization empty
- Recommended normalization implementation detail:
  - extract normalization out of the executor into a small pure builder, e.g. `build_psca_normalized_request(...)`, so the deterministic provider-context resolution is directly unit-testable.
- Immediate downstream consumption:
  - `Practitioner`
    - read from `normalized_request.provider_context.provider`
    - populate exactly as today, but from the richer normalized provider identity
  - `Organization`
    - if `selected_organization` is present:
      - populate `identifier[0].value = selected_organization.organization_id`
      - populate `name = selected_organization.display_name`
    - otherwise keep the current thin legacy behavior
  - `PractitionerRole`
    - keep `practitioner.reference` and `organization.reference`
    - if `selected_provider_role_relationship` is present:
      - populate `code[0].text = selected_provider_role_relationship.role_label`
    - otherwise keep the current fallback `code[0].text = placeholder.role`
- Validation / repair behavior:
  - keep `bundle.practitioner_identity_content_present`
  - keep `bundle.practitionerrole_author_context_present`, but make the expected text dynamic:
    - selected relationship role label when provider context is available
    - placeholder role fallback in legacy mode
  - add `bundle.organization_identity_content_present`, but only enforce it when `selected_organization` exists in normalized provider context
  - route `bundle.organization_identity_content_present` to `resource_construction`
  - keep `bundle.practitionerrole_author_context_present` routed to `resource_construction`
- Build-plan inspectability:
  - update `build-practitionerrole-1` expected inputs to include `normalized_request`
  - update support-resource step descriptions/expected-input wording so Dev UI reflects that selected provider/org/role context is now part of the available build input
- What stays staged for later:
  - schematic-stage selection of the “right” org/role from a multi-org provider context
  - any use of the full organization list beyond the one normalized selected organization
  - richer `PractitionerRole` fields like specialty, telecom, period, or availability
  - multi-organization patient-scenario matching logic

4. File-level change plan

- Create [request_normalization_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/request_normalization_builder.py)
  - hold the deterministic normalization logic for the new provider context
- Update [models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py)
  - add the new provider/org/role input and normalized-context models
  - extend `WorkflowBuildInput` and `NormalizedBuildRequest`
  - expand `ProfileReferenceInput.source_type` to support a non-stub compatibility value, so derived compatibility `provider_profile` is honest
- Update [executors.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/executors.py)
  - make `request_normalization` call the new builder
- Update [build_plan_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/build_plan_builder.py)
  - add `normalized_request` as an expected input for `build-practitionerrole-1`
  - refine support-resource step wording for inspectability
- Update [resource_construction_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/resource_construction_builder.py)
  - consume normalized provider context for `Practitioner`, `Organization`, and `PractitionerRole`
  - update deterministic evidence, deferred paths, and assumptions
- Update [validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/validation_builder.py)
  - add conditional organization content validation
  - make PractitionerRole validation compare against normalized selected role label when available
- Update [repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/repair_decision_builder.py)
  - add routing/directive mapping for `bundle.organization_identity_content_present`
  - adjust rationale text for `bundle.practitionerrole_author_context_present`
- Update tests:
  - add [test_psca_request_normalization_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_request_normalization_builder.py)
  - update [test_psca_resource_construction_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_resource_construction_builder.py)
  - update [test_psca_validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_validation_builder.py)
  - update [test_psca_repair_decision_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_repair_decision_builder.py)
  - update [test_psca_repair_execution_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_repair_execution_builder.py) with one organization-targeted retry path
  - update [test_psca_bundle_builder_workflow.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_bundle_builder_workflow.py)
- Update docs:
  - [README.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md)
  - [docs/development-plan.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md)

5. Step-by-step implementation plan

1. Add the new provider/org/role models and `NormalizedProviderContext` to `models.py`.
2. Extend `WorkflowBuildInput` with optional `provider_context` and `NormalizedBuildRequest` with normalized provider context.
3. Implement a pure normalization builder:
   - construct normalized provider context from either rich `provider_context` or legacy `provider_profile`
   - derive compatibility `provider_profile` from the normalized provider identity
   - enforce deterministic selection rules for provider-role relationships
4. Refactor the `request_normalization` executor to use that builder.
5. Update `build_plan_builder.py` so `build-practitionerrole-1` explicitly declares `normalized_request` as an input and support-resource step descriptions reflect richer provider context.
6. Update `resource_construction_builder.py`:
   - Practitioner:
     - source from `normalized_request.provider_context.provider`
   - Organization:
     - populate identifier + name when `selected_organization` exists
     - otherwise keep the current legacy-thin behavior
   - PractitionerRole:
     - keep references
     - source `code[0].text` from selected relationship role label when available
     - fallback to placeholder role otherwise
   - update assumptions, deferred paths, and deterministic evidence accordingly
7. Update workflow validation:
   - keep practitioner validation
   - make PractitionerRole context validation compare against normalized selected role label or legacy fallback
   - add conditional organization identity validation when selected organization exists
8. Update repair routing:
   - add `bundle.organization_identity_content_present -> resource_construction`
   - map it to `build-organization-1`
   - keep `bundle.practitionerrole_author_context_present -> build-practitionerrole-1`
9. Add direct normalization tests:
   - legacy `provider_profile` only -> normalized legacy mode with no selected org/role
   - explicit provider context + explicit selected relationship -> normalized selected org/role
   - single relationship + no explicit selected id -> deterministic single-relationship mode
   - multiple relationships + no selected id -> deterministic normalization error
   - selected relationship pointing to unknown org -> deterministic normalization error
10. Update resource-construction tests:
    - new rich provider-context path populates:
      - `Practitioner.identifier/name`
      - `Organization.identifier/name`
      - `PractitionerRole.code[0].text`
    - legacy path still leaves Organization thin
11. Update validation tests:
    - rich provider-context happy path passes
    - removing Organization identifier or name when selected org exists fails `bundle.organization_identity_content_present`
    - removing PractitionerRole code text fails `bundle.practitionerrole_author_context_present`
    - legacy path does not require Organization identity content
12. Update repair-decision tests:
    - organization identity failure routes to `resource_construction`
    - targeted directive is `["build-organization-1"]`
13. Update repair-execution tests:
    - one organization-identity failure reruns only `build-organization-1`
    - downstream `bundle_finalization`, `validation`, and `repair_decision` still rerun as today
14. Update workflow smoke test:
    - switch the main smoke path to use `provider_context`
    - assert normalized selected organization/provider-role context is visible
    - assert enriched `Organization` and `PractitionerRole` in the final candidate bundle
15. Update README and development-plan wording after tests are green.

6. Definition of Done

- `WorkflowBuildInput` supports a richer optional `provider_context` with provider identity, organizations, provider-role relationships, and explicit selected relationship.
- `NormalizedBuildRequest` exposes a normalized provider context that is inspectable in Dev UI.
- Legacy callers/tests using only `provider_profile` still work.
- Rich provider-context input now materially changes support-resource construction:
  - `Practitioner` identity comes from structured provider identity
  - `Organization` can carry deterministic identifier + name from the selected organization
  - `PractitionerRole.code[0].text` can carry a deterministic selected role label
- Dev UI visibly shows:
  - the richer top-level `provider_context` input
  - normalized selected provider/org/role context in `request_normalization`
  - richer `Organization` and `PractitionerRole` scaffolds in `resource_construction`
- Validation now protects:
  - practitioner identity content
  - practitioner role context label
  - organization identity content when richer provider context is available
- Repair routing/execution now supports the new organization identity failure path through existing `resource_construction` retry mechanics.
- What remains intentionally deferred:
  - schematic-stage org/role selection heuristics
  - multi-org patient-scenario matching
  - richer PractitionerRole specialty/period/telecom semantics
  - broader provider-management infrastructure
  - removal of legacy `provider_profile`

7. Risks / notes

- The main real risk is dual-input drift between legacy `provider_profile` and new `provider_context`. This slice should make `provider_context` authoritative whenever both are supplied.
- A second real risk is accidental selection intelligence creep. This slice should require explicit selected relationship when the provider has multiple role relationships instead of guessing.
- A third real risk is over-enriching PractitionerRole from too little structure. Keep it to one deterministic role label plus existing references.
- A fourth real risk is making Organization validation unconditional and breaking the legacy compatibility path. Organization identity validation should only fire when a selected organization exists in normalized provider context.

8. Targeted `docs/development-plan.md` updates after implementation

- In Section 8, change `Current Focus` from provider input expansion to the next bounded realism/quality slice after structured provider/org/role context is available upstream.
- In Section 9, replace `Next Planned Slice` with: “Revisit whether non-Composition exact fullUrl alignment can later narrow beyond bundle-finalization ownership.”
- In Section 10, update the Phase 8 note to state that the workflow now accepts structured provider/org/role context and immediately uses the selected organization/provider-role relationship for richer support-resource construction.
- In Section 12, refine the provider-related assumption to say the workflow now accepts explicit provider/org/role context, but patient-scenario-specific context selection is still deferred.
- In Section 13, replace the old provider-input limitation risk with the next real risk: dual support for legacy `provider_profile` and richer `provider_context` can drift unless normalization precedence stays explicit and deterministic.
- In Section 16, update the immediate next objective away from provider input expansion and toward the remaining exact-alignment ownership slice or the next bounded realism improvement that consumes the richer normalized provider context.
