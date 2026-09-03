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

from typing import Any

CHECK_RESULT_SCHEMA_VERSION = "mncs.check-result/1"

PASS_OUTCOMES = frozenset({"pass"})
FAIL_OUTCOMES = frozenset({"blocked", "invalid"})
UNKNOWN_OUTCOMES = frozenset({"pass-with-findings", "review-required", "unknown"})


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
    return check, None


__all__ = [
    "CHECK_RESULT_SCHEMA_VERSION",
    "FAIL_OUTCOMES",
    "PASS_OUTCOMES",
    "UNKNOWN_OUTCOMES",
    "classify_report",
    "project_report_to_check",
]
