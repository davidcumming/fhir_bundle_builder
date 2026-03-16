# First Visible AI Slice: MedicationRequest Resource Construction Agent

## Summary

Implement the thinnest real-model vertical slice inside the existing PS-CA core workflow by making only `build-medicationrequest-1` agent-backed, while leaving request normalization, schematic generation, build planning, bundle finalization, validation, and repair behavior structurally unchanged.

The slice should be **opt-in at workflow runtime** so the current deterministic repo baseline stays intact for existing tests and offline runs. When the new mode is selected, the workflow must call a real OpenAI-backed agent during `resource_construction`, reject invalid model output at the workflow boundary, store both the raw agent output and the accepted normalized MedicationRequest artifact, and surface that trace in the existing Dev UI artifacts. There is **no deterministic fallback** in agent mode: missing config or invalid model output must fail the run clearly.

## Key Changes

### 1. Activation model and workflow contract

- Add `workflow_options.medication_request_generation_mode: Literal["deterministic", "agent_required"]` with default `"deterministic"`.
- Carry that mode into the normalized request so both the initial run and bounded retry path can see it without reaching back into top-level input state.
- In this first slice, only `build-medicationrequest-1` is agent-backed when mode is `"agent_required"`.
- `medicationrequest-2`, if planned, stays deterministic even in agent mode. This keeps the slice to one real agent step and avoids broadening multiplicity behavior.
- If mode is `"agent_required"` and either `OPENAI_API_KEY` or `FHIR_BUNDLE_BUILDER_MEDICATION_AGENT_MODEL` is missing, fail `resource_construction` with a clear runtime error. Do not silently downgrade to deterministic behavior.

### 2. OpenAI gateway and MedicationRequest agent

- Add one small OpenAI gateway module using existing `httpx` async patterns already present in the repo.
- Use the OpenAI API by default, with:
  - required `OPENAI_API_KEY`
  - required `FHIR_BUNDLE_BUILDER_MEDICATION_AGENT_MODEL`
- Use a single strict-JSON request shape via the OpenAI chat/completions API with structured output enforcement (`json_schema` / strict JSON response contract).
- Add one dedicated `MedicationRequest` agent module that:
  - builds a bounded structured prompt input
  - calls the OpenAI gateway
  - stores the raw response text/object
  - parses and validates the returned JSON
  - returns a typed accepted result or raises a clear rejection error

The agent input should be intentionally small and explicit:

- placeholder metadata:
  - `placeholder_id = "medicationrequest-1"`
  - allowed `resourceType`
  - allowed local `id`
  - allowed patient reference(s)
- medication-specific facts:
  - authoritative normalized medication display text for `medicationrequest-1`
  - medication id / source index for traceability
- compact patient context:
  - patient id/display name
  - optionally gender/birth date presence or values already normalized
- compact provider/request context:
  - provider display name
  - selected organization display name if available
  - selected role label if available
  - scenario label / request intent
- explicit instructions:
  - return JSON only
  - do not invent unsupported references
  - do not add unrelated resources or fields
  - preserve exact provided ids/references/status/intent

### 3. Acceptance boundary and normalized artifact policy

- Keep the current MedicationRequest validation semantics unchanged by accepting only a **minimal supported MedicationRequest shape** in this slice:
  - `resourceType == "MedicationRequest"`
  - `id == "medicationrequest-1"`
  - `status == "draft"`
  - `intent == "proposal"`
  - `subject.reference == "Patient/patient-1"`
  - `medicationCodeableConcept.text` is a non-empty string
- Preserve the current exact-text validation contract by instructing the model to use the authoritative normalized medication text exactly as provided. This avoids broadening validation rules in the first slice.
- Reject at the workflow boundary if:
  - output is not valid JSON
  - `resourceType` is wrong
  - `id` is wrong
  - `subject.reference` is outside the allowed reference set
  - required fields are missing or malformed
  - unsupported reference-bearing content is present
- Normalize the accepted resource by merging the validated agent fields onto the deterministic base scaffold so existing deterministic fields like `meta.profile` remain intact and the accepted scaffold fits the current bundle path cleanly.
- Store both:
  - the raw model output
  - the accepted normalized MedicationRequest JSON used by the workflow

### 4. Core workflow integration

- Keep the existing workflow graph unchanged.
- Keep the deterministic `build_psca_resource_construction_result(...)` builder as the base scaffold producer.
- Add one async post-processing helper that augments a `ResourceConstructionStageResult` with the MedicationRequest agent result when `medication_request_generation_mode == "agent_required"`.
- Call that augmentation helper from:
  - the `resource_construction` executor
  - the retry path in `repair_execution_builder.py` after a rerun of resource construction, so the bounded retry path stays consistent if it ever regenerates `build-medicationrequest-1`
- Add typed inspectability fields to the resource-construction artifacts:
  - `MedicationRequestAgentTrace`
    - provider: `"openai"`
    - model name
    - bounded input payload
    - raw response text
    - parsed response JSON
    - accepted normalized resource JSON
    - status: `accepted` / `rejected`
    - rejection reason if applicable
    - provider response id if available
  - `ResourceConstructionStepResult.medication_agent_trace: MedicationRequestAgentTrace | None`
  - `ResourceConstructionEvidence.agent_step_ids: list[str]`
- Update stage-level summary text when the agent path runs so Dev UI visibly says that one MedicationRequest step was model-backed and the rest of the stage remained deterministic.

### 5. Minimal user-trigger path and docs

- Add one minimal runnable example input file for the core workflow, e.g. `examples/psca_medication_agent_demo_input.json`, using the existing `WorkflowBuildInput` shape and one medication item that maps to `medicationrequest-1`.
- Update the README only enough to cover:
  - required env vars
  - the opt-in workflow option
  - the exact Dev UI command
  - where to inspect the agent invocation in the `resource_construction` artifact
- Update `docs/development-plan.md` narrowly to record that the first visible model-backed core workflow slice is now the current focus / completed next step once implemented.

## Public Type / Interface Changes

- `WorkflowOptionsInput`
  - add `medication_request_generation_mode`
- `WorkflowDefaults` or `NormalizedBuildRequest`
  - add the normalized downstream copy of the selected MedicationRequest generation mode
- `ResourceConstructionStepResult`
  - add optional `medication_agent_trace`
- `ResourceConstructionEvidence`
  - add `agent_step_ids`
- Add new typed models for:
  - `MedicationRequestAgentBoundedInput`
  - `MedicationRequestAgentTrace`
  - `MedicationRequestAgentAcceptedResult` or equivalent narrow validated result type

Core workflow behavior remains otherwise unchanged:
- same workflow stages
- same bundle path
- same validation contract for MedicationRequest content
- same repair routing structure

## Test Plan

Add only the minimum coverage needed to lock the slice:

1. `MedicationRequest` agent boundary test
- mock the OpenAI gateway to return valid strict JSON
- assert accepted normalized resource has:
  - correct `resourceType`
  - correct `id`
  - correct `subject.reference`
  - exact medication text
- assert raw response and accepted normalized resource are both preserved in the trace

2. Rejection-path boundary tests
- non-JSON output -> clear rejection
- wrong `resourceType` -> clear rejection
- disallowed `subject.reference` -> clear rejection
- malformed payload -> clear rejection

3. Resource construction integration test
- run `build_psca_resource_construction_result` through the new async augmentation path in agent mode with a mocked gateway
- assert:
  - `build-medicationrequest-1` contains `medication_agent_trace`
  - registry entry `medicationrequest-1` uses the accepted normalized resource
  - `build-allergyintolerance-1` and `build-condition-1` remain deterministic and untouched
  - `agent_step_ids == ["build-medicationrequest-1"]`

4. Workflow-level smoke test
- run the existing core workflow entrypoint in agent mode with a mocked gateway
- assert:
  - `resource_construction.step_results` contains the agent trace on `build-medicationrequest-1`
  - the candidate bundle includes the accepted MedicationRequest
  - validation still passes under the existing deterministic expectations

5. Missing-config test
- set agent mode without required env vars
- assert the workflow fails clearly during `resource_construction` with a useful configuration error
- assert there is no silent deterministic fallback

Do not add live-network tests. Real model execution is validated manually through the existing Dev UI flow.

## Assumptions and Defaults

- Default provider for this first slice: **OpenAI API**
- Gateway implementation: small direct `httpx` integration, not a broader provider framework
- Activation default: `workflow_options.medication_request_generation_mode = "deterministic"` to preserve the current deterministic baseline
- Real model behavior is only required when `medication_request_generation_mode = "agent_required"`
- No fallback to deterministic MedicationRequest generation when agent mode is selected and configuration is missing or the model output is invalid
- Only `build-medicationrequest-1` is agent-backed in this slice
- The accepted MedicationRequest contract remains intentionally narrow and aligned to the current validation rules
- No changes to Condition, AllergyIntolerance, bundle assembly logic, standards-validation policy, or repair-agent behavior in this slice
