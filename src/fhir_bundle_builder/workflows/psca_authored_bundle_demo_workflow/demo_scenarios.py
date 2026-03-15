"""Canonical demo scenarios for the authored-input Dev UI wrapper flow."""

from __future__ import annotations

from pydantic import BaseModel, Field

from fhir_bundle_builder.authoring import (
    PatientAuthoringInput,
    PatientAuthoredRecordReviewEditInput,
    ProviderAuthoringInput,
    ProviderAuthoredRecordReviewEditInput,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.models import BundleRequestInput

from .models import AuthoredBundleDemoInput


class DemoScenarioDefinition(BaseModel):
    """Minimal metadata for one canonical authored-input demo scenario."""

    scenario_id: str
    title: str
    purpose: str
    highlight_tags: list[str] = Field(default_factory=list)


RICH_REVIEWED_DEMO = DemoScenarioDefinition(
    scenario_id="rich_reviewed_demo",
    title="Rich Reviewed Demo",
    purpose=(
        "Shows the full authored-input path with patient/provider authoring, bounded record refinement, "
        "rich provider context, and a successful deterministic workflow run."
    ),
    highlight_tags=[
        "rich_provider",
        "edited_record_path",
        "selected_provider_relationship",
        "successful_validation",
    ],
)

THIN_PROVIDER_DEMO = DemoScenarioDefinition(
    scenario_id="thin_provider_demo",
    title="Thin Provider Demo",
    purpose=(
        "Shows honest thin-provider behavior where provider facts are preserved, "
        "organization/relationship gaps remain visible, and the workflow still runs cleanly."
    ),
    highlight_tags=[
        "thin_provider",
        "provider_gaps_visible",
        "unmapped_provider_facts",
        "successful_validation",
    ],
)


def build_rich_reviewed_demo_input() -> AuthoredBundleDemoInput:
    """Return the canonical rich reviewed authored-input demo scenario."""

    return AuthoredBundleDemoInput(
        patient_authoring=PatientAuthoringInput(
            authoring_text=(
                "The patient's name is Nora Field. She is a female age 55 who lives in Red Deer, Alberta. "
                "She has diabetes, takes metformin, and has a peanut allergy."
            ),
            complexity_level="medium",
            scenario_label="demo-patient-rich-reviewed",
        ),
        provider_authoring=ProviderAuthoringInput(
            authoring_text=(
                "The provider's name is Maya Chen. "
                "She is a female oncologist at Fraser Cancer Clinic."
            ),
            scenario_label="demo-provider-rich-reviewed",
        ),
        patient_review_edits=PatientAuthoredRecordReviewEditInput(
            display_name="Nora Field Reviewed",
            medication_display_texts=["Metformin 850 MG oral tablet"],
        ),
        provider_review_edits=ProviderAuthoredRecordReviewEditInput(
            relationship_role_label="medical oncologist",
            selected_relationship_active=True,
        ),
        request=BundleRequestInput(
            request_text="Create the canonical rich reviewed authored-input demo bundle run.",
            scenario_label="rich-reviewed-demo",
        ),
    )


def build_thin_provider_demo_input() -> AuthoredBundleDemoInput:
    """Return the canonical thin-provider authored-input demo scenario."""

    return AuthoredBundleDemoInput(
        patient_authoring=PatientAuthoringInput(
            authoring_text=(
                "The patient's name is Ellis Stone. He is a male age 48 who has hypertension and takes lisinopril."
            ),
            complexity_level="low",
            scenario_label="demo-patient-thin-provider",
        ),
        provider_authoring=ProviderAuthoringInput(
            authoring_text="The provider is a female oncologist in BC.",
            scenario_label="demo-provider-thin-provider",
        ),
        provider_review_edits=ProviderAuthoredRecordReviewEditInput(
            display_name="Dr. Rowan Park",
        ),
        request=BundleRequestInput(
            request_text="Create the canonical thin-provider authored-input demo bundle run.",
            scenario_label="thin-provider-demo",
        ),
    )
