"""Direct tests for the bounded provider authoring foundation."""

from __future__ import annotations

from fhir_bundle_builder.authoring import ProviderAuthoringInput, build_provider_authored_record


def test_provider_authoring_builder_extracts_named_provider_with_explicit_org_and_role() -> None:
    prompt = (
        "The provider's name is Maya Chen. "
        "She is a female oncologist at Fraser Cancer Clinic."
    )

    record = build_provider_authored_record(
        ProviderAuthoringInput(
            authoring_text=prompt,
            scenario_label="pytest-provider-authoring-rich",
        )
    )

    assert record.provider.display_name == "Maya Chen"
    assert record.provider.provider_id.startswith("maya-chen-")
    assert record.professional_facts.administrative_gender == "female"
    assert record.professional_facts.specialty_or_role_label == "oncologist"
    assert len(record.organizations) == 1
    assert record.organizations[0].display_name == "Fraser Cancer Clinic"
    assert record.organizations[0].source_mode == "direct_extraction"
    assert len(record.provider_role_relationships) == 1
    assert record.provider_role_relationships[0].organization_id == record.organizations[0].organization_id
    assert record.provider_role_relationships[0].role_label == "oncologist"
    assert record.selected_provider_role_relationship_id == record.provider_role_relationships[0].relationship_id
    assert record.authoring_evidence.display_name_source_mode == "direct_extraction"
    assert "role:oncologist" in record.authoring_evidence.applied_scenario_tags
    assert "organization_explicit" in record.authoring_evidence.applied_scenario_tags
    assert record.unresolved_authoring_gaps == []


def test_provider_authoring_builder_preserves_role_and_location_without_inventing_org_or_relationship() -> None:
    prompt = "The provider is a female oncologist in BC."

    first = build_provider_authored_record(
        ProviderAuthoringInput(
            authoring_text=prompt,
            scenario_label="pytest-provider-authoring-thin",
        )
    )
    second = build_provider_authored_record(
        ProviderAuthoringInput(
            authoring_text=prompt,
            scenario_label="pytest-provider-authoring-thin",
        )
    )

    assert first.record_id == second.record_id
    assert first.provider.provider_id == second.provider.provider_id
    assert first.provider.display_name == "Authored Oncologist"
    assert first.professional_facts.administrative_gender == "female"
    assert first.professional_facts.specialty_or_role_label == "oncologist"
    assert first.professional_facts.jurisdiction_text == "BC"
    assert first.organizations == []
    assert first.provider_role_relationships == []
    assert first.selected_provider_role_relationship_id is None
    assert first.authoring_evidence.display_name_source_mode == "scenario_template"
    assert sorted(gap.gap_code for gap in first.unresolved_authoring_gaps) == [
        "missing_named_provider",
        "missing_organization",
        "missing_provider_role_relationship",
    ]
