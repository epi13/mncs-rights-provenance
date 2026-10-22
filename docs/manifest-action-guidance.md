# Manifest action guidance

`mncs-rp manifest-action-guidance RIGHTS.json --action redistribute-binary`
shows the indexed conditions for the manifest's declared distribution license
and each source entry. The project license and source entries stay separate;
the query does not intersect permissions or merge conditional obligations.

Each source retains its manifest reference, declared license status, evidence
references, and a source-scoped action summary. Those inputs remain declared
and unverified. SPDX `AND` and `OR` structure is preserved in an inline term
tree; a large tree is deferred to the existing `mncs-rp action-guidance`
query at the source's stable license reference. Unavailable, unsupported, or
unasserted expressions stay unresolved.

The report includes an exact input-byte digest when invoked through the CLI
and recomputes the canonical manifest identity. An identity mismatch is a
consistency diagnostic; neither digest establishes the authority or truth of
the manifest's declarations.

The report pages at most eight source entries (four by default). Continue with
`--offset` and `--limit` to inspect further inputs without producing an
unbounded report. `status` describes coverage by the bounded term index only.
The report does not verify declarations, determine grant authority, establish
that the manifest captures every artifact input, resolve cross-license
compatibility, or make a legal conclusion.

The output contract is
[`schemas/v0.1/manifest-action-guidance.schema.json`](../schemas/v0.1/manifest-action-guidance.schema.json).
Its inline expression tree reuses the versioned action-guidance schema. The
command is a preflight aid for source or binary redistribution; it explains
which indexed conditions may need attention before preparing that operation.
