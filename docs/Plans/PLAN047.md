# UI Slice 1: Thin Patient Authoring Browser Page

## Summary
Build a minimal server-rendered WSGI page inside the existing Python package, with no new frontend framework and no persistence. The page will expose a single patient authoring form, call the existing `build_patient_authored_record(...)` and `map_authored_patient_to_patient_context(...)` functions on submit, and render both structured results on the same page.

## Files To Add
- [src/fhir_bundle_builder/web/__init__.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/web/__init__.py)
- [src/fhir_bundle_builder/web/patient_authoring_app.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/web/patient_authoring_app.py)
- [tests/test_patient_authoring_web_app.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_patient_authoring_web_app.py)

## Files To Modify
- [README.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/README.md)

## Backend Route/Page Flow
- `GET /`
  - Return `302` redirect to `/patient-authoring` for convenience.
- `GET /patient-authoring`
  - Render one HTML page with:
    - heading `Patient Profile Authoring`
    - textarea `patient narrative`
    - select `complexity` with `low`, `medium`, `high`
    - submit button
    - empty results area
- `POST /patient-authoring`
  - Parse `application/x-www-form-urlencoded` form data.
  - Validate:
    - narrative must be non-empty after trim
    - complexity must be one of `low|medium|high`
  - On validation failure:
    - return `400`
    - rerender same page with sticky form values and visible error message
  - On success:
    - build authored record
    - map to patient context
    - return `200`
    - rerender same page with results populated
- Any other path
  - Return `404` plain text response.

## How Existing Builder And Mapper Will Be Called
Inside [src/fhir_bundle_builder/web/patient_authoring_app.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/src/fhir_bundle_builder/web/patient_authoring_app.py):

```python
authoring_input = PatientAuthoringInput(
    authoring_text=narrative.strip(),
    complexity_level=complexity,
    scenario_label="patient-authoring-web-ui",
)
authored_record = build_patient_authored_record(authoring_input)
mapped_result = map_authored_patient_to_patient_context(authored_record)
```

Rendered result sections will include:
- patient identity
- conditions
- medications
- allergies
- background facts
- unresolved authoring gaps
- authoring evidence
- mapped patient context
- unmapped fields
- one optional raw JSON inspector section using `model_dump_json(indent=2)`

## Implementation Notes
- Use stdlib WSGI only: `wsgiref.simple_server` for local run, inline HTML rendering in Python, no templating engine.
- Expose a top-level WSGI callable `app` so tests can hit it through `httpx.WSGITransport`.
- Keep HTML/CSS minimal and inline. No separate static assets.
- Keep form state sticky after submit so the page is immediately inspectable.

## Test Plan
Add route/page tests in [tests/test_patient_authoring_web_app.py](/Users/davidcumming/coding_projects/fhir_bundle_builder/tests/test_patient_authoring_web_app.py):

- `GET /patient-authoring` returns `200` and renders heading plus form fields.
- `GET /` redirects to `/patient-authoring`.
- `POST /patient-authoring` with valid narrative and complexity returns `200` and includes:
  - authored patient identity
  - at least one authored section such as conditions/medications/allergies when applicable
  - mapped patient context section
- `POST /patient-authoring` with empty narrative returns `400` and visible error text.
- `POST /patient-authoring` with invalid complexity returns `400` and visible error text.
- Optional narrow assertion that raw JSON block is present for inspection.

Verification pass after implementation:
- run `pytest tests/test_patient_authoring_web_app.py`
- run full `pytest`

## Run Instructions
- `source .venv/bin/activate`
- `PYTHONPATH=src python -m fhir_bundle_builder.web.patient_authoring_app`
- Open `http://127.0.0.1:8000/patient-authoring`

README update will add only this minimal browser-slice run path and note that it is a thin local inspection UI.

## Assumptions And Risks
- Assumption: the smallest maintainable choice is a stdlib WSGI app because the repo has no existing web framework pattern and already has enough test support via `httpx`.
- Assumption: a single fixed `scenario_label="patient-authoring-web-ui"` is sufficient for this slice.
- Risk: inline HTML in Python is not a long-term UI pattern. Recommendation: accept that for Slice 1 because it keeps the surface narrow and avoids introducing a frontend architecture prematurely.
- Risk: `PatientAuthoringInput` does not itself reject empty text. Recommendation: enforce trimmed non-empty validation in the route and treat that as the user-facing boundary for this slice.
