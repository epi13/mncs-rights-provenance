# MNCS-Language Findings from Rights & Provenance Work

Deficiencies and friction discovered while implementing
`language/rights_policy.mncs` and its multi-backend corpora. Each finding is
stated precisely enough to be fixed independently. Findings were produced
against mncs-language commit `ad2e89e` ("feat: portable WASM realizes the full
executable envelope"), branch `feat/backend-family-expansion`.

## LF-1 portable-wasm loses finite-type identity inside returned records

- **Severity:** high for cross-backend agreement testing.
- **Repro:** return a record whose fields are enum (`finite`) values, e.g.
  `gate_severities(input) -> GateSeverities` in `language/rights_policy.mncs`,
  executed via `mncs experiment run --backend portable-wasm`. Every field comes
  back as `{"type_identity": "unresolved", "variant_identity": "unresolved"}`.
  The same corpus passes fully on `research-bytecode` (20/20).
- **Impact:** any function returning records-of-enums cannot be
  expectation-checked through the WASM backend. Bare enum returns work.
- **Suspected area:** WASM record realization in `crates/mncs-codegen`
  (`wasm.rs`/`lower.rs`): the memory layout stores the discriminant but the
  host-side reconstruction of `ExecutionValue::Finite` lacks the semantic type
  identities, so they degrade to `"unresolved"` instead of failing closed or
  carrying the contract's type identity.
- **Desired resolution:** reconstruct finite values from the backend value
  contract (`BackendValueContract::Finite`) embedded in the artifact, or emit
  `UNSUPPORTED/UNKNOWN` for such returns rather than silently returning
  unresolved identities.

## LF-2 match has no wildcard arm

- The match grammar accepts only explicit variant arms (plus payload binders
  and `{ .. }` payload ignore). There is no `_ =>` catch-all arm.
- Impact: verbose exhaustive matches over large enums; combined with LF-3 this
  makes simple helper logic noisy. Exhaustiveness is otherwise valuable; a
  wildcard arm would be an additive Profile 0.6+ feature.

## LF-3 no module-level constants

- Top-level items are modules/enums/records/functions only. Named constants
  must be inlined as literals (see the code tables in
  `language/rights_policy.mncs`). A `const NAME: T = value;` item (or
  let-bindings at module scope) would remove magic numbers from source.

## LF-4 boolean subjects cannot be matched

- `match (x > 0) { true => .., false => .. }` does not parse: match arms are
  identifiers, and booleans are not finite variants. if/else works. Documented
  here so future contributors do not retry the pattern.

## LF-5 scalar backends refuse records/payload sums (known, in progress)

- At the referenced commit, c11/llvm-ir/cranelift fail closed on record values
  and payload-bearing variants. Work to expand the scalar realization envelope
  was observed in progress on the branch this was tested against. Until it
  lands, the rights-policy core runs its full corpus only on
  `research-bytecode`, with `evaluate`/lattice corpora also on `portable-wasm`.
  `language/run_backend_tests.sh` encodes exactly this coverage and should be
  widened when the scalar expansion lands.

## LF-6 pressure-verdict probe (2026-09): no new gap; LF-1 avoided by shape

- While implementing `language/pressure_provenance.mncs`
  (`mncs.rights.pressure.v01`: `combine_verdict`, `promotion_combined`,
  `authority_verdict`, `lineage_verdict`) no new compiler capability gap was
  encountered. The module validates cleanly and its 44-case corpus passes
  fully on **both** `research-bytecode` (44/44) and `portable-wasm` (44/44)
  with cross-backend agreement (44/44).
- The design deliberately avoids LF-1: all four functions return **bare
  `Verdict` enums** and take either bare `Verdict`/`Truth` arguments or a
  `PromotionInputs` record *input* (record inputs reconstruct correctly on
  WASM). No function returns a record-of-enums, the shape LF-1 degrades to
  `unresolved`. This is a workaround-by-shape, not a fix for LF-1 itself:
  LF-1 remains open for the existing `gate_severities` corpus.
- No capability-gap artifact was emitted for this work because no obstruction
  was met. The dogfood lineage references LF-1 as a `reports-gap` link with
  `resolving_change` UNKNOWN, preserving the honest state.

## LF-7 claims-status probe (2026-09): no new gap; LF-1/LF-2 avoided by shape

- While implementing `language/rights_claims.mncs`
  (`mncs.rights.claims.v01`: `claim_status`, `temporal_state`,
  `evidence_state`, `basis_compatible`, `attribution_due`, `signed_state`,
  `supersede_link_valid`) no new compiler capability gap was encountered.
  The module validates cleanly and its 50-case corpus passes fully on
  **both** `research-bytecode` (50/50) and `portable-wasm` (50/50) with
  cross-backend agreement (50/50).
- The design deliberately avoids LF-1 and LF-2: all entry functions take
  scalar (`u64`) or bare-enum arguments and return bare enums or `u64`
  (never records-of-enums, never records at all), so there is nothing for
  the WASM finite-identity degradation or the missing wildcard arm to
  catch on. The corpus generator needs a small encoding helper for enum
  arguments (`status()` in `language/tools/gen_claims_corpus.py`), but that
  is ordinary corpus tooling, not a language gap: declaration-inventory
  identities for enum arguments already work.
- No capability-gap artifact was emitted for this work because no
  obstruction was met. Set-level composition (supersession-edge walking,
  cycle detection, pairwise conflict reporting) stays host-side in
  `src/mncs_rights_provenance/claims.py` by design: the normative core
  never walks graphs, so no graph-traversal surface was requested from
  the language.

## Non-findings (worked as intended)

- Payload-bearing enums, exhaustive matching with payload binders, records with
  functional update, bounded integer types, strict `&&`/`||`, and the
  `experiment run/compare` harness all behaved correctly and are load-bearing
  for this subsystem.
