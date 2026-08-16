# Legal Landscape

> This document is a research map, not legal advice. Legal conclusions should be reviewed by qualified counsel before they are turned into binding project terms.

## Apache License 2.0

Apache-2.0 remains the baseline license for this repository. It provides broad copyright permissions, an express patent grant, redistribution conditions, NOTICE mechanics, warranty disclaimers, and limitation of liability. The MNCS framework is initially designed to supplement established licensing rather than rewrite it.

Primary source: <https://www.apache.org/licenses/LICENSE-2.0>

## AI-assisted and AI-generated authorship

The U.S. Copyright Office's January 2025 Part 2 report states that existing copyright principles can protect generative-AI outputs where a human author determines sufficient expressive elements; use of AI assistance does not itself bar copyrightability, while prompts alone are not necessarily sufficient human control over expressive elements. MNCS therefore avoids converting an AI provenance label into a copyright conclusion.

Primary source: <https://www.copyright.gov/ai/Copyright-and-Artificial-Intelligence-Part-2-Copyrightability-Report.pdf>

## Open Source AI Definition

The Open Source Initiative's Open Source AI Definition 1.0 distinguishes the preferred form for modification across data information, code, and parameters. It also recognizes that the legal mechanism applicable to model parameters may not always be settled. This supports an artifact-aware rights model rather than assuming all machine-native artifacts behave like source code.

Primary source: <https://opensource.org/ai/open-source-ai-definition>

## SPDX

SPDX provides standardized license expressions and software supply-chain metadata. MNCS should map to SPDX rather than invent incompatible license identifiers or dependency metadata where SPDX already has a suitable representation.

Primary source: <https://spdx.dev/>

## Developer Certificate of Origin

The DCO is a widely used contribution sign-off mechanism based on a contributor representing that they created a contribution or have the right to submit it under the project's license. MNCS may use the DCO unchanged and supplement it with provenance-specific information rather than modifying the DCO text.

Primary source: <https://developercertificate.org/>

## Research position for v0.1

The framework treats these as separate assertions:

- how an artifact was produced;
- whether human authorship is confirmed, material, mixed/undetermined, machine-originated and unresolved, third-party licensed, public-domain asserted, or unresolved;
- what rights basis supports distribution;
- what license expression applies to rights the project can license;
- whether third-party material is known, possible, or unknown.

No schema value should be interpreted as an automatic legal determination outside the explicit assertion it represents.
