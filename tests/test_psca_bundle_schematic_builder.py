"""Direct tests for deterministic PS-CA schematic generation."""

from __future__ import annotations

from fhir_bundle_builder.specifications.psca import PscaAssetQuery, PscaAssetRepository
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.models import (
    BundleRequestInput,
    PatientAllergyInput,
    PatientConditionInput,
    PatientContextInput,
    PatientIdentityInput,
    PatientMedicationInput,
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
    assert schematic.evidence.patient_context.normalization_mode == "patient_context_explicit"
    assert schematic.evidence.patient_context.patient_id == "patient-schematic-test"
    assert schematic.evidence.patient_context.administrative_gender_present is True
    assert schematic.evidence.patient_context.birth_date_present is True
    section_contexts = {context.section_key: context for context in schematic.evidence.clinical_section_contexts}
    assert section_contexts["medications"].available_item_count == 1
    assert section_contexts["medications"].selected_single_entry_display_text == "Atorvastatin 20 MG oral tablet"
    assert section_contexts["medications"].planned_entry_display_texts == ["Atorvastatin 20 MG oral tablet"]
    assert [
        (entry.placeholder_id, entry.source_medication_index, entry.medication_id, entry.display_text)
        for entry in section_contexts["medications"].planned_medication_entries
    ] == [
        (
            "medicationrequest-1",
            0,
            "med-schematic-1",
            "Atorvastatin 20 MG oral tablet",
        )
    ]
    assert section_contexts["medications"].planned_placeholder_count == 1
    assert section_contexts["medications"].deferred_additional_item_count == 0
    assert section_contexts["medications"].planning_disposition == "fixed_single_entry_selected_item"
    assert section_contexts["allergies"].planning_disposition == "fixed_single_entry_selected_item"
    assert section_contexts["problems"].planning_disposition == "fixed_single_entry_selected_item"
    assert schematic.evidence.provider_context.normalization_mode == "provider_context_explicit_selection"
    assert schematic.evidence.provider_context.provider_id == "provider-schematic-test"
    assert schematic.evidence.provider_context.selected_organization_id == "org-schematic-test"
    assert schematic.evidence.provider_context.selected_provider_role_relationship_id == "provider-role-schematic-1"
    assert schematic.evidence.provider_context.selected_provider_role_label == "attending-physician"
    assert "explicit structured patient/clinical context" in schematic.summary
    assert "supports at most two medication placeholders" in schematic.placeholder_note
    assert "explicitly selected provider-role relationship context" in schematic.summary
    assert "explicitly selected provider-role relationship" in schematic.placeholder_note


def test_psca_bundle_schematic_builder_records_legacy_provider_context_fallback() -> None:
    repository = PscaAssetRepository()
    normalized_assets = repository.load_foundation_context(PscaAssetQuery())
    normalized_request = _build_legacy_normalized_request()

    schematic = build_psca_bundle_schematic(normalized_assets, normalized_request)
    placeholders = {placeholder.placeholder_id: placeholder for placeholder in schematic.resource_placeholders}

    assert placeholders["practitionerrole-1"].role == "document-author"
    assert schematic.evidence.patient_context.normalization_mode == "legacy_patient_profile"
    assert all(
        context.planning_disposition == "legacy_profile_fallback"
        for context in schematic.evidence.clinical_section_contexts
    )
    assert schematic.evidence.provider_context.normalization_mode == "legacy_provider_profile"
    assert schematic.evidence.provider_context.selected_organization_id is None
    assert schematic.evidence.provider_context.selected_provider_role_relationship_id is None
    assert "legacy patient-profile fallback context" in schematic.summary
    assert "legacy provider-profile fallback context" in schematic.summary
    assert "legacy provider-profile fallback only" in schematic.placeholder_note


def test_psca_bundle_schematic_builder_supports_bounded_two_medication_planning() -> None:
    repository = PscaAssetRepository()
    normalized_assets = repository.load_foundation_context(PscaAssetQuery())
    normalized_request = build_psca_normalized_request(
        WorkflowBuildInput(
            specification=SpecificationSelection(),
            patient_profile=ProfileReferenceInput(
                profile_id="patient-schematic-test",
                display_name="Schematic Test Patient",
            ),
            patient_context=PatientContextInput(
                patient=PatientIdentityInput(
                    patient_id="patient-schematic-test",
                    display_name="Schematic Test Patient",
                    source_type="patient_management",
                ),
                medications=[
                    PatientMedicationInput(
                        medication_id="med-schematic-1",
                        display_text="Atorvastatin 20 MG oral tablet",
                    ),
                    PatientMedicationInput(
                        medication_id="med-schematic-2",
                        display_text="Metformin 500 MG oral tablet",
                    ),
                ],
                allergies=[
                    PatientAllergyInput(
                        allergy_id="alg-schematic-1",
                        display_text="Peanut allergy",
                    )
                ],
                conditions=[
                    PatientConditionInput(
                        condition_id="cond-schematic-1",
                        display_text="Type 2 diabetes mellitus",
                    )
                ],
            ),
            provider_profile=ProfileReferenceInput(
                profile_id="provider-schematic-test",
                display_name="Schematic Test Provider",
            ),
            request=BundleRequestInput(
                request_text="Create a deterministic schematic for testing.",
                scenario_label="pytest-schematic-multi-patient",
            ),
        )
    )

    schematic = build_psca_bundle_schematic(normalized_assets, normalized_request)
    section_contexts = {context.section_key: context for context in schematic.evidence.clinical_section_contexts}

    assert section_contexts["medications"].available_item_count == 2
    assert section_contexts["medications"].selected_single_entry_display_text is None
    assert section_contexts["medications"].planned_entry_display_texts == [
        "Atorvastatin 20 MG oral tablet",
        "Metformin 500 MG oral tablet",
    ]
    assert [
        (entry.placeholder_id, entry.source_medication_index, entry.medication_id)
        for entry in section_contexts["medications"].planned_medication_entries
    ] == [
        ("medicationrequest-1", 0, "med-schematic-1"),
        ("medicationrequest-2", 1, "med-schematic-2"),
    ]
    assert section_contexts["medications"].planned_placeholder_count == 2
    assert section_contexts["medications"].deferred_additional_item_count == 0
    assert section_contexts["medications"].planning_disposition == "bounded_two_entry_selected_first_two"
    assert section_contexts["allergies"].planned_placeholder_count == 1
    assert {placeholder.placeholder_id for placeholder in schematic.resource_placeholders} >= {
        "medicationrequest-1",
        "medicationrequest-2",
        "allergyintolerance-1",
        "condition-1",
    }
    medications_section = next(
        section for section in schematic.section_scaffolds if section.section_key == "medications"
    )
    assert medications_section.entry_placeholder_ids == ["medicationrequest-1", "medicationrequest-2"]
    relationships = {relationship.relationship_id: relationship for relationship in schematic.relationships}
    assert relationships["section-entry-medications"].target_id == "medicationrequest-1"
    assert relationships["section-entry-medications-2"].target_id == "medicationrequest-2"
    assert "bounded two-placeholder path" in schematic.summary


def test_psca_bundle_schematic_builder_records_medication_overflow_beyond_two_as_deferred() -> None:
    repository = PscaAssetRepository()
    normalized_assets = repository.load_foundation_context(PscaAssetQuery())
    normalized_request = build_psca_normalized_request(
        WorkflowBuildInput(
            specification=SpecificationSelection(),
            patient_profile=ProfileReferenceInput(
                profile_id="patient-schematic-overflow-test",
                display_name="Schematic Overflow Patient",
            ),
            patient_context=PatientContextInput(
                patient=PatientIdentityInput(
                    patient_id="patient-schematic-overflow-test",
                    display_name="Schematic Overflow Patient",
                    source_type="patient_management",
                ),
                medications=[
                    PatientMedicationInput(medication_id="med-overflow-1", display_text="Atorvastatin 20 MG oral tablet"),
                    PatientMedicationInput(medication_id="med-overflow-2", display_text="Metformin 500 MG oral tablet"),
                    PatientMedicationInput(medication_id="med-overflow-3", display_text="Lisinopril 10 MG oral tablet"),
                ],
                allergies=[],
                conditions=[],
            ),
            provider_profile=ProfileReferenceInput(
                profile_id="provider-schematic-overflow-test",
                display_name="Schematic Overflow Provider",
            ),
            request=BundleRequestInput(
                request_text="Create a deterministic schematic for bounded medication overflow testing.",
                scenario_label="pytest-schematic-overflow",
            ),
        )
    )

    schematic = build_psca_bundle_schematic(normalized_assets, normalized_request)
    medications_context = next(
        context
        for context in schematic.evidence.clinical_section_contexts
        if context.section_key == "medications"
    )

    assert medications_context.available_item_count == 3
    assert medications_context.planned_placeholder_count == 2
    assert medications_context.planned_entry_display_texts == [
        "Atorvastatin 20 MG oral tablet",
        "Metformin 500 MG oral tablet",
    ]
    assert [entry.medication_id for entry in medications_context.planned_medication_entries] == [
        "med-overflow-1",
        "med-overflow-2",
    ]
    assert medications_context.deferred_additional_item_count == 1
    assert "additional medication items remain deferred" in schematic.summary


def test_psca_bundle_schematic_builder_keeps_allergies_and_problems_fixed_to_one_entry_when_multiple_items_exist() -> None:
    repository = PscaAssetRepository()
    normalized_assets = repository.load_foundation_context(PscaAssetQuery())
    normalized_request = build_psca_normalized_request(
        WorkflowBuildInput(
            specification=SpecificationSelection(),
            patient_profile=ProfileReferenceInput(
                profile_id="patient-schematic-fixed-trio-test",
                display_name="Schematic Fixed Trio Patient",
            ),
            patient_context=PatientContextInput(
                patient=PatientIdentityInput(
                    patient_id="patient-schematic-fixed-trio-test",
                    display_name="Schematic Fixed Trio Patient",
                    source_type="patient_management",
                ),
                medications=[
                    PatientMedicationInput(
                        medication_id="med-fixed-trio-1",
                        display_text="Atorvastatin 20 MG oral tablet",
                    )
                ],
                allergies=[
                    PatientAllergyInput(
                        allergy_id="alg-fixed-trio-1",
                        display_text="Peanut allergy",
                    ),
                    PatientAllergyInput(
                        allergy_id="alg-fixed-trio-2",
                        display_text="Latex allergy",
                    ),
                ],
                conditions=[
                    PatientConditionInput(
                        condition_id="cond-fixed-trio-1",
                        display_text="Type 2 diabetes mellitus",
                    ),
                    PatientConditionInput(
                        condition_id="cond-fixed-trio-2",
                        display_text="Hypertension",
                    ),
                ],
            ),
            provider_profile=ProfileReferenceInput(
                profile_id="provider-schematic-fixed-trio-test",
                display_name="Schematic Fixed Trio Provider",
            ),
            request=BundleRequestInput(
                request_text="Create a deterministic schematic for fixed single-entry trio testing.",
                scenario_label="pytest-schematic-fixed-trio",
            ),
        )
    )

    schematic = build_psca_bundle_schematic(normalized_assets, normalized_request)
    section_contexts = {context.section_key: context for context in schematic.evidence.clinical_section_contexts}
    section_scaffolds = {section.section_key: section for section in schematic.section_scaffolds}
    placeholder_ids = {placeholder.placeholder_id for placeholder in schematic.resource_placeholders}

    assert section_contexts["allergies"].available_item_count == 2
    assert section_contexts["allergies"].selected_single_entry_display_text is None
    assert section_contexts["allergies"].planned_placeholder_count == 1
    assert section_contexts["allergies"].deferred_additional_item_count == 0
    assert section_contexts["allergies"].planning_disposition == "fixed_single_entry_multiple_items_deferred"
    assert section_contexts["problems"].available_item_count == 2
    assert section_contexts["problems"].selected_single_entry_display_text is None
    assert section_contexts["problems"].planned_placeholder_count == 1
    assert section_contexts["problems"].deferred_additional_item_count == 0
    assert section_contexts["problems"].planning_disposition == "fixed_single_entry_multiple_items_deferred"
    assert section_scaffolds["allergies"].entry_placeholder_ids == ["allergyintolerance-1"]
    assert section_scaffolds["problems"].entry_placeholder_ids == ["condition-1"]
    assert "allergyintolerance-2" not in placeholder_ids
    assert "condition-2" not in placeholder_ids


def _build_normalized_request():
    return build_psca_normalized_request(
        WorkflowBuildInput(
            specification=SpecificationSelection(),
            patient_profile=ProfileReferenceInput(
                profile_id="patient-schematic-test",
                display_name="Schematic Test Patient",
            ),
            patient_context=PatientContextInput(
                patient=PatientIdentityInput(
                    patient_id="patient-schematic-test",
                    display_name="Schematic Test Patient",
                    source_type="patient_management",
                    administrative_gender="female",
                    birth_date="1985-02-14",
                ),
                medications=[
                    PatientMedicationInput(
                        medication_id="med-schematic-1",
                        display_text="Atorvastatin 20 MG oral tablet",
                    )
                ],
                allergies=[
                    PatientAllergyInput(
                        allergy_id="alg-schematic-1",
                        display_text="Peanut allergy",
                    )
                ],
                conditions=[
                    PatientConditionInput(
                        condition_id="cond-schematic-1",
                        display_text="Type 2 diabetes mellitus",
                    )
                ],
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
