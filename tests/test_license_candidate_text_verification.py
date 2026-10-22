"""Bounded verification of local bytes against candidate registry digests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from mncs_rights_provenance.cli import main

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(
    (ROOT / "schemas/v0.1/license-candidate-text-verification.schema.json").read_text()
)
VALIDATOR = Draft202012Validator(SCHEMA)


def _verify(
    identifier: str,
    repository_root: Path,
    capsys: pytest.CaptureFixture[str],
) -> tuple[int, dict]:
    with pytest.raises(SystemExit) as exit_result:
        main([
            "license-candidate",
            "verify-text",
            identifier,
            "--repository-root",
            str(repository_root),
        ])
    return exit_result.value.code, json.loads(capsys.readouterr().out)


def _candidate() -> dict:
    registry = json.loads(
        (ROOT / "src/mncs_rights_provenance/resources/license-candidates.json").read_text()
    )
    return next(
        item for item in registry["candidates"]
        if item["identifier"] == "LicenseRef-MNCS-Permissive-0.4"
    )


def _write_candidate(root: Path, content: bytes) -> Path:
    candidate_path = root / _candidate()["text_ref"]
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_path.write_bytes(content)
    return candidate_path


def _assert_schema(document: dict) -> None:
    assert list(VALIDATOR.iter_errors(document)) == []
    assert document["legal_conclusion"] == "NOT_MADE"
    assert document["verification_scope"] == "file-byte-digest-equality-only"


def test_cli_reports_digest_match_without_approving_candidate(capsys) -> None:
    candidate = _candidate()
    code, report = _verify(candidate["identifier"], ROOT, capsys)

    _assert_schema(report)
    assert code == 0
    assert report["status"] == "digest-match"
    assert report["expected_sha256"] == candidate["text_sha256"]
    assert report["observed_sha256"] == candidate["text_sha256"]
    assert report["content_evidence"] == "local-file-bytes"
    assert report["candidate_status"] == "draft-for-legal-review"
    assert report["adoption_status"] == "not-adopted"
    assert report["effective_grant"] is False


def test_cli_reports_mismatch_as_content_evidence_not_a_legal_conclusion(
    tmp_path: Path, capsys
) -> None:
    candidate = _candidate()
    _write_candidate(tmp_path, b"different bytes, same claimed local reference\n")

    code, report = _verify(candidate["identifier"], tmp_path, capsys)

    _assert_schema(report)
    assert code == 1
    assert report["status"] == "digest-mismatch"
    assert report["expected_sha256"] != report["observed_sha256"]
    assert report["candidate_status"] == "draft-for-legal-review"
    assert report["effective_grant"] is False


def test_cli_distinguishes_unknown_and_unavailable_candidate_text(capsys, tmp_path: Path) -> None:
    unknown_code, unknown = _verify("LicenseRef-Not-Registered", tmp_path, capsys)
    missing_code, missing = _verify(_candidate()["identifier"], tmp_path, capsys)

    _assert_schema(unknown)
    _assert_schema(missing)
    assert unknown_code == 1
    assert unknown["status"] == "unknown-candidate"
    assert unknown["expected_sha256"] is None
    assert missing_code == 1
    assert missing["status"] == "input-unavailable"
    assert missing["expected_sha256"] == _candidate()["text_sha256"]


def test_cli_bounds_candidate_text_reads_and_rejects_references_escaping_root(
    tmp_path: Path, capsys
) -> None:
    candidate = _candidate()
    oversized_root = tmp_path / "oversized"
    _write_candidate(oversized_root, b"x" * (64 * 1024 + 1))
    too_large_code, too_large = _verify(candidate["identifier"], oversized_root, capsys)

    root = tmp_path / "root"
    outside = tmp_path / "outside"
    _write_candidate(outside, b"outside-root bytes")
    root.mkdir()
    try:
        (root / "legal-candidates").symlink_to(outside / "legal-candidates")
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    unsafe_code, unsafe = _verify(candidate["identifier"], root, capsys)

    _assert_schema(too_large)
    _assert_schema(unsafe)
    assert too_large_code == 1
    assert too_large["status"] == "input-too-large"
    assert too_large["observed_sha256"] is None
    assert unsafe_code == 1
    assert unsafe["status"] == "unsafe-reference"
    assert unsafe["observed_sha256"] is None
