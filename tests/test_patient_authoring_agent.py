"""Focused tests for the bounded patient authoring agent slice."""

from __future__ import annotations

from fhir_bundle_builder.authoring import (
    PatientAuthoringInput,
    author_patient_record,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.openai_gateway import (
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
            response_id="resp_patient_123",
            raw_text=self._raw_text,
            raw_response_json={"id": "resp_patient_123", "choices": [{"message": {"content": self._raw_text}}]},
        )


async def test_patient_authoring_agent_accepts_valid_json_and_normalizes_record() -> None:
    result = await author_patient_record(
        PatientAuthoringInput(
            authoring_text=(
                "Jane River is a 58 year old woman in Calgary with diabetes and hypertension. "
                "She takes metformin and lisinopril and has a peanut allergy."
            ),
            complexity_level="medium",
            scenario_label="pytest-patient-agent-valid",
        ),
        gateway=_FakeGateway(
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

    assert result.validation_outcome.status == "accepted"
    assert result.accepted_record is not None
    assert result.accepted_record.patient.display_name == "Jane River"
    assert result.accepted_record.authoring_evidence.builder_mode == "openai_patient_authoring_agent"
    assert result.accepted_record.conditions[0].source_mode == "agent_structured_output"
    assert result.accepted_record.medications[0].medication_id == "medication-authored-1"
    assert result.trace.raw_response_text.startswith('{"patient":{"display_name":"Jane River"')
    assert result.trace.accepted_payload_json is not None


async def test_patient_authoring_agent_rejects_invalid_json_but_preserves_raw_output() -> None:
    result = await author_patient_record(
        PatientAuthoringInput(
            authoring_text="Test narrative",
            complexity_level="low",
            scenario_label="pytest-patient-agent-invalid-json",
        ),
        gateway=_FakeGateway("not-json"),
    )

    assert result.validation_outcome.status == "rejected"
    assert result.accepted_record is None
    assert "non-JSON output" in result.validation_outcome.errors[0]
    assert result.trace.raw_response_text == "not-json"
    assert result.trace.status == "rejected"


async def test_patient_authoring_agent_rejects_schema_invalid_payload() -> None:
    result = await author_patient_record(
        PatientAuthoringInput(
            authoring_text="Test narrative",
            complexity_level="medium",
            scenario_label="pytest-patient-agent-schema-invalid",
        ),
        gateway=_FakeGateway(
            (
                '{"patient":{"display_name":" "},"background_facts":{"residence_text":"Toronto",'
                '"smoking_status_text":null},"conditions":[],"medications":[],"allergies":[]}'
            )
        ),
    )

    assert result.validation_outcome.status == "rejected"
    assert result.accepted_record is None
    assert any("patient.display_name" in error for error in result.validation_outcome.errors)
    assert result.trace.parsed_response_json is not None
    assert result.trace.accepted_payload_json is None
