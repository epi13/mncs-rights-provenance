from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from mncs_rights_provenance.cli import main

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


def test_real_forge_record_verifies_as_digest_only_external_evidence(
    tmp_path: Path, capsys,
) -> None:
    preserved = json.loads(
        (ROOT / "evidence/rights-e2e-forge-verification-20261022.json").read_text(
            encoding="utf-8"
        )
    )
    forge_record = preserved["forge_evidence"]
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    (evidence_dir / "forge-license-evidence.json").write_text(
        json.dumps(forge_record), encoding="utf-8"
    )
    (evidence_dir / "fabric-evidence.json").write_text(
        json.dumps(preserved["fabric_evidence"]), encoding="utf-8"
    )
    result = preserved["fabric_result"]
    result_path = tmp_path / "fabric/results/result.json"
    result_path.parent.mkdir(parents=True)
    result_path.write_bytes(result["utf8"].encode("utf-8"))

    manifest = BUILDER.build_rights_manifest(tmp_path, distribution_license="Apache-2.0")
    manifest_path = tmp_path / "rights-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    forge_reference = next(
        item
        for item in manifest["provenance"]["process_evidence"]
        if item["reference"] == forge_record["evidence_id"]
    )
    assert forge_reference["sha256"] == forge_record["content_digest"].removeprefix("sha256:")
    assert manifest["rights"]["rights_basis"] == "unknown-needs-review"
    assert manifest["rights"]["third_party_material"] == "unknown"
    assert manifest["rights"]["copyright_status"] == "mixed-or-undetermined"
    assert manifest["provenance"]["origin_classification"] == "human-directed-machine-generated"

    try:
        main(["evidence", "verify", str(evidence_dir / "forge-license-evidence.json")])
    except SystemExit as exc:
        exit_code = int(exc.code or 0)
    else:  # pragma: no cover - the CLI contract exits with its command result
        exit_code = 0
    report = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert report["evidence_id"] == forge_record["evidence_id"]
    assert report["record_schema_version"] == "0.3.0"
    assert report["content_digest_matches"] is True
    assert report["record_interpretation"] == "uninterpreted-external-record"
    assert report["verification_scope"] == "canonical-content-digest-only"
    assert "claims" not in report
    assert report["legal_conclusion"] == "NOT_MADE"

    try:
        main([
            "validate",
            str(manifest_path),
            "--artifact-file",
            str(result_path),
            "--findings-are-not-failures",
        ])
    except SystemExit as exc:
        validation_exit_code = int(exc.code or 0)
    else:  # pragma: no cover - the CLI contract exits with its command result
        validation_exit_code = 0
    validation = json.loads(capsys.readouterr().out)

    assert validation_exit_code == 0
    assert validation["manifest_identity_matches"] is True
    assert validation["outcome"] == "review-required"
    assert validation["legal_conclusion"] == "NOT_MADE"
    assert "rights basis is explicitly unknown and needs review" in validation["findings"]
    assert "third-party material state is unresolved" in validation["findings"]
