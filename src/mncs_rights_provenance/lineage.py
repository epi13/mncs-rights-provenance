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

from .artifact_binding import validate_native_artifact_binding
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

SCHEMA_VERSION = "0.4.0"
PREVIOUS_SCHEMA_VERSION = "0.3.0"
SUPPORTED_SCHEMA_VERSIONS = frozenset({PREVIOUS_SCHEMA_VERSION, SCHEMA_VERSION})

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

ARTIFACT_RELATIONS = frozenset(
    {
        "created-from",
        "derived-from",
        "generated-from",
        "transformed-by",
        "compiled-from",
        "incorporates",
        "references",
        "depends-upon",
        "independently-implemented-against",
    }
)

ARTIFACT_EVIDENCE_STATES = frozenset(
    {
        "directly-observed",
        "declared",
        "inferred",
        "verified-attestation",
        "unverified-attestation",
        "unavailable",
    }
)

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
    schema_version: str = SCHEMA_VERSION
    artifact_relationships: list[dict[str, Any]] | None = None
    artifact_transformations: list[dict[str, Any]] | None = None
    artifact_binding_refs: list[dict[str, Any]] | None = None
    artifact_lineage_state: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "schema_version": self.schema_version,
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
        if self.schema_version == SCHEMA_VERSION:
            if self.artifact_relationships is not None:
                value["artifact_relationships"] = [
                    dict(item) for item in self.artifact_relationships
                ]
            if self.artifact_transformations is not None:
                value["artifact_transformations"] = [
                    dict(item) for item in self.artifact_transformations
                ]
            if self.artifact_binding_refs is not None:
                value["artifact_binding_refs"] = [
                    dict(item) for item in self.artifact_binding_refs
                ]
            if self.artifact_lineage_state is not None:
                value["artifact_lineage_state"] = self.artifact_lineage_state
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
    schema_version = value.get("schema_version")
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise ValueError(f"unsupported lineage schema_version: {value.get('schema_version')!r}")
    subject = value.get("subject")
    if not isinstance(subject, Mapping):
        raise TypeError("lineage record requires a subject object")
    claims = value.get("authority_claims") or ()
    promotion = value.get("promotion_dimensions")
    artifact_relationships = value.get("artifact_relationships")
    artifact_transformations = value.get("artifact_transformations")
    artifact_binding_refs = value.get("artifact_binding_refs")
    if schema_version == PREVIOUS_SCHEMA_VERSION and any(
        value.get(key) is not None
        for key in (
            "artifact_relationships",
            "artifact_transformations",
            "artifact_binding_refs",
            "artifact_lineage_state",
        )
    ):
        raise ValueError("v0.3 lineage records cannot contain v0.4 artifact fields")
    if schema_version == SCHEMA_VERSION:
        if artifact_relationships is not None and (
            not isinstance(artifact_relationships, list)
            or not all(isinstance(item, Mapping) for item in artifact_relationships)
        ):
            raise TypeError("artifact_relationships entries must be objects")
        if artifact_transformations is not None and (
            not isinstance(artifact_transformations, list)
            or not all(isinstance(item, Mapping) for item in artifact_transformations)
        ):
            raise TypeError("artifact_transformations entries must be objects")
        if artifact_binding_refs is not None and (
            not isinstance(artifact_binding_refs, list)
            or not all(isinstance(item, Mapping) for item in artifact_binding_refs)
        ):
            raise TypeError("artifact_binding_refs entries must be objects")
        for index, edge in enumerate(artifact_relationships or []):
            if edge.get("relation") not in ARTIFACT_RELATIONS:
                raise ValueError(
                    f"artifact_relationships[{index}].relation is unsupported: "
                    f"{edge.get('relation')!r}"
                )
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
        schema_version=str(schema_version),
        artifact_relationships=[dict(item) for item in artifact_relationships]
        if artifact_relationships is not None else None,
        artifact_transformations=[dict(item) for item in artifact_transformations]
        if artifact_transformations is not None else None,
        artifact_binding_refs=[dict(item) for item in artifact_binding_refs]
        if artifact_binding_refs is not None else None,
        artifact_lineage_state=dict(value["artifact_lineage_state"])
        if isinstance(value.get("artifact_lineage_state"), Mapping)
        else None,
    )


def migrate_lineage_record_03_to_04(document: Mapping[str, Any]) -> dict[str, Any]:
    """Upgrade one v0.3 lineage record without inventing artifact facts.

    The only semantic change is the versioned artifact-relationship extension.
    Existing relationships and evidence are copied byte-for-byte at the JSON
    value level; the content digest is recomputed because schema_version is
    digest-bound. New artifact fields remain absent (unknown).
    """
    if document.get("schema_version") not in {PREVIOUS_SCHEMA_VERSION, SCHEMA_VERSION}:
        raise ValueError(
            f"cannot migrate lineage schema_version {document.get('schema_version')!r}"
        )
    upgraded = dict(document)
    upgraded["schema_version"] = SCHEMA_VERSION
    upgraded.pop("content_digest", None)
    upgraded["content_digest"] = compute_lineage_digest(upgraded)
    return upgraded


def lineage_record_from_artifact_binding(
    binding: Mapping[str, Any],
    *,
    lineage_id: str,
    binding_reference: str,
) -> LineageRecord:
    """Create a v0.4 lineage record that retains one native artifact binding.

    The binding itself remains an on-demand referenced record. This bounded
    projection copies only its typed artifact relationships and transformation
    record, preserving their evidence states and binding them to the exact
    canonical digest of the supplied binding value.
    """
    if not isinstance(binding, Mapping):
        raise TypeError("artifact binding must be an object")
    binding = validate_native_artifact_binding(binding)
    expected = {
        "schema_version", "artifact", "rights", "lineage", "legal_conclusion"
    }
    if set(binding) != expected or binding.get("schema_version") != (
        "mncs.rights-provenance.native-artifact-binding/0.1.0"
    ):
        raise ValueError("artifact binding does not match native-artifact-binding/0.1.0")
    if binding.get("legal_conclusion") != "NOT_MADE":
        raise ValueError("artifact binding must preserve legal_conclusion NOT_MADE")
    artifact = binding.get("artifact")
    rights = binding.get("rights")
    lineage = binding.get("lineage")
    if not all(isinstance(item, Mapping) for item in (artifact, rights, lineage)):
        raise TypeError("artifact binding requires artifact, rights, and lineage objects")
    artifact_identity = artifact.get("identity")
    producer = artifact.get("producer")
    producer_contract = artifact.get("producer_contract")
    if not all(isinstance(item, str) and item for item in (
        artifact_identity, producer, producer_contract, lineage_id, binding_reference
    )):
        raise ValueError("lineage and artifact binding references must be non-empty strings")
    if len(lineage_id) > 512 or len(binding_reference) > 1024:
        raise ValueError("lineage or artifact binding reference exceeds its bound")
    rights_state = rights.get("state")
    if not isinstance(rights_state, str) or rights_state not in {"declared", "review", "unknown"}:
        raise ValueError("artifact binding rights.state is unsupported")
    if rights.get("compatibility") != "unknown":
        raise ValueError("artifact binding compatibility must remain unknown")
    lineage_state = lineage.get("state")
    if not isinstance(lineage_state, str) or lineage_state not in {"complete", "partial", "unknown"}:
        raise ValueError("artifact binding lineage.state is unsupported")

    binding_digest = digest_prefixed(dict(binding))
    relationships = lineage.get("relationships")
    if not isinstance(relationships, list) or len(relationships) > 128:
        raise ValueError("artifact binding relationships must be a bounded list")
    retained_relationships: list[dict[str, Any]] = []
    for index, edge in enumerate(relationships):
        if not isinstance(edge, Mapping):
            raise TypeError(f"artifact binding relationship {index} must be an object")
        relation = edge.get("relation")
        if not isinstance(relation, str) or relation not in ARTIFACT_RELATIONS:
            raise ValueError(f"artifact binding relationship {index} has an unsupported relation")
        state = edge.get("evidence_state")
        if not isinstance(state, str) or state not in ARTIFACT_EVIDENCE_STATES:
            raise ValueError(f"artifact binding relationship {index} has an unsupported evidence state")
        evidence = edge.get("evidence")
        if not isinstance(evidence, list) or len(evidence) > 16:
            raise ValueError(f"artifact binding relationship {index} evidence must be bounded")
        if state != "unavailable" and not evidence:
            raise ValueError(f"artifact binding relationship {index} requires evidence")
        retained_relationships.append({**dict(edge), "binding_digest": binding_digest})

    transformation = lineage.get("transformation")
    if not isinstance(transformation, Mapping):
        raise TypeError("artifact binding transformation must be an object")
    transform_state = transformation.get("evidence_state")
    if transform_state not in {"directly-observed", "declared", "inferred", "unavailable"}:
        raise ValueError("artifact binding transformation evidence_state is unsupported")
    transform_evidence = transformation.get("evidence")
    if not isinstance(transform_evidence, list) or len(transform_evidence) > 16:
        raise ValueError("artifact binding transformation evidence must be bounded")
    if transform_state != "unavailable" and not transform_evidence:
        raise ValueError("artifact binding transformation requires evidence")
    retained_transformation = {
        **dict(transformation),
        "artifact_identity": artifact_identity,
        "binding_digest": binding_digest,
    }

    artifact_refs: list[dict[str, Any]] = [{"id": artifact_identity, "role": "subject"}]
    source_snapshot = lineage.get("source_snapshot_identity")
    if isinstance(source_snapshot, str) and source_snapshot:
        artifact_refs.append({"id": source_snapshot, "role": "input"})

    return LineageRecord(
        lineage_id=lineage_id,
        subject={"artifact_refs": artifact_refs},
        rights_summary={
            "rights_state": rights_state,
            "compatibility": "unknown",
            "legal_conclusion": "NOT_MADE",
        },
        artifact_relationships=retained_relationships,
        artifact_transformations=[retained_transformation],
        artifact_binding_refs=[{
            "reference": binding_reference,
            "content_digest": binding_digest,
            "schema_version": binding["schema_version"],
            "artifact_identity": artifact_identity,
            "producer": producer,
            "producer_contract": producer_contract,
        }],
        artifact_lineage_state={
            "state": lineage_state,
            "evidence_state": "declared" if lineage_state == "complete" else "inferred",
            "binding_digest": binding_digest,
        },
        unresolved=["rights.compatibility"],
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
    "ARTIFACT_EVIDENCE_STATES",
    "ARTIFACT_RELATIONS",
    "DERIVATION_RELATIONS",
    "EVALUATION_BINDINGS",
    "GAP_RELATIONS",
    "SCHEMA_VERSION",
    "LineageRecord",
    "compute_lineage_digest",
    "lineage_record_from_artifact_binding",
    "lineage_record_from_dict",
    "lineage_verdict",
    "migrate_lineage_record_03_to_04",
    "migrate_manifest_02_to_03",
    "seal_lineage_record",
    "verify_lineage_digest",
]
