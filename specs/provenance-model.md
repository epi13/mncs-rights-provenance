# MNCS Provenance Model v0.1

> **Status:** superseded by the implemented v0.2 contracts. See
> `schemas/v0.2/`, `specs/policy-core.md`, and the repository README for the
> system that actually exists. This document is retained for provenance of the
> v0.1 vocabulary, which v0.2 preserves.

This document defines the initial technical provenance vocabulary.

## Origin classifications

| Value | Meaning |
|---|---|
| `human-authored` | Evidence supports direct human authorship of the artifact. |
| `human-ai-assisted` | A human developed the artifact with machine assistance while retaining material direct authorship. |
| `human-directed-machine-generated` | A human directed generation but the machine produced material implementation/output. |
| `autonomous-machine-generated` | An automated system produced the artifact without direct human authorship of the artifact itself being asserted. |
| `mixed-machine-origin` | Multiple machine/human transformations make a simpler origin label misleading. |
| `third-party-derived` | The artifact is known to derive from external material. |
| `generated-from-licensed-source` | Generation/transformation is tied to identified licensed source material. |
| `generated-from-public-domain-source` | Generation/transformation is tied to source material for which a public-domain basis is separately asserted. |
| `origin-uncertain` | Available evidence does not support a stronger classification. |

## Participants

Participants may be `human`, `model`, `agent`, `tool`, `organization`, or `unknown`. A model identifier should be treated as provenance metadata, not an author or owner designation.

## Process evidence

Evidence records are references rather than necessarily embedded payloads. v0.1 recognizes Fabric receipts, prompts, tool logs, validation receipts, commits, external records, and other references.

## Evidence graph

A manifest is a release-oriented summary. Implementations MAY retain a richer graph linking:

`input -> participant/tool action -> transformation -> validation -> artifact`

The summary must not claim more than the underlying graph can support.

## Invariants

1. Origin classification MUST NOT automatically determine copyright status.
2. Model/agent participants MUST NOT be interpreted as rights holders merely because they appear in provenance.
3. Missing evidence MUST be representable without fabrication.
4. Third-party source information MUST remain separable from the project's own rights assertion.
