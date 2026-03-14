"""Direct tests for deterministic PS-CA bundle finalization."""

from __future__ import annotations

from copy import deepcopy
import uuid

import pytest

from fhir_bundle_builder.specifications.psca import PscaAssetQuery, PscaAssetRepository
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.build_plan_builder import (
    build_psca_build_plan,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.bundle_finalization_builder import (
    build_psca_candidate_bundle_result,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.resource_construction_builder import (
    build_psca_resource_construction_result,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.schematic_builder import (
    build_psca_bundle_schematic,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.models import (
    BundleRequestInput,
    NormalizedBuildRequest,
    ProfileReferenceInput,
    SpecificationSelection,
    WorkflowDefaults,
)


def test_psca_bundle_finalization_builder_assembles_expected_bundle_scaffold() -> None:
    normalized_request, schematic, construction = _build_construction_inputs()

    result = build_psca_candidate_bundle_result(construction, schematic, normalized_request)
    bundle_identifier_value = result.candidate_bundle.fhir_bundle["identifier"]["value"]
    full_urls = [entry["fullUrl"] for entry in result.candidate_bundle.fhir_bundle["entry"]]

    assert result.assembly_mode == "deterministic_registry_bundle_scaffold"
    assert result.candidate_bundle.bundle_state == "candidate_scaffold_assembled"
    assert result.candidate_bundle.entry_count == 8
    assert result.candidate_bundle.fhir_bundle["resourceType"] == "Bundle"
    assert result.candidate_bundle.fhir_bundle["id"] == "ca.infoway.io.psca-pytest-finalization"
    assert result.candidate_bundle.fhir_bundle["identifier"]["system"] == "urn:fhir-bundle-builder:candidate-bundle-identifier"
    assert str(uuid.UUID(bundle_identifier_value)) == bundle_identifier_value
    assert result.candidate_bundle.fhir_bundle["timestamp"].endswith("Z")
    assert result.candidate_bundle.fhir_bundle["meta"]["profile"] == [schematic.bundle_scaffold.profile_url]
    assert result.candidate_bundle.fhir_bundle["type"] == "document"
    assert [assembly.placeholder_id for assembly in result.entry_assembly] == [
        "composition-1",
        "patient-1",
        "practitionerrole-1",
        "practitioner-1",
        "organization-1",
        "medicationrequest-1",
        "allergyintolerance-1",
        "condition-1",
    ]
    assert [entry["resource"]["resourceType"] for entry in result.candidate_bundle.fhir_bundle["entry"]] == [
        "Composition",
        "Patient",
        "PractitionerRole",
        "Practitioner",
        "Organization",
        "MedicationRequest",
        "AllergyIntolerance",
        "Condition",
    ]
    assert all(full_url.startswith("urn:uuid:") for full_url in full_urls)
    assert [assembly.full_url for assembly in result.entry_assembly] == full_urls
    assert result.entry_assembly[0].required_by_bundle_scaffold is True
    assert result.entry_assembly[1].required_by_bundle_scaffold is True
    assert result.candidate_bundle.deferred_paths == []
    assert len(result.candidate_bundle.fhir_bundle["entry"][0]["resource"]["section"]) == 3
    assert result.candidate_bundle.fhir_bundle["entry"][0]["resource"]["subject"]["reference"] == full_urls[1]
    assert result.candidate_bundle.fhir_bundle["entry"][0]["resource"]["author"][0]["reference"] == full_urls[2]
    assert result.candidate_bundle.fhir_bundle["entry"][2]["resource"]["practitioner"]["reference"] == full_urls[3]
    assert result.candidate_bundle.fhir_bundle["entry"][2]["resource"]["organization"]["reference"] == full_urls[4]
    assert result.candidate_bundle.fhir_bundle["entry"][5]["resource"]["subject"]["reference"] == full_urls[1]
    assert result.candidate_bundle.fhir_bundle["entry"][6]["resource"]["patient"]["reference"] == full_urls[1]
    assert result.candidate_bundle.fhir_bundle["entry"][7]["resource"]["subject"]["reference"] == full_urls[1]
    assert result.candidate_bundle.fhir_bundle["entry"][0]["resource"]["section"][0]["entry"][0]["reference"] == full_urls[5]
    assert result.candidate_bundle.fhir_bundle["entry"][0]["resource"]["section"][1]["entry"][0]["reference"] == full_urls[6]
    assert result.candidate_bundle.fhir_bundle["entry"][0]["resource"]["section"][2]["entry"][0]["reference"] == full_urls[7]
    assert any(
        evidence.target_path == "identifier.value"
        for evidence in result.candidate_bundle.deterministic_value_evidence
    )
    assert any(
        evidence.target_path == "entry[0].fullUrl"
        for evidence in result.candidate_bundle.deterministic_value_evidence
    )


def test_psca_bundle_finalization_builder_fails_when_composition_not_finalized() -> None:
    normalized_request, schematic, construction = _build_construction_inputs()
    broken_construction = deepcopy(construction)
    composition_entry = next(
        entry for entry in broken_construction.resource_registry if entry.placeholder_id == "composition-1"
    )
    composition_entry.current_scaffold.scaffold_state = "composition_scaffold_created"

    with pytest.raises(ValueError, match="sections_attached"):
        build_psca_candidate_bundle_result(broken_construction, schematic, normalized_request)


def _build_construction_inputs() -> tuple[NormalizedBuildRequest, object, object]:
    repository = PscaAssetRepository()
    normalized_assets = repository.load_foundation_context(PscaAssetQuery())
    schematic = build_psca_bundle_schematic(normalized_assets)
    plan = build_psca_build_plan(schematic)
    normalized_request = NormalizedBuildRequest(
        stage_id="request_normalization",
        status="placeholder_complete",
        summary="Test normalized request.",
        placeholder_note="Test artifact.",
        source_refs=[],
        specification=SpecificationSelection(),
        patient_profile=ProfileReferenceInput(
            profile_id="patient-finalization-test",
            display_name="Finalization Test Patient",
        ),
        provider_profile=ProfileReferenceInput(
            profile_id="provider-finalization-test",
            display_name="Finalization Test Provider",
        ),
        request=BundleRequestInput(
            request_text="Create a deterministic candidate bundle for testing.",
            scenario_label="pytest-finalization",
        ),
        workflow_defaults=WorkflowDefaults(
            bundle_type="document",
            specification_mode="normalized-asset-foundation",
            validation_mode="foundational_dual_channel",
            resource_construction_mode="deterministic_content_enriched_foundation",
        ),
        run_label="pytest-finalization:ca.infoway.io.psca:2.1.1-DFT",
    )
    construction = build_psca_resource_construction_result(plan, schematic, normalized_request)
    return normalized_request, schematic, construction
