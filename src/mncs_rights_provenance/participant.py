"""Participant assertions for distributed Commons consumption.

Rights & Provenance owns participant identity, producer identity, and
provenance lineage.  A participant assertion projects one sealed v0.2
evidence record into the bounded identity material a Commons mesh node
needs for its capsule ``producer`` slot and Replication ``independence``
correlation:

- who/what produced the evidence (verbatim producer fields);
- which evidence record it came from (evidence id + content digest);
- whether the record's digest verifies (binding check, reported honestly);
- which subjects and claim kinds it covers.

An assertion is identity evidence, never permission: knowing the producer
implies nothing about correctness, independence, or authority.  Commons
evaluates every assertion inside its own local trust domain.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .evidence import SCHEMA_VERSION, verify_evidence_digest

PARTICIPANT_ASSERTION_VERSION = "mncs.rights.participant-assertion/v0.1"

MAX_STRING = 512
MAX_LIST_ENTRIES = 64


def _bounded_text(value: Any) -> str | None:
    if isinstance(value, str) and value.strip() and len(value) <= MAX_STRING:
        return value
    return None


def _bounded_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    items = []
    for item in values[:MAX_LIST_ENTRIES]:
        text = _bounded_text(item)
        if text is not None:
            items.append(text)
    return sorted(set(items))


def participant_assertion_from_evidence(record: Mapping[str, Any]) -> dict[str, Any]:
    """Project a sealed v0.2 evidence record into a participant assertion.

    Raises ``ValueError`` for the wrong schema and ``TypeError`` for a
    missing producer: those are structural defects, not verdicts.
    A digest mismatch does not raise;
    it is reported as ``bindingOk: false`` so consumers can downgrade the
    claim instead of guessing.
    """

    if not isinstance(record, Mapping):
        raise TypeError("evidence record must be a JSON object")
    if record.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"unsupported evidence schema_version: {record.get('schema_version')!r}")
    producer = record.get("producer")
    if not isinstance(producer, Mapping):
        raise TypeError("evidence record requires a producer object")

    binding_ok, expected_digest = verify_evidence_digest(record)
    producer_identity = (
        _bounded_text(producer.get("stableId"))
        or _bounded_text(producer.get("producer"))
        or _bounded_text(producer.get("name"))
        or "unknown-producer"
    )
    subject = record.get("subject")
    subject_refs: list[str] = []
    if isinstance(subject, Mapping):
        refs = subject.get("artifact_refs")
        if isinstance(refs, list):
            for ref in refs[:MAX_LIST_ENTRIES]:
                if isinstance(ref, Mapping):
                    text = _bounded_text(ref.get("id"))
                else:
                    text = _bounded_text(ref)
                if text is not None:
                    subject_refs.append(text)
    claims = record.get("claims")
    claim_kinds = []
    if isinstance(claims, list):
        for claim in claims[:MAX_LIST_ENTRIES]:
            if isinstance(claim, Mapping):
                kind = _bounded_text(claim.get("claim_type"))
                if kind is not None:
                    claim_kinds.append(kind)

    return {
        "assertionVersion": PARTICIPANT_ASSERTION_VERSION,
        "evidenceId": _bounded_text(record.get("evidence_id")) or "unknown-evidence",
        "evidenceDigest": record.get("content_digest")
        if isinstance(record.get("content_digest"), str)
        else None,
        "expectedDigest": expected_digest,
        "bindingOk": binding_ok,
        "producer": {
            "id": producer_identity,
            "type": _bounded_text(producer.get("producer")) or "unknown",
            "recordKind": _bounded_text(producer.get("recordKind")),
            "schemaVersion": _bounded_text(producer.get("schemaVersion")),
        },
        "subjectRefs": sorted(set(subject_refs)),
        "claimKinds": sorted(set(claim_kinds)),
        "authority": "assertion-only; identity evidence, never permission or correctness",
    }
