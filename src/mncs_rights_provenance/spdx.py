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

_IDSTRING = r"[A-Za-z0-9.-]+"
_LICENSE_REF_RE = re.compile(
    rf"^(?:(?i:DocumentRef-){_IDSTRING}:)?(?i:LicenseRef-){_IDSTRING}$"
)
_LICENSE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]*\+?$")
_EXCEPTION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]*$")
_TOKEN_RE = re.compile(
    rf"\s*(\(|\)|AND\b|OR\b|WITH\b|"
    rf"(?:(?i:DocumentRef-){_IDSTRING}:)?(?i:LicenseRef-){_IDSTRING}|"
    rf"[A-Za-z0-9][A-Za-z0-9.-]*\+?)"
)

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
    """Check SPDX 2.3 expression shape without asserting list membership.

    License identifiers that this package does not recognize remain valid
    syntax and are resolved as unknown terms. This parser validates operator
    placement, grouping, ``WITH`` shape, and local/external ``LicenseRef``
    syntax; it is not a license-list or legal-compatibility validator.
    """
    try:
        parse_spdx_expression(expression)
    except (TypeError, ValueError):
        return False
    return True


class _SPDXExpressionParser:
    def __init__(self, expression: str) -> None:
        if (not isinstance(expression, str) or not expression
                or len(expression) > 256 or expression.strip() != expression
                or "\n" in expression or "\r" in expression or "\t" in expression):
            raise ValueError("invalid SPDX expression text")
        self.tokens: list[str] = []
        offset = 0
        while offset < len(expression):
            match = _TOKEN_RE.match(expression, offset)
            if match is None:
                raise ValueError("unsupported SPDX expression syntax")
            self.tokens.append(match.group(1))
            offset = match.end()
        self.offset = 0
        self.depth = 0

    def parse(self) -> dict[str, Any]:
        if not self.tokens:
            raise ValueError("missing SPDX license expression")
        value, _ = self._or()
        if self.offset != len(self.tokens):
            raise ValueError("unexpected SPDX expression token")
        return value

    def _or(self) -> tuple[dict[str, Any], bool]:
        children = [self._and()]
        while self._peek("OR"):
            self.offset += 1
            children.append(self._and())
        values = [value for value, _ in children]
        return (values[0] if len(values) == 1 else
                {"operator": "OR", "terms": values}, len(values) == 1 and children[0][1])

    def _and(self) -> tuple[dict[str, Any], bool]:
        children = [self._with()]
        while self._peek("AND"):
            self.offset += 1
            children.append(self._with())
        values = [value for value, _ in children]
        return (values[0] if len(values) == 1 else
                {"operator": "AND", "terms": values}, len(values) == 1 and children[0][1])

    def _with(self) -> tuple[dict[str, Any], bool]:
        value, simple = self._atom()
        if not self._peek("WITH"):
            return value, simple
        if not simple:
            raise ValueError("WITH must follow a simple SPDX expression")
        self.offset += 1
        if self.offset >= len(self.tokens):
            raise ValueError("WITH must be followed by an exception identifier")
        exception = self.tokens[self.offset]
        if not _EXCEPTION_ID_RE.fullmatch(exception):
            raise ValueError("WITH must be followed by an exception identifier")
        self.offset += 1
        return {"license": value["license"], "exception": exception}, True

    def _atom(self) -> tuple[dict[str, Any], bool]:
        if self._peek("("):
            if self.depth >= 8:
                raise ValueError("SPDX expression nesting exceeds 8 levels")
            self.offset += 1
            self.depth += 1
            value, _ = self._or()
            if not self._peek(")"):
                raise ValueError("unclosed SPDX expression group")
            self.offset += 1
            self.depth -= 1
            return value, False
        if self.offset >= len(self.tokens):
            raise ValueError("missing SPDX license identifier")
        identifier = self.tokens[self.offset]
        if identifier in {"AND", "OR", "WITH", ")"}:
            raise ValueError("missing SPDX license identifier")
        if not (_LICENSE_REF_RE.fullmatch(identifier)
                or _LICENSE_ID_RE.fullmatch(identifier)):
            raise ValueError("invalid SPDX license identifier or reference")
        self.offset += 1
        return {"license": identifier}, True

    def _peek(self, token: str) -> bool:
        return self.offset < len(self.tokens) and self.tokens[self.offset] == token


def parse_spdx_expression(expression: str) -> dict[str, Any]:
    """Parse SPDX 2.3 expression structure while preserving identifiers.

    The returned tree preserves OR alternatives and AND obligations. It does
    not verify that an identifier exists in the SPDX License List.
    """
    return _SPDXExpressionParser(expression).parse()


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
    """Map SPDX package metadata into source evidence, without resolving compatibility."""
    sources: list[dict[str, Any]] = []
    packages = spdx_document.get("packages")
    if not isinstance(packages, list):
        return sources
    for package in packages:
        if not isinstance(package, Mapping):
            continue
        declared = package.get("licenseDeclared")
        concluded = package.get("licenseConcluded")
        if isinstance(declared, str) and declared:
            license_value = declared
            confidence = "unknown" if declared in {"NOASSERTION", "NONE"} else "observed-declaration"
            note = (
                "Imported from SPDX licenseDeclared; the license identity is evidence, "
                "not verification, and compatibility remains unresolved."
                if confidence == "observed-declaration"
                else "SPDX licenseDeclared is " + declared + "; rights and compatibility remain unknown."
            )
        elif isinstance(concluded, str) and concluded:
            license_value = concluded
            confidence = "unknown" if concluded in {"NOASSERTION", "NONE"} else "analysis"
            note = (
                "Imported from SPDX licenseConcluded; the analyzer conclusion is evidence, "
                "not verification, and compatibility remains unresolved."
                if confidence == "analysis"
                else "SPDX licenseConcluded is " + concluded + "; rights and compatibility remain unknown."
            )
        else:
            continue
        sources.append(
            {
                "kind": "package",
                "reference": str(
                    package.get("downloadLocation") or package.get("name", "spdx-package")
                ),
                # SPDX identifies a declaration or analysis result, but this
                # importer has no target license or rule set with which to
                # decide compatibility.
                "license_status": "unknown",
                "license": license_value,
                "confidence": confidence,
                "notes": note,
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


__all__ = [
    "export_spdx",
    "import_spdx_sources",
    "is_valid_spdx_expression",
    "parse_spdx_expression",
]
