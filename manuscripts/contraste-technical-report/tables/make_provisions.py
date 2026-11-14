"""The tables and the numbers of the provisions chapter of the technical report (``sections/08-provisions.tex``).

Every table is generated from the committed artifacts under ``data/derived`` (cases C03, C06 and C07) and, for the tables of
statutory parameters and the worked example of the non-linearity of the expected credit loss, from the pinned engine
``riskvalidation`` called as the pipeline calls it. The numbers the prose quotes are written as macros to
``tables/provisions-numbers.tex`` (``\\pv<Name>``), so that no number of the chapter is typed by hand.

    E:/_venvs/contraste-u16-i/Scripts/python.exe manuscripts/contraste-technical-report/tables/make_provisions.py
"""
from __future__ import annotations

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import figkit  # noqa: E402
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _halfup import fixed, percent, sci, install as _halfup_install  # noqa: E402
_halfup_install(figkit)

DATES = ["2006-12", "2008-12", "2010-12", "2019-12", "2020-06", "2023-06"]
SCENARIOS = ["base", "recession", "consumer-arrears-shock", "house-price-fall", "uf-inflation-spike", "combined-severe"]
SCEN_LABEL = {"base": "Base", "recession": "Recession", "consumer-arrears-shock": "Consumer arrears shock",
              "house-price-fall": "House price fall", "uf-inflation-spike": "UF inflation spike",
              "combined-severe": "Combined severe"}
LIGHT = {"green": "G", "amber": "A", "red": "R", "not_evaluated": "n/e"}
OUT = HERE
MACROS: dict[str, str] = {}


def fit_width() -> None:
    """Wrap the tabular of every generated table in a box that shrinks it to the text width when it is wider."""
    for f in OUT.glob("provisions-t-*.tex"):
        s = f.read_text(encoding="utf-8")
        if "\\resizebox" in s or "\\fitwidth" in s:
            continue
        s = s.replace("\\begin{tabular}", "\\fitwidth{%\n\\begin{tabular}", 1)
        s = s.replace("\\end{tabular}", "\\end{tabular}}", 1)
        f.write_text(s, encoding="utf-8", newline="\n")


def macro(name: str, text: str) -> None:
    MACROS[name] = text


def c06(date: str) -> dict:
    return figkit.doc(f"C06/rd-{date}.json")


def c06m(date: str) -> dict:
    return figkit.doc(f"C06/models-rd-{date}.json")


def rung(models: dict, rid: str) -> dict:
    return next(r for r in models["model"] if r["id"] == rid)


def test(doc: dict, tid: str, model: str | None = None, segment: str | None = None) -> dict:
    return next(t for t in doc["tests"] if t["test_id"] == tid and (model is None or t["model_id"] == model)
                and (segment is None or t["segment"] == segment))


def num(x: float, d: int = 3) -> str:
    return f"{x:,.{d}f}".replace(",", "{,}") if abs(x) >= 1000 else f"{fixed(x, d)}"


# ---------------------------------------------------------------------------------------------------------------------
# C06: the lifetime PD rungs and the PC-Hazard network


def tables_c06() -> None:
    rows_fit, rows_rungs, rows_s4, rows_ecl, rows_sicr = [], [], [], [], []
    holds_all, ibs_gap, gap_gap = [], [], []
    for d in DATES:
        m, v = c06m(d), c06(d)
        p = rung(m, "L3-pch")
        tr = p["details"]["training"]
        ev = p["details"]["evaluation"]
        rows_fit.append([d, int(p["parameters"]["n_loans"]["value"]),
                         int(p["parameters"]["n_defaults"]["value"]), tr["train_loans"], tr["holdout_loans"], tr["epochs_run"],
                         tr["best_epoch"], tr["train_nll_per_default"], tr["holdout_nll_per_default"]])
        comp = {r["rung_id"]: r for r in v["outputs"]["rung_comparison"]}
        rows_rungs.append([d, comp["L0-km"]["integrated_brier"], comp["L1-dth"]["integrated_brier"],
                           comp["L2-cox"]["integrated_brier"], comp["L3-pch"]["integrated_brier"],
                           comp["L1-dth"]["c_index"], comp["L2-cox"]["c_index"], comp["L3-pch"]["c_index"]])
        g = ev["mean_abs_decile_gap_aalen_johansen"]
        crit = ev["criteria"]
        rows_s4.append([d, ev["integrated_brier"]["cox"], ev["integrated_brier"]["pch"], g["cox_mean"], g["pch_mean"],
                        "yes" if ev["holds_at_date"] else "no"])
        holds_all.append(bool(ev["holds_at_date"]))
        ibs_gap.append(ev["integrated_brier"]["pch"] - ev["integrated_brier"]["cox"])
        gap_gap.append(g["pch_mean"] - g["cox_mean"])
        so = v["outputs"]["stage_summary"]["rows"]
        s1, s2 = so[0], so[1]
        imp = v["impact"]
        rows_ecl.append([d, s1["ecl"] / 1e6, s2["ecl"] / 1e6, imp["ecl_total"]["value"] / 1e6, imp["coverage"]["value"] * 100,
                         imp["stage2_share"]["value"] * 100, f"{fixed(imp['nl_index']['value'], 4)}", imp["ecl_backtest_ratio"]["value"]])
        sic = test(v, "ifrs9.sicr_effectiveness")
        x = sic["extras"]
        if sic["metric"] is None:
            rows_sicr.append([d, None, None, None, None, None, None])
        else:
            rows_sicr.append([d, x["default_rate_stage1"] * 100, x["default_rate_stage2"] * 100, sic["metric"],
                              f"[{fixed(x['metric_interval'][0], 2)}, {fixed(x['metric_interval'][1], 2)}]", x["roc_auc"],
                              f"[{fixed(x['roc_auc_interval'][0], 3)}, {fixed(x['roc_auc_interval'][1], 3)}]"])
    cp = [rung(c06m(d), "L3-pch")["details"]["evaluation"]["c_index"] for d in DATES]
    macro("CindexPchMin", f"{fixed(min(c['pch'] for c in cp), 2)}")
    macro("CindexPchMax", f"{fixed(max(c['pch'] for c in cp), 2)}")
    macro("CindexCoxMin", f"{fixed(min(c['cox'] for c in cp), 2)}")
    macro("CindexCoxMax", f"{fixed(max(c['cox'] for c in cp), 2)}")
    macro("DatesHold", str(sum(holds_all)))
    macro("DatesTotal", str(len(holds_all)))
    macro("PbsWorseMax", f"{fixed(max(ibs_gap), 5)}")
    macro("PbsBetterMax", f"{fixed(-min(ibs_gap), 5)}")
    macro("GapBetterMax", f"{fixed(-min(gap_gap), 4)}")
    macro("HoldDates", ", ".join(d for d, h in zip(DATES, holds_all) if h))
    macro("FailDates", ", ".join(d for d, h in zip(DATES, holds_all) if not h))
    first = c06m(DATES[0])
    macro("NetParams", str(int(rung(first, "L3-pch")["parameters"]["network_parameters"]["value"])))
    arch = rung(first, "L3-pch")["details"]["architecture"]
    macro("NetInputs", str(arch["inputs"]))
    macro("NetOutputs", str(arch["outputs"]))
    macro("NetHidden", str(arch["hidden"][0]))
    macro("FollowShort", f"{fixed(min(rung(c06m(d), 'L3-pch')['details']['evaluation']['follow_up_months'] for d in DATES), 0)}")
    macro("FollowLong", f"{fixed(max(rung(c06m(d), 'L3-pch')['details']['evaluation']['follow_up_months'] for d in DATES), 0)}")
    h = c06m("2010-12")
    l1 = rung(h, "L1-dth")["details"]
    macro("DthCells", num(l1["cells"], 0))
    macro("DthLoans", num(int(rung(h, "L1-dth")["parameters"]["n_loans"]["value"]), 0))
    macro("CleanLoans", num(int(l1["cleaning"]["loans-kept"]), 0))
    macro("DthCoef", str(len(next(e for e in h["fit"]["ladder"] if e["rung_id"] == "L1-dth")["coefficients"])))
    macro("CoxCoef", str(len(next(e for e in h["fit"]["ladder"] if e["rung_id"] == "L2-cox")["coefficients"])))
    macro("LossRho", f"{fixed(h['fit']['pit']['rho'], 2)}")
    macro("Lgdbands", str(len(h["fit"]["lgd"]["segments"])))

    figkit.table(OUT / "provisions-t-pch-fit.tex",
                 ["Reporting date", "Loans", "Defaults", "Training loans", "Hold-out loans", "Epochs run", "Best epoch",
                  "Training NLL", "Hold-out NLL"], rows_fit,
                 caption=("The PC-Hazard network fitted at each of the six reporting dates of case C06 on the SBA 7(a) loans as known at the "
                          "date: the loans and defaults of the fit, the split into training and hold-out loans, the epochs run before early "
                          "stopping, the epoch of the lowest hold-out loss and the negative log-likelihood per training default on each part."),
                 label="tab:prov-pch-fit", digits=3, align="lrrrrrrrr", wide=True)
    figkit.table(OUT / "provisions-t-rungs.tex",
                 ["Date", "PBS KM", "PBS DTH", "PBS Cox", "PBS PCH", "C DTH", "C Cox", "C PCH"], rows_rungs,
                 caption=("Pooled Brier score (PBS, the mean over the observed horizons of 6 to 36 months of the Brier term of the pooled "
                          "predicted against the pooled observed cumulative default; it equals the observed variance plus the squared gap "
                          "between the two, so it measures calibration in the large and carries no ranking information) of the four lifetime PD rungs, Kaplan-Meier (KM), "
                          "discrete-time hazard (DTH), Cox and PC-Hazard (PCH), and the c-index of the 12-month PD of the three rungs that rank "
                          "loans, on the loans with 36 months of contractual life left, per reporting date of case C06."),
                 label="tab:prov-rungs", digits=4)
    figkit.table(OUT / "provisions-t-s4.tex",
                 ["Date", "PBS Cox", "PBS PCH", "Gap Cox", "Gap PCH", "Both criteria hold"], rows_s4,
                 caption=("PC-Hazard against Cox at the six reporting dates of case C06: the pooled Brier score (PBS) and the mean absolute "
                          "gap between predicted and Aalen-Johansen observed cumulative default across the ten risk deciles at 12, 24 and 36 "
                          "months, with the last column stating whether the PC-Hazard rung has both the lower PBS and the smaller gap."),
                 label="tab:prov-s4", digits=4)
    figkit.table(OUT / "provisions-t-ecl.tex",
                 ["Date", "Stage 1 ECL", "Stage 2 ECL", "Total ECL", "Coverage (\\%)", "Stage 2 share (\\%)", "NL index", "Realised / ECL"],
                 rows_ecl,
                 caption=("Probability-weighted expected credit loss of the SBA 7(a) book at the six reporting dates of case C06, in USD "
                          "million: by stage (Stage 3 holds no balance at a date), the coverage of the gross carrying amount, the share of the "
                          "gross carrying amount in Stage 2, the non-linearity index of the scenarios and the ratio of the discounted losses realised in the "
                          "12 months after the date to the 12-month ECL."),
                 label="tab:prov-ecl", digits=3, wide=True)
    figkit.table(OUT / "provisions-t-sicr.tex",
                 ["Date", "Stage 1 default rate (\\%)", "Stage 2 default rate (\\%)", "Ratio", "Ratio interval", "ROC AUC", "AUC interval"],
                 rows_sicr,
                 caption=("Effectiveness of the Stage 2 flag in case C06: the default rate within 12 months after each reporting date of the "
                          "accounts in Stage 1 and in Stage 2, their ratio with its interval on the log scale, and the area under the ROC curve "
                          "of the flag with its interval; a dash marks a date with no account in Stage 2, where the test is not evaluated."),
                 label="tab:prov-sicr", digits=3, wide=True)

    # the battery: lights
    tests_rows = [("Lifetime PD, Kaplan-Meier", "ifrs9.lifetime_pd_backtest", "L0-km"),
                  ("Lifetime PD, discrete-time hazard", "ifrs9.lifetime_pd_backtest", "L1-dth"),
                  ("Lifetime PD, Cox", "ifrs9.lifetime_pd_backtest", "L2-cox"),
                  ("Lifetime PD, PC-Hazard", "ifrs9.lifetime_pd_backtest", "L3-pch"),
                  ("Stage 2 effectiveness", "ifrs9.sicr_effectiveness", None),
                  ("Threshold stability", "ifrs9.sicr_threshold_stability", None),
                  ("Stage migration", "ifrs9.stage_migration_backtest", None),
                  ("ECL backtest", "ifrs9.ecl_backtest", None),
                  ("Scenario sensitivity", "ifrs9.scenario_sensitivity", None),
                  ("Non-linearity", "ifrs9.nonlinearity", None),
                  ("Overlay diagnostics", "ifrs9.overlay_diagnostics", None),
                  ("Reconciliation identities", "ifrs9.reconciliation_identities", None)]
    docs = {d: c06(d) for d in DATES}
    rows = []
    n_red = 0
    for label, tid, mid in tests_rows:
        row = [label]
        for d in DATES:
            seg = "all" if tid == "ifrs9.lifetime_pd_backtest" else None
            t = test(docs[d], tid, mid, seg)
            row.append(LIGHT[t["light"]])
            n_red += t["light"] == "red"
        rows.append(row)
    macro("BatteryRed", str(n_red))
    macro("BatteryCells", str(len(tests_rows) * len(DATES)))
    figkit.table(OUT / "provisions-t-battery.tex", ["Test"] + DATES, rows,
                 caption=("Traffic lights of the nine tests of the IFRS 9 validation battery on the six reporting dates of case C06 (G green, A "
                          "amber, R red, n/e not evaluated); the lifetime PD test is shown for each of the four rungs on all origination cohorts "
                          "pooled, and the lights are the acceptance gates of the engine, not regulatory thresholds."),
                 label="tab:prov-battery", align="lcccccc")
    d10 = docs["2010-12"]
    macro("StageTwoShareTen", f"{percent(d10['impact']['stage2_share']['value'], 1)}")
    d20 = docs["2020-06"]
    macro("StageTwoShareTwenty", f"{percent(d20['impact']['stage2_share']['value'], 1)}")
    macro("RatioTwenty", f"{fixed(d20['impact']['ecl_backtest_ratio']['value'], 3)}")
    macro("RatioTen", f"{fixed(d10['impact']['ecl_backtest_ratio']['value'], 3)}")
    macro("NlTen", f"{fixed(d10['impact']['nl_index']['value'], 4)}")
    macro("NlMax", f"{fixed(max(docs[d]['impact']['nl_index']['value'] for d in DATES), 4)}")
    macro("NlPositive", str(sum(docs[d]["impact"]["nl_index"]["value"] > 0 for d in DATES)))
    macro("LevelTen", f"{percent(d10['impact']['ecl_stage2']['value'] / d10['impact']['ecl_total']['value'], 1)}")
    macro("WrongOrder", str(sum(any(f["id"] == "F-SCENARIO-ORDER" for f in docs[d]["findings"]) for d in DATES)))
    macro("MigrationRed", str(sum(test(docs[d], "ifrs9.stage_migration_backtest")["light"] == "red" for d in DATES)))
    macro("NoStageTwo", str(sum(docs[d]["impact"]["ecl_stage2"]["value"] == 0 for d in DATES)))
    macro("AllocBnTen", f"{fixed(d10['impact']['ecl_total']['value'] / 1e9, 2)}")
    macro("AllocBnTwenty", f"{fixed(d20['impact']['ecl_total']['value'] / 1e9, 2)}")
    macro("LifetimeGapTen", f"{percent(test(d10, 'ifrs9.lifetime_pd_backtest', 'L1-dth', 'all')['metric'], 1)}")
    macro("LifetimeGapTwenty", f"{percent(test(d20, 'ifrs9.lifetime_pd_backtest', 'L1-dth', 'all')['metric'], 1)}")
    macro("LifetimeGapPchTen", f"{percent(test(d10, 'ifrs9.lifetime_pd_backtest', 'L3-pch', 'all')['metric'], 1)}")
    macro("LifetimeGapPchTwenty", f"{percent(test(d20, 'ifrs9.lifetime_pd_backtest', 'L3-pch', 'all')['metric'], 1)}")
    macro("SicrRatioTen", f"{fixed(test(d10, 'ifrs9.sicr_effectiveness')['metric'], 2)}")
    macro("EligTen", num(rung(c06m("2010-12"), "L3-pch")["details"]["evaluation"]["eligible_accounts"], 0))
    macro("DefTen", num(rung(c06m("2010-12"), "L3-pch")["details"]["evaluation"]["defaults_followed"], 0))
    macro("ReconMax", f"{sci(max(test(docs[d], 'ifrs9.reconciliation_identities')['metric'] for d in DATES))}")
    macro("ScenWeights", ", ".join(f"{fixed(s['weight'], 2)}" for s in d10["outputs"]["scenarios"]))
    macro("RhoUsed", f"{fixed(d10['outputs']['non_linearity']['parameters']['rho'], 2)}")


def curve_and_decile_macros() -> None:
    import statistics

    m = c06m("2010-12")
    names = {"L0-km": "Km", "L1-dth": "Dth", "L2-cox": "Cox", "L3-pch": "Pch"}
    for e in m["fit"]["ladder"]:
        macro("BaseEnd" + names[e["rung_id"]], f"{percent(e['baseline']['cumulative_pd'][-1], 1)}")
        macro("BaseMonth" + names[e["rung_id"]], str(e["baseline"]["months"][-1]))
    words = {12: "Twelve", 24: "TwentyFour", 36: "ThirtySix"}
    counts = []
    for rid, tag in (("L2-cox", "Cox"), ("L3-pch", "Pch")):
        for k, w in words.items():
            errs = []
            for d in DATES:
                p = rung(c06m(d), rid)
                for row in p["details"]["decile_calibration"]:
                    if row["months"] == k and row["observed_aalen_johansen"]:
                        errs.append(abs(row["predicted_cumulative_pd"] / row["observed_aalen_johansen"] - 1.0))
            macro(f"DecMed{tag}{w}", f"{percent(statistics.median(errs), 0)}")
            counts.append(len(errs))
    macro("DecPointsMin", str(min(counts)))
    macro("DecPointsMax", str(max(counts)))


# ---------------------------------------------------------------------------------------------------------------------
# the worked example of the non-linearity, from the engine


def worked_example() -> None:
    import numpy as np
    from riskvalidation.provisions import ecl as rv_ecl
    from riskvalidation.provisions import term_structure as ts

    z = np.array([1.0, 0.0, -2.0])
    w = np.array([0.25, 0.5, 0.25])
    pit = ts.ttc_to_pit(0.02, 0.12, z)
    weighted = float(ts.weighted_pit_pd(0.02, 0.12, z, w))
    zbar = float(w @ z)
    at_mean = float(ts.ttc_to_pit(0.02, 0.12, np.array([zbar]))[0])
    nl = float(rv_ecl.non_linearity_index(0.4 * weighted, 0.4 * at_mean))
    gh = float(ts.gauss_hermite_pit_pd(0.02, 0.12, 64))
    macro("WxPitUp", f"{percent(pit[0], 3)}")
    macro("WxPitMid", f"{percent(pit[1], 3)}")
    macro("WxPitDown", f"{percent(pit[2], 3)}")
    macro("WxWeighted", f"{percent(weighted, 3)}")
    macro("WxAtMean", f"{percent(at_mean, 3)}")
    macro("WxZbar", f"{fixed(zbar, 2)}")
    macro("WxRatio", f"{fixed(weighted / at_mean, 2)}")
    macro("WxIndex", f"{fixed(nl, 3)}")
    macro("WxGh", f"{fixed(gh, 4)}")
    macro("WxLossWeighted", f"{percent(0.4 * weighted, 2)}")
    macro("WxLossMean", f"{percent(0.4 * at_mean, 2)}")
    # discount factors of the golden example of the engine documentation, mid-period at 6 per cent
    df = rv_ecl.discount_factors(np.array([0.06]), np.array([3, 6]), "mid-period")
    macro("WxDfOne", f"{fixed(df[0, 0], 6)}")
    macro("WxDfTwo", f"{fixed(df[0, 1], 6)}")
    # the golden ECL: q = (0.01, 0.01) on months 6 and 12, LGD 0.4, EAD 100000, r = 0
    q = np.array([[0.01, 0.01]])
    e12 = rv_ecl.ecl_scenario(q, np.array([0.4]), np.array([[100000.0, 100000.0]]), np.array([0.0]), np.array([6, 12]), 12,
                              "mid-period")
    macro("WxGoldenEcl", f"{fixed(float(e12[0]), 1)}")
    # the term-structure identity: constant hazard 0.01 on months 3 and 6
    t = ts.from_hazard(np.array([0.01, 0.01]), np.array([3, 6]))
    macro("WxCumTwo", f"{fixed(float(t.cumulative[1]), 4)}")


# ---------------------------------------------------------------------------------------------------------------------
# C07: the three regimes, the statutory tables as the engine holds them


def tables_c07() -> None:
    import numpy as np  # noqa: F401
    from riskvalidation.provisions import local_cl as cl
    from riskvalidation.provisions import local_es as es

    rows, totals = [], {}
    for s in SCENARIOS:
        d = figkit.doc(f"C07/{s}.json")
        imp = d["impact"]
        b1, i9, bd = (imp[k]["value"] / 1e9 for k in ("provision_cmf_b1", "provision_ifrs9", "provision_bde"))
        rows.append([SCEN_LABEL[s], b1, i9, bd, i9 / b1, bd / b1])
        totals[s] = (b1, i9, bd)
    figkit.table(OUT / "provisions-t-c07.tex", ["Scenario", "CMF B-1", "IFRS 9", "BdE Annex 9", "IFRS 9 / B-1", "BdE / B-1"], rows,
                 caption=("Provision of the synthetic bank Banco Andino under the three regimes in the six scenarios of case C07, in CLP "
                          "billion: the CMF B-1 comparable total, the probability-weighted IFRS 9 expected credit loss with overlays and the "
                          "Banco de Espana Annex 9 coverage, with the ratios of the last two to the first; the bank is synthetic, calibrated to "
                          "CMF aggregates."),
                 label="tab:prov-c07", digits=3)
    base = figkit.doc("C07/base.json")
    o = base["outputs"]
    macro("SevenBaseB", f"{fixed(totals['base'][0], 1)}")
    macro("SevenBaseI", f"{fixed(totals['base'][1], 1)}")
    macro("SevenBaseD", f"{fixed(totals['base'][2], 1)}")
    macro("SevenRatioI", f"{percent(totals['base'][1] / totals['base'][0], 0)}")
    macro("SevenRatioD", f"{percent(totals['base'][2] / totals['base'][0], 0)}")
    macro("SevenSevereB", f"{fixed(totals['combined-severe'][0], 1)}")
    macro("SevenSevereI", f"{fixed(totals['combined-severe'][1], 1)}")
    macro("SevenSevereD", f"{fixed(totals['combined-severe'][2], 1)}")
    macro("SevenSevereGrowthB", f"{percent((totals['combined-severe'][0] / totals['base'][0] - 1), 1)}")
    macro("SevenSevereGrowthI", f"{percent((totals['combined-severe'][1] / totals['base'][1] - 1), 1)}")
    macro("SevenSevereGrowthD", f"{percent((totals['combined-severe'][2] / totals['base'][2] - 1), 1)}")
    segs = o["portfolio"]["segments"]
    macro("SevenAccounts", num(sum(s["accounts"] for s in segs), 0))
    macro("SevenExposureTn", f"{fixed(sum(s['gross_exposure'] for s in segs) / 1e12, 2)}")
    macro("SevenMin", f"{percent(o['b1_detail']['minimum_check']['minimum_rate'], 2)}")
    macro("SevenMinAmount", f"{fixed(o['b1_detail']['minimum_check']['minimum_amount'] / 1e9, 2)}")
    macro("SevenMinProv", f"{fixed(o['b1_detail']['minimum_check']['normal_portfolio_provision_before_minimum'] / 1e9, 2)}")
    macro("SevenOverlayShare", f"{percent(base['tests'][7]['metric'], 2)}" if base["tests"][7]["test_id"] == "ifrs9.overlay_diagnostics" else "")
    macro("SevenSicrRatio", f"{fixed([t for t in base['tests'] if t['test_id'] == 'ifrs9.sicr_effectiveness'][0]['metric'], 2)}")
    macro("SevenNlBase", f"{percent([t for t in base['tests'] if t['test_id'] == 'ifrs9.scenario_sensitivity'][0]['metric'], 1)}")
    steps = o["gap_bridge"]["steps"]
    macro("BridgeBasis", f"{fixed(steps[0]['amount'] / 1e9, 1)}")
    macro("BridgeLife", f"{fixed(steps[1]['amount'] / 1e9, 1)}")
    macro("BridgeWeight", f"{fixed(steps[2]['amount'] / 1e9, 1)}")
    macro("BridgeDisc", f"{fixed(steps[3]['amount'] / 1e9, 1)}")
    macro("BridgeOverlay", f"{fixed(steps[5]['amount'] / 1e9, 2)}")
    macro("BridgeTotal", f"{fixed(base['impact']['gap_ifrs9_minus_b1']['value'] / 1e9, 1)}")
    macro("BridgeSum", f"{fixed(sum(s['amount'] for s in steps) / 1e9, 1)}")
    names = {s["segment_id"]: s["label"]["en"] for s in o["portfolio"]["segments"]}
    rows = [[names[s["segment_id"]], s["cmf_b1_provision"] / 1e9, s["ifrs9_provision"] / 1e9, s["bde_annex9_provision"] / 1e9]
            for s in o["comparison"]["rows"]]
    figkit.table(OUT / "provisions-t-c07-seg.tex", ["Segment", "CMF B-1", "IFRS 9", "BdE Annex 9"], rows,
                 caption=("Provision by segment of Banco Andino in the base scenario of case C07 under the three regimes, in CLP billion; "
                          f"the IFRS 9 column excludes {fixed(o['comparison']['unallocated']['ifrs9_provision'] / 1e9, 2)} CLP billion of overlays that no segment carries, and the BdE column is zero where "
                          "the adjusted guarantees cover the exposure."),
                 label="tab:prov-c07-seg", digits=2)
    # stage mapping
    i9 = {r["stage"]: r for r in o["ifrs9_detail"]["stage_summary"]}
    bd = {r["mapped_stage"]: r for r in o["bde_detail"]["categories"]}
    rows = []
    for st, name in (("stage1", "Stage 1 / normal"), ("stage2", "Stage 2 / special watch"), ("stage3", "Stage 3 / doubtful")):
        rows.append([name, i9[st]["gross_carrying_amount"] / 1e9, i9[st]["ecl"] / 1e9, i9[st]["coverage"] * 100,
                     bd[st]["exposure"] / 1e9, bd[st]["provision"] / 1e9, bd[st]["coverage_rate"] * 100])
    figkit.table(OUT / "provisions-t-c07-stage.tex",
                 ["Stage or category", "IFRS 9 exposure", "IFRS 9 ECL", "Coverage (\\%)", "Annex 9 exposure", "Annex 9 provision",
                  "Coverage (\\%)"], rows,
                 caption=("The IFRS 9 stages and the Banco de Espana Annex 9 categories mapped onto them, for Banco Andino in the base "
                          "scenario of case C07: exposure and loss allowance in CLP billion and the coverage of the exposure in per cent; the "
                          "two classifications place different amounts in each stage because Annex 9 assigns a category by days past due, "
                          "forbearance and watch list."),
                 label="tab:prov-c07-stage", digits=2, wide=True)
    macro("SevenStageTwoI", f"{percent(i9['stage2']['coverage'], 1)}")
    macro("SevenStageTwoD", f"{percent(bd['stage2']['coverage_rate'], 1)}")
    macro("SevenStageThreeI", f"{percent(i9['stage3']['coverage'], 1)}")
    macro("SevenStageThreeD", f"{percent(bd['stage3']['coverage_rate'], 1)}")
    macro("SevenStageOneI", f"{percent(i9['stage1']['coverage'], 2)}")
    macro("SevenStageOneD", f"{percent(bd['stage1']['coverage_rate'], 2)}")

    # B-1 individual categories from the engine, with the base-scenario exposure and provision
    cat = {c["category_id"]: c for c in o["regimes"][0]["by_category"]}
    rows = []
    for k in ("A1", "A2", "A3", "A4", "A5", "A6", "B1", "B2", "B3", "B4"):
        pi, pdi, pe = cl.b1_individual_category(k)
        rows.append([k, pi * 100, pdi * 100, pe * 100, cat[k]["exposure"] / 1e9, cat[k]["provision"] / 1e9,
                     cat[k]["provision"] / cat[k]["exposure"] * 100])
    figkit.table(OUT / "provisions-t-b1.tex",
                 ["Category", "PI (\\%)", "PDI (\\%)", "PE (\\%)", "Exposure", "Provision", "Applied rate (\\%)"], rows,
                 caption=("The ten individual-assessment categories of CMF Chapter B-1 as the engine holds them (probability of default PI, "
                          "loss given default PDI and the provision factor PE = PI x PDI, in per cent) and the exposure and provision of Banco "
                          "Andino in each, in CLP billion, in the base scenario of case C07; the applied rate is below PE where the guarantor "
                          "category replaces the debtor category on the guaranteed part."),
                 label="tab:prov-b1", digits=3, wide=True)
    macro("SevenAFourRate", f"{percent(cat['A4']['provision'] / cat['A4']['exposure'], 2)}")
    macro("SevenIndividualCount", str(len(cat) - 5))

    # reproduction of the statutory tables: every cell through the public functions
    fam = []
    dev = 0.0
    n = 0
    for pvg in (0.2, 0.6, 0.85, 0.95):
        for b in ("0", "1-29", "30-59", "60-89", "default"):
            pi, pdi, pe = cl.b1_mortgage_pe(pvg, b)
            dev = max(dev, abs(pe - pi * pdi))
            n += 1
    fam.append(["Residential mortgages", n, dev])
    n, dev = 0, 0.0
    for re_ in (True, False):
        for pvb in (0.3, 0.45, 0.7, 0.85, 0.95):
            for b in ("0", "1-29", "30-59", "60-89", "default"):
                pi, pdi, pe = cl.b1_leasing_pe(pvb, b, re_)
                dev = max(dev, abs(pe - pi * pdi))
                n += 1
    fam.append(["Commercial leasing", n, dev])
    n, dev = 0, 0.0
    for sch in ("CAE", "CORFO"):
        for b in ("0", "1-29", "30-59", "60-89", "default", "not-due"):
            pi, pdi, pe = cl.b1_student_loan_pe(sch, b)
            dev = max(dev, abs(pe - pi * pdi))
            n += 1
    fam.append(["Student loans", n, dev])
    n, dev = 0, 0.0
    for rec in (False, True):
        for ptvg in (0.5, 0.7, 0.85, 0.95, None):
            for b in ("0", "1-29", "30-59", "60-89", "default"):
                pi, pdi, pe = cl.b1_commercial_pe(b, ptvg, rec)
                dev = max(dev, abs(pe - pi * pdi))
                n += 1
    fam.append(["Generic commercial and factoring", n, dev])
    n, dev = 0, 0.0
    for dpd in (3, 20, 45, 75):
        for mort in (True, False):
            for arr in (False, True):
                for prod in ("leasing-auto", "instalment", "cards-lines-other"):
                    pi, pdi, pe = cl.b1_consumer_pe(dpd, mort, arr, prod)
                    dev = max(dev, abs(pe - pi * pdi))
                    n += 1
    fam.append(["Consumer loans", n, dev])
    macro("ConsumerPiCells", str(4 * 4))
    macro("MortgageCells", str(fam[0][1]))
    figkit.table(OUT / "provisions-t-b1check.tex", ["Table family", "Cells evaluated", "Largest |PE - PI x PDI|"], fam,
                 caption=("Check of the identity PE = PI x PDI over the cells of each standard-method table of CMF Chapter B-1, evaluated "
                          "through the public functions of the engine at one value in each bucket: the number of cells evaluated and the "
                          "largest absolute difference between the provision factor the engine returns and the product of its two parameters, "
                          "as a decimal; the mortgage table carries transcribed provision factors that agree to its own rounding."),
                 label="tab:prov-b1-check", digits=7)
    macro("MortgageDev", f"{sci(fam[0][2])}")
    macro("OtherDev", f"{max(f[2] for f in fam[1:]):.1e}")

    # the Annex 9 coverage tables
    rows = []
    segs_es = ["A.1.1", "A.1.2", "A.1.3", "A.2.1", "A.2.2", "A.2.3", "B.1.1", "B.1.2", "B.1.3", "B.2", "B.2.1", "B.3"]
    for sg in segs_es:
        rows.append([sg, es.annex9_normal_coverage(sg, "normal") * 100, es.annex9_normal_coverage(sg, "normal-special-watch") * 100]
                    + [es.annex9_doubtful_coverage(sg, dd) * 100 for dd in (120, 220, 300, 400, 500, 600, 700)])
    figkit.table(OUT / "provisions-t-annex9.tex",
                 ["Segment", "Normal", "Special watch", "90 d--6 m", "6--9 m", "9--12 m", "12--15 m", "15--18 m", "18--21 m", "$>$21 m"],
                 rows,
                 caption=("Annex 9 coverage of the uncovered amount in per cent as the engine returns it: point 144 for normal risk and for "
                          "normal risk under special watch, and point 140 for doubtful risk by the age of the oldest past-due amount (the "
                          "bucket reached at 120, 220, 300, 400, 500, 600 and 700 days); the segments run from A.1.1 construction to B.3 other "
                          "purposes."),
                 label="tab:prov-annex9", digits=1, wide=True)
    macro("AnnexSegments", str(len(segs_es)))


# ---------------------------------------------------------------------------------------------------------------------
# C03: the vintages of the same file


def tables_c03() -> None:
    rows = []
    obs = []
    for f in ("fy2006-07", "fy2008-10", "fy2011-14", "fy2015-17", "fy2018-20"):
        d = figkit.doc(f"C03/{f}.json")
        for r in d["outputs"]["vintage_summary"]["rows"]:
            if r["mark_observed"]:
                obs.append((r["fiscal_year"], r["observed_5y_pd"], r["n"]))
    obs = sorted(set(obs))
    hi = max(obs, key=lambda x: x[1])
    lo = min(obs, key=lambda x: x[1])
    macro("VintageHighYear", str(hi[0]))
    macro("VintageHigh", f"{percent(hi[1], 1)}")
    macro("VintageLowYear", str(lo[0]))
    macro("VintageLow", f"{percent(lo[1], 1)}")
    macro("VintageCount", str(len(obs)))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tables_c06()
    curve_and_decile_macros()
    worked_example()
    tables_c07()
    tables_c03()
    fit_width()
    lines = ["% Numbers quoted by sections/08-provisions.tex, written by tables/make_provisions.py from data/derived and the engine."]
    for k, v in sorted(MACROS.items()):
        lines.append(f"\\newcommand{{\\pv{k}}}{{{v}}}")
    (OUT / "provisions-numbers.tex").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {len(MACROS)} numbers and the tables to {OUT}")


if __name__ == "__main__":
    main()
