# MNCS Integration Plan

## Fabric

Fabric should become the primary producer of process evidence. Candidate additions to Fabric receipts include:

- artifact identifiers and hashes;
- input/source references;
- model/agent/tool participants and roles;
- transformation steps;
- validation receipt links;
- proposed origin classification;
- pointer to the resulting rights manifest.

Fabric should emit evidence, not legal conclusions. The rights layer may consume Fabric receipts and apply policy later.

## Commons

Commons should preserve institutional reasoning that cannot be represented as a simple manifest field:

- findings about recurring provenance patterns;
- decisions on classification policy;
- open legal/technical questions;
- hypotheses about source similarity;
- failed approaches;
- handoffs and artifact references;
- superseded rights findings with temporal context.

A current release manifest should link to relevant Commons records without treating every historical discussion as current policy.

## Forge

Forge can provide analysis evidence for:

- dependency/license discovery;
- source-lineage inspection;
- similarity findings;
- generated-code ancestry clues;
- SPDX extraction/generation;
- contradictions between declared and observed provenance.

Forge findings should include confidence/evidence and should be able to return `unknown` rather than inventing a license.

## Validator

Validator should enforce schema and release policy separately from technical correctness. Example gates:

- schema validity;
- required evidence present;
- incompatible license finding blocks release;
- unresolved rights states route to review;
- manifest/artifact hashes match.

## SPDX

MNCS should map conventional license expressions, packages/files, checksums, dependencies, and AI/supply-chain metadata to SPDX wherever possible. MNCS-specific extensions should be limited to concepts that cannot be represented cleanly in the applicable SPDX version.

The goal is an export path such as:

`Fabric evidence -> MNCS rights manifest -> Validator policy -> SPDX/release bundle`
