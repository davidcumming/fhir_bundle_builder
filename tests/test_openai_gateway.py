"""Focused tests for the minimal OpenAI gateway."""

from __future__ import annotations

import json

import pytest

from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.openai_gateway import (
    OpenAIChatCompletionsGateway,
    OpenAIGatewayConfig,
    OpenAIGatewayConfigurationError,
    OpenAIGatewayError,
    load_patient_authoring_gateway_config_from_env,
)


class _FakeSuccessResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return {
            "id": "chatcmpl_test_123",
            "choices": [
                {
                    "message": {
                        "content": '{"resourceType":"MedicationRequest"}',
                    }
                }
            ],
        }


class _FakeErrorResponse:
    status_code = 400
    text = '{"error":{"message":"unsupported parameter: temperature"}}'

    def __init__(self) -> None:
        self.request = type("Request", (), {"url": "https://api.openai.com/v1/chat/completions"})()

    def raise_for_status(self) -> None:
        import httpx

        raise httpx.HTTPStatusError(
            "400 Bad Request",
            request=self.request,
            response=self,
        )

    def json(self) -> dict[str, object]:
        return {"error": {"message": "unsupported parameter: temperature"}}


class _FakeAsyncClient:
    def __init__(self, *, response: object, recorder: dict[str, object], **_: object) -> None:
        self._response = response
        self._recorder = recorder

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def post(self, url: str, *, headers: dict[str, str], json: dict[str, object]) -> object:
        self._recorder["url"] = url
        self._recorder["headers"] = headers
        self._recorder["json"] = json
        return self._response


async def test_openai_gateway_omits_temperature_and_uses_json_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    recorder: dict[str, object] = {}
    response = _FakeSuccessResponse()
    monkeypatch.setattr(
        "fhir_bundle_builder.workflows.psca_bundle_builder_workflow.openai_gateway.httpx.AsyncClient",
        lambda **kwargs: _FakeAsyncClient(response=response, recorder=recorder, **kwargs),
    )
    gateway = OpenAIChatCompletionsGateway(
        OpenAIGatewayConfig(
            api_key="test-key",
            model_name="gpt-5-mini",
        )
    )

    completion = await gateway.create_json_completion(
        system_prompt="Return JSON only.",
        user_payload={"hello": "world"},
        schema_name="test_schema",
        schema={"type": "object"},
    )

    payload = recorder["json"]
    assert "temperature" not in payload
    assert payload["response_format"]["type"] == "json_schema"
    assert payload["response_format"]["json_schema"]["strict"] is True
    assert completion.response_id == "chatcmpl_test_123"
    assert json.loads(completion.raw_text) == {"resourceType": "MedicationRequest"}


async def test_openai_gateway_surfaces_provider_error_body(monkeypatch: pytest.MonkeyPatch) -> None:
    recorder: dict[str, object] = {}
    response = _FakeErrorResponse()
    monkeypatch.setattr(
        "fhir_bundle_builder.workflows.psca_bundle_builder_workflow.openai_gateway.httpx.AsyncClient",
        lambda **kwargs: _FakeAsyncClient(response=response, recorder=recorder, **kwargs),
    )
    gateway = OpenAIChatCompletionsGateway(
        OpenAIGatewayConfig(
            api_key="test-key",
            model_name="gpt-5-mini",
        )
    )

    with pytest.raises(OpenAIGatewayError, match="unsupported parameter: temperature"):
        await gateway.create_json_completion(
            system_prompt="Return JSON only.",
            user_payload={"hello": "world"},
            schema_name="test_schema",
            schema={"type": "object"},
        )


def test_patient_authoring_gateway_config_strips_quotes_and_rejects_non_ascii(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key”")
    monkeypatch.setenv("FHIR_BUNDLE_BUILDER_PATIENT_AUTHORING_MODEL", "“gpt-5-mini”")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    config = load_patient_authoring_gateway_config_from_env()

    assert config.api_key == "sk-test-key"
    assert config.model_name == "gpt-5-mini"

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key\u201dwith-smart-quote")
    with pytest.raises(OpenAIGatewayConfigurationError, match="non-ASCII value for OPENAI_API_KEY"):
        load_patient_authoring_gateway_config_from_env()
