#!/usr/bin/env python3
"""Project a native ``mncs-rp validate`` report into ``mncs.check-result/1``.

Thin CLI over :mod:`mncs_rights_provenance.check_projection` for CI
provider commands. Owns no policy; the projection table lives in the
library module. Exits 2 emitting nothing when the report establishes no
claim (caller records NOT_ESTABLISHED instead of fabricating a verdict).

Usage:
    rp_to_check.py --input rp-report.json --output check-result.json
        [--check-id rights-provenance] [--provider mncs-rights-provenance]
        [--scope ...] [--contract-revision ...] [--producer-revision ...]
        [--manifest-path RIGHTS.json] [--manifest-digest HEX]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mncs_rights_provenance.check_projection import project_report_to_check


def main() -> int:
    parser = argparse.ArgumentParser(description="Project mncs-rp report to check-result.")
    parser.add_argument("--input", required=True, help="mncs-rp validate JSON report")
    parser.add_argument("--output", required=True, help="check-result/1 output path")
    parser.add_argument("--check-id", default="rights-provenance")
    parser.add_argument("--provider", default="mncs-rights-provenance")
    parser.add_argument("--scope", default="")
    parser.add_argument("--claim", default="")
    parser.add_argument("--contract-revision", default="")
    parser.add_argument("--producer-revision", default="")
    parser.add_argument("--manifest-path", default="")
    parser.add_argument("--manifest-digest", default="")
    args = parser.parse_args()

    try:
        report = json.loads(Path(args.input).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"error: cannot read rights report: {exc}", file=sys.stderr)
        return 2

    check, error = project_report_to_check(
        report,
        check_id=args.check_id,
        provider=args.provider,
        scope=args.scope,
        claim=args.claim,
        contract_revision=args.contract_revision,
        producer_revision=args.producer_revision,
        manifest_path=args.manifest_path,
        manifest_digest=args.manifest_digest,
    )
    if error is not None or check is None:
        print(f"error: {error}", file=sys.stderr)
        return 2
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(check, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"rights {report.get('outcome')!r} -> {check['verdict']} ({args.output})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
