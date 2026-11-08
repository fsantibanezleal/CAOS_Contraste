"""Experiment 3: the size of the net UF position, and whether the treatment changes who is prioritised.

The prediction below was written into this header by the author before the script was first run (no version control history shows that order).

Restated on 2026-11-08 after review and after the runs: the decision rule below and its refutation clause were written out after the runs as
the criterion of the statement; the statement itself is the one first written.

* H4 (a different supervisory outcome). There is a net UF position, as a share of Tier 1 inside the range the generator can balance, at
  which the Annex 1 treatment flags the bank as prioritised under at least one of the three tests of Annex 1 in most books (more than half
  of the seeds) while the single-currency treatment of the same flows flags it in none. It is decided by that criterion: a position
  qualifies only when Annex 1 flags more than half of the 20 books and the single-currency treatment flags none of them. It is refuted when no
  position of the range qualifies. The script also records, as a separate quantity, the positions at which more than half of the books are
  classified differently (flagged by Annex 1 and not by the single-currency treatment) and the first position at which any book is.

The book is the case's generator at the variant parameters of the long UF variant, with only ``net_uf_share_tier1`` changed over a grid from
-1.5 to 1.5 in steps of 0.1 (positions the generator cannot balance are refused by it and listed), 20 seeds of the repricing profiles per
position (seeds 101 to 120), on the curves of the valuation date. A pair is flagged when the engine's ``prioritised_bank`` reports a breach.

Run from the repository root with the raw files in ``CONTRASTE_DATA``::

    python manuscripts/uf-as-its-own-currency-in-irrbb/experiments/exp_sweep.py

It writes ``experiments/sweep.json`` (the run time is measured).
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import time

import numpy as np

import uf_core as u

SEEDS = tuple(range(101, 121))
GRID = tuple(round(x, 2) for x in np.arange(-1.5, 1.5001, 0.1))
TESTS = ("nii-tier1", "eve-tier1", "nii-margin")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=None)
    args = ap.parse_args()
    t0 = time.perf_counter()
    raw = u.load_raw(args.data)
    ctx = u.context(raw)
    base_spec = u.bk.SPECS["long-uf"]
    out: dict = {"valuation_date": ctx.date, "seeds": list(SEEDS), "grid": list(GRID), "positions": {}, "refused": []}
    h4_positions, majority_differ, first_differ = [], [], None
    for nu in GRID:
        spec = dataclasses.replace(base_spec, id=f"sweep{nu:+.2f}", params={**base_spec.params, "net_uf_share_tier1": nu})
        rows = {"annex1": {t: 0 for t in TESTS}, "single": {t: 0 for t in TESTS}, "positive_parts": {t: 0 for t in TESTS}}
        any_flag = {"annex1": 0, "single": 0, "positive_parts": 0}
        annex_only = 0
        ratios_nii, ratios_eve, nii_t1_a, nii_t1_s, eve_t1_a, eve_t1_s, n_ok = [], [], [], [], [], [], 0
        try:
            u.bk.build_book(SEEDS[0], spec, ctx.uf)
        except u.bk.BookError as e:
            out["refused"].append({"net_uf_share_tier1": nu, "reason": str(e)[:160]})
            continue
        for seed in SEEDS:
            book = u.bk.build_book(seed, spec, ctx.uf)
            a = u.measures(book, ctx, u.ANNEX1)
            s = u.measures(book, ctx, u.SINGLE)
            pp = u.positive_parts(u.leg_deltas(book, ctx, u.ANNEX1))
            m = u.margin_12m(book, ctx)
            cls = {"annex1": u.prioritised(book, ctx, a, m), "single": u.prioritised(book, ctx, s, m),
                   "positive_parts": u.prioritised(book, ctx, pp, m)}
            for name, c in cls.items():
                for t in TESTS:
                    rows[name][t] += int(c[t])
                any_flag[name] += int(any(c.values()))
            annex_only += int(any(cls["annex1"].values()) and not any(cls["single"].values()))
            ratios_nii.append(a["delta_nii"] / s["delta_nii"] if s["delta_nii"] > 0 else float("nan"))
            ratios_eve.append(a["delta_eve"] / s["delta_eve"] if s["delta_eve"] > 0 else float("nan"))
            nii_t1_a.append(a["delta_nii"] / book.tier1)
            nii_t1_s.append(s["delta_nii"] / book.tier1)
            eve_t1_a.append(a["delta_eve"] / book.tier1)
            eve_t1_s.append(s["delta_eve"] / book.tier1)
            n_ok += 1

        def ms(x):
            m_, hw, sd = u.mean_ci(np.array(x))
            return {"mean": m_, "ci_half": hw, "sd": sd}

        out["positions"][f"{nu:+.2f}"] = {
            "net_uf_share_tier1": nu, "n": n_ok, "flag_counts": rows, "any_flag": any_flag, "annex_flagged_single_not": annex_only,
            "ratio_nii_annex_over_single": ms(ratios_nii), "ratio_eve_annex_over_single": ms(ratios_eve),
            "annex_nii_over_tier1": ms(nii_t1_a), "single_nii_over_tier1": ms(nii_t1_s),
            "annex_eve_over_tier1": ms(eve_t1_a), "single_eve_over_tier1": ms(eve_t1_s)}
        if any_flag["annex1"] > n_ok / 2 and any_flag["single"] == 0:
            h4_positions.append(nu)
        if annex_only > n_ok / 2:
            majority_differ.append(nu)
        if annex_only > 0 and first_differ is None:
            first_differ = nu
    out["h4_positions_where_annex_flags_and_single_does_not"] = h4_positions
    out["positions_where_most_books_are_classified_differently"] = majority_differ
    out["first_position_with_a_differing_book"] = first_differ
    feasible = [p["net_uf_share_tier1"] for p in out["positions"].values()]
    out["feasible_range"] = [min(feasible), max(feasible)] if feasible else None
    out["seconds"] = time.perf_counter() - t0
    (u.HERE / "sweep.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"wrote sweep.json in {out['seconds']:.1f} s; feasible {out['feasible_range']}; H4 positions {h4_positions}; most books differ at {majority_differ}; first differing book at {first_differ}; refused {len(out['refused'])}")


if __name__ == "__main__":
    main()
