#!/usr/bin/env bash
# CI provider: native rights/provenance evaluation -> mncs.check-result/1.
#
# Runs `mncs-rp validate` over the repository's own dogfood manifest and
# projects the native report (preserved verbatim) into the shared boundary
# contract with scripts/rp_to_check.py. The verdict carries the signal;
# this script exits 0 whenever a check was established so aggregation can
# decide the declared boundary. It exits nonzero only when no claim could
# be established (missing/malformed report), letting run-check record
# NOT_ESTABLISHED instead of fabricating a verdict.
#
# Manifest choice: dogfood/human-specification.json is a real manifest
# over real repository content. It honestly evaluates to review-required
# (human review outstanding) -> UNKNOWN, which the family boundary
# records visibly without fabricating PASS. See
# docs/mncs-actions-integration.md.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="${RIGHTS_MANIFEST:-dogfood/human-specification.json}"
OUTPUT="${CHECK_OUTPUT:-.mncs/rights-check.json}"
REPORT="$(mktemp)"
trap 'rm -f "$REPORT"' EXIT

cd "$ROOT"
mkdir -p "$(dirname "$OUTPUT")"

# mncs-rp exit codes distinguish outcomes (pass=0, findings/review=4,
# blocked=3, invalid=1); all of them still emit a JSON report. Only a
# missing/unreadable report is an execution failure.
set +e
mncs-rp validate "$MANIFEST" --findings-are-not-failures >"$REPORT" 2>"$REPORT.stderr"
RP_STATUS=$?
set -e
if [[ ! -s "$REPORT" ]]; then
  echo "error: mncs-rp produced no report (exit $RP_STATUS):" >&2
  cat "$REPORT.stderr" >&2 || true
  exit 2
fi

python3 scripts/rp_to_check.py \
  --input "$REPORT" \
  --output "$OUTPUT" \
  --check-id rights-provenance \
  --provider mncs-rights-provenance \
  --scope repository \
  --contract-revision 0.3.0 \
  --manifest-path "$MANIFEST"
