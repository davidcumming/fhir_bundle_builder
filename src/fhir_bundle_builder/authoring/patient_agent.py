"""Bounded real-model patient authoring for the patient authoring page."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import ValidationError

from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.openai_gateway import (
    OpenAIChatCompletionsGateway,
    OpenAIGatewayConfigurationError,
    OpenAIGatewayError,
    OpenAIJSONCompletionResponse,
    load_patient_authoring_gateway_config_from_env,
)

from .patient_builder import (
    build_deterministic_patient_id,
    build_deterministic_patient_record_id,
    build_patient_authoring_gaps,
    get_patient_complexity_policy,
)
from .patient_models import (
    PatientAuthoredAllergy,
    PatientAuthoredBackgroundFacts,
    PatientAuthoredCondition,
    PatientAuthoredIdentity,
    PatientAuthoredMedication,
    PatientAuthoredRecord,
    PatientAuthoringAgentBoundedInput,
    PatientAuthoringAgentItemPayload,
    PatientAuthoringAgentPayload,
    PatientAuthoringAgentTrace,
    PatientAuthoringEvidence,
    PatientAuthoringInput,
    PatientAuthoringValidationOutcome,
)

_SYSTEM_PROMPT = (
    "You convert one patient narrative into one strict JSON patient authoring payload. "
    "Return exactly one JSON object that matches the requested schema. "
    "Do not include markdown, prose, comments, code fences, or extra keys. "
    "Use only information supported by the narrative. "
    "Do not invent record ids, patient ids, item ids, mapped context, complexity policy, "
    "validation state, raw trace fields, or unresolved gap fields."
)


class PatientAuthoringAgentError(RuntimeError):
    """Raised when the patient authoring agent call cannot be completed."""


class PatientAuthoringAgentGateway(Protocol):
    """Minimal protocol implemented by the OpenAI gateway and test doubles."""

    @property
    def model_name(self) -> str: ...

    async def create_json_completion(
        self,
        *,
        system_prompt: str,
        user_payload: dict[str, Any],
        schema_name: str,
        schema: dict[str, Any],
    ) -> OpenAIJSONCompletionResponse: ...


@dataclass(frozen=True)
class PatientAuthoringAgentRunResult:
    """Accepted or rejected result for one patient authoring agent invocation."""

    trace: PatientAuthoringAgentTrace
    validation_outcome: PatientAuthoringValidationOutcome
    accepted_record: PatientAuthoredRecord | None


def build_patient_authoring_gateway_from_env() -> OpenAIChatCompletionsGateway:
    """Build the shared OpenAI gateway for the patient authoring path."""

    return OpenAIChatCompletionsGateway(load_patient_authoring_gateway_config_from_env())


async def author_patient_record(
    authoring_input: PatientAuthoringInput,
    gateway: PatientAuthoringAgentGateway | None = None,
) -> PatientAuthoringAgentRunResult:
    """Run the patient authoring agent and validate the returned payload."""

    if gateway is None:
        try:
            gateway = build_patient_authoring_gateway_from_env()
        except OpenAIGatewayConfigurationError:
            raise

    bounded_input = build_patient_authoring_bounded_input(authoring_input)
    return await invoke_patient_authoring_agent(
        bounded_input=bounded_input,
        gateway=gateway,
    )


def build_patient_authoring_bounded_input(
    authoring_input: PatientAuthoringInput,
) -> PatientAuthoringAgentBoundedInput:
    """Build the bounded structured input sent to the patient authoring agent."""

    policy = get_patient_complexity_policy(authoring_input.complexity_level)
    return PatientAuthoringAgentBoundedInput(
        authoring_text=authoring_input.authoring_text,
        complexity_level=authoring_input.complexity_level,
        scenario_label=authoring_input.scenario_label,
        history_detail=policy.history_detail,
        target_condition_count=policy.target_condition_count,
        target_medication_count=policy.target_medication_count,
        target_allergy_count=policy.target_allergy_count,
    )


async def invoke_patient_authoring_agent(
    *,
    bounded_input: PatientAuthoringAgentBoundedInput,
    gateway: PatientAuthoringAgentGateway,
) -> PatientAuthoringAgentRunResult:
    """Invoke the patient authoring agent and validate the returned JSON payload."""

    try:
        provider_response = await gateway.create_json_completion(
            system_prompt=_SYSTEM_PROMPT,
            user_payload={"patient_authoring_task": bounded_input.model_dump()},
            schema_name="patient_authoring_payload",
            schema=_patient_authoring_json_schema(bounded_input),
        )
    except OpenAIGatewayError as exc:
        raise PatientAuthoringAgentError(str(exc)) from exc

    base_trace = PatientAuthoringAgentTrace(
        provider="openai",
        model_name=gateway.model_name,
        bounded_input=bounded_input,
        raw_response_text=provider_response.raw_text,
        parsed_response_json=None,
        accepted_payload_json=None,
        status="rejected",
        rejection_reason=None,
        provider_response_id=provider_response.response_id,
    )

    try:
        parsed_json = json.loads(provider_response.raw_text)
    except json.JSONDecodeError:
        return _rejected_run_result(
            base_trace,
            "Patient authoring agent returned non-JSON output.",
        )

    if not isinstance(parsed_json, dict):
        return _rejected_run_result(
            base_trace,
            "Patient authoring agent returned a JSON value that was not an object.",
            parsed_response_json={"non_object_response": parsed_json},
        )

    try:
        payload = PatientAuthoringAgentPayload.model_validate(parsed_json)
    except ValidationError as exc:
        errors = _validation_error_messages(exc)
        return _rejected_run_result(
            base_trace,
            "Patient authoring agent returned schema-invalid content.",
            parsed_response_json=parsed_json,
            errors=errors,
        )

    accepted_record = _normalize_payload_to_authored_record(
        payload=payload,
        bounded_input=bounded_input,
    )
    accepted_payload_json = payload.model_dump(mode="json")
    accepted_trace = PatientAuthoringAgentTrace.model_validate(
        {
            **base_trace.model_dump(),
            "parsed_response_json": parsed_json,
            "accepted_payload_json": accepted_payload_json,
            "status": "accepted",
            "rejection_reason": None,
        }
    )
    return PatientAuthoringAgentRunResult(
        trace=accepted_trace,
        validation_outcome=PatientAuthoringValidationOutcome(status="accepted", errors=[]),
        accepted_record=accepted_record,
    )


def _rejected_run_result(
    base_trace: PatientAuthoringAgentTrace,
    rejection_reason: str,
    *,
    parsed_response_json: dict[str, Any] | None = None,
    errors: list[str] | None = None,
) -> PatientAuthoringAgentRunResult:
    trace = PatientAuthoringAgentTrace.model_validate(
        {
            **base_trace.model_dump(),
            "parsed_response_json": parsed_response_json,
            "status": "rejected",
            "rejection_reason": rejection_reason,
        }
    )
    validation_errors = [rejection_reason]
    if errors:
        validation_errors.extend(errors)
    return PatientAuthoringAgentRunResult(
        trace=trace,
        validation_outcome=PatientAuthoringValidationOutcome(
            status="rejected",
            errors=validation_errors,
        ),
        accepted_record=None,
    )


def _normalize_payload_to_authored_record(
    *,
    payload: PatientAuthoringAgentPayload,
    bounded_input: PatientAuthoringAgentBoundedInput,
) -> PatientAuthoredRecord:
    policy = get_patient_complexity_policy(bounded_input.complexity_level)
    display_name = payload.patient.display_name.strip()

    conditions = _build_condition_items(payload.conditions)
    medications = _build_medication_items(payload.medications)
    allergies = _build_allergy_items(payload.allergies)

    return PatientAuthoredRecord(
        record_id=build_deterministic_patient_record_id(
            bounded_input.authoring_text,
            bounded_input.scenario_label,
        ),
        scenario_label=bounded_input.scenario_label,
        patient=PatientAuthoredIdentity(
            patient_id=build_deterministic_patient_id(
                display_name,
                bounded_input.authoring_text,
            ),
            display_name=display_name,
            administrative_gender=payload.patient.administrative_gender,
            age_years=payload.patient.age_years,
            birth_date=payload.patient.birth_date,
        ),
        background_facts=PatientAuthoredBackgroundFacts(
            residence_text=_normalize_optional_text(payload.background_facts.residence_text),
            smoking_status_text=_normalize_optional_text(payload.background_facts.smoking_status_text),
        ),
        conditions=conditions,
        medications=medications,
        allergies=allergies,
        complexity_policy_applied=policy,
        unresolved_authoring_gaps=build_patient_authoring_gaps(
            policy,
            conditions,
            medications,
            allergies,
        ),
        authoring_evidence=PatientAuthoringEvidence(
            source_authoring_text=bounded_input.authoring_text,
            builder_mode="openai_patient_authoring_agent",
            extracted_name=display_name,
            extracted_gender=payload.patient.administrative_gender,
            extracted_age_years=payload.patient.age_years,
            extracted_birth_date=payload.patient.birth_date,
            extracted_residence_text=_normalize_optional_text(payload.background_facts.residence_text),
            extracted_smoking_status_text=_normalize_optional_text(payload.background_facts.smoking_status_text),
            applied_scenario_tags=[],
        ),
    )


def _build_condition_items(
    items: list[PatientAuthoringAgentItemPayload],
) -> list[PatientAuthoredCondition]:
    return [
        PatientAuthoredCondition(
            condition_id=f"condition-authored-{index}",
            display_text=item.display_text.strip(),
            source_mode="agent_structured_output",
            source_note=item.source_note.strip(),
        )
        for index, item in enumerate(items, start=1)
    ]


def _build_medication_items(
    items: list[PatientAuthoringAgentItemPayload],
) -> list[PatientAuthoredMedication]:
    return [
        PatientAuthoredMedication(
            medication_id=f"medication-authored-{index}",
            display_text=item.display_text.strip(),
            source_mode="agent_structured_output",
            source_note=item.source_note.strip(),
        )
        for index, item in enumerate(items, start=1)
    ]


def _build_allergy_items(
    items: list[PatientAuthoringAgentItemPayload],
) -> list[PatientAuthoredAllergy]:
    return [
        PatientAuthoredAllergy(
            allergy_id=f"allergy-authored-{index}",
            display_text=item.display_text.strip(),
            source_mode="agent_structured_output",
            source_note=item.source_note.strip(),
        )
        for index, item in enumerate(items, start=1)
    ]


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _patient_authoring_json_schema(
    bounded_input: PatientAuthoringAgentBoundedInput,
) -> dict[str, Any]:
    item_schema: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "required": ["display_text", "source_note"],
        "properties": {
            "display_text": {"type": "string", "minLength": 1},
            "source_note": {"type": "string", "minLength": 1},
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "patient",
            "background_facts",
            "conditions",
            "medications",
            "allergies",
        ],
        "properties": {
            "patient": {
                "type": "object",
                "additionalProperties": False,
                "required": ["display_name", "administrative_gender", "age_years", "birth_date"],
                "properties": {
                    "display_name": {"type": "string", "minLength": 1},
                    "administrative_gender": {
                        "type": ["string", "null"],
                        "enum": ["female", "male", "other", "unknown", None],
                    },
                    "age_years": {"type": ["integer", "null"], "minimum": 0, "maximum": 130},
                    "birth_date": {
                        "type": ["string", "null"],
                        "pattern": r"^\d{4}-\d{2}-\d{2}$",
                    },
                },
            },
            "background_facts": {
                "type": "object",
                "additionalProperties": False,
                "required": ["residence_text", "smoking_status_text"],
                "properties": {
                    "residence_text": {"type": ["string", "null"]},
                    "smoking_status_text": {"type": ["string", "null"]},
                },
            },
            "conditions": {
                "type": "array",
                "items": item_schema,
                "maxItems": bounded_input.target_condition_count,
            },
            "medications": {
                "type": "array",
                "items": item_schema,
                "maxItems": bounded_input.target_medication_count,
            },
            "allergies": {
                "type": "array",
                "items": item_schema,
                "maxItems": bounded_input.target_allergy_count,
            },
        },
    }


def _validation_error_messages(exc: ValidationError) -> list[str]:
    messages: list[str] = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error.get("loc", ()))
        message = error.get("msg", "Invalid value.")
        if location:
            messages.append(f"{location}: {message}")
        else:
            messages.append(message)
    return messages
