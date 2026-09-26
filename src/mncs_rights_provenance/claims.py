"""Host mirror of the normative rights-claim status core.

Mirrors ``language/rights_claims.mncs`` (module ``mncs.rights.claims.v01``)
scalar-for-scalar and is pinned to the same contract by
``conformance/claims-golden-vectors.json`` (see ``tests/test_claims_host.py``).
The ``.mncs`` core stays normative: changing this mirror without changing
(or deliberately confirming) the core is a defect.

Set-level helpers (``resolve_superseded``, ``status_view``, ``find_conflicts``,
``supersession_problems``, ``select``) compose the pure core over claim
collections. They report; they never resolve. Conflicting claims coexist in
the output, supersession cycles surface as problems (never as silent heads),
and missing evidence stays ``Unknown`` no matter what surrounds the claim.

Boundary (load-bearing): a claim is a machine-readable statement, not a
legal fact. ``Verified`` means the stated evidence requirements were met for
the stated scope. Nothing here is a legal warranty of title, ownership, or
non-infringement.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

STATUSES = (
    "Asserted",
    "Verified",
    "Contested",
    "Superseded",
    "Expired",
    "Revoked",
    "Incompatible",
    "Unknown",
)

CLAIM_FIELDS = (
    "id",
    "subject",
    "claimant",
    "basis",
    "license",
    "attribution",
    "redistribute",
    "derivatives",
    "commercial",
    "evidence",
    "effective",
    "expires",
    "revoked",
    "supersedes",
    "verified",
    "contested",
)

#: Rights-basis code shared with the policy core; 5 forces Unknown.
BASIS_UNKNOWN = 5


def _u64(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"claim field {field!r} must be a non-negative int, got {value!r}")
    return value


def normalize_claim(claim: Mapping[str, Any]) -> dict[str, int]:
    """Validate a claim record and return it as a plain ``{field: int}`` dict.

    All 16 normative fields must be present. Missing fields raise; the
    mirror never fills gaps with defaults (that would fabricate consent,
    evidence, or liveness).
    """
    if not isinstance(claim, Mapping):
        raise TypeError(f"claim must be a mapping, got {type(claim).__name__}")
    missing = [name for name in CLAIM_FIELDS if name not in claim]
    if missing:
        raise ValueError(f"claim missing fields: {', '.join(missing)}")
    return {name: _u64(claim[name], name) for name in CLAIM_FIELDS}


def claim_status(claim: Mapping[str, Any], now: int, superseded: int) -> str:
    """Canonical per-claim status. Precedence: Revoked > Expired >
    Superseded > Contested > Unknown (no evidence) > Verified > Asserted."""
    item = normalize_claim(claim)
    now = _u64(now, "now")
    superseded = _u64(superseded, "superseded")
    if item["revoked"] == 1:
        return "Revoked"
    if item["expires"] == 0 or now < item["expires"]:
        if superseded == 1:
            return "Superseded"
        if item["contested"] == 1:
            return "Contested"
        if item["evidence"] == 0:
            return "Unknown"
        if item["verified"] == 1:
            return "Verified"
        return "Asserted"
    return "Expired"


def temporal_state(effective: int, expires: int, now: int, revoked: int) -> int:
    """Pure temporal projection: 0 live, 1 not-yet-effective, 2 expired,
    3 revoked. Revocation dominates time."""
    effective = _u64(effective, "effective")
    expires = _u64(expires, "expires")
    now = _u64(now, "now")
    revoked = _u64(revoked, "revoked")
    if revoked == 1:
        return 3
    if expires == 0 or now < expires:
        if now < effective:
            return 1
        return 0
    return 2


def evidence_state(evidence: int, current: int, checked: int) -> int:
    """Evidence freshness: 0 current, 1 stale, 2 missing, 3 unchecked."""
    evidence = _u64(evidence, "evidence")
    current = _u64(current, "current")
    checked = _u64(checked, "checked")
    if checked == 0:
        return 3
    if evidence == 0:
        return 2
    if evidence == current:
        return 0
    return 1


def dim_compatible(left: int, right: int) -> int:
    """One scope dimension: 0 compatible, 1 conflict, 2 unknown."""
    left = _u64(left, "left")
    right = _u64(right, "right")
    if left == 2 or right == 2:
        return 2
    if left == right:
        return 0
    return 1


def basis_compatible(
    a_basis: int,
    a_redistribute: int,
    a_derivatives: int,
    a_commercial: int,
    b_basis: int,
    b_redistribute: int,
    b_derivatives: int,
    b_commercial: int,
) -> int:
    """Mechanical compatibility of two scope tuples: 0 compatible,
    1 conflict, 2 unknown. Unknown basis (5) on either side forces
    Unknown; forbid-vs-permit on any shared dimension is a conflict."""
    a_basis = _u64(a_basis, "a_basis")
    b_basis = _u64(b_basis, "b_basis")
    if a_basis == BASIS_UNKNOWN or b_basis == BASIS_UNKNOWN:
        return 2
    dims = (
        dim_compatible(a_redistribute, b_redistribute),
        dim_compatible(a_derivatives, b_derivatives),
        dim_compatible(a_commercial, b_commercial),
    )
    if 1 in dims:
        return 1
    if 2 in dims:
        return 2
    return 0


def claims_compatible(first: Mapping[str, Any], second: Mapping[str, Any]) -> int:
    """``basis_compatible`` over two claim records."""
    left = normalize_claim(first)
    right = normalize_claim(second)
    return basis_compatible(
        left["basis"],
        left["redistribute"],
        left["derivatives"],
        left["commercial"],
        right["basis"],
        right["redistribute"],
        right["derivatives"],
        right["commercial"],
    )


def attribution_due(attribution: int, status: str) -> int:
    """Attribution duty: 1 due, 0 not due, 2 uncertain scope.
    Non-live statuses report 2: the mirror does not decide what expired
    or revoked claims still require."""
    attribution = _u64(attribution, "attribution")
    if status not in STATUSES:
        raise ValueError(f"unknown claim status {status!r}")
    if status in ("Asserted", "Verified"):
        return 1 if attribution == 1 else 0
    return 2


def signed_state(sig_valid: int, signer_authorized: int, content_verified: int) -> str:
    """Signed-assertion layering. A valid signature never implies legal
    authority or truth on its own: unauthorized signers stay Contested,
    unverified content stays Asserted, missing signatures stay Unknown."""
    sig_valid = _u64(sig_valid, "sig_valid")
    signer_authorized = _u64(signer_authorized, "signer_authorized")
    content_verified = _u64(content_verified, "content_verified")
    if sig_valid == 0:
        return "Unknown"
    if signer_authorized == 0:
        return "Contested"
    if content_verified == 1:
        return "Verified"
    return "Asserted"


def supersede_link_valid(base_live: int, successor_known: int, same_subject: int) -> int:
    """Single-link supersession validity: 0 valid, 1 subject mismatch,
    2 successor basis unknown, 3 base not live."""
    base_live = _u64(base_live, "base_live")
    successor_known = _u64(successor_known, "successor_known")
    same_subject = _u64(same_subject, "same_subject")
    if same_subject == 0:
        return 1
    if successor_known == 0:
        return 2
    if base_live == 0:
        return 3
    return 0


def _is_live(claim: Mapping[str, int], now: int) -> bool:
    return temporal_state(claim["effective"], claim["expires"], now, claim["revoked"]) == 0


def _is_known(claim: Mapping[str, int]) -> bool:
    return claim["basis"] != BASIS_UNKNOWN


def _by_id(claims: Sequence[Mapping[str, int]]) -> dict[int, Mapping[str, int]]:
    by_id: dict[int, Mapping[str, int]] = {}
    for claim in claims:
        if claim["id"] in by_id:
            raise ValueError(f"duplicate claim id {claim['id']}")
        by_id[claim["id"]] = claim
    return by_id


def resolve_superseded(claims: Sequence[Mapping[str, Any]], now: int) -> dict[int, bool]:
    """Resolve the ``superseded`` flag per claim from supersession edges.

    A claim is superseded iff another **live** claim in the set names it
    via ``supersedes`` on the **same subject** (the normative core's
    "another live claim names this one"). Cross-subject naming is a
    problem, not a supersession (see ``supersession_problems``).
    """
    now = _u64(now, "now")
    items = [normalize_claim(claim) for claim in claims]
    _by_id(items)  # reject duplicate ids; a set with two identities is no set
    flags: dict[int, bool] = {claim["id"]: False for claim in items}
    for base in items:
        for successor in items:
            if successor["id"] == base["id"]:
                continue
            if (
                successor["supersedes"] == base["id"]
                and successor["subject"] == base["subject"]
                and _is_live(successor, now)
            ):
                flags[base["id"]] = True
                break
    return flags


def status_view(claims: Sequence[Mapping[str, Any]], now: int) -> list[dict[str, Any]]:
    """Per-claim projection in input order: ``id``, ``subject``,
    ``status`` (normative precedence), ``superseded`` (resolved edges),
    ``attribution`` (normative duty code).

    ``Incompatible`` never appears here: pairwise scope conflicts surface
    through ``find_conflicts`` while each claim keeps its own status.
    """
    flags = resolve_superseded(claims, now)
    view: list[dict[str, Any]] = []
    for raw in claims:
        claim = normalize_claim(raw)
        status = claim_status(claim, now, 1 if flags[claim["id"]] else 0)
        view.append(
            {
                "id": claim["id"],
                "subject": claim["subject"],
                "status": status,
                "superseded": flags[claim["id"]],
                "attribution": attribution_due(claim["attribution"], status),
            }
        )
    return view


def find_conflicts(claims: Sequence[Mapping[str, Any]]) -> list[dict[str, int]]:
    """Report forbid-vs-permit scope conflicts between same-subject pairs.

    Each entry is ``{a, b, subject}`` with ``a < b``. Both claims keep
    their own status: the conflict is reported, never merged or resolved.
    Liveness filtering is the caller's policy decision; the mechanics
    here are deliberately liveness-blind.
    """
    items = [normalize_claim(claim) for claim in claims]
    _by_id(items)  # reject duplicate ids before pairing
    conflicts: list[dict[str, int]] = []
    for index, first in enumerate(items):
        for second in items[index + 1 :]:
            if first["subject"] != second["subject"]:
                continue
            if claims_compatible(first, second) == 1:
                low, high = sorted((first["id"], second["id"]))
                conflicts.append({"a": low, "b": high, "subject": first["subject"]})
    return conflicts


def _cycle_members(items: Sequence[Mapping[str, int]]) -> set[int]:
    """Claim ids lying on a directed ``supersedes`` cycle (existing targets
    only; dangling links cannot form cycles). Iterative coloring, no
    recursion limit."""
    by_id = _by_id(items)
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {claim["id"]: WHITE for claim in items}
    on_cycle: set[int] = set()

    def successors(node: int) -> list[int]:
        target = by_id[node]["supersedes"]
        if target != 0 and target in by_id:
            return [target]
        return []

    for start in by_id:
        if color[start] != WHITE:
            continue
        stack: list[tuple[int, int]] = [(start, 0)]
        color[start] = GRAY
        path: list[int] = [start]
        while stack:
            current, offset = stack[-1]
            targets = successors(current)
            if offset >= len(targets):
                color[current] = BLACK
                stack.pop()
                if path and path[-1] == current:
                    path.pop()
                continue
            stack[-1] = (current, offset + 1)
            neighbor = targets[offset]
            if color[neighbor] == GRAY:
                on_cycle.add(neighbor)
                if neighbor in path:
                    on_cycle.update(path[path.index(neighbor) :])
                continue
            if color[neighbor] == WHITE:
                color[neighbor] = GRAY
                stack.append((neighbor, 0))
                path.append(neighbor)
    return on_cycle


def supersession_problems(claims: Sequence[Mapping[str, Any]], now: int) -> list[dict[str, Any]]:
    """Surface supersession links that cannot establish a clean handoff.

    Entries are ``{claim, kind, detail}`` with kind in ``dangling-link``
    (names an id outside the set), ``subject-mismatch``, ``successor-unknown``
    (successor basis needs review), ``base-not-live``, or ``cycle``. Valid
    links produce no entry. Problems are preserved as data; the view layer
    never silently picks a head across them.
    """
    now = _u64(now, "now")
    items = [normalize_claim(claim) for claim in claims]
    by_id = _by_id(items)
    problems: list[dict[str, Any]] = []
    for claim in items:
        target_id = claim["supersedes"]
        if target_id == 0:
            continue
        target = by_id.get(target_id)
        if target is None:
            problems.append(
                {
                    "claim": claim["id"],
                    "kind": "dangling-link",
                    "detail": f"supersedes unknown claim {target_id}",
                }
            )
            continue
        code = supersede_link_valid(
            1 if _is_live(target, now) else 0,
            1 if _is_known(claim) else 0,
            1 if target["subject"] == claim["subject"] else 0,
        )
        if code == 1:
            problems.append(
                {
                    "claim": claim["id"],
                    "kind": "subject-mismatch",
                    "detail": (
                        f"claim {claim['id']} (subject {claim['subject']}) names "
                        f"claim {target_id} (subject {target['subject']})"
                    ),
                }
            )
        elif code == 2:
            problems.append(
                {
                    "claim": claim["id"],
                    "kind": "successor-unknown",
                    "detail": f"successor claim {claim['id']} basis needs review",
                }
            )
        elif code == 3:
            problems.append(
                {
                    "claim": claim["id"],
                    "kind": "base-not-live",
                    "detail": f"base claim {target_id} is not live",
                }
            )
    for member in sorted(_cycle_members(items)):
        problems.append(
            {
                "claim": member,
                "kind": "cycle",
                "detail": "supersession edge lies on a directed cycle",
            }
        )
    return problems


def select(
    claims: Sequence[Mapping[str, Any]],
    *,
    subject: int | None = None,
    claimant: int | None = None,
    basis: int | None = None,
) -> list[dict[str, int]]:
    """Filter projection over stored claim fields, in input order.

    Only equality filters over exact identities; the projection invents
    nothing and returns normalized copies. Status filtering composes with
    ``status_view`` on the caller's side.
    """
    if subject is not None:
        subject = _u64(subject, "subject")
    if claimant is not None:
        claimant = _u64(claimant, "claimant")
    if basis is not None:
        basis = _u64(basis, "basis")
    selected: list[dict[str, int]] = []
    for raw in claims:
        claim = normalize_claim(raw)
        if subject is not None and claim["subject"] != subject:
            continue
        if claimant is not None and claim["claimant"] != claimant:
            continue
        if basis is not None and claim["basis"] != basis:
            continue
        selected.append(claim)
    return selected


__all__ = [
    "BASIS_UNKNOWN",
    "CLAIM_FIELDS",
    "STATUSES",
    "attribution_due",
    "basis_compatible",
    "claim_status",
    "claims_compatible",
    "dim_compatible",
    "evidence_state",
    "find_conflicts",
    "normalize_claim",
    "resolve_superseded",
    "select",
    "signed_state",
    "status_view",
    "supersede_link_valid",
    "supersession_problems",
    "temporal_state",
]
