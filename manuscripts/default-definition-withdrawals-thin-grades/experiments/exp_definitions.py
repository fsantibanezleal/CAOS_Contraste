"""Experiment 1: the default definition as part of the PD, on the three agencies' committed CEREP artifacts.

Reads ``data/derived/C04/{sp,moodys,fitch}.json`` (the case C04 documents) and writes
``experiments/definitions.json``. It adds to the committed documents what they do not hold:

* the long-run average PD of every grade under the default page (D2), the defaults page (D3), the transition page
  (D4) and the transition page with the withdrawals kept in the denominator (keep), with the Jeffreys interval of each
  pooled count (from the committed documents);
* the IRB risk weight of the agency's cohort mix under each definition, computed with the product's own risk-weight
  function (``pipeline.cases.c05_ldp_calibration._irb_rw``, the one behind the committed ``rw_d2`` and ``rw_d4``);
* the interval of those quantities from a bootstrap over the annual cohorts: B = 2,000 resamples of the cohort years
  with replacement, the same resample feeding every definition (seed 20261104), percentile interval at 95%;
* the share of the cohort years in which the transition page's rate is below the default page's.

Run from the repository root::

    E:/_venvs/contraste-u16-i/Scripts/python.exe manuscripts/default-definition-withdrawals-thin-grades/experiments/exp_definitions.py

It reads committed JSON only and takes about ten seconds.
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "manuscripts" / "_shared"))
sys.path.insert(0, str(ROOT / "data-pipeline"))

import figkit  # noqa: E402
from pipeline.cases.c05_ldp_calibration import _irb_rw  # noqa: E402

SEED = 20261104
B = 2000
GRADES = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC-C"]
AGENCIES = ("sp", "moodys", "fitch")
DEFS = ("d2", "d3", "d4", "keep")


def arr(x) -> np.ndarray:
    return np.array([[np.nan if v is None else v for v in row] for row in x], dtype=float)


def lra(rates: np.ndarray) -> np.ndarray:
    """Paragraph 84's average of the one-year rates over the cohorts where a grade's rate is defined."""
    out = np.full(rates.shape[1], np.nan)
    for g in range(rates.shape[1]):
        col = rates[np.isfinite(rates[:, g]), g]
        if col.size:
            out[g] = col.mean()
    return out


def portfolio_rw(pds: np.ndarray, mix: np.ndarray) -> float:
    if np.any(~np.isfinite(pds[mix > 0])):
        return float("nan")
    return float(sum(w * _irb_rw(float(p)) for p, w in zip(pds, mix) if w > 0))


def pct(x: np.ndarray) -> dict:
    x = x[np.isfinite(x)]
    if x.size == 0:
        return {"n": 0}
    lo, med, hi = np.percentile(x, [2.5, 50, 97.5])
    return {"n": int(x.size), "mean": float(x.mean()), "sd": float(x.std(ddof=1)), "lo": float(lo),
            "median": float(med), "hi": float(hi)}


def one_agency(code: str) -> dict:
    doc = figkit.doc(f"C04/{code}.json")
    out = doc["outputs"]
    rates = {k: arr(out["pd"][k]) if out["pd"].get(k) is not None else None for k in DEFS}
    mix = np.array(out["origination"][:7], dtype=float)
    mix = mix / mix.sum()
    res: dict = {"agency": out["agency"]["code"], "name": out["agency"]["name"], "cohorts": len(out["cohorts"]),
                 "labels": [c["label"] for c in out["cohorts"]], "mix": mix.tolist()}
    point = {}
    for k in DEFS:
        if rates[k] is None:
            point[k] = None
            continue
        v = lra(rates[k])
        point[k] = {"lra": v.tolist(), "rw": portfolio_rw(v, mix)}
    res["point"] = point
    # the committed intervals of the pooled counts (Jeffreys), where the definition has them
    res["jeffreys"] = {k: out["lra"][k]["jeffreys"] for k in ("d2", "d3", "d4") if out["lra"].get(k)}
    res["pooled_counts"] = {k: {"defaults": out["lra"][k]["defaults"], "n": out["lra"][k]["n"]}
                            for k in ("d2", "d3", "d4") if out["lra"].get(k)}
    res["definition_gap"] = out["definition_gap"]
    # the years in which the transition page's rate is below the default page's
    if rates["d4"] is not None:
        below = []
        for g in range(7):
            both = np.isfinite(rates["d4"][:, g]) & np.isfinite(rates["d2"][:, g]) & (rates["d2"][:, g] > 0)
            below.append({"years": int(both.sum()),
                          "d4_below_d2": int((rates["d4"][both, g] < rates["d2"][both, g]).sum()),
                          "d4_equal_d2": int((rates["d4"][both, g] == rates["d2"][both, g]).sum())})
        res["years_d4_below_d2"] = below
    # the bootstrap over the cohort years
    rng = np.random.default_rng(SEED)
    t = len(res["labels"])
    keys = [k for k in DEFS if rates[k] is not None]
    draws = {k: {"lra": np.zeros((B, 7)), "rw": np.zeros(B)} for k in keys}
    for b in range(B):
        idx = rng.integers(0, t, t)
        for k in keys:
            v = lra(rates[k][idx])
            draws[k]["lra"][b] = v
            draws[k]["rw"][b] = portfolio_rw(v, mix)
    boot: dict = {"B": B, "seed": SEED, "resampled": "cohort years, with replacement, one resample for every definition"}
    for k in keys:
        boot[k] = {"lra": [pct(draws[k]["lra"][:, g]) for g in range(7)], "rw": pct(draws[k]["rw"])}
    if "d4" in keys:
        boot["ratio_d4_over_d2"] = [pct(draws["d4"]["lra"][:, g] / np.where(draws["d2"]["lra"][:, g] > 0,
                                                                            draws["d2"]["lra"][:, g], np.nan))
                                    for g in range(7)]
        diff = draws["d2"]["rw"] - draws["d4"]["rw"]
        boot["rw_d2_minus_d4"] = pct(diff)
        boot["share_rw_d2_above_d4"] = float(np.mean(diff > 0))
    res["bootstrap"] = boot
    # the limits again from a second set of B resamples with the next seed
    if "d4" in keys:
        rng2 = np.random.default_rng(SEED + 1)
        ratio2, diff2 = [], []
        for b in range(B):
            idx = rng2.integers(0, t, t)
            v2, v4 = lra(rates["d2"][idx]), lra(rates["d4"][idx])
            ratio2.append(v4[6] / v2[6] if v2[6] > 0 else np.nan)
            diff2.append(portfolio_rw(v2, mix) - portfolio_rw(v4, mix))
        r2, d2 = pct(np.array(ratio2)), pct(np.array(diff2))
        boot["second_seed"] = {"seed": SEED + 1, "ratio_ccc": r2, "rw_d2_minus_d4": d2,
                                "max_abs_diff_of_limits": {
                                    "ratio_ccc": max(abs(r2["lo"] - boot["ratio_d4_over_d2"][6]["lo"]),
                                                     abs(r2["hi"] - boot["ratio_d4_over_d2"][6]["hi"])),
                                    "rw_gap": max(abs(d2["lo"] - boot["rw_d2_minus_d4"]["lo"]),
                                                  abs(d2["hi"] - boot["rw_d2_minus_d4"]["hi"]))}}
    return res


def main() -> None:
    result = {"seed": SEED, "bootstrap_resamples": B, "agencies": {a: one_agency(a) for a in AGENCIES}}
    # the check against the committed impact values
    sp_doc = figkit.doc("C04/sp.json")["impact"]
    sp = result["agencies"]["sp"]["point"]
    result["check_against_committed"] = {
        "rw_d2": {"here": sp["d2"]["rw"], "committed": sp_doc["rw_d2"]["value"]},
        "rw_d4": {"here": sp["d4"]["rw"], "committed": sp_doc["rw_d4"]["value"]},
        "lra_d2_ccc_c": {"here": sp["d2"]["lra"][6], "committed": sp_doc["lra_d2_ccc_c"]["value"]},
        "lra_d4_ccc_c": {"here": sp["d4"]["lra"][6], "committed": sp_doc["lra_d4_ccc_c"]["value"]},
    }
    for name, v in result["check_against_committed"].items():
        v["abs_diff"] = abs(v["here"] - v["committed"])
    (HERE / "definitions.json").write_text(json.dumps(result, indent=1), encoding="utf-8", newline="\n")
    print(json.dumps(result["check_against_committed"], indent=1))


if __name__ == "__main__":
    main()
