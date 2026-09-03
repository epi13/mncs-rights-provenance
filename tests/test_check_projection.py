"""Integration: native rights/provenance -> mncs.check-result/1 -> family boundary.

Covers the authoritative projection (``check_projection.py``), the CLI
(``scripts/rp_to_check.py``), the CI provider scripts, and the wiring
between provider check ids and the caller workflow's declared boundary.
Live ``mncs-rp validate`` output is exercised wherever deterministic;
synthetic reports cover PASS/FAIL paths no committed manifest reaches
today (no committed manifest passes canonical-release: human review is
genuinely outstanding, and the tests assert that fact explicitly rather
than fabricating PASS).
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mncs_rights_provenance.check_projection import (
    CHECK_RESULT_SCHEMA_VERSION,
    classify_report,
    project_report_to_check,
)

WORKFLOW = ROOT / ".github" / "workflows" / "mncs-family.yml"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")

MNCS_RP = shutil.which("mncs-rp")


def mncs_rp_bin() -> str:
    if MNCS_RP is None:
        pytest.skip("mncs-rp not installed")
    return MNCS_RP


def check_shape_valid(check: dict) -> list[str]:
    """Minimal local shape check for mncs.check-result/1 (no cross-repo import)."""
    errors = []
    if check.get("schema_version") != CHECK_RESULT_SCHEMA_VERSION:
        errors.append("schema_version")
    for field in ("id", "provider"):
        if not isinstance(check.get(field), str) or not check[field]:
            errors.append(field)
    if check.get("verdict") not in ("PASS", "FAIL", "UNKNOWN"):
        errors.append("verdict")
    for ref in check.get("references", []):
        if not isinstance(ref, dict) or not ref.get("kind"):
            errors.append("references.kind")
        digest = ref.get("digest")
        if digest is not None and not re.match(r"^(sha256:)?[a-f0-9]{64}$", str(digest)):
            errors.append("references.digest")
        path = ref.get("path")
        if path is not None and (".." in str(path) or str(path).startswith("/")):
            errors.append("references.path")
    return errors


# ---- authoritative mapping ----


def test_pass_maps_to_pass():
    verdict, _, error = classify_report({"outcome": "pass", "structural_valid": True})
    assert (verdict, error) == ("PASS", None)


def test_blocked_and_invalid_map_to_fail():
    for outcome in ("blocked", "invalid"):
        verdict, _, error = classify_report({"outcome": outcome, "structural_valid": False})
        assert (verdict, error) == ("FAIL", None), outcome


def test_review_paths_map_to_unknown():
    for outcome in ("pass-with-findings", "review-required", "unknown"):
        verdict, _, error = classify_report({"outcome": outcome})
        assert (verdict, error) == ("UNKNOWN", None), outcome


def test_drift_maps_to_unknown_never_pass():
    verdict, notes, error = classify_report({"outcome": "future-outcome"})
    assert error is None and verdict == "UNKNOWN"
    assert any("drift" in note for note in notes)


def test_missing_outcome_establishes_no_claim():
    for bad in ({}, {"outcome": ""}, {"outcome": None}, "nope", None):
        verdict, _, error = classify_report(bad)
        assert verdict is None and error, bad


def test_contradictory_reports_establish_no_claim():
    verdict, _, error = classify_report({"outcome": "pass", "structural_valid": False})
    assert verdict is None and error
    verdict, _, error = classify_report({"outcome": "invalid", "structural_valid": True})
    assert verdict is None and error


def test_identity_mismatch_downgrades_pass_to_fail():
    verdict, notes, error = classify_report({"outcome": "pass", "manifest_identity_matches": False})
    assert error is None and verdict == "FAIL"
    assert any("identity mismatch" in note for note in notes)


def test_projection_preserves_native_result():
    report = {
        "outcome": "review-required",
        "severity": "review",
        "findings": ["human review state is unacceptable for release"],
        "issues": [],
        "manifest_identity_expected": "a" * 64,
        "legal_conclusion": "NOT_MADE",
    }
    check, error = project_report_to_check(
        report,
        manifest_path="dogfood/human-specification.json",
        contract_revision="0.3.0",
    )
    assert error is None and check is not None
    assert check["verdict"] == "UNKNOWN"
    assert "review-required" in check["summary"]
    assert any("human review" in item for item in check["unresolved"])
    assert check["references"][0]["kind"] == "rights-manifest"
    assert check["references"][0]["path"] == "dogfood/human-specification.json"
    assert check_shape_valid(check) == []


def test_projection_no_claim_emits_nothing():
    check, error = project_report_to_check({"severity": "none"})
    assert check is None and error


# ---- live native evaluation ----


def test_live_dogfood_manifest_projects_to_unknown(tmp_path):
    rp = mncs_rp_bin()
    manifest = ROOT / "dogfood" / "human-specification.json"
    report_path = tmp_path / "report.json"
    proc = subprocess.run(
        [rp, "validate", str(manifest), "--findings-are-not-failures"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
    )
    report_path.write_text(proc.stdout, encoding="utf-8")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    # Honest current state: human review genuinely outstanding.
    assert report["outcome"] == "review-required"
    out = tmp_path / "check.json"
    cli = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "rp_to_check.py"),
            "--input",
            str(report_path),
            "--output",
            str(out),
            "--manifest-path",
            "dogfood/human-specification.json",
            "--contract-revision",
            "0.3.0",
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
    )
    assert cli.returncode == 0, cli.stderr
    check = json.loads(out.read_text(encoding="utf-8"))
    assert check["verdict"] == "UNKNOWN"
    assert check_shape_valid(check) == []


def test_live_invalid_manifest_projects_to_fail(tmp_path):
    rp = mncs_rp_bin()
    manifest = ROOT / "examples" / "human-authored.json"
    report_path = tmp_path / "report.json"
    proc = subprocess.run(
        [rp, "validate", str(manifest), "--findings-are-not-failures"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
    )
    report = json.loads(proc.stdout)
    assert report["outcome"] == "invalid"
    report_path.write_text(proc.stdout, encoding="utf-8")
    out = tmp_path / "check.json"
    cli = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "rp_to_check.py"),
            "--input",
            str(report_path),
            "--output",
            str(out),
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
    )
    assert cli.returncode == 0, cli.stderr
    check = json.loads(out.read_text(encoding="utf-8"))
    # A structurally-invalid artifact is a valid negative claim (FAIL),
    # not a missing claim: the domain ran and spoke negatively.
    assert check["verdict"] == "FAIL"
    assert check_shape_valid(check) == []


def test_cli_missing_report_fails_closed(tmp_path):
    out = tmp_path / "check.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "rp_to_check.py"),
            "--input",
            str(tmp_path / "does-not-exist.json"),
            "--output",
            str(out),
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
    )
    assert proc.returncode == 2
    assert not out.exists()


def test_cli_malformed_input_fails_closed(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("not json", encoding="utf-8")
    out = tmp_path / "check.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "rp_to_check.py"),
            "--input",
            str(bad),
            "--output",
            str(out),
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
    )
    assert proc.returncode == 2
    assert not out.exists()


# ---- provider scripts ----


def test_rights_provider_script_produces_valid_check(tmp_path):
    mncs_rp_bin()
    out = tmp_path / "rights-check.json"
    env = dict(os.environ, CHECK_OUTPUT=str(out))
    proc = subprocess.run(
        ["bash", str(ROOT / "scripts" / "ci-rights-check.sh")],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    check = json.loads(out.read_text(encoding="utf-8"))
    assert check["id"] == "rights-provenance"
    assert check["provider"] == "mncs-rights-provenance"
    assert check["verdict"] == "UNKNOWN"  # honest: review outstanding
    assert check_shape_valid(check) == []


def test_project_provider_script_produces_valid_check(tmp_path):
    out = tmp_path / "project-check.json"
    # Bounded subset: the script's own full-suite invocation would recurse
    # into this test file. Mechanics (exit mapping, JSON shape) are what
    # is pinned here; the full suite runs in CI.
    env = dict(os.environ, CHECK_OUTPUT=str(out), PROJECT_TEST_ARGS="tests/test_manifest.py -q")
    proc = subprocess.run(
        ["bash", str(ROOT / "scripts" / "ci-project-check.sh")],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    check = json.loads(out.read_text(encoding="utf-8"))
    assert check["id"] == "project-tests"
    assert check["verdict"] in ("PASS", "FAIL")
    assert check_shape_valid(check) == []


def test_repeated_provider_use_stable(tmp_path):
    mncs_rp_bin()
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    for out in (first, second):
        env = dict(os.environ, CHECK_OUTPUT=str(out))
        proc = subprocess.run(
            ["bash", str(ROOT / "scripts" / "ci-rights-check.sh")],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            check=False,
            env=env,
        )
        assert proc.returncode == 0, proc.stderr
    assert json.loads(first.read_text()) == json.loads(second.read_text())


# ---- MNCS pressure agreement ----


def test_mncs_projection_arms_match_host():
    text = (ROOT / "language" / "check_projection.mncs").read_text(encoding="utf-8")
    # MNCS arm -> (expected MNCS verdict, native outcome string, expected host verdict)
    arms = {
        "Pass": ("Pass", "pass", "PASS"),
        "Blocked": ("Fail", "blocked", "FAIL"),
        "Invalid": ("Fail", "invalid", "FAIL"),
        "PassWithFindings": ("Unknown", "pass-with-findings", "UNKNOWN"),
        "ReviewRequired": ("Unknown", "review-required", "UNKNOWN"),
        "Unknown": ("Unknown", "unknown", "UNKNOWN"),
        "Unrecognized": ("Unknown", "future-x", "UNKNOWN"),
    }
    for outcome, (mncs_verdict, native, host_verdict) in arms.items():
        assert re.search(rf"Outcome\.{outcome}\s*=>\s*CheckVerdict\.{mncs_verdict}\b", text), (
            f"MNCS projection missing {outcome} => {mncs_verdict}"
        )
        got, _, error = classify_report({"outcome": native})
        assert error is None and got == host_verdict, outcome
    assert re.search(r"Truth\.No\s*=>\s*CheckVerdict\.Fail", text)
    assert "Unknown => CheckVerdict.Pass" not in text


def test_mncs_projection_compiles_clean():
    binary = os.environ.get("MNCS_BIN")
    if not binary:
        pytest.skip("MNCS_BIN not set")
    proc = subprocess.run(
        [binary, "source-study", str(ROOT / "language" / "check_projection.mncs")],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
    )
    document = json.loads(proc.stdout)
    diags = document.get("diagnostics", [])
    assert diags == [], diags
    assert document.get("compilation_status") == "completed"


# ---- caller wiring ----


def test_caller_workflow_pins_immutable_revision():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "mncs-family-verify.yml@main" not in text
    match = re.search(r"mncs-family-verify\.yml@([^\s\"']+)", text)
    assert match, "no reusable workflow pin found"
    assert FULL_SHA.match(match.group(1)), f"caller pin floats: {match.group(1)}"


def test_provider_ids_match_declared_boundary():
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    job = doc["jobs"]["family"]
    required = [item.strip() for item in job["with"]["required-checks"].split(",")]
    assert required == ["rights-provenance", "project-tests"]
    assert job["with"]["rights-check-id"] in required
    assert job["with"]["project-check-id"] in required
    assert job["with"]["rights-provider"] == "mncs-rights-provenance"
    # mncs-validation is intentionally not applicable here: this repository
    # ships no validator-consumable bundle; its MNCS cores are covered by
    # project-tests (backend agreement). Absence is declared, never PASS.
    assert "mncs-validation" not in required
    assert "mncs-command" not in job["with"]
