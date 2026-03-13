# docs/microsoft-agent-framework-best-practices.md

# Microsoft Agent Framework Best Practices

## Purpose

This document provides team-level best practices for designing, building, testing, and evolving agentic workflow software using Microsoft Agent Framework and Dev UI.

It is intended to guide development of workflow-oriented, multi-agent systems in a way that remains maintainable, observable, extensible, and suitable for future production hardening.

This document is deliberately technology- and architecture-focused. It is not a coding standard, a UI standard, or a feature specification for any one workflow.

## Core Position

For non-trivial business workflows, the primary architectural unit should be the **workflow**, not a single free-form chat agent.

Agents should be used where language reasoning, synthesis, interpretation, or ambiguity handling is required. Deterministic logic should be used where correctness, repeatability, and inspectability matter more than generative flexibility.

The system should be designed so that it can evolve from development-time testing in Dev UI to a larger application architecture without major redesign.

---

## 1. Design the System Around Explicit Workflows

### 1.1 Use workflows for business processes
Use Agent Framework workflows as the top-level execution model for any process that has:
- multiple stages
- branching or routing
- retries or repair loops
- human-in-the-loop steps
- integrations with tools or external systems
- checkpointing or resumability requirements

Do not model these systems as one agent with one very large prompt.

### 1.2 Prefer explicit control flow over emergent behavior
A workflow should make the control path visible and intentional. Routing, branching, parallelism, retries, and handoffs should exist in the workflow graph, not be left to the model to improvise.

### 1.3 Keep the workflow graph understandable
A workflow should be explainable to another developer by looking at its executors, edges, input types, and outputs. If the team cannot quickly understand the workflow from its graph, the design is probably too implicit.

---

## 2. Keep Responsibilities Narrow and Clean

### 2.1 Give each executor one primary job
Each executor should have a single, stable responsibility. Examples:
- normalize request
- retrieve specification assets
- create a structural plan
- generate resource content
- validate output
- route repair work

Do not create "god executors" that combine orchestration, business logic, validation, and generation.

### 2.2 Separate orchestration from generation
The orchestrator should coordinate state and progression through the workflow. It should not also be the main generator of final domain artifacts.

### 2.3 Separate deterministic work from LLM work
Do not use an LLM step for work that should be deterministic, such as:
- ID generation
- dependency sorting
- schema validation
- routing decisions based on structured results
- artifact persistence
- reference reconciliation
- state transitions

Use agents for tasks that actually benefit from model reasoning.

---

## 3. Prefer Typed Artifacts Over Prompt Chaining

### 3.1 Pass structured messages between steps
Workflow stages should exchange well-defined typed artifacts rather than loosely structured text blobs.

Examples of good intermediate artifacts:
- request context
- normalized input package
- workflow plan
- validation report
- repair instruction
- generation result
- review result
- state snapshot

### 3.2 Keep contracts explicit
Every important workflow step should have a clear input contract and output contract. The team should be able to say:
- what goes in
- what comes out
- what the step is allowed to decide
- what it must not decide

### 3.3 Avoid prompt soup
Do not let the workflow become a chain of free-form prompts where every step reads arbitrary prose from the previous step. That approach becomes fragile, hard to debug, and hard to extend.

---

## 4. Use Agents Deliberately

### 4.1 Use agents where interpretation matters
Agents are best suited for:
- interpreting user intent
- synthesizing content from multiple inputs
- drafting human-readable output
- analyzing ambiguous situations
- proposing repair options
- translating between domain language and structured requests

### 4.2 Do not use agents as hidden rule engines
If the system has real business rules, domain constraints, routing criteria, or validation logic, those should not live only inside prompts.

### 4.3 Keep prompts role-based and bounded
Prompts should define the executor's role, task boundaries, constraints, and expected output shape. Do not use prompts as the main storage location for the whole application's logic.

---

## 5. Treat Tools as Stable Capability Boundaries

### 5.1 Build tools around important capabilities
Tools should represent bounded capabilities such as:
- retrieve reusable context
- fetch specification assets
- search supporting artifacts
- run deterministic validation
- generate identifiers
- patch domain artifacts
- perform calculations
- call external services

### 5.2 Keep tool contracts stable
A tool should have:
- a clear purpose
- a constrained input model
- a constrained output model
- well-defined error behavior

Tools should not be vague general-purpose escape hatches.

### 5.3 Put high-impact actions behind safeguards
Any action that mutates important state, accepts risky inferences, writes reusable assets, or publishes a result should be guarded by deterministic checks or approval logic.

### 5.4 Prefer tools over giant context injection
If information can be retrieved when needed, prefer a retrieval or lookup tool over stuffing large amounts of reference material into prompts.

---

## 6. Treat Memory Carefully

### 6.1 Separate conversational memory from domain memory
Do not confuse:
- conversation/session memory
with
- business/domain data

Chat history is not a durable system of record.

### 6.2 Use memory for continuity, not for core truth
Memory is useful for:
- maintaining conversational continuity
- preserving recent execution context
- retaining temporary reasoning context
- recalling prior workflow decisions within a session

It should not be the authoritative store for:
- domain entities
- reusable profiles
- specification assets
- persistent workflow artifacts
- validation baselines

### 6.3 Make domain data explicitly retrievable
Important data should live in explicit stores or assets that can be retrieved through deterministic mechanisms or bounded tools.

---

## 7. Make State a First-Class Concept

### 7.1 Keep state outside the agent instance
Do not rely on the internal state of agent objects as the durable representation of workflow progress.

### 7.2 Track workflow state explicitly
For each meaningful run, the system should be able to identify:
- current stage
- current input artifact
- current output artifact
- pending work
- previous decisions
- prior validation findings
- retry or repair history

### 7.3 Persist state in a way that supports resumption
Even if the first implementation uses in-memory execution, shape the workflow so it can later support durable checkpointing and session recovery.

---

## 8. Start Simple, Then Add Sophistication

### 8.1 Start with the smallest useful workflow
The first workflow should be:
- narrow in scope
- sequential where possible
- easy to inspect
- easy to run in Dev UI
- easy to trace from input to output

### 8.2 Add branching only when justified
Branching, fan-out, fan-in, handoffs, and concurrent execution are powerful, but they increase operational complexity. Add them because the workflow needs them, not because the framework supports them.

### 8.3 Delay parallelism until correctness is stable
Parallelism should come after the team has already proven:
- step boundaries are correct
- contracts are clean
- outputs are stable
- observability is good
- failures are understandable

---

## 9. Design for Validation and Repair

### 9.1 Validation should not be an afterthought
If the workflow produces important structured output, validation should be built into the workflow from the beginning.

### 9.2 Keep validation as deterministic as possible
Use deterministic mechanisms for structural and business-rule validation wherever practical. Let agents interpret results or propose fixes, but do not bury hard validation inside prompts if it can be expressed explicitly.

### 9.3 Route repair work explicitly
If something fails validation, the workflow should determine:
- what failed
- where it failed
- what stage should be revisited
- whether the failure is auto-repairable
- whether human input is required

### 9.4 Preserve successful work where practical
The repair model should avoid rebuilding everything unless necessary.

---

## 10. Use Human-in-the-Loop Intentionally

### 10.1 Design for user intervention paths
Human input should be a normal workflow path for cases such as:
- missing critical data
- conflicting source information
- risky assumptions
- approval of important actions
- acceptance of generated outputs

### 10.2 Do not bolt human review on at the end
Human review should be modeled explicitly in workflow design where it matters.

### 10.3 Use approvals for sensitive operations
Mutating critical state or accepting uncertain outputs should not happen invisibly if the consequences are meaningful.

---

## 11. Use Dev UI as a Development and Debugging Surface

### 11.1 Treat Dev UI as a test bench
Dev UI should be used to:
- run workflows interactively
- inspect executor outputs
- review workflow events
- inspect traces
- verify routing behavior
- test intermediate artifacts
- support team review

### 11.2 Do not treat Dev UI as the product
Dev UI is for development and debugging. Product architecture should not depend on Dev UI behaviors, assumptions, or limitations.

### 11.3 Design workflows to be understandable in Dev UI
A healthy workflow should be understandable from:
- the workflow graph
- the executor list
- the event stream
- the visible inputs and outputs
- the trace timeline

If the workflow cannot be inspected meaningfully there, the workflow likely needs better boundaries.

### 11.4 Prefer structured workflow inputs
Where possible, workflows should start from structured input types rather than only free-form text. This makes testing more repeatable and forces clearer contracts.

---

## 12. Make Observability Part of Development Discipline

### 12.1 Design every stage to be inspectable
Each workflow stage should produce outputs that help answer:
- what happened
- why it happened
- what was decided
- what artifact changed
- what the next step is

### 12.2 Use traces to understand performance and failures
The team should use workflow traces and events to identify:
- bottlenecks
- unstable steps
- routing problems
- retry loops
- noisy failure patterns
- over-complicated stages

### 12.3 Do not hide critical decisions in opaque prose
Important branching or repair decisions should be visible in structured outputs or event data, not only embedded in natural-language narration.

---

## 13. Build for Extensibility from the Beginning

### 13.1 Keep domain assets externalized
Specifications, reusable profiles, reference assets, templates, and validation support materials should be externalized rather than hard-coded into prompts.

### 13.2 Keep provider-specific assumptions isolated
Model-provider-specific choices should be isolated behind clear boundaries so the core workflow is not tightly coupled to one provider's behavior.

### 13.3 Make workflows composable
As workflows mature, they should be able to become reusable capabilities that can later be wrapped, reused, or called by other workflows or agents.

---

## 14. Practical Team Guardrails

The team should follow these guardrails during development:

### 14.1 Do not create a single "super agent"
If one agent is doing orchestration, retrieval, generation, validation, and repair, the architecture is drifting.

### 14.2 Do not use chat history as the data layer
Conversation state is not a substitute for explicit data and artifact management.

### 14.3 Do not route from prose when a structured result would work
Routing, branching, and repair decisions should be based on structured outputs whenever possible.

### 14.4 Do not bury business rules in prompts
If a rule matters, make it explicit in code, data, assets, or deterministic validation.

### 14.5 Do not skip observability
A workflow that cannot be traced clearly will become expensive to evolve.

### 14.6 Do not introduce advanced framework features too early
Use concurrency, fan-out, fan-in, and complex handoffs only when the simpler version is already solid.

### 14.7 Do not delay checkpointing and state design
Even early prototypes should be shaped so that resumability and state persistence can be added cleanly.

---

## 15. Recommended Development Pattern for New Workflow Projects

### 15.1 Phase 1: workflow foundation
Start by defining:
- workflow purpose
- stage boundaries
- typed artifacts
- state model
- tool boundaries
- validation strategy
- repair strategy

### 15.2 Phase 2: minimal executable workflow
Implement the smallest sequential version that:
- runs end to end
- is visible in Dev UI
- produces inspectable outputs
- has deterministic boundaries where needed

### 15.3 Phase 3: improve executor quality
Strengthen:
- prompts
- tool integrations
- deterministic checks
- error handling
- output structure
- trace clarity

### 15.4 Phase 4: add repair loops and human review
Only after the basic workflow is stable should the team add:
- retries
- repair routing
- approval flows
- resumption logic
- more advanced orchestration patterns

### 15.5 Phase 5: harden for extensibility
Once the workflow is useful, improve:
- persistence
- provider abstraction
- asset ingestion
- modular packaging
- workflow reuse
- workflow-as-capability patterns

---

## 16. Recommended Checklist for Reviewing a Workflow Slice

Before considering a workflow slice complete, confirm:

- Is the workflow step boundary clear?
- Is the executor narrowly responsible?
- Is deterministic logic separated from model-driven logic?
- Are the inputs and outputs explicit?
- Can the step be understood in Dev UI?
- Are events and traces useful?
- Is the tool boundary clean?
- Is state handled explicitly?
- Is validation considered?
- Is there a path for human intervention where appropriate?
- Will this design still make sense when the system grows?

If the answer to several of these is "no", the slice is not ready.

---

## 17. Summary

Microsoft Agent Framework is strongest when used as a structured orchestration platform, not as a thin wrapper around a chatbot.

The most important team habits are:
- use workflows as the backbone
- keep executors narrowly focused
- use deterministic logic where correctness matters
- use agents where interpretation matters
- use tools as bounded capabilities
- keep state and artifacts explicit
- treat memory carefully
- design for validation, repair, and human intervention
- use Dev UI for shared inspection and debugging
- build for extensibility early, not after the system becomes tangled

If the team follows those practices, it will be much easier to evolve a prototype workflow into a durable, extensible system.