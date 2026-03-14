## 1. Repo assessment

- The repo already has the right architectural seam for this slice:
  - `StandardsValidator` protocol in [validation/standards.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/validation/standards.py)
  - `StandardsValidationRequest` / `StandardsValidationResult` in [validation/models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/validation/models.py)
  - validation builder wiring that accepts any `StandardsValidator` in [validation_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/validation_builder.py)
- The current executor wiring is hardcoded to one global local validator singleton in [executors.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/executors.py):
  - `_STANDARDS_VALIDATOR = LocalCandidateBundleScaffoldStandardsValidator()`
  - there is no runtime selection/config policy yet
- The current local validator is still intentionally narrow:
  - bundle scaffold shape only
  - one warning finding `external_profile_validation_deferred`
  - no network access
- The current validation result shape does not yet record:
  - requested validator mode
  - whether an external validator actually ran
  - whether fallback was used
- The current tests only exercise the local scaffold validator path. There is no mocked external adapter coverage yet.
- The repo currently has no HTTP client dependency and no established env/config pattern for runtime service selection:
  - `pyproject.toml` only depends on Agent Framework, Pydantic, and typing extensions
  - repo search shows no existing `httpx`, `requests`, `aiohttp`, or env-based runtime config handling
- The README currently documents only the local validation path.
- The development plan currently points at a different next slice, so this implementation will intentionally change the plan sequencing.
- Matchbox’s documented primary validation path is the FHIR `$validate` operation on the server, with `resource` in the body and `profile` / optional `ig` supplied to the operation; the public docs and tutorial are enough to ground a narrow adapter plan:
  - [Validation of FHIR resources - Matchbox](https://ahdis.github.io/matchbox/validation/)
  - [Tutorial: validation - Matchbox](https://ahdis.github.io/matchbox/validation-tutorial/)

## 2. Proposed slice scope

- Add one real external standards-validator adapter:
  - `MatchboxStandardsValidator`
- Keep the local scaffold validator as:
  - the default validator in local/dev environments
  - the fallback validator when `matchbox` mode is requested but Matchbox is unreachable or misconfigured
- Keep one active standards result per run:
  - do not merge local + Matchbox findings on successful Matchbox runs
  - use Matchbox-only result on success
  - use local-only result with explicit fallback warning on transport/config failure
- Recommended narrow runtime config policy:
  - mode: `local_scaffold` or `matchbox`
  - Matchbox base URL
  - optional timeout seconds
  - env-driven, not workflow-input-driven
- Out of scope after this slice:
  - Docker or deployment setup
  - CI integration against live Matchbox
  - generic validator plugin platform
  - arbitrary-spec validation config
  - operational monitoring/retries/circuit breaking

## 3. Proposed Matchbox integration approach

- Add a narrow runtime config model, for example:
  - `StandardsValidatorMode = Literal["local_scaffold", "matchbox"]`
  - `StandardsValidationConfig`
    - `mode`
    - `matchbox_base_url: str | None`
    - `timeout_seconds: float`
- Load config from env in a small resolver/factory layer. Recommended env names:
  - `FHIR_BUNDLE_BUILDER_STANDARDS_VALIDATOR_MODE`
  - `FHIR_BUNDLE_BUILDER_MATCHBOX_BASE_URL`
  - `FHIR_BUNDLE_BUILDER_MATCHBOX_TIMEOUT_SECONDS`
- Keep `WorkflowBuildInput` and `NormalizedBuildRequest` unchanged in this slice. This is runtime infrastructure choice, not per-request domain input.
- Use one active standards validator at a time:
  - `local_scaffold` mode:
    - run only `LocalCandidateBundleScaffoldStandardsValidator`
  - `matchbox` mode:
    - attempt Matchbox first
    - if Matchbox returns a valid response, use only Matchbox findings/status
    - if Matchbox is unavailable, times out, is misconfigured, returns non-2xx, or returns an unparseable payload, fall back to the local scaffold validator and record that fallback explicitly
- Keep Matchbox specifics isolated in a new adapter module. Recommended request policy:
  - `POST {base_url}/$validate`
  - query params:
    - `profile={bundle_profile_url}`
    - `ig={package_id}#{version}`
  - headers:
    - `Accept: application/fhir+json`
    - `Content-Type: application/fhir+json`
  - body:
    - `StandardsValidationRequest.bundle_json`
- Response translation policy:
  - primary expected response: FHIR `OperationOutcome`
  - parser should tolerate either:
    - a single `OperationOutcome`
    - or a list of `OperationOutcome` resources if Matchbox returns that shape in some deployments/docs
  - flatten `issue` items into `ValidationFinding`:
    - `channel = "standards"`
    - severity map:
      - `fatal` / `error` -> `error`
      - `warning` -> `warning`
      - `information` -> `information`
    - `code = "matchbox.<issue.code>"` if present, else `matchbox.issue`
    - `location = issue.expression[0]` if present, else `issue.location[0]`, else `OperationOutcome.issue[{i}]`
    - `message = issue.diagnostics` if present, else `issue.details.text`, else a deterministic fallback message
  - `StandardsValidationResult.status` stays derived from mapped severities
- Extend `StandardsValidationResult` so the standards channel explicitly records runtime behavior:
  - `requested_validator_mode`
  - `attempted_validator_ids`
  - `external_validation_executed`
  - `fallback_used`
- Fallback behavior in `matchbox` mode:
  - run local scaffold validator only after Matchbox transport/config failure
  - preserve local validator findings
  - add one explicit warning finding such as `matchbox.unavailable_fallback_local`
  - add one deferred area stating local fallback is not equivalent to full external conformance validation
- Keep the workflow/business-rule validation layer unchanged.
- Recommended dependency:
  - add `httpx` as the only new runtime dependency
- Recommended default config values:
  - mode default: `local_scaffold`
  - timeout default: `10.0`
  - if mode is `matchbox` and base URL is missing, treat that as fallback-to-local with a clear warning rather than crashing the workflow

## 4. File-level change plan

- Update [validation/models.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/validation/models.py)
  - add validator mode/config types
  - extend `StandardsValidationResult` with requested-mode / attempted-validator / fallback metadata
- Update [validation/standards.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/validation/standards.py)
  - keep the local validator
  - add a small status helper if needed for shared mapping
- Create [validation/matchbox.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/validation/matchbox.py)
  - `MatchboxStandardsValidator`
  - Matchbox request/response translation
- Create [validation/runtime.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/validation/runtime.py)
  - env-based config loader
  - validator selection / fallback policy
- Update [validation/__init__.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/validation/__init__.py)
  - export new config/adapter/runtime helpers as needed
- Update [executors.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/executors.py)
  - replace the hardcoded global validator singleton with resolved runtime config/validator policy
- Update [pyproject.toml](/Users/davidcumming/coding_projects/fhir_bundle_builder/pyproject.toml)
  - add `httpx`
- Add tests:
  - new direct adapter test file, e.g. `tests/test_matchbox_standards_validator.py`
  - update `tests/test_psca_validation_builder.py`
  - update workflow smoke test only as needed for the richer standards result metadata
- Update [README.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md) and [docs/development-plan.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md)

## 5. Step-by-step implementation plan

1. Add the runtime validation config types and extend `StandardsValidationResult` to record:
   - requested mode
   - attempted validator ids
   - whether external validation actually executed
   - whether fallback was used
2. Add `httpx` to runtime dependencies.
3. Implement `MatchboxStandardsValidator` as an async adapter using `httpx.AsyncClient`.
4. Implement Matchbox request construction against `POST {base_url}/$validate` using:
   - `profile` from `StandardsValidationRequest.bundle_profile_url`
   - `ig` from `specification_package_id#specification_version`
   - FHIR JSON body from `bundle_json`
5. Implement Matchbox response translation:
   - parse `OperationOutcome`
   - tolerate either single or list form
   - map issues into `ValidationFinding`
   - compute `StandardsValidationResult.status`
6. Add a small runtime resolver/factory:
   - load env config
   - return local validator in `local_scaffold` mode
   - return a narrow “attempt Matchbox, else local fallback” path in `matchbox` mode
7. Define exact fallback semantics:
   - transport/config/payload failure -> local scaffold validator result
   - append warning `matchbox.unavailable_fallback_local`
   - set:
     - `requested_validator_mode = "matchbox"`
     - `attempted_validator_ids = ["matchbox_standards_validator", "local_candidate_bundle_scaffold_validator"]`
     - `external_validation_executed = False`
     - `fallback_used = True`
   - if Matchbox succeeds:
     - `requested_validator_mode = "matchbox"`
     - `attempted_validator_ids = ["matchbox_standards_validator"]`
     - `external_validation_executed = True`
     - `fallback_used = False`
8. Wire the runtime resolver into the validation executor and repair execution path so both use the same standards-validator selection policy.
9. Add tests:
   - direct Matchbox adapter test with mocked successful `OperationOutcome` response and severity/code/location mapping assertions
   - direct fallback test where Matchbox transport fails and local fallback is used with explicit warning metadata
   - update validation builder happy-path assertions to include the richer standards-result metadata for default local mode
   - optionally add one executor/workflow smoke assertion that default mode remains local unless env vars change
10. Update README with:
   - default local validator behavior
   - env vars for Matchbox mode
   - note that Matchbox is optional and not required for tests/dev
11. Update development plan to reflect that the first real external standards validator path now exists.

## 6. Definition of Done

- The repo contains a real `MatchboxStandardsValidator` implementation behind the existing `StandardsValidator` interface.
- The local scaffold validator remains available and is still the default in normal local development.
- Standards validator selection is configurable through a narrow local config policy.
- `matchbox` mode is optional, not mandatory.
- When Matchbox succeeds:
  - the standards channel uses Matchbox findings/status only
  - the result clearly records that external validation executed
- When Matchbox is unavailable or misconfigured:
  - the standards channel falls back to the local scaffold validator
  - the result clearly records requested mode `matchbox`, fallback usage, and that full external validation did not occur
- Workflow/business-rule validation remains unchanged and still runs independently.
- Dev UI shows richer standards-validation metadata, including effective validator behavior.
- Unit tests do not require live Matchbox and pass using mocked adapter responses.
- What remains intentionally deferred:
  - live Matchbox CI/integration setup
  - deployment/container orchestration
  - broader validator backend ecosystem
  - arbitrary-spec validator routing

## 7. Risks / notes

- The main risk is leaking Matchbox-specific transport or payload details into workflow code outside the adapter/resolver. Keep all Matchbox request/response handling isolated.
- Another real risk is masking real Matchbox validation findings by falling back too aggressively. Fallback should happen only on transport/config/parsing failure, not on valid Matchbox validation errors.
- Matchbox response shape may vary between deployments/docs. The adapter should tolerate both a single `OperationOutcome` and a list, but stop short of becoming a generic payload normalizer.
- Adding env-driven selection without any current config pattern is intentional here, but it should stay narrow and local rather than spreading config handling across domain models.

## 8. Targeted `docs/development-plan.md` updates after implementation

- In Section 8, change `Current Focus` from the Matchbox adapter slice to the next bounded realism/hardening slice after first external standards validation is available.
- In Section 9, replace `Next Planned Slice` with a bounded follow-on such as: “Deepen Organization/provider-role realism or expand repair execution for `resource_construction` using the stronger validation foundation.”
- In Section 10, keep `Phase 8: Minimal End-to-End PS-CA Workflow` as `In Progress` unless a separate decision moves the project into Phase 9 explicitly.
- In Section 10, add a short Phase 8 or Phase 9 note that the workflow now supports its first real external standards-validation path through an optional Matchbox adapter with local fallback.
- In Section 12, add or refine an assumption that Matchbox is optional infrastructure and the workflow must remain runnable with the local scaffold validator alone.
- In Section 13, add one concise risk only if it is observed during implementation: Matchbox availability or response-shape variance may require a small amount of adapter hardening before broader operational use.
- In Section 16, update the immediate next objective to the next realism/hardening slice after first external standards validation, not Matchbox integration itself.
