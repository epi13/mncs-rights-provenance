from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_environment_rights_capability_has_bounded_read_only_invocation() -> None:
    manifest = json.loads((ROOT / ".mncs/project.json").read_text(encoding="utf-8"))
    rights = next(
        item for item in manifest["contracts"]["provides"]
        if item["contract"] == "rights-provenance"
    )

    assert rights["effects"] == ["read"]
    assert rights["invocation"] == {
        "kind": "python",
        "path": "scripts/environment_rights_validate.py",
        "fixed_argv": [
            "validate",
            "RIGHTS.json",
            "--findings-are-not-failures",
        ],
        "timeout_seconds": 30,
    }
    assert set(rights["fingerprint_sources"]) >= {
        "RIGHTS.json",
        "scripts/environment_rights_validate.py",
    }

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / rights["invocation"]["path"]),
            *rights["invocation"]["fixed_argv"],
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=rights["invocation"]["timeout_seconds"],
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["structural_valid"] is True
    assert report["manifest_identity_matches"] is True
    assert report["outcome"] == "review-required"
    assert report["legal_conclusion"] == "NOT_MADE"
