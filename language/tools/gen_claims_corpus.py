#!/usr/bin/env python3
"""Generate the execution corpus and host golden vectors for the normative
rights-claim status core (language/rights_claims.mncs).

Emits:
  language/corpora/claims-corpus.json
  conformance/claims-golden-vectors.json

Run from the repository root:
    python3 language/tools/gen_claims_corpus.py

Conventions mirror gen_pressure_corpus.py: the corpus carries executable
cases (typed arguments with declaration-inventory identities plus pinned
expectations) for `mncs experiment run`; the golden vectors carry the
same contract in symbolic form for host consumers.
"""

from __future__ import annotations

import json
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = "mncs.rights.claims.v01"
CORPORA_DIR = ROOT / "language" / "corpora"
CONFORMANCE_DIR = ROOT / "conformance"

STATUSES = (
    "Asserted",
    "Verified",
    "Contested",
    "Superseded",
    "Expired",
    "Revoked",
    "Incompatible",
    "Unknown",
)

CLAIM_FIELDS = [
    ("id", "u64"),
    ("subject", "u64"),
    ("claimant", "u64"),
    ("basis", "u64"),
    ("license", "u64"),
    ("attribution", "u64"),
    ("redistribute", "u64"),
    ("derivatives", "u64"),
    ("commercial", "u64"),
    ("evidence", "u64"),
    ("effective", "u64"),
    ("expires", "u64"),
    ("revoked", "u64"),
    ("supersedes", "u64"),
    ("verified", "u64"),
    ("contested", "u64"),
]


def u64(value: int) -> dict:
    return {"integer": {"value": value, "type": {"bits": 64, "signed": False}}}


def status(name: str) -> dict:
    return {
        "finite": {
            "type_identity": f"mncs:0.2:finite-type:{MODULE}::ClaimStatus",
            "variant_identity": f"mncs:0.2:finite-variant:{MODULE}::ClaimStatus::{name}",
            "discriminant": STATUSES.index(name),
        }
    }


def claim_record(values: dict[str, int]) -> dict:
    full = {name: values.get(name, 0) for name, _ in CLAIM_FIELDS}
    joined = "".join(f"{name}:{ty};" for name, ty in sorted(CLAIM_FIELDS))
    digest = urllib.parse.quote(joined, safe="")
    return {
        "record": {
            "type_identity": f"mncs:0.2:record-type:{MODULE}::Claim::{digest}",
            "name": "Claim",
            "fields": [[name, u64(full[name])] for name, _ty in sorted(CLAIM_FIELDS)],
        }
    }


def request(function: str, arguments: list) -> dict:
    return {
        "schema_version": "0.1",
        "target": {"module": MODULE, "function": function},
        "arguments": arguments,
        "step_budget": 4096,
    }


def case(case_id: str, function: str, arguments: list, expected_values: list) -> dict:
    return {"id": case_id, "request": request(function, arguments), "expected": expected_values}


def claim_case(case_id: str, values: dict, now: int, superseded: int, expected: str):
    return (
        case(case_id, "claim_status", [claim_record(values), u64(now), u64(superseded)], [status(expected)]),
        {"function": "claim_status", "inputs": {"claim": values, "now": now, "superseded": superseded}, "output": expected},
    )


def scalar_case(case_id: str, function: str, args: list[int], expected: int):
    return (
        case(case_id, function, [u64(a) for a in args], [u64(expected)]),
        {"function": function, "inputs": {"args": args}, "output": expected},
    )


def enum_case(case_id: str, function: str, args: list, expected: str):
    encoded = [status(a) if isinstance(a, str) else u64(a) for a in args]
    return (
        case(case_id, function, encoded, [status(expected)]),
        {"function": function, "inputs": {"args": args}, "output": expected},
    )


def attrib_case(case_id: str, attribution: int, status_name: str, expected: int):
    return (
        case(case_id, "attribution_due", [u64(attribution), status(status_name)], [u64(expected)]),
        {"function": "attribution_due", "inputs": {"attribution": attribution, "status": status_name}, "output": expected},
    )


BASE = {"id": 1, "subject": 7, "claimant": 3, "basis": 2, "license": 9,
        "attribution": 1, "redistribute": 1, "derivatives": 1, "commercial": 2,
        "evidence": 42, "effective": 100, "expires": 0, "revoked": 0,
        "supersedes": 0, "verified": 0, "contested": 0}


def build() -> tuple[list, list]:
    corpus, golden = [], []

    def add(pair):
        corpus.append(pair[0])
        golden.append(pair[1])

    # claim_status: precedence Revoked > Expired > Superseded >
    # Contested > Unknown(no evidence) > Verified > Asserted.
    add(claim_case("status-revoked-dominates", {**BASE, "revoked": 1, "verified": 1}, 500, 0, "Revoked"))
    add(claim_case("status-expired", {**BASE, "expires": 400, "verified": 1}, 500, 0, "Expired"))
    add(claim_case("status-expiry-boundary", {**BASE, "expires": 500, "verified": 1}, 500, 0, "Expired"))
    add(claim_case("status-live-before-expiry", {**BASE, "expires": 501, "verified": 1}, 500, 0, "Verified"))
    add(claim_case("status-no-expiry", {**BASE, "verified": 1}, 10**12, 0, "Verified"))
    add(claim_case("status-superseded", {**BASE, "evidence": 42}, 500, 1, "Superseded"))
    add(claim_case("status-contested-beats-verified", {**BASE, "verified": 1, "contested": 1}, 500, 0, "Contested"))
    add(claim_case("status-no-evidence-unknown", {**BASE, "evidence": 0, "verified": 0}, 500, 0, "Unknown"))
    add(claim_case("status-verified-flag-without-evidence-unknown", {**BASE, "evidence": 0, "verified": 1}, 500, 0, "Unknown"))
    add(claim_case("status-verified", {**BASE, "verified": 1}, 500, 0, "Verified"))
    add(claim_case("status-asserted", dict(BASE), 500, 0, "Asserted"))
    add(claim_case("status-revoked-beats-contested", {**BASE, "revoked": 1, "contested": 1}, 500, 0, "Revoked"))
    add(claim_case("status-expired-beats-superseded", {**BASE, "expires": 100}, 500, 1, "Expired"))
    add(claim_case("status-superseded-beats-contested", {**BASE, "contested": 1}, 500, 1, "Superseded"))

    # temporal_state(effective, expires, now, revoked): 0 live,
    # 1 not-yet, 2 expired, 3 revoked.
    add(scalar_case("temporal-live", "temporal_state", [100, 0, 500, 0], 0))
    add(scalar_case("temporal-not-yet", "temporal_state", [600, 0, 500, 0], 1))
    add(scalar_case("temporal-expired", "temporal_state", [100, 400, 500, 0], 2))
    add(scalar_case("temporal-expiry-boundary", "temporal_state", [100, 500, 500, 0], 2))
    add(scalar_case("temporal-revoked-dominates", "temporal_state", [100, 0, 500, 1], 3))
    add(scalar_case("temporal-revoked-beats-expiry", "temporal_state", [100, 400, 500, 1], 3))

    # evidence_state(evidence, current, checked): 0 current, 1 stale,
    # 2 missing, 3 unchecked.
    add(scalar_case("evidence-current", "evidence_state", [42, 42, 1], 0))
    add(scalar_case("evidence-stale", "evidence_state", [42, 43, 1], 1))
    add(scalar_case("evidence-missing", "evidence_state", [0, 43, 1], 2))
    add(scalar_case("evidence-unchecked", "evidence_state", [42, 42, 0], 3))
    add(scalar_case("evidence-unchecked-beats-missing", "evidence_state", [0, 0, 0], 3))

    # basis_compatible: 0 compatible, 1 conflict, 2 unknown.
    add(scalar_case("compat-permit-permit", "basis_compatible", [2, 1, 1, 1, 1, 1, 1, 1], 0))
    add(scalar_case("compat-forbid-forbid", "basis_compatible", [2, 0, 0, 0, 1, 0, 0, 0], 0))
    add(scalar_case("compat-redistribute-conflict", "basis_compatible", [2, 0, 1, 1, 1, 1, 1, 1], 1))
    add(scalar_case("compat-derivatives-conflict", "basis_compatible", [0, 1, 0, 1, 3, 1, 1, 1], 1))
    add(scalar_case("compat-commercial-conflict", "basis_compatible", [2, 1, 1, 0, 4, 1, 1, 1], 1))
    add(scalar_case("compat-unknown-basis", "basis_compatible", [5, 1, 1, 1, 1, 1, 1, 1], 2))
    add(scalar_case("compat-unknown-basis-other-side", "basis_compatible", [2, 0, 0, 0, 5, 1, 1, 1], 2))
    add(scalar_case("compat-unknown-scope", "basis_compatible", [2, 1, 1, 2, 1, 1, 1, 1], 2))
    add(scalar_case("compat-conflict-beats-unknown", "basis_compatible", [2, 0, 2, 1, 1, 1, 1, 1], 1))

    # attribution_due: 1 due, 0 not due, 2 uncertain scope.
    add(attrib_case("attrib-asserted-required", 1, "Asserted", 1))
    add(attrib_case("attrib-verified-required", 1, "Verified", 1))
    add(attrib_case("attrib-verified-not-required", 0, "Verified", 0))
    add(attrib_case("attrib-asserted-not-required", 0, "Asserted", 0))
    add(attrib_case("attrib-expired-uncertain", 1, "Expired", 2))
    add(attrib_case("attrib-revoked-uncertain", 1, "Revoked", 2))
    add(attrib_case("attrib-unknown-uncertain", 1, "Unknown", 2))

    # signed_state: layers stay separate.
    add(enum_case("signed-none-unknown", "signed_state", [0, 0, 0], "Unknown"))
    add(enum_case("signed-naked-sig-unknown", "signed_state", [0, 1, 1], "Unknown"))
    add(enum_case("signed-no-authority-contested", "signed_state", [1, 0, 0], "Contested"))
    add(enum_case("signed-unverified-asserted", "signed_state", [1, 1, 0], "Asserted"))
    add(enum_case("signed-full-verified", "signed_state", [1, 1, 1], "Verified"))

    # supersede_link_valid: 0 valid, 1 subject mismatch,
    # 2 successor basis unknown, 3 base not live.
    add(scalar_case("link-valid", "supersede_link_valid", [1, 1, 1], 0))
    add(scalar_case("link-subject-mismatch", "supersede_link_valid", [1, 1, 0], 1))
    add(scalar_case("link-basis-unknown", "supersede_link_valid", [1, 0, 1], 2))
    add(scalar_case("link-base-not-live", "supersede_link_valid", [0, 1, 1], 3))
    return corpus, golden


def main() -> None:
    corpus, golden = build()
    corpus_doc = {"schema_version": "0.1", "name": "rights-claims-v1", "cases": corpus}
    golden_doc = {
        "schema_version": "0.1",
        "source_module": MODULE,
        "description": "Symbolic contract for the rights-claim status core; executable form in language/corpora/claims-corpus.json.",
        "cases": golden,
    }
    corpus_path = CORPORA_DIR / "claims-corpus.json"
    golden_path = CONFORMANCE_DIR / "claims-golden-vectors.json"
    corpus_path.write_text(json.dumps(corpus_doc, indent=1) + "\n")
    golden_path.write_text(json.dumps(golden_doc, indent=1) + "\n")
    print(f"wrote {len(corpus)} corpus cases -> {corpus_path}")
    print(f"wrote {len(golden)} golden vectors -> {golden_path}")


if __name__ == "__main__":
    main()
