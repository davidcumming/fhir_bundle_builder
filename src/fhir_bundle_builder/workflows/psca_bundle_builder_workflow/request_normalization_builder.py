"""Deterministic PS-CA request normalization helpers."""

from __future__ import annotations

from .models import (
    NormalizedBuildRequest,
    NormalizedProviderContext,
    ProfileReferenceInput,
    ProviderContextInput,
    ProviderIdentityInput,
    ProviderOrganizationInput,
    ProviderRoleRelationshipInput,
    WorkflowBuildInput,
    WorkflowDefaults,
)


def build_psca_normalized_request(message: WorkflowBuildInput) -> NormalizedBuildRequest:
    """Normalize the top-level workflow request into deterministic workflow inputs."""

    provider_context = _normalize_provider_context(
        message.provider_context,
        message.provider_profile,
    )
    provider_profile = ProfileReferenceInput(
        profile_id=provider_context.provider.provider_id,
        display_name=provider_context.provider.display_name,
        source_type=provider_context.provider.source_type,
    )

    return NormalizedBuildRequest(
        stage_id="request_normalization",
        status="placeholder_complete",
        summary="Validated the top-level workflow input and applied deterministic request-normalization defaults.",
        placeholder_note="This stage now normalizes structured provider context deterministically but still defers deeper request interpretation and patient-specific provider-context selection.",
        source_refs=[],
        specification=message.specification,
        patient_profile=message.patient_profile,
        provider_profile=provider_profile,
        provider_context=provider_context,
        request=message.request,
        workflow_defaults=WorkflowDefaults(
            bundle_type="document",
            specification_mode="normalized-asset-foundation",
            validation_mode="foundational_dual_channel",
            resource_construction_mode="deterministic_content_enriched_foundation",
        ),
        run_label=f"{message.request.scenario_label}:{message.specification.package_id}:{message.specification.version}",
    )


def _normalize_provider_context(
    provider_context: ProviderContextInput | None,
    provider_profile: ProfileReferenceInput,
) -> NormalizedProviderContext:
    if provider_context is None:
        return NormalizedProviderContext(
            provider=ProviderIdentityInput(
                provider_id=provider_profile.profile_id,
                display_name=provider_profile.display_name,
                source_type=provider_profile.source_type,
            ),
            organizations=[],
            provider_role_relationships=[],
            selected_provider_role_relationship=None,
            selected_organization=None,
            normalization_mode="legacy_provider_profile",
        )

    organizations_by_id = {
        organization.organization_id: organization
        for organization in provider_context.organizations
    }
    selected_relationship = _select_provider_role_relationship(provider_context)
    selected_organization = None
    normalization_mode: str = "provider_context_explicit_selection"
    if selected_relationship is None:
        normalization_mode = "provider_context_single_relationship"
    else:
        selected_organization = organizations_by_id.get(selected_relationship.organization_id)
        if selected_organization is None:
            raise ValueError(
                "Selected provider-role relationship references an unknown organization: "
                f"{selected_relationship.organization_id}."
            )
        normalization_mode = (
            "provider_context_explicit_selection"
            if provider_context.selected_provider_role_relationship_id is not None
            else "provider_context_single_relationship"
        )

    return NormalizedProviderContext(
        provider=ProviderIdentityInput.model_validate(provider_context.provider.model_dump()),
        organizations=[
            ProviderOrganizationInput.model_validate(organization.model_dump())
            for organization in provider_context.organizations
        ],
        provider_role_relationships=[
            ProviderRoleRelationshipInput.model_validate(relationship.model_dump())
            for relationship in provider_context.provider_role_relationships
        ],
        selected_provider_role_relationship=(
            ProviderRoleRelationshipInput.model_validate(selected_relationship.model_dump())
            if selected_relationship is not None
            else None
        ),
        selected_organization=(
            ProviderOrganizationInput.model_validate(selected_organization.model_dump())
            if selected_organization is not None
            else None
        ),
        normalization_mode=normalization_mode,
    )


def _select_provider_role_relationship(
    provider_context: ProviderContextInput,
) -> ProviderRoleRelationshipInput | None:
    relationships = provider_context.provider_role_relationships
    selected_relationship_id = provider_context.selected_provider_role_relationship_id
    if selected_relationship_id is not None:
        for relationship in relationships:
            if relationship.relationship_id == selected_relationship_id:
                return relationship
        raise ValueError(
            "Selected provider-role relationship id was not found in provider_context: "
            f"{selected_relationship_id}."
        )

    if not relationships:
        return None
    if len(relationships) == 1:
        return relationships[0]

    raise ValueError(
        "provider_context includes multiple provider-role relationships but no explicit "
        "selected_provider_role_relationship_id."
    )
