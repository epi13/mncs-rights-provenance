"""Compact first-use projection of authorized rights and agent governance."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Mapping
from typing import Any

from .license_resolution import (
    RESOLUTION_SCHEMA,
    license_action_guidance,
    license_action_ruleset_identity,
    license_resolver_identity,
    resolve_license_expression,
)
from .manifest import compute_manifest_identity
from .validation import validate_manifest_structure

CONTEXT_SCHEMA = "mncs.rights-provenance.agent-context/1"
GOVERNANCE_SCHEMA = "mncs.rights.agent-governance/0.1.0"
_RIGHTS_RULES = {
    "external_material": {"verify", "record-source"},
    "incompatible_rights": {"resolve-before-inclusion", "explain-and-escalate"},
    "unknown_rights": {"investigate", "preserve-unknown"},
}
_PROVENANCE_RULES = {
    "lineage": {"preserve", "best-effort"},
    "transformations": {"record", "best-effort"},
    "external_inputs": {"identify", "best-effort"},
    "unverifiable_claims": {"distinguish", "record"},
}
_AGENT_RULES = {
    "copying_external_implementations": {"authorization-required", "verify-rights"},
    "independent_implementation": {"permitted-when-lawful", "investigate"},
    "rights_conflict": {"explain-and-escalate", "investigate"},
    "provenance_loss": {"diagnose-and-recover", "record-unknown"},
}
_SHA256_DIGEST = re.compile(r"^sha256:[a-f0-9]{64}$")
_REFERENCE_FIELDS = {
    "detail_ref",
    "expression_ref",
    "expression_tree_ref",
    "license_terms_ref",
    "rules_ref",
    "unresolved_identifiers_ref",
    "evidence_ref",
}


def _bounded_label(value: Any, fallback: str, *, limit: int = 128) -> str:
    if isinstance(value, str) and value:
        return value[:limit]
    return fallback


def _compact_authoritative_references(context: dict[str, Any]) -> None:
    """Replace repeated long manifest/profile refs with resolvable source aliases."""
    source_references = {
        key: source.get("reference")
        for key, source in context["sources"].items()
        if key in {"rights_manifest", "governance_profile"}
        and isinstance(source, Mapping)
        and isinstance(source.get("reference"), str)
    }
    def compact(value: Any) -> Any:
        if not isinstance(value, str):
            return value
        for key, source_ref in source_references.items():
            alias = f"source:{key}"
            if len(source_ref) <= len(alias):
                continue
            if value == source_ref or value.startswith(source_ref + "#"):
                return alias + value[len(source_ref):]
        return value

    def compact_fields(record: dict[str, Any]) -> None:
        for field in _REFERENCE_FIELDS:
            if field in record:
                record[field] = compact(record[field])

    rights = context["rights"]
    compact_fields(rights["license_terms"])
    compact_fields(rights["action_guidance"])
    for source in rights["sources"]:
        compact_fields(source)
        if isinstance(source.get("evidence_refs"), list):
            source["evidence_refs"] = [compact(item) for item in source["evidence_refs"]]

    provenance = context["provenance"]
    compact_fields(provenance)
    for relationship in provenance["projection"]["relationships"]:
        if "from" in relationship:
            relationship["from"] = compact(relationship["from"])

    compact_fields(context["governance"])
    for diagnostic in context["diagnostics"]:
        compact_fields(diagnostic)

def _fit_context(context: dict[str, Any], budget: int) -> None:
    """Drop on-demand detail before the admission projection exceeds its budget."""
    target = budget - 96  # leave room for the final content identity
    original_diagnostics = list(context["diagnostics"])
    rights = context["rights"]
    terms = rights["license_terms"]
    if len(json.dumps(context, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")) <= target:
        return
    if "expression_tree" in terms:
        terms.pop("expression_tree")
        terms["detail_ref"] = context["sources"]["rights_manifest"]["reference"] + "#/rights/distribution_license"
    if len(json.dumps(context, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")) <= target:
        return
    provenance = context["provenance"]
    # Deduplicate long references and lineage digests before discarding useful
    # diagnostics; these references remain resolvable through the source map.
    _compact_authoritative_references(context)
    for relationship in provenance["projection"]["relationships"]:
        relationship.pop("to", None)
        source_key = next(
            (
                key for key, source in context["sources"].items()
                if isinstance(source, Mapping)
                and (
                    relationship.get("from") == source.get("reference")
                    or relationship.get("from") == f"source:{key}"
                )
            ),
            None,
        )
        digest = relationship.pop("content_digest", None)
        if source_key is not None and isinstance(digest, str):
            relationship["content_digest_ref"] = f"#/sources/{source_key}/sha256"
        else:
            relationship["content_digest"] = digest
    encoded = json.dumps(context, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(encoded) <= target:
        return
    provenance["relationship_kinds"] = dict(list(provenance["relationship_kinds"].items())[:8])
    for limit in (8, 4, 2, 0):
        context["diagnostics"] = context["diagnostics"][:limit]
        encoded = json.dumps(context, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        if len(encoded) <= target:
            return
    if rights["sources"]:
        rights["sources"] = []
        rights["sources_truncated"] = rights["source_count"] > 0
    provenance["relationship_kinds"] = {}
    encoded = json.dumps(context, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(encoded) > target:
        # Preserve the legal declaration, authority, evidence references, and
        # lineage edges. Long rule detail remains reachable through detail_ref.
        governance = context["governance"]
        governance["rules_ref"] = governance.pop(
            "detail_ref", governance.get("rules_ref")
        )
        governance.pop("rules", None)
    action_guidance = rights.get("action_guidance")
    encoded = json.dumps(context, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if (
        len(encoded) > target
        and isinstance(action_guidance, dict)
        and action_guidance.get("expression_tree") is not None
    ):
        action_guidance.pop("expression_tree")
    encoded = json.dumps(context, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(encoded) > target and isinstance(action_guidance, dict):
        action_guidance.pop("not_assessed", None)
        action_guidance.pop("decision_notes", None)
        action_guidance.pop("decision_note_count", None)
        action_guidance.pop("decision_notes_truncated", None)
        ruleset = action_guidance.get("ruleset")
        if isinstance(ruleset, Mapping):
            # The exact ruleset version and identity remain in `sources`.
            action_guidance.pop("ruleset", None)
        actions = action_guidance.get("actions")
        if (
            isinstance(actions, Mapping)
            and actions
            and all(
                isinstance(result, Mapping)
                and result.get("status") == action_guidance.get("status")
                for result in actions.values()
            )
        ):
            # The shared status already summarizes every action in this case.
            action_guidance.pop("actions", None)
    encoded = json.dumps(context, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(encoded) > target:
        expression = terms.get("expression")
        if isinstance(expression, str) and len(expression) > 128:
            terms["expression"] = expression[:128]
            terms["expression_truncated"] = True
            terms.setdefault(
                "detail_ref",
                context["sources"]["rights_manifest"]["reference"]
                + "#/rights/distribution_license",
            )
    encoded = json.dumps(context, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(encoded) > target:
        unresolved = terms.get("unresolved_identifiers")
        if isinstance(unresolved, list) and unresolved:
            terms["unresolved_identifier_count"] = len(unresolved)
            terms["unresolved_identifiers_ref"] = (
                context["sources"]["rights_manifest"]["reference"]
                + "#/rights/distribution_license"
            )
            terms.pop("unresolved_identifiers")
    encoded = json.dumps(context, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(encoded) > target:
        declaration = rights.get("distribution_license")
        if isinstance(declaration, str) and len(declaration) > 128:
            rights["distribution_license"] = declaration[:128]
            rights["distribution_license_truncated"] = True
    encoded = json.dumps(context, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(encoded) > target:
        compatibility = rights.get("compatibility")
        if isinstance(compatibility, dict):
            compatibility.pop("reason", None)
        license_compatibility = terms.get("compatibility")
        if isinstance(license_compatibility, dict):
            license_compatibility.pop("reason", None)
    encoded = json.dumps(context, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(encoded) > target and isinstance(terms.get("detail_ref"), str):
        # The declaration is already projected on rights.distribution_license;
        # drop its duplicate resolver copy once the authoritative reference is present.
        terms.pop("expression", None)
    if original_diagnostics:
        action_guidance = rights.get("action_guidance")
        if (
            isinstance(terms.get("expression"), str)
            and terms.get("expression") == rights.get("distribution_license")
        ):
            terms.pop("expression", None)
        compatibility = rights.get("compatibility")
        if isinstance(compatibility, dict):
            compatibility.pop("reason", None)
        license_compatibility = terms.get("compatibility")
        if isinstance(license_compatibility, dict):
            license_compatibility.pop("reason", None)
        if (
            isinstance(action_guidance, Mapping)
            and terms.get("detail_ref") == action_guidance.get("expression_ref")
        ):
            # The action-guidance expression reference points at this same
            # declaration and remains available with its query contract.
            terms.pop("detail_ref", None)
        context["diagnostics"] = original_diagnostics
        _compact_authoritative_references(context)
        retained: list[dict[str, Any]] = []
        for diagnostic in original_diagnostics:
            retained.append(diagnostic)
            context["diagnostics"] = retained
            encoded = json.dumps(
                context, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
            if len(encoded) > target:
                retained.pop()
                context["diagnostics"] = retained
                break


def _validate_governance(value: Any) -> tuple[dict[str, Any] | None, list[str]]:
    if not isinstance(value, Mapping):
        return None, ["governance profile must be an object"]
    allowed_top = {"schema_version", "profile_id", "profile_version", "rights", "provenance", "agent_governance"}
    if set(value) != allowed_top:
        return None, ["governance profile fields do not match the supported contract"]
    if value.get("schema_version") != GOVERNANCE_SCHEMA:
        return None, ["governance profile schema version is unsupported"]
    if (
        not isinstance(value.get("profile_id"), str)
        or not value["profile_id"]
        or len(value["profile_id"]) > 160
    ):
        return None, ["governance profile_id is missing or exceeds the supported length"]
    if (
        not isinstance(value.get("profile_version"), int)
        or isinstance(value.get("profile_version"), bool)
        or not 1 <= value["profile_version"] <= 65535
    ):
        return None, ["governance profile_version is outside the supported range"]

    clean: dict[str, Any] = {
        "schema_version": GOVERNANCE_SCHEMA,
        "profile_id": value["profile_id"],
        "profile_version": value["profile_version"],
    }
    errors: list[str] = []
    for section, rules in (
        ("rights", _RIGHTS_RULES),
        ("provenance", _PROVENANCE_RULES),
        ("agent_governance", _AGENT_RULES),
    ):
        raw = value.get(section)
        if not isinstance(raw, Mapping) or set(raw) != set(rules):
            errors.append(f"governance {section} rules do not match the supported contract")
            continue
        clean[section] = {}
        for key, allowed_values in rules.items():
            if raw.get(key) not in allowed_values:
                errors.append(f"governance {section}.{key} is unsupported")
            else:
                clean[section][key] = raw[key]
    return (clean if not errors else None), errors


def _combine_action_trees(source: Any, binary: Any) -> dict[str, Any] | None:
    if not isinstance(source, Mapping) or not isinstance(binary, Mapping):
        return None
    operator = source.get("operator")
    if operator in {"AND", "OR"} or binary.get("operator") in {"AND", "OR"}:
        source_terms = source.get("terms")
        binary_terms = binary.get("terms")
        if (
            operator != binary.get("operator")
            or not isinstance(source_terms, list)
            or not isinstance(binary_terms, list)
            or len(source_terms) != len(binary_terms)
        ):
            return None
        terms: list[dict[str, Any]] = []
        for source_term, binary_term in zip(source_terms, binary_terms, strict=True):
            combined = _combine_action_trees(source_term, binary_term)
            if combined is None:
                return None
            terms.append(combined)
        return {"operator": operator, "terms": terms}

    if source.get("license") != binary.get("license") or source.get("status") != binary.get("status"):
        return None
    status = source.get("status")
    if status != "reference-summary":
        fields = (
            "license", "exception", "status", "reason", "reference_kind",
            "candidate_status", "candidate_version", "effective_grant",
            "adoption_status",
        )
        limits = {
            "license": 128,
            "exception": 128,
            "status": 64,
            "reason": 256,
            "reference_kind": 64,
            "candidate_status": 64,
            "candidate_version": 64,
            "adoption_status": 64,
        }
        if any(source.get(field) != binary.get(field) for field in fields):
            return None
        result: dict[str, Any] = {}
        license_value = source.get("license")
        for field in fields:
            value = source.get(field)
            if isinstance(value, str):
                result[field] = value[:limits[field]]
            elif isinstance(value, (bool, int)):
                result[field] = value
        if isinstance(license_value, str) and len(license_value) > limits["license"]:
            result["license_truncated"] = True
        return result

    source_conditions = source.get("conditions")
    binary_conditions = binary.get("conditions")
    if not isinstance(source_conditions, list) or not isinstance(binary_conditions, list):
        return None
    binary_by_id = {
        condition.get("id"): condition
        for condition in binary_conditions
        if isinstance(condition, Mapping) and isinstance(condition.get("id"), str)
    }
    if len(binary_by_id) != len(binary_conditions):
        return None
    conditions: list[dict[str, Any]] = []
    for condition in source_conditions:
        if not isinstance(condition, Mapping) or not isinstance(condition.get("id"), str):
            return None
        other = binary_by_id.get(condition["id"])
        if not isinstance(other, Mapping):
            return None
        if (
            condition.get("when") != other.get("when")
            or condition.get("guidance") != other.get("guidance")
        ):
            return None
        relations = {
            "redistribute-source": condition.get("action_relation"),
            "redistribute-binary": other.get("action_relation"),
        }
        if any(not isinstance(value, str) for value in relations.values()):
            return None
        conditions.append({
            "id": condition["id"][:128],
            "when": str(condition.get("when", "trigger unavailable"))[:256],
            "guidance": str(condition.get("guidance", "Review this condition."))[:256],
            "action_relations": relations,
        })
    return {
        "license": str(source.get("license", ""))[:128],
        "status": status,
        "conditions": conditions,
    }


def _action_guidance_context(expression: Any, expression_ref: str) -> dict[str, Any]:
    ruleset = license_action_ruleset_identity()
    action_names = ("redistribute-source", "redistribute-binary")
    results: dict[str, Any] = {}
    reports: list[dict[str, Any]] = []
    all_notes: list[str] = []
    identifier_counts: dict[str, int] = {}
    condition_counts: dict[str, int] = {}
    for action in action_names:
        if isinstance(expression, str) and expression:
            report = license_action_guidance(expression, action)
            reports.append(report)
            identifiers = report.get("unresolved_identifiers", [])
            conditions = report.get("unresolved_conditions", [])
            notes = report.get("decision_notes", [])
            identifier_values = identifiers if isinstance(identifiers, list) else []
            condition_values = conditions if isinstance(conditions, list) else []
            note_values = notes if isinstance(notes, list) else []
            all_notes.extend(item for item in note_values if isinstance(item, str))
            identifier_counts[action] = len(identifier_values)
            condition_counts[action] = len(condition_values)
            result: dict[str, Any] = {"status": report.get("status", "unresolved")}
        else:
            result = {"status": "unresolved"}
            all_notes.append("No declared distribution license expression is available.")
        results[action] = result

    statuses = {result["status"] for result in results.values()}
    status = (
        "unresolved" if not isinstance(expression, str) or not expression or "unresolved" in statuses
        else "partial" if "partial" in statuses
        else "reference-summary"
    )
    expression_evidence = "declared-unverified" if reports else "no-usable-declaration"
    combined_tree = (
        _combine_action_trees(
            reports[0].get("expression_tree"), reports[1].get("expression_tree")
        )
        if len(reports) == 2 else None
    )
    context = {
        "schema_version": "mncs.rights.license-action-context/1",
        "status": status,
        "expression_ref": expression_ref,
        "expression_evidence": expression_evidence,
        "query_ref": "mncs-rp action-guidance",
        "ruleset": ruleset,
        "expression_tree": combined_tree,
        "actions": results,
        "not_assessed": [
            "license authority or ownership",
            "cross-license compatibility",
            "completeness of the artifact input set",
        ],
        "legal_conclusion": "NOT_MADE",
    }
    if any(identifier_counts.values()) or any(condition_counts.values()):
        context["unresolved_action_counts"] = {
            action: {
                "identifiers": identifier_counts.get(action, 0),
                "conditions": condition_counts.get(action, 0),
            }
            for action in action_names
        }
    unique_notes = list(dict.fromkeys(all_notes))
    if unique_notes:
        context.update({
            "decision_notes": unique_notes[:4],
            "decision_note_count": len(unique_notes),
            "decision_notes_truncated": len(unique_notes) > 4,
        })
    return context


def build_agent_context(
    manifest: Mapping[str, Any],
    governance: Mapping[str, Any] | None,
    *,
    binding: Mapping[str, Any] | None,
    manifest_ref: str = "RIGHTS.json",
    governance_ref: str = "governance/agent-governance.json",
    manifest_digest: str | None = None,
    governance_digest: str | None = None,
) -> dict[str, Any]:
    """Build the Environment admission summary without trusting file self-claims.

    The Environment binding supplies the policy authority. The governance file
    supplies only a versioned, allow-listed rule profile; external metadata
    cannot name an issuer, expand scope, or add free-form instructions.
    """
    manifest_ref = _bounded_label(manifest_ref, "RIGHTS.json", limit=256)
    governance_ref = _bounded_label(
        governance_ref, "governance/agent-governance.json", limit=256
    )
    manifest_digest = (
        manifest_digest
        if isinstance(manifest_digest, str) and _SHA256_DIGEST.fullmatch(manifest_digest)
        else None
    )
    governance_digest = (
        governance_digest
        if isinstance(governance_digest, str) and _SHA256_DIGEST.fullmatch(governance_digest)
        else None
    )
    diagnostics: list[dict[str, str]] = []
    manifest_issues = validate_manifest_structure(manifest)
    if manifest_issues:
        diagnostics.append({
            "code": "rights-manifest-invalid",
            "severity": "review",
            "summary": "Rights manifest failed structural validation.",
            "evidence_ref": manifest_ref,
            "remedy": "repair-manifest",
        })
    declared_identity = manifest.get("manifest_identity")
    try:
        observed_identity = compute_manifest_identity(manifest)
    except (TypeError, ValueError):
        observed_identity = None
        diagnostics.append({
            "code": "rights-manifest-unsealable",
            "severity": "review",
            "summary": "Manifest content is not representable in the canonical identity format.",
            "evidence_ref": manifest_ref,
            "remedy": "repair-manifest-values",
        })
    if declared_identity is not None and declared_identity != observed_identity:
        diagnostics.append({
            "code": "rights-manifest-identity-mismatch",
            "severity": "review",
            "summary": "Manifest identity does not match its canonical content.",
            "evidence_ref": manifest_ref,
            "remedy": "recompute-identity-from-authoritative-content",
        })

    rights_value = manifest.get("rights")
    rights: Mapping[str, Any] = (
        rights_value if isinstance(rights_value, Mapping) else {}
    )
    expression = rights.get("distribution_license")
    if isinstance(expression, str):
        license_resolution = resolve_license_expression(expression)
        if len(expression) > 4096:
            license_resolution["expression_truncated"] = True
            license_resolution["detail_ref"] = (
                f"{manifest_ref}#/rights/distribution_license"
            )
    else:
        license_resolution = {
            "schema_version": RESOLUTION_SCHEMA,
            "expression_evidence": "no-usable-declaration",
            "expression": None,
            "status": "unresolved",
            "reason": "distribution license is absent",
            "compatibility": {"status": "unknown", "reason": "license is absent"},
        }
    candidate_registry = license_resolution.get("candidate_registry")
    candidate_registry_source = (
        {
            "reference": candidate_registry["reference"],
            "sha256": candidate_registry["sha256"],
        }
        if (
            isinstance(candidate_registry, Mapping)
            and isinstance(candidate_registry.get("reference"), str)
            and isinstance(candidate_registry.get("sha256"), str)
        )
        else None
    )

    for field, code, remedy in (
        ("copyright_status", "copyright-status-unresolved", "review-copyright-basis"),
        ("rights_basis", "rights-basis-unknown", "record-rights-evidence"),
        ("third_party_material", "third-party-material-unknown", "identify-external-material"),
    ):
        value = rights.get(field)
        unresolved = value is None or (
            isinstance(value, str)
            and value in {
                "unresolved", "machine-originated-unresolved",
                "unknown-needs-review", "unknown", "possible",
            }
        )
        if unresolved:
            diagnostics.append({
                "code": code,
                "severity": "review",
                "summary": f"{field.replace('_', ' ')} remains unresolved in the declared manifest.",
                "evidence_ref": f"{manifest_ref}#/rights/{field}",
                "remedy": remedy,
            })
    raw_candidate_references = license_resolution.get("candidate_references", [])
    candidate_references: list[str] = (
        [item for item in raw_candidate_references if isinstance(item, str)]
        if isinstance(raw_candidate_references, list)
        else []
    )
    for candidate_reference in candidate_references:
        diagnostics.append({
            "code": "license-candidate-not-effective",
            "severity": "review",
            "summary": (
                f"{candidate_reference} is an unadopted draft and grants no rights here."
            ),
            "evidence_ref": (
                candidate_registry_source["reference"]
                if candidate_registry_source is not None
                else "mncs_rights_provenance/resources/license-candidates.json"
            ),
            "remedy": "identify-effective-license-declaration",
        })
    raw_unresolved_identifiers = license_resolution.get("unresolved_identifiers", [])
    unresolved_identifiers: set[str] = (
        {item for item in raw_unresolved_identifiers if isinstance(item, str)}
        if isinstance(raw_unresolved_identifiers, list)
        else set()
    )
    unresolved_identifiers.difference_update(candidate_references)
    if (
        license_resolution.get("status") in {"unresolved", "partial"}
        and unresolved_identifiers
    ):
        diagnostics.append({
            "code": "license-terms-unresolved",
            "severity": "review",
            "summary": "Some license expression terms are outside the bounded term index.",
            "evidence_ref": f"{manifest_ref}#/rights/distribution_license",
            "remedy": "inspect-license-reference",
        })

    provenance_value = manifest.get("provenance")
    provenance: Mapping[str, Any] = (
        provenance_value if isinstance(provenance_value, Mapping) else {}
    )
    graph_value = provenance.get("graph")
    graph: Mapping[str, Any] = graph_value if isinstance(graph_value, Mapping) else {}
    raw_edges = graph.get("edges")
    edges: list[Any] = raw_edges if isinstance(raw_edges, list) else []
    raw_participants = provenance.get("participants")
    participants: list[Any] = raw_participants if isinstance(raw_participants, list) else []
    origin = _bounded_label(provenance.get("origin_classification"), "origin-uncertain")
    if origin == "origin-uncertain":
        diagnostics.append({
            "code": "provenance-origin-uncertain",
            "severity": "review",
            "summary": "Origin is explicitly unresolved; no authorship or ownership conclusion is inferred.",
            "evidence_ref": f"{manifest_ref}#/provenance",
            "remedy": "add-evidence-or-preserve-uncertainty",
        })

    source_summaries: list[dict[str, Any]] = []
    raw_rights_sources = rights.get("sources")
    raw_sources: list[Any] = (
        raw_rights_sources if isinstance(raw_rights_sources, list) else []
    )
    for index, source in enumerate(raw_sources[:4]):
        if not isinstance(source, Mapping):
            continue
        source_license = source.get("license")
        status = _bounded_label(source.get("license_status"), "unknown", limit=64)
        source_summaries.append({
            "kind": _bounded_label(source.get("kind"), "other", limit=64),
            "reference": str(source.get("reference", "unknown"))[:160],
            "license": source_license[:128] if isinstance(source_license, str) else None,
            "license_status_declared": status,
            "verification_state": "unverified",
            "license_terms_status": resolve_license_expression(source_license).get("status")
            if isinstance(source_license, str) else "unresolved",
            "license_terms_ref": f"{manifest_ref}#/rights/sources/{index}/license",
            "evidence_refs": [
                str(item.get("reference", ""))[:160]
                for item in source.get("evidence", [])[:2]
                if isinstance(item, Mapping)
            ] if isinstance(source.get("evidence"), list) else [],
        })
        if status in {"unknown", "incompatible"}:
            has_license_expression = (
                isinstance(source_license, str)
                and bool(source_license)
                and source_license not in {"NOASSERTION", "NONE"}
            )
            if status == "unknown" and has_license_expression:
                summary = (
                    "A license expression is recorded, but compatibility with the "
                    "distribution license and source verification remain unresolved."
                )
            elif status == "unknown":
                summary = "No usable source license expression is recorded; source rights remain unknown."
            else:
                summary = "A source license status is declared as incompatible."
            diagnostics.append({
                "code": "source-license-" + status,
                "severity": "review",
                "summary": summary,
                "evidence_ref": f"{manifest_ref}#/rights/sources/{index}",
                "remedy": "investigate-external-rights",
            })

    clean_governance, governance_errors = _validate_governance(governance)
    binding_value = dict(binding or {})
    expected_profile = binding_value.get("profile_id")
    if not isinstance(expected_profile, str) or len(expected_profile) > 160:
        expected_profile = None
    authority_value = binding_value.get("authority")
    authority_scope = authority_value.get("scope") if isinstance(authority_value, Mapping) else None
    clean_authority_scope: list[str] = (
        [item for item in authority_scope if isinstance(item, str)]
        if isinstance(authority_scope, list)
        else []
    )
    authorized = (
        binding_value.get("authorized") is True
        and isinstance(expected_profile, str)
        and isinstance(authority_value, Mapping)
        and isinstance(authority_value.get("issuer"), str)
        and 0 < len(authority_value["issuer"]) <= 120
        and isinstance(authority_value.get("basis"), str)
        and 0 < len(authority_value["basis"]) <= 120
        and isinstance(authority_value.get("source_ref"), str)
        and 0 < len(authority_value["source_ref"]) <= 256
        and isinstance(authority_scope, list)
        and 0 < len(authority_scope) <= 16
        and all(isinstance(item, str) and 0 < len(item) <= 120 for item in authority_scope)
    )
    profile_matches = bool(clean_governance and clean_governance.get("profile_id") == expected_profile)
    governance_active = authorized and profile_matches
    if governance_errors or not governance_active:
        reason = "; ".join(governance_errors[:3]) or (
            "governance profile does not match an explicitly authorized Environment binding"
        )
        diagnostics.append({
            "code": "agent-governance-unavailable",
            "severity": "review",
            "summary": reason,
            "evidence_ref": governance_ref,
            "remedy": "repair-authorized-profile-binding",
        })
    if (
        governance_active
        and clean_governance is not None
        and clean_governance["provenance"]["lineage"] == "preserve"
        and not graph and not manifest.get("lineage")
    ):
        diagnostics.append({
            "code": "lineage-reference-missing",
            "severity": "review",
            "summary": "The authorized profile requires lineage, but the manifest has no graph or record reference.",
            "evidence_ref": f"{manifest_ref}#/provenance",
            "remedy": "diagnose-and-recover-lineage",
        })

    source_manifest_identity = observed_identity
    context_sources: dict[str, Any] = {
        "rights_manifest": {
            "reference": manifest_ref,
            "sha256": manifest_digest,
            "manifest_identity": source_manifest_identity,
            "identity_state": (
                "verified-content-digest"
                if declared_identity is not None and declared_identity == observed_identity
                else "computed-from-observed-content"
            ),
        },
        "governance_profile": {
            "reference": governance_ref,
            "sha256": governance_digest,
        },
    }
    if candidate_registry_source is not None:
        context_sources["license_candidate_registry"] = candidate_registry_source
    license_resolver_source = {
        "reference": (
            "mncs_rights_provenance.license_resolution/"
            + RESOLUTION_SCHEMA.rsplit("/", 1)[1]
        ),
        "sha256": license_resolver_identity(),
    }
    context_sources["license_resolver"] = license_resolver_source
    action_ruleset = license_action_ruleset_identity()
    action_rules_source = {
        "reference": action_ruleset["module_ref"],
        "sha256": action_ruleset["identity"],
    }
    context_sources["license_action_ruleset"] = action_rules_source
    context_lineage_relationships = [
        {
            "from": manifest_ref,
            "to": "agent-context",
            "relation": "generated-from" if manifest_digest else "referenced",
            "content_digest": manifest_digest,
            "evidence_state": "observed-input" if manifest_digest else "unavailable",
        },
        {
            "from": governance_ref,
            "to": "agent-context",
            "relation": "generated-from" if governance_digest else "referenced",
            "content_digest": governance_digest,
            "evidence_state": "observed-input" if governance_digest else "unavailable",
        },
    ]
    context_lineage_relationships.append({
        "from": license_resolver_source["reference"],
        "to": "agent-context",
        "relation": "referenced",
        "content_digest": license_resolver_source["sha256"],
        "evidence_state": "observed-input",
    })
    context_lineage_relationships.append({
        "from": action_rules_source["reference"],
        "to": "agent-context",
        "relation": "referenced",
        "content_digest": action_rules_source["sha256"],
        "evidence_state": "observed-input",
    })
    if candidate_registry_source is not None:
        context_lineage_relationships.append({
            "from": candidate_registry_source["reference"],
            "to": "agent-context",
            "relation": "generated-from",
            "content_digest": candidate_registry_source["sha256"],
            "evidence_state": "observed-input",
        })
    context_lineage_relationships.append({
        "from": "mncs_rights_provenance.agent_context.build_agent_context",
        "to": "agent-context",
        "relation": "transformed-by",
        "content_digest": None,
        "evidence_state": "observed-execution",
    })
    context: dict[str, Any] = {
        "schema_version": CONTEXT_SCHEMA,
        "context_budget_bytes": (
            binding_value.get("context_budget_bytes")
            if isinstance(binding_value.get("context_budget_bytes"), int)
            and 4096 <= binding_value["context_budget_bytes"] <= 8192
            else 8192
        ),
        "status": "review" if diagnostics else "declared",
        "sources": context_sources,
        "rights": {
            "distribution_license": expression[:256] if isinstance(expression, str) else None,
            "declaration_state": "declared" if isinstance(expression, str) else "unknown",
            "copyright_status": _bounded_label(rights.get("copyright_status"), "unresolved"),
            "rights_basis": _bounded_label(rights.get("rights_basis"), "unknown-needs-review"),
            "third_party_material": _bounded_label(rights.get("third_party_material"), "unknown"),
            "sources": source_summaries,
            "source_count": len(raw_sources),
            "sources_truncated": len(raw_sources) > 4,
            "license_terms": license_resolution,
            "license_terms_access": {
                "query_ref": "mncs-rp license-resolve",
            },
            "action_guidance": _action_guidance_context(
                expression, f"{manifest_ref}#/rights/distribution_license"
            ),
            "compatibility": {"status": "unknown", "reason": "no cross-artifact compatibility conclusion was established"},
        },
        "provenance": {
            "origin_classification": origin,
            "evidence_state": "declared-unverified",
            "participant_count": len(participants),
            "relationship_count": len(edges),
            "relationship_kinds": dict(sorted(
                Counter(
                    str(edge.get("relation", "unknown"))[:64]
                    for edge in edges if isinstance(edge, Mapping)
                ).items(),
                key=lambda item: (-item[1], item[0]),
            )[:16]),
            "detail_ref": f"{manifest_ref}#/provenance",
            "projection": {
                "schema_version": "mncs.rights-provenance.context-lineage/1",
                "output_ref": "#/identity",
                "relationships": context_lineage_relationships,
            },
        },
        "governance": {
            "status": "authorized" if governance_active else "unavailable",
            "profile_id": expected_profile if governance_active else None,
            "profile_version": clean_governance.get("profile_version") if governance_active and clean_governance else None,
            "authority": ({
                "issuer": authority_value.get("issuer"),
                "basis": authority_value.get("basis"),
                "source_ref": authority_value.get("source_ref"),
                "scope": clean_authority_scope,
            } if governance_active and isinstance(authority_value, Mapping) else None),
            "rules": ({
                "rights": clean_governance["rights"],
                "provenance": clean_governance["provenance"],
                "agent_governance": clean_governance["agent_governance"],
            } if governance_active and clean_governance else None),
            "detail_ref": governance_ref,
        },
        "diagnostics": diagnostics[:12],
    }
    if isinstance(expression, str) and len(expression) > 256:
        context["rights"]["distribution_license_truncated"] = True
    _fit_context(context, context["context_budget_bytes"])
    # Context identity deliberately binds policy authority, evidence digests,
    # and the compact projection, so edits invalidate admission context.
    context["identity"] = "sha256:" + hashlib.sha256(
        json.dumps(context, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return context
