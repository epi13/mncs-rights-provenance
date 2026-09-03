"""``mncs-rp`` command line interface.

Agent-first: every command emits a structured JSON document on stdout.
``--human`` adds an indented human-readable rendering where useful.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import __version__
from .canonical import canonical_bytes
from .evidence import evidence_record_from_dict, seal_evidence_record, verify_evidence_digest
from .graph import check_graph_integrity
from .lineage import (
    lineage_record_from_dict,
    verify_lineage_digest,
)
from .manifest import (
    BASE_SCHEMA_VERSION,
    SCHEMA_VERSION,
    compute_manifest_identity,
    load_manifest_file,
)
from .policy import evaluate_policy, profile_from_dict
from .policy_input import policy_input_from_manifest
from .promotion import promotion_inputs_from_dict, promotion_report
from .spdx import export_spdx
from .validation import (
    validate_lineage_structure,
    validate_manifest_structure,
)


def _emit(value: Any, *, human: bool = False) -> None:
    json.dump(value, sys.stdout, indent=2 if human else None, sort_keys=True)
    sys.stdout.write("\n")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        document = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _emit({"valid": False, "outcome": "invalid", "issues": [f"cannot read manifest: {exc}"]})
        return 2

    issues = validate_manifest_structure(document)
    structurally_valid = not issues

    graph_ok = True
    graph_issues: list[str] = []
    if structurally_valid:
        graph_ok, graph_issues = check_graph_integrity(document)
        if not graph_ok:
            issues = issues + graph_issues

    hash_mismatch = False
    artifact_hashes = ((document.get("artifact") or {}).get("hashes")) or []
    declared_identity = document.get("manifest_identity")
    identity_ok = True
    identity_expected = compute_manifest_identity(document) if isinstance(document, dict) else ""
    if (
        isinstance(declared_identity, str)
        and declared_identity
        and declared_identity != identity_expected
    ):
        identity_ok = False
        issues.append("manifest_identity does not match canonical content")

    if args.artifact_file:
        digest = hashlib.sha256(Path(args.artifact_file).read_bytes()).hexdigest()
        expected = {item.get("value") for item in artifact_hashes if isinstance(item, dict)}
        if digest not in expected:
            hash_mismatch = True
            issues.append(
                f"artifact file sha256 {digest} does not match any declared artifact hash"
            )

    profile_enforcements: dict[str, int] | None = None
    if args.profile:
        try:
            profile_document = json.loads(Path(args.profile).read_text(encoding="utf-8"))
            profile_enforcements = profile_from_dict(profile_document)
        except (OSError, ValueError) as exc:
            _emit(
                {
                    "valid": False,
                    "outcome": "invalid",
                    "issues": [f"cannot read policy profile: {exc}"],
                }
            )
            return 2

    policy_input = policy_input_from_manifest(
        document,
        hash_mismatch=hash_mismatch,
        broken_evidence_refs=_count_broken_refs(document, args.evidence_dir),
        graph_invalid=not graph_ok,
    )
    outcome = evaluate_policy(
        policy_input, structurally_valid=structurally_valid, enforcements=profile_enforcements
    )

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "manifest": str(args.manifest),
        "structural_valid": structurally_valid,
        "issues": sorted(set(issues)),
        "manifest_identity_expected": identity_expected,
        "manifest_identity_matches": identity_ok,
        "policy_profile": args.profile or "default-canonical-release",
        **outcome.to_dict(),
        "legal_conclusion": "NOT_MADE",
    }
    _emit(report, human=args.human)

    if report["outcome"] == "invalid":
        return 1
    if report["outcome"] == "blocked":
        return 3
    if report["outcome"] in {"review-required", "pass-with-findings"}:
        return 0 if args.findings_are_not_failures else 4
    return 0


def _count_broken_refs(document: dict[str, Any], evidence_dir: str | None) -> int:
    """Count evidence references that cannot be resolved locally when a dir is given."""
    if not evidence_dir:
        return 0
    root = Path(evidence_dir)
    refs: list[dict[str, Any]] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if isinstance(node.get("kind"), str) and isinstance(node.get("reference"), str):
                refs.append(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(document)
    broken = 0
    for ref in refs:
        reference = str(ref["reference"])
        candidate = root / reference
        if ref.get("kind") == "commit":
            continue
        if not candidate.exists():
            broken += 1
    return broken


def cmd_identity(args: argparse.Namespace) -> int:
    try:
        document = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _emit({"ok": False, "error": str(exc)})
        return 2
    expected = compute_manifest_identity(document)
    declared = document.get("manifest_identity")
    _emit(
        {
            "ok": declared in (None, "", expected),
            "manifest_identity": expected,
            "declared": declared,
            "canonical_bytes": len(
                canonical_bytes({k: v for k, v in document.items() if k != "manifest_identity"})
            ),
        }
    )
    return 0


def cmd_graph(args: argparse.Namespace) -> int:
    manifest = load_manifest_file(args.manifest)
    nodes = [
        {
            "id": node.node_id,
            "kind": node.kind,
            **({"label": node.label} if node.label else {}),
            **({"external_ref": node.external_ref} if node.external_ref else {}),
        }
        for node in manifest.graph_nodes
    ]
    edges = [
        {"from": edge.source, "to": edge.target, "relation": edge.relation}
        | ({"transformation": edge.transformation} if edge.transformation else {})
        for edge in manifest.graph_edges
    ]
    ok, issues = check_graph_integrity(manifest_to_dict_compat(manifest))
    _emit({"dag_valid": ok, "nodes": nodes, "edges": edges, "issues": issues}, human=args.human)
    return 0 if ok else 1


def manifest_to_dict_compat(manifest: Any) -> dict[str, Any]:
    from .manifest import manifest_to_dict

    return manifest_to_dict(manifest)


def cmd_attest(args: argparse.Namespace) -> int:
    attestation = {
        "assertion_type": args.type,
        "assertedBy": args.by,
        "assertedAt": args.at or _now_iso(),
        "statement": args.statement,
    }
    if args.identity:
        attestation["assertedByIdentity"] = args.identity
    if args.applies_to:
        attestation["appliesTo"] = [
            item.strip() for item in args.applies_to.split(",") if item.strip()
        ]
    _emit(attestation)
    return 0


def cmd_export_spdx(args: argparse.Namespace) -> int:
    document = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    spdx_document = export_spdx(document)
    _emit(spdx_document)
    return 0


def cmd_evidence_verify(args: argparse.Namespace) -> int:
    try:
        document = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _emit({"ok": False, "error": str(exc)})
        return 2
    ok, expected = verify_evidence_digest(document)
    result: dict[str, Any] = {"ok": ok, "content_digest_expected": expected}
    if ok:
        record = evidence_record_from_dict(document)
        sealed = seal_evidence_record(record)
        result["evidence_id"] = sealed.evidence_id
        result["claims"] = [
            {"claim_type": claim.get("claim_type", "other"), "confidence": claim.get("confidence")}
            for claim in sealed.claims
        ]
    else:
        result["reason"] = "content_digest does not match canonical content"
    _emit(result, human=args.human)
    return 0 if ok else 1


def cmd_init(args: argparse.Namespace) -> int:
    manifest = {
        # Scaffolds carry no lineage yet, so they stay at the base version
        # that every pinned consumer (Forge, mncs-validator-rs) accepts.
        "schema_version": BASE_SCHEMA_VERSION,
        "spec_profile": args.profile,
        "artifact": {"id": args.artifact_id, "class": args.artifact_class},
        "provenance": {
            "origin_classification": "origin-uncertain",
            "participants": [],
            "process_evidence": [],
        },
        "rights": {
            "distribution_license": args.license,
            "copyright_status": "unresolved",
            "rights_basis": "unknown-needs-review",
            "third_party_material": "unknown",
            "sources": [],
            "notes": "Scaffolded by mncs-rp init; unresolved states are intentional until evidence arrives.",
        },
        "review": {
            "technical_validation": "not-run",
            "provenance_validation": "not-run",
            "human_acceptance": "not-reviewed",
        },
    }
    if args.seal:
        from .manifest import seal_manifest

        manifest = seal_manifest(manifest)
    _emit(manifest)
    return 0


def cmd_lineage_verify(args: argparse.Namespace) -> int:
    try:
        document = json.loads(Path(args.lineage).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _emit({"ok": False, "error": str(exc)})
        return 2
    issues = validate_lineage_structure(document)
    ok_digest, expected = verify_lineage_digest(document)
    if not ok_digest:
        issues = sorted(set(issues + ["content_digest does not match canonical content"]))
    try:
        record = lineage_record_from_dict(document)
        parsed: dict[str, Any] = {
            "lineage_id": record.lineage_id,
            "changesets": [item.get("changeset_id") for item in record.changesets],
            "authority_claims": len(record.authority_claims),
            "capability_gap_links": len(record.capability_gap_links),
        }
    except (TypeError, ValueError) as exc:
        issues = sorted(set(issues + [f"cannot parse lineage record: {exc}"]))
        parsed = {}
    result: dict[str, Any] = {
        "ok": not issues,
        "issues": issues,
        "content_digest_expected": expected,
        "content_digest_matches": ok_digest,
        **parsed,
    }
    _emit(result, human=args.human)
    return 0 if not issues else 1


def cmd_promotion_evaluate(args: argparse.Namespace) -> int:
    try:
        document = json.loads(Path(args.document).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _emit({"ok": False, "error": str(exc)})
        return 2
    dimensions_value: Any = None
    if isinstance(document, dict):
        if "promotion_dimensions" in document:
            dimensions_value = document.get("promotion_dimensions")
        elif isinstance(document.get("lineage"), dict):
            dimensions_value = document["lineage"].get("promotion_dimensions")
    if not isinstance(dimensions_value, dict):
        _emit(
            {
                "ok": False,
                "error": "no promotion_dimensions found (lineage record or manifest lineage block required)",
            }
        )
        return 2
    inputs = promotion_inputs_from_dict(dimensions_value)
    report = promotion_report(inputs)
    _emit({"ok": True, **report}, human=args.human)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mncs-rp", description="MNCS Rights & Provenance tooling")
    parser.add_argument("--version", action="version", version=f"mncs-rp {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser(
        "validate", help="validate a manifest and evaluate release policy"
    )
    validate_parser.add_argument("manifest")
    validate_parser.add_argument(
        "--artifact-file", help="verify sha256 of this file against declared artifact hashes"
    )
    validate_parser.add_argument("--profile", help="path to a policy-profile JSON document")
    validate_parser.add_argument(
        "--evidence-dir", help="root for resolving local evidence references"
    )
    validate_parser.add_argument("--human", action="store_true")
    validate_parser.add_argument(
        "--findings-are-not-failures",
        action="store_true",
        help="exit 0 even when outcome is pass-with-findings/review-required",
    )
    validate_parser.set_defaults(func=cmd_validate)

    identity_parser = subparsers.add_parser("identity", help="compute/verify manifest identity")
    identity_parser.add_argument("manifest")
    identity_parser.set_defaults(func=cmd_identity)

    graph_parser = subparsers.add_parser("graph", help="show the provenance graph")
    graph_parser.add_argument("manifest")
    graph_parser.add_argument("--human", action="store_true")
    graph_parser.set_defaults(func=cmd_graph)

    attest_parser = subparsers.add_parser(
        "attest", help="emit a contribution attestation JSON fragment"
    )
    attest_parser.add_argument("--type", required=True, dest="type")
    attest_parser.add_argument("--by", required=True)
    attest_parser.add_argument("--statement", required=True)
    attest_parser.add_argument("--at")
    attest_parser.add_argument("--identity")
    attest_parser.add_argument("--applies-to")
    attest_parser.set_defaults(func=cmd_attest)

    spdx_parser = subparsers.add_parser("export-spdx", help="export an SPDX 2.3 document")
    spdx_parser.add_argument("manifest")
    spdx_parser.set_defaults(func=cmd_export_spdx)

    evidence_parser = subparsers.add_parser("evidence", help="evidence-record operations")
    evidence_sub = evidence_parser.add_subparsers(dest="evidence_command", required=True)
    evidence_verify = evidence_sub.add_parser(
        "verify", help="verify an evidence record's content digest"
    )
    evidence_verify.add_argument("evidence")
    evidence_verify.add_argument("--human", action="store_true")
    evidence_verify.set_defaults(func=cmd_evidence_verify)

    init_parser = subparsers.add_parser("init", help="scaffold an uncertain-by-default manifest")
    init_parser.add_argument("artifact_id")
    init_parser.add_argument(
        "--artifact-class",
        default="source-code",
        choices=sorted(
            {
                "source-code",
                "documentation",
                "dataset",
                "model-weights",
                "configuration",
                "experiment-output",
                "receipt",
                "binary",
                "other",
            }
        ),
    )
    init_parser.add_argument("--license", default="Apache-2.0")
    init_parser.add_argument(
        "--profile", default="canonical-release", choices=["development", "canonical-release"]
    )
    init_parser.add_argument(
        "--seal", action="store_true", help="attach computed manifest_identity"
    )
    init_parser.set_defaults(func=cmd_init)

    lineage_parser = subparsers.add_parser("lineage", help="lineage-record operations")
    lineage_sub = lineage_parser.add_subparsers(dest="lineage_command", required=True)
    lineage_verify = lineage_sub.add_parser("verify", help="verify a lineage record")
    lineage_verify.add_argument("lineage")
    lineage_verify.add_argument("--human", action="store_true")
    lineage_verify.set_defaults(func=cmd_lineage_verify)

    promotion_parser = subparsers.add_parser("promotion", help="promotion-input operations")
    promotion_sub = promotion_parser.add_subparsers(dest="promotion_command", required=True)
    promotion_eval = promotion_sub.add_parser(
        "evaluate", help="combine promotion dimensions (FAIL > UNKNOWN > PASS)"
    )
    promotion_eval.add_argument("document", help="lineage record or manifest with lineage block")
    promotion_eval.add_argument("--human", action="store_true")
    promotion_eval.set_defaults(func=cmd_promotion_evaluate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    exit_code = args.func(args)
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
