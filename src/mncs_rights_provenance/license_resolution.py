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

from .spdx import is_valid_spdx_expression

RESOLUTION_SCHEMA = "mncs.rights.license-resolution/1"
_CANDIDATE_REGISTRY_REF = "mncs_rights_provenance/resources/license-candidates.json"

_TOKENS = re.compile(r"\s*(\(|\)|AND\b|OR\b|[A-Za-z0-9][A-Za-z0-9.+-]*)")

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
    for entry in entries:
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("identifier"), str)
            or entry["identifier"] in candidates
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
        ):
            raise TypeError("packaged license candidate registry has an invalid entry")
        candidates[entry["identifier"]] = entry
    if not candidates:
        raise RuntimeError("packaged license candidate registry is empty")
    return candidates, "sha256:" + hashlib.sha256(registry_bytes).hexdigest()


_CANDIDATES, _CANDIDATE_REGISTRY_DIGEST = _load_license_candidates()


def license_resolver_identity() -> str:
    """Return the content identity of the bounded license term index."""
    value = {
        "schema_version": RESOLUTION_SCHEMA,
        "terms": _TERMS,
        "candidate_registry_sha256": _CANDIDATE_REGISTRY_DIGEST,
    }
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


class _ExpressionParser:
    def __init__(self, expression: str) -> None:
        tokens: list[str] = []
        offset = 0
        while offset < len(expression):
            match = _TOKENS.match(expression, offset)
            if match is None:
                raise ValueError("unsupported SPDX expression syntax")
            tokens.append(match.group(1))
            offset = match.end()
        self.tokens = tokens
        self.offset = 0

    def parse(self) -> dict[str, Any]:
        value = self._or()
        if self.offset != len(self.tokens):
            raise ValueError("unexpected SPDX expression token")
        return value

    def _or(self) -> dict[str, Any]:
        children = [self._and()]
        while self._peek("OR"):
            self.offset += 1
            children.append(self._and())
        return children[0] if len(children) == 1 else {"operator": "OR", "terms": children}

    def _and(self) -> dict[str, Any]:
        children = [self._atom()]
        while self._peek("AND"):
            self.offset += 1
            children.append(self._atom())
        return children[0] if len(children) == 1 else {"operator": "AND", "terms": children}

    def _atom(self) -> dict[str, Any]:
        if self._peek("("):
            self.offset += 1
            value = self._or()
            if not self._peek(")"):
                raise ValueError("unclosed SPDX expression group")
            self.offset += 1
            return value
        if self.offset >= len(self.tokens) or self.tokens[self.offset] in {"AND", "OR", ")"}:
            raise ValueError("missing SPDX license identifier")
        identifier = self.tokens[self.offset]
        self.offset += 1
        if identifier == "WITH":
            raise ValueError("WITH must follow a license identifier")
        if self._peek("WITH"):
            self.offset += 1
            if self.offset >= len(self.tokens) or self.tokens[self.offset] in {"AND", "OR", ")", "WITH"}:
                raise ValueError("WITH must be followed by an exception identifier")
            exception = self.tokens[self.offset]
            self.offset += 1
            return {"license": identifier, "exception": exception}
        return {"license": identifier}

    def _peek(self, token: str) -> bool:
        return self.offset < len(self.tokens) and self.tokens[self.offset] == token


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
        if not is_valid_spdx_expression(expression):
            raise ValueError("invalid SPDX expression shape")
        tree = _ExpressionParser(expression).parse()
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
            candidate = _CANDIDATES.get(identifier)
            if candidate is not None:
                unresolved.append(identifier)
                candidate_references.add(identifier)
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
            terms = _TERMS.get(identifier)
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
    return result
