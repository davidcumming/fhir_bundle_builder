# docs/psca-workflow-development-guidance.md

# PS-CA Workflow Development Guidance

## Purpose

This document provides project-specific development guidance for building the PS-CA bundle generation workflow using Microsoft Agent Framework and Dev UI.

It translates the team's general Microsoft Agent Framework best practices into guidance specific to this project. Its goal is to help the team build the workflow in a way that is inspectable, extensible, and aligned with the long-term architecture of the AI-Assisted FHIR Bundle Builder.

This document is not a low-level technical design, a code specification, or a final implementation contract. It is a practical architectural guide for how the team should approach workflow development for the PS-CA use case.

## Scope

This guidance applies to the initial workflow that generates PS-CA bundles from:
- a selected specification and version
- a selected patient profile
- a selected provider profile
- user instructions
- imported specification assets usable by the workflow

It is focused on development of the workflow itself before product UI development.

---

## 1. Core Development Position

The PS-CA bundle builder must be developed as a **workflow-first system**, not as a chatbot with helper tools.

The top-level system behavior must be represented as an explicit workflow in Microsoft Agent Framework, with clear executors, edges, artifacts, and state transitions. Dev UI should be used as the primary development surface for proving and inspecting that workflow before any major investment in application UI.

The workflow should be built so that:
- each stage has a narrow responsibility
- intermediate artifacts are inspectable
- deterministic logic is separated from model-driven logic
- reusable patient/provider/specification context is externalized
- validation and repair are part of the design from the beginning
- the architecture can later expand to additional specifications and richer workflows without major redesign

---

## 2. What the Initial Workflow Must Prove

Before UI work or major feature expansion, the workflow must prove the following:

1. a PS-CA build request can be accepted in a structured form
2. specification assets can be retrieved in a form useful to the workflow
3. the workflow can generate a bundle schematic
4. the workflow can derive a build plan
5. the workflow can execute resource construction steps in an ordered way
6. the workflow can maintain a bundle-in-progress
7. the workflow can produce a candidate bundle
8. the workflow can validate the candidate bundle
9. the workflow can produce repair-oriented findings
10. the workflow can be understood and debugged in Dev UI

If the workflow cannot prove those things, UI work should remain secondary.

---

## 3. Recommended Initial Workflow Shape

For the PS-CA project, the recommended first workflow should remain mostly sequential.

The initial workflow should favor clarity and inspectability over sophistication. Advanced patterns such as fan-out, fan-in, concurrent execution, or complex branching should be deferred until the basic shape is stable.

The preferred first-pass workflow is:

1. request normalization
2. specification asset retrieval
3. bundle schematic generation
4. bundle build planning
5. iterative resource construction
6. bundle finalization
7. validation
8. repair decision

This gives the team a workflow that is easy to inspect in Dev UI and easy to reason about when things go wrong.

---

## 4. Recommended Logical Executors

The following logical executors should anchor the initial PS-CA workflow.

### 4.1 Request Normalization Executor
Responsible for converting raw user-facing input into a normalized build request context.

Typical responsibilities:
- validate that required top-level inputs are present
- normalize bundle type, version, patient profile reference, provider profile reference, and request text
- apply defaults for the initial PS-CA workflow where needed
- produce a stable internal request artifact

This should be primarily deterministic.

### 4.2 Specification Asset Retrieval Executor
Responsible for retrieving the PS-CA assets needed by downstream steps.

Typical responsibilities:
- load the imported specification package for PS-CA
- retrieve normalized assets relevant to the requested workflow
- provide a compact workflow-usable context rather than raw source files
- fail clearly if required assets are missing

This should be primarily deterministic.

### 4.3 Bundle Schematic Executor
Responsible for creating the initial bundle scaffold.

Typical responsibilities:
- identify the expected structural pattern of the requested PS-CA bundle
- establish the base Bundle structure
- establish the Composition scaffold
- establish required or expected sections
- create placeholders for expected resources

This may use an agent, but its output must be strongly structured.

### 4.4 Bundle Build Planner Executor
Responsible for determining the order in which bundle resources should be built.

Typical responsibilities:
- inspect the bundle schematic
- account for reference and dependency relationships
- derive an ordered build plan
- identify required versus optional build steps
- produce a resource-by-resource execution sequence

This should rely heavily on deterministic logic, even if an agent assists with reasoning.

### 4.5 Resource Construction Executor
Responsible for building one resource at a time.

Typical responsibilities:
- accept the current resource build step
- accept current bundle context and relevant profile/spec context
- determine the resource-level build strategy
- call lower-level element-building capabilities as needed
- return a completed or partially completed resource artifact

This may be implemented as one executor at first, even if it later evolves into a deeper subworkflow.

### 4.6 Bundle Update Executor
Responsible for writing the newly built resource back into the bundle-in-progress and maintaining reference consistency.

Typical responsibilities:
- replace or update placeholders
- maintain IDs and references
- update section entries where applicable
- keep the bundle-in-progress internally consistent

This should be deterministic.

### 4.7 Validation Executor
Responsible for validating the candidate bundle.

Typical responsibilities:
- run bundle checks
- collect findings
- produce structured validation results
- classify findings by severity and likely repair target

This should be deterministic wherever possible.

### 4.8 Repair Decision Executor
Responsible for deciding what should happen after validation.

Typical responsibilities:
- determine whether the workflow is complete
- determine whether repair is possible
- determine whether to return to resource construction, planning, schematic generation, or user intervention
- produce a structured repair decision

This should be driven by structured validation output, not by free-form prose.

---

## 5. Recommended Artifact Model

The PS-CA workflow should be built around explicit intermediate artifacts. These artifacts should be visible in development and traceable in Dev UI as much as practical.

The exact schema may evolve, but the following conceptual artifacts should remain stable.

### 5.1 Build Request Context
A normalized request artifact containing:
- specification
- version
- patient profile reference or snapshot
- provider profile reference or snapshot
- request text
- workflow defaults
- workflow metadata

### 5.2 Specification Asset Context
A workflow-usable package of PS-CA assets, not merely raw structure definition files.

It should eventually contain things such as:
- supported profiles relevant to the workflow
- required bundle-level structure hints
- required/expected section hints
- profile summaries
- element-level constraint summaries
- terminology usage hints
- dependency hints
- validation support assets

### 5.3 Bundle Schematic
A structured representation of the bundle scaffold, including:
- base Bundle identity and type
- Composition placeholder or scaffold
- conceptual sections
- placeholder resources
- expected resource relationships

### 5.4 Build Plan
A structured ordered list of resource build steps, including:
- step order
- resource type or role
- dependencies
- expected inputs
- optionality
- notes for later repair routing

### 5.5 Resource Build Request
A focused request artifact for one resource construction step.

### 5.6 Resource Build Result
A structured result for the resource that includes:
- resource content
- assumptions
- warnings
- unresolved issues
- reference contributions

### 5.7 Bundle-in-Progress
The current evolving bundle artifact.

### 5.8 Validation Report
A structured validation artifact with:
- findings
- severity
- location
- probable cause
- suggested repair target

### 5.9 Repair Decision
A structured statement of:
- complete
- retry current stage
- revisit resource construction
- revisit build planning
- revisit schematic generation
- request human input
- fail with explanation

---

## 6. Guidance on the Specification Ingestion Pipeline

This project must support a pipeline that imports an arbitrary FHIR specification package into assets that the workflow can use.

That pipeline should be treated as a first-class architectural capability, not as a one-time preprocessing hack.

### 6.1 Core principle
Executors and agents should not depend directly on raw FHIR specification files wherever avoidable. They should consume normalized assets shaped for workflow use.

### 6.2 Why this matters
Raw StructureDefinitions, ValueSets, and CodeSystems are useful source material, but they are not the most effective runtime representation for agentic workflow execution.

The workflow will be stronger if it can retrieve compact assets such as:
- what resource types matter for this bundle type
- what sections are expected
- what profile constraints are critical
- which elements are likely required or conditionally relevant
- what terminology bindings matter
- what dependency relationships are important

### 6.3 Initial ingestion pipeline expectation
The ingestion pipeline does not need to be fully general on day one, but it should be designed so that it can eventually:
- accept a FHIR specification package as input
- extract the artifacts relevant to workflow generation
- normalize those artifacts into workflow-usable assets
- version those assets
- support future specs beyond PS-CA

### 6.4 Development guidance
For workflow development, the team should avoid hard-coding PS-CA rules directly into prompts wherever a normalized spec asset could be used instead.

---

## 7. Guidance on Agents vs Deterministic Logic

The PS-CA workflow should aggressively separate deterministic logic from language-model reasoning.

### 7.1 Use deterministic logic for:
- top-level request validation
- workflow state transitions
- spec asset retrieval
- dependency sorting
- ID generation
- bundle patch/update operations
- reference registry maintenance
- structural validation
- routing based on structured conditions

### 7.2 Use agents for:
- interpreting user request nuance
- drafting bundle schematic details where ambiguity exists
- synthesizing resource content from mixed context
- filling element content when judgment is needed
- proposing repair options when deterministic logic alone is insufficient
- producing human-readable explanations

### 7.3 Team rule
If a step must be repeatable, explainable, and safe under strict constraints, default toward deterministic implementation unless there is a clear reason not to.

---

## 8. Guidance on Memory and Context

### 8.1 Do not use session history as the source of truth
Conversation or session memory should not be treated as the authoritative source for:
- patient data
- provider data
- specification rules
- validation rules
- intermediate domain artifacts

### 8.2 Keep domain context externalized
The workflow should retrieve domain context through explicit artifacts and tools, including:
- patient profile assets
- provider profile assets
- imported PS-CA assets
- bundle-in-progress
- validation outputs

### 8.3 Use memory for continuity only
Memory can help preserve execution continuity, but the workflow should still function from explicit artifacts even if session memory is limited or reset.

---

## 9. Guidance on Tools for This Project

The project should define tools as stable capability boundaries rather than using arbitrary helper logic hidden inside prompts.

Examples of likely tool categories for this project include:
- retrieve patient profile
- retrieve provider profile
- retrieve specification assets
- retrieve profile summary
- retrieve terminology guidance
- generate identifiers
- update bundle artifact
- validate candidate bundle
- persist workflow artifact
- retrieve prior workflow artifact

The exact implementation can evolve, but the capability boundaries should remain clean.

### Team rule
If an agent is repeatedly asked to "remember" or "figure out" the same external fact or artifact, that usually indicates a missing tool or missing normalized asset.

---

## 10. Guidance on Dev UI Usage

Dev UI should be the primary development surface for proving the PS-CA workflow before building product UI.

### 10.1 What Dev UI should be used for
The team should use Dev UI to:
- register and run the workflow
- inspect executor outputs
- observe routing behavior
- inspect workflow events
- inspect traces
- verify intermediate artifacts
- demonstrate progress to teammates

### 10.2 What should be visible in Dev UI
A developer reviewing the workflow in Dev UI should be able to understand:
- what input started the run
- what each major executor did
- what artifacts were produced
- where failure occurred
- whether validation passed
- what repair decision was made

### 10.3 Team quality bar
A workflow slice should not be treated as complete until another team member can inspect it in Dev UI and understand the stage outputs without reading the source code first.

---

## 11. Guidance on Validation and Repair

Validation and repair must be part of the workflow shape from the beginning.

### 11.1 The workflow should not stop at generation
A candidate bundle is not the final success condition. The actual success condition is a candidate bundle plus a validation outcome that the workflow can explain.

### 11.2 Validation results must be structured
Validation output should include enough structure to support repair decisions such as:
- data issue
- resource issue
- bundle structure issue
- dependency/planning issue
- missing user input
- unrecoverable issue

### 11.3 Repair should be targeted
The workflow should revisit the smallest reasonable stage rather than rebuilding everything by default.

### 11.4 Human intervention path
If the workflow cannot safely repair a problem, it should return a structured request for human clarification or approval.

---

## 12. Recommended Early Delivery Slices

The project should be developed in small slices that prove architecture rather than rushing toward a polished app.

Recommended early slices:

### Slice 1: workflow skeleton in Dev UI
Prove:
- workflow registration
- structured input
- basic executor chain
- visible outputs in Dev UI

### Slice 2: PS-CA asset retrieval
Prove:
- imported asset access
- normalized PS-CA asset context
- stable retrieval patterns

### Slice 3: bundle schematic generation
Prove:
- Bundle scaffold generation
- Composition scaffold generation
- section placeholder generation

### Slice 4: build planning
Prove:
- ordered resource steps
- dependency awareness
- structured build plan

### Slice 5: one or two resource construction steps
Prove:
- resource-by-resource build
- bundle update
- basic reference consistency

### Slice 6: validation and repair decision
Prove:
- validation report
- repair routing result
- rerun entry point logic

### Slice 7: end-to-end minimal PS-CA workflow
Prove:
- a full narrow run from request to validated candidate bundle

---

## 13. Anti-Patterns to Avoid on This Project

The team should avoid the following:

### 13.1 One giant "build the whole bundle" agent
This undermines inspectability, repairability, and future extensibility.

### 13.2 Prompt-embedded specification logic
Do not solve PS-CA support by pasting large amounts of profile logic directly into prompts if it can be provided through normalized assets.

### 13.3 Free-form step outputs for routing
Repair and branch decisions must not depend on parsing vague prose when structured outputs can be used.

### 13.4 Hidden domain state
Important state must not exist only in memory or inside an agent session.

### 13.5 UI-first workflow development
Do not start by building a polished interface for a workflow that is not yet stable in Dev UI.

### 13.6 Early over-engineering
Do not start with full concurrency, full spec generalization, or deep subworkflow nesting before the base workflow is proven.

---

## 14. Team Review Checklist for PS-CA Workflow Slices

Before approving a workflow slice, confirm:

- Is the slice small and focused?
- Is the executor responsibility clear?
- Is deterministic logic separated from model-driven logic?
- Are the inputs and outputs explicit?
- Can the step be inspected in Dev UI?
- Is the output shaped as a useful artifact?
- Does the design reduce future coupling?
- Does the design avoid hard-coding PS-CA logic where normalized assets should be used?
- Is validation or future repair thinking preserved?
- Will this step still make sense when additional specs are supported later?

If several answers are "no", the slice needs revision.

---

## 15. Summary

The PS-CA workflow should be developed as a workflow-first, artifact-driven, inspection-friendly system in Microsoft Agent Framework.

The team should use Dev UI to prove the workflow before building the product UI. The architecture should emphasize:
- narrow executors
- typed artifacts
- explicit state
- deterministic boundaries
- externalized specification assets
- structured validation
- targeted repair
- controlled extensibility

The most important practical rule for this project is simple:

**Do not let the initial PS-CA workflow become a hidden chatbot implementation. Build it as a visible workflow system that can later grow into a durable product capability.**