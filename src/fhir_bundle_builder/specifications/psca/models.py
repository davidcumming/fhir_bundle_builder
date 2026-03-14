"""Typed models for PS-CA asset retrieval and normalization."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

PscaNormalizationLevel = Literal["foundation"]
PscaWorkflowProfileRole = Literal[
    "bundle",
    "composition",
    "patient",
    "practitioner",
    "practitioner_role",
    "organization",
]
PscaCompositionSectionKey = Literal[
    "medications",
    "allergies",
    "problems",
    "procedures_history",
    "immunizations",
    "medical_devices",
    "results",
    "vital_signs",
    "past_illness_history",
    "functional_status",
    "plan_of_care",
    "social_history",
    "pregnancy_history",
    "advance_directives",
    "family_history",
    "patient_story",
]


class PscaAssetQuery(BaseModel):
    """Inputs required for the initial PS-CA asset retrieval boundary."""

    package_id: str = Field(default="ca.infoway.io.psca")
    version: str = Field(default="2.1.1-DFT")
    include_example_inventory: bool = Field(default=True)
    selected_example_bundle_filename: str = Field(default="Bundle1Example.json")


class PscaPackageSummary(BaseModel):
    """Normalized summary of the PS-CA package metadata."""

    package_id: str
    version: str
    fhir_version: str
    canonical_url: str
    index_entry_count: int
    structure_definition_count: int
    example_count: int
    package_root: str


class PscaWorkflowProfileSummary(BaseModel):
    """Workflow-scoped summary of a foundational PS-CA profile."""

    role: PscaWorkflowProfileRole
    profile_id: str
    resource_type: str
    url: str
    title: str
    base_definition: str
    snapshot_element_count: int
    differential_element_count: int
    must_support_count: int
    source_filename: str


class PscaSelectedProfiles(BaseModel):
    """Foundational profile set needed by the current workflow slices."""

    bundle: PscaWorkflowProfileSummary
    composition: PscaWorkflowProfileSummary
    patient: PscaWorkflowProfileSummary
    practitioner: PscaWorkflowProfileSummary
    practitioner_role: PscaWorkflowProfileSummary
    organization: PscaWorkflowProfileSummary


class PscaExampleSummary(BaseModel):
    """Minimal example inventory entry."""

    filename: str
    resource_type: str
    resource_id: str | None = None


class PscaBundleExampleSummary(BaseModel):
    """Normalized summary of a selected PS-CA bundle example."""

    filename: str
    bundle_type: str
    entry_resource_types: list[str]
    composition_section_titles: list[str]
    composition_subject_resource_type: str | None = None
    composition_author_resource_types: list[str] = Field(default_factory=list)
    sections: list["PscaBundleExampleSectionSummary"] = Field(default_factory=list)


class PscaBundleExampleSectionSummary(BaseModel):
    """Normalized summary of one Composition section inside a bundle example."""

    title: str
    loinc_code: str | None = None
    entry_resource_types: list[str] = Field(default_factory=list)


class PscaCompositionSectionDefinitionSummary(BaseModel):
    """Normalized summary of one PS-CA Composition section definition."""

    section_key: PscaCompositionSectionKey
    slice_name: str
    title: str
    loinc_code: str
    required: bool
    allowed_entry_resource_types: list[str] = Field(default_factory=list)
    source_profile_id: str


class PscaNormalizedAssetContext(BaseModel):
    """First normalized workflow-usable PS-CA asset context."""

    package_summary: PscaPackageSummary
    workflow_profile_inventory: list[PscaWorkflowProfileSummary]
    selected_profiles: PscaSelectedProfiles
    composition_section_definitions: list[PscaCompositionSectionDefinitionSummary]
    example_inventory: list[PscaExampleSummary]
    selected_bundle_example: PscaBundleExampleSummary
    normalization_level: PscaNormalizationLevel = "foundation"
    source_refs: list[str] = Field(default_factory=list)
