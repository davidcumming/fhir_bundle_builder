"""Minimal OpenAI chat-completions gateway for bounded workflow agent calls."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import httpx


class OpenAIGatewayConfigurationError(RuntimeError):
    """Raised when the OpenAI gateway is required but not configured."""


class OpenAIGatewayError(RuntimeError):
    """Raised when an OpenAI gateway call fails or returns an unusable payload."""


@dataclass(frozen=True)
class OpenAIGatewayConfig:
    """Runtime configuration for the minimal OpenAI gateway."""

    api_key: str
    model_name: str
    base_url: str = "https://api.openai.com/v1"
    timeout_seconds: float = 60.0


@dataclass(frozen=True)
class OpenAIJSONCompletionResponse:
    """Minimal structured response returned by the OpenAI gateway."""

    response_id: str | None
    raw_text: str
    raw_response_json: dict[str, Any]


def load_openai_gateway_config_from_env() -> OpenAIGatewayConfig:
    """Load the minimal OpenAI gateway configuration from environment variables."""

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise OpenAIGatewayConfigurationError(
            "MedicationRequest agent mode requires OPENAI_API_KEY to be set."
        )

    model_name = os.getenv("FHIR_BUNDLE_BUILDER_MEDICATION_AGENT_MODEL", "").strip()
    if not model_name:
        raise OpenAIGatewayConfigurationError(
            "MedicationRequest agent mode requires FHIR_BUNDLE_BUILDER_MEDICATION_AGENT_MODEL to be set."
        )

    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip() or "https://api.openai.com/v1"
    timeout_seconds = float(os.getenv("FHIR_BUNDLE_BUILDER_MEDICATION_AGENT_TIMEOUT_SECONDS", "60"))
    return OpenAIGatewayConfig(
        api_key=api_key,
        model_name=model_name,
        base_url=base_url.rstrip("/"),
        timeout_seconds=timeout_seconds,
    )


class OpenAIChatCompletionsGateway:
    """Minimal OpenAI chat-completions client for strict JSON workflow calls."""

    def __init__(self, config: OpenAIGatewayConfig) -> None:
        self._config = config

    @property
    def model_name(self) -> str:
        return self._config.model_name

    async def create_json_completion(
        self,
        *,
        system_prompt: str,
        user_payload: dict[str, Any],
        schema_name: str,
        schema: dict[str, Any],
    ) -> OpenAIJSONCompletionResponse:
        """Submit one strict-JSON chat completion request and return the raw model output."""

        payload = {
            "model": self._config.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=True, indent=2)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                },
            },
        }

        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self._config.timeout_seconds) as client:
            try:
                response = await client.post(
                    f"{self._config.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                error_body = _provider_error_body(exc.response)
                raise OpenAIGatewayError(
                    "MedicationRequest agent call to OpenAI failed: "
                    f"HTTP {exc.response.status_code} for {exc.request.url}. "
                    f"Provider response: {error_body}"
                ) from exc
            except httpx.HTTPError as exc:
                raise OpenAIGatewayError(
                    f"MedicationRequest agent call to OpenAI failed: {exc}."
                ) from exc

        try:
            response_json = response.json()
        except ValueError as exc:
            raise OpenAIGatewayError(
                "MedicationRequest agent call returned a non-JSON provider response."
            ) from exc

        raw_text = _extract_first_message_text(response_json)
        if not raw_text:
            raise OpenAIGatewayError(
                "MedicationRequest agent call did not return any message content."
            )

        response_id = response_json.get("id")
        return OpenAIJSONCompletionResponse(
            response_id=response_id if isinstance(response_id, str) else None,
            raw_text=raw_text,
            raw_response_json=response_json,
        )


def _extract_first_message_text(response_json: dict[str, Any]) -> str:
    choices = response_json.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return ""
    message = first_choice.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts).strip()
    return ""


def _provider_error_body(response: httpx.Response) -> str:
    try:
        body = response.json()
        return json.dumps(body, ensure_ascii=True)
    except ValueError:
        return response.text[:1000]
