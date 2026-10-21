#!/usr/bin/env python3
"""Generate the executable and host-reference corpus for redistribution action rules."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = "mncs.rights.license_actions.v01"
PROGRAM = ROOT / "language" / "rights_license_actions.mncs"
CORPUS_PATH = ROOT / "language" / "corpora" / "license-action-guidance-corpus.json"
GOLDEN_PATH = ROOT / "conformance" / "license-action-guidance-golden-vectors.json"

ACTIONS = ("Source", "Binary")
CONDITIONS = (
    "RetainCopyNotice",
    "RetainSourceNotice",
    "ReproduceBinaryNotice",
    "ProvideLicenseCopy",
    "MarkModifiedFiles",
    "PreserveSourceNotices",
    "PreserveNoticeAttributions",
    "NoEndorsement",
)
RELATIONS = ("OperationClassMatchesTrigger", "OtherTriggerPreservedForReview")


def finite(type_name: str, variant: str, variants: tuple[str, ...]) -> dict:
    type_identity = f"mncs:0.2:finite-type:{MODULE}::{type_name}"
    return {
        "finite": {
            "type_identity": type_identity,
            "variant_identity": (
                f"mncs:0.2:finite-variant:{MODULE}::{type_name}::{variant}"
            ),
            "discriminant": variants.index(variant),
        }
    }


def request(action: str, condition: str) -> dict:
    return {
        "schema_version": "0.1",
        "target": {"module": MODULE, "function": "action_relation"},
        "arguments": [
            finite("RedistributionAction", action, ACTIONS),
            finite("IndexedCondition", condition, CONDITIONS),
        ],
        "step_budget": 256,
    }


def expected(action: str, condition: str) -> str:
    if condition == "NoEndorsement":
        return "OtherTriggerPreservedForReview"
    if condition in {"RetainSourceNotice", "PreserveSourceNotices"}:
        return (
            "OperationClassMatchesTrigger"
            if action == "Source"
            else "OtherTriggerPreservedForReview"
        )
    if condition == "ReproduceBinaryNotice":
        return (
            "OtherTriggerPreservedForReview"
            if action == "Source"
            else "OperationClassMatchesTrigger"
        )
    return "OperationClassMatchesTrigger"


def kebab_case(value: str) -> str:
    return "".join(
        ("-" if index and char.isupper() else "") + char.lower()
        for index, char in enumerate(value)
    )


def build() -> tuple[list[dict], list[dict]]:
    corpus: list[dict] = []
    golden: list[dict] = []
    for action in ACTIONS:
        for condition in CONDITIONS:
            result = expected(action, condition)
            case_id = f"{action.lower()}-{kebab_case(condition)}"
            corpus.append({
                "id": case_id,
                "request": request(action, condition),
                "expected": [finite("ActionRelation", result, RELATIONS)],
            })
            golden.append({
                "function": "action_relation",
                "inputs": {"action": action, "condition": condition},
                "output": result,
            })
    return corpus, golden


def main() -> None:
    corpus, golden = build()
    CORPUS_PATH.write_text(json.dumps({
        "schema_version": "0.1",
        "name": "license-action-guidance-v1",
        "cases": corpus,
    }, indent=1) + "\n", encoding="utf-8")
    GOLDEN_PATH.write_text(json.dumps({
        "schema_version": "0.1",
        "source_module": MODULE,
        "description": (
            "Executable finite rules for relating indexed notice conditions "
            "to source or binary redistribution action classes."
        ),
        "cases": golden,
    }, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {len(corpus)} action cases and {len(golden)} host vectors")


if __name__ == "__main__":
    main()
