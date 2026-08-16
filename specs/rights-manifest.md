# MNCS Rights Manifest Specification v0.1

The canonical machine-readable form is defined by `schemas/mncs-rights-manifest.schema.json`.

## Top-level sections

### `artifact`

Identifies the artifact and its class, repository/commit when relevant, and affected paths.

### `provenance`

Records origin classification, participants, process evidence, and optional notes.

### `rights`

Records distribution license, copyright-status classification, rights basis, third-party-material state, sources, and notes.

### `review`

Records technical validation, provenance validation, human acceptance, and optional review notes.

## Copyright status vocabulary

- `human-authorship-confirmed`
- `human-authorship-material`
- `mixed-or-undetermined`
- `machine-originated-unresolved`
- `third-party-licensed`
- `public-domain-asserted`
- `unresolved`

These are project evidence states, not judicial determinations.

## Rights basis vocabulary

- `project-owned-or-controlled`
- `contributor-attested`
- `third-party-license`
- `public-domain-basis`
- `no-exclusive-right-asserted`
- `unknown-needs-review`

`no-exclusive-right-asserted` means the project is not using an exclusive-right claim as its asserted basis. It does not automatically prove that no third party possesses rights.

## License expressions

Implementations SHOULD use SPDX license identifiers/expressions when a suitable expression exists. v0.1 permits a string because future artifact types may use terms not yet represented by a software-license identifier.
