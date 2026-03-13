# Conversation and Development Index

This index tracks the architect-guided development trail for the AI-Assisted FHIR Bundle Builder project.

## Purpose

The purpose of this index is to provide a stable entry point into the project's decision history, planning trail, implementation slices, and architectural documentation.

It should be updated throughout development so that the current state of the project can be understood without reconstructing the entire conversation history.

## Core References

- `docs/architecture-and-system-requirements.md` - Stable high-level architecture and system requirements baseline.
- `README.md` - Repository entry point.

## Working Rules for This Project

- Development proceeds in small bounded slices.
- Architecture and workflow decisions are reviewed before implementation.
- Codex implements only the approved scope for the current slice.
- Every slice should leave behind durable documentation of what changed and why.
- This index should always point to the latest authoritative planning and implementation records.

## Suggested Ongoing Structure

As development progresses, add and maintain references to entries such as:

- request intake notes
- architecture review notes
- approved implementation plans
- plan revisions
- implementation summaries
- verification notes
- open decisions and deferred items

## Initial Entries

### 0001 - Project Initialization
- Established the initial high-level architecture and system requirements baseline.
- Confirmed the project will use an architect-driven, Codex-executed development workflow with persistent documentation.
- Confirmed that support for specification ingestion is a first-class architectural concern.

Related references:
- `docs/architecture-and-system-requirements.md`

## Current Architectural Direction

The current direction is to establish the workflow foundation first, before UI-focused development. The near-term emphasis should remain on:

- workflow architecture
- agent responsibilities
- state and artifact model
- specification ingestion pipeline concept
- bounded implementation slices that prove the workflow incrementally

## Next Likely Documentation Needs

The following documents are likely to be created early in the project:

- workflow artifact contracts
- specification ingestion requirements or design
- session state model
- first implementation slice plan
- verification checklist or definition of done

## Open Architectural Themes

These themes are expected to recur during development and should be tracked as they become more concrete:

- how raw FHIR artifacts are normalized for agent use
- how validation findings route back into repair loops
- how reusable patient and provider profiles are represented
- how workflow state and intermediate artifacts are stored
- how agent prompts or contracts remain inspectable and maintainable
