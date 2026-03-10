Here is the complete revised application architecture and system requirements for the solution you are building.

1. Solution overview

The solution is a configurable multi-agent application for generating a realistic, syntactically valid, and profile-aware synthetic FHIR bundle, with the first implemented use case being a PS-CA patient summary bundle.

The system takes a high-level user request such as:

“Create a PS-CA patient summary for a 25-year-old patient with stomach cancer, one active medication, one allergy, and one recent procedure.”

It then:
	1.	derives a realistic clinical profile,
	2.	converts that profile into a structured bundle build plan,
	3.	builds the bundle resource by resource,
	4.	validates each resource with deterministic tooling,
	5.	assembles the final Composition and Bundle,
	6.	performs final validation and consistency review,
	7.	returns the final bundle plus an execution trace showing how the agents coordinated the work.

This is not a toy chatbot. It is a controlled assembly pipeline that uses agents for judgment and generation, and deterministic workflow/tooling for process control and conformance.

2. Primary design goals

The architecture should satisfy these goals:
	1.	Demonstrate Microsoft Agent Framework clearly.
	2.	Show multiple agents working together in a visible, understandable way.
	3.	Show cost-optimized model mixing by role.
	4.	Be modular enough to support future bundle types beyond PS-CA.
	5.	Use deterministic validation rather than relying on LLM judgment for FHIR conformance.
	6.	Keep memory simple in v1.
	7.	Keep the architecture generic while making the first implemented manifest PS-CA-specific.
	8.	Produce something that is demoable and also genuinely useful.

3. Core architectural principles

3.1 One base agent design, many configured roles

All agents should use the same underlying agent construction pattern.

Each agent instance should be configurable with:
	•	role name
	•	role description
	•	instructions
	•	model provider
	•	model name
	•	tool set
	•	memory file/path
	•	output schema
	•	allowed task types
	•	visibility/logging settings

This means coordinator, requirements agent, builder, and validator are not totally different implementations. They are role-configured instances of the same base agent pattern.

3.2 Workflow controls the system, not agent chat

The architecture must be workflow-led, not chat-led.

Agents should not improvise the full end-to-end process through open conversation. Instead, a function-based workflow should control:
	•	stage order
	•	agent invocation
	•	resource dependencies
	•	retry limits
	•	escalation behavior
	•	final delivery

3.3 Structured artifacts only

Agents must exchange structured artifacts, not loose prose.

Use typed payloads such as Pydantic models or equivalent.

This is mandatory.

3.4 Deterministic tooling is the source of truth

LLMs should not be the final authority for FHIR validation or terminology correctness.

Use deterministic tools for:
	•	FHIR validation
	•	terminology lookup
	•	bundle assembly logic where practical

The LLM-based validator becomes an interpreter and fixer-assistant, not the conformance engine.

3.5 Minimal context injection

Each task packet should include only the context required for that task.

Do not pass the entire bundle or full build history into every resource generation step.

3.6 Hard circuit breakers

All repair loops must have bounded retry limits.

No infinite builder-validator loops.

4. Functional scope of v1

4.1 In scope

Version 1 should support:
	•	one bundle type: PS-CA patient summary
	•	one user-facing coordinator
	•	one requirements derivation stage
	•	one assembly manager stage
	•	one reusable resource builder invoked repeatedly
	•	one validator/explainer stage
	•	deterministic FHIR validation integration
	•	terminology lookup integration
	•	per-agent memory using Markdown or JSON
	•	visible execution trace
	•	model selection by configuration
	•	local API execution on the Windows machine

4.2 Out of scope for v1

Do not include these in version 1:
	•	vector database memory
	•	dynamic agent spawning
	•	MCP transport
	•	cloud deployment complexity
	•	multiple bundle types
	•	group chat orchestration
	•	advanced long-term memory systems
	•	autonomous worker-to-worker communication
	•	production security hardening

5. High-level system architecture

The system consists of the following major layers:

5.1 User interaction layer

This is the simplest possible interface for v1.

Recommended options:
	•	command-line chat interface, or
	•	minimal local web UI

Responsibilities:
	•	accept the user request
	•	display coordination trace
	•	display intermediate status updates
	•	show final bundle and validation summary

5.2 Agent orchestration layer

This is the Microsoft Agent Framework layer.

It contains:
	•	Coordinator Agent
	•	Requirements Agent
	•	Assembly Manager Agent
	•	Resource Builder Agent
	•	Validator Agent

These are invoked by a function-based workflow.

5.3 Workflow control layer

This is the deterministic control plane.

Responsibilities:
	•	stage progression
	•	artifact routing
	•	dependency resolution
	•	retry counting
	•	escalation
	•	final packaging

This layer should own the real process logic.

5.4 Tooling layer

Deterministic tools exposed to agents or workflow:
	•	FHIR validator wrapper
	•	terminology lookup tool
	•	artifact read/write tool
	•	bundle assembly tool
	•	manifest/profile lookup tool
	•	ID/reference generation tool
	•	trace/log persistence tool

5.5 Artifact and memory layer

Stores:
	•	structured agent handoff artifacts
	•	per-agent memory files
	•	accepted resources
	•	validation outputs
	•	final delivery package
	•	execution logs

5.6 Configuration layer

Configurable runtime definitions:
	•	agent role configs
	•	model configs
	•	tool permissions
	•	bundle manifest
	•	retry limits
	•	output paths
	•	validation settings

6. Agent roles and responsibilities

6.1 Coordinator Agent

Purpose

Acts as the single visible user-facing coordinator.

Responsibilities
	•	receives the user request
	•	explains the plan
	•	invokes the requirements stage
	•	invokes the assembly stage
	•	invokes final validation/review
	•	compares final output with original request
	•	returns final delivery package
	•	narrates what is happening

Behavior requirements
	•	must be highly transparent
	•	must describe delegation decisions
	•	must explain which role is doing what
	•	must explain major failures clearly

Example model profile

High-capability orchestration model.

6.2 Requirements Agent

Purpose

Transforms a user request into a realistic structured clinical specification.

Responsibilities
	•	infer realistic clinical details from the ask
	•	identify plausible conditions, procedures, meds, allergies, care team details
	•	resolve terminology through lookup tools where possible
	•	create a structured Patient Summary Specification
	•	record assumptions and realism notes

Important boundary

This agent does not build FHIR resources.

It builds the clinical truth specification.

Example model profile

Strong reasoning/synthesis model.

6.3 Assembly Manager Agent

Purpose

Converts the clinical specification into a bundle construction plan and coordinates build execution.

Responsibilities
	•	determine resource build order
	•	create resource task packets
	•	manage dependency references
	•	invoke the Resource Builder repeatedly
	•	invoke validation after each resource
	•	apply retry limits
	•	escalate failures
	•	trigger Composition creation
	•	trigger Bundle assembly

Important boundary

This agent does not freely invent the process. It operates within workflow rules.

6.4 Resource Builder Agent

Purpose

Builds one resource at a time from a bounded task packet.

Responsibilities
	•	receive one resource task packet
	•	generate one target resource
	•	revise based on validation feedback
	•	return structured resource output

Important boundary

It should not receive broad irrelevant context.
It should not try to solve the whole bundle.

Reuse principle

The same builder role is reused for Patient, Practitioner, Condition, MedicationStatement, AllergyIntolerance, Procedure, Composition, and other future resources.

6.5 Validator Agent

Purpose

Interprets deterministic validation output and provides readable fix guidance.

Responsibilities
	•	invoke or receive output from deterministic validation tool
	•	translate validator output into human-readable issues
	•	classify issues
	•	suggest fixes
	•	signal pass/fail to workflow
	•	produce validation summary

Important boundary

This agent is not the source of validation truth.
The deterministic validator is.

7. Core workflow

The reusable workflow should be generic enough for future bundle types.

7.1 Workflow stages

Stage 1: Intake

Input:
	•	user request

Output:
	•	RequestPacket

Stage 2: Requirements derivation

Coordinator sends RequestPacket to Requirements Agent.

Output:
	•	PatientSummarySpecification

Stage 3: Build planning

Assembly Manager converts the specification into a BuildPlan.

Output:
	•	ordered resource build steps
	•	dependencies
	•	validation checkpoints
	•	retry policy

Stage 4: Foundational resource generation

Build and validate foundational resources first.

Examples:
	•	Patient
	•	Practitioner
	•	Organization if needed

Each resource follows:
	1.	create ResourceTaskPacket
	2.	call Resource Builder
	3.	run deterministic validation
	4.	if failed, Validator Agent interprets issues
	5.	retry until pass or max retries hit

Stage 5: Section resource generation

Build and validate clinical resources section by section.

Examples:
	•	Condition
	•	MedicationStatement
	•	AllergyIntolerance
	•	Procedure
	•	Observation if required

Same per-resource loop.

Stage 6: Composition generation

Build Composition using accepted resources and section references.

Validate it.

Stage 7: Bundle assembly

Assemble final Bundle from accepted resources and Composition.

Validate the full bundle.

Stage 8: Final review

Coordinator verifies:
	•	consistency with original request
	•	consistency with requirements specification
	•	no obvious drift or contradictions
	•	final package completeness

Stage 9: Delivery

Return:
	•	final bundle
	•	validation summary
	•	assumptions
	•	execution trace
	•	any unresolved issues

8. Structured artifact contracts

These should be implemented first.

8.1 RequestPacket

Fields should include:
	•	request_id
	•	bundle_type
	•	user_goal
	•	clinical prompt
	•	realism constraints
	•	output expectations
	•	created_at

8.2 PatientSummarySpecification

Fields should include:
	•	demographics
	•	care team context
	•	conditions
	•	medications
	•	allergies
	•	procedures
	•	encounters if relevant
	•	required sections
	•	coded facts
	•	realism assumptions
	•	bundle notes

8.3 BuildPlan

Fields should include:
	•	bundle_type
	•	build_steps
	•	dependency map
	•	required resource types
	•	retry policy
	•	validation checkpoints
	•	final assembly instructions

8.4 ResourceTaskPacket

Fields should include:
	•	step_id
	•	target_resource_type
	•	applicable_profile
	•	required facts
	•	required coded values
	•	reference dependencies
	•	required output schema
	•	retry_count

8.5 ValidationResult

Fields should include:
	•	target_type
	•	target_id
	•	passed
	•	severity summary
	•	raw validator output reference
	•	parsed issues
	•	suggested fixes
	•	retryable

8.6 DeliveryPackage

Fields should include:
	•	request_id
	•	bundle_type
	•	final_bundle_path or object
	•	final_validation_summary
	•	assumptions
	•	deviations
	•	execution_trace
	•	generated_artifacts_index

9. Deterministic tools required

9.1 FHIR Validator Tool

Purpose

Performs actual FHIR/profile conformance validation.

Requirements
	•	callable from workflow or agent tool wrapper
	•	returns machine-readable output
	•	supports PS-CA-relevant validation
	•	usable for resource-level validation
	•	usable for full-bundle validation

Role in system

Source of conformance truth.

9.2 Terminology Lookup Tool

Purpose

Resolves valid codes and displays for clinical facts.

Requirements
	•	query by concept text
	•	return code system, code, display
	•	optionally support validation of code/display pair

Role in system

Prevents hallucinated coding.

9.3 Artifact Storage Tool

Purpose

Reads/writes structured artifacts and generated resources.

Requirements
	•	save JSON resources
	•	save Markdown/JSON memories
	•	save validator output
	•	save final delivery package

9.4 Bundle Assembly Tool

Purpose

Constructs final bundle structure from accepted resources.

Requirements
	•	assign entries
	•	wire references
	•	insert Composition correctly
	•	preserve stable IDs

9.5 Manifest/Profile Lookup Tool

Purpose

Provides build manifest rules for PS-CA.

Requirements
	•	list required sections
	•	list required/optional resource types
	•	list build order rules
	•	expose bundle-specific constraints

10. Memory design

Keep memory simple.

10.1 Per-agent memory

Each agent has its own memory file, likely Markdown or JSON.

Coordinator memory
	•	user-facing presentation notes
	•	prior demo preferences
	•	trace style preferences

Requirements memory
	•	realism heuristics
	•	example patient patterns
	•	common section expectations

Assembly Manager memory
	•	build policy notes
	•	prior failure patterns
	•	retry/escalation guidelines

Resource Builder memory
	•	resource generation notes
	•	common profile pitfalls
	•	resource templates or hints

Validator memory
	•	common validator error interpretations
	•	common fix strategies

10.2 Session memory

Each agent also has its own current session state.

10.3 Memory constraints

Memory should not become a hidden second source of truth.
The structured artifacts remain primary.

11. Context injection rules

These rules are mandatory.

Rule 1

Never pass the entire bundle context to every resource build step.

Rule 2

Each ResourceTaskPacket must include only:
	•	the facts needed for that resource
	•	the references needed for that resource
	•	the applicable constraints for that resource

Rule 3

The builder should not need to infer unrelated bundle sections.

Rule 4

Accepted resources should be stored outside the prompt context and referenced by IDs or selected fields where possible.

12. Retry and escalation rules

These are mandatory circuit breakers.

12.1 Resource build retry cap

Recommended:
	•	max_retries_per_resource = 3

12.2 Validation retry flow
	1.	build resource
	2.	validate
	3.	parse issues
	4.	revise
	5.	repeat until pass or max retries hit

12.3 Escalation behavior

If a resource fails after max retries:
	•	mark step as failed
	•	halt assembly or move to controlled failure state
	•	bubble issue to Coordinator
	•	include failure in trace

12.4 No silent degradation

The system must not silently skip required resources.

13. Configuration requirements

Everything possible should be configurable.

13.1 Agent role configuration

For each role:
	•	name
	•	description
	•	instructions
	•	model provider
	•	model name
	•	tools enabled
	•	memory file
	•	output schema
	•	logging verbosity

13.2 Workflow configuration
	•	bundle type
	•	stage list
	•	build order
	•	retry limits
	•	validation behavior
	•	escalation behavior

13.3 Bundle manifest configuration

PS-CA-specific rules should live in manifest/config, not hardcoded deeply into the workflow.

13.4 Model configuration

All model selection should be externalized.

14. System requirements

14.1 Functional requirements

FR-1

The system shall accept a high-level natural-language request for a synthetic PS-CA patient summary bundle.

FR-2

The system shall derive a structured clinical specification from the request.

FR-3

The system shall resolve clinical terminology through deterministic lookup where required.

FR-4

The system shall produce a bundle build plan based on the structured specification.

FR-5

The system shall build required resources one at a time using a reusable Resource Builder.

FR-6

The system shall validate each generated resource using deterministic FHIR validation tooling.

FR-7

The system shall retry failed resource generation up to a configurable maximum.

FR-8

The system shall assemble a Composition from validated resources.

FR-9

The system shall assemble a final Bundle from validated resources and Composition.

FR-10

The system shall validate the final bundle using deterministic validation tooling.

FR-11

The system shall provide a human-readable explanation of validation issues.

FR-12

The system shall provide a user-visible execution trace showing coordination decisions and build progress.

FR-13

The system shall maintain separate memory/state for each configured agent instance.

FR-14

The system shall allow model/provider selection by configuration per agent role.

FR-15

The system shall persist structured artifacts generated during execution.

FR-16

The system shall support future extension to additional bundle types by adding manifests/configuration rather than rewriting the core architecture.

14.2 Non-functional requirements

NFR-1 Simplicity

Version 1 shall use simple persistent memory such as Markdown or JSON files.

NFR-2 Transparency

The system shall expose coordination behavior clearly enough for a live demo audience to understand what is happening.

NFR-3 Determinism

FHIR conformance results shall come from deterministic validation tooling, not LLM judgment.

NFR-4 Modularity

Bundle-type-specific logic shall be separated from the generic assembly platform logic.

NFR-5 Configurability

Model selection, role instructions, tool availability, and retry behavior shall be configurable without major code changes.

NFR-6 Safety against loops

The system shall enforce hard retry limits to prevent runaway loops and excessive API cost.

NFR-7 Context discipline

The system shall minimize context payloads to reduce cost and improve generation quality.

NFR-8 Reusability

The Resource Builder shall be reusable across resource types and future bundle types.

NFR-9 Inspectability

Structured artifacts and logs shall be stored in a way that supports troubleshooting and demonstration.

NFR-10 Demo readiness

The system shall be runnable locally on the Windows machine via a simple command-line or local web interface.

15. Recommended v1 build order
	1.	Define structured artifact models.
	2.	Define PS-CA build manifest.
	3.	Implement deterministic validator tool wrapper.
	4.	Implement terminology lookup tool.
	5.	Implement base agent configuration model.
	6.	Implement Coordinator and Requirements flow.
	7.	Implement Assembly Manager with retry logic.
	8.	Implement reusable Resource Builder.
	9.	Implement Validator Agent as explainer over deterministic validation output.
	10.	Implement final bundle assembly and delivery package generation.
	11.	Add improved trace/logging.
	12.	Add richer middleware/context-provider-based refinement later.

16. Final recommended system statement

The system you are building is a configurable, workflow-led, multi-agent FHIR bundle assembly platform, with PS-CA patient summary generation as its first implemented use case.

It uses Microsoft Agent Framework for:
	•	configurable role-based agents,
	•	function-based workflow orchestration,
	•	tool invocation,
	•	per-agent state/memory,
	•	and transparent multi-agent coordination.

It uses deterministic external tooling for:
	•	FHIR validation,
	•	terminology resolution,
	•	and stable bundle assembly support.

Its key architectural idea is that the same base agent design can be configured into coordinator, requirements, builder, and validator roles, while the workflow and manifest define how those roles collaborate for a given bundle type.

That gives you a strong demo, a reusable architecture, and a credible path to extend the platform beyond PS-CA later.

If you want, the next best step is for me to turn this into a formal design document with sections like Purpose, Scope, Architecture, Functional Requirements, Non-Functional Requirements, Risks, and Implementation Phases.
