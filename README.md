# FHIR Bundle Builder

This repository is currently proving the workflow shape for a PS-CA bundle builder in Microsoft Agent Framework Dev UI.

The implemented slice is intentionally narrow:

- structured top-level workflow input
- deterministic workflow stages for request normalization, PS-CA asset retrieval, bundle schematic generation, and build planning
- inspectable structured artifacts emitted at each stage
- no product UI
- no real bundle population yet
- no real resource construction yet
- no arbitrary-spec ingestion yet

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

## Retrieval-stage output

The `specification_asset_retrieval` stage now emits the first normalized PS-CA asset context for workflow use. In Dev UI you should see:

- normalized package metadata
- workflow-scoped foundational profile summaries
- selected foundational profiles for bundle, composition, patient, practitioner, practitioner role, and organization
- example inventory summary
- selected bundle example summary

## Current slice boundaries

This slice is for workflow shape, PS-CA normalized asset retrieval, the first real schematic artifact, and the first real build plan only.

- The workflow reads existing PS-CA package files deterministically from the repo.
- The spec retrieval stage exposes a normalized PS-CA asset context with foundational profiles, Composition section definitions, and selected example evidence.
- The schematic stage emits a real PS-CA bundle scaffold with:
  - bundle-level scaffold metadata
  - a Composition scaffold
  - required section scaffolds for medications, allergies, and problems
  - explicit resource placeholders
  - explicit schematic relationships and provenance
- The build-plan stage emits a structured deterministic build plan with explicit steps, dependencies, expected inputs, and expected outputs.
- Resource construction emits placeholder resource build results only.
- Validation and repair are placeholder stages used to prove the end-to-end workflow path.

## Schematic-stage output

The `bundle_schematic` stage now emits the first real PS-CA schematic artifact for workflow use. In Dev UI you should see:

- a Bundle scaffold fixed to `document`
- a Composition scaffold fixed to LOINC `60591-5`
- required section scaffolds for medications, allergies, and problems
- placeholders for `Composition`, `Patient`, `PractitionerRole`, `Practitioner`, `Organization`, `MedicationRequest`, `AllergyIntolerance`, and `Condition`
- explicit relationships for:
  - bundle entries
  - Composition subject and author
  - PractitionerRole support links
  - section-entry wiring
- provenance showing which normalized assets and example evidence were used

## Build-plan-stage output

The `build_plan` stage now emits the first real PS-CA planning artifact for workflow use. In Dev UI you should see:

- plan metadata showing deterministic schematic-derived planning and the two-step Composition strategy
- ordered steps for:
  - patient
  - practitioner
  - organization
  - practitioner role
  - composition scaffold
  - medication, allergy, and problem section entries
  - composition finalization
- explicit prerequisite relationships rather than a simple linear chain
- expected step inputs and expected outputs that the later resource-construction slice can consume
- deferred items that remain outside this slice, such as bundle assembly intelligence and element-level population
