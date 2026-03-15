"""Direct and end-to-end tests for thin authored-input bundle-build orchestration."""

from __future__ import annotations

from fhir_bundle_builder.authoring import (
    AuthoredBundleBuildInput,
    PatientAuthoringInput,
    ProviderAuthoringInput,
    build_patient_authored_record,
    build_provider_authored_record,
    prepare_authored_bundle_build_input,
    run_authored_bundle_build,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.models import BundleRequestInput


def test_authored_bundle_preparation_composes_rich_patient_and_provider_records() -> None:
    patient_record = build_patient_authored_record(
        PatientAuthoringInput(
            authoring_text=(
                "The patient's name is Nora Field. She is a female age 55 who lives in Red Deer, Alberta. "
                "She has diabetes, takes metformin, and has a peanut allergy."
            ),
            complexity_level="medium",
            scenario_label="pytest-authored-bundle-patient-rich",
        )
    )
    provider_record = build_provider_authored_record(
        ProviderAuthoringInput(
            authoring_text=(
                "The provider's name is Maya Chen. "
                "She is a female oncologist at Fraser Cancer Clinic."
            ),
            scenario_label="pytest-authored-bundle-provider-rich",
        )
    )

    preparation = prepare_authored_bundle_build_input(
        AuthoredBundleBuildInput(
            patient_record=patient_record,
            provider_record=provider_record,
            request=BundleRequestInput(
                request_text="Create a deterministic bundle from authored patient and provider records.",
                scenario_label="pytest-authored-bundle-prep-rich",
            ),
        )
    )

    assert preparation.source_patient_record_id == patient_record.record_id
    assert preparation.source_provider_record_id == provider_record.record_id
    assert preparation.patient_mapping.source_record_id == patient_record.record_id
    assert preparation.provider_mapping.source_record_id == provider_record.record_id
    assert preparation.workflow_input.patient_profile.profile_id == patient_record.patient.patient_id
    assert preparation.workflow_input.patient_profile.display_name == "Nora Field"
    assert preparation.workflow_input.patient_profile.source_type == "patient_management"
    assert preparation.workflow_input.provider_profile.profile_id == provider_record.provider.provider_id
    assert preparation.workflow_input.provider_profile.display_name == "Maya Chen"
    assert preparation.workflow_input.provider_profile.source_type == "provider_management"
    assert preparation.workflow_input.patient_context is not None
    assert preparation.workflow_input.provider_context is not None
    assert preparation.workflow_input_summary.patient_id == patient_record.patient.patient_id
    assert preparation.workflow_input_summary.provider_id == provider_record.provider.provider_id
    assert preparation.workflow_input_summary.mapped_condition_count == 1
    assert preparation.workflow_input_summary.mapped_medication_count == 1
    assert preparation.workflow_input_summary.mapped_allergy_count == 1
    assert preparation.workflow_input_summary.mapped_organization_count == 1
    assert preparation.workflow_input_summary.mapped_provider_role_relationship_count == 1
    assert preparation.workflow_input_summary.has_selected_provider_role_relationship is True
    assert preparation.workflow_input_summary.scenario_label == "pytest-authored-bundle-prep-rich"
    assert preparation.patient_mapping.unmapped_fields == [
        "patient.age_years",
        "background_facts.residence_text",
    ]
    assert preparation.provider_mapping.unmapped_fields == ["professional_facts.administrative_gender"]


def test_authored_bundle_preparation_keeps_thin_provider_mapping_inspectable() -> None:
    patient_record = build_patient_authored_record(
        PatientAuthoringInput(
            authoring_text=(
                "The patient's name is Ellis Stone. He is a male age 48 who has hypertension and takes lisinopril."
            ),
            complexity_level="low",
            scenario_label="pytest-authored-bundle-patient-thin",
        )
    )
    provider_record = build_provider_authored_record(
        ProviderAuthoringInput(
            authoring_text="The provider is a female oncologist in BC.",
            scenario_label="pytest-authored-bundle-provider-thin",
        )
    )

    preparation = prepare_authored_bundle_build_input(
        AuthoredBundleBuildInput(
            patient_record=patient_record,
            provider_record=provider_record,
            request=BundleRequestInput(
                request_text="Create a deterministic bundle from thin authored provider context.",
                scenario_label="pytest-authored-bundle-prep-thin-provider",
            ),
        )
    )

    assert preparation.workflow_input.provider_context is not None
    assert preparation.workflow_input.provider_context.provider.display_name == "Authored Oncologist"
    assert preparation.workflow_input.provider_context.organizations == []
    assert preparation.workflow_input.provider_context.provider_role_relationships == []
    assert preparation.workflow_input.provider_context.selected_provider_role_relationship_id is None
    assert preparation.workflow_input.provider_profile.profile_id == provider_record.provider.provider_id
    assert preparation.provider_mapping.unmapped_fields == [
        "professional_facts.administrative_gender",
        "professional_facts.jurisdiction_text",
        "professional_facts.specialty_or_role_label",
    ]
    assert preparation.workflow_input_summary.mapped_organization_count == 0
    assert preparation.workflow_input_summary.mapped_provider_role_relationship_count == 0
    assert preparation.workflow_input_summary.has_selected_provider_role_relationship is False


async def test_authored_bundle_orchestration_runs_workflow_from_composed_authored_records() -> None:
    patient_record = build_patient_authored_record(
        PatientAuthoringInput(
            authoring_text=(
                "The patient's name is Nora Field. She is a female age 55 who lives in Red Deer, Alberta. "
                "She has diabetes, takes metformin, and has a peanut allergy."
            ),
            complexity_level="medium",
            scenario_label="pytest-authored-bundle-run-patient",
        )
    )
    provider_record = build_provider_authored_record(
        ProviderAuthoringInput(
            authoring_text=(
                "The provider's name is Maya Chen. "
                "She is a female oncologist at Fraser Cancer Clinic."
            ),
            scenario_label="pytest-authored-bundle-run-provider",
        )
    )

    result = await run_authored_bundle_build(
        AuthoredBundleBuildInput(
            patient_record=patient_record,
            provider_record=provider_record,
            request=BundleRequestInput(
                request_text="Create a deterministic authored-input PS-CA bundle run.",
                scenario_label="pytest-authored-bundle-run",
            ),
        )
    )

    assert result.preparation.workflow_input_summary.scenario_label == "pytest-authored-bundle-run"
    assert result.preparation.workflow_input.patient_context is not None
    assert result.preparation.workflow_input.provider_context is not None
    assert result.workflow_output.normalized_request.patient_context.patient.patient_id == patient_record.patient.patient_id
    assert result.workflow_output.normalized_request.provider_context.provider.provider_id == (
        provider_record.provider.provider_id
    )
    assert result.workflow_output.normalized_request.provider_context.selected_provider_role_relationship is not None
    assert result.workflow_output.normalized_request.provider_context.selected_provider_role_relationship.role_label == (
        "oncologist"
    )
    assert result.workflow_output.resource_construction.step_results[0].resource_scaffold.fhir_scaffold["name"][0][
        "text"
    ] == "Nora Field"
    assert result.workflow_output.resource_construction.step_results[1].resource_scaffold.fhir_scaffold["name"][0][
        "text"
    ] == "Maya Chen"
    assert result.workflow_output.resource_construction.step_results[2].resource_scaffold.fhir_scaffold["name"] == (
        "Fraser Cancer Clinic"
    )
    assert result.workflow_output.resource_construction.step_results[3].resource_scaffold.fhir_scaffold["code"][0][
        "text"
    ] == "oncologist"
    assert result.workflow_output.validation_report.workflow_validation.status == "passed"
