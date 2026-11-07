"""The cross-check of ``extended_study.py`` against the product's committed study function: on the same seed and the same
repetitions, the coverage of the five treatments of ``c04_bounds.bounds_rung`` (first-year, pooled and ten-fold designs)
must equal the coverage the extended study computes. Run from the repository root::

    python manuscripts/anchored-pd-under-informative-withdrawals/experiments/crosscheck_pipeline.py

Exit code 0 when every coverage agrees to the last repetition, 1 otherwise.
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import extended_study as ex  # noqa: E402

REPS = 40
INFORMATIVE = 9.0


def main() -> int:
    q, ob = ex.load_generator()
    seed, big_seed = 20261104, 20261105
    ref = ex.bnd.bounds_rung(ex.fam._paths, q, ob, seed=seed, scale_seed=big_seed, reps=REPS, informative=INFORMATIVE,
                             withdrawal_rate=ex.WITHDRAWAL_RATE, window=ex.WINDOW)
    mine: dict[str, ex.Cell] = {}
    latent = ex.fam._paths(q, ob)
    truth = np.asarray(latent.truth()["pd_by_grade"]["1"], float)
    observed = ex.fam._paths(q, ob, withdrawal_rate=ex.WITHDRAWAL_RATE, informative=INFORMATIVE, window=ex.WINDOW)
    mine["first_year"] = ex.Cell("first_year", REPS, truth, {})
    mine["pooled"] = ex.Cell("pooled", REPS, truth, {})
    for ch in np.random.SeedSequence(seed).spawn(REPS):
        steps, follow = ex.draw(latent, observed, ch)
        c0, w0 = steps[0]["counts"], np.asarray(steps[0]["withdrawn"], float)
        mine["first_year"].add(ex.evaluate(c0, w0, follow[0], follow[0]))
        cp = sum(s["counts"] for s in steps)
        wp = sum(np.asarray(s["withdrawn"], float) for s in steps)
        mine["pooled"].add(ex.evaluate(cp, wp, sum(follow), sum(follow)))
    big = [int(o) * ex.bnd.SCALE for o in ob]
    lat10 = ex.fam._paths(q, big, 1)
    obs10 = ex.fam._paths(q, big, 1, withdrawal_rate=ex.WITHDRAWAL_RATE, informative=INFORMATIVE, window=ex.WINDOW)
    mine["first_year_x10"] = ex.Cell("first_year_x10", REPS, truth, {})
    for ch in np.random.SeedSequence(big_seed).spawn(REPS):
        steps, follow = ex.draw(lat10, obs10, ch)
        c0, w0 = steps[0]["counts"], np.asarray(steps[0]["withdrawn"], float)
        mine["first_year_x10"].add(ex.evaluate(c0, w0, follow[0], follow[0]))
    bad = 0
    for design in ref["designs"]:
        if design["id"] not in mine:
            continue  # capture70 thins the count with a stream of its own; the capture ladder is not cross-checked
        cell = mine[design["id"]].summary()
        for t in design["treatments"]:
            if t["id"] == "identified" or t["id"] in cell["treatments"]:
                theirs = [c["rate"] for c in t["coverage"]]
                ours = cell["treatments"][t["id"]]["coverage"]
                ok = np.allclose(theirs, ours, atol=1e-4)
                bad += 0 if ok else 1
                print(f"{design['id']:15s} {t['id']:11s} {'equal' if ok else 'DIFFERENT'}")
    print("cross-check:", "passed" if bad == 0 else f"{bad} mismatches")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
