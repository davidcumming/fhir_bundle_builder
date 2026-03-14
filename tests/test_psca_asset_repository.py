"""Direct tests for the PS-CA asset retrieval boundary."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from fhir_bundle_builder.specifications.psca import PscaAssetQuery, PscaAssetRepository


def test_psca_asset_repository_loads_foundation_context() -> None:
    repository = PscaAssetRepository()

    context = repository.load_foundation_context(PscaAssetQuery())

    assert context.normalization_level == "foundation"
    assert context.package_summary.package_id == "ca.infoway.io.psca"
    assert context.package_summary.version == "2.1.1-DFT"
    assert context.package_summary.structure_definition_count == 35
    assert context.package_summary.example_count == 16
    assert len(context.workflow_profile_inventory) == 6
    assert context.selected_profiles.bundle.profile_id == "bundle-ca-ps"
    assert context.selected_profiles.composition.resource_type == "Composition"
    assert len(context.composition_section_definitions) >= 3
    required_sections = {section.section_key: section for section in context.composition_section_definitions if section.required}
    assert required_sections["medications"].allowed_entry_resource_types == ["MedicationStatement", "MedicationRequest"]
    assert required_sections["allergies"].allowed_entry_resource_types == ["AllergyIntolerance"]
    assert required_sections["problems"].allowed_entry_resource_types == ["Condition"]
    assert context.selected_bundle_example.filename == "Bundle1Example.json"
    assert context.selected_bundle_example.bundle_type == "document"
    assert "Composition" in context.selected_bundle_example.entry_resource_types
    assert "Active Problems" in context.selected_bundle_example.composition_section_titles
    assert context.selected_bundle_example.composition_subject_resource_type == "Patient"
    assert context.selected_bundle_example.composition_author_resource_types == ["PractitionerRole"]
    example_sections = {section.loinc_code: section for section in context.selected_bundle_example.sections}
    assert example_sections["10160-0"].entry_resource_types == ["MedicationRequest"]
    assert example_sections["48765-2"].entry_resource_types == ["AllergyIntolerance"]
    assert example_sections["11450-4"].entry_resource_types == ["Condition"]
    assert len(context.example_inventory) == 16


def test_psca_asset_repository_fails_for_missing_example_bundle() -> None:
    repository = PscaAssetRepository()

    with pytest.raises(FileNotFoundError, match="missing-example.json"):
        repository.load_foundation_context(
            PscaAssetQuery(selected_example_bundle_filename="missing-example.json")
        )


def test_psca_asset_repository_fails_for_missing_foundational_profile(tmp_path: Path) -> None:
    source_root = Path("fhir/ca.infoway.io.psca-2.1.1-dft")
    copied_root = tmp_path / "fhir" / source_root.name
    shutil.copytree(source_root, copied_root)
    (copied_root / "structuredefinition-profile-bundle-ca-ps.json").unlink()

    repository = PscaAssetRepository(package_root=copied_root)

    with pytest.raises(FileNotFoundError, match="structuredefinition-profile-bundle-ca-ps.json"):
        repository.load_foundation_context(PscaAssetQuery())
