# FHIR Bundle Builder

This repository is currently proving the workflow shape for a PS-CA bundle builder in Microsoft Agent Framework Dev UI.

The implemented slice is intentionally narrow:

- structured top-level workflow input
- deterministic placeholder executors for the major workflow stages
- inspectable structured artifacts emitted at each stage
- no product UI
- no real PS-CA asset normalization yet
- no real bundle generation yet

## Repository shape

- `docs/` contains architecture, workflow, and planning guidance.
- `fhir/ca.infoway.io.psca-2.1.1-dft/` contains the PS-CA source package already present in the repo.
- `src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/` contains the workflow skeleton.
- `entities/psca_bundle_builder_workflow/` exports the workflow for Dev UI discovery.

## Setup

Use the existing virtual environment in the repo root.

```bash
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e '.[dev]'
```

## Run the smoke test

```bash
pytest
```

## Launch in Dev UI

```bash
source .venv/bin/activate
devui ./entities --reload --port 8080 --no-open
```

Then open [http://127.0.0.1:8080](http://127.0.0.1:8080).

## What to expect in Dev UI

- One workflow entity named `PS-CA Bundle Builder Skeleton`.
- A structured top-level input form with:
  - `specification`
  - `patient_profile`
  - `provider_profile`
  - `request`
  - `workflow_options`
- Sequential executor steps in this order:
  - `request_normalization`
  - `specification_asset_retrieval`
  - `bundle_schematic`
  - `build_plan`
  - `resource_construction`
  - `bundle_finalization`
  - `validation`
  - `repair_decision`
- Structured outputs for every stage, plus a final nested run result yielded by `repair_decision`.

## Current slice boundaries

This slice is for workflow shape and inspectability only.

- The workflow reads existing PS-CA package files deterministically from the repo.
- The spec retrieval stage exposes a stub context and explicitly does not normalize assets yet.
- Resource construction emits placeholder resource build results only.
- Validation and repair are placeholder stages used to prove the end-to-end workflow path.
