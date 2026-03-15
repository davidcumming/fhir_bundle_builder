"""Deterministic PS-CA schematic generation from normalized assets."""

from __future__ import annotations

from fhir_bundle_builder.specifications.psca import (
    PscaBundleExampleSectionSummary,
    PscaCompositionSectionDefinitionSummary,
    PscaNormalizedAssetContext,
)

from .models import (
    BundleScaffold,
    BundleSchematic,
    CompositionScaffold,
    NormalizedBuildRequest,
    ResourcePlaceholder,
    SchematicEvidence,
    SchematicProviderContextEvidence,
    SchematicRelationship,
    SectionScaffold,
)

_REQUIRED_SECTION_KEYS = ("medications", "allergies", "problems")
_RESOURCE_PROFILE_METADATA: dict[str, tuple[str, str]] = {
    "MedicationRequest": (
        "medicationrequest-ca-ps",
        "http://fhir.infoway-inforoute.ca/io/psca/StructureDefinition/medicationrequest-ca-ps",
    ),
    "MedicationStatement": (
        "medicationstatement-ca-ps",
        "http://fhir.infoway-inforoute.ca/io/psca/StructureDefinition/medicationstatement-ca-ps",
    ),
    "AllergyIntolerance": (
        "allergyintolerance-ca-ps",
        "http://fhir.infoway-inforoute.ca/io/psca/StructureDefinition/allergyintolerance-ca-ps",
    ),
    "Condition": (
        "condition-ca-ps",
        "http://fhir.infoway-inforoute.ca/io/psca/StructureDefinition/condition-ca-ps",
    ),
}


def build_psca_bundle_schematic(
    normalized_assets: PscaNormalizedAssetContext,
    normalized_request: NormalizedBuildRequest,
) -> BundleSchematic:
    """Build the first real PS-CA schematic artifact from normalized assets."""

    section_definitions = {section.section_key: section for section in normalized_assets.composition_section_definitions}
    required_sections = [_require_section_definition(section_definitions, key) for key in _REQUIRED_SECTION_KEYS]
    example_sections_by_code = {
        section.loinc_code: section for section in normalized_assets.selected_bundle_example.sections if section.loinc_code
    }

    if normalized_assets.selected_bundle_example.composition_subject_resource_type != "Patient":
        raise ValueError("Selected example bundle does not expose a Composition.subject reference to Patient.")

    author_resource_types = normalized_assets.selected_bundle_example.composition_author_resource_types
    if "PractitionerRole" not in author_resource_types:
        raise ValueError("Selected example bundle does not expose the expected Composition.author PractitionerRole pattern.")

    example_entry_types = normalized_assets.selected_bundle_example.entry_resource_types
    for required_type in ("PractitionerRole", "Practitioner", "Organization"):
        if required_type not in example_entry_types:
            raise ValueError(
                f"Selected example bundle does not contain the required author-support resource type '{required_type}'."
            )

    bundle_profile = normalized_assets.selected_profiles.bundle
    composition_profile = normalized_assets.selected_profiles.composition
    patient_profile = normalized_assets.selected_profiles.patient
    practitioner_profile = normalized_assets.selected_profiles.practitioner
    practitioner_role_profile = normalized_assets.selected_profiles.practitioner_role
    organization_profile = normalized_assets.selected_profiles.organization
    provider_context_evidence = _provider_context_evidence(normalized_request)
    provider_context_summary = _provider_context_summary(provider_context_evidence.normalization_mode)
    provider_context_note = _provider_context_note(provider_context_evidence.normalization_mode)
    practitioner_role_label = provider_context_evidence.selected_provider_role_label or "document-author"

    section_resource_placeholders: list[ResourcePlaceholder] = []
    section_scaffolds: list[SectionScaffold] = []
    used_profile_ids = [
        bundle_profile.profile_id,
        composition_profile.profile_id,
        patient_profile.profile_id,
        practitioner_role_profile.profile_id,
        practitioner_profile.profile_id,
        organization_profile.profile_id,
    ]

    for section_definition in required_sections:
        example_section = example_sections_by_code.get(section_definition.loinc_code)
        selected_resource_type = _select_section_resource_type(section_definition, example_section)
        selected_profile_id, selected_profile_url = _RESOURCE_PROFILE_METADATA[selected_resource_type]
        if selected_profile_id not in used_profile_ids:
            used_profile_ids.append(selected_profile_id)

        placeholder = ResourcePlaceholder(
            placeholder_id=f"{selected_resource_type.lower()}-1",
            resource_type=selected_resource_type,
            role=f"{section_definition.section_key}-section-entry",
            profile_url=selected_profile_url,
            required=True,
            section_keys=[section_definition.section_key],
            required_later_fields=["identifier", "clinical content"],
        )
        section_resource_placeholders.append(placeholder)
        section_scaffolds.append(
            SectionScaffold(
                section_key=section_definition.section_key,
                slice_name=section_definition.slice_name,
                title=_select_section_title(section_definition, example_section),
                loinc_code=section_definition.loinc_code,
                required=section_definition.required,
                allowed_resource_types=section_definition.allowed_entry_resource_types,
                entry_placeholder_ids=[placeholder.placeholder_id],
            )
        )

    resource_placeholders = [
        ResourcePlaceholder(
            placeholder_id="patient-1",
            resource_type="Patient",
            role="document-subject",
            profile_url=patient_profile.url,
            required=True,
            required_later_fields=["identifier", "name"],
        ),
        ResourcePlaceholder(
            placeholder_id="practitioner-1",
            resource_type="Practitioner",
            role="author-practitioner",
            profile_url=practitioner_profile.url,
            required=True,
            required_later_fields=["identifier", "name"],
        ),
        ResourcePlaceholder(
            placeholder_id="organization-1",
            resource_type="Organization",
            role="author-organization",
            profile_url=organization_profile.url,
            required=True,
            required_later_fields=["identifier", "name"],
        ),
        ResourcePlaceholder(
            placeholder_id="practitionerrole-1",
            resource_type="PractitionerRole",
            role=practitioner_role_label,
            profile_url=practitioner_role_profile.url,
            required=True,
            required_later_fields=["practitioner", "organization"],
        ),
        *section_resource_placeholders,
        ResourcePlaceholder(
            placeholder_id="composition-1",
            resource_type="Composition",
            role="document-composition",
            profile_url=composition_profile.url,
            required=True,
            required_later_fields=["status", "title", "date", "author", "subject"],
        ),
    ]

    relationships = [
        SchematicRelationship(
            relationship_id="bundle-entry-composition",
            relationship_type="bundle_entry",
            source_id="bundle",
            target_id="composition-1",
            description="Bundle scaffold includes the required Composition entry.",
        ),
        SchematicRelationship(
            relationship_id="bundle-entry-patient",
            relationship_type="bundle_entry",
            source_id="bundle",
            target_id="patient-1",
            description="Bundle scaffold includes the required Patient entry.",
        ),
        SchematicRelationship(
            relationship_id="bundle-entry-practitionerrole",
            relationship_type="bundle_entry",
            source_id="bundle",
            target_id="practitionerrole-1",
            description="Bundle scaffold includes the author PractitionerRole placeholder.",
        ),
        SchematicRelationship(
            relationship_id="bundle-entry-practitioner",
            relationship_type="bundle_entry",
            source_id="bundle",
            target_id="practitioner-1",
            description="Bundle scaffold includes the supporting Practitioner placeholder.",
        ),
        SchematicRelationship(
            relationship_id="bundle-entry-organization",
            relationship_type="bundle_entry",
            source_id="bundle",
            target_id="organization-1",
            description="Bundle scaffold includes the supporting Organization placeholder.",
        ),
        SchematicRelationship(
            relationship_id="composition-subject",
            relationship_type="composition_subject",
            source_id="composition-1",
            target_id="patient-1",
            reference_path="Composition.subject",
            description="Composition scaffold points to the Patient placeholder as its subject.",
        ),
        SchematicRelationship(
            relationship_id="composition-author",
            relationship_type="composition_author",
            source_id="composition-1",
            target_id="practitionerrole-1",
            reference_path="Composition.author",
            description="Composition scaffold points to PractitionerRole as the initial author pattern.",
        ),
        SchematicRelationship(
            relationship_id="practitionerrole-practitioner",
            relationship_type="practitioner_role_practitioner",
            source_id="practitionerrole-1",
            target_id="practitioner-1",
            reference_path="PractitionerRole.practitioner",
            description="PractitionerRole placeholder links to the supporting Practitioner placeholder.",
        ),
        SchematicRelationship(
            relationship_id="practitionerrole-organization",
            relationship_type="practitioner_role_organization",
            source_id="practitionerrole-1",
            target_id="organization-1",
            reference_path="PractitionerRole.organization",
            description="PractitionerRole placeholder links to the supporting Organization placeholder.",
        ),
        *[
            SchematicRelationship(
                relationship_id=f"bundle-entry-{placeholder.placeholder_id}",
                relationship_type="bundle_entry",
                source_id="bundle",
                target_id=placeholder.placeholder_id,
                description=f"Bundle scaffold includes the {placeholder.resource_type} section-entry placeholder.",
            )
            for placeholder in section_resource_placeholders
        ],
        *[
            SchematicRelationship(
                relationship_id=f"section-entry-{section.section_key}",
                relationship_type="composition_section_entry",
                source_id="composition-1",
                target_id=section.entry_placeholder_ids[0],
                reference_path=f"Composition.section:{section.slice_name}.entry",
                description=f"Composition scaffold wires the {section.title} section to its placeholder entry resource.",
            )
            for section in section_scaffolds
        ],
    ]

    omitted_optional_sections = [
        f"{section.slice_name}:{section.title}"
        for section in normalized_assets.composition_section_definitions
        if not section.required
    ]

    return BundleSchematic(
        stage_id="bundle_schematic",
        status="placeholder_complete",
        summary=(
            "Generated the first deterministic PS-CA bundle schematic from normalized assets, "
            f"required section definitions, selected example evidence, and {provider_context_summary}."
        ),
        placeholder_note=(
            "This slice builds a real schematic scaffold only; build ordering, resource population, "
            f"and optional PS-CA sections remain deferred. {provider_context_note}"
        ),
        source_refs=normalized_assets.source_refs,
        generation_basis="deterministic_psca_foundation_rules",
        bundle_scaffold=BundleScaffold(
            profile_url=bundle_profile.url,
            bundle_type="document",
            required_entry_placeholder_ids=["composition-1", "patient-1"],
            required_later_fields=["identifier", "timestamp"],
        ),
        composition_scaffold=CompositionScaffold(
            placeholder_id="composition-1",
            profile_url=composition_profile.url,
            expected_type_system="http://loinc.org",
            expected_type_code="60591-5",
            expected_type_display="Patient summary Document",
            required_later_fields=["status", "title", "date", "author", "subject", "section"],
        ),
        section_scaffolds=section_scaffolds,
        resource_placeholders=resource_placeholders,
        relationships=relationships,
        evidence=SchematicEvidence(
            selected_example_filename=normalized_assets.selected_bundle_example.filename,
            selected_example_section_titles=normalized_assets.selected_bundle_example.composition_section_titles,
            selected_example_entry_resource_types=normalized_assets.selected_bundle_example.entry_resource_types,
            used_profile_ids=used_profile_ids,
            used_section_slice_names=[section.slice_name for section in section_scaffolds],
            provider_context=provider_context_evidence,
            source_refs=normalized_assets.source_refs,
        ),
        omitted_optional_sections=omitted_optional_sections,
    )


def _require_section_definition(
    section_definitions: dict[str, PscaCompositionSectionDefinitionSummary],
    section_key: str,
) -> PscaCompositionSectionDefinitionSummary:
    section_definition = section_definitions.get(section_key)
    if section_definition is None:
        raise ValueError(f"Required PS-CA section definition '{section_key}' is missing from normalized assets.")
    return section_definition


def _select_section_resource_type(
    section_definition: PscaCompositionSectionDefinitionSummary,
    example_section: PscaBundleExampleSectionSummary | None,
) -> str:
    if example_section is None:
        raise ValueError(
            f"Selected bundle example does not contain evidence for required section '{section_definition.section_key}'."
        )

    for resource_type in example_section.entry_resource_types:
        if resource_type in section_definition.allowed_entry_resource_types:
            return resource_type

    raise ValueError(
        "Selected bundle example does not contain a compatible resource type for "
        f"required section '{section_definition.section_key}'."
    )


def _select_section_title(
    section_definition: PscaCompositionSectionDefinitionSummary,
    example_section: PscaBundleExampleSectionSummary | None,
) -> str:
    if example_section and example_section.title:
        return example_section.title
    return section_definition.title


def _provider_context_evidence(
    normalized_request: NormalizedBuildRequest,
) -> SchematicProviderContextEvidence:
    provider_context = normalized_request.provider_context
    selected_organization = provider_context.selected_organization
    selected_relationship = provider_context.selected_provider_role_relationship
    return SchematicProviderContextEvidence(
        normalization_mode=provider_context.normalization_mode,
        provider_id=provider_context.provider.provider_id,
        provider_display_name=provider_context.provider.display_name,
        provider_source_type=provider_context.provider.source_type,
        selected_organization_id=(
            selected_organization.organization_id if selected_organization is not None else None
        ),
        selected_organization_display_name=(
            selected_organization.display_name if selected_organization is not None else None
        ),
        selected_provider_role_relationship_id=(
            selected_relationship.relationship_id if selected_relationship is not None else None
        ),
        selected_provider_role_label=(
            selected_relationship.role_label if selected_relationship is not None else None
        ),
    )


def _provider_context_summary(normalization_mode: str) -> str:
    if normalization_mode == "provider_context_explicit_selection":
        return "an explicitly selected provider-role relationship context"
    if normalization_mode == "provider_context_single_relationship":
        return "a deterministically selected single provider-role relationship context"
    return "legacy provider-profile fallback context"


def _provider_context_note(normalization_mode: str) -> str:
    if normalization_mode == "provider_context_explicit_selection":
        return (
            "The schematic records the explicitly selected provider-role relationship "
            "and organization context for inspectability."
        )
    if normalization_mode == "provider_context_single_relationship":
        return (
            "The schematic records the deterministically selected single provider-role "
            "relationship and organization context for inspectability."
        )
    return (
        "The schematic records legacy provider-profile fallback only; richer selected "
        "organization and provider-role context remains unavailable in this run."
    )
