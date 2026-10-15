"""The cross-field checks of the C10 documents: what JSON Schema cannot compare, as one importable module.

``violations(doc)`` takes a C10 variant document (``outputs.kind`` loan-type or correlation-grid) or a C10 models document and
returns one message per broken identity (an empty list is a sound document). The tests of U7-S run it on the fixtures and on planted
counter-examples; the C10 bake (U7-P) runs it on every document it writes under ``data/derived/C10/`` (``tests/c10/`` imports this
module and fails on a non-empty list), so the orderings (VaR not below EL, ES not below VaR, EC = VaR - EL), the Euler sums and the
asymptotic anchor, the grid identities, the window labels, the currencies, the IRB identity with its maturity treatment and the
granularity identities hold for a baked document, not only for the committed fixtures (engine-portfolio-api, Conventions).

Standard library only. The formulas are those of dossier 04 sections C.4, H.1, H.5 and H.6 and of the engine contract
(docs/contracts/engine/portfolio-api.md).
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from statistics import NormalDist

ND = NormalDist()
RETAIL = ("residential_mortgage", "qrre", "other_retail", "retail_consumer")
RUNG_IDS = ["c1-lhp", "c2-gaussian-1f", "c2-gaussian-mf", "c3-student-t", "c4-creditrisk-plus", "c5-granularity", "c6-is-gaussian",
            "c6-is-student-t"]
SAMPLE_METHODS = {"gaussian-copula-one-factor", "gaussian-copula-multi-factor", "student-t-copula", "creditrisk-plus"}
CHI2_1_95 = ND.inv_cdf(0.975) ** 2


# --- the formulas (dossier 04 C.4, H.1) ----------------------------------------------------------------------------


def lhp_cdf(x: float, pd: float, rho: float) -> float:
    return ND.cdf((math.sqrt(1 - rho) * ND.inv_cdf(x) - ND.inv_cdf(pd)) / math.sqrt(rho))


def lhp_quantile(q: float, pd: float, rho: float) -> float:
    return ND.cdf((ND.inv_cdf(pd) + math.sqrt(rho) * ND.inv_cdf(q)) / math.sqrt(1 - rho))


def implied_factor(x: float, pd: float, rho: float) -> float:
    return (ND.inv_cdf(pd) - math.sqrt(1 - rho) * ND.inv_cdf(x)) / math.sqrt(rho)


def lhp_pdf(x: float, pd: float, rho: float) -> float:
    g = ND.inv_cdf(x)
    return math.sqrt((1 - rho) / rho) * math.exp(0.5 * g * g - (math.sqrt(1 - rho) * g - ND.inv_cdf(pd)) ** 2 / (2 * rho))


def conditional_pd(pd: float, rho: float, z: float) -> float:
    return ND.cdf((ND.inv_cdf(pd) - math.sqrt(rho) * z) / math.sqrt(1 - rho))


def lhp_es(pd: float, rho: float, q: float, steps: int = 4000) -> float:
    """E[p(Z) | Z <= G(1 - q)]: the expected shortfall of the LHP loss fraction (Simpson quadrature)."""
    z0, lo = ND.inv_cdf(1 - q), ND.inv_cdf(1 - q) - 12.0
    h = (z0 - lo) / steps
    def f(z):
        return conditional_pd(pd, rho, z) * ND.pdf(z)
    s = f(lo) + f(z0) + sum((4 if k % 2 else 2) * f(lo + k * h) for k in range(1, steps))
    return s * h / 3 / (1 - q)


def binom_upper(k: int, n: int, p: float) -> float:
    return sum(math.comb(n, j) * p**j * (1 - p) ** (n - j) for j in range(k, n + 1))


def gamma_lower(a: float, x: float) -> float:
    """The regularised lower incomplete gamma P(a, x) by its series."""
    term = total = 1.0 / a
    n = 0
    while abs(term) > 1e-16 * abs(total):
        n += 1
        term *= x / (a + n)
        total += term
    return total * math.exp(-x + a * math.log(x) - math.lgamma(a))


def gamma_quantile(xi: float, q: float) -> float:
    """The q-quantile of the Gamma factor with shape xi and rate xi (mean 1, variance 1/xi; Gordy and Lutkebohmert 2013, p. 43)."""
    lo, hi = 0.0, 1.0
    while gamma_lower(xi, xi * hi) < q:
        hi *= 2
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if gamma_lower(xi, xi * mid) < q else (lo, mid)
    return (lo + hi) / 2


def gl_delta(xi: float, q: float) -> float:
    a = gamma_quantile(xi, q)
    return (a - 1) * (xi + (1 - xi) / a)


def wilson(p: float, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


def maturity_adjustment(pd: float, maturity: float) -> float:
    """(1 + (M - 2.5) b) / (1 - 1.5 b), b = (0.11852 - 0.05478 ln PD)^2 (BCBS 2005 explanatory note; dossier 04 C.4)."""
    b = (0.11852 - 0.05478 * math.log(pd)) ** 2
    return (1 + (maturity - 2.5) * b) / (1 - 1.5 * b)


def close(a: float, b: float, rel: float = 1e-6, abs_: float = 1e-9) -> bool:
    return math.isclose(a, b, rel_tol=rel, abs_tol=abs_)


# --- the checks ----------------------------------------------------------------------------------------------------


def window_violations(o: dict) -> list[str]:
    bad = []
    w = o["windows"]
    for k in ("fit", "evaluation"):
        if w[k]["n_years"] != w[k]["last_year"] - w[k]["first_year"] + 1:
            bad.append(f"windows.{k}: n_years != last_year - first_year + 1")
    if w["fit"]["last_year"] >= w["evaluation"]["first_year"]:
        bad.append("windows: the fit window does not end before the evaluation window begins")
    years = [r["year"] for r in o["annual_rates"]]
    if years != list(range(w["fit"]["first_year"], w["evaluation"]["last_year"] + 1)):
        bad.append("annual_rates: the years are not every year of both windows once, ascending")
    for r in o["annual_rates"]:
        want = "fit" if r["year"] <= w["fit"]["last_year"] else "evaluation"
        if r["window"] != want:
            bad.append(f"annual_rates {r['year']}: window is {r['window']}, expected {want}")
    used = sum(1 for r in o["annual_rates"] if r["window"] == "fit" and r["loss_rate"] is not None)
    if o["fit"]["n_years_used"] != used:
        bad.append("fit.n_years_used != the fit-window years with a rate")
    if [m["quarter"][:4] for m in o["data_status"]["missing_quarters"]] != [str(r["year"]) for r in o["annual_rates"] if r["n_quarters"] < 4]:
        bad.append("data_status.missing_quarters do not match the years with fewer than four quarters")
    if o["data_status"]["quarters_expected"] != 4 * len(years):
        bad.append("data_status.quarters_expected != 4 * years")
    return bad


def fit_violations(o: dict) -> list[str]:
    bad = []
    ml = o["fit"]["maximum_likelihood"]
    pd, rho = ml["pd"]["estimate"], ml["rho"]["estimate"]
    for est in ("maximum_likelihood", "moments"):
        for par in ("pd", "rho"):
            e = o["fit"][est][par]
            if not e["ci_low"] <= e["estimate"] <= e["ci_high"]:
                bad.append(f"fit.{est}.{par}: the interval does not contain the estimate")
    fd = o["fitted_distribution"]
    if fd["pd"] != pd or fd["rho"] != rho:
        bad.append("fitted_distribution: pd and rho are not the maximum-likelihood estimates")
    c = fd["curve"]
    if not (len(c["x"]) == len(c["pdf"]) == len(c["cdf"])) or c["x"] != sorted(set(c["x"])) or any(b < a for a, b in zip(c["cdf"], c["cdf"][1:])):
        bad.append("fitted_distribution.curve: lengths, order or monotonicity")
    else:
        for x, p, f in zip(c["x"], c["pdf"], c["cdf"]):
            if not (close(p, lhp_pdf(x, pd, rho), 1e-5) and close(f, lhp_cdf(x, pd, rho), 0, 1e-6)):
                bad.append(f"fitted_distribution.curve at {x}: not the Vasicek density and distribution function")
    for qv in fd["quantiles"]:
        if not close(qv["value"], lhp_quantile(qv["level"], pd, rho), 0, 1e-6):
            bad.append(f"fitted_distribution.quantiles {qv['level']}: not the Vasicek quantile")
    q99, q999 = lhp_quantile(0.99, pd, rho), lhp_quantile(0.999, pd, rho)
    for r in o["annual_rates"]:
        if r["loss_rate"] is None:
            continue
        x = r["loss_rate"]
        if not (close(r["fitted_cdf"], lhp_cdf(x, pd, rho), 0, 1e-6) and close(r["implied_factor"], implied_factor(x, pd, rho), 0, 1e-6)):
            bad.append(f"annual_rates {r['year']}: fitted_cdf or implied_factor is not recomputed from the fit")
        if r["exceeds_99"] != (x > q99) or r["exceeds_999"] != (x > q999):
            bad.append(f"annual_rates {r['year']}: an exceedance flag disagrees with the fitted quantile")
    p = o["profile_likelihood"]
    if not (len(p["rho"]) == len(p["log_likelihood"]) == len(p["pd_at_rho"])) or p["rho"] != sorted(set(p["rho"])):
        bad.append("profile_likelihood: lengths or order")
    else:
        if not close(max(p["log_likelihood"]), p["max_log_likelihood"], 0, 1e-9) or not close(p["max_log_likelihood"], ml["log_likelihood"], 0, 1e-9):
            bad.append("profile_likelihood: the maximum is not the maximum-likelihood log-likelihood")
        if not close(p["cutoff"], p["max_log_likelihood"] - CHI2_1_95 / 2, 0, 1e-6):
            bad.append("profile_likelihood.cutoff != max - chi2_1(0.95) / 2")
        step = max(b - a for a, b in zip(p["rho"], p["rho"][1:]))
        inside = [r for r, ll in zip(p["rho"], p["log_likelihood"]) if ll >= p["cutoff"] - 1e-9]
        if inside and (min(inside) < ml["rho"]["ci_low"] - step - 1e-9 or max(inside) > ml["rho"]["ci_high"] + step + 1e-9):
            bad.append("profile_likelihood: the points above the cutoff are not the stated interval of rho")
    ev = [r for r in o["annual_rates"] if r["window"] == "evaluation" and r["loss_rate"] is not None]
    bt = o["backtest"]
    if bt["n_years_evaluated"] != len(ev):
        bad.append("backtest.n_years_evaluated != the evaluation years with a rate")
    if [row["level"] for row in bt["rows"]] != [0.95, 0.99, 0.999]:
        bad.append("backtest: levels are not [0.95, 0.99, 0.999]")
    for row in bt["rows"]:
        q = lhp_quantile(row["level"], pd, rho)
        above = [r["year"] for r in ev if r["loss_rate"] > q]
        if not close(row["fitted_quantile"], q, 0, 1e-6) or row["years_exceeding"] != above or row["observed_exceedances"] != len(above):
            bad.append(f"backtest {row['level']}: quantile or exceedance count not recomputed")
        if not close(row["expected_exceedances"], len(ev) * (1 - row["level"]), 0, 1e-9):
            bad.append(f"backtest {row['level']}: expected exceedances != n (1 - level)")
        if not close(row["p_value_upper"], binom_upper(len(above), len(ev), 1 - row["level"]), 0, 1e-6):
            bad.append(f"backtest {row['level']}: p_value_upper is not the binomial tail")
    return bad


def irb_violations(o: dict) -> list[str]:
    i = o["irb_reference"]
    bad = []
    retail = i["asset_class"] in RETAIL
    if retail != (i["maturity"] is None) or retail != (i["maturity_adjustment"] is None):
        bad.append("irb_reference: maturity and maturity_adjustment are null exactly for a retail class")
        return bad
    ma = 1.0
    if not retail:
        ma = maturity_adjustment(i["pd"], i["maturity"])
        if not close(i["maturity_adjustment"], ma, 1e-6):
            bad.append("irb_reference.maturity_adjustment is not recomputed from pd and maturity")
    if not close(i["k_irb"], i["lgd"] * (lhp_quantile(0.999, i["pd"], i["irb_correlation"]) - i["pd"]) * ma, 1e-6, 1e-9):
        bad.append("irb_reference.k_irb != lgd (LHP quantile at the IRB correlation - pd) x maturity adjustment")
    if not close(i["ec_lhp_fitted"], i["lgd"] * (lhp_quantile(0.999, i["pd"], i["fitted_correlation"]) - i["pd"]) * ma, 1e-6, 1e-9):
        bad.append("irb_reference.ec_lhp_fitted does not use the same maturity treatment as k_irb")
    if not close(i["ratio_fitted_to_irb"], i["ec_lhp_fitted"] / i["k_irb"], 1e-6, 1e-9):
        bad.append("irb_reference.ratio_fitted_to_irb != ec_lhp_fitted / k_irb")
    if i["fitted_correlation"] != o["fit"]["maximum_likelihood"]["rho"]["estimate"]:
        bad.append("irb_reference.fitted_correlation is not the maximum-likelihood correlation")
    return bad


def portfolio_violations(o: dict) -> list[str]:
    p, bad = o["portfolio"], []
    total = sum(g["n_names"] * g["ead_each"] for g in p["groups"])
    if not close(p["total_ead"], total, 1e-9):
        bad.append("portfolio.total_ead != sum of n_names x ead_each")
    if p["n_names"] != sum(g["n_names"] for g in p["groups"]):
        bad.append("portfolio.n_names != sum of the groups' n_names")
    hhi = sum(g["n_names"] * (g["ead_each"] / total) ** 2 for g in p["groups"])
    if not close(p["hhi"], hhi, 1e-6) or not close(p["effective_names"], 1 / hhi, 1e-6):
        bad.append("portfolio.hhi or effective_names not recomputed")
    if not close(p["largest_share"], max(g["ead_each"] for g in p["groups"]) / total, 1e-6):
        bad.append("portfolio.largest_share not recomputed")
    if len({g["id"] for g in p["groups"]}) != len(p["groups"]):
        bad.append("portfolio.groups: duplicate ids")
    ml = o["fit"]["maximum_likelihood"]
    if p["calibration"]["pd"] != ml["pd"]["estimate"] or p["calibration"]["rho"] != ml["rho"]["estimate"]:
        bad.append("portfolio.calibration is not the maximum-likelihood fit")
    for place, cur in [("portfolio", p["currency"]), ("granularity", o["granularity"]["currency"])] + \
            [(f"rung {r['id']}", r["currency"]) for r in o["rungs"]] + \
            [(f"rung {r['id']} curve", r["distribution"]["currency"]) for r in o["rungs"] if r["distribution"] is not None] + \
            [(f"euler {e['rung_method']}", e["currency"]) for e in o["euler"]]:
        if cur != o["currency"]:
            bad.append(f"{place}: currency {cur} differs from the document's {o['currency']}")
    return bad


def measure_violations(o: dict, tol: float = 1e-6) -> list[str]:
    """VaR not below EL, ES not below VaR, EC = VaR - EL, nondecreasing in the level; the ladder and its estimators."""
    bad = []
    if [r["id"] for r in o["rungs"]] != RUNG_IDS:
        bad.append("rungs: not the eight rung ids in order")
    for r in o["rungs"]:
        if not r["id"].startswith(r["rung"].lower() + "-"):
            bad.append(f"{r['id']}: id does not match rung {r['rung']}")
        if r["evaluated"]:
            if r["estimator"] == "monte-carlo" and (r["simulation"] is None or r["simulation"]["n_scenarios"] < 1):
                bad.append(f"{r['id']}: a Monte Carlo rung without its simulation")
            c = r["distribution"]
            n = len(c["loss"])
            if not (n == len(c["cdf"]) == len(c["density"]) >= 8) or c["loss"] != sorted(set(c["loss"])) or any(b < a for a, b in zip(c["cdf"], c["cdf"][1:])):
                bad.append(f"{r['id']}: the loss curve lengths, order or monotonicity")
            elif c["loss"][-1] < max(m["var"] for m in r["measures"]):
                bad.append(f"{r['id']}: the grid stops below the 99.9% VaR")
        else:
            if r["measures"] is not None or r["distribution"] is not None or r["diagnostics"]:
                bad.append(f"{r['id']}: a rung that did not run carries a number")
            continue
        for m in r["measures"]:
            where = f"{r['id']}@{m['level']}"
            if m["var"] < m["el"] - tol:
                bad.append(f"{where}: VaR below EL")
            if m["es"] is not None and m["es"] < m["var"] - tol:
                bad.append(f"{where}: ES below VaR")
            if abs(m["ec"] - (m["var"] - m["el"])) > tol * max(1.0, m["var"]):
                bad.append(f"{where}: EC != VaR - EL")
        ms = r["measures"]
        for a, b in zip(ms, ms[1:]):
            if b["level"] > a["level"] and (b["var"] < a["var"] - tol or (a["es"] is not None and b["es"] is not None and b["es"] < a["es"] - tol)):
                bad.append(f"{r['id']}: a measure falls as the level rises")
        if len({m["level"] for m in ms}) != len(ms):
            bad.append(f"{r['id']}: a level appears twice")
    return bad


def lhp_rung_violations(o: dict) -> list[str]:
    """The C1 rung recomputes from the calibration; the C5 rung is C1 plus the granularity adjustment of its level."""
    bad = []
    cal, p = o["portfolio"]["calibration"], o["portfolio"]
    by = {r["id"]: r for r in o["rungs"]}
    c1 = by.get("c1-lhp")
    if c1 is None or not c1["evaluated"]:
        return ["c1-lhp: absent or not evaluated"]
    ead_lgd = p["total_ead"] * p["lgd_mean"]
    for m in c1["measures"]:
        if not (close(m["el"], ead_lgd * cal["pd"], 1e-6) and close(m["var"], ead_lgd * lhp_quantile(m["level"], cal["pd"], cal["rho"]), 1e-6)
                and close(m["es"], ead_lgd * lhp_es(cal["pd"], cal["rho"], m["level"]), 1e-5)):
            bad.append(f"c1-lhp@{m['level']}: not recomputed from the calibration")
    c5 = by.get("c5-granularity")
    if c5 is not None and c5["evaluated"]:
        lv = {x["q"]: x for x in o["granularity"]["levels"]}
        for m in c5["measures"]:
            base = next(x for x in c1["measures"] if x["level"] == m["level"])
            if m["level"] not in lv or not close(m["var"], base["var"] + lv[m["level"]]["ga_money"], 1e-6, 1e-2):
                bad.append(f"c5-granularity@{m['level']}: VaR != C1 VaR + the level's ga_money")
    return bad


def euler_violations(o: dict) -> list[str]:
    bad = []
    groups = {g["id"]: g for g in o["portfolio"]["groups"]}
    by_method = {r["method"]: r for r in o["rungs"] if r["evaluated"]}
    for e in o["euler"]:
        if e["rung_method"] not in by_method or e["rung_method"] not in SAMPLE_METHODS:
            bad.append(f"{e['rung_method']}: not the method of an evaluated sample-based rung")
        for lv in e["levels"]:
            where = f"{e['rung_method']}@{lv['level']}"
            rows = lv["rows"]
            same = [m for m in (by_method[e["rung_method"]]["measures"] if e["rung_method"] in by_method else []) if m["level"] == lv["level"]]
            if not same or not (close(same[0]["var"], lv["var_total"], 1e-9) and close(same[0]["es"], lv["es_total"], 1e-9)):
                bad.append(f"{where}: the totals are not the rung's VaR and ES")
            if {r["group_id"] for r in rows} != set(groups) or len(rows) != len(groups):
                bad.append(f"{where}: the rows do not cover the portfolio groups once")
            for key, total, tol in (("rc_var", lv["var_total"], lv["var_sum_tolerance"]), ("rc_es", lv["es_total"], lv["es_sum_tolerance"])):
                s = sum(r[key] for r in rows)
                if abs(s - total) > tol * total:
                    bad.append(f"{where}: sum of {key} {s} is not {total} within {tol}")
            for share, key, total in (("share_var", "rc_var", lv["var_total"]), ("share_es", "rc_es", lv["es_total"])):
                for r in rows:
                    if not close(r[share], r[key] / total, 0, 1e-6):
                        bad.append(f"{where}: {share} of {r['group_id']} != {key} / total")
            for r in rows:
                if r["group_id"] in groups and not close(r["ead"], groups[r["group_id"]]["n_names"] * groups[r["group_id"]]["ead_each"], 1e-9):
                    bad.append(f"{where}: ead of {r['group_id']} is not the group's exposure")
            if lv["anchor"] is not None:
                a = lv["anchor"]
                rho = next((x["value"] for x in by_method.get(e["rung_method"], {}).get("parameters", []) if x["name"] == "rho"), None)
                if {x["group_id"] for x in a["rows"]} != set(groups):
                    bad.append(f"{where}: the anchor does not cover the groups")
                elif rho is None:
                    bad.append(f"{where}: the anchor needs the rung's rho parameter")
                else:
                    z = ND.inv_cdf(1 - lv["level"])
                    for x in a["rows"]:
                        g = groups[x["group_id"]]
                        want = g["n_names"] * g["ead_each"] * g["lgd"] * conditional_pd(g["pd"], rho, z)
                        if not close(x["rc_var"], want, 1e-6, 0.01):
                            bad.append(f"{where}: anchor row {x['group_id']} is not u_j p_j(G(1 - q))")
                if not close(sum(x["rc_var"] for x in a["rows"]), a["asrf_var"], 1e-9, 0.01):
                    bad.append(f"{where}: anchor.asrf_var is not the sum of its rows")
    return bad


def granularity_violations(o: dict) -> list[str]:
    g, bad = o["granularity"], []
    for lv in g["levels"]:
        a = gamma_quantile(g["xi"], lv["q"])
        if not close(lv["alpha_q"], a, 1e-6) or not close(lv["delta"], (a - 1) * (g["xi"] + (1 - g["xi"]) / a), 1e-6):
            bad.append(f"granularity {lv['q']}: alpha_q or delta not recomputed (Gamma shape xi, rate xi; eq. 15)")
        if not close(lv["ga_money"], lv["ga"] * o["portfolio"]["total_ead"], 1e-6, 0.01):
            bad.append(f"granularity {lv['q']}: ga_money != ga x total_ead (GA is a share of EAD)")
        if g["xi"] == 0.25 and lv["q"] == 0.999 and abs(lv["delta"] - g["delta_reference"]) >= 0.005:
            bad.append("granularity: delta at xi 0.25 and q 0.999 is not the paper's 4.83")
    if [lv["q"] for lv in g["levels"]] != sorted(lv["q"] for lv in g["levels"]):
        bad.append("granularity.levels not ascending")
    rows = g["by_n_names"]
    if [r["n_names"] for r in rows] != sorted(r["n_names"] for r in rows):
        bad.append("granularity.by_n_names not ascending")
    for r in rows:
        if not close(r["hhi"], 1 / r["n_names"], 1e-9):
            bad.append(f"granularity n={r['n_names']}: hhi != 1/n")
        if not close(r["ga"] * r["n_names"], rows[0]["ga"] * rows[0]["n_names"], 1e-6):
            bad.append(f"granularity n={r['n_names']}: ga x n is not constant")
    return bad


def cell_violations(o: dict) -> list[str]:
    """The identities of a correlation-grid document that JSON Schema cannot state."""
    g, bad = o["generator"], []
    grid = g["rho_grid"]
    if grid != sorted(grid) or len(set(grid)) != len(grid):
        bad.append("rho_grid is not strictly increasing")
    if not any(math.isclose(g["null_rho"], x, abs_tol=1e-12) for x in grid):
        bad.append("null_rho is not on the grid")
    if sorted(c["known_rho"] for c in o["cells"]) != sorted(grid):
        bad.append("the cells do not cover the rho grid exactly once")
    for c in o["cells"]:
        cid = c["known_rho"]
        if c["series_length_years"] != g["series_length_years"] or c["n_replications"] != g["n_replications"]:
            bad.append(f"{cid}: length or replications differ from the generator")
        if c["n_valid"] + c["n_failed"] != c["n_replications"]:
            bad.append(f"{cid}: n_valid + n_failed != n_replications")
        want = "size" if math.isclose(cid, g["null_rho"], abs_tol=1e-12) else "power"
        if c["role"] != want:
            bad.append(f"{cid}: role is {c['role']}, expected {want}")
        if [e["estimator"] for e in c["estimators"]] != ["maximum-likelihood", "moments"]:
            bad.append(f"{cid}: estimators are not [maximum-likelihood, moments]")
        for e in c["estimators"]:
            r, n = e["rejection_rate"], c["n_valid"]
            if not math.isclose(e["bias"], e["mean_estimate"] - cid, abs_tol=1e-9):
                bad.append(f"{cid}/{e['estimator']}: bias != mean_estimate - known_rho")
            if not math.isclose(e["rejection_se"], math.sqrt(r * (1 - r) / n), abs_tol=1e-9):
                bad.append(f"{cid}/{e['estimator']}: rejection_se != sqrt(r(1-r)/n_valid)")
            lo, hi = wilson(r, n)
            if not (math.isclose(e["rejection_ci_low"], lo, abs_tol=1e-6) and math.isclose(e["rejection_ci_high"], hi, abs_tol=1e-6)):
                bad.append(f"{cid}/{e['estimator']}: the rejection interval is not the 95% Wilson interval")
            if not e["rejection_ci_low"] <= r <= e["rejection_ci_high"]:
                bad.append(f"{cid}/{e['estimator']}: the interval does not contain the rate")
    return bad


def models_violations(f: dict) -> list[str]:
    bad = []
    s = f["simulator"]
    if s["rho_grid"] != sorted(set(s["rho_grid"])):
        bad.append("simulator.rho_grid is not strictly increasing")
    if not any(math.isclose(s["null_rho"], x, abs_tol=1e-12) for x in s["rho_grid"]):
        bad.append("simulator.null_rho is not on the grid")
    if [r["id"] for r in f["ladder"]] != RUNG_IDS:
        bad.append("ladder: not the eight rung ids in order")
    for r in f["ladder"]:
        if (r["n_scenarios"] is None) != (r["estimator"] != "monte-carlo"):
            bad.append(f"ladder {r['id']}: n_scenarios is set exactly for a Monte Carlo rung")
    if len({g["id"] for g in f["portfolio_spec"]["groups"]}) != len(f["portfolio_spec"]["groups"]):
        bad.append("portfolio_spec.groups: duplicate ids")
    if f["portfolio_spec"]["currency"] != f["currency"]:
        bad.append("portfolio_spec.currency differs from the document's")
    g = f["granularity"]
    if abs(gl_delta(g["xi_reference"], g["q_reference"]) - g["delta_reference"]) >= 0.005:
        bad.append("granularity.delta_reference is not the delta of xi_reference and q_reference")
    return bad


def loan_type_violations(o: dict) -> list[str]:
    return (window_violations(o) + fit_violations(o) + irb_violations(o) + portfolio_violations(o) + measure_violations(o)
            + lhp_rung_violations(o) + euler_violations(o) + granularity_violations(o))


def violations(doc: dict) -> list[str]:
    """Every broken cross-field identity of a C10 document (variant or models); an empty list is a sound document."""
    if doc.get("case_id") != "C10":
        return ["not a C10 document"]
    if doc.get("schema") == "contraste.models/v1":
        return models_violations(doc["fit"])
    kind = doc.get("outputs", {}).get("kind")
    if kind == "loan-type":
        return loan_type_violations(doc["outputs"])
    if kind == "correlation-grid":
        return cell_violations(doc["outputs"])
    return [f"unknown outputs.kind {kind!r}"]


def document_violations(path: str | Path) -> list[str]:
    """``violations`` of the JSON document at ``path`` (the bake's check on every file under data/derived/C10/)."""
    return violations(json.loads(Path(path).read_text(encoding="utf-8")))
