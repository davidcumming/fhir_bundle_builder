"""Direct tests for the bounded patient authoring foundation."""

from __future__ import annotations

from fhir_bundle_builder.authoring import (
    PatientAuthoringInput,
    build_patient_authored_record,
    get_patient_complexity_policy,
)


def test_patient_authoring_builder_exposes_fixed_complexity_policies() -> None:
    low = get_patient_complexity_policy("low")
    medium = get_patient_complexity_policy("medium")
    high = get_patient_complexity_policy("high")

    assert (low.history_detail, low.target_condition_count, low.target_medication_count, low.target_allergy_count) == (
        "brief",
        1,
        1,
        0,
    )
    assert (
        medium.history_detail,
        medium.target_condition_count,
        medium.target_medication_count,
        medium.target_allergy_count,
    ) == ("standard", 2, 2, 1)
    assert (high.history_detail, high.target_condition_count, high.target_medication_count, high.target_allergy_count) == (
        "rich",
        3,
        3,
        2,
    )


def test_patient_authoring_builder_extracts_demographics_and_bounded_condition_from_prompt() -> None:
    prompt = (
        "The patient is a male of age 62 that lives in Edmonton, Alberta. "
        "They are life long smokers and upon seeing their family doctor, the family doctor is suspicious of lung cancer. "
        "The man's name is Jack Fulber."
    )

    record = build_patient_authored_record(
        PatientAuthoringInput(
            authoring_text=prompt,
            complexity_level="medium",
            scenario_label="pytest-patient-authoring-jack",
        )
    )

    assert record.patient.display_name == "Jack Fulber"
    assert record.patient.patient_id.startswith("jack-fulber-")
    assert record.patient.administrative_gender == "male"
    assert record.patient.age_years == 62
    assert record.background_facts.residence_text == "Edmonton, Alberta"
    assert record.background_facts.smoking_status_text == "Lifelong smoker"
    assert [condition.display_text for condition in record.conditions] == ["Possible lung cancer"]
    assert record.conditions[0].source_mode == "scenario_template"
    assert "possible_lung_cancer" in record.authoring_evidence.applied_scenario_tags
    assert "smoking_history" in record.authoring_evidence.applied_scenario_tags
    assert [gap.area for gap in record.unresolved_authoring_gaps] == ["conditions", "medications", "allergies"]


def test_patient_authoring_builder_extracts_bounded_lists_and_is_deterministic() -> None:
    prompt = (
        "The patient's name is Jane River. She is a female age 58 who lives in Calgary, Alberta. "
        "She has diabetes and hypertension, takes metformin and lisinopril, and has a peanut allergy and a latex allergy."
    )

    first = build_patient_authored_record(
        PatientAuthoringInput(
            authoring_text=prompt,
            complexity_level="high",
            scenario_label="pytest-patient-authoring-jane",
        )
    )
    second = build_patient_authored_record(
        PatientAuthoringInput(
            authoring_text=prompt,
            complexity_level="high",
            scenario_label="pytest-patient-authoring-jane",
        )
    )

    assert first.record_id == second.record_id
    assert first.patient.patient_id == second.patient.patient_id
    assert [condition.display_text for condition in first.conditions] == [
        "Type 2 diabetes mellitus",
        "Hypertension",
    ]
    assert [medication.display_text for medication in first.medications] == [
        "Metformin 500 MG oral tablet",
        "Lisinopril 10 MG oral tablet",
    ]
    assert [allergy.display_text for allergy in first.allergies] == [
        "Peanut allergy",
        "Latex allergy",
    ]
    assert all(item.source_mode == "direct_extraction" for item in first.medications)
    assert [gap.area for gap in first.unresolved_authoring_gaps] == ["conditions", "medications"]
