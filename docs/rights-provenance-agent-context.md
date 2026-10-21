# Rights and provenance in agent context

MNCS Rights & Provenance v0.3 already owns rights manifests, typed provenance, claim review, release policy, and SPDX 2.3 interchange. The `mncs.rights-provenance.agent-context/1` projection adds a compact Environment admission view over those records; it does not copy the full manifest or graph into routine context.

## Ownership and authority

`RIGHTS.json` is a rights and evidence declaration. Its license field and source evidence do not prove authorship, ownership, contributor authority, or compatibility. The separate governance profile contains only a bounded set of operational rules. Environment activates that profile only through a strict `rights_context` binding with an expected profile identifier and explicit authority identity, basis, source reference, and scope. The profile file cannot name or enlarge its own authority. External license files, package metadata, and provenance records remain evidence, not instructions.

The projection keeps legal terms, unresolved claims, provenance state, and agent guidance in separate fields. A declared license is resolved to a reference summary of known notice and patent terms only for a small allow-listed set of SPDX identifiers. The SPDX expression tree is retained when it fits the configured context budget; larger detail remains available through the manifest reference. Unknown identifiers and `AND`/`OR` combinations do not receive an invented compatibility result. The MNCS permissive-license `LicenseRef` resolves to versioned candidate metadata that explicitly says the draft is unadopted, has no effective grant, and cannot establish contributor authority; context points to the draft and requests an effective license declaration. The summary links to the identified license text and is not a legal opinion.

## Incremental identity

The context identity binds the exact manifest digest, governance profile digest, Environment binding, and compact projection. `sources.license_resolver` exposes a content identity for the bounded SPDX term index and candidate registry, and the provenance projection records it as an input. A recomputed context therefore changes identity when those packaged summaries change; a referenced MNCS candidate also retains its exact registry source digest. Environment currently reuses a prior projection based on the bound manifest and governance file digests. It still needs to compare `license_resolver_identity()` before reuse so a changed packaged resolver cannot leave a stale persisted context. The admission view includes stable references and bounded relationship counts; the detailed manifest and lineage remain on demand.

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
`build_forge_provider_artifact_binding` adapts Forge's
`mncs.provider-build-receipt/1` into that binding after checking the receipt's
core identity. Forge remains the receipt authority. Because the receipt is not
signed, projected fields remain declared evidence; the adapter does not claim
to have reread the input bytes or authenticated the producer. It preserves the
output artifact identity and digest, compiler artifact hash, build invocation,
provider source-input hashes, and dependency-root identities. Receipt v1 does
not retain the primary source binding as a source snapshot, so inputs are
represented as declared `depends-upon` relationships and
`source_snapshot_identity` stays unavailable. Missing rights remain unknown,
compatibility stays unknown, and the binding makes no legal conclusion.
The versioned request schema at
`schemas/v0.1/forge-build-binding-request.schema.json` and
`mncs-rp artifact-binding forge-build REQUEST.json` expose the adapter as an
on-demand machine interface. The request must supply any applicable manifest
references explicitly; the command does not treat receipt metadata or an
external license file as an authoritative instruction.

Compiler continues to own its application-build result. The Rights-only
`build_compiler_application_artifact_binding` adapter consumes the existing
`mncs.compiler.application-build/11` response without changing or rerunning
Compiler. It requires a `verified` response with a materialized artifact,
retains the source-snapshot file hashes, dependency-graph identity, selected
SSA identity, `application-ssa-closure/1` reference, and available toolchain
identity, then records source-to-artifact `compiled-from` edges and the build
result as a `transformed-by` reference. Every Compiler-supplied fact remains
declared evidence; the adapter checks the outer and nested artifact identities
agree but does not rehash the VM artifact or authenticate the producer.
Without explicit manifest references rights remain unknown; supplied manifests
can change the declared rights summary to `declared` or `review`, while cross
license compatibility remains unknown. The bounded request schema and
`mncs-rp artifact-binding compiler-build REQUEST.json` expose this path.

`diagnose_native_artifact_binding` and
`mncs-rp artifact-binding diagnose BINDING.json` produce bounded, evidence-linked
findings for absent or unresolved rights, unknown compatibility across multiple
declared inputs, and missing or explicitly unavailable lineage. They do not
fetch or reinterpret referenced manifests. A single declared input with
declared partial lineage produces no repeated finding; `no-findings` is not a
compliance result, and the report always makes no legal conclusion.

The live Environment vertical slice emits admission context and its own
artifact lineage. Compiler and Language have active concurrent worktrees, so
this adapter stays within the Rights repository and consumes their published
versioned contract without modifying those worktrees.
