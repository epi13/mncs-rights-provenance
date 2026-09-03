"""Distributed-pressure provenance tests: lineage, authority, promotion.

Covers the systems scenarios required for the six-repository coordinated
workflow: normal lifecycle, cross-repository ChangeSets, conflicting
evidence, unknown provenance, supersession, duplicate pressure, partial
failure, tampering, golden-vector agreement, authority/identity separation,
and v0.2 backward compatibility.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from mncs_rights_provenance.authority import (
    ActorRef,
    AuthorityClaim,
    authority_claim_from_dict,
    authority_verdict,
)
from mncs_rights_provenance.lineage import (
    compute_lineage_digest,
    lineage_record_from_dict,
    lineage_verdict,
    migrate_manifest_02_to_03,
    seal_lineage_record,
    verify_lineage_digest,
)
from mncs_rights_provenance.manifest import (
    compute_manifest_identity,
    manifest_from_dict,
    manifest_to_dict,
    seal_manifest,
)
from mncs_rights_provenance.promotion import (
    combine_verdict,
    promotion_combined,
    promotion_inputs_from_dict,
    promotion_report,
)
from mncs_rights_provenance.validation import (
    validate_lineage_structure,
    validate_manifest_structure,
)

CONFORMANCE = Path(__file__).resolve().parents[1] / "conformance"


def _pressure_vectors() -> list[dict]:
    return json.loads((CONFORMANCE / "pressure-golden-vectors.json").read_text())["cases"]


def _all_pass_dimensions() -> dict:
    return {
        name: {"verdict": "pass"}
        for name in (
            "technical",
            "test_conformance",
            "compiler_backend",
            "coordination_dependency",
            "provenance",
            "authority",
            "rights_license",
            "policy",
        )
    }


def _lineage_doc(**overrides) -> dict:
    doc = {
        "schema_version": "0.3.0",
        "lineage_id": "mncs-rights://lineage/test-chain",
        "subject": {"artifact_refs": [{"id": "example/app#feature", "role": "output"}]},
        "changesets": [{"changeset_id": "changeset/test-001"}],
        "derivations": [{"from": "src", "to": "out", "relation": "derived-from"}],
        "contributions": [
            {
                "contributor": {"type": "human", "actor_class": "human", "role": "author"},
                "contribution_id": "contrib-1",
                "changeset_id": "changeset/test-001",
            }
        ],
        "evaluations": [
            {
                "evaluator": "forge",
                "evaluator_version": "0.1",
                "verdict": "pass",
                "binding": "advisory",
            }
        ],
        "authority_claims": [
            {
                "subject": {"type": "human", "role": "author"},
                "scope": "may_propose",
                "asserted_by": "maintainer",
                "verdict": "pass",
            }
        ],
        "capability_gap_links": [{"gap_ref": "gap/test-001", "relation": "reports-gap"}],
        "promotion_dimensions": _all_pass_dimensions(),
        "lifecycle": {"to_state": "evaluating"},
        "unresolved": [],
    }
    doc.update(overrides)
    sealed = seal_lineage_record(lineage_record_from_dict({**doc}))
    return sealed.to_dict()


# ---- Golden-vector agreement (Python mirrors the MNCS-language core) --------


@pytest.mark.parametrize("case", _pressure_vectors())
def test_pressure_golden_vectors(case: dict) -> None:
    function = case["function"]
    inputs = case["inputs"]
    if function == "combine_verdict":
        assert (
            combine_verdict(inputs["left"].lower(), inputs["right"].lower())
            == case["output"].lower()
        )
    elif function == "promotion_combined":
        lowered = {key: {"verdict": value.lower()} for key, value in inputs.items()}
        result = promotion_combined(promotion_inputs_from_dict(lowered))
        assert result == case["output"].lower()
    elif function == "authority_verdict":
        assert (
            authority_verdict(
                scope_matches=inputs["scope_matches"],
                evidence_present=inputs["evidence_present"],
                approval_present=inputs["approval_present"],
            )
            == case["output"].lower()
        )
    elif function == "lineage_verdict":
        assert (
            lineage_verdict(
                has_changeset=inputs["has_changeset"],
                has_derivation=inputs["has_derivation"],
                has_producer=inputs["has_producer"],
                evidence_bound=inputs["evidence_bound"],
                tamper_detected=inputs["tamper_detected"],
            )
            == case["output"].lower()
        )
    else:  # pragma: no cover
        raise AssertionError(f"unknown golden function {function!r}")


def test_combine_verdict_ordering() -> None:
    assert combine_verdict("fail", "pass") == "fail"
    assert combine_verdict("fail", "unknown") == "fail"
    assert combine_verdict("unknown", "pass") == "unknown"
    assert combine_verdict("pass", "pass") == "pass"
    assert combine_verdict("unknown", "unknown") == "unknown"
    with pytest.raises(ValueError):
        combine_verdict("pass", "certain")


def test_promotion_dimensions_stay_independent() -> None:
    """A FAIL in one dimension never fabricates conclusions in others."""
    dimensions = _all_pass_dimensions()
    dimensions["rights_license"] = {"verdict": "fail"}
    report = promotion_report(promotion_inputs_from_dict(dimensions))
    assert report["combined"] == "fail"
    assert report["dimensions"]["technical"]["verdict"] == "pass"
    assert report["dimensions"]["rights_license"]["verdict"] == "fail"
    # UNKNOWN does not become PASS and does not erase the failing dimension.
    dimensions["provenance"] = {"verdict": "unknown"}
    report = promotion_report(promotion_inputs_from_dict(dimensions))
    assert report["combined"] == "fail"
    assert report["dimensions"]["provenance"]["verdict"] == "unknown"


# ---- Normal lifecycle --------------------------------------------------------


def test_normal_lifecycle_lineage() -> None:
    """pressure -> gap -> proposal -> implementation -> evidence -> Forge
    evaluation -> rights/provenance linkage -> promotion inputs."""
    doc = _lineage_doc(
        lineage_id="mncs-rights://lineage/lifecycle-demo",
        lifecycle={"from_state": "proposed", "to_state": "evaluating"},
    )
    assert validate_lineage_structure(doc) == []
    ok, _ = verify_lineage_digest(doc)
    assert ok
    record = lineage_record_from_dict(doc)
    assert record.changesets[0]["changeset_id"] == "changeset/test-001"
    assert record.capability_gap_links[0]["gap_ref"] == "gap/test-001"
    assert record.lifecycle is not None and record.lifecycle["to_state"] == "evaluating"
    assert record.promotion_dimensions is not None
    assert promotion_combined(record.promotion_dimensions) == "pass"


def test_manifest_lineage_block_binds_changeset() -> None:
    manifest = {
        "schema_version": "0.3.0",
        "artifact": {"id": "example/app#feature", "class": "source-code"},
        "provenance": {
            "origin_classification": "human-ai-assisted",
            "participants": [{"type": "human", "role": "developer"}],
            "process_evidence": [],
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
            "human_acceptance": "not-reviewed",
        },
        "lineage": {
            "changesets": [{"changeset_id": "changeset/test-001"}],
            "capability_gaps": ["gap/test-001"],
            "promotion_dimensions": _all_pass_dimensions(),
        },
    }
    assert validate_manifest_structure(seal_manifest(manifest)) == []
    parsed = manifest_from_dict(seal_manifest(manifest))
    assert parsed.lineage is not None
    assert parsed.lineage["changesets"][0]["changeset_id"] == "changeset/test-001"
    rebuilt = manifest_to_dict(parsed)
    assert compute_manifest_identity(rebuilt) == compute_manifest_identity(seal_manifest(manifest))


# ---- Cross-repository ChangeSet ----------------------------------------------


def test_cross_repository_changeset_keeps_lineage() -> None:
    """One logical ChangeSet spanning three repositories stays reconstructable."""
    doc = _lineage_doc(
        lineage_id="mncs-rights://lineage/xrepo-001",
        changesets=[
            {
                "changeset_id": "changeset/xrepo-001",
                "final_tree": "tree:abc123",
                "base_revisions": [
                    {"repository": "example/app", "commit": "aaa1111"},
                    {"repository": "example/mncs-language", "commit": "bbb2222"},
                    {"repository": "example/stdlib", "commit": "ccc3333"},
                ],
            }
        ],
        derivations=[
            {"from": "app:pressure", "to": "lang:gap/test-001", "relation": "gap-derived-from"},
            {"from": "lang:gap/test-001", "to": "lang:change/bbb2222", "relation": "resolves-gap"},
            {"from": "lang:change/bbb2222", "to": "app:adoption", "relation": "derived-from"},
            {"from": "app:adoption", "to": "changeset/xrepo-001", "relation": "member-of"},
        ],
    )
    assert validate_lineage_structure(doc) == []
    record = lineage_record_from_dict(doc)
    relations = [edge["relation"] for edge in record.derivations]
    assert "gap-derived-from" in relations
    assert "resolves-gap" in relations
    assert "member-of" in relations
    # The resolving change links the original gap: "why does this feature exist"
    # is answerable from the chain.
    assert any(
        edge["from"] == "lang:gap/test-001" and edge["relation"] == "resolves-gap"
        for edge in record.derivations
    )


# ---- Conflicting evidence -----------------------------------------------------


def test_conflicting_evidence_coexists_without_fabricated_certainty() -> None:
    """Two incompatible evaluations remain visible; combination is not PASS."""
    first = _lineage_doc(
        lineage_id="mncs-rights://lineage/conflict-a",
        evaluations=[{"evaluator": "forge-a", "verdict": "pass", "binding": "advisory"}],
    )
    second = _lineage_doc(
        lineage_id="mncs-rights://lineage/conflict-b",
        evaluations=[{"evaluator": "forge-b", "verdict": "fail", "binding": "advisory"}],
    )
    assert validate_lineage_structure(first) == []
    assert validate_lineage_structure(second) == []
    # Policy consumers combine per-dimension: fail dominates; the conflict is
    # preserved as two records, not merged into one PASS.
    combined = combine_verdict("pass", "fail")
    assert combined == "fail"
    # Conflicting attestations are likewise preserved, not resolved by format.
    manifest = {
        "schema_version": "0.3.0",
        "artifact": {"id": "example/app#x", "class": "source-code"},
        "provenance": {
            "origin_classification": "origin-uncertain",
            "participants": [],
            "process_evidence": [],
        },
        "rights": {
            "distribution_license": "Apache-2.0",
            "copyright_status": "unresolved",
            "rights_basis": "unknown-needs-review",
            "third_party_material": "unknown",
            "sources": [],
        },
        "review": {
            "technical_validation": "not-run",
            "provenance_validation": "not-run",
            "human_acceptance": "not-reviewed",
        },
        "attestations": [
            {
                "assertion_type": "derivation",
                "assertedBy": "agent-a",
                "assertedAt": "2026-09-01T00:00:00Z",
                "statement": "derived from X",
            },
            {
                "assertion_type": "derivation",
                "assertedBy": "agent-b",
                "assertedAt": "2026-09-01T01:00:00Z",
                "statement": "derived from Y, not X",
            },
        ],
    }
    assert validate_manifest_structure(manifest) == []


# ---- Unknown provenance --------------------------------------------------------


def test_unknown_provenance_stays_unknown() -> None:
    doc = _lineage_doc(
        lineage_id="mncs-rights://lineage/unknown-origin",
        contributions=[],
        authority_claims=[],
        unresolved=["origin", "authority", "producer"],
    )
    assert validate_lineage_structure(doc) == []
    # Missing actor/authority evidence is UNKNOWN, never defaulted.
    assert (
        authority_verdict(scope_matches=True, evidence_present=False, approval_present=False)
        == "unknown"
    )
    assert (
        lineage_verdict(
            has_changeset=False,
            has_derivation=False,
            has_producer=False,
            evidence_bound=False,
            tamper_detected=False,
        )
        == "unknown"
    )
    actor = ActorRef()
    assert actor.actor_type == "unknown"
    assert actor.actor_class == "unknown"


def test_authority_is_not_identity() -> None:
    """Knowing the producer implies nothing about permission."""
    claim = AuthorityClaim(
        subject=ActorRef(actor_type="agent", actor_class="autonomous-agent", role="proposer"),
        scope="may_promote",
        asserted_by="maintainer",
        verdict="unknown",
        unresolved=("promotion-authority",),
    )
    assert claim.subject.actor_class == "autonomous-agent"
    assert claim.verdict == "unknown"
    # Same identity, different scopes and verdicts coexist.
    allowed = AuthorityClaim(
        subject=claim.subject, scope="may_propose", asserted_by="maintainer", verdict="pass"
    )
    assert allowed.verdict == "pass"
    assert authority_claim_from_dict(allowed.to_dict()).scope == "may_propose"
    # Out-of-scope is FAIL, not UNKNOWN.
    assert (
        authority_verdict(scope_matches=False, evidence_present=True, approval_present=True)
        == "fail"
    )


# ---- Supersession ---------------------------------------------------------------


def test_supersession_preserves_history() -> None:
    old = _lineage_doc(lineage_id="mncs-rights://lineage/v1")
    new = _lineage_doc(
        lineage_id="mncs-rights://lineage/v2",
        supersessions=[
            {"supersedes_lineage": "mncs-rights://lineage/v1", "reason": "corrected producer"}
        ],
    )
    assert validate_lineage_structure(old) == []
    assert validate_lineage_structure(new) == []
    record = lineage_record_from_dict(new)
    assert record.supersessions[0]["supersedes_lineage"] == "mncs-rights://lineage/v1"
    # The old record still verifies independently: history is not rewritten.
    assert verify_lineage_digest(old)[0]


# ---- Duplicate pressure ----------------------------------------------------------


def test_duplicate_pressure_converges_without_merging() -> None:
    """Two projects discover the same gap; both origins survive convergence."""
    first = _lineage_doc(
        lineage_id="mncs-rights://lineage/app-a-gap",
        subject={"artifact_refs": [{"id": "app-a#feature"}]},
        capability_gap_links=[
            {
                "gap_ref": "gap/shared-001",
                "originating_repository": "app-a",
                "relation": "reports-gap",
            }
        ],
    )
    second = _lineage_doc(
        lineage_id="mncs-rights://lineage/app-b-gap",
        subject={"artifact_refs": [{"id": "app-b#feature"}]},
        capability_gap_links=[
            {
                "gap_ref": "gap/shared-001",
                "originating_repository": "app-b",
                "relation": "reports-gap",
            }
        ],
    )
    resolution = _lineage_doc(
        lineage_id="mncs-rights://lineage/lang-resolution",
        capability_gap_links=[
            {
                "gap_ref": "gap/shared-001",
                "resolving_change": "lang@def5678",
                "relation": "resolves-gap",
            }
        ],
        derivations=[
            {"from": "app-a#feature", "to": "gap/shared-001", "relation": "gap-derived-from"},
            {"from": "app-b#feature", "to": "gap/shared-001", "relation": "gap-derived-from"},
            {"from": "gap/shared-001", "to": "lang@def5678", "relation": "resolves-gap"},
        ],
    )
    for doc in (first, second, resolution):
        assert validate_lineage_structure(doc) == []
    record = lineage_record_from_dict(resolution)
    origins = {
        edge["from"] for edge in record.derivations if edge["relation"] == "gap-derived-from"
    }
    assert origins == {"app-a#feature", "app-b#feature"}


# ---- Partial failure ---------------------------------------------------------------


def test_partial_failure_blocks_promotion_without_invalidating_unrelated_evidence() -> None:
    dimensions = _all_pass_dimensions()
    dimensions["compiler_backend"] = {"verdict": "fail", "unresolved": ["wasm-coverage"]}
    report = promotion_report(promotion_inputs_from_dict(dimensions))
    assert report["combined"] == "fail"
    # Unrelated dimensions keep their own verdicts and evidence.
    assert report["dimensions"]["technical"]["verdict"] == "pass"
    assert report["dimensions"]["provenance"]["verdict"] == "pass"
    assert report["dimensions"]["compiler_backend"]["verdict"] == "fail"


# ---- Tampering ----------------------------------------------------------------------


def test_tampering_invalidates_content_identity() -> None:
    doc = _lineage_doc()
    tampered = deepcopy(doc)
    tampered["evaluations"][0]["verdict"] = (
        "pass" if doc["evaluations"][0]["verdict"] != "pass" else "fail"
    )
    ok, expected = verify_lineage_digest(tampered)
    assert not ok
    assert expected == compute_lineage_digest(tampered)
    assert (
        lineage_verdict(
            has_changeset=True,
            has_derivation=True,
            has_producer=True,
            evidence_bound=True,
            tamper_detected=not ok,
        )
        == "fail"
    )


# ---- Versioning ------------------------------------------------------------------------


def test_v02_manifests_remain_valid_and_migrate_cleanly() -> None:
    v02 = {
        "schema_version": "0.2.0",
        "artifact": {"id": "example/project#artifact", "class": "source-code"},
        "provenance": {
            "origin_classification": "human-authored",
            "participants": [{"type": "human", "role": "author"}],
            "process_evidence": [],
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
        },
    }
    assert validate_manifest_structure(v02) == []
    upgraded = migrate_manifest_02_to_03(v02)
    assert upgraded["schema_version"] == "0.3.0"
    assert "lineage" not in upgraded  # migration invents no provenance
    assert validate_manifest_structure(upgraded) == []
    parsed = manifest_from_dict(upgraded)
    assert parsed.schema_version == "0.3.0"
    assert parsed.lineage is None


def test_v03_extended_vocabulary_rejected_under_v02() -> None:
    manifest = {
        "schema_version": "0.2.0",
        "artifact": {"id": "example/project#artifact", "class": "source-code"},
        "provenance": {
            "origin_classification": "human-authored",
            "participants": [{"type": "human", "role": "author"}],
            "process_evidence": [{"kind": "lineage-record", "reference": "x"}],
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
        },
    }
    issues = validate_manifest_structure(manifest)
    assert any("kind invalid" in issue for issue in issues)
    manifest["schema_version"] = "0.3.0"
    assert validate_manifest_structure(manifest) == []


def test_capability_gap_link_requires_only_gap_ref() -> None:
    """Every gap field except the stable reference may be unknown."""
    doc = _lineage_doc(capability_gap_links=[{"gap_ref": "gap/minimal-001"}])
    assert validate_lineage_structure(doc) == []
    bad = _lineage_doc(capability_gap_links=[{"originating_repository": "app"}])
    assert any("gap_ref" in issue for issue in validate_lineage_structure(bad))


def test_promotion_dimension_defaults_to_unknown() -> None:
    inputs = promotion_inputs_from_dict({})
    assert promotion_combined(inputs) == "unknown"
    partial = promotion_inputs_from_dict({"technical": {"verdict": "pass"}})
    assert promotion_combined(partial) == "unknown"


def test_v03_json_schemas_accept_examples_and_dogfood() -> None:
    """The JSON Schemas are the contract: examples and dogfood must validate."""
    jsonschema = pytest.importorskip("jsonschema")
    root = Path(__file__).resolve().parents[1]
    manifest_schema = json.loads(
        (root / "schemas" / "v0.3" / "mncs-rights-manifest.schema.json").read_text()
    )
    lineage_schema = json.loads(
        (root / "schemas" / "v0.3" / "lineage-record.schema.json").read_text()
    )
    jsonschema.Draft202012Validator.check_schema(manifest_schema)
    jsonschema.Draft202012Validator.check_schema(lineage_schema)
    manifest_validator = jsonschema.Draft202012Validator(manifest_schema)
    lineage_validator = jsonschema.Draft202012Validator(lineage_schema)
    manifest_doc = json.loads(
        (root / "examples" / "v0.3" / "manifest-with-lineage.json").read_text()
    )
    assert list(manifest_validator.iter_errors(manifest_doc)) == []
    lineage_doc = json.loads(
        (root / "examples" / "v0.3" / "lineage-record-example.json").read_text()
    )
    assert list(lineage_validator.iter_errors(lineage_doc)) == []
    dogfood_doc = json.loads((root / "dogfood" / "distributed-pressure-changeset.json").read_text())
    assert list(lineage_validator.iter_errors(dogfood_doc)) == []


def test_builder_emission_defaults_to_base_version() -> None:
    """New manifests without lineage stay 0.2.0 so pinned consumers
    (Forge, mncs-validator-rs) keep working with zero changes."""
    from mncs_rights_provenance.model import Artifact, Manifest

    plain = Manifest(
        artifact=Artifact(id="example/x", artifact_class="source-code"),
        provenance_origin="origin-uncertain",
    )
    assert manifest_to_dict(plain)["schema_version"] == "0.2.0"
    assert validate_manifest_structure(manifest_to_dict(plain)) == []


def test_lineage_content_bumps_emission_to_v03() -> None:
    """Attaching lineage bumps emission 0.2.0 -> 0.3.0, never downward."""
    from mncs_rights_provenance.model import Artifact, Manifest

    manifest = Manifest(
        artifact=Artifact(id="example/x", artifact_class="source-code"),
        provenance_origin="origin-uncertain",
        lineage={"changesets": [{"changeset_id": "changeset/x"}]},
    )
    assert manifest_to_dict(manifest)["schema_version"] == "0.3.0"
    assert validate_manifest_structure(manifest_to_dict(manifest)) == []
