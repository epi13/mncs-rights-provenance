#!/usr/bin/env python3
"""Generate corpus and host golden vectors for source-license evidence state."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = "mncs.rights.source_license_status.v01"
CORPUS_PATH = ROOT / "language/corpora/source-license-status-corpus.json"
GOLDEN_PATH = ROOT / "conformance/source-license-status-golden-vectors.json"

STATUSES = ("Compatible", "Incompatible", "Unknown", "NotApplicable")
EVIDENCE_STATES = ("Unverified", "Verified")
VERIFIED_ASSESSMENTS = {
    "Compatible": "VerifiedCompatible",
    "Incompatible": "VerifiedIncompatible",
    "Unknown": "VerifiedUnknown",
    "NotApplicable": "VerifiedNotApplicable",
}
ASSESSMENTS = (
    "Unverified",
    "VerifiedCompatible",
    "VerifiedIncompatible",
    "VerifiedUnknown",
    "VerifiedNotApplicable",
)
ASSESSMENT_LABELS = {
    "Unverified": "unverified",
    "VerifiedCompatible": "verified-compatible",
    "VerifiedIncompatible": "verified-incompatible",
    "VerifiedUnknown": "verified-unknown",
    "VerifiedNotApplicable": "verified-not-applicable",
}


def finite(type_name: str, variant: str) -> dict:
    variants = {
        "LicenseStatus": STATUSES,
        "EvidenceState": EVIDENCE_STATES,
        "Assessment": ASSESSMENTS,
    }[type_name]
    return {
        "finite": {
            "type_identity": f"mncs:0.2:finite-type:{MODULE}::{type_name}",
            "variant_identity": (
                f"mncs:0.2:finite-variant:{MODULE}::{type_name}::{variant}"
            ),
            "discriminant": variants.index(variant),
        }
    }


def build() -> tuple[list[dict], list[dict]]:
    corpus_cases: list[dict] = []
    golden_cases: list[dict] = []
    for evidence in EVIDENCE_STATES:
        for status in STATUSES:
            assessment = (
                "Unverified" if evidence == "Unverified"
                else VERIFIED_ASSESSMENTS[status]
            )
            case_id = f"{evidence.lower()}-{status.lower()}"
            corpus_cases.append({
                "id": case_id,
                "request": {
                    "schema_version": "0.1",
                    "target": {
                        "module": MODULE,
                        "function": "classify_source_license_status",
                    },
                    "arguments": [
                        finite("LicenseStatus", status),
                        finite("EvidenceState", evidence),
                    ],
                    "step_budget": 256,
                },
                "expected": [finite("Assessment", assessment)],
            })
            golden_cases.append({
                "case_id": case_id,
                "status": status.lower().replace("notapplicable", "not-applicable"),
                "evidence_state": evidence.lower(),
                "assessment": ASSESSMENT_LABELS[assessment],
            })
    return corpus_cases, golden_cases


def main() -> int:
    corpus_cases, golden_cases = build()
    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    CORPUS_PATH.write_text(json.dumps({
        "schema_version": "0.1",
        "name": "source-license-status-evidence-v1",
        "cases": corpus_cases,
    }, indent=1) + "\n", encoding="utf-8")
    GOLDEN_PATH.write_text(json.dumps({
        "schema_version": "0.1",
        "source_module": MODULE,
        "description": (
            "Evidence-state classifications generated from the normative "
            "MNCS source-license status core."
        ),
        "cases": golden_cases,
    }, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"cases": len(corpus_cases), "golden_vectors": len(golden_cases)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
