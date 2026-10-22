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
- `language/source_license_status.mncs` — typed source-license assessment
  classification that keeps unverified declarations separate from verified
  compatible, incompatible, unknown, and not-applicable assessments; mirrored
  by `src/mncs_rights_provenance/policy_input.py` and pinned by
  `language/tools/gen_source_license_status_corpus.py`,
  `language/corpora/source-license-status-corpus.json`,
  `conformance/source-license-status-golden-vectors.json`, and
  `tests/test_source_license_status.py`.
- `language/pressure_provenance.mncs` — tri-state distributed-pressure
  verdicts (`combine_verdict`, `promotion_combined`, `authority_verdict`,
  `lineage_verdict`).
- `language/check_projection.mncs` — Outcome to check-verdict projection.
- `language/rights_claims.mncs` — per-claim rights status, conflict,
  supersession, attribution, and UNKNOWN preservation (module
  `mncs.rights.claims.v01`), mirrored in host code by
  `src/mncs_rights_provenance/claims.py` (scalar mirror plus set-level
  query layer, pinned by `tests/test_claims_host.py`).
- `language/rights_license_actions.mncs` — source/binary redistribution
  trigger classification for indexed license conditions, pinned by its
  bounded cross-backend corpus and host-projection checks.
- `language/implementation_lineage.mncs` — evidence-aware component and
  aggregate classification for machine-native, host-language, migrated,
  inherited-external, generated, mixed, and unknown implementation origins;
  pinned by `language/corpora/implementation-lineage-corpus.json` and
  `tests/test_implementation_lineage_core.py`. This core does not determine
  authorship, ownership, completeness, or legal independence.
- `language/manifest_reference_consistency.mncs` — repeated manifest-reference
  consistency and the bounded rule for when distinct declarations need a
  compatibility review; it does not resolve license compatibility. Its host
  mirror and cross-backend corpus are pinned by
  `language/tools/gen_manifest_reference_consistency_corpus.py`,
  `language/corpora/manifest-reference-consistency-corpus.json`,
  `conformance/manifest-reference-consistency-golden-vectors.json`, and
  `tests/test_manifest_reference_consistency_core.py`.
- `language/rights_agent_governance.mncs` — versioned profile guidance
  vocabulary and supported field/value pairs; it grants no legal rights and
  is pinned against the host context mirror by
  `language/corpora/agent-governance-corpus.json` and
  `tests/test_agent_governance.py`.
- `language/corpora/` plus `language/run_backend_tests.sh` — execution
  corpora with cross-backend agreement checks.

Source-rights policy explanations are a bounded projection over manifest
declarations, not a second policy engine. `src/mncs_rights_provenance/policy_diagnostics.py`
projects the active unknown/unverified and contradictory-source gates into
`mncs.rights.policy-diagnostic/1` records validated by
`schemas/v0.1/policy-diagnostic.schema.json` and pinned by
`tests/test_policy_diagnostics.py`. These records retain source and evidence
references while marking them `declared-unverified`; they must not promote
claims to verified facts, change gate severity, or replace
`legal_conclusion=NOT_MADE`.
The operational contract and output bounds are in
`docs/source-rights-policy-diagnostics.md`.

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
