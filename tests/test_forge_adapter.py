from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from mncs_rights_provenance import build_forge_provider_artifact_binding
from mncs_rights_provenance.cli import MAX_FORGE_BINDING_REQUEST_BYTES, main
from mncs_rights_provenance.forge_adapter import BUILD_BINDING_REQUEST_SCHEMA

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas/v0.1/native-artifact-binding.schema.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA)
REQUEST_SCHEMA = json.loads(
    (ROOT / "schemas/v0.1/forge-build-binding-request.schema.json").read_text()
)
REQUEST_VALIDATOR = Draft202012Validator(REQUEST_SCHEMA)


def _digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def _build_receipt() -> dict:
    core = {
        "inputs": {
            "provider": "fixture-provider",
            "declaration_identity": "1" * 64,
            "source_inputs": {
                "mncs-rights-provenance:src/example.mncs": "2" * 64,
                "mncs-rights-provenance:src/helper.mncs": "3" * 64,
            },
            "compiler_artifact_sha256": "4" * 64,
            "build_transport_sha256": "5" * 64,
            "configuration": {"target": "fixture"},
            "dependency_roots": [
                {
                    "repository": "mncs-language",
                    "path": "stdlib",
                    "content_identity": "6" * 64,
                }
            ],
            "stdlib": "fixture-stdlib",
            "abi": {"backend_schema": "mncs.backend/1"},
        },
        "artifact": {
            "address": "artifacts/example.json",
            "sha256": "7" * 64,
            "identity": "compiler-artifact:example",
            "payload_sha256": "8" * 64,
            "interface_identity": "9" * 64,
            "schema_version": "mncs.backend/1",
            "backend": "fixture",
            "target": "target:fixture",
        },
        "inventory_identity": "a" * 64,
        "build_capability": {"reference": "capability:build"},
        "build_invocation_identity": "b" * 64,
        "remediation_admission": {"status": "admitted"},
    }
    return {
        "schema_version": "mncs.provider-build-receipt/1",
        "identity": _digest(core),
        "core": core,
    }


def _manifest(reference: str, rights_state: str) -> dict:
    return {
        "reference": reference,
        "manifest_digest": "sha256:" + "c" * 64,
        "manifest_identity": "d" * 64,
        "evidence_state": "declared",
        "rights_state": rights_state,
        "license_expression_ref": reference + "#/rights/distribution_license",
        "obligations_ref": reference + "#/rights/license_terms",
    }


def test_forge_receipt_projects_declared_inputs_and_compilation_event() -> None:
    binding = build_forge_provider_artifact_binding(
        _build_receipt(),
        [_manifest("project/RIGHTS.json", "declared")],
        context_identity="sha256:" + "e" * 64,
    )

    assert list(VALIDATOR.iter_errors(binding)) == []
    assert binding["artifact"] == {
        "producer": "mncs-forge",
        "producer_contract": "mncs.provider-build-receipt/1",
        "identity": "compiler-artifact:example",
        "content_digest": "sha256:" + "7" * 64,
    }
    assert binding["rights"]["state"] == "declared"
    assert binding["rights"]["compatibility"] == "unknown"
    assert binding["lineage"]["state"] == "partial"
    assert binding["lineage"]["source_snapshot_identity"] is None
    assert binding["lineage"]["transformation"]["kind"] == "compilation"
    assert binding["lineage"]["transformation"]["evidence_state"] == "declared"
    assert [edge["relation"] for edge in binding["lineage"]["relationships"]] == [
        "depends-upon",
        "depends-upon",
        "depends-upon",
    ]
    assert all(edge["evidence_state"] == "declared" for edge in binding["lineage"]["relationships"])
    assert binding["legal_conclusion"] == "NOT_MADE"


def test_missing_or_unresolved_rights_remain_unknown_or_review() -> None:
    metadata_receipt = _build_receipt()
    metadata_receipt["core"]["inputs"]["configuration"]["license"] = "MIT"
    metadata_receipt["identity"] = _digest(metadata_receipt["core"])
    unknown = build_forge_provider_artifact_binding(metadata_receipt)
    unresolved = build_forge_provider_artifact_binding(
        _build_receipt(), [_manifest("dependency/RIGHTS.json", "unresolved")]
    )

    assert unknown["rights"]["state"] == "unknown"
    assert unknown["rights"]["contributing_manifests"] == []
    assert unresolved["rights"]["state"] == "review"
    assert unknown["legal_conclusion"] == unresolved["legal_conclusion"] == "NOT_MADE"


def test_adapter_rejects_tampered_receipt_identity_and_unbounded_inputs() -> None:
    tampered = _build_receipt()
    tampered["core"]["artifact"]["identity"] = "changed"
    with pytest.raises(ValueError, match="does not match its core"):
        build_forge_provider_artifact_binding(tampered)

    oversized = _build_receipt()
    oversized["core"]["inputs"]["source_inputs"] = {
        f"repository:source-{index}.mncs": f"{index:064x}" for index in range(65)
    }
    oversized["identity"] = _digest(oversized["core"])
    with pytest.raises(ValueError, match="64-item input bounds"):
        build_forge_provider_artifact_binding(oversized)


def test_bounded_cli_emits_the_machine_binding(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    request_path = tmp_path / "forge-binding-request.json"
    request = {
        "schema_version": BUILD_BINDING_REQUEST_SCHEMA,
        "build_receipt": _build_receipt(),
        "contributing_manifests": [_manifest("project/RIGHTS.json", "declared")],
        "context_identity": "sha256:" + "e" * 64,
    }
    assert list(REQUEST_VALIDATOR.iter_errors(request)) == []
    request_path.write_text(json.dumps(request))

    with pytest.raises(SystemExit) as result:
        main(["artifact-binding", "forge-build", str(request_path)])

    output = json.loads(capsys.readouterr().out)
    assert result.value.code == 0
    assert list(VALIDATOR.iter_errors(output)) == []
    assert output["artifact"]["producer"] == "mncs-forge"
    assert output["rights"]["context_identity"] == request["context_identity"]


def test_cli_rejects_oversized_request_before_parsing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    request_path = tmp_path / "oversized-request.json"
    request_path.write_bytes(b" " * (MAX_FORGE_BINDING_REQUEST_BYTES + 1))

    with pytest.raises(SystemExit) as result:
        main(["artifact-binding", "forge-build", str(request_path)])

    output = json.loads(capsys.readouterr().out)
    assert result.value.code == 2
    assert output["ok"] is False
    assert output["legal_conclusion"] == "NOT_MADE"
    assert "2 MiB" in output["error"]
