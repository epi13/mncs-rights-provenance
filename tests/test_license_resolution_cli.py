"""On-demand SPDX term resolution remains structured and evidence-aware."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from mncs_rights_provenance.cli import main

ROOT = Path(__file__).resolve().parents[1]


def _resolve(expression: str, capsys: pytest.CaptureFixture[str]) -> dict:
    with pytest.raises(SystemExit) as result:
        main(["license-resolve", expression])
    assert result.value.code == 0
    return json.loads(capsys.readouterr().out)


def test_license_resolution_cli_outputs_schema_for_known_and_compound_terms(capsys) -> None:
    schema = json.loads((ROOT / "schemas/v0.1/license-resolution.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)

    for expression in (
        "Apache-2.0",
        "MIT OR (BSD-2-Clause AND Zlib)",
        "GPL-2.0-only WITH Classpath-exception-2.0",
        "LicenseRef-External",
        "LicenseRef-MNCS-Permissive-0.1",
        "LicenseRef-MNCS-Permissive-0.3",
    ):
        result = _resolve(expression, capsys)
        assert list(validator.iter_errors(result)) == []
        assert result["expression"] == expression
        assert result["expression_evidence"] == ("caller-supplied-declaration-unverified")
        assert result["compatibility"]["status"] == "unknown"


@pytest.mark.parametrize("expression", ["GPL-3.0-only", "MIT AND", "A" * 4097])
def test_unknown_and_unresolved_expressions_are_successful_machine_results(
    expression: str, capsys: pytest.CaptureFixture[str]
) -> None:
    schema = json.loads((ROOT / "schemas/v0.1/license-resolution.schema.json").read_text())
    result = _resolve(expression, capsys)

    assert list(Draft202012Validator(schema).iter_errors(result)) == []
    assert result["status"] in {"partial", "unresolved"}
    assert result["compatibility"]["status"] == "unknown"
    if len(expression) > 4096:
        assert result["status"] == "unresolved"
        assert result["expression"] == expression[:256]
        assert "exceeds the bounded resolver input size" in result["reason"]


def test_candidate_expression_remains_non_effective_and_unverified(capsys) -> None:
    expression = "LicenseRef-MNCS-Permissive-0.1 OR LicenseRef-MNCS-Permissive-0.2"
    result = _resolve(expression, capsys)
    leaves = result["expression_tree"]["terms"]

    assert result["status"] == "partial"
    assert [item["status"] for item in leaves] == [
        "candidate-unapproved",
        "candidate-unapproved",
    ]
    assert all(item["effective_grant"] is False for item in leaves)
    assert all("permissions" not in item for item in leaves)
    assert len(result["candidate_review_details"]) == 2
    assert result["candidate_references"] == [
        "LicenseRef-MNCS-Permissive-0.1",
        "LicenseRef-MNCS-Permissive-0.2",
    ]
