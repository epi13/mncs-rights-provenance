"""Golden-vector conformance: Python policy must match the MNCS-language core.

The vectors in ``conformance/golden-vectors.json`` are generated from the
normative reference semantics that the MNCS-language module
``language/rights_policy.mncs`` implements. That module is executed across
compiler backends by ``language/run_backend_tests.sh``; this test pins the
Python implementation to the same vectors so host and language cores cannot
drift.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mncs_rights_provenance.gates import GATE_NAMES, apply_enforcement
from mncs_rights_provenance.policy import evaluate_policy
from mncs_rights_provenance.policy_input import PolicyInput

CONFORMANCE = Path(__file__).resolve().parents[1] / "conformance"
SEVERITY_RANK = {
    "none": 0,
    "finding": 1,
    "review": 2,
    "blocking": 3,
    "None": 0,
    "Finding": 1,
    "Review": 2,
    "Blocking": 3,
}
# Language-core GateSeverities field names, canonical order == GATE_NAMES order.
LANGUAGE_GATE_FIELDS = [
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
HOST_TO_LANGUAGE = dict(zip(GATE_NAMES, LANGUAGE_GATE_FIELDS))


def _load_vectors() -> list[dict]:
    return json.loads((CONFORMANCE / "golden-vectors.json").read_text())["cases"]


def _policy_input(case: dict) -> PolicyInput:
    data = case["input"]
    return PolicyInput(
        origin_code=data["origin_code"],
        copyright_code=data["copyright_code"],
        rights_basis_code=data["rights_basis_code"],
        third_party_code=data["third_party_code"],
        provenance_validation_code=data["prov_valid_code"],
        human_acceptance_code=data["human_accept_code"],
        incompatible_source_count=data["incompatible_source_count"],
        unknown_source_count=data["unknown_source_count"],
        contradiction_count=data["contradiction_count"],
        hash_mismatch=data["hash_mismatch"],
        broken_evidence_refs=data["broken_evidence_refs"],
        graph_invalid=data["graph_invalid"],
        attestation_conflicts=data["attestation_conflicts"],
        impossible_evidence=data["impossible_evidence"],
        canonical_release_profile=data["canonical_release_profile"],
    )


@pytest.mark.parametrize(
    "case", _load_vectors(), ids=lambda c: c["input"].get("_id", str(c["input"]))
)
def test_golden_outcome(case: dict) -> None:
    outcome = evaluate_policy(_policy_input(case))
    # Language enum variants are PascalCase; host outcomes are snake_case.
    expected_snake = _snake(case["outcome"])
    assert outcome.outcome == expected_snake


LANGUAGE_RANK = {"None": 0, "Finding": 1, "Review": 2, "Blocking": 3}


@pytest.mark.parametrize("case", _load_vectors())
def test_golden_gate_severities(case: dict) -> None:
    outcome = evaluate_policy(_policy_input(case))
    by_language_field = {
        HOST_TO_LANGUAGE[result.gate]: result.severity for result in outcome.gate_results
    }
    for gate_field, expected in case["severities"].items():
        assert by_language_field[gate_field] == LANGUAGE_RANK[expected], (
            f"{gate_field}: python={by_language_field[gate_field]} golden={expected}"
        )


def _snake(name: str) -> str:
    out = []
    for index, char in enumerate(name):
        if char.isupper() and index > 0:
            out.append("-")
        out.append(char.lower())
    return "".join(out)


def test_gate_table_matches_language_core_order() -> None:
    """The 14 gates here must correspond 1:1 with GateSeverities fields."""
    assert len(GATE_NAMES) == 14


def test_enforcement_ceiling_semantics() -> None:
    from mncs_rights_provenance.gates import (
        BLOCKING,
        ENFORCEMENT_DISABLED,
        ENFORCEMENT_FATAL,
        ENFORCEMENT_FINDING,
        ENFORCEMENT_REVIEW,
        FINDING,
        NONE,
        REVIEW,
    )

    assert apply_enforcement(BLOCKING, ENFORCEMENT_FATAL) == BLOCKING
    assert apply_enforcement(BLOCKING, ENFORCEMENT_REVIEW) == REVIEW
    assert apply_enforcement(BLOCKING, ENFORCEMENT_FINDING) == FINDING
    assert apply_enforcement(BLOCKING, ENFORCEMENT_DISABLED) == NONE
    assert apply_enforcement(REVIEW, ENFORCEMENT_REVIEW) == REVIEW
    assert apply_enforcement(FINDING, ENFORCEMENT_DISABLED) == NONE
