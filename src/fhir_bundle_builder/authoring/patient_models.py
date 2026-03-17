"""Typed contracts for the bounded patient authoring foundation."""

from __future__ import annotations

from typing import Any
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from typing_extensions import Annotated

from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.models import PatientContextInput

PatientComplexityLevel = Literal["low", "medium", "high"]
PatientAuthoringItemSourceMode = Literal[
    "direct_extraction",
    "scenario_template",
    "manual_review_edit",
    "agent_structured_output",
]
PatientAdministrativeGender = Literal["female", "male", "other", "unknown"]
PatientAuthoringBuilderMode = Literal["demo_template_authoring", "openai_patient_authoring_agent"]
NonEmptyTrimmedString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


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
    builder_mode: PatientAuthoringBuilderMode
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


class PatientAuthoringAgentBoundedInput(BaseModel):
    """Bounded structured input supplied to the patient authoring agent."""

    authoring_text: str
    complexity_level: PatientComplexityLevel
    scenario_label: str
    history_detail: Literal["brief", "standard", "rich"]
    target_condition_count: int
    target_medication_count: int
    target_allergy_count: int


class PatientAuthoringAgentPatientPayload(BaseModel):
    """Structured patient demographics returned by the patient authoring agent."""

    model_config = ConfigDict(extra="forbid")

    display_name: NonEmptyTrimmedString
    administrative_gender: PatientAdministrativeGender | None = None
    age_years: int | None = Field(default=None, ge=0, le=130)
    birth_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class PatientAuthoringAgentBackgroundFactsPayload(BaseModel):
    """Structured background facts returned by the patient authoring agent."""

    model_config = ConfigDict(extra="forbid")

    residence_text: str | None = None
    smoking_status_text: str | None = None


class PatientAuthoringAgentItemPayload(BaseModel):
    """One authored clinical list item returned by the patient authoring agent."""

    model_config = ConfigDict(extra="forbid")

    display_text: NonEmptyTrimmedString
    source_note: NonEmptyTrimmedString


class PatientAuthoringAgentPayload(BaseModel):
    """Strict structured payload accepted from the patient authoring agent."""

    model_config = ConfigDict(extra="forbid")

    patient: PatientAuthoringAgentPatientPayload
    background_facts: PatientAuthoringAgentBackgroundFactsPayload
    conditions: list[PatientAuthoringAgentItemPayload] = Field(default_factory=list)
    medications: list[PatientAuthoringAgentItemPayload] = Field(default_factory=list)
    allergies: list[PatientAuthoringAgentItemPayload] = Field(default_factory=list)


class PatientAuthoringValidationOutcome(BaseModel):
    """Boundary-validation result for one patient authoring agent invocation."""

    status: Literal["accepted", "rejected"]
    errors: list[str] = Field(default_factory=list)


class PatientAuthoringAgentTrace(BaseModel):
    """Inspectable trace for the bounded patient authoring agent invocation."""

    provider: Literal["openai"]
    model_name: str
    bounded_input: PatientAuthoringAgentBoundedInput
    raw_response_text: str
    parsed_response_json: dict[str, Any] | None = None
    accepted_payload_json: dict[str, Any] | None = None
    status: Literal["accepted", "rejected"]
    rejection_reason: str | None = None
    provider_response_id: str | None = None
