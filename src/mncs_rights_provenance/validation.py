"""Structural validation of v0.2 manifests and evidence records.

Hand-rolled bounded checks mirroring ``schemas/v0.2/*.json`` so validation
works without a JSON-Schema engine (matching the mncs-validator-rs approach).
The full JSON Schemas remain canonical; ``tests`` cross-checks this module
against them with ``jsonschema`` when available.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from .model import ARTIFACT_CLASSES

SCHEMA_VERSION = "0.2.0"
LINEAGE_SCHEMA_VERSION = "0.3.0"
SUPPORTED_MANIFEST_VERSIONS = frozenset({"0.2.0", "0.3.0"})

_SHA256_RE = re.compile(r"^[a-fA-F0-9]{64}$")
_TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[Tt ]\d{2}:\d{2}:\d{2}(\.\d+)?([Zz]|[+-]\d{2}:\d{2})$"
)

ORIGINS = frozenset(
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
COPYRIGHT = frozenset(
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
BASIS = frozenset(
    {
        "project-owned-or-controlled",
        "contributor-attested",
        "third-party-license",
        "public-domain-basis",
        "no-exclusive-right-asserted",
        "unknown-needs-review",
    }
)
THIRD_PARTY = frozenset({"none-known", "present", "possible", "unknown"})
EVIDENCE_KINDS = frozenset(
    {
        "fabric-receipt",
        "fabric-execution-record",
        "forge-analysis",
        "validation-receipt",
        "prompt",
        "tool-log",
        "commit",
        "external-record",
        "rights-evidence-record",
        "other",
    }
)
NODE_KINDS = frozenset({"artifact", "action", "transformation", "validation", "external"})
EDGE_RELATIONS = frozenset(
    {"derived-from", "transformed-by", "validated-by", "executed-by", "attested-by", "referenced"}
)
REVIEW_TECHNICAL = frozenset({"passed", "failed", "not-run", "not-applicable"})
REVIEW_PROVENANCE = frozenset({"passed", "failed", "incomplete", "not-run"})
REVIEW_HUMAN = frozenset({"accepted", "rejected", "not-reviewed", "not-required"})
ATTESTATION_TYPES = frozenset(
    {
        "contribution-scope",
        "origin-knowledge",
        "machine-assistance-disclosure",
        "third-party-disclosure",
        "license-basis",
        "uncertainty-acknowledgement",
        "evidence-integrity",
        "other",
    }
)
# v0.3 additive vocabulary for distributed development pressure. v0.2
# documents never contain these values; v0.3 documents may.
EVIDENCE_KINDS_V03_EXTRA = frozenset(
    {
        "forge-evaluation",
        "lineage-record",
        "capability-gap-artifact",
        "promotion-record",
        "commons-record",
    }
)
EDGE_RELATIONS_V03_EXTRA = frozenset(
    {
        "member-of",
        "supersedes",
        "superseded-by",
        "resolves-gap",
        "gap-derived-from",
        "evaluated-by",
        "approved-by",
    }
)
ATTESTATION_TYPES_V03_EXTRA = frozenset(
    {
        "changeset-membership",
        "authority-scope",
        "promotion-dimensions",
        "derivation",
        "capability-gap-link",
        "evaluation-binding",
        "approval",
    }
)
PROMOTION_DIMENSIONS = (
    "technical",
    "test_conformance",
    "compiler_backend",
    "coordination_dependency",
    "provenance",
    "authority",
    "rights_license",
    "policy",
)
PROMOTION_VERDICTS = frozenset({"pass", "fail", "unknown"})
AUTHORITY_SCOPES = frozenset(
    {
        "may_propose",
        "may_provide_evidence",
        "may_evaluate",
        "may_attest",
        "may_approve",
        "may_promote",
        "may_modify_repository",
        "may_approve_change_class",
        "unknown",
    }
)
ACTOR_CLASSES = frozenset(
    {
        "human",
        "human-directed-agent",
        "autonomous-agent",
        "forge-evaluator",
        "ci",
        "maintainer",
        "mnel-model",
        "fabric-worker",
        "external-contributor",
        "federated-deployment",
        "unknown",
    }
)
_Digest_RE = re.compile(r"^sha256:[a-f0-9]{64}$")


def validate_manifest_structure(document: Mapping[str, Any]) -> list[str]:
    """Return a sorted list of structural problems; empty means valid.

    Accepts v0.2 and v0.3 manifests. v0.2 documents validate exactly as
    before; v0.3 additionally permits the optional ``lineage`` block and the
    extended pressure vocabulary.
    """
    issues: list[str] = []
    if not isinstance(document, Mapping):
        return ["manifest must be a JSON object"]
    version = document.get("schema_version")
    if version not in SUPPORTED_MANIFEST_VERSIONS:
        issues.append(f"unsupported schema_version: {version!r}")
        return sorted(issues)
    is_v03 = version == "0.3.0"

    identity = document.get("manifest_identity")
    if identity is not None and not (isinstance(identity, str) and _SHA256_RE.match(identity)):
        issues.append("manifest_identity must be a 64-char lowercase/uppercase hex sha256")

    profile = document.get("spec_profile")
    if profile is not None and profile not in {"development", "canonical-release"}:
        issues.append(f"invalid spec_profile: {profile!r}")

    issues.extend(_validate_artifact(document.get("artifact")))
    issues.extend(_validate_provenance(document.get("provenance"), is_v03=is_v03))
    issues.extend(_validate_rights(document.get("rights"), is_v03=is_v03))
    issues.extend(_validate_review(document.get("review")))
    issues.extend(_validate_attestations(document.get("attestations"), is_v03=is_v03))
    if is_v03:
        issues.extend(_validate_manifest_lineage(document.get("lineage")))

    policy = document.get("policy")
    if policy is not None:
        if not isinstance(policy, Mapping):
            issues.append("policy must be an object")
        else:
            evaluation = policy.get("last_evaluation")
            if evaluation is not None:
                if not isinstance(evaluation, Mapping):
                    issues.append("policy.last_evaluation must be an object")
                elif evaluation.get("outcome") not in {
                    "pass",
                    "pass-with-findings",
                    "review-required",
                    "blocked",
                    "invalid",
                }:
                    issues.append("policy.last_evaluation.outcome is invalid")

    extensions = document.get("extensions")
    if extensions is not None:
        if not isinstance(extensions, Mapping):
            issues.append("extensions must be an object")
        else:
            for key in extensions:
                if not isinstance(key, str) or ":" not in key:
                    issues.append(f"extension key {key!r} must be namespaced like 'producer:key'")
    return sorted(set(issues))


def _require_object(value: Any, name: str, issues: list[str]) -> bool:
    if not isinstance(value, Mapping):
        issues.append(f"{name} must be an object")
        return False
    return True


def _validate_artifact(value: Any) -> list[str]:
    issues: list[str] = []
    if not _require_object(value, "artifact", issues):
        return issues
    if not isinstance(value.get("id"), str) or not value["id"]:
        issues.append("artifact.id must be a non-empty string")
    artifact_class = value.get("class")
    if artifact_class not in ARTIFACT_CLASSES:
        issues.append(f"invalid artifact.class: {artifact_class!r}")
    paths = value.get("paths")
    if paths is not None:
        if not isinstance(paths, list) or any(not isinstance(p, str) for p in paths):
            issues.append("artifact.paths must be an array of strings")
        elif len(paths) != len(set(paths)):
            issues.append("artifact.paths contains duplicates")
    hashes = value.get("hashes")
    if hashes is not None:
        issues.extend(_validate_hashes(hashes, "artifact.hashes"))
    artifacts = value.get("artifacts")
    if artifacts is not None:
        if not isinstance(artifacts, list):
            issues.append("artifact.artifacts must be an array")
        else:
            for index, member in enumerate(artifacts):
                if (
                    not isinstance(member, Mapping)
                    or not member.get("id")
                    or member.get("class") not in ARTIFACT_CLASSES
                ):
                    issues.append(f"artifact.artifacts[{index}] requires id and valid class")
    commit = value.get("commit")
    if commit is not None and (not isinstance(commit, str) or not commit.strip()):
        issues.append("artifact.commit must be a non-empty string when present")
    return issues


def _validate_hashes(hashes: Any, label: str) -> list[str]:
    issues: list[str] = []
    if not isinstance(hashes, list):
        issues.append(f"{label} must be an array")
        return issues
    for index, item in enumerate(hashes):
        if not isinstance(item, Mapping):
            issues.append(f"{label}[{index}] must be an object")
            continue
        if item.get("algorithm") != "sha256":
            issues.append(f"{label}[{index}].algorithm must be 'sha256'")
        if not isinstance(item.get("value"), str) or not _SHA256_RE.match(item["value"]):
            issues.append(f"{label}[{index}].value must be sha256 hex")
    return issues


def _allowed_evidence_kinds(is_v03: bool) -> frozenset[str]:
    if is_v03:
        return EVIDENCE_KINDS | EVIDENCE_KINDS_V03_EXTRA
    return EVIDENCE_KINDS


def _allowed_edge_relations(is_v03: bool) -> frozenset[str]:
    if is_v03:
        return EDGE_RELATIONS | EDGE_RELATIONS_V03_EXTRA
    return EDGE_RELATIONS


def _allowed_attestation_types(is_v03: bool) -> frozenset[str]:
    if is_v03:
        return ATTESTATION_TYPES | ATTESTATION_TYPES_V03_EXTRA
    return ATTESTATION_TYPES


def _validate_evidence_refs(items: Any, label: str, *, is_v03: bool = False) -> list[str]:
    issues: list[str] = []
    if items is None:
        return issues
    if not isinstance(items, list):
        issues.append(f"{label} must be an array")
        return issues
    allowed = _allowed_evidence_kinds(is_v03)
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            issues.append(f"{label}[{index}] must be an object")
            continue
        kind = item.get("kind")
        reference = item.get("reference")
        if kind not in allowed:
            issues.append(f"{label}[{index}].kind invalid: {kind!r}")
        if not isinstance(reference, str) or not reference:
            issues.append(f"{label}[{index}].reference must be non-empty")
        sha = item.get("sha256")
        if sha is not None and not (isinstance(sha, str) and _SHA256_RE.match(sha)):
            issues.append(f"{label}[{index}].sha256 must be sha256 hex")
        producer_reference = item.get("producer_reference")
        if producer_reference is not None:
            issues.extend(
                _validate_producer_reference(
                    producer_reference, f"{label}[{index}].producer_reference"
                )
            )
    return issues


def _validate_producer_reference(value: Any, label: str) -> list[str]:
    issues: list[str] = []
    if not isinstance(value, Mapping):
        issues.append(f"{label} must be an object")
        return issues
    for field in ("producer", "recordKind", "schemaVersion", "stableId"):
        entry = value.get(field)
        if not isinstance(entry, str) or not entry:
            issues.append(f"{label}.{field} must be a non-empty string")
    digest = value.get("contentDigest")
    if digest is not None and not (
        isinstance(digest, str) and digest.startswith("sha256:") and _SHA256_RE.match(digest[7:])
    ):
        issues.append(f"{label}.contentDigest must be 'sha256:<64 hex>'")
    return issues


def _validate_provenance(value: Any, *, is_v03: bool = False) -> list[str]:
    issues: list[str] = []
    if not _require_object(value, "provenance", issues):
        return issues
    if value.get("origin_classification") not in ORIGINS:
        issues.append(
            f"provenance.origin_classification invalid: {value.get('origin_classification')!r}"
        )
    participants = value.get("participants")
    if not isinstance(participants, list):
        issues.append("provenance.participants must be an array")
    else:
        for index, participant in enumerate(participants):
            if not isinstance(participant, Mapping):
                issues.append(f"provenance.participants[{index}] must be an object")
                continue
            if participant.get("type") not in {
                "human",
                "model",
                "agent",
                "tool",
                "organization",
                "unknown",
            }:
                issues.append(
                    f"provenance.participants[{index}].type invalid: {participant.get('type')!r}"
                )
            role = participant.get("role")
            if not isinstance(role, str) or not role:
                issues.append(f"provenance.participants[{index}].role must be non-empty")
    issues.extend(
        _validate_evidence_refs(
            value.get("process_evidence"), "provenance.process_evidence", is_v03=is_v03
        )
    )

    graph = value.get("graph")
    if graph is not None:
        if not isinstance(graph, Mapping):
            issues.append("provenance.graph must be an object")
        else:
            nodes = graph.get("nodes") or []
            edges = graph.get("edges") or []
            if not isinstance(nodes, list) or not isinstance(edges, list):
                issues.append("provenance.graph nodes/edges must be arrays")
            elif len(nodes) > 256:
                issues.append("provenance.graph.nodes exceeds 256 entries")
            elif len(edges) > 512:
                issues.append("provenance.graph.edges exceeds 512 entries")
            else:
                node_ids: set[str] = set()
                for index, node in enumerate(nodes):
                    if not isinstance(node, Mapping):
                        issues.append(f"provenance.graph.nodes[{index}] must be an object")
                        continue
                    node_id = node.get("id")
                    if not isinstance(node_id, str) or not node_id or len(node_id) > 256:
                        issues.append(f"provenance.graph.nodes[{index}].id invalid")
                    elif node_id in node_ids:
                        issues.append(f"duplicate graph node id: {node_id!r}")
                    else:
                        node_ids.add(node_id)
                    if node.get("kind") not in NODE_KINDS:
                        issues.append(
                            f"provenance.graph.nodes[{index}].kind invalid: {node.get('kind')!r}"
                        )
                for index, edge in enumerate(edges):
                    if not isinstance(edge, Mapping):
                        issues.append(f"provenance.graph.edges[{index}] must be an object")
                        continue
                    source = edge.get("from")
                    target = edge.get("to")
                    if not isinstance(source, str) or source not in node_ids:
                        issues.append(
                            f"provenance.graph.edges[{index}].from references unknown node"
                        )
                    if not isinstance(target, str) or target not in node_ids:
                        issues.append(f"provenance.graph.edges[{index}].to references unknown node")
                    if edge.get("relation") not in _allowed_edge_relations(is_v03):
                        issues.append(
                            f"provenance.graph.edges[{index}].relation invalid: {edge.get('relation')!r}"
                        )
    return issues


def _validate_rights(value: Any, *, is_v03: bool = False) -> list[str]:
    issues: list[str] = []
    if not _require_object(value, "rights", issues):
        return issues
    license_value = value.get("distribution_license")
    if not isinstance(license_value, str) or not license_value:
        issues.append("rights.distribution_license must be a non-empty string")
    if value.get("copyright_status") not in COPYRIGHT:
        issues.append(f"rights.copyright_status invalid: {value.get('copyright_status')!r}")
    if value.get("rights_basis") not in BASIS:
        issues.append(f"rights.rights_basis invalid: {value.get('rights_basis')!r}")
    if value.get("third_party_material") not in THIRD_PARTY:
        issues.append(f"rights.third_party_material invalid: {value.get('third_party_material')!r}")
    sources = value.get("sources")
    if not isinstance(sources, list):
        issues.append("rights.sources must be an array")
        return issues
    for index, source in enumerate(sources):
        if not isinstance(source, Mapping):
            issues.append(f"rights.sources[{index}] must be an object")
            continue
        if source.get("kind") not in {
            "repository",
            "file",
            "dataset",
            "model",
            "documentation",
            "conversation",
            "package",
            "other",
        }:
            issues.append(f"rights.sources[{index}].kind invalid: {source.get('kind')!r}")
        if not isinstance(source.get("reference"), str) or not source["reference"]:
            issues.append(f"rights.sources[{index}].reference must be non-empty")
        if source.get("license_status") not in {
            "compatible",
            "incompatible",
            "unknown",
            "not-applicable",
        }:
            issues.append(
                f"rights.sources[{index}].license_status invalid: {source.get('license_status')!r}"
            )
        confidence = source.get("confidence")
        if confidence is not None and confidence not in {
            "observed-declaration",
            "analysis",
            "heuristic",
            "asserted",
            "unknown",
        }:
            issues.append(f"rights.sources[{index}].confidence invalid: {confidence!r}")
        issues.extend(
            _validate_evidence_refs(
                source.get("evidence"), f"rights.sources[{index}].evidence", is_v03=is_v03
            )
        )
    return issues


def _validate_review(value: Any) -> list[str]:
    issues: list[str] = []
    if not _require_object(value, "review", issues):
        return issues
    if value.get("technical_validation") not in REVIEW_TECHNICAL:
        issues.append(f"review.technical_validation invalid: {value.get('technical_validation')!r}")
    if value.get("provenance_validation") not in REVIEW_PROVENANCE:
        issues.append(
            f"review.provenance_validation invalid: {value.get('provenance_validation')!r}"
        )
    if value.get("human_acceptance") not in REVIEW_HUMAN:
        issues.append(f"review.human_acceptance invalid: {value.get('human_acceptance')!r}")
    reviewed_at = value.get("reviewed_at")
    if reviewed_at is not None and not (
        isinstance(reviewed_at, str) and _TIMESTAMP_RE.match(reviewed_at)
    ):
        issues.append("review.reviewed_at must be an ISO-8601 timestamp")
    refs = value.get("commons_refs")
    if refs is not None:
        if not isinstance(refs, list):
            issues.append("review.commons_refs must be an array")
        else:
            for index, ref in enumerate(refs):
                issues.extend(_validate_producer_reference(ref, f"review.commons_refs[{index}]"))
    return issues


def _validate_attestations(value: Any, *, is_v03: bool = False) -> list[str]:
    issues: list[str] = []
    if value is None:
        return issues
    if not isinstance(value, list):
        issues.append("attestations must be an array")
        return issues
    allowed = _allowed_attestation_types(is_v03)
    for index, attestation in enumerate(value):
        if not isinstance(attestation, Mapping):
            issues.append(f"attestations[{index}] must be an object")
            continue
        if attestation.get("assertion_type") not in allowed:
            issues.append(
                f"attestations[{index}].assertion_type invalid: {attestation.get('assertion_type')!r}"
            )
        for field in ("assertedBy", "assertedAt", "statement"):
            entry = attestation.get(field)
            if not isinstance(entry, str) or not entry:
                issues.append(f"attestations[{index}].{field} must be non-empty")
        signature = attestation.get("signature")
        if signature is not None:
            if not isinstance(signature, Mapping):
                issues.append(f"attestations[{index}].signature must be an object")
            else:
                if signature.get("algorithm") != "ed25519":
                    issues.append(f"attestations[{index}].signature.algorithm must be 'ed25519'")
                for field in ("keyIdentifier", "value"):
                    entry = signature.get(field)
                    if not isinstance(entry, str) or not entry:
                        issues.append(f"attestations[{index}].signature.{field} must be non-empty")
    return issues


def _validate_digest_value(value: Any, label: str, issues: list[str]) -> None:
    if not isinstance(value, str) or not _Digest_RE.match(value):
        issues.append(f"{label} must be 'sha256:<64 hex>'")


def _validate_manifest_lineage(value: Any) -> list[str]:
    """Validate the optional v0.3 manifest ``lineage`` summary block."""
    issues: list[str] = []
    if value is None:
        return issues
    if not isinstance(value, Mapping):
        return ["lineage must be an object"]
    changesets = value.get("changesets")
    if changesets is not None:
        if not isinstance(changesets, list):
            issues.append("lineage.changesets must be an array")
        else:
            for index, entry in enumerate(changesets):
                if not isinstance(entry, Mapping):
                    issues.append(f"lineage.changesets[{index}] must be an object")
                    continue
                if not isinstance(entry.get("changeset_id"), str) or not entry["changeset_id"]:
                    issues.append(f"lineage.changesets[{index}].changeset_id must be non-empty")
                digest = entry.get("content_digest")
                if digest is not None:
                    _validate_digest_value(
                        digest, f"lineage.changesets[{index}].content_digest", issues
                    )
    for field in ("derives_from", "supersedes", "capability_gaps"):
        entries = value.get(field)
        if entries is not None and (
            not isinstance(entries, list) or any(not isinstance(item, str) for item in entries)
        ):
            issues.append(f"lineage.{field} must be an array of strings")
    records = value.get("lineage_records")
    if records is not None:
        if not isinstance(records, list):
            issues.append("lineage.lineage_records must be an array")
        else:
            for index, entry in enumerate(records):
                if not isinstance(entry, Mapping):
                    issues.append(f"lineage.lineage_records[{index}] must be an object")
                    continue
                if not isinstance(entry.get("lineage_id"), str) or not entry["lineage_id"]:
                    issues.append(f"lineage.lineage_records[{index}].lineage_id must be non-empty")
                digest = entry.get("content_digest")
                if digest is not None:
                    _validate_digest_value(
                        digest, f"lineage.lineage_records[{index}].content_digest", issues
                    )
    dimensions = value.get("promotion_dimensions")
    if dimensions is not None:
        issues.extend(_validate_promotion_dimensions(dimensions, "lineage.promotion_dimensions"))
    lifecycle = value.get("lifecycle")
    if lifecycle is not None:
        if not isinstance(lifecycle, Mapping):
            issues.append("lineage.lifecycle must be an object")
        elif not isinstance(lifecycle.get("to_state"), str) or not lifecycle["to_state"]:
            issues.append("lineage.lifecycle.to_state must be non-empty")
    return sorted(set(issues))


def _validate_promotion_dimensions(value: Any, label: str) -> list[str]:
    issues: list[str] = []
    if not isinstance(value, Mapping):
        return [f"{label} must be an object"]
    for name in PROMOTION_DIMENSIONS:
        entry = value.get(name)
        if not isinstance(entry, Mapping):
            issues.append(f"{label}.{name} must be an object")
            continue
        if entry.get("verdict") not in PROMOTION_VERDICTS:
            issues.append(f"{label}.{name}.verdict invalid: {entry.get('verdict')!r}")
        evidence = entry.get("evidence")
        if evidence is not None:
            issues.extend(
                _validate_evidence_refs(evidence, f"{label}.{name}.evidence", is_v03=True)
            )
    return issues


def _validate_actor_ref(value: Any, label: str) -> list[str]:
    issues: list[str] = []
    if not isinstance(value, Mapping):
        return [f"{label} must be an object"]
    if value.get("type") not in {"human", "model", "agent", "tool", "organization", "unknown"}:
        issues.append(f"{label}.type invalid: {value.get('type')!r}")
    actor_class = value.get("actor_class")
    if actor_class is not None and actor_class not in ACTOR_CLASSES:
        issues.append(f"{label}.actor_class invalid: {actor_class!r}")
    return issues


def _validate_authority_claim(value: Any, label: str) -> list[str]:
    issues: list[str] = []
    if not isinstance(value, Mapping):
        return [f"{label} must be an object"]
    issues.extend(_validate_actor_ref(value.get("subject"), f"{label}.subject"))
    if value.get("scope") not in AUTHORITY_SCOPES:
        issues.append(f"{label}.scope invalid: {value.get('scope')!r}")
    if not isinstance(value.get("asserted_by"), str) or not value["asserted_by"]:
        issues.append(f"{label}.asserted_by must be non-empty")
    if value.get("verdict") not in PROMOTION_VERDICTS:
        issues.append(f"{label}.verdict invalid: {value.get('verdict')!r}")
    level = value.get("authority_level")
    if level is not None and (not isinstance(level, int) or not 1 <= level <= 5):
        issues.append(f"{label}.authority_level must be an integer 1..5")
    evidence = value.get("basis_evidence")
    if evidence is not None:
        issues.extend(_validate_evidence_refs(evidence, f"{label}.basis_evidence", is_v03=True))
    return issues


def validate_lineage_structure(document: Mapping[str, Any]) -> list[str]:
    """Structural checks for standalone v0.3 lineage records."""
    issues: list[str] = []
    if not isinstance(document, Mapping):
        return ["lineage record must be a JSON object"]
    if document.get("schema_version") != LINEAGE_SCHEMA_VERSION:
        issues.append(f"unsupported lineage schema_version: {document.get('schema_version')!r}")
        return sorted(issues)
    if not isinstance(document.get("lineage_id"), str) or not document["lineage_id"]:
        issues.append("lineage_id must be a non-empty string")
    subject = document.get("subject")
    if not isinstance(subject, Mapping):
        issues.append("subject must be an object")
    else:
        refs = subject.get("artifact_refs")
        if not isinstance(refs, list) or not refs:
            issues.append("subject.artifact_refs must be a non-empty array")
        else:
            for index, ref in enumerate(refs):
                if (
                    not isinstance(ref, Mapping)
                    or not isinstance(ref.get("id"), str)
                    or not ref["id"]
                ):
                    issues.append(f"subject.artifact_refs[{index}] requires a non-empty id")
    for index, entry in enumerate(document.get("changesets") or ()):
        if not isinstance(entry, Mapping):
            issues.append(f"changesets[{index}] must be an object")
            continue
        if not isinstance(entry.get("changeset_id"), str) or not entry["changeset_id"]:
            issues.append(f"changesets[{index}].changeset_id must be non-empty")
        digest = entry.get("content_digest")
        if digest is not None:
            _validate_digest_value(digest, f"changesets[{index}].content_digest", issues)
    for index, edge in enumerate(document.get("derivations") or ()):
        if not isinstance(edge, Mapping):
            issues.append(f"derivations[{index}] must be an object")
            continue
        if not isinstance(edge.get("from"), str) or not edge["from"]:
            issues.append(f"derivations[{index}].from must be non-empty")
        if not isinstance(edge.get("to"), str) or not edge["to"]:
            issues.append(f"derivations[{index}].to must be non-empty")
        if edge.get("relation") not in {
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
        }:
            issues.append(f"derivations[{index}].relation invalid: {edge.get('relation')!r}")
        if edge.get("from") == edge.get("to"):
            issues.append(f"derivations[{index}] is a self-loop")
    for index, entry in enumerate(document.get("evaluations") or ()):
        if not isinstance(entry, Mapping):
            issues.append(f"evaluations[{index}] must be an object")
            continue
        if not isinstance(entry.get("evaluator"), str) or not entry["evaluator"]:
            issues.append(f"evaluations[{index}].evaluator must be non-empty")
        if entry.get("verdict") not in PROMOTION_VERDICTS:
            issues.append(f"evaluations[{index}].verdict invalid: {entry.get('verdict')!r}")
        binding = entry.get("binding")
        if binding is not None and binding not in {"advisory", "authoritative", "unknown"}:
            issues.append(f"evaluations[{index}].binding invalid: {binding!r}")
    for index, entry in enumerate(document.get("authority_claims") or ()):
        issues.extend(_validate_authority_claim(entry, f"authority_claims[{index}]"))
    for index, entry in enumerate(document.get("capability_gap_links") or ()):
        if not isinstance(entry, Mapping):
            issues.append(f"capability_gap_links[{index}] must be an object")
            continue
        if not isinstance(entry.get("gap_ref"), str) or not entry["gap_ref"]:
            issues.append(f"capability_gap_links[{index}].gap_ref must be non-empty")
    dimensions = document.get("promotion_dimensions")
    if dimensions is not None:
        issues.extend(_validate_promotion_dimensions(dimensions, "promotion_dimensions"))
    digest = document.get("content_digest")
    if not isinstance(digest, str) or not _Digest_RE.match(digest):
        issues.append("content_digest must be 'sha256:<64 hex>'")
    return sorted(set(issues))


def validate_evidence_structure(document: Mapping[str, Any]) -> list[str]:
    """Structural checks for standalone evidence records."""
    issues: list[str] = []
    if not isinstance(document, Mapping):
        return ["evidence record must be a JSON object"]
    if document.get("schema_version") != SCHEMA_VERSION:
        issues.append(f"unsupported evidence schema_version: {document.get('schema_version')!r}")
        return sorted(issues)
    if not isinstance(document.get("evidence_id"), str) or not document["evidence_id"]:
        issues.append("evidence_id must be a non-empty string")
    if document.get("kind") not in {
        "fabric-execution",
        "forge-analysis",
        "validation-result",
        "commit",
        "prompt-record",
        "tool-log",
        "contribution-attestation",
        "external-record",
        "review-decision",
        "other",
    }:
        issues.append(f"kind invalid: {document.get('kind')!r}")
    digest = document.get("content_digest")
    if not (
        isinstance(digest, str) and digest.startswith("sha256:") and _SHA256_RE.match(digest[7:])
    ):
        issues.append("content_digest must be 'sha256:<64 hex>'")
    issues.extend(_validate_producer_reference(document.get("producer"), "producer"))
    subject = document.get("subject")
    if not isinstance(subject, Mapping):
        issues.append("subject must be an object")
        return sorted(set(issues))
    artifact_refs = subject.get("artifact_refs")
    if not isinstance(artifact_refs, list) or not artifact_refs:
        issues.append("subject.artifact_refs must be a non-empty array")
    else:
        for index, ref in enumerate(artifact_refs):
            if not isinstance(ref, Mapping) or not isinstance(ref.get("id"), str) or not ref["id"]:
                issues.append(f"subject.artifact_refs[{index}] requires a non-empty id")
    for index, claim in enumerate(document.get("claims") or ()):
        if not isinstance(claim, Mapping):
            issues.append(f"claims[{index}] must be an object")
            continue
        if not isinstance(claim.get("statement"), str) or not claim["statement"]:
            issues.append(f"claims[{index}].statement must be non-empty")
        if claim.get("confidence") not in {"high", "medium", "low", "insufficient-evidence"}:
            issues.append(f"claims[{index}].confidence invalid: {claim.get('confidence')!r}")
    return sorted(set(issues))


__all__ = [
    "LINEAGE_SCHEMA_VERSION",
    "SCHEMA_VERSION",
    "SUPPORTED_MANIFEST_VERSIONS",
    "validate_evidence_structure",
    "validate_lineage_structure",
    "validate_manifest_structure",
]
