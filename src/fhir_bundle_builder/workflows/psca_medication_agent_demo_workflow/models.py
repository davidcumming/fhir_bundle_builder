"""Typed models for the one-click MedicationRequest agent demo workflow."""

from __future__ import annotations

from pydantic import BaseModel


class MedicationAgentDemoInput(BaseModel):
    """Empty top-level input for the one-click Dev UI MedicationRequest agent demo."""

    pass
