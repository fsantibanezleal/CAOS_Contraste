"""The exposure of the book along Hull-White paths, through ``riskvalidation.ccr`` (ladder rungs 3 and 4).

One simulation per (curve, a, sigma, seed) feeds every variant: the short rate on the union of the report grid, the close-out
dates and the swaps' reset dates, the bank account, and the value of every swap at every point. The variants differ only in how
the values become an exposure:

- uncollateralised: ``max(V(t), 0)`` on the main grid (single swap, netting set, wrong-way risk);
- variation margin: ORE's credit support amount and delivery amount on the main grid, the residual ``max(V_closeout - C, 0)`` on
  the close-out grid, where the close-out value is the **sticky-date** value of decision B3 (the market of ``t + delta``, the
  portfolio not aged);
- initial margin: the regression DIM of ORE (a proxy, never SIMM) applied path by path to the variation-margin exposure.

Every measure is an engine call; this module sequences them, picks the indices and keeps the units. The close-out offset
``delta`` is the calendar-day equivalent of the MPoR on the 30/360 axis of the case (``book.closeout_years``).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from riskvalidation.ccr import collateral as col
from riskvalidation.ccr import exposure as ex
from riskvalidation.ccr import hw1f
from riskvalidation.ccr import swaps as sw
from riskvalidation.ccr.swaps import Swap

from . import book

BATCHES = 20
ROLL_EPS = 1e-7
"""The shifted swap of the sticky close-out starts this much (years, about three seconds) before the close-out date, so that
the coupon fixed at the default date is read as fixed there and not as fixing on the close-out date itself."""


@dataclass
class Sim:
    """The paths and the swap values of one (curve, a, sigma, seed)."""

    tenors: np.ndarray
    zeros: np.ndarray
    a: float
    sigma: float
    p0: Any
    forward: Any
    swaps: list[Swap]
    report: np.ndarray          # (K,) the report grid, years
    main: np.ndarray            # (K0,) 0 and the report grid
    grid: np.ndarray            # (Ks,) the simulation grid
    r: np.ndarray               # (P, Ks) short rates
    numeraire: np.ndarray       # (P, Ks) the bank account
    values: np.ndarray          # (S, P, Ks) the value of each swap, aged
    deltas: dict[int, float] = field(default_factory=dict)   # MPoR business days -> close-out offset in years
    _sticky: dict[int, np.ndarray] = field(default_factory=dict)

    def index(self, t: float | np.ndarray) -> np.ndarray | int:
        idx = np.searchsorted(self.grid, np.asarray(t, dtype=float) - sw.TIME_TOL)
        if np.any(np.abs(self.grid[idx] - np.asarray(t, dtype=float)) > 1e-7):
            raise ValueError(f"time {t} is not on the simulation grid")
        return idx

    @property
    def n_paths(self) -> int:
        return self.r.shape[0]

    def main_values(self, members: list[int]) -> np.ndarray:
        """(P, K0) the netting-set value of the swaps ``members`` at the main grid."""
        return ex.net_values(self.values[members][:, :, self.index(self.main)])

    def per_swap_main(self) -> np.ndarray:
        return self.values[:, :, self.index(self.main)]

    def sticky(self, mpor_business_days: int) -> np.ndarray:
        """(S, P, K0) the sticky-date value of each swap at the close-out of every main-grid date: the market of ``t + delta``
        with the portfolio not aged. A swap rolled forward by ``delta`` and valued at ``t + delta`` has the same remaining
        flows and the same tenors as the swap at ``t``, so the engine's ``swap_value`` of the shifted swap is the value the
        scenario of the close-out date gives the unaged swap; the fixing of a period already begun is the path's own, read at
        the reset date."""
        if mpor_business_days in self._sticky:
            return self._sticky[mpor_business_days]
        delta = self.deltas[mpor_business_days]
        out = np.zeros((len(self.swaps), self.n_paths, self.main.size))
        for s, swap in enumerate(self.swaps):
            shifted = Swap(swap.trade_id, swap.notional, swap.fixed_rate, swap.is_payer, swap.start + delta - ROLL_EPS,
                           swap.maturity + delta - ROLL_EPS, swap.fixed_frequency)
            resets, times = sw.reset_times(swap), sw.cash_flow_times(swap)
            for k, t in enumerate(self.main):
                if t >= swap.maturity - sw.TIME_TOL:
                    continue
                j = int(np.searchsorted(resets, t + sw.TIME_TOL, side="right")) - 1
                # the coupon of the period begun at the last reset on or before t was fixed on or before t: it is known at the
                # close-out of a default at t, whether t is inside the period or on its first day
                i_reset = self.index(resets[j])
                tau = float(times[j] - resets[j])
                p_fix = hw1f.bond_price(self.r[:, i_reset], float(resets[j]), float(times[j]), self.a, self.sigma, self.p0,
                                        self.forward)
                fixing = (1.0 / p_fix - 1.0) / tau
                i_close = self.index(t + delta)
                out[s, :, k] = sw.swap_value(shifted, float(t + delta), self.r[:, i_close], self.a, self.sigma, self.p0,
                                             self.forward, fixing)
        self._sticky[mpor_business_days] = out
        return out


def simulate(tenors: np.ndarray, zeros: np.ndarray, a: float, sigma: float, n_paths: int, seed: int, swaps: list[Swap],
             deltas: dict[int, float]) -> Sim:
    p0, forward = hw1f.curve_functions(zeros, tenors)
    report = np.array(book.GRID)
    main = np.concatenate([[0.0], report])
    parts = [main] + [main + d for d in deltas.values()]
    merged = np.unique(np.round(np.concatenate(parts), 12))
    grid = sw.simulation_grid(merged, swaps)
    r = hw1f.simulate_short_rate(grid, a, sigma, forward, n_paths, seed)
    numeraire = hw1f.bank_account(grid, r, a, sigma, p0, forward)
    values = sw.swap_values_on_grid(swaps, grid, r, a, sigma, p0, forward)
    return Sim(tenors, zeros, a, sigma, p0, forward, swaps, report, main, grid, r, numeraire, values, dict(deltas))


# ------------------------------------------------------------------------------------------------- exposure paths


@dataclass
class Exposures:
    """The exposure paths of a variant at the report grid (P, K), the mean collateral balance and the time-zero balance."""

    x: np.ndarray                    # the exposure to the counterparty
    y: np.ndarray                    # the bank's own exposure (reported positive)
    values: np.ndarray               # (P, K0) the netting-set value at the main grid, with t = 0
    balance: np.ndarray | None = None   # (P, K) the collateral held
    dim: np.ndarray | None = None       # (P, K0) the DIM per path, with t = 0
    x_vm: np.ndarray | None = None      # the exposure before initial margin
    y_vm: np.ndarray | None = None
    v0: float = 0.0
    c0: float = 0.0


def uncollateralised(sim: Sim, members: list[int]) -> Exposures:
    v = sim.main_values(members)
    return Exposures(np.maximum(v[:, 1:], 0.0), np.maximum(-v[:, 1:], 0.0), v, v0=float(v[0, 0]))


def variation_margin(sim: Sim, members: list[int], mpor_bd: int, mta: float | None = None) -> Exposures:
    """ORE's credit support amount, delivery amount and sticky-date close-out, through ``riskvalidation.ccr.collateral``."""
    vm = sim.main_values(members)
    vc = ex.net_values(sim.sticky(mpor_bd)[members])
    args = (book.CSA["independent_amount"], book.CSA["threshold"], book.CSA["threshold"], book.CSA["mta"] if mta is None else mta)
    x, bal = col.variation_margin_exposure(vm, vc, *args)
    y, bal_own = col.variation_margin_exposure(-vm, -vc, *args)
    return Exposures(x[:, 1:], y[:, 1:], vm, balance=bal[:, 1:], v0=float(vm[0, 0]), c0=float(bal[0, 0]))


def initial_margin(sim: Sim, members: list[int], vm_exposures: Exposures, mpor_bd: int, quantile: float, horizon_cd: int,
                   mpor_cd: int, order: int) -> Exposures:
    """The regression DIM at every main-grid date (``X = V_closeout - V``, the sticky close-out value standing for the
    value after the MPoR plus the flows in it), applied path by path to the variation-margin exposure."""
    vm = vm_exposures.values
    vc = ex.net_values(sim.sticky(mpor_bd)[members])
    dim = np.column_stack([col.dynamic_initial_margin(vm[:, k], vc[:, k], np.zeros(vm.shape[0]), quantile, horizon_cd, mpor_cd, order)
                           for k in range(vm.shape[1])])
    x = col.apply_initial_margin(vm_exposures.x, dim[:, 1:])
    y = col.apply_initial_margin(vm_exposures.y, dim[:, 1:])
    return Exposures(x, y, vm, balance=vm_exposures.balance, dim=dim, x_vm=vm_exposures.x, y_vm=vm_exposures.y,
                     v0=vm_exposures.v0, c0=vm_exposures.c0)


# ----------------------------------------------------------------------------------------------------- profiles


def _batch_indices(n: int, b: int) -> np.ndarray:
    """Batch ``b`` of ``BATCHES``: a block of the first half and its antithetic mirror (path i and i + P/2 are a pair)."""
    half = n // 2
    step = half // BATCHES
    first = np.arange(b * step, (b + 1) * step)
    return np.concatenate([first, first + half])


def measures(paths: np.ndarray, numeraire: np.ndarray, p0r: np.ndarray, grid: np.ndarray, pfe_q: float | None, seed: int,
             pfe_bootstrap: int = 50) -> dict[str, Any]:
    """The engine's measures of a non-negative exposure (P, K) and the batch errors of its first-year averages.

    The discounted EE ``ee_d`` is the engine's ``expected_exposure`` under the numeraire (a price: it does not depend on the
    measure the paths are drawn in). The undiscounted EE of the document is the expectation in the ``t``-forward measure,
    ``ee = ee_d / P(0, t)`` (``p0r`` is ``P(0, t)`` on the grid): that is the rung-2 statement ``EE_B(t) = swaption / P(0, t)`` of
    the engine contract and the quantity ORE's own discounted profile gives, whereas the plain mean of the paths is the
    expectation in the simulation's own measure, which differs between engines by the convexity gap. The PFE is the quantile of the
    paths (the simulation measure). ``eff``, ``epe`` and ``eepe`` are the engine's functions of ``ee``."""
    ee_d, ee_d_se = ex.expected_exposure(paths, numeraire)
    ee, ee_se = ee_d / p0r, ee_d_se / p0r
    out: dict[str, Any] = {"ee": ee, "ee_se": ee_se, "ee_d": ee_d, "ee_d_se": ee_d_se}
    if pfe_q is not None:
        out["pfe"], out["pfe_se"] = ex.pfe(paths, pfe_q, seed=seed, n_bootstrap=pfe_bootstrap)
    eff = ex.effective_ee(ee)
    out["eff"] = eff
    out["epe"], out["eepe"] = ex.epe(grid, ee), ex.effective_epe(grid, eff)
    epes, eepes = [], []
    scaled = paths / numeraire
    for b in range(BATCHES):
        e_b = scaled[_batch_indices(paths.shape[0], b)].mean(axis=0) / p0r
        epes.append(ex.epe(grid, e_b))
        eepes.append(ex.effective_epe(grid, ex.effective_ee(e_b)))
    out["epe_se"], out["eepe_se"] = float(np.std(epes, ddof=1) / np.sqrt(BATCHES)), float(np.std(eepes, ddof=1) / np.sqrt(BATCHES))
    return out


def netting_profiles(sim: Sim, members: list[int], p0r: np.ndarray) -> dict[str, Any]:
    """The per-trade EE (uncollateralised, forward-measure like the document's EE), their sum, the netted EE and the netting
    benefit, all from the same paths."""
    per = sim.per_swap_main()[:, :, 1:]
    num = sim.numeraire[:, sim.index(sim.report)]
    ee_each, se_each = [], []
    for s in members:
        e, se = ex.expected_exposure(per[s], num)
        ee_each.append(e / p0r)
        se_each.append(se / p0r)
    net = ex.net_values(per[members])
    e_net, se_net = ex.expected_exposure(net, num)
    ee_net, se_net = e_net / p0r, se_net / p0r
    ee_arr = np.array(ee_each)
    benefit = ex.netting_benefit(ee_arr, ee_net)
    # the standard errors of the sum and of the benefit come from the paths: their sum of positive parts per path
    pos_sum = np.maximum(per[members], 0.0).sum(axis=0) / num / p0r
    se_sum = pos_sum.std(axis=0, ddof=1) / np.sqrt(pos_sum.shape[0])
    ben_paths = pos_sum - np.maximum(net, 0.0) / num / p0r
    se_ben = ben_paths.std(axis=0, ddof=1) / np.sqrt(ben_paths.shape[0])
    return {"per_trade": ee_arr, "per_trade_se": np.array(se_each), "sum": ee_arr.sum(axis=0), "sum_se": se_sum,
            "net": ee_net, "net_se": se_net, "benefit": benefit, "benefit_se": se_ben}
