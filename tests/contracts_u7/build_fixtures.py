"""Builds the three U7-S fixture documents (docs/contracts/fixtures/c10).

Run: ``python tests/contracts_u7/build_fixtures.py``. Deterministic, standard library only. The numbers are round and small on
purpose; every identity the contract promises (docs/contracts/engine/portfolio-api.md) is computed here from the formulas of
dossier 04 sections C.4 and H (the Vasicek quantile, the implied factor, the LHP expected shortfall, the granularity delta), but
the documents are fixtures, never results: every one is labelled ``fixture`` in its provenance and its ids, and the portfolio is
labelled ``illustrative``. The loss rates are made up for the contract and are not the Federal Reserve's.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from statistics import NormalDist

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "docs" / "contracts" / "fixtures" / "c10"
ND = NormalDist()
GEN = "fixture:u7-s-contracts"
NE = "fixture: the test did not run, no number stands in for it"


def r(x: float, d: int = 9) -> float:
    return round(x, d)


def txt(en: str, es: str) -> dict:
    return {"en": en, "es": es}


# --- the Vasicek formulas (dossier 04 C.4 and H.1) ------------------------------------------------------------------


def lhp_cdf(x: float, pd: float, rho: float) -> float:
    return ND.cdf((math.sqrt(1 - rho) * ND.inv_cdf(x) - ND.inv_cdf(pd)) / math.sqrt(rho))


def lhp_quantile(q: float, pd: float, rho: float) -> float:
    return ND.cdf((ND.inv_cdf(pd) + math.sqrt(rho) * ND.inv_cdf(q)) / math.sqrt(1 - rho))


def lhp_pdf(x: float, pd: float, rho: float) -> float:
    g = ND.inv_cdf(x)
    return math.sqrt((1 - rho) / rho) * math.exp(0.5 * g * g - (math.sqrt(1 - rho) * g - ND.inv_cdf(pd)) ** 2 / (2 * rho))


def implied_factor(x: float, pd: float, rho: float) -> float:
    return (ND.inv_cdf(pd) - math.sqrt(1 - rho) * ND.inv_cdf(x)) / math.sqrt(rho)


def lhp_es(pd: float, rho: float, q: float, steps: int = 4000) -> float:
    z0, lo = ND.inv_cdf(1 - q), ND.inv_cdf(1 - q) - 12.0
    h = (z0 - lo) / steps
    f = lambda z: ND.cdf((ND.inv_cdf(pd) - math.sqrt(rho) * z) / math.sqrt(1 - rho)) * ND.pdf(z)
    s = f(lo) + f(z0) + sum((4 if k % 2 else 2) * f(lo + k * h) for k in range(1, steps))
    return s * h / 3 / (1 - q)


def binom_upper(k: int, n: int, p: float) -> float:
    return sum(math.comb(n, j) * p**j * (1 - p) ** (n - j) for j in range(k, n + 1))


def gamma_lower(a: float, x: float) -> float:
    term = total = 1.0 / a
    n = 0
    while abs(term) > 1e-16 * abs(total):
        n += 1
        term *= x / (a + n)
        total += term
    return total * math.exp(-x + a * math.log(x) - math.lgamma(a))


def gamma_quantile(xi: float, q: float) -> float:
    """q-quantile of the Gamma factor with shape xi and rate xi (mean 1, variance 1/xi): the reading that gives delta 4.83."""
    lo, hi = 0.0, 1.0
    while gamma_lower(xi, xi * hi) < q:
        hi *= 2
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if gamma_lower(xi, xi * mid) < q else (lo, mid)
    return (lo + hi) / 2


def wilson(p: float, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


# --- the envelope -------------------------------------------------------------------------------------------------


def envelope_common(truth: str, illustrative: bool) -> dict:
    inputs = [{"source": "fixture-not-a-result", "class": "fixture", "files": []}]
    classes = {"fixture-not-a-result": "fixture"}
    if illustrative:
        inputs.append({"source": "illustrative-portfolio", "class": "illustrative", "files": []})
        classes["illustrative-portfolio"] = "illustrative"
    return {
        "provenance": {"truth_status": truth, "inputs": inputs, "licence_classes": classes, "generators": [GEN], "seed": 0,
                       "code_version": "fixture", "riskvalidation_version": None},
        "lane": {"lane": "precompute", "reasons": ["fixture"]},
    }


def test_row(test_id: str, model_id: str | None, reason: str) -> dict:
    return {"test_id": test_id, "model_id": model_id, "segment": None, "statistic": None, "p_value": None, "metric": None,
            "h0": "fixture row", "alternative": "fixture row", "policy_version": "fixture", "alpha_amber": None,
            "alpha_red": None, "light": "not_evaluated", "n": None, "n_events": None, "inputs_hash": "0" * 64,
            "reference": "fixture, not a result", "notes": reason, "extras": {}}


def eval_row(test_id: str, model_id: str | None, h0: str, statistic, p_value, metric, light: str, n, n_events, extras: dict,
             amber: float = 0.05, red: float = 0.01) -> dict:
    return {"test_id": test_id, "model_id": model_id, "segment": None, "statistic": statistic, "p_value": p_value,
            "metric": metric, "h0": h0, "alternative": "fixture row", "policy_version": "fixture", "alpha_amber": amber,
            "alpha_red": red, "light": light, "n": n, "n_events": n_events, "inputs_hash": "0" * 64,
            "reference": "fixture, not a result", "notes": "fixture row with round numbers, not a result", "extras": extras}


def model_summary(mid: str, rung: str) -> dict:
    return {"id": mid, "family": "portfolio-credit-capital", "rung": rung,
            "title": txt(f"Fixture model {mid}", f"Modelo de ejemplo {mid}"), "short_title": txt(mid, mid),
            "engine": "riskvalidation", "engine_version": "fixture", "licence": "BSD-3-Clause", "calibration": None,
            "parameters": {}, "checkpoint_sha256": None}


def model_record(mid: str, rung: str) -> dict:
    d = model_summary(mid, rung)
    d["details"] = {}
    return d


MODEL_IDS = [("m-lhp", "C1"), ("m-gaussian-1f", "C2"), ("m-student-t", "C3")]

# --- the loan-type fixture (residential) --------------------------------------------------------------------------

PD_HAT, RHO_HAT, LGD = 0.0030, 0.06, 0.45
RATES = {1985: 0.0020, 1986: 0.0024, 1987: 0.0028, 1988: 0.0030, 1989: 0.0034, 1990: None, 1991: 0.0052, 1992: 0.0050,
         1993: 0.0042, 1994: 0.0034, 1995: 0.0030, 1996: 0.0028, 1997: 0.0026, 1998: 0.0024, 1999: 0.0022, 2000: 0.0024,
         2001: 0.0030, 2002: 0.0036, 2003: 0.0036, 2004: 0.0030, 2005: 0.0026, 2006: 0.0028, 2007: 0.0045, 2008: 0.0085,
         2009: 0.0160, 2010: 0.0230, 2011: 0.0120, 2012: 0.0080}
QUANTILE_LEVELS = [0.5, 0.9, 0.95, 0.99, 0.999]
CURVE_X = [0.0005, 0.001, 0.002, 0.003, 0.004, 0.006, 0.008, 0.012, 0.016, 0.024, 0.032]
CUR = "USD"
GROUPS = [
    {"id": "g-large", "label": txt("Large names", "Nombres grandes"), "n_names": 10, "ead_each": 4000000.0, "pd": 0.0015,
     "lgd": LGD, "loading": 0.22, "sector": "prime"},
    {"id": "g-mid", "label": txt("Mid-size names", "Nombres medianos"), "n_names": 50, "ead_each": 600000.0, "pd": 0.0030,
     "lgd": LGD, "loading": 0.25, "sector": "prime"},
    {"id": "g-small", "label": txt("Small names", "Nombres pequenos"), "n_names": 1000, "ead_each": 30000.0, "pd": 0.0050,
     "lgd": LGD, "loading": 0.30, "sector": "near-prime"},
]
TOTAL_EAD = sum(g["n_names"] * g["ead_each"] for g in GROUPS)
HHI = sum(g["n_names"] * (g["ead_each"] / TOTAL_EAD) ** 2 for g in GROUPS)
NOTICE_ILLUSTRATIVE = txt("Illustrative portfolio: constructed for the contract, never a bank's.",
                          "Cartera ilustrativa: construida para el contrato, nunca la de un banco.")
FIXTURE_NOTICE = txt("Fixture, not a result. Round numbers for the contract.",
                     "Ejemplo, no es un resultado. Numeros redondos para el contrato.")
ALPHA_Q = r(gamma_quantile(0.25, 0.999), 9)
DELTA = r((ALPHA_Q - 1) * (0.25 + 0.75 / ALPHA_Q), 9)
SCALE_X = TOTAL_EAD * LGD


def named(name: str, value: float, unit: str) -> dict:
    return {"name": name, "value": value, "unit": unit}


def curve(scale: float) -> dict:
    """The loss distribution of a rung: the LHP curve with the loss axis stretched by `scale` (a fixture shape)."""
    loss = [r(x * SCALE_X, 2) for x in CURVE_X]
    return {"currency": CUR, "loss": loss,
            "cdf": [r(lhp_cdf(x / scale, PD_HAT, RHO_HAT)) for x in CURVE_X],
            "density": [r(lhp_pdf(x / scale, PD_HAT, RHO_HAT) / scale / SCALE_X, 12) for x in CURVE_X]}


def measures(scale_var: float, scale_es: float, el: float, se: tuple[float, float] | None, ga_money: dict | None = None) -> list[dict]:
    out = []
    for q in (0.99, 0.999):
        var = SCALE_X * lhp_quantile(q, PD_HAT, RHO_HAT) * scale_var
        es = SCALE_X * lhp_es(PD_HAT, RHO_HAT, q) * scale_es
        m = {"level": q, "el": r(el, 2), "var": r(var, 2), "es": r(es, 2), "es_reason": None, "ec": r(var - el, 2),
             "var_se": None, "es_se": None}
        if se is not None:
            m["var_se"], m["es_se"] = r(se[0] * var, 2), r(se[1] * es, 2)
        if ga_money is not None:
            m["var"] = r(var + ga_money[q], 2)
            m["ec"] = r(m["var"] - el, 2)
            m["es"], m["es_reason"] = None, "the granularity adjustment is a quantile add-on and defines no expected shortfall"
        out.append(m)
    return out


def rung(rid: str, rung_id: str, method: str, label: tuple[str, str], estimator: str, parameters: list, ms: list | None,
         curve_scale: float | None, simulation: dict | None = None, diagnostics: list | None = None,
         reason: str | None = None) -> dict:
    return {"id": rid, "rung": rung_id, "method": method, "label": txt(*label), "currency": CUR, "estimator": estimator,
            "evaluated": ms is not None, "reason": reason, "parameters": parameters, "diagnostics": diagnostics or [],
            "simulation": simulation, "measures": ms, "distribution": None if curve_scale is None else curve(curve_scale)}


def asrf_rows(q: float, rho: float) -> list[dict]:
    """The asymptotic one-factor VaR contribution of each group: ead lgd p(G(1 - q)) summed over its names (dossier 04 C.4;
    the first term of Emmer and Tasche 2005 eq. 2.17)."""
    z = ND.inv_cdf(1 - q)
    return [{"group_id": g["id"],
             "rc_var": r(g["n_names"] * g["ead_each"] * g["lgd"]
                         * ND.cdf((ND.inv_cdf(g["pd"]) - math.sqrt(rho) * z) / math.sqrt(1 - rho)), 2)} for g in GROUPS]


def euler_level(q: float, var_total: float, es_total: float, v_share: list[float], e_share: list[float], v_bias: float,
                anchor: bool) -> dict:
    rows = []
    for k, g in enumerate(GROUPS):
        ead = g["n_names"] * g["ead_each"]
        rc_var = r(var_total * v_share[k] * (1 + (v_bias if k == len(GROUPS) - 1 else 0.0)), 2)
        rc_es = r(es_total * e_share[k], 2)
        rows.append({"group_id": g["id"], "ead": ead, "rc_var": rc_var, "rc_es": rc_es, "share_var": 0.0, "share_es": 0.0})
    rows[-1]["rc_es"] = r(es_total - sum(x["rc_es"] for x in rows[:-1]), 2)
    for x in rows:
        x["share_var"], x["share_es"] = r(x["rc_var"] / var_total), r(x["rc_es"] / es_total)
    return {"level": q, "var_total": var_total, "es_total": es_total, "var_sum_tolerance": 0.01, "es_sum_tolerance": 1e-6,
            "var_method": "kernel", "es_method": "tail-sample", "rows": rows,
            "anchor": ({"method": "asrf-asymptotic", "asrf_var": r(sum(x["rc_var"] for x in asrf_rows(q, RHO_HAT)), 2),
                        "rows": asrf_rows(q, RHO_HAT)} if anchor else None),
            "anchor_reason": None if anchor else "the asymptotic one-factor contribution is a Gaussian one-factor result; "
                                                 "no closed form is specified for this rung"}


def build_loan_type() -> tuple[dict, dict]:
    el = r(sum(g["n_names"] * g["ead_each"] * g["lgd"] * g["pd"] for g in GROUPS), 2)
    q99, q999 = lhp_quantile(0.99, PD_HAT, RHO_HAT), lhp_quantile(0.999, PD_HAT, RHO_HAT)
    annual = []
    for year, x in RATES.items():
        window = "fit" if year <= 2006 else "evaluation"
        if x is None:
            annual.append({"year": year, "window": window, "n_quarters": 3, "loss_rate": None,
                           "reason": "fixture: the quarter 1990Q3 is absent from the table; the annual rate is null, never interpolated",
                           "fitted_cdf": None, "implied_factor": None, "exceeds_99": None, "exceeds_999": None})
        else:
            annual.append({"year": year, "window": window, "n_quarters": 4, "loss_rate": x, "reason": None,
                           "fitted_cdf": r(lhp_cdf(x, PD_HAT, RHO_HAT)), "implied_factor": r(implied_factor(x, PD_HAT, RHO_HAT)),
                           "exceeds_99": x > q99, "exceeds_999": x > q999})
    ev = [(y, x) for y, x in RATES.items() if y >= 2007 and x is not None]
    bt_rows = []
    for lv in (0.95, 0.99, 0.999):
        q = lhp_quantile(lv, PD_HAT, RHO_HAT)
        above = [y for y, x in ev if x > q]
        p = binom_upper(len(above), len(ev), 1 - lv)
        bt_rows.append({"level": lv, "fitted_quantile": r(q), "expected_exceedances": r(len(ev) * (1 - lv)),
                        "observed_exceedances": len(above), "years_exceeding": above, "p_value_upper": r(p),
                        "light": "green" if p >= 0.05 else "amber" if p >= 0.01 else "red"})
    z = ND.inv_cdf(0.975)
    grid = [r(0.02 * k, 2) for k in range(1, 16)]
    max_ll, h = 95.4, 0.04
    ll = [r(max_ll - (z * z / 2) * ((x - RHO_HAT) / h) ** 2, 9) for x in grid]
    ml = {"pd": {"estimate": PD_HAT, "ci_low": 0.0025, "ci_high": 0.0036},
          "rho": {"estimate": RHO_HAT, "ci_low": 0.02, "ci_high": 0.10},
          "log_likelihood": max_ll, "converged": True, "interval_method": "profile-likelihood", "level": 0.95}
    moments = {"pd": {"estimate": 0.0030, "ci_low": 0.0026, "ci_high": 0.0035},
               "rho": {"estimate": 0.055, "ci_low": 0.02, "ci_high": 0.11},
               "interval_method": "parametric-bootstrap", "n_bootstrap": 200, "level": 0.95}
    k_irb = LGD * (lhp_quantile(0.999, PD_HAT, 0.15) - PD_HAT)
    ec_fit = LGD * (q999 - PD_HAT)
    k_star = r(k_irb, 12)  # the fixture's K*: the IRB K per unit of EAD at the regulatory correlation (one class, one PD)
    ga999 = r(0.08 * HHI, 12)  # GA of eq. 17 as a share of EAD (Gordy and Lutkebohmert 2013, eq. 9); a made-up scale 0.08 / n
    ga_levels = []
    for q_, ga_ in ((0.99, r(0.4 * ga999, 12)), (0.999, ga999)):
        a_ = r(gamma_quantile(0.25, q_), 9)
        ga_levels.append({"q": q_, "alpha_q": a_, "delta": r((a_ - 1) * (0.25 + 0.75 / a_), 9), "ga": ga_,
                          "ga_money": r(ga_ * TOTAL_EAD, 2)})
    ga_money = {x["q"]: x["ga_money"] for x in ga_levels}

    def mc(n: int) -> dict:
        return {"n_scenarios": n, "seed": 4001, "chunk_size": 100000}

    rungs = [
        rung("c1-lhp", "C1", "lhp-vasicek", ("Large homogeneous portfolio (Vasicek)", "Cartera homogenea grande (Vasicek)"), "analytic",
             [named("pd", PD_HAT, "decimal"), named("rho", RHO_HAT, "-"), named("lgd", LGD, "decimal")],
             measures(1.0, 1.0, el, None), 1.0),
        rung("c2-gaussian-1f", "C2", "gaussian-copula-one-factor", ("Gaussian copula, one factor", "Copula gaussiana, un factor"),
             "monte-carlo", [named("rho", RHO_HAT, "-"), named("lgd", LGD, "decimal")],
             measures(0.97, 0.97, el, (0.004, 0.005)), 0.97, mc(1000000)),
        rung("c2-gaussian-mf", "C2", "gaussian-copula-multi-factor", ("Gaussian copula, sector factors", "Copula gaussiana, factores sectoriales"),
             "monte-carlo", [named("n_factors", 2, "-"), named("lgd", LGD, "decimal")],
             measures(1.02, 1.02, el, (0.004, 0.005)), 1.02, mc(1000000)),
        rung("c3-student-t", "C3", "student-t-copula", ("Student-t copula", "Copula t de Student"), "monte-carlo",
             [named("nu", 5, "-"), named("rho", RHO_HAT, "-")], measures(1.35, 1.55, el, (0.006, 0.008)), 1.35, mc(1000000)),
        rung("c4-creditrisk-plus", "C4", "creditrisk-plus", ("CreditRisk+ (stable recursion)", "CreditRisk+ (recursion estable)"),
             "analytic", [named("sigma2", 0.5, "-"), named("loss_unit", 10000.0, CUR)], measures(1.05, 1.08, el, None), 1.05),
        rung("c5-granularity", "C5", "granularity-adjustment", ("Granularity adjustment", "Ajuste por granularidad"), "analytic",
             [named("xi", 0.25, "-"), named("gamma", 0.25, "-"), named("q", 0.999, "decimal")],
             measures(1.0, 1.0, el, None, ga_money), 1.0),
        rung("c6-is-gaussian", "C6", "importance-sampling", ("Importance sampling, Gaussian copula", "Muestreo por importancia, copula gaussiana"),
             "monte-carlo", [named("theta", 0.35, "-"), named("factor_shift", -1.2, "-")],
             measures(0.97, 0.97, el, (0.0005, 0.0006)), 0.97, mc(100000),
             [named("variance_ratio_vs_plain_mc", 38.4, "ratio"), named("effective_sample_share", 0.12, "share")]),
        rung("c6-is-student-t", "C6", "importance-sampling", ("Importance sampling, Student-t copula", "Muestreo por importancia, copula t"),
             "none", [], None, None,
             reason="the exponential twist of dossier 04 H.7 is derived for the normal copula; no Student-t twist is specified, "
                    "so the rung did not run and no number stands in for it"),
    ]
    ms = {x["id"]: x["measures"] for x in rungs if x["evaluated"]}

    def levels(method_id: str, anchor: bool, v_shares: list, e_shares: list) -> list:
        out = []
        for i, q in enumerate((0.99, 0.999)):
            m = ms[method_id][i]
            out.append(euler_level(q, m["var"], m["es"], v_shares[i], e_shares[i], 0.004, anchor))
        return out

    euler = [
        {"rung_method": "gaussian-copula-one-factor", "currency": CUR,
         "levels": levels("c2-gaussian-1f", True, [[0.16, 0.28, 0.56], [0.15, 0.27, 0.58]], [[0.17, 0.28, 0.55], [0.16, 0.27, 0.57]])},
        {"rung_method": "student-t-copula", "currency": CUR,
         "levels": levels("c3-student-t", False, [[0.18, 0.28, 0.54], [0.19, 0.27, 0.54]], [[0.19, 0.28, 0.53], [0.20, 0.27, 0.53]])},
    ]
    k99 = next(x for x in bt_rows if x["level"] == 0.99)
    out = {
        "kind": "loan-type", "loan_type": "residential",
        "label": txt("Residential real estate", "Credito hipotecario residencial"), "currency": CUR,
        "loss_rate_definition": txt("Net charge-off rate, annualised, decimal per year; the annual rate is the mean of the four "
                                    "quarterly rates. Fixture values, not the Federal Reserve's.",
                                    "Tasa de castigo neta anualizada, decimal por ano; la tasa anual es el promedio de las cuatro "
                                    "tasas trimestrales. Valores de ejemplo, no los de la Reserva Federal."),
        "windows": {"fit": {"first_year": 1985, "last_year": 2006, "n_years": 22},
                    "evaluation": {"first_year": 2007, "last_year": 2012, "n_years": 6}},
        "data_status": {"source": "federal-reserve-chargeoff-release", "table": "chgallsa",
                        "series": "fixture: the column of the loan type is set by the bake", "seasonal_adjustment": "SA",
                        "bank_scope": "all-banks", "files_as_of": "2026-08-25", "quarters_expected": 112,
                        "missing_quarters": [{"quarter": "1990Q3", "reason": "fixture: the quarter is absent from the table"}],
                        "notice": FIXTURE_NOTICE},
        "annual_rates": annual,
        "fit": {"n_years_used": sum(1 for y, x in RATES.items() if y <= 2006 and x is not None), "maximum_likelihood": ml,
                "moments": moments},
        "profile_likelihood": {"level": 0.95, "rho": grid, "log_likelihood": ll,
                               "pd_at_rho": [r(PD_HAT + 0.00002 * (x - RHO_HAT) / 0.02, 9) for x in grid],
                               "max_log_likelihood": max_ll, "cutoff": r(max_ll - z * z / 2, 9)},
        "fitted_distribution": {
            "pd": PD_HAT, "rho": RHO_HAT,
            "curve": {"x": CURVE_X, "pdf": [r(lhp_pdf(x, PD_HAT, RHO_HAT), 9) for x in CURVE_X],
                      "cdf": [r(lhp_cdf(x, PD_HAT, RHO_HAT)) for x in CURVE_X]},
            "quantiles": [{"level": lv, "value": r(lhp_quantile(lv, PD_HAT, RHO_HAT))} for lv in QUANTILE_LEVELS]},
        "backtest": {"n_years_evaluated": len(ev), "rows": bt_rows},
        "irb_reference": {"regime": "basel3", "asset_class": "residential_mortgage", "reference": "CRE31.14", "pd": PD_HAT,
                          "lgd": LGD, "maturity": None, "maturity_adjustment": None, "irb_correlation": 0.15, "fitted_correlation": RHO_HAT, "k_irb": r(k_irb),
                          "ec_lhp_fitted": r(ec_fit), "ratio_fitted_to_irb": r(ec_fit / k_irb)},
        "portfolio": {"label": "illustrative", "notice": NOTICE_ILLUSTRATIVE, "currency": CUR,
                      "n_names": sum(g["n_names"] for g in GROUPS), "total_ead": TOTAL_EAD, "groups": GROUPS, "lgd_mean": LGD,
                      "lgd_gamma": 0.25, "levels": [0.99, 0.999], "horizon_years": 1,
                      "calibration": {"pd": PD_HAT, "rho": RHO_HAT, "source": "fit-maximum-likelihood"},
                      "hhi": r(HHI), "effective_names": r(1 / HHI),
                      "largest_share": r(max(g["ead_each"] for g in GROUPS) / TOTAL_EAD)},
        "rungs": rungs,
        "granularity": {"currency": CUR, "xi": 0.25, "gamma": 0.25, "k_source": "irb-regulatory-correlation", "k_star": k_star,
                        "delta_reference": 4.83,
                        "delta_reference_source": "Gordy and Lutkebohmert (2013), eq. 15 and p. 46 (dossier 04 H.5)",
                        "levels": ga_levels, "by_n_names_level": 0.999,
                        "by_n_names": [{"n_names": n, "hhi": r(1 / n), "ga": r(0.08 / n, 12),
                                        "truth_ga": r(0.93 * 0.08 / n, 12) if n <= 200 else None,
                                        "truth_reason": None if n <= 200 else
                                        "fixture: the CreditRisk+ recursion was not run beyond 200 names"}
                                       for n in (10, 20, 50, 100, 200, 500, 1000)]},
        "euler": euler,
    }
    n_ev = len(ev)
    euler_dev = max(abs(sum(x["rc_var"] for x in lv["rows"]) - lv["var_total"]) / lv["var_total"]
                    for e in euler for lv in e["levels"])
    variant = {
        "schema": "contraste.case/v1", "case_id": "C10", "variant_id": "fixture-residential",
        "model": [model_summary(m, rg) for m, rg in MODEL_IDS], "outputs": out,
        "tests": [
            eval_row("portfolio.tail_backtest", "m-lhp", "the evaluation years fall above the fitted quantile at the expected rate",
                     float(k99["observed_exceedances"]), k99["p_value_upper"], float(k99["expected_exceedances"]),
                     k99["light"], n_ev, k99["observed_exceedances"], {"primary_level": 0.99, "thresholds": {}}),
            test_row("portfolio.mc_convergence", "m-gaussian-1f", NE),
            eval_row("portfolio.euler_additivity", "m-gaussian-1f", "the Euler contributions add up to the total", None, None,
                     r(euler_dev, 6), "green", len(GROUPS), None, {"thresholds": {"tolerance": 0.01}}),
            test_row("portfolio.crp_recursion_vs_mc", "m-lhp", NE),
        ],
        "impact": {
            "ec_lhp_999_share": {"value": r(ec_fit), "unit": "share of EAD",
                                 "label": txt("LHP capital at 99.9% with the fitted correlation", "Capital LHP al 99,9% con la correlacion ajustada")},
            "ec_ratio_fitted_to_irb": {"value": r(ec_fit / k_irb), "unit": "ratio",
                                       "label": txt("Fitted capital over IRB capital", "Capital ajustado sobre capital IRB")}},
        "findings": [{"id": "f-c10-tail", "severity": "S2", "status": "open", "evidence": ["portfolio.tail_backtest"],
                      "title": txt("Fixture finding: two evaluation years above the fitted 99% quantile",
                                   "Hallazgo de ejemplo: dos anos de evaluacion sobre el cuantil 99% ajustado")}],
        **envelope_common("real-outcomes", True),
    }
    return variant, models_doc()


# --- the correlation-grid fixture ---------------------------------------------------------------------------------

GRID = [0.04, 0.08, 0.12, 0.16]
NULL_RHO = 0.12
REPS, LENGTH = 1000, 22
CELLS = {  # known_rho: (n_failed, ML (mean, rmse, coverage, rejection), moments (mean, rmse, coverage, rejection))
    0.04: (4, (0.043, 0.030, 0.94, 0.62), (0.047, 0.036, 0.91, 0.48)),
    0.08: (6, (0.083, 0.034, 0.93, 0.17), (0.088, 0.041, 0.90, 0.14)),
    0.12: (9, (0.124, 0.040, 0.94, 0.054), (0.131, 0.049, 0.90, 0.061)),
    0.16: (11, (0.163, 0.047, 0.93, 0.21), (0.171, 0.056, 0.89, 0.17)),
}


def build_grid() -> dict:
    cells = []
    for rho in GRID:
        failed, ml, mo = CELLS[rho]
        valid = REPS - failed
        ests = []
        for name, (mean, rmse, cov, rej) in (("maximum-likelihood", ml), ("moments", mo)):
            lo, hi = wilson(rej, valid)
            ests.append({"estimator": name, "mean_estimate": mean, "bias": r(mean - rho), "rmse": rmse, "coverage": cov,
                         "rejection_rate": rej, "rejection_se": r(math.sqrt(rej * (1 - rej) / valid)),
                         "rejection_ci_low": r(lo), "rejection_ci_high": r(hi)})
        cells.append({"known_rho": rho, "series_length_years": LENGTH, "n_replications": REPS, "n_valid": valid,
                      "n_failed": failed, "role": "size" if rho == NULL_RHO else "power", "estimators": ests})
    size = next(c for c in cells if c["role"] == "size")["estimators"][0]
    n = next(c for c in cells if c["role"] == "size")["n_valid"]
    zstat = (size["rejection_rate"] - 0.05) / math.sqrt(0.05 * 0.95 / n)
    p = 2 * (1 - ND.cdf(abs(zstat)))
    out = {
        "kind": "correlation-grid", "label": txt("Correlation grid, 22 years", "Grilla de correlaciones, 22 anos"),
        "generator": {"name": "vasicek-lhp-simulator",
                      "shaped_on": "yearly default fractions of a large homogeneous portfolio with one systematic factor (dossier 04 C.4)",
                      "known_pd": 0.02, "rho_grid": GRID, "series_length_years": LENGTH, "n_replications": REPS,
                      "null_rho": NULL_RHO, "alpha": 0.05, "seed": 7001, "notice": FIXTURE_NOTICE},
        "size_power_definition": txt("Size is the rate at which H0: rho = null_rho is rejected when the known correlation equals "
                                     "null_rho; power is the same rate at any other known correlation.",
                                     "El tamano es la tasa de rechazo de H0: rho = null_rho cuando la correlacion conocida es "
                                     "null_rho; la potencia es la misma tasa con otra correlacion conocida."),
        "cells": cells,
    }
    return {
        "schema": "contraste.case/v1", "case_id": "C10", "variant_id": "fixture-grid-22",
        "model": [model_summary("m-lhp", "C1")], "outputs": out,
        "tests": [eval_row("portfolio.correlation_size_power", "m-lhp",
                           "the rejection rate at the null correlation equals the nominal level", r(zstat, 6), r(p, 6),
                           size["rejection_rate"], "green", n, round(size["rejection_rate"] * n),
                           {"role": "size", "known_rho": NULL_RHO, "estimator": "maximum-likelihood",
                            "thresholds": {"power_green": 0.8, "power_amber": 0.5}})],
        "impact": {"size_ml": {"value": size["rejection_rate"], "unit": "rate",
                               "label": txt("Size of the maximum-likelihood test", "Tamano del test de maxima verosimilitud")}},
        "findings": [], **envelope_common("synthetic-known-truth", False),
    }


# --- the models fixture -------------------------------------------------------------------------------------------


def models_doc() -> dict:
    ladder = []
    spec = [
        ("c1-lhp", "C1", "lhp-vasicek", ("Large homogeneous portfolio (Vasicek)", "Cartera homogenea grande (Vasicek)"), "analytic", None,
         "riskvalidation.portfolio.portfolio.lhp_measures", "Vasicek (2002), Risk, December 2002; dossier 04 C.4",
         [named("pd", PD_HAT, "decimal"), named("rho", RHO_HAT, "-")]),
        ("c2-gaussian-1f", "C2", "gaussian-copula-one-factor", ("Gaussian copula, one factor", "Copula gaussiana, un factor"),
         "monte-carlo", 1000000, "riskvalidation.portfolio.copula.simulate_gaussian", "Li (2000); dossier 04 H.3",
         [named("rho", RHO_HAT, "-")]),
        ("c2-gaussian-mf", "C2", "gaussian-copula-multi-factor", ("Gaussian copula, sector factors", "Copula gaussiana, factores sectoriales"),
         "monte-carlo", 1000000, "riskvalidation.portfolio.copula.simulate_gaussian", "Li (2000); dossier 04 H.3",
         [named("n_factors", 2, "-")]),
        ("c3-student-t", "C3", "student-t-copula", ("Student-t copula", "Copula t de Student"), "monte-carlo", 1000000,
         "riskvalidation.portfolio.copula.simulate_student_t", "Frey and McNeil (2003); Demarta and McNeil (2005); dossier 04 H.3",
         [named("nu", 5, "-")]),
        ("c4-creditrisk-plus", "C4", "creditrisk-plus", ("CreditRisk+ (stable recursion)", "CreditRisk+ (recursion estable)"), "analytic",
         None, "riskvalidation.portfolio.creditrisk_plus.pmf_stable", "Haaf, Reiss and Schoenmakers (2004); dossier 04 H.4",
         [named("sigma2", 0.5, "-")]),
        ("c5-granularity", "C5", "granularity-adjustment", ("Granularity adjustment", "Ajuste por granularidad"), "analytic", None,
         "riskvalidation.portfolio.granularity.granularity_adjustment", "Gordy and Lutkebohmert (2013); dossier 04 H.5",
         [named("xi", 0.25, "-"), named("gamma", 0.25, "-")]),
        ("c6-is-gaussian", "C6", "importance-sampling", ("Importance sampling, Gaussian copula", "Muestreo por importancia, copula gaussiana"),
         "monte-carlo", 100000, "riskvalidation.portfolio.importance.importance_sample_gaussian",
         "Glasserman and Li (2005); dossier 04 H.7 (the twist is UNVERIFIED there)", []),
        ("c6-is-student-t", "C6", "importance-sampling", ("Importance sampling, Student-t copula", "Muestreo por importancia, copula t"),
         "monte-carlo", 100000, "riskvalidation.portfolio.importance.importance_sample_gaussian",
         "Glasserman and Li (2005); no Student-t twist is specified, the rung is a not-evaluated row", []),
    ]
    for rid, rg, method, label, est, n, fn, ref, params in spec:
        ladder.append({"id": rid, "rung": rg, "method": method, "label": txt(*label), "estimator": est, "n_scenarios": n,
                       "engine_function": fn, "reference": ref, "parameters": params})
    loan_types = [
        ("commercial-industrial", ("Commercial and industrial", "Comerciales e industriales"), "corporate", "CRE31.5"),
        ("commercial-real-estate", ("Commercial real estate", "Inmobiliario comercial"), "hvcre", "CRE31.11"),
        ("residential", ("Residential real estate", "Credito hipotecario residencial"), "residential_mortgage", "CRE31.14"),
        ("credit-cards", ("Credit cards", "Tarjetas de credito"), "qrre", "CRE31.15"),
        ("other-consumer", ("Other consumer", "Otro consumo"), "other_retail", "CRE31.16"),
    ]
    fit = {
        "currency": CUR,
        "windows": {"fit": {"first_year": 1985, "last_year": 2006, "n_years": 22},
                    "evaluation": {"first_year": 2007, "last_year": 2012, "n_years": 6}},
        "loan_types": [{"id": i, "label": txt(*lb), "table_column": "fixture: the column name is set by the bake from the Board's table",
                        "irb_asset_class": ac, "irb_reference": ref} for i, lb, ac, ref in loan_types],
        "estimators": [
            {"id": "maximum-likelihood", "label": txt("Maximum likelihood", "Maxima verosimilitud"),
             "engine_function": "riskvalidation.portfolio.asrf_fit.fit_ml", "interval_method": "profile-likelihood",
             "reference": "Vasicek (2002); dossier 04 C.4"},
            {"id": "moments", "label": txt("Method of moments", "Metodo de momentos"),
             "engine_function": "riskvalidation.portfolio.asrf_fit.fit_moments", "interval_method": "parametric-bootstrap",
             "reference": "dossier 04 C.4 (E[L^2] = joint default probability)"}],
        "ladder": ladder,
        "portfolio_spec": {"label": "illustrative", "notice": NOTICE_ILLUSTRATIVE, "currency": CUR, "groups": GROUPS, "lgd_mean": LGD,
                           "lgd_gamma": 0.25, "levels": [0.99, 0.999], "horizon_years": 1},
        "granularity": {"xi": 0.25, "gamma": 0.25, "k_source": "irb-regulatory-correlation", "xi_reference": 0.25, "q_reference": 0.999, "delta_reference": 4.83,
                        "reference": "Gordy and Lutkebohmert (2013), eq. 15 and eq. 16 (dossier 04 H.5)"},
        "simulator": {"known_pd": 0.02, "rho_grid": [r(0.02 * k, 2) for k in range(1, 13)], "series_lengths_years": [22, 40],
                      "n_replications": 1000, "null_rho": 0.12, "alpha": 0.05, "seed": 7001},
    }
    return {"schema": "contraste.models/v1", "case_id": "C10", "fit_id": "fixture-c10",
            "model": [model_record(m, rg) for m, rg in MODEL_IDS], "fit": fit, **envelope_common("real-outcomes", True)}


def dump(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")


def main() -> None:
    variant, models = build_loan_type()
    dump(FIX / "variant-loan-type-fixture.json", variant)
    dump(FIX / "variant-correlation-grid-fixture.json", build_grid())
    dump(FIX / "models-fixture.json", models)


if __name__ == "__main__":
    main()
