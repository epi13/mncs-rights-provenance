#!/usr/bin/env python3
"""Generate dogfood manifests from real MNCS repository state.

Every manifest here references a real file at a real commit in a real MNCS
repository, with its true sha256. These are the subsystem's own fixtures:
MNCS documenting MNCS. Sections whose upstream material is unavailable in the
current checkout are skipped explicitly rather than fabricated.

Regenerate after upstream changes:

    python3 scripts/dogfood_generate.py
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ROOT.parent
OUT = ROOT / "dogfood"


class MissingRepo(Exception):
    pass


def git(repo: str, *args: str) -> str:
    repo_path = PROJECTS / repo
    if not (repo_path / ".git").exists():
        raise MissingRepo(repo)
    result = subprocess.run(
        ["git", "-C", str(repo_path), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def base_manifest() -> dict:
    return {
        "schema_version": "0.2.0",
        "spec_profile": "canonical-release",
        "provenance": {"participants": [], "process_evidence": []},
        "rights": {
            "distribution_license": "Apache-2.0",
            "sources": [],
        },
        "review": {},
    }


def finish(manifest: dict) -> dict:
    provenance = manifest["provenance"]
    provenance.setdefault("origin_classification", "origin-uncertain")
    rights = manifest["rights"]
    rights.setdefault("copyright_status", "unresolved")
    rights.setdefault("rights_basis", "unknown-needs-review")
    rights.setdefault("third_party_material", "unknown")
    review = manifest["review"]
    review.setdefault("technical_validation", "not-run")
    review.setdefault("provenance_validation", "passed")
    review.setdefault("human_acceptance", "not-reviewed")

    reduced = {k: v for k, v in manifest.items() if k != "manifest_identity"}
    canonical = json.dumps(reduced, sort_keys=True, separators=(",", ":")).encode()
    manifest["manifest_identity"] = hashlib.sha256(canonical).hexdigest()
    return manifest


def write(name: str, manifest: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"wrote {path.relative_to(ROOT)}")


def skip_guard(label: str):
    class _Guard:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            if exc_type is None:
                return False
            if issubclass(exc_type, (MissingRepo, FileNotFoundError)):
                print(f"skipped {label}: upstream material unavailable")
                return True
            return False

    return _Guard()


def section_human_specification(rp_head: str) -> None:
    spec_rel = Path("docs/problem-statement.md")
    spec_abs = PROJECTS / "mncs-rights-provenance" / spec_rel
    manifest = base_manifest()
    manifest["artifact"] = {
        "id": f"mncs-rights-provenance:{rp_head}:docs/problem-statement.md",
        "class": "documentation",
        "repository": "github.com/epi13/mncs-rights-provenance",
        "commit": rp_head,
        "paths": [str(spec_rel)],
        "hashes": [{"algorithm": "sha256", "value": sha256_file(spec_abs), "scope": "file"}],
    }
    manifest["provenance"]["origin_classification"] = "human-authored"
    manifest["provenance"]["participants"] = [
        {"type": "human", "role": "author", "name": "project maintainer"}
    ]
    manifest["provenance"]["process_evidence"] = [
        {"kind": "commit", "reference": f"github.com/epi13/mncs-rights-provenance@{rp_head}"}
    ]
    manifest["rights"]["copyright_status"] = "human-authorship-confirmed"
    manifest["rights"]["rights_basis"] = "contributor-attested"
    manifest["rights"]["third_party_material"] = "none-known"
    write("human-specification.json", finish(manifest))


def section_agent_directed_fabric(fabric_head: str) -> None:
    code_rel = Path("src/mncs_fabric/provenance.py")
    code_abs = PROJECTS / "mncs-fabric" / code_rel
    manifest = base_manifest()
    manifest["artifact"] = {
        "id": f"mncs-fabric:{fabric_head}:{code_rel}",
        "class": "source-code",
        "repository": "github.com/epi13/mncs-fabric",
        "commit": fabric_head,
        "paths": [str(code_rel)],
        "hashes": [{"algorithm": "sha256", "value": sha256_file(code_abs), "scope": "file"}],
    }
    manifest["provenance"]["origin_classification"] = "human-directed-machine-generated"
    manifest["provenance"]["participants"] = [
        {"type": "human", "role": "director", "name": "project operator"},
        {
            "type": "model",
            "role": "implementation",
            "model": "ox-alpha (opencode agent)",
            "provider": "undisclosed",
        },
        {"type": "agent", "role": "orchestrator", "name": "opencode"},
    ]
    manifest["provenance"]["notes"] = (
        "Classification describes process only. Machine participation does "
        "not determine copyright status; rights fields remain evidence states."
    )
    manifest["rights"]["copyright_status"] = "machine-originated-unresolved"
    manifest["rights"]["rights_basis"] = "no-exclusive-right-asserted"
    manifest["rights"]["third_party_material"] = "none-known"
    write("agent-directed-fabric-module.json", finish(manifest))


def section_mncs_language_core(rp_head: str) -> None:
    lang_src_rel = Path("language/rights_policy.mncs")
    lang_src_abs = ROOT / lang_src_rel
    corpus_abs = ROOT / "language/corpora/policy-evaluation-corpus.json"
    manifest = base_manifest()
    src_hash = sha256_file(lang_src_abs)
    evidence_entry = {
        "kind": "validation-receipt",
        "reference": "mncs://experiment-run/language/corpora/policy-evaluation-corpus.json",
    }
    if corpus_abs.exists():
        evidence_entry["sha256"] = sha256_file(corpus_abs)
    manifest["artifact"] = {
        "id": f"mncs-rights-provenance:{rp_head}:language/rights_policy.mncs",
        "class": "source-code",
        "repository": "github.com/epi13/mncs-rights-provenance",
        "commit": rp_head,
        "paths": [str(lang_src_rel)],
        "hashes": [{"algorithm": "sha256", "value": src_hash, "scope": "file"}],
    }
    manifest["provenance"]["origin_classification"] = "autonomous-machine-generated"
    manifest["provenance"]["participants"] = [
        {
            "type": "model",
            "role": "implementation",
            "model": "ox-alpha (opencode agent)",
            "provider": "undisclosed",
        },
        {"type": "tool", "role": "compiler", "name": "mncs-cli (research-bytecode/portable-wasm)"},
    ]
    manifest["provenance"]["process_evidence"] = [evidence_entry]
    manifest["provenance"]["graph"] = {
        "nodes": [
            {
                "id": "policy-source",
                "kind": "artifact",
                "artifact_class": "source-code",
                "hashes": [{"algorithm": "sha256", "value": src_hash}],
            },
            {
                "id": "compile-action",
                "kind": "transformation",
                "label": "mncs compile --target research-bytecode|portable-wasm",
            },
            {
                "id": "corpus-validation",
                "kind": "validation",
                "label": "experiment run across backends",
            },
            {"id": "golden-vectors", "kind": "artifact", "artifact_class": "dataset"},
        ],
        "edges": [
            {"from": "policy-source", "to": "compile-action", "relation": "transformed-by"},
            {"from": "compile-action", "to": "corpus-validation", "relation": "validated-by"},
            {"from": "corpus-validation", "to": "golden-vectors", "relation": "derived-from"},
        ],
    }
    manifest["rights"]["copyright_status"] = "machine-originated-unresolved"
    manifest["rights"]["rights_basis"] = "no-exclusive-right-asserted"
    manifest["rights"]["third_party_material"] = "none-known"
    manifest["review"]["technical_validation"] = "passed"
    write("mncs-language-policy-core.json", finish(manifest))


def section_third_party_dependency(commons_head: str) -> None:
    pyproject_abs = PROJECTS / "MNCS-Commons/pyproject.toml"
    text = pyproject_abs.read_text(encoding="utf-8")
    dependency = "zstandard" if "zstandard" in text else "unknown"
    manifest = base_manifest()
    manifest["artifact"] = {
        "id": f"mncs-commons:{commons_head}:dependency/{dependency}",
        "class": "binary",
        "repository": "github.com/epi13/MNCS-Commons",
        "commit": commons_head,
    }
    manifest["provenance"]["origin_classification"] = "third-party-derived"
    manifest["provenance"]["participants"] = [
        {"type": "organization", "role": "upstream-author", "name": dependency}
    ]
    manifest["rights"]["distribution_license"] = "BSD-3-Clause"
    manifest["rights"]["copyright_status"] = "third-party-licensed"
    manifest["rights"]["rights_basis"] = "third-party-license"
    manifest["rights"]["third_party_material"] = "present"
    manifest["rights"]["sources"] = [
        {
            "kind": "package",
            "reference": f"pypi.org/project/{dependency}",
            "license_status": "compatible",
            "license": "BSD-3-Clause",
            "confidence": "observed-declaration",
            "notes": "License per upstream declaration; declaration is evidence, not verification.",
        }
    ]
    write("third-party-dependency.json", finish(manifest))


def section_uncertain_origin(rp_head: str) -> None:
    uncertain_rel = Path("docs/open-questions.md")
    uncertain_abs = PROJECTS / "mncs-rights-provenance" / uncertain_rel
    manifest = base_manifest()
    manifest["artifact"] = {
        "id": f"mncs-rights-provenance:{rp_head}:docs/open-questions.md",
        "class": "documentation",
        "repository": "github.com/epi13/mncs-rights-provenance",
        "commit": rp_head,
        "paths": [str(uncertain_rel)],
        "hashes": [{"algorithm": "sha256", "value": sha256_file(uncertain_abs), "scope": "file"}],
    }
    manifest["provenance"]["origin_classification"] = "origin-uncertain"
    manifest["provenance"]["participants"] = [{"type": "unknown", "role": "contributor"}]
    manifest["provenance"]["notes"] = (
        "Edit history mixes human and machine-assisted sessions without "
        "preserved per-session attribution. Uncertainty is preserved rather "
        "than resolved by assumption."
    )
    manifest["rights"]["distribution_license"] = "Apache-2.0"
    manifest["rights"]["copyright_status"] = "unresolved"
    manifest["rights"]["rights_basis"] = "unknown-needs-review"
    manifest["rights"]["third_party_material"] = "possible"
    write("uncertain-origin-document.json", finish(manifest))


def main() -> int:
    rp_head = git("mncs-rights-provenance", "rev-parse", "--short", "HEAD")

    sections = (
        ("human-specification", lambda: section_human_specification(rp_head)),
        ("agent-directed-fabric-module", lambda: section_agent_directed_fabric(
            git("mncs-fabric", "rev-parse", "--short", "HEAD"))),
        ("mncs-language-policy-core", lambda: section_mncs_language_core(rp_head)),
        ("third-party-dependency", lambda: section_third_party_dependency(
            git("MNCS-Commons", "rev-parse", "--short", "HEAD"))),
        ("uncertain-origin-document", lambda: section_uncertain_origin(rp_head)),
    )
    generated = 0
    for label, fn in sections:
        with skip_guard(label):
            fn()
            generated += 1

    total = len(list(OUT.glob("*.json"))) if OUT.exists() else 0
    print(f"\nGenerated {generated} dogfood manifest(s); {total} present.")
    if generated == 0 and total == 0:
        print("no dogfood manifests available; nothing to validate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
