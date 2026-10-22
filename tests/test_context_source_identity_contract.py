"""Versioned cache dependencies exposed by the Rights context provider."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

import mncs_rights_provenance.agent_context as agent_context_module
import mncs_rights_provenance.context_identity as context_identity_module
from mncs_rights_provenance import (
    agent_context_source_identities as package_source_identities,
)
from mncs_rights_provenance.agent_context import build_agent_context
from mncs_rights_provenance.context_identity import agent_context_source_identities

ROOT = Path(__file__).resolve().parents[1]


def test_source_identity_contract_matches_projection_and_schema() -> None:
    schema = json.loads((ROOT / "schemas/v0.1/context-source-identities.schema.json").read_text())
    Draft202012Validator.check_schema(schema)

    identities = agent_context_source_identities()
    assert package_source_identities is agent_context_source_identities
    assert list(Draft202012Validator(schema).iter_errors(identities)) == []

    manifest = json.loads((ROOT / "RIGHTS.json").read_text())
    governance = json.loads((ROOT / "governance/agent-governance.json").read_text())
    context = build_agent_context(
        manifest,
        governance,
        binding={"authorized": True, "profile_id": "test-profile"},
    )

    assert identities["context_schema"] == context["schema_version"]
    assert identities["license_resolver"] == context["sources"]["license_resolver"]["sha256"]
    assert (
        identities["license_action_ruleset"]
        == context["sources"]["license_action_ruleset"]["sha256"]
    )


def test_source_identity_contract_changes_with_each_projection_dependency(monkeypatch) -> None:
    original = agent_context_source_identities()

    monkeypatch.setattr(
        context_identity_module,
        "license_resolver_identity",
        lambda: "sha256:" + "a" * 64,
    )
    monkeypatch.setattr(
        context_identity_module,
        "license_action_ruleset_identity",
        lambda: {"identity": "sha256:" + "b" * 64},
    )
    revised = agent_context_source_identities()

    assert original["schema_version"] == revised["schema_version"]
    assert original["context_schema"] == revised["context_schema"]
    assert original["license_resolver"] != revised["license_resolver"]
    assert original["license_action_ruleset"] != revised["license_action_ruleset"]


def test_context_identity_binds_non_file_projection_dependencies(monkeypatch) -> None:
    manifest = json.loads((ROOT / "RIGHTS.json").read_text())
    governance = json.loads((ROOT / "governance/agent-governance.json").read_text())
    binding = {"authorized": True, "profile_id": "test-profile"}
    resolver_identity = agent_context_module.license_resolver_identity
    action_identity = agent_context_module.license_action_ruleset_identity
    baseline = build_agent_context(manifest, governance, binding=binding)

    changed_resolver = "sha256:" + "c" * 64
    monkeypatch.setattr(
        agent_context_module,
        "license_resolver_identity",
        lambda: changed_resolver,
    )
    resolver_context = build_agent_context(manifest, governance, binding=binding)
    assert resolver_context["identity"] != baseline["identity"]
    assert resolver_context["sources"]["license_resolver"]["sha256"] == changed_resolver
    resolver_edge = next(
        item for item in resolver_context["provenance"]["projection"]["relationships"]
        if item["from"] == resolver_context["sources"]["license_resolver"]["reference"]
    )
    assert resolver_edge["content_digest"] == changed_resolver

    monkeypatch.setattr(agent_context_module, "license_resolver_identity", resolver_identity)
    original_ruleset = action_identity()
    changed_ruleset_identity = "sha256:" + "d" * 64
    monkeypatch.setattr(
        agent_context_module,
        "license_action_ruleset_identity",
        lambda: {**original_ruleset, "identity": changed_ruleset_identity},
    )
    ruleset_context = build_agent_context(manifest, governance, binding=binding)
    assert ruleset_context["identity"] != baseline["identity"]
    assert (
        ruleset_context["sources"]["license_action_ruleset"]["sha256"]
        == changed_ruleset_identity
    )
    ruleset_edge = next(
        item for item in ruleset_context["provenance"]["projection"]["relationships"]
        if item["from"] == ruleset_context["sources"]["license_action_ruleset"]["reference"]
    )
    assert ruleset_edge["content_digest"] == changed_ruleset_identity


def test_context_identity_binds_context_schema_version(monkeypatch) -> None:
    manifest = json.loads((ROOT / "RIGHTS.json").read_text())
    governance = json.loads((ROOT / "governance/agent-governance.json").read_text())
    binding = {"authorized": True, "profile_id": "test-profile"}
    baseline = build_agent_context(manifest, governance, binding=binding)

    changed_schema = "mncs.rights-provenance.agent-context/2"
    monkeypatch.setattr(agent_context_module, "CONTEXT_SCHEMA", changed_schema)
    monkeypatch.setattr(context_identity_module, "CONTEXT_SCHEMA", changed_schema)
    revised = build_agent_context(manifest, governance, binding=binding)

    assert revised["schema_version"] == changed_schema
    assert revised["identity"] != baseline["identity"]
    assert agent_context_source_identities()["context_schema"] == changed_schema
