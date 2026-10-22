#!/usr/bin/env python3
"""Generate executable cases and host vectors for manifest consistency."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = "mncs.rights.manifest_reference_consistency.v01"


def u64(value: int) -> dict:
    return {"integer": {"value": value, "type": {"bits": 64, "signed": False}}}


def request(function: str, arguments: list[dict]) -> dict:
    return {
        "schema_version": "0.1",
        "target": {"module": MODULE, "function": function},
        "arguments": arguments,
        "step_budget": 4096,
    }


def case(case_id: str, function: str, args: list[int], output: int) -> tuple[dict, dict]:
    return (
        {
            "id": case_id,
            "request": request(function, [u64(value) for value in args]),
            "expected": [u64(output)],
        },
        {
            "case_id": case_id,
            "function": function,
            "inputs": {"args": args},
            "output": output,
        },
    )


def build() -> tuple[list[dict], list[dict]]:
    same = [1, 1, 1, 1, 1, 1, 1]
    vectors = [
        case("reference:different-reference", "repeated_reference_metadata_conflict", [0, 0, 0, 0, 0, 0, 0], 0),
        case("reference:same-and-identical", "repeated_reference_metadata_conflict", same, 0),
        case("reference:same-digest-conflict", "repeated_reference_metadata_conflict", [1, 0, 1, 1, 1, 1, 1], 1),
        case("reference:same-identity-conflict", "repeated_reference_metadata_conflict", [1, 1, 0, 1, 1, 1, 1], 1),
        case("reference:same-evidence-state-conflict", "repeated_reference_metadata_conflict", [1, 1, 1, 0, 1, 1, 1], 1),
        case("reference:same-rights-state-conflict", "repeated_reference_metadata_conflict", [1, 1, 1, 1, 0, 1, 1], 1),
        case("reference:same-license-ref-conflict", "repeated_reference_metadata_conflict", [1, 1, 1, 1, 1, 0, 1], 1),
        case("reference:same-obligations-ref-conflict", "repeated_reference_metadata_conflict", [1, 1, 1, 1, 1, 1, 0], 1),
        case("reference:invalid-flag", "repeated_reference_metadata_conflict", [1, 2, 1, 1, 1, 1, 1], 2),
        case("compatibility:no-declarations", "compatibility_review_required", [0], 0),
        case("compatibility:one-declaration", "compatibility_review_required", [1], 0),
        case("compatibility:two-declarations", "compatibility_review_required", [2], 1),
        case("compatibility:bounded-many-declarations", "compatibility_review_required", [64], 1),
    ]
    return [item[0] for item in vectors], [item[1] for item in vectors]


def write() -> None:
    corpus_cases, golden_cases = build()
    corpus = {
        "schema_version": "0.1",
        "name": "rights-manifest-reference-consistency-v1",
        "cases": corpus_cases,
    }
    golden = {
        "schema_version": "0.1",
        "name": "rights-manifest-reference-consistency-v1",
        "source_module": MODULE,
        "cases": golden_cases,
    }
    for path, value in (
        (ROOT / "language/corpora/manifest-reference-consistency-corpus.json", corpus),
        (ROOT / "conformance/manifest-reference-consistency-golden-vectors.json", golden),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    write()
