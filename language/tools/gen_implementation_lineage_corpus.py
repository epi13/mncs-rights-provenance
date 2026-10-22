#!/usr/bin/env python3
"""Generate executable cases and host golden vectors for the implementation-lineage core."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = "mncs.rights.implementation_lineage.v01"
REPRESENTATIONS = (
    "MachineNative", "HostLanguage", "Mixed", "Other", "Unknown",
)
ORIGINS = (
    "NewLocal", "Migrated", "InheritedExternal", "Generated", "Mixed", "Unknown",
)
EVIDENCE_STATES = (
    "DirectlyObserved", "Declared", "Inferred", "VerifiedAttestation",
    "UnverifiedAttestation", "Unavailable",
)
CLASSIFICATION_STATUSES = ("Known", "Unknown", "Invalid")
LINEAGE_STATUSES = ("Partial", "Unknown", "Invalid")


def enum(type_name: str, variants: tuple[str, ...], value: str) -> dict:
    return {
        "finite": {
            "type_identity": f"mncs:0.2:finite-type:{MODULE}::{type_name}",
            "variant_identity": f"mncs:0.2:finite-variant:{MODULE}::{type_name}::{value}",
            "discriminant": variants.index(value),
        }
    }


def u64(value: int) -> dict:
    return {"integer": {"value": value, "type": {"bits": 64, "signed": False}}}


def request(function: str, arguments: list[dict]) -> dict:
    return {
        "schema_version": "0.1",
        "target": {"module": MODULE, "function": function},
        "arguments": arguments,
        "step_budget": 4096,
    }


def component_case(
    case_id: str,
    representation: str,
    origin: str,
    evidence_state: str,
    has_evidence: int,
    has_verified_verifier: int,
    expected: str,
) -> tuple[dict, dict]:
    arguments = [
        enum("Representation", REPRESENTATIONS, representation),
        enum("Origin", ORIGINS, origin),
        enum("EvidenceState", EVIDENCE_STATES, evidence_state),
        u64(has_evidence),
        u64(has_verified_verifier),
    ]
    return (
        {
            "id": case_id,
            "request": request("implementation_component_status", arguments),
            "expected": [enum("ClassificationStatus", CLASSIFICATION_STATUSES, expected)],
        },
        {
            "case_id": case_id,
            "function": "implementation_component_status",
            "inputs": {
                "args": [
                    REPRESENTATIONS.index(representation),
                    ORIGINS.index(origin),
                    EVIDENCE_STATES.index(evidence_state),
                    has_evidence,
                    has_verified_verifier,
                ]
            },
            "output": expected,
        },
    )


def aggregate_case(case_id: str, known: int, total: int, expected: str) -> tuple[dict, dict]:
    arguments = [u64(known), u64(total)]
    return (
        {
            "id": case_id,
            "request": request("implementation_lineage_status", arguments),
            "expected": [enum("LineageStatus", LINEAGE_STATUSES, expected)],
        },
        {
            "case_id": case_id,
            "function": "implementation_lineage_status",
            "inputs": {"args": [known, total]},
            "output": expected,
        },
    )


def build() -> tuple[list[dict], list[dict]]:
    pairs = [
        component_case("component:native-new-local-declared", "MachineNative", "NewLocal", "Declared", 1, 0, "Known"),
        component_case("component:native-migrated-inferred", "MachineNative", "Migrated", "Inferred", 1, 0, "Known"),
        component_case("component:host-inherited-external", "HostLanguage", "InheritedExternal", "Declared", 1, 0, "Known"),
        component_case("component:generated-inferred", "MachineNative", "Generated", "Inferred", 1, 0, "Known"),
        component_case("component:mixed-representation", "Mixed", "Unknown", "DirectlyObserved", 1, 0, "Known"),
        component_case("component:both-classifications-unknown", "Unknown", "Unknown", "Declared", 1, 0, "Unknown"),
        component_case("component:unavailable-preserves-unknown", "Unknown", "Unknown", "Unavailable", 0, 0, "Unknown"),
        component_case("component:unavailable-cannot-claim-classification", "MachineNative", "Unknown", "Unavailable", 0, 0, "Invalid"),
        component_case("component:unavailable-cannot-carry-evidence", "Unknown", "Unknown", "Unavailable", 1, 0, "Invalid"),
        component_case("component:declared-requires-evidence", "MachineNative", "Migrated", "Declared", 0, 0, "Invalid"),
        component_case("component:verified-attestation-has-verifier-reference", "MachineNative", "Migrated", "VerifiedAttestation", 1, 1, "Known"),
        component_case("component:verified-attestation-needs-verifier-reference", "MachineNative", "Migrated", "VerifiedAttestation", 1, 0, "Invalid"),
        component_case("component:unverified-attestation-remains-known-claim", "HostLanguage", "InheritedExternal", "UnverifiedAttestation", 1, 0, "Known"),
        component_case("component:binary-flags-are-validated", "MachineNative", "Migrated", "Declared", 2, 0, "Invalid"),
        aggregate_case("lineage:known-subset-is-partial", 1, 3, "Partial"),
        aggregate_case("lineage:no-known-components-is-unknown", 0, 3, "Unknown"),
        aggregate_case("lineage:empty-is-unknown", 0, 0, "Unknown"),
        aggregate_case("lineage:known-count-cannot-exceed-total", 2, 1, "Invalid"),
    ]
    return [pair[0] for pair in pairs], [pair[1] for pair in pairs]


def write() -> None:
    corpus_cases, golden_cases = build()
    corpus = {
        "schema_version": "0.1",
        "name": "rights-implementation-lineage-v1",
        "cases": corpus_cases,
    }
    golden = {
        "schema_version": "0.1",
        "name": "rights-implementation-lineage-v1",
        "source_module": MODULE,
        "cases": golden_cases,
    }
    outputs = (
        (ROOT / "language/corpora/implementation-lineage-corpus.json", corpus),
        (ROOT / "conformance/implementation-lineage-golden-vectors.json", golden),
    )
    for path, value in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    write()
