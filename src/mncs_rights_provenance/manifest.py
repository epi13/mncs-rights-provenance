"""Manifest serialization, identity, and file IO."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .canonical import canonical_bytes, sha256_hex
from .model import (
    Artifact,
    Attestation,
    EvidenceRef,
    GraphEdge,
    GraphNode,
    Manifest,
    Participant,
    Review,
    Rights,
    Source,
)

SCHEMA_VERSION = "0.3.0"
BASE_SCHEMA_VERSION = "0.2.0"
SUPPORTED_MANIFEST_VERSIONS = frozenset({"0.2.0", "0.3.0"})

_IDENTITY_EXCLUDED_FIELDS = frozenset({"manifest_identity"})


def manifest_to_dict(manifest: Manifest) -> dict[str, Any]:
    provenance: dict[str, Any] = {
        "origin_classification": manifest.provenance_origin,
        "participants": [participant.to_dict() for participant in manifest.participants],
        "process_evidence": [item.to_dict() for item in manifest.process_evidence],
    }
    if manifest.provenance_notes is not None:
        provenance["notes"] = manifest.provenance_notes
    if manifest.graph_nodes or manifest.graph_edges:
        provenance["graph"] = {
            "nodes": [_node_to_dict(node) for node in manifest.graph_nodes],
            "edges": [_edge_to_dict(edge) for edge in manifest.graph_edges],
        }

    value: dict[str, Any] = {
        "schema_version": manifest.schema_version,
        "artifact": manifest.artifact.to_dict(),
        "provenance": provenance,
        "rights": _rights_to_dict(manifest.rights),
        "review": _review_to_dict(manifest.review),
    }
    if manifest.lineage is not None:
        # Lineage content requires a v0.3-aware consumer: bump upward so a
        # lineage-carrying document never masquerades as v0.2. The bump only
        # ever moves 0.2.0 -> 0.3.0, never downward, and never invents content.
        if value["schema_version"] == BASE_SCHEMA_VERSION:
            value["schema_version"] = SCHEMA_VERSION
        value["lineage"] = dict(manifest.lineage)
    if manifest.spec_profile is not None:
        value["spec_profile"] = manifest.spec_profile
    if manifest.attestations:
        value["attestations"] = [_attestation_to_dict(item) for item in manifest.attestations]
    if manifest.policy is not None:
        value["policy"] = dict(manifest.policy)
    if manifest.extensions:
        value["extensions"] = dict(manifest.extensions)
    return value


def compute_manifest_identity(document: Mapping[str, Any]) -> str:
    """Identity over canonical JSON with identity/signature fields removed."""
    reduced = {key: item for key, item in document.items() if key not in _IDENTITY_EXCLUDED_FIELDS}
    return sha256_hex(reduced)


def seal_manifest(document: dict[str, Any]) -> dict[str, Any]:
    """Attach ``manifest_identity`` to *document* and return it."""
    document["manifest_identity"] = compute_manifest_identity(document)
    return document


def manifest_from_dict(value: Mapping[str, Any]) -> Manifest:
    if not isinstance(value, Mapping):
        raise TypeError("manifest must be a JSON object")
    version = value.get("schema_version")
    if version not in SUPPORTED_MANIFEST_VERSIONS:
        raise ValueError(
            f"unsupported manifest schema_version: {version!r} (expected one of {sorted(SUPPORTED_MANIFEST_VERSIONS)!r})"
        )

    artifact_value = value.get("artifact")
    if not isinstance(artifact_value, Mapping):
        raise TypeError("manifest.artifact must be an object")
    artifact = Artifact(
        id=str(artifact_value.get("id", "")),
        artifact_class=str(artifact_value.get("class", "other")),
        repository=_optional_str(artifact_value.get("repository")),
        commit=_optional_str(artifact_value.get("commit")),
        paths=tuple(str(item) for item in artifact_value.get("paths") or ()),
        hashes=tuple(
            dict(item) for item in artifact_value.get("hashes") or () if isinstance(item, Mapping)
        ),
        artifacts=tuple(
            dict(item)
            for item in artifact_value.get("artifacts") or ()
            if isinstance(item, Mapping)
        ),
    )

    provenance_value = value.get("provenance")
    if not isinstance(provenance_value, Mapping):
        raise TypeError("manifest.provenance must be an object")

    graph_value = provenance_value.get("graph") or {}
    graph_nodes = tuple(
        GraphNode(
            node_id=str(node.get("id", "")),
            kind=str(node.get("kind", "artifact")),
            label=_optional_str(node.get("label")),
            artifact_class=_optional_str(node.get("artifact_class")),
            hashes=tuple(
                dict(item) for item in node.get("hashes") or () if isinstance(item, Mapping)
            ),
            evidence=tuple(
                _evidence_ref(item)
                for item in node.get("evidence") or ()
                if isinstance(item, Mapping)
            ),
            external_ref=_optional_str(node.get("external_ref")),
        )
        for node in graph_value.get("nodes") or ()
        if isinstance(node, Mapping)
    )
    graph_edges = tuple(
        GraphEdge(
            source=str(edge.get("from", "")),
            target=str(edge.get("to", "")),
            relation=str(edge.get("relation", "referenced")),
            transformation=_optional_str(edge.get("transformation")),
            evidence=tuple(
                _evidence_ref(item)
                for item in edge.get("evidence") or ()
                if isinstance(item, Mapping)
            ),
            timestamp=_optional_str(edge.get("timestamp")),
        )
        for edge in graph_value.get("edges") or ()
        if isinstance(edge, Mapping)
    )

    rights_value = value.get("rights")
    if not isinstance(rights_value, Mapping):
        raise TypeError("manifest.rights must be an object")
    sources = tuple(
        Source(
            source_kind=str(source.get("kind", "other")),
            reference=str(source.get("reference", "")),
            license_status=str(source.get("license_status", "unknown")),
            license=_optional_str(source.get("license")),
            confidence=_optional_str(source.get("confidence")),
            notes=_optional_str(source.get("notes")),
            evidence=tuple(
                _evidence_ref(item)
                for item in source.get("evidence") or ()
                if isinstance(item, Mapping)
            ),
        )
        for source in rights_value.get("sources") or ()
        if isinstance(source, Mapping)
    )
    rights = Rights(
        distribution_license=str(rights_value.get("distribution_license", "")),
        copyright_status=str(rights_value.get("copyright_status", "unresolved")),
        rights_basis=str(rights_value.get("rights_basis", "unknown-needs-review")),
        third_party_material=str(rights_value.get("third_party_material", "unknown")),
        sources=sources,
        notes=_optional_str(rights_value.get("notes")),
    )

    review_value = value.get("review")
    if not isinstance(review_value, Mapping):
        raise TypeError("manifest.review must be an object")
    review = Review(
        technical_validation=str(review_value.get("technical_validation", "not-run")),
        provenance_validation=str(review_value.get("provenance_validation", "not-run")),
        human_acceptance=str(review_value.get("human_acceptance", "not-reviewed")),
        reviewer=_optional_str(review_value.get("reviewer")),
        reviewed_at=_optional_str(review_value.get("reviewed_at")),
        commons_refs=tuple(
            dict(item)
            for item in review_value.get("commons_refs") or ()
            if isinstance(item, Mapping)
        ),
        notes=_optional_str(review_value.get("notes")),
    )

    attestations = tuple(
        Attestation(
            assertion_type=str(item.get("assertion_type", "other")),
            asserted_by=str(item.get("assertedBy", "")),
            asserted_at=str(item.get("assertedAt", "")),
            statement=str(item.get("statement", "")),
            asserted_by_identity=_optional_str(item.get("assertedByIdentity")),
            applies_to=tuple(str(ref) for ref in item.get("appliesTo") or ()),
            evidence=tuple(
                _evidence_ref(sub) for sub in item.get("evidence") or () if isinstance(sub, Mapping)
            ),
            supersedes=tuple(str(ref) for ref in item.get("supersedes") or ()),
            signature=dict(item["signature"])
            if isinstance(item.get("signature"), Mapping)
            else None,
        )
        for item in value.get("attestations") or ()
        if isinstance(item, Mapping)
    )

    manifest = Manifest(
        artifact=artifact,
        provenance_origin=str(provenance_value.get("origin_classification", "origin-uncertain")),
        participants=[
            Participant(
                participant_type=str(participant.get("type", "unknown")),
                role=str(participant.get("role", "unknown")),
                name=_optional_str(participant.get("name")),
                model=_optional_str(participant.get("model")),
                provider=_optional_str(participant.get("provider")),
                runtime=_optional_str(participant.get("runtime")),
                digest=_optional_str(participant.get("digest")),
                participant_ref=_optional_str(participant.get("participant_ref")),
            )
            for participant in provenance_value.get("participants") or ()
            if isinstance(participant, Mapping)
        ],
        process_evidence=[
            _evidence_ref(item)
            for item in provenance_value.get("process_evidence") or ()
            if isinstance(item, Mapping)
        ],
        rights=rights,
        review=review,
        attestations=list(attestations),
        spec_profile=_optional_str(value.get("spec_profile")),
        manifest_identity=_optional_str(value.get("manifest_identity")),
        provenance_notes=_optional_str(provenance_value.get("notes")),
        policy=dict(value["policy"]) if isinstance(value.get("policy"), Mapping) else None,
        extensions=dict(value["extensions"])
        if isinstance(value.get("extensions"), Mapping)
        else {},
        graph_nodes=list(graph_nodes),
        graph_edges=list(graph_edges),
        schema_version=str(version),
        lineage=dict(value["lineage"]) if isinstance(value.get("lineage"), Mapping) else None,
    )
    return manifest


def load_manifest_file(path: str | Path) -> Manifest:
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    return manifest_from_dict(document)


def _node_to_dict(node: GraphNode) -> dict[str, Any]:
    value: dict[str, Any] = {"id": node.node_id, "kind": node.kind}
    if node.label is not None:
        value["label"] = node.label
    if node.artifact_class is not None:
        value["artifact_class"] = node.artifact_class
    if node.hashes:
        value["hashes"] = [dict(item) for item in node.hashes]
    if node.evidence:
        value["evidence"] = [item.to_dict() for item in node.evidence]
    if node.external_ref is not None:
        value["external_ref"] = node.external_ref
    return value


def _edge_to_dict(edge: GraphEdge) -> dict[str, Any]:
    value: dict[str, Any] = {"from": edge.source, "to": edge.target, "relation": edge.relation}
    if edge.transformation is not None:
        value["transformation"] = edge.transformation
    if edge.evidence:
        value["evidence"] = [item.to_dict() for item in edge.evidence]
    if edge.timestamp is not None:
        value["timestamp"] = edge.timestamp
    return value


def _rights_to_dict(rights: Rights) -> dict[str, Any]:
    value: dict[str, Any] = {
        "distribution_license": rights.distribution_license,
        "copyright_status": rights.copyright_status,
        "rights_basis": rights.rights_basis,
        "third_party_material": rights.third_party_material,
        "sources": [],
    }
    for source in rights.sources:
        entry: dict[str, Any] = {
            "kind": source.source_kind,
            "reference": source.reference,
            "license_status": source.license_status,
        }
        if source.license is not None:
            entry["license"] = source.license
        if source.confidence is not None:
            entry["confidence"] = source.confidence
        if source.notes is not None:
            entry["notes"] = source.notes
        if source.evidence:
            entry["evidence"] = [item.to_dict() for item in source.evidence]
        value["sources"].append(entry)
    if rights.notes is not None:
        value["notes"] = rights.notes
    return value


def _review_to_dict(review: Review) -> dict[str, Any]:
    value: dict[str, Any] = {
        "technical_validation": review.technical_validation,
        "provenance_validation": review.provenance_validation,
        "human_acceptance": review.human_acceptance,
    }
    if review.reviewer is not None:
        value["reviewer"] = review.reviewer
    if review.reviewed_at is not None:
        value["reviewed_at"] = review.reviewed_at
    if review.commons_refs:
        value["commons_refs"] = [dict(item) for item in review.commons_refs]
    if review.notes is not None:
        value["notes"] = review.notes
    return value


def _attestation_to_dict(attestation: Attestation) -> dict[str, Any]:
    value: dict[str, Any] = {
        "assertion_type": attestation.assertion_type,
        "assertedBy": attestation.asserted_by,
        "assertedAt": attestation.asserted_at,
        "statement": attestation.statement,
    }
    if attestation.asserted_by_identity is not None:
        value["assertedByIdentity"] = attestation.asserted_by_identity
    if attestation.applies_to:
        value["appliesTo"] = list(attestation.applies_to)
    if attestation.evidence:
        value["evidence"] = [item.to_dict() for item in attestation.evidence]
    if attestation.supersedes:
        value["supersedes"] = list(attestation.supersedes)
    if attestation.signature is not None:
        value["signature"] = dict(attestation.signature)
    return value


def _evidence_ref(value: Mapping[str, Any]) -> EvidenceRef:
    producer_reference = value.get("producer_reference")
    return EvidenceRef(
        kind=str(value.get("kind", "other")),
        reference=str(value.get("reference", "")),
        sha256=value.get("sha256") if isinstance(value.get("sha256"), str) else None,
        producer_reference=dict(producer_reference)
        if isinstance(producer_reference, Mapping)
        else None,
    )


def _optional_str(value: Any) -> str | None:
    return str(value) if isinstance(value, str) and value else None


__all__ = [
    "BASE_SCHEMA_VERSION",
    "SCHEMA_VERSION",
    "SUPPORTED_MANIFEST_VERSIONS",
    "canonical_bytes",
    "compute_manifest_identity",
    "load_manifest_file",
    "manifest_from_dict",
    "manifest_to_dict",
    "seal_manifest",
]
