"""Host gate over the rights-claims core: readable records in, verdicts out.

The gate reports; it never resolves. Revoked/Expired block, anything
needing a human reviews, all-Verified clears, and missing evidence
stays Unknown.
"""

from __future__ import annotations

import pytest

from mncs_rights_provenance import host_gate


def _verified(subject: str) -> dict:
    return {
        "subject": subject,
        "claimant": "epi13",
        "license": "Apache-2.0",
        "evidence": ["LICENSE"],
        "verified": True,
    }


def test_clear_when_all_verified():
    result = host_gate.evaluate_subjects([_verified("mncs-vm")], now=100)
    assert result["overall"] == "clear"
    assert result["subjects"] == {"mncs-vm": "clear"}


def test_unknown_evidence_reviews():
    result = host_gate.evaluate_subjects(
        [{"subject": "blob", "claimant": "x", "license": "MIT"}], now=100
    )
    assert result["overall"] == "review"
    assert result["subjects"] == {"blob": "review"}


def test_verified_without_evidence_is_not_clear():
    record = _verified("s")
    record["evidence"] = []
    result = host_gate.evaluate_subjects([record], now=100)
    assert result["subjects"] == {"s": "review"}


def test_revoked_blocks():
    record = _verified("s")
    record["revoked"] = True
    result = host_gate.evaluate_subjects([record], now=100)
    assert result["overall"] == "blocked"
    assert result["subjects"] == {"s": "blocked"}


def test_expired_blocks():
    record = _verified("s")
    record["expires"] = 50
    result = host_gate.evaluate_subjects([record], now=100)
    assert result["overall"] == "blocked"


def test_contested_reviews():
    record = _verified("s")
    record["contested"] = True
    result = host_gate.evaluate_subjects([record], now=100)
    assert result["overall"] == "review"
    assert result["subjects"] == {"s": "review"}


def test_watched_subject_without_claims_reviews():
    result = host_gate.evaluate_subjects(
        [_verified("a")], now=100, subjects=["a", "ghost"]
    )
    assert result["overall"] == "review"
    assert result["subjects"]["ghost"] == "review"
    assert result["subjects"]["a"] == "clear"


def test_conflicting_claims_review_never_resolve():
    first = _verified("s")
    second = _verified("s")
    second["redistribute"] = True
    result = host_gate.evaluate_subjects([first, second], now=100)
    assert result["overall"] == "review"
    assert result["conflicts"], "expected a reported conflict"


def test_malformed_record_raises():
    with pytest.raises(host_gate.GateInputError):
        host_gate.evaluate_subjects(["not-a-mapping"], now=100)
