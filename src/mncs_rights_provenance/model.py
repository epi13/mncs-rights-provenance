"""Typed view over the v0.2 manifest document model.

The dict form is canonical; these dataclasses are a convenience layer for
constructing and inspecting manifests. Unknown/optional evidence stays
explicitly optional: the library never fills missing evidence with defaults.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

ORIGIN_CLASSIFICATIONS = frozenset(
    {
        "human-authored",
        "human-ai-assisted",
        "human-directed-machine-generated",
        "autonomous-machine-generated",
        "mixed-machine-origin",
        "third-party-derived",
        "generated-from-licensed-source",
        "generated-from-public-domain-source",
        "origin-uncertain",
    }
)

COPYRIGHT_STATUSES = frozenset(
    {
        "human-authorship-confirmed",
        "human-authorship-material",
        "mixed-or-undetermined",
        "machine-originated-unresolved",
        "third-party-licensed",
        "public-domain-asserted",
        "unresolved",
    }
)

RIGHTS_BASES = frozenset(
    {
        "project-owned-or-controlled",
        "contributor-attested",
        "third-party-license",
        "public-domain-basis",
        "no-exclusive-right-asserted",
        "unknown-needs-review",
    }
)

THIRD_PARTY_STATES = frozenset({"none-known", "present", "possible", "unknown"})

ARTIFACT_CLASSES = frozenset(
    {
        "source-code",
        "documentation",
        "dataset",
        "model-weights",
        "configuration",
        "experiment-output",
        "receipt",
        "binary",
        "other",
    }
)


@dataclass(frozen=True)
class Artifact:
    id: str
    artifact_class: str
    repository: str | None = None
    commit: str | None = None
    paths: tuple[str, ...] = ()
    hashes: tuple[Mapping[str, Any], ...] = ()
    artifacts: tuple[Mapping[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {"id": self.id, "class": self.artifact_class}
        if self.hashes:
            value["hashes"] = [dict(item) for item in self.hashes]
        if self.artifacts:
            value["artifacts"] = [dict(item) for item in self.artifacts]
        if self.repository is not None:
            value["repository"] = self.repository
        if self.commit is not None:
            value["commit"] = self.commit
        if self.paths:
            value["paths"] = list(self.paths)
        return value


@dataclass(frozen=True)
class Participant:
    participant_type: str
    role: str
    name: str | None = None
    model: str | None = None
    provider: str | None = None
    runtime: str | None = None
    digest: str | None = None
    participant_ref: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {"type": self.participant_type, "role": self.role}
        for key in ("name", "model", "provider", "runtime", "digest", "participant_ref"):
            item = getattr(self, key)
            if item is not None:
                value[key] = item
        return value


@dataclass(frozen=True)
class EvidenceRef:
    kind: str
    reference: str
    sha256: str | None = None
    producer_reference: Mapping[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {"kind": self.kind, "reference": self.reference}
        if self.sha256 is not None:
            value["sha256"] = self.sha256
        if self.producer_reference is not None:
            value["producer_reference"] = dict(self.producer_reference)
        return value


@dataclass(frozen=True)
class GraphNode:
    node_id: str
    kind: str
    label: str | None = None
    artifact_class: str | None = None
    hashes: tuple[Mapping[str, Any], ...] = ()
    evidence: tuple[EvidenceRef, ...] = ()
    external_ref: str | None = None


@dataclass(frozen=True)
class GraphEdge:
    source: str
    target: str
    relation: str
    transformation: str | None = None
    evidence: tuple[EvidenceRef, ...] = ()
    timestamp: str | None = None


@dataclass(frozen=True)
class Source:
    source_kind: str
    reference: str
    license_status: str
    license: str | None = None
    confidence: str | None = None
    notes: str | None = None
    evidence: tuple[EvidenceRef, ...] = ()


@dataclass(frozen=True)
class Rights:
    distribution_license: str
    copyright_status: str
    rights_basis: str
    third_party_material: str
    sources: tuple[Source, ...] = ()
    notes: str | None = None


@dataclass(frozen=True)
class Review:
    technical_validation: str
    provenance_validation: str
    human_acceptance: str
    reviewer: str | None = None
    reviewed_at: str | None = None
    commons_refs: tuple[Mapping[str, Any], ...] = ()
    notes: str | None = None


@dataclass(frozen=True)
class Attestation:
    assertion_type: str
    asserted_by: str
    asserted_at: str
    statement: str
    asserted_by_identity: str | None = None
    applies_to: tuple[str, ...] = ()
    evidence: tuple[EvidenceRef, ...] = ()
    supersedes: tuple[str, ...] = ()
    signature: Mapping[str, Any] | None = None


@dataclass
class Manifest:
    """Mutable builder/view; serialize with :func:`manifest_to_dict`."""

    artifact: Artifact
    provenance_origin: str
    participants: list[Participant] = field(default_factory=list)
    process_evidence: list[EvidenceRef] = field(default_factory=list)
    graph_nodes: list[GraphNode] = field(default_factory=list)
    graph_edges: list[GraphEdge] = field(default_factory=list)
    rights: Rights = Rights("Apache-2.0", "unresolved", "unknown-needs-review", "unknown")
    review: Review = Review("not-run", "not-run", "not-reviewed")
    attestations: list[Attestation] = field(default_factory=list)
    spec_profile: str | None = None
    manifest_identity: str | None = None
    provenance_notes: str | None = None
    policy: Mapping[str, Any] | None = None
    extensions: dict[str, Any] = field(default_factory=dict)
