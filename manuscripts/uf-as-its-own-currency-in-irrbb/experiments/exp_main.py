"""Experiment 2: the main comparison and the ablation, on 30 synthetic banks of each variant.

The predictions below were written into this header by the author of the manuscript before this script was first run; no version
control history can show that order (the manuscript is committed by the main session after the run), so they are the author's word.

Restated on 2026-11-08 after review and after the runs: the text of H1 was narrowed from every shock to the two aggregated measures, and the
statement of H1 is therefore a statement revised after its result, not a prediction.

* H1 (the sandwich). For every variant, every seed and every treatment, the sum of the two legs is at most the Annex 1 pair rule, which
  is at most the sum of the positive parts, for the two measures (each the maximum over its scenarios, aggregated per treatment; the
  check is on the two aggregated measures and not on each scenario). One violation beyond a relative 1e-9 refutes it.
* H2 (the attribution of the delta EVE gap). In the three variants whose net UF position is 30 percent of Tier 1 (long UF, short UF,
  offset on and off), the switch that replaces the plain sum of the legs by the pair rule has the largest absolute exact Shapley value of the
  five switches for the delta EVE, in the mean over the seeds. It is refuted in any of the three variants in which another switch has the
  larger absolute mean value.
* H3 (the comparators). The Annex 1 delta NII exceeds the delta NII of the single-currency treatment and of the Basel positive-part
  aggregation, and the Annex 1 delta EVE does not fall below the single-currency one, in every variant and every seed. One exception refutes it.
  H3 was written after ``exp_reproduce.py`` had printed the values of the committed seed, in which the CLP steepener variant already has the
  Annex 1 delta NII below the positive-part one (6,783 against 8,415); it is therefore not a prediction that the data could have confirmed, and
  the manuscript reports it as a statement refuted in that clause.

Everything the experiment compares is run here on the same flows: the Annex 1 measure (all switches on), the single-currency treatment (all
off), the positive-part aggregation of the Basel standard with the case's curves, sizes and floors and no charge, and the repricing-gap and
duration-gap measures of the engine. The 32 treatments of the factorial give the exact Shapley values, the one-at-a-time removal from
Annex 1 and the one-at-a-time addition to the single currency.

Run from the repository root with the raw files in ``CONTRASTE_DATA``::

    python manuscripts/uf-as-its-own-currency-in-irrbb/experiments/exp_main.py

It writes ``experiments/main.json`` (the run time is measured).
"""
from __future__ import annotations

import argparse
import json
import time

import numpy as np

import uf_core as u

SEEDS = tuple(range(1, 31))
VARIANTS = tuple(u.bk.SPECS)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=None)
    args = ap.parse_args()
    t0 = time.perf_counter()
    raw = u.load_raw(args.data)
    ctx = u.context(raw)
    out: dict = {"valuation_date": ctx.date, "seeds": list(SEEDS), "case_seed": u.CASE_SEED, "switches": list(u.SWITCHES), "variants": {}}
    sand = {"checked": 0, "violations": 0}
    h3 = {"checked": 0, "violations": 0, "by_variant": {}}
    for vid in VARIANTS:
        rec: dict[str, list] = {k: [] for k in ("annex_eve", "annex_nii", "single_eve", "single_nii", "pos_eve", "pos_nii", "gap_nii", "gap_eve",
                                                "charge", "max_pair", "tier1", "pn_ur", "margin")}
        sh = {"delta_eve": {s: [] for s in u.SWITCHES}, "delta_nii": {s: [] for s in u.SWITCHES}}
        loo = {"delta_eve": {s: [] for s in u.SWITCHES}, "delta_nii": {s: [] for s in u.SWITCHES}}
        aoi = {"delta_eve": {s: [] for s in u.SWITCHES}, "delta_nii": {s: [] for s in u.SWITCHES}}
        for seed in (*SEEDS, u.CASE_SEED):
            book = u.book_of(vid, seed, ctx)
            fac = u.factorial(book, ctx)
            full, none = fac[tuple(sorted(u.SWITCHES))], fac[()]
            d = u.leg_deltas(book, ctx, u.ANNEX1)
            pp = u.positive_parts(d)
            gap = u.gap_measures(book, ctx)
            for key in ("delta_eve", "delta_nii"):
                sv = u.shapley(fac, key)
                assert abs(sum(sv.values()) - (full[key] - none[key])) < 1e-6 * max(1.0, abs(full[key])), "Shapley values must add up"
            if seed == u.CASE_SEED:
                out.setdefault("case_seed_values", {})[vid] = {
                    "annex1": {k: full[k] for k in ("delta_eve", "delta_nii", "charge", "max_pair")}, "single": {k: none[k] for k in ("delta_eve", "delta_nii")},
                    "shapley": {k: u.shapley(fac, k) for k in ("delta_eve", "delta_nii")},
                    "leave_one_out": {k: {s: full[k] - fac[tuple(sorted(set(u.SWITCHES) - {s}))][k] for s in u.SWITCHES} for k in ("delta_eve", "delta_nii")},
                    "add_one_in": {k: {s: fac[(s,)][k] - none[k] for s in u.SWITCHES} for k in ("delta_eve", "delta_nii")},
                    "positive_parts": pp, "gap": gap}
                continue
            rec["annex_eve"].append(full["delta_eve"])
            rec["annex_nii"].append(full["delta_nii"])
            rec["single_eve"].append(none["delta_eve"])
            rec["single_nii"].append(none["delta_nii"])
            rec["pos_eve"].append(pp["delta_eve"])
            rec["pos_nii"].append(pp["delta_nii"])
            rec["gap_nii"].append(gap["delta_nii_gap"])
            rec["gap_eve"].append(gap["delta_eve_duration"])
            rec["charge"].append(full["charge"])
            rec["max_pair"].append(full["max_pair"])
            rec["tier1"].append(full["tier1"])
            rec["pn_ur"].append(full["pn_ur"])
            rec["margin"].append(u.margin_12m(book, ctx))
            for key in ("delta_eve", "delta_nii"):
                sv = u.shapley(fac, key)
                for s in u.SWITCHES:
                    sh[key][s].append(sv[s])
                    loo[key][s].append(full[key] - fac[tuple(sorted(set(u.SWITCHES) - {s}))][key])
                    aoi[key][s].append(fac[(s,)][key] - none[key])
            # H1 on every treatment of the factorial: sum <= pair <= positive parts is checked on the leg deltas of the eight non-aggregation treatments
            for bits in np.ndindex(2, 2, 2):
                tr = u.Treatment(bool(bits[0]), bool(bits[1]), bool(bits[2]), True, False)
                dd = u.leg_deltas(book, ctx, tr)
                pair = u.aggregate(dd, tr)
                net = u.aggregate(dd, u.Treatment(*bits, False, False))
                pos = u.positive_parts(dd)
                for key in ("delta_eve", "delta_nii"):
                    sand["checked"] += 1
                    tol = 1e-9 * max(1.0, abs(pair[key]))
                    if net[key] > pair[key] + tol or pair[key] > pos[key] + tol:
                        sand["violations"] += 1
            h3["checked"] += 1
            clauses = {"nii_over_single": full["delta_nii"] > none["delta_nii"], "nii_over_positive_parts": full["delta_nii"] > pp["delta_nii"],
                       "eve_not_below_single": full["delta_eve"] >= none["delta_eve"] - 1e-9}
            row = h3["by_variant"].setdefault(vid, {k: 0 for k in clauses})
            for k, ok in clauses.items():
                row[k] += 0 if ok else 1
            if not all(clauses.values()):
                h3["violations"] += 1

        def summ(x):
            m, hw, sd = u.mean_ci(np.array(x))
            return {"mean": m, "ci_half": hw, "sd": sd}

        agg = {k: summ(v) for k, v in rec.items()}
        ratio_nii = np.array(rec["annex_nii"]) / np.array(rec["single_nii"])
        short_eve = 100.0 * (1.0 - np.array(rec["single_eve"]) / np.array(rec["annex_eve"]))
        share = np.array(rec["charge"]) / np.array(rec["annex_nii"])
        t1 = np.array(rec["tier1"])
        agg["ratio_nii_annex_over_single"] = summ(ratio_nii)
        agg["eve_shortfall_single_percent"] = summ(short_eve)
        agg["charge_share_of_nii"] = summ(share)
        agg["annex_nii_over_tier1"] = summ(np.array(rec["annex_nii"]) / t1)
        agg["annex_eve_over_tier1"] = summ(np.array(rec["annex_eve"]) / t1)
        agg["pos_over_annex_eve"] = summ(np.array(rec["pos_eve"]) / np.array(rec["annex_eve"]))
        agg["pos_over_annex_nii"] = summ(np.array(rec["pos_nii"]) / np.array(rec["annex_nii"]))
        agg["gap_over_annex_nii"] = summ(np.array(rec["gap_nii"]) / np.array(rec["annex_nii"]))
        agg["gap_over_annex_eve"] = summ(np.array(rec["gap_eve"]) / np.array(rec["annex_eve"]))
        agg["single_over_annex_eve"] = summ(np.array(rec["single_eve"]) / np.array(rec["annex_eve"]))
        out["variants"][vid] = {
            "summary": agg,
            "shapley": {k: {s: summ(v) for s, v in d.items()} for k, d in sh.items()},
            "leave_one_out": {k: {s: summ(v) for s, v in d.items()} for k, d in loo.items()},
            "add_one_in": {k: {s: summ(v) for s, v in d.items()} for k, d in aoi.items()},
        }
    out["h1_sandwich"] = sand
    out["h3_comparators"] = h3
    h2 = {}
    for vid in ("long-uf", "short-uf", "offset-on-off"):
        means = {s: out["variants"][vid]["shapley"]["delta_eve"][s]["mean"] for s in u.SWITCHES}
        top = max(means, key=lambda s: abs(means[s]))
        h2[vid] = {"largest_absolute": top, "means": means}
    out["h2_eve_attribution"] = h2
    out["seconds"] = time.perf_counter() - t0
    (u.HERE / "main.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"wrote main.json in {out['seconds']:.1f} s; H1 {sand}; H3 {h3}")
    for vid, r in h2.items():
        print(vid, r["largest_absolute"], {k: round(v) for k, v in r["means"].items()})


if __name__ == "__main__":
    main()
