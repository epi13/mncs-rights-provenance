"""Versioned implementation-origin lineage for artifact records.

This extension classifies computational implementation components without
claiming that the classification is complete or legally verified.  The
containing content-addressed lineage record binds the extension bytes.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA_VERSION = "mncs.rights-provenance.implementation-lineage/0.1.0"
EXTENSION_KEY = "mncs-rights:implementation-lineage"
MAX_COMPONENTS = 64
MAX_EVIDENCE = 16

REPRESENTATION_ORDER = (
    "machine-native",
    "host-language",
    "mixed",
    "other",
    "unknown",
)
ORIGIN_ORDER = (
    "new-local",
    "migrated",
    "inherited-external",
    "generated",
    "mixed",
    "unknown",
)
EVIDENCE_STATE_ORDER = (
    "directly-observed",
    "declared",
    "inferred",
    "verified-attestation",
    "unverified-attestation",
    "unavailable",
)
REPRESENTATIONS = frozenset(REPRESENTATION_ORDER)
ORIGINS = frozenset(ORIGIN_ORDER)
EVIDENCE_STATES = frozenset(EVIDENCE_STATE_ORDER)


def implementation_component_status(
    representation: int,
    origin: int,
    evidence_state: int,
    has_evidence: int,
    has_verified_verifier: int,
) -> str:
    """Host mirror of ``implementation_component_status`` in the MNCS core."""
    values = (representation, origin, evidence_state, has_evidence, has_verified_verifier)
    if any(not isinstance(value, int) or isinstance(value, bool) for value in values):
        return "Invalid"
    if not 0 <= representation < len(REPRESENTATION_ORDER):
        return "Invalid"
    if not 0 <= origin < len(ORIGIN_ORDER):
        return "Invalid"
    if not 0 <= evidence_state < len(EVIDENCE_STATE_ORDER):
        return "Invalid"
    if has_evidence not in (0, 1) or has_verified_verifier not in (0, 1):
        return "Invalid"
    if EVIDENCE_STATE_ORDER[evidence_state] == "unavailable":
        if (
            REPRESENTATION_ORDER[representation] == "unknown"
            and ORIGIN_ORDER[origin] == "unknown"
            and has_evidence == 0
        ):
            return "Unknown"
        return "Invalid"
    if has_evidence == 0:
        return "Invalid"
    if (
        EVIDENCE_STATE_ORDER[evidence_state] == "verified-attestation"
        and has_verified_verifier == 0
    ):
        return "Invalid"
    if (
        REPRESENTATION_ORDER[representation] == "unknown"
        and ORIGIN_ORDER[origin] == "unknown"
    ):
        return "Unknown"
    return "Known"


def implementation_lineage_status(known_components: int, total_components: int) -> str:
    """Host mirror of the bounded aggregate status in the MNCS core."""
    values = (known_components, total_components)
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in values):
        return "Invalid"
    if known_components > total_components:
        return "Invalid"
    return "Unknown" if known_components == 0 else "Partial"


def _text(value: Any, label: str, limit: int) -> str:
    if not isinstance(value, str) or not value or len(value) > limit or "\x00" in value:
        raise ValueError(f"{label} must be non-empty text of at most {limit} characters")
    return value


def _evidence(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be an object")
    allowed = {"reference", "state", "sha256", "verifier_ref"}
    if set(value) - allowed or not {"reference", "state"}.issubset(value):
        raise ValueError(f"{label} must contain only reference, state, digest, and verifier fields")
    state = value.get("state")
    if not isinstance(state, str) or state not in EVIDENCE_STATES:
        raise ValueError(f"{label}.state is unsupported")
    result: dict[str, Any] = {
        "reference": _text(value.get("reference"), f"{label}.reference", 1024),
        "state": state,
    }
    digest = value.get("sha256")
    if digest is not None:
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(char not in "0123456789abcdefABCDEF" for char in digest)
        ):
            raise ValueError(f"{label}.sha256 must be 64 hexadecimal characters")
        result["sha256"] = digest.lower()
    verifier = value.get("verifier_ref")
    if verifier is not None:
        result["verifier_ref"] = _text(verifier, f"{label}.verifier_ref", 512)
    if state == "verified-attestation" and not result.get("verifier_ref"):
        raise ValueError(f"{label}.verifier_ref is required for verified attestation")
    return result


def normalize_implementation_lineage(
    value: Mapping[str, Any], *, expected_artifact_ref: str | None = None,
) -> dict[str, Any]:
    """Validate and normalize one bounded implementation-lineage extension."""
    if not isinstance(value, Mapping):
        raise TypeError("implementation lineage must be an object")
    required = {
        "schema_version", "artifact_ref", "status", "coverage", "components",
        "legal_conclusion",
    }
    if set(value) != required:
        raise ValueError("implementation lineage fields do not match the versioned contract")
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"implementation lineage schema_version must be {SCHEMA_VERSION}")
    artifact_ref = _text(value.get("artifact_ref"), "implementation_lineage.artifact_ref", 512)
    if expected_artifact_ref is not None and artifact_ref != expected_artifact_ref:
        raise ValueError("implementation lineage artifact_ref does not match its lineage subject")
    if value.get("coverage") != "unverified-subset":
        raise ValueError("implementation lineage coverage must remain unverified-subset")
    if value.get("legal_conclusion") != "NOT_MADE":
        raise ValueError("implementation lineage legal_conclusion must be NOT_MADE")
    components = value.get("components")
    if not isinstance(components, Sequence) or isinstance(components, (str, bytes)):
        raise TypeError("implementation_lineage.components must be an array")
    if len(components) > MAX_COMPONENTS:
        raise ValueError(f"implementation_lineage.components exceeds the {MAX_COMPONENTS}-item bound")
    normalized: list[dict[str, Any]] = []
    known_components = 0
    seen: set[str] = set()
    component_fields = {
        "component_ref", "representation", "origin", "evidence_state", "evidence"
    }
    for index, component in enumerate(components):
        label = f"implementation_lineage.components[{index}]"
        if not isinstance(component, Mapping) or set(component) != component_fields:
            raise ValueError(f"{label} does not match the component contract")
        component_ref = _text(component.get("component_ref"), f"{label}.component_ref", 512)
        if component_ref in seen:
            raise ValueError(f"{label}.component_ref is duplicated")
        seen.add(component_ref)
        representation = component.get("representation")
        if not isinstance(representation, str) or representation not in REPRESENTATIONS:
            raise ValueError(f"{label}.representation is unsupported")
        origin = component.get("origin")
        if not isinstance(origin, str) or origin not in ORIGINS:
            raise ValueError(f"{label}.origin is unsupported")
        evidence_state = component.get("evidence_state")
        if not isinstance(evidence_state, str) or evidence_state not in EVIDENCE_STATES:
            raise ValueError(f"{label}.evidence_state is unsupported")
        evidence = component.get("evidence")
        if not isinstance(evidence, Sequence) or isinstance(evidence, (str, bytes)):
            raise TypeError(f"{label}.evidence must be an array")
        if len(evidence) > MAX_EVIDENCE:
            raise ValueError(f"{label}.evidence exceeds the {MAX_EVIDENCE}-item bound")
        clean_evidence = [
            _evidence(item, f"{label}.evidence[{evidence_index}]")
            for evidence_index, item in enumerate(evidence)
        ]
        if evidence_state == "unavailable" and clean_evidence:
            raise ValueError(f"{label}.evidence must be empty when evidence_state is unavailable")
        if evidence_state == "unavailable" and (
            representation != "unknown" or origin != "unknown"
        ):
            raise ValueError(
                f"{label} must preserve unknown classifications when evidence is unavailable"
            )
        if evidence_state != "unavailable" and not clean_evidence:
            raise ValueError(f"{label}.evidence is required unless evidence_state is unavailable")
        if evidence_state == "verified-attestation" and not any(
            item["state"] == "verified-attestation" and item.get("verifier_ref")
            for item in clean_evidence
        ):
            raise ValueError(f"{label} needs verified evidence with a verifier_ref")
        decision = implementation_component_status(
            REPRESENTATION_ORDER.index(representation),
            ORIGIN_ORDER.index(origin),
            EVIDENCE_STATE_ORDER.index(evidence_state),
            int(bool(clean_evidence)),
            int(any(
                item["state"] == "verified-attestation" and item.get("verifier_ref")
                for item in clean_evidence
            )),
        )
        if decision == "Invalid":
            raise ValueError(f"{label} is inconsistent with implementation-lineage core rules")
        known_components += int(decision == "Known")
        normalized.append({
            "component_ref": component_ref,
            "representation": representation,
            "origin": origin,
            "evidence_state": evidence_state,
            "evidence": clean_evidence,
        })
    status = implementation_lineage_status(known_components, len(normalized)).lower()
    if value.get("status") != status:
        raise ValueError("implementation lineage status conflicts with its component classifications")
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_ref": artifact_ref,
        "status": status,
        "coverage": "unverified-subset",
        "components": normalized,
        "legal_conclusion": "NOT_MADE",
    }


__all__ = [
    "EVIDENCE_STATES",
    "EXTENSION_KEY",
    "MAX_COMPONENTS",
    "ORIGINS",
    "ORIGIN_ORDER",
    "REPRESENTATIONS",
    "REPRESENTATION_ORDER",
    "SCHEMA_VERSION",
    "EVIDENCE_STATE_ORDER",
    "implementation_component_status",
    "implementation_lineage_status",
    "normalize_implementation_lineage",
]
