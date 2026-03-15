# FHIR Bundle Builder

This repository is currently proving the workflow shape for a PS-CA bundle builder in Microsoft Agent Framework Dev UI.

The implemented slice is intentionally narrow:

- structured top-level workflow input
- deterministic workflow stages for request normalization, PS-CA asset retrieval, bundle schematic generation, and build planning
- deterministic content-enriched resource construction driven by the real build plan
- deterministic bundle finalization into a real candidate `Bundle` scaffold
- structured dual-channel validation over the candidate bundle scaffold
- optional Matchbox-backed standards validation behind the existing validator boundary
- structured repair decision and bounded retry execution artifacts
- structured patient/clinical request normalization for richer patient-centered realism
- structured provider/org/role request normalization for richer support-resource realism
- provider-context-aware schematic provenance before resource construction begins
- inspectable structured artifacts emitted at each stage
- no product UI
- no full bundle population yet
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

## Standards validator modes

The workflow defaults to the local scaffold-shape standards validator, so local development and tests do not require Matchbox.

- Default local mode:
  - no env vars required
  - runs only the local candidate-bundle scaffold validator
- Optional Matchbox mode:
  - `FHIR_BUNDLE_BUILDER_STANDARDS_VALIDATOR_MODE=matchbox`
  - `FHIR_BUNDLE_BUILDER_MATCHBOX_BASE_URL=http://127.0.0.1:8081/matchbox/fhir`
  - optional `FHIR_BUNDLE_BUILDER_MATCHBOX_TIMEOUT_SECONDS=10`

Example:

```bash
export FHIR_BUNDLE_BUILDER_STANDARDS_VALIDATOR_MODE=matchbox
export FHIR_BUNDLE_BUILDER_MATCHBOX_BASE_URL=http://127.0.0.1:8081/matchbox/fhir
pytest
```

If Matchbox mode is selected but the service is unavailable or misconfigured, the workflow falls back to the local scaffold validator and records that fallback explicitly in the standards-validation result.

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
  - `patient_context`
  - `provider_profile`
  - `provider_context`
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
  - `repair_execution`
- Structured outputs for every stage, plus a final nested run result yielded by `repair_execution`.

## Retrieval-stage output

The `specification_asset_retrieval` stage now emits the first normalized PS-CA asset context for workflow use. In Dev UI you should see:

- normalized package metadata
- workflow-scoped foundational profile summaries
- selected foundational profiles for bundle, composition, patient, practitioner, practitioner role, and organization
- example inventory summary
- selected bundle example summary

## Current slice boundaries

This slice is for workflow shape, PS-CA normalized asset retrieval, the first real schematic artifact, the first real build plan, the first meaningful content-enriched resource-construction path for core clinical resources, the first structured patient/clinical input-normalization path, the first support-resource enrichment for the selected provider-facing author path, the first structured provider/org/role input-normalization path, the first provider-context-aware schematic provenance path, the first candidate-bundle finalization foundation, the first validation foundation, the first optional Matchbox-backed external standards-validation path, the first repair-decision foundation, and the first bounded repair-execution foundation with narrow step-subset repair directives for resource construction plus narrower bundle-finalization-owned reference-alignment findings.

- The workflow reads existing PS-CA package files deterministically from the repo.
- The spec retrieval stage exposes a normalized PS-CA asset context with foundational profiles, Composition section definitions, and selected example evidence.
- The schematic stage emits a real PS-CA bundle scaffold with:
  - bundle-level scaffold metadata
  - a Composition scaffold
  - required section scaffolds for medications, allergies, and problems
  - explicit resource placeholders
  - explicit schematic relationships and provider-context-aware provenance
- The build-plan stage emits a structured deterministic build plan with explicit steps, dependencies, expected inputs, and expected outputs.
- The resource-construction stage emits deterministic content-enriched FHIR-shaped resource scaffolds, per-step construction results, and a registry of the latest scaffold state per placeholder.
- The bundle-finalization stage emits a real candidate `Bundle` scaffold assembled deterministically from the registry and schematic bundle-entry expectations.
- The validation stage emits a structured report with separate standards-validation and workflow-rule results.
- The repair-decision stage emits structured routing recommendations.
- The repair-execution stage can act on a narrow supported subset of those recommendations through one bounded retry pass.
- That bounded retry pass now supports rerunning either:
  - `bundle_finalization`
  - `resource_construction` plus its downstream stages
- `resource_construction` retries now use the first narrow repair-directive model:
  - deterministic build-step-subset directives derived from stable validation finding codes
  - explicit applied directive evidence
  - explicit regenerated vs reused placeholder reporting
  - no element-level patching or generic repair DSL

## Schematic-stage output

The `bundle_schematic` stage now emits the first real PS-CA schematic artifact for workflow use. In Dev UI you should see:

- a Bundle scaffold fixed to `document`
- a Composition scaffold fixed to LOINC `60591-5`
- required section scaffolds for medications, allergies, and problems
- placeholders for `Composition`, `Patient`, `PractitionerRole`, `Practitioner`, `Organization`, `MedicationRequest`, `AllergyIntolerance`, and `Condition`
- `PractitionerRole` placeholder role reflecting the selected provider-role label when normalized provider context supplies one
- explicit relationships for:
  - bundle entries
  - Composition subject and author
  - PractitionerRole support links
  - section-entry wiring
- provenance showing which normalized assets, example evidence, and selected normalized provider/org/role context were used
- provenance showing which normalized patient identity and section-level clinical context counts were available for the run
- summary and placeholder-note text showing whether the run used:
  - legacy patient-profile fallback
  - explicit patient/clinical context with fixed single-entry consumption
  - explicit patient/clinical context with additional structured items still deferred under fixed one-entry-per-section planning
  - legacy provider-profile fallback
  - deterministic single-relationship provider-context selection
  - explicit provider-role relationship selection

## Build-plan-stage output

The `build_plan` stage now emits the first real PS-CA planning artifact for workflow use. In Dev UI you should see:

- plan metadata showing deterministic schematic-derived planning and the incremental Composition section-finalization strategy
- ordered steps for:
  - patient
  - practitioner
  - organization
  - practitioner role
  - composition scaffold
  - medication, allergy, and problem section entries
  - section-specific composition finalization for medications, allergies, and problems
- explicit prerequisite relationships rather than a simple linear chain
- expected step inputs and expected outputs that the later resource-construction slice can consume
- deferred items that remain outside this slice, such as bundle assembly intelligence and element-level population

## Resource-construction-stage output

The `resource_construction` stage now emits the first real scaffold-oriented construction artifact for workflow use. In Dev UI you should see:

- construction mode metadata showing deterministic content-enriched construction
- ordered per-step construction results aligned to the build plan
- FHIR-shaped scaffolds with narrow deterministic content for core patient, composition, section-entry, and selected provider-facing support resources
- deterministic local references such as:
  - `Patient/patient-1`
  - `PractitionerRole/practitionerrole-1`
  - section-entry references attached to `Composition`
- deterministic placeholder content such as:
  - a Patient identifier and display name
  - optional Patient gender and birth date when structured patient context supplies them
  - a Practitioner identifier and display name from normalized provider identity context
  - an Organization identifier system/value and name when selected provider-organization context is available
  - a PractitionerRole relationship identifier system/value plus a narrow author label from the selected provider-role relationship when available
  - a Composition status and title
  - section-entry status and text content for medications, allergies, and problems, using structured patient clinical profile text when exactly one matching item is available
- normalized patient-context inspectability showing the selected patient identity and any single-entry clinical profile items currently consumable by the fixed one-entry-per-section workflow
- schematic-level patient-context inspectability showing available item counts for medications, allergies, and problems even when the current planner still keeps one placeholder per required section
- normalized provider-context inspectability showing the selected provider, selected organization, and selected provider-role relationship when available
- a resource registry showing the latest scaffold state per placeholder
- explicit incremental `Composition` behavior:
  - scaffold creation
  - deterministic medications section attachment
  - deterministic allergies section attachment
  - deterministic problems section attachment
- unresolved and deferred fields called out explicitly rather than implied

## Bundle-finalization-stage output

The `bundle_finalization` stage now emits the first real candidate-bundle artifact for workflow use. In Dev UI you should see:

- bundle-finalization metadata showing deterministic registry-driven assembly
- a real FHIR-shaped `Bundle` scaffold with:
  - `resourceType = Bundle`
  - deterministic `id`
  - deterministic local `identifier`
  - deterministic synthetic `timestamp`
  - `meta.profile`
  - `type = document`
  - ordered `entry.fullUrl` + `entry.resource` items
- deterministic entry ordering derived from the bundle schematic’s `bundle_entry` relationships
- explicit entry assembly details for each placeholder resource
- deterministic `urn:uuid:` fullUrls aligned to internal resource references in the assembled candidate bundle copy
- explicit local candidate-bundle identity evidence rather than deferred bundle-level identity fields
- a clear distinction between the candidate bundle scaffold and a future validated bundle

## Validation-stage output

The `validation` stage now emits the first real structured validation artifact for workflow use. In Dev UI you should see:

- overall validation status derived from deterministic channel results
- a separate standards-validation section with:
  - validator identity
  - requested validator mode
  - attempted validator ids
  - whether external Matchbox validation actually executed
  - whether local fallback was used
  - checks run
  - findings
  - explicit deferred areas
- a separate workflow/business-rule validation section with:
  - deterministic bundle/document checks
  - deterministic bundle identity/fullUrl checks
  - narrower Composition scaffold/content checks for:
    - summary type coding
    - core scaffold content (`status`, `title`)
    - subject reference alignment
    - author reference alignment
  - support-resource identity/content checks for:
    - `Practitioner`
    - `Organization` when selected organization context exists
    - `PractitionerRole` selected relationship identity when selected provider-role context exists
    - `PractitionerRole` author-context label
  - section-specific deterministic Composition section-presence checks for medications, allergies, and problems
  - resource-specific placeholder-content checks for `MedicationRequest`, `AllergyIntolerance`, and `Condition`
  - resource-specific non-Composition source-reference contribution checks for:
    - `PractitionerRole.practitioner`
    - `PractitionerRole.organization`
    - `MedicationRequest.subject`
    - `AllergyIntolerance.patient`
    - `Condition.subject`
  - resource-specific non-Composition exact fullUrl alignment checks for:
    - `PractitionerRole.practitioner`
    - `PractitionerRole.organization`
    - `MedicationRequest.subject`
    - `AllergyIntolerance.patient`
    - `Condition.subject`
  - section-specific Composition section-entry exact fullUrl alignment checks for:
    - medications
    - allergies
    - problems
  - findings tied to bundle structure and PS-CA expectations
  - explicit deferred areas
- counts for errors, warnings, and informational findings
- validation evidence linking back to the candidate bundle, schematic, build plan, and resource construction artifacts
- clear standards-channel provenance showing whether validation ran locally, through Matchbox, or through local fallback after Matchbox was unavailable

## Repair-decision-stage output

The `repair_decision` stage now emits the first real structured repair-routing artifact for workflow use. In Dev UI you should see:

- an overall repair decision such as:
  - `external_validation_pending`
  - `repair_recommended`
  - `complete_no_repair_needed`
- a recommended repair target and next workflow stage when an internal repair is appropriate
- per-finding routing records that show:
  - the original validation channel and severity
  - the stable finding code
  - the deterministic route target
  - whether the finding is actionable in the current workflow
- explicit separation between internal repair recommendations and deferred external standards-validation dependencies
- when `resource_construction` is recommended:
  - a structured deterministic repair directive
  - trigger finding codes
  - target build-step ids
  - target placeholder ids
  - single-support-resource targeting for Practitioner, Organization, and PractitionerRole content repairs
  - scaffold-plus-finalizers targeting for Composition scaffold/content issues where replaying the scaffold step still requires replaying section-finalize steps
  - section-specific Composition finalize targeting when one or more required Composition sections are missing
  - single-resource section-entry targeting when only one section-entry placeholder-content rule fails
  - section-specific Composition finalize targeting when one Composition section-entry exact fullUrl alignment rule fails
- when `bundle_finalization` is recommended:
  - narrower resource-specific exact fullUrl alignment findings for non-Composition references whose local source contribution was already correct
- when `resource_construction` is recommended for non-Composition reference ownership:
  - single-resource targeting for the step that owns the local reference contribution before downstream fullUrl rewriting
- a clear distinction between repair recommendation and actual repair execution, which is still deferred

## Repair-execution-stage output

The `repair_execution` stage now emits the first real bounded retry artifact for workflow use. In Dev UI you should see:

- the incoming repair recommendation target and whether it is retry-eligible in this slice
- one of these retry outcomes:
  - `executed`
  - `deferred`
  - `not_needed`
  - `unsupported`
- for executed retries:
  - the applied `resource_construction` repair directive when that target is retried
  - the regenerated `resource_construction` artifact when that target is retried
  - the rerun stage ids
  - the regenerated artifact keys
  - the post-retry resource construction result, candidate bundle, validation report, and repair decision
  - whether the construction rerun was:
    - `full_build`
    - `targeted_repair`
  - which placeholder resources were regenerated versus reused
- for non-executed retries:
  - an explicit deferred or unsupported reason
- a clear distinction between:
  - the original first-pass artifacts
  - the bounded post-retry artifacts nested under `repair_execution`
- a single-pass policy only; no recursive retry loop is implemented in this slice
- support for only these executable internal retry targets:
  - `bundle_finalization`
  - `resource_construction`
