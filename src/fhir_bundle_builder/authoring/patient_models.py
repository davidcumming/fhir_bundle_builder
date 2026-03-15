"""Typed contracts for the bounded patient authoring foundation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.models import PatientContextInput

PatientComplexityLevel = Literal["low", "medium", "high"]
PatientAuthoringItemSourceMode = Literal["direct_extraction", "scenario_template", "manual_review_edit"]
PatientAdministrativeGender = Literal["female", "male", "other", "unknown"]


class PatientAuthoringInput(BaseModel):
    """Natural-language authoring request for one bounded patient record."""

    authoring_text: str
    complexity_level: PatientComplexityLevel
    scenario_label: str = "patient-authoring-demo"


class PatientComplexityPolicy(BaseModel):
    """Fixed bounded richness policy for the first authoring slice."""

    complexity_level: PatientComplexityLevel
    history_detail: Literal["brief", "standard", "rich"]
    target_condition_count: int
    target_medication_count: int
    target_allergy_count: int


class PatientAuthoredIdentity(BaseModel):
    """Structured authored patient identity and demographics."""

    patient_id: str
    display_name: str
    administrative_gender: PatientAdministrativeGender | None = None
    age_years: int | None = None
    birth_date: str | None = None


class PatientAuthoredBackgroundFacts(BaseModel):
    """Structured authored patient facts not yet mapped into the bundle workflow."""

    residence_text: str | None = None
    smoking_status_text: str | None = None


class PatientAuthoredCondition(BaseModel):
    """One authored patient condition."""

    condition_id: str
    display_text: str
    source_mode: PatientAuthoringItemSourceMode
    source_note: str


class PatientAuthoredMedication(BaseModel):
    """One authored patient medication."""

    medication_id: str
    display_text: str
    source_mode: PatientAuthoringItemSourceMode
    source_note: str


class PatientAuthoredAllergy(BaseModel):
    """One authored patient allergy."""

    allergy_id: str
    display_text: str
    source_mode: PatientAuthoringItemSourceMode
    source_note: str


class PatientAuthoringGap(BaseModel):
    """One explicit authored-content shortfall against the bounded complexity policy."""

    area: Literal["conditions", "medications", "allergies"]
    target_count: int
    authored_count: int
    reason: str


class PatientAuthoringEvidence(BaseModel):
    """Inspectability fields for how the authored patient record was built."""

    source_authoring_text: str
    builder_mode: Literal["demo_template_authoring"]
    extracted_name: str | None = None
    extracted_gender: PatientAdministrativeGender | None = None
    extracted_age_years: int | None = None
    extracted_birth_date: str | None = None
    extracted_residence_text: str | None = None
    extracted_smoking_status_text: str | None = None
    applied_scenario_tags: list[str] = Field(default_factory=list)


class PatientAuthoredRecord(BaseModel):
    """Structured authored patient record produced upstream of bundle generation."""

    record_id: str
    scenario_label: str
    patient: PatientAuthoredIdentity
    background_facts: PatientAuthoredBackgroundFacts = Field(default_factory=PatientAuthoredBackgroundFacts)
    conditions: list[PatientAuthoredCondition] = Field(default_factory=list)
    medications: list[PatientAuthoredMedication] = Field(default_factory=list)
    allergies: list[PatientAuthoredAllergy] = Field(default_factory=list)
    complexity_policy_applied: PatientComplexityPolicy
    unresolved_authoring_gaps: list[PatientAuthoringGap] = Field(default_factory=list)
    authoring_evidence: PatientAuthoringEvidence


class PatientAuthoringMapResult(BaseModel):
    """Result of mapping an authored patient record into workflow-ready patient context."""

    source_record_id: str
    patient_context: PatientContextInput
    unmapped_fields: list[str] = Field(default_factory=list)
    mapped_condition_count: int
    mapped_medication_count: int
    mapped_allergy_count: int
