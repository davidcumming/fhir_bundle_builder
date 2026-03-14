"""Deterministic filesystem-backed retrieval for bundled PS-CA assets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import (
    PscaAssetQuery,
    PscaBundleExampleSummary,
    PscaBundleExampleSectionSummary,
    PscaCompositionSectionDefinitionSummary,
    PscaCompositionSectionKey,
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
    _COMPOSITION_SECTION_KEYS: dict[str, PscaCompositionSectionKey] = {
        "sectionMedications": "medications",
        "sectionAllergies": "allergies",
        "sectionProblems": "problems",
        "sectionProceduresHx": "procedures_history",
        "sectionImmunizations": "immunizations",
        "sectionMedicalDevices": "medical_devices",
        "sectionResults": "results",
        "sectionVitalSigns": "vital_signs",
        "sectionPastIllnessHx": "past_illness_history",
        "sectionFunctionalStatus": "functional_status",
        "sectionPlanOfCare": "plan_of_care",
        "sectionSocialHistory": "social_history",
        "sectionPregnancyHx": "pregnancy_history",
        "sectionAdvanceDirectives": "advance_directives",
        "sectionFamilyHistory": "family_history",
        "sectionPatientStory": "patient_story",
    }
    _RESOURCE_TYPE_ALIASES: dict[str, str] = {
        "allergyintolerance": "AllergyIntolerance",
        "bundle": "Bundle",
        "composition": "Composition",
        "condition": "Condition",
        "deviceusestatement": "DeviceUseStatement",
        "diagnosticreport": "DiagnosticReport",
        "familymemberhistory": "FamilyMemberHistory",
        "imagingstudy": "ImagingStudy",
        "immunization": "Immunization",
        "medicationrequest": "MedicationRequest",
        "medicationstatement": "MedicationStatement",
        "observation": "Observation",
        "organization": "Organization",
        "patient": "Patient",
        "practitioner": "Practitioner",
        "practitionerrole": "PractitionerRole",
        "procedure": "Procedure",
        "specimen": "Specimen",
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
        composition_section_definitions = self._load_composition_section_definitions(
            selected_profiles.composition,
            index_by_id,
        )
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
            composition_section_definitions=composition_section_definitions,
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

    def _load_composition_section_definitions(
        self,
        composition_profile: PscaWorkflowProfileSummary,
        index_by_id: dict[str, dict[str, Any]],
    ) -> list[PscaCompositionSectionDefinitionSummary]:
        profile_path = self.package_root / composition_profile.source_filename
        payload = self._read_json(profile_path)
        differential_elements = payload.get("differential", {}).get("element", [])
        profile_type_cache: dict[str, str] = {}

        section_definitions: list[PscaCompositionSectionDefinitionSummary] = []
        for element in differential_elements:
            if element.get("path") != "Composition.section" or not element.get("sliceName"):
                continue

            slice_name = element["sliceName"]
            section_key = self._COMPOSITION_SECTION_KEYS.get(slice_name)
            if section_key is None:
                continue

            root_id = element["id"]
            title = self._find_section_title(differential_elements, root_id)
            loinc_code = self._find_section_loinc_code(differential_elements, root_id)
            allowed_entry_resource_types = self._find_section_entry_resource_types(
                differential_elements,
                root_id,
                index_by_id,
                profile_type_cache,
            )

            if loinc_code is None:
                raise ValueError(f"Composition section '{slice_name}' is missing a LOINC code pattern.")

            section_definitions.append(
                PscaCompositionSectionDefinitionSummary(
                    section_key=section_key,
                    slice_name=slice_name,
                    title=title,
                    loinc_code=loinc_code,
                    required=element.get("min", 0) > 0,
                    allowed_entry_resource_types=allowed_entry_resource_types,
                    source_profile_id=composition_profile.profile_id,
                )
            )

        if not section_definitions:
            raise ValueError("No Composition section definitions could be extracted from the PS-CA composition profile.")

        return section_definitions

    def _load_selected_bundle_example(self, filename: str) -> PscaBundleExampleSummary:
        example_path = self.examples_root / filename
        if not example_path.exists():
            raise FileNotFoundError(f"Requested PS-CA bundle example '{filename}' was not found.")

        payload = self._read_json(example_path)
        if payload.get("resourceType") != "Bundle":
            raise ValueError(f"Requested example '{filename}' is not a Bundle resource.")

        entries = payload.get("entry", [])
        entry_resource_types = [entry.get("resource", {}).get("resourceType", "Unknown") for entry in entries]
        resource_type_index = self._build_bundle_reference_type_index(entries)
        composition = next((entry.get("resource") for entry in entries if entry.get("resource", {}).get("resourceType") == "Composition"), None)
        section_titles = [section.get("title", "") for section in composition.get("section", [])] if composition else []
        composition_subject_resource_type = None
        composition_author_resource_types: list[str] = []
        section_summaries: list[PscaBundleExampleSectionSummary] = []

        if composition:
            composition_subject_resource_type = self._reference_to_resource_type(
                composition.get("subject", {}).get("reference"),
                resource_type_index,
            )
            composition_author_resource_types = [
                resource_type
                for resource_type in (
                    self._reference_to_resource_type(author.get("reference"), resource_type_index)
                    for author in composition.get("author", [])
                )
                if resource_type is not None
            ]
            section_summaries = [
                PscaBundleExampleSectionSummary(
                    title=section.get("title", ""),
                    loinc_code=self._extract_loinc_code(section.get("code", {})),
                    entry_resource_types=[
                        resource_type
                        for resource_type in (
                            self._reference_to_resource_type(entry.get("reference"), resource_type_index)
                            for entry in section.get("entry", [])
                        )
                        if resource_type is not None
                    ],
                )
                for section in composition.get("section", [])
            ]

        return PscaBundleExampleSummary(
            filename=filename,
            bundle_type=payload.get("type", "unknown"),
            entry_resource_types=entry_resource_types,
            composition_section_titles=section_titles,
            composition_subject_resource_type=composition_subject_resource_type,
            composition_author_resource_types=composition_author_resource_types,
            sections=section_summaries,
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

    @staticmethod
    def _extract_loinc_code(code_payload: dict[str, Any]) -> str | None:
        for coding in code_payload.get("coding", []):
            if coding.get("system") == "http://loinc.org" and coding.get("code"):
                return coding["code"]
        return None

    def _find_section_title(self, differential_elements: list[dict[str, Any]], root_id: str) -> str:
        title_element = next((element for element in differential_elements if element.get("id") == f"{root_id}.title"), None)
        if title_element:
            return (
                title_element.get("fixedString")
                or title_element.get("short")
                or title_element.get("definition")
                or self._humanize_slice_name(root_id.split(":")[-1])
            )

        root_element = next((element for element in differential_elements if element.get("id") == root_id), None)
        if root_element:
            return root_element.get("short") or root_element.get("definition") or self._humanize_slice_name(root_id.split(":")[-1])
        return self._humanize_slice_name(root_id.split(":")[-1])

    @staticmethod
    def _find_section_loinc_code(differential_elements: list[dict[str, Any]], root_id: str) -> str | None:
        code_element = next((element for element in differential_elements if element.get("id") == f"{root_id}.code"), None)
        if not code_element:
            return None
        coding = (code_element.get("patternCodeableConcept") or {}).get("coding", [])
        if not coding:
            return None
        return coding[0].get("code")

    def _find_section_entry_resource_types(
        self,
        differential_elements: list[dict[str, Any]],
        root_id: str,
        index_by_id: dict[str, dict[str, Any]],
        profile_type_cache: dict[str, str],
    ) -> list[str]:
        resource_types: list[str] = []
        prefix = f"{root_id}.entry:"
        for element in differential_elements:
            if not str(element.get("id", "")).startswith(prefix):
                continue

            for type_payload in element.get("type", []):
                for target_profile in type_payload.get("targetProfile", []):
                    profile_id = target_profile.rstrip("/").split("/")[-1]
                    try:
                        resource_type = self._resolve_profile_resource_type(profile_id, index_by_id, profile_type_cache)
                    except FileNotFoundError:
                        continue
                    if resource_type not in resource_types:
                        resource_types.append(resource_type)
        return resource_types

    def _resolve_profile_resource_type(
        self,
        profile_id: str,
        index_by_id: dict[str, dict[str, Any]],
        profile_type_cache: dict[str, str],
    ) -> str:
        if profile_id in profile_type_cache:
            return profile_type_cache[profile_id]

        index_entry = index_by_id.get(profile_id)
        if index_entry is None:
            inferred_resource_type = self._infer_resource_type_from_profile_id(profile_id)
            if inferred_resource_type is not None:
                profile_type_cache[profile_id] = inferred_resource_type
                return inferred_resource_type
            raise FileNotFoundError(f"Profile '{profile_id}' referenced by Composition section is missing from .index.json.")

        profile_path = self.package_root / index_entry["filename"]
        if not profile_path.exists():
            inferred_resource_type = self._infer_resource_type_from_profile_id(profile_id)
            if inferred_resource_type is not None:
                profile_type_cache[profile_id] = inferred_resource_type
                return inferred_resource_type
            raise FileNotFoundError(f"Profile '{profile_id}' referenced by Composition section is missing file '{index_entry['filename']}'.")

        resource_type = self._read_json(profile_path)["type"]
        profile_type_cache[profile_id] = resource_type
        return resource_type

    @staticmethod
    def _humanize_slice_name(slice_name: str) -> str:
        name = slice_name.removeprefix("section")
        chars: list[str] = []
        for index, char in enumerate(name):
            if index > 0 and char.isupper() and name[index - 1].islower():
                chars.append(" ")
            chars.append(char)
        return "".join(chars) or slice_name

    @staticmethod
    def _build_bundle_reference_type_index(entries: list[dict[str, Any]]) -> dict[str, str]:
        index: dict[str, str] = {}
        for entry in entries:
            resource = entry.get("resource", {})
            resource_type = resource.get("resourceType")
            resource_id = resource.get("id")
            if resource_type is None:
                continue
            full_url = entry.get("fullUrl")
            if full_url:
                index[full_url] = resource_type
            if resource_id:
                index[f"{resource_type}/{resource_id}"] = resource_type
                index[resource_id] = resource_type
        return index

    def _reference_to_resource_type(self, reference: str | None, resource_type_index: dict[str, str]) -> str | None:
        if not reference:
            return None
        if reference in resource_type_index:
            return resource_type_index[reference]

        parsed_reference = reference.rstrip("/").split("/")
        if len(parsed_reference) >= 2:
            candidate = "/".join(parsed_reference[-2:])
            if candidate in resource_type_index:
                return resource_type_index[candidate]
            return parsed_reference[-2]
        return resource_type_index.get(reference)

    def _infer_resource_type_from_profile_id(self, profile_id: str) -> str | None:
        leading_token = profile_id.split("-")[0]
        if leading_token in self._RESOURCE_TYPE_ALIASES.values():
            return leading_token
        return self._RESOURCE_TYPE_ALIASES.get(leading_token.lower())

    def _relative_ref(self, path: Path) -> str:
        return path.relative_to(self.repo_root).as_posix()
