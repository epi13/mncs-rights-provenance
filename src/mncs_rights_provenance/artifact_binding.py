"""Build bounded rights/provenance references for an existing artifact record.

This module does not own artifact identities, source snapshots, or build
events. Callers pass those references from their authoritative producer
records; the binding keeps them together without inferring legal conclusions.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA_VERSION = "mncs.rights-provenance.native-artifact-binding/0.1.0"
_RIGHTS_STATES = {"declared", "unresolved", "unknown"}
_EVIDENCE_STATES = {
    "directly-observed",
    "declared",
    "inferred",
    "verified-attestation",
    "unverified-attestation",
    "unavailable",
}
_RELATIONS = {
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
_TRANSFORMATIONS = {
    "source-write",
    "generation",
    "transformation",
    "compilation",
    "link",
    "packaging",
    "other",
}
_DIGEST_PREFIX = "sha256:"


def _text(value: Any, label: str, limit: int) -> str:
    if not isinstance(value, str) or not value or len(value) > limit:
        raise ValueError(f"{label} must be a non-empty string of at most {limit} characters")
    return value


def _optional_text(value: Any, label: str, limit: int) -> str | None:
    if value is None:
        return None
    return _text(value, label, limit)


def _digest(value: Any, label: str, *, nullable: bool = True) -> str | None:
    if value is None and nullable:
        return None
    if (
        not isinstance(value, str)
        or len(value) != 71
        or not value.startswith(_DIGEST_PREFIX)
        or any(char not in "0123456789abcdef" for char in value[len(_DIGEST_PREFIX):])
    ):
        raise ValueError(f"{label} must be a lowercase sha256 digest")
    return value


def _evidence(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be an object")
    if set(value) - {"reference", "sha256", "state", "verifier_ref"}:
        raise ValueError(f"{label} contains unsupported fields")
    state = value.get("state")
    if not isinstance(state, str) or state not in _EVIDENCE_STATES:
        raise ValueError(f"{label}.state is unsupported")
    result: dict[str, Any] = {
        "reference": _text(value.get("reference"), f"{label}.reference", 1024),
        "state": state,
    }
    if "sha256" in value:
        digest = value["sha256"]
        if digest is not None and (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(char not in "0123456789abcdefABCDEF" for char in digest)
        ):
            raise ValueError(f"{label}.sha256 must be a 64-character hexadecimal digest")
        result["sha256"] = digest
    if "verifier_ref" in value:
        result["verifier_ref"] = _text(value["verifier_ref"], f"{label}.verifier_ref", 512)
    if state == "verified-attestation" and "verifier_ref" not in result:
        raise ValueError(f"{label} needs verifier_ref for a verified attestation")
    return result


def _evidence_list(value: Any, label: str, *, required: bool) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) > 16:
        raise ValueError(f"{label} must be a list of at most 16 evidence references")
    result = [_evidence(item, f"{label}[{index}]") for index, item in enumerate(value)]
    if required and not result:
        raise ValueError(f"{label} needs evidence for its declared evidence state")
    return result


def _contributing_manifest(value: Any, index: int) -> dict[str, Any]:
    label = f"contributing_manifests[{index}]"
    required = {
        "reference",
        "manifest_digest",
        "manifest_identity",
        "evidence_state",
        "rights_state",
        "license_expression_ref",
        "obligations_ref",
    }
    if not isinstance(value, Mapping) or set(value) != required:
        raise ValueError(f"{label} does not match the supported manifest reference contract")
    evidence_state = value["evidence_state"]
    rights_state = value["rights_state"]
    if not isinstance(evidence_state, str) or evidence_state not in _EVIDENCE_STATES:
        raise ValueError(f"{label}.evidence_state is unsupported")
    if not isinstance(rights_state, str) or rights_state not in _RIGHTS_STATES:
        raise ValueError(f"{label}.rights_state is unsupported")
    identity = value["manifest_identity"]
    if identity is not None and (
        not isinstance(identity, str)
        or len(identity) != 64
        or any(char not in "0123456789abcdefABCDEF" for char in identity)
    ):
        raise ValueError(f"{label}.manifest_identity must be a 64-character hexadecimal identity")
    return {
        "reference": _text(value["reference"], f"{label}.reference", 1024),
        "manifest_digest": _digest(value["manifest_digest"], f"{label}.manifest_digest"),
        "manifest_identity": identity,
        "evidence_state": evidence_state,
        "rights_state": rights_state,
        "license_expression_ref": _optional_text(
            value["license_expression_ref"], f"{label}.license_expression_ref", 1024
        ),
        "obligations_ref": _optional_text(
            value["obligations_ref"], f"{label}.obligations_ref", 1024
        ),
    }


def _relationship(value: Any, index: int) -> dict[str, Any]:
    label = f"relationships[{index}]"
    required = {"from", "to", "relation", "evidence_state", "evidence"}
    if not isinstance(value, Mapping) or set(value) != required:
        raise ValueError(f"{label} does not match the supported relationship contract")
    state = value["evidence_state"]
    relation = value["relation"]
    if not isinstance(state, str) or state not in _EVIDENCE_STATES:
        raise ValueError(f"{label}.evidence_state is unsupported")
    if not isinstance(relation, str) or relation not in _RELATIONS:
        raise ValueError(f"{label}.relation is unsupported")
    evidence = _evidence_list(
        value["evidence"], f"{label}.evidence", required=state != "unavailable"
    )
    return {
        "from": _text(value["from"], f"{label}.from", 512),
        "to": _text(value["to"], f"{label}.to", 512),
        "relation": relation,
        "evidence_state": state,
        "evidence": evidence,
    }


def build_native_artifact_binding(
    artifact: Mapping[str, Any],
    contributing_manifests: Sequence[Mapping[str, Any]],
    transformation: Mapping[str, Any],
    relationships: Sequence[Mapping[str, Any]],
    *,
    source_snapshot_identity: str | None,
    context_identity: str | None = None,
) -> dict[str, Any]:
    """Bind rights references to producer identities without asserting compliance.

    The caller supplies producer-owned artifact and event facts. Rights state is
    only a compact summary of the supplied declarations: any unknown input
    keeps the aggregate unknown, unresolved input yields review, and the
    resolver never asserts cross-license compatibility. Lineage is emitted as
    ``partial`` when at least one source or transformation fact exists and as
    ``unknown`` otherwise; completeness requires a separately versioned,
    authoritative attestation contract.
    """
    if not isinstance(artifact, Mapping):
        raise TypeError("artifact must be an object")
    artifact_required = {"producer", "producer_contract", "identity", "content_digest"}
    if set(artifact) != artifact_required:
        raise ValueError("artifact does not match the supported producer identity contract")
    clean_artifact = {
        "producer": _text(artifact["producer"], "artifact.producer", 160),
        "producer_contract": _text(artifact["producer_contract"], "artifact.producer_contract", 160),
        "identity": _text(artifact["identity"], "artifact.identity", 512),
        "content_digest": _digest(artifact["content_digest"], "artifact.content_digest"),
    }

    if (
        not isinstance(contributing_manifests, Sequence)
        or isinstance(contributing_manifests, (str, bytes))
    ):
        raise TypeError("contributing_manifests must be a list")
    if len(contributing_manifests) > 64:
        raise ValueError("contributing_manifests exceeds the 64-input bound")
    clean_manifests = [
        _contributing_manifest(item, index)
        for index, item in enumerate(contributing_manifests)
    ]
    input_rights = [item["rights_state"] for item in clean_manifests]
    if not input_rights or "unknown" in input_rights:
        rights_state = "unknown"
    elif "unresolved" in input_rights:
        rights_state = "review"
    else:
        rights_state = "declared"

    if not isinstance(transformation, Mapping):
        raise TypeError("transformation must be an object")
    transform_required = {"kind", "toolchain_identity", "event_ref", "evidence_state", "evidence"}
    if set(transformation) != transform_required:
        raise ValueError("transformation does not match the supported producer event contract")
    transform_kind = transformation["kind"]
    transform_state = transformation["evidence_state"]
    if not isinstance(transform_kind, str) or transform_kind not in _TRANSFORMATIONS:
        raise ValueError("transformation.kind is unsupported")
    if transform_state not in {"directly-observed", "declared", "inferred", "unavailable"}:
        raise ValueError("transformation.evidence_state is unsupported")
    clean_transformation = {
        "kind": transform_kind,
        "toolchain_identity": _optional_text(
            transformation["toolchain_identity"], "transformation.toolchain_identity", 512
        ),
        "event_ref": _optional_text(transformation["event_ref"], "transformation.event_ref", 1024),
        "evidence_state": transform_state,
        "evidence": _evidence_list(
            transformation["evidence"],
            "transformation.evidence",
            required=transform_state != "unavailable",
        ),
    }

    if not isinstance(relationships, Sequence) or isinstance(relationships, (str, bytes)):
        raise TypeError("relationships must be a list")
    if len(relationships) > 128:
        raise ValueError("relationships exceeds the 128-edge bound")
    clean_relationships = [_relationship(item, index) for index, item in enumerate(relationships)]
    source_identity = _optional_text(source_snapshot_identity, "source_snapshot_identity", 512)
    lineage_state = (
        "partial"
        if source_identity or clean_relationships or clean_transformation["evidence"]
        else "unknown"
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "artifact": clean_artifact,
        "rights": {
            "state": rights_state,
            "context_identity": _digest(context_identity, "context_identity"),
            "contributing_manifests": clean_manifests,
            "compatibility": "unknown",
        },
        "lineage": {
            "state": lineage_state,
            "source_snapshot_identity": source_identity,
            "transformation": clean_transformation,
            "relationships": clean_relationships,
        },
        "legal_conclusion": "NOT_MADE",
    }


__all__ = ["SCHEMA_VERSION", "build_native_artifact_binding"]
