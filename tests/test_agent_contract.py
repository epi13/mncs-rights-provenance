"""Pin the rights agent contract to the normative MNCS cores."""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CONTRACT = REPO / "AGENTS.md"

CORES = (
    "language/rights_policy.mncs",
    "language/pressure_provenance.mncs",
    "language/check_projection.mncs",
    "language/corpora/",
    "language/run_backend_tests.sh",
    "scripts/rp_to_check.py",
    "specs/distributed-pressure.md",
)


def contract_text() -> str:
    assert CONTRACT.is_file(), "AGENTS.md (agent execution contract) is missing"
    return CONTRACT.read_text(encoding="utf-8")


def test_contract_names_existing_paths():
    text = contract_text()
    assert CORES, "core list must not be empty"
    for ref in CORES:
        assert ref in text, f"contract must mention {ref}"
        assert (REPO / ref).exists(), f"contract names missing {ref}"


def test_contract_claims_rights_authority_and_routes_language():
    text = contract_text()
    assert "owns **rights semantics**" in text
    assert "mncs-language" in text
    assert "development-pressure" in text
