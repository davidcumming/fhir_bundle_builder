# Agent Profiles

This folder contains the formal role profiles for the core agents used by the PS-CA Bundle Assembly Platform.

These profiles are design artifacts first. They define the intended responsibilities, boundaries, behavior rules, inputs, outputs, and workflow role of each agent. They are also intended to become source material for runtime agent configuration, prompt/instruction generation, and future OpenViking context resources.

## Purpose of these profiles

The agent profiles exist to ensure that the system is built around clear separation of responsibilities rather than vague multi-agent prompting.

They help with:
- defining role boundaries,
- reducing overlap between agents,
- making workflow behavior easier to reason about,
- giving Codex and developers a stable source of truth,
- supporting future runtime configuration,
- preparing for OpenViking-backed context and instruction loading.

## Current core agent profiles

### 1. Coordinator Agent
**File:** `coordinator-agent-profile.md`

The Coordinator Agent is the single visible user-facing orchestrator. It receives the user's request, explains the plan, launches the major stages, monitors progress, performs final consistency review, and returns the final delivery package.

### 2. Requirements Agent
**File:** `requirements-agent-profile.md`

The Requirements Agent transforms a high-level user request into a structured, clinically plausible patient summary specification. It owns clinical realism and completeness at the specification level, but not FHIR construction or conformance validation.

### 3. Assembly Manager Agent
**File:** `assembly-manager-agent-profile.md`

The Assembly Manager Agent converts the specification into a staged build process. It owns build sequencing, dependency handling, task packet creation, retry control, and assembly progression.

### 4. Resource Builder Agent
**File:** `resource-builder-agent-profile.md`

The Resource Builder Agent generates one FHIR resource at a time from a bounded task packet. It stays narrowly focused on the current resource and revises based on validation feedback.

### 5. Validator Agent
**File:** `validator-agent-profile.md`

The Validator Agent interprets deterministic validation output, classifies issues, assesses retryability, and provides focused repair guidance. It is not the conformance authority; deterministic tooling is.

## Supporting template

### Agent Profile Template
**File:** `agent-profile-template.md`

This file provides the standard structure for defining future agent roles. New profiles should follow this template unless there is a strong reason to deviate.

## Design rules for all agent profiles

All agent profiles in this directory should follow these rules:

1. Each role must have a clearly defined purpose.
2. Each role must have explicit non-responsibilities.
3. Each role must define what it receives and what it returns.
4. Each role must define behavioral constraints.
5. Each role must identify the tools and context it is allowed to use.
6. Each role must describe how it fits into the larger workflow.
7. Each role must define success conditions and failure modes.

## Relationship to system architecture

These profiles support the architecture described in:

- `docs/psca-bundle-assembly-architecture.md`

The architecture establishes:
- Microsoft Agent Framework as the orchestration and workflow runtime,
- OpenViking as the context and memory substrate,
- deterministic tooling as the source of truth for validation and terminology support,
- structured artifacts as the contract layer between workflow stages.

These profiles define how each agent role participates in that architecture.

## How these profiles will be used

Over time, these profiles are expected to support several implementation concerns:

### 1. Prompt and instruction sources
Each profile can be transformed into runtime instructions for the corresponding agent.

### 2. Configuration references
Role names, responsibilities, and tool boundaries can inform configuration files.

### 3. OpenViking resources
The profile content can be loaded into OpenViking as reusable role-context resources.

### 4. Test and evaluation criteria
Success criteria and failure modes can inform evaluation scenarios and tests.

## Expected future additions

Likely future profile additions may include:
- Documentation or Trace Narrator Agent
- Terminology Specialist Agent
- Bundle Manifest Specialist Agent
- Repair Specialist Agent
- Review or Governance Agent

These should be added only when the workflow truly requires them.

## Authoring guidance

When creating a new agent profile:
- keep responsibilities narrow,
- avoid overlapping roles unless intentional,
- define strong boundaries,
- prefer operational clarity over personality,
- do not make an agent responsible for a whole workflow if a smaller scoped role will do,
- distinguish clearly between LLM judgment and deterministic truth.

## Notes

These profiles are intentionally written in Markdown because Markdown is:
- easy to review in Git,
- easy to edit,
- easy for Codex to consume,
- easy to turn into structured runtime artifacts later.

As the project matures, some profile content may also be represented in YAML or JSON for runtime configuration, but Markdown remains the primary authoring format.