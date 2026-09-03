"""Authority vocabulary: actor identity is not permission.

An ``actor_ref`` records who or what produced something. An authority claim
records whether that actor may perform a scoped transition, as asserted by
somebody, with evidence, and with an explicit tri-state verdict. Unknown or
disputed authority stays ``unknown``; classifiers never default to human,
trusted, or permitted.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .promotion import VERDICT_FAIL, VERDICT_PASS, VERDICT_UNKNOWN, VERDICTS

ACTOR_TYPES = frozenset({"human", "model", "agent", "tool", "organization", "unknown"})

ACTOR_CLASSES = frozenset(
    {
        "human",
        "human-directed-agent",
        "autonomous-agent",
        "forge-evaluator",
        "ci",
        "maintainer",
        "mnel-model",
        "fabric-worker",
        "external-contributor",
        "federated-deployment",
        "unknown",
    }
)

AUTHORITY_SCOPES = frozenset(
    {
        "may_propose",
        "may_provide_evidence",
        "may_evaluate",
        "may_attest",
        "may_approve",
        "may_promote",
        "may_modify_repository",
        "may_approve_change_class",
        "unknown",
    }
)


@dataclass(frozen=True)
class ActorRef:
    actor_type: str = "unknown"
    actor_class: str = "unknown"
    role: str | None = None
    name: str | None = None
    participant_ref: str | None = None
    digest: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {"type": self.actor_type}
        if self.actor_class != "unknown":
            value["actor_class"] = self.actor_class
        for key in ("role", "name", "participant_ref", "digest"):
            item = getattr(self, key)
            if item is not None:
                value[key] = item
        return value


@dataclass(frozen=True)
class AuthorityClaim:
    subject: ActorRef
    scope: str
    asserted_by: str
    verdict: str = VERDICT_UNKNOWN
    repository: str | None = None
    change_class: str | None = None
    authority_level: int | None = None
    basis_evidence: tuple[Mapping[str, Any], ...] = ()
    unresolved: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "subject": self.subject.to_dict(),
            "scope": self.scope,
            "asserted_by": self.asserted_by,
            "verdict": self.verdict,
        }
        if self.repository is not None:
            value["repository"] = self.repository
        if self.change_class is not None:
            value["change_class"] = self.change_class
        if self.authority_level is not None:
            value["authority_level"] = self.authority_level
        if self.basis_evidence:
            value["basis_evidence"] = [dict(item) for item in self.basis_evidence]
        if self.unresolved:
            value["unresolved"] = list(self.unresolved)
        return value


def authority_verdict(
    *, scope_matches: bool, evidence_present: bool, approval_present: bool
) -> str:
    """Normative scoped-authority verdict (mirrors the MNCS-language core).

    - scope mismatch is FAIL (explicitly out of scope);
    - missing evidence or approval is UNKNOWN, never PASS;
    - PASS requires scope match plus present evidence and approval basis.
    """
    if not scope_matches:
        return VERDICT_FAIL
    if not evidence_present:
        return VERDICT_UNKNOWN
    if not approval_present:
        return VERDICT_UNKNOWN
    return VERDICT_PASS


def actor_ref_from_dict(value: Mapping[str, Any]) -> ActorRef:
    actor_type = str(value.get("type", "unknown"))
    if actor_type not in ACTOR_TYPES:
        actor_type = "unknown"
    actor_class = str(value.get("actor_class", "unknown"))
    if actor_class not in ACTOR_CLASSES:
        actor_class = "unknown"
    return ActorRef(
        actor_type=actor_type,
        actor_class=actor_class,
        role=str(value["role"]) if isinstance(value.get("role"), str) else None,
        name=str(value["name"]) if isinstance(value.get("name"), str) else None,
        participant_ref=str(value["participant_ref"])
        if isinstance(value.get("participant_ref"), str)
        else None,
        digest=str(value["digest"]) if isinstance(value.get("digest"), str) else None,
    )


def authority_claim_from_dict(value: Mapping[str, Any]) -> AuthorityClaim:
    subject = value.get("subject")
    actor = actor_ref_from_dict(subject) if isinstance(subject, Mapping) else ActorRef()
    scope = str(value.get("scope", "unknown"))
    if scope not in AUTHORITY_SCOPES:
        scope = "unknown"
    verdict = str(value.get("verdict", VERDICT_UNKNOWN))
    if verdict not in VERDICTS:
        verdict = VERDICT_UNKNOWN
    level = value.get("authority_level")
    return AuthorityClaim(
        subject=actor,
        scope=scope,
        asserted_by=str(value.get("asserted_by", "")),
        verdict=verdict,
        repository=str(value["repository"]) if isinstance(value.get("repository"), str) else None,
        change_class=str(value["change_class"])
        if isinstance(value.get("change_class"), str)
        else None,
        authority_level=int(level) if isinstance(level, int) and 1 <= level <= 5 else None,
        basis_evidence=tuple(
            dict(item) for item in value.get("basis_evidence") or () if isinstance(item, Mapping)
        ),
        unresolved=tuple(str(item) for item in value.get("unresolved") or ()),
    )


__all__ = [
    "ACTOR_CLASSES",
    "ACTOR_TYPES",
    "AUTHORITY_SCOPES",
    "ActorRef",
    "AuthorityClaim",
    "actor_ref_from_dict",
    "authority_claim_from_dict",
    "authority_verdict",
]
