# Rights & Provenance in Distributed Development Pressure v0.3

> **Status:** experimental, additive to v0.2. v0.2 manifests and evidence
> records remain valid. v0.3 adds optional lineage/authority/promotion
> inputs for the six-repository coordinated pressure workflow. This
> specification describes what is implemented in this repository; sibling
> design notes own the rest.

## 1. Role boundary

`mncs-rights-provenance` provides **facts, claims, manifests, attestations,
relationships, and policy inputs** for distributed pressure. It does not own:

| Owner | Owns |
|---|---|
| MNCDS (`development-pressure-protocol.md`) | development-process semantics, lifecycle, authority levels, ChangeSet definition |
| MNCS (`development-pressure-evidence.md`) | evidence meaning, acceptance boundary, promotion boundary |
| Commons (`development-pressure-records.md`) | exchange surface, coordination records, relationship retention |
| Forge (`development-pressure-workflow.md`) | bounded evaluation workflow, candidate comparison |
| mncs-language (`capability-gap-artifacts.md`) | technical capability-gap semantics, emission rules |
| **this repository** | **provenance/authority/rights facts and claims that let the above interoperate without collapsing into one another** |

In particular this repository never decides: whether a proposal is
technically correct, whether an evaluation is authoritative, whether a
promotion is warranted, or what any legal conclusion is. It records the
evidence and claims those decisions consume and emit, with explicit
`PASS / FAIL / UNKNOWN` scoping and explicit unknowns.

## 2. Ten concepts stay distinct

| # | Concept | What it is | Where its authority lives |
|---|---|---|---|
| 1 | observation / evidence | what a producer directly saw or measured | producer (Fabric, Forge, compiler, human, tool) |
| 2 | claim | a scoped assertion a producer is willing to defend, with confidence | producer; confidence never upgraded downstream |
| 3 | proposal | one candidate response to pressure | proposer; MNCDS/Commons record identity |
| 4 | evaluation | bounded execution/comparison of a frozen candidate | evaluator (Forge, backend, human reviewer); declared plan |
| 5 | authority | whether a participant may perform a transition in a scope | policy / maintainer / governance; recorded as a scoped claim |
| 6 | contribution | an actor's submitted work unit bound to a ChangeSet | contributor attestation + repository PR |
| 7 | derivation | a causal edge: X was produced from Y via T with evidence E | lineage record; content-addressed |
| 8 | approval | a scoped acceptance by an authorized party | approver; never inferred from evaluation alone |
| 9 | promotion | a scoped decision that a candidate/ChangeSet advances an authority level | promotion record; MNCS boundary |
| 10 | rights state | known vs unresolved license/copyright/basis facts | manifest rights section + license-evidence records |

Evidence that a compiler cannot express something is not permission to
modify the compiler. A proposed implementation is not authoritative. An
agent producing a patch implies no ownership. Tests passing implies no
provenance. Valid provenance implies no correctness. Technical approval
manufactures no legal conclusion. Promotion may require several
independent evidence dimensions (see §6).

Unknown is legitimate everywhere. Implementations MUST NOT invent
missing provenance, authority, authorship, rights, approval, or evidence.

## 3. Stable identifiers (reuse, do not reinvent)

All cross-repository references reuse the family's existing identity
primitives:

- content identity: `sha256:<64 hex>` over RFC 8785 canonical JSON
  (manifests: `manifest_identity`; evidence: `content_digest`; lineage:
  `content_digest`);
- producer reference: `{producer, recordKind, schemaVersion, stableId,
  contentDigest?, scope?}` (`commons.mncs.dev/producer-reference/v0alpha1`);
- repository revision: `{repository, commit}` strings plus artifact
  `hashes[]` and assembled `final-tree` digests owned by MNCDS/Forge records;
- local tape: evidence `reference` strings are opaque to this layer and are
  resolved by the holding repository.

This repository defines **no new hash function, no new signature scheme,
no new global registry**. A ChangeSet is identified by the ChangeSet
identity its owning record (MNCDS/Commons) assigns; rights/provenance
records **reference** that identity plus its `content_digest` when known.
References survive branch deletion, rebases, and PR merges because they
bind content digests and exact revisions, never branch names.

Reference shapes implemented in `schemas/v0.3/lineage-record.schema.json`:

- `changeset_ref`: `{changeset_id, content_digest?, base_revisions?[],
  final_tree?, source}` — `changeset_id` is the owner's stable string;
  digests bind the exact bytes when available, otherwise UNKNOWN.
- `repository_change_ref`: `{repository, commit, paths?[], tree_digest?}`.
- `artifact_ref`: `{id, class?, hash_value?, role?}`.
- `evidence_ref`: the v0.2 `evidenceRef` shape plus optional
  `producer_reference`.
- `actor_ref`: `{type, role?, name?, participant_ref?, digest?}` — identity
  only; carries no authority by itself.
- `claim_ref`: `{claim_type, statement_digest?, confidence}` — claims are
  never dereferenced into truth.

## 4. Lineage record

A lineage record is a standalone, content-addressed, append-only document
that makes one causal chain reconstructable:

```text
artifact/change/evidence —derived-from→ prior artifact/evidence
                         —member-of→ ChangeSet
                         —produced-by→ actor (identity only)
                         —evaluated-by→ evaluation binding
                         —approved-by→ approval claim (scoped)
                         —superseded-by→ successor lineage
                         —gap-link→ capability-gap artifact
```

Schema: `schemas/v0.3/lineage-record.schema.json`, implemented by
`src/mncs_rights_provenance/lineage.py`. Fields:

- `lineage_id`: producer-scoped stable string
  (e.g. `mncs-rights://lineage/<slug>`).
- `subject`: the artifact/change/evidence this record is about.
- `changesets[]`: `changeset_ref` entries. One record may belong to zero
  or more ChangeSets; zero means "lineage known, ChangeSet membership
  unknown" — not "no ChangeSet".
- `derivations[]`: `{from, to, relation, transformation?, evidence?[]}`.
  Relations reuse the manifest graph vocabulary plus pressure relations:
  `derived-from`, `transformed-by`, `validated-by`, `executed-by`,
  `attested-by`, `referenced`, `member-of`, `supersedes`, `superseded-by`,
  `resolves-gap`, `gap-derived-from`, `evaluated-by`, `approved-by`.
- `contributions[]`: `{contributor (actor_ref), contribution_id?,
  changeset_id?, attestation_digest?, evidence?[]}`. A contribution is a
  submitted work unit; the attestation is evidence the actor asserted
  something, not proof it is true.
- `evaluations[]`: Forge-style reconstructable bindings: `{evaluator,
  evaluator_version, policy_revision?, input_digest, corpus_digest?,
  backend?, worker_identity?, verdict (pass/fail/unknown),
  advisory_or_authoritative, evidence?[], unresolved?[]}`. Missing
  evaluators, versions, or inputs are recorded as explicit unknowns, never
  guessed. Forge remains the authority for what it evaluated.
- `approvals[]`: `{approver (actor_ref), scope, authority_level?,
  verdict, basis_evidence?[], policy?, unresolved?[]}`. Approval is scoped
  (see §5) and never inferred from evaluation success.
- `supersessions[]`: `{supersedes_lineage?, superseded_by?,
  reason?, evidence?[]}`. Supersession links; history is never rewritten.
- `capability_gap_links[]`: see §7.
- `lifecycle`: optional `{from_state?, to_state, actor?, evidence?[]}` —
  records that a transition was observed; MNCDS owns the lifecycle itself.
- `rights_summary`: optional pointer `{manifest_identity?,
  outcome?, legal_conclusion: NOT_MADE}` — a cached hint, never a
  substitute for the manifest.
- `unresolved[]`: explicit unknown-field names.
- `content_digest`: canonical identity.

Validation (`validation.validate_lineage_structure`) enforces structure,
bounded sizes, DAG integrity for derivation edges, and digest well-formedness.
`verify_lineage_digest` detects post-evidence tampering the same way
evidence records do: any byte change invalidates `content_digest`.

## 5. Authority is not identity

An `actor_ref` records **who or what produced something**. An
**authority claim** records **whether that actor may perform a transition
in a scope**, as asserted by somebody, with evidence, and with an explicit
verdict. The two are stored side by side and never merged.

Implemented in `src/mncs_rights_provenance/authority.py`. Vocabulary:

- actor kinds reuse manifest participants:
  `human | model | agent | tool | organization | unknown`, plus an
  explicit `actor_class`: `human | human-directed-agent |
  autonomous-agent | forge-evaluator | ci | maintainer | mnel-model |
  fabric-worker | external-contributor | federated-deployment | unknown`.
  `actor_class: unknown` is the default; classifiers MUST NOT default to
  human, trusted, or permitted.
- authority scopes (minimal, not IAM):
  `may_propose | may_provide_evidence | may_evaluate | may_attest |
  may_approve | may_promote | may_modify_repository |
  may_approve_change_class | unknown`.
  A claim may name a repository or change class for the last two scopes;
  otherwise scope is repository-agnostic.
- verdicts are tri-state: `pass | fail | unknown`. `unknown` covers
  missing, disputed, expired, or out-of-scope authority.
- An authority claim is `{subject (actor_ref), scope, repository?,
  change_class?, authority_level?, asserted_by, basis_evidence?[],
  verdict, unresolved?[]}`. It is evidence that `asserted_by` asserted a
  scoped permission — not proof the permission exists. Policy consumers
  decide.

Normative tri-state helpers live in MNCS-language
(`language/pressure_provenance.mncs`, module `mncs.rights.pressure.v01`)
and are mirrored by `promotion.py`/`authority.py` against shared golden
vectors: `combine_verdict` (`FAIL > UNKNOWN > PASS`), `authority_verdict`,
`lineage_verdict`, `promotion_combined`.

## 6. Promotion inputs (independent dimensions, no flattening)

Promotion consumes provenance evidence without equating provenance with
correctness. A promotion input set carries eight independent dimensions:

`technical | test_conformance | compiler_backend |
coordination_dependency | provenance | authority | rights_license | policy`

Each dimension is `{verdict: pass|fail|unknown, evidence?[],
unresolved?[]}`. Dimensions are reported independently and combined only
by the explicit rule `FAIL > UNKNOWN > PASS` into one summary verdict.
A failure or UNKNOWN in one dimension never fabricates a conclusion in
another, and the per-dimension breakdown is always retained alongside the
summary. The summary is a policy input, not a promotion decision; MNCS
owns the boundary.

Implemented by `src/mncs_rights_provenance/promotion.py` and normatively
by `promotion_combined` in `language/pressure_provenance.mncs`. Host and
language implementations are pinned by
`conformance/pressure-golden-vectors.json`.

Promotion-dimension evidence SHOULD reference the exact revisions,
final-tree identity, policy/evaluator revisions, and unresolved unknowns
the MNCS promotion record names. When that context is unavailable the
dimension is UNKNOWN with the gap named, never PASS.

## 7. Capability-gap provenance

A `capability_gap_link` connects a language/compiler/library/backend
deficiency to the pressure that justified it and the change that resolved
it, so a future developer can answer "why does this language feature
exist":

```text
originating repository / ChangeSet / triggering source artifact /
triggering test-or-evidence / backend-runtime / producer /
environment-toolchain / proposed workaround /
resolving language change / validation proving resolution /
adoption back into the originating consumer
```

Every field is optional except a stable `gap_ref` string (the
`gap_id`/artifact identity the language record assigns). Missing fields
are UNKNOWN, never invented. The resolving change links back with
relation `resolves-gap`; the consumer adoption links forward with
`gap-derived-from`. Amendments and re-validations are new linked records,
never overwrites — matching the language artifact contract.

## 8. Commons, Forge, MNCDS attachment points

- **Commons:** lineage records and promotion-input summaries project to
  inert Observations through the existing `adapters/rights.py` pattern
  (producer-attributed, UNKNOWN claim-verification preserved). Historical
  lineage stays historical via standard lifecycle/supersession; later
  evidence amends via `supersedes` links. Commons never becomes the source
  of legal or rights conclusions. Conflicting lineage claims coexist as
  conflicting records.
- **Forge:** an `evaluations[]` entry carries exactly what Forge needs to
  reconstruct a run: frozen inputs, exact versions, evaluator identity,
  active policy/rules, accepted/rejected evidence, output, and whether the
  evaluation was advisory or authoritative. Forge may emit lineage records
  as a publisher; it MUST record unavailable evidence as UNKNOWN.
- **MNCDS lifecycle** (`observed → localized → proposed → evaluating →
  selected|rejected → adopted|retired`): lineage `lifecycle` blocks attach
  to transitions without owning them. Important transitions
  (proposal registration, freeze, evaluation publication, selection,
  adoption) SHOULD leave a lineage record with actor, authority claim,
  evidence digests, and unresolved fields.

## 9. Distributed concurrency rules

- Append-only evidence: new results, replications, disagreements,
  invalidations, and corrections are new records linked to the original
  identity. Originals are never mutated.
- Competing proposals keep separate identities. Convergent pressures link
  (`groups_with` / `gap-derived-from`) but never silently merge.
- Supersession is explicit and preserves the full chain.
- Duplicate pressure (two projects, same gap) converges by referencing the
  same eventual `gap_ref`/resolution without erasing either origin.
- Partial failure: one ChangeSet member failing evaluation blocks
  promotion of the coordinated whole (combined verdict FAIL) without
  invalidating unrelated members' evidence; per-member dimensions stay
  inspectable.
- Tampering: any post-evidence byte change invalidates the content digest
  and MUST be reported as a digest mismatch, never silently accepted.
- Deletion/rebasing: references bind digests and exact revisions, so
  history remains reconstructable after branches and PRs disappear.
  Evidence arriving after evaluation is a new amendment, not a rewrite.

## 10. Versioning and migration

- v0.2 (`schema_version: 0.2.0`) is frozen. All v0.2 manifests, evidence
  records, corpora, and golden vectors remain valid.
- v0.3 (`schema_version: 0.3.0`) is strictly additive: optional `lineage`
  block on manifests, extended graph relations, extended evidence kinds,
  extended attestation types, plus the new standalone lineage record. v0.2
  documents validate unchanged under the v0.3 validator. v0.3 documents
  with lineage content require a v0.3-aware consumer;
  `scripts/migrate_02_to_03.py` (and `lineage.migrate_manifest_02_to_03`)
  performs the mechanical upgrade (version bump, no invented provenance).
- Emission compatibility: builders emit `0.2.0` for lineage-free manifests
  so pinned consumers (Forge's packaged schema, `mncs-validator-rs`
  `SUPPORTED_SCHEMA_VERSION`) keep working with zero changes. Attaching a
  `lineage` block bumps emission `0.2.0 -> 0.3.0` automatically (upward
  only, never downward). A deliberate pinned-version update in Forge and
  the Rust validator remains a well-scoped follow-up; it is not required
  for this change because lineage records travel alongside manifests, not
  inside the Forge-validated core.
- Changing verdict codes, severity lattices, or aggregation order is a
  breaking change requiring a version bump, migration note, golden-vector
  regeneration, and cross-repository consumer updates.

## 11. Conformance targets

1. Python lineage/authority/promotion logic reproduces
   `conformance/pressure-golden-vectors.json` exactly.
2. The MNCS-language core (`language/pressure_provenance.mncs`) executes
   its corpus on `research-bytecode` (full) and `portable-wasm`
   (verdict-only, same bare-enum shaping as the existing policy core) with
   cross-backend agreement.
3. The six-PR dogfood ChangeSet (`dogfood/distributed-pressure-changeset.json`)
   validates, with UNKNOWNs preserved where evidence is genuinely absent.
4. Negative cases (conflict, unknown, supersession, partial failure,
   tamper) behave as specified in `tests/test_pressure_provenance.py`.
