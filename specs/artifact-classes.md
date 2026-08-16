# Artifact Classes v0.1

The manifest supports the following initial classes:

- `source-code` — preferred source form of software.
- `documentation` — prose, specifications, diagrams, and supporting material.
- `dataset` — collections of data used for research, evaluation, training, or operation.
- `model-weights` — learned parameters/checkpoints or equivalent machine-learning parameters.
- `configuration` — configuration, manifests, prompts-as-config, policies, and deployment settings.
- `experiment-output` — candidate solutions, research results, generated patches, or other experimental artifacts not yet treated as canonical source.
- `receipt` — evidence records emitted by Fabric/Validator/other systems.
- `binary` — compiled or packaged object form.
- `other` — a class not covered above.

Artifact type does not itself select a license. Implementations should apply artifact-specific policies and record the actual distribution license/terms in the rights manifest.

Future versions may add profiles for datasets, weights, and research corpora where a single software-license field is insufficient.
