"""Real data, PD calibration by vintage (case C03, SBA 7(a) loans): the e-process monitor read at every age.

Reads the five committed cohort documents ``data/derived/C03/fy*.json`` (their ``sequential`` block holds the engine's PD
e-process of every vintage and of the cohort) and recomputes the block from the document's own vintage curves with the
product's builder ``pipeline.cases.c03.sequential.build`` and the engine (release 1.1.0), so that the table of the
manuscript is the engine's output on the committed curves and not a copy. The monitor is read at the five ages 12, 24,
36, 48 and 60 months; the fixed-window comparator is the champion's binomial test read once at the five-year mark (the light of
the document's test row).

    python manuscripts/e-process-sequential-monitors/experiments/exp_c03.py
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from importlib import metadata

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "data-pipeline"))


def main() -> int:
    from pipeline.cases.c03 import sequential as seq

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=pathlib.Path, default=HERE / "results_c03.json")
    args = ap.parse_args()
    cohorts = {}
    for path in sorted((ROOT / "data" / "derived" / "C03").glob("fy*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        out = doc["outputs"]
        committed = out["sequential"]
        curves = out["vintage_curves"]
        # the champion's binomial rows of the document, to rebuild the five-year light of each vintage
        tests = [t for t in doc.get("tests", []) if t.get("test_id") == seq.FIXED_TEST]
        champions = {t["model_id"] for t in tests}
        champion = next(iter(champions)) if champions else ""
        rebuilt = seq.build(curves, doc.get("tests", []), champion)
        same = True
        for k in ("average", "product"):
            same &= np.allclose(np.array(committed[k]["log_e"], dtype=float), np.array(rebuilt[k]["log_e"], dtype=float),
                                equal_nan=True, rtol=1e-6, atol=1e-4)
            same &= committed[k]["rejection_month"] == rebuilt[k]["rejection_month"]
        vint = [{k: v[k] for k in ("fiscal_year", "n", "defaults", "predicted_defaults", "rejection_month", "max_log_e",
                                   "five_year_light", "months_observed")} for v in committed["vintages"]]
        cohorts[path.stem] = {
            "months": committed["months"], "vintages": vint,
            "average": {k: committed["average"][k] for k in ("rejection_month", "max_log_e", "anytime_p_value")},
            "product": {k: committed["product"][k] for k in ("rejection_month", "max_log_e", "anytime_p_value")},
            "recomputed_equals_committed": bool(same),
            "sources": {"document": f"data/derived/C03/{path.name}", "builder": "data-pipeline/pipeline/cases/c03/sequential.py"},
        }
        print(path.stem, "average", committed["average"]["rejection_month"], "product", committed["product"]["rejection_month"],
              "recomputed equal:", same, flush=True)
    result = {"meta": {"engine_version": metadata.version("riskvalidation"), "alpha_level": seq.ALPHA_LEVEL,
                       "direction": seq.DIRECTION, "headline": seq.HEADLINE, "script": "experiments/exp_c03.py"},
              "cohorts": cohorts}
    args.out.write_text(json.dumps(result, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
