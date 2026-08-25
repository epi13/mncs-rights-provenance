"""Release-policy evaluation: gates -> severities -> structured outcome."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .gates import (
    BLOCKING,
    DEFAULT_ENFORCEMENTS,
    ENFORCEMENT_DISABLED,
    ENFORCEMENT_FATAL,
    FINDING,
    GATE_FINDINGS,
    GATE_NAMES,
    GATE_TABLE,
    NONE,
    REVIEW,
    apply_enforcement,
)
from .policy_input import PolicyInput

OUTCOME_PASS = "pass"
OUTCOME_PASS_WITH_FINDINGS = "pass-with-findings"
OUTCOME_REVIEW_REQUIRED = "review-required"
OUTCOME_BLOCKED = "blocked"
OUTCOME_INVALID = "invalid"

SEVERITY_NAMES = {NONE: "none", FINDING: "finding", REVIEW: "review", BLOCKING: "blocking"}
ENFORCEMENT_NAMES = {0: "disabled", 1: "finding", 2: "review", 3: "fatal"}

DEFAULT_PROFILE_ID = "mncs-rights-provenance/canonical-release@0.2.0"


@dataclass(frozen=True)
class GateResult:
    gate: str
    severity: int
    enforcement: int
    effective_severity: int


@dataclass
class PolicyOutcome:
    outcome: str
    severity: int
    gate_results: list[GateResult] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "severity": SEVERITY_NAMES[self.severity],
            "gate_results": [
                {
                    "gate": result.gate,
                    "severity": SEVERITY_NAMES[result.severity],
                    "enforcement": ENFORCEMENT_NAMES[result.enforcement],
                    "effective_severity": SEVERITY_NAMES[result.effective_severity],
                }
                for result in self.gate_results
            ],
            "findings": list(self.findings),
            "note": (
                "Passing means project evidence requirements were satisfied; "
                "this is not a legal warranty of title or non-infringement."
            ),
        }


def profile_from_dict(value: Mapping[str, Any]) -> dict[str, int]:
    """Extract per-gate enforcement ceilings from a policy-profile document."""
    enforcements = dict(DEFAULT_ENFORCEMENTS)
    if not isinstance(value, Mapping):
        return enforcements
    gates = value.get("gates")
    mapping = {
        "disabled": ENFORCEMENT_DISABLED,
        "finding": 1,
        "review": 2,
        "fatal": ENFORCEMENT_FATAL,
    }
    if isinstance(gates, Mapping):
        for name in GATE_NAMES:
            gate = gates.get(name)
            if isinstance(gate, Mapping):
                enforcement = mapping.get(str(gate.get("enforcement")))
                if enforcement is not None:
                    enforcements[name] = enforcement
    return enforcements


def evaluate_policy(
    policy_input: PolicyInput,
    *,
    structurally_valid: bool = True,
    enforcements: Mapping[str, int] | None = None,
) -> PolicyOutcome:
    """Evaluate all gates and derive the release outcome.

    ``structurally_valid=False`` short-circuits to ``invalid``: structural
    validation is a distinct layer that must pass before policy speaks.
    """

    if not structurally_valid:
        return PolicyOutcome(outcome=OUTCOME_INVALID, severity=BLOCKING)

    caps = enforcements or DEFAULT_ENFORCEMENTS
    gate_results: list[GateResult] = []
    findings: list[str] = []
    combined = NONE

    for name, gate_fn, _default in GATE_TABLE:
        raw = gate_fn(policy_input)
        cap = caps.get(name, DEFAULT_ENFORCEMENTS[name])
        effective = apply_enforcement(raw, cap)
        gate_results.append(
            GateResult(gate=name, severity=raw, enforcement=cap, effective_severity=effective)
        )
        if effective > NONE:
            findings.append(GATE_FINDINGS[name])
            combined = max(combined, effective)

    if combined >= BLOCKING:
        outcome = OUTCOME_BLOCKED
    elif combined >= REVIEW:
        outcome = OUTCOME_REVIEW_REQUIRED
    elif combined >= FINDING:
        outcome = OUTCOME_PASS_WITH_FINDINGS
    else:
        outcome = OUTCOME_PASS

    return PolicyOutcome(
        outcome=outcome,
        severity=combined,
        gate_results=gate_results,
        findings=sorted(set(findings)),
    )


__all__ = [
    "DEFAULT_PROFILE_ID",
    "OUTCOME_BLOCKED",
    "OUTCOME_INVALID",
    "OUTCOME_PASS",
    "OUTCOME_PASS_WITH_FINDINGS",
    "OUTCOME_REVIEW_REQUIRED",
    "GateResult",
    "PolicyOutcome",
    "evaluate_policy",
    "profile_from_dict",
]
