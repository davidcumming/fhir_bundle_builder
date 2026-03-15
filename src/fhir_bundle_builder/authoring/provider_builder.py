"""Deterministic demo builder for bounded provider authoring."""

from __future__ import annotations

import hashlib
import re

from .provider_models import (
    ProviderAuthoredIdentity,
    ProviderAuthoredOrganization,
    ProviderAuthoredProfessionalFacts,
    ProviderAuthoredRecord,
    ProviderAuthoredRoleRelationship,
    ProviderAuthoringEvidence,
    ProviderAuthoringGap,
    ProviderAuthoringInput,
)

_ROLE_PATTERNS: list[tuple[str, str]] = [
    ("family doctor", "family doctor"),
    ("oncologist", "oncologist"),
    ("surgeon", "surgeon"),
    ("cardiologist", "cardiologist"),
    ("nurse practitioner", "nurse practitioner"),
]


def build_provider_authored_record(authoring_input: ProviderAuthoringInput) -> ProviderAuthoredRecord:
    """Build one bounded authored provider record from natural-language input."""

    text = authoring_input.authoring_text.strip()
    lowered = text.lower()

    extracted_name = _extract_name(text)
    extracted_gender = _extract_gender(lowered)
    extracted_role_label = _extract_role_label(lowered)
    extracted_jurisdiction = _extract_jurisdiction_text(text)
    extracted_organization_name = _extract_organization_name(text)
    scenario_tags = _scenario_tags(lowered, extracted_organization_name)

    display_name, display_name_source_mode, display_name_source_note = _provider_display_name(
        extracted_name,
        extracted_role_label,
    )
    provider_id = _deterministic_provider_id(display_name, text)
    record_id = _deterministic_record_id(text, authoring_input.scenario_label)

    organizations = _authored_organizations(extracted_organization_name, text)
    provider_role_relationships = _authored_provider_role_relationships(
        organizations,
        extracted_role_label,
        extracted_organization_name,
    )
    selected_provider_role_relationship_id = (
        provider_role_relationships[0].relationship_id if provider_role_relationships else None
    )

    return ProviderAuthoredRecord(
        record_id=record_id,
        scenario_label=authoring_input.scenario_label,
        provider=ProviderAuthoredIdentity(
            provider_id=provider_id,
            display_name=display_name,
        ),
        professional_facts=ProviderAuthoredProfessionalFacts(
            administrative_gender=extracted_gender,
            specialty_or_role_label=extracted_role_label,
            jurisdiction_text=extracted_jurisdiction,
        ),
        organizations=organizations,
        provider_role_relationships=provider_role_relationships,
        selected_provider_role_relationship_id=selected_provider_role_relationship_id,
        unresolved_authoring_gaps=_authoring_gaps(
            extracted_name=extracted_name,
            organizations=organizations,
            provider_role_relationships=provider_role_relationships,
        ),
        authoring_evidence=ProviderAuthoringEvidence(
            source_authoring_text=text,
            builder_mode="demo_template_authoring",
            extracted_name=extracted_name,
            extracted_gender=extracted_gender,
            extracted_specialty_or_role_label=extracted_role_label,
            extracted_jurisdiction_text=extracted_jurisdiction,
            extracted_organization_name=extracted_organization_name,
            applied_scenario_tags=scenario_tags,
            display_name_source_mode=display_name_source_mode,
            display_name_source_note=display_name_source_note,
        ),
    )


def _extract_name(text: str) -> str | None:
    patterns = [
        re.compile(r"\b(?:name is|named) (?P<name>(?:Dr\. )?[A-Z][A-Za-z'-]+(?: [A-Z][A-Za-z'-]+)+)\b"),
        re.compile(r"\bprovider is (?P<name>(?:Dr\. )?[A-Z][A-Za-z'-]+(?: [A-Z][A-Za-z'-]+)+)\b"),
        re.compile(r"\bdoctor is (?P<name>(?:Dr\. )?[A-Z][A-Za-z'-]+(?: [A-Z][A-Za-z'-]+)+)\b"),
    ]
    for pattern in patterns:
        match = pattern.search(text)
        if match is not None:
            return match.group("name").strip().rstrip(".,")
    return None


def _extract_gender(lowered: str) -> str | None:
    padded = f" {lowered} "
    if any(token in padded for token in [" female ", " woman ", " she ", " her "]):
        return "female"
    if any(token in padded for token in [" male ", " man ", " he ", " his "]):
        return "male"
    return None


def _extract_role_label(lowered: str) -> str | None:
    for token, label in _ROLE_PATTERNS:
        if token in lowered:
            return label
    return None


def _extract_jurisdiction_text(text: str) -> str | None:
    match = re.search(
        r"\bin (?P<location>(?:[A-Z]{2,}|[A-Z][A-Za-z]+(?: [A-Z][A-Za-z]+)*)(?:, (?:[A-Z]{2,}|[A-Z][A-Za-z]+(?: [A-Z][A-Za-z]+)*))?)",
        text,
    )
    if match is None:
        return None
    return match.group("location").strip().rstrip(".")


def _extract_organization_name(text: str) -> str | None:
    patterns = [
        re.compile(
            r"\b(?:at|with|from|works at|practices at) "
            r"(?P<organization>[A-Z][A-Za-z0-9&.'-]+(?: [A-Z][A-Za-z0-9&.'-]+)*)"
            r"(?=$|[,.])"
        ),
    ]
    for pattern in patterns:
        match = pattern.search(text)
        if match is not None:
            return match.group("organization").strip().rstrip(".,")
    return None


def _scenario_tags(lowered: str, extracted_organization_name: str | None) -> list[str]:
    tags: list[str] = []
    role_label = _extract_role_label(lowered)
    if role_label is not None:
        tags.append(f"role:{role_label.replace(' ', '-')}")
    if extracted_organization_name is not None:
        tags.append("organization_explicit")
    if "bc" in lowered or "british columbia" in lowered:
        tags.append("jurisdiction:bc")
    return tags


def _provider_display_name(
    extracted_name: str | None,
    extracted_role_label: str | None,
) -> tuple[str, str, str]:
    if extracted_name is not None:
        return (
            extracted_name,
            "direct_extraction",
            "Prompt explicitly names the provider.",
        )
    if extracted_role_label is not None:
        return (
            f"Authored {extracted_role_label.title()}",
            "scenario_template",
            "Prompt did not provide a provider name, so a bounded role-based label was used.",
        )
    return (
        "Authored Provider",
        "scenario_template",
        "Prompt did not provide a provider name, so a bounded generic provider label was used.",
    )


def _authored_organizations(
    extracted_organization_name: str | None,
    authoring_text: str,
) -> list[ProviderAuthoredOrganization]:
    if extracted_organization_name is None:
        return []
    return [
        ProviderAuthoredOrganization(
            organization_id=_deterministic_organization_id(extracted_organization_name, authoring_text),
            display_name=extracted_organization_name,
            source_mode="direct_extraction",
            source_note="Prompt explicitly names the organization.",
        )
    ]


def _authored_provider_role_relationships(
    organizations: list[ProviderAuthoredOrganization],
    extracted_role_label: str | None,
    extracted_organization_name: str | None,
) -> list[ProviderAuthoredRoleRelationship]:
    if not organizations or extracted_role_label is None or extracted_organization_name is None:
        return []
    relationship_id = _deterministic_relationship_id(
        organization_display_name=extracted_organization_name,
        role_label=extracted_role_label,
    )
    return [
        ProviderAuthoredRoleRelationship(
            relationship_id=relationship_id,
            organization_id=organizations[0].organization_id,
            role_label=extracted_role_label,
            source_mode="direct_extraction",
            source_note="Prompt explicitly supports both organization and provider-role label.",
        )
    ]


def _authoring_gaps(
    extracted_name: str | None,
    organizations: list[ProviderAuthoredOrganization],
    provider_role_relationships: list[ProviderAuthoredRoleRelationship],
) -> list[ProviderAuthoringGap]:
    gaps: list[ProviderAuthoringGap] = []
    if extracted_name is None:
        gaps.append(
            ProviderAuthoringGap(
                gap_code="missing_named_provider",
                reason="Prompt did not explicitly identify a named provider.",
            )
        )
    if not organizations:
        gaps.append(
            ProviderAuthoringGap(
                gap_code="missing_organization",
                reason="Prompt did not explicitly support authoring an organization.",
            )
        )
    if not provider_role_relationships:
        gaps.append(
            ProviderAuthoringGap(
                gap_code="missing_provider_role_relationship",
                reason="Prompt did not explicitly support a linked provider-role relationship.",
            )
        )
    return gaps


def _deterministic_provider_id(display_name: str, authoring_text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", display_name.lower()).strip("-") or "authored-provider"
    suffix = hashlib.sha1(authoring_text.encode("utf-8")).hexdigest()[:8]
    return f"{slug}-{suffix}"


def _deterministic_organization_id(display_name: str, authoring_text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", display_name.lower()).strip("-") or "authored-organization"
    suffix = hashlib.sha1(f"{display_name}:{authoring_text}".encode("utf-8")).hexdigest()[:8]
    return f"{slug}-{suffix}"


def _deterministic_relationship_id(organization_display_name: str, role_label: str) -> str:
    org_slug = re.sub(r"[^a-z0-9]+", "-", organization_display_name.lower()).strip("-") or "organization"
    role_slug = re.sub(r"[^a-z0-9]+", "-", role_label.lower()).strip("-") or "role"
    suffix = hashlib.sha1(f"{organization_display_name}:{role_label}".encode("utf-8")).hexdigest()[:8]
    return f"{org_slug}-{role_slug}-{suffix}"


def _deterministic_record_id(authoring_text: str, scenario_label: str) -> str:
    suffix = hashlib.sha1(f"{scenario_label}:{authoring_text}".encode("utf-8")).hexdigest()[:10]
    return f"provider-authored-record-{suffix}"
