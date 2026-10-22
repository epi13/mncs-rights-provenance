# Rights and provenance in agent context

MNCS Rights & Provenance v0.3 already owns rights manifests, typed provenance, claim review, release policy, and SPDX 2.3 interchange. The `mncs.rights-provenance.agent-context/1` projection adds a compact Environment admission view over those records; it does not copy the full manifest or graph into routine context.

## Ownership and authority

`RIGHTS.json` is a rights and evidence declaration. Its license field and source evidence do not prove authorship, ownership, contributor authority, or compatibility. The separate governance profile contains only a bounded set of operational rules. Environment activates that profile only through a strict `rights_context` binding with an expected profile identifier and explicit authority identity, basis, source reference, and scope. The profile file cannot name or enlarge its own authority. External license files, package metadata, and provenance records remain evidence, not instructions.

The projection keeps legal terms, unresolved claims, provenance state, and agent guidance in separate fields. A declared license is resolved to a reference summary of known notice and patent terms only for a small allow-listed set of SPDX identifiers. The versioned `mncs.rights.license-resolution/4` output uses the SPDX 2.3 expression parser, which preserves `AND`/`OR` precedence and local or external `LicenseRef` identity; known identifiers are matched case-insensitively while their declared spelling remains in the expression tree. Each result labels the supplied expression `caller-supplied-declaration-unverified`; this does not verify the declaration, ownership, authority, or compatibility. A reference whose extracted terms were not supplied remains explicitly unresolved. Malformed operator sequences are rejected. The expression tree is retained when it fits the configured context budget; larger detail remains available through the manifest reference. Unknown identifiers and `AND`/`OR` combinations do not receive an invented compatibility result. An unadopted MNCS permissive-license candidate remains non-effective and cannot establish contributor authority. The compact context includes a per-candidate count and stable reference to its unresolved legal-review decisions in the versioned candidate registry; it does not embed or activate the draft terms. The summary links to the identified license text and is not a legal opinion.

Agents can request the full bounded term summary with
`mncs-rp license-resolve '<SPDX expression>'`. The admission context carries
`rights.license_terms_access.query_ref` is available on admission. Agents use
the declared expression in `rights.distribution_license` as its argument. If
`rights.distribution_license_truncated` is true, the full expression remains
in `rights.license_terms.expression` when present; otherwise
`rights.license_terms.detail_ref` points to the authoritative manifest field.
The agent-context schema describes both full and budget-compacted term records.
Unknown and malformed expressions return structured results without a process
error; compatibility remains `unknown` for all branches.

The agent-context schema also types the authorized governance issuer, basis,
scope, allow-listed rules, compact rule references, source-rights summaries,
provenance evidence states, and actionable diagnostics. Missing or malformed
input digests remain null; their lineage edges are labeled `referenced` with
`evidence_state: unavailable` instead of being presented as observed inputs.
When long authoritative source references would exceed the configured budget,
the full references remain once in `sources`. Repeated references use
`source:rights_manifest` or `source:governance_profile`, optionally followed by
the original JSON-pointer fragment. The versioned context contract expands
`source:<key>` through `sources.<key>.reference`, so consumers can resolve
details without losing the authoritative location.
If source summaries are omitted to stay within budget, `source_count` and
`sources_truncated` retain the scope of the omitted material and the manifest
reference keeps the full source list available on demand.
In the most compact form, a lineage edge may omit `to` because its destination
is the projection's `output_ref`, and may use `content_digest_ref` to point at
the digest already stored in `sources`. The normal full projection continues
to carry the destination and digest inline.

The supported governance field/value pairs are normative in
`language/rights_agent_governance.mncs`. Its 33-case execution corpus includes
each allowed pair and a mismatched known value for every field. The Python
profile validator remains an Environment adapter and is pinned against the
corpus by `tests/test_agent_governance.py`; the same finite core is exercised
on the research-bytecode and portable-WASM backends. `Supported` means only
that an authorized Environment profile may communicate that operational
guidance. It does not grant legal rights or make an external declaration
authoritative. Unrecognized profile values leave governance unavailable.

The Rights project also publishes the bounded Environment test capability
`mncs-rights-provenance:test/rights-agent-context-provenance`. It runs focused
agent-context, governance, SPDX parsing, native license-action, license
resolution, v0.4 lineage and artifact-binding, implementation-lineage core
and projection, artifact-diagnostic, and `mncs.check-result/1` projection
tests. Environment supplies the selected MNCS-Language toolchain to the native
core tests, and the capability has a 300-second ceiling. Agents can use
Environment `verify` for this cross-layer contract set without launching the
full repository suite; the existing full-suite capability remains available
for broader verification.

The `rights.action_guidance` projection applies the native-backed, versioned
`mncs.rights.license_actions.v01` rules to source and binary redistribution.
It keeps one SPDX `AND`/`OR` expression tree, the original trigger text, and
both operation-class relations for each indexed condition. This avoids
duplicating the tree while preserving which branch contains a condition and
whether the source or binary operation matches its trigger. Unknown terms
remain unresolved, declarations remain unverified, and the projection makes
no ownership, compatibility, or legal conclusion. The context carries the
ruleset identity and a manifest reference. If the action tree exceeds the
configured context budget, it becomes an on-demand reference through
`mncs-rp action-guidance`; the shared action status and bounded unresolved
counts remain in the compact context.
When both operations share the same compact status, the repeated per-action
status objects may be omitted. `expression_ref` and `query_ref` still identify
the declaration and the action-guidance query. If the term projection omits a
duplicate `detail_ref`, that same expression reference identifies the source.

When a source records a usable license expression but leaves `license_status`
unknown, its diagnostic names the unresolved compatibility and source
verification. Missing expressions and SPDX `NOASSERTION`/`NONE` remain a
separate unknown state.

## Incremental identity

The context identity binds the exact manifest digest, governance profile digest, Environment binding, and compact projection. `sources.license_resolver` exposes a content identity for the SPDX 2.3 parser contract, bounded term index, and candidate registry; `sources.license_action_ruleset` separately identifies the operation guidance mapping. The provenance projection records both as inputs. A recomputed context therefore changes identity when parser behavior, packaged summaries, or action guidance changes; a referenced MNCS candidate also retains its exact registry source digest. Environment consumers can obtain the complete non-file dependency set through `agent_context_source_identities()`, whose `mncs.rights-provenance.context-source-identities/1` result is validated by `schemas/v0.1/context-source-identities.schema.json`. Compare that mapping along with the authorized binding and exact manifest and governance digests before reusing a prior projection. Bump the context schema when projection semantics change. A change to any of these inputs changes the Rights projection identity. A Rights regression test changes the governance version and lineage rule, then checks that the profile source digest, projected rule, and context identity all change. When a projection is reused for a selected working checkout, Environment refreshes the recorded manifest source root so its provenance points to the checkout currently selected by the authoritative session. The admission view includes stable references and bounded relationship counts; the detailed manifest and lineage remain on demand.

The persisted context projection records its own bounded lineage: each observed input has a `generated-from` relationship bound to its content digest, and the Rights projection function has a `transformed-by` relationship to the context artifact. A missing input is retained as a `referenced` unavailable source rather than claimed as an observed input.

The existing `rights_claims` gate remains independent. It continues to block only revoked or expired claims and marks unknown or conflicting evidence for review. This context projection does not turn governance into a legal license condition or add a routine human approval gate.

## Current declaration and candidate

The Rights repository remains Apache-2.0 licensed. `RIGHTS.json` records that observed declaration while leaving copyright basis, provenance completeness, and third-party inventory unresolved. `legal-candidates/MNCS-Permissive-0.3.md` is the current versioned working candidate; versions 0.1 and 0.2 are historical. No candidate is approved, adopted, or applied to existing work. Candidate 0.3 explicitly includes the initial Licensor in the draft patent-grant Contributor definition while preserving the grant-authority limit; that choice remains open for legal review.

Standalone content-addressed lineage records now have a v0.4 extension for producer artifact bindings. `artifact_relationships` preserves distinct kinds such as `compiled-from`, `incorporates`, and `independently-implemented-against`, along with each relationship's evidence state. `artifact_transformations` retains the producer's transformation kind, event, toolchain, and evidence state. Both are linked to the exact digest of the referenced binding; the bounded binding itself remains available on demand. Lineage status is stored with its own evidence state: partial or unknown status inferred from binding contents stays inferred, while a declared `complete` value remains a claim rather than a completeness attestation. These fields stay separate from the v0.3 pressure-oriented `derivations` vocabulary, so specification use is not collapsed into copying or derivation. A declared `independently-implemented-against` relationship remains a claim, not proof of independent origin. The v0.3-to-v0.4 migration changes only the version and content digest; artifact relationships remain absent until evidence is supplied.

The conversion command is `mncs-rp lineage from-artifact-binding BINDING.json --lineage-id ID --reference REF`. It creates a digest-sealed v0.4 record from an existing native binding without changing the Compiler or Forge source record. Rights state and compatibility remain separate: compatibility stays unknown, and the record makes no legal conclusion.

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

For source migrations and mixed native/host builds, a v0.4 lineage record may
carry the independently versioned
`mncs.rights-provenance.implementation-lineage/0.1.0` extension under
`extensions["mncs-rights:implementation-lineage"]`. Its component records
separate representation (`machine-native`, `host-language`, or unknown) from
origin (`new-local`, `migrated`, `inherited-external`, `generated`, mixed, or
unknown), and preserve evidence state plus bounded evidence references. Its
status is `partial` when an evidence-backed classification is present and
`unknown` otherwise. The extension is bound by the containing lineage digest and can be supplied to
`lineage_record_from_artifact_binding` or the CLI's `--implementation-lineage`
input. The coverage marker is always `unverified-subset`; an empty or unknown
list remains unknown, and unavailable evidence cannot carry a known
classification. A declared migration or generation classification does not
verify independent origin, authorship, ownership, or legal rights.
The schema is
`schemas/extensions/v0.1/implementation-lineage.schema.json`.

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
`mncs.compiler.application-build/4`, `/7`, or `/11` response without changing
or rerunning Compiler. The current request contract is
`mncs.rights-provenance.compiler-build-binding-request/0.2.0`; `/0.1.0` remains
accepted for existing callers. The adapter requires a `verified` response with
a materialized artifact, retains the source-snapshot file hashes,
dependency-graph identity, selected SSA identity,
`application-ssa-closure/1` reference, and available toolchain identity, then
records source-to-artifact `compiled-from` edges and the build result as a
`transformed-by` reference. Every Compiler-supplied fact remains declared
evidence; an optional canonical Environment Store reference is separately
recorded as directly observed evidence of the response record. The adapter
checks that the outer and nested artifact identities agree but does not
re-hash the VM artifact or authenticate the producer.
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

Environment has an admission-context capability and a selected-checkout
invalidation path covered by Environment tests. This Rights slice consumes the
published Compiler contract and canonical Environment Store record without
changing Compiler or Environment implementation worktrees.

The bounded handoff evidence in `evidence/rights-handoff-*20261021.json`
records a live `application-build/4` response retrieved through Environment's
canonical artifact store. Its source snapshot hash matches
`examples/rights-handoff.mncs`; the binding retains the Store reference as
directly observed and the Compiler transformation as declared. The contributing
Rights manifest records the repository license declaration while keeping
machine-originated copyright unresolved. The Rights artifact diagnostic
returns `review` with `artifact-rights-unresolved`, compatibility remains
unknown, lineage is partial, and the legal conclusion remains `NOT_MADE`. The
binding's `context_identity` is null because the live Environment context
operation did not project `rights_context` for this session; the request does
not substitute a locally computed or unrelated context. The Environment resolver was invoked
against the corrected binding, resolved both sources (`inputs.status=available`),
and returned a bounded review context with identity `sha256:40b482ba…`, the
expected governance profile, and review diagnostics. The separate evidence
record preserves that observation apart from the missing session projection.
A separate Environment worktree contains project-scoped admission and
cache-invalidation work. On 2026-10-21, the connected MCP `context` operation
still omitted `rights_context` for session `ses_de553dd5fd5d1178`. A fresh
`LocalEnvironmentMCP` from Control main called the same configured Environment
RPC and returned the context with identity `sha256:40b482ba…` and status
`review`; the current compactor preserves that provider projection. All three
enumerated bridge processes started before the Control source change that added
this pass-through. This strongly indicates stale code in the connected MCP
service, although the process serving that tool call was not mapped to a
specific PID. No shared service was restarted. The observation and its limits
are recorded in
`evidence/rights-handoff-context-transport-freshness-20261021.json`; repeat the
read-only context request after the normal MCP lifecycle refresh. The claim
cleanup observation initially exposed a Control bridge mismatch: it forwarded
an expected Store generation on release although the Environment CLI accepts
that fence only on acquire. Control commit `8f4c9eae` now rejects that argument
before RPC while preserving generation fencing on acquire; all 25 tests in the
Control bridge test file pass. A separate active Control worktree for the typed
Compiler build gate remained untouched. The evidence record preserves the
failure, safe release, and repair. The current v1 binding resolves paths from
the workspace root, so the Rights definition points at the canonical workspace
checkout. The separate Environment worktree adds selected-checkout scope; until
that contract is integrated, rights changes that exist only in another
worktree do not update this project's admission context.

On 2026-10-21, the Rights provider was declared as a bounded, read-only
Environment invocation. Live readiness now reports `ready` with zero unknown
capabilities, and the provider and targeted test capability are available.
The connected Environment MCP context operation still omits `rights_context`.
A canonical `mncs-env context` read of the persisted session does contain the
field, but returns `review`: its stored binding still uses checkout-relative
`RIGHTS.json` and `governance/agent-governance.json` references, which resolve
at the workspace root and are unavailable. The current project definition
points to the canonical workspace checkout; a normal `resume` did not refresh
the stored binding. The observation is recorded in
`evidence/rights-environment-invocation-readiness-20261021.json`.

The generated `.mncs/project-view.json` also remains pending. A targeted
Environment projection apply was safely deferred because
`mncs-doctor:projection-health` is unbound in this Rights-only selected scope;
no projection bytes were written. Control does not expose the `projections`
operation through its operation contract. Repairing that requires the active
Environment integration or an explicitly authorized provider scope, so this
campaign left its Environment and Doctor worktrees untouched.

The v0.4 implementation-lineage extension adds a bounded, versioned view of
which components are machine-native, host-language, migrated, inherited from
external sources, generated, or unknown. It is separate from copyright and
ownership claims. `coverage: unverified-subset` and `legal_conclusion:
NOT_MADE` are fixed by its schema and validator. The extension is digest-bound
inside a v0.4 lineage record and can be attached to a Compiler artifact binding
with `mncs-rp lineage from-artifact-binding --implementation-lineage FILE`.
The status rules live in `language/implementation_lineage.mncs`, execute
against the bounded corpus on research-bytecode and portable-wasm, and are
mirrored by the host normalizer.
The worked example
`examples/v0.4/lineage-from-live-compiler-binding-with-implementation-lineage.json`
uses the recorded Compiler build binding: it labels the source representation
machine-native while leaving its implementation origin unknown and its
evidence declared. That classification records what the existing build
evidence supports without asserting a complete history or independent origin.
