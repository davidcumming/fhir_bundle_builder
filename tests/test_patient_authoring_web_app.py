"""Route tests for the AI-assisted patient authoring web page."""

from __future__ import annotations

import httpx
import pytest

from fhir_bundle_builder.web.patient_authoring_app import app
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.openai_gateway import (
    OpenAIGatewayConfigurationError,
    OpenAIJSONCompletionResponse,
)


class _FakeGateway:
    def __init__(self, raw_text: str, model_name: str = "gpt-test") -> None:
        self._raw_text = raw_text
        self._model_name = model_name

    @property
    def model_name(self) -> str:
        return self._model_name

    async def create_json_completion(self, **_: object) -> OpenAIJSONCompletionResponse:
        return OpenAIJSONCompletionResponse(
            response_id="resp_web_123",
            raw_text=self._raw_text,
            raw_response_json={"id": "resp_web_123", "choices": [{"message": {"content": self._raw_text}}]},
        )


@pytest.mark.asyncio
async def test_get_patient_authoring_page_renders_form_and_sections() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/patient-authoring")

    assert response.status_code == 200
    assert "Patient Profile Authoring" in response.text
    assert "Submitted Input" in response.text
    assert "Validation Errors / Agent Errors" in response.text
    assert "Raw Agent Output" in response.text
    assert "Accepted Structured Patient Profile" in response.text
    assert "Mapped Patient Context" in response.text
    assert "Raw JSON Inspection" in response.text


@pytest.mark.asyncio
async def test_get_root_redirects_to_patient_authoring_page() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        response = await client.get("/")

    assert response.status_code == 302
    assert response.headers["location"] == "/patient-authoring"


@pytest.mark.asyncio
async def test_valid_post_renders_agent_output_and_does_not_use_deterministic_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "fhir_bundle_builder.authoring.patient_builder.build_patient_authored_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("deterministic builder should not run")),
    )
    monkeypatch.setattr(
        "fhir_bundle_builder.authoring.patient_agent.build_patient_authoring_gateway_from_env",
        lambda: _FakeGateway(
            (
                '{"patient":{"display_name":"Jane River","administrative_gender":"female","age_years":58,'
                '"birth_date":"1967-02-14"},"background_facts":{"residence_text":"Calgary, Alberta",'
                '"smoking_status_text":"Never smoker"},"conditions":[{"display_text":"Type 2 diabetes mellitus",'
                '"source_note":"Narrative states diabetes."},{"display_text":"Hypertension",'
                '"source_note":"Narrative states hypertension."}],"medications":[{"display_text":"Metformin 500 MG oral tablet",'
                '"source_note":"Narrative states metformin."},{"display_text":"Lisinopril 10 MG oral tablet",'
                '"source_note":"Narrative states lisinopril."}],"allergies":[{"display_text":"Peanut allergy",'
                '"source_note":"Narrative states peanut allergy."}]}'
            )
        ),
    )

    narrative = (
        "The patient's name is Jane River. She is a female age 58 who lives in Calgary, Alberta. "
        "She has diabetes and hypertension, takes metformin and lisinopril, and has a peanut allergy."
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/patient-authoring",
            data={"narrative": narrative, "complexity": "medium"},
        )

    assert response.status_code == 200
    assert "Raw Agent Output" in response.text
    assert "Accepted Structured Patient Profile" in response.text
    assert "Mapped Patient Context" in response.text
    assert "Agent Trace JSON" in response.text
    assert "Validation Outcome JSON" in response.text
    assert "Accepted Structured Patient Profile JSON" in response.text
    assert "Mapped Patient Context JSON" in response.text
    assert "Jane River" in response.text
    assert "resp_web_123" in response.text
    assert "openai_patient_authoring_agent" in response.text


@pytest.mark.asyncio
async def test_valid_post_renders_vague_medications_when_agent_preserves_explicit_medication_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "fhir_bundle_builder.authoring.patient_agent.build_patient_authoring_gateway_from_env",
        lambda: _FakeGateway(
            (
                '{"patient":{"display_name":"Casey River","administrative_gender":null,"age_years":null,'
                '"birth_date":null},"background_facts":{"residence_text":null,"smoking_status_text":null},'
                '"conditions":[],"medications":[{"display_text":"Inhaler (unspecified)",'
                '"source_note":"Narrative says the patient uses an inhaler when breathing gets bad."},'
                '{"display_text":"Pills for blood pressure (unspecified)",'
                '"source_note":"Narrative says the patient takes a few pills every morning for blood pressure."}],'
                '"allergies":[]}'
            )
        ),
    )

    narrative = (
        "I use an inhaler when my breathing gets bad and I take a few pills every morning "
        "for my blood pressure."
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/patient-authoring",
            data={"narrative": narrative, "complexity": "medium"},
        )

    assert response.status_code == 200
    assert "Inhaler (unspecified)" in response.text
    assert "Pills for blood pressure (unspecified)" in response.text
    assert "Raw Agent Output" in response.text
    assert "Accepted Structured Patient Profile" in response.text


@pytest.mark.asyncio
async def test_invalid_json_post_returns_502_and_shows_raw_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "fhir_bundle_builder.authoring.patient_agent.build_patient_authoring_gateway_from_env",
        lambda: _FakeGateway("not-json"),
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/patient-authoring",
            data={"narrative": "Patient narrative", "complexity": "low"},
        )

    assert response.status_code == 502
    assert "Validation Errors / Agent Errors" in response.text
    assert "non-JSON output" in response.text
    assert "Raw Agent Output" in response.text
    assert "not-json" in response.text
    assert "No accepted structured patient profile yet." in response.text


@pytest.mark.asyncio
async def test_schema_invalid_post_returns_502_and_surfaces_validation_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "fhir_bundle_builder.authoring.patient_agent.build_patient_authoring_gateway_from_env",
        lambda: _FakeGateway(
            (
                '{"patient":{"display_name":" "},"background_facts":{"residence_text":"Toronto",'
                '"smoking_status_text":null},"conditions":[],"medications":[],"allergies":[]}'
            )
        ),
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/patient-authoring",
            data={"narrative": "Patient narrative", "complexity": "medium"},
        )

    assert response.status_code == 502
    assert "schema-invalid content" in response.text or "patient.display_name" in response.text
    assert "patient.display_name" in response.text
    assert "Raw Agent Output" in response.text
    assert "Accepted Structured Patient Profile" in response.text


@pytest.mark.asyncio
async def test_missing_configuration_returns_503_with_visible_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "fhir_bundle_builder.authoring.patient_agent.build_patient_authoring_gateway_from_env",
        lambda: (_ for _ in ()).throw(
            OpenAIGatewayConfigurationError(
                "Patient authoring agent mode requires FHIR_BUNDLE_BUILDER_PATIENT_AUTHORING_MODEL to be set."
            )
        ),
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/patient-authoring",
            data={"narrative": "Patient narrative", "complexity": "medium"},
        )

    assert response.status_code == 503
    assert "FHIR_BUNDLE_BUILDER_PATIENT_AUTHORING_MODEL" in response.text
    assert "Raw Agent Output" in response.text
    assert "No raw agent output yet." in response.text
    assert "No accepted structured patient profile yet." in response.text


@pytest.mark.asyncio
async def test_empty_narrative_returns_validation_error_with_sticky_values() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/patient-authoring",
            data={"narrative": "   ", "complexity": "high"},
        )

    assert response.status_code == 400
    assert "Patient narrative is required." in response.text
    assert "option value=\"high\" selected" in response.text


@pytest.mark.asyncio
async def test_invalid_complexity_returns_validation_error_with_sticky_narrative() -> None:
    transport = httpx.ASGITransport(app=app)
    narrative = "The patient's name is Alex Winter."
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/patient-authoring",
            data={"narrative": narrative, "complexity": "extreme"},
        )

    assert response.status_code == 400
    assert "Complexity must be one of low, medium, or high." in response.text
    assert "Alex Winter" in response.text
