from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class BundleType(str, Enum):
    PS_CA_PATIENT_SUMMARY = "ps_ca_patient_summary"


class ResourceType(str, Enum):
    PATIENT = "Patient"
    ENCOUNTER = "Encounter"
    CONDITION = "Condition"
    ALLERGY_INTOLERANCE = "AllergyIntolerance"
    MEDICATION_STATEMENT = "MedicationStatement"
    PROCEDURE = "Procedure"
    COMPOSITION = "Composition"
    BUNDLE = "Bundle"


class SeverityLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class BuildStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ESCALATED = "escalated"


class Issue(BaseModel):
    code: str
    severity: SeverityLevel
    message: str
    location: Optional[str] = None
    suggestion: Optional[str] = None
    retryable: bool = False
    details: Dict[str, Any] = Field(default_factory=dict)
