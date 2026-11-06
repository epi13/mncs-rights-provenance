"""Bounded execution adapter for the native license action relation kernel.

This module owns only the host-to-MNCS value encoding and execution boundary.
The relationship classification itself is returned by the packaged MNCS
module; a missing or unusable runtime never falls back to a host rule table.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import threading
from importlib.resources import files
from pathlib import Path
from typing import Any

MODULE = "mncs.rights.license_actions.v01"
_SOURCE_NAME = "rights_license_actions.mncs"
_MAX_SOURCE_BYTES = 64 * 1024
_MAX_RESULT_BYTES = 256 * 1024
_TIMEOUT_SECONDS = 60
_MAX_RESULT_CACHE_ENTRIES = 4

_ACTION_VARIANTS = {
    "redistribute-source": ("Source", 0),
    "redistribute-binary": ("Binary", 1),
}
_CONDITION_VARIANTS = {
    "retain-copyright-and-permission-notice": ("RetainCopyNotice", 0),
    "retain-notice-conditions-and-disclaimer": ("RetainSourceNotice", 1),
    "reproduce-notice-conditions-and-disclaimer": ("ReproduceBinaryNotice", 2),
    "provide-license-copy": ("ProvideLicenseCopy", 3),
    "mark-modified-files": ("MarkModifiedFiles", 4),
    "preserve-applicable-source-notices": ("PreserveSourceNotices", 5),
    "preserve-notice-attributions": ("PreserveNoticeAttributions", 6),
    "no-endorsement-without-permission": ("NoEndorsement", 7),
    "do-not-misrepresent-origin": ("DoNotMisrepresentOrigin", 8),
    "mark-altered-source": ("MarkAlteredSource", 9),
    "preserve-zlib-source-notice": ("PreserveZlibSourceNotice", 10),
}
_RELATION_VARIANTS = {
    "OperationClassMatchesTrigger": (
        "operation-class-matches-trigger", 0,
    ),
    "OtherTriggerPreservedForReview": (
        "other-trigger-preserved-for-review", 1,
    ),
}
_ACTION_TYPE = f"mncs:0.2:finite-type:{MODULE}::RedistributionAction"
_CONDITION_TYPE = f"mncs:0.2:finite-type:{MODULE}::IndexedCondition"
_RELATION_TYPE = f"mncs:0.2:finite-type:{MODULE}::ActionRelation"

_CACHE_LOCK = threading.Lock()
_RESULT_CACHE: dict[
    tuple[Any, ...], tuple[dict[tuple[str, str], str] | None, str | None]
] = {}


class NativeActionRuntimeError(RuntimeError):
    """The selected MNCS runtime could not produce bounded relation results."""


def _remember_result(
    key: tuple[Any, ...],
    value: tuple[dict[tuple[str, str], str] | None, str | None],
) -> None:
    _RESULT_CACHE[key] = value
    while len(_RESULT_CACHE) > _MAX_RESULT_CACHE_ENTRIES:
        _RESULT_CACHE.pop(next(iter(_RESULT_CACHE)))


def _source_bytes() -> bytes:
    try:
        resource = files("mncs_rights_provenance").joinpath("resources", _SOURCE_NAME)
        content = resource.read_bytes()
    except (OSError, TypeError, ValueError):
        raise NativeActionRuntimeError("packaged MNCS action source is unavailable") from None
    if not content or len(content) > _MAX_SOURCE_BYTES:
        raise NativeActionRuntimeError("packaged MNCS action source is missing or oversized")
    if f"module {MODULE};".encode("ascii") not in content:
        raise NativeActionRuntimeError("packaged MNCS action source has the wrong module identity")
    return content


def native_action_contract_inputs() -> dict[str, Any]:
    """Return the source and finite-value bindings covered by the ruleset id."""
    content = _source_bytes()
    return {
        "module": MODULE,
        "source_sha256": "sha256:" + hashlib.sha256(content).hexdigest(),
        "actions": _ACTION_VARIANTS,
        "conditions": _CONDITION_VARIANTS,
        "relations": _RELATION_VARIANTS,
    }


def _selected_binary() -> tuple[Path, tuple[Any, ...]]:
    selected = os.environ.get("MNCS_BIN") or os.environ.get("MNCS")
    if not selected:
        raise NativeActionRuntimeError(
            "native MNCS runtime is unavailable; set MNCS_BIN or MNCS to its executable path"
        )
    candidate = Path(selected).expanduser()
    if not candidate.is_file() and candidate.parent == Path("."):
        located = shutil.which(selected)
        if located:
            candidate = Path(located)
    try:
        resolved = candidate.resolve(strict=True)
        info = resolved.stat()
    except (OSError, RuntimeError):
        raise NativeActionRuntimeError("selected MNCS runtime executable is unavailable") from None
    if not resolved.is_file() or not os.access(resolved, os.X_OK):
        raise NativeActionRuntimeError("selected MNCS runtime is not an executable file")
    identity = (
        str(resolved), info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
    )
    return resolved, identity


def _finite_value(type_identity: str, variant_name: str, discriminant: int) -> dict[str, Any]:
    return {
        "finite": {
            "type_identity": type_identity,
            "variant_identity": f"mncs:0.2:finite-variant:{MODULE}::{type_identity.rsplit('::', 1)[-1]}::{variant_name}",
            "discriminant": discriminant,
        }
    }


def _case_id(action_name: str, condition_name: str) -> str:
    def kebab(value: str) -> str:
        output: list[str] = []
        for index, char in enumerate(value):
            if char.isupper() and index:
                output.append("-")
            output.append(char.lower())
        return "".join(output)

    return f"{action_name.lower()}-{kebab(condition_name)}"


def _build_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for action_name, action_discriminant in _ACTION_VARIANTS.values():
        action_label = "source" if action_name == "Source" else "binary"
        for condition_name, condition_discriminant in _CONDITION_VARIANTS.values():
            cases.append({
                "id": _case_id(action_label, condition_name),
                "request": {
                    "schema_version": "0.1",
                    "target": {"module": MODULE, "function": "action_relation"},
                    "arguments": [
                        _finite_value(_ACTION_TYPE, action_name, action_discriminant),
                        _finite_value(_CONDITION_TYPE, condition_name, condition_discriminant),
                    ],
                    "step_budget": 256,
                },
            })
    return cases


def _run_all_relations(binary: Path, source: bytes) -> dict[tuple[str, str], str]:
    cases = _build_cases()
    expected_ids = {case["id"] for case in cases}
    with tempfile.TemporaryDirectory(prefix="mncs-rights-action-") as temporary:
        root = Path(temporary)
        source_path = root / _SOURCE_NAME
        corpus_path = root / "corpus.json"
        output_dir = root / "output"
        source_path.write_bytes(source)
        corpus_path.write_text(
            json.dumps({
                "schema_version": "0.1",
                "name": "rights-license-action-production-consumer",
                "cases": cases,
            }, separators=(",", ":")),
            encoding="utf-8",
        )
        try:
            process = subprocess.run(
                [
                    str(binary), "experiment", "run", str(source_path),
                    "--backend", "portable-wasm",
                    "--corpus", str(corpus_path),
                    "--output-dir", str(output_dir),
                ],
                cwd=root,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise NativeActionRuntimeError("native MNCS action execution exceeded its time limit") from None
        except OSError:
            raise NativeActionRuntimeError("native MNCS action execution could not start") from None
        if process.returncode != 0:
            raise NativeActionRuntimeError(
                f"native MNCS action execution exited with status {process.returncode}"
            )
        result_path = output_dir / "result.json"
        try:
            if result_path.stat().st_size > _MAX_RESULT_BYTES:
                raise NativeActionRuntimeError("native MNCS action result exceeded its size limit")
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except NativeActionRuntimeError:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError):
            raise NativeActionRuntimeError("native MNCS action result is unavailable or malformed") from None

    if not isinstance(result, dict) or result.get("status") != "PASS":
        raise NativeActionRuntimeError("native MNCS action corpus did not complete successfully")
    result_cases = result.get("cases")
    if not isinstance(result_cases, list) or len(result_cases) != len(expected_ids):
        raise NativeActionRuntimeError("native MNCS action corpus returned an incomplete result set")
    by_id: dict[str, dict[str, Any]] = {}
    for case in result_cases:
        if not isinstance(case, dict) or not isinstance(case.get("case_id"), str):
            raise NativeActionRuntimeError("native MNCS action corpus returned an invalid case")
        if case["case_id"] in by_id:
            raise NativeActionRuntimeError("native MNCS action corpus returned a duplicate case")
        by_id[case["case_id"]] = case
    if set(by_id) != expected_ids:
        raise NativeActionRuntimeError("native MNCS action corpus returned unexpected cases")

    relations: dict[tuple[str, str], str] = {}
    for action, (action_name, _) in _ACTION_VARIANTS.items():
        for condition_id, (condition_name, _) in _CONDITION_VARIANTS.items():
            case = by_id[_case_id("source" if action_name == "Source" else "binary", condition_name)]
            returned = case.get("returned")
            if case.get("status") != "returned" or not isinstance(returned, list) or len(returned) != 1:
                raise NativeActionRuntimeError("native MNCS action case did not return one finite value")
            value = returned[0]
            finite = value.get("finite") if isinstance(value, dict) else None
            if not isinstance(finite, dict) or finite.get("type_identity") != _RELATION_TYPE:
                raise NativeActionRuntimeError("native MNCS action case returned the wrong finite type")
            variant_identity = finite.get("variant_identity")
            relation_name = next((
                name for name in _RELATION_VARIANTS
                if variant_identity == f"mncs:0.2:finite-variant:{MODULE}::ActionRelation::{name}"
            ), None)
            if relation_name is None:
                raise NativeActionRuntimeError("native MNCS action case returned an unknown relation")
            expected_discriminant = _RELATION_VARIANTS[relation_name][1]
            if finite.get("discriminant") != expected_discriminant:
                raise NativeActionRuntimeError("native MNCS action relation identity is inconsistent")
            relations[(action, condition_id)] = _RELATION_VARIANTS[relation_name][0]
    return relations


def _cached_relations() -> dict[tuple[str, str], str]:
    source = _source_bytes()
    source_identity = hashlib.sha256(source).hexdigest()
    raw_selected = os.environ.get("MNCS_BIN") or os.environ.get("MNCS")
    try:
        binary, binary_identity = _selected_binary()
    except NativeActionRuntimeError as error:
        missing_runtime_key = (raw_selected, None, source_identity)
        with _CACHE_LOCK:
            cached = _RESULT_CACHE.get(missing_runtime_key)
            if cached is None:
                _remember_result(missing_runtime_key, (None, str(error)))
                cached = _RESULT_CACHE[missing_runtime_key]
        if cached[0] is None:
            raise NativeActionRuntimeError(cached[1] or str(error))
        return cached[0]

    runtime_key = (binary_identity, source_identity)
    with _CACHE_LOCK:
        cached = _RESULT_CACHE.get(runtime_key)
        if cached is None:
            try:
                _remember_result(runtime_key, (_run_all_relations(binary, source), None))
            except NativeActionRuntimeError as error:
                _remember_result(runtime_key, (None, str(error)))
            cached = _RESULT_CACHE[runtime_key]
    if cached[0] is None:
        raise NativeActionRuntimeError(cached[1] or "native MNCS action execution failed")
    return cached[0]


def classify_action_relation(action: str, condition_id: str) -> str:
    """Return the native relation string for one indexed condition and action."""
    if action not in _ACTION_VARIANTS or condition_id not in _CONDITION_VARIANTS:
        raise NativeActionRuntimeError("action or condition has no MNCS finite-value binding")
    return _cached_relations()[(action, condition_id)]
