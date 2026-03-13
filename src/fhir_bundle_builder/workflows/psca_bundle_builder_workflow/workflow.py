"""Workflow wiring for the PS-CA bundle builder skeleton."""

from __future__ import annotations

from agent_framework import WorkflowBuilder

from .executors import (
    WORKFLOW_NAME,
    WORKFLOW_VERSION,
    build_plan,
    bundle_finalization,
    bundle_schematic,
    repair_decision,
    request_normalization,
    resource_construction,
    specification_asset_retrieval,
    validation,
)

workflow = (
    WorkflowBuilder(
        start_executor=request_normalization,
        name=WORKFLOW_NAME,
        description=(
            "Deterministic workflow skeleton for the PS-CA bundle builder. "
            f"Version {WORKFLOW_VERSION} proves workflow shape and inspectable stage outputs in Dev UI."
        ),
    )
    .add_chain(
        [
            request_normalization,
            specification_asset_retrieval,
            bundle_schematic,
            build_plan,
            resource_construction,
            bundle_finalization,
            validation,
            repair_decision,
        ]
    )
    .build()
)
