"""Typed contracts for the bounded provider authoring foundation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.models import ProviderContextInput

ProviderAuthoringItemSourceMode = Literal["direct_extraction", "scenario_template", "manual_review_edit"]
ProviderAdministrativeGender = Literal["female", "male", "other", "unknown"]


class ProviderAuthoringInput(BaseModel):
    """Natural-language authoring request for one bounded provider record."""

    authoring_text: str
    scenario_label: str = "provider-authoring-demo"


class ProviderAuthoredIdentity(BaseModel):
    """Structured authored provider identity."""

    provider_id: str
    display_name: str


class ProviderAuthoredProfessionalFacts(BaseModel):
    """Structured authored provider facts not yet fully mapped into workflow inputs."""

    administrative_gender: ProviderAdministrativeGender | None = None
    specialty_or_role_label: str | None = None
    jurisdiction_text: str | None = None


class ProviderAuthoredOrganization(BaseModel):
    """One authored organization explicitly supported by prompt text."""

    organization_id: str
    display_name: str
    source_mode: ProviderAuthoringItemSourceMode
    source_note: str


class ProviderAuthoredRoleRelationship(BaseModel):
    """One authored provider-role relationship explicitly supported by prompt text."""

    relationship_id: str
    organization_id: str
    role_label: str
    source_mode: ProviderAuthoringItemSourceMode
    source_note: str


class ProviderAuthoringGap(BaseModel):
    """One explicit authoring shortfall for the bounded provider slice."""

    gap_code: Literal[
        "missing_named_provider",
        "missing_organization",
        "missing_provider_role_relationship",
    ]
    reason: str


class ProviderAuthoringEvidence(BaseModel):
    """Inspectability fields for how the authored provider record was built."""

    source_authoring_text: str
    builder_mode: Literal["demo_template_authoring"]
    extracted_name: str | None = None
    extracted_gender: ProviderAdministrativeGender | None = None
    extracted_specialty_or_role_label: str | None = None
    extracted_jurisdiction_text: str | None = None
    extracted_organization_name: str | None = None
    applied_scenario_tags: list[str] = Field(default_factory=list)
    display_name_source_mode: ProviderAuthoringItemSourceMode
    display_name_source_note: str


class ProviderAuthoredRecord(BaseModel):
    """Structured authored provider record produced upstream of bundle generation."""

    record_id: str
    scenario_label: str
    provider: ProviderAuthoredIdentity
    professional_facts: ProviderAuthoredProfessionalFacts = Field(default_factory=ProviderAuthoredProfessionalFacts)
    organizations: list[ProviderAuthoredOrganization] = Field(default_factory=list)
    provider_role_relationships: list[ProviderAuthoredRoleRelationship] = Field(default_factory=list)
    selected_provider_role_relationship_id: str | None = None
    unresolved_authoring_gaps: list[ProviderAuthoringGap] = Field(default_factory=list)
    authoring_evidence: ProviderAuthoringEvidence


class ProviderAuthoringMapResult(BaseModel):
    """Result of mapping an authored provider record into workflow-ready provider context."""

    source_record_id: str
    provider_context: ProviderContextInput
    unmapped_fields: list[str] = Field(default_factory=list)
    mapped_organization_count: int
    mapped_provider_role_relationship_count: int
    has_selected_provider_role_relationship: bool
