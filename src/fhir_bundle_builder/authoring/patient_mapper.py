"""Deterministic mapper from authored patient records into workflow-ready patient context."""

from __future__ import annotations

from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.models import (
    PatientAllergyInput,
    PatientConditionInput,
    PatientContextInput,
    PatientIdentityInput,
    PatientMedicationInput,
)

from .patient_models import PatientAuthoredRecord, PatientAuthoringMapResult


def map_authored_patient_to_patient_context(record: PatientAuthoredRecord) -> PatientAuthoringMapResult:
    """Map a bounded authored patient record into the current workflow patient-context shape."""

    unmapped_fields: list[str] = []
    if record.patient.age_years is not None and record.patient.birth_date is None:
        unmapped_fields.append("patient.age_years")
    if record.background_facts.residence_text is not None:
        unmapped_fields.append("background_facts.residence_text")
    if record.background_facts.smoking_status_text is not None:
        unmapped_fields.append("background_facts.smoking_status_text")

    patient_context = PatientContextInput(
        patient=PatientIdentityInput(
            patient_id=record.patient.patient_id,
            display_name=record.patient.display_name,
            source_type="patient_management",
            administrative_gender=record.patient.administrative_gender,
            birth_date=record.patient.birth_date,
        ),
        conditions=[
            PatientConditionInput(
                condition_id=condition.condition_id,
                display_text=condition.display_text,
            )
            for condition in record.conditions
        ],
        medications=[
            PatientMedicationInput(
                medication_id=medication.medication_id,
                display_text=medication.display_text,
            )
            for medication in record.medications
        ],
        allergies=[
            PatientAllergyInput(
                allergy_id=allergy.allergy_id,
                display_text=allergy.display_text,
            )
            for allergy in record.allergies
        ],
    )

    return PatientAuthoringMapResult(
        source_record_id=record.record_id,
        patient_context=patient_context,
        unmapped_fields=unmapped_fields,
        mapped_condition_count=len(patient_context.conditions),
        mapped_medication_count=len(patient_context.medications),
        mapped_allergy_count=len(patient_context.allergies),
    )
