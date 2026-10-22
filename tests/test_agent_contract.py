"""Pin the rights agent contract to the normative MNCS cores."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CONTRACT = REPO / "AGENTS.md"

CORES = (
    "language/rights_policy.mncs",
    "language/source_license_status.mncs",
    "language/tools/gen_source_license_status_corpus.py",
    "language/corpora/source-license-status-corpus.json",
    "conformance/source-license-status-golden-vectors.json",
    "tests/test_source_license_status.py",
    "language/pressure_provenance.mncs",
    "language/check_projection.mncs",
    "language/rights_license_actions.mncs",
    "language/implementation_lineage.mncs",
    "language/corpora/implementation-lineage-corpus.json",
    "tests/test_implementation_lineage_core.py",
    "language/rights_agent_governance.mncs",
    "language/corpora/agent-governance-corpus.json",
    "tests/test_agent_governance.py",
    "language/corpora/",
    "language/run_backend_tests.sh",
    "scripts/rp_to_check.py",
    "specs/distributed-pressure.md",
)

SUPPORTING_CONTRACT_PATHS = (
    "docs/source-rights-policy-diagnostics.md",
    "schemas/v0.1/policy-diagnostic.schema.json",
    "src/mncs_rights_provenance/policy_diagnostics.py",
    "tests/test_policy_diagnostics.py",
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


def test_contract_names_existing_diagnostic_projection_paths():
    text = contract_text()
    for ref in SUPPORTING_CONTRACT_PATHS:
        assert ref in text, f"contract must mention {ref}"
        assert (REPO / ref).exists(), f"contract names missing {ref}"


def test_contract_claims_rights_authority_and_routes_language():
    text = contract_text()
    assert "owns **rights semantics**" in text
    assert "mncs-language" in text
    assert "development-pressure" in text
