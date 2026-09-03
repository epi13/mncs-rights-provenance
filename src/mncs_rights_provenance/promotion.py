"""Tri-state promotion verdicts for distributed development pressure.

Eight independent evidence dimensions stay independent: each carries its own
``pass | fail | unknown`` plus evidence and unresolved fields. Combination
uses the family rule ``FAIL > UNKNOWN > PASS`` and always retains the
per-dimension breakdown alongside the summary.

The normative semantics live in MNCS-language
(``language/pressure_provenance.mncs``, module ``mncs.rights.pressure.v01``);
this module mirrors them and is pinned by
``conformance/pressure-golden-vectors.json``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

VERDICT_PASS = "pass"
VERDICT_FAIL = "fail"
VERDICT_UNKNOWN = "unknown"

VERDICTS = frozenset({VERDICT_PASS, VERDICT_FAIL, VERDICT_UNKNOWN})

DIMENSIONS = (
    "technical",
    "test_conformance",
    "compiler_backend",
    "coordination_dependency",
    "provenance",
    "authority",
    "rights_license",
    "policy",
)

_RANK = {VERDICT_PASS: 0, VERDICT_UNKNOWN: 1, VERDICT_FAIL: 2}
_NAME_BY_RANK = {rank: name for name, rank in _RANK.items()}


def combine_verdict(left: str, right: str) -> str:
    """Combine two tri-state verdicts: FAIL dominates UNKNOWN dominates PASS."""
    try:
        left_rank = _RANK[left]
    except KeyError:
        raise ValueError(f"invalid verdict: {left!r}") from None
    try:
        right_rank = _RANK[right]
    except KeyError:
        raise ValueError(f"invalid verdict: {right!r}") from None
    return _NAME_BY_RANK[max(left_rank, right_rank)]


@dataclass(frozen=True)
class PromotionDimension:
    verdict: str = VERDICT_UNKNOWN
    evidence: tuple[Mapping[str, Any], ...] = ()
    unresolved: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {"verdict": self.verdict}
        if self.evidence:
            value["evidence"] = [dict(item) for item in self.evidence]
        if self.unresolved:
            value["unresolved"] = list(self.unresolved)
        return value


@dataclass(frozen=True)
class PromotionInputs:
    technical: PromotionDimension = field(default_factory=PromotionDimension)
    test_conformance: PromotionDimension = field(default_factory=PromotionDimension)
    compiler_backend: PromotionDimension = field(default_factory=PromotionDimension)
    coordination_dependency: PromotionDimension = field(default_factory=PromotionDimension)
    provenance: PromotionDimension = field(default_factory=PromotionDimension)
    authority: PromotionDimension = field(default_factory=PromotionDimension)
    rights_license: PromotionDimension = field(default_factory=PromotionDimension)
    policy: PromotionDimension = field(default_factory=PromotionDimension)

    def to_dict(self) -> dict[str, Any]:
        return {
            "technical": self.technical.to_dict(),
            "test_conformance": self.test_conformance.to_dict(),
            "compiler_backend": self.compiler_backend.to_dict(),
            "coordination_dependency": self.coordination_dependency.to_dict(),
            "provenance": self.provenance.to_dict(),
            "authority": self.authority.to_dict(),
            "rights_license": self.rights_license.to_dict(),
            "policy": self.policy.to_dict(),
        }


def promotion_combined(inputs: PromotionInputs) -> str:
    """Fold all eight dimensions with :func:`combine_verdict`."""
    verdicts = (
        inputs.technical.verdict,
        inputs.test_conformance.verdict,
        inputs.compiler_backend.verdict,
        inputs.coordination_dependency.verdict,
        inputs.provenance.verdict,
        inputs.authority.verdict,
        inputs.rights_license.verdict,
        inputs.policy.verdict,
    )
    combined = VERDICT_PASS
    for verdict in verdicts:
        combined = combine_verdict(combined, verdict)
    return combined


def promotion_inputs_from_dict(value: Mapping[str, Any]) -> PromotionInputs:
    """Parse a ``promotion_dimensions`` mapping; unknown/missing is UNKNOWN."""

    def dimension(name: str) -> PromotionDimension:
        entry = value.get(name)
        if not isinstance(entry, Mapping):
            return PromotionDimension(verdict=VERDICT_UNKNOWN, unresolved=(name,))
        verdict = entry.get("verdict")
        if verdict not in VERDICTS:
            verdict = VERDICT_UNKNOWN
        evidence = tuple(
            dict(item) for item in entry.get("evidence") or () if isinstance(item, Mapping)
        )
        unresolved = tuple(str(item) for item in entry.get("unresolved") or ())
        return PromotionDimension(verdict=str(verdict), evidence=evidence, unresolved=unresolved)

    return PromotionInputs(
        technical=dimension("technical"),
        test_conformance=dimension("test_conformance"),
        compiler_backend=dimension("compiler_backend"),
        coordination_dependency=dimension("coordination_dependency"),
        provenance=dimension("provenance"),
        authority=dimension("authority"),
        rights_license=dimension("rights_license"),
        policy=dimension("policy"),
    )


def promotion_report(inputs: PromotionInputs) -> dict[str, Any]:
    """Per-dimension breakdown plus the combined summary (never flattened alone)."""
    return {
        "dimensions": inputs.to_dict(),
        "combined": promotion_combined(inputs),
        "rule": "FAIL > UNKNOWN > PASS; breakdown retained; summary is a policy input, not a decision.",
    }


__all__ = [
    "DIMENSIONS",
    "VERDICTS",
    "VERDICT_FAIL",
    "VERDICT_PASS",
    "VERDICT_UNKNOWN",
    "PromotionDimension",
    "PromotionInputs",
    "combine_verdict",
    "promotion_combined",
    "promotion_inputs_from_dict",
    "promotion_report",
]
