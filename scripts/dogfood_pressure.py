#!/usr/bin/env python3
"""Regenerate the distributed-pressure dogfood lineage record.

The record binds the six coordinated development-pressure repositories into
one reconstructable ChangeSet lineage. Every reference uses real identities
(real commits, real PR numbers, real document paths). Anything not yet known
— evaluators, promotion decisions, resolving compiler changes — stays an
explicit UNKNOWN rather than invented provenance.

Regenerate:
    python3 scripts/dogfood_pressure.py
Verify:
    mncs-rp lineage verify dogfood/distributed-pressure-changeset.json
    mncs-rp promotion evaluate dogfood/distributed-pressure-changeset.json
"""

from __future__ import annotations

import json
from pathlib import Path

from mncs_rights_provenance.lineage import lineage_record_from_dict, seal_lineage_record

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dogfood" / "distributed-pressure-changeset.json"

CHANGESET_ID = "changeset/distributed-pressure-001"

# Real merge heads at the time of writing (origin/main of each repository).
# These are content references, not branch names, so the chain survives
# branch deletion and rebases.
REPOS = {
    "mncds": {
        "repository": "github.com/epi13/machine-native-complexity-development-specification",
        "commit": "256bcad7e6cca9333954c2f2f37b3f6da8f1a8bd",
        "pr": 7,
        "doc": "docs/development-pressure-protocol.md",
    },
    "commons": {
        "repository": "github.com/epi13/MNCS-Commons",
        "commit": "ead5366fa4700657ef246df88ca17e206dd62845",
        "pr": 32,
        "doc": "docs/development-pressure-records.md",
    },
    "forge": {
        "repository": "github.com/epi13/mncs-forge-mcp",
        "commit": "805f821f4eea457c3940274750b21774c487d9a1",
        "pr": 74,
        "doc": "docs/development-pressure-workflow.md",
    },
    "language": {
        "repository": "github.com/epi13/mncs-language",
        "commit": "4f3146a97f92389490d3e8dffdf08266e3390968",
        "pr": 104,
        "doc": "docs/capability-gap-artifacts.md",
    },
    "mncs": {
        "repository": "github.com/epi13/machine-native-complexity-standard",
        "commit": "8dcab5f64816cd1994eff39e78f628a6a02bf8a6",
        "pr": 71,
        "doc": "docs/development-pressure-evidence.md",
    },
    "rights": {
        "repository": "github.com/epi13/mncs-rights-provenance",
        "commit": "0c5e17e5ea08fe03d479b5d75496beddb4affa68",
        "pr": None,  # this work becomes the sixth PR; number assigned on open
        "doc": "specs/distributed-pressure.md",
    },
}


def unknown_dimensions() -> dict:
    return {
        name: {"verdict": "unknown", "unresolved": ["no-promotion-evaluation-yet"]}
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


def build() -> dict:
    base_revisions = [
        {"repository": info["repository"], "commit": info["commit"]} for info in REPOS.values()
    ]
    return {
        "schema_version": "0.3.0",
        "lineage_id": "mncs-rights://lineage/distributed-pressure-six-repo-001",
        "subject": {
            "artifact_refs": [
                {
                    "id": f"{info['repository']}#{info['doc']}",
                    "class": "documentation",
                    "role": "subject",
                }
                for info in REPOS.values()
            ],
        },
        "changesets": [
            {
                "changeset_id": CHANGESET_ID,
                "source": "MNCDS development-pressure protocol (six-repository coordination)",
                "base_revisions": base_revisions,
            }
        ],
        "derivations": [
            {"from": "mncds#protocol", "to": "commons#records", "relation": "gap-derived-from"},
            {"from": "mncds#protocol", "to": "forge#workflow", "relation": "gap-derived-from"},
            {
                "from": "mncds#protocol",
                "to": "language#capability-gaps",
                "relation": "gap-derived-from",
            },
            {
                "from": "mncds#protocol",
                "to": "mncs#evidence-boundary",
                "relation": "gap-derived-from",
            },
            {
                "from": "mncds#protocol",
                "to": "rights#distributed-pressure",
                "relation": "gap-derived-from",
            },
            {
                "from": "language#capability-gaps",
                "to": "rights#capability-gap-links",
                "relation": "referenced",
            },
            {
                "from": "forge#workflow",
                "to": "rights#evaluation-bindings",
                "relation": "referenced",
            },
            {
                "from": "rights#distributed-pressure",
                "to": CHANGESET_ID,
                "relation": "member-of",
            },
        ],
        "contributions": [
            {
                "contributor": {
                    "type": "agent",
                    "actor_class": "human-directed-agent",
                    "role": "author",
                },
                "contribution_id": f"{name}-pressure-docs-pr{info['pr']}"
                if info["pr"]
                else f"{name}-pressure-docs",
                "changeset_id": CHANGESET_ID,
            }
            for name, info in REPOS.items()
        ],
        "evaluations": [],
        "approvals": [],
        "authority_claims": [
            {
                "subject": {
                    "type": "agent",
                    "actor_class": "human-directed-agent",
                    "role": "author",
                },
                "scope": "may_propose",
                "asserted_by": "repository-maintainer",
                "verdict": "unknown",
                "unresolved": ["maintainer-review-pending"],
            }
        ],
        "capability_gap_links": [
            {
                "gap_ref": "mncs-language/LF-1",
                "originating_repository": "github.com/epi13/mncs-rights-provenance",
                "triggering_artifact": "language/rights_policy.mncs gate_severities record return",
                "backend_runtime": "portable-wasm",
                "producer": "mncs-rights-provenance backend conformance",
                "relation": "reports-gap",
                "proposed_workaround": "pressure core returns bare Verdict enums; gate-severities corpus stays research-bytecode-only",
            }
        ],
        "promotion_dimensions": unknown_dimensions(),
        "lifecycle": {"from_state": "proposed", "to_state": "evaluating"},
        "rights_summary": {"outcome": "unknown", "legal_conclusion": "NOT_MADE"},
        "unresolved": [
            "forge-evaluation-bindings",
            "commons-retention-refs",
            "promotion-decision",
            "resolving-change-for-LF-1",
            "rights-pr-number",
            "maintainer-approvals",
        ],
    }


def main() -> int:
    record = lineage_record_from_dict(build())
    sealed = seal_lineage_record(record)
    OUT.write_text(json.dumps(sealed.to_dict(), indent=2, sort_keys=True) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
