"""Generic host gate over the normative rights-claims core.

Hosts (sessions, CI, services) hold readable claim records -- string
subjects, claimants, licenses, evidence references -- while
:mod:`claims` speaks only integer codes. This module is the single
encoding point: it maps readable records to core codes
deterministically (enumeration by first appearance, stable within one
evaluation), runs the set-level queries, and reduces them to a
per-subject gate verdict.

Gate semantics (host policy, documented here, not normative):

- ``blocked``: any live-failing claim for the subject -- Revoked or
  Expired. There is no grant to rely on.
- ``review``: anything needing a human -- Contested, Unknown (missing
  evidence stays Unknown no matter what surrounds it), Superseded
  heads, pairwise conflicts, supersession problems, or no claims at
  all for the subject.
- ``clear``: every claim for the subject is Verified.

Conflict and supersession reports never resolve: they only ever push
a subject from ``clear`` toward ``review``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from . import claims as _core

GATE_BLOCKED = "blocked"
GATE_REVIEW = "review"
GATE_CLEAR = "clear"

#: Readable fields accepted on an input claim record. ``id`` is
#: optional (position is used when absent); ``supersedes`` lists ids.
READABLE_FIELDS = (
    "subject",
    "claimant",
    "license",
    "evidence",
    "verified",
    "contested",
    "revoked",
    "effective",
    "expires",
    "supersedes",
)


class GateInputError(ValueError):
    """A readable claim record is malformed."""


def _enum(values: Sequence[str]) -> dict[str, int]:
    table: dict[str, int] = {}
    for value in values:
        if value not in table:
            table[value] = len(table) + 1
    return table


def encode_claims(
    records: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, int]], dict[str, dict[str, int]]]:
    """Encode readable records to core ``{field: int}`` claims.

    Returns the encoded claims plus the enumeration tables used, so
    callers can map statuses back to readable subjects.
    """
    for position, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise GateInputError(f"claim #{position} must be a mapping")
    subjects = _enum([str(r.get("subject", "")) for r in records])
    claimants = _enum([str(r.get("claimant", "")) for r in records])
    licenses = _enum([str(r.get("license", "")) for r in records])
    encoded: list[dict[str, int]] = []
    for position, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise GateInputError(f"claim #{position} must be a mapping")
        try:
            evidence = record.get("evidence", [])
            evidence_refs = list(evidence) if evidence is not None else []
            verified = 1 if record.get("verified", False) else 0
            if verified and not evidence_refs:
                # Verified without evidence is fabrication; the core
                # would call this Unknown, so encode it as such.
                verified = 0
            encoded.append(
                {
                    "id": int(record.get("id", position + 1)),
                    "subject": subjects[str(record.get("subject", ""))],
                    "claimant": claimants[str(record.get("claimant", ""))],
                    "basis": 1,
                    "license": licenses[str(record.get("license", ""))],
                    "attribution": 1 if record.get("attribution", True) else 0,
                    "redistribute": 1 if record.get("redistribute", False) else 0,
                    "derivatives": 1 if record.get("derivatives", True) else 0,
                    "commercial": 1 if record.get("commercial", False) else 0,
                    "evidence": 1 if evidence_refs else 0,
                    "effective": int(record.get("effective", 0)),
                    "expires": int(record.get("expires", 0)),
                    "revoked": 1 if record.get("revoked", False) else 0,
                    "supersedes": 0,
                    "verified": verified,
                    "contested": 1 if record.get("contested", False) else 0,
                }
            )
        except (TypeError, ValueError) as error:
            raise GateInputError(f"claim #{position} malformed: {error}") from error
    # Supersession edges resolve after ids are known.
    by_id = {claim["id"]: claim for claim in encoded}
    for position, record in enumerate(records):
        for target in record.get("supersedes", []) or []:
            successor = by_id.get(int(target))
            if successor is not None:
                successor["supersedes"] = encoded[position]["id"]
    tables = {"subject": subjects, "claimant": claimants, "license": licenses}
    return encoded, tables


def evaluate_subjects(
    records: Sequence[Mapping[str, Any]],
    *,
    now: int,
    subjects: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Gate verdict per subject plus the overall gate.

    ``subjects`` limits the verdict to an explicit watch list; every
    watched subject with no claims reports ``review`` (unknown). When
    omitted, every subject appearing in ``records`` is reported.
    """
    encoded, tables = encode_claims(records)
    view = _core.status_view(encoded, now)
    conflicts = _core.find_conflicts(encoded)
    problems = _core.supersession_problems(encoded, now)
    conflict_ids: set[int] = set()
    for conflict in conflicts:
        conflict_ids.add(conflict["a"])
        conflict_ids.add(conflict["b"])
    problem_ids: set[int] = set()
    for problem in problems:
        for key in ("claim", "successor", "base"):
            if isinstance(problem.get(key), int):
                problem_ids.add(problem[key])
    id_subject = {claim["id"]: claim["subject"] for claim in encoded}
    flagged_subjects = {
        id_subject[cid] for cid in conflict_ids | problem_ids if cid in id_subject
    }

    reverse = {code: name for name, code in tables["subject"].items()}

    verdicts: dict[str, str] = {}
    detail: dict[str, list[str]] = {}
    names = list(subjects) if subjects is not None else sorted(reverse.values())
    for name in names:
        code = tables["subject"].get(name)
        statuses = [v["status"] for v in view if code is not None and v["subject"] == code]
        reasons: list[str] = []
        if not statuses:
            verdicts[name] = GATE_REVIEW
            detail[name] = ["no claims: unknown"]
            continue
        if any(s in ("Revoked", "Expired") for s in statuses):
            verdicts[name] = GATE_BLOCKED
            reasons = [s for s in statuses if s in ("Revoked", "Expired")]
        elif (
            any(s in ("Contested", "Unknown", "Superseded") for s in statuses)
            or (code in flagged_subjects)
        ):
            verdicts[name] = GATE_REVIEW
            reasons = [s for s in statuses if s != "Verified"]
            if code in flagged_subjects:
                reasons.append("conflict-or-supersession-problem")
        else:
            verdicts[name] = GATE_CLEAR
            reasons = ["all verified"]
        detail[name] = sorted(set(reasons))

    overall = GATE_CLEAR
    if any(v == GATE_BLOCKED for v in verdicts.values()):
        overall = GATE_BLOCKED
    elif any(v == GATE_REVIEW for v in verdicts.values()):
        overall = GATE_REVIEW
    return {
        "overall": overall,
        "subjects": verdicts,
        "detail": detail,
        "problems": problems,
        "conflicts": [
            {"a": c["a"], "b": c["b"], "subject": c["subject"]} for c in conflicts
        ],
    }


__all__ = [
    "GATE_BLOCKED",
    "GATE_CLEAR",
    "GATE_REVIEW",
    "GateInputError",
    "encode_claims",
    "evaluate_subjects",
]
