from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from mncs_rights_provenance import build_native_artifact_binding

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas/v0.1/native-artifact-binding.schema.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA)


def _manifest(reference: str, *, state: str = "declared", evidence_state: str = "directly-observed") -> dict:
    return {
        "reference": reference,
        "manifest_digest": "sha256:" + "a" * 64,
        "manifest_identity": "b" * 64,
        "evidence_state": evidence_state,
        "rights_state": state,
        "license_expression_ref": reference + "#/rights/distribution_license",
        "obligations_ref": reference + "#/rights/license_terms",
    }


def _transformation() -> dict:
    return {
        "kind": "compilation",
        "toolchain_identity": "mncs-compiler:producer-3",
        "event_ref": "mncs-compiler:build-receipt/build-17",
        "evidence_state": "directly-observed",
        "evidence": [{
            "reference": "mncs-compiler:build-receipt/build-17",
            "sha256": "c" * 64,
            "state": "directly-observed",
        }],
    }


def test_builder_preserves_multi_input_lineage_without_compatibility_claim() -> None:
    binding = build_native_artifact_binding(
        {
            "producer": "mncs-compiler",
            "producer_contract": "mncs.compiler.application-build/11",
            "identity": "artifact:app-17",
            "content_digest": "sha256:" + "d" * 64,
        },
        [_manifest("repo-a/RIGHTS.json"), _manifest("dependency-b/RIGHTS.json")],
        _transformation(),
        [{
            "from": "snapshot:source-17",
            "to": "artifact:app-17",
            "relation": "compiled-from",
            "evidence_state": "directly-observed",
            "evidence": [{
                "reference": "mncs-compiler:build-receipt/build-17",
                "state": "directly-observed",
            }],
        }],
        source_snapshot_identity="snapshot:source-17",
        context_identity="sha256:" + "e" * 64,
    )

    assert list(VALIDATOR.iter_errors(binding)) == []
    assert binding["rights"]["state"] == "declared"
    assert binding["rights"]["compatibility"] == "unknown"
    assert [item["reference"] for item in binding["rights"]["contributing_manifests"]] == [
        "repo-a/RIGHTS.json", "dependency-b/RIGHTS.json",
    ]
    assert binding["lineage"]["state"] == "partial"
    assert binding["lineage"]["relationships"][0]["relation"] == "compiled-from"
    assert binding["legal_conclusion"] == "NOT_MADE"


def test_unknown_rights_and_declared_origin_are_not_promoted_to_verified_facts() -> None:
    unknown = _manifest("external/RIGHTS.json", state="unknown", evidence_state="declared")
    unknown["manifest_digest"] = None
    unknown["manifest_identity"] = None
    unknown["license_expression_ref"] = None
    unknown["obligations_ref"] = None
    binding = build_native_artifact_binding(
        {
            "producer": "mncs-agent",
            "producer_contract": "mncs.agent.output/1",
            "identity": "artifact:generated-1",
            "content_digest": None,
        },
        [unknown],
        {
            "kind": "generation",
            "toolchain_identity": "agent-runtime:session-17",
            "event_ref": None,
            "evidence_state": "declared",
            "evidence": [{"reference": "work-log:session-17", "state": "declared"}],
        },
        [{
            "from": "spec:format-1",
            "to": "artifact:generated-1",
            "relation": "independently-implemented-against",
            "evidence_state": "declared",
            "evidence": [{"reference": "work-log:session-17", "state": "declared"}],
        }],
        source_snapshot_identity=None,
    )

    assert list(VALIDATOR.iter_errors(binding)) == []
    assert binding["rights"]["state"] == "unknown"
    assert binding["rights"]["compatibility"] == "unknown"
    assert binding["lineage"]["state"] == "partial"
    assert binding["lineage"]["relationships"][0]["evidence_state"] == "declared"
    assert binding["legal_conclusion"] == "NOT_MADE"


def test_unresolved_input_stays_in_review_and_lineage_is_never_called_complete() -> None:
    binding = build_native_artifact_binding(
        {
            "producer": "mncs-forge",
            "producer_contract": "mncs.forge.release-artifact/1",
            "identity": "artifact:release-19",
            "content_digest": "sha256:" + "f" * 64,
        },
        [_manifest("repo-a/RIGHTS.json"), _manifest("repo-b/RIGHTS.json", state="unresolved")],
        _transformation(),
        [],
        source_snapshot_identity="snapshot:source-19",
    )

    assert list(VALIDATOR.iter_errors(binding)) == []
    assert binding["rights"]["state"] == "review"
    assert binding["lineage"]["state"] == "partial"


def test_verified_attestation_needs_verifier_and_input_count_is_bounded() -> None:
    transformation = _transformation()
    transformation["evidence"] = [{"reference": "attestation:1", "state": "verified-attestation"}]
    artifact = {
        "producer": "mncs-compiler",
        "producer_contract": "mncs.compiler.application-build/11",
        "identity": "artifact:test",
        "content_digest": None,
    }
    with pytest.raises(ValueError, match="verifier_ref"):
        build_native_artifact_binding(
            artifact, [_manifest("repo-a/RIGHTS.json")], transformation, [],
            source_snapshot_identity=None,
        )

    with pytest.raises(ValueError, match="64-input bound"):
        build_native_artifact_binding(
            artifact, [_manifest(f"repo-{index}/RIGHTS.json") for index in range(65)],
            _transformation(), [], source_snapshot_identity=None,
        )
