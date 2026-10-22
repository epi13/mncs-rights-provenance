# License action guidance

`mncs-rp action-guidance '<SPDX expression>' --action redistribute-source`
and `--action redistribute-binary` expose the indexed notice conditions that
the Rights & Provenance resolver associates with a declared expression. To
run directly from a source checkout, use
`PYTHONPATH=src python -m mncs_rights_provenance.cli action-guidance '<SPDX expression>' --action redistribute-source`.

The result keeps SPDX `AND` and `OR` nodes. `AND` retains the conditions for
each term; `OR` keeps its alternatives and asks the caller to identify the
applicable branch from rights evidence. Each condition retains its original
trigger and a reference to the recognized license text. Conditions outside the
requested redistribution action remain visible as review cues.

`operation-class-matches-trigger` only means the requested source or binary
redistribution matches the condition's indexed action class. The original
`when` trigger remains authoritative for whether its additional facts apply.

For a manifest with multiple contributing inputs, use
[`manifest-action-guidance`](manifest-action-guidance.md). It reports the
project distribution license and each declared source independently, retaining
per-source notices and unknown states rather than merging them into one
permission result.

The action-class mapping is normative in
`language/rights_license_actions.mncs` (`mncs.rights.license_actions.v01`).
The executable corpus in `language/corpora/license-action-guidance-corpus.json`
pins every action/condition pair across the research-bytecode and portable-WASM
backends; the host projection has a parity test against those vectors.

The versioned JSON result labels the input expression as an unverified caller
declaration, gives an identity for the action ruleset, and reports unresolved
identifiers. A recognized expression only yields an indexed reference summary;
the output does not establish that the declaration is accurate, that a grantor
has authority, that a use is compatible, or that all contributing inputs are
represented. An unknown term or exception stays unresolved. The command
returns structured output for unresolved results so agents can continue with
the diagnostic instead of treating it as a tool crash.

This query complements the compact agent context: agents can inspect the
conditions for a concrete source or binary redistribution when preparing an
operation, without placing license texts or a full rights graph in every
admission context. The helper currently indexes MIT, ISC, 0BSD, BSD-2-Clause,
BSD-2-Clause-Patent, BSD-3-Clause, Apache-2.0, and Zlib. Other SPDX identifiers
and local license references remain unresolved. ISC's copyright and permission
notice condition applies to all copies; 0BSD has no indexed redistribution
condition; and Zlib's origin rule applies to use while its altered-source and
notice rules retain their source-specific triggers. Zlib's suggested product
documentation acknowledgment is optional and is not represented as a condition.

An empty indexed condition list is a statement about the narrow condition
index, not proof of authority, compatibility, or completeness for another
artifact or use. The indexed text references are the SPDX License List pages:
[ISC](https://spdx.org/licenses/ISC.html), [0BSD](https://spdx.org/licenses/0BSD.html),
and [Zlib](https://spdx.org/licenses/Zlib.html).

Validate outputs with
`schemas/v0.1/license-action-guidance.schema.json`. The result is not legal
advice or a release-compliance determination.
