"""Host mirror of the normative manifest-reference consistency core."""

from __future__ import annotations


def repeated_reference_metadata_conflict(
    same_reference: int,
    same_manifest_digest: int,
    same_manifest_identity: int,
    same_evidence_state: int,
    same_rights_state: int,
    same_license_expression_ref: int,
    same_obligations_ref: int,
) -> int:
    """Return 0 for consistent, 1 for inconsistent, or 2 for invalid flags."""
    values = (
        same_reference,
        same_manifest_digest,
        same_manifest_identity,
        same_evidence_state,
        same_rights_state,
        same_license_expression_ref,
        same_obligations_ref,
    )
    if any(type(value) is not int or value < 0 for value in values):
        raise ValueError("comparison flags must be non-negative integers")
    if any(value > 1 for value in values):
        return 2
    if same_reference == 0:
        return 0
    return int(any(value == 0 for value in values[1:]))


def compatibility_review_required(distinct_declaration_count: int) -> int:
    """Return 1 only when more than one distinct declaration is present."""
    if (
        type(distinct_declaration_count) is not int
        or not 0 <= distinct_declaration_count < 2**64
    ):
        raise ValueError("distinct declaration count must be a u64 integer")
    return int(distinct_declaration_count > 1)
