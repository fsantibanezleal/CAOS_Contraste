"""The lifetime PD ladder of C06 (CT-506): three rungs fitted on the loans as known at a reporting date.

L0 Kaplan-Meier, the non-parametric reference (``statsmodels.duration.survfunc.SurvfuncRight``): one pooled curve by loan
age. L1 discrete-time hazard, a logit on loan-quarter cells with the loan covariates, the age profile and the macro
covariates one quarter before each period (``statsmodels`` GLM, binomial family): the rung that conditions on a scenario.
L2 Cox proportional hazards with the loan covariates and loan age as the time scale (``statsmodels`` PHReg, Breslow
ties). lifelines is not used: 0.30.3 requires pandas below 3.0 and the pipeline pins pandas 3.0.6 (unit sizing U5,
technology matrix). Prepayment is treated as censoring in every rung (``competing_prepayment`` false): the lifetime PD is
the cause-specific default hazard, so the term structure carries no prepayment attrition, a stated limit.

Every rung says how many loans and defaults it stands on; a rung with too few is ``not_evaluated`` with the reason
(``MIN_LOANS``, ``MIN_EVENTS``) and is never fitted.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .macro import MACRO_VARS, History, Scaler, fit_scaler
from .panel import (EXIT_DEFAULT, N_STRATA, SECTOR_NAMES, Loans, Observation, decode_stratum)

MIN_LOANS = 200
MIN_EVENTS = 30
#: the macro values a hazard reads are limited to the training range widened by this share of the range on each side
SUPPORT_MARGIN = 0.25
#: the age bands of the hazard rung, in quarters of loan age: [0,2) [2,4) ... (the last band is open)
AGE_EDGES = (2, 4, 6, 8, 12, 16, 24, 40)
N_BANDS = len(AGE_EDGES) + 1
AGE_LABELS = ("age_q_0_1", "age_q_2_3", "age_q_4_5", "age_q_6_7", "age_q_8_11", "age_q_12_15", "age_q_16_23", "age_q_24_39", "age_q_40_plus")
SIZE_LABELS = ("size_50k_150k", "size_150k_350k", "size_over_350k")
TERM_LABELS = ("term_61_120", "term_121_240", "term_over_240")
COVARIATES = ("size", "term", "sector", "revolver")


def age_band(age_q: np.ndarray) -> np.ndarray:
    return np.searchsorted(np.asarray(AGE_EDGES), np.asarray(age_q), side="right").astype(np.int64)


def static_design(stratum: np.ndarray) -> tuple[np.ndarray, tuple[str, ...]]:
    """The loan covariates as dummy columns, one row per stratum code given: size (3), term (3), sector (11), revolver."""
    d = decode_stratum(stratum)
    cols: list[np.ndarray] = []
    names: list[str] = []
    for k, lab in enumerate(SIZE_LABELS, start=1):
        cols.append((d["size"] == k).astype(float))
        names.append(lab)
    for k, lab in enumerate(TERM_LABELS, start=1):
        cols.append((d["term"] == k).astype(float))
        names.append(lab)
    for k, lab in enumerate(SECTOR_NAMES[:-1]):
        cols.append((d["sector"] == k).astype(float))
        names.append("sector_" + lab)
    cols.append(d["revolver"].astype(float))
    names.append("revolver")
    return np.column_stack(cols), tuple(names)


@dataclass(frozen=True)
class Status:
    """Whether a rung was fitted, on how much, and why not when it was not."""

    evaluated: bool
    n_loans: int
    n_events: int
    reason: str | None


def check_enough(n_loans: int, n_events: int, rung: str) -> Status:
    if n_loans < MIN_LOANS or n_events < MIN_EVENTS:
        return Status(False, n_loans, n_events,
                      f"{rung}: {n_loans} loans and {n_events} defaults, fewer than the {MIN_LOANS} loans and {MIN_EVENTS} "
                      "defaults a fit needs")
    return Status(True, n_loans, n_events, None)


# ---------------------------------------------------------------------------------------------------------------------
# cells: the loan-quarter table of the hazard rung


@dataclass(frozen=True)
class Cells:
    """Loan-quarter cells aggregated by (stratum, age band, calendar quarter): the at-risk count and the defaults."""

    stratum: np.ndarray
    band: np.ndarray
    cal_quarter: np.ndarray
    at_risk: np.ndarray
    events: np.ndarray

    @property
    def n(self) -> int:
        return int(self.at_risk.shape[0])


def build_cells(loans: Loans, obs: Observation) -> Cells:
    """The person-period table of the loans selected at the reporting date, aggregated. With n completed quarters of age,
    a loan is at risk in age quarters 0..n-1 in full; a loan that defaults is also at risk in full in quarter n (the event
    quarter) and a loan censored is at risk in quarter n for the fraction of the quarter it was observed."""
    sel = np.flatnonzero(obs.selected)
    q_r = int(np.datetime64(obs.reporting_date, "M").astype(np.int64)) // 3
    q0_all = loans.origination_quarter[sel]
    q_first = int(q0_all.min()) if sel.size else 0
    n_q = obs.age_months[sel] // 3
    event = obs.event[sel]
    frac = np.where(event, 1.0, (obs.age_months[sel] % 3) / 3.0)
    stratum = loans.stratum[sel]
    if sel.size == 0:
        z = np.zeros(0, dtype=np.int64)
        return Cells(z, z, z, z.astype(float), z)
    q0 = q0_all - q_first
    nq, na = int(q0.max()) + 1, int(n_q.max()) + 1
    flat = (stratum * nq + q0) * na + n_q
    size = N_STRATA * nq * na
    ends = np.bincount(flat, minlength=size).reshape(N_STRATA, nq, na).astype(float)
    partial = np.bincount(flat, weights=frac, minlength=size).reshape(N_STRATA, nq, na)
    evs = np.bincount(flat[event], minlength=size).reshape(N_STRATA, nq, na)
    beyond = np.cumsum(ends[:, :, ::-1], axis=2)[:, :, ::-1] - ends   # loans whose terminal quarter is after a
    at_risk = beyond + partial
    s_i, q_i, a_i = np.nonzero(at_risk > 0.0)
    cal = q_first + q_i + a_i
    keep = cal <= q_r
    s_i, q_i, a_i, cal = s_i[keep], q_i[keep], a_i[keep], cal[keep]
    frame = pd.DataFrame({"s": s_i, "b": age_band(a_i), "c": cal, "n": at_risk[s_i, q_i, a_i], "e": evs[s_i, q_i, a_i]})
    g = frame.groupby(["s", "b", "c"], sort=True).sum().reset_index()
    return Cells(stratum=g["s"].to_numpy(np.int64), band=g["b"].to_numpy(np.int64), cal_quarter=g["c"].to_numpy(np.int64),
                 at_risk=g["n"].to_numpy(float), events=g["e"].to_numpy(np.int64))


def quarterly_default_rates(cells: Cells) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """``(quarters, at_risk, events)`` by calendar quarter, over all loans, in quarter order."""
    frame = pd.DataFrame({"c": cells.cal_quarter, "n": cells.at_risk, "e": cells.events}).groupby("c").sum().sort_index()
    return frame.index.to_numpy(np.int64), frame["n"].to_numpy(float), frame["e"].to_numpy(np.int64)


# ---------------------------------------------------------------------------------------------------------------------
# L1, the discrete-time hazard


@dataclass(frozen=True)
class HazardModel:
    status: Status
    names: tuple[str, ...] = ()
    params: np.ndarray = field(default_factory=lambda: np.zeros(0))
    bse: np.ndarray = field(default_factory=lambda: np.zeros(0))
    scaler: Scaler | None = None
    n_cells: int = 0
    log_likelihood: float = float("nan")
    converged: bool = False
    macro_names: tuple[str, ...] = MACRO_VARS
    macro_lo: np.ndarray | None = None
    macro_hi: np.ndarray | None = None

    # the parameter positions, filled by ``fit_hazard``
    index: dict[str, int] = field(default_factory=dict)

    def lp_strata(self) -> np.ndarray:
        """The linear predictor of every stratum code at the reference age band and zero macro: constant plus the
        loan covariates."""
        d, names = static_design(np.arange(N_STRATA))
        lp = np.full(N_STRATA, self.params[self.index["const"]])
        for k, nm in enumerate(names):
            if nm in self.index:
                lp = lp + self.params[self.index[nm]] * d[:, k]
        return lp

    def age_effect(self, max_age_q: int) -> np.ndarray:
        """Effect of the age band for each age in quarters 0..max_age_q."""
        band = age_band(np.arange(max_age_q + 1))
        eff = np.zeros(N_BANDS)
        for b in range(1, N_BANDS):
            nm = AGE_LABELS[b]
            if nm in self.index:
                eff[b] = self.params[self.index[nm]]
        return eff[band]

    def macro_effect(self, macro_lag: np.ndarray) -> np.ndarray:
        """Effect of the lagged macro values (T, 3) in the units the model was fitted on."""
        beta = np.array([self.params[self.index[m]] if m in self.index else 0.0 for m in self.macro_names])
        return self.scaler.apply(self.clip_macro(macro_lag)) @ beta

    def clip_macro(self, values: np.ndarray) -> np.ndarray:
        """The macro values limited to the range the model was fitted on: a hazard is never extrapolated beyond the
        support of its training quarters (a stated guard, CT-506)."""
        return np.clip(values, self.macro_lo, self.macro_hi)

    def _hazard(self, stratum: np.ndarray, age_q: np.ndarray, macro_eff: np.ndarray, t: int, lp: np.ndarray | None,
                age_eff: np.ndarray | None) -> np.ndarray:
        lp = self.lp_strata() if lp is None else lp
        eff = self.age_effect(int(age_q.max()) + t) if age_eff is None else age_eff
        eta = lp[stratum][:, None] + eff[age_q[:, None] + np.arange(1, t + 1)[None, :]] + macro_eff
        return 1.0 / (1.0 + np.exp(-eta))

    def hazard_path(self, stratum: np.ndarray, age_q: np.ndarray, macro_lag: np.ndarray, lp: np.ndarray | None = None,
                    age_eff: np.ndarray | None = None) -> np.ndarray:
        """Quarterly default hazard of the accounts for quarters 1..T ahead under one macro path: (A, T). Quarter t of
        an account of age ``age_q`` quarters is its age quarter ``age_q + t``; ``macro_lag`` (T, 3) is what the hazard
        reads (``macro.lagged_for_hazard``)."""
        t = macro_lag.shape[0]
        return self._hazard(stratum, age_q, self.macro_effect(macro_lag)[None, :], t, lp, age_eff)

    def hazard_frozen(self, stratum: np.ndarray, age_q: np.ndarray, macro_const: np.ndarray, t: int,
                      lp: np.ndarray | None = None, age_eff: np.ndarray | None = None) -> np.ndarray:
        """The same hazard with each account's macro held at its own constant ``macro_const`` (A, 3): the origination
        expectation with no macro forecast."""
        beta = np.array([self.params[self.index[m]] if m in self.index else 0.0 for m in self.macro_names])
        eff = (self.scaler.apply(self.clip_macro(macro_const)) @ beta)[:, None]
        return self._hazard(stratum, age_q, eff, t, lp, age_eff)


def fit_hazard(cells: Cells, history: History, n_loans: int) -> HazardModel:
    """Binomial GLM (logit) on the aggregated loan-quarter cells, covariates as ``static_design``, the age bands and the
    three macro variables of the quarter before each cell, standardised on the training quarters."""
    import statsmodels.api as sm

    n_events = int(cells.events.sum())
    status = check_enough(n_loans, n_events, "L1-dth")
    if not status.evaluated:
        return HazardModel(status=status)
    support = history.window(max(int(cells.cal_quarter.min()) - 1, history.first), int(cells.cal_quarter.max()) - 1)
    scaler = fit_scaler(support)
    lag = np.clip(cells.cal_quarter - 1, history.first, history.last)
    macro = scaler.apply(history.values[lag - history.first])
    d, names = static_design(cells.stratum)
    band = np.column_stack([(cells.band == b).astype(float) for b in range(1, N_BANDS)])
    cols = {"const": np.ones(cells.n)}
    for k, nm in enumerate(names):
        cols[nm] = d[:, k]
    for b in range(1, N_BANDS):
        cols[AGE_LABELS[b]] = band[:, b - 1]
    for j, nm in enumerate(MACRO_VARS):
        cols[nm] = macro[:, j]
    keep = [k for k, v in cols.items() if k == "const" or np.ptp(v) > 0.0]
    x = np.column_stack([cols[k] for k in keep])
    y = np.column_stack([cells.events, cells.at_risk - cells.events]).astype(float)
    res = sm.GLM(y, x, family=sm.families.Binomial()).fit(maxiter=100)
    return HazardModel(status=status, names=tuple(keep), params=np.asarray(res.params, dtype=float),
                       bse=np.asarray(res.bse, dtype=float), scaler=scaler, n_cells=int(cells.n),
                       log_likelihood=float(res.llf), converged=bool(res.converged), index={k: i for i, k in enumerate(keep)},
                       macro_lo=support.min(axis=0) - SUPPORT_MARGIN * np.ptp(support, axis=0),
                       macro_hi=support.max(axis=0) + SUPPORT_MARGIN * np.ptp(support, axis=0))


# ---------------------------------------------------------------------------------------------------------------------
# L0 Kaplan-Meier and L2 Cox, on the loan table (time in months of loan age)


@dataclass(frozen=True)
class StepCurve:
    """A right-continuous step function of loan age in months: ``value`` at the given ``times``."""

    times: np.ndarray
    value: np.ndarray

    def at(self, t: np.ndarray, before: float) -> np.ndarray:
        idx = np.searchsorted(self.times, np.asarray(t, dtype=float), side="right") - 1
        out = np.where(idx >= 0, self.value[np.clip(idx, 0, None)], before)
        return out


@dataclass(frozen=True)
class KaplanMeier:
    status: Status
    survival: StepCurve | None = None
    n_at_risk0: int = 0

    def cumulative(self, age_months: np.ndarray, horizon_months: np.ndarray) -> np.ndarray:
        """P(default by age a + k | alive at a) = 1 - S(a + k) / S(a), accounts (A,) by horizons (H,)."""
        s0 = self.survival.at(age_months, 1.0)
        s1 = self.survival.at((age_months[:, None] + horizon_months[None, :]).ravel(), 1.0).reshape(len(age_months), -1)
        return 1.0 - s1 / s0[:, None]


def fit_km(loans: Loans, obs: Observation) -> KaplanMeier:
    from statsmodels.duration.survfunc import SurvfuncRight

    sel = obs.selected
    n, d = int(sel.sum()), int(obs.event.sum())
    status = check_enough(n, d, "L0-km")
    if not status.evaluated:
        return KaplanMeier(status)
    sf = SurvfuncRight(obs.age_months[sel].astype(float) + 0.5, obs.event[sel].astype(int))
    return KaplanMeier(status, StepCurve(np.asarray(sf.surv_times, dtype=float), np.asarray(sf.surv_prob, dtype=float)), n)


@dataclass(frozen=True)
class CoxModel:
    status: Status
    names: tuple[str, ...] = ()
    params: np.ndarray = field(default_factory=lambda: np.zeros(0))
    bse: np.ndarray = field(default_factory=lambda: np.zeros(0))
    cumulative_hazard: StepCurve | None = None
    keep: tuple[int, ...] = ()

    def linear_predictor(self, stratum: np.ndarray) -> np.ndarray:
        d, _ = static_design(stratum)
        return d[:, list(self.keep)] @ self.params

    def cumulative(self, stratum: np.ndarray, age_months: np.ndarray, horizon_months: np.ndarray) -> np.ndarray:
        h0 = self.cumulative_hazard
        base = h0.at(age_months, 0.0)
        ahead = h0.at((age_months[:, None] + horizon_months[None, :]).ravel(), 0.0).reshape(len(age_months), -1)
        mult = np.exp(self.linear_predictor(stratum))
        return 1.0 - np.exp(-(ahead - base[:, None]) * mult[:, None])


def fit_cox(loans: Loans, obs: Observation) -> CoxModel:
    from statsmodels.duration.hazard_regression import PHReg

    sel = np.flatnonzero(obs.selected)
    n, d = int(sel.size), int(obs.event.sum())
    status = check_enough(n, d, "L2-cox")
    if not status.evaluated:
        return CoxModel(status)
    x_all, names = static_design(loans.stratum[sel])
    keep = [k for k in range(x_all.shape[1]) if np.ptp(x_all[:, k]) > 0.0]
    x = x_all[:, keep]
    res = PHReg(obs.age_months[sel].astype(float) + 0.5, x, status=obs.event[sel].astype(int), ties="breslow").fit(disp=0)
    times, cum = res.baseline_cumulative_hazard[0][0], res.baseline_cumulative_hazard[0][1]
    return CoxModel(status, tuple(names[k] for k in keep), np.asarray(res.params, dtype=float), np.asarray(res.bse, dtype=float),
                    StepCurve(np.asarray(times, dtype=float), np.asarray(cum, dtype=float)), tuple(keep))


@dataclass(frozen=True)
class Ladder:
    km: KaplanMeier
    dth: HazardModel
    cox: CoxModel
    cells: Cells | None


def fit_ladder(loans: Loans, obs: Observation, history: History) -> Ladder:
    """Fit the three rungs on what is known at ``obs.reporting_date``."""
    cells = build_cells(loans, obs)
    return Ladder(km=fit_km(loans, obs), dth=fit_hazard(cells, history, int(obs.selected.sum())), cox=fit_cox(loans, obs), cells=cells)


__all__ = ["Cells", "CoxModel", "HazardModel", "KaplanMeier", "Ladder", "MIN_EVENTS", "MIN_LOANS", "Status",
           "EXIT_DEFAULT", "age_band", "build_cells", "fit_ladder", "static_design"]
