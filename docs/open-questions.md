# Open Questions

These questions are intentionally unresolved in v0.1 and should be answered from observed MNCS workflows where possible.

1. What is the correct provenance granularity: repository, file, commit, symbol, region, or artifact graph?
2. When multiple models iteratively modify the same code, when should origin become `mixed-machine-origin` rather than preserving a transformation chain?
3. How should prompts be referenced when they contain sensitive or non-redistributable content?
4. Which unresolved states should block public releases versus merely require a NOTICE?
5. How should similarity analysis be represented without overstating what similarity can prove legally?
6. How should model/provider terms be recorded when the model itself is not redistributed but its output becomes an artifact?
7. Which portions of the manifest can map directly to SPDX 3.x and which require an MNCS extension?
8. Should Fabric emit one manifest per job, per artifact, or both?
9. How should Commons preserve superseded rights findings without confusing them with current release state?
10. When is a separate MNCS legal instrument actually necessary rather than Apache-2.0 plus provenance and contribution attestations?
11. How should future recognition of rights in currently uncertain machine-originated material be handled without creating accidental restrictions today?
12. What evidence threshold should justify `human-authorship-confirmed` versus `human-authorship-material`?
