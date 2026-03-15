## Demo-Scenario And Documentation Consolidation

### 1. Repo assessment

- The repo is already demo-capable:
  - bounded patient/provider authoring exists
  - authored-input orchestration exists
  - the Dev UI wrapper flow can author, refine, prepare, and run the deterministic workflow end to end
  - wrapper-flow smoke tests already exercise real rich/thin paths
- What is already usable:
  - `tests/test_psca_authored_bundle_demo_workflow.py` contains the two strongest end-to-end demo examples
  - authoring-builder tests contain good supporting prompts for patient/provider behavior
  - README explains how to launch Dev UI and what stages exist
- What is fragmented or hard to reuse consistently:
  - the canonical demo inputs are implicit, buried inside tests
  - README describes the flow, but not which exact scenarios to run or what each proves
  - there is no single named source for “the recommended demo scenarios”
  - scenario naming is inconsistent across tests (`pytest-demo-*`, `pytest-authored-demo-*`, etc.)
  - there is no short demo guide that maps scenario -> purpose -> what to highlight
- Constraints that matter now:
  - keep this as consolidation, not a new feature slice
  - avoid a large fixture/scenario platform
  - do not change workflow/authoring/orchestration semantics
  - keep the smallest useful alignment between docs and tests

### 2. Proposed demo-scenario consolidation scope

- Standardize exactly **two** canonical demo scenarios in this slice.
  - Two is sufficient because they cover the current meaningful demo distinctions without creating a scenario catalog.
- Canonical scenario 1: `rich_reviewed_demo`
  - What it proves:
    - full authored-input path
    - patient and provider authoring
    - authored-record refinement/editing
    - rich provider path with organization + provider-role relationship
    - successful deterministic workflow run with selected provider relationship
  - Suggested inputs:
    - reuse the existing Nora Field / Maya Chen / Fraser Cancer Clinic scenario already in the wrapper smoke test
- Canonical scenario 2: `thin_provider_demo`
  - What it proves:
    - patient authoring plus thin provider path
    - honest preservation of missing organization/relationship gaps
    - unmapped provider facts remain visible
    - workflow still runs cleanly without inventing richer provider context
  - Suggested inputs:
    - reuse the existing Ellis Stone / “female oncologist in BC” scenario already in the wrapper smoke test
- What this slice should add/refine:
  - one small canonical scenario helper module
  - one short demo-scenarios doc
  - README pointers to those scenarios
  - wrapper smoke tests rewritten to use the named scenario helpers
- What should remain deferred:
  - more scenarios
  - random scenario generation
  - persistence-backed scenario storage
  - a general fixture framework
  - new domain/business behavior

### 3. Proposed consolidation architecture

- Put canonical scenario definitions in a **tiny shared helper module** under the existing wrapper workflow package:
  - `src/fhir_bundle_builder/workflows/psca_authored_bundle_demo_workflow/demo_scenarios.py`
- Keep the helper intentionally small:
  - one small typed metadata model or named tuple/dataclass for scenario name + purpose
  - two builder functions that return fully formed `AuthoredBundleDemoInput`
  - no registry framework, no loaders, no discovery system
- Recommended public surface:
  - `build_rich_reviewed_demo_input() -> AuthoredBundleDemoInput`
  - `build_thin_provider_demo_input() -> AuthoredBundleDemoInput`
  - optional small metadata constants for:
    - scenario id
    - short title
    - what it proves
    - key highlights
- How tests and docs should reference them:
  - wrapper smoke tests should import and use those two helpers directly
  - README should point readers to the scenario doc and name the two canonical demos
  - `docs/demo-scenarios.md` should document:
    - scenario name
    - exact helper to use
    - what path it exercises
    - what to point out in Dev UI
- How to keep this small and non-framework-like:
  - no scenario inheritance
  - no parameterized scenario builder API beyond two concrete functions
  - no fixture package unless the helper module clearly needs one later
  - keep authoring-only unit-test prompts where they are; only standardize end-to-end demo scenarios now

### 4. File-level change plan

- Create `/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_authored_bundle_demo_workflow/demo_scenarios.py`
  - defines the two canonical wrapper-flow demo inputs and minimal scenario metadata
- Update `/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_authored_bundle_demo_workflow/__init__.py`
  - export the canonical scenario helpers if useful for direct import
- Update `/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_psca_authored_bundle_demo_workflow.py`
  - replace inline scenario construction with the named canonical helpers
  - keep the same behavioral assertions
- Create `/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/demo-scenarios.md`
  - short canonical demo guide tied to the current Dev UI wrapper flow
- Update `/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md`
  - add a concise “recommended demo scenarios” pointer
- Update `/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md`
  - move current focus from summary polish to demo-scenario/documentation consolidation

### 5. Step-by-step implementation plan

1. Extract the current rich and thin wrapper smoke-test inputs into a tiny canonical scenario helper module.
2. Give each scenario a stable, honest name:
   - `rich_reviewed_demo`
   - `thin_provider_demo`
3. Keep each helper fully explicit.
   - return a complete `AuthoredBundleDemoInput`
   - reuse today’s working prompts and review edits exactly, unless a tiny naming cleanup is needed
4. Add minimal scenario metadata in the same module.
   - short title
   - one-sentence purpose
   - key demo path tags such as `rich_provider`, `thin_provider`, `edited_record_path`
5. Rewrite the wrapper smoke tests to import the canonical scenario helpers instead of building inputs inline.
6. Add `docs/demo-scenarios.md`.
   - explain the two canonical scenarios
   - state what each proves
   - list what to highlight in the Dev UI output:
     - rich provider path
     - thin provider path
     - edited-record path
     - mapped/unmapped visibility
     - final validation/bundle outcome
7. Update README to point to the new demo-scenarios doc and mention the two recommended demos by name.
8. Update development-plan.md once tests are green.

### 6. Definition of Done

- The repo has a single small source of truth for the recommended end-to-end demo scenarios.
- Two canonical demo scenarios are named and documented:
  - one rich reviewed demo
  - one thin provider demo
- Wrapper smoke tests use those canonical helpers rather than duplicating inline demo inputs.
- README clearly points users to the canonical demo scenarios.
- A new short demo guide explains:
  - which scenario to run
  - what it proves
  - what to highlight in the current Dev UI flow
- What becomes easier:
  - repeatable demos
  - onboarding to the authored-input wrapper flow
  - understanding which scenario exercises which path
  - keeping docs and smoke coverage aligned
- Still out of scope:
  - scenario catalogs
  - random scenario generation
  - persistence-backed demo storage
  - new workflow/domain behavior
  - a general fixture platform

### 7. Risks / notes

- The main risk is overgrowing this into a fixture framework. Keep it to two concrete helpers and one short doc.
- A second risk is letting docs drift from tests again. The smoke tests should import the canonical scenario helpers directly.
- A third risk is picking too many scenarios. Two is enough for the current wrapper-flow story because the rich scenario already covers the edited-record path.
- A fourth risk is putting demo-only material into core authoring/orchestration modules. Keep it scoped to the wrapper workflow package and docs.

### 8. Targeted `docs/development-plan.md` updates after implementation

- Section 8 `Current Focus`
  - change to: implement a thin demo-scenario and documentation consolidation pass so the current authored-input demo flow is easier to use repeatedly and explain consistently
- Section 9 `Next Planned Slice`
  - change to: after demo-scenario/documentation consolidation, decide whether to add one more narrow Dev UI usability pass or return to a workflow-quality/documentation-focused slice
- Section 10 Phase 8 note
  - append that the repo now includes two canonical named authored-input demo scenarios aligned across docs and wrapper smoke coverage
- Section 12 `Known Early Assumptions`
  - add that the current demo story is intentionally standardized on two canonical authored-input scenarios rather than a broader scenario catalog
  - add that canonical demo-scenario helpers should stay small and explicit, and remain scoped to the wrapper workflow/demo layer
- Section 13 `Known Early Risks`
  - add that demo-scenario consolidation may drift into a larger fixture platform unless the shared scenario layer remains limited to the current canonical examples
  - add that documentation value will regress quickly if canonical scenario docs and wrapper smoke tests stop sharing the same named inputs
- Section 16 `Immediate Next Objective`
  - update to: complete the demo-scenario and documentation consolidation pass and prove the current authored-input demo flow is repeatable and consistently documented through a small canonical scenario set
