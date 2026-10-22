"""Evidence-aware source-license classification and release-policy projection."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from mncs_rights_provenance.cli import main as cli_main
from mncs_rights_provenance.manifest import compute_manifest_identity
from mncs_rights_provenance.policy import evaluate_policy
from mncs_rights_provenance.policy_input import (
    _classify_source_license_status,
    count_license_contradictions,
    policy_input_from_manifest,
)

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "language/corpora/source-license-status-corpus.json"
GOLDEN = ROOT / "conformance/source-license-status-golden-vectors.json"
PROGRAM = ROOT / "language/source_license_status.mncs"


def load_corpus() -> dict:
    return json.loads(CORPUS.read_text(encoding="utf-8"))


def load_golden() -> dict:
    return json.loads(GOLDEN.read_text(encoding="utf-8"))


def test_generated_corpus_and_golden_are_deterministic() -> None:
    from language.tools.gen_source_license_status_corpus import build

    corpus_cases, golden_cases = build()
    assert corpus_cases == load_corpus()["cases"]
    assert golden_cases == load_golden()["cases"]
    assert len(corpus_cases) == len(golden_cases) == 8


def test_host_mirror_matches_every_normative_golden_vector() -> None:
    vectors = load_golden()
    assert vectors["source_module"] == "mncs.rights.source_license_status.v01"
    for vector in vectors["cases"]:
        actual = _classify_source_license_status(
            vector["status"], evidence_verified=vector["evidence_state"] == "verified"
        )
        assert actual == vector["assessment"], vector["case_id"]


def _mncs_binary() -> str:
    override = os.environ.get("MNCS_BIN")
    binary = override if override and Path(override).is_file() else shutil.which("mncs")
    if not binary:
        pytest.skip("no MNCS experiment runner (MNCS_BIN or PATH)")
    probe = subprocess.run(
        [binary, "experiment", "run"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    runner_signals = (
        "--backend is required",
        "experiment plan/run requires an MNCS source path",
    )
    if probe.returncode != 0 and not any(signal in probe.stderr for signal in runner_signals):
        pytest.skip("configured mncs command does not provide the experiment runner")
    return binary


def _run(backend: str) -> list[dict]:
    with tempfile.TemporaryDirectory(prefix="mncs-source-license-status-") as temporary:
        output = Path(temporary) / "output"
        process = subprocess.run(
            [
                _mncs_binary(), "experiment", "run", str(PROGRAM),
                "--backend", backend, "--corpus", str(CORPUS),
                "--output-dir", str(output),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert process.returncode == 0, process.stderr[-2000:]
        return json.loads((output / "result.json").read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize("backend", ["mncs-research-bytecode", "mncs-portable-wasm-mvp"])
def test_live_native_execution_matches_all_corpus_expectations(backend: str) -> None:
    cases = _run(backend)
    assert len(cases) == len(load_corpus()["cases"])
    failed = [case["case_id"] for case in cases if not case.get("expectation_met")]
    assert failed == []


@pytest.mark.parametrize(
    "status", ["compatible", "incompatible", "unknown", "not-applicable"]
)
def test_manifest_status_and_external_metadata_remain_unverified(status: str) -> None:
    source = {
        "kind": "package",
        "reference": "external:package/1",
        "license_status": status,
        "confidence": "heuristic",
        "evidence": [{"kind": "external-record", "reference": "catalog:package/1"}],
    }
    document = {
        "provenance": {"origin_classification": "origin-uncertain"},
        "rights": {"sources": [source]},
        "review": {},
    }

    normalized = policy_input_from_manifest(document)
    assert normalized.incompatible_source_count == 0
    assert normalized.unknown_source_count == 1

    outcome = evaluate_policy(normalized)
    by_gate = {item.gate: item.severity for item in outcome.gate_results}
    assert by_gate["no_incompatible_third_party_license"] == 0
    assert by_gate["unknown_source_license"] == 2
    assert outcome.outcome != "blocked"


def test_verified_statuses_have_distinct_policy_classifications() -> None:
    assert _classify_source_license_status(
        "incompatible", evidence_verified=True
    ) == "verified-incompatible"
    assert _classify_source_license_status(
        "unknown", evidence_verified=True
    ) == "verified-unknown"
    assert _classify_source_license_status(
        "compatible", evidence_verified=True
    ) == "verified-compatible"
    assert _classify_source_license_status(
        "not-applicable", evidence_verified=True
    ) == "verified-not-applicable"


def test_conflicting_statuses_require_review_without_claiming_incompatibility() -> None:
    rights = {"sources": [
        {
            "reference": "external:package/1",
            "license_status": "compatible",
            "license": "MIT",
        },
        {
            "reference": "external:package/1",
            "license_status": "incompatible",
            "license": "MIT",
        },
        {
            "reference": "external:package/1",
            "license_status": "unknown",
        },
    ]}
    document = {
        "provenance": {"origin_classification": "origin-uncertain"},
        "rights": rights,
        "review": {},
    }

    assert count_license_contradictions(rights) == 1
    normalized = policy_input_from_manifest(document)
    assert normalized.incompatible_source_count == 0
    assert normalized.unknown_source_count == 3
    assert normalized.contradiction_count == 1

    outcome = evaluate_policy(normalized)
    by_gate = {item.gate: item.severity for item in outcome.gate_results}
    assert by_gate["no_incompatible_third_party_license"] == 0
    assert by_gate["no_contradictory_license_evidence"] == 2
    assert by_gate["unknown_source_license"] == 2
    assert outcome.outcome != "blocked"


def test_unknown_status_does_not_contradict_a_single_determinate_status() -> None:
    assert count_license_contradictions({"sources": [
        {"reference": "external:package/1", "license_status": "compatible"},
        {"reference": "external:package/1", "license_status": "unknown"},
    ]}) == 0


def test_different_license_expressions_for_one_source_are_still_reviewed() -> None:
    assert count_license_contradictions({"sources": [
        {
            "reference": "external:package/1",
            "license_status": "unknown",
            "license": "MIT",
        },
        {
            "reference": "external:package/1",
            "license_status": "unknown",
            "license": "BSD-3-Clause",
        },
    ]}) == 1


def test_validate_cli_reviews_unverified_incompatible_metadata(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest = {
        "schema_version": "0.3.0",
        "artifact": {"id": "test:source-status", "class": "source-code"},
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
    gates = {gate["gate"]: gate["severity"] for gate in report["gate_results"]}
    assert result.value.code == 0
    assert report["structural_valid"] is True
    assert report["manifest_identity_matches"] is True
    assert report["outcome"] == "review-required"
    assert report["legal_conclusion"] == "NOT_MADE"
    assert gates["no_incompatible_third_party_license"] == "none"
    assert gates["unknown_source_license"] == "review"
    assert "one or more source license statuses are unknown or unverified" in report["findings"]
