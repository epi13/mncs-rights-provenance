"""Agreement for the normative manifest-reference consistency core."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from mncs_rights_provenance.manifest_reference_consistency import (
    compatibility_review_required,
    repeated_reference_metadata_conflict,
)

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "language/corpora/manifest-reference-consistency-corpus.json"
GOLDEN = ROOT / "conformance/manifest-reference-consistency-golden-vectors.json"
PROGRAM = ROOT / "language/manifest_reference_consistency.mncs"


def load_corpus() -> dict:
    return json.loads(CORPUS.read_text(encoding="utf-8"))


def load_golden() -> dict:
    return json.loads(GOLDEN.read_text(encoding="utf-8"))


def _evaluate(vector: dict) -> int:
    function = vector["function"]
    args = vector["inputs"]["args"]
    if function == "repeated_reference_metadata_conflict":
        return repeated_reference_metadata_conflict(*args)
    if function == "compatibility_review_required":
        return compatibility_review_required(*args)
    raise AssertionError(f"unknown golden function: {function}")


def test_generated_corpus_and_golden_are_deterministic() -> None:
    from language.tools.gen_manifest_reference_consistency_corpus import build

    corpus_cases, golden_cases = build()
    assert corpus_cases == load_corpus()["cases"]
    assert golden_cases == load_golden()["cases"]
    assert len(corpus_cases) == len(golden_cases) == 13


def test_host_mirror_matches_every_normative_golden_vector() -> None:
    golden = load_golden()
    assert golden["source_module"] == "mncs.rights.manifest_reference_consistency.v01"
    for vector in golden["cases"]:
        assert _evaluate(vector) == vector["output"], vector["case_id"]


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
    with tempfile.TemporaryDirectory(prefix="mncs-manifest-consistency-") as temporary:
        output = Path(temporary) / "output"
        process = subprocess.run(
            [
                _mncs_binary(), "experiment", "run", str(PROGRAM),
                "--backend", backend, "--corpus", str(CORPUS),
                "--output-dir", str(output),
            ],
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        assert process.returncode == 0, process.stderr[-2000:]
        return json.loads((output / "result.json").read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize("backend", ["mncs-research-bytecode", "mncs-portable-wasm-mvp"])
def test_live_native_execution_matches_all_corpus_expectations(backend: str) -> None:
    cases = _run(backend)
    assert len(cases) == len(load_corpus()["cases"])
    assert [case["case_id"] for case in cases if not case.get("expectation_met")] == []
