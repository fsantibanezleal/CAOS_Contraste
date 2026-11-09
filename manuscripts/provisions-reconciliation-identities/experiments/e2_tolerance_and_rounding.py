"""E2: false alarms of the gate on clean tables, by tolerance basis, and the rounding of the published tables.

    python manuscripts/provisions-reconciliation-identities/experiments/e2_tolerance_and_rounding.py

Data: the six committed C06 documents, and 200 clean books resampled from each (``common.resample``: every opening and
movement multiplied by ``1 + 0.25 eps``, every closing the exact sum), so 1,200 resampled books of the shape and the size of
the six dates. Clean tables are the case the gate must not flag. Part A judges the six committed tables and the 1,200
resampled books on seven tolerance bases: a fixed absolute tolerance of 1e-6, 1e-2 and 1 units of money, and a relative one
(``tolerance * max(1, G)``) of 1e-12, 1e-9, 1e-6 and 1e-4. Part B rounds every stored number of a resampled book to the nearest
multiple of s (units, thousands, millions), independently, as a table published in those units does, and judges the rounded
book on the engine's basis 1e-6 * G.

Predictions, written before the first run of this script (the author of the unit, 2026-11-07; the residuals of the six
committed tables had been printed by the product's notebook, so the first is a reproduction):

  Q1  a fixed absolute tolerance of 1e-6 units flags at least one of the six committed clean tables, and the relative basis
      1e-6 flags none of the six and none of the 1,200 resampled books;
  Q2  after rounding to s = 1, 10 and 1,000 units no book is flagged on the basis 1e-6; at s = 10,000 fewer than 1% are;
  Q3  at s = 100,000 between 30% and 95% of the books are flagged, and at s = 1,000,000 more than 99%.

The rounding error of an identity of about eleven terms has a standard deviation of about 0.96 s, against a limit of 47,000
to 117,000 units on these books; Q2 and Q3 are that arithmetic, written as a prediction on the engine's gate.
Repetitions: 200 per date, generator seeded ``[SEED_BASE, 2, date index, repetition]``.
"""
from __future__ import annotations

import sys
import time

import numpy as np

import common as c

REPS = 200
ABSOLUTE = (1e-6, 1e-2, 1.0)
RELATIVE = (1e-12, 1e-9, 1e-6, 1e-4)
STEPS = (1.0, 10.0, 1e3, 1e4, 1e5, 1e6)


def rounded(book: c.Book, step: float) -> c.Book:
    b = book.copy()

    def r(x: float) -> float:
        return round(x / step) * step

    for tab in (b.allowance, b.gca):
        for row in tab.values():
            row["opening"] = r(row["opening"])
            row["closing"] = r(row["closing"])
            row["movements"] = {k: r(v) for k, v in row["movements"].items()}
    for line in b.lines:
        line["amount"] = r(line["amount"])
    b.stage_ecl = {k: r(v) for k, v in b.stage_ecl.items()}
    return b


def judge(book: c.Book) -> dict[str, bool]:
    res = c.residuals(book)
    out = {f"abs:{a:g}": c.gate_absolute(res, a) for a in ABSOLUTE}
    out.update({f"rel:{t:g}": c.gate_full(res, c.limit(book, t)) for t in RELATIVE})
    return out


def main() -> int:
    t0 = time.perf_counter()
    books = c.committed_books()
    clean = {}
    for d, b in books.items():
        res = c.residuals(b)
        clean[d] = {"max_residual": max(res.values()), "gross": b.gross(), "relative_residual": max(res.values()) / b.gross(),
                    **{k: v for k, v in judge(b).items()}}
    bases = [f"abs:{a:g}" for a in ABSOLUTE] + [f"rel:{t:g}" for t in RELATIVE]
    resampled = {k: [0, 0] for k in bases}
    rel_resid: list[float] = []
    rounding = {f"{s:g}": {"flagged": [0, 0], "ratio_to_limit": [], "by_date": {d: 0 for d in c.DATES}} for s in STEPS}
    for di, d in enumerate(c.DATES):
        for k in range(REPS):
            b = c.resample(books[d], np.random.default_rng([c.SEED_BASE, 2, di, k]))
            for key, v in judge(b).items():
                resampled[key][0] += int(v)
                resampled[key][1] += 1
            rel_resid.append(max(c.residuals(b).values()) / b.gross())
            for s in STEPS:
                rb = rounded(b, s)
                res = c.residuals(rb)
                cell = rounding[f"{s:g}"]
                cell["flagged"][0] += int(c.gate_full(res, c.limit(rb)))
                cell["by_date"][d] += int(c.gate_full(res, c.limit(rb)))
                cell["flagged"][1] += 1
                cell["ratio_to_limit"].append(max(res.values()) / c.limit(rb))
    summary = {}
    for key, cell in rounding.items():
        a = np.array(cell["ratio_to_limit"])
        summary[key] = {"flagged": cell["flagged"], "by_date": cell["by_date"], "ratio_q50": float(np.quantile(a, 0.5)), "ratio_q90": float(np.quantile(a, 0.9)),
                        "ratio_q99": float(np.quantile(a, 0.99)), "ratio_max": float(a.max())}
    c.save("e2_tolerance_and_rounding.json", {
        "meta": {"reps": REPS, "dates": list(c.DATES), "absolute": list(ABSOLUTE), "relative": list(RELATIVE), "steps": list(STEPS),
                 "seed_base": c.SEED_BASE, "seconds": round(time.perf_counter() - t0, 1)},
        "committed": clean, "resampled": resampled,
        "resampled_relative_residual": {"max": float(max(rel_resid)), "median": float(np.median(rel_resid))},
        "rounding": summary})
    print("done in", round(time.perf_counter() - t0, 1), "s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
