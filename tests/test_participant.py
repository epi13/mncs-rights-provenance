"""Participant assertions: identity evidence for distributed consumers."""

from __future__ import annotations

import pytest

from mncs_rights_provenance.evidence import (
    EvidenceRecord,
    seal_evidence_record,
)
from mncs_rights_provenance.participant import (
    PARTICIPANT_ASSERTION_VERSION,
    participant_assertion_from_evidence,
)


def sample_record() -> EvidenceRecord:
    return EvidenceRecord(
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


def test_assertion_projects_identity_material() -> None:
    sealed = seal_evidence_record(sample_record()).to_dict()
    assertion = participant_assertion_from_evidence(sealed)
    assert assertion["assertionVersion"] == PARTICIPANT_ASSERTION_VERSION
    assert assertion["evidenceId"] == "mncs-fabric://execution/rec-1"
    assert assertion["bindingOk"] is True
    assert assertion["expectedDigest"] == sealed["content_digest"]
    assert assertion["producer"]["id"] == "mncs-fabric://execution/rec-1"
    assert assertion["subjectRefs"] == ["example/project#artifact"]
    assert assertion["claimKinds"] == ["unknown-license-state"]
    assert "never permission" in assertion["authority"]


def test_tampering_is_reported_not_raised() -> None:
    sealed = seal_evidence_record(sample_record()).to_dict()
    sealed["claims"][0]["statement"] = "Everything is definitely fine."
    assertion = participant_assertion_from_evidence(sealed)
    assert assertion["bindingOk"] is False
    assert assertion["expectedDigest"] != sealed["content_digest"]


def test_structural_defects_raise() -> None:
    with pytest.raises(ValueError):
        participant_assertion_from_evidence({"schema_version": "9.9"})
    with pytest.raises(TypeError):
        participant_assertion_from_evidence({"schema_version": "0.2.0"})
    with pytest.raises(TypeError):
        participant_assertion_from_evidence("not-a-record")  # type: ignore[arg-type]
