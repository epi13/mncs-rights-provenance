"""Rights-claim status core: corpus integrity, golden agreement, live execution.

Covers the normative claim layer (``language/rights_claims.mncs``):
corpus/golden determinism, case-identity alignment, live
``mncs experiment run`` smoke on both compiler backends, malformed
requests failing structured (never crashing), and symbolic spot checks
on precedence, conflict, and UNKNOWN preservation.

The host mirror (``mncs_rights_provenance.claims``) is pinned to the same
golden vectors by ``tests/test_claims_host.py``; agreement here is measured
directly as well: committed vectors regenerate byte-identically, and the
toolchain executes the committed corpus with every expectation met.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "language" / "tools"))

from gen_claims_corpus import build

CORPUS = ROOT / "language" / "corpora" / "claims-corpus.json"
GOLDEN = ROOT / "conformance" / "claims-golden-vectors.json"
PROGRAM = ROOT / "language" / "rights_claims.mncs"

FUNCTIONS = {
    "claim_status",
    "temporal_state",
    "evidence_state",
    "basis_compatible",
    "attribution_due",
    "signed_state",
    "supersede_link_valid",
}

STATUSES = (
    "Asserted",
    "Verified",
    "Contested",
    "Superseded",
    "Expired",
    "Revoked",
    "Incompatible",
    "Unknown",
)


def mncs_bin() -> str:
    override = os.environ.get("MNCS_BIN")
    if override and Path(override).is_file():
        return override
    found = shutil.which("mncs")
    if found:
        return found
    pytest.skip("no mncs binary (MNCS_BIN or PATH)")


def load_corpus() -> dict:
    return json.loads(CORPUS.read_text())


def load_golden() -> dict:
    return json.loads(GOLDEN.read_text())


def run_cases(cases: list[dict], backend: str, strict: bool = True) -> list[dict]:
    doc = {"schema_version": "0.1", "name": "claims-pytest-probe", "cases": cases}
    with tempfile.TemporaryDirectory() as tmp:
        corpus_path = Path(tmp) / "probe-corpus.json"
        out_dir = Path(tmp) / "out"
        corpus_path.write_text(json.dumps(doc))
        proc = subprocess.run(
            [
                mncs_bin(),
                "experiment",
                "run",
                str(PROGRAM),
                "--backend",
                backend,
                "--corpus",
                str(corpus_path),
                "--output-dir",
                str(out_dir),
            ],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        if strict:
            assert proc.returncode == 0, proc.stderr[-2000:]
        result_path = out_dir / "result.json"
        assert result_path.is_file(), proc.stderr[-2000:]
        return json.loads(result_path.read_text())["cases"]


def test_corpus_shape():
    doc = load_corpus()
    assert doc["schema_version"] == "0.1"
    assert doc["name"] == "rights-claims-v1"
    ids = [c["id"] for c in doc["cases"]]
    assert len(ids) == len(set(ids)) > 0
    for case in doc["cases"]:
        assert case["request"]["target"]["module"] == "mncs.rights.claims.v01"
        assert case["request"]["target"]["function"] in FUNCTIONS
        assert case["expected"], case["id"]


def test_golden_aligns_with_corpus():
    golden = load_golden()
    assert golden["source_module"] == "mncs.rights.claims.v01"
    corpus_ids = [c["id"] for c in load_corpus()["cases"]]
    assert len(golden["cases"]) == len(corpus_ids)
    for case in golden["cases"]:
        assert case["function"] in FUNCTIONS


def test_regeneration_deterministic():
    corpus, golden = build()
    assert json.dumps({"cases": corpus}, indent=1) == json.dumps(
        {"cases": load_corpus()["cases"]}, indent=1
    )
    assert json.dumps({"cases": golden}, indent=1) == json.dumps(
        {"cases": load_golden()["cases"]}, indent=1
    )


def test_status_precedence_symbols():
    outputs = {
        (c["function"], json.dumps(c["inputs"], sort_keys=True)): c["output"]
        for c in load_golden()["cases"]
    }

    def out(fn, inputs):
        return outputs[(fn, json.dumps(inputs, sort_keys=True))]

    revoked = {"claim": {**_base(), "revoked": 1, "verified": 1}, "now": 500, "superseded": 0}
    assert out("claim_status", revoked) == "Revoked"
    no_evidence = {"claim": {**_base(), "evidence": 0, "verified": 1}, "now": 500, "superseded": 0}
    assert out("claim_status", no_evidence) == "Unknown"


def _base() -> dict:
    return {
        "id": 1,
        "subject": 7,
        "claimant": 3,
        "basis": 2,
        "license": 9,
        "attribution": 1,
        "redistribute": 1,
        "derivatives": 1,
        "commercial": 2,
        "evidence": 42,
        "effective": 100,
        "expires": 0,
        "revoked": 0,
        "supersedes": 0,
        "verified": 0,
        "contested": 0,
    }


def test_live_smoke_research_bytecode():
    cases = [
        c
        for c in load_corpus()["cases"]
        if c["id"] in ("status-revoked-dominates", "compat-redistribute-conflict", "evidence-stale")
    ]
    assert len(cases) == 3
    results = run_cases(cases, "research-bytecode")
    assert all(c.get("expectation_met") for c in results)


def test_live_agreement_portable_wasm():
    cases = [
        c
        for c in load_corpus()["cases"]
        if c["id"]
        in (
            "status-verified-flag-without-evidence-unknown",
            "signed-no-authority-contested",
            "attrib-expired-uncertain",
        )
    ]
    assert len(cases) == 3
    results = run_cases(cases, "portable-wasm")
    assert all(c.get("expectation_met") for c in results)


def test_malformed_requests_fail_structured():
    good = next(c for c in load_corpus()["cases"] if c["id"] == "status-asserted")
    bad_function = dict(good, id="bad-function")
    bad_function["request"] = dict(
        good["request"], target={"module": "mncs.rights.claims.v01", "function": "no_such_fn"}
    )
    bad_arity = dict(good, id="bad-arity")
    bad_arity["request"] = dict(good["request"], arguments=good["request"]["arguments"][:1])
    bad_discriminant = json.loads(json.dumps(good))
    bad_discriminant["id"] = "bad-discriminant"
    bad_discriminant["request"]["arguments"][0] = {
        "finite": {
            "type_identity": "mncs:0.2:finite-type:mncs.rights.claims.v01::ClaimStatus",
            "variant_identity": "mncs:0.2:finite-variant:mncs.rights.claims.v01::ClaimStatus::Bogus",
            "discriminant": 99,
        }
    }
    results = run_cases(
        [bad_function, bad_arity, bad_discriminant], "research-bytecode", strict=False
    )
    by_id = {c["case_id"]: c for c in results}
    assert by_id["bad-function"]["status"] == "invalid_request"
    assert by_id["bad-arity"]["status"] == "invalid_request"
    assert by_id["bad-discriminant"]["status"] == "invalid_request"
    assert all(c.get("expectation_met") is not True for c in results)
