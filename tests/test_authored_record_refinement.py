"""Direct tests for bounded authored-record review/edit refinement."""

from __future__ import annotations

from fhir_bundle_builder.authoring import (
    PatientAuthoringInput,
    PatientAuthoredRecordReviewEditInput,
    ProviderAuthoringInput,
    ProviderAuthoredRecordReviewEditInput,
    apply_patient_authored_record_review_edits,
    apply_provider_authored_record_review_edits,
    build_patient_authored_record,
    build_provider_authored_record,
)


def test_patient_authored_record_refinement_noop_keeps_original_record() -> None:
    record = build_patient_authored_record(
        PatientAuthoringInput(
            authoring_text="The patient's name is Nora Field. She is a female age 55 who has diabetes and takes metformin.",
            complexity_level="medium",
            scenario_label="pytest-patient-refinement-noop",
        )
    )

    result = apply_patient_authored_record_review_edits(record, PatientAuthoredRecordReviewEditInput())

    assert result.edits_applied is False
    assert result.source_record_id == record.record_id
    assert result.refined_record_id == record.record_id
    assert result.original_record == record
    assert result.refined_record == record
    assert result.edited_field_paths == []


def test_patient_authored_record_refinement_applies_scalar_and_list_edits() -> None:
    record = build_patient_authored_record(
        PatientAuthoringInput(
            authoring_text=(
                "The patient's name is Jane River. She is a female age 58 who lives in Calgary, Alberta. "
                "She has diabetes and hypertension, takes metformin and lisinopril, and has a peanut allergy."
            ),
            complexity_level="high",
            scenario_label="pytest-patient-refinement-edit",
        )
    )

    result = apply_patient_authored_record_review_edits(
        record,
        PatientAuthoredRecordReviewEditInput(
            display_name="Nora Field",
            birth_date="1969-05-14",
            residence_text="Red Deer, Alberta",
            smoking_status_text="Former smoker",
            condition_display_texts=["Type 2 diabetes mellitus"],
            medication_display_texts=["Metformin 850 MG oral tablet"],
            allergy_display_texts=[],
        ),
    )

    assert result.edits_applied is True
    assert result.refined_record.record_id != record.record_id
    assert result.refined_record.patient.patient_id == record.patient.patient_id
    assert result.refined_record.patient.display_name == "Nora Field"
    assert result.refined_record.patient.birth_date == "1969-05-14"
    assert result.refined_record.background_facts.residence_text == "Red Deer, Alberta"
    assert result.refined_record.background_facts.smoking_status_text == "Former smoker"
    assert [condition.display_text for condition in result.refined_record.conditions] == ["Type 2 diabetes mellitus"]
    assert [medication.display_text for medication in result.refined_record.medications] == [
        "Metformin 850 MG oral tablet"
    ]
    assert result.refined_record.allergies == []
    assert result.refined_record.conditions[0].source_mode == "manual_review_edit"
    assert result.refined_record.medications[0].source_mode == "manual_review_edit"
    assert sorted(result.edited_field_paths) == [
        "allergies",
        "background_facts.residence_text",
        "background_facts.smoking_status_text",
        "conditions",
        "medications",
        "patient.birth_date",
        "patient.display_name",
    ]
    assert [gap.area for gap in result.refined_record.unresolved_authoring_gaps] == [
        "conditions",
        "medications",
        "allergies",
    ]


def test_provider_authored_record_refinement_updates_thin_provider_without_inventing_org_or_relationship() -> None:
    record = build_provider_authored_record(
        ProviderAuthoringInput(
            authoring_text="The provider is a female oncologist in BC.",
            scenario_label="pytest-provider-refinement-thin",
        )
    )

    result = apply_provider_authored_record_review_edits(
        record,
        ProviderAuthoredRecordReviewEditInput(
            display_name="Dr. Maya Chen",
            jurisdiction_text="British Columbia",
            specialty_or_role_label="oncologist",
        ),
    )

    assert result.edits_applied is True
    assert result.refined_record.provider.provider_id == record.provider.provider_id
    assert result.refined_record.provider.display_name == "Dr. Maya Chen"
    assert result.refined_record.professional_facts.jurisdiction_text == "British Columbia"
    assert result.refined_record.organizations == []
    assert result.refined_record.provider_role_relationships == []
    assert result.refined_record.selected_provider_role_relationship_id is None
    assert sorted(gap.gap_code for gap in result.refined_record.unresolved_authoring_gaps) == [
        "missing_organization",
        "missing_provider_role_relationship",
    ]


def test_provider_authored_record_refinement_can_create_explicit_org_and_relationship() -> None:
    record = build_provider_authored_record(
        ProviderAuthoringInput(
            authoring_text="The provider is a female oncologist in BC.",
            scenario_label="pytest-provider-refinement-rich",
        )
    )

    result = apply_provider_authored_record_review_edits(
        record,
        ProviderAuthoredRecordReviewEditInput(
            display_name="Maya Chen",
            organization_display_name="Fraser Cancer Clinic",
            relationship_role_label="oncologist",
            selected_relationship_active=True,
        ),
    )

    assert result.edits_applied is True
    assert result.refined_record.provider.display_name == "Maya Chen"
    assert len(result.refined_record.organizations) == 1
    assert result.refined_record.organizations[0].display_name == "Fraser Cancer Clinic"
    assert result.refined_record.organizations[0].source_mode == "manual_review_edit"
    assert len(result.refined_record.provider_role_relationships) == 1
    assert result.refined_record.provider_role_relationships[0].role_label == "oncologist"
    assert result.refined_record.provider_role_relationships[0].source_mode == "manual_review_edit"
    assert result.refined_record.selected_provider_role_relationship_id == (
        result.refined_record.provider_role_relationships[0].relationship_id
    )
    assert result.refined_record.unresolved_authoring_gaps == []
