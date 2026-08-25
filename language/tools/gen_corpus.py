#!/usr/bin/env python3
"""Generate execution corpora and host-implementation golden vectors for the
MNCS-language rights policy core (language/rights_policy.mncs).

Emits:
  language/corpora/policy-evaluation-corpus.json   (evaluate + gate_severities)
  language/corpora/severity-combine-corpus.json    (combine/apply_enforcement tables)
  conformance/golden-vectors.json                  (host cross-check vectors)

Run from the repository root:
    python3 language/tools/gen_corpus.py
"""

from __future__ import annotations

import json
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = "mncs.rights.policy.v01"
CORPORA_DIR = ROOT / "language" / "corpora"
CONFORMANCE_DIR = ROOT / "conformance"

SEVERITY_VARIANTS = ("None", "Finding", "Review", "Blocking")
OUTCOME_VARIANTS = ("Pass", "PassWithFindings", "ReviewRequired", "Blocked")
TRUTH_VARIANTS = ("No", "Yes")

GATE_INPUT_FIELDS = [
    ("attestation_conflicts", "i32"),
    ("broken_evidence_refs", "i32"),
    ("canonical_release_profile", "Truth"),
    ("contradiction_count", "i32"),
    ("copyright_code", "i32"),
    ("graph_invalid", "Truth"),
    ("hash_mismatch", "Truth"),
    ("human_accept_code", "i32"),
    ("impossible_evidence", "Truth"),
    ("incompatible_source_count", "i32"),
    ("origin_code", "i32"),
    ("prov_valid_code", "i32"),
    ("rights_basis_code", "i32"),
    ("third_party_code", "i32"),
    ("unknown_source_count", "i32"),
]

# Canonical gate order (must match gates.GATE_TABLE / rights_policy.mncs).
GATE_SEVERITY_FIELDS = [
    "hash_correspondence",
    "evidence_refs",
    "graph_integrity",
    "incompatible_license",
    "contradictory_license",
    "rights_basis_resolved",
    "third_party_resolved",
    "copyright_resolved",
    "provenance_passed",
    "provenance_complete",
    "human_review_ok",
    "unknown_source_license",
    "attestation_integrity",
    "impossible_evidence_gate",
]


def integer(value: int) -> dict:
    return {"integer": {"value": value, "type": {"bits": 32, "signed": True}}}


VARIANT_TABLES = {
    "Severity": SEVERITY_VARIANTS,
    "Outcome": OUTCOME_VARIANTS,
    "Truth": TRUTH_VARIANTS,
    "Enforcement": ("Disabled", "FindingCap", "ReviewCap", "Fatal"),
}


def finite(type_name: str, variant: str) -> dict:
    variants = VARIANT_TABLES[type_name]
    return {
        "finite": {
            "type_identity": f"mncs:0.2:finite-type:{MODULE}::{type_name}",
            "variant_identity": f"mncs:0.2:finite-variant:{MODULE}::{type_name}::{variant}",
            "discriminant": variants.index(variant),
        }
    }


def truth(flag: bool) -> dict:
    return finite("Truth", TRUTH_VARIANTS[1 if flag else 0])


def record_input(case: dict) -> dict:
    """Build a GateInput record value from a plain case dict."""
    values = {
        "origin_code": integer(case["origin_code"]),
        "copyright_code": integer(case["copyright_code"]),
        "rights_basis_code": integer(case["rights_basis_code"]),
        "third_party_code": integer(case["third_party_code"]),
        "prov_valid_code": integer(case["prov_valid_code"]),
        "human_accept_code": integer(case["human_accept_code"]),
        "incompatible_source_count": integer(case["incompatible_source_count"]),
        "unknown_source_count": integer(case["unknown_source_count"]),
        "contradiction_count": integer(case["contradiction_count"]),
        "hash_mismatch": truth(case["hash_mismatch"]),
        "broken_evidence_refs": integer(case["broken_evidence_refs"]),
        "graph_invalid": truth(case["graph_invalid"]),
        "attestation_conflicts": integer(case["attestation_conflicts"]),
        "impossible_evidence": truth(case["impossible_evidence"]),
        "canonical_release_profile": truth(case["canonical_release_profile"]),
    }
    joined = "".join(f"{name}:{ty};".format(name=name, ty=ty) for name, ty in sorted(GATE_INPUT_FIELDS))
    digest = urllib.parse.quote(joined, safe="")
    return {
        "record": {
            "type_identity": f"mncs:0.2:record-type:{MODULE}::GateInput::{digest}",
            "name": "GateInput",
            "fields": [[name, values[name]] for name, _ty in sorted(GATE_INPUT_FIELDS)],
        }
    }


def request(function: str, arguments: list) -> dict:
    return {
        "schema_version": "0.1",
        "target": {"module": MODULE, "function": function},
        "arguments": arguments,
        "step_budget": 4096,
    }


GATE_SEVERITY_FIELD_TYPES = [(name, "Severity") for name in GATE_SEVERITY_FIELDS]


def _severities_record(severities: list[str]) -> dict:
    values = {
        name: finite("Severity", variant)
        for name, variant in zip(GATE_SEVERITY_FIELDS, severities)
    }
    joined = "".join(f"{name}:{ty};".format(name=name, ty=ty) for name, ty in sorted(GATE_SEVERITY_FIELD_TYPES))
    digest = urllib.parse.quote(joined, safe="")
    return {
        "record": {
            "type_identity": f"mncs:0.2:record-type:{MODULE}::GateSeverities::{digest}",
            "name": "GateSeverities",
            "fields": [[name, values[name]] for name, _ty in sorted(GATE_SEVERITY_FIELD_TYPES)],
        }
    }


def case(case_id: str, function: str, arguments: list, expected_values: list | None = None) -> dict:
    entry = {"id": case_id, "request": request(function, arguments)}
    if expected_values is not None:
        entry["expected"] = expected_values
    return entry


# ---- Reference semantics (mirrors src/mncs_rights_provenance/gates.py) ------


def ref_severities(c: dict) -> list[str]:
    canonical = c["canonical_release_profile"]
    review_or_finding = "Review" if canonical else "Finding"

    def gate() -> list[str]:
        out = ["None"] * 14
        out[0] = "Blocking" if c["hash_mismatch"] else "None"
        out[1] = "Review" if c["broken_evidence_refs"] > 0 else "None"
        out[2] = "Blocking" if c["graph_invalid"] else "None"
        out[3] = "Blocking" if c["incompatible_source_count"] > 0 else "None"
        out[4] = "Review" if c["contradiction_count"] > 0 else "None"
        out[5] = "Review" if c["rights_basis_code"] == 5 else "None"
        if c["third_party_code"] in (2, 3):
            out[6] = review_or_finding
        if c["copyright_code"] == 6:
            out[7] = review_or_finding
        if c["prov_valid_code"] == 1:
            out[8] = "Blocking"
        if c["prov_valid_code"] in (2, 3):
            out[9] = "Review"
        if c["human_accept_code"] == 1:
            out[10] = "Blocking"
        elif c["human_accept_code"] == 2:
            out[10] = review_or_finding
        if c["unknown_source_count"] > 0:
            out[11] = review_or_finding
        if c["attestation_conflicts"] > 0:
            out[12] = "Review"
        if c["impossible_evidence"]:
            out[13] = "Blocking"
        return out

    return gate()


RANK = {"None": 0, "Finding": 1, "Review": 2, "Blocking": 3}
NAME_BY_RANK = {v: k for k, v in RANK.items()}
OUTCOME_BY_RANK = {0: "Pass", 1: "PassWithFindings", 2: "ReviewRequired", 3: "Blocked"}


def combine(a: str, b: str) -> str:
    return NAME_BY_RANK[max(RANK[a], RANK[b])]


DEFAULT_ENFORCEMENT_RANKS = [3, 2, 3, 3, 2, 2, 2, 2, 3, 2, 2, 2, 2, 3]


def ref_outcome(c: dict) -> str:
    severities = ref_severities(c)
    effective = [
        NAME_BY_RANK[min(RANK[severity], cap)]
        for severity, cap in zip(severities, DEFAULT_ENFORCEMENT_RANKS)
    ]
    combined = NAME_BY_RANK[max(RANK[s] for s in effective)]
    return OUTCOME_BY_RANK[RANK[combined]]


# ---- Cases -------------------------------------------------------------------


def evaluation_cases() -> list[dict]:
    base = {
        "origin_code": 0,
        "copyright_code": 0,
        "rights_basis_code": 0,
        "third_party_code": 0,
        "prov_valid_code": 0,
        "human_accept_code": 0,
        "incompatible_source_count": 0,
        "unknown_source_count": 0,
        "contradiction_count": 0,
        "hash_mismatch": False,
        "broken_evidence_refs": 0,
        "graph_invalid": False,
        "attestation_conflicts": 0,
        "impossible_evidence": False,
        "canonical_release_profile": True,
    }

    def variant(**overrides):
        case_dict = dict(base)
        case_dict.update(overrides)
        return case_dict

    return [
        variant(),  # fully clean -> pass
        variant(hash_mismatch=True),  # blocking via hash
        variant(incompatible_source_count=1),  # blocking via license
        variant(graph_invalid=True),  # blocking via graph
        variant(impossible_evidence=True),  # blocking via falsified evidence
        variant(prov_valid_code=1),  # blocking via failed provenance validation
        variant(human_accept_code=1),  # blocking via human rejection
        variant(rights_basis_code=5),  # review: unknown rights basis
        variant(third_party_code=2),  # review: possible third party
        variant(third_party_code=3),  # review: unknown third party
        variant(copyright_code=6),  # review: unresolved copyright
        variant(prov_valid_code=2),  # review: incomplete provenance validation
        variant(prov_valid_code=3),  # review: provenance not run
        variant(human_accept_code=2),  # review: not reviewed
        variant(unknown_source_count=2),  # review: unknown source license
        variant(broken_evidence_refs=1),  # review: broken evidence reference
        variant(attestation_conflicts=1),  # review: conflicting attestations
        variant(contradiction_count=1),  # review: contradictory license evidence
        variant(canonical_release_profile=False, third_party_code=3),  # finding only (dev profile)
        variant(
            canonical_release_profile=False,
            third_party_code=3,
            copyright_code=6,
            human_accept_code=2,
            unknown_source_count=1,
        ),  # multiple dev-profile findings -> pass-with-findings
    ]


def main() -> int:
    CORPORA_DIR.mkdir(parents=True, exist_ok=True)
    CONFORMANCE_DIR.mkdir(parents=True, exist_ok=True)

    eval_entries = []
    gates_entries = []
    golden_cases = []
    for index, case_dict in enumerate(evaluation_cases()):
        input_value = record_input(case_dict)
        severities = ref_severities(case_dict)
        outcome = ref_outcome(case_dict)
        eval_entries.append(
            case(
                f"evaluate-{index:02d}",
                "evaluate",
                [input_value],
                [finite("Outcome", outcome)],
            )
        )
        gates_entries.append(
            case(
                f"gates-{index:02d}",
                "gate_severities",
                [input_value],
                [_severities_record(severities)],
            )
        )
        golden_cases.append(
            {
                "input": case_dict,
                "severities": dict(zip(GATE_SEVERITY_FIELDS, severities)),
                "outcome": outcome,
            }
        )

    combine_entries = []
    for left in SEVERITY_VARIANTS:
        for right in SEVERITY_VARIANTS:
            combine_entries.append(
                case(
                    f"combine-{left}-{right}",
                    "combine",
                    [finite("Severity", left), finite("Severity", right)],
                    [finite("Severity", combine(left, right))],
                )
            )
    enforcement_rank = {"Disabled": 0, "FindingCap": 1, "ReviewCap": 2, "Fatal": 3}

    def apply_enforcement_ref(severity: str, enforcement: str) -> str:
        rank = RANK[severity]
        level = enforcement_rank[enforcement]
        if level >= 3:
            return severity
        cap = {2: 2, 1: 1, 0: 0}[level]
        return NAME_BY_RANK[min(rank, cap)]

    for severity in SEVERITY_VARIANTS:
        for enforcement in ("Disabled", "FindingCap", "ReviewCap", "Fatal"):
            combine_entries.append(
                case(
                    f"enforce-{enforcement}-{severity}",
                    "apply_enforcement",
                    [finite("Severity", severity), finite("Enforcement", enforcement)],
                    [finite("Severity", apply_enforcement_ref(severity, enforcement))],
                )
            )

    eval_corpus = {
        "schema_version": "0.1",
        "name": "rights-policy-evaluation-v1",
        "cases": eval_entries,
    }
    gates_corpus = {
        "schema_version": "0.1",
        "name": "rights-policy-gate-severities-v1",
        "cases": gates_entries,
    }
    combine_corpus = {
        "schema_version": "0.1",
        "name": "severity-lattice-v1",
        "cases": combine_entries,
    }
    CORPORA_DIR.mkdir(parents=True, exist_ok=True)
    (CORPORA_DIR / "policy-evaluation-corpus.json").write_text(json.dumps(eval_corpus, indent=1) + "\n")
    (CORPORA_DIR / "gate-severities-corpus.json").write_text(json.dumps(gates_corpus, indent=1) + "\n")
    (CORPORA_DIR / "severity-combine-corpus.json").write_text(json.dumps(combine_corpus, indent=1) + "\n")

    golden = {
        "schema_version": "0.2.0",
        "source_module": MODULE,
        "description": (
            "Golden vectors generated by language/tools/gen_corpus.py from the "
            "normative reference semantics. Host implementations must reproduce "
            "these exactly."
        ),
        "cases": golden_cases,
    }
    CONFORMANCE_DIR.mkdir(parents=True, exist_ok=True)
    (CONFORMANCE_DIR / "golden-vectors.json").write_text(json.dumps(golden, indent=1) + "\n")

    print(
        json.dumps(
            {
                "evaluation_cases": len(eval_entries),
                "gate_severities_cases": len(gates_entries),
                "lattice_cases": len(combine_entries),
                "golden_vectors": len(golden_cases),
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
