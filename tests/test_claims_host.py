"""Host agreement for the rights-claim status core plus set-layer behavior.

Golden agreement: the host mirror (``mncs_rights_provenance.claims``) must
reproduce every symbolic vector in ``conformance/claims-golden-vectors.json``,
the same contract the MNCS-language core executes across compiler backends.
Set layer: supersession resolution, conflict reporting (never resolving),
problem surfacing (dangling links, mismatches, cycles), UNKNOWN preservation,
and the filter projection.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mncs_rights_provenance import claims as host

CONFORMANCE = Path(__file__).resolve().parents[1] / "conformance"
GOLDEN = CONFORMANCE / "claims-golden-vectors.json"


def _vectors() -> list[dict]:
    return json.loads(GOLDEN.read_text())["cases"]


def _evaluate(vector: dict):
    function = vector["function"]
    inputs = vector["inputs"]
    if function == "claim_status":
        return host.claim_status(inputs["claim"], inputs["now"], inputs["superseded"])
    if function == "attribution_due":
        return host.attribution_due(inputs["attribution"], inputs["status"])
    if function == "basis_compatible":
        return host.basis_compatible(*inputs["args"])
    if function in ("temporal_state", "evidence_state", "supersede_link_valid"):
        return getattr(host, function)(*inputs["args"])
    if function == "signed_state":
        return host.signed_state(*inputs["args"])
    raise AssertionError(f"no host mirror for {function}")


@pytest.mark.parametrize(
    "vector",
    _vectors(),
    ids=lambda v: (
        v["function"]
        + ":"
        + str(v["inputs"].get("claim", v["inputs"].get("status", v["inputs"].get("args", "?"))))
    ),
)
def test_host_matches_golden(vector: dict) -> None:
    assert _evaluate(vector) == vector["output"]


def _base(**overrides) -> dict:
    claim = {
        "id": 1,
        "subject": 7,
        "claimant": 3,
        "basis": 2,
        "license": 9,
        "attribution": 1,
        "redistribute": 1,
        "derivatives": 1,
        "commercial": 2,
        "evidence": 42,
        "effective": 100,
        "expires": 0,
        "revoked": 0,
        "supersedes": 0,
        "verified": 0,
        "contested": 0,
    }
    claim.update(overrides)
    return claim


def test_supersession_chain_resolves() -> None:
    old = _base(id=1, verified=1)
    new = _base(id=2, verified=1, supersedes=1)
    assert host.resolve_superseded([old, new], 500) == {1: True, 2: False}
    view = {entry["id"]: entry for entry in host.status_view([old, new], 500)}
    assert view[1]["status"] == "Superseded"
    assert view[1]["superseded"] is True
    assert view[2]["status"] == "Verified"
    assert view[2]["attribution"] == 1


def test_cross_subject_edge_is_problem_not_supersession() -> None:
    base = _base(id=1, subject=7)
    other = _base(id=2, subject=8, supersedes=1)
    assert host.resolve_superseded([base, other], 500) == {1: False, 2: False}
    problems = host.supersession_problems([base, other], 500)
    assert [(p["claim"], p["kind"]) for p in problems] == [(2, "subject-mismatch")]


def test_dangling_link_surfaces() -> None:
    lone = _base(id=1, supersedes=99)
    problems = host.supersession_problems([lone], 500)
    assert [(p["claim"], p["kind"]) for p in problems] == [(1, "dangling-link")]
    # A dangling link names nobody, so nobody is superseded by it.
    assert host.resolve_superseded([lone], 500) == {1: False}


def test_unknown_successor_and_dead_base_surface() -> None:
    base = _base(id=1)
    unknown = _base(id=2, basis=5, supersedes=1)
    problems = host.supersession_problems([base, unknown], 500)
    assert (2, "successor-unknown") in [(p["claim"], p["kind"]) for p in problems]
    dead = _base(id=3, expires=100)
    heir = _base(id=4, supersedes=3)
    problems = host.supersession_problems([dead, heir], 500)
    assert (4, "base-not-live") in [(p["claim"], p["kind"]) for p in problems]


def test_cycle_members_reported_never_headed() -> None:
    first = _base(id=1, supersedes=2)
    second = _base(id=2, supersedes=1)
    problems = host.supersession_problems([first, second], 500)
    cycles = sorted(p["claim"] for p in problems if p["kind"] == "cycle")
    assert cycles == [1, 2]


def test_conflicts_reported_without_resolution() -> None:
    permit = _base(id=1, verified=1)
    forbid = _base(id=2, verified=1, redistribute=0)
    assert host.find_conflicts([permit, forbid]) == [{"a": 1, "b": 2, "subject": 7}]
    # Both claims keep their own status: the conflict changes nothing.
    view = {entry["id"]: entry for entry in host.status_view([permit, forbid], 500)}
    assert view[1]["status"] == "Verified"
    assert view[2]["status"] == "Verified"


def test_unknown_preserved_beside_verified_conflict() -> None:
    verified = _base(id=1, verified=1, redistribute=1)
    bare = _base(id=2, evidence=0, verified=0, redistribute=0)
    assert host.find_conflicts([verified, bare]) == [{"a": 1, "b": 2, "subject": 7}]
    view = {entry["id"]: entry for entry in host.status_view([verified, bare], 500)}
    assert view[2]["status"] == "Unknown"
    assert view[2]["attribution"] == 2


def test_select_filters_stored_fields_only() -> None:
    first = _base(id=1, subject=7)
    second = _base(id=2, subject=8, claimant=9)
    assert [c["id"] for c in host.select([first, second], subject=7)] == [1]
    assert [c["id"] for c in host.select([first, second], claimant=9)] == [2]
    assert [c["id"] for c in host.select([first, second], basis=2)] == [1, 2]
    assert host.select([first, second], subject=77) == []


def test_invalid_claims_rejected() -> None:
    incomplete = _base()
    del incomplete["evidence"]
    with pytest.raises(ValueError):
        host.normalize_claim(incomplete)
    with pytest.raises(ValueError):
        host.normalize_claim(_base(evidence=True))
    with pytest.raises(ValueError):
        host.normalize_claim(_base(expires=-1))
    with pytest.raises(ValueError):
        host.attribution_due(1, "Bogus")
    with pytest.raises(ValueError):
        host.resolve_superseded([_base(id=1), _base(id=1)], 500)
