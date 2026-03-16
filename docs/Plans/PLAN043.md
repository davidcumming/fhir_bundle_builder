1. Repo assessment

- The current canonical status vocabulary is already stable in the wrapper models:
  - `ready`
  - `ready_with_limitations`
  - `success_low_concern`
  - `success_with_limitations`
  - `success_external_validation_deferred`
  - `failure_or_incomplete`
  - provider path mode: `rich` / `thin`
- The wrapper tests already anchor those typed labels well through `readiness_summary`, `run_interpretation_summary`, and `final_summary` assertions.
- What is already stable:
  - typed status literals in [`models.py`](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_authored_bundle_demo_workflow/models.py)
  - limitation-label keys like `thin_provider_path`, `patient_gaps_remain`, `external_validation_deferred` in [`executors.py`](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_authored_bundle_demo_workflow/executors.py)
  - wrapper smoke-test expectations in [`test_psca_authored_bundle_demo_workflow.py`](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_authored_bundle_demo_workflow.py)
- What is still drifting or ambiguous:
  - prose varies between `deferred external validation` and `external validation remains deferred`
  - prose varies between `thin provider path`, `thin-provider path`, and `richer provider-path demo`
  - docs sometimes say `limitation-bearing` rather than using the current wrapper labels directly
  - wrapper prose uses natural-language summaries like `Ready to run with limitations` and `Run completed but external validation remains deferred`, but there is no single explicit rule saying these are sentence-case renderings of the typed labels
  - `warning`, `limitations`, and `deferred` are close concepts in docs, but they are not yet cleanly separated:
    - `warnings` belong to validation status/results
    - `limitations` belong to wrapper advisory interpretation
    - `deferred external validation` is a distinct current-state interpretation
- Constraints that matter now:
  - keep existing typed labels as the anchor
  - do not change behavior to match wording
  - do not invent a new status taxonomy
  - keep the cleanup bounded to wrapper-facing code/tests/docs

2. Proposed terminology/status consistency scope

- Audit and refine terminology across:
  - wrapper typed labels and docstrings
  - wrapper stage `summary` / `placeholder_note` prose
  - wrapper smoke tests
  - README
  - `docs/demo-scenarios.md`
  - `docs/operator-guidance.md`
  - `docs/development-plan.md`
- Treat these as canonical terms/labels:
  - typed labels:
    - `ready`
    - `ready_with_limitations`
    - `success_low_concern`
    - `success_with_limitations`
    - `success_external_validation_deferred`
    - `failure_or_incomplete`
  - path terms:
    - `rich provider path`
    - `thin provider path`
  - interpretation terms:
    - `deferred external validation`
    - `advisory`
    - `good enough for demo/testing`
- Canonical prose renderings for stage summaries should be:
  - `ready` -> `Ready to run`
  - `ready_with_limitations` -> `Ready to run with limitations`
  - `success_low_concern` -> `Run completed with low concern`
  - `success_with_limitations` -> `Run completed with limitations`
  - `success_external_validation_deferred` -> `Run completed with deferred external validation`
  - `failure_or_incomplete` -> `Run incomplete or failed`
- What should remain deferred:
  - broader naming cleanup outside the wrapper/demo/operator-guidance surface
  - any rename of typed literals
  - validation terminology redesign
  - a large glossary system

3. Proposed consistency architecture

- Anchor canonical terminology in the existing wrapper model literals.
  - `models.py` remains the source of truth for status names.
- Add one small “canonical terminology” note to `docs/operator-guidance.md`.
  - It should explicitly say:
    - typed labels are canonical
    - human-readable stage text is a sentence-case rendering of those labels
    - docs may use explanatory prose, but should prefer the canonical label on first mention
- Relationship between surfaces:
  - models:
    - canonical labels only
  - executors:
    - short human-readable sentences mapped one-to-one to canonical labels
  - tests:
    - assert typed labels, not long prose strings
    - only assert prose if a very small, stable prefix check is clearly worth it
  - README/demo docs/operator guide:
    - use canonical labels in backticks on first mention
    - use prose variation only after the canonical label is established
- Acceptable prose variation:
  - sentence-case rendering is acceptable in stage text
  - short explanatory phrasing is acceptable in docs after the canonical label is named
- Not acceptable:
  - introducing new near-synonyms like `warning-bearing` as a wrapper status term
  - using `limitation-bearing` where a canonical label is clearer
  - using hyphenated variants like `thin-provider path` when the stable phrase is `thin provider path`

4. File-level change plan

- Update [`src/fhir_bundle_builder/workflows/psca_authored_bundle_demo_workflow/executors.py`](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_authored_bundle_demo_workflow/executors.py)
  - tighten stage `summary` / `placeholder_note` wording to match the canonical prose renderings
  - normalize `deferred external validation` phrasing
  - normalize `thin provider path` / `rich provider path` phrasing
- Update [`src/fhir_bundle_builder/workflows/psca_authored_bundle_demo_workflow/models.py`](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_authored_bundle_demo_workflow/models.py)
  - add only a very small docstring/comment clarification if needed that typed labels are the canonical wrapper vocabulary
  - no literal changes planned
- Update [`tests/test_psca_authored_bundle_demo_workflow.py`](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_authored_bundle_demo_workflow.py)
  - keep typed-label assertions as the primary contract
  - make only tiny wording/comment alignment edits if needed
  - do not add brittle long-prose assertions by default
- Update [`README.md`](/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md)
  - align wrapper terminology to canonical labels
  - add a short note that typed labels are canonical and prose is summarized
- Update [`docs/demo-scenarios.md`](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/demo-scenarios.md)
  - normalize scenario interpretation wording to the canonical status terms
- Update [`docs/operator-guidance.md`](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/operator-guidance.md)
  - add the small canonical terminology section
  - align trust-language to the typed labels
- Update [`docs/development-plan.md`](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md)
  - move focus to terminology/status consistency audit
  - add one small assumption/risk only if the audit reveals a real one

5. Step-by-step implementation plan

1. Audit the current wrapper-facing terminology surface and make a short internal mapping table:
   - typed label
   - canonical sentence-case rendering
   - currently used variants that should be normalized
2. Confirm that no typed literal changes are needed.
   - keep the current model literals unchanged unless a real ambiguity is discovered
3. Normalize wrapper executor prose.
   - change any wording that drifts from the canonical sentence-case renderings
   - prefer `deferred external validation`
   - prefer `thin provider path` / `rich provider path`
   - remove avoidable near-synonyms like `limitation-bearing` from stage-facing prose
4. Add one compact “canonical terminology” subsection to `docs/operator-guidance.md`.
   - list the canonical typed labels
   - state that stage prose is a human-readable rendering of those labels
   - clarify that `warnings` belong to validation output, while `limitations` and `deferred external validation` belong to wrapper interpretation
5. Align README to that terminology.
   - make wrapper terminology consistent with the operator guide
   - add a short pointer that typed labels are canonical
6. Align `docs/demo-scenarios.md`.
   - update scenario interpretation text to use the canonical terms directly
   - keep scenario guidance concise and truthful
7. Review the wrapper smoke tests.
   - keep the current typed-label assertions
   - only update wording/comments if they drift
   - avoid turning prose into a brittle contract unless a short stable check is clearly useful
8. Update `docs/development-plan.md`.
   - set current focus to the terminology/status consistency audit
   - set next planned slice accordingly
   - add any new assumption/risk only if truly surfaced by the audit
9. Validate by doing one final cross-read of:
   - wrapper models
   - wrapper executor summaries/notes
   - wrapper tests
   - README
   - demo scenarios
   - operator guidance
   - development plan

6. Definition of Done

- The wrapper’s typed labels remain unchanged and are clearly treated as canonical.
- Wrapper stage prose uses one stable, sentence-case rendering of the canonical labels.
- README, demo scenarios, operator guidance, and development-plan wording all use the same status vocabulary consistently.
- `thin provider path` and `rich provider path` appear consistently without competing variants.
- `deferred external validation` is used consistently as the preferred phrase.
- `limitations`, `warnings`, and `deferred external validation` are more clearly separated in docs.
- Wrapper smoke tests continue to anchor the canonical typed labels without becoming prose-fragile.
- What becomes more consistent:
  - demo narration
  - reviewer interpretation
  - future maintenance of wrapper summary wording
  - status vocabulary across code, tests, and docs
- Still out of scope:
  - behavior changes
  - literal status renames
  - broad repo-wide naming cleanup
  - new domain semantics

7. Risks / notes

- The main risk is overcorrecting prose into something less readable. Keep typed labels canonical, but let stage text remain human-readable sentence case.
- A second risk is making docs stricter than the actual code surface. The audit should follow the current model literals, not invent a more elegant taxonomy.
- A third risk is adding prose-string test assertions that become brittle. Keep tests anchored to typed labels unless a very small stable string check is clearly justified.
- A fourth risk is conflating wrapper interpretation with validation semantics. Preserve the distinction:
  - validation warnings are downstream workflow artifacts
  - wrapper limitations are derived/advisory
  - deferred external validation is a specific current-state interpretation

8. Targeted `docs/development-plan.md` updates after implementation

- Section 8 `Current Focus`
  - change to: implement a terminology and status consistency audit so the current wrapper labels, stage prose, tests, and docs use one stable truthful vocabulary
- Section 9 `Next Planned Slice`
  - change to: after terminology/status consistency cleanup, decide whether to return to a narrow workflow-quality slice or keep consolidating small wrapper/demo maintainability details
- Section 10 Phase 8 note
  - append that the repo now treats the current wrapper typed status labels as canonical and aligns stage prose/docs to those labels without changing behavior
- Section 12 `Known Early Assumptions`
  - add that wrapper typed labels should remain the canonical anchor for wrapper-facing terminology, while stage prose and docs may use only closely aligned sentence-case renderings
  - add that a small terminology note in operator guidance is preferred over introducing a broader glossary system
- Section 13 `Known Early Risks`
  - add that terminology drift between typed labels and prose may slowly overstate or blur current trust boundaries unless wrapper docs and stage text stay anchored to the canonical labels
  - add that prose-focused testing can become brittle unless typed labels remain the primary asserted contract
- Section 16 `Immediate Next Objective`
  - update to: complete the terminology and status consistency audit and prove the current wrapper/demo vocabulary is aligned across code, tests, and docs without changing workflow behavior
