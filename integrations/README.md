# MNCS Integration: what exists now

This document describes the integrations that are **implemented and tested**,
not aspirations. For the original v0.1 integration plan, see git history of
this file.

## mncs-fabric — primary process-evidence producer

- `src/mncs_fabric/provenance.py` projects execution records into standalone
  evidence records (`kind=fabric-execution`, schema 0.2.0), content-addressed
  with the family's canonical-JSON SHA-256 convention.
- CLI: `mncs-fabric provenance emit <record.json> [--receipt r.json]
  [--run-id ...] [--task-id ...]`.
- Boundary: Fabric emits observations (outputs/inputs with sha256, identities,
  argv digest, outcome, node fingerprint). It never classifies origin by its
  own authority; caller-supplied proposals are carried as attributed claims.
- The receipt format is untouched; evidence references receipts by identity.

## mncs-forge-mcp — evidence analysis

- v0.2 manifests validate alongside v0.1 (version-aware packaged schemas);
  Forge drafts emit conservative v0.2 documents under `spec_profile=development`.
- New operation `rights.license-evidence.scan` (CLI
  `mncs-forge license-evidence scan`, MCP tool
  `mncs_forge_license_evidence_scan`) produces a confidence-ranked license
  evidence record: declared metadata → `observed-declaration`; notice-file
  keywords → `heuristic` + recorded sha256; nothing found →
  `insufficient-evidence` ("do not infer one").
- Existing `observe/advisory/enforced` policy modes and candidate-selection
  enforcement continue to work unchanged on both manifest versions.

## mncs-validator-rs — independent release-policy evaluation

- `mncs-rs rights-validate <manifest>` performs structural validation,
  RFC 8785 identity verification, DAG integrity checks, and canonical-release
  gate evaluation mirroring this repository's MNCS-language core.
- Golden vectors (`fixtures/rights-conformance/golden-vectors.json`) are
  generated from `language/rights_policy.mncs`'s reference semantics and must
  reproduce exactly in Rust tests.
- Exit codes distinguish outcomes: pass=0, findings/review=4, blocked=3,
  invalid=1. Reports are structured JSON including per-gate severities.
- Technical-correctness validation remains a separate layer; neither promotes
  the other.

## MNCS-Commons — institutional memory

- `adapters/rights.py` projects evidence records into inert Observations
  (producer-attributed, UNKNOWN claim-verification status preserved) and
  bounds validator reports into retention summaries explicitly marked as
  historical rather than current policy.
- Unsupported schema versions refuse to guess; supersession uses standard
  Commons relations/lifecycle.

## mncs-control-mcp / mncs-harness — context across boundaries

- Control experiments accept a `rights_evidence` producer-reference relation;
  rights manifests/evidence ride the existing producer-reference spine across
  handoffs and publications without payload duplication.
- Harness `to_rights_participant()` maps actor-provenance records to manifest
  participants preserving `stable_id`/content-digest traceability.

## Repository conventions

A repository adopting rights & provenance needs exactly one new file plus an
optional state directory:

```
mncs-rights.toml          # or a "rights_provenance" table in mncs-forge.toml:
                          #   mode = "observe" | "advisory" | "enforced"
                          #   manifest = "RIGHTS.json"
RIGHTS.json               # current manifest (spec_profile selects strictness)
.mncs-rights/             # optional local evidence store for resolved refs
```

Development tolerates incomplete provenance (`spec_profile = "development"`
downgrades uncertain states to findings). Canonical public releases should use
`canonical-release` where unresolved states route to review.

## Release bundle shape

A release pipeline can emit alongside ordinary artifacts:

```
<artifact files>
RIGHTS.json                     # sealed manifest (manifest_identity attached)
evidence/*.json                 # fabric/forge/validation evidence records
spdx.json                       # SPDX 2.3 export
validator-report.json           # mncs-rs rights-validate output
```

See `examples/end-to-end/run_demo.sh` for a working pipeline through all
family members.
