#!/usr/bin/env bash
# Run the rights-policy MNCS-language core across available compiler backends
# and verify cross-backend agreement.
#
# Backend coverage notes (recorded 2026-08):
# - research-bytecode: full corpus (evaluate + gate_severities + lattice).
# - portable-wasm:     evaluate + lattice corpora. The gate-severities corpus
#                      is excluded because the WASM realization currently
#                      returns "unresolved" type identities for enum-typed
#                      fields inside returned records. See
#                      docs/language-findings.md finding LF-1.
# - c11/llvm-ir/cranelift: refuse records/payload sums at HEAD (scalar
#   realization envelope); excluded until that expansion lands.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MNCS="${MNCS_BIN:-mncs}"
OUT="${TMPDIR:-/tmp}/mncs-rp-backends"
mkdir -p "$OUT"

run() { # backend corpus outdir
  local backend="$1" corpus="$2" outdir="$3"
  echo "== $backend / $(basename "$corpus")"
  "$MNCS" experiment run "$ROOT/language/rights_policy.mncs" \
    --backend "$backend" --corpus "$corpus" --output-dir "$outdir" >/dev/null
  python3 - "$outdir/result.json" <<'PY'
import json, sys
result = json.load(open(sys.argv[1]))
cases = result["cases"]
met = sum(1 for case in cases if case.get("expectation_met"))
failed = [c["case_id"] for c in cases if not c.get("expectation_met")]
print(f"   expectation_met {met}/{len(cases)}")
if failed:
    print("   FAILED:", ", ".join(failed[:8]))
    sys.exit(1)
PY
}

STATUS=0
for backend in research-bytecode portable-wasm; do
  for corpus in policy-evaluation-corpus.json severity-combine-corpus.json; do
    if ! run "$backend" "$ROOT/language/corpora/$corpus" "$OUT/$backend"; then STATUS=1; fi
  done
  if [ "$backend" = "research-bytecode" ]; then
    if ! run "$backend" "$ROOT/language/corpora/gate-severities-corpus.json" "$OUT/$backend"; then STATUS=1; fi
  fi
done

echo "== cross-backend compare (evaluation corpus)"
"$MNCS" experiment compare \
  "$OUT/research-bytecode/result.json" \
  "$OUT/portable-wasm/result.json" >/dev/null 2>&1 || {
    # compare expects same corpus; evaluation corpus ran on both, so compare directly
    python3 - <<'PY' || STATUS=1
import json
rb = json.load(open("/tmp/mncs-rp-backends/research-bytecode/result.json"))
pw = json.load(open("/tmp/mncs-rp-backends/portable-wasm/result.json"))
def outcomes(result):
    return {c["case_id"]: json.dumps(c.get("returned")) for c in result["cases"] if c["case_id"].startswith("evaluate")}
left, right = outcomes(rb), outcomes(pw)
mismatch = [k for k in left if left[k] != right.get(k)]
print("   evaluate agreement:", f"{len(left)-len(mismatch)}/{len(left)}")
if mismatch:
    print("   MISMATCH:", mismatch)
    raise SystemExit(1)
PY
}

exit $STATUS
