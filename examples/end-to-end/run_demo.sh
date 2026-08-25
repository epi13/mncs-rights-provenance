#!/usr/bin/env bash
# End-to-end MNCS Rights & Provenance demonstration.
#
# Fabric executes a real bounded job -> emits process evidence -> Forge scans
# license declarations -> the rights manifest binds both evidence records into
# one provenance graph -> the independent Rust validator evaluates release
# policy -> Commons retains the finding -> SPDX is exported.
#
# Each stage uses the real subsystem CLIs/APIs. Missing optional components are
# skipped with an explicit marker rather than faked. Set KEEP_WORK=1 to inspect.
set -uo pipefail

DEMO_ROOT="$(cd "$(dirname "$0")" && pwd)"
RP_SRC="$(cd "$DEMO_ROOT/../../src" && pwd)"
PROJECTS_DIR="$(cd "$DEMO_ROOT/../../.." && pwd)"

WORK="$(mktemp -d /tmp/mncs-rp-e2e.XXXXXX)"
cleanup() { [ "${KEEP_WORK:-0}" = "1" ] && echo "kept: $WORK" || rm -rf "$WORK"; }
trap cleanup EXIT

note() { printf '%s\n' "$*"; }

note "== 0. workspace: $WORK"

# ---------------------------------------------------------------- Fabric ----
FABRIC_STAGE=0
if python3 -c "import mncs_fabric" >/dev/null 2>&1; then
  mkdir -p "$WORK/bundle" "$WORK/job" "$WORK/evidence" "$WORK/fabric"
  cat > "$WORK/bundle/task.py" <<'PY'
import json, hashlib, pathlib
payload = {"greeting": "hello from a bounded fabric job", "n": 42}
out = pathlib.Path("result.json")
out.write_text(json.dumps(payload, sort_keys=True))
print(hashlib.sha256(out.read_bytes()).hexdigest())
PY
  cat > "$WORK/fill_identities.py" <<PY
import json, pathlib, sys
from mncs_fabric.artifacts import build_manifest
bundle = pathlib.Path(sys.argv[1])
job_dir = pathlib.Path(sys.argv[2])
manifest = build_manifest(bundle)
plan_path = job_dir / "job-plan.json"
plan = json.loads(plan_path.read_text())
identity = manifest["manifest_identity"]
if not identity.startswith("sha256:"):
    identity = "sha256:" + identity
plan["artifact_manifest_identity"] = identity
plan["candidate_identity"] = identity
(job_dir / "artifact-manifest.json").write_text(json.dumps(manifest, indent=1))
plan_path.write_text(json.dumps(plan, indent=1))
PY
  cat > "$WORK/job/job-plan.json" <<'JSON'
{
  "schema_version": "mncs-fabric.job-plan.v0.1",
  "job_id": "demo:rights-provenance:e2e",
  "candidate_identity": null,
  "evaluator_identity": null,
  "artifact_manifest_identity": null,
  "argv": ["@python", "task.py"],
  "environment": {},
  "network_policy": "DECLARED_OFFLINE",
  "required_capabilities": ["python"],
  "timeout_seconds": 10,
  "output_limit_bytes": 65536,
  "working_directory": ".",
  "result_paths": ["result.json"]
}
JSON
  if python3 "$WORK/fill_identities.py" "$WORK/bundle" "$WORK/job" \
      && python3 -m mncs_fabric.cli run local "$WORK/job/job-plan.json" \
      --root "$WORK/bundle" --manifest "$WORK/job/artifact-manifest.json" \
      --label e2e-demo --output "$WORK/fabric/execution-record.json" \
      --results-dir "$WORK/fabric/results" >/dev/null 2>&1; then
    note "== 1. Fabric executed a real bounded job"
    if python3 -m mncs_fabric.cli provenance emit "$WORK/fabric/execution-record.json" \
        --output "$WORK/evidence/fabric-evidence.json" --run-id demo-run-1 >/dev/null 2>&1; then
      note "== 2. Fabric rights/provenance evidence emitted"
      FABRIC_STAGE=1
    else
      note "!! provenance emit failed"
    fi
  else
    note "!! fabric local execution unavailable in this environment"
  fi
else
  note "!! mncs-fabric not importable; SKIPPED stages 1-2"
fi

# ----------------------------------------------------------------- Forge ----
cat > "$WORK/forge_scan.py" <<'PY'
import json, pathlib, sys
work = pathlib.Path(sys.argv[1])
try:
    from mncs_forge.config import ForgeConfig
    from mncs_forge.application.license_evidence import scan_license_evidence
except ImportError:
    print("!! mncs-forge not importable; SKIPPED stage 3")
    raise SystemExit(0)
project = work / "project"
raw = {
    "project": {"name": "e2e-demo", "identity": "e2e-demo"},
    "limits": {"timeout_seconds": 1, "output_bytes": 1024},
}
config = ForgeConfig(
    config_path=project / "mncs-forge.toml",
    root=project,
    raw=raw,
    path_values={},
    providers={},
    workflows={},
    verifiers={},
)
evidence = scan_license_evidence(config)
(work / "evidence").mkdir(parents=True, exist_ok=True)
(work / "evidence/forge-license-evidence.json").write_text(json.dumps(evidence, indent=2))
print("== 3. Forge license evidence scanned:", evidence["evidence_id"])
PY
mkdir -p "$WORK/project/src"
printf '[project]\nname = "e2e-demo"\nversion = "0.1.0"\nlicense = "Apache-2.0"\n' > "$WORK/project/pyproject.toml"
{ printf 'Apache License\nVersion 2.0, January 2004\n'; } > "$WORK/project/LICENSE"
python3 "$WORK/forge_scan.py" "$WORK"

# ------------------------------------------------------- Rights manifest ----
cat > "$WORK/build_manifest.py" <<PY
import hashlib, json, pathlib, sys
sys.path.insert(0, "$RP_SRC")
from mncs_rights_provenance import (
    Artifact, EvidenceRef, GraphEdge, GraphNode, Manifest, Participant,
    Rights, Review, Source, validate_manifest_structure,
)
from mncs_rights_provenance.manifest import manifest_to_dict, seal_manifest

work = pathlib.Path(sys.argv[1])
evidence_dir = work / "evidence"

process_evidence = []
graph_nodes = [
    GraphNode(node_id="job", kind="action", label="bounded fabric execution"),
    GraphNode(node_id="outputs", kind="artifact", artifact_class="experiment-output"),
]
graph_edges = [GraphEdge(source="job", target="outputs", relation="derived-from")]

def load(name):
    path = evidence_dir / name
    return json.loads(path.read_text()) if path.exists() else None

for filename in ("fabric-evidence.json", "forge-license-evidence.json"):
    doc = load(filename)
    if doc is None:
        continue
    process_evidence.append(EvidenceRef(
        kind="rights-evidence-record",
        reference=doc["evidence_id"],
        sha256=str(doc["content_digest"]).split(":", 1)[1],
        producer_reference=doc["producer"],
    ))

if load("forge-license-evidence.json") is not None:
    doc = load("forge-license-evidence.json")
    graph_nodes.append(GraphNode(
        node_id="license-analysis", kind="external",
        label="Forge license scan", external_ref=doc["evidence_id"]))
    graph_edges.append(GraphEdge(
        source="license-analysis", target="outputs", relation="attested-by"))

sources = []
if load("forge-license-evidence.json") is not None:
    sources.append(Source(
        source_kind="package",
        reference="pypi.org/project/demo",
        license_status="compatible",
        license="Apache-2.0",
        confidence="observed-declaration",
    ))

result_hash = None
results = work / "fabric/results"
if results.exists():
    for path in sorted(results.rglob("result.json")):
        result_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        break

hashes = [{"algorithm": "sha256", "value": result_hash, "scope": "file"}] if result_hash else []
graph_nodes[1] = GraphNode(
    node_id="outputs", kind="artifact", artifact_class="experiment-output",
    hashes=[{"algorithm": "sha256", "value": h["value"]} for h in hashes])

manifest = Manifest(
    artifact=Artifact(id="demo:e2e-artifact", artifact_class="experiment-output",
                      hashes=hashes),
    provenance_origin="human-directed-machine-generated",
    participants=[
        Participant(participant_type="model", role="implementation",
                    model="local-python-runtime"),
    ],
    process_evidence=process_evidence,
    graph_nodes=graph_nodes,
    graph_edges=graph_edges,
    rights=Rights(
        distribution_license="Apache-2.0",
        copyright_status="mixed-or-undetermined",
        rights_basis="contributor-attested",
        third_party_material="none-known",
        sources=sources,
    ),
    review=Review(technical_validation="passed", provenance_validation="passed",
                  human_acceptance="not-reviewed"),
    spec_profile="canonical-release",
)
document = manifest_to_dict(manifest)
issues = validate_manifest_structure(document)
assert not issues, issues
seal_manifest(document)
(work / "rights-manifest.json").write_text(json.dumps(document, indent=2))
print("== 4. Rights manifest built and sealed:",
      document["manifest_identity"][:16], "...")
PY
PYTHONPATH="$RP_SRC" python3 "$WORK/build_manifest.py" "$WORK"

# ------------------------------------------------------------- Validator ----
VALIDATOR_BIN="${VALIDATOR_BIN:-}"
validator_dir="${MNCS_VALIDATOR_DIR:-$PROJECTS_DIR/mncs-validator-rs}"
run_validator() {
  if [ -n "$VALIDATOR_BIN" ] && command -v "$VALIDATOR_BIN" >/dev/null 2>&1; then
    "$VALIDATOR_BIN" rights-validate "$1"
    return $?
  fi
  if command -v cargo >/dev/null 2>&1 && [ -d "$validator_dir" ]; then
    (cd "$validator_dir" && cargo run --quiet -- rights-validate "$1")
    return $?
  fi
  return 127
}
set +e
run_validator "$WORK/rights-manifest.json" > "$WORK/validator-report.json" 2>/dev/null
validator_rc=$?
set -e
case $validator_rc in
  0) note "== 5. Validator outcome: pass" ;;
  4) note "== 5. Validator outcome: findings/review (exit 4)" ;;
  *) note "!! validator unavailable or blocked (rc=$validator_rc)" ;;
esac
if [ -s "$WORK/validator-report.json" ]; then
  python3 -c "
import json
d = json.load(open('$WORK/validator-report.json'))
print('   outcome:', d.get('outcome'), '| findings:', len(d.get('findings', [])))"
fi

# ------------------------------------------- Artifact/hash correspondence ----
RESULT_FILE="$WORK/fabric/results/result.json"
if [ -f "$RESULT_FILE" ] && command -v mncs-rp >/dev/null 2>&1; then
  if PYTHONPATH="$RP_SRC" python3 -m mncs_rights_provenance.cli validate \
      "$WORK/rights-manifest.json" --artifact-file "$RESULT_FILE" \
      > "$WORK/rp-validation.json" 2>/dev/null; then
    note "== 5b. Artifact sha256 corresponds to the declared manifest hash"
  else
    rc=$?
    case $rc in
      1) note "!! stage 5b: structural invalid" ;;
      3) note "== 5b. hash/policy mismatch detected (blocked)" ;;
      *) note "== 5b. validation findings recorded (rc=$rc)" ;;
    esac
    python3 -c "
import json
d = json.load(open('$WORK/rp-validation.json'))
print('   outcome:', d.get('outcome'), '| identity matches:', d.get('manifest_identity_matches'))"
  fi
fi

# -------------------------------------------------------------- Commons -----
cat > "$WORK/commons_publish.py" <<PY
import json, pathlib, sys
try:
    from mncs_commons.store import CommonsStore
except ImportError:
    print("!! mncs-commons not importable; SKIPPED stage 6")
    raise SystemExit(0)
from mncs_commons.adapters.rights import from_rights_evidence_record

work = pathlib.Path(sys.argv[1])
ev_path = work / "evidence/fabric-evidence.json"
if not ev_path.exists():
    print("!! no fabric evidence; SKIPPED commons projection")
    raise SystemExit(0)
store = CommonsStore(work / "commons-store")
result = from_rights_evidence_record(
    json.loads(ev_path.read_text()),
    subject_identity="demo:e2e-artifact",
    created_at="2026-08-25T00:00:00Z",
    scope_context={"demo": "end-to-end"},
    artifact_id="demo:e2e-artifact",
)
assert result.record is not None, [d.code for d in result.diagnostics]
store.init()
stored = store.add_record(result.record)
digest = getattr(stored, "content_digest", None) or stored.get("contentDigest") or "published"
print("== 6. Commons retained rights observation:", str(digest)[:19])
PY
PYTHONPATH="$PROJECTS_DIR/MNCS-Commons/src" python3 "$WORK/commons_publish.py" "$WORK"

# ----------------------------------------------------------------- SPDX -----
if PYTHONPATH="$RP_SRC" python3 -m mncs_rights_provenance.cli export-spdx \
    "$WORK/rights-manifest.json" > "$WORK/spdx.json" 2>/dev/null; then
  note "== 7. SPDX exported ($(wc -c < "$WORK/spdx.json") bytes)"
else
  note "!! SPDX export skipped"
fi

note ""
note "== end-to-end complete"
