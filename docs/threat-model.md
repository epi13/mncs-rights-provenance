# Threat Model

The framework is designed to make rights/provenance failures visible; it cannot eliminate them.

## Threats

### False provenance

A participant or automation records an origin classification that is unsupported by evidence.

**Mitigation:** evidence references, immutable receipt hashes, validation, and human escalation for contradictions.

### Hallucinated license metadata

A model invents an upstream license or assumes compatibility.

**Mitigation:** source references, `unknown` states, Forge/license verification, and release gates.

### Unrecognized third-party similarity

Generated code materially resembles upstream copyrighted code without explicit lineage.

**Mitigation:** source/similarity analysis where feasible, dependency inspection, conservative `possible`/`unknown` status, and review.

### Provenance stripping

Artifacts are copied without their manifests or release metadata.

**Mitigation:** release bundles, NOTICE/release policy, embedded references where appropriate, and signed/hashed manifests.

### Evidence tampering

Receipts or manifests are edited after generation.

**Mitigation:** content hashes, append-only Commons records where appropriate, commit linkage, and signature support in later versions.

### Privacy or secret leakage

Prompts/logs may contain credentials, proprietary data, or personal information.

**Mitigation:** reference evidence by digest/controlled URI when full disclosure is inappropriate; provenance does not require publishing sensitive payloads.

### False legal certainty

Technical systems present a classification as a court-level legal conclusion.

**Mitigation:** separate namespaces for provenance and rights, conservative vocabulary, explicit unresolved states, and documented non-goals.
