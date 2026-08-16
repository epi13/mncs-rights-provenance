# Problem Statement

## Conventional assumption

Traditional open-source workflows often model contribution lineage as a chain such as:

`human author -> contribution -> copyright/patent rights -> project license`

That model remains useful, but it is incomplete for machine-native development.

## Machine-native reality

An MNCS artifact may instead emerge from:

`human intent -> orchestrator -> model -> tool -> model review -> validator -> transformation -> human acceptance -> repository`

A later experiment may modify the same artifact through a different chain. Technical provenance can therefore be multi-party, multi-model, and iterative even when no single participant can accurately be described as the sole author.

## The gap

A conventional `LICENSE` file answers what permissions a project intends to grant over rights it can license. It does not necessarily answer:

- which artifact regions came from humans, models, tools, or upstream works;
- which third-party materials influenced a generated artifact;
- whether asserted authorship is human, mixed, uncertain, or not yet evaluated;
- what evidence supports a rights assertion;
- whether provenance is sufficient for release;
- how later automated transformations affect lineage.

## Goal

MNCS Rights & Provenance defines an evidence model for those questions while remaining compatible with ordinary open-source licensing.

The framework must not infer a legal conclusion from a technical origin label. In particular, `autonomous-machine-generated` is an origin classification, not a declaration that an artifact is public domain, copyrightable, uncopyrightable, owned by a model, or owned by the operator.

## Non-goals for v0.1

- Writing a replacement for Apache-2.0.
- Determining copyrightability automatically.
- Declaring model outputs free of third-party claims.
- Guaranteeing non-infringement.
- Creating rights that do not otherwise exist.
- Requiring one model vendor, orchestration framework, or provenance store.
