"""Per-history capitals of the C17 cells, checked against the committed documents and written as compact JSON.

The committed documents ``data/derived/C17/xi-*.json`` hold, for every cell of 1,000 independent histories, only the percentiles of
the ratio of each rung's capital to the true quantile. The bootstrap intervals, the share of histories within a factor of two of
the truth and the share that conclude an infinite mean need the ratio of every history. The bake of the case
(``data-pipeline/pipeline/cases/c17/bake.py``) caches those arrays per cell in a cache folder; this script

1. finds, for every cell, the cached arrays whose percentiles, share underestimating and ``n_defined`` reproduce the committed
   document for every rung (a cache of another bake is refused, never used),
2. writes ``histories-<variant>.json`` here: the capital over the true quantile of each history, ten rungs, the fitted tail index
   above one, two, four and eight times the collection threshold, and the number of recorded losses, at six significant digits,
3. with ``--check-rerun N`` re-draws the first N histories of one cell through the product's own ``bake.run_cell`` (the engine
   ``riskvalidation`` 1.1.0, seed 42) and compares them with the cached arrays, so that the cache is shown to be the output of the
   committed pipeline and not a file of unknown origin.

Run from the repository root::

    python manuscripts/instability-of-operational-risk-capital/experiments/extract_histories.py --cache <folder of the bake cache of the case>
    python manuscripts/instability-of-operational-risk-capital/experiments/extract_histories.py --cache <...> --check-rerun 8 --cell xi-0-96:5:10000

Without ``--cache`` the folder is ``$CAOS_TEMP_ROOT/contraste-instability-of-operational-risk-capital/cache`` (an error when the variable is unset).
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DERIVED = ROOT / "data" / "derived" / "C17"
VARIANTS = ("xi-0-6", "xi-0-8", "xi-0-96", "xi-1-1")
RUNGS = ("lda_lognormal", "lda_lognormal_truncated", "lda_splice", "sla", "sla_mean_corrected", "scenario",
         "sla_mean_adjusted", "sla_cvm", "sla_obre", "sla_cvm_lognormal")
SEED = 42  # the case seed of the committed bake (provenance.seed of every document)
RTOL = 1e-6


def doc_summary(capital: dict, rung: str) -> dict:
    """The summary of a rung in a document: the five rungs of the first ladder are flat, the others are under ``summary``."""
    block = capital[rung]
    return block["summary"] if "summary" in block else block


def matches(arrays: dict, cell: dict, truth: float) -> bool:
    """True when the cached arrays reproduce every rung's percentiles, share underestimating and n_defined of the cell."""
    if any(r not in arrays for r in RUNGS):
        return False  # a cache of an older bake without the robust rungs
    for rung in RUNGS:
        s = doc_summary(cell["capital"], rung)
        x = np.asarray(arrays[rung], dtype=float) / truth
        x = x[np.isfinite(x)]
        if s is None:  # the document states no summary (a tail index of 1 or more has no mean-corrected rung): no history has a capital
            if x.size:
                return False
            continue
        if x.size != s["n_defined"]:
            return False
        if x.size == 0:
            continue
        for key, p in (("p05", 5), ("p25", 25), ("median", 50), ("p75", 75), ("p95", 95)):
            want = s["ratio_to_truth"][key]
            if abs(np.percentile(x, p) - want) > RTOL * abs(want):
                return False
        if abs(float((x < 1.0).mean()) - s["share_underestimating"]) > 1e-6:
            return False
    return True


def sig(x: float, digits: int = 6):
    """A float at ``digits`` significant digits, or None for a history on which the rung is undefined."""
    if not math.isfinite(x):
        return None
    return float(f"{x:.{digits - 1}e}")


def find_cache(cache: pathlib.Path, vid: str, cell: dict, truth: float) -> tuple[pathlib.Path, dict]:
    pattern = str(cache / f"{vid}-y{cell['years']}-h{cell['collection_threshold_eur']}-*.npz")
    for path in sorted(glob.glob(pattern)):
        with np.load(path, allow_pickle=False) as z:
            arrays = {k: z[k] for k in z.files}
        if matches(arrays, cell, truth):
            return pathlib.Path(path), arrays
    raise SystemExit(f"no cached cell reproduces the committed document for {vid} {cell['id']} ({pattern})")


def extract(cache: pathlib.Path) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for vid in VARIANTS:
        doc = json.loads((DERIVED / f"{vid}.json").read_text(encoding="utf-8"))
        truth = float(doc["outputs"]["truth"]["annual_loss_quantile"]["value_eur"])
        out = {"variant": vid, "tail_index": doc["outputs"]["tail_index"], "truth_eur": truth, "seed": SEED, "cells": []}
        for cell in doc["outputs"]["cells"]:
            path, a = find_cache(cache, vid, cell, truth)
            out["cells"].append({
                "id": cell["id"], "years": cell["years"], "threshold_eur": cell["collection_threshold_eur"],
                "seed_first": cell["replications"]["seed_first"], "n_replications": cell["replications"]["n_replications"],
                "cache_key": path.stem.rsplit("-", 1)[-1],
                "failed": [int(x) for x in a["failed"]],
                "n_losses": [int(x) for x in a["n_losses"]],
                "ratio": {r: [sig(v / truth) for v in a[r]] for r in RUNGS},
                "xi": [[sig(v) for v in row] for row in a["xi"]],
            })
            print(f"{vid} {cell['id']}: matched cache {path.name}", file=sys.stderr)
        found[vid] = out
    return found


def check_rerun(cache: pathlib.Path, spec: str, n: int, workers: int) -> None:
    """Re-draw the first ``n`` histories of a cell through the product's bake and compare them with the cached arrays."""
    vid, years, thr = spec.split(":")
    years, thr = int(years), float(thr)
    sys.path.insert(0, str(ROOT / "data-pipeline"))
    from pipeline.cases.c17 import bake, params as P  # noqa: PLC0415
    from pipeline.cases.c17.generator import cell_seeds, variant, variants  # noqa: PLC0415
    from pipeline.cases.c17.replicate import bank_business_indicator, scenario_points, scenario_prior  # noqa: PLC0415

    vi = [v.variant_id for v in variants()].index(vid)
    ci = list(P.CELLS).index((years, int(thr)))
    v = variant(P.TAIL_INDICES[vi])
    first, _ = cell_seeds(SEED, vi, ci, P.N_REPLICATIONS)
    prior, _ = scenario_prior(v, scenario_points(v), years)
    cell = bake.run_cell(v, years, thr, first, n, bank_business_indicator()["bi_eur"], prior, P.MC_YEARS_REPLICATION, False, workers, None, "rerun")
    doc = json.loads((DERIVED / f"{vid}.json").read_text(encoding="utf-8"))
    truth = float(doc["outputs"]["truth"]["annual_loss_quantile"]["value_eur"])
    cdoc = next(c for c in doc["outputs"]["cells"] if c["years"] == years and c["collection_threshold_eur"] == thr)
    _, cached = find_cache(cache, vid, cdoc, truth)
    worst = 0.0
    for r in RUNGS:
        a, b = np.asarray(cell.arrays[r]), np.asarray(cached[r])[:n]
        same_nan = np.array_equal(np.isnan(a), np.isnan(b))
        ok = ~np.isnan(a) & ~np.isnan(b)
        rel = float(np.max(np.abs(a[ok] - b[ok]) / np.abs(b[ok]))) if ok.any() else 0.0
        worst = max(worst, rel)
        print(f"rerun {vid} y{years} h{int(thr)} first {n} histories, {r}: same undefined set {same_nan}, max relative difference {rel:.3e}")
        if not same_nan:
            raise SystemExit(f"{r}: the rerun leaves a different set of histories undefined")
    print(f"worst relative difference over the ten rungs: {worst:.3e}")
    if worst > 1e-9:
        raise SystemExit("the rerun differs from the cache")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", help="the bake cache folder of the case (default: $CONTRASTE_DATA_ROOT/cache/C17)")
    ap.add_argument("--check-rerun", type=int, default=0, metavar="N", help="re-draw the first N histories of --cell and compare")
    ap.add_argument("--cell", default="xi-0-96:5:10000", help="variant:years:threshold of the rerun check")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    if args.cache:
        cache = pathlib.Path(args.cache)
    elif os.environ.get("CAOS_TEMP_ROOT"):
        cache = pathlib.Path(os.environ["CAOS_TEMP_ROOT"]) / "contraste-instability-of-operational-risk-capital" / "cache"
    else:
        raise SystemExit("pass --cache <folder of the bake cache of the case> or set CAOS_TEMP_ROOT")
    if args.check_rerun:
        check_rerun(cache, args.cell, args.check_rerun, args.workers)
        return 0
    for vid, doc in extract(cache).items():
        path = HERE / f"histories-{vid}.json"
        path.write_text(json.dumps(doc, separators=(",", ":")), encoding="utf-8")
        print(f"wrote {path.name}: {path.stat().st_size:,} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
