"""The results the figure and table scripts of this manuscript read: the compact JSON of the experiments, the committed
documents of cases C20 and C21 under ``data/derived``, and the small helpers that format a rate with its standard error.

Run the scripts from the repository root: ``python manuscripts/measured-corrections-of-validation-tests/make_tables.py``.
"""
from __future__ import annotations

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_shared"))
sys.path.insert(0, str(HERE / "experiments"))
import figkit  # noqa: E402

RESULTS = HERE / "experiments" / "results"
TABLES = HERE / "tables"
FIGURES = HERE / "figures"


def results(name: str) -> dict:
    return json.loads((RESULTS / f"{name}.json").read_text(encoding="utf-8"))


COVERAGE_RESULTS = results("coverage")
EXACT = results("exact")
SHIFT = results("shift")
SITUATION = results("situation")
SITUATION_INDEP = results("situation_indep")

#: The three window pairs of the main comparison (calibration rows, test rows); the test window is 0.1, 1 and 4 times the calibration.
PAIRS = {"A": (20000, 2000), "B": (2000, 2000), "C": (1000, 4000)}


def cov_cell(n: int, m: int, b: float = 1.0) -> dict:
    return next(c for c in COVERAGE_RESULTS["cells"] if c["n"] == n and c["m"] == m and abs(c["b"] - b) < 1e-9)


def shift_cell(n_eval: int, shift: float) -> dict:
    return next(c for c in SHIFT["cells"] if c["n_eval"] == n_eval and abs(c["shift"] - shift) < 1e-9)


def sit_cell(n: int, gap: float) -> dict:
    return next(c for c in SITUATION["cells"] if c["n"] == n and abs(c["gap"] - gap) < 1e-9)


def sit_indep_cell(n: int, bias: float) -> dict:
    return next(c for c in SITUATION_INDEP["cells"] if c["n"] == n and abs(c["bias"] - bias) < 1e-9)


def r3(x: float) -> str:
    return f"{x:.3f}"


def pm(rate: dict, digits: int = 3) -> str:
    """A rate with its standard error as a LaTeX math string, the form ``figkit.table`` passes through.

    A rate of 0 or 1 has a sample standard error of zero, which is not the uncertainty of the rate: it is printed as its count with the
    one-sided 95 percent bound of the rule of three, 3 / R. A rate below 0.005 is printed with four decimals.
    """
    reps = int(rate["reps"])
    hits = int(round(rate["rate"] * reps))
    count = f"{reps:,}".replace(",", "{,}")
    if hits == 0:
        return f"$0 \\text{{ of }} {count}\\ (<{3.0 / reps:.4f})$"
    if hits == reps:
        return f"${count} \\text{{ of }} {count}\\ (>{1.0 - 3.0 / reps:.4f})$"
    d = 4 if rate["rate"] < 0.005 else digits
    return f"${rate['rate']:.{d}f} \\pm {rate['se']:.{d}f}$"


def jload(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def oracle_fixed(n_eval: int, shift: float) -> dict:
    """A fixed cut on the raw drop set at the 95th percentile of the drops of the same cell without shift (size 0.05 by construction,
    in sample): the rate of ``drop > cut`` at ``shift``, with its standard error. The cut needs a simulation of the null, which a
    validation team does not have."""
    import numpy as np

    cut = float(np.percentile(shift_cell(n_eval, 0.0)["drops"], 95.0))
    drops = np.asarray(shift_cell(n_eval, shift)["drops"])
    r = float(np.mean(drops > cut))
    return {"rate": r, "se": (r * (1 - r) / len(drops)) ** 0.5, "reps": len(drops), "cut": cut}
