"""Build the end-to-end demo manifest without promoting evidence to clearance."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from mncs_rights_provenance import (
    Artifact,
    EvidenceRef,
    GraphEdge,
    GraphNode,
    Manifest,
    Participant,
    Review,
    Rights,
    validate_manifest_structure,
)
from mncs_rights_provenance.manifest import manifest_to_dict, seal_manifest


def _load_record(evidence_dir: Path, filename: str) -> dict[str, Any] | None:
    path = evidence_dir / filename
    if not path.exists():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return value


def _evidence_ref(record: Mapping[str, Any]) -> EvidenceRef:
    identity = record.get("evidence_id")
    if not isinstance(identity, str) or not identity:
        raise ValueError("evidence record has no stable evidence_id")

    content_digest = record.get("content_digest")
    digest: str | None = None
    if isinstance(content_digest, str):
        digest = content_digest.removeprefix("sha256:")
        if not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise ValueError("evidence record content_digest is not a SHA-256 digest")

    producer = record.get("producer")
    producer_reference = producer if isinstance(producer, Mapping) else None
    return EvidenceRef(
        kind="rights-evidence-record",
        reference=identity,
        sha256=digest,
        producer_reference=producer_reference,
    )


def build_rights_manifest(
    work: Path, *, distribution_license: str
) -> dict[str, Any]:
    """Create a sealed manifest from the demo's explicit inputs.

    A scanned project license declaration is retained as evidence. It does not
    establish contributor authority, source completeness, or compatibility.
    """

    evidence_dir = work / "evidence"
    evidence_records = [
        record
        for filename in ("fabric-evidence.json", "forge-license-evidence.json")
        if (record := _load_record(evidence_dir, filename)) is not None
    ]
    evidence_refs = [_evidence_ref(record) for record in evidence_records]

    graph_nodes = [
        GraphNode(node_id="job", kind="action", label="bounded fabric execution"),
        GraphNode(node_id="outputs", kind="artifact", artifact_class="experiment-output"),
    ]
    graph_edges = [GraphEdge(source="job", target="outputs", relation="derived-from")]

    license_record = _load_record(evidence_dir, "forge-license-evidence.json")
    if license_record is not None:
        license_ref = _evidence_ref(license_record)
        graph_nodes.append(
            GraphNode(
                node_id="license-analysis",
                kind="external",
                label="Forge license declaration scan",
                external_ref=license_ref.reference,
                evidence=(license_ref,),
            )
        )
        # The artifact retains a reference to this observation. The scan did
        # not test license compatibility or verify the artifact's ownership.
        graph_edges.append(
            GraphEdge(
                source="outputs",
                target="license-analysis",
                relation="referenced",
                evidence=(license_ref,),
            )
        )

    result_hash: str | None = None
    results_dir = work / "fabric" / "results"
    if results_dir.exists():
        for path in sorted(results_dir.rglob("result.json")):
            result_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            break

    hashes = (
        [{"algorithm": "sha256", "value": result_hash, "scope": "file"}]
        if result_hash
        else []
    )
    if result_hash:
        graph_nodes[1] = GraphNode(
            node_id="outputs",
            kind="artifact",
            artifact_class="experiment-output",
            hashes=[{"algorithm": "sha256", "value": result_hash}],
        )

    manifest = Manifest(
        artifact=Artifact(
            id="demo:e2e-artifact",
            artifact_class="experiment-output",
            hashes=hashes,
        ),
        provenance_origin="human-directed-machine-generated",
        participants=[
            Participant(
                participant_type="tool",
                role="executor",
                name="local-python-runtime",
            )
        ],
        process_evidence=evidence_refs,
        graph_nodes=graph_nodes,
        graph_edges=graph_edges,
        rights=Rights(
            distribution_license=distribution_license,
            copyright_status="mixed-or-undetermined",
            rights_basis="unknown-needs-review",
            third_party_material="unknown",
            sources=[],
            notes=(
                "The distribution license is copied from the demo project's declaration. "
                "Forge scan observations do not establish contributor authority, "
                "third-party inventory completeness, or license compatibility."
            ),
        ),
        review=Review(
            technical_validation="not-run",
            provenance_validation="not-run",
            human_acceptance="not-reviewed",
            notes=(
                "Manifest structure validation is not technical or provenance validation."
            ),
        ),
        spec_profile="canonical-release",
    )
    document = manifest_to_dict(manifest)
    issues = validate_manifest_structure(document)
    if issues:
        raise ValueError(f"generated rights manifest is invalid: {issues}")
    seal_manifest(document)
    return document


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("work", type=Path)
    parser.add_argument("--distribution-license", required=True)
    args = parser.parse_args()

    document = build_rights_manifest(
        args.work, distribution_license=args.distribution_license
    )
    output_path = args.work / "rights-manifest.json"
    output_path.write_text(json.dumps(document, indent=2), encoding="utf-8")
    print("== 4. Rights manifest built and sealed:", document["manifest_identity"][:16], "...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
