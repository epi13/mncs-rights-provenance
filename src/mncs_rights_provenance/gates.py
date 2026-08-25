"""Normative per-gate severity semantics (canonical-release baseline).

This module mirrors gate functions in ``language/rights_policy.mncs``. Each
gate returns the severity it *would* speak at under the default canonical
release policy; profiles then cap severities via enforcement ceilings.

Severity lattice: BLOCKING(3) > REVIEW(2) > FINDING(1) > NONE(0).
"""

from __future__ import annotations

from .policy_input import (
    BLOCKING,
    FINDING,
    NONE,
    REVIEW,
    COPYRIGHT_CODES,
    HUMAN_ACCEPTANCE_CODES,
    PROVENANCE_VALIDATION_CODES,
    RIGHTS_BASIS_CODES,
    THIRD_PARTY_CODES,
    PolicyInput,
)

ENFORCEMENT_DISABLED = 0
ENFORCEMENT_FINDING = 1
ENFORCEMENT_REVIEW = 2
ENFORCEMENT_FATAL = 3


def apply_enforcement(severity: int, enforcement: int) -> int:
    """An enforcement level caps how loudly a gate may speak."""
    if enforcement >= ENFORCEMENT_FATAL:
        return severity
    if enforcement == ENFORCEMENT_REVIEW:
        return severity if severity < REVIEW else REVIEW
    if enforcement == ENFORCEMENT_FINDING:
        return severity if severity < FINDING else FINDING
    return NONE


def g_hash_correspondence(i: PolicyInput) -> int:
    return BLOCKING if i.hash_mismatch else NONE


def g_evidence_refs(i: PolicyInput) -> int:
    return REVIEW if i.broken_evidence_refs > 0 else NONE


def g_graph_integrity(i: PolicyInput) -> int:
    return BLOCKING if i.graph_invalid else NONE


def g_incompatible_license(i: PolicyInput) -> int:
    return BLOCKING if i.incompatible_source_count > 0 else NONE


def g_contradictory_license(i: PolicyInput) -> int:
    return REVIEW if i.contradiction_count > 0 else NONE


def g_rights_basis(i: PolicyInput) -> int:
    return REVIEW if i.rights_basis_code == RIGHTS_BASIS_CODES["unknown-needs-review"] else NONE


def g_third_party(i: PolicyInput) -> int:
    if i.third_party_code in (THIRD_PARTY_CODES["possible"], THIRD_PARTY_CODES["unknown"]):
        return REVIEW if i.canonical_release_profile else FINDING
    return NONE


def g_copyright_status(i: PolicyInput) -> int:
    if i.copyright_code == COPYRIGHT_CODES["unresolved"]:
        return REVIEW if i.canonical_release_profile else FINDING
    return NONE


def g_provenance_passed(i: PolicyInput) -> int:
    return BLOCKING if i.provenance_validation_code == PROVENANCE_VALIDATION_CODES["failed"] else NONE


def g_provenance_complete(i: PolicyInput) -> int:
    if i.provenance_validation_code in (
        PROVENANCE_VALIDATION_CODES["incomplete"],
        PROVENANCE_VALIDATION_CODES["not-run"],
    ):
        return REVIEW
    return NONE


def g_human_review(i: PolicyInput) -> int:
    if i.human_acceptance_code == HUMAN_ACCEPTANCE_CODES["rejected"]:
        return BLOCKING
    if i.human_acceptance_code == HUMAN_ACCEPTANCE_CODES["not-reviewed"]:
        return REVIEW if i.canonical_release_profile else FINDING
    return NONE


def g_unknown_sources(i: PolicyInput) -> int:
    if i.unknown_source_count > 0:
        return REVIEW if i.canonical_release_profile else FINDING
    return NONE


def g_attestation_integrity(i: PolicyInput) -> int:
    return REVIEW if i.attestation_conflicts > 0 else NONE


def g_impossible_evidence(i: PolicyInput) -> int:
    return BLOCKING if i.impossible_evidence else NONE


# Canonical order; also the order of the fixed-severity record in the
# MNCS-language core and the Rust implementation.
GATE_TABLE = (
    ("artifact_hash_correspondence", g_hash_correspondence, ENFORCEMENT_FATAL),
    ("evidence_references_resolve", g_evidence_refs, ENFORCEMENT_REVIEW),
    ("graph_integrity", g_graph_integrity, ENFORCEMENT_FATAL),
    ("no_incompatible_third_party_license", g_incompatible_license, ENFORCEMENT_FATAL),
    ("no_contradictory_license_evidence", g_contradictory_license, ENFORCEMENT_REVIEW),
    ("rights_basis_resolved", g_rights_basis, ENFORCEMENT_REVIEW),
    ("third_party_material_resolved", g_third_party, ENFORCEMENT_REVIEW),
    ("copyright_status_resolved", g_copyright_status, ENFORCEMENT_REVIEW),
    ("provenance_validation_passed", g_provenance_passed, ENFORCEMENT_FATAL),
    ("provenance_complete", g_provenance_complete, ENFORCEMENT_REVIEW),
    ("human_review_state_acceptable", g_human_review, ENFORCEMENT_REVIEW),
    ("unknown_source_license", g_unknown_sources, ENFORCEMENT_REVIEW),
    ("attestation_integrity", g_attestation_integrity, ENFORCEMENT_REVIEW),
    ("no_falsified_or_impossible_evidence", g_impossible_evidence, ENFORCEMENT_FATAL),
)

GATE_NAMES = tuple(name for name, _, _ in GATE_TABLE)
DEFAULT_ENFORCEMENTS = {name: enforcement for name, _, enforcement in GATE_TABLE}

GATE_FINDINGS = {
    "artifact_hash_correspondence": "artifact/hash correspondence failed",
    "evidence_references_resolve": "one or more evidence references are missing or unresolvable",
    "graph_integrity": "provenance graph violates integrity rules",
    "no_incompatible_third_party_license": "known incompatible third-party license terms",
    "no_contradictory_license_evidence": "contradictory license evidence present",
    "rights_basis_resolved": "rights basis is explicitly unknown and needs review",
    "third_party_material_resolved": "third-party material state is unresolved",
    "copyright_status_resolved": "copyright status remains unresolved",
    "provenance_validation_passed": "provenance validation failed",
    "provenance_complete": "provenance validation is incomplete or has not run",
    "human_review_state_acceptable": "human review state is unacceptable for release",
    "unknown_source_license": "one or more source licenses have unknown status",
    "attestation_integrity": "contribution attestations conflict or supersede unsoundly",
    "no_falsified_or_impossible_evidence": "evidence appears falsified or internally impossible",
}

__all__ = [
    "BLOCKING",
    "DEFAULT_ENFORCEMENTS",
    "ENFORCEMENT_DISABLED",
    "ENFORCEMENT_FATAL",
    "ENFORCEMENT_FINDING",
    "ENFORCEMENT_REVIEW",
    "FINDING",
    "GATE_FINDINGS",
    "GATE_NAMES",
    "GATE_TABLE",
    "NONE",
    "REVIEW",
    "apply_enforcement",
]
