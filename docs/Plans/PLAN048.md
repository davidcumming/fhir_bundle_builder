# UI Slice 1 Revision: AI-Assisted Patient Authoring

## Summary
Revise Slice 1 so the FastAPI page remains the browser surface, but the backend authoring path becomes a real OpenAI-backed patient authoring call with an explicit acceptance boundary. The page will submit one narrative, invoke one bounded patient authoring agent, validate and normalize the result into the repo’s existing `PatientAuthoredRecord` shape, map it into `PatientContextInput`, and render raw and accepted artifacts separately.

Chosen pattern: **Option C, hybrid bounded extraction + deterministic post-processing**.

Justification:
- It matches the repo’s existing medication-agent pattern: model call first, then strict parse/validate/normalize at the application boundary.
- It preserves the existing `PatientAuthoredRecord` and `map_authored_patient_to_patient_context(...)` contracts.
- It keeps deterministic code explicit and secondary: IDs, complexity policy application, unresolved-gap computation, and mapping remain deterministic, but the primary authoring engine is the OpenAI-backed agent.
- It avoids asking the model to invent repo-owned derived fields such as `record_id`, `patient_id`, item IDs, and gap summaries.

## Public Interfaces And Contracts
Reuse the existing gateway class in [openai_gateway.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/openai_gateway.py) and add a patient-agent flow in the authoring package, centered on these types:
- `PatientAuthoringAgentBoundedInput`
- `PatientAuthoringAgentPayload`
- `PatientAuthoringValidationOutcome`
- `PatientAuthoringAgentTrace`
- extend `PatientAuthoringItemSourceMode` with `agent_structured_output`
- extend `PatientAuthoringEvidence.builder_mode` with `openai_patient_authoring_agent`

Exact model-return contract for the accepted agent payload:

```json
{
  "patient": {
    "display_name": "string",
    "administrative_gender": "female|male|other|unknown|null",
    "age_years": "integer|null",
    "birth_date": "YYYY-MM-DD|null"
  },
  "background_facts": {
    "residence_text": "string|null",
    "smoking_status_text": "string|null"
  },
  "conditions": [
    {
      "display_text": "string",
      "source_note": "string"
    }
  ],
  "medications": [
    {
      "display_text": "string",
      "source_note": "string"
    }
  ],
  "allergies": [
    {
      "display_text": "string",
      "source_note": "string"
    }
  ]
}
```

Contract rules:
- top-level artifact must be strict JSON object only, no prose, markdown, or wrapper text
- `additionalProperties: false` at every object layer
- `patient.display_name` is required and must be non-empty after trim
- `conditions`, `medications`, and `allergies` are arrays of bounded items with non-empty `display_text` and `source_note`
- array `maxItems` are generated from the existing complexity policy for the submitted level
- the model does **not** return `record_id`, `patient_id`, item IDs, complexity policy, unresolved gaps, mapped context, or raw trace fields

Validation/rejection behavior:
- invalid JSON: reject, keep raw text, no accepted record, no mapped context
- schema-invalid JSON: reject, keep raw text and parsed JSON if available, no accepted record, no mapped context
- missing required fields or blank required values: reject as unusable content
- missing agent configuration: reject visibly with no deterministic fallback
- accepted output is converted into the canonical `PatientAuthoredRecord` only after boundary validation succeeds

## Implementation Changes
- Replace the `POST /patient-authoring` success path in [patient_authoring_app.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/web/patient_authoring_app.py) so it no longer calls `build_patient_authored_record(...)` as the page’s primary engine.
- Make `run_patient_authoring_flow(...)` async and have it call a new bounded patient-authoring agent module, then map only the accepted normalized record.
- Add a patient-agent module under the authoring package, for example [patient_agent.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/authoring/patient_agent.py), that mirrors the medication-agent structure:
  - build bounded input from submitted narrative and existing complexity policy
  - call `OpenAIChatCompletionsGateway.create_json_completion(...)`
  - use strict JSON-schema response formatting
  - parse raw text
  - validate against `PatientAuthoringAgentPayload`
  - normalize into `PatientAuthoredRecord`
  - return typed trace + validation outcome + accepted record
- Keep deterministic logic only for:
  - `get_patient_complexity_policy(...)`
  - deterministic `record_id` and `patient_id`
  - authored item IDs
  - unresolved gap calculation
  - `map_authored_patient_to_patient_context(...)`
- Do **not** reuse `build_patient_authored_record(...)` on the new page path. If helper reuse is needed, extract only the ID/gap/policy helpers from [patient_builder.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/authoring/patient_builder.py) instead of calling the full deterministic authoring builder.
- Reuse the existing gateway architecture, not a second client stack. Narrow change in [openai_gateway.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/openai_gateway.py):
  - keep `OpenAIChatCompletionsGateway` as-is
  - generalize or add a patient-specific env-loader wrapper so patient and medication flows share the same gateway path
- UI sections must be rendered, labeled, and kept separate exactly as:
  - `Submitted Input`
  - `Validation Errors / Agent Errors`
  - `Raw Agent Output`
  - `Accepted Structured Patient Profile`
  - `Mapped Patient Context`
  - `Raw JSON Inspection`
- `Raw Agent Output` shows the raw model text and basic trace metadata when available.
- `Raw JSON Inspection` shows separate JSON blocks for:
  - full agent trace
  - validation outcome
  - accepted structured patient profile
  - mapped patient context
- Response behavior:
  - input validation error: `400`
  - missing agent configuration: `503`
  - provider failure or invalid model output: `502`
  - success: `200`

## Configuration
Required environment variables for the patient-agent path:
- `OPENAI_API_KEY`
- `FHIR_BUNDLE_BUILDER_PATIENT_AUTHORING_MODEL`

Optional:
- `OPENAI_BASE_URL`
- `FHIR_BUNDLE_BUILDER_PATIENT_AUTHORING_TIMEOUT_SECONDS`

Missing-config behavior:
- the page renders a visible agent error naming the missing variable(s)
- it does not silently call `build_patient_authored_record(...)`
- accepted structured output and mapped context remain empty-state
- raw output remains empty-state because no provider call was attempted

## Test Plan
Add a focused patient-agent boundary test file, for example [test_patient_authoring_agent.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_patient_authoring_agent.py), and update [test_patient_authoring_web_app.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_patient_authoring_web_app.py).

Required mocked cases:
- valid agent output is accepted, normalized into `PatientAuthoredRecord`, mapped, and rendered
- invalid JSON is rejected visibly and raw agent output is still shown
- schema-invalid output is rejected visibly
- missing configuration is surfaced visibly with no deterministic fallback
- raw model output is rendered separately from accepted structured output
- accepted success renders the six required UI sections and separate JSON inspection blocks

Test constraints:
- mock the OpenAI gateway; no live OpenAI calls
- assert the page path no longer depends on `build_patient_authored_record(...)` for primary authoring
- keep one integration-style FastAPI route test and one direct agent-boundary unit test layer

## Reporting And Run Commands
After implementation, delivery must report:
- files added
- files modified
- exact run command
- exact test commands
- required environment variables
- whether the page now performs a real OpenAI-backed call

Planned run command:
- `source .venv/bin/activate && PYTHONPATH=src uvicorn fhir_bundle_builder.web.patient_authoring_app:app --reload`

Planned test commands:
- `source .venv/bin/activate && PYTHONPATH=src pytest tests/test_patient_authoring_agent.py tests/test_patient_authoring_web_app.py`
- `source .venv/bin/activate && PYTHONPATH=src pytest`

## Assumptions And Defaults
- Keep FastAPI and the current one-page server-rendered UI shell.
- Keep complexity semantics unchanged for this slice; they remain bounded max-item targets.
- Do not add provider authoring, bundle generation, persistence, multi-turn chat, or a broader agent framework.
- The accepted structured patient artifact remains `PatientAuthoredRecord`.
- The page is considered complete only if it now makes a real OpenAI-backed call on the primary authoring path when required configuration is present.
