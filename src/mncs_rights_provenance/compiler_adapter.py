"""Project Compiler application-build results into Rights artifact bindings.

Compiler owns the application-build response and artifact identities. This
adapter consumes the versioned response without re-running compilation,
rehashing the serialized VM artifact, verifying its producer, or making a
legal conclusion. Response facts remain declared evidence.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from .artifact_binding import build_native_artifact_binding

APPLICATION_BUILD_SCHEMA = "mncs.compiler.application-build/11"
APPLICATION_BUILD_SCHEMAS = frozenset({
    "mncs.compiler.application-build/4",
    "mncs.compiler.application-build/7",
    APPLICATION_BUILD_SCHEMA,
})
COMPILER_BINDING_REQUEST_SCHEMA = "mncs.rights-provenance.compiler-build-binding-request/0.2.0"
LEGACY_COMPILER_BINDING_REQUEST_SCHEMA = "mncs.rights-provenance.compiler-build-binding-request/0.1.0"
_DIGEST_RE = re.compile(r"^sha256:([0-9a-f]{64})$")
_CLOSURE_RE = re.compile(r"^application-ssa-closure/1:([0-9a-f]{64})$")
_MAX_SOURCE_FILES = 65


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be an object")
    return value


def _text(value: Any, label: str, limit: int) -> str:
    if not isinstance(value, str) or not value or len(value) > limit:
        raise ValueError(f"{label} must be a non-empty string of at most {limit} characters")
    return value


def _digest(value: Any, label: str) -> tuple[str, str]:
    if not isinstance(value, str):
        raise TypeError(f"{label} must be a sha256-prefixed digest")
    match = _DIGEST_RE.fullmatch(value)
    if match is None:
        raise ValueError(f"{label} must be a lowercase sha256-prefixed digest")
    return value, match.group(1)


def _stage0_toolchain_identity(value: Any) -> str:
    try:
        encoded = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ValueError("Compiler Stage-0 toolchain identity must contain JSON values") from error
    digest = hashlib.sha256(encoded).hexdigest()
    return f"mncs-compiler:stage0-toolchain-description/sha256:{digest}"


def _source_file_references(
    source_snapshot: Mapping[str, Any], source_snapshot_identity: str
) -> list[tuple[str, list[dict[str, Any]]]]:
    files = source_snapshot.get("files")
    if not isinstance(files, Sequence) or isinstance(files, (str, bytes)):
        raise TypeError("application_build.source_snapshot.files must be a list")
    if not 1 <= len(files) <= _MAX_SOURCE_FILES:
        raise ValueError("Compiler source snapshot must contain between 1 and 65 files")

    result: list[tuple[str, list[dict[str, Any]]]] = []
    seen: set[tuple[str, str]] = set()
    for index, raw_file in enumerate(files):
        source_file = _mapping(raw_file, f"source_snapshot.files[{index}]")
        module = _text(source_file.get("module"), f"source_files[{index}].module", 128)
        source_id = _text(source_file.get("source_id"), f"source_files[{index}].source_id", 256)
        _, digest_hex = _digest(
            source_file.get("sha256"), f"source_files[{index}].sha256"
        )
        key = (module, source_id)
        if key in seen:
            raise ValueError("Compiler source snapshot contains a duplicate module/source identity")
        seen.add(key)

        source_ref = f"mncs-compiler:source-snapshot/{source_snapshot_identity}/file/{index}"
        source_identity_ref = f"mncs-compiler:source/{module}/{source_id}"
        evidence = [
            {"reference": source_ref, "sha256": digest_hex, "state": "declared"},
            {"reference": source_identity_ref, "state": "declared"},
        ]
        result.append((source_ref, evidence))
    return result


def build_compiler_application_artifact_binding(
    application_build: Mapping[str, Any],
    contributing_manifests: Sequence[Mapping[str, Any]] = (),
    *,
    context_identity: str | None = None,
    store_ref: str | None = None,
) -> dict[str, Any]:
    """Bind a verified Compiler application-build response to Rights data.

    The adapter retains compiler-declared source hashes, snapshot and graph
    identities, the application SSA closure reference, and toolchain identity.
    An optional canonical Environment Store reference is retained as directly
    observed evidence for the exact response record. Compiler response facts
    remain declared, and no response field is elevated to verified-attestation
    evidence.
    """
    response = _mapping(application_build, "application_build")
    response_schema = response.get("schema_version")
    if response_schema not in APPLICATION_BUILD_SCHEMAS:
        supported = ", ".join(sorted(APPLICATION_BUILD_SCHEMAS))
        raise ValueError(f"application_build.schema_version must be one of: {supported}")
    if response.get("status") != "verified":
        raise ValueError("only a Compiler response with status 'verified' can bind an artifact")

    source_snapshot = _mapping(response.get("source_snapshot"), "source_snapshot")
    source_snapshot_identity, source_snapshot_hex = _digest(
        source_snapshot.get("identity"), "source_snapshot.identity"
    )
    source_references = _source_file_references(source_snapshot, source_snapshot_identity)

    dependency_graph = _mapping(response.get("dependency_graph"), "dependency_graph")
    dependency_graph_identity, dependency_graph_hex = _digest(
        dependency_graph.get("identity"), "dependency_graph.identity"
    )

    artifact = _mapping(response.get("artifact"), "artifact")
    artifact_identity, artifact_hex = _digest(artifact.get("identity"), "artifact.identity")
    artifact_value = _mapping(artifact.get("value"), "artifact.value")
    if artifact_value.get("artifact_id") != artifact_identity:
        raise ValueError("Compiler artifact identity does not match artifact.value.artifact_id")
    artifact_source = _mapping(artifact_value.get("source"), "artifact.value.source")
    lowering_refs = artifact_source.get("lowering_refs")
    if not isinstance(lowering_refs, Sequence) or isinstance(lowering_refs, (str, bytes)):
        raise TypeError("artifact.value.source.lowering_refs must be a list")
    if len(lowering_refs) > 64:
        raise ValueError("Compiler artifact has more than 64 lowering references")
    closure_refs = [
        value for value in lowering_refs
        if isinstance(value, str) and _CLOSURE_RE.fullmatch(value)
    ]
    if len(closure_refs) != 1:
        raise ValueError("Compiler application artifact must retain one SSA closure reference")
    closure_ref = closure_refs[0]
    selected_ssa_identity = artifact_source.get("selected_ssa_identity")
    if selected_ssa_identity is not None:
        selected_ssa_identity = _text(
            selected_ssa_identity, "artifact.value.source.selected_ssa_identity", 512
        )

    producer = _mapping(response.get("producer"), "producer")
    probe = producer.get("probe")
    stage0_toolchain = producer.get("stage0_toolchain")
    probe_digest: str | None = None
    if isinstance(probe, Mapping):
        raw_probe_digest = probe.get("probe_executable_sha256")
        if raw_probe_digest is not None:
            _, probe_digest = _digest(raw_probe_digest, "producer.probe.probe_executable_sha256")

    toolchain_identity: str | None = None
    toolchain_evidence: list[dict[str, Any]] = []
    if probe_digest is not None:
        probe_ref = f"mncs-compiler:probe-executable/sha256:{probe_digest}"
        toolchain_identity = probe_ref
        toolchain_evidence.append(
            {"reference": probe_ref, "sha256": probe_digest, "state": "declared"}
        )
    if isinstance(stage0_toolchain, Mapping):
        stage0_ref = _stage0_toolchain_identity(stage0_toolchain)
        if toolchain_identity is None:
            toolchain_identity = stage0_ref
        stage0_hex = stage0_ref.rsplit(":", 1)[-1]
        toolchain_evidence.append(
            {"reference": stage0_ref, "sha256": stage0_hex, "state": "declared"}
        )

    build_ref = (
        f"mncs-compiler:application-build-result/{response_schema.rsplit('/', 1)[-1]}/"
        f"{source_snapshot_identity}/{dependency_graph_identity}/{artifact_identity}"
    )
    source_snapshot_ref = f"mncs-compiler:source-snapshot/{source_snapshot_identity}"
    dependency_graph_ref = f"mncs-compiler:dependency-graph/{dependency_graph_identity}"
    closure_ref_evidence = f"mncs-compiler:{closure_ref}"
    transformation_evidence: list[dict[str, Any]] = [
        {"reference": build_ref, "state": "declared"},
        {
            "reference": source_snapshot_ref,
            "sha256": source_snapshot_hex,
            "state": "declared",
        },
        {
            "reference": dependency_graph_ref,
            "sha256": dependency_graph_hex,
            "state": "declared",
        },
        {"reference": closure_ref_evidence, "state": "declared"},
        *toolchain_evidence,
    ]
    if store_ref is not None:
        store_ref = _text(store_ref, "store_ref", 1024)
        if any(ord(character) < 0x20 for character in store_ref):
            raise ValueError("store_ref must not contain control characters")
        transformation_evidence.append({
            "reference": store_ref,
            "state": "directly-observed",
        })
    if isinstance(selected_ssa_identity, str):
        transformation_evidence.append({
            "reference": f"mncs-compiler:selected-ssa/{selected_ssa_identity}",
            "state": "declared",
        })
    relationships: list[dict[str, Any]] = [
        {
            "from": source_ref,
            "to": f"mncs-compiler:artifact/{artifact_identity}",
            "relation": "compiled-from",
            "evidence_state": "declared",
            "evidence": [
                {"reference": build_ref, "state": "declared"},
                *source_evidence,
            ],
        }
        for source_ref, source_evidence in source_references
    ]
    relationships.append(
        {
            "from": build_ref,
            "to": f"mncs-compiler:artifact/{artifact_identity}",
            "relation": "transformed-by",
            "evidence_state": "declared",
            "evidence": transformation_evidence,
        }
    )

    binding = build_native_artifact_binding(
        {
            "producer": "mncs-compiler",
        "producer_contract": response_schema,
            "identity": artifact_identity,
            "content_digest": f"sha256:{artifact_hex}",
        },
        contributing_manifests,
        {
            "kind": "compilation",
            "toolchain_identity": toolchain_identity,
            "event_ref": build_ref,
            "evidence_state": "declared",
            "evidence": transformation_evidence,
        },
        relationships,
        source_snapshot_identity=source_snapshot_identity,
        context_identity=context_identity,
    )
    return binding


__all__ = [
    "APPLICATION_BUILD_SCHEMA",
    "APPLICATION_BUILD_SCHEMAS",
    "COMPILER_BINDING_REQUEST_SCHEMA",
    "LEGACY_COMPILER_BINDING_REQUEST_SCHEMA",
    "build_compiler_application_artifact_binding",
]
