"""Deterministic demo builder for bounded patient authoring."""

from __future__ import annotations

import hashlib
import re

from .patient_models import (
    PatientAuthoredAllergy,
    PatientAuthoredBackgroundFacts,
    PatientAuthoredCondition,
    PatientAuthoredIdentity,
    PatientAuthoredMedication,
    PatientAuthoredRecord,
    PatientAuthoringEvidence,
    PatientAuthoringGap,
    PatientAuthoringInput,
    PatientComplexityLevel,
    PatientComplexityPolicy,
)

_COMPLEXITY_POLICIES: dict[PatientComplexityLevel, PatientComplexityPolicy] = {
    "low": PatientComplexityPolicy(
        complexity_level="low",
        history_detail="brief",
        target_condition_count=1,
        target_medication_count=1,
        target_allergy_count=0,
    ),
    "medium": PatientComplexityPolicy(
        complexity_level="medium",
        history_detail="standard",
        target_condition_count=2,
        target_medication_count=2,
        target_allergy_count=1,
    ),
    "high": PatientComplexityPolicy(
        complexity_level="high",
        history_detail="rich",
        target_condition_count=3,
        target_medication_count=3,
        target_allergy_count=2,
    ),
}


def get_patient_complexity_policy(level: PatientComplexityLevel) -> PatientComplexityPolicy:
    """Return the fixed bounded richness policy for the given complexity level."""

    return _COMPLEXITY_POLICIES[level]


def build_patient_authored_record(authoring_input: PatientAuthoringInput) -> PatientAuthoredRecord:
    """Build one bounded authored patient record from natural-language input."""

    text = authoring_input.authoring_text.strip()
    lowered = text.lower()
    policy = get_patient_complexity_policy(authoring_input.complexity_level)

    extracted_name = _extract_name(text)
    extracted_gender = _extract_gender(lowered)
    extracted_age_years = _extract_age_years(lowered)
    extracted_birth_date = _extract_birth_date(text)
    extracted_residence = _extract_residence(text)
    extracted_smoking_status = _extract_smoking_status(lowered)
    scenario_tags = _scenario_tags(lowered)

    display_name = extracted_name or "Authored Patient"
    patient_id = _deterministic_patient_id(display_name, text)
    record_id = _deterministic_record_id(text, authoring_input.scenario_label)

    conditions = _bounded_conditions(lowered, policy.target_condition_count)
    medications = _bounded_medications(lowered, policy.target_medication_count)
    allergies = _bounded_allergies(lowered, policy.target_allergy_count)

    return PatientAuthoredRecord(
        record_id=record_id,
        scenario_label=authoring_input.scenario_label,
        patient=PatientAuthoredIdentity(
            patient_id=patient_id,
            display_name=display_name,
            administrative_gender=extracted_gender,
            age_years=extracted_age_years,
            birth_date=extracted_birth_date,
        ),
        background_facts=PatientAuthoredBackgroundFacts(
            residence_text=extracted_residence,
            smoking_status_text=extracted_smoking_status,
        ),
        conditions=conditions,
        medications=medications,
        allergies=allergies,
        complexity_policy_applied=policy,
        unresolved_authoring_gaps=_authoring_gaps(policy, conditions, medications, allergies),
        authoring_evidence=PatientAuthoringEvidence(
            source_authoring_text=text,
            builder_mode="demo_template_authoring",
            extracted_name=extracted_name,
            extracted_gender=extracted_gender,
            extracted_age_years=extracted_age_years,
            extracted_birth_date=extracted_birth_date,
            extracted_residence_text=extracted_residence,
            extracted_smoking_status_text=extracted_smoking_status,
            applied_scenario_tags=scenario_tags,
        ),
    )


def _extract_name(text: str) -> str | None:
    patterns = [
        re.compile(r"\bname is (?P<name>[A-Z][A-Za-z]+(?: [A-Z][A-Za-z]+)+)\b"),
        re.compile(r"\bnamed (?P<name>[A-Z][A-Za-z]+(?: [A-Z][A-Za-z]+)+)\b"),
    ]
    for pattern in patterns:
        match = pattern.search(text)
        if match is not None:
            return match.group("name").strip()
    return None


def _extract_gender(lowered: str) -> str | None:
    if any(token in lowered for token in [" female ", " woman ", " she ", " her "]):
        return "female"
    if any(token in lowered for token in [" male ", " man ", " he ", " his "]):
        return "male"
    return None


def _extract_age_years(lowered: str) -> int | None:
    patterns = [
        re.compile(r"\bage(?: of)? (?P<age>\d{1,3})\b"),
        re.compile(r"\baged (?P<age>\d{1,3})\b"),
        re.compile(r"\b(?P<age>\d{1,3})-year-old\b"),
    ]
    for pattern in patterns:
        match = pattern.search(lowered)
        if match is not None:
            return int(match.group("age"))
    return None


def _extract_birth_date(text: str) -> str | None:
    match = re.search(r"\b(19|20)\d{2}-\d{2}-\d{2}\b", text)
    if match is None:
        return None
    return match.group(0)


def _extract_residence(text: str) -> str | None:
    match = re.search(
        r"\blives in (?P<location>[A-Z][A-Za-z]+(?: [A-Z][A-Za-z]+)*(?:, [A-Z][A-Za-z]+(?: [A-Z][A-Za-z]+)*)?)",
        text,
    )
    if match is None:
        return None
    return match.group("location").strip().rstrip(".")


def _extract_smoking_status(lowered: str) -> str | None:
    if "lifelong smoker" in lowered or "life long smoker" in lowered or "life long smokers" in lowered:
        return "Lifelong smoker"
    if "smoker" in lowered or "smoking" in lowered:
        return "Smoker"
    return None


def _scenario_tags(lowered: str) -> list[str]:
    tags: list[str] = []
    if "lung cancer" in lowered and any(token in lowered for token in ["suspicious", "suspect", "possible"]):
        tags.append("possible_lung_cancer")
    if "smoker" in lowered or "smoking" in lowered:
        tags.append("smoking_history")
    if "diabetes" in lowered:
        tags.append("diabetes_history")
    if "hypertension" in lowered or "high blood pressure" in lowered:
        tags.append("hypertension_history")
    return tags


def _bounded_conditions(lowered: str, target_count: int) -> list[PatientAuthoredCondition]:
    conditions: list[PatientAuthoredCondition] = []
    if "lung cancer" in lowered and any(token in lowered for token in ["suspicious", "suspect", "possible"]):
        conditions.append(
            PatientAuthoredCondition(
                condition_id="condition-authored-1",
                display_text="Possible lung cancer",
                source_mode="scenario_template",
                source_note="Prompt indicates clinical suspicion of lung cancer.",
            )
        )
    elif "lung cancer" in lowered:
        conditions.append(
            PatientAuthoredCondition(
                condition_id="condition-authored-1",
                display_text="Lung cancer",
                source_mode="direct_extraction",
                source_note="Prompt directly mentions lung cancer.",
            )
        )

    if "diabetes" in lowered:
        conditions.append(
            PatientAuthoredCondition(
                condition_id=f"condition-authored-{len(conditions) + 1}",
                display_text="Type 2 diabetes mellitus",
                source_mode="direct_extraction",
                source_note="Prompt directly mentions diabetes.",
            )
        )

    if "hypertension" in lowered or "high blood pressure" in lowered:
        conditions.append(
            PatientAuthoredCondition(
                condition_id=f"condition-authored-{len(conditions) + 1}",
                display_text="Hypertension",
                source_mode="direct_extraction",
                source_note="Prompt directly mentions hypertension or high blood pressure.",
            )
        )

    if "copd" in lowered or "chronic obstructive pulmonary disease" in lowered:
        conditions.append(
            PatientAuthoredCondition(
                condition_id=f"condition-authored-{len(conditions) + 1}",
                display_text="Chronic obstructive pulmonary disease",
                source_mode="direct_extraction",
                source_note="Prompt directly mentions COPD.",
            )
        )

    return conditions[:target_count]


def _bounded_medications(lowered: str, target_count: int) -> list[PatientAuthoredMedication]:
    candidates = [
        ("atorvastatin", "Atorvastatin 20 MG oral tablet"),
        ("metformin", "Metformin 500 MG oral tablet"),
        ("lisinopril", "Lisinopril 10 MG oral tablet"),
    ]
    medications: list[PatientAuthoredMedication] = []
    for token, display_text in candidates:
        if token in lowered:
            medications.append(
                PatientAuthoredMedication(
                    medication_id=f"medication-authored-{len(medications) + 1}",
                    display_text=display_text,
                    source_mode="direct_extraction",
                    source_note=f"Prompt directly mentions {token}.",
                )
            )
    return medications[:target_count]


def _bounded_allergies(lowered: str, target_count: int) -> list[PatientAuthoredAllergy]:
    candidates = [
        ("peanut allergy", "Peanut allergy"),
        ("latex allergy", "Latex allergy"),
        ("penicillin allergy", "Penicillin allergy"),
    ]
    allergies: list[PatientAuthoredAllergy] = []
    for token, display_text in candidates:
        if token in lowered:
            allergies.append(
                PatientAuthoredAllergy(
                    allergy_id=f"allergy-authored-{len(allergies) + 1}",
                    display_text=display_text,
                    source_mode="direct_extraction",
                    source_note=f"Prompt directly mentions {token}.",
                )
            )
    return allergies[:target_count]


def _authoring_gaps(
    policy: PatientComplexityPolicy,
    conditions: list[PatientAuthoredCondition],
    medications: list[PatientAuthoredMedication],
    allergies: list[PatientAuthoredAllergy],
) -> list[PatientAuthoringGap]:
    gaps: list[PatientAuthoringGap] = []
    for area, target_count, authored_count in [
        ("conditions", policy.target_condition_count, len(conditions)),
        ("medications", policy.target_medication_count, len(medications)),
        ("allergies", policy.target_allergy_count, len(allergies)),
    ]:
        if authored_count < target_count:
            gaps.append(
                PatientAuthoringGap(
                    area=area,
                    target_count=target_count,
                    authored_count=authored_count,
                    reason=(
                        "Prompt-supported content did not justify additional authored items "
                        f"for the bounded {area} target."
                    ),
                )
            )
    return gaps


def _deterministic_patient_id(display_name: str, authoring_text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", display_name.lower()).strip("-") or "authored-patient"
    suffix = hashlib.sha1(authoring_text.encode("utf-8")).hexdigest()[:8]
    return f"{slug}-{suffix}"


def _deterministic_record_id(authoring_text: str, scenario_label: str) -> str:
    suffix = hashlib.sha1(f"{scenario_label}:{authoring_text}".encode("utf-8")).hexdigest()[:10]
    return f"patient-authored-record-{suffix}"
