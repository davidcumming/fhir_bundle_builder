"""Deterministic mapper from authored provider records into workflow-ready provider context."""

from __future__ import annotations

from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.models import (
    ProviderContextInput,
    ProviderIdentityInput,
    ProviderOrganizationInput,
    ProviderRoleRelationshipInput,
)

from .provider_models import ProviderAuthoredRecord, ProviderAuthoringMapResult


def map_authored_provider_to_provider_context(record: ProviderAuthoredRecord) -> ProviderAuthoringMapResult:
    """Map a bounded authored provider record into the current workflow provider-context shape."""

    unmapped_fields: list[str] = []
    if record.professional_facts.administrative_gender is not None:
        unmapped_fields.append("professional_facts.administrative_gender")
    if record.professional_facts.jurisdiction_text is not None:
        unmapped_fields.append("professional_facts.jurisdiction_text")

    specialty_used_for_relationship = (
        record.professional_facts.specialty_or_role_label is not None
        and any(
            relationship.role_label == record.professional_facts.specialty_or_role_label
            for relationship in record.provider_role_relationships
        )
    )
    if record.professional_facts.specialty_or_role_label is not None and not specialty_used_for_relationship:
        unmapped_fields.append("professional_facts.specialty_or_role_label")

    selected_provider_role_relationship_id = record.selected_provider_role_relationship_id
    if selected_provider_role_relationship_id is None and len(record.provider_role_relationships) == 1:
        selected_provider_role_relationship_id = record.provider_role_relationships[0].relationship_id

    provider_context = ProviderContextInput(
        provider=ProviderIdentityInput(
            provider_id=record.provider.provider_id,
            display_name=record.provider.display_name,
            source_type="provider_management",
        ),
        organizations=[
            ProviderOrganizationInput(
                organization_id=organization.organization_id,
                display_name=organization.display_name,
            )
            for organization in record.organizations
        ],
        provider_role_relationships=[
            ProviderRoleRelationshipInput(
                relationship_id=relationship.relationship_id,
                organization_id=relationship.organization_id,
                role_label=relationship.role_label,
            )
            for relationship in record.provider_role_relationships
        ],
        selected_provider_role_relationship_id=selected_provider_role_relationship_id,
    )

    return ProviderAuthoringMapResult(
        source_record_id=record.record_id,
        provider_context=provider_context,
        unmapped_fields=unmapped_fields,
        mapped_organization_count=len(provider_context.organizations),
        mapped_provider_role_relationship_count=len(provider_context.provider_role_relationships),
        has_selected_provider_role_relationship=selected_provider_role_relationship_id is not None,
    )
