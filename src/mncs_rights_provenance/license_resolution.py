"""Conservative, explainable summaries of a small set of SPDX license terms.

This module preserves the SPDX expression tree and reports only terms tied to
the referenced license text. It does not decide copyright ownership or license
compatibility. Unknown identifiers and unsupported expression syntax remain
unknown instead of being reduced to permission flags.
"""

from __future__ import annotations

import hashlib
import json
import re
from importlib.resources import files
from typing import Any

from .spdx import parse_spdx_expression

RESOLUTION_SCHEMA = "mncs.rights.license-resolution/3"
_CANDIDATE_REGISTRY_REF = "mncs_rights_provenance/resources/license-candidates.json"

_LOCAL_LICENSE_REF = re.compile(r"^LicenseRef-[A-Za-z0-9.-]+$", re.IGNORECASE)
_DOCUMENT_LICENSE_REF = re.compile(
    r"^DocumentRef-[A-Za-z0-9.-]+:LicenseRef-[A-Za-z0-9.-]+$",
    re.IGNORECASE,
)

# Each entry is a short machine-readable index to the identified license text,
# not an independent grant or an exhaustive legal interpretation.
_TERMS: dict[str, dict[str, Any]] = {
    "MIT": {
        "source": "https://spdx.org/licenses/MIT.html",
        "permissions": ["use", "copy", "modify", "merge", "publish", "distribute", "sublicense", "sell"],
        "conditions": [
            {"id": "retain-copyright-and-permission-notice", "when": "all copies or substantial portions"}
        ],
        "patent": {"status": "no-express-patent-grant-in-identified-text"},
        "warranty": "as-is-and-liability-disclaimer",
    },
    "BSD-2-Clause": {
        "source": "https://spdx.org/licenses/BSD-2-Clause.html",
        "permissions": ["use", "redistribute-source", "redistribute-binary", "modify"],
        "conditions": [
            {"id": "retain-notice-conditions-and-disclaimer", "when": "source redistribution"},
            {"id": "reproduce-notice-conditions-and-disclaimer", "when": "binary redistribution"},
        ],
        "patent": {"status": "no-express-patent-grant-in-identified-text"},
        "warranty": "as-is-and-liability-disclaimer",
    },
    "BSD-2-Clause-Patent": {
        "source": "https://spdx.org/licenses/BSD-2-Clause-Patent.html",
        "permissions": ["use", "redistribute-source", "redistribute-binary", "modify"],
        "conditions": [
            {"id": "retain-notice-conditions-and-disclaimer", "when": "source redistribution"},
            {"id": "reproduce-notice-conditions-and-disclaimer", "when": "binary redistribution"},
        ],
        "patent": {
            "status": "explicit-grant-in-identified-text",
            "scope": "claims licensable by the grantor and necessarily infringed by its contribution alone or by its contribution with the work to which it was added",
            "termination": "only as stated in the identified license text",
        },
        "warranty": "as-is-and-liability-disclaimer",
    },
    "BSD-3-Clause": {
        "source": "https://spdx.org/licenses/BSD-3-Clause.html",
        "permissions": ["use", "redistribute-source", "redistribute-binary", "modify"],
        "conditions": [
            {"id": "retain-notice-conditions-and-disclaimer", "when": "source redistribution"},
            {"id": "reproduce-notice-conditions-and-disclaimer", "when": "binary redistribution"},
            {"id": "no-endorsement-without-permission", "when": "use of contributor names to endorse or promote"},
        ],
        "patent": {"status": "no-express-patent-grant-in-identified-text"},
        "warranty": "as-is-and-liability-disclaimer",
    },
    "Apache-2.0": {
        "source": "https://www.apache.org/licenses/LICENSE-2.0.html",
        "permissions": ["reproduce", "prepare-derivative-works", "display", "perform", "sublicense", "distribute"],
        "conditions": [
            {"id": "provide-license-copy", "when": "redistribution"},
            {"id": "mark-modified-files", "when": "redistributed modified files"},
            {"id": "preserve-applicable-source-notices", "when": "source-form derivative works"},
            {"id": "preserve-notice-attributions", "when": "the work includes a NOTICE file and the attribution applies"},
        ],
        "patent": {
            "status": "explicit-grant-in-identified-text",
            "scope": "claims licensable by each contributor and necessarily infringed by its contribution alone or with the work to which it was submitted",
            "termination": "patent-litigation-termination-for-the-work",
        },
        "warranty": "as-is-and-liability-disclaimer",
    },
}


def _load_license_candidates() -> tuple[dict[str, dict[str, Any]], str]:
    resource = files("mncs_rights_provenance").joinpath(
        "resources", "license-candidates.json"
    )
    registry_bytes = resource.read_bytes()
    value = json.loads(registry_bytes)
    if (
        not isinstance(value, dict)
        or value.get("schema_version") != "mncs.rights.license-candidates/1"
    ):
        raise RuntimeError("packaged license candidate registry has an unsupported schema")
    entries = value.get("candidates")
    if not isinstance(entries, list):
        raise TypeError("packaged license candidate registry has no candidate list")
    candidates: dict[str, dict[str, Any]] = {}
    folded_identifiers: set[str] = set()
    for entry in entries:
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("identifier"), str)
            or entry["identifier"].casefold() in folded_identifiers
            or not isinstance(entry.get("version"), str)
            or not entry["version"]
            or entry.get("status") != "draft-for-legal-review"
            or entry.get("adoption_status") != "not-adopted"
            or entry.get("effective_grant") is not False
            or entry.get("retroactive_application") is not False
            or entry.get("adoption_authority") is not None
            or not isinstance(entry.get("text_ref"), str)
            or not entry["text_ref"]
            or entry.get("declared_rights_prove_authority") is not False
            or not isinstance(entry.get("legal_review_decisions"), list)
            or len(entry["legal_review_decisions"]) > 64
            or any(
                not isinstance(decision, str)
                or not decision.strip()
                or len(decision) > 128
                for decision in entry["legal_review_decisions"]
            )
            or len(set(entry["legal_review_decisions"]))
            != len(entry["legal_review_decisions"])
        ):
            raise TypeError("packaged license candidate registry has an invalid entry")
        candidates[entry["identifier"]] = entry
        folded_identifiers.add(entry["identifier"].casefold())
    if not candidates:
        raise RuntimeError("packaged license candidate registry is empty")
    return candidates, "sha256:" + hashlib.sha256(registry_bytes).hexdigest()


_CANDIDATES, _CANDIDATE_REGISTRY_DIGEST = _load_license_candidates()
_CANDIDATE_IDENTIFIERS = {
    identifier.casefold(): identifier for identifier in _CANDIDATES
}
_TERM_IDENTIFIERS = {identifier.casefold(): identifier for identifier in _TERMS}
_CANDIDATE_INDEX = {
    identifier: index for index, identifier in enumerate(_CANDIDATES)
}


def license_resolver_identity() -> str:
    """Return the content identity of the parser and bounded license term index."""
    value = {
        "schema_version": RESOLUTION_SCHEMA,
        "expression_parser": "spdx-2.3-license-expression/1",
        "terms": _TERMS,
        "candidate_registry_sha256": _CANDIDATE_REGISTRY_DIGEST,
    }
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def resolve_license_expression(expression: str) -> dict[str, Any]:
    """Return a bounded term tree; compatibility and authority stay unresolved."""
    if len(expression) > 4096:
        return {
            "schema_version": RESOLUTION_SCHEMA,
            "expression": expression[:256],
            "status": "unresolved",
            "reason": "expression exceeds the bounded resolver input size",
            "compatibility": {"status": "unknown", "reason": "expression was not resolved"},
        }
    try:
        tree = parse_spdx_expression(expression)
    except ValueError as error:
        return {
            "schema_version": RESOLUTION_SCHEMA,
            "expression": expression,
            "status": "unresolved",
            "reason": str(error),
            "compatibility": {"status": "unknown", "reason": "expression was not resolved"},
        }

    unresolved: list[str] = []
    candidate_references: set[str] = set()

    def expand(node: dict[str, Any]) -> dict[str, Any]:
        if "license" in node:
            identifier = str(node["license"])
            exception = node.get("exception")
            if isinstance(exception, str):
                unresolved.append(f"{identifier} WITH {exception}")
                return {
                    "license": identifier,
                    "exception": exception,
                    "status": "unknown-license-exception-terms",
                }
            candidate_identifier = _CANDIDATE_IDENTIFIERS.get(identifier.casefold())
            candidate = _CANDIDATES.get(candidate_identifier) if candidate_identifier else None
            if candidate is not None:
                unresolved.append(candidate_identifier)
                candidate_references.add(candidate_identifier)
                return {
                    "license": identifier,
                    "status": "candidate-unapproved",
                    "candidate_status": candidate["status"],
                    "candidate_version": candidate["version"],
                    "effective_grant": candidate["effective_grant"],
                    "adoption_status": candidate["adoption_status"],
                    "declared_rights_prove_authority": False,
                    "source_ref": candidate["text_ref"],
                    "registry_ref": _CANDIDATE_REGISTRY_REF,
                    "registry_sha256": _CANDIDATE_REGISTRY_DIGEST,
                }
            if _DOCUMENT_LICENSE_REF.fullmatch(identifier):
                unresolved.append(identifier)
                return {
                    "license": identifier,
                    "status": "unresolved-license-reference",
                    "reference_kind": "external-document-license-ref",
                    "reason": "the referenced SPDX document and its extracted license terms were not supplied",
                }
            if _LOCAL_LICENSE_REF.fullmatch(identifier):
                unresolved.append(identifier)
                return {
                    "license": identifier,
                    "status": "unresolved-license-reference",
                    "reference_kind": "document-local-license-ref",
                    "reason": "the document-local extracted license terms were not supplied",
                }
            terms_identifier = _TERM_IDENTIFIERS.get(identifier.casefold())
            terms = _TERMS.get(terms_identifier) if terms_identifier else None
            if terms is None:
                unresolved.append(identifier)
                return {"license": identifier, "status": "unknown-license-terms"}
            return {"license": identifier, "status": "reference-summary", **terms}
        return {
            "operator": node["operator"],
            "terms": [expand(child) for child in node["terms"]],
        }

    expanded = expand(tree)
    status = "partial" if unresolved else "reference-summary"
    result: dict[str, Any] = {
        "schema_version": RESOLUTION_SCHEMA,
        "expression": expression,
        "status": status,
        "expression_tree": expanded,
        "unresolved_identifiers": sorted(set(unresolved)),
        "candidate_references": sorted(candidate_references),
        "compatibility": {
            "status": "unknown",
            "reason": "license terms are summarized per expression branch; compatibility is not inferred",
        },
    }
    if candidate_references:
        result["candidate_registry"] = {
            "reference": _CANDIDATE_REGISTRY_REF,
            "sha256": _CANDIDATE_REGISTRY_DIGEST,
        }
        result["candidate_review_details"] = [
            {
                "license": identifier,
                "status": _CANDIDATES[identifier]["status"],
                "decision_count": len(
                    _CANDIDATES[identifier]["legal_review_decisions"]
                ),
                "decisions_ref": (
                    f"{_CANDIDATE_REGISTRY_REF}#/candidates/"
                    f"{_CANDIDATE_INDEX[identifier]}/legal_review_decisions"
                ),
            }
            for identifier in sorted(candidate_references)
        ]
    return result
