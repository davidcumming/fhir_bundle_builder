"""Direct tests for deterministic PS-CA request normalization."""

from __future__ import annotations

import pytest

from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.models import (
    BundleRequestInput,
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
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.request_normalization_builder import (
    build_psca_normalized_request,
)


def test_request_normalization_supports_legacy_provider_profile_mode() -> None:
    normalized = build_psca_normalized_request(
        WorkflowBuildInput(
            specification=SpecificationSelection(),
            patient_profile=ProfileReferenceInput(
                profile_id="patient-normalization-test",
                display_name="Normalization Test Patient",
            ),
            provider_profile=ProfileReferenceInput(
                profile_id="provider-normalization-test",
                display_name="Normalization Test Provider",
            ),
            request=BundleRequestInput(
                request_text="Create a deterministic normalized request for testing.",
                scenario_label="pytest-normalization-legacy",
            ),
        )
    )

    assert normalized.provider_profile.profile_id == "provider-normalization-test"
    assert normalized.patient_profile.profile_id == "patient-normalization-test"
    assert normalized.patient_context.normalization_mode == "legacy_patient_profile"
    assert normalized.patient_context.patient.patient_id == "patient-normalization-test"
    assert normalized.patient_context.selected_medication_for_single_entry is None
    assert normalized.patient_context.planned_medication_entries == []
    assert normalized.patient_context.deferred_additional_medication_count == 0
    assert normalized.provider_context.normalization_mode == "legacy_provider_profile"
    assert normalized.provider_context.provider.provider_id == "provider-normalization-test"
    assert normalized.provider_context.selected_provider_role_relationship is None
    assert normalized.provider_context.selected_organization is None


def test_request_normalization_supports_explicit_provider_context_selection() -> None:
    normalized = build_psca_normalized_request(
        _workflow_input_with_provider_context(selected_relationship_id="provider-role-2")
    )

    assert normalized.provider_profile.profile_id == "provider-normalization-test"
    assert normalized.provider_profile.source_type == "provider_management"
    assert normalized.provider_context.normalization_mode == "provider_context_explicit_selection"
    assert normalized.provider_context.selected_provider_role_relationship is not None
    assert normalized.provider_context.selected_provider_role_relationship.relationship_id == "provider-role-2"
    assert normalized.provider_context.selected_organization is not None
    assert normalized.provider_context.selected_organization.organization_id == "org-normalization-2"


def test_request_normalization_supports_explicit_patient_context() -> None:
    normalized = build_psca_normalized_request(_workflow_input_with_patient_context())

    assert normalized.patient_profile.profile_id == "patient-normalization-test"
    assert normalized.patient_profile.source_type == "patient_management"
    assert normalized.patient_context.normalization_mode == "patient_context_explicit"
    assert normalized.patient_context.patient.patient_id == "patient-normalization-test"
    assert normalized.patient_context.patient.administrative_gender == "female"
    assert normalized.patient_context.patient.birth_date == "1985-02-14"
    assert normalized.patient_context.selected_medication_for_single_entry is not None
    assert normalized.patient_context.selected_medication_for_single_entry.medication_id == "med-1"
    assert len(normalized.patient_context.planned_medication_entries) == 1
    assert normalized.patient_context.planned_medication_entries[0].placeholder_id == "medicationrequest-1"
    assert normalized.patient_context.planned_medication_entries[0].source_medication_index == 0
    assert normalized.patient_context.planned_medication_entries[0].medication_id == "med-1"
    assert normalized.patient_context.deferred_additional_medication_count == 0
    assert normalized.patient_context.selected_allergy_for_single_entry is not None
    assert normalized.patient_context.selected_allergy_for_single_entry.allergy_id == "alg-1"
    assert normalized.patient_context.selected_condition_for_single_entry is not None
    assert normalized.patient_context.selected_condition_for_single_entry.condition_id == "cond-1"


def test_request_normalization_selects_single_relationship_deterministically() -> None:
    normalized = build_psca_normalized_request(
        WorkflowBuildInput(
            specification=SpecificationSelection(),
            patient_profile=ProfileReferenceInput(
                profile_id="patient-normalization-test",
                display_name="Normalization Test Patient",
            ),
            provider_profile=ProfileReferenceInput(
                profile_id="provider-profile-legacy",
                display_name="Legacy Provider",
            ),
            provider_context=ProviderContextInput(
                provider=ProviderIdentityInput(
                    provider_id="provider-normalization-test",
                    display_name="Normalization Test Provider",
                    source_type="provider_management",
                ),
                organizations=[
                    ProviderOrganizationInput(
                        organization_id="org-normalization-1",
                        display_name="Normalization Org One",
                    )
                ],
                provider_role_relationships=[
                    ProviderRoleRelationshipInput(
                        relationship_id="provider-role-1",
                        organization_id="org-normalization-1",
                        role_label="document-author",
                    )
                ],
            ),
            request=BundleRequestInput(
                request_text="Create a deterministic normalized request for testing.",
                scenario_label="pytest-normalization-single",
            ),
        )
    )

    assert normalized.provider_context.normalization_mode == "provider_context_single_relationship"
    assert normalized.provider_context.selected_provider_role_relationship is not None
    assert normalized.provider_context.selected_provider_role_relationship.relationship_id == "provider-role-1"
    assert normalized.provider_context.selected_organization is not None
    assert normalized.provider_context.selected_organization.organization_id == "org-normalization-1"


def test_request_normalization_rejects_multiple_relationships_without_selection() -> None:
    with pytest.raises(ValueError, match="multiple provider-role relationships"):
        build_psca_normalized_request(_workflow_input_with_provider_context())


def test_request_normalization_rejects_selected_relationship_with_unknown_organization() -> None:
    with pytest.raises(ValueError, match="unknown organization"):
        build_psca_normalized_request(
            WorkflowBuildInput(
                specification=SpecificationSelection(),
                patient_profile=ProfileReferenceInput(
                    profile_id="patient-normalization-test",
                    display_name="Normalization Test Patient",
                ),
                provider_profile=ProfileReferenceInput(
                    profile_id="provider-profile-legacy",
                    display_name="Legacy Provider",
                ),
                provider_context=ProviderContextInput(
                    provider=ProviderIdentityInput(
                        provider_id="provider-normalization-test",
                        display_name="Normalization Test Provider",
                        source_type="provider_management",
                    ),
                    organizations=[
                        ProviderOrganizationInput(
                            organization_id="org-normalization-1",
                            display_name="Normalization Org One",
                        )
                    ],
                    provider_role_relationships=[
                        ProviderRoleRelationshipInput(
                            relationship_id="provider-role-1",
                            organization_id="org-missing",
                            role_label="document-author",
                        )
                    ],
                    selected_provider_role_relationship_id="provider-role-1",
                ),
                request=BundleRequestInput(
                    request_text="Create a deterministic normalized request for testing.",
                    scenario_label="pytest-normalization-invalid",
                ),
            )
        )


def test_request_normalization_keeps_multiple_patient_items_inspectable_without_selecting_one() -> None:
    normalized = build_psca_normalized_request(
        WorkflowBuildInput(
            specification=SpecificationSelection(),
            patient_profile=ProfileReferenceInput(
                profile_id="patient-profile-legacy",
                display_name="Legacy Patient",
            ),
            patient_context=PatientContextInput(
                patient=PatientIdentityInput(
                    patient_id="patient-normalization-test",
                    display_name="Normalization Test Patient",
                    source_type="patient_management",
                ),
                medications=[
                    PatientMedicationInput(medication_id="med-1", display_text="Atorvastatin 20 MG oral tablet"),
                    PatientMedicationInput(medication_id="med-2", display_text="Metformin 500 MG oral tablet"),
                ],
                allergies=[
                    PatientAllergyInput(allergy_id="alg-1", display_text="Peanut allergy"),
                    PatientAllergyInput(allergy_id="alg-2", display_text="Latex allergy"),
                ],
                conditions=[
                    PatientConditionInput(condition_id="cond-1", display_text="Type 2 diabetes mellitus"),
                    PatientConditionInput(condition_id="cond-2", display_text="Hypertension"),
                ],
            ),
            provider_profile=ProfileReferenceInput(
                profile_id="provider-normalization-test",
                display_name="Normalization Test Provider",
            ),
            request=BundleRequestInput(
                request_text="Create a deterministic normalized request for testing.",
                scenario_label="pytest-normalization-multi-patient",
            ),
        )
    )

    assert len(normalized.patient_context.medications) == 2
    assert len(normalized.patient_context.allergies) == 2
    assert len(normalized.patient_context.conditions) == 2
    assert normalized.patient_context.selected_medication_for_single_entry is None
    assert [entry.placeholder_id for entry in normalized.patient_context.planned_medication_entries] == [
        "medicationrequest-1",
        "medicationrequest-2",
    ]
    assert [entry.source_medication_index for entry in normalized.patient_context.planned_medication_entries] == [0, 1]
    assert [entry.medication_id for entry in normalized.patient_context.planned_medication_entries] == [
        "med-1",
        "med-2",
    ]
    assert normalized.patient_context.deferred_additional_medication_count == 0
    assert normalized.patient_context.selected_allergy_for_single_entry is None
    assert normalized.patient_context.selected_condition_for_single_entry is None


def test_request_normalization_records_bounded_medication_overflow_explicitly() -> None:
    normalized = build_psca_normalized_request(
        WorkflowBuildInput(
            specification=SpecificationSelection(),
            patient_profile=ProfileReferenceInput(
                profile_id="patient-profile-overflow",
                display_name="Overflow Patient",
            ),
            patient_context=PatientContextInput(
                patient=PatientIdentityInput(
                    patient_id="patient-normalization-overflow",
                    display_name="Normalization Overflow Patient",
                    source_type="patient_management",
                ),
                medications=[
                    PatientMedicationInput(medication_id="med-1", display_text="Atorvastatin 20 MG oral tablet"),
                    PatientMedicationInput(medication_id="med-2", display_text="Metformin 500 MG oral tablet"),
                    PatientMedicationInput(medication_id="med-3", display_text="Lisinopril 10 MG oral tablet"),
                ],
                allergies=[],
                conditions=[],
            ),
            provider_profile=ProfileReferenceInput(
                profile_id="provider-normalization-test",
                display_name="Normalization Test Provider",
            ),
            request=BundleRequestInput(
                request_text="Create a deterministic normalized request for medication overflow testing.",
                scenario_label="pytest-normalization-med-overflow",
            ),
        )
    )

    assert [entry.medication_id for entry in normalized.patient_context.planned_medication_entries] == [
        "med-1",
        "med-2",
    ]
    assert normalized.patient_context.deferred_additional_medication_count == 1


def _workflow_input_with_provider_context(
    *,
    selected_relationship_id: str | None = None,
) -> WorkflowBuildInput:
    return WorkflowBuildInput(
        specification=SpecificationSelection(),
        patient_profile=ProfileReferenceInput(
            profile_id="patient-normalization-test",
            display_name="Normalization Test Patient",
        ),
        provider_profile=ProfileReferenceInput(
            profile_id="provider-profile-legacy",
            display_name="Legacy Provider",
        ),
        provider_context=ProviderContextInput(
            provider=ProviderIdentityInput(
                provider_id="provider-normalization-test",
                display_name="Normalization Test Provider",
                source_type="provider_management",
            ),
            organizations=[
                ProviderOrganizationInput(
                    organization_id="org-normalization-1",
                    display_name="Normalization Org One",
                ),
                ProviderOrganizationInput(
                    organization_id="org-normalization-2",
                    display_name="Normalization Org Two",
                ),
            ],
            provider_role_relationships=[
                ProviderRoleRelationshipInput(
                    relationship_id="provider-role-1",
                    organization_id="org-normalization-1",
                    role_label="document-author",
                ),
                ProviderRoleRelationshipInput(
                    relationship_id="provider-role-2",
                    organization_id="org-normalization-2",
                    role_label="attending-physician",
                ),
            ],
            selected_provider_role_relationship_id=selected_relationship_id,
        ),
        request=BundleRequestInput(
            request_text="Create a deterministic normalized request for testing.",
            scenario_label="pytest-normalization-rich",
        ),
    )


def _workflow_input_with_patient_context() -> WorkflowBuildInput:
    return WorkflowBuildInput(
        specification=SpecificationSelection(),
        patient_profile=ProfileReferenceInput(
            profile_id="patient-profile-legacy",
            display_name="Legacy Patient",
        ),
        patient_context=PatientContextInput(
            patient=PatientIdentityInput(
                patient_id="patient-normalization-test",
                display_name="Normalization Test Patient",
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
            profile_id="provider-normalization-test",
            display_name="Normalization Test Provider",
        ),
        request=BundleRequestInput(
            request_text="Create a deterministic normalized request for testing.",
            scenario_label="pytest-normalization-patient",
        ),
    )
