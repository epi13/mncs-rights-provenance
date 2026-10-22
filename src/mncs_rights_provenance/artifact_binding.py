"""Build bounded rights/provenance references for an existing artifact record.

This module does not own artifact identities, source snapshots, or build
events. Callers pass those references from their authoritative producer
records; the binding keeps them together without inferring legal conclusions.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .manifest_reference_consistency import (
    compatibility_review_required,
    repeated_reference_metadata_conflict,
)

SCHEMA_VERSION = "mncs.rights-provenance.native-artifact-binding/0.1.0"
DIAGNOSTIC_SCHEMA_VERSION = "mncs.rights-provenance.artifact-binding-diagnostic/0.2.0"
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


def validate_native_artifact_binding(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize one v0.1 native artifact binding.

    This checks the bounded producer contract without inferring missing source
    facts or making a compatibility or legal conclusion.
    """
    if not isinstance(value, Mapping):
        raise TypeError("artifact binding must be an object")
    required = {"schema_version", "artifact", "rights", "lineage", "legal_conclusion"}
    if set(value) != required or value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("artifact binding does not match native-artifact-binding/0.1.0")
    if value.get("legal_conclusion") != "NOT_MADE":
        raise ValueError("artifact binding legal_conclusion must be NOT_MADE")

    artifact = value.get("artifact")
    artifact_fields = {"producer", "producer_contract", "identity", "content_digest"}
    if not isinstance(artifact, Mapping) or set(artifact) != artifact_fields:
        raise ValueError("artifact does not match the producer identity contract")
    clean_artifact = {
        "producer": _text(artifact["producer"], "artifact.producer", 160),
        "producer_contract": _text(
            artifact["producer_contract"], "artifact.producer_contract", 160
        ),
        "identity": _text(artifact["identity"], "artifact.identity", 512),
        "content_digest": _digest(artifact["content_digest"], "artifact.content_digest"),
    }

    rights = value.get("rights")
    rights_fields = {"state", "context_identity", "contributing_manifests", "compatibility"}
    if not isinstance(rights, Mapping) or set(rights) != rights_fields:
        raise ValueError("rights does not match the native artifact binding contract")
    if rights.get("compatibility") != "unknown":
        raise ValueError("native artifact binding cannot assert compatibility")
    manifests = rights.get("contributing_manifests")
    if not isinstance(manifests, Sequence) or isinstance(manifests, (str, bytes)):
        raise TypeError("rights.contributing_manifests must be a list")
    if len(manifests) > 64:
        raise ValueError("rights.contributing_manifests exceeds the 64-input bound")
    clean_manifests = [
        _contributing_manifest(item, index) for index, item in enumerate(manifests)
    ]
    input_rights = [item["rights_state"] for item in clean_manifests]
    expected_rights_state = (
        "unknown" if not input_rights or "unknown" in input_rights
        else "review" if "unresolved" in input_rights
        else "declared"
    )
    if rights.get("state") != expected_rights_state:
        raise ValueError("rights.state conflicts with contributing manifest evidence")
    context_identity = _digest(rights.get("context_identity"), "rights.context_identity")

    lineage = value.get("lineage")
    lineage_fields = {
        "state", "source_snapshot_identity", "transformation", "relationships"
    }
    if not isinstance(lineage, Mapping) or set(lineage) != lineage_fields:
        raise ValueError("lineage does not match the native artifact binding contract")
    lineage_state = lineage.get("state")
    if not isinstance(lineage_state, str) or lineage_state not in {"complete", "partial", "unknown"}:
        raise ValueError("lineage.state is unsupported")
    source_identity = _optional_text(
        lineage.get("source_snapshot_identity"), "lineage.source_snapshot_identity", 512
    )
    transformation_value = lineage.get("transformation")
    if not isinstance(transformation_value, Mapping):
        raise TypeError("lineage.transformation must be an object")
    transformation_fields = {
        "kind", "toolchain_identity", "event_ref", "evidence_state", "evidence"
    }
    if set(transformation_value) != transformation_fields:
        raise ValueError("lineage.transformation does not match the producer event contract")
    transform_kind = transformation_value.get("kind")
    transform_state = transformation_value.get("evidence_state")
    if not isinstance(transform_kind, str) or transform_kind not in _TRANSFORMATIONS:
        raise ValueError("lineage.transformation.kind is unsupported")
    if not isinstance(transform_state, str) or transform_state not in {
        "directly-observed", "declared", "inferred", "unavailable"
    }:
        raise ValueError("lineage.transformation.evidence_state is unsupported")
    clean_transformation = {
        "kind": transform_kind,
        "toolchain_identity": _optional_text(
            transformation_value.get("toolchain_identity"),
            "lineage.transformation.toolchain_identity", 512,
        ),
        "event_ref": _optional_text(
            transformation_value.get("event_ref"), "lineage.transformation.event_ref", 1024
        ),
        "evidence_state": transform_state,
        "evidence": _evidence_list(
            transformation_value.get("evidence"), "lineage.transformation.evidence",
            required=transform_state != "unavailable",
        ),
    }
    relationships = lineage.get("relationships")
    if not isinstance(relationships, Sequence) or isinstance(relationships, (str, bytes)):
        raise TypeError("lineage.relationships must be a list")
    if len(relationships) > 128:
        raise ValueError("lineage.relationships exceeds the 128-edge bound")
    clean_relationships = [
        _relationship(item, index) for index, item in enumerate(relationships)
    ]
    expected_lineage_state = (
        "partial"
        if source_identity or clean_relationships or clean_transformation["evidence"]
        else "unknown"
    )
    if lineage_state != expected_lineage_state and lineage_state != "complete":
        raise ValueError("lineage.state conflicts with available binding evidence")

    return {
        "schema_version": SCHEMA_VERSION,
        "artifact": clean_artifact,
        "rights": {
            "state": expected_rights_state,
            "context_identity": context_identity,
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


def diagnose_native_artifact_binding(binding: Mapping[str, Any]) -> dict[str, Any]:
    """Explain unresolved rights or lineage in one native artifact binding.

    This bounded report diagnoses declared record state only. It does not
    fetch referenced manifests, infer license compatibility, or make a legal
    conclusion. A no-findings report means this check found no listed issue;
    it is not a compliance result.
    """
    if not isinstance(binding, Mapping):
        raise TypeError("binding must be an object")
    if set(binding) != {"schema_version", "artifact", "rights", "lineage", "legal_conclusion"}:
        raise ValueError("binding fields do not match the native artifact binding contract")
    if binding.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"binding.schema_version must be {SCHEMA_VERSION}")
    if binding.get("legal_conclusion") != "NOT_MADE":
        raise ValueError("binding.legal_conclusion must be NOT_MADE")

    artifact = binding.get("artifact")
    rights = binding.get("rights")
    lineage = binding.get("lineage")
    if not isinstance(artifact, Mapping) or not isinstance(rights, Mapping):
        raise TypeError("binding must contain artifact and rights objects")
    if not isinstance(lineage, Mapping):
        raise TypeError("binding must contain a lineage object")
    if set(artifact) != {"producer", "producer_contract", "identity", "content_digest"}:
        raise ValueError("binding.artifact fields do not match the producer identity contract")
    _text(artifact.get("producer"), "artifact.producer", 160)
    _text(artifact.get("producer_contract"), "artifact.producer_contract", 160)
    artifact_identity = _text(artifact.get("identity"), "artifact.identity", 512)
    _digest(artifact.get("content_digest"), "artifact.content_digest")
    if set(rights) - {"state", "context_identity", "contributing_manifests", "compatibility"}:
        raise ValueError("binding.rights contains unsupported fields")
    rights_state = rights.get("state")
    if not isinstance(rights_state, str) or rights_state not in {"declared", "review", "unknown"}:
        raise ValueError("binding.rights.state is unsupported")
    if "context_identity" in rights:
        _digest(rights.get("context_identity"), "rights.context_identity")
    manifests = rights.get("contributing_manifests")
    if not isinstance(manifests, Sequence) or isinstance(manifests, (str, bytes)):
        raise TypeError("binding.rights.contributing_manifests must be a list")
    if len(manifests) > 64 or any(not isinstance(item, Mapping) for item in manifests):
        raise ValueError("binding rights manifests exceed the supported shape")
    if rights.get("compatibility") != "unknown":
        raise ValueError("binding.rights.compatibility must remain unknown")
    clean_manifests = [
        _contributing_manifest(item, index) for index, item in enumerate(manifests)
    ]
    manifest_states = [item["rights_state"] for item in clean_manifests]
    manifest_fields = (
        "manifest_digest",
        "manifest_identity",
        "evidence_state",
        "rights_state",
        "license_expression_ref",
        "obligations_ref",
    )
    by_reference: dict[str, tuple[int, dict[str, Any]]] = {}
    reference_conflicts: set[str] = set()
    first_reference_conflict: tuple[int, int, list[str]] | None = None
    for index, manifest in enumerate(clean_manifests):
        prior = by_reference.get(manifest["reference"])
        if prior is None:
            by_reference[manifest["reference"]] = (index, manifest)
            continue
        prior_index, prior_manifest = prior
        conflicting_fields = [
            field for field in manifest_fields
            if prior_manifest[field] != manifest[field]
        ]
        result = repeated_reference_metadata_conflict(
            1,
            *(int(prior_manifest[field] == manifest[field]) for field in manifest_fields),
        )
        if result == 2:
            raise AssertionError("validated manifest metadata produced invalid comparison flags")
        if result == 1:
            reference_conflicts.add(manifest["reference"])
            if first_reference_conflict is None:
                first_reference_conflict = (prior_index, index, conflicting_fields)

    distinct_declarations = {
        (
            manifest["reference"],
            manifest["manifest_digest"],
            manifest["manifest_identity"],
            manifest["evidence_state"],
            manifest["rights_state"],
            manifest["license_expression_ref"],
            manifest["obligations_ref"],
        )
        for manifest in clean_manifests
    }

    if set(lineage) != {"state", "source_snapshot_identity", "transformation", "relationships"}:
        raise ValueError("binding.lineage fields do not match the native artifact binding contract")
    lineage_state = lineage.get("state")
    if not isinstance(lineage_state, str) or lineage_state not in {"complete", "partial", "unknown"}:
        raise ValueError("binding.lineage.state is unsupported")
    relationships = lineage.get("relationships")
    transformation = lineage.get("transformation")
    if (
        not isinstance(relationships, Sequence)
        or isinstance(relationships, (str, bytes))
        or len(relationships) > 128
        or any(not isinstance(item, Mapping) for item in relationships)
    ):
        raise ValueError("binding.lineage.relationships must be a bounded list of objects")
    if not isinstance(transformation, Mapping):
        raise TypeError("binding.lineage.transformation must be an object")
    transform_required = {
        "kind", "toolchain_identity", "event_ref", "evidence_state", "evidence",
    }
    if set(transformation) != transform_required:
        raise ValueError("binding transformation fields do not match the producer event contract")
    if not isinstance(transformation.get("kind"), str) or transformation["kind"] not in _TRANSFORMATIONS:
        raise ValueError("binding.lineage.transformation.kind is unsupported")
    _optional_text(transformation.get("toolchain_identity"), "transformation.toolchain_identity", 512)
    _optional_text(transformation.get("event_ref"), "transformation.event_ref", 1024)
    transformation_evidence = transformation.get("evidence")
    transformation_state = transformation.get("evidence_state")
    if not isinstance(transformation_state, str) or transformation_state not in {
        "directly-observed", "declared", "inferred", "unavailable",
    }:
        raise ValueError("binding.lineage.transformation.evidence_state is unsupported")
    clean_transformation_evidence = _evidence_list(
        transformation_evidence,
        "binding.lineage.transformation.evidence",
        required=transformation_state != "unavailable",
    )
    clean_relationships = [
        _relationship(item, index) for index, item in enumerate(relationships)
    ]
    relationship_states = [item["evidence_state"] for item in clean_relationships]
    source_snapshot_identity = _optional_text(
        lineage.get("source_snapshot_identity"), "lineage.source_snapshot_identity", 512
    )

    diagnostics: list[dict[str, str]] = []
    rights_state_consistent = (
        (rights_state == "declared" and bool(manifests) and all(
            state == "declared" for state in manifest_states
        ))
        or (rights_state == "review" and "unresolved" in manifest_states and "unknown" not in manifest_states)
        or (rights_state == "unknown" and (not manifests or "unknown" in manifest_states))
    )
    if not rights_state_consistent:
        diagnostics.append({
            "code": "artifact-rights-state-conflict",
            "severity": "review",
            "summary": "Aggregate rights state conflicts with the contributing manifest states.",
            "evidence_ref": "#/rights",
            "remedy": "reconcile-aggregate-rights-state-from-contributing-manifests",
        })
    if not manifests:
        diagnostics.append({
            "code": "artifact-rights-manifests-missing",
            "severity": "review",
            "summary": "No contributing Rights manifests were supplied.",
            "evidence_ref": "#/rights/contributing_manifests",
            "remedy": "attach-contributing-rights-manifests",
        })
    if "unknown" in manifest_states:
        diagnostics.append({
            "code": "artifact-rights-unknown",
            "severity": "review",
            "summary": "At least one contributing rights declaration remains unknown.",
            "evidence_ref": "#/rights/contributing_manifests",
            "remedy": "investigate-unknown-rights-declarations",
        })
    if "unresolved" in manifest_states:
        diagnostics.append({
            "code": "artifact-rights-unresolved",
            "severity": "review",
            "summary": "At least one contributing rights declaration remains unresolved.",
            "evidence_ref": "#/rights/contributing_manifests",
            "remedy": "resolve-rights-evidence-or-preserve-unresolved-state",
        })
    if reference_conflicts:
        if first_reference_conflict is None:
            raise AssertionError("manifest reference conflict has no evidence pair")
        first_index, second_index, conflicting_fields = first_reference_conflict
        diagnostics.append({
            "code": "artifact-rights-manifest-reference-inconsistent",
            "severity": "review",
            "summary": (
                f"{len(reference_conflicts)} repeated manifest reference(s) carry inconsistent "
                "metadata; the first conflicting pair differs in "
                f"{', '.join(conflicting_fields)}."
            ),
            "evidence_ref": "#/rights/contributing_manifests",
            "evidence_refs": [
                f"#/rights/contributing_manifests/{first_index}",
                f"#/rights/contributing_manifests/{second_index}",
            ],
            "conflicting_fields": conflicting_fields,
            "conflict_count": len(reference_conflicts),
            "remedy": "reconcile-manifest-reference-evidence",
        })
    if compatibility_review_required(len(distinct_declarations)) == 1:
        diagnostics.append({
            "code": "artifact-rights-compatibility-unknown",
            "severity": "review",
            "summary": (
                "Multiple rights manifests are present, but compatibility has not been established."
            ),
            "evidence_ref": "#/rights/compatibility",
            "remedy": "evaluate-compatibility-from-authoritative-license-terms",
        })

    source_snapshot_identity = lineage.get("source_snapshot_identity")
    has_lineage_evidence = (
        bool(clean_transformation_evidence) and transformation_state != "unavailable"
    ) or any(state != "unavailable" for state in relationship_states)
    if lineage_state == "complete":
        diagnostics.append({
            "code": "artifact-lineage-completeness-unsubstantiated",
            "severity": "review",
            "summary": "This binding contract contains no authoritative lineage-completeness attestation.",
            "evidence_ref": "#/lineage/state",
            "remedy": "attach-authoritative-completeness-attestation-or-mark-partial",
        })
    elif lineage_state == "unknown" and (
        source_snapshot_identity or clean_relationships or has_lineage_evidence
    ):
        diagnostics.append({
            "code": "artifact-lineage-state-conflict",
            "severity": "review",
            "summary": "Lineage is marked unknown even though source or transformation evidence is present.",
            "evidence_ref": "#/lineage",
            "remedy": "recompute-lineage-state-from-recorded-evidence",
        })
    elif lineage_state == "unknown":
        diagnostics.append({
            "code": "artifact-lineage-missing",
            "severity": "review",
            "summary": "No source snapshot, transformation evidence, or lineage relationship is available.",
            "evidence_ref": "#/lineage",
            "remedy": "retrieve-or-recover-producer-lineage-records",
        })
    elif lineage_state == "partial" and not (
        source_snapshot_identity or clean_relationships or clean_transformation_evidence
    ):
        diagnostics.append({
            "code": "artifact-lineage-state-conflict",
            "severity": "review",
            "summary": "Lineage is marked partial but contains no source, transformation, or relationship evidence.",
            "evidence_ref": "#/lineage",
            "remedy": "reconcile-lineage-state-or-restore-producer-evidence",
        })
    else:
        if transformation_state == "unavailable" or "unavailable" in relationship_states:
            diagnostics.append({
                "code": "artifact-lineage-evidence-unavailable",
                "severity": "review",
                "summary": "Some producer lineage evidence is explicitly unavailable.",
                "evidence_ref": (
                    "#/lineage/relationships"
                    if "unavailable" in relationship_states
                    else "#/lineage/transformation/evidence"
                ),
                "remedy": "reconcile-producer-records-or-record-evidence-unavailable",
            })

    return {
        "schema_version": DIAGNOSTIC_SCHEMA_VERSION,
        "status": "review" if diagnostics else "no-findings",
        "artifact_identity": artifact_identity,
        "diagnostics": diagnostics[:12],
        "legal_conclusion": "NOT_MADE",
    }


__all__ = [
    "DIAGNOSTIC_SCHEMA_VERSION",
    "SCHEMA_VERSION",
    "build_native_artifact_binding",
    "diagnose_native_artifact_binding",
    "validate_native_artifact_binding",
]
