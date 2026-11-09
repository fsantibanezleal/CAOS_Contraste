"""Experiment 1: the committed C15 documents reproduced by independent engine calls, and the single-currency counterfactual of the same flows.

The statements of the SDD item on the UF as its own currency were written after the C15 bake (the item entered the SDD on 2026-10-21, the
documents on 2026-10-16), so no outcome of this experiment could have refuted them: the experiment reproduces them (``R1`` to ``R4`` of
the manuscript) and does not test them. What it adds, with the engine's functions on the committed flows:

* the contract test of this module: the Annex 1 treatment of ``uf_core`` equals the committed delta EVE, delta NII, charge and margin of the
  six variants to a relative 1e-12;
* the single-currency treatment of the same flows (the notebook's counterfactual) and the aggregation of the Basel standard (positive parts),
  and the gap measures of the engine, on the six variants;
* the prioritised-bank classification under each treatment;
* the value of the UF leg on its real curve against the peso curve (the consistency of the discount curve with the unit of account);
* the check of the sandwich of the Theory section on the leg deltas of every variant.

Run from the repository root with the raw files in ``CONTRASTE_DATA``::

    python manuscripts/uf-as-its-own-currency-in-irrbb/experiments/exp_reproduce.py

It writes ``experiments/reproduce.json`` (run times measured, in seconds).
"""
from __future__ import annotations

import argparse
import json
import time

import numpy as np

import uf_core as u


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=None)
    args = ap.parse_args()
    t0 = time.perf_counter()
    raw = u.load_raw(args.data)
    ctx = u.context(raw)
    out: dict = {"valuation_date": ctx.date, "uf_value": ctx.uf, "seed": u.CASE_SEED, "variants": {}}
    worst = 0.0
    sandwich = {"checked": 0, "violations": 0, "max_violation": 0.0}
    for vid in u.bk.SPECS:
        book = u.book_of(vid, u.CASE_SEED, ctx)
        c = u.committed(vid)
        d = u.leg_deltas(book, ctx, u.ANNEX1)
        a = u.aggregate(d, u.ANNEX1)
        s_tr = u.measures(book, ctx, u.SINGLE)
        pp = u.positive_parts(d)
        gap = u.gap_measures(book, ctx)
        margin = u.margin_12m(book, ctx)
        com_margin = c["thresholds"]["net_interest_and_indexation_margin_12m"]
        dev = {
            "delta_eve": abs(a["delta_eve"] - c["eve"]["delta_eve"]) / c["eve"]["delta_eve"],
            "delta_nii": abs(a["delta_nii"] - c["nii"]["delta_nii"]) / c["nii"]["delta_nii"],
            "charge": abs(a["charge"] - c["nii"]["indexation_charge"]) / c["nii"]["indexation_charge"],
            "margin": abs(margin - com_margin) / com_margin,
        }
        worst = max(worst, *dev.values())
        # the leg deltas of every shock against the committed pairs
        leg_dev = 0.0
        for k, row in enumerate(c["eve"]["rows"]):
            leg_dev = max(leg_dev, abs(d["eve"]["CLP"][k] - row["pair"]["delta_clp"]), abs(d["eve"]["UR"][k] - row["pair"]["delta_ur"]))
        for k, row in enumerate(c["nii"]["rows"]):
            leg_dev = max(leg_dev, abs(d["nii"]["CLP"][k] - row["pair"]["delta_clp"]), abs(d["nii"]["UR"][k] - row["pair"]["delta_ur"]))
        # the sandwich: the sum of the legs <= the pair rule <= the positive parts, shock by shock, for the eight curve/size/floor treatments
        for bits in np.ndindex(2, 2, 2):
            tr = u.Treatment(bool(bits[0]), bool(bits[1]), bool(bits[2]), True, False)
            dd = u.leg_deltas(book, ctx, tr)
            for key, n in (("eve", 6), ("nii", 2)):
                for i in range(n):
                    x, y = dd[key]["CLP"][i], dd[key]["UR"][i]
                    lo, mid, hi = max(x + y, 0.0), eve_pair(x, y), max(x, 0.0) + max(y, 0.0)
                    sandwich["checked"] += 1
                    viol = max(lo - mid, mid - hi, 0.0)
                    if viol > 1e-9 * max(1.0, abs(mid)):
                        sandwich["violations"] += 1
                        sandwich["max_violation"] = max(sandwich["max_violation"], viol)
        t1 = book.tier1
        cls = {
            "annex1": u.prioritised(book, ctx, a, margin),
            "single": u.prioritised(book, ctx, s_tr, margin),
            "positive_parts": u.prioritised(book, ctx, {"delta_eve": pp["delta_eve"], "delta_nii": pp["delta_nii"]}, margin),
        }
        # the gross present value of the UF assets and of the UF liabilities on the UF curve and on the peso curve, in pesos
        p = u._prepare(book, ctx)
        pv = {}
        for side, sign in (("asset", 1.0), ("liability", -1.0)):
            flows = sum(it.flows * ctx.uf for it in p["items"]["UR"] if it.side == side) * sign
            pv[side] = {"real_curve": float(u.eve_nii.eve(flows, ctx.fits["UR"].rates, u.MID)),
                        "peso_curve": float(u.eve_nii.eve(flows, ctx.fits["CLP"].rates, u.MID))}
            pv[side]["understatement_percent"] = 100.0 * (1.0 - pv[side]["peso_curve"] / pv[side]["real_curve"])
        out["variants"][vid] = {
            "tier1": t1, "pn_ur": d["pn_ur"], "net_uf_share_tier1": d["pn_ur"] / t1, "margin_12m": margin,
            "annex1": {"delta_eve": a["delta_eve"], "delta_nii": a["delta_nii"], "max_pair": a["max_pair"], "charge": a["charge"]},
            "single": {"delta_eve": s_tr["delta_eve"], "delta_nii": s_tr["delta_nii"]},
            "positive_parts": pp, "gap": gap,
            "committed": {"delta_eve": c["eve"]["delta_eve"], "delta_nii": c["nii"]["delta_nii"], "charge": c["nii"]["indexation_charge"],
                          "closest_floor_bp": min(x["distance_bp"] for x in c["floors"]["distances"]),
                          "floor_effects": len(c["floors"]["effects"]), "cpi_effect": (c["cpi_scenario"] or {}).get("effect")},
            "relative_deviation": dev, "max_leg_delta_deviation": leg_dev,
            "ratio_nii_annex_over_single": a["delta_nii"] / s_tr["delta_nii"],
            "eve_shortfall_single_percent": 100.0 * (1.0 - s_tr["delta_eve"] / a["delta_eve"]),
            "charge_share_of_nii": a["charge"] / a["delta_nii"],
            "classification": cls,
            "ratios_tier1": {k: {"nii": v_nii / t1, "eve": v_eve / t1} for k, (v_nii, v_eve) in
                             {"annex1": (a["delta_nii"], a["delta_eve"]), "single": (s_tr["delta_nii"], s_tr["delta_eve"]),
                              "positive_parts": (pp["delta_nii"], pp["delta_eve"])}.items()},
            "ur_leg_gross_pv": pv,
        }
    out["max_relative_deviation"] = worst
    out["sandwich"] = sandwich
    out["seconds"] = time.perf_counter() - t0
    path = u.HERE / "reproduce.json"
    path.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"wrote {path.name}: max relative deviation {worst:.2e}, sandwich {sandwich}, {out['seconds']:.1f} s")


def eve_pair(x: float, y: float) -> float:
    return float(u.eve_nii.cmf_pair(x, y, True))


if __name__ == "__main__":
    main()
