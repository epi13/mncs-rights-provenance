"""Adapt Forge's versioned provider build receipt into the Rights binding.

Forge remains authoritative for its build receipt. This adapter validates its
self-identity and projects only the fields present in receipt version 1. It
does not verify who produced the receipt, reread its inputs, or make a legal
conclusion; evidence from this unsigned receipt remains declared.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any, cast

from .artifact_binding import build_native_artifact_binding

BUILD_RECEIPT_SCHEMA = "mncs.provider-build-receipt/1"
BUILD_BINDING_REQUEST_SCHEMA = "mncs.rights-provenance.forge-build-binding-request/0.1.0"
_HEX_DIGEST_LENGTH = 64


def _text(value: Any, label: str, limit: int) -> str:
    if not isinstance(value, str) or not value or len(value) > limit:
        raise ValueError(f"{label} must be a non-empty string of at most {limit} characters")
    return value


def _hex_digest(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != _HEX_DIGEST_LENGTH
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError(f"{label} must be a lowercase 64-character SHA-256 digest")
    return value


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be an object")
    return value


def _core_identity(core: Mapping[str, Any]) -> str:
    try:
        encoded = json.dumps(
            core,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ValueError("Forge build receipt core must contain JSON-compatible values") from error
    return hashlib.sha256(encoded).hexdigest()


def _input_reference(kind: str, name: str, digest: str) -> str:
    reference = f"mncs-forge:{kind}/{name}@sha256:{digest}"
    if len(reference) > 512:
        raise ValueError("Forge input reference exceeds the 512-character lineage bound")
    return reference


def build_forge_provider_artifact_binding(
    build_receipt: Mapping[str, Any],
    contributing_manifests: Sequence[Mapping[str, Any]] = (),
    *,
    context_identity: str | None = None,
) -> dict[str, Any]:
    """Project one Forge provider build receipt into the native Rights binding.

    Source inputs and dependency roots are represented as declared
    ``depends-upon`` relationships. Receipt v1 has no source snapshot identity
    and does not retain the primary source binding in its top-level build
    record, so this adapter does not manufacture either fact. The compilation
    event and compiler artifact identity remain separately referenced.
    """
    receipt = _mapping(build_receipt, "build_receipt")
    if receipt.get("schema_version") != BUILD_RECEIPT_SCHEMA:
        raise ValueError(f"build_receipt.schema_version must be {BUILD_RECEIPT_SCHEMA}")
    receipt_identity = _hex_digest(receipt.get("identity"), "build_receipt.identity")
    core = _mapping(receipt.get("core"), "build_receipt.core")
    if _core_identity(core) != receipt_identity:
        raise ValueError("Forge build receipt identity does not match its core")

    artifact = _mapping(core.get("artifact"), "build_receipt.core.artifact")
    artifact_identity = _text(artifact.get("identity"), "artifact.identity", 512)
    artifact_digest = _hex_digest(artifact.get("sha256"), "artifact.sha256")
    _hex_digest(artifact.get("payload_sha256"), "artifact.payload_sha256")

    inputs = _mapping(core.get("inputs"), "build_receipt.core.inputs")
    compiler_digest = _hex_digest(
        inputs.get("compiler_artifact_sha256"),
        "build_receipt.core.inputs.compiler_artifact_sha256",
    )
    invocation_identity = _hex_digest(
        core.get("build_invocation_identity"),
        "build_receipt.core.build_invocation_identity",
    )
    source_inputs = _mapping(inputs.get("source_inputs"), "build_receipt.core.inputs.source_inputs")
    dependency_roots = inputs.get("dependency_roots")
    if not isinstance(dependency_roots, Sequence) or isinstance(dependency_roots, (str, bytes)):
        raise TypeError("build_receipt.core.inputs.dependency_roots must be a list")
    if len(source_inputs) > 64 or len(dependency_roots) > 64:
        raise ValueError("Forge build receipt exceeds the 64-item input bounds")

    artifact_reference = f"mncs-forge:artifact/{artifact_identity}"
    receipt_reference = f"mncs-forge:provider-build-receipt/{receipt_identity}"
    relationships: list[dict[str, Any]] = []
    for name, raw_digest in source_inputs.items():
        input_name = _text(name, "source input name", 430)
        input_digest = _hex_digest(raw_digest, f"source_inputs[{input_name!r}]")
        input_reference = _input_reference("provider-source-input", input_name, input_digest)
        relationships.append(
            {
                "from": artifact_reference,
                "to": input_reference,
                "relation": "depends-upon",
                "evidence_state": "declared",
                "evidence": [
                    {"reference": receipt_reference, "state": "declared"},
                    {
                        "reference": input_reference,
                        "sha256": input_digest,
                        "state": "declared",
                    },
                ],
            }
        )

    for index, raw_dependency in enumerate(dependency_roots):
        dependency = _mapping(raw_dependency, f"dependency_roots[{index}]")
        repository = _text(dependency.get("repository"), f"dependency_roots[{index}].repository", 160)
        path = _text(dependency.get("path"), f"dependency_roots[{index}].path", 384)
        content_identity = _hex_digest(
            dependency.get("content_identity"),
            f"dependency_roots[{index}].content_identity",
        )
        input_name = f"{repository}:{path}"
        input_reference = _input_reference("provider-dependency-root", input_name, content_identity)
        relationships.append(
            {
                "from": artifact_reference,
                "to": input_reference,
                "relation": "depends-upon",
                "evidence_state": "declared",
                "evidence": [
                    {"reference": receipt_reference, "state": "declared"},
                    {
                        "reference": input_reference,
                        "sha256": content_identity,
                        "state": "declared",
                    },
                ],
            }
        )

    binding = build_native_artifact_binding(
        {
            "producer": "mncs-forge",
            "producer_contract": BUILD_RECEIPT_SCHEMA,
            "identity": artifact_identity,
            "content_digest": f"sha256:{artifact_digest}",
        },
        contributing_manifests,
        {
            "kind": "compilation",
            "toolchain_identity": f"mncs-compiler-artifact:sha256:{compiler_digest}",
            "event_ref": receipt_reference,
            "evidence_state": "declared",
            "evidence": [
                {"reference": receipt_reference, "state": "declared"},
                {
                    "reference": f"mncs-forge:provider-build-invocation/{invocation_identity}",
                    "state": "declared",
                },
            ],
        },
        relationships,
        source_snapshot_identity=None,
        context_identity=context_identity,
    )
    return cast(dict[str, Any], binding)


__all__ = ["BUILD_RECEIPT_SCHEMA", "build_forge_provider_artifact_binding"]
