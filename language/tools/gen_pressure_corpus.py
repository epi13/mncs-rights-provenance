#!/usr/bin/env python3
"""Generate execution corpora and host golden vectors for the normative
distributed-pressure verdict core (language/pressure_provenance.mncs).

Emits:
  language/corpora/pressure-verdict-corpus.json
  conformance/pressure-golden-vectors.json

Run from the repository root:
    python3 language/tools/gen_pressure_corpus.py
"""

from __future__ import annotations

import json
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = "mncs.rights.pressure.v01"
CORPORA_DIR = ROOT / "language" / "corpora"
CONFORMANCE_DIR = ROOT / "conformance"

VERDICTS = ("Pass", "Fail", "Unknown")
TRUTHS = ("No", "Yes")

PROMOTION_FIELDS = [
    ("authority", "Verdict"),
    ("compiler_backend", "Verdict"),
    ("coordination_dependency", "Verdict"),
    ("policy", "Verdict"),
    ("provenance", "Verdict"),
    ("rights_license", "Verdict"),
    ("technical", "Verdict"),
    ("test_conformance", "Verdict"),
]


def finite(type_name: str, variant: str) -> dict:
    tables = {"Verdict": VERDICTS, "Truth": TRUTHS}
    variants = tables[type_name]
    return {
        "finite": {
            "type_identity": f"mncs:0.2:finite-type:{MODULE}::{type_name}",
            "variant_identity": f"mncs:0.2:finite-variant:{MODULE}::{type_name}::{variant}",
            "discriminant": variants.index(variant),
        }
    }


def truth(flag: bool) -> dict:
    return finite("Truth", TRUTHS[1 if flag else 0])


def promotion_record(values: dict[str, str]) -> dict:
    encoded = {name: finite("Verdict", values[name]) for name, _ in PROMOTION_FIELDS}
    joined = "".join(f"{name}:{ty};" for name, ty in sorted(PROMOTION_FIELDS))
    digest = urllib.parse.quote(joined, safe="")
    return {
        "record": {
            "type_identity": f"mncs:0.2:record-type:{MODULE}::PromotionInputs::{digest}",
            "name": "PromotionInputs",
            "fields": [[name, encoded[name]] for name, _ty in sorted(PROMOTION_FIELDS)],
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


# ---- Reference semantics (mirrors promotion.py / authority.py / lineage.py) --


def ref_combine(left: str, right: str) -> str:
    rank = {"Pass": 0, "Unknown": 1, "Fail": 2}
    names = {v: k for k, v in rank.items()}
    return names[max(rank[left], rank[right])]


def ref_promotion(values: dict[str, str]) -> str:
    combined = "Pass"
    for name, _ in PROMOTION_FIELDS:
        combined = ref_combine(combined, values[name])
    return combined


def ref_authority(scope: bool, evidence: bool, approval: bool) -> str:
    if not scope:
        return "Fail"
    if not evidence:
        return "Unknown"
    if not approval:
        return "Unknown"
    return "Pass"


def ref_lineage(
    changeset: bool, derivation: bool, producer: bool, bound: bool, tamper: bool
) -> str:
    if tamper:
        return "Fail"
    if changeset and derivation and producer and bound:
        return "Pass"
    return "Unknown"


def main() -> int:
    CORPORA_DIR.mkdir(parents=True, exist_ok=True)
    CONFORMANCE_DIR.mkdir(parents=True, exist_ok=True)

    entries: list[dict] = []
    golden: list[dict] = []

    for left in VERDICTS:
        for right in VERDICTS:
            expected = ref_combine(left, right)
            entries.append(
                case(
                    f"combine-{left}-{right}",
                    "combine_verdict",
                    [finite("Verdict", left), finite("Verdict", right)],
                    [finite("Verdict", expected)],
                )
            )
            golden.append(
                {
                    "function": "combine_verdict",
                    "inputs": {"left": left, "right": right},
                    "output": expected,
                }
            )

    def promotion_case(case_id: str, values: dict[str, str]) -> None:
        expected = ref_promotion(values)
        entries.append(
            case(
                case_id,
                "promotion_combined",
                [promotion_record(values)],
                [finite("Verdict", expected)],
            )
        )
        golden.append(
            {"function": "promotion_combined", "inputs": dict(values), "output": expected}
        )

    all_pass = {name: "Pass" for name, _ in PROMOTION_FIELDS}
    promotion_case("promotion-all-pass", all_pass)
    for name, _ in PROMOTION_FIELDS:
        values = dict(all_pass)
        values[name] = "Fail"
        promotion_case(f"promotion-{name}-fail", values)
        values = dict(all_pass)
        values[name] = "Unknown"
        promotion_case(f"promotion-{name}-unknown", values)
    mixed = dict(all_pass)
    mixed["technical"] = "Unknown"
    mixed["authority"] = "Fail"
    promotion_case("promotion-mixed-fail-dominates", mixed)
    promotion_case("promotion-all-unknown", {name: "Unknown" for name, _ in PROMOTION_FIELDS})

    for scope in (False, True):
        for evidence in (False, True):
            for approval in (False, True):
                expected = ref_authority(scope, evidence, approval)
                tag = f"{int(scope)}{int(evidence)}{int(approval)}"
                entries.append(
                    case(
                        f"authority-{tag}",
                        "authority_verdict",
                        [truth(scope), truth(evidence), truth(approval)],
                        [finite("Verdict", expected)],
                    )
                )
                golden.append(
                    {
                        "function": "authority_verdict",
                        "inputs": {
                            "scope_matches": scope,
                            "evidence_present": evidence,
                            "approval_present": approval,
                        },
                        "output": expected,
                    }
                )

    combos = [
        ("lineage-complete", True, True, True, True, False),
        ("lineage-missing-changeset", False, True, True, True, False),
        ("lineage-missing-derivation", True, False, True, True, False),
        ("lineage-missing-producer", True, True, False, True, False),
        ("lineage-unbound-evidence", True, True, True, False, False),
        ("lineage-tampered", True, True, True, True, True),
        ("lineage-tampered-partial", False, False, False, False, True),
        ("lineage-empty", False, False, False, False, False),
    ]
    for case_id, changeset, derivation, producer, bound, tamper in combos:
        expected = ref_lineage(changeset, derivation, producer, bound, tamper)
        entries.append(
            case(
                case_id,
                "lineage_verdict",
                [
                    truth(changeset),
                    truth(derivation),
                    truth(producer),
                    truth(bound),
                    truth(tamper),
                ],
                [finite("Verdict", expected)],
            )
        )
        golden.append(
            {
                "function": "lineage_verdict",
                "inputs": {
                    "has_changeset": changeset,
                    "has_derivation": derivation,
                    "has_producer": producer,
                    "evidence_bound": bound,
                    "tamper_detected": tamper,
                },
                "output": expected,
            }
        )

    corpus = {"schema_version": "0.1", "name": "pressure-verdicts-v1", "cases": entries}
    (CORPORA_DIR / "pressure-verdict-corpus.json").write_text(json.dumps(corpus, indent=1) + "\n")

    vectors = {
        "schema_version": "0.3.0",
        "source_module": MODULE,
        "description": (
            "Golden vectors generated by language/tools/gen_pressure_corpus.py from the "
            "normative distributed-pressure verdict semantics. Host implementations must "
            "reproduce these exactly."
        ),
        "cases": golden,
    }
    (CONFORMANCE_DIR / "pressure-golden-vectors.json").write_text(
        json.dumps(vectors, indent=1) + "\n"
    )

    print(json.dumps({"corpus_cases": len(entries), "golden_vectors": len(golden)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
