#!/usr/bin/env bash
# CI provider: project test suite -> mncs.check-result/1.
#
# Runs the repository's own pytest suite and records the outcome as a
# check-result. The verdict carries the signal (PASS/FAIL); this script
# exits 0 whenever the suite ran to a decision so aggregation can decide
# the declared boundary. It exits nonzero only when the suite could not
# run at all (no claim established).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT="${CHECK_OUTPUT:-.mncs/project-check.json}"
# Overridable for tests; CI default runs the full suite.
TEST_ARGS="${PROJECT_TEST_ARGS:-tests -q}"

cd "$ROOT"
mkdir -p "$(dirname "$OUTPUT")"

set +e
# shellcheck disable=SC2086
SUMMARY="$(python3 -m pytest $TEST_ARGS 2>&1)"
PYTEST_STATUS=$?
set -e

if [[ "$PYTEST_STATUS" -eq 0 ]]; then
  VERDICT="PASS"
else
  VERDICT="FAIL"
fi

TAIL="$(printf '%s' "$SUMMARY" | tail -n 5 | tr '\n' ';' | cut -c1-500)"

python3 - "$OUTPUT" "$VERDICT" "$PYTEST_STATUS" "$TAIL" <<'PY'
import json
import sys

output, verdict, status, tail = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
check = {
    "schema_version": "mncs.check-result/1",
    "id": "project-tests",
    "provider": "project-verifier",
    "verdict": verdict,
    "summary": f"pytest exit={status}: {tail}",
}
if verdict != "PASS":
    check["unresolved"] = [f"project suite exit={status}: {tail}"]
with open(output, "w", encoding="utf-8") as handle:
    json.dump(check, handle, indent=2, sort_keys=True)
    handle.write("\n")
print(f"project-tests -> {verdict} ({output})")
PY
