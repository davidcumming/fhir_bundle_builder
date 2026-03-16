"""Focused tests for the bounded MedicationRequest agent slice."""

from __future__ import annotations

import pytest

from fhir_bundle_builder.specifications.psca import PscaAssetQuery, PscaAssetRepository
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.build_plan_builder import (
    build_psca_build_plan,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.medication_request_agent import (
    MedicationRequestAgentError,
    apply_medication_request_agent_to_construction_result,
    invoke_medication_request_agent,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.models import (
    BundleRequestInput,
    MedicationRequestAgentBoundedInput,
    PatientAllergyInput,
    PatientConditionInput,
    PatientContextInput,
    PatientIdentityInput,
    PatientMedicationInput,
    ProfileReferenceInput,
    ProviderContextInput,
    ProviderIdentityInput,
    ProviderOrganizationInput,
    ProviderRoleRelationshipInput,
    SpecificationSelection,
    WorkflowBuildInput,
    WorkflowOptionsInput,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.openai_gateway import (
    OpenAIJSONCompletionResponse,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.request_normalization_builder import (
    build_psca_normalized_request,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.resource_construction_builder import (
    build_psca_resource_construction_result,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.schematic_builder import (
    build_psca_bundle_schematic,
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
            response_id="resp_test_123",
            raw_text=self._raw_text,
            raw_response_json={"id": "resp_test_123", "choices": [{"message": {"content": self._raw_text}}]},
        )


async def test_medication_request_agent_accepts_valid_json_and_preserves_trace() -> None:
    bounded_input = _build_bounded_input()
    accepted = await invoke_medication_request_agent(
        bounded_input=bounded_input,
        base_resource={
            "resourceType": "MedicationRequest",
            "id": "medicationrequest-1",
            "meta": {"profile": ["https://example.org/StructureDefinition/MedicationRequest"]},
            "subject": {"reference": "Patient/patient-1"},
        },
        gateway=_FakeGateway(
            (
                '{"resourceType":"MedicationRequest","id":"medicationrequest-1","status":"draft",'
                '"intent":"proposal","subject":{"reference":"Patient/patient-1"},'
                '"medicationCodeableConcept":{"text":"Atorvastatin 20 MG oral tablet"}}'
            )
        ),
    )

    assert accepted.normalized_resource_json["resourceType"] == "MedicationRequest"
    assert accepted.normalized_resource_json["id"] == "medicationrequest-1"
    assert accepted.normalized_resource_json["subject"]["reference"] == "Patient/patient-1"
    assert (
        accepted.normalized_resource_json["medicationCodeableConcept"]["text"]
        == "Atorvastatin 20 MG oral tablet"
    )
    assert accepted.normalized_resource_json["meta"]["profile"] == [
        "https://example.org/StructureDefinition/MedicationRequest"
    ]
    assert accepted.trace.raw_response_text.startswith('{"resourceType":"MedicationRequest"')
    assert accepted.trace.accepted_normalized_resource_json == accepted.normalized_resource_json
    assert accepted.trace.provider_response_id == "resp_test_123"


async def test_medication_request_agent_rejects_non_json_output() -> None:
    with pytest.raises(MedicationRequestAgentError, match="non-JSON output"):
        await invoke_medication_request_agent(
            bounded_input=_build_bounded_input(),
            base_resource=_base_resource(),
            gateway=_FakeGateway("not-json"),
        )


async def test_medication_request_agent_rejects_wrong_resource_type() -> None:
    with pytest.raises(MedicationRequestAgentError, match="wrong resourceType"):
        await invoke_medication_request_agent(
            bounded_input=_build_bounded_input(),
            base_resource=_base_resource(),
            gateway=_FakeGateway(
                (
                    '{"resourceType":"Condition","id":"medicationrequest-1","status":"draft",'
                    '"intent":"proposal","subject":{"reference":"Patient/patient-1"},'
                    '"medicationCodeableConcept":{"text":"Atorvastatin 20 MG oral tablet"}}'
                )
            ),
        )


async def test_medication_request_agent_rejects_disallowed_reference() -> None:
    with pytest.raises(MedicationRequestAgentError, match="allowed reference set"):
        await invoke_medication_request_agent(
            bounded_input=_build_bounded_input(),
            base_resource=_base_resource(),
            gateway=_FakeGateway(
                (
                    '{"resourceType":"MedicationRequest","id":"medicationrequest-1","status":"draft",'
                    '"intent":"proposal","subject":{"reference":"Patient/other-patient"},'
                    '"medicationCodeableConcept":{"text":"Atorvastatin 20 MG oral tablet"}}'
                )
            ),
        )


async def test_medication_request_agent_rejects_malformed_payload() -> None:
    with pytest.raises(MedicationRequestAgentError, match="malformed medicationCodeableConcept"):
        await invoke_medication_request_agent(
            bounded_input=_build_bounded_input(),
            base_resource=_base_resource(),
            gateway=_FakeGateway(
                (
                    '{"resourceType":"MedicationRequest","id":"medicationrequest-1","status":"draft",'
                    '"intent":"proposal","subject":{"reference":"Patient/patient-1"},'
                    '"medicationCodeableConcept":"Atorvastatin 20 MG oral tablet"}'
                )
            ),
        )


async def test_apply_medication_request_agent_to_construction_result_updates_only_first_medication_step() -> None:
    repository = PscaAssetRepository()
    normalized_assets = repository.load_foundation_context(PscaAssetQuery())
    normalized_request = _build_normalized_request()
    schematic = build_psca_bundle_schematic(normalized_assets, normalized_request)
    plan = build_psca_build_plan(schematic)
    construction = build_psca_resource_construction_result(plan, schematic, normalized_request)

    augmented = await apply_medication_request_agent_to_construction_result(
        construction,
        normalized_request,
        gateway=_FakeGateway(
            (
                '{"resourceType":"MedicationRequest","id":"medicationrequest-1","status":"draft",'
                '"intent":"proposal","subject":{"reference":"Patient/patient-1"},'
                '"medicationCodeableConcept":{"text":"Atorvastatin 20 MG oral tablet"},'
                '"authoredOn":"2026-03-16"}'
            )
        ),
    )

    steps = {step.step_id: step for step in augmented.step_results}
    registry = {entry.placeholder_id: entry for entry in augmented.resource_registry}

    assert augmented.evidence.agent_step_ids == ["build-medicationrequest-1"]
    assert "model-backed MedicationRequest step" in augmented.summary
    assert steps["build-medicationrequest-1"].medication_agent_trace is not None
    assert steps["build-allergyintolerance-1"].medication_agent_trace is None
    assert steps["build-condition-1"].medication_agent_trace is None
    assert (
        registry["medicationrequest-1"].current_scaffold.fhir_scaffold["medicationCodeableConcept"]["text"]
        == "Atorvastatin 20 MG oral tablet"
    )
    assert registry["medicationrequest-1"].current_scaffold.fhir_scaffold["authoredOn"] == "2026-03-16"


def _build_bounded_input() -> MedicationRequestAgentBoundedInput:
    return MedicationRequestAgentBoundedInput(
        placeholder_id="medicationrequest-1",
        medication_id="med-1",
        source_medication_index=0,
        medication_display_text="Atorvastatin 20 MG oral tablet",
        required_resource_id="medicationrequest-1",
        allowed_patient_references=["Patient/patient-1"],
        patient_id="patient-1",
        patient_display_name="Test Patient",
        patient_administrative_gender="female",
        patient_birth_date="1985-02-14",
        provider_display_name="Test Provider",
        selected_organization_display_name="Test Organization",
        selected_role_label="attending-physician",
        request_text="Create a PS-CA bundle with one medication request.",
        bundle_intent="PS-CA document bundle skeleton",
        scenario_label="pytest-med-agent",
    )


def _base_resource() -> dict[str, object]:
    return {
        "resourceType": "MedicationRequest",
        "id": "medicationrequest-1",
        "meta": {"profile": ["https://example.org/StructureDefinition/MedicationRequest"]},
        "subject": {"reference": "Patient/patient-1"},
    }


def _build_normalized_request():
    return build_psca_normalized_request(
        WorkflowBuildInput(
            specification=SpecificationSelection(),
            patient_profile=ProfileReferenceInput(
                profile_id="patient-resource-test",
                display_name="Resource Test Patient",
            ),
            patient_context=PatientContextInput(
                patient=PatientIdentityInput(
                    patient_id="patient-resource-test",
                    display_name="Resource Test Patient",
                    source_type="patient_management",
                    administrative_gender="female",
                    birth_date="1985-02-14",
                ),
                medications=[
                    PatientMedicationInput(
                        medication_id="med-1",
                        display_text="Atorvastatin 20 MG oral tablet",
                    )
                ],
                allergies=[
                    PatientAllergyInput(
                        allergy_id="alg-1",
                        display_text="Peanut allergy",
                    )
                ],
                conditions=[
                    PatientConditionInput(
                        condition_id="cond-1",
                        display_text="Type 2 diabetes mellitus",
                    )
                ],
            ),
            provider_profile=ProfileReferenceInput(
                profile_id="provider-resource-test",
                display_name="Resource Test Provider",
            ),
            provider_context=ProviderContextInput(
                provider=ProviderIdentityInput(
                    provider_id="provider-resource-test",
                    display_name="Resource Test Provider",
                    source_type="provider_management",
                ),
                organizations=[
                    ProviderOrganizationInput(
                        organization_id="org-resource-test",
                        display_name="Resource Test Organization",
                    )
                ],
                provider_role_relationships=[
                    ProviderRoleRelationshipInput(
                        relationship_id="provider-role-1",
                        organization_id="org-resource-test",
                        role_label="attending-physician",
                    )
                ],
            ),
            request=BundleRequestInput(
                request_text="Create an agent-backed MedicationRequest for testing.",
                scenario_label="pytest-med-agent",
            ),
            workflow_options=WorkflowOptionsInput(
                medication_request_generation_mode="agent_required",
            ),
        )
    )
