# Source rights policy diagnostics

`mncs-rp validate` includes `diagnostics` when a source-license policy gate is
active. Each record follows
[`schemas/v0.1/policy-diagnostic.schema.json`](../schemas/v0.1/policy-diagnostic.schema.json)
and carries a stable `mncs.rights.policy-diagnostic/1` schema version.

`source-license-status-unverified` explains why a manifest's compatible,
incompatible, unknown, or not-applicable label does not establish a verified
assessment. It includes the declared source reference, label, optional license
expression and confidence, and bounded references to evidence records.
`source-license-declarations-conflict` identifies references whose declared
license expressions or determinate status labels disagree. An `unknown`
label by itself does not create a contradiction.

Both diagnostics mark their evidence as `declared-unverified`, follow the
effective severity selected by the configured policy profile, and include a
remedy. They do not change release gate semantics or make a legal conclusion.
The report retains `legal_conclusion=NOT_MADE`.

To keep context and output bounded, each diagnostic includes at most 16
source declarations or conflict groups and at most 8 evidence references per
source or conflict. Omitted entries are counted. Text fields are limited to
256 characters and carry a truncation marker where needed. Consumers should
use the source and evidence references to retrieve full records on demand.
