"""Experiment 4: the post-shock floor of the UR, which binds on no committed curve, made to bind by translating the real curve.

On the committed curves of 2026-09-03 no floor binds (the closest post-shock UR rate is 20.48 bp from the floor of -2 percent), so the
effect of the floor on a measure is not demonstrated by the committed documents. The raw files hold one month, so no historical low-rate
curve is available. This experiment therefore translates the fitted UR curve down by a stated number of basis points (a what-if on the level
of the real curve, not a forecast and not a historical curve) and measures, with the engine, the Annex 1 measures with the UR floor of -2
percent, with no floor on either leg, and with the peso floor of 0 on the UR.

The prediction below was written into this header by the author before the script was first run (no version control history shows that order).

* H5 (a floor never raises the measure). For every variant, every translation and every seed, the Annex 1 delta EVE and delta NII with the
  floor of -2 percent are at most the measures with no floor (relative tolerance 1e-9). One exception refutes it.

The variants are the six of the case, 20 seeds of the repricing profiles per variant (seeds 201 to 220) and the translations 0, -25, -50,
-100, -150, -200, -250 and -300 bp of the UR curve; the peso curve is not moved.

Run from the repository root with the raw files in ``CONTRASTE_DATA``::

    python manuscripts/uf-as-its-own-currency-in-irrbb/experiments/exp_floors.py

It writes ``experiments/floors.json`` (the run time is measured).
"""
from __future__ import annotations

import argparse
import json
import time

import numpy as np

import uf_core as u

SEEDS = tuple(range(201, 221))
SHIFTS = (0.0, -25.0, -50.0, -100.0, -150.0, -200.0, -250.0, -300.0)


def lowest_ur_rates(book, ctx):
    """The lowest unfloored post-shock UR rate over the six EVE shocks and the two NII shocks, and its distance to the floor in bp."""
    z = u.shocks.shock_size("CLF", "cmf-annex1")
    r0 = ctx.fits["UR"].rates
    low = []
    for s in u.SHOCKS:
        shape = u.shocks.shock_curve(s, z.parallel_bp, z.short_bp, z.long_bp, u.MID)
        low.append(float(u.shocks.apply_floor(r0, shape, None).min()))
    for bp in (u.NII_BP, -u.NII_BP):
        low.append(float(u.shocks.apply_floor(r0, np.full(19, bp), None)[:6].min()))
    return min(low), (min(low) - u.vt.UR_FLOOR) * 1e4


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=None)
    args = ap.parse_args()
    t0 = time.perf_counter()
    raw = u.load_raw(args.data)
    out: dict = {"seeds": list(SEEDS), "shifts_bp": list(SHIFTS), "ur_floor": u.vt.UR_FLOOR, "results": {}}
    raises = {"checked": 0, "violations": 0, "max_increase": 0.0, "examples": []}
    for shift in SHIFTS:
        ctx = u.context(raw, level_shift_bp=shift)
        per_var = {}
        for vid in u.bk.SPECS:
            rec = {k: [] for k in ("eve_floor", "eve_none", "eve_peso", "nii_floor", "nii_none", "nii_peso", "dist", "binds")}
            n_raise = {"eve": 0, "nii": 0}
            n_lower = {"eve": 0, "nii": 0}
            for seed in SEEDS:
                book = u.book_of(vid, seed, ctx)
                tr = u.ANNEX1
                vals = {}
                for name, ov in (("floor", None), ("none", {"UR": None, "CLP": None}), ("peso", {"UR": u.vt.OTHER_FLOOR})):
                    d = u.leg_deltas(book, ctx, tr, ov)
                    vals[name] = u.aggregate(d, tr)
                low, dist = lowest_ur_rates(book, ctx)
                rec["dist"].append(dist)
                rec["binds"].append(int(dist <= 0.0))
                for key in ("eve", "nii"):
                    rec[f"{key}_floor"].append(vals["floor"][f"delta_{key}"])
                    rec[f"{key}_none"].append(vals["none"][f"delta_{key}"])
                    rec[f"{key}_peso"].append(vals["peso"][f"delta_{key}"])
                    raises["checked"] += 1
                    inc = vals["floor"][f"delta_{key}"] - vals["none"][f"delta_{key}"]
                    if inc < -1e-9 * max(1.0, abs(vals["none"][f"delta_{key}"])):
                        n_lower[key] += 1
                    if inc > 1e-9 * max(1.0, abs(vals["none"][f"delta_{key}"])):
                        n_raise[key] += 1
                        raises["violations"] += 1
                        raises["max_increase"] = max(raises["max_increase"], inc)
                        if len(raises["examples"]) < 6:
                            raises["examples"].append({"variant": vid, "shift_bp": shift, "seed": seed, "measure": key,
                                                       "with_floor": vals["floor"][f"delta_{key}"], "no_floor": vals["none"][f"delta_{key}"]})

            def ms(x):
                m, hw, sd = u.mean_ci(np.array(x))
                return {"mean": m, "ci_half": hw, "sd": sd}

            eff_eve = np.array(rec["eve_floor"]) - np.array(rec["eve_none"])
            eff_nii = np.array(rec["nii_floor"]) - np.array(rec["nii_none"])
            per_var[vid] = {"books_where_floor_raises_eve": n_raise["eve"], "books_where_floor_raises_nii": n_raise["nii"],
                            "books_where_floor_lowers_eve": n_lower["eve"], "books_where_floor_lowers_nii": n_lower["nii"],
                            "distance_bp": ms(rec["dist"]), "share_of_seeds_binding": float(np.mean(rec["binds"])),
                            "eve_with_floor": ms(rec["eve_floor"]), "eve_no_floor": ms(rec["eve_none"]), "eve_effect": ms(eff_eve),
                            "nii_with_floor": ms(rec["nii_floor"]), "nii_no_floor": ms(rec["nii_none"]), "nii_effect": ms(eff_nii),
                            "eve_with_peso_floor": ms(rec["eve_peso"]), "nii_with_peso_floor": ms(rec["nii_peso"])}
        out["results"][f"{shift:+.0f}"] = per_var
    out["h5_floor_never_raises"] = raises
    out["seconds"] = time.perf_counter() - t0
    (u.HERE / "floors.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"wrote floors.json in {out['seconds']:.1f} s; H5 {raises['violations']} of {raises['checked']} raise, max increase {raises['max_increase']:.1f}")


if __name__ == "__main__":
    main()
