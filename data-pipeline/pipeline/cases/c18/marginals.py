"""The four marginals at one year and 99.9 percent (decision Q5), each from the engine, with the EC = VaR - EL basis (decision W2).

* **Credit**: the engine's grouped copula (``portfolio_from_groups`` and ``simulate_gaussian``) on the six C07 segments: each segment
  is a group of representative names that carry its exposure, PD, LGD and asset correlation, one systematic factor.
* **Market**: C11's mixed-portfolio VaR and ES (champion of the 1 percent level, last forecast day) moved to 99.9 percent and one year
  by two named conventions (the normal quantile ratio and the square root of 250, decision W4) and scaled to the market share of RWA.
  C11 publishes a VaR and an ES, not a distribution, so the marginal the copula needs is the zero-mean Student t whose scale and degrees
  of freedom reproduce the scaled VaR and ES; its VaR and ES are then read from the engine on the quantile grid of it.
* **IRRBB**: the engine's Hull-White one-factor simulation on C15's committed curve and book (the same seed and parameters), the
  economic value change of each path with the losses of the two currency legs added and gains not netted across currencies (SRP31.129).
* **Operational**: ``oprisk.aggregate`` on the C17 generator parameters of ``xi-0-8``, the frequency scaled by Banco Andino's assets
  over the C17 bank's, the euro severities converted at the BCCh rate of the as-of date (decision W5). An infinite-mean severity
  reports its expected loss as undefined and its EC as the VaR alone.

The VaR, ES, EL and Monte Carlo errors are the engine's (``portfolio.portfolio``, ``oprisk.aggregate``, ``irrbb.simulation``). Where
the pipeline fits (the Student t of the market marginal) it fits a distribution to two engine-free inputs, and the result is checked
back through the engine's estimators.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist
from typing import Any, Callable

import numpy as np
from riskvalidation.aggregation import copulas as rv_cop
from riskvalidation.irrbb import eve_nii, shocks, simulation
from riskvalidation.oprisk import aggregate as rv_agg
from riskvalidation.oprisk import sla as rv_sla
from riskvalidation.portfolio import copula as rv_pcop
from riskvalidation.portfolio import portfolio as rv_port
from scipy import optimize, stats

from . import params as P
from .anchors import Anchors

T = P.text
Ppf = Callable[[np.ndarray], np.ndarray]


@dataclass(frozen=True)
class Marginal:
    risk: str
    el: float | None                 # None: undefined (infinite mean)
    var: float
    es: float
    ec: float
    var_se: float | None
    ppf: Ppf
    el_for_aggregate: float          # the EL the aggregation subtracts (0.0 where undefined: the EC is the VaR alone)
    producer: str
    source_documents: list[str]
    statement: dict[str, str]
    parameters: list[str]            # the names of the named parameters scaling this marginal
    extras: dict[str, Any]


# ------------------------------------------------------------------------------------------------ credit


def credit(anchors: Anchors, n_draws: int = P.N_DRAWS, seed: int = P.SEED, chunk: int = P.CHUNK) -> Marginal:
    groups = []
    for s in anchors.segments:
        n = min(s.accounts, P.CREDIT_NAMES_PER_SEGMENT)
        groups.append({"id": s.segment_id, "n_names": n, "ead_each": s.exposure_clp_m / n, "pd": s.pd, "lgd": s.lgd, "loading": math.sqrt(s.rho),
                       "sector": "systematic"})
    port = rv_port.portfolio_from_groups(groups, "CLP", P.CREDIT_LGD_GAMMA, one_factor=True, label="banco-andino-c07-segments")
    el = rv_port.expected_loss(port)
    sample = rv_pcop.simulate_gaussian(port, n_draws, seed, chunk)
    m = rv_port.measures_from_sample(sample.losses, [P.LEVEL], el)[0]
    srt = np.sort(sample.losses)
    return Marginal("credit", el, m.var, m.es or 0.0, m.ec, m.var_se, rv_cop.marginal_ppf_sample(srt), el, "credit-grouped-copula-c07-segments",
                    ["c07-outputs", "riskvalidation.portfolio.portfolio.portfolio_from_groups", "riskvalidation.portfolio.copula.simulate_gaussian"],
                    T("No scaling: the engine's grouped copula runs on the six C07 segments of Banco Andino, each a group of "
                      f"{P.CREDIT_NAMES_PER_SEGMENT} representative names that carry the segment's exposure, PD, LGD and asset correlation (one systematic "
                      "factor); the accounts number 171,500, which no simulation of 10^6 scenarios could carry name by name."),
                    [], {"n_draws": n_draws, "seed": seed, "names": int(port.ead.size), "es_se": m.es_se})


# ------------------------------------------------------------------------------------------------ market


def _t_es_over_var(nu: float, level: float) -> float:
    """ES/VaR of a standard Student t at ``level``: a fit helper for the family, not a reported number."""
    x = stats.t.ppf(level, nu)
    es = stats.t.pdf(x, nu) / (1.0 - level) * (nu + x * x) / (nu - 1.0)
    return float(es / x)


def market_scaling() -> dict[str, float]:
    nd = NormalDist()
    level = nd.inv_cdf(P.LEVEL) / nd.inv_cdf(P.SOURCE_LEVEL)
    horizon = math.sqrt(P.TRADING_DAYS / 1.0)
    return {"level_factor": round(level, 10), "horizon_factor": round(horizon, 10), "value": round(level * horizon, 10)}


def market(anchors: Anchors, n_draws: int = P.N_DRAWS) -> Marginal:
    c11 = anchors.c11_champion
    sc = market_scaling()
    notional = anchors.rwa_by_risk["market"]
    var_t, es_t = c11["var"] * sc["value"] * notional, c11["es"] * sc["value"] * notional
    target = es_t / var_t
    lo, hi = 2.02, 400.0
    if not (_t_es_over_var(hi, P.LEVEL) <= target <= _t_es_over_var(lo, P.LEVEL)):
        raise ValueError(f"the scaled ES/VaR {target:.4f} is outside what a Student t can reproduce at {P.LEVEL}")
    nu = float(optimize.brentq(lambda v: _t_es_over_var(v, P.LEVEL) - target, lo, hi, xtol=1e-12))
    scale = var_t / float(stats.t.ppf(P.LEVEL, nu))
    # the quantile grid of the fitted law at the Hazen positions (i - 0.5) / n: a deterministic "sample", so no Monte Carlo noise enters the
    # marginal; the engine's VaR and ES estimators read it back
    positions = (np.arange(1, n_draws + 1) - 0.5) / n_draws
    sample = scale * stats.t.ppf(positions, nu)
    m_var, m_es = rv_port.var_from_sample(sample, P.LEVEL), rv_port.es_from_sample(sample, P.LEVEL)
    ppf = rv_cop.marginal_ppf_sample(sample)
    return Marginal("market", 0.0, m_var, m_es, m_var, None, ppf, 0.0, "market-c11-mixed-portfolio-scaled-to-market-rwa",
                    [f"c11-outputs mixed-2023 ({c11['model_id']}, alpha 0.01, {c11['date']})", "market share of RWA from the 20-F mix (ratio)"],
                    T("C11's mixed-portfolio VaR and ES of the last forecast day, moved from 99 percent and one day to 99.9 percent and one year by the normal "
                      "quantile ratio and the square root of 250 (two conventions), and scaled to the market share of RWA: the position value is taken as the "
                      "market RWA of Banco Andino. The expected loss is zero (a zero-mean return)."),
                    ["market_rwa_share", "market_horizon_scaling"],
                    {"nu": nu, "scale": scale, "target_var": var_t, "target_es": es_t, "c11": c11, "notional_clp_m": notional, "scaling": sc})


# ------------------------------------------------------------------------------------------------ irrbb


def irrbb(anchors: Anchors, n_paths: int = P.N_PATHS_IRRBB) -> Marginal:
    """The EVE loss of the Hull-White paths of C15 (same curve, book, parameters and seed), losses of the two legs added."""
    o, models = anchors.c15, anchors.c15_models
    uf = o["ur_currency"]["uf_value"]
    mid = np.array([b["midpoint_years"] for b in models["buckets"]])
    floors = {"CLP": 0.0, "UR": -0.02}
    conv = {"CLP": 1.0, "UR": uf}
    key = {"CLP": "clp", "UR": "ur"}
    loss = np.zeros(n_paths)
    legs = []
    for leg in o["legs"]:
        n = leg["leg"]
        r0 = np.array(o["curves"][key[n]]["zero_rates_at_midpoints"])
        flows = np.zeros(19)
        for it in leg["items"]:
            for cf in it["cash_flows"]:
                flows[cf["bucket"] - 1] += cf["amount"] * conv[n]
        base_eve = float(eve_nii.eve(flows, r0, mid))
        ear = next(x for x in o["ear_evar"] if x["leg"] == n)
        if abs(base_eve - ear["base_eve"]) > 1e-6 * max(1.0, abs(base_eve)):
            raise ValueError(f"C15 {n} leg: the base EVE rebuilt from the committed items {base_eve} differs from the document's {ear['base_eve']}")
        sigma = next(p["value"] for p in ear["parameters"] if p["name"] == "sigma")
        a = next(p["value"] for p in ear["parameters"] if p["name"] == "a")
        paths = simulation.hw1f_scenarios(r0, mid, a, sigma, ear["horizon_months"], n_paths, ear["seed"])
        shift = (paths[:, -1] - paths[:, 0]) * 1e4
        eve_p = np.array([eve_nii.eve(flows, shocks.apply_floor(r0, np.full(19, d), floors[n]), mid) for d in shift])
        leg_loss = base_eve - eve_p
        loss += leg_loss
        legs.append({"leg": n, "base_eve": base_eve, "sigma": sigma, "a": a, "seed": ear["seed"], "mean_loss": float(leg_loss.mean())})
    el = float(loss.mean())
    srt = np.sort(loss)
    m = rv_port.measures_from_sample(loss, [P.LEVEL], el)[0]
    return Marginal("irrbb", el, m.var, m.es or 0.0, m.ec, m.var_se, rv_cop.marginal_ppf_sample(srt), el, "irrbb-engine-simulation-c15-curve-and-book",
                    [f"c15-outputs ({anchors.sources['c15_variant']})", "riskvalidation.irrbb.simulation.hw1f_scenarios"],
                    T("No scaling: the engine's Hull-White one-factor simulation runs on C15's curve and book of Banco Andino (the paths, parameters and seed of "
                      "C15); the economic value lost on each path is taken per currency leg and the two legs are added (EVE is additive across the legs "
                      "of one balance sheet; the standardised measure of C15 nets nothing across currencies, a rule of the prescribed shocks that a simulation of one rate "
                      "factor does not need)."),
                    [], {"n_paths": n_paths, "legs": legs, "es_se": m.es_se})


# ------------------------------------------------------------------------------------------------ operational


def operational(anchors: Anchors, fx_rate: float, n_points: int = 1 << 21) -> Marginal:
    """The compound Poisson annual loss of the C17 ``xi-0-8`` generator scaled to Banco Andino, in CLP millions."""
    g, gen = anchors.c17_generator, anchors.c17
    xi, beta, loc = gen["tail_index"], gen["scale_eur"], gen["location_eur"]
    bank_assets_eur_m = g["assets_eur_bn"] * 1000.0
    scaling = anchors.total_assets_clp_m / (bank_assets_eur_m * fx_rate)
    lam = gen["lambda_per_year"] * scaling
    par = (xi, beta, loc)
    infinite = bool(gen["infinite_mean"]) or xi >= 1.0
    # a grid that carries the 99.9 percent quantile and the tail beyond it to about a millionth of the mass
    q_sla = float(rv_sla.sla_var(lam, "gpd", par, P.LEVEL))
    extent = 4.0 * q_sla * (1e3 ** xi)
    last: Exception | None = None
    for _ in range(6):
        step = extent / n_points
        f = rv_agg.discretise_severity("gpd", par, step, n_points)
        h = rv_agg.fft_aggregate("poisson", (lam,), f, padding_factor=4)
        missing = float(max(0.0, 1.0 - h.sum()))
        try:
            rv_agg.quantile_from_pmf(h, step, P.LEVEL)       # the engine refuses a grid that does not reach the quantile
        except ValueError as exc:
            last = exc
            extent *= 4.0
            continue
        if missing <= 1e-6:
            break
        extent *= 4.0
    else:
        raise ValueError(f"the operational grid never carried the quantile and the tail: {last}")
    h = np.maximum(h, 0.0)
    unit = fx_rate / 1e6                                  # EUR -> CLP millions
    grid = np.arange(n_points) * step * unit
    pmf = h.copy()
    pmf[-1] += max(0.0, 1.0 - pmf.sum())                   # the mass beyond the grid (at most a millionth) sits on its last node
    pmf = pmf / pmf.sum()
    var = rv_agg.quantile_from_pmf(h, step, P.LEVEL) * unit
    if infinite:
        # the contract reports the expected loss as undefined and the EC as the VaR alone (W5), but the engine has no ES for an infinite mean
        # and the document has no field for its absence: the variant of decision Y1 (xi-0-8) is finite, and another is refused here
        raise ValueError(f"the C17 variant has an infinite-mean severity (xi {xi}): no expected shortfall exists to write for the operational marginal")
    el = float(rv_agg.compound_poisson_moments(lam, "gpd", par).mean) * unit
    es = float(rv_agg.es_for_severity(h, step, P.LEVEL, "gpd", par)) * unit
    ec, el_agg = var - el, el
    return Marginal("operational", el, var, es, ec, None, rv_cop.marginal_ppf_pmf(grid, pmf), el_agg, "operational-oprisk-aggregate-c17-parameters-scaled",
                    ["c17-models generator parameters (xi-0-8)", "riskvalidation.oprisk.aggregate"],
                    T("The C17 generator frequency scaled by assets, the loss distribution recomputed through oprisk.aggregate (Fourier aggregation of the "
                      "Poisson-generalised-Pareto compound) and converted at the BCCh EUR to CLP rate of the as-of date."),
                    ["asset_scaling", "operational_conversion_rate"],
                    {"lambda_per_year": lam, "asset_scaling": scaling, "grid_step_eur": step, "grid_points": n_points, "missing_mass": missing,
                     "infinite_mean": infinite, "fx_rate": fx_rate, "tail_index": xi})


def all_marginals(anchors: Anchors, fx_rate: float, n_draws: int = P.N_DRAWS, n_paths: int = P.N_PATHS_IRRBB) -> list[Marginal]:
    return [credit(anchors, n_draws), market(anchors, n_draws), irrbb(anchors, n_paths), operational(anchors, fx_rate)]
