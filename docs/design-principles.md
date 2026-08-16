# Design Principles

## 1. Evidence before certainty

Record the strongest evidence available. Unknown and unresolved states are preferable to invented certainty.

## 2. Provenance is not a legal conclusion

Origin classifications describe process. Rights fields describe an asserted rights basis. Neither should silently determine the other.

## 3. Technology neutrality

The specification must work for human-only projects, local models, hosted models, agents, compilers, synthesis systems, future machine participants, and non-MNCS orchestrators.

## 4. Artifact awareness

Source code, documentation, datasets, model weights, configuration, experiment outputs, receipts, and binaries may require different rights treatment. The manifest records artifact type explicitly.

## 5. Interoperability over reinvention

Use established identifiers and standards where possible, including SPDX license expressions and compatible provenance/integrity formats.

## 6. Explicit uncertainty

`unresolved`, `unknown`, and `incomplete` are first-class values. Release policy can decide when they are acceptable.

## 7. No license laundering

A downstream distribution license cannot erase incompatible upstream terms. Known sources must be recorded and compatibility evaluated separately.

## 8. Tamper-evident evidence

Receipts, prompts, source references, validation records, and manifests should be hashable and linkable to immutable artifacts where practical.

## 9. Minimum necessary disclosure

Provenance should support auditability without forcing publication of secrets, personal data, credentials, or material that cannot lawfully be redistributed.

## 10. Human governance remains explicit

Automation may produce and validate evidence, but release policy must identify which unresolved states require human review or legal escalation.
