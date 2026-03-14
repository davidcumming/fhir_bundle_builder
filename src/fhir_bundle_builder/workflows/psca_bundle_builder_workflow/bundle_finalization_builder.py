"""Deterministic PS-CA candidate bundle assembly from the resource registry."""

from __future__ import annotations

from copy import deepcopy

from .models import (
    BundleEntryAssemblyResult,
    BundleSchematic,
    CandidateBundleArtifact,
    CandidateBundleEvidence,
    CandidateBundleResult,
    NormalizedBuildRequest,
    ResourceConstructionStageResult,
)


def build_psca_candidate_bundle_result(
    construction: ResourceConstructionStageResult,
    schematic: BundleSchematic,
    normalized_request: NormalizedBuildRequest,
) -> CandidateBundleResult:
    """Assemble the first real candidate bundle scaffold from constructed resource scaffolds."""

    registry = {entry.placeholder_id: entry for entry in construction.resource_registry}
    required_entry_ids = list(schematic.bundle_scaffold.required_entry_placeholder_ids)
    ordered_placeholder_ids = [
        relationship.target_id
        for relationship in schematic.relationships
        if relationship.relationship_type == "bundle_entry"
    ]

    missing_required = [placeholder_id for placeholder_id in required_entry_ids if placeholder_id not in registry]
    if missing_required:
        raise ValueError(
            f"Candidate bundle finalization is missing required bundle entry placeholders: {', '.join(missing_required)}."
        )

    missing_bundle_entries = [placeholder_id for placeholder_id in ordered_placeholder_ids if placeholder_id not in registry]
    if missing_bundle_entries:
        raise ValueError(
            "Candidate bundle finalization is missing registry scaffolds for bundle-entry placeholders: "
            f"{', '.join(missing_bundle_entries)}."
        )

    composition_entry = registry.get("composition-1")
    if composition_entry is None:
        raise ValueError("Candidate bundle finalization requires the finalized Composition scaffold 'composition-1'.")
    if composition_entry.current_scaffold.scaffold_state != "sections_attached":
        raise ValueError(
            "Candidate bundle finalization requires 'composition-1' to be in scaffold state 'sections_attached'."
        )

    entry_assembly: list[BundleEntryAssemblyResult] = []
    bundle_entries: list[dict[str, object]] = []
    populated_paths = ["resourceType", "id", "meta.profile[0]", "type"]

    for index, placeholder_id in enumerate(ordered_placeholder_ids):
        registry_entry = registry[placeholder_id]
        bundle_entries.append({"resource": deepcopy(registry_entry.current_scaffold.fhir_scaffold)})
        entry_assembly.append(
            BundleEntryAssemblyResult(
                sequence=index + 1,
                placeholder_id=placeholder_id,
                resource_type=registry_entry.resource_type,
                required_by_bundle_scaffold=placeholder_id in required_entry_ids,
                source_registry_step_id=registry_entry.latest_step_id,
                scaffold_state=registry_entry.current_scaffold.scaffold_state,
                entry_path=f"entry[{index}].resource",
            )
        )
        populated_paths.append(f"entry[{index}].resource")

    bundle_id = f"{normalized_request.specification.package_id}-{normalized_request.request.scenario_label}"
    fhir_bundle = {
        "resourceType": "Bundle",
        "id": bundle_id,
        "meta": {"profile": [schematic.bundle_scaffold.profile_url]},
        "type": schematic.bundle_scaffold.bundle_type,
        "entry": bundle_entries,
    }

    candidate_bundle = CandidateBundleArtifact(
        bundle_id=bundle_id,
        profile_url=schematic.bundle_scaffold.profile_url,
        bundle_type=schematic.bundle_scaffold.bundle_type,
        bundle_state="candidate_scaffold_assembled",
        entry_count=len(bundle_entries),
        fhir_bundle=fhir_bundle,
        populated_paths=populated_paths,
        deferred_paths=[
            *schematic.bundle_scaffold.required_later_fields,
            "entry.fullUrl",
        ],
    )

    return CandidateBundleResult(
        stage_id="bundle_finalization",
        status="placeholder_complete",
        summary="Assembled a deterministic candidate bundle scaffold from the current resource registry and bundle schematic.",
        placeholder_note="This stage assembles a real Bundle-shaped candidate scaffold only; identifier policy, timestamp policy, entry fullUrls, validation, and repair remain deferred.",
        source_refs=construction.source_refs,
        assembly_mode="deterministic_registry_bundle_scaffold",
        candidate_bundle=candidate_bundle,
        entry_assembly=entry_assembly,
        deferred_items=[
            "Bundle.identifier remains deferred.",
            "Bundle.timestamp remains deferred.",
            "Bundle.entry.fullUrl values remain deferred.",
            "Deep reference consistency repair remains deferred.",
        ],
        unresolved_items=[
            "The candidate bundle is scaffold-only and has not been structurally validated yet.",
            "No bundle-level identifier or timestamp strategy has been applied yet.",
        ],
        evidence=CandidateBundleEvidence(
            source_resource_construction_stage_id=construction.stage_id,
            source_schematic_stage_id=schematic.stage_id,
            source_build_plan_stage_id=construction.evidence.source_build_plan_stage_id,
            required_entry_placeholder_ids=required_entry_ids,
            ordered_placeholder_ids=ordered_placeholder_ids,
            source_refs=construction.source_refs,
        ),
    )
