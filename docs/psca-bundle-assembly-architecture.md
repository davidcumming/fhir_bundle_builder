Yes. Here is the revised design document with Microsoft Agent Framework as the orchestration/runtime layer and OpenViking as the context layer.

PS-CA Bundle Assembly Platform

Revised Design Document

Microsoft Agent Framework + OpenViking

Recommended filename: docs/psca-bundle-assembly-architecture.md

1. Purpose

This document defines the revised architecture for a configurable multi-agent application that generates realistic, syntactically valid, and profile-aware synthetic FHIR bundles, with the first implemented use case being a PS-CA patient summary bundle.

The revised design uses:
	•	Microsoft Agent Framework for agents, workflows, tools, stateful orchestration, and multi-agent runtime behavior. Microsoft describes Agent Framework as a framework for building AI agents and multi-agent workflows in Python and .NET, with features such as session-based state management, type safety, filters, telemetry, and extensive model support.  ￼
	•	OpenViking for unified context management, specifically memory, resources, and skills organized through a filesystem-style context model. OpenViking describes itself as an open-source context database for AI agents that unifies memories, resources, and skills using a file-system paradigm.  ￼

This design keeps the orchestration logic explicit and deterministic while offloading context storage, retrieval, and agent-facing knowledge organization to OpenViking.

2. Architectural intent

The main architectural shift is this:
	•	Before: simple file-based memory and local context injection managed directly by the application.
	•	Now: OpenViking becomes the context substrate under the application, while Microsoft Agent Framework remains the agent and workflow runtime.

That means the app is still your app. OpenViking does not replace the application architecture. It replaces much of the ad hoc memory/context layer you were planning to build yourself. OpenViking is specifically focused on context management and hierarchical delivery of memory, resources, and skills, while Agent Framework provides the agent and workflow primitives.  ￼

3. Business objective

The system should accept a request such as:

“Create a PS-CA patient summary for a 25-year-old patient with stomach cancer, one active medication, one allergy, and one recent procedure.”

It should then:
	1.	derive a realistic clinical profile,
	2.	resolve terminology and clinical assumptions,
	3.	build the patient summary bundle resource by resource,
	4.	validate each resource deterministically,
	5.	assemble and validate the final bundle,
	6.	return the result plus a visible execution trace.

The design must also demonstrate a credible enterprise pattern:
	•	model mixing by role,
	•	explicit workflow-led coordination,
	•	reusable structured contracts,
	•	centralized context management,
	•	future support for other bundle types.

4. High-level architecture

The system is composed of five major layers.

4.1 User interaction layer

A simple local interface, such as CLI or minimal web UI, used to submit requests and display:
	•	execution narration,
	•	intermediate progress,
	•	validation results,
	•	final bundle output.

4.2 Agent orchestration layer

Implemented with Microsoft Agent Framework.

This layer contains the runtime roles:
	•	Coordinator Agent
	•	Requirements Agent
	•	Assembly Manager Agent
	•	Resource Builder Agent
	•	Validator Agent

Microsoft Agent Framework’s ChatAgent is the primary Python agent implementation and supports tools, context providers, middleware, and both streaming and non-streaming responses.  ￼

4.3 Workflow control layer

Also implemented with Microsoft Agent Framework.

This layer is responsible for:
	•	stage order,
	•	dependency sequencing,
	•	retries and escalation,
	•	assembly flow,
	•	final delivery.

Microsoft positions workflows as a type-safe orchestration mechanism for blending AI agents with business processes.  ￼

4.4 Context layer

Implemented with OpenViking.

This layer stores and serves:
	•	agent memory,
	•	reusable resources,
	•	bundle manifests,
	•	validation knowledge,
	•	terminology guidance,
	•	role-specific skills or reference assets.

OpenViking describes its main value as unifying memories, resources, and skills through a hierarchical file-system paradigm for agents.  ￼

4.5 Deterministic tooling layer

Implemented by your application as wrapped tools/services.

This layer provides:
	•	FHIR validation,
	•	terminology lookup,
	•	artifact persistence,
	•	bundle assembly helpers,
	•	ID/reference helpers.

This remains application-owned and is not replaced by OpenViking.

5. Core design principles

5.1 Microsoft Agent Framework owns orchestration

All runtime execution, role invocation, and stage progression should be handled by Agent Framework. That is what it is built for. Microsoft explicitly positions it as the successor to AutoGen and Semantic Kernel for building and orchestrating AI agents and workflows.  ￼

5.2 OpenViking owns context organization

All agent memory, reusable domain knowledge, manifests, prompt resources, and retrieval-oriented context should be organized through OpenViking wherever practical. OpenViking is specifically designed to manage agent memory, resources, and skills under one context model.  ￼

5.3 Structured artifact contracts remain mandatory

Even with OpenViking, agents must exchange typed payloads, not loose prose. OpenViking is a context system, not a substitute for explicit contracts between workflow stages.

5.4 Deterministic tooling remains the source of truth

OpenViking does not replace:
	•	deterministic FHIR validation,
	•	terminology resolution,
	•	assembly logic,
	•	retry policy.

Those remain application responsibilities.

5.5 Minimal injected context remains mandatory

OpenViking can improve context retrieval, but the Assembly Manager must still pass only the minimum required context into each build task. OpenViking’s file-system-style hierarchical context model is useful here because it supports navigable and structured context rather than dumping everything into one prompt.  ￼

6. Revised solution overview

The application is now best described as:

A workflow-led multi-agent FHIR bundle assembly platform built on Microsoft Agent Framework, using OpenViking as the shared context database for memory, resources, and skill-like domain assets.

Functionally, it still behaves the same:
	•	a Coordinator accepts the request,
	•	a Requirements Agent derives the clinical specification,
	•	an Assembly Manager controls staged construction,
	•	a Resource Builder generates one resource at a time,
	•	a Validator interprets deterministic validation output,
	•	the final result is returned with a trace.

The change is in how context is stored and delivered:
	•	role instructions can be stored as OpenViking resources,
	•	agent memory can be stored in OpenViking,
	•	PS-CA manifests can be stored in OpenViking,
	•	validation playbooks can be stored in OpenViking,
	•	future reusable bundle patterns can be stored in OpenViking.

7. Agent roles

The roles stay the same.

7.1 Coordinator Agent

Purpose:
	•	user-facing orchestration and narration.

Responsibilities:
	•	accept request,
	•	explain plan,
	•	trigger major stages,
	•	report status,
	•	compare final output to original request,
	•	return delivery package.

OpenViking usage:
	•	store coordinator operating instructions,
	•	store narration style guidance,
	•	store prior demo or usage preferences.

7.2 Requirements Agent

Purpose:
	•	derive a realistic patient summary specification.

Responsibilities:
	•	infer clinically plausible content,
	•	normalize the request into structured facts,
	•	pull reference knowledge,
	•	resolve coding assumptions through deterministic tools.

OpenViking usage:
	•	store disease profiles,
	•	patient archetypes,
	•	reusable clinical reference notes,
	•	bundle-specific realism guidance.

This is one of the strongest OpenViking fits, because the Requirements Agent benefits heavily from organized, reusable domain context.

7.3 Assembly Manager Agent

Purpose:
	•	convert the specification into a build plan and control resource-level execution.

Responsibilities:
	•	create ordered task packets,
	•	manage dependencies,
	•	invoke Builder repeatedly,
	•	invoke Validator,
	•	enforce retry caps,
	•	escalate failures.

OpenViking usage:
	•	store bundle manifests,
	•	resource dependency maps,
	•	build policy notes,
	•	reusable strategy resources by bundle type.

7.4 Resource Builder Agent

Purpose:
	•	build one resource at a time.

Responsibilities:
	•	consume one bounded task packet,
	•	generate the target resource,
	•	revise based on validator feedback,
	•	return resource output.

OpenViking usage:
	•	store resource drafting guidance,
	•	resource-specific templates,
	•	profile hints,
	•	common pitfalls and examples.

7.5 Validator Agent

Purpose:
	•	explain deterministic validation output and propose fixes.

Responsibilities:
	•	read validator output,
	•	summarize issues,
	•	classify issues,
	•	suggest fixes,
	•	signal retryable vs non-retryable failures.

OpenViking usage:
	•	store validator troubleshooting notes,
	•	known PS-CA profile failure patterns,
	•	fix heuristics,
	•	mappings from common validator errors to repair guidance.

8. Workflow design

The core workflow remains generic and bundle-driven.

8.1 Generic workflow stages
	1.	Intake request
	2.	Derive structured requirements
	3.	Create build plan
	4.	Build foundational resources
	5.	Validate foundational resources
	6.	Build dependent resources
	7.	Validate dependent resources
	8.	Build Composition
	9.	Assemble Bundle
	10.	Validate Bundle
	11.	Final consistency review
	12.	Deliver output

8.2 PS-CA specialization

PS-CA is implemented as a bundle manifest plus domain assets, not a special-purpose one-off application.

That manifest and its supporting context can now live inside OpenViking, which is one of the biggest architectural wins. OpenViking is explicitly meant to organize resources and skills in a structured hierarchy, which is a strong match for bundle manifests, section rules, and reference material.  ￼

9. Structured artifact contracts

These remain unchanged in principle and should still be implemented first in code.

Mandatory contracts:
	•	RequestPacket
	•	PatientSummarySpecification
	•	BuildPlan
	•	ResourceTaskPacket
	•	ValidationResult
	•	DeliveryPackage

OpenViking should not replace these contracts. It should support them by providing context to agents before they execute.

10. Revised context architecture

This is the main change.

10.1 What moves into OpenViking

OpenViking should manage:
	•	role instructions
	•	persistent agent memory
	•	reusable domain resources
	•	clinical reference notes
	•	PS-CA manifest and section guidance
	•	resource construction hints
	•	validator troubleshooting notes
	•	bundle-type-specific playbooks
	•	future skill-like reusable assets

10.2 What stays outside OpenViking

The following should remain application-owned:
	•	Pydantic contract models
	•	workflow logic
	•	retry counters
	•	escalation logic
	•	deterministic validator invocation
	•	terminology service invocation
	•	final bundle assembly logic
	•	execution trace generation
	•	app configuration for runtime wiring

10.3 Why this split is correct

OpenViking is designed as a context database for agents, not as a full workflow engine. Microsoft Agent Framework is designed to build and orchestrate AI agents and workflows. Keeping those concerns separated gives you a cleaner architecture and less framework confusion.  ￼

11. Deterministic tooling requirements

These requirements become even more important in the revised design.

11.1 FHIR Validator Tool

Must remain deterministic and authoritative.

11.2 Terminology Lookup Tool

Must remain deterministic and be used to resolve codes rather than relying on model memory.

11.3 Bundle Assembly Tool

Must remain deterministic and handle final structural assembly.

11.4 Artifact Persistence

The app still needs its own persisted runtime outputs even if OpenViking stores contextual resources.

12. Configuration design

The revised system should be config-heavy.

12.1 Agent role config

Each agent role should declare:
	•	name
	•	instructions resource path
	•	model provider
	•	model name
	•	enabled tools
	•	OpenViking context roots
	•	output contract
	•	logging verbosity

12.2 Workflow config

Workflow config should declare:
	•	bundle type
	•	stage ordering
	•	retry limits
	•	escalation behavior
	•	validation behavior

12.3 OpenViking mapping config

Add a dedicated mapping layer that declares where each role reads context from in OpenViking.

For example:
	•	coordinator context root
	•	requirements context root
	•	assembly manager context root
	•	builder context root
	•	validator context root
	•	bundle manifest root

That makes the architecture much more maintainable.

13. Functional requirements

FR-1 The system shall accept a high-level request for a synthetic PS-CA bundle.

FR-2 The system shall derive a structured clinical specification from the request.

FR-3 The system shall retrieve role-relevant context from OpenViking before agent execution where configured.

FR-4 The system shall generate a bundle build plan from the specification.

FR-5 The system shall generate resources one at a time using a reusable Resource Builder.

FR-6 The system shall validate each resource using deterministic validation tooling.

FR-7 The system shall use deterministic terminology lookup where required.

FR-8 The system shall assemble Composition and Bundle artifacts from validated resources.

FR-9 The system shall validate the final Bundle using deterministic tooling.

FR-10 The system shall return a user-visible execution trace.

FR-11 The system shall maintain separate role-specific context and memory roots.

FR-12 The system shall support configurable model selection by role.

FR-13 The system shall support future bundle types through manifests and OpenViking resource trees, not architectural rewrite.

14. Non-functional requirements

NFR-1 Simplicity
Version 1 shall avoid unnecessary complexity in OpenViking integration and use it primarily for context storage and retrieval.

NFR-2 Transparency
The system shall visibly narrate coordination decisions.

NFR-3 Deterministic conformance
FHIR validation and terminology correctness must not rely on LLM judgment.

NFR-4 Modularity
Orchestration must remain in Agent Framework and context must remain in OpenViking.

NFR-5 Configurability
Roles, models, tools, bundle manifests, and OpenViking roots must be externally configurable.

NFR-6 Loop safety
The assembly loop must enforce hard retry limits.

NFR-7 Context discipline
The system must inject only minimal relevant context.

NFR-8 Extensibility
The platform must support new bundle types by adding manifests, resource trees, and configuration.

15. Technical implications

15.1 Benefits of this revised approach

This revision can reduce the amount of custom context plumbing you need to build yourself. OpenViking’s design goal is to provide a unified context database for agent memory, resources, and skills.  ￼

It also gives you a stronger future story:
	•	richer context organization,
	•	reusable knowledge assets,
	•	easier multi-role context separation,
	•	cleaner scaling beyond PS-CA.

15.2 Added complexity

This also adds another framework to your stack. OpenViking’s prerequisites include Python 3.10+, Go 1.22+, and a modern C++ compiler for some components, and it supports Linux, macOS, and Windows.  ￼

So this revision is stronger architecturally, but heavier operationally.

16. Recommended implementation strategy

Do not fully replatform everything at once.

Recommended phased approach:

Phase 1

Keep building the core Agent Framework app:
	•	contracts
	•	workflow
	•	validator wrapper
	•	terminology tool
	•	basic roles

Phase 2

Introduce OpenViking as the context backend for:
	•	role instructions
	•	manifests
	•	memory/resources

Phase 3

Refactor context loading so agents consume OpenViking-backed context systematically rather than ad hoc local files.

That sequence reduces risk.

17. Revised conclusion

The revised architecture should be:
	•	Microsoft Agent Framework for runtime orchestration, agents, workflows, tool invocation, and stateful execution.  ￼
	•	OpenViking for unified context management, including memory, resources, and skill-like domain assets.  ￼
	•	Your application layer for artifact contracts, deterministic validation, terminology lookup, assembly control, retry policy, and delivery packaging.

That is the correct split.

It gives you a stronger platform story than the original design, while still preserving the core rule that matters most: workflow control and conformance logic remain explicit, inspectable, and deterministic.

If you want, the next move is to convert this into a repo-ready folder structure and implementation plan that assumes OpenViking is part of the stack.
