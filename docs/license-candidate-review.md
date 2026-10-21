# MNCS Permissive License candidate review

The Rights repository is currently licensed under Apache-2.0. Its existing `LICENSE` and contribution history remain governed by that license. `legal-candidates/MNCS-Permissive-0.1.md` is a working draft for future legal review only; it is not approved, adopted, or applied retroactively.

Version 0.1 is preserved as an incomplete historical draft. Version 0.2 is a separate unadopted proposal: it makes the copyright grant and notice conditions technology-neutral and adds a contribution-limited patent grant with an enumerated set of acts. BSD-2-Clause-Patent informs the patent scope and combination boundary; the draft has no patent-litigation retaliation clause. These choices need legal review before any adoption.

| Reference | Relevant structure | Candidate decision |
|---|---|---|
| [MIT](https://opensource.org/license/mit) | Broad permission to use, modify, distribute, sublicense, and sell; preserve copyright and permission notices; warranty and liability disclaimer; no express patent grant in the text. | Use as a model for short, broad copyright permissions and familiar notice language. |
| [BSD-2-Clause](https://spdx.org/licenses/BSD-2-Clause.html) | Source and binary redistribution conditions preserve or reproduce notices, conditions, and disclaimer. | Keep notice obligations clear for source and compiled forms. |
| [BSD-2-Clause-Patent](https://spdx.org/licenses/BSD-2-Clause-Patent.html) | BSD-style notice conditions plus an express patent grant that names licensed acts, scope terms, and contribution/combination boundaries. | Use as a drafting reference only. Version 0.2 proposes a similar contribution-limited shape; test its boundaries and no-retaliation choice in legal review. |
| [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0.html) | Explicit copyright and patent grants, contributor-linked scope, patent-litigation termination, modified-file notices, license-copy and conditional NOTICE obligations. | Keep as the current repository license. A new candidate should not recreate all of Apache-2.0's framework unless MNCS needs it. |

The machine-readable summary identifies license text, a small set of notice conditions, and explicit patent scope where stated. It leaves cross-license compatibility and ownership unresolved. A declared license or contributor assertion does not prove authority to grant rights. Machine assistance or generation does not itself establish who owns copyright.

`src/mncs_rights_provenance/resources/license-candidates.json` records the
candidate as a versioned, unadopted draft. The license resolver recognizes
that local `LicenseRef` and points agents to this status and its draft text;
it does not add proposed permissions to the effective license-term index.
Environment context therefore surfaces an actionable review diagnostic while
preserving `unknown` compatibility. The versioned license-resolution view
also exposes the count and JSON Pointer for a candidate's
`legal_review_decisions`; the registry digest in context binds that on-demand
reference without repeating the decision list or draft terms. The registry is
metadata about the candidate, not a replacement for an effective repository
license.

## Decisions still open

- Whether MNCS needs its own legal license at all, or should retain Apache-2.0 for new work and invest only in machine-readable rights and provenance.
- Final patent-grant wording and scope, including how submitted contributions and later work are defined.
- Whether a patent-litigation response clause is desirable and what scope it could safely cover.
- How to handle works whose copyright ownership is unclear, including machine-generated material.
- Final notice, trademark, and disclaimer language under applicable jurisdictions.

## Drafting finding

The 0.1 candidate's patent paragraph identifies a contributor-limited claim
class, but does not enumerate licensed patent acts or define the grant's term,
`covered work`, `contributor`, or `contribution`. It also does not settle which
combinations fall within the grant. The BSD-2-Clause-Patent text makes those
boundaries explicit, while Apache-2.0 also defines contributor relationships
and includes a patent-litigation termination condition. These are candidate
design references, not terms MNCS has adopted. Keep patent rights unresolved
until a later draft records the decisions and receives legal review.

The reviewed source observations and their limits are recorded in
`evidence/license-candidate-patent-drafting-review-20261021.json`.
The version 0.2 proposal and its unresolved choices are recorded in
`evidence/license-candidate-v02-review-20261021.json`.
