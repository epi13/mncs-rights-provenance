# Policy Core Specification v0.2

The release-policy **decision semantics** are implemented once, in MNCS-language,
as `language/rights_policy.mncs` (module `mncs.rights.policy.v01`). Host
implementations mirror it and are pinned to it by golden vectors.

## Status

- `evaluate` / `gate_severities` semantics: **normative** (this file + module).
- Default enforcement ceilings: **normative** for the canonical-release profile.
- Profiles may only *lower* enforcement (cap severities); they cannot raise a
  gate above its default ceiling.

## Encoding contract

Integer codes are fixed; changing them is a breaking spec change requiring a
schema-version bump and a migration note.

| Field | Codes |
|---|---|
| origin_code | 0 human-authored, 1 human-ai-assisted, 2 human-directed-machine-generated, 3 autonomous-machine-generated, 4 mixed-machine-origin, 5 third-party-derived, 6 generated-from-licensed-source, 7 generated-from-public-domain-source, 8 origin-uncertain |
| copyright_code | 0 human-authorship-confirmed, 1 human-authorship-material, 2 mixed-or-undetermined, 3 machine-originated-unresolved, 4 third-party-licensed, 5 public-domain-asserted, 6 unresolved |
| rights_basis_code | 0 project-owned-or-controlled, 1 contributor-attested, 2 third-party-license, 3 public-domain-basis, 4 no-exclusive-right-asserted, 5 unknown-needs-review |
| third_party_code | 0 none-known, 1 present, 2 possible, 3 unknown |
| prov_valid_code | 0 passed, 1 failed, 2 incomplete, 3 not-run |
| human_accept_code | 0 accepted, 1 rejected, 2 not-reviewed, 3 not-required |

Booleans are encoded as the `Truth` finite type (`No` = 0, `Yes` = 1).

## Severity lattice

`None(0) < Finding(1) < Review(2) < Blocking(3)`; combination is max.

## Enforcement ceilings

`Disabled(0) < FindingCap(1) < ReviewCap(2) < Fatal(3)`. A ceiling caps how
loudly a gate may speak: effective severity = min(raw severity, ceiling rank),
where Disabled maps everything to None and Fatal preserves raw severity.

## Gates and default ceilings (canonical order)

| # | Gate field (language) | Schema gate name | Raw trigger | Default ceiling |
|---|---|---|---|---|
| 0 | hash_correspondence | artifact_hash_correspondence | artifact/hash mismatch | fatal |
| 1 | evidence_refs | evidence_references_resolve | any broken evidence reference | review |
| 2 | graph_integrity | graph_integrity | DAG integrity violation | fatal |
| 3 | incompatible_license | no_incompatible_third_party_license | >=1 incompatible source | fatal |
| 4 | contradictory_license | no_contradictory_license_evidence | >=1 license-evidence contradiction | review |
| 5 | rights_basis_resolved | rights_basis_resolved | basis unknown-needs-review | review |
| 6 | third_party_resolved | third_party_material_resolved | possible/unknown (canonical profile: review; development: finding) | review |
| 7 | copyright_resolved | copyright_status_resolved | unresolved (canonical: review; development: finding) | review |
| 8 | provenance_passed | provenance_validation_passed | provenance validation failed | fatal |
| 9 | provenance_complete | provenance_complete | incomplete/not-run | review |
| 10 | human_review_ok | human_review_state_acceptable | rejected -> blocking; not-reviewed (canonical: review; dev: finding) | review |
| 11 | unknown_source_license | unknown_source_license | >=1 unknown-status source (canonical: review; dev: finding) | review |
| 12 | attestation_integrity | attestation_integrity | conflicting attestations | review |
| 13 | impossible_evidence_gate | no_falsified_or_impossible_evidence | falsified/impossible evidence | fatal |

## Outcome derivation

Over structurally valid manifests:

- any effective Blocking -> `blocked`
- else any effective Review -> `review-required`
- else any effective Finding -> `pass-with-findings`
- else -> `pass`

Structurally invalid manifests are `invalid` before gates run. A passing
outcome records that project evidence requirements were met. It is never a
legal warranty of title or non-infringement, and never a determination of
copyright status.

## Cross-implementation conformance

1. `python3 language/tools/gen_corpus.py` regenerates corpora + golden vectors.
2. `bash language/run_backend_tests.sh` executes the MNCS core across compiler
   backends (`research-bytecode`, `portable-wasm`) and checks every expectation.
3. `pytest tests/test_policy_golden.py` pins the Python implementation to the
   same vectors.
4. The Rust validator consumes the same golden vectors in its test-suite.

Backend coverage exclusions and their reasons live in
`docs/language-findings.md`.
