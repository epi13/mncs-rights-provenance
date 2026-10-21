"""Cross-backend and host-mirror checks for redistribution trigger rules."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

from language.tools.gen_action_guidance_corpus import build

from mncs_rights_provenance.license_resolution import license_action_guidance

CORPUS = ROOT / "language" / "corpora" / "license-action-guidance-corpus.json"
GOLDEN = ROOT / "conformance" / "license-action-guidance-golden-vectors.json"
PROGRAM = ROOT / "language" / "rights_license_actions.mncs"

CONDITION_BINDINGS = {
    "RetainCopyNotice": ("MIT", "retain-copyright-and-permission-notice"),
    "RetainSourceNotice": (
        "BSD-2-Clause", "retain-notice-conditions-and-disclaimer",
    ),
    "ReproduceBinaryNotice": (
        "BSD-2-Clause", "reproduce-notice-conditions-and-disclaimer",
    ),
    "ProvideLicenseCopy": ("Apache-2.0", "provide-license-copy"),
    "MarkModifiedFiles": ("Apache-2.0", "mark-modified-files"),
    "PreserveSourceNotices": (
        "Apache-2.0", "preserve-applicable-source-notices",
    ),
    "PreserveNoticeAttributions": (
        "Apache-2.0", "preserve-notice-attributions",
    ),
    "NoEndorsement": ("BSD-3-Clause", "no-endorsement-without-permission"),
    "DoNotMisrepresentOrigin": ("Zlib", "do-not-misrepresent-origin"),
    "MarkAlteredSource": ("Zlib", "mark-altered-source"),
    "PreserveZlibSourceNotice": ("Zlib", "preserve-zlib-source-notice"),
}
HOST_RELATION_TO_CORE = {
    "operation-class-matches-trigger": "OperationClassMatchesTrigger",
    "other-trigger-preserved-for-review": "OtherTriggerPreservedForReview",
}


def mncs_bin() -> str:
    override = os.environ.get("MNCS_BIN")
    if override and Path(override).is_file():
        return override
    found = shutil.which("mncs")
    if found:
        return found
    pytest.skip("no mncs binary (MNCS_BIN or PATH)")


def load_corpus() -> dict:
    return json.loads(CORPUS.read_text(encoding="utf-8"))


def load_golden() -> dict:
    return json.loads(GOLDEN.read_text(encoding="utf-8"))


def run_cases(cases: list[dict], backend: str) -> list[dict]:
    document = {
        "schema_version": "0.1",
        "name": "license-action-guidance-pytest-probe",
        "cases": cases,
    }
    with tempfile.TemporaryDirectory() as tmp:
        corpus_path = Path(tmp) / "probe-corpus.json"
        output_dir = Path(tmp) / "out"
        corpus_path.write_text(json.dumps(document), encoding="utf-8")
        process = subprocess.run(
            [
                mncs_bin(), "experiment", "run", str(PROGRAM),
                "--backend", backend,
                "--corpus", str(corpus_path),
                "--output-dir", str(output_dir),
            ],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        assert process.returncode == 0, process.stderr[-2000:]
        result_path = output_dir / "result.json"
        assert result_path.is_file(), process.stderr[-2000:]
        return json.loads(result_path.read_text(encoding="utf-8"))["cases"]


def test_corpus_and_golden_vectors_are_complete_and_deterministic() -> None:
    corpus = load_corpus()
    golden = load_golden()
    regenerated_corpus, regenerated_golden = build()

    assert corpus["schema_version"] == "0.1"
    assert corpus["name"] == "license-action-guidance-v1"
    assert golden["source_module"] == "mncs.rights.license_actions.v01"
    assert len(corpus["cases"]) == len(golden["cases"]) == 22
    assert json.dumps(corpus["cases"], indent=1) == json.dumps(regenerated_corpus, indent=1)
    assert json.dumps(golden["cases"], indent=1) == json.dumps(regenerated_golden, indent=1)


def test_host_action_projection_matches_every_language_vector() -> None:
    for vector in load_golden()["cases"]:
        action = "redistribute-source" if vector["inputs"]["action"] == "Source" else (
            "redistribute-binary"
        )
        expression, condition_id = CONDITION_BINDINGS[vector["inputs"]["condition"]]
        report = license_action_guidance(expression, action)
        condition = next(
            item for item in report["expression_tree"]["conditions"]
            if item["id"] == condition_id
        )
        assert HOST_RELATION_TO_CORE[condition["action_relation"]] == vector["output"]


@pytest.mark.parametrize("backend", ["research-bytecode", "portable-wasm"])
def test_native_core_executes_every_action_condition_pair(backend: str) -> None:
    results = run_cases(load_corpus()["cases"], backend)

    assert len(results) == 22
    assert all(case.get("expectation_met") for case in results)
