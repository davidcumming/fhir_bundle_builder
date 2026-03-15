"""Deterministic bounded refinement helpers for authored patient and provider records."""

from __future__ import annotations

import hashlib
import json
import re

from .authored_record_refinement_models import (
    PatientAuthoredRecordRefinementResult,
    PatientAuthoredRecordReviewEditInput,
    ProviderAuthoredRecordRefinementResult,
    ProviderAuthoredRecordReviewEditInput,
)
from .patient_builder import _authoring_gaps as _patient_authoring_gaps
from .patient_models import (
    PatientAuthoredAllergy,
    PatientAuthoredBackgroundFacts,
    PatientAuthoredCondition,
    PatientAuthoredIdentity,
    PatientAuthoredMedication,
    PatientAuthoredRecord,
)
from .provider_models import (
    ProviderAuthoredIdentity,
    ProviderAuthoredOrganization,
    ProviderAuthoredProfessionalFacts,
    ProviderAuthoredRecord,
    ProviderAuthoredRoleRelationship,
    ProviderAuthoringGap,
)

_MANUAL_REVIEW_SOURCE_NOTE = "Updated during bounded authored-record review/edit refinement."


def apply_patient_authored_record_review_edits(
    record: PatientAuthoredRecord,
    edits: PatientAuthoredRecordReviewEditInput | None = None,
) -> PatientAuthoredRecordRefinementResult:
    """Apply bounded structured edits to one authored patient record."""

    if edits is None or not _fields_set(edits):
        return PatientAuthoredRecordRefinementResult(
            source_record_id=record.record_id,
            refined_record_id=record.record_id,
            edits_applied=False,
            original_record=record,
            refined_record=record,
        )

    edited_field_paths: list[str] = []
    patient = record.patient.model_copy(deep=True)
    background_facts = record.background_facts.model_copy(deep=True)
    conditions = list(record.conditions)
    medications = list(record.medications)
    allergies = list(record.allergies)
    fields_set = _fields_set(edits)

    if "display_name" in fields_set:
        display_name = _normalize_required_text(edits.display_name, field_name="display_name")
        if display_name != patient.display_name:
            patient = patient.model_copy(update={"display_name": display_name})
            edited_field_paths.append("patient.display_name")

    if "administrative_gender" in fields_set and edits.administrative_gender != patient.administrative_gender:
        patient = patient.model_copy(update={"administrative_gender": edits.administrative_gender})
        edited_field_paths.append("patient.administrative_gender")

    if "age_years" in fields_set and edits.age_years != patient.age_years:
        patient = patient.model_copy(update={"age_years": edits.age_years})
        edited_field_paths.append("patient.age_years")

    if "birth_date" in fields_set:
        birth_date = _normalize_optional_text(edits.birth_date)
        if birth_date != patient.birth_date:
            patient = patient.model_copy(update={"birth_date": birth_date})
            edited_field_paths.append("patient.birth_date")

    if "residence_text" in fields_set:
        residence_text = _normalize_optional_text(edits.residence_text)
        if residence_text != background_facts.residence_text:
            background_facts = background_facts.model_copy(update={"residence_text": residence_text})
            edited_field_paths.append("background_facts.residence_text")

    if "smoking_status_text" in fields_set:
        smoking_status_text = _normalize_optional_text(edits.smoking_status_text)
        if smoking_status_text != background_facts.smoking_status_text:
            background_facts = background_facts.model_copy(update={"smoking_status_text": smoking_status_text})
            edited_field_paths.append("background_facts.smoking_status_text")

    if "condition_display_texts" in fields_set:
        condition_display_texts = _normalize_display_text_list(edits.condition_display_texts)
        if condition_display_texts != [condition.display_text for condition in record.conditions]:
            conditions = _refined_conditions(condition_display_texts)
            edited_field_paths.append("conditions")

    if "medication_display_texts" in fields_set:
        medication_display_texts = _normalize_display_text_list(edits.medication_display_texts)
        if medication_display_texts != [medication.display_text for medication in record.medications]:
            medications = _refined_medications(medication_display_texts)
            edited_field_paths.append("medications")

    if "allergy_display_texts" in fields_set:
        allergy_display_texts = _normalize_display_text_list(edits.allergy_display_texts)
        if allergy_display_texts != [allergy.display_text for allergy in record.allergies]:
            allergies = _refined_allergies(allergy_display_texts)
            edited_field_paths.append("allergies")

    if not edited_field_paths:
        return PatientAuthoredRecordRefinementResult(
            source_record_id=record.record_id,
            refined_record_id=record.record_id,
            edits_applied=False,
            original_record=record,
            refined_record=record,
        )

    refined_record = PatientAuthoredRecord(
        record_id=_deterministic_refined_record_id("patient-authored-record-refined", record.record_id, edits),
        scenario_label=record.scenario_label,
        patient=PatientAuthoredIdentity(**patient.model_dump()),
        background_facts=PatientAuthoredBackgroundFacts(**background_facts.model_dump()),
        conditions=conditions,
        medications=medications,
        allergies=allergies,
        complexity_policy_applied=record.complexity_policy_applied,
        unresolved_authoring_gaps=_patient_authoring_gaps(
            record.complexity_policy_applied,
            conditions,
            medications,
            allergies,
        ),
        authoring_evidence=record.authoring_evidence,
    )
    return PatientAuthoredRecordRefinementResult(
        source_record_id=record.record_id,
        refined_record_id=refined_record.record_id,
        edits_applied=True,
        edited_field_paths=edited_field_paths,
        original_record=record,
        refined_record=refined_record,
    )


def apply_provider_authored_record_review_edits(
    record: ProviderAuthoredRecord,
    edits: ProviderAuthoredRecordReviewEditInput | None = None,
) -> ProviderAuthoredRecordRefinementResult:
    """Apply bounded structured edits to one authored provider record."""

    if edits is None or not _fields_set(edits):
        return ProviderAuthoredRecordRefinementResult(
            source_record_id=record.record_id,
            refined_record_id=record.record_id,
            edits_applied=False,
            original_record=record,
            refined_record=record,
        )

    edited_field_paths: list[str] = []
    provider = record.provider.model_copy(deep=True)
    professional_facts = record.professional_facts.model_copy(deep=True)
    organization = record.organizations[0].model_copy(deep=True) if record.organizations else None
    relationship = (
        record.provider_role_relationships[0].model_copy(deep=True)
        if record.provider_role_relationships
        else None
    )
    fields_set = _fields_set(edits)

    if "display_name" in fields_set:
        display_name = _normalize_required_text(edits.display_name, field_name="display_name")
        if display_name != provider.display_name:
            provider = provider.model_copy(update={"display_name": display_name})
            edited_field_paths.append("provider.display_name")

    if "administrative_gender" in fields_set and edits.administrative_gender != professional_facts.administrative_gender:
        professional_facts = professional_facts.model_copy(
            update={"administrative_gender": edits.administrative_gender}
        )
        edited_field_paths.append("professional_facts.administrative_gender")

    if "specialty_or_role_label" in fields_set:
        specialty_or_role_label = _normalize_optional_text(edits.specialty_or_role_label)
        if specialty_or_role_label != professional_facts.specialty_or_role_label:
            professional_facts = professional_facts.model_copy(
                update={"specialty_or_role_label": specialty_or_role_label}
            )
            edited_field_paths.append("professional_facts.specialty_or_role_label")

    if "jurisdiction_text" in fields_set:
        jurisdiction_text = _normalize_optional_text(edits.jurisdiction_text)
        if jurisdiction_text != professional_facts.jurisdiction_text:
            professional_facts = professional_facts.model_copy(update={"jurisdiction_text": jurisdiction_text})
            edited_field_paths.append("professional_facts.jurisdiction_text")

    if "organization_display_name" in fields_set:
        organization_display_name = _normalize_optional_text(edits.organization_display_name)
        current_organization_name = organization.display_name if organization is not None else None
        if organization_display_name != current_organization_name:
            if organization_display_name is None:
                organization = None
                relationship = None
            elif organization is None:
                organization = ProviderAuthoredOrganization(
                    organization_id=_deterministic_refined_organization_id(
                        provider.provider_id,
                        organization_display_name,
                    ),
                    display_name=organization_display_name,
                    source_mode="manual_review_edit",
                    source_note=_MANUAL_REVIEW_SOURCE_NOTE,
                )
            else:
                organization = organization.model_copy(
                    update={
                        "display_name": organization_display_name,
                        "source_mode": "manual_review_edit",
                        "source_note": _MANUAL_REVIEW_SOURCE_NOTE,
                    }
                )
            edited_field_paths.append("organizations[0].display_name")

    if organization is not None and relationship is not None and relationship.organization_id != organization.organization_id:
        relationship = relationship.model_copy(update={"organization_id": organization.organization_id})

    if "relationship_role_label" in fields_set:
        relationship_role_label = _normalize_optional_text(edits.relationship_role_label)
        current_relationship_role = relationship.role_label if relationship is not None else None
        if relationship_role_label != current_relationship_role:
            if relationship_role_label is None or organization is None:
                relationship = None
            elif relationship is None:
                relationship = ProviderAuthoredRoleRelationship(
                    relationship_id=_deterministic_refined_relationship_id(
                        organization.display_name,
                        relationship_role_label,
                    ),
                    organization_id=organization.organization_id,
                    role_label=relationship_role_label,
                    source_mode="manual_review_edit",
                    source_note=_MANUAL_REVIEW_SOURCE_NOTE,
                )
            else:
                relationship = relationship.model_copy(
                    update={
                        "role_label": relationship_role_label,
                        "organization_id": organization.organization_id,
                        "source_mode": "manual_review_edit",
                        "source_note": _MANUAL_REVIEW_SOURCE_NOTE,
                    }
                )
            edited_field_paths.append("provider_role_relationships[0].role_label")

    if relationship is None:
        selected_provider_role_relationship_id = None
    else:
        selected_provider_role_relationship_id = relationship.relationship_id

    if "selected_relationship_active" in fields_set:
        selected_relationship_active = bool(edits.selected_relationship_active)
        selected_provider_role_relationship_id = (
            relationship.relationship_id
            if selected_relationship_active and relationship is not None
            else None
        )
        if selected_provider_role_relationship_id != record.selected_provider_role_relationship_id:
            edited_field_paths.append("selected_provider_role_relationship_id")
    elif selected_provider_role_relationship_id != record.selected_provider_role_relationship_id:
        edited_field_paths.append("selected_provider_role_relationship_id")

    if not edited_field_paths:
        return ProviderAuthoredRecordRefinementResult(
            source_record_id=record.record_id,
            refined_record_id=record.record_id,
            edits_applied=False,
            original_record=record,
            refined_record=record,
        )

    organizations = [organization] if organization is not None else []
    provider_role_relationships = [relationship] if relationship is not None else []
    refined_record = ProviderAuthoredRecord(
        record_id=_deterministic_refined_record_id("provider-authored-record-refined", record.record_id, edits),
        scenario_label=record.scenario_label,
        provider=ProviderAuthoredIdentity(**provider.model_dump()),
        professional_facts=ProviderAuthoredProfessionalFacts(**professional_facts.model_dump()),
        organizations=organizations,
        provider_role_relationships=provider_role_relationships,
        selected_provider_role_relationship_id=selected_provider_role_relationship_id,
        unresolved_authoring_gaps=_provider_authoring_gaps(
            provider_display_name=provider.display_name,
            organizations=organizations,
            provider_role_relationships=provider_role_relationships,
        ),
        authoring_evidence=record.authoring_evidence,
    )
    return ProviderAuthoredRecordRefinementResult(
        source_record_id=record.record_id,
        refined_record_id=refined_record.record_id,
        edits_applied=True,
        edited_field_paths=edited_field_paths,
        original_record=record,
        refined_record=refined_record,
    )


def _refined_conditions(display_texts: list[str]) -> list[PatientAuthoredCondition]:
    return [
        PatientAuthoredCondition(
            condition_id=f"condition-reviewed-{index}",
            display_text=display_text,
            source_mode="manual_review_edit",
            source_note=_MANUAL_REVIEW_SOURCE_NOTE,
        )
        for index, display_text in enumerate(display_texts, start=1)
    ]


def _refined_medications(display_texts: list[str]) -> list[PatientAuthoredMedication]:
    return [
        PatientAuthoredMedication(
            medication_id=f"medication-reviewed-{index}",
            display_text=display_text,
            source_mode="manual_review_edit",
            source_note=_MANUAL_REVIEW_SOURCE_NOTE,
        )
        for index, display_text in enumerate(display_texts, start=1)
    ]


def _refined_allergies(display_texts: list[str]) -> list[PatientAuthoredAllergy]:
    return [
        PatientAuthoredAllergy(
            allergy_id=f"allergy-reviewed-{index}",
            display_text=display_text,
            source_mode="manual_review_edit",
            source_note=_MANUAL_REVIEW_SOURCE_NOTE,
        )
        for index, display_text in enumerate(display_texts, start=1)
    ]


def _provider_authoring_gaps(
    provider_display_name: str,
    organizations: list[ProviderAuthoredOrganization],
    provider_role_relationships: list[ProviderAuthoredRoleRelationship],
) -> list[ProviderAuthoringGap]:
    gaps: list[ProviderAuthoringGap] = []
    if not _looks_like_named_provider(provider_display_name):
        gaps.append(
            ProviderAuthoringGap(
                gap_code="missing_named_provider",
                reason="The refined record does not yet include an explicit named provider identity.",
            )
        )
    if not organizations:
        gaps.append(
            ProviderAuthoringGap(
                gap_code="missing_organization",
                reason="The refined record does not yet include an explicit organization.",
            )
        )
    if not provider_role_relationships:
        gaps.append(
            ProviderAuthoringGap(
                gap_code="missing_provider_role_relationship",
                reason="The refined record does not yet include a linked provider-role relationship.",
            )
        )
    return gaps


def _looks_like_named_provider(display_name: str) -> bool:
    normalized = display_name.strip()
    return bool(normalized) and not normalized.startswith("Authored ")


def _fields_set(model: object) -> set[str]:
    return set(getattr(model, "model_fields_set", set()))


def _normalize_required_text(value: str | None, *, field_name: str) -> str:
    normalized = _normalize_optional_text(value)
    if normalized is None:
        raise ValueError(f"{field_name} cannot be blank in authored-record refinement.")
    return normalized


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_display_text_list(values: list[str] | None) -> list[str]:
    if values is None:
        return []
    return [display_text for display_text in (_normalize_optional_text(value) for value in values) if display_text]


def _deterministic_refined_record_id(prefix: str, source_record_id: str, edits: object) -> str:
    payload = json.dumps(
        getattr(edits, "model_dump")(mode="json", exclude_none=False),
        sort_keys=True,
    )
    suffix = hashlib.sha1(f"{source_record_id}:{payload}".encode("utf-8")).hexdigest()[:10]
    return f"{prefix}-{suffix}"


def _deterministic_refined_organization_id(provider_id: str, organization_display_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", organization_display_name.lower()).strip("-") or "authored-organization"
    suffix = hashlib.sha1(f"{provider_id}:{organization_display_name}".encode("utf-8")).hexdigest()[:8]
    return f"{slug}-{suffix}"


def _deterministic_refined_relationship_id(organization_display_name: str, role_label: str) -> str:
    organization_slug = re.sub(r"[^a-z0-9]+", "-", organization_display_name.lower()).strip("-") or "organization"
    role_slug = re.sub(r"[^a-z0-9]+", "-", role_label.lower()).strip("-") or "role"
    suffix = hashlib.sha1(f"{organization_display_name}:{role_label}".encode("utf-8")).hexdigest()[:8]
    return f"{organization_slug}-{role_slug}-{suffix}"
