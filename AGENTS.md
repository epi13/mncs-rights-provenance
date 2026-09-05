# MNCS agent execution contract (rights & provenance)

This repository owns **rights semantics** in the ecosystem authority table
(pressure semantics MNCDS, coordination MNCS-Commons, language capability
mncs-language, assurance mncs-forge-mcp, transport mncs-actions). It adopts
the ecosystem agent contract bound in mncs-actions (`AGENTS.md` there) with
the language mirror in mncs-language. Enforced by
`tests/test_agent_contract.py`: every path named below must exist.

## 1. Normative MNCS cores come first

Release-policy decisions, pressure verdicts, and check projections are
defined once in MNCS-language and mirrored in host code, never the reverse:

- `language/rights_policy.mncs` — release-policy decision engine.
- `language/pressure_provenance.mncs` — tri-state distributed-pressure
  verdicts (`combine_verdict`, `promotion_combined`, `authority_verdict`,
  `lineage_verdict`).
- `language/check_projection.mncs` — Outcome to check-verdict projection.
- `language/corpora/` plus `language/run_backend_tests.sh` — execution
  corpora with cross-backend agreement checks.

Changing host mirroring without changing (or deliberately confirming) the
normative core is a defect. New semantics land in the `.mncs` core with
corpus agreement before host code relies on them.

## 2. Pressure routing

Language or compiler gaps found here (a verdict unexpressible in the active
profile, a backend that cannot realize valid semantics) become
development-pressure evidence owned by mncs-language, per
`specs/distributed-pressure.md`. Fix upstream, re-run this repository's
corpus agreement, then resume.

## 3. Projection discipline

Native reports project to `mncs.check-result/1` only through
`scripts/rp_to_check.py`. PASS/FAIL/UNKNOWN versus no-claim is load-bearing:
uncertainty stays explicit, and promotion keeps its eight independent
dimensions with breakdowns retained.

## 4. Badges derive from evidence

This repository currently carries no MNCS conformance badge in `README.md`;
do not add a decorative one. A future badge must render the evidence-driven
verdict and must not overstate what the corpora and agreement checks prove.
