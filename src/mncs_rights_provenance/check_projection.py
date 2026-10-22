"""Project a native ``mncs-rp validate`` report into ``mncs.check-result/1``.

This module is the authoritative owner of the rights/provenance boundary
projection. ``mncs-actions`` carries the resulting check without
reinterpreting it; its ``rights_adapter.py`` mirrors this table and must
be kept in agreement (see ``tests/test_check_projection.py`` and
``docs/mncs-actions-integration.md``).

Native result (``outcome``) is never replaced: it is preserved verbatim
in the check summary/unresolved/references alongside severity, findings,
issues, and manifest identity. ``legal_conclusion`` remains ``NOT_MADE``
upstream; passing means project evidence requirements were satisfied,
never a legal warranty.

Mapping (explicit, reviewable)::

    pass                  -> PASS  (requires structural coherence + identity match)
    blocked / invalid     -> FAIL  (valid negative established)
    pass-with-findings /
    review-required /
    unknown               -> UNKNOWN (review outstanding; never PASS)
    unrecognized non-empty -> UNKNOWN + drift note (never PASS)

No claim (caller must emit nothing; the execution layer records
``NOT_ESTABLISHED``/``INVALID`` instead of fabricating a verdict)::

    - report missing/empty/non-string outcome (malformed report)
    - pass for a structurally invalid manifest (self-contradictory)
    - invalid for a structurally valid manifest (self-contradictory)

Binding failure (``manifest_identity_matches`` False) downgrades an
otherwise-passing claim to FAIL. Tampering is Fail, never a pass, never
silent.
"""

from __future__ import annotations

import json
from typing import Any

from .policy_diagnostics import (
    POLICY_DIAGNOSTIC_GATE_BY_CODE,
    POLICY_DIAGNOSTIC_SCHEMA_VERSION,
)

CHECK_RESULT_SCHEMA_VERSION = "mncs.check-result/1"
MAX_RIGHTS_DIAGNOSTIC_COUNT = 8
MAX_RIGHTS_DIAGNOSTIC_BYTES = 64 * 1024

PASS_OUTCOMES = frozenset({"pass"})
FAIL_OUTCOMES = frozenset({"blocked", "invalid"})
UNKNOWN_OUTCOMES = frozenset({"pass-with-findings", "review-required", "unknown"})
POLICY_DIAGNOSTIC_FIELDS = frozenset({
    "schema_version",
    "code",
    "gate",
    "severity",
    "message",
    "evidence_state",
    "source_declarations",
    "omitted_source_declarations",
    "conflicts",
    "omitted_conflicts",
    "remedy",
    "legal_conclusion",
})
_SOURCE_DECLARATION_FIELDS = frozenset({
    "source_kind",
    "source_reference",
    "source_reference_truncated",
    "declared_license_status",
    "evidence_state",
    "declared_license_expression",
    "declared_confidence",
    "text_truncated",
    "evidence_references",
    "omitted_evidence_reference_entries",
})
_CONFLICT_FIELDS = frozenset({
    "source_reference",
    "source_reference_truncated",
    "declaration_count",
    "declared_statuses",
    "declared_license_expressions",
    "omitted_license_expression_variants",
    "evidence_references",
    "omitted_evidence_reference_entries",
    "source_kinds",
    "omitted_source_kinds",
})
_EVIDENCE_REFERENCE_FIELDS = frozenset({
    "kind", "reference", "sha256", "sha256_truncated", "text_truncated",
})


def _short_text(value: Any, *, limit: int, allow_empty: bool = False) -> bool:
    return (
        isinstance(value, str)
        and len(value) <= limit
        and (allow_empty or bool(value))
    )


def _nonnegative_int(value: Any) -> bool:
    return type(value) is int and 0 <= value <= 2**63 - 1


def _valid_evidence_reference(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) - _EVIDENCE_REFERENCE_FIELDS:
        return False
    if not _short_text(value.get("kind"), limit=64):
        return False
    if not _short_text(value.get("reference"), limit=256):
        return False
    if "sha256" in value and not _short_text(value["sha256"], limit=72, allow_empty=True):
        return False
    return all(
        type(value[key]) is bool
        for key in ("sha256_truncated", "text_truncated")
        if key in value
    )


def _valid_evidence_references(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) <= 8
        and all(_valid_evidence_reference(item) for item in value)
    )


def _valid_source_declaration(value: Any) -> bool:
    required = {
        "source_kind", "source_reference", "source_reference_truncated",
        "declared_license_status", "evidence_state",
    }
    if (
        not isinstance(value, dict)
        or not required.issubset(value)
        or set(value) - _SOURCE_DECLARATION_FIELDS
        or not _short_text(value.get("source_kind"), limit=64)
        or not _short_text(value.get("source_reference"), limit=256)
        or type(value.get("source_reference_truncated")) is not bool
        or not _short_text(value.get("declared_license_status"), limit=64)
        or value.get("evidence_state") != "declared-unverified"
    ):
        return False
    for key, limit in (("declared_license_expression", 256), ("declared_confidence", 64)):
        if key in value and not _short_text(value[key], limit=limit, allow_empty=True):
            return False
    if "text_truncated" in value and type(value["text_truncated"]) is not bool:
        return False
    if "evidence_references" in value and not _valid_evidence_references(
        value["evidence_references"]
    ):
        return False
    return (
        "omitted_evidence_reference_entries" not in value
        or _nonnegative_int(value["omitted_evidence_reference_entries"])
    )


def _valid_conflict(value: Any) -> bool:
    if (
        not isinstance(value, dict)
        or set(value) != _CONFLICT_FIELDS
        or not _short_text(value.get("source_reference"), limit=256)
        or type(value.get("source_reference_truncated")) is not bool
        or type(value.get("declaration_count")) is not int
        or value["declaration_count"] < 1
        or not _nonnegative_int(value.get("omitted_license_expression_variants"))
        or not _nonnegative_int(value.get("omitted_evidence_reference_entries"))
        or not _nonnegative_int(value.get("omitted_source_kinds"))
    ):
        return False
    statuses = value.get("declared_statuses")
    expressions = value.get("declared_license_expressions")
    source_kinds = value.get("source_kinds")
    return (
        isinstance(statuses, list)
        and len(statuses) <= 3
        and all(
            isinstance(item, str)
            and item in {"compatible", "incompatible", "not-applicable"}
            for item in statuses
        )
        and isinstance(expressions, list)
        and len(expressions) <= 8
        and all(
            isinstance(item, dict)
            and set(item) == {"value", "text_truncated"}
            and _short_text(item.get("value"), limit=256, allow_empty=True)
            and type(item.get("text_truncated")) is bool
            for item in expressions
        )
        and _valid_evidence_references(value.get("evidence_references"))
        and isinstance(source_kinds, list)
        and len(source_kinds) <= 8
        and all(_short_text(item, limit=64) for item in source_kinds)
    )


def _valid_policy_diagnostic(diagnostic: dict[str, Any]) -> bool:
    code = diagnostic.get("code")
    if not isinstance(code, str):
        return False
    expected_gate = POLICY_DIAGNOSTIC_GATE_BY_CODE.get(code)
    return not (
        diagnostic.get("schema_version") != POLICY_DIAGNOSTIC_SCHEMA_VERSION
        or expected_gate is None
        or diagnostic.get("gate") != expected_gate
        or set(diagnostic) != POLICY_DIAGNOSTIC_FIELDS
        or not isinstance(diagnostic.get("severity"), str)
        or diagnostic["severity"] not in {"finding", "review"}
        or diagnostic.get("evidence_state") != "declared-unverified"
        or diagnostic.get("legal_conclusion") != "NOT_MADE"
        or not _short_text(diagnostic.get("message"), limit=512)
        or not _short_text(diagnostic.get("remedy"), limit=512)
        or not isinstance(diagnostic.get("source_declarations"), list)
        or len(diagnostic["source_declarations"]) > 16
        or not all(_valid_source_declaration(item) for item in diagnostic["source_declarations"])
        or not isinstance(diagnostic.get("conflicts"), list)
        or len(diagnostic["conflicts"]) > 16
        or not all(_valid_conflict(item) for item in diagnostic["conflicts"])
        or not _nonnegative_int(diagnostic.get("omitted_source_declarations"))
        or not _nonnegative_int(diagnostic.get("omitted_conflicts"))
    )


def classify_report(report: Any) -> tuple[str | None, list[str], str | None]:
    """Classify a native validate report.

    Returns ``(verdict, unresolved_notes, error)``. ``error`` non-None (and
    verdict None) means the report establishes no claim.
    """
    unresolved: list[str] = []
    if not isinstance(report, dict):
        return None, [], "rights report must be a JSON object"
    outcome = report.get("outcome")
    if not isinstance(outcome, str) or not outcome.strip():
        return None, [], "rights report has no outcome (malformed report)"
    normalized = outcome.strip().lower()
    structural_valid = report.get("structural_valid")
    identity_matches = report.get("manifest_identity_matches")
    if normalized == "pass" and structural_valid is False:
        return None, [], "rights report claims pass for a structurally invalid manifest"
    if normalized == "invalid" and structural_valid is True:
        return None, [], "rights report claims invalid for a structurally valid manifest"
    if normalized in PASS_OUTCOMES:
        verdict = "PASS"
    elif normalized in FAIL_OUTCOMES:
        verdict = "FAIL"
    else:
        verdict = "UNKNOWN"
        if normalized not in UNKNOWN_OUTCOMES:
            unresolved.append(
                f"rights outcome {outcome!r} unrecognized; treated as UNKNOWN (vocabulary drift)"
            )
    if identity_matches is False:
        if verdict == "PASS":
            verdict = "FAIL"
            unresolved.append("manifest identity mismatch: binding failure downgrades pass to FAIL")
        else:
            unresolved.append("manifest identity mismatch")
    return verdict, unresolved, None


def _project_policy_diagnostics(
    report: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Carry recognized Rights diagnostics through the extensible check result.

    The native verdict remains authoritative. These records add bounded
    explanation for downstream consumers; they never alter PASS/FAIL/UNKNOWN.
    """
    raw = report.get("diagnostics")
    if raw is None:
        return [], []
    if not isinstance(raw, list):
        return [], ["rights policy diagnostics were malformed and omitted"]

    notes: list[str] = []
    records = raw[:MAX_RIGHTS_DIAGNOSTIC_COUNT]
    if len(raw) > MAX_RIGHTS_DIAGNOSTIC_COUNT:
        notes.append(
            f"{len(raw) - MAX_RIGHTS_DIAGNOSTIC_COUNT} additional rights diagnostics omitted by the projection bound"
        )

    projected: list[dict[str, Any]] = []
    total_bytes = 0
    for diagnostic in records:
        if not isinstance(diagnostic, dict):
            notes.append("a non-object rights policy diagnostic was omitted")
            continue
        if not _valid_policy_diagnostic(diagnostic):
            notes.append("an unsupported or malformed rights policy diagnostic was omitted")
            continue
        try:
            encoded_size = len(
                json.dumps(
                    diagnostic, ensure_ascii=False, sort_keys=True,
                    separators=(",", ":"), allow_nan=False,
                ).encode("utf-8")
            )
        except (TypeError, ValueError):
            notes.append("a non-JSON rights policy diagnostic was omitted")
            continue
        if encoded_size > MAX_RIGHTS_DIAGNOSTIC_BYTES or (
            total_bytes + encoded_size > MAX_RIGHTS_DIAGNOSTIC_BYTES
        ):
            notes.append("rights policy diagnostics exceeded the projection size bound")
            break

        total_bytes += encoded_size
        projected.append(dict(diagnostic))
        code = diagnostic["code"]
        expected_gate = POLICY_DIAGNOSTIC_GATE_BY_CODE[code]
        omitted = (
            diagnostic["omitted_source_declarations"]
            + diagnostic["omitted_conflicts"]
        )
        summary = (
            f"rights diagnostic ({code}; {expected_gate}; {diagnostic['severity']}; "
            f"{diagnostic['evidence_state']}): {diagnostic['message']} "
            f"Remedy: {diagnostic['remedy']}"
        )
        if omitted:
            summary += f" {omitted} source entries or conflict groups omitted."
        notes.append(summary)

    return projected, notes


def project_report_to_check(
    report: dict[str, Any],
    *,
    check_id: str = "rights-provenance",
    provider: str = "mncs-rights-provenance",
    scope: str = "",
    claim: str = "",
    contract_revision: str = "",
    producer_revision: str = "",
    manifest_path: str = "",
    manifest_digest: str = "",
) -> tuple[dict[str, Any] | None, str | None]:
    """Build the shared boundary projection, preserving the native result.

    Returns ``(check, error)``. ``error`` non-None means no claim could be
    established (caller must emit nothing).
    """
    verdict, notes, error = classify_report(report)
    if error is not None or verdict is None:
        return None, error

    outcome = str(report.get("outcome", ""))
    severity = str(report.get("severity", ""))
    findings = report.get("findings", [])
    if not isinstance(findings, list):
        findings = [str(findings)]
    issues = report.get("issues", [])
    if not isinstance(issues, list):
        issues = [str(issues)]
    identity = str(report.get("manifest_identity_expected", ""))

    summary_parts = [
        f"rights outcome {outcome or '(missing)'} -> {verdict}",
        f"severity {severity or '(missing)'}",
    ]
    if manifest_path:
        summary_parts.append(f"manifest {manifest_path}")
    summary = "; ".join(summary_parts) + ". Native result preserved; legal_conclusion=NOT_MADE."

    unresolved: list[str] = list(notes)
    for finding in findings:
        unresolved.append(f"rights finding: {finding}")
    for issue in issues:
        unresolved.append(f"rights issue: {issue}")
    if verdict == "UNKNOWN" and not unresolved:
        unresolved.append(f"rights outcome {outcome!r} requires review under adapter semantics")

    rights_diagnostics, diagnostic_notes = _project_policy_diagnostics(report)
    unresolved.extend(diagnostic_notes)

    references: list[dict[str, Any]] = []
    if manifest_path or manifest_digest or identity:
        ref: dict[str, Any] = {
            "kind": "rights-manifest",
            "producer": "mncs-rights-provenance",
        }
        if contract_revision:
            ref["contract_revision"] = contract_revision
        if producer_revision:
            ref["producer_revision"] = producer_revision
        if manifest_path:
            ref["path"] = manifest_path
        digest = manifest_digest or identity
        if digest:
            ref["digest"] = digest
        references.append(ref)

    check: dict[str, Any] = {
        "schema_version": CHECK_RESULT_SCHEMA_VERSION,
        "id": check_id,
        "provider": provider,
        "verdict": verdict,
        "summary": summary,
    }
    if scope:
        check["scope"] = scope
    if claim:
        check["claim"] = claim
    if contract_revision:
        check["contract_revision"] = contract_revision
    if producer_revision:
        check["producer_revision"] = producer_revision
    if unresolved:
        check["unresolved"] = unresolved
    if references:
        check["references"] = references
    if rights_diagnostics:
        check["rights_diagnostics"] = rights_diagnostics
    return check, None


__all__ = [
    "CHECK_RESULT_SCHEMA_VERSION",
    "FAIL_OUTCOMES",
    "PASS_OUTCOMES",
    "UNKNOWN_OUTCOMES",
    "classify_report",
    "project_report_to_check",
]
