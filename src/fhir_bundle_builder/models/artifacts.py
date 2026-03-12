from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .common import BuildStatus, BundleType, Issue, ResourceType, utc_now


class RequestPacket(BaseModel):
    request_id: str
    bundle_type: BundleType
    user_request: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    realism_constraints: List[str] = Field(default_factory=list)
    output_expectations: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class PatientSummarySpecification(BaseModel):
    specification_id: str
    request_id: str
    bundle_type: BundleType
    patient_story: str
    sections_required: List[str] = Field(default_factory=list)
    confirmed_facts: Dict[str, Any] = Field(default_factory=dict)
    inferred_facts: Dict[str, Any] = Field(default_factory=dict)
    coding_requirements: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class BuildStep(BaseModel):
    step_id: str
    name: str
    target_resource_type: Optional[ResourceType] = None
    depends_on: List[str] = Field(default_factory=list)
    instructions: List[str] = Field(default_factory=list)
    retry_limit: int = 2
    status: BuildStatus = BuildStatus.PENDING


class BuildPlan(BaseModel):
    plan_id: str
    specification_id: str
    bundle_type: BundleType
    steps: List[BuildStep] = Field(default_factory=list)
    dependency_map: Dict[str, List[str]] = Field(default_factory=dict)
    retry_policy: Dict[str, int] = Field(default_factory=dict)
    final_assembly_instructions: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class ResourceTaskPacket(BaseModel):
    task_id: str
    build_step_id: str
    target_resource_type: ResourceType
    profile_uri: Optional[str] = None
    required_facts: Dict[str, Any] = Field(default_factory=dict)
    coded_values: Dict[str, Any] = Field(default_factory=dict)
    dependency_references: Dict[str, str] = Field(default_factory=dict)
    validation_focus: List[str] = Field(default_factory=list)
    prior_issues: List[Issue] = Field(default_factory=list)
    attempt_number: int = 1
    created_at: datetime = Field(default_factory=utc_now)


class ValidationResult(BaseModel):
    validation_id: str
    target_type: str
    target_id: str
    passed: bool
    summary: str
    issues: List[Issue] = Field(default_factory=list)
    suggested_fixes: List[str] = Field(default_factory=list)
    retryable: bool = False
    raw_result_ref: Optional[str] = None
    validated_at: datetime = Field(default_factory=utc_now)


class DeliveryPackage(BaseModel):
    delivery_id: str
    request_id: str
    bundle_type: BundleType
    status: BuildStatus
    final_bundle: Dict[str, Any] = Field(default_factory=dict)
    validation_result: Optional[ValidationResult] = None
    assumptions: List[str] = Field(default_factory=list)
    deviations: List[str] = Field(default_factory=list)
    execution_trace: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
