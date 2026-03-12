from __future__ import annotations

from fhir_bundle_builder.models import (
    BuildPlan,
    BuildStatus,
    BuildStep,
    BundleType,
    DeliveryPackage,
    Issue,
    PatientSummarySpecification,
    RequestPacket,
    ResourceTaskPacket,
    ResourceType,
    SeverityLevel,
    ValidationResult,
)


def main() -> None:
    request = RequestPacket(
        request_id="req-001",
        bundle_type=BundleType.PS_CA_PATIENT_SUMMARY,
        user_request="Create a PS-CA patient summary for a 25-year-old patient with stomach cancer.",
        metadata={"channel": "cli"},
        realism_constraints=["Keep the scenario clinically plausible."],
    )
    print(f"ok RequestPacket {request.request_id}")

    specification = PatientSummarySpecification(
        specification_id="spec-001",
        request_id=request.request_id,
        bundle_type=request.bundle_type,
        patient_story="25-year-old adult with active stomach cancer and recent procedure history.",
        sections_required=["problems", "medications", "allergies", "procedures"],
        confirmed_facts={"age": 25, "primary_condition": "stomach cancer"},
        assumptions=["One recent procedure is included to support the requested scenario."],
    )
    print(f"ok PatientSummarySpecification {specification.specification_id}")

    build_step = BuildStep(
        step_id="step-001",
        name="Build patient resource",
        target_resource_type=ResourceType.PATIENT,
        instructions=["Create the foundational Patient resource first."],
    )
    build_plan = BuildPlan(
        plan_id="plan-001",
        specification_id=specification.specification_id,
        bundle_type=specification.bundle_type,
        steps=[build_step],
        dependency_map={"step-001": []},
        retry_policy={"default_retry_limit": 2},
        final_assembly_instructions=["Assemble Composition, then Bundle, after all prerequisite resources pass validation."],
    )
    print(f"ok BuildPlan {build_plan.plan_id}")

    issue = Issue(
        code="example-warning",
        severity=SeverityLevel.WARNING,
        message="Example interpreted validator warning.",
        retryable=True,
    )
    task_packet = ResourceTaskPacket(
        task_id="task-001",
        build_step_id=build_step.step_id,
        target_resource_type=ResourceType.PATIENT,
        required_facts={"name": "Example Patient"},
        dependency_references={"request": request.request_id},
        prior_issues=[issue],
    )
    print(f"ok ResourceTaskPacket {task_packet.task_id}")

    validation = ValidationResult(
        validation_id="val-001",
        target_type=task_packet.target_resource_type.value,
        target_id=task_packet.task_id,
        passed=True,
        summary="Resource passed deterministic validation.",
        suggested_fixes=[],
    )
    print(f"ok ValidationResult {validation.validation_id}")

    delivery = DeliveryPackage(
        delivery_id="delivery-001",
        request_id=request.request_id,
        bundle_type=request.bundle_type,
        status=BuildStatus.SUCCEEDED,
        final_bundle={"resourceType": "Bundle", "type": "document"},
        validation_result=validation,
        execution_trace=["request accepted", "specification derived", "bundle delivered"],
    )
    print(f"ok DeliveryPackage {delivery.delivery_id}")


if __name__ == "__main__":
    main()
