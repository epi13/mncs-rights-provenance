"""Structural validation of v0.2 manifests and evidence records.

Hand-rolled bounded checks mirroring ``schemas/v0.2/*.json`` so validation
works without a JSON-Schema engine (matching the mncs-validator-rs approach).
The full JSON Schemas remain canonical; ``tests`` cross-checks this module
against them with ``jsonschema`` when available.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from .model import ARTIFACT_CLASSES

SCHEMA_VERSION = "0.2.0"

_SHA256_RE = re.compile(r"^[a-fA-F0-9]{64}$")
_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[Tt ]\d{2}:\d{2}:\d{2}(\.\d+)?([Zz]|[+-]\d{2}:\d{2})$")

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
EDGE_RELATIONS = frozenset({"derived-from", "transformed-by", "validated-by", "executed-by", "attested-by", "referenced"})
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


def validate_manifest_structure(document: Mapping[str, Any]) -> list[str]:
    """Return a sorted list of structural problems; empty means valid."""
    issues: list[str] = []
    if not isinstance(document, Mapping):
        return ["manifest must be a JSON object"]
    if document.get("schema_version") != SCHEMA_VERSION:
        issues.append(f"unsupported schema_version: {document.get('schema_version')!r}")
        return sorted(issues)

    identity = document.get("manifest_identity")
    if identity is not None and not (isinstance(identity, str) and _SHA256_RE.match(identity)):
        issues.append("manifest_identity must be a 64-char lowercase/uppercase hex sha256")

    profile = document.get("spec_profile")
    if profile is not None and profile not in {"development", "canonical-release"}:
        issues.append(f"invalid spec_profile: {profile!r}")

    issues.extend(_validate_artifact(document.get("artifact")))
    issues.extend(_validate_provenance(document.get("provenance")))
    issues.extend(_validate_rights(document.get("rights")))
    issues.extend(_validate_review(document.get("review")))
    issues.extend(_validate_attestations(document.get("attestations")))

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
                if not isinstance(member, Mapping) or not member.get("id") or member.get("class") not in ARTIFACT_CLASSES:
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


def _validate_evidence_refs(items: Any, label: str) -> list[str]:
    issues: list[str] = []
    if items is None:
        return issues
    if not isinstance(items, list):
        issues.append(f"{label} must be an array")
        return issues
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            issues.append(f"{label}[{index}] must be an object")
            continue
        kind = item.get("kind")
        reference = item.get("reference")
        if kind not in EVIDENCE_KINDS:
            issues.append(f"{label}[{index}].kind invalid: {kind!r}")
        if not isinstance(reference, str) or not reference:
            issues.append(f"{label}[{index}].reference must be non-empty")
        sha = item.get("sha256")
        if sha is not None and not (isinstance(sha, str) and _SHA256_RE.match(sha)):
            issues.append(f"{label}[{index}].sha256 must be sha256 hex")
        producer_reference = item.get("producer_reference")
        if producer_reference is not None:
            issues.extend(_validate_producer_reference(producer_reference, f"{label}[{index}].producer_reference"))
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
    if digest is not None and not (isinstance(digest, str) and digest.startswith("sha256:") and _SHA256_RE.match(digest[7:])):
        issues.append(f"{label}.contentDigest must be 'sha256:<64 hex>'")
    return issues


def _validate_provenance(value: Any) -> list[str]:
    issues: list[str] = []
    if not _require_object(value, "provenance", issues):
        return issues
    if value.get("origin_classification") not in ORIGINS:
        issues.append(f"provenance.origin_classification invalid: {value.get('origin_classification')!r}")
    participants = value.get("participants")
    if not isinstance(participants, list):
        issues.append("provenance.participants must be an array")
    else:
        for index, participant in enumerate(participants):
            if not isinstance(participant, Mapping):
                issues.append(f"provenance.participants[{index}] must be an object")
                continue
            if participant.get("type") not in {"human", "model", "agent", "tool", "organization", "unknown"}:
                issues.append(f"provenance.participants[{index}].type invalid: {participant.get('type')!r}")
            role = participant.get("role")
            if not isinstance(role, str) or not role:
                issues.append(f"provenance.participants[{index}].role must be non-empty")
    issues.extend(_validate_evidence_refs(value.get("process_evidence"), "provenance.process_evidence"))

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
                        issues.append(f"provenance.graph.nodes[{index}].kind invalid: {node.get('kind')!r}")
                for index, edge in enumerate(edges):
                    if not isinstance(edge, Mapping):
                        issues.append(f"provenance.graph.edges[{index}] must be an object")
                        continue
                    source = edge.get("from")
                    target = edge.get("to")
                    if not isinstance(source, str) or source not in node_ids:
                        issues.append(f"provenance.graph.edges[{index}].from references unknown node")
                    if not isinstance(target, str) or target not in node_ids:
                        issues.append(f"provenance.graph.edges[{index}].to references unknown node")
                    if edge.get("relation") not in EDGE_RELATIONS:
                        issues.append(f"provenance.graph.edges[{index}].relation invalid: {edge.get('relation')!r}")
    return issues


def _validate_rights(value: Any) -> list[str]:
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
        if source.get("license_status") not in {"compatible", "incompatible", "unknown", "not-applicable"}:
            issues.append(f"rights.sources[{index}].license_status invalid: {source.get('license_status')!r}")
        confidence = source.get("confidence")
        if confidence is not None and confidence not in {
            "observed-declaration",
            "analysis",
            "heuristic",
            "asserted",
            "unknown",
        }:
            issues.append(f"rights.sources[{index}].confidence invalid: {confidence!r}")
        issues.extend(_validate_evidence_refs(source.get("evidence"), f"rights.sources[{index}].evidence"))
    return issues


def _validate_review(value: Any) -> list[str]:
    issues: list[str] = []
    if not _require_object(value, "review", issues):
        return issues
    if value.get("technical_validation") not in REVIEW_TECHNICAL:
        issues.append(f"review.technical_validation invalid: {value.get('technical_validation')!r}")
    if value.get("provenance_validation") not in REVIEW_PROVENANCE:
        issues.append(f"review.provenance_validation invalid: {value.get('provenance_validation')!r}")
    if value.get("human_acceptance") not in REVIEW_HUMAN:
        issues.append(f"review.human_acceptance invalid: {value.get('human_acceptance')!r}")
    reviewed_at = value.get("reviewed_at")
    if reviewed_at is not None and not (isinstance(reviewed_at, str) and _TIMESTAMP_RE.match(reviewed_at)):
        issues.append("review.reviewed_at must be an ISO-8601 timestamp")
    refs = value.get("commons_refs")
    if refs is not None:
        if not isinstance(refs, list):
            issues.append("review.commons_refs must be an array")
        else:
            for index, ref in enumerate(refs):
                issues.extend(_validate_producer_reference(ref, f"review.commons_refs[{index}]"))
    return issues


def _validate_attestations(value: Any) -> list[str]:
    issues: list[str] = []
    if value is None:
        return issues
    if not isinstance(value, list):
        issues.append("attestations must be an array")
        return issues
    for index, attestation in enumerate(value):
        if not isinstance(attestation, Mapping):
            issues.append(f"attestations[{index}] must be an object")
            continue
        if attestation.get("assertion_type") not in ATTESTATION_TYPES:
            issues.append(f"attestations[{index}].assertion_type invalid: {attestation.get('assertion_type')!r}")
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
    if not (isinstance(digest, str) and digest.startswith("sha256:") and _SHA256_RE.match(digest[7:])):
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


__all__ = ["SCHEMA_VERSION", "validate_evidence_structure", "validate_manifest_structure"]
