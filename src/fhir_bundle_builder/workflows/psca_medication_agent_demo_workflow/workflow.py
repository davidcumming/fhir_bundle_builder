"""Workflow wiring for the one-click Dev UI MedicationRequest agent demo."""

from __future__ import annotations

from agent_framework import WorkflowBuilder

from .executors import (
    WORKFLOW_NAME,
    WORKFLOW_VERSION,
    build_plan,
    bundle_finalization,
    bundle_schematic,
    demo_input_preparation,
    repair_decision,
    repair_execution,
    request_normalization,
    resource_construction,
    specification_asset_retrieval,
    validation,
)

workflow = (
    WorkflowBuilder(
        start_executor=demo_input_preparation,
        name=WORKFLOW_NAME,
        description=(
            "One-click Dev UI workflow that seeds the canonical MedicationRequest agent demo input "
            "and then runs the existing PS-CA bundle builder workflow. "
            f"Version {WORKFLOW_VERSION}."
        ),
    )
    .add_chain(
        [
            demo_input_preparation,
            request_normalization,
            specification_asset_retrieval,
            bundle_schematic,
            build_plan,
            resource_construction,
            bundle_finalization,
            validation,
            repair_decision,
            repair_execution,
        ]
    )
    .build()
)
