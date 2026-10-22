from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from mncs_rights_provenance.artifact_binding import (
    DIAGNOSTIC_SCHEMA_VERSION,
    build_native_artifact_binding,
    diagnose_native_artifact_binding,
)
from mncs_rights_provenance.cli import MAX_ARTIFACT_BINDING_DIAGNOSTIC_BYTES, main

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(
    (ROOT / "schemas/v0.2/native-artifact-binding-diagnostic.schema.json").read_text()
)


def _manifest(reference: str, rights_state: str = "declared") -> dict:
    return {
        "reference": reference,
        "manifest_digest": "sha256:" + "a" * 64,
        "manifest_identity": "b" * 64,
        "rights_state": rights_state,
        "evidence_state": "declared",
        "license_expression_ref": "#/rights/distribution_license",
        "obligations_ref": "#/rights/license_terms",
    }


def _binding(
    *,
    rights_state: str = "declared",
    manifests: list[dict] | None = None,
    lineage_state: str = "partial",
    relationship_state: str | None = "declared",
    transformation_state: str = "declared",
    source_snapshot_identity: str | None = None,
) -> dict:
    relationships = []
    if relationship_state is not None:
        relationships = [{
            "from": "source:demo",
            "to": "artifact:demo",
            "relation": "generated-from",
            "evidence_state": relationship_state,
            "evidence": [] if relationship_state == "unavailable" else [
                {"reference": "producer:edge", "state": "declared"}
            ],
        }]
    binding = build_native_artifact_binding(
        {
            "producer": "mncs-demo",
            "producer_contract": "mncs.demo.build/1",
            "identity": "artifact:demo",
            "content_digest": "sha256:" + "c" * 64,
        },
        manifests or [],
        {
            "kind": "generation",
            "toolchain_identity": None,
            "event_ref": "producer:event-1",
            "evidence_state": transformation_state,
            "evidence": [] if transformation_state == "unavailable" else [
                {"reference": "producer:build", "state": "declared"}
            ],
        },
        relationships,
        source_snapshot_identity=source_snapshot_identity,
    )
    # Keep intentional aggregate conflicts valid at the field/schema level so
    # the diagnostic can explain the mismatch instead of rejecting the input.
    binding["rights"]["state"] = rights_state
    binding["lineage"]["state"] = lineage_state
    return binding


def test_missing_rights_and_lineage_produce_evidence_linked_remedies() -> None:
    report = diagnose_native_artifact_binding(
        _binding(
            rights_state="unknown",
            lineage_state="unknown",
            relationship_state=None,
            transformation_state="unavailable",
        )
    )

    assert report["schema_version"] == DIAGNOSTIC_SCHEMA_VERSION
    assert report["status"] == "review"
    assert {item["code"] for item in report["diagnostics"]} == {
        "artifact-rights-manifests-missing",
        "artifact-lineage-missing",
    }
    assert all(item["evidence_ref"].startswith("#/") for item in report["diagnostics"])
    assert all(item["remedy"] for item in report["diagnostics"])
    assert report["legal_conclusion"] == "NOT_MADE"
    Draft202012Validator.check_schema(SCHEMA)
    assert list(Draft202012Validator(SCHEMA).iter_errors(report)) == []


def test_unknown_and_unresolved_rights_remain_distinct() -> None:
    unknown = diagnose_native_artifact_binding(
        _binding(rights_state="unknown", manifests=[_manifest("dependency/RIGHTS.json", "unknown")])
    )
    unresolved = diagnose_native_artifact_binding(
        _binding(
            rights_state="review",
            manifests=[_manifest("dependency/RIGHTS.json", "unresolved")],
        )
    )

    assert unknown["diagnostics"][0]["code"] == "artifact-rights-unknown"
    assert unknown["diagnostics"][0]["remedy"] == "investigate-unknown-rights-declarations"
    assert unresolved["diagnostics"][0]["code"] == "artifact-rights-unresolved"
    assert unresolved["diagnostics"][0]["remedy"] == "resolve-rights-evidence-or-preserve-unresolved-state"


def test_multiple_declared_inputs_report_unknown_compatibility_without_inference() -> None:
    report = diagnose_native_artifact_binding(
        _binding(
            manifests=[
                _manifest("project/RIGHTS.json"),
                _manifest("dependency/RIGHTS.json"),
            ]
        )
    )

    finding = report["diagnostics"][0]
    assert finding["code"] == "artifact-rights-compatibility-unknown"
    assert finding["remedy"] == "evaluate-compatibility-from-authoritative-license-terms"
    assert report["legal_conclusion"] == "NOT_MADE"


def test_repeated_identical_manifest_reference_does_not_add_compatibility_noise() -> None:
    manifest = _manifest("dependency/RIGHTS.json")
    binding = _binding(manifests=[manifest, dict(manifest)])
    report = diagnose_native_artifact_binding(
        binding
    )

    assert report["status"] == "no-findings"
    assert report["diagnostics"] == []
    assert binding["rights"]["compatibility"] == "unknown"
    assert report["legal_conclusion"] == "NOT_MADE"


def test_repeated_manifest_reference_with_changed_metadata_is_actionable() -> None:
    first = _manifest("dependency/RIGHTS.json")
    second = dict(first)
    second["manifest_digest"] = "sha256:" + "d" * 64
    second["license_expression_ref"] = "#/rights/alternate_license"
    binding = _binding(manifests=[first, second])

    report = diagnose_native_artifact_binding(binding)
    codes = {item["code"] for item in report["diagnostics"]}

    assert "artifact-rights-manifest-reference-inconsistent" in codes
    assert "artifact-rights-compatibility-unknown" in codes
    assert len(binding["rights"]["contributing_manifests"]) == 2
    finding = next(
        item for item in report["diagnostics"]
        if item["code"] == "artifact-rights-manifest-reference-inconsistent"
    )
    assert finding["evidence_ref"] == "#/rights/contributing_manifests"
    assert finding["evidence_refs"] == [
        "#/rights/contributing_manifests/0",
        "#/rights/contributing_manifests/1",
    ]
    assert finding["conflicting_fields"] == [
        "manifest_digest",
        "license_expression_ref",
    ]
    assert finding["conflict_count"] == 1
    assert finding["remedy"] == "reconcile-manifest-reference-evidence"
    assert report["legal_conclusion"] == "NOT_MADE"


def test_mixed_unknown_and_unresolved_inputs_keep_both_states_and_compatibility() -> None:
    report = diagnose_native_artifact_binding(
        _binding(
            rights_state="unknown",
            manifests=[
                _manifest("dependency-a/RIGHTS.json", "unknown"),
                _manifest("dependency-b/RIGHTS.json", "unresolved"),
            ],
        )
    )

    codes = {item["code"] for item in report["diagnostics"]}
    assert codes == {
        "artifact-rights-unknown",
        "artifact-rights-unresolved",
        "artifact-rights-compatibility-unknown",
    }


def test_conflicting_aggregate_rights_state_is_reported_from_input_manifests() -> None:
    report = diagnose_native_artifact_binding(
        _binding(
            rights_state="declared",
            manifests=[_manifest("dependency/RIGHTS.json", "unknown")],
        )
    )

    assert report["diagnostics"][0]["code"] == "artifact-rights-state-conflict"
    assert report["diagnostics"][0]["remedy"] == (
        "reconcile-aggregate-rights-state-from-contributing-manifests"
    )


def test_complete_lineage_without_an_attestation_remains_reviewable() -> None:
    report = diagnose_native_artifact_binding(
        _binding(lineage_state="complete")
    )

    assert "artifact-lineage-completeness-unsubstantiated" in {
        item["code"] for item in report["diagnostics"]
    }


def test_lineage_state_conflict_is_reported_when_marked_unknown_with_evidence() -> None:
    report = diagnose_native_artifact_binding(
        _binding(
            manifests=[_manifest("project/RIGHTS.json")],
            lineage_state="unknown",
        )
    )

    assert "artifact-lineage-state-conflict" in {
        item["code"] for item in report["diagnostics"]
    }


def test_known_single_manifest_and_declared_partial_lineage_are_not_noisy() -> None:
    report = diagnose_native_artifact_binding(
        _binding(manifests=[_manifest("project/RIGHTS.json")])
    )

    assert report["status"] == "no-findings"
    assert report["diagnostics"] == []
    assert report["legal_conclusion"] == "NOT_MADE"


def test_explicitly_unavailable_relationship_evidence_is_actionable() -> None:
    report = diagnose_native_artifact_binding(
        _binding(
            relationship_state="unavailable",
            manifests=[_manifest("project/RIGHTS.json")],
        )
    )

    assert report["diagnostics"][0]["code"] == "artifact-lineage-evidence-unavailable"
    assert report["diagnostics"][0]["remedy"] == "reconcile-producer-records-or-record-evidence-unavailable"


def test_unavailable_transformation_evidence_points_to_the_transformation_record() -> None:
    report = diagnose_native_artifact_binding(
        _binding(
            manifests=[_manifest("project/RIGHTS.json")],
            relationship_state=None,
            transformation_state="unavailable",
            source_snapshot_identity="source-snapshot:demo",
        )
    )

    assert report["diagnostics"][0]["code"] == "artifact-lineage-evidence-unavailable"
    assert report["diagnostics"][0]["evidence_ref"] == "#/lineage/transformation/evidence"


def test_bounded_cli_returns_diagnostic_json_and_rejects_oversized_binding(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    binding_path = tmp_path / "binding.json"
    binding_path.write_text(json.dumps(_binding(rights_state="unknown", lineage_state="unknown")))

    with pytest.raises(SystemExit) as result:
        main(["artifact-binding", "diagnose", str(binding_path)])

    report = json.loads(capsys.readouterr().out)
    assert result.value.code == 0
    assert report["status"] == "review"
    assert list(Draft202012Validator(SCHEMA).iter_errors(report)) == []

    oversized_path = tmp_path / "oversized.json"
    oversized_path.write_bytes(b" " * (MAX_ARTIFACT_BINDING_DIAGNOSTIC_BYTES + 1))
    with pytest.raises(SystemExit) as oversized_result:
        main(["artifact-binding", "diagnose", str(oversized_path)])
    error = json.loads(capsys.readouterr().out)
    assert oversized_result.value.code == 2
    assert error["legal_conclusion"] == "NOT_MADE"
    assert "2 MiB" in error["error"]
