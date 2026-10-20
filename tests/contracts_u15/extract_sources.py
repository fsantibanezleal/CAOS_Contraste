"""Extracts the committed facts the U15-S fixtures are written from, into tests/contracts_u15/snapshots/source-extract.json.

Run: ``python tests/contracts_u15/extract_sources.py [--c18-ref origin/task/u13-p1]``. Reads the committed case documents of the four fixture
entries (C01/german, C07/banco-andino, C18/banco-andino, C22/generators) from ``data/derived`` (C18 is not on the integration branch yet: it is
read with ``git show`` from the ref given) and writes one compact JSON file, so that ``build_fixtures.py`` is deterministic and reproducible
anywhere without the case branches. The sha256 of a document is taken over its bytes with line endings normalised to LF (a Windows checkout
hashes as a Linux one). Standard library only.

Which variants belong to which fit: a variant document carries no fit id. C01 german-twin is the only variant of the german fit (its provenance
reads uci-german only); C07, C18 and C22 have one models document, so all their variants belong to it (A D1 of the U15 research addendum).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from attribute_table import pointers, resolve  # noqa: E402  (this folder is not a package)

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "tests" / "contracts_u15" / "snapshots" / "source-extract.json"
DERIVED = ROOT / "data" / "derived"

# case -> (fit id, models document, variants of the fit, default variant, where the documents are read from)
CASES = {
    "C01": ("german", "models-german.json", ["german-twin"], "german-twin", "tree"),
    "C07": ("banco-andino", "models-banco-andino.json",
            ["base", "combined-severe", "consumer-arrears-shock", "house-price-fall", "recession", "uf-inflation-spike"], "base", "tree"),
    "C18": ("banco-andino", "models-banco-andino.json",
            ["baseline", "eba-2025-adverse", "fed-2026-severely-adverse", "ngfs-delayed-transition", "reverse-stress", "t-copula-baseline"],
            "baseline", "git"),
    "C22": ("generators", "models-generators.json",
            ["broken-monotonicity", "clustering", "concentration", "discrimination-decay", "drift", "leakage", "miscalibration", "null"],
            "null", "tree"),
}
ROW_KEYS = ["test_id", "model_id", "segment", "statistic", "p_value", "metric", "light"]
DEFAULT_KEYS = ROW_KEYS + ["h0", "reference", "policy_version", "alpha_amber", "alpha_red", "n", "n_events", "inputs_hash"]


def sha256_lf(raw: bytes) -> str:
    return hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()


def read(rel: str, source: str, ref: str) -> bytes:
    if source == "git":
        return subprocess.run(["git", "show", f"{ref}:{rel}"], cwd=ROOT, check=True, capture_output=True).stdout
    return (ROOT / rel).read_bytes()


def load(rel: str, source: str, ref: str) -> tuple[dict, str]:
    raw = read(rel, source, ref)
    return json.loads(raw.decode("utf-8")), sha256_lf(raw)


def registry_decisions(src: Path) -> dict[str, str]:
    """test id -> ``decision`` (``p_value`` or ``metric``) of every ``@register(...)`` in the engine sources: the ``spec(test_id).decision`` of
    ``core/registry.py``. Read from the source text, so the engine need not be installed."""
    out: dict[str, str] = {}
    rx = re.compile(r'register\(\s*"([^"]+)"(.*?)decision="(p_value|metric)"', re.S)
    for f in sorted(src.rglob("*.py")):
        for m in rx.finditer(f.read_text(encoding="utf-8")):
            out[m.group(1)] = m.group(3)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--c18-ref", default="origin/task/u13-p1")
    ap.add_argument("--engine-src", required=True, help="the src folder of the engine checkout (the batch 3 integration head) whose registry gives spec(test_id).decision")
    args = ap.parse_args()
    engine_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=Path(args.engine_src).parent, check=True, capture_output=True, text=True).stdout.strip()
    decisions = registry_decisions(Path(args.engine_src))
    commit = subprocess.run(["git", "rev-parse", args.c18_ref], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    out: dict = {"c18_ref": args.c18_ref, "c18_commit": commit, "engine_commit": engine_commit, "cases": {}}
    for case, (fit, models_name, variants, default, source) in CASES.items():
        models, models_hash = load(f"data/derived/{case}/{models_name}", source, args.c18_ref)
        manifest, manifest_hash = load(f"data/derived/manifests/{case}.json", source, args.c18_ref)
        assert models["case_id"] == case and models["fit_id"] == fit, (case, models["fit_id"])
        docs: dict[str, dict] = {f"data/derived/{case}/{models_name}": models, f"data/derived/manifests/{case}.json": manifest}
        entry = {
            "fit_id": fit,
            "manifest": {"path": f"data/derived/manifests/{case}.json", "sha256": manifest_hash, "title": manifest["title"],
                         "category": manifest["category"], "question": manifest["question"], "sources": manifest["sources"],
                         "seed": manifest["seed"]},
            "models_document": {"path": f"data/derived/{case}/{models_name}", "sha256": models_hash,
                                "code_version": models["provenance"]["code_version"],
                                "riskvalidation_version": models["provenance"]["riskvalidation_version"],
                                "truth_status": models["provenance"]["truth_status"],
                                "models": [{"id": m["id"], "family": m.get("family"), "rung": m.get("rung"), "engine": m.get("engine"),
                                            "title": m.get("title")}
                                           for m in models["model"]]},
            "default_variant": default,
            "variants": [],
        }
        for v in variants:
            doc, h = load(f"data/derived/{case}/{v}.json", source, args.c18_ref)
            docs[f"data/derived/{case}/{v}.json"] = doc
            keys = DEFAULT_KEYS if v == default else ROW_KEYS
            entry["variants"].append({
                "variant_id": doc["variant_id"], "path": f"data/derived/{case}/{v}.json", "sha256": h,
                "code_version": doc["provenance"]["code_version"],
                "riskvalidation_version": doc["provenance"]["riskvalidation_version"],
                "sources": [i["source"] for i in doc["provenance"]["inputs"]],
                "findings": doc["findings"],
                "tests": [{k: r[k] for k in keys} for r in doc["tests"]],
            })
        if case == "C07":   # the one PMA of the fixture entries (A26 of the addendum): the overlays of the default variant
            base, _ = load(f"data/derived/{case}/{default}.json", source, args.c18_ref)
            entry["pma"] = {"pointer": f"data/derived/{case}/{default}.json#/outputs/ifrs9_detail/overlays_total",
                            "overlays_total": base["outputs"]["ifrs9_detail"]["overlays_total"],
                            "model_output": base["impact"]["provision_ifrs9"]["value"],
                            "model_output_pointer": f"data/derived/{case}/{default}.json#/impact/provision_ifrs9/value",
                            "currency": base["outputs"]["ifrs9_detail"]["currency"]}
        verified, values = [], {}
        for ptrs in pointers(case, entry).values():
            for ptr in ptrs:
                path, _, frag = ptr.partition("#")
                value = resolve(docs[path], frag)   # KeyError: the fixture would cite a field that is not there
                verified.append(ptr)
                if len(json.dumps(value, ensure_ascii=False)) < 600:
                    values[ptr] = value
        entry["verified_pointers"] = sorted(set(verified))
        entry["pointer_values"] = dict(sorted(values.items()))
        default_doc = docs[f"data/derived/{case}/{default}.json"]
        entry["impact_keys"] = list(default_doc["impact"])
        if case == "C18":
            named = models["fit"]["named_parameters"]
            entry["named_parameters_count"] = len(named)
        default_rows = next(v for v in entry["variants"] if v["variant_id"] == default)["tests"]
        entry["spec_decisions"] = {t: decisions.get(t) for t in sorted({r["test_id"] for r in default_rows})}
        out["cases"][case] = entry
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}: " + ", ".join(f"{c} {len(e['variants'])} variants" for c, e in out["cases"].items()))


if __name__ == "__main__":
    main()
