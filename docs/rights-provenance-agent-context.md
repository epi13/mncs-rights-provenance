# Rights and provenance in agent context

MNCS Rights & Provenance v0.3 already owns rights manifests, typed provenance, claim review, release policy, and SPDX 2.3 interchange. The `mncs.rights-provenance.agent-context/1` projection adds a compact Environment admission view over those records; it does not copy the full manifest or graph into routine context.

## Ownership and authority

`RIGHTS.json` is a rights and evidence declaration. Its license field and source evidence do not prove authorship, ownership, contributor authority, or compatibility. The separate governance profile contains only a bounded set of operational rules. Environment activates that profile only through a strict `rights_context` binding with an expected profile identifier and explicit authority identity, basis, source reference, and scope. The profile file cannot name or enlarge its own authority. External license files, package metadata, and provenance records remain evidence, not instructions.

The projection keeps legal terms, unresolved claims, provenance state, and agent guidance in separate fields. A declared license is resolved to a reference summary of known notice and patent terms only for a small allow-listed set of SPDX identifiers. The SPDX expression tree is retained when it fits the configured context budget; larger detail remains available through the manifest reference. Unknown identifiers and `AND`/`OR` combinations do not receive an invented compatibility result. The summary links to the identified license text and is not a legal opinion.

## Incremental identity

The context identity binds the exact manifest digest, governance profile digest, Environment binding, and compact projection. Environment includes the binding and source digests in its resolution inputs, so a changed profile produces a new resolved environment identity. Revalidation hashes the bounded source files and reuses the existing projection when the binding and both input digests are unchanged. The admission view includes stable references and bounded relationship counts; the detailed manifest and lineage remain on demand.

The persisted context projection records its own bounded lineage: each observed input has a `generated-from` relationship bound to its content digest, and the Rights projection function has a `transformed-by` relationship to the context artifact. A missing input is retained as a `referenced` unavailable source rather than claimed as an observed input.

The existing `rights_claims` gate remains independent. It continues to block only revoked or expired claims and marks unknown or conflicting evidence for review. This context projection does not turn governance into a legal license condition or add a routine human approval gate.

## Current declaration and candidate

The Rights repository remains Apache-2.0 licensed. `RIGHTS.json` records that observed declaration while leaving copyright basis, provenance completeness, and third-party inventory unresolved. `legal-candidates/MNCS-Permissive-0.1.md` is a versioned working candidate only; it is neither adopted nor applied to existing work.

The initial relation vocabulary uses existing v0.3 `referenced`, `derived-from`, and `transformed-by` meanings. Further distinct relation kinds such as `compiled-from`, `incorporates`, and `independently-implemented-against` need a versioned lineage contract rather than being smuggled into one generic relation.

## Native artifact integration boundary

The Compiler's application-build contracts already identify source snapshots,
input hashes, dependency snapshots, producer/toolchain facts, selected SSA,
and emitted artifact identities. Compiler documentation also defines an
`application-ssa-closure/1` digest reference in artifact source provenance.
Forge owns its build/release receipts and candidate/evaluation lineage; Doctor
records the provenance of its own diagnostic runtime. Rights should reference
those records instead of reconstructing them or creating a second artifact
store.

`schemas/v0.1/native-artifact-binding.schema.json` defines a bounded
cross-system association for that next integration. It retains each
contributing manifest and its obligation reference, identifies the compiler
artifact and source snapshot, and preserves typed relationships such as
`compiled-from` and `independently-implemented-against`. The latter records a
claim about a specification relationship; it does not prove independent
origin. Missing receipts stay unavailable, compatibility stays unknown, and
the record explicitly makes no legal conclusion.

`build_native_artifact_binding` constructs this contract from producer-owned
artifact, event, source snapshot, and manifest references. It bounds every
collection, retains declaration/evidence states, leaves compatibility
unknown, and never claims complete lineage: that requires an authoritative
completeness attestation contract. Its tests exercise multi-input builds,
agent-generated origin claims, unresolved rights, and missing verification.
Compiler and Forge do not yet emit the binding. The live Environment vertical
slice emits admission context and its own artifact lineage; Compiler and
Language have active concurrent worktrees, so integration at their build
boundary remains a follow-up that must bind their existing identities and
receipts without changing their active implementation.
