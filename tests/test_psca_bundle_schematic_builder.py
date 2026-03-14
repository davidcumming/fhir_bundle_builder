"""Direct tests for deterministic PS-CA schematic generation."""

from __future__ import annotations

from fhir_bundle_builder.specifications.psca import PscaAssetQuery, PscaAssetRepository
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.schematic_builder import (
    build_psca_bundle_schematic,
)


def test_psca_bundle_schematic_builder_generates_required_scaffold() -> None:
    repository = PscaAssetRepository()
    normalized_assets = repository.load_foundation_context(PscaAssetQuery())

    schematic = build_psca_bundle_schematic(normalized_assets)

    assert schematic.generation_basis == "deterministic_psca_foundation_rules"
    assert schematic.bundle_scaffold.bundle_type == "document"
    assert schematic.bundle_scaffold.required_entry_placeholder_ids == ["composition-1", "patient-1"]
    assert schematic.composition_scaffold.expected_type_code == "60591-5"

    section_scaffolds = {section.section_key: section for section in schematic.section_scaffolds}
    assert set(section_scaffolds) == {"medications", "allergies", "problems"}
    assert section_scaffolds["medications"].entry_placeholder_ids == ["medicationrequest-1"]
    assert section_scaffolds["allergies"].entry_placeholder_ids == ["allergyintolerance-1"]
    assert section_scaffolds["problems"].entry_placeholder_ids == ["condition-1"]

    placeholders = {placeholder.placeholder_id: placeholder for placeholder in schematic.resource_placeholders}
    assert set(placeholders) == {
        "patient-1",
        "practitioner-1",
        "organization-1",
        "practitionerrole-1",
        "condition-1",
        "medicationrequest-1",
        "allergyintolerance-1",
        "composition-1",
    }
    assert placeholders["composition-1"].profile_url == normalized_assets.selected_profiles.composition.url
    assert placeholders["medicationrequest-1"].section_keys == ["medications"]
    assert placeholders["condition-1"].profile_url == (
        "http://fhir.infoway-inforoute.ca/io/psca/StructureDefinition/condition-ca-ps"
    )

    relationships = {relationship.relationship_id: relationship for relationship in schematic.relationships}
    assert relationships["composition-subject"].target_id == "patient-1"
    assert relationships["composition-author"].target_id == "practitionerrole-1"
    assert relationships["practitionerrole-practitioner"].target_id == "practitioner-1"
    assert relationships["practitionerrole-organization"].target_id == "organization-1"
    assert relationships["section-entry-medications"].target_id == "medicationrequest-1"

    assert "sectionImmunizations:Immunizations" in schematic.omitted_optional_sections
    assert schematic.evidence.selected_example_filename == "Bundle1Example.json"
    assert "composition-ca-ps" in schematic.evidence.used_profile_ids
