# MNCS Rights & Provenance

Research, specifications, schemas, and reference tooling for machine-native software rights, contribution provenance, authorship uncertainty, and artifact licensing within the MNCS ecosystem.

> **Status:** experimental specification, v0.1.0. This project is not legal advice and does not attempt to manufacture copyright or other rights where law does not recognize them.

## Why this exists

Conventional software licensing usually assumes a reasonably clear chain from author to copyright owner to contributor to license grant. Machine-native development can involve humans, models, agents, tools, experiments, validators, and later transformations in the production of one artifact. The resulting technical lineage can be knowable even when the legal characterization of authorship is not.

MNCS Rights & Provenance therefore separates two questions:

1. **What evidence do we have about how an artifact came to exist?**
2. **What rights basis and distribution terms are asserted for that artifact?**

The framework records evidence without turning provenance labels into legal conclusions.

## Current approach

The repository itself remains licensed under **Apache-2.0**. The initial framework is designed to work alongside established licenses rather than replace them prematurely.

Core rule:

> **Uncertainty is a valid state. Provenance should record what is known, what is asserted, and what still requires review.**

## Repository map

- `docs/` — problem statement, design principles, terminology, legal landscape, threat model, and open questions.
- `specs/` — normative draft specifications for provenance, rights manifests, artifact classes, contribution attestations, and release policy.
- `schemas/` — machine-readable JSON Schema definitions.
- `examples/` — representative provenance manifests covering human, assisted, autonomous, and third-party-derived cases.
- `integrations/` — proposed integration points for Fabric, Commons, Forge, Validator, and SPDX.
- `scripts/` — reference validation tooling.

## Origin classifications

The v0.1 vocabulary includes:

- `human-authored`
- `human-ai-assisted`
- `human-directed-machine-generated`
- `autonomous-machine-generated`
- `mixed-machine-origin`
- `third-party-derived`
- `generated-from-licensed-source`
- `generated-from-public-domain-source`
- `origin-uncertain`

These classifications describe **origin evidence**, not ownership or copyrightability.

## Validate the examples

```bash
python -m pip install -r requirements-dev.txt
python scripts/validate_examples.py
```

CI performs the same validation on pushes and pull requests.

## Intended MNCS integration

The long-term design is for Fabric to emit provenance evidence, Forge to analyze source and license relationships, Validator to enforce release policy, and Commons to retain findings/decisions/questions about uncertain rights states. The manifest is deliberately tool- and model-agnostic so other systems can emit the same format.

## Maturity

Version 0.1 is a research and interoperability baseline. It intentionally does **not** define a new software license. A future license should only be considered after real MNCS artifacts provide enough evidence to identify gaps that Apache-2.0 plus provenance/attestation cannot solve.

## License

Apache License 2.0. See `LICENSE`.
