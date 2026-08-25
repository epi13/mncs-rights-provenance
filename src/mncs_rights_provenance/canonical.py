"""RFC 8785-compatible canonical JSON for the MNCS value profile.

Mirrors ``mncs_fabric.receipts._mncs_jcs`` so digests agree across the family.
Keys are ASCII in practice; numbers used by this subsystem are integers or
finite bounded values produced by adapters.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any


def canonical_bytes(value: Any) -> bytes:
    if value is None:
        return b"null"
    if value is True:
        return b"true"
    if value is False:
        return b"false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value).encode("ascii")
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite number is not canonically serializable")
        if value == 0:
            return b"0"
        if value.is_integer():
            return str(int(value)).encode("ascii")
        text = repr(value).lower()
        if "e" in text:
            mantissa, exponent = text.split("e")
            sign = "+" if not exponent.startswith("-") else "-"
            exponent = exponent.lstrip("+-0") or "0"
            text = mantissa + "e" + sign + exponent
        return text.encode("ascii")
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if isinstance(value, (list, tuple)):
        return b"[" + b",".join(canonical_bytes(item) for item in value) + b"]"
    if isinstance(value, dict):
        items = sorted(value.items(), key=lambda item: str(item[0]).encode("utf-16-be"))
        return (
            b"{"
            + b",".join(
                canonical_bytes(str(key)) + b":" + canonical_bytes(item) for key, item in items
            )
            + b"}"
        )
    raise TypeError(f"unsupported canonical JSON value: {type(value).__name__}")


def sha256_hex(value: Any) -> str:
    """SHA-256 hex digest over the canonical encoding of *value*."""
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def digest_prefixed(value: Any) -> str:
    return "sha256:" + sha256_hex(value)
