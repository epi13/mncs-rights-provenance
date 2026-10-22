"""Evidence-linked diagnostics for unresolved source-rights policy inputs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from mncs_rights_provenance.check_projection import project_report_to_check
from mncs_rights_provenance.cli import main as cli_main
from mncs_rights_provenance.gates import ENFORCEMENT_DISABLED
from mncs_rights_provenance.manifest import compute_manifest_identity
from mncs_rights_provenance.policy import evaluate_policy
from mncs_rights_provenance.policy_input import policy_input_from_manifest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas/v0.1/policy-diagnostic.schema.json"


def _document(sources: list[dict]) -> dict:
    return {
        "provenance": {"origin_classification": "origin-uncertain"},
        "rights": {
            "copyright_status": "unresolved",
            "rights_basis": "unknown-needs-review",
            "third_party_material": "present",
            "sources": sources,
        },
        "review": {},
    }


def _diagnostics(sources: list[dict], *, enforcements: dict | None = None) -> dict:
    policy_input = policy_input_from_manifest(_document(sources))
    return evaluate_policy(policy_input, enforcements=enforcements).to_dict()


def _validate_diagnostics(report: dict) -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    diagnostics = report["diagnostics"]
    errors = [error.message for item in diagnostics for error in validator.iter_errors(item)]
    assert errors == []


def test_unverified_declaration_retains_external_evidence_as_a_review_diagnostic() -> None:
    report = _diagnostics([{
        "kind": "package",
        "reference": "external:package/1",
        "license": "MIT",
        "license_status": "incompatible",
        "confidence": "heuristic",
        "evidence": [{
            "kind": "external-record",
            "reference": "catalog:package/1",
            "sha256": "a" * 64,
        }],
    }])

    diagnostic, = report["diagnostics"]
    source, = diagnostic["source_declarations"]
    assert diagnostic["code"] == "source-license-status-unverified"
    assert diagnostic["gate"] == "unknown_source_license"
    assert diagnostic["severity"] == "review"
    assert diagnostic["evidence_state"] == "declared-unverified"
    assert source["declared_license_status"] == "incompatible"
    assert source["declared_confidence"] == "heuristic"
    assert source["evidence_references"][0]["reference"] == "catalog:package/1"
    assert "authorized assessment" in diagnostic["remedy"]
    assert diagnostic["legal_conclusion"] == "NOT_MADE"
    assert report["gate_results"]
    gate_severity = {
        item["gate"]: item["severity"] for item in report["gate_results"]
    }
    assert gate_severity["no_incompatible_third_party_license"] == "none"
    assert gate_severity["unknown_source_license"] == "review"
    _validate_diagnostics(report)


def test_conflicting_status_declarations_are_explained_without_incompatibility_claim() -> None:
    report = _diagnostics([
        {
            "kind": "package",
            "reference": "external:package/1",
            "license": "MIT",
            "license_status": "compatible",
            "evidence": [{"kind": "external-record", "reference": "catalog:a"}],
        },
        {
            "kind": "package",
            "reference": "external:package/1",
            "license": "MIT",
            "license_status": "incompatible",
            "evidence": [{"kind": "external-record", "reference": "catalog:b"}],
        },
        {
            "kind": "package",
            "reference": "external:package/1",
            "license_status": "unknown",
        },
    ])

    by_code = {item["code"]: item for item in report["diagnostics"]}
    conflict = by_code["source-license-declarations-conflict"]
    group, = conflict["conflicts"]
    assert group["source_reference"] == "external:package/1"
    assert group["declared_statuses"] == ["compatible", "incompatible"]
    assert {item["reference"] for item in group["evidence_references"]} == {
        "catalog:a", "catalog:b",
    }
    assert conflict["evidence_state"] == "declared-unverified"
    assert "does not establish legal incompatibility" in conflict["message"]
    assert conflict["legal_conclusion"] == "NOT_MADE"
    gate_severity = {
        item["gate"]: item["severity"] for item in report["gate_results"]
    }
    assert gate_severity["no_incompatible_third_party_license"] == "none"
    assert gate_severity["no_contradictory_license_evidence"] == "review"
    _validate_diagnostics(report)


def test_diagnostic_evidence_and_output_stay_bounded() -> None:
    sources = [
        {
            "kind": "package",
            "reference": f"external:package/{index}",
            "license_status": "unknown",
            "evidence": [
                {"kind": "external-record", "reference": f"catalog:{index}/{ref}"}
                for ref in range(10)
            ],
        }
        for index in range(18)
    ]
    report = _diagnostics(sources)

    diagnostic, = report["diagnostics"]
    assert len(diagnostic["source_declarations"]) == 16
    assert diagnostic["omitted_source_declarations"] == 2
    assert all(len(item["evidence_references"]) <= 8 for item in diagnostic["source_declarations"])
    assert all(
        item["omitted_evidence_reference_entries"] == 2
        for item in diagnostic["source_declarations"]
    )
    _validate_diagnostics(report)


def test_disabled_unverified_gate_does_not_emit_a_policy_diagnostic() -> None:
    report = _diagnostics(
        [{"kind": "package", "reference": "external:package/1", "license_status": "unknown"}],
        enforcements={"unknown_source_license": ENFORCEMENT_DISABLED},
    )
    assert "source-license-status-unverified" not in {
        item["code"] for item in report["diagnostics"]
    }


def test_validate_cli_emits_the_versioned_actionable_source_diagnostic(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest = {
        "schema_version": "0.3.0",
        "artifact": {"id": "test:policy-diagnostic", "class": "source-code"},
        "provenance": {
            "origin_classification": "human-authored",
            "participants": [{"type": "human", "role": "author"}],
            "process_evidence": [],
        },
        "rights": {
            "distribution_license": "Apache-2.0",
            "copyright_status": "third-party-licensed",
            "rights_basis": "third-party-license",
            "third_party_material": "present",
            "sources": [{
                "kind": "package",
                "reference": "external:package/1",
                "license_status": "incompatible",
                "license": "MIT",
                "confidence": "heuristic",
                "evidence": [{
                    "kind": "external-record",
                    "reference": "catalog:package/1",
                }],
            }],
        },
        "review": {
            "technical_validation": "passed",
            "provenance_validation": "passed",
            "human_acceptance": "accepted",
        },
    }
    manifest["manifest_identity"] = compute_manifest_identity(manifest)
    path = tmp_path / "rights-manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(SystemExit) as result:
        cli_main(["validate", str(path), "--findings-are-not-failures"])

    report = json.loads(capsys.readouterr().out)
    diagnostic, = report["diagnostics"]
    assert result.value.code == 0
    assert report["structural_valid"] is True
    assert report["outcome"] == "review-required"
    assert report["legal_conclusion"] == "NOT_MADE"
    assert diagnostic["code"] == "source-license-status-unverified"
    assert diagnostic["source_declarations"][0]["evidence_references"][0]["reference"] == (
        "catalog:package/1"
    )
    _validate_diagnostics(report)
    check, check_error = project_report_to_check(report)
    assert check_error is None and check is not None
    assert check["verdict"] == "UNKNOWN"
    assert check["rights_diagnostics"] == report["diagnostics"]
    assert any("authorized assessment" in item for item in check["unresolved"])
