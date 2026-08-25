"""Manifest round-trip, identity, validation, graph, evidence, SPDX tests."""

from __future__ import annotations

import json
from copy import deepcopy

import pytest

from mncs_rights_provenance.canonical import canonical_bytes, sha256_hex
from mncs_rights_provenance.evidence import (
    EvidenceRecord,
    compute_evidence_digest,
    evidence_record_from_dict,
    seal_evidence_record,
    verify_evidence_digest,
)
from mncs_rights_provenance.graph import check_graph_integrity
from mncs_rights_provenance.manifest import (
    SCHEMA_VERSION,
    compute_manifest_identity,
    manifest_from_dict,
    manifest_to_dict,
    seal_manifest,
)
from mncs_rights_provenance.spdx import export_spdx, import_spdx_sources, is_valid_spdx_expression
from mncs_rights_provenance.validation import validate_evidence_structure, validate_manifest_structure


def sample_manifest() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact": {"id": "example/project#artifact", "class": "source-code", "commit": "cafebabe"},
        "provenance": {
            "origin_classification": "human-ai-assisted",
            "participants": [
                {"type": "human", "role": "developer", "name": "Example Human"},
                {"type": "model", "role": "assistant", "model": "example-model"},
            ],
            "process_evidence": [
                {
                    "kind": "fabric-receipt",
                    "reference": "mncs-fabric://execution/abc123",
                    "sha256": "a" * 64,
                }
            ],
            "graph": {
                "nodes": [
                    {"id": "src", "kind": "artifact", "artifact_class": "source-code"},
                    {"id": "gen", "kind": "action", "label": "assisted edit"},
                    {"id": "out", "kind": "artifact", "artifact_class": "source-code"},
                ],
                "edges": [
                    {"from": "src", "to": "gen", "relation": "transformed-by"},
                    {"from": "gen", "to": "out", "relation": "derived-from"},
                ],
            },
        },
        "rights": {
            "distribution_license": "Apache-2.0",
            "copyright_status": "mixed-or-undetermined",
            "rights_basis": "contributor-attested",
            "third_party_material": "none-known",
            "sources": [],
        },
        "review": {
            "technical_validation": "passed",
            "provenance_validation": "passed",
            "human_acceptance": "accepted",
            "reviewer": "maintainer",
        },
    }


def test_round_trip_preserves_content() -> None:
    document = seal_manifest(sample_manifest())
    manifest = manifest_from_dict(document)
    rebuilt = manifest_to_dict(manifest)
    assert compute_manifest_identity(document) == compute_manifest_identity(rebuilt)


def test_deterministic_identity() -> None:
    document = sample_manifest()
    first = compute_manifest_identity(document)
    second = compute_manifest_identity(deepcopy(document))
    assert first == second == sha256_hex({k: v for k, v in document.items() if k != "manifest_identity"})


def test_identity_changes_when_content_changes() -> None:
    document = sample_manifest()
    before = compute_manifest_identity(document)
    mutated = deepcopy(document)
    mutated["rights"]["third_party_material"] = "possible"
    assert compute_manifest_identity(mutated) != before


def test_structural_validity_happy_path() -> None:
    issues = validate_manifest_structure(seal_manifest(sample_manifest()))
    assert issues == []


@pytest.mark.parametrize(
    "mutation,expected_fragment",
    [
        (lambda d: d.update(schema_version="0.1.0"), "schema_version"),
        (lambda d: d["artifact"].update({"class": "not-a-class"}), "invalid artifact.class"),
        (lambda d: d["rights"].update(copyright_status="totally-legal"), "copyright_status invalid"),
        (lambda d: d["provenance"].update(origin_classification="blessed-by-ai"), "origin_classification"),
        (lambda d: d["review"].update(human_acceptance="sure"), "human_acceptance invalid"),
        (lambda d: d["artifact"].update(paths=["a.py", "a.py"]), "duplicates"),
    ],
)
def test_structural_rejections(mutation, expected_fragment) -> None:
    document = sample_manifest()
    mutation(document)
    issues = validate_manifest_structure(document)
    assert any(expected_fragment in issue for issue in issues), issues


def test_graph_cycle_detection() -> None:
    document = sample_manifest()
    document["provenance"]["graph"]["edges"].append({"from": "out", "to": "src", "relation": "referenced"})
    ok, issues = check_graph_integrity(document)
    assert not ok
    assert any("cycle" in issue for issue in issues)


def test_graph_self_loop_detection() -> None:
    document = sample_manifest()
    document["provenance"]["graph"]["edges"].append({"from": "src", "to": "src", "relation": "referenced"})
    ok, issues = check_graph_integrity(document)
    assert not ok
    assert any("self-loop" in issue for issue in issues)


def test_unknown_extensions_preserved_not_interpreted() -> None:
    document = seal_manifest(sample_manifest())
    document["extensions"] = {"mncs-fabric:node-label": "worker-01"}
    assert validate_manifest_structure(document) == []
    manifest = manifest_from_dict(document)
    rebuilt = manifest_to_dict(manifest)
    assert rebuilt["extensions"]["mncs-fabric:node-label"] == "worker-01"


def test_evidence_round_trip_and_tamper_detection() -> None:
    record = EvidenceRecord(
        evidence_id="mncs-fabric://execution/rec-1",
        kind="fabric-execution",
        producer={
            "producer": "mncs-fabric",
            "recordKind": "ExecutionEvidence",
            "schemaVersion": "0.1",
            "stableId": "mncs-fabric://execution/rec-1",
        },
        subject={"artifact_refs": [{"id": "example/project#artifact", "role": "output"}]},
        claims=[
            {
                "claim_type": "unknown-license-state",
                "statement": "No license metadata observed for dependency X.",
                "confidence": "insufficient-evidence",
            }
        ],
        limitations=["Fabric does not determine licensing."],
    )
    sealed = seal_evidence_record(record)
    document = json.loads(json.dumps(sealed.to_dict()))
    assert verify_evidence_digest(document)[0]
    tampered = deepcopy(document)
    tampered["claims"][0]["statement"] = "Everything is definitely fine."
    ok, expected = verify_evidence_digest(tampered)
    assert not ok
    assert expected == compute_evidence_digest(tampered)

    parsed = evidence_record_from_dict(document)
    assert parsed.claims[0]["confidence"] == "insufficient-evidence"
    assert validate_evidence_structure(document) == []


def test_spdx_expression_checks() -> None:
    assert is_valid_spdx_expression("Apache-2.0")
    assert is_valid_spdx_expression("MIT OR Apache-2.0")
    assert is_valid_spdx_expression("(MIT OR GPL-2.0-only WITH Classpath-exception-2.0)")
    assert not is_valid_spdx_expression("")
    assert not is_valid_spdx_expression("Not A License!!")


def test_spdx_export_import_round_trip() -> None:
    document = seal_manifest(sample_manifest())
    document["rights"]["sources"] = [
        {
            "kind": "package",
            "reference": "pypi.org/project/zstandard",
            "license_status": "compatible",
            "license": "BSD-3-Clause",
        }
    ]
    spdx_document = export_spdx(document)
    assert spdx_document["spdxVersion"] == "SPDX-2.3"
    assert spdx_document["packages"][0]["licenseDeclared"] == "Apache-2.0"
    assert spdx_document["dataLicense"] == "CC0-1.0"
    sources = import_spdx_sources(spdx_document)
    # Import maps every SPDX package; both ours and the declared dependency
    # appear, each as declaration-evidence only.
    licenses = {source["license"] for source in sources}
    assert licenses == {"Apache-2.0", "BSD-3-Clause"}
    dependency = next(s for s in sources if s["license"] == "BSD-3-Clause")
    assert dependency["kind"] == "package"
    assert dependency["confidence"] == "observed-declaration"
