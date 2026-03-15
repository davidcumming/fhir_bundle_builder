"""Direct tests for mapping authored patient records into workflow patient context."""

from __future__ import annotations

from fhir_bundle_builder.authoring import (
    PatientAuthoringInput,
    build_patient_authored_record,
    map_authored_patient_to_patient_context,
)


def test_patient_authoring_mapper_maps_identity_and_lists_into_patient_context() -> None:
    record = build_patient_authored_record(
        PatientAuthoringInput(
            authoring_text=(
                "The patient's name is Jane River. She is a female age 58 who lives in Calgary, Alberta. "
                "She has diabetes and hypertension, takes metformin and lisinopril, and has a peanut allergy."
            ),
            complexity_level="medium",
            scenario_label="pytest-patient-map-jane",
        )
    )

    result = map_authored_patient_to_patient_context(record)

    assert result.source_record_id == record.record_id
    assert result.patient_context.patient.patient_id == record.patient.patient_id
    assert result.patient_context.patient.display_name == "Jane River"
    assert result.patient_context.patient.administrative_gender == "female"
    assert [condition.display_text for condition in result.patient_context.conditions] == [
        "Type 2 diabetes mellitus",
        "Hypertension",
    ]
    assert [medication.display_text for medication in result.patient_context.medications] == [
        "Metformin 500 MG oral tablet",
        "Lisinopril 10 MG oral tablet",
    ]
    assert [allergy.display_text for allergy in result.patient_context.allergies] == [
        "Peanut allergy",
    ]
    assert result.mapped_condition_count == 2
    assert result.mapped_medication_count == 2
    assert result.mapped_allergy_count == 1
    assert result.unmapped_fields == [
        "patient.age_years",
        "background_facts.residence_text",
    ]


def test_patient_authoring_mapper_records_unmapped_background_facts_explicitly() -> None:
    record = build_patient_authored_record(
        PatientAuthoringInput(
            authoring_text=(
                "The patient is a male of age 62 that lives in Edmonton, Alberta. "
                "They are life long smokers and the man's name is Jack Fulber."
            ),
            complexity_level="low",
            scenario_label="pytest-patient-map-jack",
        )
    )

    result = map_authored_patient_to_patient_context(record)

    assert result.patient_context.patient.display_name == "Jack Fulber"
    assert result.patient_context.patient.administrative_gender == "male"
    assert result.unmapped_fields == [
        "patient.age_years",
        "background_facts.residence_text",
        "background_facts.smoking_status_text",
    ]
