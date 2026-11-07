"""The tables and the numbers of the counterparty credit risk chapter of the technical report (``sections/12-ccr.tex``).

Every table is generated from the committed artifacts of case C12 (``data/derived/C12``) and of the regulatory calculators
(``data/derived/regulatory/calculators.json``); the rows of the table of the other regulatory calculators are calls of the pinned
engine ``riskvalidation`` 1.1.0, next to the reference value its documentation prints (``docs/regulatory/u9`` and ``docs/oprisk``
of the engine repository, quoted in the table). The numbers the prose quotes are written as macros to ``tables/ccr-numbers.tex``
(``\\ccr<Name>``), so that no number of the chapter is typed by hand.

    E:/_venvs/contraste-u16-i/Scripts/python.exe manuscripts/contraste-technical-report/tables/make_ccr.py
"""
from __future__ import annotations

import pathlib
import re
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import figkit  # noqa: E402

VARIANTS = ["single-swap", "netting-set", "csa-mpor-10d", "csa-mpor-20d", "with-im", "wrong-way-risk"]
LABEL = {"single-swap": "Single swap", "netting-set": "Netting set", "csa-mpor-10d": "CSA, MPoR 10 days",
         "csa-mpor-20d": "CSA, MPoR 20 days", "with-im": "CSA with initial margin", "wrong-way-risk": "Wrong-way risk"}
HORIZONS = ["10bd", "20bd", "1m", "3m", "6m", "12m"]
MACROS: dict[str, str] = {}
_CACHE: dict[str, dict] = {}


def doc(v: str) -> dict:
    if v not in _CACHE:
        _CACHE[v] = figkit.doc(f"C12/{v}.json")
    return _CACHE[v]


def out(v: str) -> dict:
    return doc(v)["outputs"]


def neg(text: str) -> str:
    """A leading minus sign as a typeset minus (a hyphen is not one)."""
    return "$-$" + text[1:] if text.startswith("-") else text


def macro(name: str, text: str) -> None:
    MACROS[name] = neg(text)


def n0(x: float) -> str:
    return neg(f"{x:,.0f}")


def nd(x: float, d: int = 2) -> str:
    return neg(f"{x:,.{d}f}")


def mth(text: str) -> str:
    """Text for use in running prose or inside math: the thousands comma becomes a braced comma."""
    return text.replace(",", "{,}")


def pm(x: float, se: float, d: int = 0) -> str:
    return "$" + mth(f"{x:,.{d}f}") + "\\pm" + mth(f"{se:,.{d}f}") + "$"


def sci(x: float) -> str:
    mant, exp = f"{x:.1e}".split("e")
    return f"${mant}\\times10^{{{int(exp)}}}$"


def fit_width() -> None:
    """Wrap the tabular of every generated table in a box that shrinks it to the text width when it is wider."""
    for f in HERE.glob("ccr-t-*.tex"):
        s = f.read_text(encoding="utf-8")
        if "\\resizebox" in s or "\\fitwidth" in s:
            continue
        s = s.replace("\\begin{tabular}", "\\fitwidth{%\n\\begin{tabular}", 1)
        s = s.replace("\\end{tabular}", "\\end{tabular}}", 1)
        f.write_text(s, encoding="utf-8", newline="\n")


def grid_index(v: str, t: float) -> int:
    g = out(v)["exposure"]["time_grid_years"]
    return int(np.argmin(np.abs(np.asarray(g) - t)))


def light_counts(rows: list[dict]) -> tuple[int, int, int, int]:
    c = {"green": 0, "amber": 0, "red": 0, "not_evaluated": 0}
    for r in rows:
        c[r["light"]] += 1
    return c["green"], c["amber"], c["red"], c["not_evaluated"]


# ---------------------------------------------------------------------------------------------------------------------
# The book and the named parameters


def table_book() -> None:
    ns = out("netting-set")
    rows = []
    for t in ns["book"]["trades"]:
        single = "yes" if t["trade_id"] == "SW-1" else "no"
        rows.append([t["trade_id"], t["side"], n0(t["notional"]["amount"]), nd(t["maturity_years"], 1),
                     "$" + f"{100 * t['fixed_rate']:.2f}" + "\\,\\%$", t["fixed_frequency_per_year"], single, "yes"])
    figkit.table(HERE / "ccr-t-book.tex", ["Trade", "Side", "Notional (USD)", "Maturity (years)", "Fixed rate",
                                          "Fixed payments per year", "In single swap", "In netting set"], rows,
                 caption="The synthetic book of case C12 on the Treasury par curve of 2025-09-30: four interest rate swaps on one floating curve, "
                         "each fixed rate equal to the par yield of the swap's maturity rounded to 10 basis points; the single swap is the first trade.",
                 label="tab:ccr-book", align="llrrrrcc")
    macro("CurveDate", ns["curve"]["curve_date"])


def table_params() -> None:
    s = out("single-swap")
    npar = s["named_parameters"]
    cal = s["calibration_used"]

    def v(name: str):
        return npar[name]["value"]

    rows = [
        ["\\relax Mean reversion $a$", pm(cal["a"], cal["a_se"], 4), "per year", "estimated (AR(1) regression)"],
        ["\\relax Volatility $\\sigma$", pm(cal["sigma"], cal["sigma_se"], 5), "per square-root year", "estimated (AR(1) regression)"],
        ["Short-rate proxy tenor", nd(cal["proxy_tenor_years"], 2), "years", "shortest Treasury zero rate"],
        ["Observations in the fit", n0(cal["n_obs"]), "daily", f"{cal['sample_start']} to {cal['sample_end']}"],
        ["Monte Carlo paths", n0(v("path_count")), "paths", "convention (antithetic)"],
        ["Seed", str(v("seed")), "integer", "convention"],
        ["Report grid points", str(len(v("time_grid_years"))), "dates", "monthly, quarterly, half-yearly"],
        ["PFE quantile", nd(v("pfe_quantile"), 2), "decimal", "convention"],
        ["CSA threshold", n0(v("csa_threshold")), "USD", "convention"],
        ["CSA minimum transfer amount", n0(v("csa_minimum_transfer_amount")), "USD", "convention"],
        ["CSA independent amount", n0(v("csa_independent_amount")), "USD", "convention"],
        ["Margin period of risk, short and long", f"{v('mpor_business_days_short')} and {v('mpor_business_days_long')}", "business days", "convention (CRE53.24 floor of 10)"],
        ["Counterparty spread (synthetic flat, sensitivity only)", nd(v("counterparty_spread"), 4), "per year", "convention"],
        ["Counterparty loss given default", nd(v("counterparty_lgd"), 2), "decimal", "convention"],
        ["Bank own spread", nd(v("bank_spread"), 4), "per year", "convention"],
        ["Bank loss given default", nd(v("bank_lgd"), 2), "decimal", "convention"],
        ["Initial margin quantile", nd(v("im_quantile"), 2), "decimal", "convention"],
        ["Initial margin horizon and MPoR", f"{v('im_horizon_calendar_days')} and {v('im_mpor_calendar_days')}", "calendar days", "convention (10 business days)"],
        ["Initial margin regression order", str(v("im_regression_order")), "polynomial order", "convention"],
        ["\\relax Wrong-way parameter grid $b$", ", ".join(f"{b:g}" for b in v("wwr_b_grid")), "per USD million", "convention"],
        ["BA-CVA sector and rating", f"{v('ba_cva_sector')}, {v('ba_cva_rating')}", "MAR50.16 Table 1", "convention"],
        ["Stress calibration window", f"{v('stress_window_start')} to {v('stress_window_end')}", "dates", "convention (CRE53.7)"],
        ["Backtest start and paths per date", f"{v('backtest_window_start')}, {n0(v('backtest_paths_per_date'))}", "month, paths", "convention"],
        ["Simulated backtests for critical values", n0(v("backtest_simulated_critical_count")), "backtests", "convention"],
        ["Agreement threshold with the reference engine", str(v("reconciliation_se_threshold")), "combined standard errors", "convention"],
        ["Agreement threshold of the closed-form checks", str(v("ee_check_k_se")), "standard errors", "convention"],
    ]
    figkit.table(HERE / "ccr-t-params.tex", ["Parameter", "Value", "Unit", "Status"], rows,
                 caption="The parameters of case C12 as the artifacts record them: the Hull-White coefficients estimated at the curve date with their "
                         "standard errors, and the conventions of the synthetic book, the CSA, the credit curve, the initial margin and the backtest.",
                 label="tab:ccr-params", align="llll")
    macro("PathCount", n0(v("path_count")))
    macro("Seed", str(v("seed")))
    macro("GridPoints", str(len(v("time_grid_years"))))
    macro("HwA", f"{cal['a']:.4f}")
    macro("HwASe", f"{cal['a_se']:.4f}")
    macro("HwSigma", f"{cal['sigma']:.5f}")
    macro("HwSigmaSe", f"{cal['sigma_se']:.5f}")
    macro("NObs", n0(cal["n_obs"]))
    macro("HistYears", f"{cal['history_years']:.2f}")
    macro("SampleStart", cal["sample_start"])
    macro("SampleEnd", cal["sample_end"])
    macro("PfeQuantile", f"{v('pfe_quantile'):.2f}")
    macro("Mta", n0(v("csa_minimum_transfer_amount")))
    macro("CpLgd", f"{v('counterparty_lgd'):.1f}")
    macro("BankSpread", f"{v('bank_spread'):.3f}")
    macro("ImQuantile", f"{v('im_quantile'):.2f}")
    macro("BacktestPaths", n0(v("backtest_paths_per_date")))
    macro("CriticalCount", n0(v("backtest_simulated_critical_count")))
    macro("StressStart", v("stress_window_start"))
    macro("StressEnd", v("stress_window_end"))
    m = re.search(r"(\d+) samples", out("single-swap")["ore_reconciliation"]["platform"])
    macro("OreSamples", n0(int(m.group(1))) if m else "UNVERIFIED")


# ---------------------------------------------------------------------------------------------------------------------
# Exposure, CVA and the regulatory measures


def table_exposure() -> None:
    rows = []
    for v in VARIANTS:
        o = out(v)
        e = o["exposure"]
        i1 = grid_index(v, 1.0)
        rows.append([LABEL[v], n0(e["ee"]["values"][i1]), n0(max(e["ee"]["values"])), n0(max(e["pfe"]["values"])),
                     pm(e["eepe"]["amount"], e["eepe"]["mc_se"]), nd(o["regulatory_comparison"]["effective_maturity_years"], 1),
                     pm(o["cva_dva"]["cva"]["amount"], o["cva_dva"]["cva"]["mc_se"], 1),
                     pm(o["cva_dva"]["dva"]["amount"], o["cva_dva"]["dva"]["mc_se"], 1)])
    figkit.table(HERE / "ccr-t-exposure.tex",
                 ["Variant", "EE at 1 year", "Peak EE", "Peak PFE 95\\%", "EEPE", "$M$ (years)", "CVA", "DVA"], rows,
                 caption="Exposure and credit valuation adjustment of the six variants of case C12, in USD: expected exposure at one year, its peak, the peak "
                         "95 percent potential future exposure, the effective expected positive exposure, the effective maturity and the CVA and DVA, with their Monte Carlo standard errors.",
                 label="tab:ccr-exposure", align="lrrrrrrr")
    ss, ns = out("single-swap"), out("netting-set")
    c10, c20, im, ww = out("csa-mpor-10d"), out("csa-mpor-20d"), out("with-im"), out("wrong-way-risk")
    for key, o in (("Single", ss), ("Netting", ns), ("CsaShort", c10), ("CsaLong", c20), ("Im", im)):
        macro("Eepe" + key, n0(o["exposure"]["eepe"]["amount"]))
        macro("EepeSe" + key, n0(o["exposure"]["eepe"]["mc_se"]))
        macro("Cva" + key, n0(o["cva_dva"]["cva"]["amount"]))
        macro("CvaD" + key, nd(o["cva_dva"]["cva"]["amount"], 1))
        macro("Dva" + key, n0(o["cva_dva"]["dva"]["amount"]))
        macro("PfePeak" + key, n0(max(o["exposure"]["pfe"]["values"])))
        macro("EePeak" + key, n0(max(o["exposure"]["ee"]["values"])))
    for key, o in (("Single", ss), ("Netting", ns)):
        g = o["exposure"]["time_grid_years"]
        macro("PeakTime" + key, nd(g[int(np.argmax(o["exposure"]["ee"]["values"]))], 1))
    macro("NettingCutEepe", f"{100 * (1 - ns['exposure']['eepe']['amount'] / ss['exposure']['eepe']['amount']):.0f}")
    macro("CvaSeNetting", nd(ns["cva_dva"]["cva"]["mc_se"], 1))
    macro("CvaSeSingle", nd(ss["cva_dva"]["cva"]["mc_se"], 1))
    macro("EeOneYearSingle", n0(ss["exposure"]["ee"]["values"][grid_index("single-swap", 1.0)]))
    macro("EeOneYearNetting", n0(ns["exposure"]["ee"]["values"][grid_index("netting-set", 1.0)]))
    macro("EeOneYearCsaShort", n0(c10["exposure"]["ee"]["values"][grid_index("csa-mpor-10d", 1.0)]))
    macro("EeOneYearCsaLong", n0(c20["exposure"]["ee"]["values"][grid_index("csa-mpor-20d", 1.0)]))
    macro("EeOneYearIm", n0(im["exposure"]["ee"]["values"][grid_index("with-im", 1.0)]))
    macro("RatioCsaShort", f"{c10['exposure']['eepe']['amount'] / ns['exposure']['eepe']['amount']:.2f}")
    macro("RatioCsaLong", f"{c20['exposure']['eepe']['amount'] / ns['exposure']['eepe']['amount']:.2f}")
    macro("CutCsaShort", f"{100 * (1 - c10['exposure']['eepe']['amount'] / ns['exposure']['eepe']['amount']):.0f}")
    macro("CutCsaLong", f"{100 * (1 - c20['exposure']['eepe']['amount'] / ns['exposure']['eepe']['amount']):.0f}")
    macro("RatioLongShort", f"{c20['exposure']['eepe']['amount'] / c10['exposure']['eepe']['amount']:.2f}")
    nb = ns["netting_benefit"]
    i1 = grid_index("netting-set", 1.0)
    macro("SumSingleOneYear", n0(nb["sum_of_single_trade_ee"]["values"][i1]))
    macro("NettedOneYear", n0(nb["netted_ee"]["values"][i1]))
    macro("NettingBenefitOneYear", n0(nb["benefit"]["values"][i1]))
    macro("NettingBenefitPct", f"{100 * nb['benefit']['values'][i1] / nb['sum_of_single_trade_ee']['values'][i1]:.0f}")
    macro("EffMaturity", nd(ns["regulatory_comparison"]["effective_maturity_years"], 1))
    macro("BaCvaM", nd(ns["ba_cva"]["counterparties"][0]["m_years"], 1))
    macro("BaCvaMSingle", nd(ss["ba_cva"]["counterparties"][0]["m_years"], 1))
    dim = im["initial_margin"]["dim"]["values"]
    macro("DimZero", n0(dim[0]))
    macro("DimPeak", n0(max(dim)))
    macro("Nica", n0(im["sa_ccr"]["nica"]["amount"]))
    macro("EeVmOnlyPeak", n0(max(im["initial_margin"]["ee_vm_only"]["values"])))
    macro("ImAlpha", f"{im['initial_margin']['alpha']:.4f}")
    macro("CvaWwrIndependent", n0(ww["wrong_way_risk"]["independent_cva"]["amount"]))


def table_regulatory() -> None:
    rows = []
    for v in VARIANTS[:5]:
        o = out(v)
        rc = o["regulatory_comparison"]
        rows.append([LABEL[v], n0(o["sa_ccr"]["ead"]["amount"]), n0(rc["alpha_times_eepe"]["amount"]),
                     nd(rc["sa_ccr_over_alpha_eepe"], 2), n0(rc["stressed"]["effective_epe"]["amount"]),
                     n0(o["ba_cva"]["capital"]["amount"]), n0(o["girr"]["delta_charge"]["amount"]),
                     n0(o["girr"]["delta_charge_undivided"]["amount"])])
    figkit.table(HERE / "ccr-t-regulatory.tex",
                 ["Variant", "SA-CCR EAD", "$1.4\\times$ EEPE", "Ratio", "Stressed EEPE", "BA-CVA capital", "GIRR delta", "GIRR undivided"], rows,
                 caption="The regulatory measures beside the model measures for the five distinct variants of case C12, in USD: the SA-CCR exposure at default, "
                         "1.4 times the effective expected positive exposure, their ratio, the stressed EEPE, the reduced BA-CVA capital and the GIRR delta charge with and without the division by the square root of two.",
                 label="tab:ccr-regulatory", align="lrrrrrrr")
    ss, ns, c10, c20, im = (out(k) for k in VARIANTS[:5])
    macro("EadSingle", n0(ss["sa_ccr"]["ead"]["amount"]))
    macro("EadNetting", n0(ns["sa_ccr"]["ead"]["amount"]))
    macro("EadCsaShort", n0(c10["sa_ccr"]["ead"]["amount"]))
    macro("EadCsaLong", n0(c20["sa_ccr"]["ead"]["amount"]))
    macro("EadIm", n0(im["sa_ccr"]["ead"]["amount"]))
    macro("AlphaEepeNetting", n0(ns["regulatory_comparison"]["alpha_times_eepe"]["amount"]))
    macro("RatioEadNetting", nd(ns["regulatory_comparison"]["sa_ccr_over_alpha_eepe"], 2))
    macro("RatioEadSingle", nd(ss["regulatory_comparison"]["sa_ccr_over_alpha_eepe"], 2))
    macro("StressedNetting", n0(ns["regulatory_comparison"]["stressed"]["effective_epe"]["amount"]))
    macro("StressedSpreadStart", f"{ns['regulatory_comparison']['stressed']['hqm_spread_start']:.4f}")
    macro("StressedSpreadPeak", f"{ns['regulatory_comparison']['stressed']['hqm_spread_peak']:.4f}")
    macro("BaCvaNetting", n0(ns["ba_cva"]["capital"]["amount"]))
    macro("BaCvaSingle", n0(ss["ba_cva"]["capital"]["amount"]))
    macro("BaCvaIm", n0(im["ba_cva"]["capital"]["amount"]))
    macro("GirrNetting", n0(ns["girr"]["delta_charge"]["amount"]))
    macro("GirrUndividedNetting", n0(ns["girr"]["delta_charge_undivided"]["amount"]))
    macro("GirrSingle", n0(ss["girr"]["delta_charge"]["amount"]))
    macro("MultNetting", f"{ns['sa_ccr']['multiplier']:.4f}")
    macro("MultSingle", f"{ss['sa_ccr']['multiplier']:.4f}")
    macro("VNetting", n0(ns["sa_ccr"]["v"]["amount"]))
    macro("AddOnNetting", n0(ns["sa_ccr"]["addon_aggregate"]["amount"]))
    macro("AddOnSingle", n0(ss["sa_ccr"]["addon_aggregate"]["amount"]))
    macro("RcCsa", n0(c10["sa_ccr"]["rc"]["amount"]))
    macro("EadCsaImDiff", n0(c10["sa_ccr"]["ead"]["amount"] - im["sa_ccr"]["ead"]["amount"]))
    macro("AlphaRcCsa", n0(1.4 * c10["sa_ccr"]["rc"]["amount"]))
    # with initial margin: C is the variation margin plus the NICA (CRE52.10, CRE52.17), so the multiplier falls below 1
    macro("MultIm", f"{im['sa_ccr']['multiplier']:.4f}")
    macro("CIm", n0(im["sa_ccr"]["c"]["amount"]))
    macro("RcIm", n0(im["sa_ccr"]["rc"]["amount"]))
    macro("EadMultDiff", n0(c10["sa_ccr"]["ead"]["amount"] - im["sa_ccr"]["ead"]["amount"]
                            - 1.4 * (c10["sa_ccr"]["rc"]["amount"] - im["sa_ccr"]["rc"]["amount"])))
    mf = {t["trade_id"]: t["maturity_factor"] for t in c10["sa_ccr"]["trades"]}
    macro("MaturityFactorCsa", f"{next(iter(mf.values())):.4f}")


def table_saccr_ladder() -> None:
    rows = []
    for v in ("single-swap", "netting-set", "csa-mpor-10d", "csa-mpor-20d", "with-im"):
        s = out(v)["sa_ccr"]
        hs = s["hedging_sets"][0]
        rows.append([LABEL[v], nd(s["rc"]["amount"], 0), nd(hs["d_b1"] / 1e6, 3), nd(hs["d_b2"] / 1e6, 3), nd(hs["d_b3"] / 1e6, 3),
                     nd(hs["effective_notional"] / 1e6, 3), n0(hs["addon"]), nd(s["multiplier"], 4), n0(s["pfe"]["amount"]), n0(s["ead"]["amount"])])
    figkit.table(HERE / "ccr-t-saccr.tex",
                 ["Variant", "RC", "$D^{B1}$", "$D^{B2}$", "$D^{B3}$", "Effective notional", "Add-on", "Multiplier", "PFE", "EAD"], rows,
                 caption="The SA-CCR intermediates of the interest rate hedging set (USD) of each variant of case C12: replacement cost, the signed effective notionals of the "
                         "three maturity buckets and the hedging set in USD million, the add-on, the multiplier, the potential future exposure and the exposure at default.",
                 label="tab:ccr-saccr", align="lrrrrrrrrr")
    s = out("netting-set")["sa_ccr"]["hedging_sets"][0]
    macro("DOneNetting", nd(s["d_b1"] / 1e6, 2))
    macro("DTwoNetting", nd(s["d_b2"] / 1e6, 2))
    macro("DThreeNetting", nd(s["d_b3"] / 1e6, 2))
    macro("ENNetting", nd(s["effective_notional"] / 1e6, 2))
    macro("DThreeSingle", nd(out("single-swap")["sa_ccr"]["hedging_sets"][0]["d_b3"] / 1e6, 2))
    t1 = out("single-swap")["sa_ccr"]["trades"][0]
    macro("SdTen", f"{t1['supervisory_duration']:.4f}")


def table_ore() -> None:
    rows = []
    for v in VARIANTS[:5]:
        r = out(v)["ore_reconciliation"]
        ag = r["agreement"]
        gaps = [abs(a["difference"]) / a["combined_se"] if a["combined_se"] > 0 else (0.0 if a["difference"] == 0 else float("inf")) for a in ag]
        within = sum(1 for a in ag if a["within_two_se"])
        ee, cv = r["eepe_agreement"], r["cva_agreement"]
        rows.append([LABEL[v], n0(ee["python"]), n0(ee["ore"]), nd(abs(ee["difference"]) / ee["combined_se"], 2), nd(cv["python"], 1), nd(cv["ore"], 1),
                     nd(abs(cv["difference"]) / cv["combined_se"], 1), f"{within} of {len(ag)}", nd(max(gaps), 1), "yes" if r["all_within_two_se"] else "no"])
        key = {"single-swap": "Single", "netting-set": "Netting", "csa-mpor-10d": "CsaShort", "csa-mpor-20d": "CsaLong", "with-im": "Im"}[v]
        macro("OreWithin" + key, str(within))
        bad = [a for a in ag if not a["within_two_se"]]
        macro("OreFirstFail" + key, nd(bad[0]["t"], 2) if bad else "none")
        macro("OreLastFail" + key, nd(bad[-1]["t"], 1) if bad else "none")
        macro("OreFailCount" + key, str(len(bad)))
        macro("OreGap" + key, nd(max(gaps), 1))
        macro("OreEepe" + key, n0(ee["ore"]))
        macro("OreCva" + key, nd(cv["ore"], 1))
        macro("OreCvaGap" + key, nd(abs(cv["difference"]) / cv["combined_se"], 1))
        macro("OreEepeGap" + key, nd(abs(ee["difference"]) / ee["combined_se"], 2))
        macro("OreCvaRel" + key, f"{100 * abs(cv['python'] - cv['ore']) / cv['ore']:.1f}")
        macro("OreEepeRel" + key, f"{100 * abs(ee['python'] - ee['ore']) / ee['ore']:.1f}")
    macro("OreGridPoints", str(len(out("single-swap")["ore_reconciliation"]["agreement"])))
    figkit.table(HERE / "ccr-t-ore.tex",
                 ["Variant", "EEPE engine", "EEPE ORE", "EEPE gap (SE)", "CVA engine", "CVA ORE", "CVA gap (SE)", "Points within 2 SE", "Largest EE gap (SE)", "All within"], rows,
                 caption="Agreement of the engine with ORE 1.8.17.0 on the five variants it can price, in USD: effective expected positive exposure and CVA of the two engines, their "
                         "gaps in combined Monte Carlo standard errors, the report dates at which the two expected exposure profiles agree within two standard errors and the largest gap.",
                 label="tab:ccr-ore", align="lrrrrrrrrc")
    # the dynamic initial margin against ORE's and the minimum-transfer-amount-zero rows
    im = out("with-im")
    o_dim = np.asarray(im["ore_reconciliation"]["ore_dim"]["values"])
    p_dim = np.asarray(im["initial_margin"]["dim"]["values"])
    ratio = float(np.mean(o_dim / p_dim))
    macro("DimRatio", f"{ratio:.3f}")
    macro("DimGap", nd(next(t for t in doc("with-im")["tests"] if t["test_id"] == "ccr.ore_dim_agreement")["statistic"], 1))
    for v, key in (("csa-mpor-10d", "Short"), ("csa-mpor-20d", "Long")):
        seg = next(t for t in doc(v)["tests"] if t["test_id"] == "ccr.reconcile_ee_profile" and t["segment"] == "minimum-transfer-amount-0")
        macro("MtaZeroGap" + key, nd(seg["statistic"], 1))
    macro("ImEeGap", nd(next(t for t in doc("with-im")["tests"] if t["test_id"] == "ccr.reconcile_ee_profile")["statistic"], 1))
    macro("OreEeGapNetting", nd(next(t for t in doc("netting-set")["tests"] if t["test_id"] == "ccr.reconcile_ee_profile")["statistic"], 2))


def table_wwr() -> None:
    w = out("wrong-way-risk")["wrong_way_risk"]
    base = next(s for s in w["sweep"] if s["b"] == 0.0)["cva"]["amount"]
    rows = []
    for s in w["sweep"]:
        rows.append([neg(f"{s['b']:g}"), pm(s["cva"]["amount"], s["cva"]["mc_se"], 1), nd(s["cva"]["amount"] / base, 3),
                     sci(s["a_calibration_max_error"]), "yes" if s["independent"] else "no"])
        key = {"-2": "NegTwo", "0": "Zero", "1": "One", "2": "Two", "4": "Four"}[f"{s['b']:g}"]
        macro("WwrCva" + key, n0(s["cva"]["amount"]))
        macro("WwrRatio" + key, nd(s["cva"]["amount"] / base, 2))
        macro("WwrPct" + key, f"{100 * (s['cva']['amount'] / base - 1):.0f}")
    figkit.table(HERE / "ccr-t-wwr.tex", ["$b$ (per USD million)", "CVA (USD)", "Ratio to $b=0$", "Largest calibration error of $a(t)$", "Independent of exposure"], rows,
                 caption="The wrong-way risk sweep of case C12 on the netting set: CVA of the Hull and White hazard model against the dependence parameter b, with its Monte Carlo standard error, "
                         "the ratio to the independent value and the largest distance between the average simulated survival and its target.",
                 label="tab:ccr-wwr", align="lrrrc")
    macro("WwrMaxBw", nd(w["largest_b_w"], 2))
    macro("WwrWMax", nd(w["w_max_usd_million"], 3))
    macro("WwrMaxCalErr", sci(max(s["a_calibration_max_error"] for s in w["sweep"])).replace("$", ""))


def table_backtest() -> None:
    b = out("netting-set")["backtest"]
    rows = []
    for obj, hs in (("Netting-set value", b["book_horizons"]), ("3 month zero rate", b["risk_factor"]["horizons"])):
        for h in hs:
            ex95 = next(e for e in h["exceedances"] if abs(e["quantile"] - 0.95) < 1e-9)
            rows.append([obj, h["horizon"], h["n"], nd(h["w2"], 2), nd(h["critical_simulated"]["p05"], 2), nd(h["critical_simulated"]["p01"], 2),
                         nd(h["effective_sample_size"], 1), "yes" if h["reject_at_5pct"] else "no", f"{ex95['count']} of {ex95['expected']:.1f}"])
    figkit.table(HERE / "ccr-t-backtest.tex",
                 ["Object", "Horizon", "Dates", "$W^2$", "5\\% critical", "1\\% critical", "Effective size", "Rejected", "Exceedances of PFE 95\\%"], rows,
                 caption="The exposure backtest of case C12 over the monthly dates from 2000-01 to 2025-09: the Anderson-Darling statistic of the probability integral transforms of the realised "
                         "netting-set value and of the 3 month zero rate, the critical values simulated under the model, the effective sample size and the observed against the expected 95 percent exceedances.",
                 label="tab:ccr-backtest", align="llrrrrrcr")
    bk = {h["horizon"]: h for h in b["book_horizons"]}
    rf = {h["horizon"]: h for h in b["risk_factor"]["horizons"]}
    macro("BtDates", str(bk["10bd"]["n"]))
    macro("BtWBookShort", nd(bk["10bd"]["w2"], 2))
    macro("BtWBookLong", nd(bk["12m"]["w2"], 2))
    macro("BtCritShort", nd(bk["10bd"]["critical_simulated"]["p05"], 2))
    macro("BtCritLong", nd(bk["12m"]["critical_simulated"]["p05"], 2))
    macro("BtCritOneShort", nd(bk["10bd"]["critical_simulated"]["p01"], 2))
    macro("BtCritOneLong", nd(bk["12m"]["critical_simulated"]["p01"], 2))
    macro("BtEssLong", nd(bk["12m"]["effective_sample_size"], 1))
    macro("BtEssShort", nd(bk["10bd"]["effective_sample_size"], 0))
    macro("BtWRfShort", nd(rf["10bd"]["w2"], 2))
    macro("BtWRfSix", nd(rf["6m"]["w2"], 2))
    pb10, pb12, pr10 = np.asarray(bk["10bd"]["pits"]), np.asarray(bk["12m"]["pits"]), np.asarray(rf["10bd"]["pits"])
    macro("PitOuterBook", f"{100 * np.mean((pb10 < 0.1) | (pb10 > 0.9)):.0f}")
    macro("PitLowBookYear", f"{100 * np.mean(pb12 < 0.1):.0f}")
    macro("PitCentralRf", f"{100 * np.mean((pr10 >= 0.4) & (pr10 < 0.6)):.0f}")
    macro("BtWRfMin",nd(min(h["w2"] for h in rf.values()), 2))
    macro("BtWRfMax", nd(max(h["w2"] for h in rf.values()), 2))
    macro("BtWRfMinHorizon", min(rf, key=lambda k: rf[k]["w2"]))
    macro("BtWRfMaxHorizon", max(rf, key=lambda k: rf[k]["w2"]))
    macro("BtRejectedBook",str(sum(1 for h in bk.values() if h["reject_at_5pct"])))
    macro("BtRejectedRf", str(sum(1 for h in rf.values() if h["reject_at_5pct"])))
    macro("BtHorizons", str(len(bk)))
    for h in HORIZONS:
        e = next(x for x in bk[h]["exceedances"] if abs(x["quantile"] - 0.95) < 1e-9)
        macro("BtExc" + {"10bd": "Ten", "20bd": "Twenty", "1m": "One", "3m": "Three", "6m": "Six", "12m": "Twelve"}[h], str(e["count"]))
    macro("BtExpected", nd(next(x for x in bk["10bd"]["exceedances"] if abs(x["quantile"] - 0.95) < 1e-9)["expected"], 1))
    e90 = next(x for x in bk["10bd"]["exceedances"] if abs(x["quantile"] - 0.90) < 1e-9)
    e99 = next(x for x in bk["10bd"]["exceedances"] if abs(x["quantile"] - 0.99) < 1e-9)
    macro("BtExcNinetyCount", str(e90["count"]))
    macro("BtExcNinetyExp", nd(e90["expected"], 1))
    macro("BtExcNinetyNineCount", str(e99["count"]))
    macro("BtExcNinetyNineExp", nd(e99["expected"], 1))
    rf4 = [next(x for x in rf[h]["exceedances"] if abs(x["quantile"] - 0.95) < 1e-9)["count"] for h in HORIZONS]
    exp95 = next(x for x in bk["10bd"]["exceedances"] if abs(x["quantile"] - 0.95) < 1e-9)["expected"]
    macro("RfBelow", str(sum(1 for c in rf4 if c < exp95)))
    macro("RfExcMin", str(min(rf4)))
    macro("RfExcMax", str(max(rf4)))
    # sub-windows
    sw = b["sub_windows"]
    rows = []
    for s in sw:
        by = {r["horizon"]: r for r in s["results"]}
        rows.append([s["window"], f"{s['start']} to {s['end']}", by["10bd"]["n"]] + [nd(by[h]["w2"], 2) for h in HORIZONS])
    figkit.table(HERE / "ccr-t-subwindows.tex", ["Window", "Dates", "$n$"] + [f"$W^2$ {h}" for h in HORIZONS], rows,
                 caption="The Anderson-Darling statistic of the netting-set value of case C12 in the three sub-windows of the backtest, by horizon: before 2008, 2008 to 2019 and from 2020, with the number of dates of each window.",
                 label="tab:ccr-subwindows", align="llrrrrrrr")
    macro("SubMin", nd(min(r["w2"] for s in sw for r in s["results"]), 2))
    macro("SubMax", nd(max(r["w2"] for s in sw for r in s["results"]), 2))
    macro("SubPre", nd(next(r["w2"] for r in sw[0]["results"] if r["horizon"] == "10bd"), 2))
    macro("SubMid", nd(next(r["w2"] for r in sw[1]["results"] if r["horizon"] == "10bd"), 2))
    macro("SubPost", nd(next(r["w2"] for r in sw[2]["results"] if r["horizon"] == "10bd"), 2))
    macro("IidFive", nd(bk["10bd"]["critical_iid"]["p05"], 3))
    macro("IidOne", nd(bk["10bd"]["critical_iid"]["p01"], 3))


def table_sensitivity() -> None:
    rows = []
    s = out("netting-set")["calibration_sensitivity"]
    for r in s:
        rows.append([r["case"], nd(r["a"], 4), nd(r["sigma"], 5), n0(r["eepe"]["amount"]), n0(r["pfe_peak"]["amount"])])
    figkit.table(HERE / "ccr-t-sensitivity.tex", ["Case", "$a$", "$\\sigma$", "EEPE (USD)", "Peak PFE 95\\% (USD)"], rows,
                 caption="Sensitivity of the netting-set exposure of case C12 to the short-rate calibration: effective expected positive exposure and peak potential future exposure when the mean reversion "
                         "or the volatility moves by one standard error of its estimate.",
                 label="tab:ccr-sensitivity", align="lrrrr")
    by = {r["case"]: r for r in s}
    macro("EepeAPlus", n0(by["a-plus-1se"]["eepe"]["amount"]))
    macro("EepeAMinus", n0(by["a-minus-1se"]["eepe"]["amount"]))
    macro("EepeSigmaPlus", n0(by["sigma-plus-1se"]["eepe"]["amount"]))
    macro("EepeSigmaMinus", n0(by["sigma-minus-1se"]["eepe"]["amount"]))
    macro("PfeAPlus", n0(by["a-plus-1se"]["pfe_peak"]["amount"]))
    macro("PfeAMinus", n0(by["a-minus-1se"]["pfe_peak"]["amount"]))
    macro("APlusValue", nd(by["a-plus-1se"]["a"], 4))
    macro("AMinusValue", nd(by["a-minus-1se"]["a"], 4))
    base = by["base"]["eepe"]["amount"]
    macro("EepeAPlusPct", f"{100 * (by['a-plus-1se']['eepe']['amount'] / base - 1):.0f}")
    macro("EepeAMinusPct", f"{100 * (by['a-minus-1se']['eepe']['amount'] / base - 1):.0f}")
    macro("EepeSigmaPct", f"{100 * (by['sigma-plus-1se']['eepe']['amount'] / base - 1):.1f}")
    # the spread of the calibrations over the backtest dates
    cals = figkit.doc("C12/models-hw1f-treasury-2000-2025.json")["fit"]["calibrations"]
    macro("CalDates", str(len(cals)))
    macro("CalAMin", nd(min(c["a"] for c in cals), 3))
    macro("CalAMax", nd(max(c["a"] for c in cals), 3))
    macro("CalSigmaMin", nd(min(c["sigma"] for c in cals), 5))
    macro("CalSigmaMax", nd(max(c["sigma"] for c in cals), 5))
    macro("CalFirstA", nd(cals[0]["a"], 3))
    macro("CalFirstDate", cals[0]["backtest_date"])
    macro("CalFirstYears", nd(cals[0]["history_years"], 1))


def table_tests() -> None:
    rows = []
    for v in VARIANTS:
        t = doc(v)["tests"]
        back = [r for r in t if r["test_id"] in ("ccr.pit_exposure_backtest", "ccr.pfe_exceedance_backtest")]
        rest = [r for r in t if r not in back]
        g, a, r, n = light_counts(rest)
        bg, ba, br, bn = light_counts(back)
        rows.append([LABEL[v], len(rest), g, a, r, len(back), bg, ba, br])
    figkit.table(HERE / "ccr-t-tests.tex",
                 ["Variant", "Engine rows", "Green", "Amber", "Red", "Backtest rows", "Green", "Amber", "Red"], rows,
                 caption="The test rows of each variant of case C12 by light: the rows that check the engine against closed forms, identities, convergence and the reference engines, and the rows of the exposure backtest "
                         "(PIT statistics and exceedance counts); no row is amber or not evaluated.",
                 label="tab:ccr-tests", align="lrrrrrrrr")
    ns = doc("netting-set")["tests"]
    macro("TestsNetting", str(len(ns)))
    macro("TestsNettingGreen", str(sum(1 for r in ns if r["light"] == "green")))
    macro("TestsNettingRed", str(sum(1 for r in ns if r["light"] == "red")))
    macro("TestsAmberAny", str(sum(1 for v in VARIANTS for r in doc(v)["tests"] if r["light"] == "amber")))
    ql = [r for r in doc("single-swap")["tests"] if r["test_id"].startswith("ccr.quantlib")]
    macro("QlMaxRel", sci(max(abs(r["statistic"]) for r in ql)).replace("$", ""))
    macro("QlRows", str(len(ql)))
    pc = {v: next(t for t in doc(v)["tests"] if t["test_id"] == "ccr.path_convergence") for v in VARIANTS}
    macro("PathConvMin", nd(min(p["statistic"] for p in pc.values()), 2))
    macro("PathConvMax", nd(max(p["statistic"] for p in pc.values()), 2))
    macro("PathConvLow", str(pc["netting-set"]["extras"]["thresholds"]["smaller_count"]))
    macro("PathConvHigh", str(pc["netting-set"]["extras"]["thresholds"]["larger_count"]))
    macro("MartingaleStat", nd(next(t for t in ns if t["test_id"] == "ccr.martingale_discounted_bonds")["statistic"], 3))
    ee = next(t for t in doc("single-swap")["tests"] if t["test_id"] == "ccr.ee_analytic_vs_simulated")
    macro("AnalyticStat", nd(ee["statistic"], 3))
    macro("AnalyticMetric", n0(ee["metric"]))


# ---------------------------------------------------------------------------------------------------------------------
# The regulatory calculators


def table_cre99() -> None:
    cal = figkit.doc("regulatory/calculators.json")
    rows = []
    exact = 0
    for ex in cal["official_examples"]:
        if ex["calculator"] != "sa-ccr":
            continue
        out_ = {o["name"]: o["value"] for o in ex["outputs"]}
        pub = {p["name"]: p["value"] for p in ex["published"]}
        ead = out_["ead"]
        hit = round(ead) == pub["ead"]
        exact += int(hit)
        rows.append([ex["title"]["en"].replace("CRE99 netting set ", "Set ").split(":")[0] + ": " + ex["title"]["en"].split(": ", 1)[1],
                     nd(out_["rc"], 0), nd(out_["addon_aggregate"], 3), nd(out_["multiplier"], 6), nd(ead, 4), n0(pub["ead"]),
                     "yes" if hit else "no", sci(ex["tolerance_relative"])])
    figkit.table(HERE / "ccr-t-cre99.tex",
                 ["Netting set (USD thousands)", "RC", "Aggregate add-on", "Multiplier", "EAD computed", "EAD published", "Rounds to published", "Relative tolerance"], rows,
                 caption="The five official worked examples of the standardised approach to counterparty credit risk (CRE99) recomputed by the engine from their trades, in USD thousands: "
                         "replacement cost, aggregate add-on, multiplier, the unrounded exposure at default and the published integer value.",
                 label="tab:ccr-cre99", align="lrrrrrcc")
    macro("CreExact", str(exact))
    macro("CreSets", str(sum(1 for e in cal["official_examples"] if e["calculator"] == "sa-ccr")))
    eads = {e["id"]: {o["name"]: o["value"] for o in e["outputs"]} for e in cal["official_examples"]}
    macro("CreEadOne", nd(eads["cre99-netting-set-1"]["ead"], 3))
    macro("CreEadFive", nd(eads["cre99-netting-set-5"]["ead"], 3))
    macro("CreMultTwo", nd(eads["cre99-netting-set-2"]["multiplier"], 6))
    macro("CreMultFive", nd(eads["cre99-netting-set-5"]["multiplier"], 6))
    macro("CreEnUsd", n0(eads["cre99-netting-set-1"]["en_usd"]))
    macro("CreDelta", nd(eads["cre99-netting-set-1"]["swaption_delta"], 4))
    macro("CreMfFive", nd(eads["cre99-netting-set-5"]["maturity_factor"], 6))
    macro("CreTol", "$10^{-9}$")
    macro("FloorValue", nd(eads["rbc20-13-output-floor"]["rwa_floored"], 1))
    macro("FloorCapped", nd(eads["rbc20-13-output-floor-capped"]["rwa_floored"], 0))
    macro("InvariantRows", str(len(cal["invariant_cases"])))
    macro("InvariantHold", str(sum(1 for c in cal["invariant_cases"] if c["holds"])))
    macro("PhaseInFirst", nd(cal["output_floor_phase_in"][0]["factor"], 2))
    macro("PhaseInLast", nd(cal["output_floor_phase_in"][-1]["factor"], 3))
    macro("PhaseInFirstYear", str(cal["output_floor_phase_in"][0]["year"]))


def table_other() -> None:
    """Rows computed by the pinned engine; the reference value is the one the engine documentation prints."""
    from riskvalidation.oprisk import sma
    from riskvalidation.regulatory import frtb, lcr_nsfr, output_floor

    losses = np.full(10, 5.37e9 / 15.0)
    sc = sma.sma_capital(35e9, losses)
    h1 = lcr_nsfr.hqla_stock(100.0, 20.0, 30.0)
    h2 = lcr_nsfr.hqla_stock(100.0, 80.0, 0.0)
    cal = figkit.doc("regulatory/calculators.json")
    inv = {c["id"]: {o["name"]: o["value"] for o in c["outputs"]} for c in cal["invariant_cases"]}
    # (calculator, quantity, computed, reference printed in the engine documentation, source page)
    data = [
        ("SMA (OPE25.7 footnote 2)", "BIC at BI of 35 bn EUR (bn)", sma.bic(35e9) / 1e9, 5.37, "oprisk/04_sma-ope25.md"),
        ("SMA (OPE25.8)", "RWA, BI 35 bn and ten annual losses of 358 m (bn)", sc.rwa / 1e9, 67.125, "oprisk/04_sma-ope25.md"),
        ("SMA (OPE25.8)", "internal loss multiplier at LC equal to BIC", sc.ilm, 1.0, "oprisk/04_sma-ope25.md"),
        ("Output floor (RBC20.13)", "floored RWA, 76 and 140 at 0.725", output_floor.floored_rwa(76, 140, 0.725), 101.5, "regulatory/u9/02_output-floor.md"),
        ("Output floor (RBC90.2)", "floored RWA with the 25 percent cap", output_floor.floored_rwa(76, 140, 0.725, cap_share=0.25), 95.0, "regulatory/u9/02_output-floor.md"),
        ("BA-CVA (MAR50.14)", "reduced capital base at rho of 1, SCVA 10 and 20", inv["ba-cva-rho-one"]["k_reduced"], 30.0, "regulatory/u9/04_ba-cva.md"),
        ("BA-CVA (MAR50.20)", "full capital base with no hedges, K reduced 30", inv["ba-cva-hedges-floor"]["k_full"], 7.5, "regulatory/u9/04_ba-cva.md"),
        ("FRTB (MAR21.4)", "cross-bucket charge with the fallback, medium scenario", inv["sbm-cross-bucket-fallback"]["cross_bucket_medium"], 10.9545, "regulatory/u9/05_frtb-sbm-and-cascade.md"),
        ("FRTB (MAR33.4)", "liquidity-horizon cascade ES, 10 and 6", frtb.liquidity_cascade_es(10.0, {20: 6.0}, 10), 11.661904, "regulatory/u9/05_frtb-sbm-and-cascade.md"),
        ("FRTB (MAR21.44)", "GIRR charge, one 10-year sensitivity of 80 million (USD)", inv["girr-delta-charge-sqrt2"]["girr_charge"], 622253.97, "regulatory/u9/05_frtb-sbm-and-cascade.md"),
        ("LCR (LCR30.39)", "HQLA, Level 1 100, Level 2A 20, Level 2B 30", h1.hqla, 141.176471, "regulatory/u9/../../liquidity/07_lcr-and-nsfr.md"),
        ("LCR (LCR30.39)", "HQLA, Level 1 100, Level 2A 80", h2.hqla, 166.666667, "liquidity/07_lcr-and-nsfr.md"),
        ("LCR (LCR40.1)", "ratio, HQLA 100 over net outflows 50", lcr_nsfr.lcr_ratio(100.0, 50.0), 2.0, "liquidity/07_lcr-and-nsfr.md"),
        ("NSFR (NSF20.2)", "available stable funding, capital 10 and stable retail deposits 100", lcr_nsfr.nsfr_asf({"regulatory_capital": 10.0, "stable_retail_deposits": 100.0}), 105.0, "liquidity/07_lcr-and-nsfr.md"),
        ("NSFR (NSF20.2)", "ratio, ASF 105 over RSF 50", lcr_nsfr.nsfr_ratio(105.0, 50.0), 2.1, "liquidity/07_lcr-and-nsfr.md"),
    ]
    rows = []
    worst = 0.0
    for calc, q, got, ref, src in data:
        rel = abs(got - ref) / abs(ref)
        worst = max(worst, rel)
        src = src.replace("regulatory/u9/../../", "")
        rows.append([calc, q, f"{got:.6g}", f"{ref:.6g}", sci(rel) if rel > 0 else "$0$"])
    figkit.table(HERE / "ccr-t-other.tex", ["Calculator (paragraph)", "Quantity", "Engine", "Reference", "Relative difference"], rows,
                 caption="The other regulatory calculators called in the pinned engine against the value their paragraph or the engine documentation prints: standardised operational risk capital, the output floor, "
                         "BA-CVA, the FRTB aggregation and liquidity cascade, the liquidity coverage ratio and the net stable funding ratio.",
                 label="tab:ccr-other", align="llrrr")
    macro("OtherRows", str(len(data)))
    macro("OtherWorst", sci(worst).replace("$", ""))
    macro("SmaBic", nd(sma.bic(35e9) / 1e9, 2))
    macro("SmaBicHalf", nd(sma.bic(0.5e9) / 1e9, 2))
    macro("SmaBicThirty", nd(sma.bic(30e9) / 1e9, 2))
    macro("SmaRwa", nd(sc.rwa / 1e9, 3))
    macro("HqlaOne", nd(h1.hqla, 3))
    macro("HqlaAdjFifteen", nd(h1.adj_15, 3))
    macro("HqlaTwo", nd(h2.hqla, 3))
    macro("HqlaAdjForty", nd(h2.adj_40, 3))
    macro("CascadeEs", nd(frtb.liquidity_cascade_es(10.0, {20: 6.0}, 10), 4))
    macro("GirrOneSens", n0(inv["girr-delta-charge-sqrt2"]["girr_charge"]))
    macro("GirrOneUndivided", n0(inv["girr-delta-charge-sqrt2"]["girr_charge_undivided"]))
    macro("FallbackCharge", nd(inv["sbm-cross-bucket-fallback"]["cross_bucket_medium"], 4))


def write_macros() -> None:
    lines = ["% Generated by tables/make_ccr.py from data/derived/C12 and data/derived/regulatory; do not edit by hand."]
    for k in sorted(MACROS):
        if not re.fullmatch(r"[A-Za-z]+", k):
            raise ValueError(f"macro name {k!r} must be letters only")
        lines.append(f"\\newcommand{{\\ccr{k}}}{{{MACROS[k]}}}")
    (HERE / "ccr-numbers.tex").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    table_book()
    table_params()
    table_exposure()
    table_regulatory()
    table_saccr_ladder()
    table_ore()
    table_wwr()
    table_backtest()
    table_sensitivity()
    table_tests()
    table_cre99()
    table_other()
    fit_width()
    write_macros()
    print("tables:", len(list(HERE.glob("ccr-t-*.tex"))), "macros:", len(MACROS))


if __name__ == "__main__":
    main()
