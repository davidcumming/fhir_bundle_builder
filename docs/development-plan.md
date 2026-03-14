# docs/development-plan.md

# Development Plan
## AI-Assisted FHIR Bundle Builder

## 1. Purpose

This document is the working development plan for the AI-Assisted FHIR Bundle Builder project.

Its purpose is to:
- define the planned development phases and slices
- provide a stable progress-tracking reference for the team
- record the current development focus
- identify completed, active, and upcoming work
- provide a place that Codex can update when approved scope changes during development

This document is not intended to be a detailed technical design for every implementation decision. It is a controlled project plan that should evolve in small, intentional updates as development progresses.

## 2. How This Plan Will Be Used

Development will follow an architect-guided, Codex-executed workflow.

The working process is:

1. the architect defines the next bounded slice of work
2. Codex is asked, in plan mode, to inspect the current project and propose an implementation plan
3. the architect reviews the proposed plan and approves or modifies it
4. Codex performs the implementation only after plan approval
5. after implementation, the result is reviewed against the approved scope
6. this development plan is updated if the project plan, sequencing, status, or assumptions changed

## 3. Rule for Updating This Plan

Codex must treat this document as a controlled project artifact.

When a development slice changes the project plan in a meaningful way, Codex must update this file as part of the same approved work item.

Examples of changes that require updating this plan:
- a phase is completed
- a new slice is added
- a slice is split into smaller slices
- sequencing changes
- a dependency is discovered
- a planned slice is deferred
- the active development focus changes
- an implementation assumption becomes obsolete
- a milestone definition changes

Examples of changes that do not necessarily require updating this plan:
- purely internal code refactoring within an unchanged slice
- minor naming changes that do not affect plan structure
- low-level implementation details that do not affect scope, sequencing, or status

## 4. Update Discipline

When updating this plan, changes should be minimal and targeted.

Codex should:
- update only the relevant sections
- preserve the overall structure of the document
- avoid rewriting the entire file unnecessarily
- keep status values current
- keep the "Current Focus" and "Next Planned Slice" sections accurate
- record new assumptions or dependencies only when they materially affect the plan

## 5. Project Objective

Build an AI-assisted application that generates FHIR bundles through a structured Microsoft Agent Framework workflow, beginning with PS-CA support.

The system must:
- use reusable patient and provider profiles
- use imported FHIR specification assets
- build bundles through staged agentic workflow execution
- validate outputs and support repair loops
- be developed workflow-first in Microsoft Agent Framework Dev UI before product UI work begins

## 6. Current Development Strategy

The project will proceed in this order:

1. establish stable architecture and project guidance documents
2. prove the workflow shape in Microsoft Agent Framework Dev UI
3. establish a specification ingestion and normalized asset pipeline for PS-CA
4. prove a minimal end-to-end PS-CA workflow
5. strengthen validation, repair routing, and workflow state handling
6. expand workflow depth and quality
7. begin UI work only after the workflow foundation is stable

## 7. Status Model

The following status labels should be used in this plan:

- Planned
- In Progress
- Blocked
- Completed
- Deferred

## 8. Current Focus

**Current Focus:** Implement the next bounded realism/quality slice now that required Composition sections can validate, route, and retry through section-specific finalize steps instead of one grouped Composition finalize step.

## 9. Next Planned Slice

**Next Planned Slice:** Deepen Organization/provider-role realism or further narrow grouped Composition scaffold/content validation where current construction maturity safely supports it.

## 10. Development Phases

## Phase 1: Foundation and Project Guidance
**Status:** Completed

### Goal
Establish the stable architectural and planning documents that will guide implementation.

### Included work
- architecture and system requirements document
- Microsoft Agent Framework best practices document
- PS-CA workflow development guidance document
- development plan document
- conversation/progress tracking structure

### Exit criteria
- core project guidance documents exist
- development workflow is agreed
- the next implementation slice is clearly defined

---

## Phase 2: Minimal Workflow Skeleton in Dev UI
**Status:** Completed

### Goal
Prove that the project can run as a visible Microsoft Agent Framework workflow in Dev UI before deeper functionality is added.

### Included work
- create the initial workflow shell
- register the workflow so it is runnable in Dev UI
- define a structured top-level workflow input model
- add placeholder executors for key workflow stages
- ensure each placeholder stage emits inspectable output
- verify the workflow graph and basic execution path can be understood in Dev UI

### Early slice intent
This phase is about workflow shape and inspectability, not real bundle generation.

### Exit criteria
- workflow runs in Dev UI
- top-level input is structured
- workflow stages are visible and understandable
- placeholder artifacts are emitted by the stages
- the team can inspect the run without reading source code first

---

## Phase 3: Specification Ingestion and Asset Normalization
**Status:** Completed

### Goal
Create the initial pipeline that converts PS-CA source specification artifacts into normalized assets the workflow can use.

### Included work
- inspect PS-CA specification files already present in the project
- define the normalized asset shapes needed by the workflow
- implement the first PS-CA ingestion path
- produce workflow-usable assets rather than relying directly on raw StructureDefinitions at runtime
- ensure version-awareness exists for the supported spec input

### Notes
This phase should be designed so the ingestion approach can later support arbitrary FHIR specifications, even if only PS-CA is implemented first.

### Exit criteria
- PS-CA assets can be ingested from source materials
- normalized assets are produced for workflow consumption
- the workflow can retrieve those assets through a stable boundary
- direct prompt-embedded dependence on raw spec content is reduced

---

## Phase 4: Bundle Schematic Generation
**Status:** Completed

### Goal
Enable the workflow to produce a structured PS-CA bundle scaffold.

### Included work
- retrieve the relevant normalized specification assets
- create the base Bundle scaffold
- create the Composition scaffold
- identify required or expected sections
- create resource placeholders
- output a structured bundle schematic artifact

### Exit criteria
- a PS-CA bundle schematic can be generated from structured input
- the schematic is inspectable in Dev UI
- schematic output is stable enough for downstream planning

---

## Phase 5: Build Planning
**Status:** Completed

### Goal
Enable the workflow to derive an ordered resource build plan from the bundle schematic and request context.

### Included work
- analyze the bundle schematic
- identify resource dependencies
- determine build order
- define a structured build plan artifact
- identify required and optional build steps

### Exit criteria
- the workflow can produce an ordered build plan
- the build plan is inspectable and structured
- build sequencing is separated from resource generation logic

---

## Phase 6: Resource Construction Foundation
**Status:** Completed

### Goal
Prove that the workflow can build resources incrementally and maintain a bundle-in-progress.

### Included work
- create the initial resource construction path
- define resource build request/result artifacts
- build one or more foundational resources
- update the bundle-in-progress after each built resource
- establish reference consistency patterns

### Suggested first resources
- Patient
- Organization
- Practitioner
- Composition scaffold update

### Exit criteria
- at least one meaningful resource path is working
- resource results are written back into the bundle-in-progress
- resource construction is inspectable in Dev UI

---

## Phase 7: Validation and Repair Routing Foundation
**Status:** Completed

### Goal
Establish the first validation and repair loop for the workflow.

### Included work
- define validation result artifact shape
- implement initial validation execution
- classify validation findings
- define repair decision artifact
- implement initial routing after validation

### Current phase note
Structured validation, deterministic repair decision/routing, and one bounded internal retry execution path now exist. Broader retry orchestration remains deferred.

### Exit criteria
- the workflow can produce a validation report
- the workflow can determine whether to complete, repair, or request clarification
- repair logic is driven by structured outputs
- one bounded internal retry path can be executed and inspected without introducing a loop engine

---

## Phase 8: Minimal End-to-End PS-CA Workflow
**Status:** In Progress

### Goal
Prove a narrow but real end-to-end PS-CA generation run.

### Included work
- execute the workflow from normalized request through validation
- produce a candidate PS-CA bundle
- verify inspectability across all major stages
- verify that the run can be demonstrated clearly in Dev UI

### Current phase note
The workflow now has a complete deterministic structural path, validation, repair routing, bounded retry execution for both bundle finalization and resource construction, the first targeted `resource_construction` repair-directive mode based on deterministic build-step subsets, resource-specific section-entry validation and repair for the fixed PS-CA section-entry trio, incremental section-specific Composition finalization and required-section validation/repair for medications, allergies, and problems, meaningful deterministic content for core clinical resources, a deterministic local bundle identity/fullUrl policy, and an optional Matchbox-backed external standards-validation path with local fallback. The next step is to deepen end-to-end realism without widening into deployment, persistence, or generic lifecycle management.

### Exit criteria
- a minimal PS-CA workflow runs end to end
- intermediate artifacts are visible
- the system produces a candidate bundle plus validation outcome
- the workflow is stable enough for iterative strengthening

---

## Phase 9: Workflow Hardening and Expansion
**Status:** Planned

### Goal
Improve workflow quality, repair depth, asset quality, and extensibility after the minimal end-to-end path exists.

### Included work
- improve specification asset coverage
- improve resource construction depth
- improve data element construction strategy
- strengthen validation
- strengthen repair routing
- improve workflow state handling
- improve observability and diagnostics
- prepare the workflow for later UI integration

### Exit criteria
- workflow quality is materially improved
- repair handling is more robust
- architecture remains modular and extensible

---

## Phase 10: UI Foundation
**Status:** Deferred

### Goal
Begin product UI development only after the workflow foundation is proven sufficiently stable.

### Included work
- define UI integration boundaries
- expose workflow capabilities to the UI layer
- support profile selection and request entry
- display workflow progress and outputs
- display bundle artifacts and validation results

### Exit criteria
- workflow foundation is already stable
- UI work does not force architectural compromises in the workflow

## 11. Phase Dependencies

The following dependencies apply at a high level:

- Phase 2 depends on Phase 1 guidance being sufficient to begin implementation
- Phase 3 should begin early enough to support Phase 4 and beyond
- Phases 4 and 5 depend on having at least an initial asset retrieval model
- Phase 6 depends on the existence of a structured build plan
- Phase 7 depends on candidate bundle output existing
- Phase 8 depends on Phases 4 through 7 reaching minimum viability
- Phase 10 depends on workflow stability, not merely code existence

## 12. Known Early Assumptions

The following assumptions currently guide the plan:

- the first supported specification is PS-CA
- only one initial PS-CA version needs to be supported
- the project already contains PS-CA source files that can seed the ingestion pipeline
- patient and provider profile support will exist conceptually even if the first workflow uses stub or placeholder retrieval
- Microsoft Agent Framework Dev UI is the correct proving ground before UI work
- the specification ingestion pipeline should be designed to support arbitrary FHIR specifications later
- the initial normalized PS-CA asset scope is intentionally limited to package metadata, selected foundational profiles, Composition section definitions, and example summaries rather than full IG normalization
- the first real PS-CA schematic intentionally covers only the required sections plus minimal subject/author support placeholders
- the first real build plan intentionally uses incremental section-specific Composition finalization and a limited hard-dependency set derived from the current schematic
- the first resource-construction slice uses partial FHIR-shaped scaffold artifacts and deterministic placeholder-derived local references rather than fully populated valid resources
- the first deterministic bundle identity policy uses local UUID-based candidate identifiers, synthetic timestamps, and `urn:uuid` entry fullUrls rather than persistent publication identity
- Matchbox is optional infrastructure and the workflow must remain runnable with the local scaffold-shape standards validator alone
- the bounded repair-execution model remains single-pass and now supports both bundle_finalization and resource_construction as internal executable targets, with section-entry narrowing operating at single-resource build-step granularity and required Composition section narrowing operating at section-specific finalize-step granularity
- the first meaningful content slice should use deterministic placeholder content from normalized request labels and schematic section metadata rather than free-text clinical synthesis
- meaningful Organization identity and richer PractitionerRole context depend on a future provider input expansion that includes organizations and provider-role relationships
- initial development should prioritize workflow shape, artifact contracts, and inspectability over feature completeness

## 13. Known Early Risks

The following risks should be monitored during development:

- raw specification assets may not be in a form directly useful to workflow execution
- the team may accidentally hard-code PS-CA logic into prompts instead of normalized assets
- the workflow may become too chat-oriented instead of artifact-driven
- validation may be introduced too late unless intentionally included in early slices
- state handling may become implicit unless workflow artifacts are defined carefully
- UI thinking may pressure the team to skip workflow discipline
- prerelease Agent Framework package behavior may affect Dev UI discovery or schema rendering details between versions
- the current provider input model may constrain support-resource realism until organization and provider-role context are explicitly modeled
- deterministic synthetic timestamps and local URN fullUrls may later need refinement when publication or persistence semantics are introduced
- Matchbox availability or response-shape variance may require a small amount of adapter hardening before broader operational use
- Composition scaffold/content validation is still grouped at the resource level even though required section attachment now occurs through section-specific finalize steps

## 14. Definition of Progress

A phase or slice should not be treated as complete merely because code was written.

Progress means:
- approved scope was implemented
- outputs are inspectable
- Dev UI behavior matches the intent of the slice
- architecture has not been undermined
- relevant documents were updated if the plan changed
- the next slice is clearer than before

## 15. Instructions for Codex When a Slice Changes the Plan

If approved work changes the plan, Codex must update this file in the same change set.

Typical updates Codex may need to make include:
- mark a phase or slice as Completed
- mark the next phase or slice as In Progress
- update the "Current Focus" section
- update the "Next Planned Slice" section
- add a newly discovered dependency
- split a phase into smaller future slices
- record a new project assumption or risk if it materially affects sequencing

Codex should make targeted edits only. It should not rewrite the full document unless explicitly instructed.

## 16. Immediate Next Objective

The immediate next objective is to deepen end-to-end realism or further narrow remaining grouped Composition scaffold/content validation where the current construction shape safely supports it.
