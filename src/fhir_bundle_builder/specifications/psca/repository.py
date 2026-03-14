"""Deterministic filesystem-backed retrieval for bundled PS-CA assets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import (
    PscaAssetQuery,
    PscaBundleExampleSummary,
    PscaExampleSummary,
    PscaNormalizedAssetContext,
    PscaPackageSummary,
    PscaSelectedProfiles,
    PscaWorkflowProfileRole,
    PscaWorkflowProfileSummary,
)


class PscaAssetRepository:
    """Load a narrow normalized PS-CA asset context from the bundled package."""

    _FOUNDATIONAL_PROFILE_IDS: dict[PscaWorkflowProfileRole, str] = {
        "bundle": "bundle-ca-ps",
        "composition": "composition-ca-ps",
        "patient": "patient-ca-ps",
        "practitioner": "practitioner-lab-ca-ps",
        "practitioner_role": "practitionerrole-lab-ca-ps",
        "organization": "organization-lab-ca-ps",
    }

    def __init__(self, package_root: Path | None = None) -> None:
        self.package_root = package_root or (Path(__file__).resolve().parents[4] / "fhir" / "ca.infoway.io.psca-2.1.1-dft")
        self.repo_root = self.package_root.parents[1]
        self.examples_root = self.package_root / "examples"

    def load_foundation_context(self, query: PscaAssetQuery) -> PscaNormalizedAssetContext:
        """Load the first workflow-usable normalized PS-CA asset context."""
        package_payload = self._read_json(self.package_root / "package.json")
        self._validate_package_query(package_payload, query)

        index_entries = self._read_json(self.package_root / ".index.json")["files"]
        index_by_id = {entry["id"]: entry for entry in index_entries if entry.get("id")}

        selected_profiles = self._load_selected_profiles(index_by_id)
        workflow_profile_inventory = [
            selected_profiles.bundle,
            selected_profiles.composition,
            selected_profiles.patient,
            selected_profiles.practitioner,
            selected_profiles.practitioner_role,
            selected_profiles.organization,
        ]
        example_inventory = self._load_example_inventory() if query.include_example_inventory else []
        selected_bundle_example = self._load_selected_bundle_example(query.selected_example_bundle_filename)

        source_refs = [
            self._relative_ref(self.package_root / "package.json"),
            self._relative_ref(self.package_root / ".index.json"),
            *[self._relative_ref(self.package_root / profile.source_filename) for profile in workflow_profile_inventory],
            self._relative_ref(self.examples_root / query.selected_example_bundle_filename),
        ]

        package_summary = PscaPackageSummary(
            package_id=package_payload["name"],
            version=package_payload["version"],
            fhir_version=package_payload["fhirVersions"][0],
            canonical_url=package_payload["canonical"],
            index_entry_count=len(index_entries),
            structure_definition_count=sum(1 for entry in index_entries if entry.get("resourceType") == "StructureDefinition"),
            example_count=len(list(sorted(self.examples_root.glob("*.json")))),
            package_root=self._relative_ref(self.package_root),
        )

        return PscaNormalizedAssetContext(
            package_summary=package_summary,
            workflow_profile_inventory=workflow_profile_inventory,
            selected_profiles=selected_profiles,
            example_inventory=example_inventory,
            selected_bundle_example=selected_bundle_example,
            source_refs=source_refs,
        )

    def _load_selected_profiles(self, index_by_id: dict[str, dict[str, Any]]) -> PscaSelectedProfiles:
        summaries: dict[str, PscaWorkflowProfileSummary] = {}
        for role, profile_id in self._FOUNDATIONAL_PROFILE_IDS.items():
            index_entry = index_by_id.get(profile_id)
            if index_entry is None:
                raise FileNotFoundError(f"Required PS-CA profile '{profile_id}' is missing from .index.json.")

            profile_path = self.package_root / index_entry["filename"]
            if not profile_path.exists():
                raise FileNotFoundError(
                    f"Required PS-CA profile file '{index_entry['filename']}' for role '{role}' is missing."
                )

            payload = self._read_json(profile_path)
            differential_elements = payload.get("differential", {}).get("element", [])
            summaries[role] = PscaWorkflowProfileSummary(
                role=role,
                profile_id=payload["id"],
                resource_type=payload["type"],
                url=payload["url"],
                title=payload.get("title") or payload.get("name") or payload["id"],
                base_definition=payload.get("baseDefinition", ""),
                snapshot_element_count=len(payload.get("snapshot", {}).get("element", [])),
                differential_element_count=len(differential_elements),
                must_support_count=sum(1 for element in differential_elements if element.get("mustSupport")),
                source_filename=index_entry["filename"],
            )

        return PscaSelectedProfiles(
            bundle=summaries["bundle"],
            composition=summaries["composition"],
            patient=summaries["patient"],
            practitioner=summaries["practitioner"],
            practitioner_role=summaries["practitioner_role"],
            organization=summaries["organization"],
        )

    def _load_example_inventory(self) -> list[PscaExampleSummary]:
        inventory: list[PscaExampleSummary] = []
        for example_path in sorted(self.examples_root.glob("*.json")):
            payload = self._read_json(example_path)
            inventory.append(
                PscaExampleSummary(
                    filename=example_path.name,
                    resource_type=payload.get("resourceType", "Unknown"),
                    resource_id=payload.get("id"),
                )
            )
        return inventory

    def _load_selected_bundle_example(self, filename: str) -> PscaBundleExampleSummary:
        example_path = self.examples_root / filename
        if not example_path.exists():
            raise FileNotFoundError(f"Requested PS-CA bundle example '{filename}' was not found.")

        payload = self._read_json(example_path)
        if payload.get("resourceType") != "Bundle":
            raise ValueError(f"Requested example '{filename}' is not a Bundle resource.")

        entry_resource_types = [entry.get("resource", {}).get("resourceType", "Unknown") for entry in payload.get("entry", [])]
        composition = next(
            (entry.get("resource") for entry in payload.get("entry", []) if entry.get("resource", {}).get("resourceType") == "Composition"),
            None,
        )
        section_titles = [section.get("title", "") for section in composition.get("section", [])] if composition else []

        return PscaBundleExampleSummary(
            filename=filename,
            bundle_type=payload.get("type", "unknown"),
            entry_resource_types=entry_resource_types,
            composition_section_titles=section_titles,
        )

    def _validate_package_query(self, package_payload: dict[str, Any], query: PscaAssetQuery) -> None:
        actual_package_id = package_payload.get("name")
        actual_version = package_payload.get("version")
        if query.package_id != actual_package_id:
            raise ValueError(
                f"Unsupported PS-CA package id '{query.package_id}'. Expected '{actual_package_id}' for this repository."
            )
        if query.version != actual_version:
            raise ValueError(
                f"Unsupported PS-CA package version '{query.version}'. Expected '{actual_version}' for this repository."
            )

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _relative_ref(self, path: Path) -> str:
        return path.relative_to(self.repo_root).as_posix()
