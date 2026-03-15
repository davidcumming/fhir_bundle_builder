# Post-Traceability Consolidation and Next-Slice Decision

## Recommendation

Do not expand workflow realism or multiplicity in the next slice.

The next bounded move should be a consolidation/defer slice that records the current honest support boundary, adds guard tests for that boundary, and makes the repo's current capability/deferred-state easier to read without changing workflow behavior.

## Why this is the right next move

- The workflow is now strong on deterministic generation, alignment validation, repair targeting, and cross-stage traceability.
- The strongest remaining realism gaps are constrained by upstream normalized input shape rather than by missing builder mechanics.
- The medications-only multiplicity slice already showed that even bounded multiplicity creates real schematic, planning, construction, validation, repair, and test burden.
- The current traceability slice already gives enough inspectability to justify a deliberate defer decision instead of continuing expansion by momentum.

## What the repo can honestly support now

- Patient identity and demographics from structured patient context.
- Single-entry allergy/problem text alignment from structured patient context when exactly one item exists.
- Bounded first-two medication mapping with explicit overflow deferral.
- Practitioner identity from structured provider context.
- Selected Organization identity from structured provider context.
- Selected PractitionerRole relationship identity and narrow role-label alignment from structured provider context.
- Cross-stage placeholder-scoped traceability from construction through validation.

## What should remain deferred

- Broader Organization semantics such as telecom, address, or type.
- Broader PractitionerRole semantics such as specialty, telecom, period, or availability.
- Any multiplicity expansion beyond the current medications-only bounded path.
- Any new generic provenance or alignment framework.
- Any semantic clinical reasoning or non-deterministic enrichment.

## Recommended follow-on after this consolidation

If a new feature slice becomes justified after consolidation, prefer a narrow validation/repair refinement inside the current truthful input boundary before attempting any new realism or multiplicity expansion.
