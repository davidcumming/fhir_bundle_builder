"""Deterministic PS-CA scaffold construction from the build plan and schematic."""

from __future__ import annotations

from copy import deepcopy

from .models import (
    BuildPlan,
    BuildPlanStep,
    BundleSchematic,
    ReferenceContribution,
    ResourceConstructionEvidence,
    ResourceConstructionStageResult,
    ResourceConstructionStepResult,
    ResourceRegistryEntry,
    ResourceScaffoldArtifact,
    ResourcePlaceholder,
    SectionScaffold,
)


def build_psca_resource_construction_result(
    plan: BuildPlan,
    schematic: BundleSchematic,
) -> ResourceConstructionStageResult:
    """Build deterministic scaffold artifacts for the current PS-CA build plan."""

    placeholders = {placeholder.placeholder_id: placeholder for placeholder in schematic.resource_placeholders}
    sections = {section.section_key: section for section in schematic.section_scaffolds}
    registry: dict[str, ResourceRegistryEntry] = {}
    registry_order: list[str] = []
    step_results: list[ResourceConstructionStepResult] = []

    for step in plan.steps:
        placeholder = _require_placeholder(placeholders, step.target_placeholder_id)
        prior_entry = registry.get(step.target_placeholder_id)
        result = _build_step_result(step, placeholder, sections, prior_entry)
        step_results.append(result)

        registry[result.target_placeholder_id] = ResourceRegistryEntry(
            placeholder_id=result.target_placeholder_id,
            resource_type=result.resource_type,
            latest_step_id=result.step_id,
            current_scaffold=result.resource_scaffold,
        )
        if result.target_placeholder_id not in registry_order:
            registry_order.append(result.target_placeholder_id)

    return ResourceConstructionStageResult(
        stage_id="resource_construction",
        status="placeholder_complete",
        summary="Constructed deterministic PS-CA resource scaffolds for the current build plan and tracked the latest scaffold state per placeholder.",
        placeholder_note="Scaffolds are partial FHIR-shaped artifacts only; full clinical population, full bundle assembly, and validation remain deferred.",
        source_refs=plan.source_refs,
        construction_mode="deterministic_scaffold_only",
        step_results=step_results,
        resource_registry=[registry[placeholder_id] for placeholder_id in registry_order],
        deferred_items=[
            "Clinical data-element population remains deferred.",
            "Generated ids and UUID replacement remain deferred.",
            "Full bundle-in-progress assembly logic remains deferred.",
            "Validation-driven reconstruction remains deferred.",
        ],
        unresolved_items=[
            "No element-level construction beyond minimal deterministic scaffolds has been implemented.",
            "No full bundle patching or entry ordering logic exists yet.",
        ],
        evidence=ResourceConstructionEvidence(
            source_build_plan_stage_id=plan.stage_id,
            source_build_plan_basis=plan.plan_basis,
            source_schematic_stage_id=schematic.stage_id,
            planned_step_ids=[step.step_id for step in plan.steps],
            source_refs=plan.source_refs,
        ),
    )


def _build_step_result(
    step: BuildPlanStep,
    placeholder: ResourcePlaceholder,
    sections: dict[str, SectionScaffold],
    prior_entry: ResourceRegistryEntry | None,
) -> ResourceConstructionStepResult:
    if step.step_kind == "anchor_resource":
        return _build_anchor_result(step, placeholder)
    if step.step_kind == "support_resource":
        if step.resource_type == "PractitionerRole":
            return _build_practitioner_role_result(step, placeholder)
        return _build_anchor_result(step, placeholder)
    if step.step_kind == "section_entry_resource":
        return _build_section_entry_result(step, placeholder)
    if step.step_kind == "composition_scaffold":
        return _build_composition_scaffold_result(step, placeholder)
    if step.step_kind == "composition_finalize":
        if prior_entry is None:
            raise ValueError("Composition finalization requires an existing registry entry for the Composition scaffold.")
        return _build_composition_finalize_result(step, placeholder, sections, prior_entry)
    raise ValueError(f"Unsupported build step kind '{step.step_kind}'.")


def _build_anchor_result(step: BuildPlanStep, placeholder: ResourcePlaceholder) -> ResourceConstructionStepResult:
    scaffold_dict = _base_scaffold(placeholder)
    populated_paths = _base_populated_paths(placeholder)
    extra_deferred: list[str] = []
    warnings: list[str] = []
    assumptions = [
        "This scaffold only establishes deterministic base metadata.",
        "No business or clinical content has been populated yet.",
    ]

    if step.resource_type == "Patient":
        extra_deferred = ["gender", "birthDate"]
    elif step.resource_type == "Practitioner":
        extra_deferred = ["name"]
    elif step.resource_type == "Organization":
        extra_deferred = ["name"]

    resource_scaffold = ResourceScaffoldArtifact(
        placeholder_id=placeholder.placeholder_id,
        resource_type=placeholder.resource_type,
        profile_url=placeholder.profile_url,
        scaffold_state="base_scaffold_created",
        fhir_scaffold=scaffold_dict,
        populated_paths=populated_paths,
        deferred_paths=_merge_deferred_paths(placeholder.required_later_fields, extra_deferred, populated_paths),
        source_step_ids=[step.step_id],
    )

    return ResourceConstructionStepResult(
        step_id=step.step_id,
        step_kind=step.step_kind,
        resource_type=step.resource_type,
        target_placeholder_id=step.target_placeholder_id,
        execution_status="scaffold_created",
        resource_scaffold=resource_scaffold,
        assumptions=assumptions,
        warnings=warnings,
        unresolved_fields=resource_scaffold.deferred_paths,
    )


def _build_practitioner_role_result(step: BuildPlanStep, placeholder: ResourcePlaceholder) -> ResourceConstructionStepResult:
    scaffold_dict = _base_scaffold(placeholder)
    scaffold_dict["practitioner"] = {"reference": "Practitioner/practitioner-1"}
    scaffold_dict["organization"] = {"reference": "Organization/organization-1"}
    populated_paths = _base_populated_paths(placeholder) + ["practitioner.reference", "organization.reference"]
    resource_scaffold = ResourceScaffoldArtifact(
        placeholder_id=placeholder.placeholder_id,
        resource_type=placeholder.resource_type,
        profile_url=placeholder.profile_url,
        scaffold_state="references_attached",
        fhir_scaffold=scaffold_dict,
        populated_paths=populated_paths,
        deferred_paths=_merge_deferred_paths(placeholder.required_later_fields, ["code"], populated_paths),
        source_step_ids=[step.step_id],
    )

    return ResourceConstructionStepResult(
        step_id=step.step_id,
        step_kind=step.step_kind,
        resource_type=step.resource_type,
        target_placeholder_id=step.target_placeholder_id,
        execution_status="scaffold_created",
        resource_scaffold=resource_scaffold,
        reference_contributions=[
            _reference_contribution("practitioner.reference", "practitioner-1", "Practitioner/practitioner-1"),
            _reference_contribution("organization.reference", "organization-1", "Organization/organization-1"),
        ],
        assumptions=[
            "PractitionerRole is scaffolded with deterministic local references only.",
        ],
        warnings=[],
        unresolved_fields=resource_scaffold.deferred_paths,
    )


def _build_section_entry_result(step: BuildPlanStep, placeholder: ResourcePlaceholder) -> ResourceConstructionStepResult:
    scaffold_dict = _base_scaffold(placeholder)
    reference_path, reference_value = _section_subject_reference(step.resource_type)
    parent_key = reference_path.split(".")[0]
    scaffold_dict[parent_key] = {"reference": reference_value}
    populated_paths = _base_populated_paths(placeholder) + [reference_path]
    resource_scaffold = ResourceScaffoldArtifact(
        placeholder_id=placeholder.placeholder_id,
        resource_type=placeholder.resource_type,
        profile_url=placeholder.profile_url,
        scaffold_state="references_attached",
        fhir_scaffold=scaffold_dict,
        populated_paths=populated_paths,
        deferred_paths=_merge_deferred_paths(
            placeholder.required_later_fields,
            _extra_deferred_paths_for_resource(step.resource_type),
            populated_paths,
        ),
        source_step_ids=[step.step_id],
    )

    return ResourceConstructionStepResult(
        step_id=step.step_id,
        step_kind=step.step_kind,
        resource_type=step.resource_type,
        target_placeholder_id=step.target_placeholder_id,
        execution_status="scaffold_created",
        resource_scaffold=resource_scaffold,
        reference_contributions=[_reference_contribution(reference_path, "patient-1", reference_value)],
        assumptions=[
            "Section-entry resources are scaffolded with only the minimal patient-linked reference for this slice.",
        ],
        warnings=[],
        unresolved_fields=resource_scaffold.deferred_paths,
    )


def _build_composition_scaffold_result(step: BuildPlanStep, placeholder: ResourcePlaceholder) -> ResourceConstructionStepResult:
    scaffold_dict = _base_scaffold(placeholder)
    scaffold_dict["type"] = {
        "coding": [
            {
                "system": "http://loinc.org",
                "code": "60591-5",
                "display": "Patient summary Document",
            }
        ]
    }
    scaffold_dict["subject"] = {"reference": "Patient/patient-1"}
    scaffold_dict["author"] = [{"reference": "PractitionerRole/practitionerrole-1"}]
    scaffold_dict["section"] = []
    populated_paths = _base_populated_paths(placeholder) + [
        "type.coding[0].system",
        "type.coding[0].code",
        "type.coding[0].display",
        "subject.reference",
        "author[0].reference",
        "section",
    ]
    resource_scaffold = ResourceScaffoldArtifact(
        placeholder_id=placeholder.placeholder_id,
        resource_type=placeholder.resource_type,
        profile_url=placeholder.profile_url,
        scaffold_state="composition_scaffold_created",
        fhir_scaffold=scaffold_dict,
        populated_paths=populated_paths,
        deferred_paths=_merge_deferred_paths(placeholder.required_later_fields, ["status", "title", "date"], populated_paths),
        source_step_ids=[step.step_id],
    )

    return ResourceConstructionStepResult(
        step_id=step.step_id,
        step_kind=step.step_kind,
        resource_type=step.resource_type,
        target_placeholder_id=step.target_placeholder_id,
        execution_status="scaffold_created",
        resource_scaffold=resource_scaffold,
        reference_contributions=[
            _reference_contribution("subject.reference", "patient-1", "Patient/patient-1"),
            _reference_contribution("author[0].reference", "practitionerrole-1", "PractitionerRole/practitionerrole-1"),
        ],
        assumptions=[
            "Composition scaffold is created before section entries are attached.",
        ],
        warnings=[],
        unresolved_fields=resource_scaffold.deferred_paths,
    )


def _build_composition_finalize_result(
    step: BuildPlanStep,
    placeholder: ResourcePlaceholder,
    sections: dict[str, SectionScaffold],
    prior_entry: ResourceRegistryEntry,
) -> ResourceConstructionStepResult:
    prior_scaffold = prior_entry.current_scaffold
    scaffold_dict = deepcopy(prior_scaffold.fhir_scaffold)
    section_blocks: list[dict[str, object]] = []
    reference_contributions: list[ReferenceContribution] = []
    populated_paths = list(prior_scaffold.populated_paths)

    for index, section_key in enumerate(("medications", "allergies", "problems")):
        section = sections.get(section_key)
        if section is None:
            raise ValueError(f"Missing section scaffold '{section_key}' required for Composition finalization.")
        entry_placeholder_id = section.entry_placeholder_ids[0]
        entry_reference = _local_reference_for_placeholder(entry_placeholder_id)
        section_blocks.append(
            {
                "title": section.title,
                "code": {"coding": [{"system": "http://loinc.org", "code": section.loinc_code}]},
                "entry": [{"reference": entry_reference}],
            }
        )
        populated_paths.extend(
            [
                f"section[{index}].title",
                f"section[{index}].code.coding[0].system",
                f"section[{index}].code.coding[0].code",
                f"section[{index}].entry[0].reference",
            ]
        )
        reference_contributions.append(
            _reference_contribution(
                f"section[{index}].entry[0].reference",
                entry_placeholder_id,
                entry_reference,
            )
        )

    scaffold_dict["section"] = section_blocks
    resource_scaffold = ResourceScaffoldArtifact(
        placeholder_id=placeholder.placeholder_id,
        resource_type=placeholder.resource_type,
        profile_url=placeholder.profile_url,
        scaffold_state="sections_attached",
        fhir_scaffold=scaffold_dict,
        populated_paths=_dedupe_paths(populated_paths),
        deferred_paths=_merge_deferred_paths(placeholder.required_later_fields, ["status", "title", "date"], populated_paths),
        source_step_ids=prior_scaffold.source_step_ids + [step.step_id],
    )

    return ResourceConstructionStepResult(
        step_id=step.step_id,
        step_kind=step.step_kind,
        resource_type=step.resource_type,
        target_placeholder_id=step.target_placeholder_id,
        execution_status="scaffold_updated",
        resource_scaffold=resource_scaffold,
        reference_contributions=reference_contributions,
        assumptions=[
            "Composition finalization only attaches deterministic section metadata and local entry references.",
        ],
        warnings=[],
        unresolved_fields=resource_scaffold.deferred_paths,
    )


def _require_placeholder(
    placeholders: dict[str, ResourcePlaceholder],
    placeholder_id: str,
) -> ResourcePlaceholder:
    placeholder = placeholders.get(placeholder_id)
    if placeholder is None:
        raise ValueError(f"Required placeholder '{placeholder_id}' is missing from the schematic.")
    return placeholder


def _base_scaffold(placeholder: ResourcePlaceholder) -> dict[str, object]:
    scaffold: dict[str, object] = {
        "resourceType": placeholder.resource_type,
        "id": placeholder.placeholder_id,
    }
    if placeholder.profile_url:
        scaffold["meta"] = {"profile": [placeholder.profile_url]}
    return scaffold


def _base_populated_paths(placeholder: ResourcePlaceholder) -> list[str]:
    populated = ["resourceType", "id"]
    if placeholder.profile_url:
        populated.append("meta.profile[0]")
    return populated


def _merge_deferred_paths(
    placeholder_required_later_fields: list[str],
    extra_deferred_paths: list[str],
    populated_paths: list[str],
) -> list[str]:
    populated_roots = {path.split(".")[0].split("[")[0] for path in populated_paths}
    deferred = [
        path
        for path in [*placeholder_required_later_fields, *extra_deferred_paths]
        if path.split(".")[0].split("[")[0] not in populated_roots
    ]
    return _dedupe_paths(deferred)


def _extra_deferred_paths_for_resource(resource_type: str) -> list[str]:
    if resource_type == "MedicationRequest":
        return ["status", "intent", "medication[x]"]
    if resource_type == "AllergyIntolerance":
        return ["clinicalStatus", "code"]
    if resource_type == "Condition":
        return ["clinicalStatus", "code"]
    return []


def _section_subject_reference(resource_type: str) -> tuple[str, str]:
    if resource_type == "MedicationRequest":
        return "subject.reference", "Patient/patient-1"
    if resource_type == "AllergyIntolerance":
        return "patient.reference", "Patient/patient-1"
    if resource_type == "Condition":
        return "subject.reference", "Patient/patient-1"
    raise ValueError(f"Unsupported section-entry resource type '{resource_type}'.")


def _reference_contribution(reference_path: str, target_placeholder_id: str, reference_value: str) -> ReferenceContribution:
    return ReferenceContribution(
        reference_path=reference_path,
        target_placeholder_id=target_placeholder_id,
        reference_value=reference_value,
        status="applied",
    )


def _local_reference_for_placeholder(placeholder_id: str) -> str:
    resource_type = placeholder_id.split("-", 1)[0]
    if resource_type == "practitionerrole":
        return f"PractitionerRole/{placeholder_id}"
    if resource_type == "allergyintolerance":
        return f"AllergyIntolerance/{placeholder_id}"
    if resource_type == "medicationrequest":
        return f"MedicationRequest/{placeholder_id}"
    if resource_type == "condition":
        return f"Condition/{placeholder_id}"
    if resource_type == "patient":
        return f"Patient/{placeholder_id}"
    if resource_type == "practitioner":
        return f"Practitioner/{placeholder_id}"
    if resource_type == "organization":
        return f"Organization/{placeholder_id}"
    if resource_type == "composition":
        return f"Composition/{placeholder_id}"
    raise ValueError(f"Unsupported placeholder id '{placeholder_id}' for local reference generation.")


def _dedupe_paths(paths: list[str]) -> list[str]:
    ordered: list[str] = []
    for path in paths:
        if path not in ordered:
            ordered.append(path)
    return ordered
