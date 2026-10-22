from __future__ import annotations

import json
from pathlib import Path

import pytest

from mncs_rights_provenance import (
    IMPLEMENTATION_LINEAGE_EXTENSION_KEY,
    IMPLEMENTATION_LINEAGE_SCHEMA_VERSION,
    build_native_artifact_binding,
    lineage_record_from_artifact_binding,
    lineage_record_from_dict,
    normalize_implementation_lineage,
    seal_lineage_record,
    validate_lineage_structure,
    verify_lineage_digest,
)
from mncs_rights_provenance.cli import main

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(
    (ROOT / "schemas/extensions/v0.1/implementation-lineage.schema.json").read_text()
)


def _binding() -> dict:
    return build_native_artifact_binding(
        {
            "producer": "mncs-compiler",
            "producer_contract": "mncs.compiler.application-build/11",
            "identity": "artifact:app-17",
            "content_digest": "sha256:" + "a" * 64,
        },
        [],
        {
            "kind": "compilation",
            "toolchain_identity": "mncs-compiler:producer-3",
            "event_ref": "build-record:17",
            "evidence_state": "declared",
            "evidence": [{"reference": "build-record:17", "state": "declared"}],
        },
        [{
            "from": "source:snapshot-17",
            "to": "artifact:app-17",
            "relation": "compiled-from",
            "evidence_state": "declared",
            "evidence": [{"reference": "build-record:17", "state": "declared"}],
        }],
        source_snapshot_identity="source:snapshot-17",
    )


def _extension(components: list[dict], *, artifact_ref: str = "artifact:app-17") -> dict:
    status = "partial" if any(
        item["evidence_state"] != "unavailable"
        and (item["representation"] != "unknown" or item["origin"] != "unknown")
        for item in components
    ) else "unknown"
    return {
        "schema_version": IMPLEMENTATION_LINEAGE_SCHEMA_VERSION,
        "artifact_ref": artifact_ref,
        "status": status,
        "coverage": "unverified-subset",
        "components": components,
        "legal_conclusion": "NOT_MADE",
    }


def _component(
    reference: str,
    representation: str,
    origin: str,
    state: str = "declared",
) -> dict:
    evidence = [] if state == "unavailable" else [{
        "reference": f"evidence:{reference}",
        "state": state,
        **({"verifier_ref": "mncs-verifier:implementation-origin/1"}
           if state == "verified-attestation" else {}),
    }]
    return {
        "component_ref": reference,
        "representation": representation,
        "origin": origin,
        "evidence_state": state,
        "evidence": evidence,
    }


def test_implementation_lineage_keeps_native_migrated_external_and_generated_components() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.Draft202012Validator.check_schema(SCHEMA)
    extension = _extension([
        _component("source:mncs-native", "machine-native", "new-local"),
        _component("source:ported-parser", "machine-native", "migrated"),
        _component("dependency:legacy-regex", "host-language", "inherited-external"),
        _component("artifact:generated-tables", "machine-native", "generated", "inferred"),
    ])
    normalized = normalize_implementation_lineage(
        extension, expected_artifact_ref="artifact:app-17"
    )
    record = lineage_record_from_artifact_binding(
        _binding(),
        lineage_id="mncs-rights://lineage/app-17-implementation",
        binding_reference="mncs-store://artifact-binding/app-17",
        implementation_lineage=extension,
    )
    seal_lineage_record(record)
    document = record.to_dict()
    retained = document["extensions"][IMPLEMENTATION_LINEAGE_EXTENSION_KEY]

    assert list(jsonschema.Draft202012Validator(SCHEMA).iter_errors(retained)) == []
    assert validate_lineage_structure(document) == []
    assert verify_lineage_digest(document)[0]
    assert retained == normalized
    assert [(item["representation"], item["origin"]) for item in retained["components"]] == [
        ("machine-native", "new-local"),
        ("machine-native", "migrated"),
        ("host-language", "inherited-external"),
        ("machine-native", "generated"),
    ]
    assert all(item["evidence_state"] != "verified-attestation" for item in retained["components"])
    assert retained["coverage"] == "unverified-subset"
    assert retained["legal_conclusion"] == "NOT_MADE"
    assert lineage_record_from_dict(document).to_dict() == document


def test_unknown_implementation_origin_stays_unknown_and_schema_versioned() -> None:
    extension = _extension([_component("source:unavailable", "unknown", "unknown", "unavailable")])
    record = lineage_record_from_artifact_binding(
        _binding(),
        lineage_id="mncs-rights://lineage/app-17-unknown-implementation",
        binding_reference="mncs-store://artifact-binding/app-17",
        implementation_lineage=extension,
    )
    seal_lineage_record(record)

    projected = record.to_dict()["extensions"][IMPLEMENTATION_LINEAGE_EXTENSION_KEY]
    assert projected["schema_version"] == IMPLEMENTATION_LINEAGE_SCHEMA_VERSION
    assert projected["status"] == "unknown"
    assert projected["components"][0]["origin"] == "unknown"
    assert projected["components"][0]["evidence_state"] == "unavailable"
    assert projected["components"][0]["evidence"] == []
    assert validate_lineage_structure(record.to_dict()) == []


def test_implementation_lineage_rejects_wrong_artifact_and_unverified_attestation() -> None:
    with pytest.raises(ValueError, match="does not match"):
        lineage_record_from_artifact_binding(
            _binding(),
            lineage_id="mncs-rights://lineage/wrong-artifact",
            binding_reference="store://binding/wrong-artifact",
            implementation_lineage=_extension([
                _component("source:one", "machine-native", "migrated")
            ], artifact_ref="artifact:other"),
        )

    invalid = _extension([{
        "component_ref": "source:verified",
        "representation": "machine-native",
        "origin": "migrated",
        "evidence_state": "verified-attestation",
        "evidence": [{"reference": "attestation:1", "state": "verified-attestation"}],
    }])
    with pytest.raises(ValueError, match="verifier_ref"):
        normalize_implementation_lineage(invalid)

    unavailable_claim = _extension([
        _component("source:unsupported", "machine-native", "migrated", "unavailable")
    ])
    with pytest.raises(ValueError, match="unknown classifications"):
        normalize_implementation_lineage(unavailable_claim)


def test_implementation_lineage_cli_preserves_extension_in_digest_bound_output(
    tmp_path: Path, capsys,
) -> None:
    binding_path = tmp_path / "binding.json"
    extension_path = tmp_path / "implementation-lineage.json"
    binding_path.write_text(json.dumps(_binding()), encoding="utf-8")
    extension_path.write_text(json.dumps(_extension([
        _component("source:ported", "machine-native", "migrated")
    ])), encoding="utf-8")

    with pytest.raises(SystemExit) as result:
        main([
            "lineage", "from-artifact-binding", str(binding_path),
            "--lineage-id", "mncs-rights://lineage/cli-implementation",
            "--reference", "store://binding/cli-implementation",
            "--implementation-lineage", str(extension_path),
        ])

    document = json.loads(capsys.readouterr().out)
    assert result.value.code == 0
    assert validate_lineage_structure(document) == []
    assert verify_lineage_digest(document)[0]
    assert document["extensions"][IMPLEMENTATION_LINEAGE_EXTENSION_KEY]["components"][0]["origin"] == "migrated"


def test_live_compiler_binding_example_preserves_unknown_implementation_origin() -> None:
    binding = json.loads(
        (ROOT / "evidence/rights-handoff-native-artifact-binding-20261021.json").read_text()
    )
    extension = json.loads(
        (ROOT / "examples/v0.4/implementation-lineage-rights-handoff.json").read_text()
    )
    expected = json.loads(
        (ROOT / "examples/v0.4/lineage-from-live-compiler-binding-with-implementation-lineage.json").read_text()
    )

    record = lineage_record_from_artifact_binding(
        binding,
        lineage_id="mncs-rights://lineage/rights-handoff-compiler-build-implementation-20261022",
        binding_reference=(
            "mncs-rights-provenance:evidence/"
            "rights-handoff-native-artifact-binding-20261021.json"
        ),
        implementation_lineage=extension,
    )
    seal_lineage_record(record)
    actual = record.to_dict()
    retained = actual["extensions"][IMPLEMENTATION_LINEAGE_EXTENSION_KEY]
    jsonschema = pytest.importorskip("jsonschema")

    assert actual == expected
    assert validate_lineage_structure(actual) == []
    assert verify_lineage_digest(actual)[0]
    assert list(jsonschema.Draft202012Validator(SCHEMA).iter_errors(retained)) == []
    component = retained["components"][0]
    assert component["representation"] == "machine-native"
    assert component["origin"] == "unknown"
    assert component["evidence_state"] == "declared"
    assert retained["coverage"] == "unverified-subset"
    assert retained["legal_conclusion"] == "NOT_MADE"
