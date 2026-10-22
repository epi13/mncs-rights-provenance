# mncs-actions integration

This repository is the first real external caller of the MNCS family
verification infrastructure (`epi13/mncs-actions`). The flow is:

```text
mncs-rights-provenance
        |
        v
native rights/provenance evaluation (mncs-rp validate)
        |
        v
authoritative native result (outcome/severity/findings/issues/identity)
        |
        v
rights adapter / native check emission (scripts/rp_to_check.py)
        |
        v
mncs.check-result/1
        |
        v
mncs-actions/run-check
        |
        v
aggregate boundary
        |
        v
evidence manifest + receipt
```

## What is native, what is projected

The native result is the `mncs-rp validate` JSON report: `outcome`
(`pass`, `pass-with-findings`, `review-required`, `blocked`, `invalid`),
per-gate severities, findings, issues, manifest identity, and
`legal_conclusion: NOT_MADE`. It stays intact and authoritative; nothing
is replaced.

The shared boundary projection (`src/mncs_rights_provenance/check_projection.py`,
surfaced via `scripts/rp_to_check.py`) carries the native result into
`mncs.check-result/1` without redefining it:

| Native `outcome` | Check `verdict` |
| --- | --- |
| `pass` | `PASS` (requires coherence + identity match) |
| `blocked`, `invalid` | `FAIL` (valid negative established) |
| `pass-with-findings`, `review-required`, `unknown` | `UNKNOWN` (review outstanding; never PASS) |
| unrecognized non-empty | `UNKNOWN` + drift note (never PASS) |

No claim (the projection emits nothing; the execution layer records
`NOT_ESTABLISHED`/`INVALID` instead of fabricating a verdict):

- missing/empty/non-string `outcome` (malformed report);
- `pass` for a structurally invalid manifest (self-contradictory);
- `invalid` for a structurally valid manifest (self-contradictory).

Binding failure (`manifest_identity_matches: false`) downgrades an
otherwise-passing claim to `FAIL`: tampering is Fail, never a pass,
never silent. The projection is mirrored in MNCS by
`language/check_projection.mncs` (compiled clean; arms pinned by
`tests/test_check_projection.py`) and carried without reinterpretation
by `mncs-actions` (`adapters/rights_adapter.py` mirrors the same table;
this repository owns the meaning).

### Source-rights policy diagnostics

When the native report contains recognized
`mncs.rights.policy-diagnostic/1` records, the projection preserves them in
the optional `rights_diagnostics` check-result extension and adds a concise
message and remedy to the standard `unresolved` list. This currently carries
the bounded diagnostics for unverified source-license declarations and
contradictory declarations. Each record remains marked
`declared-unverified` with `legal_conclusion: NOT_MADE`; a declared status is
not promoted to a verified fact or a legal compatibility conclusion.
The array contract is published at
`schemas/v0.1/check-result-rights-diagnostics.schema.json`, which references
the individual diagnostic schema.

The projection accepts at most eight records and 64 KiB total. Unsupported or
malformed records are omitted with an explicit `unresolved` note. This
explanation never changes the native outcome mapping above: for example, a
native `pass` remains `PASS` even when a diagnostic is attached, and any
release policy that requires review must express that in the native result.
Consumers should preserve the extension when forwarding the check result;
`unresolved` still provides a useful summary to consumers that do not inspect
the extension. This repository's CI path uses `scripts/rp_to_check.py` and
emits the extension. The separate `mncs-actions/adapters/rights_adapter.py`
still mirrors the verdict table without emitting `rights_diagnostics`, so
this payload is not yet available when that alternate adapter is selected.
The shared check schema accepts extra fields, but preservation through every
downstream transformation has not been established.

## How mncs-actions is invoked

`.github/workflows/mncs-family.yml` calls the reusable workflow at an
immutable SHA pin (never `@main`):

```yaml
uses: epi13/mncs-actions/.github/workflows/mncs-family-verify.yml@<40-hex-sha>
```

with `required-checks: rights-provenance,project-tests`,
`boundary: rights-family`, and provider commands that install the
package and run `scripts/ci-rights-check.sh` /
`scripts/ci-project-check.sh`. Each provider writes its check-result and
exits 0 when a check was established (the verdict carries the signal);
nonzero means no claim was established and fails closed.

## What a CI boundary means here

- Required `PASS` everywhere -> aggregate `PASS`.
- Required `FAIL` anywhere -> aggregate `FAIL` (a required check
  established a negative result).
- Required `UNKNOWN` or missing -> aggregate `UNKNOWN` (insufficient
  evidence; never fabricated into `PASS`).
- Optional providers stay visible in `unresolved` without deciding the
  boundary; omitted providers are absent (absent optional = no effect,
  absent required = `UNKNOWN`); explicitly listed but missing files are
  `INVALID`/`NOT_ESTABLISHED`.

Applicability for this repository today: `rights-provenance` and
`project-tests` are required. `mncs-validation` is intentionally not
applicable (this repository ships no validator-consumable bundle; its
MNCS cores are covered inside `project-tests` via backend agreement
checks), so no `mncs-command` is passed -- absence is declared, never
recorded as `PASS`.

Current honest state: the rights provider evaluates
`dogfood/human-specification.json`, which genuinely reports
`review-required` (human review outstanding) -> `UNKNOWN`. The family
job therefore runs with `fail-on-unknown: false`: the boundary records
`UNKNOWN` visibly in verdict outputs and evidence artifacts without
fabricating `PASS`. Flip it to `true` once a reviewed release manifest
lands; `tests/test_check_projection.py` pins the current expectation.

## Evidence

Every run preserves the aggregate `aggregate-result.json` (with
per-component `digest`/`path` bindings), the `evidence-manifest.json`
(with `references[]` entries including the `rights-manifest` kind
carrying manifest path + identity digest), and the execution receipts --
the beginning of the ChangeSet evidence graph:

```text
aggregate-result
    |
    +-- references rights check-result (digest + path)
    |       |
    |       +-- references native rights manifest (rights-manifest kind)
    |
    +-- references project-tests check-result
```

`mncs-actions` carries these references; this repository defines what
the rights references mean.
