"""C04, the live ports' parity points: projections, intervals and risk weights (U4, CT-410, CT-411).

The contract is docs/design/features/c04-transitions/contract.md section 4. The web recomputes three things live in
``frontend/src/engine/transitions.ts``, and ``frontend/src/engine/transitions.test.ts`` holds each port to the engine
on the points computed here, which the bake writes to the models artifact ``C04/models-transitions.json``
(``fit.parity``). Every number is ``riskvalidation``'s:

- ``transitions.ttc.project`` and ``ttc_portfolio``: Engelmann (2024), Spurious default probability projections in
  credit risk stress testing models, arXiv 2401.08892v1, the propagation (9) at unit balance (the portfolio rescaled
  to one after each period, his step 5) and Theorem 1's TTC portfolio (10) by power iteration to an L1 change below
  1e-14. Three starting portfolios (all in the first grade, the origination mix, uniform over the seven grades) under
  each agency's pooled one-year matrix, over 20 years. A matrix in which no grade reaches default (a scale without a
  default category, as Moody's transition page) is refused: its default rates would hold zeros to zeros.
- ``transitions.intervals``: Schuermann and Hanson (2004), Estimating probabilities of default, FRBNY Staff Report
  190, the Wald interval (2.2) and the Agresti-Coull interval (3.2) to (3.3), both with the effective number of
  observations (3.4) at a default correlation (after Miao and Gastwirth 2004) and bounded to [0, 1]; the equal-tailed
  Jeffreys interval of Beta(D + 1/2, N - D + 1/2), 0 at D = 0 and 1 at D = N (Brown, Cai and DasGupta 2001,
  doi:10.1214/ss/1009213286, as defined in Zhou, Li and Yang 2008, doi:10.1098/rsta.2008.0037, Appendix C). A grid of
  counts, sizes and correlations at 95%, with Table 5's cell (15 defaults of 531) on it; a few points at the web's
  other levels, 90% and 99%; and, at the three levels, the sizes of CEREP's pooled grades (about 2,000 to 47,000
  ratings, up to 1,500 defaults), where the web's read-out takes its counts and the Jeffreys port's error is largest.
- ``regulatory.irb``: the IRB risk weight (CRE31.5, with the PD floor of CRE32.4) under C04's convention, which is
  C05's: ``c05_ldp_calibration.IRB_ASSUMPTIONS`` (Basel III final, corporate, F-IRB LGD 45%, maturity 2.5 years; the
  dict the agency artifacts carry as ``irb``) and ``_irb_rw``, the function the case's impact calls, so the parity,
  the impact and the live capital share one definition and a PD by grade reads in C04 exactly as in C05. Rows at a PD
  of 0 (a grade with no default in any cohort, as S&P's AAA, which the engine takes at the floor from riskvalidation
  0.4.1; 0.4.0 refuses it), below, at and above the floor, to the speculative grades' PDs.

Inputs and results are kept at full precision: the bake writes ``parity`` exactly, never rounded to nine significant
digits (as C05 writes its own parity), or the 1e-9 comparison would measure the rounding instead of the port.
"""
from __future__ import annotations

import math
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import numpy as np

from riskvalidation.transitions import intervals as iv
from riskvalidation.transitions import ttc

from .c05_ldp_calibration import IRB_ASSUMPTIONS, _irb_rw

#: seven performing grades and default (last, absorbing), as pipeline.io.cerep.GRADES
N_STATES = 8
YEARS = 20

LEVEL = 0.95
INTERVAL_DEFAULTS = (0, 1, 2, 5, 15, 50)
INTERVAL_N = (50, 200, 531, 2000)        # 531: Schuermann and Hanson's Table 5 (BB, 2002), where 15 defaults sit
INTERVAL_RHO = (0.0, 0.01, 0.02, 0.05)   # Table 5 prints 0, 1% and 2%; the web's correlation knob runs to 5%
#: the web's other levels at a few (defaults, n), each independent and at a 2% correlation
LEVELS_OTHER = (0.90, 0.99)
INTERVAL_OTHER = ((0, 200), (1, 50), (5, 531), (15, 531), (50, 2000))
INTERVAL_OTHER_RHO = (0.0, 0.02)
#: CEREP's pooled grades over the 2000 to 2025 cohorts, rounded (S&P, tab 2: AAA 1,950 ratings and no default, AA
#: 21,000 with 2, A 47,000 with 16, BBB 46,000 with 53, BB 28,000 with 150, B 38,000 with 1,000, CCC to C 5,400 with
#: 1,500; tab 4's default column: AA 20,000 with 1, where the Jeffreys port's error is largest), the counts the web's
#: interval read-out takes, at its three levels
INTERVAL_POOLED = ((0, 1950), (1, 20000), (2, 21000), (16, 47000), (53, 46000), (150, 28000), (1000, 38000),
                   (1500, 5400))
LEVELS_POOLED = (0.90, 0.95, 0.99)
INTERVAL_POOLED_RHO = (0.0, 0.05)

#: 0 (a grade with no default in any cohort), below the 0.05% floor of CRE32.4, at it and above it, to the speculative
#: grades' PDs (S&P's pooled CCC to C, tab 2: about 27%)
CAPITAL_PD = (0.0, 0.0003, 0.0005, 0.001, 0.005, 0.02, 0.1, 0.25, 0.5)


def _states(v: Any, what: str) -> list[float]:
    """Seven or eight shares as eight floats, default last (a share of 0 in default when seven are given)."""
    out = [float(x) for x in v]
    if len(out) == N_STATES - 1:
        out.append(0.0)
    if len(out) != N_STATES:
        raise ValueError(f"the {what} gives {len(out)} shares, not {N_STATES - 1} grades (or {N_STATES} with default)")
    return out


def _starts(origination: list[float]) -> list[list[float]]:
    """The three starting portfolios: all in the first grade, the origination mix, uniform over the grades."""
    first = [1.0] + [0.0] * (N_STATES - 1)
    uniform = [1.0 / (N_STATES - 1)] * (N_STATES - 1) + [0.0]
    return [first, list(origination), uniform]


@contextmanager
def _named(code: str) -> Iterator[None]:
    """The engine's refusals (the matrix's rows, Theorem 1's conditions, the shares), named by the agency."""
    try:
        yield
    except ValueError as exc:
        raise ValueError(f"{code}: {exc}") from exc


def _projection(agency_matrices: dict[str, np.ndarray], origination: list[float]) -> list[dict[str, Any]]:
    """CT-410: each agency's pooled matrix, each start propagated by (9) over YEARS, and the TTC portfolio (10)."""
    if not agency_matrices:
        raise ValueError("no agency matrix: the projection parity needs at least one")
    o = _states(origination, "origination")
    rows: list[dict[str, Any]] = []
    for code, matrix in agency_matrices.items():
        t = np.asarray(matrix, dtype=float)
        if t.shape != (N_STATES, N_STATES):
            raise ValueError(f"{code}: the matrix is {t.shape}, not seven grades and default ({N_STATES} x {N_STATES})")
        with _named(code):
            ttc.propagation_matrix(t, o)  # the engine's checks of the matrix and the origination, before the column
        if not np.any(t[:-1, -1] > 0):
            raise ValueError(f"{code}: no grade reaches default (a scale without a default category, as Moody's "
                             "transition page): the projection's default rates would hold zeros to zeros")
        for w0 in _starts(o):
            with _named(code):
                out = ttc.project(t, w0, o, YEARS)
            fixed = out["ttc"]
            if not fixed["converged"]:
                raise ValueError(f"{code}: the TTC iteration did not converge in {fixed['iterations']:,} periods")
            rows.append({
                "agency": str(code), "matrix": t.tolist(), "origination": list(o), "w0": w0, "years": YEARS,
                "default_rate": out["default_rate"].tolist(),       # W_t' T V_w for t = 0 .. YEARS - 1
                "portfolio_last": out["portfolio"][-1].tolist(),    # the portfolio after YEARS periods
                "ttc": fixed["portfolio"].tolist(), "ttc_default_rate": float(fixed["default_rate"]),
            })
    return rows


def _interval(d: int, n: int, rho: float, level: float) -> dict[str, Any]:
    w = iv.pd_wald(d, n, level=level, rho=rho)
    a = iv.pd_agresti_coull(d, n, level=level, rho=rho)
    j = iv.pd_jeffreys(d, n, level=level)  # no correlation: the posterior of independent trials
    return {"defaults": d, "n": n, "rho": rho, "level": level, "wald": [w["lower"], w["upper"]],
            "agresti_coull": [a["lower"], a["upper"]], "jeffreys": [j["lower"], j["upper"]],
            "n_effective": w["n_effective"]}


def _intervals() -> list[dict[str, Any]]:
    """CT-411: the three intervals on the grid at 95% (only counts that fit their size), the points at 90% and 99%,
    then CEREP's pooled sizes at the three levels."""
    rows = [_interval(d, n, rho, LEVEL) for n in INTERVAL_N for d in INTERVAL_DEFAULTS if d <= n
            for rho in INTERVAL_RHO]
    rows += [_interval(d, n, rho, level) for level in LEVELS_OTHER for d, n in INTERVAL_OTHER if d <= n
             for rho in INTERVAL_OTHER_RHO]
    rows += [_interval(d, n, rho, level) for level in LEVELS_POOLED for d, n in INTERVAL_POOLED
             for rho in INTERVAL_POOLED_RHO]
    return rows


def _capital() -> list[dict[str, Any]]:
    """CT-411: the IRB risk weight (share of EAD) of each PD under C04's convention, C05's ``_irb_rw`` with the
    assumptions it applies (``IRB_ASSUMPTIONS``) on each row."""
    irb = IRB_ASSUMPTIONS
    rows: list[dict[str, Any]] = []
    for pd in CAPITAL_PD:
        try:
            rw = float(_irb_rw(pd))
        except ValueError as exc:  # a PD the engine refuses (0 before riskvalidation 0.4.1, which floors it)
            raise ValueError(f"the capital row at PD {pd}: {exc}") from exc
        rows.append({"pd": pd, "lgd": irb["lgd"], "maturity": irb["maturity"], "regime": irb["regime"],
                     "asset_class": irb["asset_class"], "risk_weight": rw})
    return rows


def _check_json(obj: Any, where: str) -> None:
    """The parity is plain JSON: dicts, lists, str, bool, int and finite floats (no NaN, no infinity, and no numpy
    scalar, which the exact type test refuses even where it subclasses float)."""
    if type(obj) is dict:
        for k, v in obj.items():
            if type(k) is not str:
                raise TypeError(f"{where}: the key {k!r} is not text")
            _check_json(v, f"{where}.{k}")
    elif type(obj) is list:
        for i, v in enumerate(obj):
            _check_json(v, f"{where}[{i}]")
    elif type(obj) is float:
        if not math.isfinite(obj):
            raise ValueError(f"{where}: {obj} is not a finite number")
    elif obj is not None and type(obj) not in (str, bool, int):
        raise TypeError(f"{where}: {type(obj).__name__} is not plain JSON")


def parity(agency_matrices: dict[str, np.ndarray], origination: list[float]) -> dict[str, Any]:
    """The parity block of the models artifact (``fit.parity``, contract section 4).

    ``agency_matrices`` maps an agency code to its pooled one-year matrix (8 x 8, the seven grades best first, default
    last and absorbing; rows summing to 1 within the engine's 1e-3; some grade reaching default, so a scale without a
    default category is refused, naming the agency); ``origination`` is the share of new exposure by grade (seven, or
    eight with a zero in default). Returns ``{"projection", "intervals", "capital"}``: the projection rows in the
    agencies' order, three starts each. Deterministic: no draw is involved."""
    out = {"projection": _projection(agency_matrices, origination), "intervals": _intervals(), "capital": _capital()}
    _check_json(out, "parity")
    return out
