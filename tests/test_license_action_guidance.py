"""Bounded, action-oriented projections of indexed SPDX notice conditions."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from mncs_rights_provenance.cli import main
from mncs_rights_provenance.license_resolution import (
    license_action_guidance,
    resolve_license_expression,
)

ROOT = Path(__file__).resolve().parents[1]


def _leaves(node: dict) -> list[dict]:
    if "operator" in node:
        return [leaf for term in node["terms"] for leaf in _leaves(term)]
    return [node]


def test_mit_and_bsd_notice_conditions_are_scoped_to_distribution_form() -> None:
    mit_source = license_action_guidance("MIT", "redistribute-source")
    mit_binary = license_action_guidance("MIT", "redistribute-binary")
    bsd_source = license_action_guidance("BSD-2-Clause", "redistribute-source")
    bsd_binary = license_action_guidance("BSD-2-Clause", "redistribute-binary")

    assert mit_source["status"] == mit_binary["status"] == "reference-summary"
    assert mit_source["expression_tree"]["conditions"][0]["id"] == (
        "retain-copyright-and-permission-notice"
    )
    source_conditions = {
        item["id"]: item for item in bsd_source["expression_tree"]["conditions"]
    }
    binary_conditions = {
        item["id"]: item for item in bsd_binary["expression_tree"]["conditions"]
    }
    assert source_conditions["retain-notice-conditions-and-disclaimer"]["action_relation"] == (
        "operation-class-matches-trigger"
    )
    assert binary_conditions["reproduce-notice-conditions-and-disclaimer"]["action_relation"] == (
        "operation-class-matches-trigger"
    )
    assert binary_conditions["retain-notice-conditions-and-disclaimer"]["action_relation"] == (
        "other-trigger-preserved-for-review"
    )
    assert mit_binary["legal_conclusion"] == "NOT_MADE"


def test_compound_expression_keeps_and_or_structure_and_unknown_rights() -> None:
    result = license_action_guidance(
        "MIT OR (BSD-2-Clause AND LicenseRef-External)",
        "redistribute-binary",
    )
    tree = result["expression_tree"]

    assert result["status"] == "partial"
    assert tree["operator"] == "OR"
    assert tree["terms"][1]["operator"] == "AND"
    leaves = _leaves(tree)
    assert [item["license"] for item in leaves] == [
        "MIT", "BSD-2-Clause", "LicenseRef-External",
    ]
    assert leaves[2]["status"] == "unresolved-license-reference"
    assert leaves[1]["conditions"][1]["id"] == (
        "reproduce-notice-conditions-and-disclaimer"
    )
    assert result["unresolved_identifiers"] == ["LicenseRef-External"]
    assert result["ruleset"]["identity"].startswith("sha256:")
    assert result["ruleset"]["module"] == "mncs.rights.license_actions.v01"
    assert result["ruleset"]["module_ref"] == "language/rights_license_actions.mncs"
    assert result["license_resolver"]["version"] == "mncs.rights.license-resolution/4"
    assert result["license_resolver"]["identity"].startswith("sha256:")
    assert result["unresolved_conditions"] == []
    assert any("OR branch" in note for note in result["decision_notes"])
    assert "cross-license compatibility" in result["not_assessed"]


def test_apache_conditions_keep_their_triggers_instead_of_becoming_flags() -> None:
    result = license_action_guidance("Apache-2.0", "redistribute-binary")
    conditions = result["expression_tree"]["conditions"]
    by_id = {condition["id"]: condition for condition in conditions}

    assert by_id["provide-license-copy"]["action_relation"] == (
        "operation-class-matches-trigger"
    )
    assert by_id["mark-modified-files"]["when"] == "redistributed modified files"
    assert by_id["preserve-notice-attributions"]["when"] == (
        "the work includes a NOTICE file and the attribution applies"
    )
    assert result["status"] == "reference-summary"


def test_isc_and_zerobsd_preserve_their_distinct_notice_semantics() -> None:
    isc_terms = resolve_license_expression("ISC")["expression_tree"]
    isc_source = license_action_guidance("ISC", "redistribute-source")
    isc_binary = license_action_guidance("ISC", "redistribute-binary")
    zerobsd_terms = resolve_license_expression("0BSD")["expression_tree"]
    zerobsd = license_action_guidance("0BSD", "redistribute-binary")

    assert isc_terms["status"] == zerobsd_terms["status"] == "reference-summary"
    assert isc_terms["conditions"] == [{
        "id": "retain-copyright-and-permission-notice",
        "when": "all copies",
    }]
    assert "any-purpose-with-or-without-fee" in isc_terms["permissions"]
    assert isc_source["expression_tree"]["conditions"][0]["action_relation"] == (
        "operation-class-matches-trigger"
    )
    assert isc_binary["expression_tree"]["conditions"][0]["action_relation"] == (
        "operation-class-matches-trigger"
    )
    assert zerobsd_terms["conditions"] == []
    assert zerobsd["status"] == "reference-summary"
    assert zerobsd["expression_tree"]["conditions"] == []
    assert zerobsd["expression_tree"]["coverage"] == "indexed-conditions-only"
    assert zerobsd_terms["patent"]["status"] == (
        "no-express-patent-grant-in-identified-text"
    )


def test_zlib_conditions_keep_origin_source_and_binary_triggers_separate() -> None:
    source = license_action_guidance("Zlib", "redistribute-source")
    binary = license_action_guidance("Zlib", "redistribute-binary")
    terms = resolve_license_expression("Zlib")["expression_tree"]

    source_conditions = {
        item["id"]: item for item in source["expression_tree"]["conditions"]
    }
    binary_conditions = {
        item["id"]: item for item in binary["expression_tree"]["conditions"]
    }

    assert source["status"] == binary["status"] == "reference-summary"
    assert terms["permissions"] == ["use", "commercial-use", "alter", "redistribute"]
    assert source_conditions["do-not-misrepresent-origin"]["action_relation"] == (
        "operation-class-matches-trigger"
    )
    assert binary_conditions["do-not-misrepresent-origin"]["action_relation"] == (
        "operation-class-matches-trigger"
    )
    assert source_conditions["mark-altered-source"]["when"] == "altered source versions"
    assert source_conditions["mark-altered-source"]["action_relation"] == (
        "operation-class-matches-trigger"
    )
    assert binary_conditions["mark-altered-source"]["action_relation"] == (
        "other-trigger-preserved-for-review"
    )
    assert source_conditions["preserve-zlib-source-notice"]["when"] == (
        "source distribution"
    )
    assert binary_conditions["preserve-zlib-source-notice"]["action_relation"] == (
        "other-trigger-preserved-for-review"
    )
    assert terms["patent"]["status"] == "no-express-patent-grant-in-identified-text"


def test_unknown_license_and_exception_remain_unresolved() -> None:
    unknown = license_action_guidance("GPL-3.0-only", "redistribute-source")
    exception = license_action_guidance(
        "GPL-2.0-only WITH Classpath-exception-2.0", "redistribute-source"
    )

    assert unknown["status"] == "partial"
    assert unknown["expression_tree"]["status"] == "unknown-license-terms"
    assert exception["status"] == "partial"
    assert exception["expression_tree"]["status"] == "unknown-license-exception-terms"
    assert exception["expression_tree"].get("conditions") is None


def test_action_guidance_is_versioned_and_matches_schema() -> None:
    result = license_action_guidance("MIT OR BSD-2-Clause", "redistribute-source")
    schema = json.loads(
        (ROOT / "schemas/v0.1/license-action-guidance.schema.json").read_text()
    )
    Draft202012Validator.check_schema(schema)

    assert list(Draft202012Validator(schema).iter_errors(result)) == []


def test_partial_candidate_and_exception_results_also_match_schema() -> None:
    schema = json.loads(
        (ROOT / "schemas/v0.1/license-action-guidance.schema.json").read_text()
    )
    validator = Draft202012Validator(schema)

    for expression in (
        "LicenseRef-External",
        "LicenseRef-MNCS-Permissive-0.2",
        "GPL-2.0-only WITH Classpath-exception-2.0",
    ):
        result = license_action_guidance(expression, "redistribute-source")
        assert result["status"] == "partial"
        assert list(validator.iter_errors(result)) == []


def test_invalid_and_oversized_expressions_return_bounded_schema_results() -> None:
    schema = json.loads(
        (ROOT / "schemas/v0.1/license-action-guidance.schema.json").read_text()
    )
    validator = Draft202012Validator(schema)

    for expression in ("MIT OR", "MIT OR " + "LicenseRef-External OR " * 300):
        result = license_action_guidance(expression, "redistribute-binary")
        assert result["status"] == "unresolved"
        assert result["expression_tree"] is None
        assert list(validator.iter_errors(result)) == []


def test_repeated_query_reuses_the_same_ruleset_and_projection_identity() -> None:
    first = license_action_guidance("MIT AND BSD-2-Clause", "redistribute-binary")
    second = license_action_guidance("MIT AND BSD-2-Clause", "redistribute-binary")

    assert first == second
    assert first["ruleset"]["identity"] == second["ruleset"]["identity"]


def test_cli_exposes_action_guidance_as_structured_json(capsys) -> None:
    import pytest

    with pytest.raises(SystemExit) as exit_info:
        main([
            "action-guidance",
            "MIT OR LicenseRef-External",
            "--action",
            "redistribute-binary",
        ])
    report = json.loads(capsys.readouterr().out)

    assert exit_info.value.code == 0
    assert report["schema_version"] == "mncs.rights.license-action-guidance/1"
    assert report["status"] == "partial"
    assert report["legal_conclusion"] == "NOT_MADE"
