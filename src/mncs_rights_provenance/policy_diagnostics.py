"""Bounded, evidence-linked diagnostics for source-rights policy findings.

These diagnostics explain policy inputs; they do not change gate semantics or
make legal conclusions. Manifest declarations and their references remain
unverified unless a separate authorized verification boundary says otherwise.
"""

from __future__ import annotations

from collections.abc import Mapping
from heapq import nsmallest
from typing import Any

POLICY_DIAGNOSTIC_SCHEMA_VERSION = "mncs.rights.policy-diagnostic/1"
MAX_DIAGNOSTIC_SOURCES = 16
MAX_DIAGNOSTIC_EVIDENCE_REFS = 8
MAX_DIAGNOSTIC_VARIANTS = 8
MAX_TEXT_LENGTH = 256

_DETERMINATE_STATUSES = {"compatible", "incompatible", "not-applicable"}


def _bounded_text(value: Any, *, limit: int = MAX_TEXT_LENGTH) -> tuple[str | None, bool]:
    if not isinstance(value, str):
        return None, False
    return value[:limit], len(value) > limit


def _project_evidence_reference(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    kind, kind_truncated = _bounded_text(value.get("kind"), limit=64)
    reference, reference_truncated = _bounded_text(value.get("reference"))
    if not kind or not reference:
        return None
    result: dict[str, Any] = {"kind": kind, "reference": reference}
    digest = value.get("sha256")
    if isinstance(digest, str):
        result["sha256"] = digest[:72]
        if len(digest) > 72:
            result["sha256_truncated"] = True
    if kind_truncated or reference_truncated:
        result["text_truncated"] = True
    return result


def _project_source_declaration(source: Mapping[str, Any]) -> dict[str, Any] | None:
    source_kind, kind_truncated = _bounded_text(source.get("kind"), limit=64)
    reference, reference_truncated = _bounded_text(source.get("reference"))
    if not reference:
        return None
    status, status_truncated = _bounded_text(source.get("license_status"), limit=64)
    result: dict[str, Any] = {
        "source_kind": source_kind or "unknown",
        "source_reference": reference,
        "source_reference_truncated": reference_truncated,
        "declared_license_status": status or "unknown",
        "evidence_state": "declared-unverified",
    }
    license_expression, license_truncated = _bounded_text(source.get("license"))
    if license_expression is not None:
        result["declared_license_expression"] = license_expression
    confidence, confidence_truncated = _bounded_text(source.get("confidence"), limit=64)
    if confidence is not None:
        result["declared_confidence"] = confidence
    if kind_truncated or reference_truncated or status_truncated or license_truncated or confidence_truncated:
        result["text_truncated"] = True

    projected_refs: list[dict[str, Any]] = []
    seen_refs: set[tuple[str, str, str]] = set()
    omitted_refs = 0
    evidence = source.get("evidence")
    for item in evidence if isinstance(evidence, list) else ():
        projected = _project_evidence_reference(item)
        if projected is None:
            continue
        key = (
            str(projected.get("kind", "")),
            str(projected.get("reference", "")),
            str(projected.get("sha256", "")),
        )
        if key in seen_refs:
            continue
        if len(projected_refs) < MAX_DIAGNOSTIC_EVIDENCE_REFS:
            seen_refs.add(key)
            projected_refs.append(projected)
        else:
            omitted_refs += 1
    if projected_refs:
        result["evidence_references"] = projected_refs
    if omitted_refs:
        result["omitted_evidence_reference_entries"] = omitted_refs
    return result


def collect_source_license_evidence(
    rights: Mapping[str, Any],
) -> tuple[tuple[dict[str, Any], ...], int, tuple[dict[str, Any], ...], int, int]:
    """Collect bounded source declarations and contradictions from a manifest.

    Contradictions use the same rule as the policy input gate: multiple
    nonempty license expressions or multiple distinct determinate statuses
    for one source reference. ``unknown`` alone does not conflict.
    """
    grouped: dict[str, dict[str, Any]] = {}
    declarations: list[dict[str, Any]] = []
    source_count = 0

    for raw_source in rights.get("sources") or ():
        if not isinstance(raw_source, Mapping):
            continue
        source_count += 1
        declaration = _project_source_declaration(raw_source)
        if declaration is not None and len(declarations) < MAX_DIAGNOSTIC_SOURCES:
            declarations.append(declaration)

        reference = raw_source.get("reference")
        if not isinstance(reference, str) or not reference:
            continue
        group = grouped.setdefault(reference, {
            "source_reference": reference[:MAX_TEXT_LENGTH],
            "source_reference_truncated": len(reference) > MAX_TEXT_LENGTH,
            "source_kinds": set(),
            "statuses": set(),
            "licenses": set(),
            "evidence_references": [],
            "evidence_reference_keys": set(),
            "declaration_count": 0,
        })
        group["declaration_count"] += 1
        kind = raw_source.get("kind")
        if isinstance(kind, str) and kind:
            group["source_kinds"].add(kind)
        status = raw_source.get("license_status")
        if isinstance(status, str) and status in _DETERMINATE_STATUSES:
            group["statuses"].add(status)
        license_value = raw_source.get("license")
        if isinstance(license_value, str) and license_value:
            group["licenses"].add(license_value)
        evidence = raw_source.get("evidence")
        for item in evidence if isinstance(evidence, list) else ():
            projected = _project_evidence_reference(item)
            if projected is None:
                continue
            key = (
                str(projected.get("kind", "")),
                str(projected.get("reference", "")),
                str(projected.get("sha256", "")),
            )
            if key in group["evidence_reference_keys"]:
                continue
            if len(group["evidence_references"]) < MAX_DIAGNOSTIC_EVIDENCE_REFS:
                group["evidence_reference_keys"].add(key)
                group["evidence_references"].append(projected)
            else:
                group["omitted_evidence_reference_entries"] = (
                    group.get("omitted_evidence_reference_entries", 0) + 1
                )

    conflicts: list[dict[str, Any]] = []
    conflict_count = 0
    for reference, group in grouped.items():
        if len(group["licenses"]) <= 1 and len(group["statuses"]) <= 1:
            continue
        conflict_count += 1
        if len(conflicts) >= MAX_DIAGNOSTIC_SOURCES:
            continue
        source_kinds = nsmallest(MAX_DIAGNOSTIC_VARIANTS, group["source_kinds"])
        license_values = nsmallest(MAX_DIAGNOSTIC_VARIANTS, group["licenses"])
        conflict: dict[str, Any] = {
            "source_reference": group["source_reference"],
            "source_reference_truncated": group["source_reference_truncated"],
            "declaration_count": group["declaration_count"],
            "declared_statuses": sorted(group["statuses"]),
            "declared_license_expressions": [
                {
                    "value": value[:MAX_TEXT_LENGTH],
                    "text_truncated": len(value) > MAX_TEXT_LENGTH,
                }
                for value in license_values
            ],
            "omitted_license_expression_variants": max(
                0, len(group["licenses"]) - len(license_values)
            ),
            "evidence_references": list(group["evidence_references"]),
            "omitted_evidence_reference_entries": group.get(
                "omitted_evidence_reference_entries", 0
            ),
        }
        conflict["source_kinds"] = source_kinds
        conflict["omitted_source_kinds"] = max(
            0, len(group["source_kinds"]) - len(source_kinds)
        )
        conflicts.append(conflict)

    return (
        tuple(declarations),
        source_count,
        tuple(conflicts),
        conflict_count,
        max(0, conflict_count - len(conflicts)),
    )


def project_source_policy_diagnostics(
    *,
    source_declarations: tuple[dict[str, Any], ...],
    source_count: int,
    omitted_sources: int,
    source_conflicts: tuple[dict[str, Any], ...],
    conflict_count: int,
    omitted_conflicts: int,
    unknown_source_severity: str,
    contradiction_severity: str,
) -> list[dict[str, Any]]:
    """Project only active source-license gates into bounded diagnostics."""
    diagnostics: list[dict[str, Any]] = []
    if unknown_source_severity != "none" and source_count:
        diagnostics.append({
            "schema_version": POLICY_DIAGNOSTIC_SCHEMA_VERSION,
            "code": "source-license-status-unverified",
            "gate": "unknown_source_license",
            "severity": unknown_source_severity,
            "message": (
                "Source license status labels are declarations; the available "
                "manifest evidence does not verify compatibility."
            ),
            "evidence_state": "declared-unverified",
            "source_declarations": list(source_declarations),
            "omitted_source_declarations": omitted_sources,
            "conflicts": [],
            "omitted_conflicts": 0,
            "remedy": (
                "Inspect the referenced source and evidence. Keep its status "
                "unverified until an authorized assessment records supporting "
                "evidence, then re-evaluate the manifest."
            ),
            "legal_conclusion": "NOT_MADE",
        })
    if contradiction_severity != "none" and conflict_count:
        diagnostics.append({
            "schema_version": POLICY_DIAGNOSTIC_SCHEMA_VERSION,
            "code": "source-license-declarations-conflict",
            "gate": "no_contradictory_license_evidence",
            "severity": contradiction_severity,
            "message": (
                "Declarations for one or more source references disagree; "
                "the conflict does not establish legal incompatibility."
            ),
            "evidence_state": "declared-unverified",
            "source_declarations": [],
            "omitted_source_declarations": 0,
            "conflicts": list(source_conflicts),
            "omitted_conflicts": omitted_conflicts,
            "remedy": (
                "Compare the listed declarations and their references, correct "
                "or reconcile the metadata with evidence, and retain the "
                "conflict as unresolved until the record is consistent."
            ),
            "legal_conclusion": "NOT_MADE",
        })
    return diagnostics


__all__ = [
    "MAX_DIAGNOSTIC_EVIDENCE_REFS",
    "MAX_DIAGNOSTIC_SOURCES",
    "POLICY_DIAGNOSTIC_SCHEMA_VERSION",
    "collect_source_license_evidence",
    "project_source_policy_diagnostics",
]
