"""Experiment 2: the portfolio engine against anchors outside it, against independent implementations written here from the
primary formulas, against its own committed rung, and against a simulator with a known truth.

Parts: (a) four analytic anchors; (b) an independent plain Monte Carlo of the one-factor Gaussian copula, repeated R_MC times with
independent seeds, against the engine's sampler repeated the same way; (c) an independent single-sector Panjer recursion written from
the generating function against the engine's stable recursion and its Panjer recursion; (d) the committed one-million-scenario rung
regenerated; (e) the committed simulator grids read against the binomial band of their 400 replications, and one cell re-run;
(f) the Gaussian importance sampler against plain Monte Carlo over R_IS seeds, and the Euler additivity of the expected-shortfall
contributions.

    python manuscripts/engines-and-test-catalogues/experiments/run_portfolio.py
"""
from __future__ import annotations

import json
import math
import pathlib
import time

import numpy as np
from scipy import integrate, stats

import riskvalidation
from riskvalidation.engines.vasicek import conditional_pd, lhp_cdf, lhp_pdf
from riskvalidation.portfolio import copula, creditrisk_plus as cr, granularity as gr, importance as imp, euler
from riskvalidation.portfolio import portfolio as pf
from riskvalidation.portfolio.asrf_fit import fit_ml, profile_interval
from riskvalidation.regulatory.irb import capital_requirement

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
R_MC, N_MC = 10, 200_000
R_IS, N_IS = 20, 100_000
SEED_MC = 910_001
SEED_CELL = 20261106
CELL_REPS = 200


def read(case: str, name: str) -> dict:
    return json.loads((ROOT / "data" / "derived" / case / f"{name}.json").read_text(encoding="utf-8"))


def anchors(ci: dict, cards: dict) -> dict:
    out = ci["outputs"]
    book = out["portfolio"]
    pd_hat = out["fit"]["maximum_likelihood"]["pd"]["estimate"]
    rho_hat = out["fit"]["maximum_likelihood"]["rho"]["estimate"]
    pts = np.array([0.002, 0.005, 0.01, 0.02, 0.035, 0.05, 0.07])
    areas = np.array([integrate.quad(lambda t: float(lhp_pdf(t, pd_hat, rho_hat)), 0.0, x, limit=200)[0] for x in pts])
    cdf = np.array([float(lhp_cdf(x, pd_hat, rho_hat)) for x in pts])
    res = {"lhp_integral": {"points": pts.tolist(), "max_abs_diff": float(np.abs(areas - cdf).max())}}

    c_out = cards["outputs"]
    pd_c = c_out["fit"]["maximum_likelihood"]["pd"]["estimate"]
    ref = c_out["irb_reference"]
    lgd, corr = 0.45, ref["irb_correlation"]
    thr = (stats.norm.ppf(pd_c) + math.sqrt(corr) * stats.norm.ppf(0.999)) / math.sqrt(1 - corr)
    k_sp = lgd * (stats.norm.cdf(thr) - pd_c)
    k_mod = float(capital_requirement(ref["asset_class"], pd_c, lgd, regime="basel3").k)
    k_lhp = pf.lhp_measures(1.0, lgd, pd_c, corr, (0.999,))[0].ec
    res["irb"] = {"pd": pd_c, "k_scipy": k_sp, "abs_diff_module": abs(k_mod - k_sp), "abs_diff_lhp": abs(k_lhp - k_sp)}

    rungs = {r["id"]: r for r in out["rungs"]}
    crp = rungs["c4-creditrisk-plus"]
    sigma2 = next(p["value"] for p in crp["parameters"] if p["name"] == "sigma2")
    unit = next(p["value"] for p in crp["parameters"] if p["name"] == "loss_unit")
    n_max = int(next(d["value"] for d in crp["diagnostics"] if d["name"] == "n_max"))
    ead = np.concatenate([np.full(g["n_names"], g["ead_each"]) for g in book["groups"]])
    pds = np.concatenate([np.full(g["n_names"], g["pd"]) for g in book["groups"]])
    units = np.rint(ead * book["lgd_mean"] / unit).astype(int)
    inp = cr.CreditRiskPlusInput(nu=units, pd=pds, w0=np.zeros(ead.size), weights=np.ones((ead.size, 1)),
                                 sigma2=np.array([sigma2]), loss_unit=unit, currency=book["currency"])
    pmf = cr.pmf_stable(inp, n_max)
    n = np.arange(pmf.size)
    mean_p = float((n * pmf).sum())
    var_p = float(((n - mean_p) ** 2 * pmf).sum())
    mu = float(pds.sum())
    mean_c = float((units * pds).sum())
    var_c = float((units ** 2 * pds).sum() + sigma2 * mean_c ** 2)
    res["crp_closed_form"] = {"p0_engine": float(pmf[0]), "p0_closed": (1 + sigma2 * mu) ** (-1 / sigma2),
                              "mean_engine": mean_p, "mean_closed": mean_c, "var_engine": var_p, "var_closed": var_c,
                              "rel_gap_var": abs(var_p - var_c) / var_c, "mass_outside": float(1 - pmf.sum()), "n_max": n_max,
                              "sigma2": sigma2}
    # independent single-sector Panjer recursion from the generating function G(z) = (c - s2 Q(z))^(-1/s2), c = 1 + s2 mu
    mu_j = np.bincount(units, weights=pds)
    jmax = mu_j.size - 1
    c = 1.0 + sigma2 * mu
    g = np.zeros(n_max + 1)
    g[0] = c ** (-1.0 / sigma2)
    js = np.arange(1, jmax + 1)
    for m in range(1, n_max + 1):
        top = min(m, jmax)
        jj = js[:top]
        g[m] = np.sum(mu_j[jj] * (sigma2 * (m - jj) + jj) * g[m - jj]) / (c * m)
    alt = cr.pmf_panjer(inp, n_max)
    k = min(g.size, pmf.size, alt.size)
    res["crp_independent"] = {"max_abs_diff_stable": float(np.abs(g[:k] - pmf[:k]).max()),
                              "max_abs_diff_panjer": float(np.abs(g[:k] - alt[:k]).max()),
                              "max_abs_diff_stable_vs_panjer": float(np.abs(pmf[:k] - alt[:k]).max()), "n_compared": k}

    gran = out["granularity"]
    delta = gr.delta(gran["xi"], 0.999)
    k_names = float(capital_requirement("corporate", pd_hat, 0.45, regime="basel3", maturity=2.5).k)
    prods = []
    for nn in (10, 100, 1000, 10_000):
        ones = np.ones(nn)
        prods.append(gr.granularity_adjustment(ones / nn, k_names * ones, pd_hat * ones, 0.45 * ones, gran["gamma"],
                                               gran["xi"], 0.999).ga * nn)
    res["granularity"] = {"delta": delta, "published": 4.83, "matches_printed_digits": round(delta, 2) == 4.83,
                          "ga_times_n": prods, "rel_spread": (max(prods) - min(prods)) / max(prods)}
    return res


def independent_mc(book: dict, rho: float, n: int, seed: int) -> np.ndarray:
    """Plain Monte Carlo of the one-factor Gaussian copula written from the model: default iff sqrt(rho) z + sqrt(1-rho) e < Phi^-1(PD)."""
    rng = np.random.default_rng(seed)
    ead = np.concatenate([np.full(g["n_names"], g["ead_each"] * g["lgd"]) for g in book["groups"]])
    thr = np.concatenate([np.full(g["n_names"], stats.norm.ppf(g["pd"])) for g in book["groups"]])
    out = np.empty(n)
    chunk = 10_000
    for s in range(0, n, chunk):
        m = min(chunk, n - s)
        z = rng.standard_normal((m, 1))
        e = rng.standard_normal((m, ead.size))
        out[s:s + m] = ((math.sqrt(rho) * z + math.sqrt(1 - rho) * e < thr) * ead).sum(axis=1)
    return out


def mc_comparison(ci: dict) -> dict:
    out = ci["outputs"]
    book = out["portfolio"]
    rungs = {r["id"]: r for r in out["rungs"]}
    rho = next(p["value"] for p in rungs["c2-gaussian-1f"]["parameters"] if p["name"] == "rho")
    one = pf.portfolio_from_groups(book["groups"], book["currency"], book["lgd_gamma"], one_factor=True)
    rows = {"engine": [], "independent": []}
    for r in range(R_MC):
        eng = copula.simulate_gaussian(one, N_MC, SEED_MC + r, 16741).losses
        ind = independent_mc(book, rho, N_MC, SEED_MC + 5000 + r)
        for name, x in (("engine", eng), ("independent", ind)):
            rows[name].append([pf.var_from_sample(x, 0.99), pf.es_from_sample(x, 0.99), pf.var_from_sample(x, 0.999),
                               pf.es_from_sample(x, 0.999), float(x.mean())])
    lhp = pf.lhp_measures(book["total_ead"], book["lgd_mean"], float(np.mean([g["pd"] for g in book["groups"]])), rho, (0.99, 0.999))
    names = ["var99", "es99", "var999", "es999", "mean"]
    res = {"replications": R_MC, "scenarios_each": N_MC, "rho": rho, "quantities": {}}
    for j, nm in enumerate(names):
        e = np.array([r[j] for r in rows["engine"]])
        i = np.array([r[j] for r in rows["independent"]])
        se = math.sqrt(e.var(ddof=1) / len(e) + i.var(ddof=1) / len(i))
        res["quantities"][nm] = {"engine_mean": float(e.mean()), "engine_sd": float(e.std(ddof=1)),
                                 "independent_mean": float(i.mean()), "independent_sd": float(i.std(ddof=1)),
                                 "z_difference": float((e.mean() - i.mean()) / se)}
    res["expected_loss_exact"] = pf.expected_loss(one)
    return res


def regeneration(ci: dict) -> dict:
    out = ci["outputs"]
    book = out["portfolio"]
    committed = {r["id"]: r for r in out["rungs"]}["c2-gaussian-1f"]
    sim = committed["simulation"]
    one = pf.portfolio_from_groups(book["groups"], book["currency"], book["lgd_gamma"], one_factor=True)
    t0 = time.time()
    sample = copula.simulate_gaussian(one, sim["n_scenarios"], sim["seed"], sim["chunk_size"])
    rerun = pf.measures_from_sample(sample.losses, (0.99, 0.999), pf.expected_loss(one))
    rel = []
    for m, c in zip(rerun, committed["measures"]):
        rel.extend(abs(a - b) / b for a, b in ((m.var, c["var"]), (m.es, c["es"]), (m.var_se, c["var_se"]), (m.es_se, c["es_se"])))
    return {"n_scenarios": sim["n_scenarios"], "seed": sim["seed"], "chunk": sim["chunk_size"], "max_rel_diff": max(rel),
            "values_compared": len(rel), "seconds": time.time() - t0, "baked_by": ci["provenance"]["riskvalidation_version"]}


def grids() -> dict:
    res = {}
    for years in (22, 40):
        g = read("C10", f"grid-{years}")
        n_rep = g["outputs"]["generator"]["n_replications"]
        cells = []
        for c in g["outputs"]["cells"]:
            row = {"rho": c["known_rho"]}
            for e in c["estimators"]:
                cov = e["coverage"]
                se = math.sqrt(0.95 * 0.05 / n_rep)
                row[e["estimator"]] = {"coverage": cov, "bias": e["bias"], "rmse": e["rmse"], "z_coverage": (cov - 0.95) / se}
            cells.append(row)
        res[str(years)] = {"n_replications": n_rep, "cells": cells}
    return res


def cell_rerun(g22: dict) -> dict:
    gen = g22["outputs"]["generator"]
    rng = np.random.default_rng(SEED_CELL)
    out = []
    for rho in (0.02, 0.12, 0.24):
        cov, est = [], []
        for _ in range(CELL_REPS):
            x = np.asarray(conditional_pd(gen["known_pd"], rho, rng.standard_normal(gen["series_length_years"])))
            f = fit_ml(x)
            lo, hi = profile_interval(x, 0.95)["rho"]
            cov.append(lo <= rho <= hi)
            est.append(f.rho)
        p = float(np.mean(cov))
        out.append({"rho": rho, "coverage": p, "coverage_se": math.sqrt(p * (1 - p) / CELL_REPS),
                    "bias": float(np.mean(est) - rho), "bias_se": float(np.std(est, ddof=1) / math.sqrt(CELL_REPS))})
    return {"reps": CELL_REPS, "seed": SEED_CELL, "series_years": gen["series_length_years"], "cells": out}


def is_and_euler(ci: dict) -> dict:
    out = ci["outputs"]
    book = out["portfolio"]
    rungs = {r["id"]: r for r in out["rungs"]}
    one = pf.portfolio_from_groups(book["groups"], book["currency"], book["lgd_gamma"], one_factor=True)
    thr = [m for m in rungs["c2-gaussian-1f"]["measures"] if m["level"] == 0.999][0]["var"]
    plain, isr = [], []
    for r in range(R_IS):
        x = copula.simulate_gaussian(one, N_IS, 777_000 + r, 16741).losses
        plain.append(float(np.mean(x >= thr)))
        res = imp.importance_sample_gaussian(one, thr, N_IS, 888_000 + r)
        isr.append(float(np.mean(res.weights * (res.losses >= thr))))
    plain, isr = np.array(plain), np.array(isr)
    se = math.sqrt(plain.var(ddof=1) / R_IS + isr.var(ddof=1) / R_IS)
    s = copula.simulate_gaussian(one, 200_000, 4242, 16741, track_groups=True)
    contrib = euler.es_contributions(s.group_losses, s.losses, 0.99)
    es = pf.es_from_sample(s.losses, 0.99)
    return {"threshold": thr, "replications": R_IS, "scenarios_each": N_IS,
            "plain_mean": float(plain.mean()), "plain_sd": float(plain.std(ddof=1)),
            "is_mean": float(isr.mean()), "is_sd": float(isr.std(ddof=1)), "z_difference": float((plain.mean() - isr.mean()) / se),
            "variance_ratio": float(plain.var(ddof=1) / isr.var(ddof=1)),
            "euler_sum": float(contrib.sum()), "es": es, "euler_rel_gap": abs(float(contrib.sum()) - es) / es,
            "student_t_rung": {"evaluated": rungs["c6-is-student-t"]["evaluated"], "reason": rungs["c6-is-student-t"]["reason"]}}


def main() -> None:
    ci, cards, g22 = read("C10", "commercial-industrial"), read("C10", "credit-cards"), read("C10", "grid-22")
    result = {"riskvalidation": riskvalidation.__version__}
    for name, fn in (("anchors", lambda: anchors(ci, cards)), ("mc", lambda: mc_comparison(ci)),
                     ("regeneration", lambda: regeneration(ci)), ("grids", grids), ("cell", lambda: cell_rerun(g22)),
                     ("is_euler", lambda: is_and_euler(ci))):
        t0 = time.time()
        result[name] = fn()
        print(name, f"{time.time() - t0:.0f}s")
    (HERE / "results_portfolio.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in ("grids",)}, indent=1)[:6000])


if __name__ == "__main__":
    main()
