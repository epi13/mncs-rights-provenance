"""Standalone evidence records (content-addressed producer evidence)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .canonical import digest_prefixed

SCHEMA_VERSION = "0.2.0"


@dataclass
class EvidenceRecord:
    evidence_id: str
    kind: str
    producer: dict[str, Any]
    subject: dict[str, Any]
    claims: list[dict[str, Any]] = field(default_factory=list)
    observations: list[dict[str, Any]] = field(default_factory=list)
    references: list[dict[str, Any]] = field(default_factory=list)
    context: dict[str, Any] | None = None
    limitations: list[str] = field(default_factory=list)
    extensions: dict[str, Any] = field(default_factory=dict)
    content_digest: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "evidence_id": self.evidence_id,
            "kind": self.kind,
            "producer": dict(self.producer),
            "subject": {
                "artifact_refs": list(self.subject.get("artifact_refs", ())),
                **{key: item for key, item in self.subject.items() if key != "artifact_refs"},
            },
            "claims": [dict(item) for item in self.claims],
        }
        if self.observations:
            value["observations"] = [dict(item) for item in self.observations]
        if self.references:
            value["references"] = [dict(item) for item in self.references]
        if self.context is not None:
            value["context"] = dict(self.context)
        if self.limitations:
            value["limitations"] = list(self.limitations)
        if self.extensions:
            value["extensions"] = dict(self.extensions)
        if self.content_digest is not None:
            value["content_digest"] = self.content_digest
        return value


def compute_evidence_digest(record: Mapping[str, Any]) -> str:
    reduced = {key: item for key, item in record.items() if key != "content_digest"}
    return digest_prefixed(reduced)


def seal_evidence_record(record: EvidenceRecord) -> EvidenceRecord:
    record.content_digest = compute_evidence_digest(record.to_dict())
    return record


def evidence_record_from_dict(value: Mapping[str, Any]) -> EvidenceRecord:
    if not isinstance(value, Mapping):
        raise TypeError("evidence record must be a JSON object")
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"unsupported evidence schema_version: {value.get('schema_version')!r}")
    subject = value.get("subject")
    if not isinstance(subject, Mapping):
        raise TypeError("evidence record requires a subject object")
    producer = value.get("producer")
    if not isinstance(producer, Mapping):
        raise TypeError("evidence record requires a producer object")
    return EvidenceRecord(
        evidence_id=str(value.get("evidence_id", "")),
        kind=str(value.get("kind", "other")),
        producer=dict(producer),
        subject=dict(subject),
        claims=[dict(item) for item in value.get("claims") or () if isinstance(item, Mapping)],
        observations=[
            dict(item) for item in value.get("observations") or () if isinstance(item, Mapping)
        ],
        references=[
            dict(item) for item in value.get("references") or () if isinstance(item, Mapping)
        ],
        context=dict(value["context"]) if isinstance(value.get("context"), Mapping) else None,
        limitations=[str(item) for item in value.get("limitations") or ()],
        extensions=dict(value["extensions"])
        if isinstance(value.get("extensions"), Mapping)
        else {},
        content_digest=value.get("content_digest")
        if isinstance(value.get("content_digest"), str)
        else None,
    )


def evidence_record_to_dict(record: EvidenceRecord) -> dict[str, Any]:
    return record.to_dict()


def verify_evidence_digest(value: Mapping[str, Any]) -> tuple[bool, str]:
    """Return ``(ok, expected_digest)``; ok is False when the digest mismatches."""
    declared = value.get("content_digest")
    expected = compute_evidence_digest(value)
    if not isinstance(declared, str) or declared != expected:
        return False, expected
    return True, expected


__all__ = [
    "SCHEMA_VERSION",
    "EvidenceRecord",
    "compute_evidence_digest",
    "evidence_record_from_dict",
    "evidence_record_to_dict",
    "seal_evidence_record",
    "verify_evidence_digest",
]
