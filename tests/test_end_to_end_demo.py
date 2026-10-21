from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
BUILDER_PATH = ROOT / "examples/end-to-end/build_manifest.py"
SPEC = importlib.util.spec_from_file_location("rights_e2e_manifest_builder", BUILDER_PATH)
assert SPEC is not None and SPEC.loader is not None
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


def _license_evidence() -> dict[str, object]:
    evidence_id = "mncs-forge://license-evidence/0123456789abcdef0123456789abcdef"
    return {
        "schema_version": "0.3.0",
        "evidence_id": evidence_id,
        "content_digest": "sha256:" + "a" * 64,
        "producer": {
            "producer": "mncs-forge",
            "recordKind": "LicenseEvidence",
            "schemaVersion": "0.3.0",
            "stableId": evidence_id,
        },
        "scan_inputs": [
            {"path": "pyproject.toml", "status": "observed", "sha256": "b" * 64}
        ],
        "claims": [
            {
                "claim_type": "license-identification",
                "spdx_expression": "Apache-2.0",
                "confidence": "heuristic",
            }
        ],
    }


def test_license_scan_is_linked_without_inventing_source_compatibility(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    (evidence_dir / "forge-license-evidence.json").write_text(
        json.dumps(_license_evidence()), encoding="utf-8"
    )

    manifest = BUILDER.build_rights_manifest(
        tmp_path, distribution_license="Apache-2.0"
    )

    rights = manifest["rights"]
    assert rights["distribution_license"] == "Apache-2.0"
    assert rights["rights_basis"] == "unknown-needs-review"
    assert rights["third_party_material"] == "unknown"
    assert rights["sources"] == []
    assert "do not establish" in rights["notes"]

    provenance = manifest["provenance"]
    process_evidence = provenance["process_evidence"]
    assert process_evidence == [
        {
            "kind": "rights-evidence-record",
            "reference": _license_evidence()["evidence_id"],
            "sha256": "a" * 64,
            "producer_reference": _license_evidence()["producer"],
        }
    ]
    graph = provenance["graph"]
    node = next(item for item in graph["nodes"] if item["id"] == "license-analysis")
    assert node["evidence"] == process_evidence
    edge = next(item for item in graph["edges"] if item["to"] == "license-analysis")
    assert edge["relation"] == "referenced"

    review = manifest["review"]
    assert review["technical_validation"] == "not-run"
    assert review["provenance_validation"] == "not-run"


def test_missing_license_scan_keeps_rights_unknown(tmp_path: Path) -> None:
    (tmp_path / "evidence").mkdir()

    manifest = BUILDER.build_rights_manifest(
        tmp_path, distribution_license="Apache-2.0"
    )

    rights = manifest["rights"]
    assert rights["rights_basis"] == "unknown-needs-review"
    assert rights["third_party_material"] == "unknown"
    assert rights["sources"] == []
    assert manifest["provenance"]["process_evidence"] == []
    assert not any(
        node["id"] == "license-analysis"
        for node in manifest["provenance"]["graph"]["nodes"]
    )
