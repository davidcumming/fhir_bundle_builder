# Operator Guidance

This guide explains how to interpret the current deterministic PS-CA workflow and the thin authored-input wrapper flow without overclaiming what the repo currently guarantees.

It is intentionally narrow. It documents the current trust boundaries and status labels; it does not introduce new semantics or new enforcement behavior.

## Core vs wrapper

### Core deterministic workflow

The core workflow is `PS-CA Bundle Builder Skeleton`.

What it currently guarantees:

- a deterministic PS-CA-oriented workflow path from normalized request to candidate bundle, validation, repair decision, and bounded repair execution
- explicit typed stage artifacts that can be inspected in Dev UI and tests
- deterministic handling of the currently supported patient/provider context boundary
- explicit validation and repair-routing artifacts, including deferred areas and bounded retry outcomes

What it does not currently guarantee:

- full PS-CA conformance certification
- full terminology, slicing, invariant, or profile validation in the default local validator mode
- richer provider/org/role semantics beyond the currently normalized identity fields
- full clinical completeness beyond the currently bounded workflow inputs and deterministic construction rules

### Wrapper demo workflow

The wrapper workflow is `PS-CA Authored Bundle Demo Flow`.

What it adds:

- bounded patient and provider authoring
- bounded authored-record review/edit refinement
- thin authored-input orchestration into the unchanged deterministic workflow
- wrapper-derived readiness and final interpretation summaries for easier Dev UI scanning

What it does not add:

- new bundle-generation semantics
- stronger validation guarantees than the core workflow already has
- a new source of truth for authored records, mapped contexts, or workflow outcomes
- any blocking approval step when readiness is limited

## Current trust boundaries

### Thin provider path

`thin provider path` means the authored provider input did not include enough explicit structure to support a linked organization and provider-role relationship.

In the current repo, that means:

- the workflow still runs
- provider identity may still be usable
- support-resource realism remains intentionally limited
- missing organization/relationship structure should be interpreted as honest upstream incompleteness, not as hidden rich context

Thin path is therefore not a failure state. It is a truthful limited-context state.

### Unresolved authored gaps and unmapped facts

The wrapper can surface:

- unresolved authored gaps
- unmapped authored facts

These are not the same thing:

- unresolved gaps mean the authored record itself still has known missing structure
- unmapped facts mean structured upstream information exists, but the current deterministic workflow does not yet consume it

Both should reduce confidence in completeness, but neither should be silently treated as workflow failure by default.

### Deferred external validation

`deferred external validation` means the run completed, but the repo is still intentionally not claiming full external conformance/terminology/profile validation for the current outcome.

In the default local validator mode, this is expected today because:

- the local scaffold validator is intentionally bounded
- full profile/conformance validation is deferred
- broader terminology, invariant, and slicing/cardinality validation are also deferred

This is a limitation state, not automatically a failed run.

### Standards validation fallback

If Matchbox mode is requested but unavailable, the workflow can fall back to the local scaffold validator.

That fallback should be interpreted as:

- the workflow remained runnable
- standards validation became weaker than the requested external mode
- the final interpretation should not be treated as full external validation success

## How to read current wrapper labels

The wrapper labels are advisory summaries layered over the underlying authored, preparation, validation, and repair artifacts.

They are not enforcement semantics.

### Canonical terminology

The typed wrapper labels are the canonical status vocabulary for the current wrapper flow.

- typed labels are canonical
- stage summaries should use sentence-case renderings of those labels
- docs should prefer the canonical label on first mention, then add explanatory prose if needed

For the current repo:

- validation `warnings` belong to downstream validation artifacts
- wrapper `limitations` belong to advisory wrapper interpretation
- `deferred external validation` is a distinct current-state interpretation, not just a generic warning

### Readiness labels

- `ready`
  - no current thin-path, unresolved-gap, or unmapped-fact limitation was detected by the wrapper summary logic
  - this does not by itself prove full external conformance
- `ready_with_limitations`
  - the run is still runnable
  - limitations remain visible, such as thin provider context, unresolved authored gaps, or unmapped authored facts

### Final interpretation labels

- `success_low_concern`
  - the run completed and the wrapper did not detect major current limitation signals
  - this should still be interpreted within the repo's bounded validator reality
- `success_with_limitations`
  - the run completed, but upstream or mapping limitations remain visible
- `success_external_validation_deferred`
  - the run completed, but external/fuller standards validation is still deferred or fallback-based
  - this is the normal current-state interpretation for many local-mode demo runs
- `failure_or_incomplete`
  - the workflow did not reach a sufficiently complete outcome for the current bounded path
  - use the nested validation/repair artifacts to determine whether the issue was validation failure, unsupported repair, or another incomplete path

## Good enough for demo/testing

A run is generally good enough for current demo/testing when:

- the deterministic workflow completes end to end
- the stage artifacts remain inspectable
- workflow validation passes for the bounded current path
- the operator can explain any remaining limitation labels honestly

Examples of still-acceptable demo/testing outcomes:

- `ready_with_limitations` on a scenario meant to show honest upstream limits
- `success_external_validation_deferred` under the default local validator mode
- a thin-provider scenario used specifically to show that the system does not invent richer provider context

A run should not be overclaimed as stronger than it is:

- do not treat `ready` as a certification gate
- do not treat `success_external_validation_deferred` as full external conformance success
- do not treat thin-provider outcomes as evidence of rich organization/provider-role semantics
- do not treat wrapper summaries as replacements for the underlying artifacts

## Canonical scenario interpretation

For the current canonical scenarios in [demo-scenarios.md](./demo-scenarios.md):

- `rich_reviewed_demo`
  - shows the richer provider path and bounded refinement path
  - should still be interpreted through its remaining `ready_with_limitations` or `success_external_validation_deferred` signals rather than as “fully complete”
- `thin_provider_demo`
  - shows honest limited provider context
  - should be used to demonstrate truthful limitation handling, not rich support-resource realism

Use the scenario guide for the scenario-specific highlights, and use this guide for the meaning of the current statuses and trust boundaries.
