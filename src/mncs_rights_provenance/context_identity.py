"""Versioned non-file dependencies for Rights agent-context cache keys."""

from __future__ import annotations

from .agent_context import CONTEXT_SCHEMA
from .license_resolution import (
    license_action_ruleset_identity,
    license_resolver_identity,
)

CONTEXT_SOURCE_IDENTITIES_SCHEMA = "mncs.rights-provenance.context-source-identities/1"


def agent_context_source_identities() -> dict[str, str]:
    """Return every non-file identity that can change an agent-context projection.

    Environment consumers also key on the authorized binding and the exact
    manifest and governance content digests. This contract groups the
    projection schema, license resolver, and native action ruleset so a cache
    check cannot accidentally omit one of those provider dependencies.
    """
    return {
        "schema_version": CONTEXT_SOURCE_IDENTITIES_SCHEMA,
        "context_schema": CONTEXT_SCHEMA,
        "license_resolver": license_resolver_identity(),
        "license_action_ruleset": license_action_ruleset_identity()["identity"],
    }
