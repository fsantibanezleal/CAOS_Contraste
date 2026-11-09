"""What the experiment scripts of the reconciliation manuscript share.

The engine ``riskvalidation`` (release 1.1.0) supplies every estimator, test and Hull-White function that is reconciled; the
product's pipeline (``data-pipeline/pipeline/cases/c12``) supplies the synthetic swap book, the simulation grid, the exposure
measures and the ORE 1.8.17.0 inputs and readers. This module holds what neither does: the loading of the committed documents,
the rebuild of the C12 simulation from the committed curve and calibration (so that no raw Treasury file is needed), the Wilson
interval, and the output writer.

Caches and ORE run folders are written under the folder named by the ``CAOS_TEMP_ROOT`` environment variable or by a
``--work`` argument, never inside the repository.
"""
from __future__ import annotations

import json
import math
import os
import pathlib
import sys
from typing import Any

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DERIVED = ROOT / "data" / "derived"
sys.path.insert(0, str(ROOT / "data-pipeline"))

ORE_VARIANTS = ("single-swap", "netting-set", "csa-mpor-10d", "csa-mpor-20d", "with-im")
K_SE = 2.0


def derived(rel: str) -> dict[str, Any]:
    """A committed document under ``data/derived`` (``"C12/netting-set.json"``)."""
    return json.loads((DERIVED / rel).read_text(encoding="utf-8"))


def write(path: pathlib.Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=1, sort_keys=False, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def work_root(arg: str | None) -> pathlib.Path:
    """The folder for ORE runs and caches: the argument, else ``$CAOS_TEMP_ROOT/contraste-reconciliation``."""
    if arg:
        return pathlib.Path(arg)
    base = os.environ.get("CAOS_TEMP_ROOT")
    if not base:
        raise SystemExit("set CAOS_TEMP_ROOT or pass --work: runs and caches never go inside the repository")
    return pathlib.Path(base) / "contraste-reconciliation"


def wilson(k: float, n: int, z: float = 1.959964) -> tuple[float, float]:
    """The Wilson 95 % interval of a proportion ``k / n`` (Brown, Cai and DasGupta 2001)."""
    p = k / n
    d = 1.0 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def norm_cdf(x: float) -> float:
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def norm_ppf(p: float) -> float:
    from scipy.special import ndtri

    return float(ndtri(p))


# ----------------------------------------------------------------------------------------------------------- C12 rebuild


class C12Inputs:
    """The inputs of the C12 simulation read from a committed variant document: the zero curve, the calibrated ``a`` and
    ``sigma``, the swap book, and the close-out offsets. The tenors are the month multiples the pipeline used (the document
    prints them rounded to six decimals)."""

    def __init__(self, variant: str = "netting-set") -> None:
        from pipeline.cases.c12 import book

        doc = derived(f"C12/{variant}.json")
        out = doc["outputs"]
        pts = out["curve"]["points"]
        self.tenors = np.array([round(p["tenor_years"] * 12) / 12 for p in pts])
        self.zeros = np.array([p["zero_rate"] for p in pts])
        self.a = float(out["calibration_used"]["a"])
        self.sigma = float(out["calibration_used"]["sigma"])
        self.a_se = float(out["calibration_used"]["a_se"])
        self.sigma_se = float(out["calibration_used"]["sigma_se"])
        self.curve_date = out["curve"]["curve_date"]
        self.seed = int(doc["provenance"]["seed"])
        self.paths = int(out["named_parameters"]["path_count"]["value"])
        full = derived("C12/netting-set.json")["outputs"]["book"]["trades"]
        self.trades = [book.Trade(t["trade_id"], t["notional"]["amount"], t["maturity_years"], t["side"], t["fixed_rate"]) for t in full]
        self.swaps = book.swaps_of(self.trades)
        self.deltas = {10: book.closeout_years(10), 20: book.closeout_years(20)}
        self.report = np.array(book.GRID)

    def simulate(self, seed: int, n_paths: int | None = None, a: float | None = None, sigma: float | None = None):
        from pipeline.cases.c12 import exposure as xp

        return xp.simulate(self.tenors, self.zeros, self.a if a is None else a, self.sigma if sigma is None else sigma,
                           self.paths if n_paths is None else n_paths, seed, self.swaps, self.deltas)


def spec_of(variant: str):
    from pipeline.cases.c12 import variant as vt

    return next(s for s in vt.SPECS if s.variant == variant)
