# Architecture and System Requirements
## AI-Assisted FHIR Bundle Builder

## 1. Document Purpose

This document defines the stable, high-level architecture and system requirements for the AI-Assisted FHIR Bundle Builder. It is intended to serve as an enduring reference point for the project at the start of development.

This document deliberately stays at the feature, workflow, and architectural responsibility level. It avoids low-level implementation choices that are likely to change during development. Detailed technical design, coding decisions, interface contracts, and evolving implementation notes will be captured separately through the project's ongoing development documentation process.

## 2. Document Objectives

The purpose of this document is to:

- define what the system is fundamentally intended to do
- define the major user goals and use cases
- define the major architectural components and responsibilities
- define the high-level workflow for bundle generation
- define the stable responsibilities of the agent-based system
- establish non-functional expectations that should remain broadly true throughout development
- provide a durable anchor for implementation planning and architectural review

## 3. Product Vision

The system will be an AI-assisted application for constructing FHIR bundles, beginning with support for PS-CA bundles.

Rather than relying on a single free-form AI generation step, the system will use a structured, multi-agent workflow to progressively construct a bundle from reusable profiles, specification knowledge, and user instructions. The system must support a controlled process in which bundle scaffolding is created first, resource dependencies are planned, resources are built in a deliberate order, data elements are populated with context-aware logic, and the resulting bundle is validated and repaired if necessary.

The long-term value of the system is to make bundle creation more repeatable, inspectable, reusable, and standards-aware than a simple prompt-to-output chatbot approach.

## 4. Scope

### 4.1 In Scope for the Initial System

The initial system will support:

- creation of FHIR bundles through an agent-driven workflow
- support for PS-CA as the initial specification
- support for a single initial PS-CA version in the workflow, while preserving the ability to add later versions
- reuse of patient profiles
- reuse of provider profiles
- user-driven natural language instructions for bundle generation
- staged construction of bundles through specialized agents
- validation of completed bundles
- routing of detected problems back to the appropriate stage for repair
- ingestion of implementation guide assets into a normalized specification knowledge layer that agents can use
- architecture that can later support additional specifications, bundle types, profiles, and validation capabilities

### 4.2 Out of Scope for the Initial System

The following are explicitly out of scope for this initial high-level requirements baseline:

- support for many implementation guides at the start
- final decisions on data storage technology
- final UI design and interaction details
- advanced multi-user governance and enterprise administration
- production-grade terminology server design
- final hosting, deployment, or infrastructure choices
- full operational support for all possible FHIR resource types and profiles
- complete specification of all prompt contents, code structures, or API details

## 5. Primary Business Goal

The primary business goal is to enable reliable creation of standards-aware FHIR bundles from reusable patient/provider context and user intent, with AI operating inside a controlled architecture rather than as an unconstrained generator.

## 6. Core System Principles

The system must be designed according to the following principles.

### 6.1 Structured Generation Over Free-Form Generation
The system must construct bundles through staged reasoning and controlled handoffs, not through a single end-to-end generative step.

### 6.2 Inspectability
Every major stage in the workflow should produce inspectable intermediate artifacts so that the process can be understood, reviewed, and debugged.

### 6.3 Reusability
Patient and provider information must be reusable across bundle generation sessions.

### 6.4 Standards Awareness
The system must operate in the context of explicit specification knowledge, including profiles, bundle expectations, and terminology constraints.

### 6.5 Separation of Concerns
Different concerns such as orchestration, bundle structure, planning, resource construction, data element construction, validation, and specification ingestion must be handled by different logical components.

### 6.6 Repairability
Validation failures must be routed back to the correct layer of the workflow rather than triggering blind regeneration of the entire bundle.

### 6.7 Extensibility
The architecture must allow support for additional specifications, versions, resource patterns, validation strategies, and user workflows over time.

### 6.8 Traceability
The system should make it possible to trace how a bundle was produced, what assumptions were used, and where a failure or correction occurred.

## 7. Users and Actors

### 7.1 Primary User
A user who wants to create a FHIR bundle based on a selected implementation guide, a selected patient profile, a selected provider profile, and a natural-language request.

This user may be:
- an interoperability analyst
- a standards implementer
- a tester
- a developer
- a domain expert preparing example or test bundles

### 7.2 System Actor
The agent-based workflow system that interprets the request, coordinates the build process, constructs the bundle, validates the output, and manages repair cycles.

### 7.3 Future Administrative or Authoring Actors
The architecture should allow for future users or roles responsible for:
- maintaining specification packages
- maintaining reusable patient/provider profiles
- managing validation assets
- reviewing and approving generated bundles

These roles are not required to be fully implemented in the initial version.

## 8. Primary Use Cases

### 8.1 Create a New Bundle
The user initiates creation of a new bundle by selecting a specification, version, patient profile, provider profile, and entering additional instructions.

### 8.2 Generate a Bundle Based on Reusable Clinical Context
The system creates a bundle using reusable patient and provider profiles plus the user's request-specific context.

### 8.3 Generate a Structurally Correct Bundle Scaffold
The system creates the expected structural skeleton of the bundle before attempting full content population.

### 8.4 Build a Bundle in a Dependency-Aware Order
The system determines the correct order for building resources so references and the clinical story remain coherent.

### 8.5 Populate Resource Content Incrementally
The system builds resources one at a time and builds data elements within each resource using relevant context and rules.

### 8.6 Validate a Candidate Bundle
The system validates the assembled bundle for structure, profile conformance, referential integrity, and clinical consistency.

### 8.7 Repair a Bundle After Validation Failure
The system routes correction work back to the appropriate layer such as data element, resource, build plan, or bundle schematic.

### 8.8 Reuse Existing Patient and Provider Profiles
The user may use existing reusable patient and provider profiles without re-entering all information each time.

### 8.9 Manage Reusable Inputs
The system should support the creation and maintenance of reusable patient and provider profiles through separate workflows and interfaces.

### 8.10 Import a FHIR Specification Package
The system should support importing an arbitrary FHIR specification package into normalized assets that the workflow can use for bundle construction, planning, validation, and terminology-aware generation.

## 9. High-Level Functional Requirements

### 9.1 Bundle Creation Context
The system must allow a bundle generation session to begin with the following logical inputs:

- specification selection
- version selection
- patient profile selection
- provider profile selection
- user instructions

### 9.2 Specification Awareness
The system must be able to operate in the context of a selected implementation guide and version, including access to relevant structural and terminology knowledge.

### 9.3 Reusable Profile Support
The system must support reusable patient and provider profiles that can be referenced during bundle creation.

### 9.4 Natural Language Request Support
The system must allow the user to provide request-specific instructions that refine or extend the selected reusable profiles.

### 9.5 Bundle Schematic Generation
The system must be able to generate an initial bundle schematic that represents the expected structural scaffold of the requested bundle.

### 9.6 Build Planning
The system must be able to derive an ordered plan for constructing resources in a dependency-aware manner.

### 9.7 Resource-Level Construction
The system must be able to construct resources individually based on the build plan and the available context.

### 9.8 Data Element-Level Construction
The system must be able to construct data elements within a resource according to type, constraints, terminology requirements, and contextual inputs.

### 9.9 Incremental Bundle Assembly
The system must maintain and update a bundle-in-progress as resources are completed.

### 9.10 Validation
The system must validate the candidate bundle before considering the generation successful.

### 9.11 Repair Loop
The system must support a repair loop in which validation findings can trigger targeted rework.

### 9.12 User Intervention Path
The system must be able to determine when a problem cannot be safely resolved without user input.

### 9.13 Specification Ingestion
The system must support a specification ingestion pipeline that can transform source FHIR artifacts into normalized internal assets usable by the workflow.

## 10. High-Level Workflow

The system must support the following end-to-end workflow.

### Step 1: Bundle Request Initialization
A user starts a new bundle generation session and provides the bundle creation inputs.

### Step 2: Context Normalization
The system normalizes the selected inputs and creates a coherent internal request context.

### Step 3: Bundle Structure Definition
The system creates the initial bundle scaffold based on the selected specification and version.

### Step 4: Build Planning
The system determines the order in which resources should be built so that dependencies and references can be handled correctly.

### Step 5: Resource Construction
The system builds resources one at a time according to the plan.

### Step 6: Data Element Construction
Within each resource, the system constructs the required data elements using the available context and rules.

### Step 7: Bundle Update
As each resource is completed, the system updates the bundle-in-progress.

### Step 8: Final Assembly
Once all planned resources are completed, the system prepares the candidate bundle for validation.

### Step 9: Validation
The system validates the candidate bundle and produces a validation outcome.

### Step 10: Repair or Completion
If issues are found, the system routes the work back to the correct stage. If no blocking issues remain, the bundle generation is considered complete.

### Step 11: Specification Ingestion and Refresh
Separately from individual bundle-generation sessions, the system must support ingestion or refresh of specification knowledge assets so that agents operate on normalized, versioned inputs rather than raw source files.

## 11. Logical Architecture Overview

The system will be composed of several logical layers or components.

### 11.1 User Interaction Layer
Responsible for capturing user selections and instructions and presenting outputs, progress, and results.

This layer may evolve significantly during development, so it is intentionally not specified in detail here.

### 11.2 Reusable Context Layer
Responsible for storing and retrieving reusable patient and provider profiles.

### 11.3 Specification Knowledge Layer
Responsible for making implementation guide knowledge available to the workflow, including structure definitions, terminology assets, bundle-specific expectations, and normalized derivative assets created through a specification ingestion pipeline.

### 11.4 Agent Workflow Layer
Responsible for coordinating and executing the staged bundle construction process.

### 11.5 Validation Layer
Responsible for assessing the candidate bundle and producing repair guidance.

### 11.6 State and Artifact Layer
Responsible for maintaining the bundle-in-progress, workflow state, intermediate artifacts, and traceability information.

### 11.7 Specification Ingestion Layer
Responsible for importing raw FHIR specification artifacts and transforming them into normalized assets that downstream agents can query and use.

## 12. Agent Model

The system will use a multi-agent model in which each agent has a focused responsibility. The exact implementation mechanism may change, but the logical responsibilities should remain stable.

## 13. Agent Responsibilities

### 13.1 Orchestrator Agent
The Orchestrator Agent is the central coordinator of the workflow.

Its responsibilities include:
- receiving the normalized bundle request context
- managing workflow state
- invoking specialized agents in the correct sequence
- passing the appropriate context to each stage
- tracking intermediate artifacts
- updating the bundle-in-progress
- handling retries and repair cycles
- determining when user intervention is required

The Orchestrator Agent must not be treated as a generic generator of the final bundle. Its main responsibility is coordination, state management, and workflow control.

### 13.2 Bundle Schematic Agent
The Bundle Schematic Agent is responsible for defining the initial structural scaffold of the bundle.

Its responsibilities include:
- determining the expected structural pattern for the selected specification/version
- creating the initial bundle shell
- ensuring required top-level bundle components are represented
- defining the expected Composition scaffold where applicable
- establishing the conceptual section structure
- creating placeholders for resources that will later be populated

This agent prioritizes structural completeness over content completeness.

### 13.3 Bundle Build Planner Agent
The Bundle Build Planner Agent is responsible for determining the order in which resources should be built.

Its responsibilities include:
- analyzing dependencies between resources
- accounting for reference relationships
- accounting for structural prerequisites
- accounting for clinical or narrative sequencing needs
- producing a build plan that can be executed incrementally
- supporting future repair-oriented replanning where necessary

This agent is responsible for ordering and dependency logic, not for full resource content generation.

### 13.4 Resource Builder Agent
The Resource Builder Agent is responsible for constructing one resource at a time.

Its responsibilities include:
- interpreting the requirements for the current resource
- determining what information is needed to populate the resource
- deciding what data elements or structures must be built
- invoking lower-level element construction logic
- assembling the resource
- ensuring the resource is internally coherent
- returning the completed resource and any assumptions or warnings

This agent owns resource-level construction strategy.

### 13.5 Data Element Builder Agent
The Data Element Builder Agent is responsible for constructing data elements within a resource.

Its responsibilities include:
- building primitive and complex elements
- handling coded elements and terminology-aware construction
- handling references, identifiers, dates, quantities, and other structured types
- handling repeating elements and nested structures
- handling extensions where applicable
- distinguishing supplied data from inferred data
- returning the built element plus rationale or warnings where needed

This agent owns element-level construction logic.

### 13.6 Bundle Validator Agent or Validation Component
The validation component is responsible for determining whether the assembled bundle is acceptable and, if not, what kind of repair is needed.

Its responsibilities include:
- checking bundle structure
- checking profile alignment
- checking element-level correctness where possible
- checking referential integrity
- checking internal coherence of the clinical story where feasible
- producing findings with enough precision to support targeted repair

This component must do more than simply say valid or invalid. It must help determine where the workflow should return for repair.

### 13.7 Specification Ingestion Pipeline or Ingestion Component
The specification ingestion component is responsible for transforming raw specification materials into usable agent assets.

Its responsibilities include:
- ingesting implementation guide artifacts such as profiles, extensions, value sets, code systems, search parameters, examples, and package metadata where available
- normalizing source artifacts into internal representations that are easier for agents to use
- deriving or indexing agent-friendly knowledge such as required elements, cardinalities, bindings, slices, references, choice elements, and profile relationships
- versioning ingested assets by specification and release
- supporting refresh or re-import when source assets change
- exposing enough metadata for later validation, planning, and explainability

This component is responsible for turning raw FHIR specification content into stable knowledge assets for the rest of the system.

## 14. Stable Architecture Concepts

The following concepts are expected to remain stable throughout development, even if implementation details change.

### 14.1 Build Request Context
A normalized representation of the user's request and selected inputs.

### 14.2 Bundle Schematic
A structural blueprint representing the expected bundle scaffold.

### 14.3 Bundle Build Plan
An ordered set of build steps describing how the bundle should be constructed.

### 14.4 Bundle-in-Progress
The evolving bundle as resources are gradually completed and inserted.

### 14.5 Reference Registry
A mechanism for maintaining consistent identities and cross-resource references during the build process.

### 14.6 Validation Report
A structured representation of validation findings and repair recommendations.

### 14.7 Workflow Session State
The record of the current workflow stage, status, iterations, and repair history.

### 14.8 Specification Asset Set
A versioned collection of normalized implementation-guide knowledge artifacts derived from raw FHIR specification materials and made available to agents.

## 15. Data and Input Concepts

### 15.1 Specification Package
The system must operate in the context of a specification package that provides the knowledge needed to construct and validate bundles for a selected implementation guide and version.

### 15.2 Patient Profile
The patient profile is a reusable package of patient-related information that may include demographics and clinically relevant details needed during bundle generation.

### 15.3 Provider Profile
The provider profile is a reusable package of practitioner, organization, authorship, or care-context information needed during bundle generation.

### 15.4 User Request
The user request is the natural language instruction that expresses the specific intent for the current bundle instance.

### 15.5 Generated Output
The output is the candidate bundle together with the artifacts and status information needed to explain how it was produced.

### 15.6 Ingested Specification Assets
Ingested specification assets are normalized, versioned artifacts derived from source FHIR materials and used by the workflow for schematic generation, build planning, resource construction, element construction, and validation.

## 16. Validation and Repair Model

The system must include a validation and repair model rather than a one-pass generation model.

### 16.1 Validation Dimensions
Validation should eventually be capable of addressing:
- structural validity
- profile-aware correctness
- referential consistency
- terminology correctness where possible
- clinical or narrative coherence where feasible

### 16.2 Repair Routing
The system must support routing validation failures back to the correct logical level.

At a minimum, the architecture must support the idea that a failure may require:
- data element repair
- resource repair
- build plan repair
- bundle schematic repair
- user intervention

### 16.3 Incremental Rework
The system should be able to preserve successful work where practical rather than unnecessarily restarting the entire process.

## 17. Reusable Profile Management Requirements

The system must support the concept of reusable patient and provider profiles as first-class inputs to bundle generation.

At a high level, the system must support:
- creation of reusable patient profiles
- updating of reusable patient profiles
- creation of reusable provider profiles
- updating of reusable provider profiles
- selection of a reusable profile during bundle generation
- using profile data as a baseline for new bundle requests

This document does not define the detailed management workflows or UI for profile maintenance.

## 18. Initial Product Constraints

The initial implementation should assume the following constraints:

- only one implementation guide is supported initially
- only one version is supported initially
- one main bundle generation use case is supported first
- development should prioritize workflow correctness over UI sophistication
- development should prioritize inspectable intermediate artifacts over opaque automation
- development should avoid prematurely locking into technology decisions that are not yet required

## 19. Non-Functional Requirements

### 19.1 Explainability
The workflow should be understandable and reviewable by a human.

### 19.2 Maintainability
The architecture should make it practical to improve one logical component without destabilizing the entire system.

### 19.3 Extensibility
The system should be able to grow to support additional specifications, versions, resource types, and workflows.

### 19.4 Reliability
The workflow should behave consistently enough to support iterative improvement and debugging.

### 19.5 Traceability
The system should make it possible to understand:
- what inputs were used
- what assumptions were made
- what artifacts were produced
- what validation issues were found
- what repair path was taken

### 19.6 Modularity
Core responsibilities should remain logically separated even if implementation approaches evolve.

### 19.7 Controlled Inference
The system should make a meaningful distinction between:
- user-supplied data
- reusable profile data
- specification-derived requirements
- inferred or synthesized content

### 19.8 Safe Failure
The system should prefer explicit warnings, repair loops, or user intervention over silently producing misleading output.

## 20. Architectural Success Criteria

At a high level, the architecture should be considered successful if it enables the following:

- a user can initiate a bundle request with reusable context and natural language instructions
- the system can create a structurally appropriate initial bundle scaffold
- the system can determine and execute a dependency-aware build order
- the system can construct resources and data elements incrementally
- the system can validate the assembled bundle
- the system can target repairs to the correct layer of the workflow
- the process is inspectable enough that a human can understand how the output was produced
- the architecture can be extended later without major rework of the core workflow model
- the system can ingest and normalize additional FHIR specifications without requiring redesign of the workflow layer

## 21. Assumptions

The following assumptions underlie this document:

- reusable patient and provider context will exist or be created by related parts of the system
- specification knowledge can be made available to the workflow in a usable form
- raw FHIR implementation-guide materials can be transformed into agent-usable assets through a preprocessing or ingestion pipeline
- the initial focus is architectural correctness rather than enterprise deployment concerns
- the project will use an implementation process in which development artifacts and decisions are documented iteratively outside this baseline document
- Codex or another coding agent will be guided through bounded slices under architectural supervision rather than operating without control

## 22. Open Areas Intentionally Deferred

The following topics are intentionally deferred to later design and implementation documentation:

- exact storage technology and schema
- exact agent framework implementation details
- exact prompt and message contract design
- exact UI flows and layout decisions
- exact validation engine design
- exact terminology service integration model
- exact deployment model
- exact authentication and authorization model
- exact logging and observability implementation
- exact artifact serialization formats beyond what becomes necessary during development
- exact internal normalized schema for ingested specification assets

## 23. Summary

The AI-Assisted FHIR Bundle Builder is a structured, multi-agent system for generating FHIR bundles from specification knowledge, reusable patient/provider context, and user instructions. Its defining architectural characteristic is that it does not treat bundle generation as a single AI output problem. Instead, it breaks the problem into orchestrated stages: request normalization, bundle schematic generation, dependency-aware build planning, incremental resource construction, element-level construction, validation, and repair.

A second foundational characteristic is that the system treats raw FHIR specification content as source material rather than as something agents should parse ad hoc during runtime. The architecture therefore includes a specification ingestion layer that transforms implementation-guide artifacts into normalized, versioned knowledge assets that agents can use repeatedly and consistently.

The architecture is intended to remain stable even as implementation details evolve. The core commitments that should remain true throughout development are the use of reusable inputs, staged agent responsibilities, inspectable intermediate artifacts, dependency-aware construction, validation-driven repair, specification-ingestion support, and a design that can grow over time without losing control of the workflow.
