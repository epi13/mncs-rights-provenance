"""Keep the host governance-profile parser aligned with its MNCS core corpus."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from mncs_rights_provenance.agent_context import (
    _validate_governance,
    build_agent_context,
)

ROOT = Path(__file__).resolve().parents[1]


def _governance() -> dict:
    return json.loads((ROOT / "governance/agent-governance.json").read_text())


def test_host_governance_validation_matches_native_execution_corpus() -> None:
    corpus = json.loads(
        (ROOT / "language/corpora/agent-governance-corpus.json").read_text()
    )

    assert len(corpus["cases"]) == 33
    for case in corpus["cases"]:
        decision = case["expected"][0]["finite"]["variant_identity"].rsplit("::", 1)[1]
        supported, section, key, value = case["id"].split(":", 3)
        assert supported in {"supported", "review"}
        assert decision == ("Supported" if supported == "supported" else "NeedsReview")

        profile = copy.deepcopy(_governance())
        profile[section][key] = value
        clean, errors = _validate_governance(profile)

        assert (clean is not None) is (supported == "supported"), case["id"]
        if supported == "review":
            assert errors == [f"governance {section}.{key} is unsupported"]


def test_unknown_policy_value_stays_unavailable_in_agent_context() -> None:
    profile = _governance()
    profile["agent_governance"]["independent_implementation"] = "future-auto-allow"
    context = build_agent_context(
        json.loads((ROOT / "RIGHTS.json").read_text()),
        profile,
        binding={
            "authorized": True,
            "profile_id": "mncs-rights-provenance/native-open@0.1.0",
            "authority": {
                "issuer": "mncs-environment",
                "basis": "explicit-environment-owner-binding",
                "source_ref": ".mncs/environment.json#/rights_context",
                "scope": ["mncs-environment", "mncs-rights-provenance"],
            },
            "context_budget_bytes": 8192,
        },
    )

    assert context["governance"]["status"] == "unavailable"
    assert context["governance"]["rules"] is None
    assert "agent-governance-unavailable" in {
        item["code"] for item in context["diagnostics"]
    }
