# MNCS Permissive License candidate review

The Rights repository is currently licensed under Apache-2.0. Its existing
`LICENSE` and contribution history remain governed by that license. Versions
0.1 through 0.3 are preserved historical drafts;
`legal-candidates/MNCS-Permissive-0.4.md` is the current working candidate for
legal review only. No candidate is approved, adopted, or applied retroactively.

Version 0.1 is preserved as an incomplete historical draft. Version 0.2 is a
historical unadopted proposal with a contribution-limited patent grant. Version
0.3 kept that grant shape and explicitly included the initial Licensor in
`Contributor`; it limits the grant to patent claims the grantor may license.
Version 0.4 carries that patent wording forward and adds an explicit
“subject to the terms and conditions” lead-in to the copyright grant, making
its relationship to the redistribution notice conditions visible in the draft.
BSD-2-Clause-Patent and Apache-2.0 inform this draft choice. The candidate has
no patent-litigation retaliation clause. These choices need legal review before
any adoption.

| Reference | Relevant structure | Candidate decision |
|---|---|---|
| [MIT](https://opensource.org/license/mit) | Broad permission to use, modify, distribute, sublicense, and sell; the grant states notice conditions; warranty and liability disclaimer; no express patent grant in the text. | Use as a model for short, broad copyright permissions and for making the connection between permission and notice conditions explicit. |
| [BSD-2-Clause](https://spdx.org/licenses/BSD-2-Clause.html) | Source and binary redistribution conditions preserve or reproduce notices, conditions, and disclaimer. | Keep notice obligations clear for source and compiled forms. |
| [BSD-2-Clause-Patent](https://spdx.org/licenses/BSD-2-Clause-Patent.html) | BSD-style notice conditions plus an express patent grant that names copyright holders and contributors, licensed acts, scope terms, and contribution/combination boundaries. | Use as a drafting reference only. Version 0.3 explicitly covers its Licensor as a patent grantor while keeping the grant limited to rights that grantor may license; legal review must assess that choice and the no-retaliation position. |
| [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0.html) | Explicit copyright and patent grants, a Contributor definition that includes the Licensor, patent-litigation termination, modified-file notices, license-copy and conditional NOTICE obligations. | Keep as the current repository license. A new candidate should not recreate all of Apache-2.0's framework unless MNCS needs it. |

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
- Whether version 0.3's inclusion of the initial Licensor in `Contributor` gives the intended patent scope, and whether that definition and its authority limit are legally sound.
- Whether the copyright grant should be expressly subject to the license terms, which notice conditions qualify, and what breach or cure consequences should apply.
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
| BSD-2-Clause-Patent | Adds a patent grant for specified acts and claims necessarily infringed by a contribution alone or a qualifying combination at contribution time. Its text makes the patent grant irrevocable except for failure to satisfy license conditions; it includes no express patent-litigation response clause. | Candidate 0.3 follows a similar contribution boundary and breach condition, and names the Licensor within `Contributor`. Those conditions still require legal review; they should not be mistaken for a patent-litigation retaliation clause. |
| Apache-2.0 | Defines contributor relationships, grants copyright and patent rights, terminates the patent grant for specified patent litigation, and sets out license-copy, modified-file, notice, and conditional NOTICE duties. | Keep Apache-2.0 operative here. Reproducing its broader framework in a new candidate would add terms that require a specific MNCS reason and separate review. |

Candidate 0.3 proposes a technology-neutral covered-work definition and a
contribution-limited patent grant. Its `Contributor` definition includes the
initial Licensor so the candidate text names that grantor explicitly. The text
does not establish that any licensor or contributor owns or can grant the
described rights; each grant remains limited to rights its grantor is
authorized to grant. The absence of a patent-litigation response is a
deliberate draft state, not an adopted policy; whether to keep that choice
remains open for legal review. These comparisons are drafting observations,
not legal advice or a compatibility determination.
The source-linked observations are recorded in
`evidence/license-candidate-options-20261021.json`.

### Copyright grant and notice conditions in version 0.4

The [MIT text](https://opensource.org/license/mit) places its notice condition
with the permission grant; [BSD-2-Clause](https://spdx.org/licenses/BSD-2-Clause.html)
permits source and binary redistribution subject to separate notice
conditions; [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0.html)
introduces its copyright grant as subject to the license terms and conditions.
Version 0.4 adds the short lead-in “Subject to the terms and conditions of
this License” before the copyright grant while retaining the separate,
technology-neutral source and other-form notice paragraph.

This wording does not determine whether every condition limits every grant,
whether breach terminates permission, or whether a cure period is appropriate.
Those remain open legal decisions. This is a draft clarification for review,
not an adoption decision or a conclusion about enforceability. Version 0.3
remains unchanged as the previous candidate. The source-linked comparison and
bounded resolver/test evidence are recorded in
`evidence/license-candidate-v04-condition-clarity-20261022.json`.

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

### Initial licensor and patent-grantor coverage

Version 0.2 left the initial Licensor outside its Contribution-based
`Contributor` definition. The [BSD-2-Clause-Patent text](https://spdx.org/licenses/BSD-2-Clause-Patent.html)
names copyright holders and contributors as patent grantors; the
[Apache-2.0 text](https://www.apache.org/licenses/LICENSE-2.0.html) defines
`Contributor` to include the Licensor. Version 0.3 follows that latter
definition shape as a provisional choice and preserves the explicit
grant-authority limit. Counsel still needs to review the intended scope and
authority boundary; the wording is not a legal conclusion. The earlier 0.2
draft question remains in
`evidence/license-candidate-patent-grantor-coverage-20261022.json`; the 0.3
draft choice and its review status are recorded in
`evidence/license-candidate-v03-patent-grantor-decision-20261022.json`.
