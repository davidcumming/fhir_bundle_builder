"""Deterministic PS-CA build-planning logic from the schematic artifact."""

from __future__ import annotations

from .models import (
    BuildPlan,
    BuildPlanEvidence,
    BuildPlanStep,
    BuildStepDependency,
    BuildStepInput,
    BuildStepOutput,
    BundleSchematic,
    ResourcePlaceholder,
    SchematicRelationship,
)


def build_psca_build_plan(schematic: BundleSchematic) -> BuildPlan:
    """Build the first real PS-CA build plan from the current schematic."""

    placeholders = {placeholder.placeholder_id: placeholder for placeholder in schematic.resource_placeholders}
    relationships = {relationship.relationship_id: relationship for relationship in schematic.relationships}
    section_scaffolds = {section.section_key: section for section in schematic.section_scaffolds}

    patient = _require_placeholder(placeholders, "patient-1")
    practitioner = _require_placeholder(placeholders, "practitioner-1")
    organization = _require_placeholder(placeholders, "organization-1")
    practitioner_role = _require_placeholder(placeholders, "practitionerrole-1")
    composition = _require_placeholder(placeholders, "composition-1")
    medication = _require_placeholder(placeholders, "medicationrequest-1")
    allergy = _require_placeholder(placeholders, "allergyintolerance-1")
    condition = _require_placeholder(placeholders, "condition-1")

    _require_relationship(relationships, "composition-subject", "patient-1")
    _require_relationship(relationships, "composition-author", "practitionerrole-1")
    _require_relationship(relationships, "practitionerrole-practitioner", "practitioner-1")
    _require_relationship(relationships, "practitionerrole-organization", "organization-1")
    _require_relationship(relationships, "section-entry-medications", "medicationrequest-1")
    _require_relationship(relationships, "section-entry-allergies", "allergyintolerance-1")
    _require_relationship(relationships, "section-entry-problems", "condition-1")

    steps = [
        BuildPlanStep(
            step_id="build-patient-1",
            sequence=1,
            step_kind="anchor_resource",
            target_placeholder_id=patient.placeholder_id,
            resource_type=patient.resource_type,
            profile_url=patient.profile_url,
            build_purpose="Create the patient anchor resource required by the document subject relationship.",
            expected_inputs=[
                _input("normalized_request", "NormalizedBuildRequest", True, "Scenario and request context for the run."),
                _input("patient_placeholder", "ResourcePlaceholder", True, "Patient placeholder from the schematic."),
            ],
            expected_outputs=[
                _output("resource_artifact:patient-1", "resource_artifact", "Placeholder Patient resource artifact."),
                _output("reference_handle:patient-1", "reference_handle", "Reusable Patient reference handle."),
            ],
        ),
        BuildPlanStep(
            step_id="build-practitioner-1",
            sequence=2,
            step_kind="support_resource",
            target_placeholder_id=practitioner.placeholder_id,
            resource_type=practitioner.resource_type,
            profile_url=practitioner.profile_url,
            build_purpose="Create the supporting Practitioner referenced by PractitionerRole.",
            expected_inputs=[
                _input("normalized_request", "NormalizedBuildRequest", True, "Scenario and request context for the run."),
                _input("practitioner_placeholder", "ResourcePlaceholder", True, "Practitioner placeholder from the schematic."),
            ],
            expected_outputs=[
                _output("resource_artifact:practitioner-1", "resource_artifact", "Placeholder Practitioner resource artifact."),
                _output("reference_handle:practitioner-1", "reference_handle", "Reusable Practitioner reference handle."),
            ],
        ),
        BuildPlanStep(
            step_id="build-organization-1",
            sequence=3,
            step_kind="support_resource",
            target_placeholder_id=organization.placeholder_id,
            resource_type=organization.resource_type,
            profile_url=organization.profile_url,
            build_purpose="Create the supporting Organization referenced by PractitionerRole.",
            expected_inputs=[
                _input("normalized_request", "NormalizedBuildRequest", True, "Scenario and request context for the run."),
                _input("organization_placeholder", "ResourcePlaceholder", True, "Organization placeholder from the schematic."),
            ],
            expected_outputs=[
                _output("resource_artifact:organization-1", "resource_artifact", "Placeholder Organization resource artifact."),
                _output("reference_handle:organization-1", "reference_handle", "Reusable Organization reference handle."),
            ],
        ),
        BuildPlanStep(
            step_id="build-practitionerrole-1",
            sequence=4,
            step_kind="support_resource",
            target_placeholder_id=practitioner_role.placeholder_id,
            resource_type=practitioner_role.resource_type,
            profile_url=practitioner_role.profile_url,
            build_purpose="Create the author PractitionerRole after its Practitioner and Organization references are available.",
            dependencies=[
                _dependency(
                    "build-practitioner-1",
                    "requires_reference_handle",
                    "PractitionerRole requires the Practitioner reference encoded in the schematic.",
                ),
                _dependency(
                    "build-organization-1",
                    "requires_reference_handle",
                    "PractitionerRole requires the Organization reference encoded in the schematic.",
                ),
            ],
            expected_inputs=[
                _input("practitioner_placeholder", "ResourcePlaceholder", True, "PractitionerRole placeholder from the schematic."),
                _input("reference_handle:practitioner-1", "reference_handle", True, "Practitioner reference for PractitionerRole.practitioner."),
                _input("reference_handle:organization-1", "reference_handle", True, "Organization reference for PractitionerRole.organization."),
            ],
            expected_outputs=[
                _output("resource_artifact:practitionerrole-1", "resource_artifact", "Placeholder PractitionerRole resource artifact."),
                _output("reference_handle:practitionerrole-1", "reference_handle", "Reusable PractitionerRole reference handle."),
            ],
        ),
        BuildPlanStep(
            step_id="build-composition-1-scaffold",
            sequence=5,
            step_kind="composition_scaffold",
            target_placeholder_id=composition.placeholder_id,
            resource_type=composition.resource_type,
            profile_url=composition.profile_url,
            build_purpose="Create the initial Composition scaffold once subject and author references are available.",
            dependencies=[
                _dependency(
                    "build-patient-1",
                    "requires_reference_handle",
                    "Composition.subject requires the Patient reference encoded in the schematic.",
                ),
                _dependency(
                    "build-practitionerrole-1",
                    "requires_reference_handle",
                    "Composition.author requires the PractitionerRole reference encoded in the schematic.",
                ),
            ],
            expected_inputs=[
                _input("normalized_request", "NormalizedBuildRequest", True, "Scenario and request context used for deterministic Composition content."),
                _input("composition_placeholder", "ResourcePlaceholder", True, "Composition placeholder from the schematic."),
                _input("reference_handle:patient-1", "reference_handle", True, "Patient reference for Composition.subject."),
                _input("reference_handle:practitionerrole-1", "reference_handle", True, "PractitionerRole reference for Composition.author."),
                _input("section_scaffolds", "SectionScaffold[]", True, "Section scaffold metadata for later section finalization."),
            ],
            expected_outputs=[
                _output("resource_artifact:composition-1", "resource_artifact", "Placeholder Composition scaffold artifact."),
                _output("reference_handle:composition-1", "reference_handle", "Reusable Composition reference handle."),
                _output("composition_scaffold_ready:composition-1", "composition_scaffold_state", "Signal that the Composition scaffold exists."),
            ],
        ),
        BuildPlanStep(
            step_id="build-medicationrequest-1",
            sequence=6,
            step_kind="section_entry_resource",
            target_placeholder_id=medication.placeholder_id,
            resource_type=medication.resource_type,
            profile_url=medication.profile_url,
            owning_section_key="medications",
            build_purpose="Create the medications section entry resource for later Composition section attachment.",
            dependencies=[
                _dependency(
                    "build-patient-1",
                    "requires_reference_handle",
                    "MedicationRequest uses Patient as the minimal hard prerequisite in this slice.",
                ),
            ],
            expected_inputs=[
                _input("normalized_request", "NormalizedBuildRequest", True, "Scenario and request context used for deterministic placeholder content."),
                _input("section_scaffold:medications", "SectionScaffold", True, "Medications section scaffold."),
                _input("medication_placeholder", "ResourcePlaceholder", True, "MedicationRequest placeholder from the schematic."),
                _input("reference_handle:patient-1", "reference_handle", True, "Patient reference for the section entry resource."),
            ],
            expected_outputs=[
                _output("resource_artifact:medicationrequest-1", "resource_artifact", "Placeholder MedicationRequest resource artifact."),
                _output("reference_handle:medicationrequest-1", "reference_handle", "Reusable MedicationRequest reference handle."),
            ],
        ),
        BuildPlanStep(
            step_id="build-allergyintolerance-1",
            sequence=7,
            step_kind="section_entry_resource",
            target_placeholder_id=allergy.placeholder_id,
            resource_type=allergy.resource_type,
            profile_url=allergy.profile_url,
            owning_section_key="allergies",
            build_purpose="Create the allergies section entry resource for later Composition section attachment.",
            dependencies=[
                _dependency(
                    "build-patient-1",
                    "requires_reference_handle",
                    "AllergyIntolerance uses Patient as the minimal hard prerequisite in this slice.",
                ),
            ],
            expected_inputs=[
                _input("normalized_request", "NormalizedBuildRequest", True, "Scenario and request context used for deterministic placeholder content."),
                _input("section_scaffold:allergies", "SectionScaffold", True, "Allergies section scaffold."),
                _input("allergy_placeholder", "ResourcePlaceholder", True, "AllergyIntolerance placeholder from the schematic."),
                _input("reference_handle:patient-1", "reference_handle", True, "Patient reference for the section entry resource."),
            ],
            expected_outputs=[
                _output("resource_artifact:allergyintolerance-1", "resource_artifact", "Placeholder AllergyIntolerance resource artifact."),
                _output("reference_handle:allergyintolerance-1", "reference_handle", "Reusable AllergyIntolerance reference handle."),
            ],
        ),
        BuildPlanStep(
            step_id="build-condition-1",
            sequence=8,
            step_kind="section_entry_resource",
            target_placeholder_id=condition.placeholder_id,
            resource_type=condition.resource_type,
            profile_url=condition.profile_url,
            owning_section_key="problems",
            build_purpose="Create the problems section entry resource for later Composition section attachment.",
            dependencies=[
                _dependency(
                    "build-patient-1",
                    "requires_reference_handle",
                    "Condition uses Patient as the minimal hard prerequisite in this slice.",
                ),
            ],
            expected_inputs=[
                _input("normalized_request", "NormalizedBuildRequest", True, "Scenario and request context used for deterministic placeholder content."),
                _input("section_scaffold:problems", "SectionScaffold", True, "Problems section scaffold."),
                _input("condition_placeholder", "ResourcePlaceholder", True, "Condition placeholder from the schematic."),
                _input("reference_handle:patient-1", "reference_handle", True, "Patient reference for the section entry resource."),
            ],
            expected_outputs=[
                _output("resource_artifact:condition-1", "resource_artifact", "Placeholder Condition resource artifact."),
                _output("reference_handle:condition-1", "reference_handle", "Reusable Condition reference handle."),
            ],
        ),
        BuildPlanStep(
            step_id="finalize-composition-1-medications-section",
            sequence=9,
            step_kind="composition_finalize",
            target_placeholder_id=composition.placeholder_id,
            resource_type=composition.resource_type,
            profile_url=composition.profile_url,
            owning_section_key="medications",
            build_purpose="Attach the medications section block to the Composition scaffold.",
            dependencies=[
                _dependency(
                    "build-composition-1-scaffold",
                    "requires_scaffold_ready",
                    "The Composition scaffold must exist before the medications section can be attached.",
                ),
                _dependency(
                    "build-medicationrequest-1",
                    "requires_section_entries_attached",
                    "The medications section entry must exist before the medications section can be attached.",
                ),
            ],
            expected_inputs=[
                _input("composition_scaffold_ready:composition-1", "composition_scaffold_state", True, "Signal that the Composition scaffold step completed."),
                _input("section_scaffold:medications", "SectionScaffold", True, "Medications section metadata."),
                _input("reference_handle:medicationrequest-1", "reference_handle", True, "Section entry reference for medications."),
            ],
            expected_outputs=[
                _output(
                    "resource_artifact:composition-1:medications-section-attached",
                    "resource_artifact",
                    "Placeholder Composition resource artifact with the medications section attached.",
                ),
                _output(
                    "composition_section_attached:composition-1:medications",
                    "composition_section_state",
                    "Signal that the medications section has been attached to the Composition scaffold.",
                ),
            ],
        ),
        BuildPlanStep(
            step_id="finalize-composition-1-allergies-section",
            sequence=10,
            step_kind="composition_finalize",
            target_placeholder_id=composition.placeholder_id,
            resource_type=composition.resource_type,
            profile_url=composition.profile_url,
            owning_section_key="allergies",
            build_purpose="Attach the allergies section block to the Composition scaffold.",
            dependencies=[
                _dependency(
                    "finalize-composition-1-medications-section",
                    "requires_scaffold_ready",
                    "The medications section attachment step establishes the prior incremental Composition section state.",
                ),
                _dependency(
                    "build-allergyintolerance-1",
                    "requires_section_entries_attached",
                    "The allergies section entry must exist before the allergies section can be attached.",
                ),
            ],
            expected_inputs=[
                _input("section_scaffold:allergies", "SectionScaffold", True, "Allergies section metadata."),
                _input(
                    "composition_section_attached:composition-1:medications",
                    "composition_section_state",
                    True,
                    "Signal that the medications section has already been attached.",
                ),
                _input("reference_handle:allergyintolerance-1", "reference_handle", True, "Section entry reference for allergies."),
            ],
            expected_outputs=[
                _output(
                    "resource_artifact:composition-1:allergies-section-attached",
                    "resource_artifact",
                    "Placeholder Composition resource artifact with the allergies section attached.",
                ),
                _output(
                    "composition_section_attached:composition-1:allergies",
                    "composition_section_state",
                    "Signal that the allergies section has been attached to the Composition scaffold.",
                ),
            ],
        ),
        BuildPlanStep(
            step_id="finalize-composition-1-problems-section",
            sequence=11,
            step_kind="composition_finalize",
            target_placeholder_id=composition.placeholder_id,
            resource_type=composition.resource_type,
            profile_url=composition.profile_url,
            owning_section_key="problems",
            build_purpose="Attach the problems section block to the Composition scaffold.",
            dependencies=[
                _dependency(
                    "finalize-composition-1-allergies-section",
                    "requires_scaffold_ready",
                    "The allergies section attachment step establishes the prior incremental Composition section state.",
                ),
                _dependency(
                    "build-condition-1",
                    "requires_section_entries_attached",
                    "The problems section entry must exist before the problems section can be attached.",
                ),
            ],
            expected_inputs=[
                _input("section_scaffold:problems", "SectionScaffold", True, "Problems section metadata."),
                _input(
                    "composition_section_attached:composition-1:allergies",
                    "composition_section_state",
                    True,
                    "Signal that the medications and allergies sections have already been attached.",
                ),
                _input("reference_handle:condition-1", "reference_handle", True, "Section entry reference for problems."),
            ],
            expected_outputs=[
                _output(
                    "resource_artifact:composition-1:problems-section-attached",
                    "resource_artifact",
                    "Placeholder Composition resource artifact with the problems section attached.",
                ),
                _output(
                    "composition_section_attached:composition-1:problems",
                    "composition_section_state",
                    "Signal that the problems section has been attached to the Composition scaffold.",
                ),
            ],
        ),
    ]

    return BuildPlan(
        stage_id="build_plan",
        status="placeholder_complete",
        summary="Derived the first deterministic PS-CA build plan from the schematic, including explicit prerequisites, step inputs, and expected outputs.",
        placeholder_note="This slice plans resource ordering only; resource creation, bundle assembly intelligence, and validation-driven replanning remain deferred.",
        source_refs=schematic.source_refs,
        plan_basis="deterministic_schematic_dependency_plan",
        composition_strategy="scaffold_then_incremental_section_finalize",
        steps=steps,
        deferred_items=[
            "Bundle entry assembly remains outside build planning.",
            "No element-level population logic is included yet.",
            "No generated IDs or full reference patching logic is included yet.",
            "No validation-driven replanning is included yet.",
        ],
        evidence=BuildPlanEvidence(
            source_schematic_stage_id=schematic.stage_id,
            source_schematic_generation_basis=schematic.generation_basis,
            planned_placeholder_ids=[
                "patient-1",
                "practitioner-1",
                "organization-1",
                "practitionerrole-1",
                "composition-1",
                "medicationrequest-1",
                "allergyintolerance-1",
                "condition-1",
            ],
            planned_section_keys=[section_key for section_key in ("medications", "allergies", "problems") if section_key in section_scaffolds],
            relationship_ids_used=[
                "composition-subject",
                "composition-author",
                "practitionerrole-practitioner",
                "practitionerrole-organization",
                "section-entry-medications",
                "section-entry-allergies",
                "section-entry-problems",
            ],
            source_refs=schematic.source_refs,
        ),
    )


def _require_placeholder(placeholders: dict[str, ResourcePlaceholder], placeholder_id: str) -> ResourcePlaceholder:
    placeholder = placeholders.get(placeholder_id)
    if placeholder is None:
        raise ValueError(f"Required schematic placeholder '{placeholder_id}' is missing.")
    return placeholder


def _require_relationship(
    relationships: dict[str, SchematicRelationship],
    relationship_id: str,
    target_id: str,
) -> SchematicRelationship:
    relationship = relationships.get(relationship_id)
    if relationship is None:
        raise ValueError(f"Required schematic relationship '{relationship_id}' is missing.")
    if relationship.target_id != target_id:
        raise ValueError(
            f"Relationship '{relationship_id}' targets '{relationship.target_id}' but expected '{target_id}'."
        )
    return relationship


def _dependency(prerequisite_step_id: str, dependency_type: str, reason: str) -> BuildStepDependency:
    return BuildStepDependency(
        prerequisite_step_id=prerequisite_step_id,
        dependency_type=dependency_type,
        reason=reason,
    )


def _input(input_key: str, input_type: str, required: bool, description: str) -> BuildStepInput:
    return BuildStepInput(
        input_key=input_key,
        input_type=input_type,
        required=required,
        description=description,
    )


def _output(output_key: str, output_type: str, description: str) -> BuildStepOutput:
    return BuildStepOutput(
        output_key=output_key,
        output_type=output_type,
        description=description,
    )
