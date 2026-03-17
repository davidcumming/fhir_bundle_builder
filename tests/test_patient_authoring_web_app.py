"""Route tests for the minimal patient authoring web page."""

from __future__ import annotations

import httpx
import pytest

from fhir_bundle_builder.web.patient_authoring_app import app


@pytest.mark.asyncio
async def test_get_patient_authoring_page_renders_form_and_sections() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/patient-authoring")

    assert response.status_code == 200
    assert "Patient Profile Authoring" in response.text
    assert "textarea" in response.text
    assert "name=\"complexity\"" in response.text
    assert "Submitted Input" in response.text
    assert "Validation Errors" in response.text
    assert "Authored Patient Profile" in response.text
    assert "Mapped Patient Context" in response.text
    assert "Raw JSON Inspection" in response.text


@pytest.mark.asyncio
async def test_get_root_redirects_to_patient_authoring_page() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        response = await client.get("/")

    assert response.status_code == 302
    assert response.headers["location"] == "/patient-authoring"


@pytest.mark.asyncio
async def test_valid_post_renders_results_sections() -> None:
    transport = httpx.ASGITransport(app=app)
    narrative = (
        "The patient's name is Jane River. She is a female age 58 who lives in Calgary, Alberta. "
        "She has diabetes and hypertension, takes metformin and lisinopril, and has a peanut allergy."
    )
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/patient-authoring",
            data={"narrative": narrative, "complexity": "medium"},
        )

    assert response.status_code == 200
    assert "Submitted Input" in response.text
    assert "Authored Patient Profile" in response.text
    assert "Mapped Patient Context" in response.text
    assert "Raw JSON Inspection" in response.text
    assert "Jane River" in response.text
    assert "medium" in response.text


@pytest.mark.asyncio
async def test_empty_narrative_returns_validation_error_with_sticky_values() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/patient-authoring",
            data={"narrative": "   ", "complexity": "high"},
        )

    assert response.status_code == 400
    assert "Validation Errors" in response.text
    assert "Patient narrative is required." in response.text
    assert "option value=\"high\" selected" in response.text


@pytest.mark.asyncio
async def test_invalid_complexity_returns_validation_error_with_sticky_narrative() -> None:
    transport = httpx.ASGITransport(app=app)
    narrative = "The patient's name is Alex Winter."
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/patient-authoring",
            data={"narrative": narrative, "complexity": "extreme"},
        )

    assert response.status_code == 400
    assert "Validation Errors" in response.text
    assert "Complexity must be one of low, medium, or high." in response.text
    assert "Alex Winter" in response.text
