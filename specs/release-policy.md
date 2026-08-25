# Release Policy v0.1

> **Status:** superseded by the implemented v0.2 contracts. See
> `schemas/v0.2/`, `specs/policy-core.md`, and the repository README for the
> system that actually exists. This document is retained for provenance of the
> v0.1 vocabulary, which v0.2 preserves.

This is the initial policy profile for public MNCS artifacts.

## Release requirements

A releasable artifact SHOULD have:

- an artifact type and stable identifier;
- an origin classification;
- participant/evidence references appropriate to the workflow;
- a distribution license/terms expression;
- a copyright-status classification;
- a rights basis;
- a third-party-material state;
- technical validation status;
- provenance validation status.

## Default gates

### Pass

`provenance_validation: passed` with no known incompatible third-party license.

### Review required

Any of the following should require explicit human review before a public release:

- `rights_basis: unknown-needs-review`;
- `third_party_material: possible` or `unknown` for a canonical release artifact;
- `copyright_status: unresolved` when the unresolved state affects the intended grant;
- contradictory or missing source-license evidence;
- provenance validation marked `incomplete`.

### Reject/block

Known incompatible source terms, failed provenance validation, falsified evidence, or a rights basis known to be insufficient for the proposed distribution should block release until corrected.

## Important limitation

Passing the policy means the artifact satisfied project evidence requirements. It is not a warranty of title or non-infringement.
