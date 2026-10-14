"""The ladder of one loan type's illustrative portfolio: rungs C1 to C6, the Euler contributions and the granularity (CT-1104,
CT-1106, CT-1107).

Every loss measure, contribution, adjustment and test row is returned by ``riskvalidation`` (``portfolio.portfolio``,
``portfolio.copula``, ``portfolio.creditrisk_plus``, ``portfolio.granularity``, ``portfolio.importance``, ``portfolio.euler``,
``validation.portfolio``). This module builds the engine's inputs, calls it, and orders its answers into the blocks of the
``c10-outputs`` contract. The loss curve of a rung is the distribution function of the engine's loss sample (or of its
probability mass function) on a money grid: a binning of the engine's output for the plot, never a risk measure.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from riskvalidation.engines import vasicek
from riskvalidation.portfolio import copula, creditrisk_plus, euler, granularity, importance
from riskvalidation.portfolio import portfolio as pf
from riskvalidation.regulatory import irb
from riskvalidation.validation import portfolio as val

from . import params as P
from . import portfolios


def T(en: str, es: str) -> dict[str, str]:
    return {"en": en, "es": es}


class LadderError(ValueError):
    """A rung of the ladder broke an invariant the contract states (the bake stops rather than writing it)."""


@dataclass
class Run:
    """The sizes of one ladder run (full size for the bake, small for the tests)."""

    n_scenarios: int
    n_is: int
    n_crp: int
    n_convergence: int
    n_lhp_names: int
    thin: int = 1
    var_tolerance: float = P.EULER_TOLERANCES["var"]
    seeds: dict[str, int] = field(default_factory=lambda: dict(P.SEEDS))

    @classmethod
    def scaled(cls, scale: float) -> Run:
        if scale >= 1.0:
            return cls(P.FULL_SCENARIOS, P.FULL_IS_SCENARIOS, P.FULL_CRP_SAMPLE, P.FULL_CONVERGENCE_SCENARIOS, P.LHP_LIKE_NAMES)
        s = max(scale, 1e-4)
        return cls(max(20_000, round(P.FULL_SCENARIOS * s)), max(20_000, round(P.FULL_IS_SCENARIOS * s)),
                   max(20_000, round(P.FULL_CRP_SAMPLE * s)), max(20_000, round(P.FULL_CONVERGENCE_SCENARIOS * s)), 400, 10, 0.05)


def measure(m: pf.LossMeasures, es_reason: str | None = None) -> dict[str, Any]:
    """A ``LossMeasures`` as the document's ``measures[*]`` block (they map one to one)."""
    return {"level": m.level, "el": m.el, "var": m.var, "es": m.es, "es_reason": es_reason if m.es is None else None,
            "ec": m.ec, "var_se": m.var_se, "es_se": m.es_se}


def named(name: str, value: float, unit: str) -> dict[str, Any]:
    return {"name": name, "value": float(value), "unit": unit}


# --- the loss curve of a rung on the document's money grid ------------------------------------------------------------------


def money_grid(total_ead: float, lgd: float, pd: float, rho: float, vars_max: float) -> list[float]:
    """Strictly increasing money points: the LHP quantiles from 0.1% to 99.95% and a linear extension past the largest VaR."""
    scale = total_ead * lgd
    body = [scale * vasicek.lhp_quantile(u, pd, rho) for u in np.linspace(0.001, 0.9995, 56)]
    top = max(vars_max * 1.25, body[-1] * 1.05)
    ext = list(np.linspace(body[-1], top, 9)[1:])
    pts = sorted({round(x, 2) for x in [*body, *ext] if x > 0})
    return pts


def curve_from_cdf(grid: list[float], cdf_at, density_at, currency: str) -> dict[str, Any]:
    """``{currency, loss, cdf, density}``: the cdf at the grid and a histogram density from the cdf at the cell edges."""
    g = np.asarray(grid)
    cdf = np.clip(cdf_at(g), 0.0, 1.0)
    cdf = np.maximum.accumulate(cdf)
    dens = density_at(g)
    return {"currency": currency, "loss": [float(x) for x in g], "cdf": [float(x) for x in cdf],
            "density": [float(max(x, 0.0)) for x in dens]}


def histogram_density(cdf_at, grid: np.ndarray) -> np.ndarray:
    """Density at each grid point from the cdf at the midpoints between neighbours (a histogram density, per unit of money)."""
    edges = np.concatenate([[grid[0] - (grid[1] - grid[0]) / 2], (grid[:-1] + grid[1:]) / 2, [grid[-1] + (grid[-1] - grid[-2]) / 2]])
    f = np.clip(cdf_at(edges), 0.0, 1.0)
    return np.maximum(np.diff(f) / np.diff(edges), 0.0)


def sample_cdf(losses: np.ndarray):
    s = np.sort(losses)
    n = s.size
    return lambda x: np.searchsorted(s, x, side="right") / n


def weighted_cdf(res: importance.ImportanceResult):
    order = np.argsort(res.losses)
    s, w = res.losses[order], res.weights[order]
    tail = np.concatenate([[w.sum()], w.sum() - np.cumsum(w)])    # sum of weights of the losses above each point
    n = res.n_scenarios

    def f(x):
        i = np.searchsorted(s, x, side="right")
        return 1.0 - tail[i] / n
    return f


# --- the calibration of the CreditRisk+ rung (a parameter choice, not a risk measure) -----------------------------------------


def vasicek_default_rate_variance(pd: float, rho: float) -> float:
    """Var of the LHP default fraction, E[p(Z)^2] - pd^2, by Gauss-Hermite quadrature of the engine's conditional PD."""
    x, w = np.polynomial.hermite_e.hermegauss(200)
    p = np.array([vasicek.conditional_pd(pd, rho, float(z)) for z in x])
    return float(np.sum(w * p * p) / math.sqrt(2 * math.pi) - pd * pd)


# --- the rungs ------------------------------------------------------------------------------------------------------------------


@dataclass
class Ladder:
    """What the ladder computed, for the document, the tests of the document and the findings."""

    rungs: list[dict[str, Any]]
    euler: list[dict[str, Any]]
    granularity: dict[str, Any]
    tests: list[dict[str, Any]]
    diagnostics: dict[str, Any]
    portfolio: dict[str, Any]


def _expand(groups: list[dict[str, Any]], key: str) -> np.ndarray:
    return np.concatenate([np.full(g["n_names"], g[key], dtype=float) for g in groups])


def build_portfolios(groups: list[dict[str, Any]]) -> tuple[pf.Portfolio, pf.Portfolio]:
    one = pf.portfolio_from_groups(groups, P.CURRENCY, P.LGD_GAMMA, one_factor=True)
    sectors = sorted({g["sector"] for g in groups}, key=[g["sector"] for g in groups].index)
    fc = np.full((len(sectors), len(sectors)), P.SECTOR_CORRELATION)
    np.fill_diagonal(fc, 1.0)
    multi = pf.portfolio_from_groups(groups, P.CURRENCY, P.LGD_GAMMA, factor_corr=fc, one_factor=False)
    return one, multi


def run_ladder(loan_type: dict[str, Any], pd: float, rho: float, groups: list[dict[str, Any]], run: Run) -> Ladder:
    cur = P.CURRENCY
    lt = loan_type["id"]
    n_names = sum(g["n_names"] for g in groups)
    total_ead = sum(g["n_names"] * g["ead_each"] for g in groups)
    chunk = portfolios.chunk_scenarios(n_names)
    one, multi = build_portfolios(groups)
    el = pf.expected_loss(one)
    scale_money = total_ead * P.LGD
    rungs: dict[str, dict[str, Any]] = {}
    diag: dict[str, Any] = {}

    def rung(rid: str, rg: str, method: str, label: dict[str, str], estimator: str, parameters, ms, curve, sim=None,
             diagnostics=None, reason=None) -> dict[str, Any]:
        return {"id": rid, "rung": rg, "method": method, "label": label, "currency": cur, "estimator": estimator,
                "evaluated": ms is not None, "reason": reason, "parameters": parameters, "diagnostics": diagnostics or [],
                "simulation": sim, "measures": ms, "distribution": curve}

    # C1: the large homogeneous portfolio at the fitted (pd, rho)
    c1 = pf.lhp_measures(total_ead, P.LGD, pd, rho, P.LEVELS)

    # C2 / C3: the copula Monte Carlo, with the group losses kept for the Euler contributions
    def mc(rid: str, sample: copula.LossSample) -> tuple[tuple[pf.LossMeasures, ...], copula.LossSample]:
        return pf.measures_from_sample(sample.losses, P.LEVELS, el), sample

    s1 = copula.simulate_gaussian(one, run.n_scenarios, run.seeds["c2-gaussian-1f"], chunk, track_groups=True)
    m1, _ = mc("c2-gaussian-1f", s1)
    smf = copula.simulate_gaussian(multi, run.n_scenarios, run.seeds["c2-gaussian-mf"], chunk, track_groups=True)
    mmf, _ = mc("c2-gaussian-mf", smf)
    st = copula.simulate_student_t(one, P.NU, run.n_scenarios, run.seeds["c3-student-t"], chunk, track_groups=True)
    mt, _ = mc("c3-student-t", st)

    # C4: CreditRisk+, one Gamma sector with the variance of the Vasicek default rate (moment matching)
    sigma2 = vasicek_default_rate_variance(pd, rho) / (pd * pd)
    nu = np.rint(_expand(groups, "ead_each") * P.LGD / P.LOSS_UNIT).astype(np.int64)
    pdv = _expand(groups, "pd")
    inp = creditrisk_plus.CreditRiskPlusInput(nu=nu, pd=pdv, w0=np.zeros(n_names), weights=np.ones((n_names, 1)),
                                              sigma2=np.array([sigma2]), loss_unit=P.LOSS_UNIT, currency=cur)
    total_units = int(nu.sum())
    n_max = max(4000, int(vasicek.lhp_quantile(0.9999, pd, rho) * total_units * 2))
    while True:
        n_max = min(n_max, total_units)
        pmf = creditrisk_plus.pmf_stable(inp, n_max)
        if 1.0 - float(pmf.sum()) < 1e-7 or n_max >= total_units:
            break
        n_max *= 2
    crp_el = float(P.LOSS_UNIT * np.sum(np.arange(pmf.size) * pmf))
    m4 = creditrisk_plus.measures_from_pmf(pmf, P.LOSS_UNIT, P.LEVELS)
    unit_rounding = float(np.abs(nu * P.LOSS_UNIT - _expand(groups, "ead_each") * P.LGD).max())

    # C5: the granularity adjustment of the portfolio, K_i from the IRB formula at the regulatory correlation
    gran = granularity_block(loan_type, groups, pd, rho, total_ead)
    c5 = []
    for m, lv in zip(c1, gran["levels"], strict=True):
        var = m.var + lv["ga_money"]
        c5.append({"level": m.level, "el": m.el, "var": var, "es": None,
                   "es_reason": "the granularity adjustment is a quantile add-on and defines no expected shortfall",
                   "ec": var - m.el, "var_se": None, "es_se": None})

    # C6: importance sampling of the Gaussian copula, the twist targeted at the plain Monte Carlo 99.9% VaR
    threshold = m1[-1].var
    quantum = min(g["ead_each"] * g["lgd"] for g in groups)
    is_res = importance.importance_sample_gaussian(one, threshold, run.n_is, run.seeds["c6-is-gaussian"], None, chunk)
    is_ms: list[dict[str, Any]] | None = []
    is_reason = None
    for q, mp in zip(P.LEVELS, m1, strict=True):
        try:
            var_i, es_i, se_v, se_e = importance.weighted_var_es(is_res, q)
        except ValueError as exc:      # the sample does not reach the level: the rung did not run, and no number stands in for it
            is_ms, is_reason = None, f"importance sampling did not reach the {q:g} level: {exc}"
            break
        for what, a, b, sa, sb in (("VaR", var_i, mp.var, se_v, mp.var_se), ("ES", es_i, mp.es, se_e, mp.es_se)):
            # the loss of this portfolio lives on a lattice, so a quantile is known only to the smallest loss of a name: two unbiased
            # estimators may sit one lattice step apart while their batch-means errors are far smaller than the step
            tol = 4.0 * math.hypot(sa, sb) + (quantum if what == "VaR" else 0.0)
            if abs(a - b) > tol:
                raise LadderError(f"{lt}: the importance-sampling {what} at {q} is {a:.1f}, the plain Monte Carlo {b:.1f}, further "
                                  f"apart than 4 combined standard errors ({math.hypot(sa, sb):.1f}) plus the lattice step {quantum:.0f} for a VaR")
        is_ms.append({"level": q, "el": el, "var": var_i, "es": es_i, "es_reason": None, "ec": var_i - el, "var_se": se_v,
                      "es_se": se_e})
    ratios: list[dict[str, Any]] = []
    ess = float("nan")
    if is_ms is not None:
        scale_n = math.sqrt(run.n_scenarios / run.n_is)          # the plain error at the importance sample's size
        for name, plain, ours in (("variance_ratio_vs_plain_mc", m1[-1].var_se, is_ms[-1]["var_se"]),
                                  ("variance_ratio_es_vs_plain_mc", m1[-1].es_se, is_ms[-1]["es_se"])):
            if plain > 0 and ours > 0:                            # a discrete loss grid can leave a batch-means error at zero
                ratios.append(named(name, importance.variance_ratio(plain * scale_n, ours), "ratio"))
        w = is_res.weights
        ess = float(w.sum() ** 2 / (w.size * np.sum(w * w)))

    # the document's money grid reaches past every rung's VaR
    vmax = max([m.var for m in (*c1, *m1, *mmf, *mt, *m4)] + [x["var"] for x in c5] + [x["var"] for x in (is_ms or [])])
    grid = np.asarray(money_grid(total_ead, P.LGD, pd, rho, vmax))

    def cdf_of_lhp(x):
        return np.array([vasicek.lhp_cdf(min(max(v / scale_money, 1e-12), 1 - 1e-12), pd, rho) for v in x])

    def pdf_of_lhp(x):
        return np.array([vasicek.lhp_pdf(min(max(v / scale_money, 1e-12), 1 - 1e-12), pd, rho) for v in x]) / scale_money

    def crp_cdf(x):
        cum = np.cumsum(pmf)
        k = np.floor(np.asarray(x) / P.LOSS_UNIT + 1e-9).astype(int)
        return np.where(k < 0, 0.0, cum[np.clip(k, 0, cum.size - 1)])

    lbl = {
        "c1-lhp": T("Large homogeneous portfolio (Vasicek)", "Cartera homogénea grande (Vasicek)"),
        "c2-gaussian-1f": T("Gaussian copula, one factor", "Cópula gaussiana, un factor"),
        "c2-gaussian-mf": T("Gaussian copula, sector factors", "Cópula gaussiana, factores sectoriales"),
        "c3-student-t": T("Student-t copula", "Cópula t de Student"),
        "c4-creditrisk-plus": T("CreditRisk+ (stable recursion)", "CreditRisk+ (recursión estable)"),
        "c5-granularity": T("Granularity adjustment", "Ajuste por granularidad"),
        "c6-is-gaussian": T("Importance sampling, Gaussian copula", "Muestreo por importancia, cópula gaussiana"),
        "c6-is-student-t": T("Importance sampling, Student-t copula", "Muestreo por importancia, cópula t"),
    }

    def sim(rid: str, n: int) -> dict[str, int]:
        return {"n_scenarios": n, "seed": run.seeds[rid], "chunk_size": chunk}

    def mcurve(sample):
        f = sample_cdf(sample.losses)
        return curve_from_cdf(list(grid), f, lambda g: histogram_density(f, g), cur)

    r: list[dict[str, Any]] = []
    r.append(rung("c1-lhp", "C1", "lhp-vasicek", lbl["c1-lhp"], "analytic",
                  [named("pd", pd, "decimal"), named("rho", rho, "-"), named("lgd", P.LGD, "decimal")],
                  [measure(m) for m in c1], curve_from_cdf(list(grid), cdf_of_lhp, pdf_of_lhp, cur)))
    r.append(rung("c2-gaussian-1f", "C2", "gaussian-copula-one-factor", lbl["c2-gaussian-1f"], "monte-carlo",
                  [named("rho", rho, "-"), named("lgd", P.LGD, "decimal")], [measure(m) for m in m1], mcurve(s1),
                  sim("c2-gaussian-1f", run.n_scenarios)))
    r.append(rung("c2-gaussian-mf", "C2", "gaussian-copula-multi-factor", lbl["c2-gaussian-mf"], "monte-carlo",
                  [named("n_factors", multi.loadings.shape[1], "-"), named("factor_correlation", P.SECTOR_CORRELATION, "-"),
                   named("rho", rho, "-"), named("lgd", P.LGD, "decimal")], [measure(m) for m in mmf], mcurve(smf),
                  sim("c2-gaussian-mf", run.n_scenarios)))
    r.append(rung("c3-student-t", "C3", "student-t-copula", lbl["c3-student-t"], "monte-carlo",
                  [named("nu", P.NU, "-"), named("rho", rho, "-"), named("lgd", P.LGD, "decimal")], [measure(m) for m in mt],
                  mcurve(st), sim("c3-student-t", run.n_scenarios)))
    r.append(rung("c4-creditrisk-plus", "C4", "creditrisk-plus", lbl["c4-creditrisk-plus"], "analytic",
                  [named("sigma2", sigma2, "-"), named("loss_unit", P.LOSS_UNIT, cur)], [measure(m) for m in m4],
                  curve_from_cdf(list(grid), crp_cdf, lambda g: histogram_density(crp_cdf, g), cur),
                  diagnostics=[named("n_max", pmf.size - 1, "loss units"), named("tail_mass_left_out", 1.0 - float(pmf.sum()), "-"),
                               named("expected_loss", crp_el, cur), named("unit_rounding", unit_rounding, cur)]))
    r.append(rung("c5-granularity", "C5", "granularity-adjustment", lbl["c5-granularity"], "analytic",
                  [named("xi", P.XI, "-"), named("gamma", P.LGD_GAMMA, "-"), named("q", 0.999, "decimal")], c5,
                  curve_from_cdf(list(grid), cdf_of_lhp, pdf_of_lhp, cur)))
    if is_ms is not None:
        wf = weighted_cdf(is_res)
        r.append(rung("c6-is-gaussian", "C6", "importance-sampling", lbl["c6-is-gaussian"], "monte-carlo",
                      [named("threshold", threshold, cur), named("factor_shift", float(is_res.factor_shift[0]), "-")], is_ms,
                      curve_from_cdf(list(grid), wf, lambda g: histogram_density(wf, g), cur), sim("c6-is-gaussian", run.n_is),
                      diagnostics=[*ratios, named("effective_sample_share", ess, "share")]))
    else:
        r.append(rung("c6-is-gaussian", "C6", "importance-sampling", lbl["c6-is-gaussian"], "none",
                      [named("threshold", threshold, cur)], None, None, reason=is_reason))
    r.append(rung("c6-is-student-t", "C6", "importance-sampling", lbl["c6-is-student-t"], "none",
                  [], None, None, reason="the exponential twist of dossier 04 H.7 is derived for the normal copula; no Student-t "
                                         "twist is specified, so the rung did not run and no number stands in for it"))
    for x in r:
        rungs[x["id"]] = x

    # the Euler contributions of the three sample-based rungs, by group, at both levels
    euler_blocks, euler_tests = euler_blocks_for(groups, one, [("gaussian-copula-one-factor", "m-gaussian-1f", s1, m1, rho),
                                                               ("gaussian-copula-multi-factor", "m-gaussian-mf", smf, mmf, None),
                                                               ("student-t-copula", "m-student-t", st, mt, None)], run.var_tolerance)

    # the Monte Carlo against the analytic anchor, on a portfolio of many identical names (the granularity gap is the C5 rung's)
    n_l = run.n_lhp_names
    lhp_like = pf.portfolio_from_groups(
        [{"id": "g-lhp", "n_names": n_l, "ead_each": total_ead / n_l, "pd": pd, "lgd": P.LGD, "loading": math.sqrt(rho), "sector": "core"}],
        cur, P.LGD_GAMMA, one_factor=True)
    s_l = copula.simulate_gaussian(lhp_like, run.n_convergence, run.seeds["convergence"], portfolios.chunk_scenarios(n_l))
    m_l = pf.measures_from_sample(s_l.losses, (0.999,), pf.expected_loss(lhp_like))[0]
    anchor = pf.lhp_measures(total_ead, P.LGD, pd, rho, (0.999,))[0].var
    t_conv = val.mc_convergence(m_l.var, m_l.var_se, anchor, "var", model_id="m-gaussian-1f", segment="lhp-like-99.9")

    # the CreditRisk+ recursion against a Monte Carlo of the same Poisson-Gamma model
    mc_units = crp_sample(groups, nu, sigma2, run.n_crp, run.seeds["crp"])
    t_crp = val.crp_recursion_vs_mc(pmf, mc_units, model_id="m-creditrisk-plus")

    diag.update({"pd": pd, "rho": rho, "sigma2": sigma2, "convergence_estimate": m_l.var, "convergence_anchor": anchor,
                 "convergence_se": m_l.var_se, "unit_rounding": unit_rounding, "is_variance_ratio": ratios[0]["value"] if ratios else None, "chunk": chunk,
                 "n_names": n_names, "lhp_like_names": n_l})
    nh = euler.hhi(one.ead)
    port = {"n_names": n_names, "total_ead": total_ead, "hhi": nh, "effective_names": euler.effective_names(one.ead),
            "largest_share": max(g["ead_each"] for g in groups) / total_ead}
    return Ladder([rungs[i] for i in ("c1-lhp", "c2-gaussian-1f", "c2-gaussian-mf", "c3-student-t", "c4-creditrisk-plus", "c5-granularity",
                                      "c6-is-gaussian", "c6-is-student-t")],
                  euler_blocks, gran, [*euler_tests, t_conv.to_dict(), t_crp.to_dict()], diag, port)


def crp_sample(groups: list[dict[str, Any]], nu: np.ndarray, sigma2: float, n: int, seed: int) -> np.ndarray:
    """A Monte Carlo sample, in loss units, of the Poisson-Gamma model the recursion computes (the comparator of the test row).

    Names of a group are identical, so their Poisson counts add into one Poisson with the summed intensity."""
    rng = np.random.default_rng(np.random.PCG64(seed))
    s = rng.gamma(shape=1.0 / sigma2, scale=sigma2, size=n)
    out = np.zeros(n, dtype=np.int64)
    start = 0
    for g in groups:
        unit = int(nu[start])
        out += unit * rng.poisson(g["n_names"] * g["pd"] * s)
        start += g["n_names"]
    return out


def euler_blocks_for(groups: list[dict[str, Any]], one: pf.Portfolio, items, var_tol: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    blocks, tests = [], []
    ead_g = [g["n_names"] * g["ead_each"] for g in groups]
    for method, model_id, sample, ms, rho in items:
        levels = []
        for m in ms:
            q = m.level
            rc_es = euler.es_contributions(sample.group_losses, sample.losses, q)
            rc_var = euler.var_contributions_kernel(sample.group_losses, sample.losses, q)
            rows = [{"group_id": g["id"], "ead": e, "rc_var": float(v), "rc_es": float(s_), "share_var": float(v) / m.var,
                     "share_es": float(s_) / m.es} for g, e, v, s_ in zip(groups, ead_g, rc_var, rc_es, strict=True)]
            anchor, reason = None, ("the asymptotic one-factor contribution is a Gaussian one-factor result; no closed form is "
                                    "specified for this rung")
            if rho is not None:
                per_name = euler.asrf_var_contributions(one.ead, one.pd, one.lgd, rho, q)
                cut = np.cumsum([0] + [g["n_names"] for g in groups])
                arows = [{"group_id": g["id"], "rc_var": float(per_name[a:b].sum())}
                         for g, a, b in zip(groups, cut[:-1], cut[1:], strict=True)]
                anchor, reason = {"method": "asrf-asymptotic", "asrf_var": float(per_name.sum()), "rows": arows}, None
            levels.append({"level": q, "var_total": m.var, "es_total": m.es, "var_sum_tolerance": var_tol,
                           "es_sum_tolerance": P.EULER_TOLERANCES["es"], "var_method": "kernel", "es_method": "tail-sample",
                           "rows": rows, "anchor": anchor, "anchor_reason": reason})
            tests.append(val.euler_additivity(rc_var, m.var, var_tol, model_id=model_id,
                                              segment=f"var-{q:g}").to_dict())
            tests.append(val.euler_additivity(rc_es, m.es, P.EULER_TOLERANCES["es"], model_id=model_id,
                                              segment=f"es-{q:g}").to_dict())
        blocks.append({"rung_method": method, "currency": P.CURRENCY, "levels": levels})
    return blocks, tests


def irb_k(loan_type: dict[str, Any], pd: float) -> irb.IRBResult:
    kw = {} if loan_type["irb_asset_class"] in ("residential_mortgage", "qrre", "other_retail", "retail_consumer") else {"maturity": P.IRB_MATURITY}
    res = irb.capital_requirement(loan_type["irb_asset_class"], pd, P.LGD, regime=P.IRB_REGIME, **kw)
    if abs(res.pd_applied - pd) > 0.0:
        raise LadderError(f"{loan_type['id']}: the IRB PD floor moved the PD {pd} to {res.pd_applied}; the comparison needs pd as is")
    return res


def granularity_block(loan_type: dict[str, Any], groups: list[dict[str, Any]], pd: float, rho: float, total_ead: float) -> dict[str, Any]:
    n = sum(g["n_names"] for g in groups)
    share = np.concatenate([np.full(g["n_names"], g["ead_each"] / total_ead) for g in groups])
    pds = _expand(groups, "pd")
    k_group = {g["id"]: irb_k(loan_type, g["pd"]).k for g in groups}
    k = np.concatenate([np.full(g["n_names"], k_group[g["id"]]) for g in groups])
    lgd = np.full(n, P.LGD)
    levels = []
    k_star = None
    for q in P.LEVELS:
        res = granularity.granularity_adjustment(share, k, pds, lgd, P.LGD_GAMMA, P.XI, q)
        k_star = res.k_star
        levels.append({"q": q, "alpha_q": res.alpha_q, "delta": res.delta, "ga": res.ga, "ga_money": res.ga * total_ead})
    # n identical names of the portfolio's mix: GA proportional to 1/n, and the CreditRisk+ recursion of the same model
    k_mix = irb_k(loan_type, pd).k
    q = 0.999
    alpha_q = granularity.gamma_quantile(P.XI, q)
    omega = k_mix / (P.LGD * pd * (alpha_q - 1.0))
    rows = []
    for nn in (10, 20, 50, 100, 200, 500, 1000, 2000):
        res = granularity.granularity_adjustment(np.full(nn, 1.0 / nn), np.full(nn, k_mix), np.full(nn, pd), np.full(nn, P.LGD),
                                                 P.LGD_GAMMA, P.XI, q)
        truth, why = None, None
        if not 0.0 < omega <= 1.0:
            why = f"the weight on the systematic factor implied by K ({omega:.3f}) is outside (0, 1]; the recursion was not run"
        else:
            inp = creditrisk_plus.CreditRiskPlusInput(
                nu=np.ones(nn, dtype=np.int64), pd=np.full(nn, pd), w0=np.full(nn, 1.0 - omega), weights=np.full((nn, 1), omega),
                sigma2=np.array([1.0 / P.XI]), loss_unit=1.0, currency=P.CURRENCY)
            n_max = max(40, 4 * nn)
            while True:
                pmf = creditrisk_plus.pmf_stable(inp, n_max)
                if pmf.sum() >= q + 1e-6 or n_max >= 20 * nn:
                    break
                n_max *= 2
            try:
                var_units = creditrisk_plus.measures_from_pmf(pmf, 1.0, (q,))[0].var
            except ValueError as exc:
                why = f"the recursion did not reach the level: {exc}"
            else:
                el_share = P.LGD * pd
                truth = P.LGD * var_units / nn - (el_share + k_mix)
                truth = max(truth, 0.0)
        rows.append({"n_names": nn, "hhi": 1.0 / nn, "ga": res.ga, "truth_ga": truth, "truth_reason": why})
    return {"currency": P.CURRENCY, "xi": P.XI, "gamma": P.LGD_GAMMA, "k_source": "irb-regulatory-correlation", "k_star": k_star,
            "delta_reference": 4.83, "delta_reference_source": "Gordy and Lutkebohmert (2013), eq. 15 and p. 46 (dossier 04 H.5)",
            "levels": levels, "by_n_names_level": q, "by_n_names": rows, "omega_mix": omega}
