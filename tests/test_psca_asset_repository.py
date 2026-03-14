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
    assert context.selected_bundle_example.filename == "Bundle1Example.json"
    assert context.selected_bundle_example.bundle_type == "document"
    assert "Composition" in context.selected_bundle_example.entry_resource_types
    assert "Active Problems" in context.selected_bundle_example.composition_section_titles
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
