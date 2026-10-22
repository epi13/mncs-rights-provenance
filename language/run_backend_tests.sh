#!/usr/bin/env bash
# Run the rights-policy and distributed-pressure MNCS-language cores across
# available compiler backends and verify cross-backend agreement.
#
# Backend coverage notes (recorded 2026-08, updated 2026-09):
# - research-bytecode: full corpora (evaluate + gate_severities + lattice +
#   pressure verdicts).
# - portable-wasm:     evaluate + lattice + pressure-verdict corpora. The
#   gate-severities corpus is excluded because the WASM realization currently
#   returns "unresolved" type identities for enum-typed fields inside
#   returned records. See docs/language-findings.md finding LF-1.
#   The pressure core deliberately returns bare Verdict enums (never
#   records-of-enums) so its full corpus runs on both backends with agreement.
# - c11/llvm-ir/cranelift: refuse records/payload sums at HEAD (scalar
#   realization envelope); excluded until that expansion lands.
# - rights-claims corpus runs on research-bytecode AND portable-wasm
#   with agreement: its entry functions return bare enums/u64 (never
#   records-of-enums), dodging finding LF-1 by construction.
# - license-action-guidance corpus runs on research-bytecode AND portable-wasm
#   and compares the finite source/binary condition classifications.
# - agent-governance corpus pins every supported profile pair plus one known
#   mismatch per field; its bounded portable-WASM budget covers the exhaustive
#   finite-vocabulary match without changing the legal-rights boundary.
# - implementation-lineage corpus pins evidence-aware representation/origin
#   and aggregate status on both supported backends; it does not infer legal
#   independence, ownership, or completeness.
# - source-license status corpus distinguishes unverified declarations from
#   verified assessments on both supported backends.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MNCS="${MNCS_BIN:-mncs}"
OUT="${TMPDIR:-/tmp}/mncs-rp-backends"
mkdir -p "$OUT"

run() { # program backend corpus outdir
  local program="$1" backend="$2" corpus="$3" outdir="$4"
  echo "== $backend / $(basename "$corpus")"
  "$MNCS" experiment run "$program" \
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
    if ! run "$ROOT/language/rights_policy.mncs" "$backend" "$ROOT/language/corpora/$corpus" "$OUT/$backend"; then STATUS=1; fi
  done
  if ! run "$ROOT/language/pressure_provenance.mncs" "$backend" "$ROOT/language/corpora/pressure-verdict-corpus.json" "$OUT/$backend-pressure"; then STATUS=1; fi
  if ! run "$ROOT/language/rights_claims.mncs" "$backend" "$ROOT/language/corpora/claims-corpus.json" "$OUT/$backend-claims"; then STATUS=1; fi
  if ! run "$ROOT/language/rights_license_actions.mncs" "$backend" "$ROOT/language/corpora/license-action-guidance-corpus.json" "$OUT/$backend-license-actions"; then STATUS=1; fi
  if ! run "$ROOT/language/rights_agent_governance.mncs" "$backend" "$ROOT/language/corpora/agent-governance-corpus.json" "$OUT/$backend-agent-governance"; then STATUS=1; fi
  if ! run "$ROOT/language/implementation_lineage.mncs" "$backend" "$ROOT/language/corpora/implementation-lineage-corpus.json" "$OUT/$backend-implementation-lineage"; then STATUS=1; fi
  if ! run "$ROOT/language/manifest_reference_consistency.mncs" "$backend" "$ROOT/language/corpora/manifest-reference-consistency-corpus.json" "$OUT/$backend-manifest-reference-consistency"; then STATUS=1; fi
  if ! run "$ROOT/language/source_license_status.mncs" "$backend" "$ROOT/language/corpora/source-license-status-corpus.json" "$OUT/$backend-source-license-status"; then STATUS=1; fi
  if [ "$backend" = "research-bytecode" ]; then
    if ! run "$ROOT/language/rights_policy.mncs" "$backend" "$ROOT/language/corpora/gate-severities-corpus.json" "$OUT/$backend"; then STATUS=1; fi
  fi
done

echo "== cross-backend compare (source-license status evidence)"
python3 - <<PY || STATUS=1
import json
OUT = "$OUT"
rb = json.load(open(f"{OUT}/research-bytecode-source-license-status/result.json"))
pw = json.load(open(f"{OUT}/portable-wasm-source-license-status/result.json"))
def outcomes(result):
    return {c["case_id"]: json.dumps(c.get("returned"), sort_keys=True) for c in result["cases"]}
left, right = outcomes(rb), outcomes(pw)
mismatch = [k for k in left if left[k] != right.get(k)]
print("   source-status agreement:", f"{len(left)-len(mismatch)}/{len(left)}")
if mismatch:
    print("   MISMATCH:", mismatch)
    raise SystemExit(1)
PY

echo "== cross-backend compare (evaluation corpus)"
"$MNCS" experiment compare \
  "$OUT/research-bytecode/result.json" \
  "$OUT/portable-wasm/result.json" >/dev/null 2>&1 || {
    # compare expects same corpus; evaluation corpus ran on both, so compare directly
    python3 - <<PY || STATUS=1
import json
OUT = "$OUT"
rb = json.load(open(f"{OUT}/research-bytecode/result.json"))
pw = json.load(open(f"{OUT}/portable-wasm/result.json"))
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

echo "== cross-backend compare (pressure verdicts)"
python3 - <<PY || STATUS=1
import json, glob
OUT = "$OUT"
rb = json.load(open(f"{OUT}/research-bytecode-pressure/result.json"))
pw = json.load(open(f"{OUT}/portable-wasm-pressure/result.json"))
def outcomes(result):
    return {c["case_id"]: json.dumps(c.get("returned"), sort_keys=True) for c in result["cases"]}
left, right = outcomes(rb), outcomes(pw)
mismatch = [k for k in left if left[k] != right.get(k)]
print("   pressure agreement:", f"{len(left)-len(mismatch)}/{len(left)}")
if mismatch:
    print("   MISMATCH:", mismatch)
    raise SystemExit(1)
PY

echo "== cross-backend compare (rights claims)"
python3 - <<PY || STATUS=1
import json
OUT = "$OUT"
rb = json.load(open(f"{OUT}/research-bytecode-claims/result.json"))
pw = json.load(open(f"{OUT}/portable-wasm-claims/result.json"))
def outcomes(result):
    return {c["case_id"]: json.dumps(c.get("returned"), sort_keys=True) for c in result["cases"]}
left, right = outcomes(rb), outcomes(pw)
mismatch = [k for k in left if left[k] != right.get(k)]
print("   claims agreement:", f"{len(left)-len(mismatch)}/{len(left)}")
if mismatch:
    print("   MISMATCH:", mismatch)
    raise SystemExit(1)
PY

echo "== cross-backend compare (license action guidance)"
python3 - <<PY || STATUS=1
import json
OUT = "$OUT"
rb = json.load(open(f"{OUT}/research-bytecode-license-actions/result.json"))
pw = json.load(open(f"{OUT}/portable-wasm-license-actions/result.json"))
def outcomes(result):
    return {c["case_id"]: json.dumps(c.get("returned"), sort_keys=True) for c in result["cases"]}
left, right = outcomes(rb), outcomes(pw)
mismatch = [k for k in left if left[k] != right.get(k)]
print("   action classification agreement:", f"{len(left)-len(mismatch)}/{len(left)}")
if mismatch:
    print("   MISMATCH:", mismatch)
    raise SystemExit(1)
PY

echo "== cross-backend compare (agent governance)"
python3 - <<PY || STATUS=1
import json
OUT = "$OUT"
rb = json.load(open(f"{OUT}/research-bytecode-agent-governance/result.json"))
pw = json.load(open(f"{OUT}/portable-wasm-agent-governance/result.json"))
def outcomes(result):
    return {c["case_id"]: json.dumps(c.get("returned"), sort_keys=True) for c in result["cases"]}
left, right = outcomes(rb), outcomes(pw)
mismatch = [k for k in left if left[k] != right.get(k)]
print("   governance agreement:", f"{len(left)-len(mismatch)}/{len(left)}")
if mismatch:
    print("   MISMATCH:", mismatch)
    raise SystemExit(1)
PY

echo "== cross-backend compare (implementation lineage)"
python3 - <<PY || STATUS=1
import json
OUT = "$OUT"
rb = json.load(open(f"{OUT}/research-bytecode-implementation-lineage/result.json"))
pw = json.load(open(f"{OUT}/portable-wasm-implementation-lineage/result.json"))
def outcomes(result):
    return {c["case_id"]: json.dumps(c.get("returned"), sort_keys=True) for c in result["cases"]}
left, right = outcomes(rb), outcomes(pw)
mismatch = [k for k in left if left[k] != right.get(k)]
print("   implementation-lineage agreement:", f"{len(left)-len(mismatch)}/{len(left)}")
if mismatch:
    print("   MISMATCH:", mismatch)
    raise SystemExit(1)
PY

echo "== cross-backend compare (manifest reference consistency)"
python3 - <<PY || STATUS=1
import json
OUT = "$OUT"
rb = json.load(open(f"{OUT}/research-bytecode-manifest-reference-consistency/result.json"))
pw = json.load(open(f"{OUT}/portable-wasm-manifest-reference-consistency/result.json"))
def outcomes(result):
    return {c["case_id"]: json.dumps(c.get("returned"), sort_keys=True) for c in result["cases"]}
left, right = outcomes(rb), outcomes(pw)
mismatch = [k for k in left if left[k] != right.get(k)]
print("   manifest consistency agreement:", f"{len(left)-len(mismatch)}/{len(left)}")
if mismatch:
    print("   MISMATCH:", mismatch)
    raise SystemExit(1)
PY

exit $STATUS
