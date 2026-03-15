"""Direct tests for mapping authored provider records into workflow provider context."""

from __future__ import annotations

from fhir_bundle_builder.authoring import (
    ProviderAuthoringInput,
    build_provider_authored_record,
    map_authored_provider_to_provider_context,
)


def test_provider_authoring_mapper_maps_explicit_org_and_relationship_into_provider_context() -> None:
    record = build_provider_authored_record(
        ProviderAuthoringInput(
            authoring_text=(
                "The provider's name is Maya Chen. "
                "She is a female oncologist at Fraser Cancer Clinic."
            ),
            scenario_label="pytest-provider-map-rich",
        )
    )

    result = map_authored_provider_to_provider_context(record)

    assert result.source_record_id == record.record_id
    assert result.provider_context.provider.provider_id == record.provider.provider_id
    assert result.provider_context.provider.display_name == "Maya Chen"
    assert [organization.display_name for organization in result.provider_context.organizations] == [
        "Fraser Cancer Clinic"
    ]
    assert [relationship.role_label for relationship in result.provider_context.provider_role_relationships] == [
        "oncologist"
    ]
    assert result.provider_context.selected_provider_role_relationship_id == (
        record.provider_role_relationships[0].relationship_id
    )
    assert result.mapped_organization_count == 1
    assert result.mapped_provider_role_relationship_count == 1
    assert result.has_selected_provider_role_relationship is True
    assert result.unmapped_fields == ["professional_facts.administrative_gender"]


def test_provider_authoring_mapper_keeps_unmapped_professional_facts_explicit_when_no_relationship_exists() -> None:
    record = build_provider_authored_record(
        ProviderAuthoringInput(
            authoring_text="The provider is a female oncologist in BC.",
            scenario_label="pytest-provider-map-thin",
        )
    )

    result = map_authored_provider_to_provider_context(record)

    assert result.provider_context.provider.display_name == "Authored Oncologist"
    assert result.provider_context.organizations == []
    assert result.provider_context.provider_role_relationships == []
    assert result.provider_context.selected_provider_role_relationship_id is None
    assert result.unmapped_fields == [
        "professional_facts.administrative_gender",
        "professional_facts.jurisdiction_text",
        "professional_facts.specialty_or_role_label",
    ]
    assert result.mapped_organization_count == 0
    assert result.mapped_provider_role_relationship_count == 0
    assert result.has_selected_provider_role_relationship is False
