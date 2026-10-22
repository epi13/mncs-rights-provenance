"""Bounded, source-scoped redistribution guidance for a rights manifest.

This is a projection over each declared license expression. It deliberately
does not combine conditions into permission flags or infer compatibility.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

from .license_resolution import (
    license_action_guidance,
    license_action_ruleset_identity,
    license_resolver_identity,
)
from .manifest import compute_manifest_identity

SCHEMA_VERSION = "mncs.rights.manifest-action-guidance/1"
MAX_MANIFEST_ACTION_GUIDANCE_BYTES = 2 * 1024 * 1024
MAX_PAGE_SIZE = 8
MAX_INLINE_GUIDANCE_BYTES = 16 * 1024
MAX_SOURCE_REFERENCE_LENGTH = 512
MAX_EVIDENCE_REFERENCES = 2
MAX_UNRESOLVED_IDENTIFIERS = 32
MAX_UNRESOLVED_CONDITIONS = 16
MAX_DECISION_NOTES = 4

_ACTIONS = {"redistribute-source", "redistribute-binary"}
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_SOURCE_KINDS = {
    "repository", "file", "dataset", "model", "documentation", "conversation",
    "package", "other",
}
_LICENSE_STATUSES = {"compatible", "incompatible", "unknown", "not-applicable"}


def _bounded_text(value: Any, limit: int) -> tuple[str | None, bool]:
    if not isinstance(value, str):
        return None, False
    return value[:limit], len(value) > limit


def _action_summary(
    expression: Any,
    action: str,
    expression_ref: str | None,
) -> dict[str, Any]:
    usable = (
        isinstance(expression, str)
        and bool(expression.strip())
        and expression.strip() not in {"NOASSERTION", "NONE"}
    )
    if usable:
        report = license_action_guidance(expression, action)
        encoded = json.dumps(
            report, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        tree = report.get("expression_tree")
        tree_state = (
            "inline" if isinstance(tree, dict) and len(encoded) <= MAX_INLINE_GUIDANCE_BYTES
            else "deferred" if isinstance(tree, dict)
            else "unresolved"
        )
        if tree_state != "inline":
            tree = None
        identifiers = report.get("unresolved_identifiers", [])
        conditions = report.get("unresolved_conditions", [])
        notes = report.get("decision_notes", [])
        identifier_values = identifiers if isinstance(identifiers, list) else []
        condition_values = conditions if isinstance(conditions, list) else []
        note_values = notes if isinstance(notes, list) else []
        return {
            "status": report.get("status", "unresolved"),
            "tree_state": tree_state,
            "expression_tree": tree,
            "detail_ref": expression_ref if tree_state != "inline" else None,
            "detail_query_ref": "mncs-rp action-guidance" if tree_state != "inline" else None,
            "unresolved_identifiers": identifier_values[:MAX_UNRESOLVED_IDENTIFIERS],
            "unresolved_identifier_count": len(identifier_values),
            "unresolved_identifiers_truncated": (
                len(identifier_values) > MAX_UNRESOLVED_IDENTIFIERS
            ),
            "unresolved_conditions": condition_values[:MAX_UNRESOLVED_CONDITIONS],
            "unresolved_condition_count": len(condition_values),
            "unresolved_conditions_truncated": (
                len(condition_values) > MAX_UNRESOLVED_CONDITIONS
            ),
            "decision_notes": note_values[:MAX_DECISION_NOTES],
            "decision_note_count": len(note_values),
            "decision_notes_truncated": len(note_values) > MAX_DECISION_NOTES,
        }

    missing_state = (
        "unavailable" if expression is None or not isinstance(expression, str)
        else "not-asserted" if expression.strip() in {"NOASSERTION", "NONE"}
        else "empty"
    )
    return {
        "status": "unresolved",
        "tree_state": "unavailable",
        "expression_tree": None,
        "detail_ref": expression_ref,
        "detail_query_ref": None,
        "unresolved_identifiers": [],
        "unresolved_identifier_count": 0,
        "unresolved_identifiers_truncated": False,
        "unresolved_conditions": [],
        "unresolved_condition_count": 0,
        "unresolved_conditions_truncated": False,
        "decision_notes": [f"No usable license expression is available ({missing_state})."],
        "decision_note_count": 1,
        "decision_notes_truncated": False,
    }


def _source_projection(
    source: Any,
    index: int,
    manifest_ref: str,
    action: str,
) -> dict[str, Any]:
    if not isinstance(source, Mapping):
        return {
            "source_index": index,
            "record_state": "malformed",
            "source_kind": None,
            "source_kind_state": "unavailable",
            "reference": None,
            "reference_truncated": False,
            "license_expression": None,
            "license_expression_truncated": False,
            "license_expression_ref": f"{manifest_ref}#/rights/sources/{index}/license",
            "license_status_declaration": None,
            "license_status_state": "unavailable",
            "confidence_declaration": None,
            "evidence_state": "unresolved",
            "evidence_refs": [],
            "guidance": _action_summary(None, action, None),
        }

    raw_kind = source.get("kind")
    kind_recognized = isinstance(raw_kind, str) and raw_kind in _SOURCE_KINDS
    reference, reference_truncated = _bounded_text(
        source.get("reference"), MAX_SOURCE_REFERENCE_LENGTH
    )
    expression = source.get("license")
    expression_text, expression_truncated = _bounded_text(expression, 4096)
    expression_ref = f"{manifest_ref}#/rights/sources/{index}/license"

    raw_status = source.get("license_status")
    status_recognized = isinstance(raw_status, str) and raw_status in _LICENSE_STATUSES
    if "license_status" not in source:
        status_state = "unavailable"
    elif status_recognized:
        status_state = "declared-unverified"
    else:
        status_state = "unrecognized"

    confidence, _ = _bounded_text(source.get("confidence"), 128)
    evidence: list[dict[str, str]] = []
    raw_evidence = source.get("evidence")
    if isinstance(raw_evidence, list):
        for item in raw_evidence[:MAX_EVIDENCE_REFERENCES]:
            if not isinstance(item, Mapping):
                continue
            ref, _ = _bounded_text(item.get("reference"), MAX_SOURCE_REFERENCE_LENGTH)
            kind, _ = _bounded_text(item.get("kind"), 128)
            if ref is None:
                continue
            entry: dict[str, str] = {"reference": ref}
            if kind is not None:
                entry["kind"] = kind
            sha256, _ = _bounded_text(item.get("sha256"), 128)
            if sha256 is not None:
                entry["sha256"] = sha256
            evidence.append(entry)

    return {
        "source_index": index,
        "record_state": "usable",
        "source_kind": raw_kind if kind_recognized else "other",
        "source_kind_state": "recognized" if kind_recognized else "unrecognized",
        "reference": reference,
        "reference_truncated": reference_truncated,
        "license_expression": expression_text,
        "license_expression_truncated": expression_truncated,
        "license_expression_ref": expression_ref,
        "license_status_declaration": raw_status if status_recognized else None,
        "license_status_state": status_state,
        "confidence_declaration": confidence,
        "evidence_state": "declared-unverified",
        "evidence_refs": evidence,
        "guidance": _action_summary(expression, action, expression_ref),
    }


def manifest_action_guidance(
    manifest: Mapping[str, Any],
    action: str,
    *,
    manifest_ref: str = "RIGHTS.json",
    manifest_content_sha256: str | None = None,
    offset: int = 0,
    limit: int = 4,
) -> dict[str, Any]:
    """Return bounded action guidance without combining source obligations.

    The status summarizes only the indexed term coverage of the displayed
    expressions. A page is not evidence that the manifest lists every artifact
    input, that any declaration is accurate, or that the licenses are
    compatible.
    """
    if not isinstance(manifest, Mapping):
        raise TypeError("manifest must be a JSON object")
    if action not in _ACTIONS:
        raise ValueError("action must be redistribute-source or redistribute-binary")
    if not isinstance(manifest_ref, str) or not manifest_ref.strip() or len(manifest_ref) > 512:
        raise ValueError("manifest_ref must be bounded non-empty text")
    if "\x00" in manifest_ref:
        raise ValueError("manifest_ref must not contain a NUL character")
    if type(offset) is not int or not 0 <= offset <= 2**31 - 1:
        raise ValueError("offset must be a non-negative bounded integer")
    if type(limit) is not int or not 1 <= limit <= MAX_PAGE_SIZE:
        raise ValueError(f"limit must be an integer from 1 to {MAX_PAGE_SIZE}")
    if manifest_content_sha256 is not None and not _SHA256.fullmatch(manifest_content_sha256):
        raise ValueError("manifest_content_sha256 must be a sha256 digest")

    try:
        observed_identity = compute_manifest_identity(manifest)
    except (TypeError, ValueError):
        observed_identity = None
    declared_identity = manifest.get("manifest_identity")
    if not isinstance(declared_identity, str):
        declared_identity = None
    identity_matches = (
        declared_identity == observed_identity
        if declared_identity is not None and observed_identity is not None
        else None
    )

    rights = manifest.get("rights")
    rights = rights if isinstance(rights, Mapping) else {}
    sources_value = rights.get("sources")
    source_list_available = isinstance(sources_value, list)
    all_sources: list[Any] = sources_value if source_list_available else []
    source_count = len(all_sources)
    end = min(source_count, offset + limit)
    page = [
        _source_projection(source, index, manifest_ref, action)
        for index, source in enumerate(all_sources[offset:end], start=offset)
    ]
    next_offset = end if end < source_count else None

    output_expression = rights.get("distribution_license")
    output_ref = f"{manifest_ref}#/rights/distribution_license"
    output_expression_text, output_expression_truncated = _bounded_text(
        output_expression, 4096
    )
    output_guidance = _action_summary(output_expression, action, output_ref)
    page_statuses = [output_guidance["status"]]
    page_statuses.extend(item["guidance"]["status"] for item in page)
    has_usable_guidance = any(status in {"partial", "reference-summary"} for status in page_statuses)
    if source_list_available and next_offset is None and page_statuses and all(
        status == "reference-summary" for status in page_statuses
    ):
        status = "reference-summary"
    elif has_usable_guidance:
        status = "partial"
    else:
        status = "unresolved"

    digest_basis = "raw-file-bytes" if manifest_content_sha256 is not None else "canonical-json-fallback"
    if manifest_content_sha256 is None:
        try:
            manifest_content_sha256 = "sha256:" + hashlib.sha256(
                json.dumps(
                    manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False
                ).encode("utf-8")
            ).hexdigest()
        except (TypeError, ValueError):
            manifest_content_sha256 = None
    if not isinstance(manifest_content_sha256, str) or not _SHA256.fullmatch(manifest_content_sha256):
        manifest_content_sha256 = None
        digest_basis = "unavailable"

    diagnostics: list[str] = []
    if not source_list_available:
        diagnostics.append("source-list-unavailable")
    if next_offset is not None:
        diagnostics.append("source-page-truncated")
    if output_guidance["status"] != "reference-summary":
        diagnostics.append("distribution-license-terms-unresolved")
    if any(item["record_state"] != "usable" for item in page):
        diagnostics.append("source-record-malformed")
    if any(item["guidance"]["status"] != "reference-summary" for item in page):
        diagnostics.append("source-license-terms-unresolved")
    if identity_matches is False:
        diagnostics.append("manifest-identity-mismatch")
        if status == "reference-summary":
            status = "partial"

    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "status_scope": "indexed-license-condition-coverage-only",
        "action": action,
        "manifest": {
            "reference": manifest_ref,
            "content_sha256": manifest_content_sha256,
            "content_digest_basis": digest_basis,
            "identity_observed": observed_identity,
            "identity_declared": declared_identity,
            "identity_matches": identity_matches,
            "identity_evidence": "recomputed-from-observed-manifest-content",
            "identity_scope": "canonical-content-consistency-only",
        },
        "license_resolver": {
            "version": "mncs.rights.license-resolution/4",
            "identity": license_resolver_identity(),
        },
        "ruleset": license_action_ruleset_identity(),
        "distribution_license": {
            "license_expression": output_expression_text,
            "license_expression_truncated": output_expression_truncated,
            "license_expression_ref": output_ref,
            "evidence_state": "declared-unverified" if isinstance(output_expression, str) else "unavailable",
            "guidance": output_guidance,
        },
        "source_list_state": "declared" if source_list_available else "unavailable",
        "source_count": source_count,
        "source_offset": offset,
        "source_limit": limit,
        "source_guidance": page,
        "next_source_offset": next_offset,
        "declaration_coverage": "manifest-declarations-only",
        "compatibility": {
            "status": "unknown",
            "reason": "source-scoped conditions are preserved; cross-license compatibility is not inferred",
        },
        "not_assessed": [
            "accuracy of license declarations",
            "ownership or grant authority",
            "cross-license compatibility",
            "completeness of the artifact input set",
            "legal effect of indexed conditions",
        ],
        "diagnostic_codes": diagnostics,
        "legal_conclusion": "NOT_MADE",
    }
