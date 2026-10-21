from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from mncs_rights_provenance import build_agent_context, build_compiler_application_artifact_binding
from mncs_rights_provenance.artifact_binding import diagnose_native_artifact_binding
from mncs_rights_provenance.cli import MAX_COMPILER_BINDING_REQUEST_BYTES, main
from mncs_rights_provenance.compiler_adapter import (
    APPLICATION_BUILD_SCHEMA,
    COMPILER_BINDING_REQUEST_SCHEMA,
)

ROOT = Path(__file__).resolve().parents[1]
NATIVE_SCHEMA = json.loads((ROOT / "schemas/v0.1/native-artifact-binding.schema.json").read_text())
NATIVE_VALIDATOR = Draft202012Validator(NATIVE_SCHEMA)
REQUEST_SCHEMA = json.loads(
    (ROOT / "schemas/v0.1/compiler-build-binding-request.schema.json").read_text()
)
REQUEST_VALIDATOR = Draft202012Validator(REQUEST_SCHEMA)


def _digest(character: str) -> str:
    return "sha256:" + character * 64


def _application_build() -> dict:
    artifact_identity = _digest("a")
    return {
        "schema_version": APPLICATION_BUILD_SCHEMA,
        "status": "verified",
        "source_snapshot": {
            "identity": _digest("b"),
            "files": [
                {"module": "root", "source_id": "demo", "sha256": _digest("c")},
                {"module": "demo.lib", "source_id": "demo.lib", "sha256": _digest("d")},
            ],
        },
        "dependency_graph": {
            "identity": _digest("e"),
            "details": {
                "root_module": "demo",
                "dependencies": ["demo.lib"],
                "resolutions": [],
            },
        },
        "producer": {
            "stage0_toolchain": {
                "schema": "mncs.compiler.toolchain-identity/1",
                "bootstrap_tree_sha256": _digest("f"),
            },
            "probe": {
                "kind": "mncs.stage0-reference-compiler",
                "probe_executable_sha256": _digest("1"),
            },
        },
        "build_assumptions": {"license": "MIT"},
        "artifact": {
            "identity": artifact_identity,
            "value": {
                "schema_version": "mncs.vm.artifact/1",
                "artifact_id": artifact_identity,
                "source": {
                    "selected_ssa_identity": "mncs:compiler:ssa:selected-1",
                    "lowering_refs": [
                        "mncs:compiler:ssa:result-1",
                        "application-ssa-closure/1:" + "2" * 64,
                    ],
                },
            },
        },
    }


def _manifest(reference: str, rights_state: str = "declared") -> dict:
    return {
        "reference": reference,
        "manifest_digest": _digest("3"),
        "manifest_identity": "4" * 64,
        "evidence_state": "declared",
        "rights_state": rights_state,
        "license_expression_ref": reference + "#/rights/distribution_license",
        "obligations_ref": reference + "#/rights/license_terms",
    }


def test_compiler_application_build_projects_source_lineage_and_ir_references() -> None:
    binding = build_compiler_application_artifact_binding(
        _application_build(),
        [_manifest("project/RIGHTS.json")],
        context_identity=_digest("5"),
    )

    assert list(NATIVE_VALIDATOR.iter_errors(binding)) == []
    assert binding["artifact"]["producer"] == "mncs-compiler"
    assert binding["artifact"]["producer_contract"] == APPLICATION_BUILD_SCHEMA
    assert binding["artifact"]["identity"] == _digest("a")
    assert binding["rights"]["state"] == "declared"
    assert binding["rights"]["compatibility"] == "unknown"
    assert binding["rights"]["context_identity"] == _digest("5")
    assert binding["lineage"]["source_snapshot_identity"] == _digest("b")
    assert binding["lineage"]["state"] == "partial"
    assert binding["lineage"]["transformation"]["kind"] == "compilation"
    assert binding["lineage"]["transformation"]["evidence_state"] == "declared"
    assert binding["lineage"]["transformation"]["toolchain_identity"].endswith("1" * 64)
    relationships = binding["lineage"]["relationships"]
    assert [item["relation"] for item in relationships] == [
        "compiled-from", "compiled-from", "transformed-by",
    ]
    assert all(item["evidence_state"] == "declared" for item in relationships)
    transformation_refs = {
        item["reference"] for item in binding["lineage"]["transformation"]["evidence"]
    }
    assert "mncs-compiler:application-ssa-closure/1:" + "2" * 64 in transformation_refs
    assert "mncs-compiler:selected-ssa/mncs:compiler:ssa:selected-1" in transformation_refs
    assert "mncs-compiler:dependency-graph/" + _digest("e") in transformation_refs
    assert binding["legal_conclusion"] == "NOT_MADE"


def test_missing_rights_remain_unknown_even_when_compiler_metadata_mentions_a_license() -> None:
    binding = build_compiler_application_artifact_binding(_application_build())

    assert binding["rights"]["state"] == "unknown"
    assert binding["rights"]["contributing_manifests"] == []
    assert binding["legal_conclusion"] == "NOT_MADE"


def test_candidate_context_flows_into_compiler_artifact_binding_with_uncertainty_preserved() -> None:
    manifest = json.loads((ROOT / "RIGHTS.json").read_text())
    manifest["rights"]["distribution_license"] = "LicenseRef-MNCS-Permissive-0.1"
    governance = json.loads((ROOT / "governance/agent-governance.json").read_text())
    context = build_agent_context(
        manifest,
        governance,
        binding={
            "authorized": True,
            "profile_id": governance["profile_id"],
            "authority": {
                "issuer": "mncs-environment",
                "basis": "explicit-environment-owner-binding",
                "source_ref": ".mncs/environment.json#/rights_context",
                "scope": ["mncs-rights-provenance"],
            },
            "context_budget_bytes": 8192,
        },
    )
    artifact_binding = build_compiler_application_artifact_binding(
        _application_build(),
        [_manifest("project/RIGHTS.json", "unresolved")],
        context_identity=context["identity"],
    )

    diagnostics = {item["code"] for item in context["diagnostics"]}
    assert "license-candidate-not-effective" in diagnostics
    assert context["rights"]["license_terms"]["candidate_references"] == [
        "LicenseRef-MNCS-Permissive-0.1",
    ]
    assert artifact_binding["rights"]["state"] == "review"
    assert artifact_binding["rights"]["context_identity"] == context["identity"]
    assert artifact_binding["rights"]["compatibility"] == "unknown"
    assert artifact_binding["legal_conclusion"] == "NOT_MADE"
    diagnostic_report = diagnose_native_artifact_binding(artifact_binding)
    assert diagnostic_report["status"] == "review"
    assert diagnostic_report["diagnostics"][0]["code"] == "artifact-rights-unresolved"
    assert diagnostic_report["legal_conclusion"] == "NOT_MADE"


def test_compiler_adapter_rejects_unverified_or_inconsistent_build_results() -> None:
    unknown = _application_build()
    unknown["status"] = "unknown"
    with pytest.raises(ValueError, match="status 'verified'"):
        build_compiler_application_artifact_binding(unknown)

    tampered = _application_build()
    tampered["artifact"]["identity"] = _digest("9")
    with pytest.raises(ValueError, match="does not match artifact.value.artifact_id"):
        build_compiler_application_artifact_binding(tampered)

    missing_closure = _application_build()
    missing_closure["artifact"]["value"]["source"]["lowering_refs"] = []
    with pytest.raises(ValueError, match="one SSA closure reference"):
        build_compiler_application_artifact_binding(missing_closure)


def test_compiler_binding_request_schema_and_bounded_cli(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    request = {
        "schema_version": COMPILER_BINDING_REQUEST_SCHEMA,
        "application_build": _application_build(),
        "contributing_manifests": [_manifest("project/RIGHTS.json")],
        "context_identity": _digest("6"),
    }
    Draft202012Validator.check_schema(REQUEST_SCHEMA)
    assert list(REQUEST_VALIDATOR.iter_errors(request)) == []
    request_path = tmp_path / "compiler-binding-request.json"
    request_path.write_text(json.dumps(request))

    with pytest.raises(SystemExit) as result:
        main(["artifact-binding", "compiler-build", str(request_path)])

    output = json.loads(capsys.readouterr().out)
    assert result.value.code == 0
    assert list(NATIVE_VALIDATOR.iter_errors(output)) == []
    assert output["artifact"]["producer"] == "mncs-compiler"

    oversized_path = tmp_path / "oversized-request.json"
    oversized_path.write_bytes(b" " * (MAX_COMPILER_BINDING_REQUEST_BYTES + 1))
    with pytest.raises(SystemExit) as oversized_result:
        main(["artifact-binding", "compiler-build", str(oversized_path)])
    error = json.loads(capsys.readouterr().out)
    assert oversized_result.value.code == 2
    assert error["legal_conclusion"] == "NOT_MADE"
    assert "2 MiB" in error["error"]
