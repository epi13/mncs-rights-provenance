"""SPDX 2.3 interoperability.

Export: manifest -> SPDX document (package + AI-package provenance fields
where SPDX 3.x AI/Safety profile concepts are approximated in 2.3 via
annotations/externalRefs). Import: SPDX expressions -> source entries.

SPDX can represent conventional licensing metadata; it cannot cleanly
represent MNCS origin classifications, evidence graphs, or uncertainty
semantics, so the export carries an explicit ``mncs`` annotation pointing at
the manifest instead of pretending SPDX covers those.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from .canonical import sha256_hex

_SPDX_ID_RE = re.compile(r"^[A-Za-z0-9.\-]+$")

_KNOWN_SIMPLE = {
    "MIT",
    "Apache-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "ISC",
    "GPL-2.0-only",
    "GPL-3.0-only",
    "LGPL-2.1-only",
    "LGPL-3.0-only",
    "MPL-2.0",
    "CC0-1.0",
    "CC-BY-4.0",
    "CC-BY-SA-4.0",
    "Unlicense",
    "0BSD",
    "Zlib",
}


def is_valid_spdx_expression(expression: str) -> bool:
    """Conservative structural check; NOT a full SPDX parser or validator."""
    if not expression or len(expression) > 256:
        return False
    cleaned = expression.strip()
    if cleaned != expression or "\n" in expression or "\t" in expression:
        return False
    depth = 0
    for token in cleaned.replace("(", " ( ").replace(")", " ) ").split():
        if token == "(":
            depth += 1
            if depth > 8:
                return False
            continue
        if token == ")":
            depth -= 1
            if depth < 0:
                return False
            continue
        if token in {"AND", "OR"}:
            continue
        if not _SPDX_ID_RE.match(token):
            return False
        first = token[0]
        if not (first.isalpha() or first.isdigit()):
            return False
    return depth == 0


def export_spdx(
    document: Mapping[str, Any], *, document_uri: str = "https://mncs.invalid/spdx"
) -> dict[str, Any]:
    """Build a minimal SPDX 2.3 JSON document from a rights manifest."""
    artifact = document.get("artifact") or {}
    rights = document.get("rights") or {}
    provenance = document.get("provenance") or {}
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    artifact_id = str(artifact.get("id", "unknown-artifact"))
    package_name = re.sub(r"[^A-Za-z0-9.\-]+", "-", artifact_id)[:80] or "mncs-artifact"
    spdx_ref = f"SPDXRef-Package-{sha256_hex(artifact_id)[:12]}"
    manifest_identity = document.get("manifest_identity") or sha256_hex(document)

    subject_package = {
        "name": package_name,
        "SPDXID": spdx_ref,
        "downloadLocation": str(artifact.get("repository") or "NOASSERTION"),
        "filesAnalyzed": False,
        "licenseConcluded": str(rights.get("distribution_license") or "NOASSERTION"),
        "licenseDeclared": str(rights.get("distribution_license") or "NOASSERTION"),
        "copyrightText": _copyright_text(rights),
        "versionInfo": str(artifact.get("commit") or "NOASSERTION"),
        "externalRefs": [
            {
                "referenceCategory": "PACKAGE-MANAGER",
                "referenceType": "purl",
                "referenceLocator": f"pkg:mncs/{package_name}@{manifest_identity[:12]}",
            }
        ],
    }
    packages = [subject_package]
    relationships = []
    for index, source in enumerate(rights.get("sources") or ()):
        if not isinstance(source, Mapping):
            continue
        external_license = source.get("license")
        external_id = f"SPDXRef-External-{index}"
        packages.append(
            {
                "name": str(source.get("reference", f"external-{index}"))[:120],
                "SPDXID": external_id,
                "downloadLocation": str(source.get("reference", "NOASSERTION")),
                "filesAnalyzed": False,
                "licenseConcluded": str(external_license or "NOASSERTION"),
                "licenseDeclared": str(external_license or "NOASSERTION"),
                "copyrightText": "NOASSERTION",
                "comment": (
                    "Third-party material recorded by the MNCS manifest; "
                    f"license_status={source.get('license_status', 'unknown')} "
                    "is declared evidence, not verification."
                ),
            }
        )
        relationships.append(
            {
                "spdxElementId": spdx_ref,
                "relationshipType": "DEPENDS_ON" if source.get("kind") == "package" else "OTHER",
                "relatedSpdxElement": external_id,
                "comment": (
                    f"MNCS source kind={source.get('kind', 'other')}; "
                    f"license_status={source.get('license_status', 'unknown')}"
                ),
            }
        )

    origin = str(provenance.get("origin_classification", "origin-uncertain"))
    annotations = [
        {
            "annotationDate": now,
            "annotationType": "REVIEW",
            "annotator": "Organization: MNCS Rights & Provenance (mncs-rp export)",
            "comment": (
                f"MNCS origin classification: {origin}. This describes process "
                "evidence only and is not a copyright conclusion."
            ),
        }
    ]
    participants = [
        str(participant["model"])
        for participant in provenance.get("participants") or ()
        if isinstance(participant, Mapping)
        and isinstance(participant.get("model"), str)
        and participant.get("model")
    ]
    ai_note = None
    if participants:
        ai_note = (
            "AI-generated code present per MNCS manifest; models involved: "
            + ", ".join(sorted(set(participants)))
            + ". See MNCS manifest for evidence; this field does not assert authorship or ownership."
        )

    document_name = re.sub(r"[^A-Za-z0-9.\-]+", "-", artifact_id)[:60] or "mncs-manifest"
    return {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": document_name,
        "documentNamespace": f"{document_uri}/{manifest_identity}",
        "creationInfo": {
            "created": now,
            "creators": ["Organization: MNCS Rights & Provenance"],
            "licenseListVersion": "3.25",
            "comment": (
                "Generated by mncs-rights-provenance from an MNCS v0.2 rights manifest. "
                + (f"MNCS manifest identity: {manifest_identity}" if manifest_identity else "")
            ),
        },
        "packages": packages,
        "relationships": [
            {
                "spdxElementId": "SPDXRef-DOCUMENT",
                "relationshipType": "DESCRIBES",
                "relatedSpdxElement": spdx_ref,
            },
            *relationships,
        ],
        "annotations": annotations,
        **({"comment": [ai_note]} if ai_note else {}),
    }


def import_spdx_sources(spdx_document: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Map SPDX packages into manifest source entries (license evidence only)."""
    sources: list[dict[str, Any]] = []
    packages = spdx_document.get("packages")
    if not isinstance(packages, list):
        return sources
    for package in packages:
        if not isinstance(package, Mapping):
            continue
        license_value = package.get("licenseDeclared") or package.get("licenseConcluded")
        if not isinstance(license_value, str) or not license_value:
            continue
        status = "unknown" if license_value in {"NOASSERTION", "NONE"} else "compatible"
        sources.append(
            {
                "kind": "package",
                "reference": str(
                    package.get("downloadLocation") or package.get("name", "spdx-package")
                ),
                "license_status": status,
                "license": license_value,
                "confidence": "observed-declaration" if status == "compatible" else "unknown",
                "notes": "Imported from SPDX declaration; declaration is evidence, not verification.",
            }
        )
    return sources


def _copyright_text(rights: Mapping[str, Any]) -> str:
    status = str(rights.get("copyright_status", "unresolved"))
    if status == "human-authorship-confirmed":
        return "NOASSERTION"
    if status == "third-party-licensed":
        return "NOASSERTION"
    return "UNDETERMINED (MNCS copyright-status: " + status + ")"


__all__ = ["export_spdx", "import_spdx_sources", "is_valid_spdx_expression"]
