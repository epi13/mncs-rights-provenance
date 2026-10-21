from __future__ import annotations

import json
from pathlib import Path

import pytest

from mncs_rights_provenance import (
    LineageRecord,
    build_native_artifact_binding,
    compute_lineage_digest,
    lineage_record_from_artifact_binding,
    lineage_record_from_dict,
    migrate_lineage_record_03_to_04,
    seal_lineage_record,
    validate_lineage_structure,
    verify_lineage_digest,
)
from mncs_rights_provenance.cli import main

ROOT = Path(__file__).resolve().parents[1]


def _binding(*, rights_state: str = "declared", lineage_state: str = "partial") -> dict:
    manifest = {
        "reference": "repo/RIGHTS.json",
        "manifest_digest": "sha256:" + "a" * 64,
        "manifest_identity": "b" * 64,
        "evidence_state": "declared",
        "rights_state": rights_state if rights_state != "review" else "unresolved",
        "license_expression_ref": "repo/RIGHTS.json#/rights/distribution_license",
        "obligations_ref": "repo/RIGHTS.json#/rights/license_terms",
    }
    relations = [
        "created-from",
        "derived-from",
        "generated-from",
        "transformed-by",
        "compiled-from",
        "incorporates",
        "references",
        "depends-upon",
        "independently-implemented-against",
    ]
    evidence_state = "declared"
    evidence = [{"reference": "build-record:17", "state": "declared"}]
    return build_native_artifact_binding(
        {
            "producer": "mncs-compiler",
            "producer_contract": "mncs.compiler.application-build/11",
            "identity": "artifact:app-17",
            "content_digest": "sha256:" + "c" * 64,
        },
        [] if rights_state == "unknown" else [manifest],
        {
            "kind": "compilation",
            "toolchain_identity": "mncs-compiler:producer-3",
            "event_ref": "build-record:17",
            "evidence_state": "unavailable" if lineage_state == "unknown" else "declared",
            "evidence": [] if lineage_state == "unknown" else evidence,
        },
        [
            {
                "from": f"source:{index}",
                "to": "artifact:app-17",
                "relation": relation,
                "evidence_state": "unavailable" if lineage_state == "unknown" else evidence_state,
                "evidence": [] if lineage_state == "unknown" else evidence,
            }
            for index, relation in enumerate(relations)
        ] if lineage_state != "unknown" else [],
        source_snapshot_identity=None if lineage_state == "unknown" else "snapshot:source-17",
    )


def test_v04_lineage_preserves_native_artifact_relationships_and_evidence() -> None:
    binding = _binding()
    record = lineage_record_from_artifact_binding(
        binding,
        lineage_id="mncs-rights://lineage/app-17",
        binding_reference="mncs-store://artifact-binding/app-17",
    )
    seal_lineage_record(record)
    document = record.to_dict()

    assert document["schema_version"] == "0.4.0"
    assert validate_lineage_structure(document) == []
    assert verify_lineage_digest(document)[0]
    assert [edge["relation"] for edge in document["artifact_relationships"]] == [
        edge["relation"] for edge in binding["lineage"]["relationships"]
    ]
    assert all(edge["evidence_state"] == "declared" for edge in document["artifact_relationships"])
    assert all(edge["binding_digest"] == document["artifact_binding_refs"][0]["content_digest"]
               for edge in document["artifact_relationships"])
    assert document["artifact_transformations"][0]["event_ref"] == "build-record:17"
    assert document["artifact_transformations"][0]["toolchain_identity"] == "mncs-compiler:producer-3"
    assert document["artifact_lineage_state"] == {
        "state": "partial",
        "evidence_state": "inferred",
        "binding_digest": document["artifact_binding_refs"][0]["content_digest"],
    }
    assert document["rights_summary"] == {
        "rights_state": "declared",
        "compatibility": "unknown",
        "legal_conclusion": "NOT_MADE",
    }
    assert document["unresolved"] == ["rights.compatibility"]
    assert lineage_record_from_dict(document).to_dict() == document


def test_v04_schema_accepts_lineage_from_binding_and_keeps_v03_separate() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema03 = json.loads((ROOT / "schemas/v0.3/lineage-record.schema.json").read_text())
    schema04 = json.loads((ROOT / "schemas/v0.4/lineage-record.schema.json").read_text())
    jsonschema.Draft202012Validator.check_schema(schema03)
    jsonschema.Draft202012Validator.check_schema(schema04)

    record = lineage_record_from_artifact_binding(
        _binding(),
        lineage_id="mncs-rights://lineage/schema",
        binding_reference="store://artifact-binding/schema",
    )
    seal_lineage_record(record)
    document = record.to_dict()
    assert list(jsonschema.Draft202012Validator(schema04).iter_errors(document)) == []
    assert list(jsonschema.Draft202012Validator(schema03).iter_errors(document))


def test_recorded_compiler_handoff_projection_matches_native_binding() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    binding_path = ROOT / "evidence/rights-handoff-native-artifact-binding-20261021.json"
    lineage_path = ROOT / "examples/v0.4/lineage-from-live-compiler-binding.json"
    binding = json.loads(binding_path.read_text())
    recorded = json.loads(lineage_path.read_text())
    expected = lineage_record_from_artifact_binding(
        binding,
        lineage_id="mncs-rights://lineage/rights-handoff-compiler-build-20261021",
        binding_reference=(
            "mncs-rights-provenance:evidence/rights-handoff-native-artifact-binding-20261021.json"
        ),
    )
    seal_lineage_record(expected)
    expected_document = expected.to_dict()

    schema04 = json.loads((ROOT / "schemas/v0.4/lineage-record.schema.json").read_text())
    assert recorded == expected_document
    assert validate_lineage_structure(recorded) == []
    assert list(jsonschema.Draft202012Validator(schema04).iter_errors(recorded)) == []
    assert verify_lineage_digest(recorded)[0]
    assert {edge["relation"] for edge in recorded["artifact_relationships"]} == {
        "compiled-from", "transformed-by"
    }
    assert any(
        evidence["state"] == "directly-observed"
        for edge in recorded["artifact_relationships"]
        for evidence in edge["evidence"]
    )
    assert recorded["rights_summary"] == {
        "rights_state": "review",
        "compatibility": "unknown",
        "legal_conclusion": "NOT_MADE",
    }
    assert recorded["artifact_lineage_state"]["state"] == "partial"
    assert recorded["artifact_lineage_state"]["evidence_state"] == "inferred"


def test_v04_migration_reseals_only_the_schema_version() -> None:
    legacy = LineageRecord(
        lineage_id="mncs-rights://lineage/legacy",
        subject={"artifact_refs": [{"id": "artifact:legacy"}]},
        derivations=[{"from": "source:1", "to": "artifact:legacy", "relation": "derived-from"}],
        schema_version="0.3.0",
    )
    seal_lineage_record(legacy)
    old = legacy.to_dict()
    migrated = migrate_lineage_record_03_to_04(old)

    assert migrated["schema_version"] == "0.4.0"
    assert migrated["derivations"] == old["derivations"]
    assert "artifact_relationships" not in migrated
    assert "artifact_transformations" not in migrated
    assert "artifact_binding_refs" not in migrated
    assert migrated["content_digest"] == compute_lineage_digest(migrated)
    assert validate_lineage_structure(migrated) == []
    assert lineage_record_from_dict(old).to_dict() == old


def test_unknown_rights_and_missing_lineage_remain_unknown_after_projection() -> None:
    binding = _binding(rights_state="unknown", lineage_state="unknown")
    record = lineage_record_from_artifact_binding(
        binding,
        lineage_id="mncs-rights://lineage/unknown",
        binding_reference="store://artifact-binding/unknown",
    )
    seal_lineage_record(record)
    document = record.to_dict()
    assert document["rights_summary"]["rights_state"] == "unknown"
    assert document["rights_summary"]["compatibility"] == "unknown"
    assert document["artifact_lineage_state"]["state"] == "unknown"
    assert document["artifact_lineage_state"]["evidence_state"] == "inferred"
    assert document["artifact_relationships"] == []
    assert document["artifact_transformations"][0]["evidence_state"] == "unavailable"
    assert validate_lineage_structure(document) == []


def test_declared_complete_status_is_not_promoted_to_verified() -> None:
    binding = _binding()
    binding["lineage"]["state"] = "complete"
    record = lineage_record_from_artifact_binding(
        binding,
        lineage_id="mncs-rights://lineage/claimed-complete",
        binding_reference="store://artifact-binding/claimed-complete",
    )
    seal_lineage_record(record)
    status = record.to_dict()["artifact_lineage_state"]
    assert status["state"] == "complete"
    assert status["evidence_state"] == "declared"
    assert validate_lineage_structure(record.to_dict()) == []


def test_binding_conversion_rejects_inconsistent_rights_and_unverified_attestation() -> None:
    inconsistent = _binding()
    inconsistent["rights"]["state"] = "unknown"
    with pytest.raises(ValueError, match="conflicts with contributing manifest"):
        lineage_record_from_artifact_binding(
            inconsistent,
            lineage_id="mncs-rights://lineage/bad-rights",
            binding_reference="store://artifact-binding/bad-rights",
        )

    unverifiable = _binding()
    unverifiable["lineage"]["relationships"][0]["evidence"] = [
        {"reference": "attestation:1", "state": "verified-attestation"}
    ]
    with pytest.raises(ValueError, match="verifier_ref"):
        lineage_record_from_artifact_binding(
            unverifiable,
            lineage_id="mncs-rights://lineage/bad-attestation",
            binding_reference="store://artifact-binding/bad-attestation",
        )


def test_cli_converts_binding_and_verifies_the_sealed_lineage(tmp_path: Path, capsys) -> None:
    binding_path = tmp_path / "binding.json"
    binding_path.write_text(json.dumps(_binding()), encoding="utf-8")
    with pytest.raises(SystemExit) as converted:
        main([
            "lineage",
            "from-artifact-binding",
            str(binding_path),
            "--lineage-id",
            "mncs-rights://lineage/cli",
            "--reference",
            "store://artifact-binding/cli",
        ])
    assert converted.value.code == 0
    document = json.loads(capsys.readouterr().out)
    lineage_path = tmp_path / "lineage.json"
    lineage_path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(SystemExit) as verified:
        main(["lineage", "verify", str(lineage_path)])
    assert verified.value.code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["ok"] is True
    assert report["lineage_id"] == "mncs-rights://lineage/cli"


def test_v03_cannot_smuggle_v04_artifact_relationships_into_pressure_edges() -> None:
    legacy = LineageRecord(
        lineage_id="mncs-rights://lineage/v03-relation",
        subject={"artifact_refs": [{"id": "artifact:legacy"}]},
        derivations=[{"from": "spec:1", "to": "artifact:legacy", "relation": "independently-implemented-against"}],
        schema_version="0.3.0",
    )
    seal_lineage_record(legacy)
    document = legacy.to_dict()
    assert any("relation invalid" in issue for issue in validate_lineage_structure(document))
    with pytest.raises(ValueError, match="relation is unsupported"):
        lineage_record_from_artifact_binding(
            {
                **_binding(),
                "lineage": {
                    **_binding()["lineage"],
                    "relationships": [{
                        "from": "spec:1", "to": "artifact:app-17",
                        "relation": "not-a-relation", "evidence_state": "declared",
                        "evidence": [{"reference": "note:1", "state": "declared"}],
                    }],
                },
            },
            lineage_id="mncs-rights://lineage/invalid",
            binding_reference="store://artifact-binding/invalid",
        )
