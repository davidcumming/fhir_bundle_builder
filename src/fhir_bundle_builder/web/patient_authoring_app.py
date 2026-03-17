"""Thin FastAPI page for AI-assisted patient profile authoring inspection."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Literal

import uvicorn
from fastapi import FastAPI, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse

from fhir_bundle_builder.authoring import (
    PatientAuthoredRecord,
    PatientAuthoringAgentRunResult,
    PatientAuthoringInput,
    PatientAuthoringMapResult,
    author_patient_record,
    map_authored_patient_to_patient_context,
)
from fhir_bundle_builder.workflows.psca_bundle_builder_workflow.openai_gateway import (
    OpenAIGatewayConfigurationError,
)
from fhir_bundle_builder.authoring.patient_agent import PatientAuthoringAgentError

ComplexityValue = Literal["low", "medium", "high"]
_VALID_COMPLEXITIES: tuple[ComplexityValue, ...] = ("low", "medium", "high")


@dataclass(frozen=True)
class PatientAuthoringPageResult:
    """Small render payload for the patient authoring page."""

    agent_run: PatientAuthoringAgentRunResult
    mapped_result: PatientAuthoringMapResult | None

    @property
    def accepted_record(self) -> PatientAuthoredRecord | None:
        return self.agent_run.accepted_record


app = FastAPI(title="FHIR Bundle Builder Patient Authoring")


async def run_patient_authoring_flow(
    narrative: str,
    complexity: ComplexityValue,
) -> PatientAuthoringPageResult:
    """Run the OpenAI-backed patient authoring flow for the page."""

    authoring_input = PatientAuthoringInput(
        authoring_text=narrative,
        complexity_level=complexity,
        scenario_label="patient-authoring-web-ui",
    )
    agent_run = await author_patient_record(authoring_input)
    mapped_result = None
    if agent_run.accepted_record is not None:
        mapped_result = map_authored_patient_to_patient_context(agent_run.accepted_record)
    return PatientAuthoringPageResult(
        agent_run=agent_run,
        mapped_result=mapped_result,
    )


def _render_list(items: list[str], empty_text: str) -> str:
    if not items:
        return f"<p>{escape(empty_text)}</p>"
    return "<ul>" + "".join(f"<li>{item}</li>" for item in items) + "</ul>"


def _render_key_value_list(rows: list[tuple[str, str | None]], empty_text: str) -> str:
    filtered_rows = [(label, value) for label, value in rows if value is not None and value != ""]
    if not filtered_rows:
        return f"<p>{escape(empty_text)}</p>"
    return (
        "<dl class='detail-list'>"
        + "".join(
            f"<dt>{escape(label)}</dt><dd>{escape(value)}</dd>"
            for label, value in filtered_rows
        )
        + "</dl>"
    )


def _render_accepted_record(result: PatientAuthoringPageResult | None) -> str:
    if result is None or result.accepted_record is None:
        return "<p>No accepted structured patient profile yet.</p>"

    record = result.accepted_record
    background_html = _render_key_value_list(
        [
            ("Residence", record.background_facts.residence_text),
            ("Smoking Status", record.background_facts.smoking_status_text),
        ],
        "No background facts were accepted.",
    )
    patient_html = _render_key_value_list(
        [
            ("Patient ID", record.patient.patient_id),
            ("Display Name", record.patient.display_name),
            ("Administrative Gender", record.patient.administrative_gender),
            ("Age (years)", str(record.patient.age_years) if record.patient.age_years is not None else None),
            ("Birth Date", record.patient.birth_date),
            ("Record ID", record.record_id),
            ("Scenario Label", record.scenario_label),
        ],
        "No patient identity details were accepted.",
    )
    conditions_html = _render_list(
        [
            escape(f"{condition.display_text} ({condition.source_mode})")
            for condition in record.conditions
        ],
        "No conditions accepted.",
    )
    medications_html = _render_list(
        [
            escape(f"{medication.display_text} ({medication.source_mode})")
            for medication in record.medications
        ],
        "No medications accepted.",
    )
    allergies_html = _render_list(
        [
            escape(f"{allergy.display_text} ({allergy.source_mode})")
            for allergy in record.allergies
        ],
        "No allergies accepted.",
    )
    gaps_html = _render_list(
        [
            escape(
                f"{gap.area}: {gap.authored_count}/{gap.target_count} authored - {gap.reason}"
            )
            for gap in record.unresolved_authoring_gaps
        ],
        "No unresolved authoring gaps.",
    )
    evidence_html = _render_key_value_list(
        [
            ("Builder Mode", record.authoring_evidence.builder_mode),
            ("Extracted Name", record.authoring_evidence.extracted_name),
            ("Extracted Gender", record.authoring_evidence.extracted_gender),
            (
                "Extracted Age (years)",
                (
                    str(record.authoring_evidence.extracted_age_years)
                    if record.authoring_evidence.extracted_age_years is not None
                    else None
                ),
            ),
            ("Extracted Birth Date", record.authoring_evidence.extracted_birth_date),
            ("Extracted Residence", record.authoring_evidence.extracted_residence_text),
            ("Extracted Smoking Status", record.authoring_evidence.extracted_smoking_status_text),
            (
                "Scenario Tags",
                ", ".join(record.authoring_evidence.applied_scenario_tags)
                if record.authoring_evidence.applied_scenario_tags
                else None,
            ),
        ],
        "No authoring evidence available.",
    )

    return f"""
    <div class="subsection">
      <h3>Patient Identity</h3>
      {patient_html}
    </div>
    <div class="subsection">
      <h3>Conditions</h3>
      {conditions_html}
    </div>
    <div class="subsection">
      <h3>Medications</h3>
      {medications_html}
    </div>
    <div class="subsection">
      <h3>Allergies</h3>
      {allergies_html}
    </div>
    <div class="subsection">
      <h3>Background Facts</h3>
      {background_html}
    </div>
    <div class="subsection">
      <h3>Unresolved Authoring Gaps</h3>
      {gaps_html}
    </div>
    <div class="subsection">
      <h3>Authoring Evidence</h3>
      {evidence_html}
    </div>
    """


def _render_mapped_context(result: PatientAuthoringPageResult | None) -> str:
    if result is None or result.mapped_result is None:
        return "<p>No mapped patient context yet.</p>"

    mapped = result.mapped_result
    identity_html = _render_key_value_list(
        [
            ("Patient ID", mapped.patient_context.patient.patient_id),
            ("Display Name", mapped.patient_context.patient.display_name),
            ("Source Type", mapped.patient_context.patient.source_type),
            ("Administrative Gender", mapped.patient_context.patient.administrative_gender),
            ("Birth Date", mapped.patient_context.patient.birth_date),
        ],
        "No mapped patient identity details.",
    )
    conditions_html = _render_list(
        [escape(condition.display_text) for condition in mapped.patient_context.conditions],
        "No mapped conditions.",
    )
    medications_html = _render_list(
        [escape(medication.display_text) for medication in mapped.patient_context.medications],
        "No mapped medications.",
    )
    allergies_html = _render_list(
        [escape(allergy.display_text) for allergy in mapped.patient_context.allergies],
        "No mapped allergies.",
    )
    unmapped_html = _render_list(mapped.unmapped_fields, "No unmapped fields.")

    return f"""
    <div class="subsection">
      <h3>Mapped Patient Identity</h3>
      {identity_html}
    </div>
    <div class="subsection">
      <h3>Mapped Conditions</h3>
      {conditions_html}
    </div>
    <div class="subsection">
      <h3>Mapped Medications</h3>
      {medications_html}
    </div>
    <div class="subsection">
      <h3>Mapped Allergies</h3>
      {allergies_html}
    </div>
    <div class="subsection">
      <h3>Unmapped Fields</h3>
      {unmapped_html}
      <p>Counts: {mapped.mapped_condition_count} conditions, {mapped.mapped_medication_count} medications, {mapped.mapped_allergy_count} allergies.</p>
    </div>
    """


def _render_raw_agent_output(result: PatientAuthoringPageResult | None) -> str:
    if result is None:
        return "<p>No raw agent output yet.</p>"

    trace = result.agent_run.trace
    metadata_html = _render_key_value_list(
        [
            ("Provider", trace.provider),
            ("Model Name", trace.model_name),
            ("Status", trace.status),
            ("Provider Response ID", trace.provider_response_id),
            ("Rejection Reason", trace.rejection_reason),
        ],
        "No raw agent metadata available.",
    )
    raw_text = escape(trace.raw_response_text) if trace.raw_response_text else "No raw agent output yet."
    return f"""
    <div class="subsection">
      <h3>Trace Metadata</h3>
      {metadata_html}
    </div>
    <div class="subsection">
      <h3>Raw Model Text</h3>
      <pre>{raw_text}</pre>
    </div>
    """


def _render_json_block(title: str, payload: str | None, empty_text: str) -> str:
    content = escape(payload) if payload is not None else escape(empty_text)
    return f"""
    <div class="subsection">
      <h3>{escape(title)}</h3>
      <pre>{content}</pre>
    </div>
    """


def _render_json_inspection(result: PatientAuthoringPageResult | None) -> str:
    if result is None:
        return (
            _render_json_block("Agent Trace JSON", None, "No agent trace JSON yet.")
            + _render_json_block("Validation Outcome JSON", None, "No validation outcome JSON yet.")
            + _render_json_block("Accepted Structured Patient Profile JSON", None, "No accepted patient profile JSON yet.")
            + _render_json_block("Mapped Patient Context JSON", None, "No mapped patient context JSON yet.")
        )

    accepted_record_json = (
        result.accepted_record.model_dump_json(indent=2)
        if result.accepted_record is not None
        else None
    )
    mapped_json = (
        result.mapped_result.model_dump_json(indent=2)
        if result.mapped_result is not None
        else None
    )
    return (
        _render_json_block(
            "Agent Trace JSON",
            result.agent_run.trace.model_dump_json(indent=2),
            "No agent trace JSON yet.",
        )
        + _render_json_block(
            "Validation Outcome JSON",
            result.agent_run.validation_outcome.model_dump_json(indent=2),
            "No validation outcome JSON yet.",
        )
        + _render_json_block(
            "Accepted Structured Patient Profile JSON",
            accepted_record_json,
            "No accepted patient profile JSON yet.",
        )
        + _render_json_block(
            "Mapped Patient Context JSON",
            mapped_json,
            "No mapped patient context JSON yet.",
        )
    )


def render_patient_authoring_page(
    *,
    narrative: str = "",
    complexity: str = "medium",
    errors: list[str] | None = None,
    result: PatientAuthoringPageResult | None = None,
) -> str:
    """Render the patient authoring page."""

    error_items = errors or []
    safe_narrative = escape(narrative)
    selected_complexity = complexity if complexity in _VALID_COMPLEXITIES else "medium"
    error_html = _render_list(error_items, "No validation or agent errors.")
    submitted_input_html = _render_key_value_list(
        [("Complexity", selected_complexity)],
        "No submitted input yet.",
    )
    submitted_narrative_html = (
        f"<pre>{safe_narrative}</pre>" if narrative else "<p>No narrative submitted yet.</p>"
    )

    options_html = "".join(
        (
            f"<option value=\"{value}\"{' selected' if value == selected_complexity else ''}>"
            f"{escape(value.title())}</option>"
        )
        for value in _VALID_COMPLEXITIES
    )

    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Patient Profile Authoring</title>
    <style>
      body {{
        font-family: sans-serif;
        margin: 0;
        background: #f5f7fb;
        color: #1f2933;
      }}
      main {{
        max-width: 960px;
        margin: 0 auto;
        padding: 32px 20px 48px;
      }}
      h1, h2, h3 {{
        margin-top: 0;
      }}
      form, section {{
        background: #ffffff;
        border: 1px solid #d9e2ec;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
      }}
      label {{
        display: block;
        font-weight: 600;
        margin-bottom: 8px;
      }}
      textarea, select, button {{
        font: inherit;
      }}
      textarea, select {{
        width: 100%;
        padding: 10px;
        border-radius: 8px;
        border: 1px solid #bcccdc;
        box-sizing: border-box;
      }}
      textarea {{
        min-height: 180px;
        resize: vertical;
      }}
      .field {{
        margin-bottom: 16px;
      }}
      button {{
        background: #0f62fe;
        color: #ffffff;
        border: none;
        border-radius: 8px;
        padding: 10px 16px;
        cursor: pointer;
      }}
      .subsection {{
        margin-bottom: 18px;
      }}
      .detail-list {{
        display: grid;
        grid-template-columns: max-content 1fr;
        gap: 8px 12px;
        margin: 0;
      }}
      .detail-list dt {{
        font-weight: 600;
      }}
      .detail-list dd {{
        margin: 0;
      }}
      .errors {{
        border-color: #d64545;
        background: #fff3f3;
      }}
      pre {{
        white-space: pre-wrap;
        word-break: break-word;
        background: #f5f7fb;
        padding: 12px;
        border-radius: 8px;
        overflow-x: auto;
      }}
      ul {{
        margin: 0;
        padding-left: 20px;
      }}
    </style>
  </head>
  <body>
    <main>
      <h1>Patient Profile Authoring</h1>
      <form method="post" action="/patient-authoring">
        <div class="field">
          <label for="narrative">Patient Narrative</label>
          <textarea id="narrative" name="narrative">{safe_narrative}</textarea>
        </div>
        <div class="field">
          <label for="complexity">Complexity</label>
          <select id="complexity" name="complexity">{options_html}</select>
        </div>
        <button type="submit">Author Patient Profile</button>
      </form>
      <section>
        <h2>Submitted Input</h2>
        {submitted_input_html}
        <div class="subsection">
          <h3>Narrative</h3>
          {submitted_narrative_html}
        </div>
      </section>
      <section class="{'errors' if error_items else ''}">
        <h2>Validation Errors / Agent Errors</h2>
        {error_html}
      </section>
      <section>
        <h2>Raw Agent Output</h2>
        {_render_raw_agent_output(result)}
      </section>
      <section>
        <h2>Accepted Structured Patient Profile</h2>
        {_render_accepted_record(result)}
      </section>
      <section>
        <h2>Mapped Patient Context</h2>
        {_render_mapped_context(result)}
      </section>
      <section>
        <h2>Raw JSON Inspection</h2>
        {_render_json_inspection(result)}
      </section>
    </main>
  </body>
</html>
"""


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    """Redirect the app root to the patient authoring page."""

    return RedirectResponse(url="/patient-authoring", status_code=status.HTTP_302_FOUND)


@app.get("/patient-authoring", response_class=HTMLResponse, include_in_schema=False)
async def get_patient_authoring_page() -> HTMLResponse:
    """Render the patient authoring page."""

    return HTMLResponse(render_patient_authoring_page())


@app.post("/patient-authoring", response_class=HTMLResponse, include_in_schema=False)
async def post_patient_authoring_page(
    narrative: str = Form(default=""),
    complexity: str = Form(default="medium"),
) -> HTMLResponse:
    """Handle patient authoring form submission."""

    trimmed_narrative = narrative.strip()
    errors: list[str] = []

    if not trimmed_narrative:
        errors.append("Patient narrative is required.")
    if complexity not in _VALID_COMPLEXITIES:
        errors.append("Complexity must be one of low, medium, or high.")

    if errors:
        return HTMLResponse(
            content=render_patient_authoring_page(
                narrative=trimmed_narrative,
                complexity=complexity,
                errors=errors,
            ),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        result = await run_patient_authoring_flow(trimmed_narrative, complexity)
    except OpenAIGatewayConfigurationError as exc:
        return HTMLResponse(
            content=render_patient_authoring_page(
                narrative=trimmed_narrative,
                complexity=complexity,
                errors=[str(exc)],
            ),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except PatientAuthoringAgentError as exc:
        return HTMLResponse(
            content=render_patient_authoring_page(
                narrative=trimmed_narrative,
                complexity=complexity,
                errors=[str(exc)],
            ),
            status_code=status.HTTP_502_BAD_GATEWAY,
        )

    response_errors = result.agent_run.validation_outcome.errors
    response_status = (
        status.HTTP_200_OK
        if result.accepted_record is not None
        else status.HTTP_502_BAD_GATEWAY
    )
    return HTMLResponse(
        render_patient_authoring_page(
            narrative=trimmed_narrative,
            complexity=complexity,
            errors=response_errors,
            result=result,
        ),
        status_code=response_status,
    )


def main() -> None:
    """Run the local patient authoring app."""

    uvicorn.run("fhir_bundle_builder.web.patient_authoring_app:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
