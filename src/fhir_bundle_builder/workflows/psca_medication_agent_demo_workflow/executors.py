"""Executors for the one-click Dev UI MedicationRequest agent demo workflow."""

from __future__ import annotations

from agent_framework import WorkflowContext, executor

from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.executors import (
    build_plan,
    bundle_finalization,
    bundle_schematic,
    repair_decision,
    repair_execution,
    request_normalization,
    resource_construction,
    specification_asset_retrieval,
    validation,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.models import (
    BundleRequestInput,
    PatientAllergyInput,
    PatientConditionInput,
    PatientContextInput,
    PatientIdentityInput,
    PatientMedicationInput,
    ProfileReferenceInput,
    ProviderContextInput,
    ProviderIdentityInput,
    ProviderOrganizationInput,
    ProviderRoleRelationshipInput,
    SpecificationSelection,
    WorkflowBuildInput,
    WorkflowOptionsInput,
)

from .models import MedicationAgentDemoInput

WORKFLOW_NAME = "Psca Medication Agent Demo Workflow"
WORKFLOW_VERSION = "0.1.0"


@executor(
    id="demo_input_preparation",
    input=MedicationAgentDemoInput,
    output=WorkflowBuildInput,
)
async def demo_input_preparation(
    message: MedicationAgentDemoInput,
    ctx: WorkflowContext[WorkflowBuildInput],
) -> None:
    del message
    await ctx.send_message(
        WorkflowBuildInput(
            specification=SpecificationSelection(),
            patient_profile=ProfileReferenceInput(
                profile_id="patient-demo-agent",
                display_name="Demo Agent Patient",
                source_type="patient_management",
            ),
            patient_context=PatientContextInput(
                patient=PatientIdentityInput(
                    patient_id="patient-demo-agent",
                    display_name="Demo Agent Patient",
                    source_type="patient_management",
                    administrative_gender="female",
                    birth_date="1985-02-14",
                ),
                conditions=[
                    PatientConditionInput(
                        condition_id="cond-demo-1",
                        display_text="Type 2 diabetes mellitus",
                    )
                ],
                medications=[
                    PatientMedicationInput(
                        medication_id="med-demo-1",
                        display_text="Atorvastatin 20 MG oral tablet",
                    )
                ],
                allergies=[
                    PatientAllergyInput(
                        allergy_id="alg-demo-1",
                        display_text="Peanut allergy",
                    )
                ],
            ),
            provider_profile=ProfileReferenceInput(
                profile_id="provider-demo-agent",
                display_name="Demo Agent Provider",
                source_type="provider_management",
            ),
            provider_context=ProviderContextInput(
                provider=ProviderIdentityInput(
                    provider_id="provider-demo-agent",
                    display_name="Demo Agent Provider",
                    source_type="provider_management",
                ),
                organizations=[
                    ProviderOrganizationInput(
                        organization_id="org-demo-agent",
                        display_name="Demo Agent Cancer Clinic",
                    )
                ],
                provider_role_relationships=[
                    ProviderRoleRelationshipInput(
                        relationship_id="provider-role-demo-agent",
                        organization_id="org-demo-agent",
                        role_label="attending-physician",
                    )
                ],
            ),
            request=BundleRequestInput(
                request_text="Create a PS-CA bundle with one real model-backed medication request artifact.",
                bundle_intent="PS-CA document bundle skeleton",
                scenario_label="demo-medication-agent",
            ),
            workflow_options=WorkflowOptionsInput(
                medication_request_generation_mode="agent_required",
            ),
        )
    )
