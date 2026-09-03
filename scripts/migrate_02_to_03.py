#!/usr/bin/env python3
"""Mechanical v0.2 -> v0.3 manifest migration.

Bumps ``schema_version`` without inventing provenance, authority, or lineage.
The optional ``lineage`` block stays absent until real evidence populates it.

Usage:
    python3 scripts/migrate_02_to_03.py <manifest.json> [--in-place]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mncs_rights_provenance.lineage import migrate_manifest_02_to_03
from mncs_rights_provenance.validation import validate_manifest_structure


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Migrate a v0.2 manifest to v0.3")
    parser.add_argument("manifest")
    parser.add_argument("--in-place", action="store_true")
    args = parser.parse_args(argv)
    document = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    try:
        upgraded = migrate_manifest_02_to_03(document)
    except ValueError as exc:
        print(f"cannot migrate: {exc}", file=sys.stderr)
        return 2
    issues = validate_manifest_structure(upgraded)
    if issues:
        print(f"migrated document has structural issues: {issues}", file=sys.stderr)
        return 1
    if args.in_place:
        Path(args.manifest).write_text(json.dumps(upgraded, indent=2, sort_keys=True) + "\n")
    else:
        json.dump(upgraded, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
