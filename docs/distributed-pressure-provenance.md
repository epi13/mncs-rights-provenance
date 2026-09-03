# Distributed Pressure Provenance: Contributor Guide

How `mncs-rights-provenance` participates in the six-repository coordinated
workflow, and how to tell the ten load-bearing concepts apart.

Sibling contracts (authority stays where it belongs):

- MNCDS `docs/development-pressure-protocol.md` — lifecycle, ChangeSets, authority levels
- Commons `docs/development-pressure-records.md` — exchange records, relationships
- Forge `docs/development-pressure-workflow.md` — bounded evaluation
- mncs-language `docs/capability-gap-artifacts.md` — technical gap artifacts
- MNCS `docs/development-pressure-evidence.md` — evidence meaning, promotion boundary
- this repo `specs/distributed-pressure.md` — normative lineage/authority/promotion role

## The ten concepts, concretely

Follow one running example: application `example/app` discovers the language
cannot express a bounded retry with explicit authority (a real pressure).

1. **Observation/evidence.** The developer runs the reproducer; Fabric emits
   an execution record: inputs, outputs, hashes, outcome. That record says
   what happened — nothing more.
2. **Claim.** The Forge license scanner asserts `license-identification:
   Apache-2.0` with confidence `observed-declaration`. The claim is scoped to
   the scanned files; downstream policy decides what it is worth.
3. **Proposal.** A contributor proposes `ResolutionProposal R1`: add a bounded
   retry primitive to Profile 0.7. A second contributor proposes incompatible
   `R2`. Both keep separate identities; neither is authoritative.
4. **Evaluation.** Forge freezes `R1` (candidate + corpus + evaluator plan +
   dependency snapshot), runs reference/backend/negative/compatibility checks
   on `research-bytecode`, and publishes an identity-bound evidence record:
   evaluator version, policy revision, accepted/rejected evidence, output,
   `binding: advisory`. Missing WASM coverage is recorded as UNKNOWN.
5. **Authority.** The manifest lists the proposer as
   `actor_class: human-directed-agent` (identity). A separate authority claim
   says `may_propose: pass` asserted by the maintainer with evidence, while
   `may_promote: unknown` stays unresolved. Identity and permission are never
   merged; unknown stays unknown.
6. **Contribution.** The developer submits the patch with a
   `contribution-scope` attestation: what was submitted, what third-party
   sources were referenced, what machine assistance occurred, what remains
   unresolved. The attestation is evidence an assertion was made — not proof
   it is true.
7. **Derivation.** A lineage record links `pressure → gap → R1 → evaluation →
   adoption` with relations `gap-derived-from`, `resolves-gap`,
   `evaluated-by`, `member-of`. Content digests bind every step, so the chain
   survives rebases and branch deletions.
8. **Approval.** A maintainer approves `R1` for `scope: profile-0.7-experimental`
   at `authority_level: 3`, citing the Forge evidence. Approval is scoped;
   success of the tests alone never manufactures it.
9. **Promotion.** The promotion input set reports eight dimensions
   independently: technical PASS, test PASS, compiler-backend UNKNOWN
   (WASM pending), coordination PASS, provenance PASS, authority UNKNOWN
   (promotion right unresolved), rights PASS, policy UNKNOWN. Combined:
   UNKNOWN — correctly blocking promotion while keeping every dimension
   inspectable. See `examples/v0.3/lineage-record-example.json`.
10. **Rights state.** The manifest records `distribution_license: Apache-2.0`,
    `copyright_status: mixed-or-undetermined`, `rights_basis:
    contributor-attested`, `third_party_material: none-known`, with source
    evidence. Passing policy means evidence requirements were met — never a
    legal warranty.

## Why this matters for recursive distributed development

The more MNCS lets software development create pressure that changes the
language, compiler, library, and tooling underneath itself, the more the
ecosystem needs to answer: **why does this language feature exist, who/what
produced it, what evidence justified it, what did it derive from, and who was
authorized to promote it** — even when many humans and machines apply
pressure concurrently across many repositories.

Without stable lineage, concurrent pressure collapses into folklore:
two teams discover the same gap and fork incompatible fixes; a branch is
deleted and the rationale vanishes; a CI green check is mistaken for a
promotion decision; an agent's patch is mistaken for ownership; a valid
provenance trail is mistaken for technical correctness.

The primitives in this repository — content-addressed lineage records,
scoped authority claims, per-dimension promotion inputs, explicit
supersession, append-only amendments, tamper-evident digests — are the
minimum boring machinery that keeps the recursive loop explainable,
auditable, evidence-backed, rights-aware, and safely promotable without a
central mutable "current truth", a global consensus protocol, or fake
cryptographic assurances.

## Working with lineage records

```bash
# verify structure + content digest (tamper-evident)
mncs-rp lineage verify dogfood/distributed-pressure-changeset.json

# combine promotion dimensions (FAIL > UNKNOWN > PASS, breakdown retained)
mncs-rp promotion evaluate dogfood/distributed-pressure-changeset.json

# migrate a v0.2 manifest (bumps version, invents nothing)
python3 scripts/migrate_02_to_03.py RIGHTS.json

# regenerate pressure corpora + golden vectors from the normative core
python3 language/tools/gen_pressure_corpus.py
python3 language/tools/gen_corpus.py

# multi-backend agreement (research-bytecode + portable-wasm)
bash language/run_backend_tests.sh
MNCS_BIN=/path/to/mncs-compiler bash language/run_backend_tests.sh
```

## Boundaries to respect

- Never invent provenance, authority, authorship, rights, approval, or
  evidence to make a demonstration complete. UNKNOWN is better.
- Never rewrite a historical record. Amend with a new linked record.
- Never let component PASS imply system PASS, execution imply acceptance,
  provenance imply correctness, or attestation imply truth.
- Commons retains memory; it does not confer authority. Forge evaluates
  candidates; it does not own the standard. The compiler emits gaps; it
  does not decide promotion. This repository records the facts and claims
  the others consume — it is not a workflow engine.
