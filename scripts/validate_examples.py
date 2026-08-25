#!/usr/bin/env python3
"""Validate the MNCS rights manifest schema and all JSON examples."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "mncs-rights-manifest.schema.json"
EXAMPLES_DIR = ROOT / "examples"


def load_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)

    failures = 0
    example_paths = sorted(EXAMPLES_DIR.glob("*.json"))
    if not example_paths:
        print("ERROR: no examples found", file=sys.stderr)
        return 1

    for path in example_paths:
        instance = load_json(path)
        errors = sorted(validator.iter_errors(instance), key=lambda err: list(err.path))
        if errors:
            failures += 1
            print(f"FAIL {path.relative_to(ROOT)}")
            for error in errors:
                location = ".".join(str(part) for part in error.path) or "<root>"
                print(f"  {location}: {error.message}")
        else:
            print(f"PASS {path.relative_to(ROOT)}")

    if failures:
        print(f"\n{failures} example(s) failed validation.", file=sys.stderr)
        return 1

    print(f"\nValidated schema and {len(example_paths)} example manifest(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
