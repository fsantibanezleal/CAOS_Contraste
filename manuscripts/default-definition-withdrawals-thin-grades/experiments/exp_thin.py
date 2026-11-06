"""Experiment 3: thin grades, by exact enumeration (no random numbers).

For a grade with true one-year PD p and n obligors the number of defaults is Binomial(n, p). The coverage of an interval
at p is the sum of the binomial probabilities of the counts whose interval holds p; ``riskvalidation.transitions.intervals
.exact_coverage`` computes it by enumerating the counts. The committed document ``data/derived/C04/thin.json`` holds it
for n = 50, 100, 200, 500, 1000 at the seven grades' PDs of the C04 generator. This script adds:

* the coverage on a grid of n from 50 to 50,000, to find where each interval reaches 90% and 95% by grade;
* the coverage at the cohort sizes of the generator itself (S&P-like cohorts, ``generator.obligors``);
* the closed form of the Wald interval's coverage of a small PD, 1 - (1 - p)^n, against the enumerated value (the
  Proposition of the Theory section), and the closed form of the Jeffreys interval's lower bound P(X = 0) = (1 - p)^n.

Run from the repository root::

    E:/_venvs/contraste-u16-i/Scripts/python.exe manuscripts/default-definition-withdrawals-thin-grades/experiments/exp_thin.py

It writes ``experiments/thin.json`` and takes under a minute.
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "manuscripts" / "_shared"))

import figkit  # noqa: E402
from riskvalidation.transitions.intervals import exact_coverage  # noqa: E402

GRID = (50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000)
METHODS = ("wald", "agresti_coull", "jeffreys")
LEVEL = 0.95


def main() -> None:
    thin = figkit.doc("C04/thin.json")["outputs"]
    pd1 = np.array(thin["generator"]["pd_1y"], dtype=float)
    sizes = [int(x) for x in thin["generator"]["obligors"]]
    grades = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC-C"]
    out: dict = {"level": LEVEL, "grades": grades, "pd_1y": pd1.tolist(), "grid": list(GRID), "coverage_grid": {},
                 "length_grid": {}}
    for method in METHODS:
        cov, length = [], []
        for n in GRID:
            ex = exact_coverage(method, n, pd1, level=LEVEL)
            cov.append([float(x) for x in ex["coverage"]])
            length.append([float(x) for x in ex["expected_length"]])
        out["coverage_grid"][method] = cov
        out["length_grid"][method] = length
    # the cohort sizes of the generator itself
    out["generator_sizes"] = sizes
    out["coverage_at_generator_sizes"] = {}
    for method in METHODS:
        out["coverage_at_generator_sizes"][method] = [
            float(exact_coverage(method, sizes[g], pd1, level=LEVEL)["coverage"][g]) for g in range(7)]
    # the closed forms against the enumeration, for the three smallest PDs (AAA, AA, A) over the grid
    closed = []
    for n_i, n in enumerate(GRID):
        row = {"n": n, "p": pd1.tolist(),
               "closed_form_wald": (1.0 - (1.0 - pd1) ** n).tolist(),
               "enumerated_wald": out["coverage_grid"]["wald"][n_i],
               "closed_form_jeffreys_lower": ((1.0 - pd1) ** n).tolist(),
               "enumerated_jeffreys": out["coverage_grid"]["jeffreys"][n_i],
               "np": (n * pd1).tolist()}
        closed.append(row)
    out["closed_forms"] = closed
    # the first grid size at which each interval reaches a coverage target, by grade
    first = {}
    for target in (0.90, 0.95):
        first[f"{target:.2f}"] = {}
        for method in METHODS:
            cov = np.array(out["coverage_grid"][method])
            res = []
            for g in range(7):
                hit = [GRID[i] for i in range(len(GRID)) if cov[i, g] >= target]
                res.append(hit[0] if hit else None)
            first[f"{target:.2f}"][method] = res
    out["first_grid_n_reaching"] = first
    (HERE / "thin.json").write_text(json.dumps(out, indent=1), encoding="utf-8", newline="\n")
    print(json.dumps(first, indent=1))


if __name__ == "__main__":
    main()
