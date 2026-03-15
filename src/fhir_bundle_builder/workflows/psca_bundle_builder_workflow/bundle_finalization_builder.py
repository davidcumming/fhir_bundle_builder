"""Deterministic PS-CA candidate bundle assembly from the resource registry."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from datetime import timedelta
from datetime import timezone
import uuid

from .models import (
    BundleEntryAssemblyResult,
    BundleSchematic,
    CandidateBundleArtifact,
    CandidateBundleEvidence,
    CandidateBundleResult,
    DeterministicValueEvidence,
    NormalizedBuildRequest,
    ReferenceContribution,
    ResourceConstructionStageResult,
    ResourceConstructionStepResult,
)

_CANDIDATE_BUNDLE_NAMESPACE = uuid.UUID("2f4fdf8e-1117-42e1-8ae0-5afdb257e683")
_CANDIDATE_BUNDLE_IDENTIFIER_SYSTEM = "urn:fhir-bundle-builder:candidate-bundle-identifier"
_CANDIDATE_BUNDLE_IDENTITY_EPOCH = datetime(2025, 1, 1, tzinfo=timezone.utc)
_SECONDS_IN_NON_LEAP_YEAR = 365 * 24 * 60 * 60


def build_psca_candidate_bundle_result(
    construction: ResourceConstructionStageResult,
    schematic: BundleSchematic,
    normalized_request: NormalizedBuildRequest,
) -> CandidateBundleResult:
    """Assemble the first real candidate bundle scaffold from constructed resource scaffolds."""

    registry = {entry.placeholder_id: entry for entry in construction.resource_registry}
    step_results_by_id = {
        step.step_id: step
        for step in (
            construction.step_result_history
            if construction.step_result_history
            else construction.step_results
        )
    }
    required_entry_ids = list(schematic.bundle_scaffold.required_entry_placeholder_ids)
    ordered_placeholder_ids = [
        relationship.target_id
        for relationship in schematic.relationships
        if relationship.relationship_type == "bundle_entry"
    ]
    planned_medication_placeholder_ids = _planned_medication_placeholder_ids(schematic)

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

    bundle_id = f"{normalized_request.specification.package_id}-{normalized_request.request.scenario_label}"
    bundle_seed = (
        "urn:fhir-bundle-builder:candidate-bundle:"
        f"{normalized_request.specification.package_id}:"
        f"{normalized_request.specification.version}:"
        f"{normalized_request.request.scenario_label}"
    )
    bundle_uuid = uuid.uuid5(_CANDIDATE_BUNDLE_NAMESPACE, bundle_seed)
    bundle_identifier = {
        "system": _CANDIDATE_BUNDLE_IDENTIFIER_SYSTEM,
        "value": str(bundle_uuid),
    }
    bundle_timestamp = _deterministic_bundle_timestamp(bundle_uuid)
    full_url_by_placeholder_id = {
        placeholder_id: f"urn:uuid:{uuid.uuid5(bundle_uuid, placeholder_id)}"
        for placeholder_id in ordered_placeholder_ids
    }

    entry_assembly: list[BundleEntryAssemblyResult] = []
    bundle_entries: list[dict[str, object]] = []
    populated_paths = [
        "resourceType",
        "id",
        "identifier.system",
        "identifier.value",
        "timestamp",
        "meta.profile[0]",
        "type",
    ]
    deterministic_value_evidence = [
        _value_evidence(
            "identifier.system",
            "deterministic_bundle_identity_policy",
            "fixed candidate bundle identifier system",
        ),
        _value_evidence(
            "identifier.value",
            "normalized_request",
            "package_id + version + scenario_label",
        ),
        _value_evidence(
            "timestamp",
            "deterministic_bundle_identity_policy",
            "bundle_uuid-derived offset from 2025-01-01T00:00:00Z",
        ),
    ]

    for index, placeholder_id in enumerate(ordered_placeholder_ids):
        registry_entry = registry[placeholder_id]
        full_url = full_url_by_placeholder_id[placeholder_id]
        resource_copy = deepcopy(registry_entry.current_scaffold.fhir_scaffold)
        _rewrite_resource_references(
            resource_copy,
            _aggregate_reference_contributions(registry_entry.current_scaffold.source_step_ids, step_results_by_id),
            full_url_by_placeholder_id,
        )
        bundle_entries.append({"fullUrl": full_url, "resource": resource_copy})
        entry_assembly.append(
            BundleEntryAssemblyResult(
                sequence=index + 1,
                placeholder_id=placeholder_id,
                resource_type=registry_entry.resource_type,
                full_url=full_url,
                required_by_bundle_scaffold=placeholder_id in required_entry_ids,
                source_registry_step_id=registry_entry.latest_step_id,
                scaffold_state=registry_entry.current_scaffold.scaffold_state,
                entry_path=f"entry[{index}].resource",
            )
        )
        populated_paths.append(f"entry[{index}].fullUrl")
        populated_paths.append(f"entry[{index}].resource")
        deterministic_value_evidence.append(
            _value_evidence(
                f"entry[{index}].fullUrl",
                "deterministic_bundle_identity_policy",
                f"bundle_uuid + {placeholder_id}",
            )
        )

    fhir_bundle = {
        "resourceType": "Bundle",
        "id": bundle_id,
        "identifier": bundle_identifier,
        "timestamp": bundle_timestamp,
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
        deferred_paths=[],
        deterministic_value_evidence=deterministic_value_evidence,
    )

    return CandidateBundleResult(
        stage_id="bundle_finalization",
        status="placeholder_complete",
        summary="Assembled a deterministic candidate bundle scaffold from the current resource registry and bundle schematic.",
        placeholder_note="This stage now applies a deterministic local candidate-bundle identity policy for identifier, timestamp, and entry fullUrls; persistent publication semantics remain deferred.",
        source_refs=construction.source_refs,
        assembly_mode="deterministic_registry_bundle_scaffold",
        candidate_bundle=candidate_bundle,
        entry_assembly=entry_assembly,
        deferred_items=[
            "Persistent cross-run business identity remains deferred.",
            "Public or server-assigned URLs remain deferred.",
            "Publication and transport semantics remain deferred.",
        ],
        unresolved_items=[
            "The candidate bundle is scaffold-only and has not been structurally validated yet.",
            "The bundle identity policy is local and deterministic for candidate-bundle use only.",
        ],
        evidence=CandidateBundleEvidence(
            source_resource_construction_stage_id=construction.stage_id,
            source_schematic_stage_id=schematic.stage_id,
            source_build_plan_stage_id=construction.evidence.source_build_plan_stage_id,
            required_entry_placeholder_ids=required_entry_ids,
            ordered_placeholder_ids=ordered_placeholder_ids,
            planned_medication_placeholder_ids=planned_medication_placeholder_ids,
            assembled_medication_placeholder_ids=_assembled_medication_placeholder_ids(entry_assembly),
            source_refs=construction.source_refs,
        ),
    )


def _deterministic_bundle_timestamp(bundle_uuid: uuid.UUID) -> str:
    offset_seconds = int(bundle_uuid.hex[:8], 16) % _SECONDS_IN_NON_LEAP_YEAR
    timestamp = _CANDIDATE_BUNDLE_IDENTITY_EPOCH + timedelta(seconds=offset_seconds)
    return timestamp.isoformat().replace("+00:00", "Z")


def _aggregate_reference_contributions(
    source_step_ids: list[str],
    step_results_by_id: dict[str, ResourceConstructionStepResult],
) -> list[ReferenceContribution]:
    contributions: list[ReferenceContribution] = []
    seen_paths: set[tuple[str, str]] = set()
    for step_id in source_step_ids:
        step_result = step_results_by_id.get(step_id)
        if step_result is None:
            continue
        for contribution in step_result.reference_contributions:
            key = (contribution.reference_path, contribution.target_placeholder_id)
            if key in seen_paths:
                continue
            seen_paths.add(key)
            contributions.append(contribution)
    return contributions


def _rewrite_resource_references(
    resource: dict[str, object],
    contributions: list[ReferenceContribution],
    full_url_by_placeholder_id: dict[str, str],
) -> None:
    for contribution in contributions:
        full_url = full_url_by_placeholder_id.get(contribution.target_placeholder_id)
        if full_url is None:
            raise ValueError(
                "Candidate bundle finalization could not resolve a fullUrl for referenced placeholder "
                f"'{contribution.target_placeholder_id}'."
            )
        _set_nested_value(resource, contribution.reference_path, full_url)


def _set_nested_value(root: dict[str, object], path: str, value: str) -> None:
    current: object = root
    segments = path.split(".")
    for index, segment in enumerate(segments):
        key, list_index = _parse_path_segment(segment)
        is_last = index == len(segments) - 1

        if not isinstance(current, dict):
            raise ValueError(f"Reference rewrite path '{path}' could not be resolved.")
        next_value = current.get(key)

        if list_index is None:
            if is_last:
                current[key] = value
                return
            current = next_value
            continue

        if not isinstance(next_value, list) or list_index >= len(next_value):
            raise ValueError(f"Reference rewrite path '{path}' could not be resolved.")
        list_item = next_value[list_index]
        if is_last:
            next_value[list_index] = value
            return
        current = list_item

    raise ValueError(f"Reference rewrite path '{path}' could not be resolved.")


def _parse_path_segment(segment: str) -> tuple[str, int | None]:
    if "[" not in segment:
        return segment, None
    key, rest = segment.split("[", 1)
    return key, int(rest.rstrip("]"))


def _value_evidence(target_path: str, source_artifact: str, source_detail: str) -> DeterministicValueEvidence:
    return DeterministicValueEvidence(
        target_path=target_path,
        source_artifact=source_artifact,
        source_detail=source_detail,
    )


def _planned_medication_placeholder_ids(schematic: BundleSchematic) -> list[str]:
    for section in schematic.section_scaffolds:
        if section.section_key == "medications":
            return list(section.entry_placeholder_ids)
    return []


def _assembled_medication_placeholder_ids(
    entry_assembly: list[BundleEntryAssemblyResult],
) -> list[str]:
    return [
        entry.placeholder_id
        for entry in entry_assembly
        if entry.placeholder_id.startswith("medicationrequest-")
    ]
