"""Policy input normalization: manifest vocabulary -> integer gate codes.

The integer encoding is shared with the MNCS-language policy core and the Rust
validator's GateInput. Source status evidence is classified separately by the
normative ``language/source_license_status.mncs`` core before it contributes
to those aggregate counts. Codes are fixed by ``specs/policy-core.md``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

ORIGIN_CODES = {
    "human-authored": 0,
    "human-ai-assisted": 1,
    "human-directed-machine-generated": 2,
    "autonomous-machine-generated": 3,
    "mixed-machine-origin": 4,
    "third-party-derived": 5,
    "generated-from-licensed-source": 6,
    "generated-from-public-domain-source": 7,
    "origin-uncertain": 8,
}

COPYRIGHT_CODES = {
    "human-authorship-confirmed": 0,
    "human-authorship-material": 1,
    "mixed-or-undetermined": 2,
    "machine-originated-unresolved": 3,
    "third-party-licensed": 4,
    "public-domain-asserted": 5,
    "unresolved": 6,
}

RIGHTS_BASIS_CODES = {
    "project-owned-or-controlled": 0,
    "contributor-attested": 1,
    "third-party-license": 2,
    "public-domain-basis": 3,
    "no-exclusive-right-asserted": 4,
    "unknown-needs-review": 5,
}

THIRD_PARTY_CODES = {"none-known": 0, "present": 1, "possible": 2, "unknown": 3}

PROVENANCE_VALIDATION_CODES = {"passed": 0, "failed": 1, "incomplete": 2, "not-run": 3}
TECHNICAL_VALIDATION_CODES = {"passed": 0, "failed": 1, "not-run": 2, "not-applicable": 3}
HUMAN_ACCEPTANCE_CODES = {"accepted": 0, "rejected": 1, "not-reviewed": 2, "not-required": 3}

# Severity lattice
NONE = 0
FINDING = 1
REVIEW = 2
BLOCKING = 3


@dataclass(frozen=True)
class PolicyInput:
    """Normalized gate inputs extracted from a manifest."""

    origin_code: int
    copyright_code: int
    rights_basis_code: int
    third_party_code: int
    provenance_validation_code: int
    human_acceptance_code: int
    incompatible_source_count: int
    unknown_source_count: int
    contradiction_count: int
    hash_mismatch: bool
    broken_evidence_refs: int
    graph_invalid: bool
    attestation_conflicts: int
    impossible_evidence: bool
    canonical_release_profile: bool


def policy_input_from_manifest(
    document: Mapping[str, Any],
    *,
    hash_mismatch: bool = False,
    broken_evidence_refs: int = 0,
    graph_invalid: bool = False,
    attestation_conflicts: int = 0,
    contradiction_count: int | None = None,
) -> PolicyInput:
    """Extract normalized codes from a manifest document.

    Structural facts (hash mismatches, broken references, graph integrity) are
    supplied by the caller because they require artifact/environment access.
    Source status labels are always declarations here; this adapter has no
    authenticated evidence input that can mark one verified.
    """

    provenance = document.get("provenance") or {}
    rights = document.get("rights") or {}
    review = document.get("review") or {}
    sources = rights.get("sources") or []

    incompatible = 0
    unknown_sources = 0
    for source in sources:
        if not isinstance(source, Mapping):
            continue
        # The v0.3 manifest carries declared labels, confidence vocabulary,
        # and evidence references, but no authenticated assessment boundary.
        # Do not turn any of those declarations into a release blocker.
        assessment = _classify_source_license_status(
            str(source.get("license_status", "unknown")), evidence_verified=False
        )
        if assessment == "verified-incompatible":
            incompatible += 1
        elif assessment in {"unverified", "verified-unknown"}:
            unknown_sources += 1

    if contradiction_count is None:
        contradiction_count = count_license_contradictions(rights)

    profile_value = document.get("spec_profile")
    canonical_release = profile_value != "development"

    return PolicyInput(
        origin_code=ORIGIN_CODES.get(
            str(provenance.get("origin_classification")), ORIGIN_CODES["origin-uncertain"]
        ),
        copyright_code=COPYRIGHT_CODES.get(
            str(rights.get("copyright_status")), COPYRIGHT_CODES["unresolved"]
        ),
        rights_basis_code=RIGHTS_BASIS_CODES.get(
            str(rights.get("rights_basis")), RIGHTS_BASIS_CODES["unknown-needs-review"]
        ),
        third_party_code=THIRD_PARTY_CODES.get(
            str(rights.get("third_party_material")), THIRD_PARTY_CODES["unknown"]
        ),
        provenance_validation_code=PROVENANCE_VALIDATION_CODES.get(
            str(review.get("provenance_validation")), PROVENANCE_VALIDATION_CODES["not-run"]
        ),
        human_acceptance_code=HUMAN_ACCEPTANCE_CODES.get(
            str(review.get("human_acceptance")), HUMAN_ACCEPTANCE_CODES["not-reviewed"]
        ),
        incompatible_source_count=incompatible,
        unknown_source_count=unknown_sources,
        contradiction_count=contradiction_count,
        hash_mismatch=hash_mismatch,
        broken_evidence_refs=broken_evidence_refs,
        graph_invalid=graph_invalid,
        attestation_conflicts=attestation_conflicts,
        impossible_evidence=False,
        canonical_release_profile=canonical_release,
    )


def count_license_contradictions(rights: Mapping[str, Any]) -> int:
    """Detect direct contradictions between declared license evidence fields.

    A contradiction exists when the distribution license asserts a permissive
    known basis while a source simultaneously declares an incompatible status,
    or when two sources for the same reference disagree on license status.
    Missing evidence is NOT a contradiction; it has its own gates.
    """

    contradictions = 0
    sources = [s for s in rights.get("sources") or () if isinstance(s, Mapping)]
    seen: dict[str, set[str]] = {}
    for source in sources:
        reference = str(source.get("reference", ""))
        license_value = source.get("license")
        if isinstance(license_value, str) and license_value:
            seen.setdefault(reference, set()).add(license_value)
    for licenses in seen.values():
        if len(licenses) > 1:
            contradictions += 1
    return contradictions


POLICY_INPUT_VERSION = "0.3.0"


def _classify_source_license_status(
    status: str, *, evidence_verified: bool
) -> str:
    """Mirror the normative MNCS source-license evidence classifier.

    ``evidence_verified`` must come from a trusted verifier outside the
    manifest. The manifest adapter intentionally always passes ``False``:
    confidence labels and evidence references are declarations, not proof.
    """

    if not evidence_verified:
        return "unverified"
    return {
        "compatible": "verified-compatible",
        "incompatible": "verified-incompatible",
        "unknown": "verified-unknown",
        "not-applicable": "verified-not-applicable",
    }.get(status, "verified-unknown")


__all__ = [
    "BLOCKING",
    "COPYRIGHT_CODES",
    "FINDING",
    "HUMAN_ACCEPTANCE_CODES",
    "NONE",
    "ORIGIN_CODES",
    "POLICY_INPUT_VERSION",
    "PROVENANCE_VALIDATION_CODES",
    "REVIEW",
    "RIGHTS_BASIS_CODES",
    "TECHNICAL_VALIDATION_CODES",
    "PolicyInput",
    "count_license_contradictions",
    "policy_input_from_manifest",
]
