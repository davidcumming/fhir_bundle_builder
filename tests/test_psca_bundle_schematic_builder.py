"""Direct tests for deterministic PS-CA schematic generation."""

from __future__ import annotations

from fhir_bundle_builder.specifications.psca import PscaAssetQuery, PscaAssetRepository
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.models import (
    BundleRequestInput,
    ProfileReferenceInput,
    ProviderContextInput,
    ProviderIdentityInput,
    ProviderOrganizationInput,
    ProviderRoleRelationshipInput,
    SpecificationSelection,
    WorkflowBuildInput,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.request_normalization_builder import (
    build_psca_normalized_request,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.schematic_builder import (
    build_psca_bundle_schematic,
)


def test_psca_bundle_schematic_builder_generates_required_scaffold() -> None:
    repository = PscaAssetRepository()
    normalized_assets = repository.load_foundation_context(PscaAssetQuery())
    normalized_request = _build_normalized_request()

    schematic = build_psca_bundle_schematic(normalized_assets, normalized_request)

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
    assert placeholders["practitionerrole-1"].role == "attending-physician"

    assert "sectionImmunizations:Immunizations" in schematic.omitted_optional_sections
    assert schematic.evidence.selected_example_filename == "Bundle1Example.json"
    assert "composition-ca-ps" in schematic.evidence.used_profile_ids
    assert schematic.evidence.provider_context.normalization_mode == "provider_context_explicit_selection"
    assert schematic.evidence.provider_context.provider_id == "provider-schematic-test"
    assert schematic.evidence.provider_context.selected_organization_id == "org-schematic-test"
    assert schematic.evidence.provider_context.selected_provider_role_relationship_id == "provider-role-schematic-1"
    assert schematic.evidence.provider_context.selected_provider_role_label == "attending-physician"
    assert "explicitly selected provider-role relationship context" in schematic.summary
    assert "explicitly selected provider-role relationship" in schematic.placeholder_note


def test_psca_bundle_schematic_builder_records_legacy_provider_context_fallback() -> None:
    repository = PscaAssetRepository()
    normalized_assets = repository.load_foundation_context(PscaAssetQuery())
    normalized_request = _build_legacy_normalized_request()

    schematic = build_psca_bundle_schematic(normalized_assets, normalized_request)
    placeholders = {placeholder.placeholder_id: placeholder for placeholder in schematic.resource_placeholders}

    assert placeholders["practitionerrole-1"].role == "document-author"
    assert schematic.evidence.provider_context.normalization_mode == "legacy_provider_profile"
    assert schematic.evidence.provider_context.selected_organization_id is None
    assert schematic.evidence.provider_context.selected_provider_role_relationship_id is None
    assert "legacy provider-profile fallback context" in schematic.summary
    assert "legacy provider-profile fallback only" in schematic.placeholder_note


def _build_normalized_request():
    return build_psca_normalized_request(
        WorkflowBuildInput(
            specification=SpecificationSelection(),
            patient_profile=ProfileReferenceInput(
                profile_id="patient-schematic-test",
                display_name="Schematic Test Patient",
            ),
            provider_profile=ProfileReferenceInput(
                profile_id="provider-schematic-test",
                display_name="Schematic Test Provider",
            ),
            provider_context=ProviderContextInput(
                provider=ProviderIdentityInput(
                    provider_id="provider-schematic-test",
                    display_name="Schematic Test Provider",
                    source_type="provider_management",
                ),
                organizations=[
                    ProviderOrganizationInput(
                        organization_id="org-schematic-test",
                        display_name="Schematic Test Organization",
                    )
                ],
                provider_role_relationships=[
                    ProviderRoleRelationshipInput(
                        relationship_id="provider-role-schematic-1",
                        organization_id="org-schematic-test",
                        role_label="attending-physician",
                    )
                ],
                selected_provider_role_relationship_id="provider-role-schematic-1",
            ),
            request=BundleRequestInput(
                request_text="Create a deterministic schematic for testing.",
                scenario_label="pytest-schematic",
            ),
        )
    )


def _build_legacy_normalized_request():
    return build_psca_normalized_request(
        WorkflowBuildInput(
            specification=SpecificationSelection(),
            patient_profile=ProfileReferenceInput(
                profile_id="patient-schematic-test",
                display_name="Schematic Test Patient",
            ),
            provider_profile=ProfileReferenceInput(
                profile_id="provider-schematic-test",
                display_name="Schematic Test Provider",
            ),
            request=BundleRequestInput(
                request_text="Create a deterministic schematic for testing.",
                scenario_label="pytest-schematic-legacy",
            ),
        )
    )
