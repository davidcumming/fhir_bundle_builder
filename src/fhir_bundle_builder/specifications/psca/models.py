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


class PscaNormalizedAssetContext(BaseModel):
    """First normalized workflow-usable PS-CA asset context."""

    package_summary: PscaPackageSummary
    workflow_profile_inventory: list[PscaWorkflowProfileSummary]
    selected_profiles: PscaSelectedProfiles
    example_inventory: list[PscaExampleSummary]
    selected_bundle_example: PscaBundleExampleSummary
    normalization_level: PscaNormalizationLevel = "foundation"
    source_refs: list[str] = Field(default_factory=list)
