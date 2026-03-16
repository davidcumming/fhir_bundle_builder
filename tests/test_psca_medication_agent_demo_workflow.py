"""Smoke test for the one-click MedicationRequest agent demo workflow."""

from __future__ import annotations

from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.openai_gateway import (
    OpenAIGatewayConfig,
    OpenAIJSONCompletionResponse,
)
from fhir_bundle_builder.workflows.psca_medication_agent_demo_workflow.models import (
    MedicationAgentDemoInput,
)
from fhir_bundle_builder.workflows.psca_medication_agent_demo_workflow.workflow import (
    workflow,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow import medication_request_agent as medication_agent_module


class _DemoWorkflowFakeMedicationGateway:
    def __init__(self, config: OpenAIGatewayConfig) -> None:
        self._config = config

    @property
    def model_name(self) -> str:
        return self._config.model_name

    async def create_json_completion(self, **_: object) -> OpenAIJSONCompletionResponse:
        raw_text = (
            '{"resourceType":"MedicationRequest","id":"medicationrequest-1","status":"draft",'
            '"intent":"proposal","subject":{"reference":"Patient/patient-1"},'
            '"medicationCodeableConcept":{"text":"Atorvastatin 20 MG oral tablet"}}'
        )
        return OpenAIJSONCompletionResponse(
            response_id="resp_demo_workflow_test_123",
            raw_text=raw_text,
            raw_response_json={"id": "resp_demo_workflow_test_123", "choices": [{"message": {"content": raw_text}}]},
        )


async def test_psca_medication_agent_demo_workflow_runs_without_manual_input(
    monkeypatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("FHIR_BUNDLE_BUILDER_MEDICATION_AGENT_MODEL", "gpt-test")
    monkeypatch.setattr(
        medication_agent_module,
        "OpenAIChatCompletionsGateway",
        _DemoWorkflowFakeMedicationGateway,
    )

    result = await workflow.run(
        message=MedicationAgentDemoInput(),
        include_status_events=True,
    )
    final_output = result.get_outputs()[0]

    assert final_output.normalized_request.workflow_defaults.medication_request_generation_mode == (
        "agent_required"
    )
    assert final_output.resource_construction.evidence.agent_step_ids == ["build-medicationrequest-1"]
    medication_step = next(
        step
        for step in final_output.resource_construction.step_results
        if step.step_id == "build-medicationrequest-1"
    )
    assert medication_step.medication_agent_trace is not None
    assert (
        medication_step.resource_scaffold.fhir_scaffold["medicationCodeableConcept"]["text"]
        == "Atorvastatin 20 MG oral tablet"
    )
