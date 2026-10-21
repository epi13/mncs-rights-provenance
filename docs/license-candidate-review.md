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

## License choice is independent of the Rights & Provenance system

Rights and provenance should remain useful for projects using MIT, BSD,
Apache-2.0, a local license reference, or an unresolved declaration. Adopting
an MNCS-specific license is not a prerequisite for the resolver, provenance
records, or agent-governance context. The existing Rights repository remains
Apache-2.0 licensed; the candidate stays separate from repository licensing
and contribution history.

This separation keeps current work on an established license and avoids
introducing a new legal instrument solely to make machine-readable rights
possible. A future MNCS license could describe computational forms and carry
an express patent grant in compact language, but it adds drafting, adoption,
ownership, grant-authority, and compatibility questions that the
Rights & Provenance system cannot settle. The candidate must therefore stay
optional and non-effective until its own authority approves it.

| Model | What the text supplies | Design consequence for the candidate |
|---|---|---|
| MIT | Broad copyright permission, a notice condition, and warranty/liability language; it states no express patent grant. | A concise pattern for broad copyright permissions and notice retention. Patent rights remain unstated by that text. |
| BSD-2-Clause | Permits source and binary redistribution subject to separate notice-preservation conditions; it states no express patent grant. | A concise pattern when source and other-form notice handling should be explicit. |
| BSD-2-Clause-Patent | Adds a patent grant for specified acts and claims necessarily infringed by a contribution alone or a qualifying combination at contribution time. Its text makes the patent grant irrevocable except for failure to satisfy license conditions; it includes no express patent-litigation response clause. | Candidate 0.2 follows a similar contribution boundary and breach condition. Those conditions still require legal review; they should not be mistaken for a patent-litigation retaliation clause. |
| Apache-2.0 | Defines contributor relationships, grants copyright and patent rights, terminates the patent grant for specified patent litigation, and sets out license-copy, modified-file, notice, and conditional NOTICE duties. | Keep Apache-2.0 operative here. Reproducing its broader framework in a new candidate would add terms that require a specific MNCS reason and separate review. |

Candidate 0.2 proposes a technology-neutral covered-work definition and a
contribution-limited patent grant, but it does not establish that any
contributor owns or can grant the described rights. Its express grant extends
only as far as the grantor is authorized to grant. The absence of a
patent-litigation response is a deliberate draft state, not an adopted policy;
whether to keep that choice remains open for legal review. These comparisons
are drafting observations, not legal advice or a compatibility determination.
The source-linked observations are recorded in
`evidence/license-candidate-options-20261021.json`.

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
