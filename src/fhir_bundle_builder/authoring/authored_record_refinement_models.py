"""Bounded structured review/edit contracts for authored patient and provider records."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .patient_models import (
    PatientAdministrativeGender,
    PatientAuthoredRecord,
)
from .provider_models import (
    ProviderAdministrativeGender,
    ProviderAuthoredRecord,
)


class PatientAuthoredRecordReviewEditInput(BaseModel):
    """Bounded structured edits for one authored patient record."""

    display_name: str | None = None
    administrative_gender: PatientAdministrativeGender | None = None
    age_years: int | None = None
    birth_date: str | None = None
    residence_text: str | None = None
    smoking_status_text: str | None = None
    condition_display_texts: list[str] | None = None
    medication_display_texts: list[str] | None = None
    allergy_display_texts: list[str] | None = None


class ProviderAuthoredRecordReviewEditInput(BaseModel):
    """Bounded structured edits for one authored provider record."""

    display_name: str | None = None
    administrative_gender: ProviderAdministrativeGender | None = None
    specialty_or_role_label: str | None = None
    jurisdiction_text: str | None = None
    organization_display_name: str | None = None
    relationship_role_label: str | None = None
    selected_relationship_active: bool | None = None


class PatientAuthoredRecordRefinementResult(BaseModel):
    """Inspectable result of applying bounded edits to one authored patient record."""

    source_record_id: str
    refined_record_id: str
    edits_applied: bool
    edited_field_paths: list[str] = Field(default_factory=list)
    original_record: PatientAuthoredRecord
    refined_record: PatientAuthoredRecord


class ProviderAuthoredRecordRefinementResult(BaseModel):
    """Inspectable result of applying bounded edits to one authored provider record."""

    source_record_id: str
    refined_record_id: str
    edits_applied: bool
    edited_field_paths: list[str] = Field(default_factory=list)
    original_record: ProviderAuthoredRecord
    refined_record: ProviderAuthoredRecord
