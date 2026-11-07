"""The tables and the numbers of the chapter on risk aggregation and stress testing of the technical report
(``sections/15-aggregation-stress.tex``).

Every table is generated from the committed artifacts under ``data/derived/C18`` (the five scenario and aggregation documents
and the models document of case C18). The numbers the prose quotes are written as macros to
``tables/aggregation-stress-numbers.tex`` (``\\agst<Name>``), so that no number of the chapter is typed by hand. Money is shown in
billions of Chilean pesos (CLP 10^9), read from the artifact's own scale (CLP millions).

The table of the published loss rates of the Federal Reserve (``aggregation-stress-fedkey.tex``) is the one exception that is
not read from ``data/derived``: case C19 has no committed document, and the printed values are transcribed from the tables of the
2025 supervisory stress test methodology, as recorded in the research addendum (see ``FED_KEY`` below for the source lines).

    E:/_venvs/contraste-u16-i/Scripts/python.exe manuscripts/contraste-technical-report/tables/make_aggregation-stress.py
"""
from __future__ import annotations

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import figkit  # noqa: E402

OUT = HERE
PREFIX = "aggregation-stress-"
NL = chr(10)
BS = chr(92)  # a backslash, kept out of string literals so that no escape can alter it
MACROS: dict[str, str] = {}
SOURCES: dict[str, list] = {}

SCEN = {"baseline": "baseline", "eba": "eba-2025-adverse", "fed": "fed-2026-severely-adverse", "ngfs": "ngfs-delayed-transition"}
SCEN_LABEL = {"baseline": "Federal Reserve 2026 baseline", "eba": "EBA 2025 adverse", "fed": "Federal Reserve 2026 severely adverse",
              "ngfs": "NGFS Delayed transition"}
LOAN = {"commercial-industrial": "Commercial and industrial", "commercial-real-estate": "Commercial real estate",
        "residential": "Residential", "credit-cards": "Credit cards", "other-consumer": "Other consumer"}
VARIABLE = {"unemployment_rate": "Unemployment rate", "real_gdp_growth": "Real GDP growth", "prime_rate": "Prime rate", "treasury_10y": "10-year Treasury yield"}
RISK = {"credit": "Credit", "market": "Market", "irrbb": "Interest rate (banking book)", "operational": "Operational"}
LIGHT = {"green": "green", "amber": "amber", "red": "red", "not_evaluated": "not evaluated"}
WINDOW = {"gfc-2008-09": "2008--2009", "pandemic-2020": "2020--2025"}


def macro(name: str, text: str, src: str) -> None:
    MACROS["agst" + name] = text
    SOURCES["agst" + name] = [text, src, sys._getframe(1).f_lineno]


def f(x: float, nd: int = 2) -> str:
    """A plain decimal; the minus sign is typeset as a math minus so that it never breaks a line."""
    return f"{x:.{nd}f}".replace("-", "$-$")


def bn(x: float) -> float:
    """CLP millions to CLP billions (10^9)."""
    return x / 1e3


def pc(x: float, nd: int = 1) -> str:
    return f(100.0 * x, nd)


def sci(x: float, nd: int = 1) -> str:
    """A number in scientific notation as a math string."""
    mant, exp = f"{x:.{nd}e}".split("e")
    return f"${mant}\\times10^{{{int(exp)}}}$"


def si(x: int) -> str:
    """A signed integer with a math minus."""
    return str(int(x)).replace("-", "$-$")


def n_(x: int) -> str:
    return f"{x:,}".replace(",", "{,}")


def case(v: str) -> dict:
    return figkit.doc(f"C18/{SCEN.get(v, v)}.json")


MODELS = figkit.doc("C18/models-banco-andino.json")
BASE = case("baseline")
FED = case("fed")
TCOP = figkit.doc("C18/t-copula-baseline.json")
AGG = BASE["outputs"]["aggregation"]
STRESS_BAND = TCOP["outputs"]["correlation_stress"]["aggregation"]["band"]
for _k in ("eba", "fed", "ngfs"):
    assert json.dumps(case(_k)["outputs"]["aggregation"], sort_keys=True) == json.dumps(AGG, sort_keys=True), "the aggregation block differs"
VAR_RECORD = next(m for m in MODELS["model"] if m["id"] == "c18-var-conditional-forecast")["details"]
GAR_RECORD = next(m for m in MODELS["model"] if m["id"] == "c18-growth-at-risk")["details"]
BASE_SRC = "C18/baseline.json"
MOD_SRC = "C18/models-banco-andino.json"


def write(name: str, header, rows, caption: str, label: str, align: str | None = None, wide: bool = False) -> None:
    figkit.table(OUT / f"{PREFIX}{name}.tex", header, rows, caption=caption, label=label, align=align, wide=wide)


def row_of(method: str, nu: float | None, band: list) -> dict:
    return next(r for r in band if r["method"] == method and (method != "t-copula" or r["nu"] == nu))


# ---------------------------------------------------------------------------------------------------------------------
# the aggregation of the four risks
# ---------------------------------------------------------------------------------------------------------------------

def build_band() -> None:
    names = {"lower-bound": "Lower bound (best VaR less EL)", "simple-sum": "Simple sum (headline)", "variance-covariance": "Variance-covariance",
             "gaussian-copula": "Gaussian copula", "t-copula": "Student t copula", "worst-case": "Worst case (rearrangement)"}
    rows = []
    for r, s in zip(AGG["band"], STRESS_BAND, strict=True):
        assert r["method"] == s["method"] and r["nu"] == s["nu"]
        se = "--" if r["mc_se_clp_m"] is None else f(bn(r["mc_se_clp_m"]), 1)
        se_s = "--" if s["mc_se_clp_m"] is None else f(bn(s["mc_se_clp_m"]), 1)
        nu = "--" if r["nu"] is None else f"{r['nu']:.0f}"
        rows.append([names[r["method"]], nu, f(bn(r["capital_clp_m"]), 1), se, f(r["diversification_factor"], 3), f(bn(s["capital_clp_m"]), 1), se_s])
    write("band", ["Row", "$\\nu$", "Capital", "MC s.e.", "Factor", "Stressed capital", "MC s.e."], rows,
          caption="The dependence band of case C18 over the same four marginals of Banco Andino at one year and 99.9 percent: economic capital of each row in "
                  "CLP billion, the Monte Carlo standard error of the simulated rows, the diversification factor against the simple sum, and the capital of "
                  "each row when the market-credit correlation is raised from 0.5 to 0.8. The bounds are the ends of rearrangement ranges and carry no sampling error.",
          label="tab:aggregation-stress-band", align="llrrrrr")
    sources = f"{BASE_SRC} outputs.aggregation.band"
    for key, (m, nu) in {"Lower": ("lower-bound", None), "Sum": ("simple-sum", None), "Vc": ("variance-covariance", None),
                         "Gauss": ("gaussian-copula", None), "TFour": ("t-copula", 4.0), "TEight": ("t-copula", 8.0),
                         "TThirty": ("t-copula", 30.0), "Worst": ("worst-case", None)}.items():
        r = row_of(m, nu, AGG["band"])
        s = row_of(m, nu, STRESS_BAND)
        macro("Band" + key, f(bn(r["capital_clp_m"]), 1), sources)
        macro("Df" + key, f(r["diversification_factor"], 3), sources)
        macro("Stress" + key, f(bn(s["capital_clp_m"]), 1), "C18/t-copula-baseline.json outputs.correlation_stress.aggregation.band")
        if r["mc_se_clp_m"] is not None:
            macro("Se" + key, f(bn(r["mc_se_clp_m"]), 1), sources)
            macro("StressSe" + key, f(bn(s["mc_se_clp_m"]), 1), "C18/t-copula-baseline.json outputs.correlation_stress.aggregation.band")
    g, gs = row_of("gaussian-copula", None, AGG["band"]), row_of("gaussian-copula", None, STRESS_BAND)
    macro("StressRise", pc(gs["capital_clp_m"] / g["capital_clp_m"] - 1.0, 1), "C18/t-copula-baseline.json, Gaussian row, stressed over base")
    vc, vcs = row_of("variance-covariance", None, AGG["band"]), row_of("variance-covariance", None, STRESS_BAND)
    macro("StressRiseVc", pc(vcs["capital_clp_m"] / vc["capital_clp_m"] - 1.0, 1), "C18/t-copula-baseline.json, variance-covariance row, stressed over base")
    worst, lower, simple = [row_of(m, None, AGG["band"])["capital_clp_m"] for m in ("worst-case", "lower-bound", "simple-sum")]
    macro("WorstOverSum", pc(worst / simple - 1.0, 1), sources)
    macro("BandWidth", f(bn(worst - lower), 1), sources)
    macro("GaussShare", pc(g["capital_clp_m"] / simple, 1), sources)
    macro("DivBenefit", pc(1.0 - g["diversification_factor"], 1), f"{BASE_SRC} outputs.aggregation.diversification.benefit")
    for r in TCOP["outputs"]["copula_sensitivity"]:
        macro("CopRel" + {4.0: "Four", 8.0: "Eight", 30.0: "Thirty"}[r["nu"]], pc(r["relative_difference"], 1),
              "C18/t-copula-baseline.json outputs.copula_sensitivity[*].relative_difference")
    rs = TCOP["outputs"]["rosenberg_schuermann"]
    macro("RsOver", pc(rs["case_additive_overestimate"], 1), "C18/t-copula-baseline.json outputs.rosenberg_schuermann.case_additive_overestimate")
    macro("RsLow", pc(rs["published_additive_overestimate"]["low"], 0), "C18/t-copula-baseline.json outputs.rosenberg_schuermann.published_additive_overestimate")
    macro("RsHigh", pc(rs["published_additive_overestimate"]["high"], 0), "C18/t-copula-baseline.json outputs.rosenberg_schuermann.published_additive_overestimate")
    t8, vcr = row_of("t-copula", 8.0, AGG["band"]), row_of("variance-covariance", None, AGG["band"])
    macro("DiffTEightVc", f(bn(abs(t8["capital_clp_m"] - vcr["capital_clp_m"])), 1), f"{BASE_SRC} outputs.aggregation.band, |t copula nu=8 minus variance-covariance|")
    # parameters of the run
    fit = MODELS["fit"]["aggregation"]
    macro("Draws", n_(fit["n_draws"]), f"{MOD_SRC} fit.aggregation.n_draws")
    macro("Seed", str(fit["seed"]), f"{MOD_SRC} fit.aggregation.seed")
    macro("Chunk", n_(fit["chunk_size"]), f"{MOD_SRC} fit.aggregation.chunk_size")
    macro("Level", f"{AGG['confidence_level']}", f"{BASE_SRC} outputs.aggregation.confidence_level")
    macro("Horizon", str(AGG["horizon_years"]), f"{BASE_SRC} outputs.aggregation.horizon_years")
    grid = fit["quantile_grid"]["convention"]
    macro("GridPoints", n_(grid["points"]), f"{MOD_SRC} fit.aggregation.quantile_grid.convention.points")
    macro("GridZ", f"{grid['z_max']}", f"{MOD_SRC} fit.aggregation.quantile_grid.convention.z_max")
    macro("GridStep", f"{grid['z_step']}", f"{MOD_SRC} fit.aggregation.quantile_grid.convention.z_step")
    macro("NuSet", ", ".join(f"{v:.0f}" for v in AGG["nu_set"]["values"]), f"{BASE_SRC} outputs.aggregation.nu_set.values")
    order = AGG["correlation"]["order"]
    mat = AGG["correlation"]["matrix"]
    body = " \\\\ ".join(" & ".join(f"{v:.1f}" for v in row) for row in mat)
    macro("CorrMatrix", BS + "begin{pmatrix} " + body + " " + BS + "end{pmatrix}", f"{BASE_SRC} outputs.aggregation.correlation.matrix")
    macro("CorrOrder", ", ".join(order), f"{BASE_SRC} outputs.aggregation.correlation.order")
    body_s = " \\\\ ".join(" & ".join(f"{v:.1f}" for v in row) for row in TCOP["outputs"]["correlation_stress"]["aggregation"]["correlation"]["matrix"])
    macro("CorrStressMatrix", BS + "begin{pmatrix} " + body_s + " " + BS + "end{pmatrix}",
          "C18/t-copula-baseline.json outputs.correlation_stress.aggregation.correlation.matrix")
    # the marginals
    ecs = {}
    for m in AGG["marginals"]:
        key = {"credit": "Credit", "market": "Market", "irrbb": "Irrbb", "operational": "Oper"}[m["risk"]]
        ecs[m["risk"]] = m
        macro("Ec" + key, f(bn(m["ec_clp_m"]), 1), f"{BASE_SRC} outputs.aggregation.marginals[{m['risk']}].ec_clp_m")
        macro("El" + key, f(bn(m["el_clp_m"]), 1), f"{BASE_SRC} outputs.aggregation.marginals[{m['risk']}].el_clp_m")
        macro("Var" + key, f(bn(m["var_clp_m"]), 1), f"{BASE_SRC} outputs.aggregation.marginals[{m['risk']}].var_clp_m")
        macro("Es" + key, f(bn(m["es_clp_m"]), 1), f"{BASE_SRC} outputs.aggregation.marginals[{m['risk']}].es_clp_m")
    ec_total = sum(m["ec_clp_m"] for m in AGG["marginals"])
    for m in AGG["marginals"]:
        key = {"credit": "Credit", "market": "Market", "irrbb": "Irrbb", "operational": "Oper"}[m["risk"]]
        macro("EcShare" + key, pc(m["ec_clp_m"] / ec_total, 1), f"{BASE_SRC} outputs.aggregation.marginals[{m['risk']}].ec_clp_m over the sum")
        macro("EsOverEc" + key, f(m["es_clp_m"] / m["ec_clp_m"], 1), f"{BASE_SRC} outputs.aggregation.marginals[{m['risk']}] es_clp_m over ec_clp_m")
    macro("EcSum", f(bn(sum(m["ec_clp_m"] for m in AGG["marginals"])), 1), f"{BASE_SRC} outputs.aggregation.marginals[*].ec_clp_m summed")
    macro("EsSum", f(bn(sum(m["es_clp_m"] for m in AGG["marginals"])), 1), f"{BASE_SRC} outputs.aggregation.marginals[*].es_clp_m summed")
    macro("CreditSe", f(bn(ecs["credit"]["var_se_clp_m"]), 1), f"{BASE_SRC} outputs.aggregation.marginals[credit].var_se_clp_m")
    # the expected-shortfall allocation, the diversification and the model risk
    eu = AGG["euler"]
    macro("EsTotal", f(bn(eu["es_total_clp_m"]), 1), f"{BASE_SRC} outputs.aggregation.euler.es_total_clp_m")
    macro("EulerErr", sci(eu["additivity"]["relative_error"], 1), f"{BASE_SRC} outputs.aggregation.euler.additivity.relative_error")
    macro("EulerTol", sci(eu["additivity"]["tolerance"], 0), f"{BASE_SRC} outputs.aggregation.euler.additivity.tolerance")
    for a in eu["allocation"]:
        key = {"credit": "Credit", "market": "Market", "irrbb": "Irrbb", "operational": "Oper"}[a["risk"]]
        macro("Share" + key, pc(a["share"], 1), f"{BASE_SRC} outputs.aggregation.euler.allocation[{a['risk']}].share")
        macro("Contrib" + key, f(bn(a["contribution_clp_m"]), 1), f"{BASE_SRC} outputs.aggregation.euler.allocation[{a['risk']}].contribution_clp_m")
    for a in AGG["diversification"]["euler_benefit_by_risk"]:
        key = {"credit": "Credit", "market": "Market", "irrbb": "Irrbb", "operational": "Oper"}[a["risk"]]
        macro("Benefit" + key, pc(a["benefit"], 1), f"{BASE_SRC} outputs.aggregation.diversification.euler_benefit_by_risk[{a['risk']}]")
    macro("EsBenefit", pc(1.0 - eu["es_total_clp_m"] / sum(m["es_clp_m"] for m in AGG["marginals"]), 1),
          f"{BASE_SRC} outputs.aggregation.euler.es_total_clp_m over marginals[*].es_clp_m")
    mr = AGG["model_risk"]
    bs, gx = mr["barrieu_scandolo"], mr["glasserman_xu"]
    macro("Am", f(bs["am"], 3), f"{BASE_SRC} outputs.aggregation.model_risk.barrieu_scandolo.am")
    macro("Rm", f(bs["rm"], 3), f"{BASE_SRC} outputs.aggregation.model_risk.barrieu_scandolo.rm")
    macro("RhoRef", f(bn(bs["rho_x0_clp_m"]), 1), f"{BASE_SRC} outputs.aggregation.model_risk.barrieu_scandolo.rho_x0_clp_m")
    macro("RhoMax", f(bn(bs["rho_max_clp_m"]), 1), f"{BASE_SRC} outputs.aggregation.model_risk.barrieu_scandolo.rho_max_clp_m")
    macro("RhoMin", f(bn(bs["rho_min_clp_m"]), 1), f"{BASE_SRC} outputs.aggregation.model_risk.barrieu_scandolo.rho_min_clp_m")
    macro("GxBudget", f(gx["relative_entropy_budget"], 2), f"{BASE_SRC} outputs.aggregation.model_risk.glasserman_xu.relative_entropy_budget")
    macro("GxTheta", sci(gx["theta"], 2), f"{BASE_SRC} outputs.aggregation.model_risk.glasserman_xu.theta")
    macro("GxBase", f(bn(gx["baseline_clp_m"]), 1), f"{BASE_SRC} outputs.aggregation.model_risk.glasserman_xu.baseline_clp_m")
    macro("GxWorst", f(bn(gx["worst_case_clp_m"]), 1), f"{BASE_SRC} outputs.aggregation.model_risk.glasserman_xu.worst_case_clp_m")
    macro("GxRatio", f(gx["worst_case_clp_m"] / gx["baseline_clp_m"], 2), f"{BASE_SRC} outputs.aggregation.model_risk.glasserman_xu worst over baseline")


def build_euler() -> None:
    eu = AGG["euler"]
    benefit = {b["risk"]: b["benefit"] for b in AGG["diversification"]["euler_benefit_by_risk"]}
    alloc = {a["risk"]: a for a in eu["allocation"]}
    rows = []
    for m in AGG["marginals"]:
        a = alloc[m["risk"]]
        rows.append([RISK[m["risk"]], f(bn(m["el_clp_m"]), 1), f(bn(m["ec_clp_m"]), 1), f(bn(m["es_clp_m"]), 1), f(bn(a["contribution_clp_m"]), 1),
                     pc(a["share"], 1), pc(benefit[m["risk"]], 1)])
    es_sum = sum(m["es_clp_m"] for m in AGG["marginals"])
    rows.append(["Portfolio", f(bn(sum(m["el_clp_m"] for m in AGG["marginals"])), 1), f(bn(sum(m["ec_clp_m"] for m in AGG["marginals"])), 1),
                 f(bn(es_sum), 1), f(bn(eu["es_total_clp_m"]), 1), pc(sum(a["share"] for a in eu["allocation"]), 1),
                 pc(1.0 - eu["es_total_clp_m"] / es_sum, 1)])
    write("euler", ["Risk", "EL", "EC", "ES", "Euler contribution", "Share (\\%)", "Euler benefit (\\%)"], rows,
          caption="The four marginals of Banco Andino at one year and 99.9 percent in CLP billion (expected loss, economic capital as value at risk less expected loss, and "
                  "expected shortfall) and the Euler allocation of the expected shortfall of the Gaussian copula aggregate: contribution, share of the total, and the "
                  "Euler diversification benefit of each risk. The portfolio row sums the columns; its last cell is the benefit of the whole.",
          label="tab:aggregation-stress-euler", align="lrrrrrr")


# ---------------------------------------------------------------------------------------------------------------------
# the validation battery
# ---------------------------------------------------------------------------------------------------------------------

TEST_NAME = {
    "aggregation.simple_sum_and_variance_covariance": "Aggregate against the simple sum and the variance-covariance formula",
    "aggregation.copula_choice_sensitivity": "Copula choice: largest relative gap of the t copula to the Gaussian",
    "aggregation.worst_case_bracket": "Rows inside the bounds (width of the bracket, CLP bn)",
    "aggregation.correlation_stress": "Correlation stress: stressed over base Gaussian capital",
    "aggregation.diversification_sign": "Sign of every diversification benefit",
    "aggregation.horizon_confidence_consistency": "One horizon and one level across the marginals",
    "portfolio.euler_additivity": "Euler contributions add to the total (total ES, CLP bn)",
    "aggregation.elliptical_mc_agreement": "Monte Carlo against the variance-covariance formula, elliptical case",
    "stress.sensitivity_monotonicity": "Coefficients with the wrong sign",
    "stress.satellite_backcast": "Back-cast of 2020 to 2025 (RMSE, points; peak timing, quarters)",
    "stress.static_balance_sheet_rules": "Static balance sheet rules violated",
    "stress.scenario_severity": "Scenario severity: path peak over the 2008 to 2009 peak",
}


def fmt_test(t: dict) -> tuple[str, str]:
    i = t["test_id"]
    s, m = t["statistic"], t["metric"]
    if s is None:
        return "--", "--"
    if i == "aggregation.worst_case_bracket":
        return f(bn(s), 1), f(m, 3)
    if i == "portfolio.euler_additivity":
        return f(bn(s), 1), sci(m, 1)
    if i == "stress.satellite_backcast":
        return f(100.0 * s, 2), si(m)
    if i in ("stress.sensitivity_monotonicity", "stress.static_balance_sheet_rules", "aggregation.horizon_confidence_consistency"):
        return f"{int(s)}", "--" if m is None else f(m, 3)
    if i == "aggregation.elliptical_mc_agreement":
        return f(s, 2), f(m, 4)
    return f(s, 3), "--" if m is None else f(m, 3)


def build_battery() -> None:
    rows = []
    tests = list(FED["tests"]) + [t for t in TCOP["tests"] if t["test_id"] == "aggregation.elliptical_mc_agreement"]
    order = list(TEST_NAME)
    tests.sort(key=lambda t: order.index(t["test_id"]))
    counts = {"green": 0, "amber": 0, "red": 0, "not_evaluated": 0}
    for t in tests:
        counts[t["light"]] += 1
        seg = "--" if t["segment"] is None else LOAN.get(t["segment"], VARIABLE.get(t["segment"], t["segment"]))
        s, m = fmt_test(t)
        rows.append([TEST_NAME[t["test_id"]], seg, s, m, LIGHT[t["light"]]])
    write("battery", ["Test", "Segment", "Statistic", "Metric", "Light"], rows,
          caption="The tests the engine applies to the aggregation and the stress chain of case C18 on the Federal Reserve severely adverse document and on the aggregation document: "
                  "the test, the loan type or variable it was applied to, its statistic and metric as the engine returns them, and the light the Contraste internal rule assigns. "
                  "The thresholds are internal acceptance criteria, not regulatory values.",
          label="tab:aggregation-stress-battery", align="llrrl", wide=True)
    macro("LightsGreen", str(counts["green"]), "C18/fed-2026-severely-adverse.json tests and C18/t-copula-baseline.json tests, light counts")
    macro("LightsAmber", str(counts["amber"]), "same")
    macro("LightsRed", str(counts["red"]), "same")
    macro("LightsNotEval", str(counts["not_evaluated"]), "same")
    macro("LightsTotal", str(len(tests)), "same")
    by = {(t["test_id"], t["segment"]): t for t in tests}
    cs = by[("aggregation.copula_choice_sensitivity", None)]
    macro("CopStat", pc(cs["statistic"], 1), "C18/fed-2026-severely-adverse.json tests[aggregation.copula_choice_sensitivity].statistic")
    wc = by[("aggregation.worst_case_bracket", None)]
    macro("BracketRatio", f(wc["metric"], 3), "C18/fed-2026-severely-adverse.json tests[aggregation.worst_case_bracket].metric")
    el = by[("aggregation.elliptical_mc_agreement", None)]
    macro("EllipticalZ", f(el["statistic"], 2), "C18/t-copula-baseline.json tests[aggregation.elliptical_mc_agreement].statistic")
    ss = by[("stress.sensitivity_monotonicity", None)]
    macro("WrongSigns", str(int(ss["statistic"])), "C18/fed-2026-severely-adverse.json tests[stress.sensitivity_monotonicity].statistic")
    declared = sum(c["expected_sign"] != "none" for sat_ in MODELS["fit"]["satellites"] for c in sat_["coefficients"])
    macro("SignDeclared", str(declared), f"{MOD_SRC} fit.satellites[*].coefficients[*].expected_sign other than none")
    macro("SignChecks", str(ss["n"]), "C18/fed-2026-severely-adverse.json tests[stress.sensitivity_monotonicity].n")
    bc = [t for t in tests if t["test_id"] == "stress.satellite_backcast"]
    macro("BackcastRed", str(sum(t["light"] == "red" for t in bc)), "C18/fed-2026-severely-adverse.json tests[stress.satellite_backcast].light")
    macro("BackcastTotal", str(len(bc)), "C18/fed-2026-severely-adverse.json tests[stress.satellite_backcast]")
    th = bc[0]["extras"]["thresholds"]
    macro("PeakAmber", f(th["peak_amber"], 2), "C18/fed-2026-severely-adverse.json tests[stress.satellite_backcast].extras.thresholds.peak_amber")
    macro("PeakRed", f(th["peak_red"], 2), "C18/fed-2026-severely-adverse.json tests[stress.satellite_backcast].extras.thresholds.peak_red")
    macro("TimingQuarters", str(th["timing_quarters"]), "C18/fed-2026-severely-adverse.json tests[stress.satellite_backcast].extras.thresholds.timing_quarters")
    for t in bc:
        key = {"commercial-industrial": "Ci", "commercial-real-estate": "Cre", "residential": "Res", "credit-cards": "Cards", "other-consumer": "Other"}[t["segment"]]
        macro("PeakRatio" + key, f(t["extras"]["peak_ratio"], 2), f"C18/fed-2026-severely-adverse.json tests[stress.satellite_backcast, {t['segment']}].extras.peak_ratio")
        macro("PeakPred" + key, pc(t["extras"]["peak_predicted"], 1), f"C18/fed-2026-severely-adverse.json tests[stress.satellite_backcast, {t['segment']}].extras.peak_predicted")
        macro("PeakReal" + key, pc(t["extras"]["peak_realised"], 2), f"C18/fed-2026-severely-adverse.json tests[stress.satellite_backcast, {t['segment']}].extras.peak_realised")
    sev = {s: [t for t in case(s)["tests"] if t["test_id"] == "stress.scenario_severity"] for s in SCEN}
    for s in ("eba", "fed", "ngfs"):
        macro("SevAmber" + s.capitalize(), str(sum(t["light"] == "amber" for t in sev[s])), f"C18/{SCEN[s]}.json tests[stress.scenario_severity].light")
        macro("SevGreen" + s.capitalize(), str(sum(t["light"] == "green" for t in sev[s])), f"C18/{SCEN[s]}.json tests[stress.scenario_severity].light")
        macro("SevTotal" + s.capitalize(), str(len(sev[s])), f"C18/{SCEN[s]}.json tests[stress.scenario_severity]")
    u = next(r for r in FED["outputs"]["severity"]["rows"] if r["maps_to_regressor"] == "unemployment_rate")
    g = next(r for r in FED["outputs"]["severity"]["rows"] if r["maps_to_regressor"] == "real_gdp_growth")
    macro("SevUnemp", f(u["ratio"], 2), "C18/fed-2026-severely-adverse.json outputs.severity.rows[unemployment_rate].ratio")
    macro("SevUnempPeak", f(u["path_peak_deviation"], 1), "C18/fed-2026-severely-adverse.json outputs.severity.rows[unemployment_rate].path_peak_deviation")
    macro("SevUnempHist", f(u["history_peak_deviation"], 1), "C18/fed-2026-severely-adverse.json outputs.severity.rows[unemployment_rate].history_peak_deviation")
    macro("SevGdp", f(g["ratio"], 2), "C18/fed-2026-severely-adverse.json outputs.severity.rows[real_gdp_growth].ratio")
    macro("SevMin", f(FED["outputs"]["severity"]["minimum_ratio"], 2), "C18/fed-2026-severely-adverse.json outputs.severity.minimum_ratio")


# ---------------------------------------------------------------------------------------------------------------------
# the satellites and the scenarios
# ---------------------------------------------------------------------------------------------------------------------

def build_satellites() -> None:
    sats = MODELS["fit"]["satellites"]
    ss = next(t for t in FED["tests"] if t["test_id"] == "stress.sensitivity_monotonicity")
    names = ss["extras"]["coefficients"]
    wrong: dict[str, list[str]] = {}
    for i in ss["extras"]["offending_indices"]:
        seg, coef = names[i].split(":")
        wrong.setdefault(seg, []).append(coef)
    rows = []
    for s in sats:
        w = wrong.get(s["fed_loan_type"], [])
        rows.append([LOAN[s["fed_loan_type"]], s["link"], f"{s['sample_window']['start'][:4]}Q{(int(s['sample_window']['start'][5:7]) - 1) // 3 + 1}"
                     f" to 2019Q4", str(s["n_obs"]), str(s["non_positive_quarters_in_window"]), f(s["fit_statistics"]["r_squared"], 3),
                     f(s["fit_statistics"]["residual_sd"], 4), str(len(w))])
    write("satellites", ["Loan type", "Link", "Fit window", "$n$", "Non-positive", "$R^2$", "Residual sd", "Wrong signs"], rows,
          caption="The five macro satellites of case C18 fitted by ordinary least squares on the net charge-off rates of the Federal Reserve: loan type, link, fit window, number of "
                  "observations after the lags, quarters of net recovery in the window, coefficient of determination, residual standard deviation on the link scale, and the number "
                  "of coefficients whose estimate has the sign opposite to the one expected before the fit.",
          label="tab:aggregation-stress-satellites", align="llllrrrr", wide=True)
    macro("SatNMin", str(min(s["n_obs"] for s in sats)), f"{MOD_SRC} fit.satellites[*].n_obs")
    macro("SatNMax", str(max(s["n_obs"] for s in sats)), f"{MOD_SRC} fit.satellites[*].n_obs")
    macro("SatRMin", f(min(s["fit_statistics"]["r_squared"] for s in sats), 3), f"{MOD_SRC} fit.satellites[*].fit_statistics.r_squared")
    macro("SatRMax", f(max(s["fit_statistics"]["r_squared"] for s in sats), 3), f"{MOD_SRC} fit.satellites[*].fit_statistics.r_squared")
    macro("NonPosCre", str(next(s for s in sats if s["fed_loan_type"] == "commercial-real-estate")["non_positive_quarters_in_window"]),
          f"{MOD_SRC} fit.satellites[commercial-real-estate].non_positive_quarters_in_window")
    macro("NonPosRes", str(next(s for s in sats if s["fed_loan_type"] == "residential")["non_positive_quarters_in_window"]),
          f"{MOD_SRC} fit.satellites[residential].non_positive_quarters_in_window")
    macro("SatArOrder", str(sats[0]["ar_order"]), f"{MOD_SRC} fit.satellites[0].ar_order")
    macro("SatFitEnd", sats[0]["sample_window"]["end"], f"{MOD_SRC} fit.satellites[0].sample_window.end")
    macro("SatExampleAr", f(sats[0]["coefficients"][1]["estimate"], 3), f"{MOD_SRC} fit.satellites[commercial-industrial].coefficients[ar_1].estimate")
    macro("SatExampleArSe", f(sats[0]["coefficients"][1]["std_error"], 3), f"{MOD_SRC} fit.satellites[commercial-industrial].coefficients[ar_1].std_error")
    macro("SatExampleU", f(sats[0]["coefficients"][4]["estimate"], 3), f"{MOD_SRC} fit.satellites[commercial-industrial].coefficients[unemployment_rate_lag0].estimate")
    macro("SatExampleUSe", f(sats[0]["coefficients"][4]["std_error"], 3), f"{MOD_SRC} fit.satellites[commercial-industrial].coefficients[unemployment_rate_lag0].std_error")
    wrongs_by_type = {k: len(v) for k, v in wrong.items()}
    macro("WrongCards", str(wrongs_by_type.get("credit-cards", 0)), "C18/fed-2026-severely-adverse.json tests[stress.sensitivity_monotonicity].extras.offending_indices")
    macro("WrongRes", str(wrongs_by_type.get("residential", 0)), "same")
    macro("WrongOther", str(wrongs_by_type.get("other-consumer", 0)), "same")
    macro("WrongCi", str(wrongs_by_type.get("commercial-industrial", 0)), "same")
    macro("WrongCre", str(wrongs_by_type.get("commercial-real-estate", 0)), "same")


def build_scenarios() -> None:
    rows = []
    for k in ("baseline", "eba", "fed", "ngfs"):
        d = case(k)["outputs"]
        sc = d["losses"]["scenario_losses"]
        cet = d["headline_cet1"]["rows"]
        un = next((r for r in d["severity"]["rows"] if r["maps_to_regressor"] == "unemployment_rate"), None)
        rows.append([SCEN_LABEL[k], f(bn(sc[0]["credit"]), 1), f(bn(sc[1]["credit"]), 1), f(bn(sc[2]["credit"]), 1), f(bn(sum(r["total"] for r in sc)), 1),
                     pc(cet[-1]["cet1_ratio"], 2), f(100.0 * d["p2g_proxy"]["peak_depletion"], 2), f(un["path_peak_deviation"], 1)])
        key = k.capitalize()
        macro("CumLoss" + key, f(bn(sum(r["total"] for r in sc)), 1), f"C18/{SCEN[k]}.json outputs.losses.scenario_losses[*].total summed")
        macro("CreditLossYOne" + key, f(bn(sc[0]["credit"]), 1), f"C18/{SCEN[k]}.json outputs.losses.scenario_losses[0].credit")
        macro("CreditLossYTwo" + key, f(bn(sc[1]["credit"]), 1), f"C18/{SCEN[k]}.json outputs.losses.scenario_losses[1].credit")
        macro("CreditLossYThree" + key, f(bn(sc[2]["credit"]), 1), f"C18/{SCEN[k]}.json outputs.losses.scenario_losses[2].credit")
        macro("CetEnd" + key, pc(cet[-1]["cet1_ratio"], 2), f"C18/{SCEN[k]}.json outputs.headline_cet1.rows[2].cet1_ratio")
        macro("Depletion" + key, f(100.0 * d["p2g_proxy"]["peak_depletion"], 2), f"C18/{SCEN[k]}.json outputs.p2g_proxy.peak_depletion")
        macro("UnempPeak" + key, f(un["path_peak_deviation"], 1), f"C18/{SCEN[k]}.json outputs.severity.rows[unemployment_rate].path_peak_deviation")
    write("scenarios", ["Scenario", "Credit loss, year 1", "Year 2", "Year 3", "Total loss", "CET1 ratio, end (\\%)", "Peak depletion (pp)", "Unemployment peak (pp)"], rows,
          caption="The four macro scenarios of case C18 run through the satellites and the loss-only capital path of the static balance sheet: credit loss of each of the three "
                  "years and total loss in CLP billion (the market and operational terms are unstressed annual expected losses and IRRBB enters none, so it is a floor), the CET1 ratio at the end of year three against 11 percent at the start, the largest fall of the ratio "
                  "from the start in percentage points, and the peak deviation of unemployment from the jump-off in percentage points.",
          label="tab:aggregation-stress-scenarios", align="lrrrrrrr", wide=True)
    start = FED["outputs"]["capital_start"]["cet1_ratio"]
    macro("CetStart", pc(start, 1), "C18/fed-2026-severely-adverse.json outputs.capital_start.cet1_ratio")
    stack = figkit.doc("C18/reverse-stress.json")["outputs"]["failure_point"]["stack"]["total"]
    macro("CetStack", pc(stack, 2), "C18/reverse-stress.json outputs.failure_point.stack.total")
    macro("Rwa", f(bn(FED["outputs"]["capital_start"]["rwa_clp_m"]), 0), "C18/fed-2026-severely-adverse.json outputs.capital_start.rwa_clp_m")
    macro("CetStartAmount", f(bn(FED["outputs"]["capital_start"]["cet1_clp_m"]), 1), "C18/fed-2026-severely-adverse.json outputs.capital_start.cet1_clp_m")


# ---------------------------------------------------------------------------------------------------------------------
# the VAR and the growth-at-risk quantile satellites
# ---------------------------------------------------------------------------------------------------------------------

def build_var() -> None:
    rows = []
    for w in VAR_RECORD["var"]["windows"]:
        for r in w["per_loan_type"]:
            v, o = r["metrics"]["var"], r["metrics"]["ols"]
            rows.append([WINDOW[w["window_id"]], LOAN[r["fed_loan_type"]], str(r["n_obs"]), f(100 * o["rmse"], 2), f(100 * v["rmse"], 2),
                         f(r["metrics"]["rmse_ratio_var_over_ols"], 2), f(o["peak_ratio"], 2), f(v["peak_ratio"], 2),
                         si(o["peak_timing_error_quarters"]), si(v["peak_timing_error_quarters"]),
                         "VAR" if r["closer"] == "var" else "OLS", str(r["sign_check"]["wrong_signs"])])
    write("var", ["Window", "Loan type", "$n$", "RMSE OLS", "RMSE VAR", "Ratio", "Peak OLS", "Peak VAR", "$\\Delta_{\\mathrm{OLS}}$", "$\\Delta_{\\mathrm{VAR}}$", "Closer", "Wrong signs"],
          rows,
          caption="The two episodes back-cast by the ordinary least squares satellite and by the vector autoregression conditioned on the realised GDP growth, both fitted on data "
                  "that end before the episode: observations of the fit, root mean squared error of each in percentage points of the quarterly net charge-off rate, their ratio, "
                  "the ratio of predicted to realised peak, the timing error of the peak in quarters, the model closer to the realised rates, and the VAR coefficients with a wrong sign.",
          label="tab:aggregation-stress-var", align="llrrrrrrrrlr", wide=True)
    sm = {s["window_id"]: s for s in VAR_RECORD["var"]["summary"]}
    for wid, key in (("gfc-2008-09", "Gfc"), ("pandemic-2020", "Pan")):
        macro("VarCloser" + key, str(sm[wid]["var_closer"]), f"{MOD_SRC} model[c18-var-conditional-forecast].details.var.summary[{wid}].var_closer")
        macro("OlsCloser" + key, str(sm[wid]["ols_closer"]), f"{MOD_SRC} model[c18-var-conditional-forecast].details.var.summary[{wid}].ols_closer")
        macro("VarLoanTypes" + key, str(sm[wid]["loan_types"]), f"{MOD_SRC} model[c18-var-conditional-forecast].details.var.summary[{wid}].loan_types")
        macro("VarRed" + key, str(sm[wid]["sign_checks_red"]), f"{MOD_SRC} model[c18-var-conditional-forecast].details.var.summary[{wid}].sign_checks_red")
    acc = VAR_RECORD["acceptance"]
    macro("VarWrong", str(acc["var_wrong_signs"]), f"{MOD_SRC} model[c18-var-conditional-forecast].details.acceptance.var_wrong_signs")
    macro("VarChecks", str(acc["var_sign_checks"]), f"{MOD_SRC} model[c18-var-conditional-forecast].details.acceptance.var_sign_checks")
    macro("GarWrong", str(acc["gar_wrong_signs"]), f"{MOD_SRC} model[c18-var-conditional-forecast].details.acceptance.gar_wrong_signs")
    macro("GarChecks", str(acc["gar_sign_checks"]), f"{MOD_SRC} model[c18-var-conditional-forecast].details.acceptance.gar_sign_checks")
    macro("VarLags", str(VAR_RECORD["var"]["lags"]), f"{MOD_SRC} model[c18-var-conditional-forecast].details.var.lags")
    allg = [r for w in VAR_RECORD["var"]["windows"] for r in w["per_loan_type"]]
    macro("GapToOls", sci(max(r["full_conditioning_gap_to_ols"] for r in allg), 1), f"{MOD_SRC} model[c18-var-conditional-forecast].details.var.windows[*].per_loan_type[*].full_conditioning_gap_to_ols (max)")
    for w in VAR_RECORD["var"]["windows"]:
        wk = "Gfc" if w["window_id"].startswith("gfc") else "Pan"
        nobs = [r["n_obs"] for r in w["per_loan_type"]]
        macro("VarNMin" + wk, str(min(nobs)), f"{MOD_SRC} model[c18-var-conditional-forecast].details.var.windows[{w['window_id']}].per_loan_type[*].n_obs")
        macro("VarNMax" + wk, str(max(nobs)), f"{MOD_SRC} model[c18-var-conditional-forecast].details.var.windows[{w['window_id']}].per_loan_type[*].n_obs")
        for r in w["per_loan_type"]:
            key = {"commercial-industrial": "Ci", "commercial-real-estate": "Cre", "residential": "Res", "credit-cards": "Cards", "other-consumer": "Other"}[r["fed_loan_type"]]
            m = r["metrics"]
            macro(f"Ratio{wk}{key}", f(m["rmse_ratio_var_over_ols"], 2), f"{MOD_SRC} ...windows[{w['window_id']}].per_loan_type[{r['fed_loan_type']}].metrics.rmse_ratio_var_over_ols")
            macro(f"RmseOls{wk}{key}", f(100 * m["ols"]["rmse"], 2), f"{MOD_SRC} ...windows[{w['window_id']}].per_loan_type[{r['fed_loan_type']}].metrics.ols.rmse")
            macro(f"RmseVar{wk}{key}", f(100 * m["var"]["rmse"], 2), f"{MOD_SRC} ...windows[{w['window_id']}].per_loan_type[{r['fed_loan_type']}].metrics.var.rmse")
            macro(f"PeakOls{wk}{key}", f(m["ols"]["peak_ratio"], 2), f"{MOD_SRC} ...windows[{w['window_id']}].per_loan_type[{r['fed_loan_type']}].metrics.ols.peak_ratio")
            macro(f"PeakVar{wk}{key}", f(m["var"]["peak_ratio"], 2), f"{MOD_SRC} ...windows[{w['window_id']}].per_loan_type[{r['fed_loan_type']}].metrics.var.peak_ratio")
    ex = VAR_RECORD["var"]["windows"][0]["per_loan_type"][0]["coefficients"]
    macro("VarExampleAr", f(ex[1]["estimate"], 3), f"{MOD_SRC} ...windows[gfc-2008-09].per_loan_type[commercial-industrial].coefficients[ar_1].estimate")
    macro("VarExampleArSe", f(ex[1]["std_error"], 3), f"{MOD_SRC} ...windows[gfc-2008-09].per_loan_type[commercial-industrial].coefficients[ar_1].std_error")
    macro("VarExampleU", f(ex[3]["estimate"], 3), f"{MOD_SRC} ...windows[gfc-2008-09].per_loan_type[commercial-industrial].coefficients[unemployment_rate_lag1].estimate")
    macro("VarExampleUSe", f(ex[3]["std_error"], 3), f"{MOD_SRC} ...windows[gfc-2008-09].per_loan_type[commercial-industrial].coefficients[unemployment_rate_lag1].std_error")


def build_gar() -> None:
    g = GAR_RECORD["growth_at_risk"]
    rows = []
    for w in g["windows"]:
        for c, p in zip(w["coverage"], w["pinball"], strict=True):
            assert c["tau"] == p["tau"]
            rows.append([WINDOW[w["window_id"]], f(c["tau"], 2), f"{c['hits']} of {c['n']}", f(c["rate"], 3), f(p["conditional"], 3), f(p["unconditional"], 3), f(p["ratio"], 3)])
    write("gar", ["Window", "$\\tau$", "Realised below quantile", "Rate", "Pinball, regression", "Pinball, unconditional", "Ratio"], rows,
          caption="The growth-at-risk quantile regressions of the average real GDP growth over the next four quarters, fixed at the end of the training span and scored on every later "
                  "origin: for each quantile level, the number of origins at which the realised growth fell below the predicted quantile, its rate against the nominal level, "
                  "and the mean pinball loss of the regression, of the unconditional quantile of the training span, and their ratio.",
          label="tab:aggregation-stress-gar", align="llrrrrr")
    macro("GarHorizon", str(g["horizon_quarters"]), f"{MOD_SRC} model[c18-growth-at-risk].details.growth_at_risk.horizon_quarters")
    macro("GarTaus", ", ".join(f"{t:g}" for t in g["taus"]), f"{MOD_SRC} model[c18-growth-at-risk].details.growth_at_risk.taus")
    for w in g["windows"]:
        wk = "Gfc" if w["window_id"].startswith("gfc") else "Pan"
        s = f"{MOD_SRC} model[c18-growth-at-risk].details.growth_at_risk.windows[{w['window_id']}]"
        macro("GarTrain" + wk, str(w["train_origins"]["n"]), s + ".train_origins.n")
        macro("GarTrainFirst" + wk, w["train_origins"]["first"][:4], s + ".train_origins.first")
        macro("GarTrainLast" + wk, w["train_origins"]["last"][:4], s + ".train_origins.last")
        macro("GarOrigins" + wk, str(len(w["origins"])), s + ".origins")
        macro("GarRatio" + wk, f(w["mean_pinball_ratio"], 3), s + ".mean_pinball_ratio")
        macro("GarCross" + wk, str(w["crossing_origins"]), s + ".crossing_origins")
        fo = w["first_origin"]
        macro("GarFirstQ" + wk, f(fo["growth_at_risk_5"], 2), s + ".first_origin.growth_at_risk_5")
        macro("GarFirstReal" + wk, f(fo["realised"], 2), s + ".first_origin.realised")
        macro("GarFirstDate" + wk, fo["origin"][:4] + "Q4", s + ".first_origin.origin")
        c5 = w["coverage"][0]
        macro("GarHitsLow" + wk, str(c5["hits"]), s + ".coverage[0].hits")
        c95 = w["coverage"][-1]
        macro("GarHitsHigh" + wk, str(c95["hits"]), s + ".coverage[-1].hits")
        macro("GarRateHigh" + wk, f(c95["rate"], 2), s + ".coverage[-1].rate")
        macro("GarRateUpper" + wk, f(w["coverage"][3]["rate"], 2), s + ".coverage[3].rate")
        sk = w["skewed_t_at_first_origin"]
        if wk == "Gfc":
            assert sk["status"] == "not-fitted", "the text says the skewed t fit fails in the first window"
        else:
            assert sk["status"] == "fitted", "the text reports the skewed t fit of the second window"
            macro("SkewMu" + wk, f(sk["mu"], 2), s + ".skewed_t_at_first_origin.mu")
            macro("SkewSigma" + wk, f(sk["sigma"], 2), s + ".skewed_t_at_first_origin.sigma")
            macro("SkewAlpha" + wk, f(sk["alpha"], 2), s + ".skewed_t_at_first_origin.alpha")
            macro("SkewNu" + wk, f(sk["nu"], 1), s + ".skewed_t_at_first_origin.nu")
            macro("SkewDist" + wk, f(sk["distance"], 3), s + ".skewed_t_at_first_origin.distance")
        coef = w["coefficients"][0]["terms"]
        macro("GarBetaGdp" + wk, f(coef[1]["estimate"], 2), s + ".coefficients[tau 0.05].terms[real_gdp_growth].estimate")
        macro("GarBetaSpread" + wk, f(coef[2]["estimate"], 2), s + ".coefficients[tau 0.05].terms[term_spread].estimate")
    macro("GarRegressors", " and ".join({"real_gdp_growth": "real GDP growth", "term_spread": "the spread of the ten-year Treasury yield over the prime rate"}[x] for x in g["regressors"]), f"{MOD_SRC} model[c18-growth-at-risk].details.growth_at_risk.regressors")
    macro("GarUncond", f(g["windows"][0]["unconditional_quantiles"][0], 2), f"{MOD_SRC} ...windows[gfc-2008-09].unconditional_quantiles[0]")


# ---------------------------------------------------------------------------------------------------------------------
# the published answer keys of the supervisory exercise (case C19; no committed document)
# ---------------------------------------------------------------------------------------------------------------------

#: Transcribed from the research addendum of the Contraste initiative (CAOS_MANAGE wip/contraste/u13-research-addendum-2026-10-18.md):
#: the published loss rates (percent) of the lower-risk, typical and higher-risk hypothetical portfolios, Tables 22, 27, 32 and 37 of the
#: Federal Reserve 2025 Supervisory Stress Test Methodology (lines 24 to 27 of the addendum), and the inputs of each model that
#: the public portfolio files and the scenario files do not carry (lines 160 to 163 of the addendum, the replicability table).
FED_KEY = [
    ("Corporate", "22", (2.1, 5.8, 8.5), "coefficients of the 2025 model and its initial vendor default probabilities; collateral type; four-digit industry code"),
    ("Commercial real estate", "27", (4.0, 5.5, 16.2), "county unemployment and house price paths; market vacancy, rent and price indices; net operating income"),
    ("First-lien mortgage", "32", (2.0, 2.5, 5.5), "state and county price and unemployment paths; judicial-state flag; origination spread; loan history"),
    ("Credit card", "37", (8.5, 19.7, 30.4), "state unemployment; delinquency and utilisation history; the coefficients of the 2025 model"),
]


def build_fedkey() -> None:
    rows = []
    for name, table, (lo, ty, hi), missing in FED_KEY:
        rows.append([name, table, f(lo, 1), f(ty, 1), f(hi, 1), missing])
    write("fedkey", ["Portfolio type", "Table", "Lower", "Typical", "Higher", "Inputs the public files do not carry"], rows,
          caption="The loss rates of the three hypothetical portfolios of each type that the Federal Reserve publishes for the 2024 severely adverse scenario over nine quarters, in percent "
                  "of the initial utilised balance, with the table of the 2025 methodology that prints them and the inputs of the supervisory model that are absent from the public "
                  "portfolio and scenario files. No committed Contraste computation reproduces these values.",
          label="tab:aggregation-stress-fedkey", align="llrrrp{6.2cm}", wide=True)
    macro("FedCorpLow", f(FED_KEY[0][2][0], 1), "addendum line 24 (Table 22)")
    macro("FedCorpTyp", f(FED_KEY[0][2][1], 1), "addendum line 24 (Table 22)")
    macro("FedCorpHigh", f(FED_KEY[0][2][2], 1), "addendum line 24 (Table 22)")
    macro("FedCreTyp", f(FED_KEY[1][2][1], 1), "addendum line 25 (Table 27)")
    macro("FedCardTyp", f(FED_KEY[3][2][1], 1), "addendum line 27 (Table 37)")
    macro("FedCardHigh", f(FED_KEY[3][2][2], 1), "addendum line 27 (Table 37)")
    macro("FedMortLow", f(FED_KEY[2][2][0], 1), "addendum line 26 (Table 32)")
    macro("FedMortHigh", f(FED_KEY[2][2][2], 1), "addendum line 26 (Table 32)")


def fit_width() -> None:
    """Wrap the tabular of every generated table in a box that shrinks it to the text width when it is wider."""
    for p in OUT.glob(PREFIX + "*.tex"):
        if p.name == PREFIX + "numbers.tex":
            continue
        s = p.read_text(encoding="utf-8")
        if BS + "resizebox" in s:
            continue
        s = s.replace(BS + "begin{tabular}", BS + "fitwidth{%" + NL + BS + "begin{tabular}", 1)
        s = s.replace(BS + "end{tabular}", BS + "end{tabular}}", 1)
        p.write_text(s, encoding="utf-8", newline=NL)


def write_numbers() -> None:
    lines = ["% Numbers quoted by sections/15-aggregation-stress.tex, written by tables/make_aggregation-stress.py from data/derived."]
    for k in sorted(MACROS):
        lines.append(f"{BS}newcommand{{{BS}{k}}}{{{MACROS[k]}}}")
    (OUT / f"{PREFIX}numbers.tex").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    build_band()
    build_euler()
    build_battery()
    build_satellites()
    build_scenarios()
    build_var()
    build_gar()
    build_fedkey()
    write_numbers()
    fit_width()
    print(f"{len(MACROS)} macros, {len(list(OUT.glob(PREFIX + '*.tex'))) - 1} tables")
    if "--sources" in sys.argv:
        target = pathlib.Path(sys.argv[sys.argv.index("--sources") + 1])
        target.write_text(json.dumps(SOURCES, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
