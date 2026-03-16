# Demo Scenarios

This repo now standardizes on two canonical end-to-end authored-input demo scenarios for the Dev UI wrapper workflow.

These scenarios are intentionally narrow. They are meant to make repeatable demos, onboarding, and smoke coverage easier to follow without introducing a scenario platform.

Use [operator-guidance.md](./operator-guidance.md) for the current trust-boundary meaning of wrapper readiness/finality labels, thin provider context, and deferred external validation.

## Canonical scenarios

### `rich_reviewed_demo`

- Helper:
  - `build_rich_reviewed_demo_input()`
- What it proves:
  - bounded patient authoring
  - bounded provider authoring
  - bounded authored-record review/edit refinement
  - rich provider path with explicit organization and provider-role relationship
  - deterministic workflow run with selected provider-role relationship
- Current authored inputs:
  - patient: Nora Field
  - provider: Maya Chen at Fraser Cancer Clinic
  - refinement: reviewed patient display name plus medication update, reviewed provider role-label update
- What to highlight in Dev UI:
  - patient/provider authored summaries
  - refinement overview showing edited fields were applied
  - preparation overview showing mapped patient items and rich provider path
  - final summary showing the selected provider-role relationship plus the current readiness/finality interpretation
- How to interpret this scenario:
  - this is the rich provider path demo, not a zero-limitation or externally certified scenario
  - under the default local validator mode, the current final interpretation is still expected to land on `success_external_validation_deferred`
  - current wrapper summaries may also still surface authored-gap or unmapped-fact limitations even though the provider path is rich

### `thin_provider_demo`

- Helper:
  - `build_thin_provider_demo_input()`
- What it proves:
  - bounded patient authoring
  - thin provider path when the prompt does not explicitly support organization/relationship authoring
  - honest preservation of provider gaps and unmapped provider facts
  - deterministic workflow run without inventing richer provider context
- Current authored inputs:
  - patient: Ellis Stone
  - provider: female oncologist in BC
  - refinement: reviewed provider display name only
- What to highlight in Dev UI:
  - provider overview showing thin provider path
  - unresolved provider gaps for missing organization and provider-role relationship
  - preparation overview showing unmapped provider fact counts
  - final summary showing that the workflow still runs without a selected provider-role relationship
- How to interpret this scenario:
  - `thin provider path` is the expected honest outcome when the prompt does not support organization/relationship authoring
  - the thin path is a limited-context state, not a failure state
  - under the default local validator mode, the current final interpretation is still expected to land on `success_external_validation_deferred` rather than full external conformance success

## Where these live

- Canonical scenario builders live in:
  - `src/fhir_bundle_builder/workflows/psca_authored_bundle_demo_workflow/demo_scenarios.py`
- Wrapper smoke coverage imports those helpers directly from:
  - `tests/test_psca_authored_bundle_demo_workflow.py`

## Recommended demo order

1. Run `rich_reviewed_demo` first to show the complete authored-input path.
2. Run `thin_provider_demo` second to show the system stays honest when provider context is incomplete.
