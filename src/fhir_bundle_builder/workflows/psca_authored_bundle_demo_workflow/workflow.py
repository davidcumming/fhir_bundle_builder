"""Workflow wiring for the thin Dev UI-facing authored-input demo flow."""

from __future__ import annotations

from agent_framework import WorkflowBuilder

from .executors import (
    WORKFLOW_NAME,
    WORKFLOW_VERSION,
    authored_bundle_preparation,
    authored_record_refinement,
    bundle_builder_run,
    patient_authoring,
    provider_authoring,
)

workflow = (
    WorkflowBuilder(
        start_executor=patient_authoring,
        name=WORKFLOW_NAME,
        description=(
            "Thin Dev UI wrapper workflow that starts from bounded patient/provider authoring inputs, "
            "prepares one deterministic authored-input bundle request, and runs the unchanged PS-CA bundle builder. "
            f"Version {WORKFLOW_VERSION}."
        ),
    )
    .add_chain(
        [
            patient_authoring,
            provider_authoring,
            authored_record_refinement,
            authored_bundle_preparation,
            bundle_builder_run,
        ]
    )
    .build()
)
