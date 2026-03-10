PS-CA Bundle Assembly Platform

Formal Design Document

Document filename: docs/psca-bundle-assembly-architecture.md

1. Purpose

This document defines the formal design for a configurable multi-agent application that generates realistic, syntactically valid, and profile-aware synthetic FHIR bundles, with the initial implemented use case being the creation of a PS-CA patient summary bundle.

The design has two goals:
	1.	Deliver a useful domain-relevant prototype for synthetic PS-CA bundle generation.
	2.	Provide a structured implementation vehicle for learning and demonstrating Microsoft Agent Framework in a serious, non-toy scenario.

This document describes the business purpose, scope, architecture, functional behavior, system requirements, design constraints, risks, and phased implementation approach.

2. Background and rationale

FHIR bundles, especially document-style bundles such as patient summaries, are difficult to generate reliably in a single pass. They are modular, deeply structured, reference-heavy, and often subject to profile-specific conformance constraints. Large one-shot generation tends to produce broken references, missing sections, invalid terminology, profile drift, and unstable repair loops.

This design addresses that problem by decomposing bundle creation into controlled stages:
	•	derive a realistic clinical profile,
	•	convert that profile into a structured build specification,
	•	generate resources one at a time,
	•	validate each artifact deterministically,
	•	assemble the final Composition and Bundle,
	•	perform final consistency and conformance review.

The architecture intentionally separates clinical reasoning from FHIR construction and separates LLM-driven generation from deterministic conformance tooling.

3. Objectives

The platform shall:
	•	generate a synthetic PS-CA bundle from a high-level natural-language request,
	•	produce clinically plausible content,
	•	validate resources and bundles using deterministic tooling,
	•	show clear multi-agent orchestration behavior,
	•	support configurable model selection by role,
	•	support future extension to other bundle types without re-architecting the core platform.

4. Scope

4.1 In scope for Version 1

Version 1 includes:
	•	one implemented bundle type: PS-CA patient summary,
	•	one user-facing coordinator,
	•	one requirements derivation stage,
	•	one assembly manager stage,
	•	one reusable resource builder role,
	•	one validator/explainer role,
	•	deterministic FHIR validation integration,
	•	terminology lookup integration,
	•	per-agent memory using simple Markdown or JSON files,
	•	structured artifacts between agents,
	•	visible execution trace,
	•	local execution on a Windows machine through a simple local interface.

4.2 Out of scope for Version 1

Version 1 excludes:
	•	vector databases,
	•	dynamic agent spawning,
	•	MCP transport,
	•	cloud-native production deployment,
	•	multiple bundle families,
	•	agent group chat,
	•	advanced autonomous worker-to-worker collaboration,
	•	enterprise-grade security hardening,
	•	full production scalability and observability.

5. Guiding design principles

5.1 One base agent pattern, role-configured instances

The solution shall use one underlying agent construction pattern and instantiate it into different roles through configuration. Agents differ by instructions, tools, memory, model configuration, and allowed responsibilities, not by completely separate architectural approaches.

5.2 Workflow-led architecture

The platform shall be controlled by deterministic workflow logic rather than relying on open-ended agent conversation to determine process order. Agents perform bounded reasoning and generation tasks inside an explicitly managed workflow.

5.3 Structured artifact exchange

Agents shall exchange typed structured artifacts rather than loose conversational prose. Structured artifacts improve inspectability, reliability, debugging, and testability.

5.4 Deterministic truth for conformance

FHIR conformance and terminology correctness shall not be delegated to LLM judgment. Deterministic tools shall be the source of truth for validation and coding support.

5.5 Minimal context injection

Each build step shall receive only the information necessary for that step. The full partial bundle shall not be repeatedly injected into every resource generation request.

5.6 Hard circuit breakers

All repair loops shall have explicit retry limits. Infinite or unbounded build-validate-repair cycles are prohibited.

6. Intended users and usage scenario

The primary users are internal technical and business stakeholders who want to see how a configurable multi-agent platform can construct complex healthcare artifacts in a transparent, cost-aware way.

A typical request is:

“Create a PS-CA patient summary for a 25-year-old patient with stomach cancer, one active medication, one allergy, and one recent procedure.”

The user interacts with a single visible coordinator. The system returns:
	•	the final synthetic PS-CA bundle,
	•	a validation summary,
	•	assumptions and deviations,
	•	a readable trace showing how agents coordinated the work.

7. Solution overview

The platform is a configurable multi-agent bundle assembly system with PS-CA as the first supported manifest.

At a high level, the system works as follows:
	1.	The Coordinator receives the request and explains the execution plan.
	2.	The Requirements Agent derives a structured patient summary specification.
	3.	The Assembly Manager converts the specification into an ordered build plan.
	4.	The Resource Builder is invoked repeatedly to generate individual resources.
	5.	Deterministic validation is run after each resource.
	6.	The Validator Agent interprets validator output and recommends fixes.
	7.	The Assembly Manager retries or escalates according to policy.
	8.	Composition is built from accepted resources.
	9.	The final Bundle is assembled and validated.
	10.	The Coordinator verifies consistency with the original request and returns the final delivery package.

8. Logical architecture

The system consists of six logical layers.

8.1 User interaction layer

Provides a simple command-line or local web interface for:
	•	receiving user requests,
	•	displaying progress,
	•	showing coordination narration,
	•	returning final results.

8.2 Agent layer

Contains configured Microsoft Agent Framework agents:
	•	Coordinator Agent
	•	Requirements Agent
	•	Assembly Manager Agent
	•	Resource Builder Agent
	•	Validator Agent

8.3 Workflow control layer

Contains deterministic orchestration logic responsible for:
	•	stage order,
	•	artifact routing,
	•	dependency sequencing,
	•	retry limits,
	•	escalation,
	•	delivery packaging.

8.4 Tooling layer

Contains deterministic tools, including:
	•	FHIR validator wrapper,
	•	terminology lookup tool,
	•	manifest/profile lookup,
	•	artifact persistence,
	•	bundle assembly helper,
	•	ID/reference generation helper.

8.5 Artifact and memory layer

Stores:
	•	structured artifacts,
	•	per-agent memory files,
	•	accepted resources,
	•	validation outputs,
	•	execution traces,
	•	final delivery packages.

8.6 Configuration layer

Defines runtime configuration for:
	•	agent roles,
	•	model selection,
	•	enabled tools,
	•	retry policy,
	•	bundle manifests,
	•	logging verbosity,
	•	storage paths.

9. Microsoft Agent Framework usage

The design uses Microsoft Agent Framework in the following way.

9.1 Agents

Each role is implemented as a configured agent instance using the same underlying construction model. The framework provides the agent abstraction for instructions, tools, context, state, and invocation behavior.

9.2 Function-based workflows

The core control logic is implemented through function-based workflow orchestration. This is the primary mechanism for controlling process order and lifecycle, not emergent agent conversation.

9.3 Tools

Agents use tools for deterministic capabilities such as validation, terminology lookup, file operations, manifest loading, and bundle assembly support.

9.4 Context and memory

Each agent has its own role instructions and its own simple persistent memory source. Context injection is constrained and task-specific.

9.5 Middleware and tracing

Middleware-capable design is retained in the architecture, but advanced middleware is not required for the first milestone. Version 1 tracing may be implemented in a simpler way first.

10. Agent role definitions

10.1 Coordinator Agent

Purpose
Acts as the single visible entry point and orchestrates the overall request lifecycle.

Responsibilities
	•	receive the user request,
	•	explain the planned stages,
	•	launch requirements derivation,
	•	launch assembly,
	•	launch final validation/review,
	•	compare final output to the original request,
	•	return the final delivery package.

Key behavioral requirement
The Coordinator must narrate what the system is doing so the orchestration is visible and understandable during a demo.

10.2 Requirements Agent

Purpose
Transforms a high-level request into a realistic structured clinical specification.

Responsibilities
	•	infer clinically plausible facts,
	•	resolve coded concepts where possible,
	•	determine likely section content,
	•	produce a structured Patient Summary Specification,
	•	record assumptions and realism notes.

Important boundary
This role does not build FHIR resources.

10.3 Assembly Manager Agent

Purpose
Converts the clinical specification into a build plan and manages staged construction.

Responsibilities
	•	determine resource build order,
	•	create bounded resource task packets,
	•	invoke the Resource Builder,
	•	invoke validation after each build,
	•	apply retry policy,
	•	control escalation,
	•	manage Composition creation,
	•	trigger final Bundle assembly.

Important boundary
The Assembly Manager operates within workflow-defined rules. It does not invent the overall process dynamically.

10.4 Resource Builder Agent

Purpose
Generates one resource at a time from a bounded task packet.

Responsibilities
	•	generate the target resource,
	•	revise the resource when validation feedback is supplied,
	•	return a structured result.

Important boundary
The Resource Builder does not solve the whole bundle. It only handles the current resource task.

10.5 Validator Agent

Purpose
Interprets deterministic validation output and formulates fix guidance.

Responsibilities
	•	run or consume deterministic validator output,
	•	summarize issues,
	•	classify issue severity,
	•	formulate repair suggestions,
	•	return a structured validation result.

Important boundary
The Validator Agent is not the conformance authority. Deterministic tooling is.

11. Generic workflow design

The platform shall support a reusable generic workflow shape that can be reused for bundle types beyond PS-CA.

11.1 Generic workflow stages
	1.	Intake request
	2.	Derive requirements/specification
	3.	Create build plan
	4.	Build foundational resources
	5.	Validate foundational resources
	6.	Build dependent clinical resources
	7.	Validate dependent clinical resources
	8.	Build composition-level artifacts
	9.	Assemble final bundle
	10.	Validate full bundle
	11.	Perform final consistency review
	12.	Deliver results

11.2 PS-CA specialization

For PS-CA, the generic workflow is specialized through a manifest that defines:
	•	required sections,
	•	expected resource types,
	•	resource dependency order,
	•	section composition rules,
	•	PS-CA-specific validation expectations.

This keeps the workflow reusable while allowing bundle-specific behavior through configuration.

12. Structured artifact contracts

The following structured artifacts are mandatory.

12.1 RequestPacket

Represents the incoming user request and execution metadata.

12.2 PatientSummarySpecification

Represents the clinically realistic structured specification derived by the Requirements Agent.

12.3 BuildPlan

Represents the ordered construction plan and dependency map.

12.4 ResourceTaskPacket

Represents a single bounded build request for one resource.

12.5 ValidationResult

Represents the outcome of deterministic validation plus interpreted fix guidance.

12.6 DeliveryPackage

Represents the final returned result to the user, including bundle, validation summary, assumptions, deviations, and execution trace.

These artifacts should be implemented early as explicit Python models.

13. Tooling requirements

13.1 Deterministic FHIR Validator Tool

The platform shall use a real FHIR validator tool as the conformance source of truth. The tool must support:
	•	resource-level validation,
	•	bundle-level validation,
	•	machine-readable output,
	•	PS-CA-relevant profile validation.

13.2 Terminology Lookup Tool

The platform shall support deterministic lookup of terminology codes and displays to reduce hallucinated coding and code/display mismatches.

13.3 Artifact Persistence Tooling

The platform shall persist:
	•	structured artifacts,
	•	resource JSON,
	•	memory files,
	•	validator outputs,
	•	delivery outputs,
	•	execution logs.

13.4 Bundle Assembly Support

The platform shall provide deterministic support for final bundle construction, reference wiring, and entry arrangement.

14. Memory design

Version 1 memory shall remain intentionally simple.

Each agent shall have:
	•	its own current execution/session state,
	•	its own persistent memory file stored as Markdown or JSON.

Example memory domains:
	•	Coordinator: presentation preferences, demo notes
	•	Requirements Agent: clinical realism patterns
	•	Assembly Manager: build policy notes
	•	Resource Builder: generation hints and pitfalls
	•	Validator: common validation issue interpretations

Structured artifacts remain the primary source of process truth. Memory is supplementary.

15. Context injection policy

The following context discipline rules are mandatory.
	1.	Do not pass the full partially built bundle into every build step.
	2.	Pass only the facts, references, and constraints needed for the current resource.
	3.	Store accepted artifacts outside the prompt context and reference them by ID or extracted fields.
	4.	Keep prompts focused on the local task.

This policy is critical to control cost, improve quality, and avoid context-window degradation.

16. Retry and escalation policy

The platform shall implement hard retry limits.

16.1 Resource retry cap

Recommended default:
	•	maximum three retries per resource

16.2 Escalation behavior

If a resource fails after the retry cap:
	•	mark the step as failed,
	•	halt or transition to controlled failure,
	•	bubble the issue to the Coordinator,
	•	include the failure in the final execution trace.

16.3 No silent degradation

The system shall not silently omit required resources to make the final bundle appear complete.

17. Configuration design

The system shall be heavily configuration-driven.

17.1 Agent configuration

Each role shall support configuration for:
	•	role name,
	•	instructions,
	•	model provider,
	•	model name,
	•	tools,
	•	memory source,
	•	output contract,
	•	verbosity.

17.2 Workflow configuration

The workflow shall support configuration for:
	•	bundle type,
	•	stage order,
	•	retry limits,
	•	escalation behavior,
	•	validation behavior.

17.3 Manifest configuration

Bundle-specific rules such as PS-CA requirements shall live in manifest/configuration, not deeply hardcoded control logic.

17.4 Model configuration

All model selection must be externalized so the same architecture can support different providers and cost strategies.

18. Functional requirements

FR-1 The system shall accept a natural-language request for a synthetic PS-CA patient summary bundle.

FR-2 The system shall derive a structured clinical specification from the request.

FR-3 The system shall perform terminology lookup for coded clinical concepts where required.

FR-4 The system shall generate a build plan from the clinical specification.

FR-5 The system shall build resources one at a time through a reusable Resource Builder role.

FR-6 The system shall validate each generated resource using deterministic FHIR validation tooling.

FR-7 The system shall retry failed resource generation up to a configurable retry limit.

FR-8 The system shall build a Composition from validated resources.

FR-9 The system shall assemble a final Bundle from validated resources and Composition.

FR-10 The system shall validate the final Bundle using deterministic validation tooling.

FR-11 The system shall provide a human-readable explanation of validation outcomes.

FR-12 The system shall provide a visible execution trace of delegation and progress.

FR-13 The system shall maintain separate memory/state per agent instance.

FR-14 The system shall support configurable model selection by role.

FR-15 The system shall persist intermediate artifacts for inspection and debugging.

FR-16 The system shall support future bundle types through manifests and configuration rather than requiring a full architectural rewrite.

19. Non-functional requirements

NFR-1 Simplicity
Version 1 shall favor simple, inspectable implementation choices.

NFR-2 Transparency
The coordination behavior must be visible and understandable during a live demonstration.

NFR-3 Deterministic conformance
FHIR validation results must come from deterministic tooling.

NFR-4 Modularity
Bundle-specific logic must be separated from generic platform logic.

NFR-5 Configurability
Models, tools, instructions, retries, and manifests must be externally configurable.

NFR-6 Loop safety
The system must prevent runaway validation and repair loops.

NFR-7 Context discipline
The system must minimize unnecessary context transfer between stages.

NFR-8 Reusability
The Resource Builder and workflow pattern must be reusable across future bundle types.

NFR-9 Inspectability
Artifacts and logs must be stored in a way that supports review and troubleshooting.

NFR-10 Demo readiness
The system must run locally in a practical demo setup on the Windows machine.

20. Assumptions

The design assumes:
	•	a Windows machine will be used as the first main runtime host,
	•	development documentation may be prepared on a Mac,
	•	models are API-accessible and configurable by role,
	•	deterministic FHIR validation tooling is available or can be wrapped,
	•	terminology lookup can be implemented in at least a lightweight form,
	•	the first interface can be simple and does not need production UX.

21. Risks and mitigations

Risk: infinite build/validate loops

Mitigation: hard retry caps and escalation rules.

Risk: hallucinated terminology

Mitigation: deterministic terminology lookup and coded facts in the specification stage.

Risk: context bloat

Mitigation: bounded task packets and strict context injection policy.

Risk: invalid bundle references

Mitigation: staged build order, deterministic ID/reference handling, and final assembly checks.

Risk: agents drifting from responsibilities

Mitigation: role-specific instructions, structured contracts, and workflow-led control.

Risk: early framework complexity slowing delivery

Mitigation: defer advanced middleware/context-provider sophistication until after the first successful vertical slice.

22. Implementation phases

Phase 1: foundation
	•	define artifact contracts,
	•	define PS-CA manifest,
	•	define configuration schema,
	•	establish repo structure.

Phase 2: deterministic tooling
	•	wrap FHIR validator,
	•	implement terminology lookup,
	•	implement persistence helpers.

Phase 3: first workflow slice
	•	implement Coordinator,
	•	implement Requirements Agent,
	•	implement simple build plan generation.

Phase 4: resource assembly loop
	•	implement Assembly Manager,
	•	implement Resource Builder,
	•	implement Validator Agent,
	•	implement retry and escalation logic.

Phase 5: final assembly
	•	implement Composition creation,
	•	implement Bundle assembly,
	•	implement final validation,
	•	implement DeliveryPackage generation.

Phase 6: demo hardening
	•	improve trace visibility,
	•	improve logs,
	•	refine prompts and configs,
	•	polish user interaction flow.

23. Recommended repository intent

The project should be structured as a reusable platform with a PS-CA manifest, not as a one-off PS-CA script. The architecture should make it obvious that future bundle types can be added by introducing new manifests, rules, and profile-specific helpers while reusing the same base platform.

24. Conclusion

The recommended solution is a configurable, workflow-led, multi-agent FHIR bundle assembly platform with PS-CA as the first implemented use case.

Its central design decision is to separate:
	•	clinical realism from FHIR construction,
	•	generation from deterministic validation,
	•	reusable platform logic from bundle-specific manifests,
	•	agent reasoning from workflow control.

This architecture is technically credible, aligned with Microsoft Agent Framework’s strengths, suitable for a strong internal demo, and extensible enough to support future bundle-generation scenarios beyond PS-CA.

If you want the next step, I’d turn this into a repo-ready set of markdown documents: overview.md, architecture.md, requirements.md, risks.md, and implementation-phases.md.
