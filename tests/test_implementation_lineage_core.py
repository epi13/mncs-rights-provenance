"""Agreement for the normative implementation-lineage MNCS core."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from mncs_rights_provenance.implementation_lineage import (
    implementation_component_status,
    implementation_lineage_status,
)

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "language/corpora/implementation-lineage-corpus.json"
GOLDEN = ROOT / "conformance/implementation-lineage-golden-vectors.json"
PROGRAM = ROOT / "language/implementation_lineage.mncs"


def load_corpus() -> dict:
    return json.loads(CORPUS.read_text(encoding="utf-8"))


def load_golden() -> dict:
    return json.loads(GOLDEN.read_text(encoding="utf-8"))


def test_generated_corpus_and_golden_are_deterministic() -> None:
    from language.tools.gen_implementation_lineage_corpus import build

    corpus_cases, golden_cases = build()
    assert corpus_cases == load_corpus()["cases"]
    assert golden_cases == load_golden()["cases"]
    assert len(corpus_cases) == len(golden_cases) == 18


def test_host_mirror_matches_every_normative_golden_vector() -> None:
    golden = load_golden()
    assert golden["source_module"] == "mncs.rights.implementation_lineage.v01"
    vectors = golden["cases"]
    corpus_ids = [case["id"] for case in load_corpus()["cases"]]
    assert len(corpus_ids) == len(set(corpus_ids)) == len(vectors)

    for case, vector in zip(load_corpus()["cases"], vectors, strict=True):
        assert case["id"] == vector["case_id"]
        function = vector["function"]
        args = vector["inputs"]["args"]
        if function == "implementation_component_status":
            actual = implementation_component_status(*args)
        elif function == "implementation_lineage_status":
            actual = implementation_lineage_status(*args)
        else:
            raise AssertionError(f"unknown golden function: {function}")
        assert actual == vector["output"], case["id"]
        assert case["expected"][0]["finite"]["variant_identity"].endswith(
            f"::{vector['output']}"
        )


def _mncs_binary() -> str:
    override = os.environ.get("MNCS_BIN")
    binary = override if override and Path(override).is_file() else shutil.which("mncs")
    if not binary:
        pytest.skip("no MNCS experiment runner (MNCS_BIN or PATH)")
    probe = subprocess.run(
        [binary, "experiment", "run"], capture_output=True, text=True, timeout=15
    )
    runner_signals = (
        "--backend is required",
        "experiment plan/run requires an MNCS source path",
    )
    if probe.returncode != 0 and not any(signal in probe.stderr for signal in runner_signals):
        pytest.skip("configured mncs command does not provide the experiment runner")
    return binary


def _run(backend: str) -> list[dict]:
    with tempfile.TemporaryDirectory(prefix="mncs-implementation-lineage-") as temporary:
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
        result = json.loads((output / "result.json").read_text(encoding="utf-8"))
        return result["cases"]


@pytest.mark.parametrize("backend", ["mncs-research-bytecode", "mncs-portable-wasm-mvp"])
def test_live_native_execution_matches_all_corpus_expectations(backend: str) -> None:
    cases = _run(backend)
    assert len(cases) == len(load_corpus()["cases"])
    failed = [case["case_id"] for case in cases if not case.get("expectation_met")]
    assert failed == []
