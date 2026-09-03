"""Content-addressed lineage records for cross-repository ChangeSets.

A lineage record makes one causal chain reconstructable without owning the
workflow: derivations, ChangeSet membership, contributions, evaluation
bindings, approvals, authority claims, supersessions, and capability-gap
links. History is append-only; references bind digests and exact revisions
so chains survive branch deletion, rebases, and PR merges.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .authority import (
    AuthorityClaim,
    authority_claim_from_dict,
)
from .canonical import digest_prefixed
from .promotion import (
    VERDICT_FAIL,
    VERDICT_PASS,
    VERDICT_UNKNOWN,
    PromotionInputs,
    promotion_inputs_from_dict,
)

SCHEMA_VERSION = "0.3.0"

DERIVATION_RELATIONS = frozenset(
    {
        "derived-from",
        "transformed-by",
        "validated-by",
        "executed-by",
        "attested-by",
        "referenced",
        "member-of",
        "supersedes",
        "superseded-by",
        "resolves-gap",
        "gap-derived-from",
        "evaluated-by",
        "approved-by",
    }
)

EVALUATION_BINDINGS = frozenset({"advisory", "authoritative", "unknown"})

GAP_RELATIONS = frozenset(
    {
        "reports-gap",
        "resolves-gap",
        "gap-derived-from",
        "workaround-for",
        "validates-resolution",
        "adopts-resolution",
        "unknown",
    }
)


@dataclass
class LineageRecord:
    lineage_id: str
    subject: dict[str, Any]
    changesets: list[dict[str, Any]] = field(default_factory=list)
    derivations: list[dict[str, Any]] = field(default_factory=list)
    contributions: list[dict[str, Any]] = field(default_factory=list)
    evaluations: list[dict[str, Any]] = field(default_factory=list)
    approvals: list[dict[str, Any]] = field(default_factory=list)
    authority_claims: list[AuthorityClaim] = field(default_factory=list)
    supersessions: list[dict[str, Any]] = field(default_factory=list)
    capability_gap_links: list[dict[str, Any]] = field(default_factory=list)
    promotion_dimensions: PromotionInputs | None = None
    lifecycle: dict[str, Any] | None = None
    rights_summary: dict[str, Any] | None = None
    unresolved: list[str] = field(default_factory=list)
    extensions: dict[str, Any] = field(default_factory=dict)
    content_digest: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "lineage_id": self.lineage_id,
            "subject": dict(self.subject),
        }
        if self.changesets:
            value["changesets"] = [dict(item) for item in self.changesets]
        if self.derivations:
            value["derivations"] = [dict(item) for item in self.derivations]
        if self.contributions:
            value["contributions"] = [dict(item) for item in self.contributions]
        if self.evaluations:
            value["evaluations"] = [dict(item) for item in self.evaluations]
        if self.approvals:
            value["approvals"] = [dict(item) for item in self.approvals]
        if self.authority_claims:
            value["authority_claims"] = [claim.to_dict() for claim in self.authority_claims]
        if self.supersessions:
            value["supersessions"] = [dict(item) for item in self.supersessions]
        if self.capability_gap_links:
            value["capability_gap_links"] = [dict(item) for item in self.capability_gap_links]
        if self.promotion_dimensions is not None:
            value["promotion_dimensions"] = self.promotion_dimensions.to_dict()
        if self.lifecycle is not None:
            value["lifecycle"] = dict(self.lifecycle)
        if self.rights_summary is not None:
            value["rights_summary"] = dict(self.rights_summary)
        if self.unresolved:
            value["unresolved"] = list(self.unresolved)
        if self.extensions:
            value["extensions"] = dict(self.extensions)
        if self.content_digest is not None:
            value["content_digest"] = self.content_digest
        return value


def compute_lineage_digest(record: Mapping[str, Any]) -> str:
    reduced = {key: item for key, item in record.items() if key != "content_digest"}
    return digest_prefixed(reduced)


def seal_lineage_record(record: LineageRecord) -> LineageRecord:
    record.content_digest = compute_lineage_digest(record.to_dict())
    return record


def verify_lineage_digest(value: Mapping[str, Any]) -> tuple[bool, str]:
    declared = value.get("content_digest")
    expected = compute_lineage_digest(value)
    if not isinstance(declared, str) or declared != expected:
        return False, expected
    return True, expected


def lineage_verdict(
    *,
    has_changeset: bool,
    has_derivation: bool,
    has_producer: bool,
    evidence_bound: bool,
    tamper_detected: bool,
) -> str:
    """Normative lineage-completeness verdict (mirrors the MNCS-language core).

    Tampering is FAIL. Anything missing is UNKNOWN — a lineage record never
    passes on partial evidence, and missing fields are never invented.
    """
    if tamper_detected:
        return VERDICT_FAIL
    if has_changeset and has_derivation and has_producer and evidence_bound:
        return VERDICT_PASS
    return VERDICT_UNKNOWN


def lineage_record_from_dict(value: Mapping[str, Any]) -> LineageRecord:
    if not isinstance(value, Mapping):
        raise TypeError("lineage record must be a JSON object")
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"unsupported lineage schema_version: {value.get('schema_version')!r}")
    subject = value.get("subject")
    if not isinstance(subject, Mapping):
        raise TypeError("lineage record requires a subject object")
    claims = value.get("authority_claims") or ()
    promotion = value.get("promotion_dimensions")
    return LineageRecord(
        lineage_id=str(value.get("lineage_id", "")),
        subject=dict(subject),
        changesets=[
            dict(item) for item in value.get("changesets") or () if isinstance(item, Mapping)
        ],
        derivations=[
            dict(item) for item in value.get("derivations") or () if isinstance(item, Mapping)
        ],
        contributions=[
            dict(item) for item in value.get("contributions") or () if isinstance(item, Mapping)
        ],
        evaluations=[
            dict(item) for item in value.get("evaluations") or () if isinstance(item, Mapping)
        ],
        approvals=[
            dict(item) for item in value.get("approvals") or () if isinstance(item, Mapping)
        ],
        authority_claims=[
            authority_claim_from_dict(item) for item in claims if isinstance(item, Mapping)
        ],
        supersessions=[
            dict(item) for item in value.get("supersessions") or () if isinstance(item, Mapping)
        ],
        capability_gap_links=[
            dict(item)
            for item in value.get("capability_gap_links") or ()
            if isinstance(item, Mapping)
        ],
        promotion_dimensions=promotion_inputs_from_dict(promotion)
        if isinstance(promotion, Mapping)
        else None,
        lifecycle=dict(value["lifecycle"]) if isinstance(value.get("lifecycle"), Mapping) else None,
        rights_summary=dict(value["rights_summary"])
        if isinstance(value.get("rights_summary"), Mapping)
        else None,
        unresolved=[str(item) for item in value.get("unresolved") or ()],
        extensions=dict(value["extensions"])
        if isinstance(value.get("extensions"), Mapping)
        else {},
        content_digest=value.get("content_digest")
        if isinstance(value.get("content_digest"), str)
        else None,
    )


def migrate_manifest_02_to_03(document: Mapping[str, Any]) -> dict[str, Any]:
    """Mechanical v0.2 → v0.3 manifest upgrade.

    Bumps ``schema_version`` only. No provenance, authority, or lineage is
    invented: the optional ``lineage`` block stays absent until real evidence
    populates it.
    """
    if document.get("schema_version") not in {"0.2.0", "0.3.0"}:
        raise ValueError(
            f"cannot migrate manifest schema_version {document.get('schema_version')!r}"
        )
    upgraded = dict(document)
    upgraded["schema_version"] = "0.3.0"
    return upgraded


__all__ = [
    "DERIVATION_RELATIONS",
    "EVALUATION_BINDINGS",
    "GAP_RELATIONS",
    "SCHEMA_VERSION",
    "LineageRecord",
    "compute_lineage_digest",
    "lineage_record_from_dict",
    "lineage_verdict",
    "migrate_manifest_02_to_03",
    "seal_lineage_record",
    "verify_lineage_digest",
]
