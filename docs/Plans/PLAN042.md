1. Repo assessment

- The repo already has the factual material needed for a strong operator-guidance pass:
  - README explains setup, the two Dev UI workflows, current capabilities, standards-validator modes, and the current demo summaries
  - [`docs/demo-scenarios.md`](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/demo-scenarios.md) explains the two canonical wrapper scenarios and what to highlight
  - [`docs/development-plan.md`](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md) already records key assumptions and risks around wrapper summaries being derived and non-blocking
  - the wrapper models/tests now expose stable terminology for:
    - `ready`
    - `ready_with_limitations`
    - `success_low_concern`
    - `success_with_limitations`
    - `success_external_validation_deferred`
    - `failure_or_incomplete`
- What the docs already explain well:
  - the repo is workflow-first and bounded
  - the wrapper flow is a second Dev UI workflow, not the product
  - the two canonical demo scenarios exist and are repeatable
  - Matchbox fallback and local validator behavior are documented at a basic level
- What interpretation/operator guidance is still weak:
  - README mixes core workflow facts, wrapper behavior, and operator interpretation in one long document
  - there is no single focused guide that explains what current statuses mean in practice
  - “thin provider path” is mentioned, but not fully explained as an honest upstream-limitation state versus an error state
  - “deferred external validation” is mentioned in code/tests and lightly in README, but not translated into an operator-facing trust statement
  - wrapper readiness/finality labels now exist, but there is no explicit guide saying they are advisory summaries derived from current artifacts rather than workflow enforcement semantics
  - the demo-scenarios doc still highlights outcomes, but not how to interpret them from a trust/quality perspective
- Constraints that matter now:
  - this must stay documentation-first and bounded
  - no behavioral changes to workflow, wrapper, authoring, or orchestration
  - no broad docs rewrite
  - no overclaiming beyond the current typed artifacts and current validator behavior

2. Proposed workflow-quality / operator-guidance scope

- Add one focused interpretation/operator guide for the current repo state.
- Refine README so it clearly points operators/reviewers to:
  - the core deterministic workflow
  - the wrapper demo workflow
  - the new interpretation guide
- Refine the demo-scenarios doc so each canonical scenario includes not only “what it proves” but also “how to interpret the result.”
- Exact interpretation questions this slice should answer:
  - what does the core deterministic workflow actually guarantee today?
  - what does the authored-input wrapper add, and what does it explicitly not add?
  - what does `thin provider path` mean?
  - what does `ready_with_limitations` mean?
  - what does `success_external_validation_deferred` mean?
  - when is a run good enough for demo/testing?
  - when should a run be treated as limited, partial, or not suitable for stronger trust claims?
- Docs affected:
  - README
  - `docs/demo-scenarios.md`
  - one new focused guide in `docs/`
  - `docs/development-plan.md`
- What should remain deferred:
  - troubleshooting for every internal stage
  - a broader docs taxonomy or docs site
  - automated doc testing framework
  - changes to status names or workflow behavior

3. Proposed documentation architecture

- Use **README + one focused guide + targeted demo-scenario updates**.
- Recommended new guide:
  - [`docs/operator-guidance.md`](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/operator-guidance.md)
- Why one focused guide is justified:
  - README is already long and mixes setup, capabilities, and inspectability
  - the current problem is interpretation drift, not missing setup instructions
  - a single guide is cleaner than stuffing trust-boundary explanations into README prose
- How to separate the documentation concerns:
  - README:
    - concise pointer-level guidance
    - explain where to go for operator interpretation
    - keep launch/setup and workflow-surface overview
  - new operator guide:
    - core deterministic workflow guarantees
    - wrapper-flow additions and non-guarantees
    - interpretation of readiness and final summaries
    - “good enough for demo/testing” guidance
    - common current limitation states
  - demo-scenarios doc:
    - scenario-specific interpretation guidance
    - what result pattern to expect from `rich_reviewed_demo` vs `thin_provider_demo`
- Keep this small and truthful:
  - no new product language
  - no promise that wrapper summaries are enforcement or certification
  - no claim that passing workflow validation equals full external conformance validation
  - explicitly distinguish:
    - typed workflow artifacts
    - wrapper-derived summaries
    - deferred external validation status

4. File-level change plan

- Create [`docs/operator-guidance.md`](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/operator-guidance.md)
  - focused current-state interpretation guide for operators, reviewers, and demo users
- Update [`README.md`](/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md)
  - add concise boundary clarifications and point readers to the operator guide
- Update [`docs/demo-scenarios.md`](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/demo-scenarios.md)
  - add “how to interpret this scenario” guidance for rich vs thin paths
- Update [`docs/development-plan.md`](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md)
  - move focus to workflow-quality/operator-guidance documentation
- Optional only if clearly needed during implementation:
  - a very small README wording alignment in places where wrapper summaries might currently read too strongly
- No planned code changes or behavioral tests for this slice by default.

5. Step-by-step implementation plan

1. Draft the focused operator guide.
   - keep it short and current-state only
   - organize it around interpretation questions rather than architecture restatement
2. In that guide, add a “Core vs Wrapper” section.
   - core workflow:
     - deterministic bundle-building path
     - validation and repair artifacts
     - no authoring, no UI semantics, no wrapper summaries
   - wrapper workflow:
     - authoring/refinement/orchestration host
     - derived readiness/finality summaries
     - still not a source of truth
3. Add a “Current Trust Boundaries” section.
   - explain:
     - `thin provider path`
     - unresolved authored gaps
     - unmapped authored facts
     - deferred external validation
     - fallback-based standards validation when applicable
4. Add a “How to Read Current Wrapper Labels” section.
   - define:
     - `ready`
     - `ready_with_limitations`
     - `success_low_concern`
     - `success_with_limitations`
     - `success_external_validation_deferred`
     - `failure_or_incomplete`
   - state explicitly that these are wrapper-derived advisory interpretations
5. Add a “Good Enough for Demo/Testing” section.
   - explain when a run is acceptable for:
     - demoing bounded authored-input-to-workflow behavior
     - inspecting deterministic artifact flow
     - showing honest thin-path behavior
   - explain when a run should not be overclaimed as stronger conformance or stronger upstream completeness
6. Update README.
   - add a short “Interpretation Guidance” pointer section
   - clarify that the wrapper flow supplements, but does not redefine, the core workflow
   - point users to the operator guide and demo-scenarios doc
7. Update `docs/demo-scenarios.md`.
   - for `rich_reviewed_demo`, explain that the scenario is still expected to remain limitation-bearing today because current wrapper and validation boundaries are intentionally honest and external validation remains deferred in local default mode
   - for `thin_provider_demo`, explain that “thin” is a truthful limited-context state, not a failure
8. Update `docs/development-plan.md`.
   - move current focus to operator-guidance/documentation refinement
   - adjust next planned slice and immediate next objective accordingly
   - add only small new assumptions/risks if the documentation work surfaces a real one
9. Only if implementation reveals obvious doc/code terminology drift:
   - make a tiny alignment tweak in wording, but do not change behavior or status labels
10. Validate by reviewing the updated docs against:
   - current README wording
   - current canonical demo scenarios
   - current wrapper summary terminology in code/tests

6. Definition of Done

- The repo has one focused operator/interpretation guide for the current workflow and wrapper state.
- README clearly distinguishes:
  - the core deterministic workflow
  - the authored-input wrapper flow
  - where to read current interpretation guidance
- The demo-scenarios doc now explains not just what each scenario shows, but how to interpret its outcome truthfully.
- A reviewer or demo operator can now answer, from docs alone:
  - what the core workflow guarantees
  - what the wrapper adds
  - what `thin provider path` means
  - what `deferred external validation` means
  - what wrapper readiness/finality labels imply
  - when a run is good enough for demo/testing versus still limited
- Still out of scope:
  - behavior changes
  - new UI features
  - broader docs rewrite
  - validation semantics changes
  - documentation platform work

7. Risks / notes

- The main risk is over-documenting the wrapper summaries as if they were stronger than the underlying artifacts. The new guide must keep them explicitly advisory and derived.
- A second risk is duplicating the same explanation across README and the new guide. README should stay pointer-oriented; the focused guide should hold the interpretation detail.
- A third risk is accidentally softening the repo’s honest limitations. The guide should preserve that:
  - thin provider path is limited context, not rich context in disguise
  - deferred external validation is not equivalent to completed external conformance validation
- A fourth risk is making the docs too broad for a bounded slice. Keep the guide centered on current statuses, trust boundaries, and demo/operator interpretation only.

8. Targeted `docs/development-plan.md` updates after implementation

- Section 8 `Current Focus`
  - change to: implement a workflow-quality and operator-guidance documentation pass so the deterministic core workflow, authored-input wrapper flow, and current trust/limitation boundaries are easier to interpret correctly
- Section 9 `Next Planned Slice`
  - change to: after operator-guidance/documentation refinement, decide whether to return to a narrow workflow-quality slice or add one more small demo-usability clarification pass
- Section 10 Phase 8 note
  - append that the repo now includes focused operator guidance documenting the distinction between core workflow artifacts, wrapper-derived readiness/finality summaries, and deferred external validation states
- Section 12 `Known Early Assumptions`
  - add that operator guidance should describe wrapper readiness/finality labels as advisory interpretations layered over current typed artifacts, not as new workflow guarantees
  - add that current demo/operator guidance should prefer one focused interpretation guide plus targeted README/demo-doc pointers rather than a broader docs-platform restructure
- Section 13 `Known Early Risks`
  - add that current documentation may overstate demo-wrapper trust if core workflow guarantees, wrapper-derived labels, and deferred external validation are not kept clearly separated
  - add that interpretation guidance may drift from the actual wrapper terminology unless the focused guide stays aligned to the current typed summary labels and canonical demo scenarios
- Section 16 `Immediate Next Objective`
  - update to: complete the workflow-quality and operator-guidance documentation pass and prove the repo’s current deterministic workflow guarantees, wrapper additions, and limitation/trust boundaries are documented clearly enough for demos, reviews, and maintenance
