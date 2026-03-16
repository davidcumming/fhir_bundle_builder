"""Bounded real-model MedicationRequest generation for the PS-CA workflow."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Protocol

from .models import (
    MedicationRequestAgentAcceptedResult,
    MedicationRequestAgentBoundedInput,
    MedicationRequestAgentTrace,
    NormalizedBuildRequest,
    ResourceConstructionEvidence,
    ResourceConstructionStageResult,
    ResourceConstructionStepResult,
    ResourceRegistryEntry,
    ResourceScaffoldArtifact,
)
from .openai_gateway import (
    OpenAIChatCompletionsGateway,
    OpenAIGatewayConfigurationError,
    OpenAIGatewayError,
    OpenAIJSONCompletionResponse,
    load_openai_gateway_config_from_env,
)

_AGENT_STEP_ID = "build-medicationrequest-1"
_AGENT_PLACEHOLDER_ID = "medicationrequest-1"
_ALLOWED_TOP_LEVEL_FIELDS = {
    "resourceType",
    "id",
    "status",
    "intent",
    "subject",
    "medicationCodeableConcept",
    "authoredOn",
}

_MEDICATION_REQUEST_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "resourceType",
        "id",
        "status",
        "intent",
        "subject",
        "medicationCodeableConcept",
    ],
    "properties": {
        "resourceType": {"type": "string", "enum": ["MedicationRequest"]},
        "id": {"type": "string", "enum": ["medicationrequest-1"]},
        "status": {"type": "string", "enum": ["draft"]},
        "intent": {"type": "string", "enum": ["proposal"]},
        "subject": {
            "type": "object",
            "additionalProperties": False,
            "required": ["reference"],
            "properties": {
                "reference": {"type": "string", "enum": ["Patient/patient-1"]},
            },
        },
        "medicationCodeableConcept": {
            "type": "object",
            "additionalProperties": False,
            "required": ["text"],
            "properties": {
                "text": {"type": "string"},
            },
        },
        "authoredOn": {"type": "string"},
    },
}

_SYSTEM_PROMPT = (
    "You generate a single FHIR R4 MedicationRequest resource as strict JSON only. "
    "Return exactly one JSON object that matches the requested shape. "
    "Do not include markdown, explanations, comments, or surrounding prose. "
    "Do not invent unsupported references, identifiers, resources, codes, or unrelated fields. "
    "Preserve the provided resourceType, id, status, intent, subject.reference, and exact medication text."
)


class MedicationRequestAgentError(RuntimeError):
    """Raised when the bounded MedicationRequest agent cannot produce an acceptable result."""


class MedicationRequestAgentGateway(Protocol):
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


async def apply_medication_request_agent_to_construction_result(
    result: ResourceConstructionStageResult,
    normalized_request: NormalizedBuildRequest,
    gateway: MedicationRequestAgentGateway | None = None,
) -> ResourceConstructionStageResult:
    """Augment the deterministic construction result with a bounded agent-generated MedicationRequest."""

    if normalized_request.workflow_defaults.medication_request_generation_mode != "agent_required":
        return result

    if gateway is None:
        try:
            gateway = OpenAIChatCompletionsGateway(load_openai_gateway_config_from_env())
        except OpenAIGatewayConfigurationError as exc:
            raise MedicationRequestAgentError(str(exc)) from exc

    step_index = _find_step_index(result.step_results, _AGENT_STEP_ID)
    if step_index is None:
        raise MedicationRequestAgentError(
            "MedicationRequest agent mode requires build-medicationrequest-1 to be present in the build plan."
        )

    registry_index = _find_registry_index(result.resource_registry, _AGENT_PLACEHOLDER_ID)
    if registry_index is None:
        raise MedicationRequestAgentError(
            "MedicationRequest agent mode requires medicationrequest-1 to be present in the resource registry."
        )

    original_step = result.step_results[step_index]
    bounded_input = _build_bounded_input(normalized_request)
    accepted = await invoke_medication_request_agent(
        bounded_input=bounded_input,
        base_resource=original_step.resource_scaffold.fhir_scaffold,
        gateway=gateway,
    )

    updated_step = _step_with_agent_result(original_step, accepted)
    updated_registry_entry = _registry_entry_with_agent_result(
        result.resource_registry[registry_index],
        accepted.normalized_resource_json,
    )

    updated = ResourceConstructionStageResult.model_validate(result.model_dump())
    updated.step_results[step_index] = updated_step
    updated.step_result_history = [
        updated_step if step.step_id == _AGENT_STEP_ID else step
        for step in updated.step_result_history
    ]
    updated.resource_registry[registry_index] = updated_registry_entry
    updated.evidence = ResourceConstructionEvidence.model_validate(
        {
            **updated.evidence.model_dump(),
            "agent_step_ids": [_AGENT_STEP_ID],
        }
    )
    updated.summary = (
        "Constructed PS-CA resource scaffolds with one model-backed MedicationRequest step and "
        "deterministic construction for all remaining build steps."
    )
    updated.placeholder_note = (
        "MedicationRequest/medicationrequest-1 was generated through a bounded OpenAI-backed agent call "
        "and accepted only after strict JSON and reference validation; all other resources remain deterministic."
    )
    return updated


async def invoke_medication_request_agent(
    *,
    bounded_input: MedicationRequestAgentBoundedInput,
    base_resource: dict[str, Any],
    gateway: MedicationRequestAgentGateway,
) -> MedicationRequestAgentAcceptedResult:
    """Invoke the bounded MedicationRequest agent and validate the returned JSON."""

    try:
        provider_response = await gateway.create_json_completion(
            system_prompt=_SYSTEM_PROMPT,
            user_payload={"medication_request_task": bounded_input.model_dump()},
            schema_name="psca_medication_request_resource",
            schema=_MEDICATION_REQUEST_JSON_SCHEMA,
        )
    except OpenAIGatewayError as exc:
        raise MedicationRequestAgentError(str(exc)) from exc

    try:
        parsed_json = json.loads(provider_response.raw_text)
    except json.JSONDecodeError as exc:
        raise MedicationRequestAgentError(
            "MedicationRequest agent returned non-JSON output."
        ) from exc

    if not isinstance(parsed_json, dict):
        raise MedicationRequestAgentError(
            "MedicationRequest agent returned a JSON value that was not an object."
        )

    normalized_resource = _validate_and_normalize_medication_request(
        parsed_json=parsed_json,
        bounded_input=bounded_input,
        base_resource=base_resource,
    )

    trace = MedicationRequestAgentTrace(
        provider="openai",
        model_name=gateway.model_name,
        bounded_input=bounded_input,
        raw_response_text=provider_response.raw_text,
        parsed_response_json=parsed_json,
        accepted_normalized_resource_json=normalized_resource,
        status="accepted",
        rejection_reason=None,
        provider_response_id=provider_response.response_id,
    )
    return MedicationRequestAgentAcceptedResult(
        normalized_resource_json=normalized_resource,
        trace=trace,
    )


def _build_bounded_input(
    normalized_request: NormalizedBuildRequest,
) -> MedicationRequestAgentBoundedInput:
    planned_entry = next(
        (
            entry
            for entry in normalized_request.patient_context.planned_medication_entries
            if entry.placeholder_id == _AGENT_PLACEHOLDER_ID
        ),
        None,
    )
    if planned_entry is None:
        selected_medication = normalized_request.patient_context.selected_medication_for_single_entry
        if selected_medication is None:
            raise MedicationRequestAgentError(
                "MedicationRequest agent mode requires an authoritative normalized medication for medicationrequest-1."
            )
        medication_id = selected_medication.medication_id
        source_medication_index = 0
        medication_display_text = selected_medication.display_text
    else:
        medication_id = planned_entry.medication_id
        source_medication_index = planned_entry.source_medication_index
        medication_display_text = planned_entry.display_text

    return MedicationRequestAgentBoundedInput(
        placeholder_id="medicationrequest-1",
        medication_id=medication_id,
        source_medication_index=source_medication_index,
        medication_display_text=medication_display_text,
        required_resource_id="medicationrequest-1",
        allowed_patient_references=["Patient/patient-1"],
        patient_id=normalized_request.patient_context.patient.patient_id,
        patient_display_name=normalized_request.patient_context.patient.display_name,
        patient_administrative_gender=normalized_request.patient_context.patient.administrative_gender,
        patient_birth_date=normalized_request.patient_context.patient.birth_date,
        provider_display_name=normalized_request.provider_context.provider.display_name,
        selected_organization_display_name=(
            normalized_request.provider_context.selected_organization.display_name
            if normalized_request.provider_context.selected_organization is not None
            else None
        ),
        selected_role_label=(
            normalized_request.provider_context.selected_provider_role_relationship.role_label
            if normalized_request.provider_context.selected_provider_role_relationship is not None
            else None
        ),
        request_text=normalized_request.request.request_text,
        bundle_intent=normalized_request.request.bundle_intent,
        scenario_label=normalized_request.request.scenario_label,
    )


def _validate_and_normalize_medication_request(
    *,
    parsed_json: dict[str, Any],
    bounded_input: MedicationRequestAgentBoundedInput,
    base_resource: dict[str, Any],
) -> dict[str, Any]:
    unexpected_fields = sorted(set(parsed_json) - _ALLOWED_TOP_LEVEL_FIELDS)
    if unexpected_fields:
        raise MedicationRequestAgentError(
            "MedicationRequest agent returned unsupported top-level fields: "
            f"{', '.join(unexpected_fields)}."
        )

    if parsed_json.get("resourceType") != "MedicationRequest":
        raise MedicationRequestAgentError(
            "MedicationRequest agent returned the wrong resourceType."
        )

    if parsed_json.get("id") != bounded_input.required_resource_id:
        raise MedicationRequestAgentError(
            "MedicationRequest agent returned an unexpected resource id."
        )

    if parsed_json.get("status") != bounded_input.required_status:
        raise MedicationRequestAgentError(
            "MedicationRequest agent returned an unexpected status."
        )

    if parsed_json.get("intent") != bounded_input.required_intent:
        raise MedicationRequestAgentError(
            "MedicationRequest agent returned an unexpected intent."
        )

    subject = parsed_json.get("subject")
    if not isinstance(subject, dict):
        raise MedicationRequestAgentError(
            "MedicationRequest agent returned a malformed subject object."
        )
    subject_reference = subject.get("reference")
    if subject_reference not in set(bounded_input.allowed_patient_references):
        raise MedicationRequestAgentError(
            "MedicationRequest agent returned a subject.reference outside the allowed reference set."
        )

    medication = parsed_json.get("medicationCodeableConcept")
    if not isinstance(medication, dict):
        raise MedicationRequestAgentError(
            "MedicationRequest agent returned a malformed medicationCodeableConcept object."
        )
    medication_text = medication.get("text")
    if not isinstance(medication_text, str) or not medication_text.strip():
        raise MedicationRequestAgentError(
            "MedicationRequest agent returned a missing or empty medicationCodeableConcept.text value."
        )
    if medication_text != bounded_input.medication_display_text:
        raise MedicationRequestAgentError(
            "MedicationRequest agent returned medicationCodeableConcept.text that did not exactly match "
            "the authoritative normalized medication text."
        )

    _reject_unsupported_reference_paths(parsed_json)

    normalized = deepcopy(base_resource)
    normalized["resourceType"] = "MedicationRequest"
    normalized["id"] = bounded_input.required_resource_id
    normalized["status"] = bounded_input.required_status
    normalized["intent"] = bounded_input.required_intent
    normalized["subject"] = {"reference": subject_reference}
    normalized["medicationCodeableConcept"] = {"text": medication_text}
    if "authoredOn" in parsed_json:
        authored_on = parsed_json["authoredOn"]
        if not isinstance(authored_on, str) or not authored_on.strip():
            raise MedicationRequestAgentError(
                "MedicationRequest agent returned an invalid authoredOn value."
            )
        normalized["authoredOn"] = authored_on
    return normalized


def _reject_unsupported_reference_paths(payload: dict[str, Any]) -> None:
    for path, value in _iter_reference_paths(payload):
        if path != "subject.reference":
            raise MedicationRequestAgentError(
                f"MedicationRequest agent returned unsupported reference-bearing content at {path}."
            )
        if value != "Patient/patient-1":
            raise MedicationRequestAgentError(
                "MedicationRequest agent returned an unsupported subject.reference value."
            )


def _iter_reference_paths(value: Any, prefix: str = "") -> list[tuple[str, Any]]:
    if isinstance(value, dict):
        paths: list[tuple[str, Any]] = []
        for key, nested in value.items():
            path = f"{prefix}.{key}" if prefix else key
            if key == "reference":
                paths.append((path, nested))
            paths.extend(_iter_reference_paths(nested, path))
        return paths
    if isinstance(value, list):
        paths: list[tuple[str, Any]] = []
        for index, nested in enumerate(value):
            path = f"{prefix}[{index}]"
            paths.extend(_iter_reference_paths(nested, path))
        return paths
    return []


def _find_step_index(step_results: list[ResourceConstructionStepResult], step_id: str) -> int | None:
    for index, step_result in enumerate(step_results):
        if step_result.step_id == step_id:
            return index
    return None


def _find_registry_index(resource_registry: list[ResourceRegistryEntry], placeholder_id: str) -> int | None:
    for index, entry in enumerate(resource_registry):
        if entry.placeholder_id == placeholder_id:
            return index
    return None


def _step_with_agent_result(
    step_result: ResourceConstructionStepResult,
    accepted: MedicationRequestAgentAcceptedResult,
) -> ResourceConstructionStepResult:
    updated = ResourceConstructionStepResult.model_validate(step_result.model_dump())
    updated.resource_scaffold = ResourceScaffoldArtifact.model_validate(
        {
            **updated.resource_scaffold.model_dump(),
            "fhir_scaffold": accepted.normalized_resource_json,
        }
    )
    updated.medication_agent_trace = accepted.trace
    updated.assumptions = [
        *updated.assumptions,
        "MedicationRequest/medicationrequest-1 was accepted from a bounded OpenAI-backed agent response after strict JSON and reference validation.",
    ]
    return updated


def _registry_entry_with_agent_result(
    registry_entry: ResourceRegistryEntry,
    normalized_resource_json: dict[str, Any],
) -> ResourceRegistryEntry:
    return ResourceRegistryEntry.model_validate(
        {
            **registry_entry.model_dump(),
            "current_scaffold": {
                **registry_entry.current_scaffold.model_dump(),
                "fhir_scaffold": normalized_resource_json,
            },
        }
    )
