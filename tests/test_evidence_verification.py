"""Evidence verification preserves version and interpretation boundaries."""

from __future__ import annotations

import json
from pathlib import Path

from mncs_rights_provenance.cli import main
from mncs_rights_provenance.evidence import (
    EvidenceRecord,
    compute_evidence_digest,
    seal_evidence_record,
)


def _forge_license_evidence() -> dict:
    identity = "mncs-forge://license-evidence/" + "a" * 32
    record = {
        "schema_version": "0.3.0",
        "evidence_id": identity,
        "kind": "forge-analysis",
        "producer": {
            "producer": "mncs-forge",
            "recordKind": "LicenseEvidence",
            "schemaVersion": "0.3.0",
            "stableId": identity,
        },
        "subject": {
            "artifact_refs": [{"id": "project:fixture", "role": "subject"}]
        },
        "scan_inputs": [
            {
                "path": "pyproject.toml",
                "status": "observed",
                "resolved_path": "pyproject.toml",
                "sha256": "b" * 64,
                "byte_length": 48,
            }
        ],
        "observations": [
            {
                "name": "pyproject.toml_license_declaration",
                "value": {"declared": "Apache-2.0"},
                "source_ref": {
                    "path": "pyproject.toml",
                    "resolved_path": "pyproject.toml",
                    "selector": "/project/license",
                    "sha256": "b" * 64,
                },
            }
        ],
        "claims": [
            {
                "claim_type": "license-identification",
                "confidence": "heuristic",
                "spdx_expression": "Apache-2.0",
            }
        ],
        "context": {"timestamp": "2026-10-22T00:00:00Z"},
        "limitations": [
            "Metadata is evidence supplied to Forge, not independent legal review."
        ],
    }
    from mncs_rights_provenance.evidence import compute_evidence_digest

    record["content_digest"] = compute_evidence_digest(record)
    return record


def _verify(tmp_path: Path, capsys, record: dict) -> tuple[int, dict]:
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(json.dumps(record), encoding="utf-8")
    try:
        main(["evidence", "verify", str(evidence_path)])
    except SystemExit as exc:
        exit_code = int(exc.code or 0)
    else:  # pragma: no cover - the CLI contract exits with its command result
        exit_code = 0
    return exit_code, json.loads(capsys.readouterr().out)


def test_forge_license_evidence_digest_is_verified_without_claim_interpretation(
    tmp_path: Path, capsys,
) -> None:
    exit_code, result = _verify(tmp_path, capsys, _forge_license_evidence())

    assert exit_code == 0
    assert result["schema_version"] == "mncs.rights-provenance.evidence-verification/1"
    assert result["record_schema_version"] == "0.3.0"
    assert result["record_kind"] == "forge-analysis"
    assert result["declared_producer"] == "mncs-forge"
    assert result["declared_producer_record_kind"] == "LicenseEvidence"
    assert result["content_digest_matches"] is True
    assert result["verification_scope"] == "canonical-content-digest-only"
    assert result["record_interpretation"] == "uninterpreted-external-record"
    assert "claims" not in result
    assert result["legal_conclusion"] == "NOT_MADE"


def test_external_digest_mismatch_does_not_expose_claim_summary(
    tmp_path: Path, capsys,
) -> None:
    record = _forge_license_evidence()
    record["claims"][0]["confidence"] = "verified"

    exit_code, result = _verify(tmp_path, capsys, record)

    assert exit_code == 1
    assert result["content_digest_matches"] is False
    assert result["record_interpretation"] == "uninterpreted"
    assert "claims" not in result
    assert result["legal_conclusion"] == "NOT_MADE"


def test_rights_evidence_keeps_its_existing_claim_summary(
    tmp_path: Path, capsys,
) -> None:
    record = seal_evidence_record(
        EvidenceRecord(
            evidence_id="rights-evidence:fixture",
            kind="other",
            producer={"producer": "mncs-rights-provenance"},
            subject={"artifact_refs": [{"id": "artifact:fixture", "role": "subject"}]},
            claims=[{"claim_type": "origin-classification-proposal", "confidence": "low"}],
        )
    ).to_dict()

    exit_code, result = _verify(tmp_path, capsys, record)

    assert exit_code == 0
    assert result["record_schema_version"] == "0.2.0"
    assert result["record_interpretation"] == "rights-evidence-record/0.2.0"
    assert result["claims"] == [
        {"claim_type": "origin-classification-proposal", "confidence": "low"}
    ]
    assert result["verification_scope"] == "canonical-content-digest-only"
    assert result["legal_conclusion"] == "NOT_MADE"


def test_digest_match_does_not_make_malformed_rights_record_valid(
    tmp_path: Path, capsys,
) -> None:
    record = {
        "schema_version": "0.2.0",
        "evidence_id": "rights-evidence:malformed",
        "kind": "other",
        "producer": {},
    }
    record["content_digest"] = compute_evidence_digest(record)

    exit_code, result = _verify(tmp_path, capsys, record)

    assert exit_code == 2
    assert result["content_digest_matches"] is True
    assert result["record_interpretation"] == "invalid-rights-evidence-record"
    assert "claims" not in result
    assert result["legal_conclusion"] == "NOT_MADE"
