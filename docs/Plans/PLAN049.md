# Patient Authoring Revision: Preserve Vague Medication Evidence

## Summary
Revise the patient authoring agent so explicit medication-use evidence is not dropped when the narrative lacks an exact drug name. Keep the current payload shape and UI structure, but tighten the agent instructions and add a narrow acceptance guard so the system distinguishes:
- explicit medication use with specific identity
- explicit medication use with vague or unspecified identity
- no medication evidence

Recommended implementation choice:
- keep the current `medications: [{display_text, source_note}]` shape unchanged
- strengthen the prompt so the model must emit vague medication items when medication use is stated but identity is unknown
- add a narrow deterministic **medication-evidence-presence validator**, not a fallback authoring path
- if the narrative clearly indicates medication use and the model returns `medications=[]`, reject that output as lossy rather than silently accepting it

This preserves the agent-backed path while preventing omission of explicit medication evidence.

## Key Changes
- Update the system prompt in [patient_agent.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/authoring/patient_agent.py) with explicit medication-preservation rules:
  - if the narrative says the patient uses, takes, or relies on a medication but the exact name is unknown, still emit a medication item
  - preserve the best patient-reported wording in `display_text`
  - append or keep an unspecified qualifier when identity is vague, e.g. `Inhaler (unspecified)`, `Pills for blood pressure (unspecified)`
  - `source_note` must cite the narrative evidence
  - omit medications only when there is no medication evidence at all
- Extend the bounded input or local agent helper with one narrow derived flag or summary such as `medication_evidence_present` and optionally a compact evidence hint list. This is only for validation guidance and prompt grounding, not for deterministic authoring.
- Add one acceptance rule after payload parsing:
  - when the narrative contains clear medication-use evidence and parsed `medications` is empty, reject the agent output as unusable/lossy
  - do not synthesize a medication item deterministically
  - do not introduce a deterministic fallback builder path
- Keep normalization permissive for vague medications:
  - preserve `display_text` exactly as the accepted payload provides it after trim
  - do not require normalization to a formal drug/product name
  - do not reject medication items merely because they are vague or marked unspecified
- Keep the current `PatientAuthoringAgentPayload` shape unchanged unless implementation proves a minimal bounded-input hint field is needed internally; the accepted artifact remains `PatientAuthoredRecord`.

## Important Interface / Behavior Notes
- No public UI contract change is required.
- `PatientAuthoredMedication.display_text` continues to hold patient-reported text and may now legitimately contain vague explicit phrases.
- `PatientAuthoringValidationOutcome.errors` should include a clear rejection message when medication evidence exists in the narrative but the agent omitted medications.
- `PatientAuthoringAgentTrace` should continue to preserve raw model output separately so lossy omissions remain inspectable.

## Test Plan
Update agent and route tests to lock the new behavior:
- Direct agent test with a valid vague-medication payload for a narrative like:
  - `I use an inhaler when my breathing gets bad and I take a few pills every morning for my blood pressure.`
  - assert accepted result
  - assert `accepted_record.medications` is non-empty
  - assert at least one medication `display_text` preserves vague evidence, such as `Inhaler (unspecified)` or `Pills for blood pressure (unspecified)`
  - assert `source_note` explains the narrative evidence
- Add a rejection-path test where:
  - the narrative contains clear medication evidence
  - the mocked model returns valid JSON with `medications: []`
  - assert the output is rejected as lossy
  - assert raw agent output remains preserved in the trace
  - assert no deterministic fallback medication is created
- Update one web-app route test so accepted structured output visibly includes a vague medication item for the inhaler / blood-pressure-pills narrative.
- Keep existing invalid-JSON, schema-invalid, and missing-config tests unchanged.

## Assumptions And Defaults
- Use a narrow deterministic medication-evidence detector only as a validation/prompting guard, not as a second authoring engine.
- Evidence cues should cover obvious patient-reported medication-use language such as `use an inhaler`, `take pills`, `take medication`, `blood pressure medicine`, and similar direct statements.
- No retry loop is added in this narrow slice; the first invalid lossy response is rejected visibly.
- No mapper or UI redesign is needed; once the accepted record contains vague medications, the current accepted-profile and mapped-context sections will already display them correctly.
