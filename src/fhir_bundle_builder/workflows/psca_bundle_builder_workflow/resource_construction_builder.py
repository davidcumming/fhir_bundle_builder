"""Deterministic PS-CA scaffold construction from the build plan and schematic."""

from __future__ import annotations

from copy import deepcopy

from fhir_bundle_builder.validation import (
    PlaceholderTraceabilitySummary,
    TraceabilityDrivingInput,
)

from .models import (
    BuildPlan,
    BuildPlanStep,
    BundleSchematic,
    DeterministicValueEvidence,
    NormalizedBuildRequest,
    ReferenceContribution,
    ResourceConstructionEvidence,
    ResourceConstructionRepairDirective,
    ResourceConstructionStageResult,
    ResourceConstructionStepResult,
    ResourceRegistryEntry,
    ResourceScaffoldArtifact,
    ResourcePlaceholder,
    SectionScaffold,
)

_REQUIRED_COMPOSITION_SECTION_KEYS = ("medications", "allergies", "problems")
SELECTED_PROVIDER_ORGANIZATION_IDENTIFIER_SYSTEM = (
    "urn:fhir-bundle-builder:selected-provider-organization-identifier"
)
SELECTED_PROVIDER_ROLE_RELATIONSHIP_IDENTIFIER_SYSTEM = (
    "urn:fhir-bundle-builder:selected-provider-role-relationship-identifier"
)


def build_psca_resource_construction_result(
    plan: BuildPlan,
    schematic: BundleSchematic,
    normalized_request: NormalizedBuildRequest,
    prior_result: ResourceConstructionStageResult | None = None,
    repair_directive: ResourceConstructionRepairDirective | None = None,
) -> ResourceConstructionStageResult:
    """Build deterministic enriched PS-CA resource scaffolds for the current build plan."""

    if repair_directive is not None and prior_result is None:
        raise ValueError("Targeted resource construction repair requires a prior construction result.")

    placeholders = {placeholder.placeholder_id: placeholder for placeholder in schematic.resource_placeholders}
    sections = {section.section_key: section for section in schematic.section_scaffolds}
    registry, registry_order = _initialize_registry(prior_result)
    step_results: list[ResourceConstructionStepResult] = []
    targeted_step_ids = _targeted_step_ids(plan, repair_directive)

    for step in plan.steps:
        if targeted_step_ids is not None and step.step_id not in targeted_step_ids:
            continue
        placeholder = _require_placeholder(placeholders, step.target_placeholder_id)
        prior_entry = registry.get(step.target_placeholder_id)
        result = _build_step_result(step, placeholder, sections, prior_entry, normalized_request)
        step_results.append(result)

        registry[result.target_placeholder_id] = ResourceRegistryEntry(
            placeholder_id=result.target_placeholder_id,
            resource_type=result.resource_type,
            latest_step_id=result.step_id,
            current_scaffold=result.resource_scaffold,
        )
        if result.target_placeholder_id not in registry_order:
            registry_order.append(result.target_placeholder_id)

    regenerated_placeholder_ids = _regenerated_placeholder_ids(step_results)
    reused_placeholder_ids = _reused_placeholder_ids(registry_order, regenerated_placeholder_ids)
    step_result_history = _step_result_history(plan, prior_result, step_results)
    step_results_by_id = {step_result.step_id: step_result for step_result in step_result_history}
    execution_scope = "targeted_repair" if repair_directive is not None else "full_build"
    summary = (
        "Applied a deterministic targeted repair directive to rerun only selected resource-construction steps "
        "and merged the regenerated scaffolds back into the registry."
        if repair_directive is not None
        else "Constructed deterministic content-enriched PS-CA resource scaffolds for the current build plan and tracked the latest scaffold state per placeholder."
    )
    placeholder_note = (
        "This targeted repair reruns only the directive-selected construction steps; untouched registry entries are reused from the prior result."
        if repair_directive is not None
        else "Resources now include a narrow deterministic content layer only; full clinical/provider population, bundle identity policy, and rich terminology remain deferred."
    )

    return ResourceConstructionStageResult(
        stage_id="resource_construction",
        status="placeholder_complete",
        summary=summary,
        placeholder_note=placeholder_note,
        source_refs=plan.source_refs,
        construction_mode="deterministic_content_enriched",
        execution_scope=execution_scope,
        applied_repair_directive=repair_directive,
        regenerated_placeholder_ids=regenerated_placeholder_ids,
        reused_placeholder_ids=reused_placeholder_ids,
        step_results=step_results,
        step_result_history=step_result_history,
        resource_registry=[registry[placeholder_id] for placeholder_id in registry_order],
        deferred_items=[
            "Broad clinical data-element population remains deferred.",
            "Patient-scenario-specific provider organization and provider-role selection logic remains deferred.",
            "Generated ids and UUID replacement remain deferred.",
            "Full bundle-in-progress assembly logic remains deferred.",
            "Validation-driven reconstruction remains deferred.",
        ],
        unresolved_items=[
            "Only a narrow deterministic content policy has been implemented for core PS-CA resources.",
            "Support-resource enrichment now uses only the normalized selected provider/org/role context and still defers broader provider-management semantics.",
            "No full bundle patching or entry ordering logic exists yet.",
            *(
                [
                    "Grouped validation findings still require grouped repair directives rather than single-element repair patches."
                ]
                if repair_directive is not None
                else []
            ),
        ],
        evidence=ResourceConstructionEvidence(
            source_build_plan_stage_id=plan.stage_id,
            source_build_plan_basis=plan.plan_basis,
            source_schematic_stage_id=schematic.stage_id,
            planned_step_ids=[step.step_id for step in plan.steps],
            placeholder_traceability_summaries=_placeholder_traceability_summaries(
                schematic,
                placeholders,
                registry,
                step_results_by_id,
            ),
            source_refs=plan.source_refs,
        ),
    )


def _initialize_registry(
    prior_result: ResourceConstructionStageResult | None,
) -> tuple[dict[str, ResourceRegistryEntry], list[str]]:
    if prior_result is None:
        return {}, []
    registry = {
        entry.placeholder_id: ResourceRegistryEntry.model_validate(entry.model_dump())
        for entry in prior_result.resource_registry
    }
    return registry, [entry.placeholder_id for entry in prior_result.resource_registry]


def _targeted_step_ids(
    plan: BuildPlan,
    repair_directive: ResourceConstructionRepairDirective | None,
) -> set[str] | None:
    if repair_directive is None:
        return None

    valid_step_ids = {step.step_id for step in plan.steps}
    unknown_step_ids = [step_id for step_id in repair_directive.target_step_ids if step_id not in valid_step_ids]
    if unknown_step_ids:
        raise ValueError(
            "Resource construction repair directive referenced unknown build-plan steps: "
            f"{', '.join(unknown_step_ids)}."
        )
    return set(repair_directive.target_step_ids)


def _regenerated_placeholder_ids(step_results: list[ResourceConstructionStepResult]) -> list[str]:
    ordered: list[str] = []
    for step_result in step_results:
        if step_result.target_placeholder_id not in ordered:
            ordered.append(step_result.target_placeholder_id)
    return ordered


def _reused_placeholder_ids(
    registry_order: list[str],
    regenerated_placeholder_ids: list[str],
) -> list[str]:
    regenerated = set(regenerated_placeholder_ids)
    return [placeholder_id for placeholder_id in registry_order if placeholder_id not in regenerated]


def _step_result_history(
    plan: BuildPlan,
    prior_result: ResourceConstructionStageResult | None,
    step_results: list[ResourceConstructionStepResult],
) -> list[ResourceConstructionStepResult]:
    latest_by_step_id = {
        step_result.step_id: step_result
        for step_result in (
            prior_result.step_result_history
            if prior_result is not None and prior_result.step_result_history
            else (prior_result.step_results if prior_result is not None else [])
        )
    }
    latest_by_step_id.update({step_result.step_id: step_result for step_result in step_results})
    return [
        latest_by_step_id[step.step_id]
        for step in plan.steps
        if step.step_id in latest_by_step_id
    ]


def _placeholder_traceability_summaries(
    schematic: BundleSchematic,
    placeholders: dict[str, ResourcePlaceholder],
    registry: dict[str, ResourceRegistryEntry],
    step_results_by_id: dict[str, ResourceConstructionStepResult],
) -> list[PlaceholderTraceabilitySummary]:
    ordered_placeholder_ids = [
        relationship.target_id
        for relationship in schematic.relationships
        if relationship.relationship_type == "bundle_entry"
    ]
    summaries: list[PlaceholderTraceabilitySummary] = []
    for placeholder_id in ordered_placeholder_ids:
        placeholder = placeholders.get(placeholder_id)
        registry_entry = registry.get(placeholder_id)
        if placeholder is None or registry_entry is None:
            continue
        summaries.append(
            PlaceholderTraceabilitySummary(
                placeholder_id=placeholder_id,
                resource_type=placeholder.resource_type,
                role=placeholder.role,
                section_keys=list(placeholder.section_keys),
                driving_inputs=_driving_inputs_for_placeholder(
                    registry_entry.current_scaffold.source_step_ids,
                    step_results_by_id,
                ),
                source_step_ids=list(registry_entry.current_scaffold.source_step_ids),
                latest_step_id=registry_entry.latest_step_id,
            )
        )
    return summaries


def _driving_inputs_for_placeholder(
    source_step_ids: list[str],
    step_results_by_id: dict[str, ResourceConstructionStepResult],
) -> list[TraceabilityDrivingInput]:
    driving_inputs: list[TraceabilityDrivingInput] = []
    seen: set[tuple[str, str]] = set()
    for step_id in source_step_ids:
        step_result = step_results_by_id.get(step_id)
        if step_result is None:
            continue
        for evidence in step_result.deterministic_value_evidence:
            key = (evidence.source_artifact, evidence.source_detail)
            if key in seen:
                continue
            seen.add(key)
            driving_inputs.append(
                TraceabilityDrivingInput(
                    source_artifact=evidence.source_artifact,
                    source_detail=evidence.source_detail,
                )
            )
    return driving_inputs


def _build_step_result(
    step: BuildPlanStep,
    placeholder: ResourcePlaceholder,
    sections: dict[str, SectionScaffold],
    prior_entry: ResourceRegistryEntry | None,
    normalized_request: NormalizedBuildRequest,
) -> ResourceConstructionStepResult:
    if step.step_kind == "anchor_resource":
        return _build_anchor_result(step, placeholder, normalized_request)
    if step.step_kind == "support_resource":
        if step.resource_type == "PractitionerRole":
            return _build_practitioner_role_result(step, placeholder, normalized_request)
        return _build_anchor_result(step, placeholder, normalized_request)
    if step.step_kind == "section_entry_resource":
        return _build_section_entry_result(step, placeholder, sections, normalized_request)
    if step.step_kind == "composition_scaffold":
        return _build_composition_scaffold_result(step, placeholder, normalized_request)
    if step.step_kind == "composition_finalize":
        if prior_entry is None:
            raise ValueError("Composition finalization requires an existing registry entry for the Composition scaffold.")
        return _build_composition_finalize_result(step, placeholder, sections, prior_entry)
    raise ValueError(f"Unsupported build step kind '{step.step_kind}'.")


def _build_anchor_result(
    step: BuildPlanStep,
    placeholder: ResourcePlaceholder,
    normalized_request: NormalizedBuildRequest,
) -> ResourceConstructionStepResult:
    scaffold_dict = _base_scaffold(placeholder)
    populated_paths = _base_populated_paths(placeholder)
    extra_deferred: list[str] = []
    warnings: list[str] = []
    deterministic_value_evidence: list[DeterministicValueEvidence] = []
    assumptions = [
        "This scaffold establishes deterministic base metadata first.",
    ]

    if step.resource_type == "Patient":
        patient = normalized_request.patient_context.patient
        scaffold_dict["active"] = True
        scaffold_dict["identifier"] = [{"value": patient.patient_id}]
        scaffold_dict["name"] = [{"text": patient.display_name}]
        populated_paths += ["active", "identifier[0].value", "name[0].text"]
        deterministic_value_evidence.extend(
            [
                _value_evidence(
                    "active",
                    "deterministic_content_policy",
                    "Patient active flag is fixed to true for the first meaningful content slice.",
                ),
                _value_evidence(
                    "identifier[0].value",
                    "normalized_request.patient_context.patient",
                    "patient.patient_id",
                ),
                _value_evidence(
                    "name[0].text",
                    "normalized_request.patient_context.patient",
                    "patient.display_name",
                ),
            ]
        )
        extra_deferred = ["gender", "birthDate"]
        if patient.administrative_gender is not None:
            scaffold_dict["gender"] = patient.administrative_gender
            populated_paths.append("gender")
            deterministic_value_evidence.append(
                _value_evidence(
                    "gender",
                    "normalized_request.patient_context.patient",
                    "patient.administrative_gender",
                )
            )
        if patient.birth_date is not None:
            scaffold_dict["birthDate"] = patient.birth_date
            populated_paths.append("birthDate")
            deterministic_value_evidence.append(
                _value_evidence(
                    "birthDate",
                    "normalized_request.patient_context.patient",
                    "patient.birth_date",
                )
            )
        assumptions.append(
            "Patient identity content is derived deterministically from the normalized patient identity context."
        )
    elif step.resource_type == "Practitioner":
        provider = normalized_request.provider_context.provider
        scaffold_dict["active"] = True
        scaffold_dict["identifier"] = [{"value": provider.provider_id}]
        scaffold_dict["name"] = [{"text": provider.display_name}]
        populated_paths += ["active", "identifier[0].value", "name[0].text"]
        deterministic_value_evidence.extend(
            [
                _value_evidence(
                    "active",
                    "deterministic_content_policy",
                    "Practitioner active flag is fixed to true for the support-resource enrichment slice.",
                ),
                _value_evidence(
                    "identifier[0].value",
                    "normalized_request.provider_context.provider",
                    "provider.provider_id",
                ),
                _value_evidence(
                    "name[0].text",
                    "normalized_request.provider_context.provider",
                    "provider.display_name",
                ),
            ]
        )
        extra_deferred = ["telecom", "address", "qualification"]
        assumptions.append(
            "Practitioner identity content is derived deterministically from the normalized provider identity context."
        )
    elif step.resource_type == "Organization":
        selected_organization = normalized_request.provider_context.selected_organization
        if selected_organization is not None:
            scaffold_dict["identifier"] = [
                {
                    "system": SELECTED_PROVIDER_ORGANIZATION_IDENTIFIER_SYSTEM,
                    "value": selected_organization.organization_id,
                }
            ]
            scaffold_dict["name"] = selected_organization.display_name
            populated_paths += ["identifier[0].system", "identifier[0].value", "name"]
            deterministic_value_evidence.extend(
                [
                    _value_evidence(
                        "identifier[0].system",
                        "deterministic_content_policy",
                        "fixed selected provider organization identifier system",
                    ),
                    _value_evidence(
                        "identifier[0].value",
                        "normalized_request.provider_context.selected_organization",
                        "organization_id",
                    ),
                    _value_evidence(
                        "name",
                        "normalized_request.provider_context.selected_organization",
                        "display_name",
                    ),
                ]
            )
            assumptions.append(
                "Organization identity content is derived deterministically from the normalized selected organization context, including a fixed identifier system."
            )
        else:
            extra_deferred = ["name"]
            assumptions.append(
                "Organization content remains base metadata only when legacy provider input does not supply a selected organization."
            )

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
        deterministic_value_evidence=deterministic_value_evidence,
        assumptions=assumptions,
        warnings=warnings,
        unresolved_fields=resource_scaffold.deferred_paths,
    )


def _build_practitioner_role_result(
    step: BuildPlanStep,
    placeholder: ResourcePlaceholder,
    normalized_request: NormalizedBuildRequest,
) -> ResourceConstructionStepResult:
    scaffold_dict = _base_scaffold(placeholder)
    scaffold_dict["practitioner"] = {"reference": "Practitioner/practitioner-1"}
    scaffold_dict["organization"] = {"reference": "Organization/organization-1"}
    selected_relationship = normalized_request.provider_context.selected_provider_role_relationship
    if selected_relationship is not None:
        scaffold_dict["identifier"] = [
            {
                "system": SELECTED_PROVIDER_ROLE_RELATIONSHIP_IDENTIFIER_SYSTEM,
                "value": selected_relationship.relationship_id,
            }
        ]
    role_text = (
        selected_relationship.role_label
        if selected_relationship is not None
        else placeholder.role
    )
    scaffold_dict["code"] = [{"text": role_text}]
    populated_paths = _base_populated_paths(placeholder) + [
        "practitioner.reference",
        "organization.reference",
        "code[0].text",
        *(
            ["identifier[0].system", "identifier[0].value"]
            if selected_relationship is not None
            else []
        ),
    ]
    resource_scaffold = ResourceScaffoldArtifact(
        placeholder_id=placeholder.placeholder_id,
        resource_type=placeholder.resource_type,
        profile_url=placeholder.profile_url,
        scaffold_state="references_attached",
        fhir_scaffold=scaffold_dict,
        populated_paths=populated_paths,
        deferred_paths=_merge_deferred_paths(
            placeholder.required_later_fields,
            ["specialty", "telecom", "period", "availableTime"],
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
        reference_contributions=[
            _reference_contribution("practitioner.reference", "practitioner-1", "Practitioner/practitioner-1"),
            _reference_contribution("organization.reference", "organization-1", "Organization/organization-1"),
        ],
        deterministic_value_evidence=[
            *(
                [
                    _value_evidence(
                        "identifier[0].system",
                        "deterministic_content_policy",
                        "fixed selected provider-role relationship identifier system",
                    ),
                    _value_evidence(
                        "identifier[0].value",
                        "normalized_request.provider_context.selected_provider_role_relationship",
                        "relationship_id",
                    ),
                ]
                if selected_relationship is not None
                else []
            ),
            _value_evidence(
                "code[0].text",
                (
                    "normalized_request.provider_context.selected_provider_role_relationship"
                    if selected_relationship is not None
                    else "bundle_schematic.resource_placeholders[practitionerrole-1]"
                ),
                "role_label" if selected_relationship is not None else "role",
            ),
        ],
        assumptions=[
            (
                "PractitionerRole is scaffolded with deterministic local references, a selected relationship identifier, and a narrow author-role label."
                if selected_relationship is not None
                else "PractitionerRole is scaffolded with deterministic local references plus a narrow author-role label."
            ),
            (
                "PractitionerRole author context and relationship identity are derived from the normalized selected provider-role relationship."
                if selected_relationship is not None
                else "PractitionerRole falls back to the schematic placeholder role when richer provider-role context is not available."
            ),
        ],
        warnings=[],
        unresolved_fields=resource_scaffold.deferred_paths,
    )


def _build_section_entry_result(
    step: BuildPlanStep,
    placeholder: ResourcePlaceholder,
    sections: dict[str, SectionScaffold],
    normalized_request: NormalizedBuildRequest,
) -> ResourceConstructionStepResult:
    scaffold_dict = _base_scaffold(placeholder)
    reference_path, reference_value = _section_subject_reference(step.resource_type)
    parent_key = reference_path.split(".")[0]
    scaffold_dict[parent_key] = {"reference": reference_value}
    section = sections.get(step.owning_section_key or "")
    if section is None:
        raise ValueError(f"Missing section scaffold for section-entry step '{step.step_id}'.")
    placeholder_text = _section_entry_placeholder_text(
        step.resource_type,
        section,
        normalized_request,
        placeholder.placeholder_id,
    )
    populated_paths = _base_populated_paths(placeholder) + [reference_path]
    deterministic_value_evidence = [
        _value_evidence(reference_path, "deterministic_reference_policy", f"{step.resource_type} references patient-1."),
    ]

    if step.resource_type == "MedicationRequest":
        scaffold_dict["status"] = "draft"
        scaffold_dict["intent"] = "proposal"
        scaffold_dict["medicationCodeableConcept"] = {"text": placeholder_text}
        populated_paths += ["status", "intent", "medicationCodeableConcept.text"]
        deterministic_value_evidence.extend(
            [
                _value_evidence("status", "deterministic_content_policy", "MedicationRequest status is fixed to draft for placeholder content."),
                _value_evidence("intent", "deterministic_content_policy", "MedicationRequest intent is fixed to proposal for placeholder content."),
                _value_evidence(
                    "medicationCodeableConcept.text",
                    _section_entry_text_source_artifact(
                        step.resource_type,
                        normalized_request,
                        section.section_key,
                        placeholder.placeholder_id,
                    ),
                    _section_entry_text_source_detail(
                        step.resource_type,
                        normalized_request,
                        section.title,
                        placeholder.placeholder_id,
                    ),
                ),
            ]
        )
    elif step.resource_type == "AllergyIntolerance":
        scaffold_dict["clinicalStatus"] = {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                    "code": "active",
                }
            ]
        }
        scaffold_dict["verificationStatus"] = {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification",
                    "code": "unconfirmed",
                }
            ]
        }
        scaffold_dict["code"] = {"text": placeholder_text}
        populated_paths += [
            "clinicalStatus.coding[0].system",
            "clinicalStatus.coding[0].code",
            "verificationStatus.coding[0].system",
            "verificationStatus.coding[0].code",
            "code.text",
        ]
        deterministic_value_evidence.extend(
            [
                _value_evidence("clinicalStatus.coding[0].system", "deterministic_content_policy", "Fixed AllergyIntolerance clinical status coding system."),
                _value_evidence("clinicalStatus.coding[0].code", "deterministic_content_policy", "Fixed AllergyIntolerance clinical status code."),
                _value_evidence("verificationStatus.coding[0].system", "deterministic_content_policy", "Fixed AllergyIntolerance verification status coding system."),
                _value_evidence("verificationStatus.coding[0].code", "deterministic_content_policy", "Fixed AllergyIntolerance verification status code."),
                _value_evidence(
                    "code.text",
                    _section_entry_text_source_artifact(
                        step.resource_type,
                        normalized_request,
                        section.section_key,
                        placeholder.placeholder_id,
                    ),
                    _section_entry_text_source_detail(
                        step.resource_type,
                        normalized_request,
                        section.title,
                        placeholder.placeholder_id,
                    ),
                ),
            ]
        )
    elif step.resource_type == "Condition":
        scaffold_dict["clinicalStatus"] = {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": "active",
                }
            ]
        }
        scaffold_dict["verificationStatus"] = {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                    "code": "provisional",
                }
            ]
        }
        scaffold_dict["code"] = {"text": placeholder_text}
        populated_paths += [
            "clinicalStatus.coding[0].system",
            "clinicalStatus.coding[0].code",
            "verificationStatus.coding[0].system",
            "verificationStatus.coding[0].code",
            "code.text",
        ]
        deterministic_value_evidence.extend(
            [
                _value_evidence("clinicalStatus.coding[0].system", "deterministic_content_policy", "Fixed Condition clinical status coding system."),
                _value_evidence("clinicalStatus.coding[0].code", "deterministic_content_policy", "Fixed Condition clinical status code."),
                _value_evidence("verificationStatus.coding[0].system", "deterministic_content_policy", "Fixed Condition verification status coding system."),
                _value_evidence("verificationStatus.coding[0].code", "deterministic_content_policy", "Fixed Condition verification status code."),
                _value_evidence(
                    "code.text",
                    _section_entry_text_source_artifact(
                        step.resource_type,
                        normalized_request,
                        section.section_key,
                        placeholder.placeholder_id,
                    ),
                    _section_entry_text_source_detail(
                        step.resource_type,
                        normalized_request,
                        section.title,
                        placeholder.placeholder_id,
                    ),
                ),
            ]
        )

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
        deterministic_value_evidence=deterministic_value_evidence,
        assumptions=[
            _section_entry_assumption(step.resource_type, normalized_request, placeholder.placeholder_id),
        ],
        warnings=[],
        unresolved_fields=resource_scaffold.deferred_paths,
    )


def _build_composition_scaffold_result(
    step: BuildPlanStep,
    placeholder: ResourcePlaceholder,
    normalized_request: NormalizedBuildRequest,
) -> ResourceConstructionStepResult:
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
    scaffold_dict["status"] = "final"
    scaffold_dict["title"] = f"{normalized_request.request.bundle_intent} - {normalized_request.request.scenario_label}"
    scaffold_dict["subject"] = {"reference": "Patient/patient-1"}
    scaffold_dict["author"] = [{"reference": "PractitionerRole/practitionerrole-1"}]
    scaffold_dict["section"] = []
    populated_paths = _base_populated_paths(placeholder) + [
        "type.coding[0].system",
        "type.coding[0].code",
        "type.coding[0].display",
        "status",
        "title",
        "subject.reference",
        "author[0].reference",
        "section",
    ]
    deterministic_value_evidence = [
        _value_evidence("type.coding[0].system", "bundle_schematic.composition_scaffold", "expected_type_system"),
        _value_evidence("type.coding[0].code", "bundle_schematic.composition_scaffold", "expected_type_code"),
        _value_evidence("type.coding[0].display", "bundle_schematic.composition_scaffold", "expected_type_display"),
        _value_evidence("status", "deterministic_content_policy", "Composition status is fixed to final for the first meaningful content slice."),
        _value_evidence(
            "title",
            "normalized_request.request",
            "bundle_intent + scenario_label",
        ),
        _value_evidence("subject.reference", "deterministic_reference_policy", "Composition subject references patient-1."),
        _value_evidence("author[0].reference", "deterministic_reference_policy", "Composition author references practitionerrole-1."),
    ]
    resource_scaffold = ResourceScaffoldArtifact(
        placeholder_id=placeholder.placeholder_id,
        resource_type=placeholder.resource_type,
        profile_url=placeholder.profile_url,
        scaffold_state="composition_scaffold_created",
        fhir_scaffold=scaffold_dict,
        populated_paths=populated_paths,
        deferred_paths=_merge_deferred_paths(placeholder.required_later_fields, ["date"], populated_paths),
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
        deterministic_value_evidence=deterministic_value_evidence,
        assumptions=[
            "Composition scaffold content is enriched deterministically before section entries are attached.",
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
    if not step.owning_section_key:
        raise ValueError("Composition finalization requires an owning_section_key for the targeted section.")
    scaffold_dict = deepcopy(prior_scaffold.fhir_scaffold)
    section_blocks_by_key = _existing_composition_sections_by_key(prior_scaffold.fhir_scaffold.get("section"), sections)
    reference_contributions: list[ReferenceContribution] = []
    populated_paths = list(prior_scaffold.populated_paths)
    deterministic_value_evidence: list[DeterministicValueEvidence] = []
    target_section = sections.get(step.owning_section_key)
    if target_section is None:
        raise ValueError(
            f"Missing section scaffold '{step.owning_section_key}' required for Composition finalization."
        )
    entry_placeholder_ids = list(target_section.entry_placeholder_ids)
    entry_references = [
        _local_reference_for_placeholder(entry_placeholder_id)
        for entry_placeholder_id in entry_placeholder_ids
    ]
    section_blocks_by_key[step.owning_section_key] = _composition_section_block(
        target_section,
        entry_references,
    )

    ordered_section_keys = [
        section_key
        for section_key in _REQUIRED_COMPOSITION_SECTION_KEYS
        if section_key in section_blocks_by_key
    ]
    section_blocks = [section_blocks_by_key[section_key] for section_key in ordered_section_keys]
    section_index = ordered_section_keys.index(step.owning_section_key)
    populated_paths.extend(
        [
            f"section[{section_index}].title",
            f"section[{section_index}].code.coding[0].system",
            f"section[{section_index}].code.coding[0].code",
            f"section[{section_index}].code.coding[0].display",
        ]
    )
    deterministic_value_evidence.extend(
        [
            _value_evidence(
                f"section[{section_index}].title",
                f"bundle_schematic.section_scaffolds[{target_section.section_key}]",
                "title",
            ),
            _value_evidence(
                f"section[{section_index}].code.coding[0].system",
                "deterministic_content_policy",
                "Composition section coding system is fixed to http://loinc.org.",
            ),
            _value_evidence(
                f"section[{section_index}].code.coding[0].code",
                f"bundle_schematic.section_scaffolds[{target_section.section_key}]",
                "loinc_code",
            ),
            _value_evidence(
                f"section[{section_index}].code.coding[0].display",
                f"bundle_schematic.section_scaffolds[{target_section.section_key}]",
                "title",
            ),
        ]
    )
    for entry_index, (entry_placeholder_id, entry_reference) in enumerate(
        zip(entry_placeholder_ids, entry_references, strict=False)
    ):
        populated_paths.append(f"section[{section_index}].entry[{entry_index}].reference")
        reference_contributions.append(
            _reference_contribution(
                f"section[{section_index}].entry[{entry_index}].reference",
                entry_placeholder_id,
                entry_reference,
            )
        )
        deterministic_value_evidence.append(
            _value_evidence(
                f"section[{section_index}].entry[{entry_index}].reference",
                "deterministic_reference_policy",
                f"Composition section entry references {entry_placeholder_id}.",
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
        deferred_paths=_merge_deferred_paths(placeholder.required_later_fields, ["date"], populated_paths),
        source_step_ids=_dedupe_paths(prior_scaffold.source_step_ids + [step.step_id]),
    )

    return ResourceConstructionStepResult(
        step_id=step.step_id,
        step_kind=step.step_kind,
        resource_type=step.resource_type,
        target_placeholder_id=step.target_placeholder_id,
        execution_status="scaffold_updated",
        resource_scaffold=resource_scaffold,
        reference_contributions=reference_contributions,
        deterministic_value_evidence=deterministic_value_evidence,
        assumptions=[
            "Composition finalization attaches one deterministic required section block at a time while preserving previously attached sections and can contribute up to two medication section-entry references in this slice.",
        ],
        warnings=[],
        unresolved_fields=resource_scaffold.deferred_paths,
    )


def _existing_composition_sections_by_key(
    existing_sections: object,
    sections: dict[str, SectionScaffold],
) -> dict[str, dict[str, object]]:
    if not isinstance(existing_sections, list):
        return {}

    blocks_by_key: dict[str, dict[str, object]] = {}
    for section_block in existing_sections:
        if not isinstance(section_block, dict):
            continue
        for section_key in _REQUIRED_COMPOSITION_SECTION_KEYS:
            section = sections.get(section_key)
            if section is None:
                continue
            if _section_block_matches_scaffold(section_block, section):
                blocks_by_key[section_key] = deepcopy(section_block)
                break
    return blocks_by_key


def _section_block_matches_scaffold(
    section_block: dict[str, object],
    section: SectionScaffold,
) -> bool:
    title = section_block.get("title")
    code = section_block.get("code")
    coding = code.get("coding") if isinstance(code, dict) else None
    first_coding = coding[0] if isinstance(coding, list) and coding else None
    return (
        title == section.title
        and isinstance(first_coding, dict)
        and first_coding.get("code") == section.loinc_code
    )


def _composition_section_block(
    section: SectionScaffold,
    entry_references: list[str],
) -> dict[str, object]:
    return {
        "title": section.title,
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": section.loinc_code,
                    "display": section.title,
                }
            ]
        },
        "entry": [{"reference": entry_reference} for entry_reference in entry_references],
    }


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
        return ["authoredOn"]
    if resource_type == "AllergyIntolerance":
        return ["reaction"]
    if resource_type == "Condition":
        return ["onset[x]"]
    return []


def _section_subject_reference(resource_type: str) -> tuple[str, str]:
    if resource_type == "MedicationRequest":
        return "subject.reference", "Patient/patient-1"
    if resource_type == "AllergyIntolerance":
        return "patient.reference", "Patient/patient-1"
    if resource_type == "Condition":
        return "subject.reference", "Patient/patient-1"
    raise ValueError(f"Unsupported section-entry resource type '{resource_type}'.")


def _section_entry_placeholder_text(
    resource_type: str,
    section: SectionScaffold,
    normalized_request: NormalizedBuildRequest,
    placeholder_id: str,
) -> str:
    if resource_type == "MedicationRequest":
        selected = _selected_medication_for_placeholder(normalized_request, placeholder_id)
        if selected is not None:
            return selected.display_text
    elif resource_type == "AllergyIntolerance":
        selected = normalized_request.patient_context.selected_allergy_for_single_entry
        if selected is not None:
            return selected.display_text
    elif resource_type == "Condition":
        selected = normalized_request.patient_context.selected_condition_for_single_entry
        if selected is not None:
            return selected.display_text
    return f"{section.title} placeholder for {normalized_request.request.scenario_label}"


def _section_entry_text_source_artifact(
    resource_type: str,
    normalized_request: NormalizedBuildRequest,
    section_key: str,
    placeholder_id: str,
) -> str:
    if resource_type == "MedicationRequest":
        planned_entry_index = _planned_medication_entry_list_index(normalized_request, placeholder_id)
        if planned_entry_index is not None:
            return f"normalized_request.patient_context.planned_medication_entries[{planned_entry_index}]"
    if resource_type == "AllergyIntolerance" and normalized_request.patient_context.selected_allergy_for_single_entry is not None:
        return "normalized_request.patient_context.selected_allergy_for_single_entry"
    if resource_type == "Condition" and normalized_request.patient_context.selected_condition_for_single_entry is not None:
        return "normalized_request.patient_context.selected_condition_for_single_entry"
    return f"bundle_schematic.section_scaffolds[{section_key}] + normalized_request.request"


def _section_entry_text_source_detail(
    resource_type: str,
    normalized_request: NormalizedBuildRequest,
    section_title: str,
    placeholder_id: str,
) -> str:
    if resource_type == "MedicationRequest":
        planned_entry = _planned_medication_entry_for_placeholder(normalized_request, placeholder_id)
        if planned_entry is not None:
            return (
                "display_text"
                f" (placeholder_id={planned_entry.placeholder_id}, "
                f"source_medication_index={planned_entry.source_medication_index}, "
                f"medication_id={planned_entry.medication_id})"
            )
    if resource_type == "AllergyIntolerance" and normalized_request.patient_context.selected_allergy_for_single_entry is not None:
        return "display_text"
    if resource_type == "Condition" and normalized_request.patient_context.selected_condition_for_single_entry is not None:
        return "display_text"
    return f"{section_title} + scenario_label"


def _selected_medication_for_placeholder(
    normalized_request: NormalizedBuildRequest,
    placeholder_id: str,
):
    planned_entry = _planned_medication_entry_for_placeholder(normalized_request, placeholder_id)
    if planned_entry is not None:
        return normalized_request.patient_context.medications[planned_entry.source_medication_index]
    if placeholder_id == "medicationrequest-1":
        return normalized_request.patient_context.selected_medication_for_single_entry
    return None


def _planned_medication_entry_for_placeholder(
    normalized_request: NormalizedBuildRequest,
    placeholder_id: str,
):
    for entry in normalized_request.patient_context.planned_medication_entries:
        if entry.placeholder_id == placeholder_id:
            return entry
    return None


def _planned_medication_entry_list_index(
    normalized_request: NormalizedBuildRequest,
    placeholder_id: str,
) -> int | None:
    for index, entry in enumerate(normalized_request.patient_context.planned_medication_entries):
        if entry.placeholder_id == placeholder_id:
            return index
    return None


def _section_entry_assumption(
    resource_type: str,
    normalized_request: NormalizedBuildRequest,
    placeholder_id: str,
) -> str:
    if resource_type == "MedicationRequest":
        planned_entry = _planned_medication_entry_for_placeholder(normalized_request, placeholder_id)
        if planned_entry is not None:
            return (
                "MedicationRequest placeholders consume the authoritative bounded planned-medication mapping "
                f"from request normalization; {placeholder_id} uses medication index "
                f"{planned_entry.source_medication_index} ({planned_entry.medication_id})."
            )
        return (
            "MedicationRequest placeholder text falls back to section-scaffold placeholder text when no "
            "structured bounded planned-medication mapping exists for the placeholder."
        )
    return (
        "Section-entry resources use deterministic structured clinical profile text when exactly one matching item "
        "is available; otherwise they fall back to section-scaffold placeholder text."
    )


def _reference_contribution(reference_path: str, target_placeholder_id: str, reference_value: str) -> ReferenceContribution:
    return ReferenceContribution(
        reference_path=reference_path,
        target_placeholder_id=target_placeholder_id,
        reference_value=reference_value,
        status="applied",
    )


def _value_evidence(target_path: str, source_artifact: str, source_detail: str) -> DeterministicValueEvidence:
    return DeterministicValueEvidence(
        target_path=target_path,
        source_artifact=source_artifact,
        source_detail=source_detail,
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
