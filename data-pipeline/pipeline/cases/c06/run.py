"""One reporting date of C06 (CT-507 to CT-509): the book, the term structures per scenario, the staging and the ECL.

Every number of a term structure, a stage, an ECL or an allowance is ``riskvalidation.provisions`` (the engine
``engine-provisions-api`` 1.0.0): ``from_hazard``, ``forward_pd``, ``annualise_pd``, ``ttc_to_pit``, ``implied_z``,
``allocate_stages``, ``ecl_scenario``, ``probability_weighted_ecl``, ``portfolio_allowance``. The product supplies the
hazards (the ladder), the exposure model, the LGD proxy and the policy parameters, and nothing else: no ECL, staging or
validation formula lives here (ADR-0069).

What the data cannot say. The SBA file has no delinquency, forbearance or watch-list history, so the 30 days past due
backstop, forbearance and watch-list triggers never fire (``dpd`` is 0 by construction) and the quantitative SICR test
decides Stage 2. Default is the charge-off, and a charged-off loan leaves the book: Stage 3 holds no balance at a
reporting date, and the defaults of a window pass through it (see ``rollforward``).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from riskvalidation.provisions import ecl as rv_ecl
from riskvalidation.provisions import term_structure as rv_ts
from riskvalidation.provisions.staging import StageResult, StagingPolicy, allocate_stages

from . import macro as mc
from .ladder import Ladder, fit_ladder, quarterly_default_rates
from .panel import (SEGMENT_IDS, Loans, Observation, balance_fraction, decode_stratum, observe)
from .readers import FedTables

RHO = 0.12                    # asset correlation: dossier 02 B.4 and C.1 use 0.12 for the one-factor conversion
PERIOD_MONTHS = 3
STAGE1_MONTHS = 12
LIFETIME_CAP_MONTHS = 120
CAP_Q = LIFETIME_CAP_MONTHS // PERIOD_MONTHS
BACKTEST_Q = 12               # the first 12 quarters (36 months) of each account's curve are kept for the backtests
CHUNK = 40_000
MIN_QUARTER_AT_RISK = 1000    # a quarter enters the implied systematic factor with at least this many loans at risk
MIN_DEFAULTS_LGD = 30
CONVENTION = "mid-period"
#: the staging policy: the multiplier schedule, the absolute floor and the threefold ratio are the contract's golden
#: policy (engine-provisions-api, staging); 30 and 90 days are IFRS 9 5.5.11 and B5.5.37; no probation (the file has no
#: cure dates and the reporting dates are a year apart)
POLICY = StagingPolicy(multiplier_schedule=((0.01, 4.0), (0.05, 2.5), (0.5, 1.5)), absolute_floor=0.005, threefold_ratio=3.0,
                       dpd_backstop=30, default_dpd=90, probation_months=0, low_credit_risk_pd=None)


class RungNotEvaluated(RuntimeError):
    """The hazard rung could not be fitted at this reporting date (too few loans or defaults): no ECL is computed."""


@dataclass
class DateRun:
    """Everything one reporting date produces, per account (A accounts in the book) and aggregated."""

    reporting_date: np.datetime64
    obs: Observation
    history: mc.History
    ladder: Ladder
    idx: np.ndarray                      # (A,) positions in the Loans arrays of the loans in the book
    age_m: np.ndarray                    # (A,) age in months at the reporting date
    horizon_q: np.ndarray                # (A,) quarters of expected life, capped
    segment: np.ndarray                  # (A,) term band 0..3
    stratum: np.ndarray                  # (A,) covariate stratum code
    eir: np.ndarray                      # (A,) annual effective interest rate
    eir_imputed: np.ndarray              # (A,) bool: the file records no rate, the prime rate of the approval quarter is used
    gca: np.ndarray                      # (A,) modelled gross carrying amount, USD
    lgd: np.ndarray                      # (A,)
    lgd_segments: list[dict[str, Any]]
    weights: np.ndarray                  # (S,)
    scenario_ids: tuple[str, ...]
    paths: dict[str, np.ndarray]
    macro_mean_path: np.ndarray
    z_hat: tuple[np.ndarray, np.ndarray]  # (quarters, z)
    pd_ttc: float
    satellite: mc.Satellite
    z_paths: dict[str, np.ndarray]
    ecl12: np.ndarray                    # (S, A) 12-month ECL per scenario
    ecl_life: np.ndarray                 # (S, A) lifetime ECL per scenario
    ecl12_mean: np.ndarray               # (A,) at the weighted-mean macro path
    ecl_life_mean: np.ndarray
    f_h: np.ndarray                      # (S, A) cumulative PD over the expected life
    f_orig_h: np.ndarray                 # (A,) origination expectation over the same window
    cum12: np.ndarray                    # (A, 12) probability-weighted cumulative PD, first 12 quarters (NaN when life < 12)
    cum12_orig: np.ndarray               # (A, 12)
    pd12: np.ndarray                     # (A,) weighted 12-month PD
    proj_cur_ann: np.ndarray             # (A,) projected annualised current PD one year later (NaN when life <= 4 quarters)
    proj_orig_ann: np.ndarray
    pd_orig_ann: np.ndarray
    pd_cur_ann: np.ndarray
    stage_result: StageResult = field(default=None)  # type: ignore[assignment]
    seg_curves: np.ndarray = field(default=None)     # type: ignore[assignment]  # (S + 1, 4, CAP_Q) mean cumulative PD
    seg_counts: np.ndarray = field(default=None)     # type: ignore[assignment]  # (4,)
    seg_pd_ttc: np.ndarray = field(default=None)     # type: ignore[assignment]  # (4,)

    @property
    def a(self) -> int:
        return int(self.idx.shape[0])

    @property
    def stage(self) -> np.ndarray:
        return self.stage_result.stage

    def weighted(self, per_scenario: np.ndarray) -> np.ndarray:
        return rv_ecl.probability_weighted_ecl(per_scenario, self.weights)


def annualise(pd: np.ndarray, years: np.ndarray) -> np.ndarray:
    """``annualise_pd`` of the engine, which takes one horizon at a time, applied by horizon group (NaN stays NaN)."""
    out = np.full(pd.shape, np.nan)
    for y in np.unique(years):
        m = (years == y) & np.isfinite(pd)
        if m.any():
            out[m] = rv_ts.annualise_pd(np.clip(pd[m], 1e-12, 1 - 1e-12), float(y))
    return out


def eir_for(loans: Loans, history: mc.History) -> tuple[np.ndarray, np.ndarray]:
    """The original EIR of every loan: the recorded initial rate, else the prime rate of the quarter before approval
    (known at origination; the file records rates only from the FY2008 approvals on). Returns ``(eir, imputed)``."""
    q = np.clip(loans.origination_quarter - 1, history.first, history.last)
    prime = history.values[q - history.first, 2] / 100.0
    imputed = ~np.isfinite(loans.rate)
    return np.where(imputed, prime, loans.rate), imputed


def lgd_segments(loans: Loans, obs: Observation, eir: np.ndarray) -> tuple[np.ndarray, list[dict[str, Any]]]:
    """LGD by term band as a charge-off severity proxy: the sum of the amounts charged off over the sum of the modelled
    balances at charge-off, of the defaults known at the reporting date, capped at 1. The file has no recoveries after the
    charge-off, so this is an upper-bound proxy (dossier 08 A.6). A band with fewer than ``MIN_DEFAULTS_LGD`` defaults
    takes the pooled value and says so."""
    d = np.flatnonzero(obs.event & np.isfinite(loans.chargeoff_amount))
    bal = loans.amount[d] * balance_fraction(obs.age_months[d], loans.term[d], eir[d], loans.revolver[d])
    seg = loans.term_band[d]
    coa = loans.chargeoff_amount[d]
    pooled = float(min(1.0, coa.sum() / bal.sum())) if bal.sum() > 0 else 1.0
    out, vec = [], np.zeros(4)
    for g, sid in enumerate(SEGMENT_IDS):
        m = seg == g
        n = int(m.sum())
        if n >= MIN_DEFAULTS_LGD and bal[m].sum() > 0:
            v = float(min(1.0, coa[m].sum() / bal[m].sum()))
            basis = f"{n} defaults known at the reporting date: charge-off amount over the modelled balance at charge-off, capped at 1"
        else:
            v = pooled
            basis = f"{n} defaults in this band, fewer than {MIN_DEFAULTS_LGD}: the pooled value of {len(d)} defaults"
        vec[g] = v
        out.append({"segment_id": sid, "lgd": v, "basis": basis, "defaults": n})
    return vec, out


def _quarter_rates(ladder: Ladder, hist: mc.History, min_at_risk: int) -> tuple[np.ndarray, np.ndarray, float]:
    q, n, e = quarterly_default_rates(ladder.cells)
    ok = n >= min_at_risk
    q, n, e = q[ok], n[ok], e[ok]
    if q.size < 8:
        raise RungNotEvaluated(f"only {q.size} quarters with {min_at_risk} loans at risk: the systematic factor needs at least 8")
    # keep the last contiguous run ending at the reporting quarter
    gaps = np.flatnonzero(np.diff(q) != 1)
    start = int(gaps[-1]) + 1 if gaps.size else 0
    q, n, e = q[start:], n[start:], e[start:]
    annual = 1.0 - (1.0 - np.clip(e / n, 1e-6, 0.5)) ** 4
    pd_ttc = float(np.mean(annual))
    z = rv_ts.implied_z(annual, pd_ttc, RHO)
    return q, np.asarray(z, dtype=float), pd_ttc


def _segment_pd_ttc(ladder: Ladder) -> np.ndarray:
    c = ladder.cells
    term = decode_stratum(c.stratum)["term"]
    out = np.zeros(4)
    for g in range(4):
        m = term == g
        n = float(c.at_risk[m].sum())
        rate = float(c.events[m].sum()) / n if n > 0 else 0.0
        out[g] = 1.0 - (1.0 - min(max(rate, 1e-6), 0.5)) ** 4
    return out


def run_date(loans: Loans, fed: FedTables, reporting_date: np.datetime64, *, weights: dict[str, float] | None = None,
             policy: StagingPolicy = POLICY, min_quarter_at_risk: int = MIN_QUARTER_AT_RISK) -> DateRun:
    r = np.datetime64(reporting_date, "D")
    obs = observe(loans, r)
    hist = mc.history_known(fed, r)
    ladder = fit_ladder(loans, obs, hist)
    if not ladder.dth.status.evaluated:
        raise RungNotEvaluated(str(ladder.dth.status.reason))
    model = ladder.dth
    w_map = weights or mc.SCENARIO_WEIGHTS
    ids = mc.SCENARIOS
    w = np.array([w_map[s] for s in ids])
    paths = mc.scenario_paths(fed, hist, CAP_Q)
    mean_path = mc.weighted_mean_path(paths, w_map)
    macro_lags = {s: mc.lagged_for_hazard(hist, paths[s]) for s in ids}
    mean_lag = mc.lagged_for_hazard(hist, mean_path)

    eir_all, imputed_all = eir_for(loans, hist)
    lgd_vec, lgd_info = lgd_segments(loans, obs, eir_all)

    idx = np.flatnonzero(obs.in_book)
    a = idx.size
    age_m = obs.age_at_reporting[idx]
    remaining = loans.term[idx] - age_m
    horizon_q = np.clip(-(-remaining // PERIOD_MONTHS), 1, CAP_Q).astype(np.int64)
    seg = loans.term_band[idx]
    eir = eir_all[idx]
    amount, term, revolver, stratum = loans.amount[idx], loans.term[idx], loans.revolver[idx], loans.stratum[idx]
    gca = amount * balance_fraction(age_m, term, eir, revolver)
    lgd = lgd_vec[seg]
    age_q = age_m // PERIOD_MONTHS
    q_orig = np.clip(loans.origination_quarter[idx] - 1, hist.first, hist.last)
    macro_orig = hist.values[q_orig - hist.first]

    z_q, z_hat, pd_ttc = _quarter_rates(ladder, hist, min_quarter_at_risk)

    n_s = len(ids)
    ecl12 = np.zeros((n_s, a))
    ecl_life = np.zeros((n_s, a))
    ecl12_m = np.zeros(a)
    ecl_life_m = np.zeros(a)
    f_h = np.zeros((n_s, a))
    f_orig = np.zeros(a)
    cum12 = np.full((a, BACKTEST_Q), np.nan)
    cum12_o = np.full((a, BACKTEST_Q), np.nan)
    pd12 = np.zeros(a)
    proj_cur = np.full(a, np.nan)
    proj_orig = np.full(a, np.nan)
    seg_sum = np.zeros((n_s + 1, 4, CAP_Q))
    haz_sum = np.zeros((n_s, CAP_Q))
    haz_n = np.zeros(CAP_Q)
    seg_n = np.bincount(seg, minlength=4).astype(float)
    lp = model.lp_strata()
    age_eff = model.age_effect(int(age_q.max()) + CAP_Q + 1)

    for h_q in np.unique(horizon_q):
        members = np.flatnonzero(horizon_q == h_q)
        months = PERIOD_MONTHS * np.arange(1, h_q + 1)
        horizon12 = int(min(STAGE1_MONTHS, months[-1]))
        for chunk in np.array_split(members, max(1, -(-members.size // CHUNK))):
            st, aq = stratum[chunk], age_q[chunk]
            steps = age_m[chunk, None] + PERIOD_MONTHS * np.arange(0, h_q)[None, :]
            ead_t = amount[chunk, None] * balance_fraction(steps, term[chunk, None], eir[chunk, None], revolver[chunk, None])
            lgd_c, eir_c = lgd[chunk], eir[chunk]
            seg_c = seg[chunk]
            haz_n[:h_q] += chunk.size
            cur_w = np.zeros((chunk.size, h_q))
            proj = np.zeros(chunk.size)
            for s, sid in enumerate(ids):
                hz = model.hazard_path(st, aq, macro_lags[sid][:h_q], lp=lp, age_eff=age_eff)
                haz_sum[s, :h_q] += hz.sum(axis=0)
                ts = rv_ts.from_hazard(hz, months)
                ecl12[s, chunk] = rv_ecl.ecl_scenario(ts.marginal, lgd_c, ead_t, eir_c, months, horizon12, CONVENTION)
                ecl_life[s, chunk] = rv_ecl.ecl_scenario(ts.marginal, lgd_c, ead_t, eir_c, months, int(months[-1]), CONVENTION)
                f_h[s, chunk] = ts.cumulative[:, -1]
                cur_w += w[s] * ts.cumulative
                pad = np.concatenate([ts.cumulative, np.repeat(ts.cumulative[:, -1:], CAP_Q - h_q, axis=1)], axis=1)
                for g in range(4):
                    mk = seg_c == g
                    if mk.any():
                        seg_sum[s, g] += pad[mk].sum(axis=0)
                if h_q > STAGE1_MONTHS // PERIOD_MONTHS:
                    proj += w[s] * rv_ts.forward_pd(ts, STAGE1_MONTHS, int(months[-1]))
            hz_m = model.hazard_path(st, aq, mean_lag[:h_q], lp=lp, age_eff=age_eff)
            ts_m = rv_ts.from_hazard(hz_m, months)
            ecl12_m[chunk] = rv_ecl.ecl_scenario(ts_m.marginal, lgd_c, ead_t, eir_c, months, horizon12, CONVENTION)
            ecl_life_m[chunk] = rv_ecl.ecl_scenario(ts_m.marginal, lgd_c, ead_t, eir_c, months, int(months[-1]), CONVENTION)
            hz_o = model.hazard_frozen(st, aq, macro_orig[chunk], h_q, lp=lp, age_eff=age_eff)
            ts_o = rv_ts.from_hazard(hz_o, months)
            f_orig[chunk] = ts_o.cumulative[:, -1]
            k12 = min(h_q, STAGE1_MONTHS // PERIOD_MONTHS)
            pd12[chunk] = cur_w[:, k12 - 1]
            if h_q >= BACKTEST_Q:
                cum12[chunk] = cur_w[:, :BACKTEST_Q]
                cum12_o[chunk] = ts_o.cumulative[:, :BACKTEST_Q]
            if h_q > STAGE1_MONTHS // PERIOD_MONTHS:
                proj_cur[chunk] = proj
                proj_orig[chunk] = rv_ts.forward_pd(ts_o, STAGE1_MONTHS, int(months[-1]))
    # the systematic factor each scenario implies: the book's mean quarterly hazard, annualised, through the engine's implied_z
    avg_h = haz_sum / np.maximum(haz_n, 1.0)[None, :]
    live = haz_n >= 1.0
    z_paths = {}
    for s, sid in enumerate(ids):
        annual = 1.0 - (1.0 - np.clip(avg_h[s, live], 1e-9, 0.5)) ** 4
        z_paths[sid] = np.asarray(rv_ts.implied_z(annual, pd_ttc, RHO), dtype=float)
    n_live = int(live.sum())
    sat = mc.fit_reduced_form(np.concatenate([z_paths[s] for s in ids]),
                              np.vstack([model.clip_macro(macro_lags[s][:n_live]) for s in ids]))
    seg_curves = seg_sum / np.maximum(seg_n, 1.0)[None, :, None]
    seg_curves[n_s] = np.tensordot(w, seg_curves[:n_s], axes=(0, 0))
    h_years = horizon_q * PERIOD_MONTHS / 12.0
    f_w = np.tensordot(w, f_h, axes=(0, 0))
    pd_orig_ann = annualise(f_orig, h_years)
    pd_cur_ann = annualise(f_w, h_years)
    stage_result = allocate_stages(pd_orig_ann, pd_cur_ann, np.zeros(a, dtype=np.int64), np.zeros(a, dtype=bool),
                                   np.zeros(a, dtype=bool), np.zeros(a, dtype=bool), policy)
    h_proj = np.maximum(h_years - 1.0, 0.25)
    proj_cur_ann = annualise(proj_cur, h_proj)
    proj_orig_ann = annualise(proj_orig, h_proj)
    return DateRun(
        reporting_date=r, obs=obs, history=hist, ladder=ladder, idx=idx, age_m=age_m, horizon_q=horizon_q, segment=seg, stratum=stratum, eir=eir,
        eir_imputed=imputed_all[idx], gca=gca, lgd=lgd, lgd_segments=lgd_info, weights=w, scenario_ids=ids, paths=paths,
        macro_mean_path=mean_path, z_hat=(z_q, z_hat), pd_ttc=pd_ttc, satellite=sat, z_paths=z_paths, ecl12=ecl12,
        ecl_life=ecl_life, ecl12_mean=ecl12_m, ecl_life_mean=ecl_life_m, f_h=f_h, f_orig_h=f_orig, cum12=cum12,
        cum12_orig=cum12_o, pd12=pd12, proj_cur_ann=proj_cur_ann, proj_orig_ann=proj_orig_ann, pd_orig_ann=pd_orig_ann,
        pd_cur_ann=pd_cur_ann, stage_result=stage_result, seg_curves=seg_curves, seg_counts=seg_n,
        seg_pd_ttc=_segment_pd_ttc(ladder),
    )
