# MNCS Permissive License candidate review

The Rights repository is currently licensed under Apache-2.0. Its existing `LICENSE` and contribution history remain governed by that license. `legal-candidates/MNCS-Permissive-0.1.md` is a working draft for future legal review only; it is not approved, adopted, or applied retroactively.

The candidate keeps a short MIT/BSD-style copyright permission and notice condition, then adds an explicit patent grant limited to claims the contributor can license and that are necessarily infringed by that contribution. BSD-2-Clause-Patent is a useful reference for this narrow grant. The draft deliberately has no patent litigation retaliation clause, so the possible protection and tradeoff need counsel review.

| Reference | Relevant structure | Candidate decision |
|---|---|---|
| [MIT](https://spdx.org/licenses/MIT.html) | Broad permission to use, modify, distribute, sublicense, and sell; preserve copyright and permission notices; warranty and liability disclaimer; no express patent grant in the text. | Use as a model for short, broad copyright permissions and familiar notice language. |
| [BSD-2-Clause](https://spdx.org/licenses/BSD-2-Clause.html) | Source and binary redistribution conditions preserve or reproduce notices, conditions, and disclaimer. | Keep notice obligations clear for source and compiled forms. |
| [BSD-2-Clause-Patent](https://spdx.org/licenses/BSD-2-Clause-Patent.html) | BSD-style notice conditions plus an express contribution-limited patent grant; the text does not use Apache-2.0's patent-litigation termination clause. | Use as a reference for the proposed narrow patent scope; leave retaliation absent pending deliberate review. |
| [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0.html) | Explicit copyright and patent grants, contributor-linked scope, patent-litigation termination, modified-file notices, license-copy and conditional NOTICE obligations. | Keep as the current repository license. A new candidate should not recreate all of Apache-2.0's framework unless MNCS needs it. |

The machine-readable summary identifies license text, a small set of notice conditions, and explicit patent scope where stated. It leaves cross-license compatibility and ownership unresolved. A declared license or contributor assertion does not prove authority to grant rights. Machine assistance or generation does not itself establish who owns copyright.

`src/mncs_rights_provenance/resources/license-candidates.json` records the
candidate as a versioned, unadopted draft. The license resolver recognizes
that local `LicenseRef` and points agents to this status and its draft text;
it does not add proposed permissions to the effective license-term index.
Environment context therefore surfaces an actionable review diagnostic while
preserving `unknown` compatibility. The registry is metadata about the
candidate, not a replacement for an effective repository license.

## Decisions still open

- Whether MNCS needs its own legal license at all, or should retain Apache-2.0 for new work and invest only in machine-readable rights and provenance.
- Final patent-grant wording and scope, including how submitted contributions and later work are defined.
- Whether a patent-litigation response clause is desirable and what scope it could safely cover.
- How to handle works whose copyright ownership is unclear, including machine-generated material.
- Final notice, trademark, and disclaimer language under applicable jurisdictions.
