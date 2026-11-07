"""Write every results table of the manuscript from the committed experiment outputs.

    python manuscripts/e-process-sequential-monitors/make_tables.py

Tables land in ``tables/`` as booktabs ``.tex`` files that the sections ``\\input``; no number in them is typed by hand.
The sources are ``experiments/results_*.json`` (this manuscript's experiment scripts) and, for the agreement table, the
product's committed document ``data/derived/C22/other-families.json``.
"""
from __future__ import annotations

import json
import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_shared"))
import figkit  # noqa: E402

EXP = HERE / "experiments"
OUT = HERE / "tables"


def load(name: str) -> dict:
    return json.loads((EXP / name).read_text(encoding="utf-8"))


H = load("results_hits.json")
X3 = load("results_x3_seeds.json")
AB = load("results_ablation.json")
PC = load("results_pd_correlation.json")
C11 = load("results_c11.json")
C03 = load("results_c03.json")
TH = load("results_theory.json")
MT = load("results_matched.json")
PDC = load("results_pd_comparators.json")
C22 = json.loads((figkit.DERIVED / "C22" / "other-families.json").read_text(encoding="utf-8"))["outputs"]["sequential"]


# ---------------------------------------------------------------------------------------------------------------------
# cell formatting

def raw(s: str) -> str:
    """A cell that carries LaTeX: figkit.table leaves a string that starts with a backslash as it is."""
    return "\\relax " + s


def pc(x: float, d: int = 1) -> str:
    return f"{100 * x:.{d}f}"


def pci(m: dict, key: str = "ever") -> str:
    lo, hi = m[f"{key}_ci"]
    return raw(f"{pc(m[key])} [{pc(lo)}, {pc(hi)}]")


def day(v: float | None, horizon: int = 1000) -> str:
    return f"$>${horizon:,}" if v is None else f"{v:.0f}"


def med(m: dict, horizon: int = 1000) -> str:
    lo, hi = m["median_ci"]
    if m["median_day"] is None:
        return raw(f"$>${horizon:,}")
    return raw(f"{m['median_day']:.0f} [{day(lo, horizon)}, {day(hi, horizon)}]")


def sc(sid: str) -> dict:
    return H["scenarios"][sid]["methods"]


RULES = [
    ("e_rate", "Rate e-process, two-sided (proposed)"),
    ("e_rate_upper", "Rate e-process, upper side (proposed)"),
    ("e_sprt3", "Single alternative, $3\\alpha$ (likelihood-ratio e-process)"),
    ("e_battery", "Rate and clustering e-processes, averaged (proposed)"),
    ("e_wwz", "E-backtest of Wang, Wang and Ziegel (2022)"),
    ("e_beta", "Uniform-prior Bayes factor"),
    ("kupiec_trailing", "Kupiec, last 250 days, read daily"),
    ("kupiec_cumulative", "Kupiec, all days so far, read daily"),
    ("traffic_light", "Basel traffic light, read daily"),
    ("kupiec_sidak", "Kupiec, all days so far, Sidak level"),
    ("kupiec_calibrated", "Kupiec, all days so far, simulated critical value"),
    ("cusum_calibrated", "CUSUM against $3\\alpha$, simulated threshold"),
]


def t_main() -> None:
    rows = []
    for key, label in RULES:
        n, x3, x4 = sc("null")[key], sc("rate-x3")[key], sc("rate-x4")[key]
        rows.append([raw(label), pci(n), pci(x3, "by"), med(x3), pci(x4, "by"), med(x4)])
    n_reps = H["meta"]["reps"]
    bound = 0.05 + 3 * math.sqrt(0.05 * 0.95 / n_reps)
    figkit.table(
        OUT / "main-results.tex",
        ["Rule", "Size, \\%", "Power by day 250, \\% (x3)", "Median day (x3)", "Power by day 250, \\% (x4)", "Median day (x4)"],
        rows, align="p{5.6cm}rrrrr", wide=True, label="tab:main-results",
        caption=(f"Every rule read every day on {n_reps:,} streams of 1,000 days from the generator of known truth at a VaR level of 1\\,\\%: "
                 "size is the share of correct-model streams rejected at some day, power by day 250 the share of streams with a hit rate three (x3) "
                 "or four (x4) times too high rejected by day 250, and the median day is the median first-rejection day over all streams "
                 "(the symbol $>$ marks a median beyond the horizon). Brackets are 95\\,\\% Wilson intervals for shares and 95\\,\\% bootstrap "
                 f"intervals for medians. The anytime bound for a size of 5\\,\\% plus three Monte Carlo standard errors is {pc(bound)}\\,\\%."))


def t_clustering() -> None:
    cols = [("null", "Correct model"), ("cluster-0.1", "$q=0.1$"), ("cluster-0.2", "$q=0.2$"), ("cluster-0.4", "$q=0.4$")]
    keys = [("e_cluster", "Clustering e-process (proposed)"), ("e_battery", "Rate and clustering, averaged (proposed)"),
            ("e_rate", "Rate e-process (proposed)"), ("independence_trailing", "Christoffersen independence, last 250 days, read daily"),
            ("kupiec_trailing", "Kupiec, last 250 days, read daily"), ("traffic_light", "Basel traffic light, read daily"),
            ("kupiec_calibrated", "Kupiec, all days so far, simulated critical value")]
    rows = [[raw(label)] + [pci(sc(sid)[key]) for sid, _ in cols] for key, label in keys]
    figkit.table(
        OUT / "clustering.tex", ["Rule"] + [raw(c) for _, c in cols], rows, align="p{6.2cm}rrrr", wide=True, label="tab:clustering",
        caption=("Share of 1,000-day streams rejected at some day, in percent, when the hit rate is right (1\\,\\%) and a hit follows a hit with "
                 "probability $q$ (0.1, 0.2, 0.4), for the proposed clustering monitors, the rate monitor and the fixed-window tests read daily. "
                 f"{H['meta']['reps']:,} streams per column; brackets are 95\\,\\% Wilson intervals. The first column is the size of each rule, "
                 "the other three the power against clustering."))


def t_x3() -> None:
    rows = []
    for name, lab in (("x3", "Two-sided, 3"), ("x4", "Two-sided, 4"), ("x3_upper", "Upper side, 3"), ("x4_upper", "Upper side, 4")):
        f = X3["factors"][name]
        lo, hi = f["pooled_median_ci"]
        rows.append([raw(f"{lab}"), f"{f['seed_median_mean']:.1f}", f"{f['seed_median_sd']:.1f}",
                     raw(f"{pc(f['share_of_seeds_below_window'], 0)}"), raw(f"{f['pooled_median']:.1f} [{lo:.0f}, {hi:.0f}]"),
                     f"{f['pooled_traffic_light_median']:.0f}",
                     raw(f"{100 * f['pooled_power_cost']:.1f} $\\pm$ {100 * f['pooled_power_cost_se']:.1f}"),
                     raw(f"{100 * f['seed_power_cost_mean']:.1f} $\\pm$ {100 * f['seed_power_cost_sd']:.1f}")])
    s = X3["meta"]
    figkit.table(
        OUT / "x3-seeds.tex",
        ["Monitor, hit-rate factor", "Mean of seed medians", "SD of seed medians", "Seeds with median below 250, \\%",
         "Pooled median [95\\% CI]", "Traffic-light median", "Power cost, points ($\\pm$ SE)", "Per-seed power cost, points ($\\pm$ SD)"],
        rows, align="rrrrrrrr", wide=True, label="tab:x3-seeds",
        caption=(f"The two-sided and the upper-side rate e-process at a hit rate three and four times too high on {s['seeds']} independent seed sequences of {s['reps']:,} streams "
                 f"({s['seeds'] * s['reps']:,} streams per factor): the median first-rejection day of each seed with its mean and standard deviation, "
                 "the share of seeds whose median is below the 250-day window, the median of the pooled streams with a bootstrap interval, the "
                 "traffic-light median, and the power cost, the Kupiec power of one reading at day 250 minus the e-process power by day 250, "
                 "pooled with its standard error and per seed with its standard deviation."))


def verdict_word(ok: bool) -> str:
    return "Held" if ok else "Not met"


def t_hypotheses() -> None:
    n = H["meta"]["reps"]
    bound = 0.05 + 3 * math.sqrt(0.05 * 0.95 / n)
    null = sc("null")
    x3, x4 = X3["factors"]["x3"], X3["factors"]["x4"]
    u3, u4 = X3["factors"]["x3_upper"], X3["factors"]["x4_upper"]
    size_ok = null["e_rate"]["ever"] <= bound and min(null["kupiec_trailing"]["ever"], null["kupiec_cumulative"]["ever"]) > bound
    d3 = x3["pooled_median_ci"][1] < 250 and x3["pooled_median"] < x3["pooled_traffic_light_median"]
    d4 = x4["pooled_median_ci"][1] < 250 and x4["pooled_median"] < x4["pooled_traffic_light_median"]
    c3, c4 = x3["pooled_power_cost"] < 0.10, x4["pooled_power_cost"] < 0.10
    # the refutation clause as the design states it: the real windows only (the equity 2007 to 2009 and the foreign-exchange 2008 windows)
    real_fires = not all(float(C11_E[w]) < float(C11_L[w]) for w in ("equity-2007-09", "fx-2008"))
    holds_as_stated = size_ok and d3 and d4 and c3 and c4 and not real_fires
    rho3 = next(r for r in PC["rows"] if r["rho"] == 0.03)
    over = rho3["e_average"]["ever"] > bound and rho3["e_product"]["ever"] > bound
    eq = PDC["equal_size_chi2"]["scenarios"]
    abl = AB["pd_combine"]
    chi_more = all(eq[c]["chi2_sim"]["ever"] > abl[c]["average"]["ever"] for c in ("all-x1.05", "all-x1.1"))
    u_ok = (u3["pooled_median_ci"][1] < 250 and u3["pooled_power_cost"] < 0.10 and u4["pooled_median_ci"][1] < 250 and u4["pooled_power_cost"] < 0.10)

    def span(text: str) -> list[str]:
        return ["\\multicolumn{3}{l}{\\textit{" + text + "}}"]

    rows = [
        span("Stated before the experiments"),
        [raw("Size (H1): the e-process rejects a correct VaR in at most $5\\,\\%$ plus three standard errors of the streams, read daily over 1,000 days, "
             "where the repeated Kupiec rule exceeds that"),
         raw(f"e-process {pc(null['e_rate']['ever'])}\\,\\%; Kupiec last 250 days {pc(null['kupiec_trailing']['ever'])}\\,\\%, all days "
             f"{pc(null['kupiec_cumulative']['ever'])}\\,\\%; bound {pc(bound)}\\,\\%"), verdict_word(size_ok)],
        [raw("Delay (H2): the median detection day is below the 250-day window, and below the traffic light's, at a hit rate three and four times too high"),
         raw(f"x3: pooled median {x3['pooled_median']:.0f} [{x3['pooled_median_ci'][0]:.0f}, {x3['pooled_median_ci'][1]:.0f}] "
             f"(traffic light {x3['pooled_traffic_light_median']:.0f}); {pc(x3['share_of_seeds_below_window'], 0)}\\,\\% of seeds below 250. "
             f"x4: {x4['pooled_median']:.0f} [{x4['pooled_median_ci'][0]:.0f}, {x4['pooled_median_ci'][1]:.0f}] (traffic light {x4['pooled_traffic_light_median']:.0f})"),
         raw(f"x3: {verdict_word(d3).lower()}; x4: {verdict_word(d4).lower()}")],
        [raw("Power cost (H3): one Kupiec reading at day 250 has less than 10 points more power than the e-process has by day 250"),
         raw(f"x3: {100 * x3['pooled_power_cost']:.1f} $\\pm$ {100 * x3['pooled_power_cost_se']:.1f} points; "
             f"x4: {100 * x4['pooled_power_cost']:.1f} $\\pm$ {100 * x4['pooled_power_cost_se']:.1f} points"),
         raw(f"x3: {verdict_word(c3).lower()}; x4: {verdict_word(c4).lower()}")],
        [raw("Refutation clause (R), as the design states it: the hypothesis is refuted if the delay is not lower than the traffic light's on the equity "
             "2007 to 2009 and foreign-exchange 2008 windows"),
         raw(f"real windows (models the light flags): median day {C11_E['equity-2007-09']} against {C11_L['equity-2007-09']} and "
             f"{C11_E['fx-2008']} against {C11_L['fx-2008']}. The same comparison on the generator, which this study adds, is the delay criterion of H2 "
             f"(x3 {x3['pooled_median']:.0f} against {x3['pooled_traffic_light_median']:.0f})"),
         raw("Fires" if real_fires else "Does not fire")],
        [raw("PD prediction (from the documentation of the engine): the PD monitor over-rejects a correct PD when the defaults of a year are correlated, "
             "because its null is binomial"),
         raw(f"asset correlation 0.03: product {pc(rho3['e_product']['ever'])}\\,\\%, average {pc(rho3['e_average']['ever'])}\\,\\% of the histories"),
         raw("Confirmed" if over else "Not confirmed")],
        [raw("Overall, the hypotheses H1 to H3 and R as stated"),
         raw("H2 and H3 fail at three times the nominal rate; H1 holds; R does not fire"),
         raw("Holds" if holds_as_stated else "Does not hold as stated")],
        span("Not stated before the experiments (chosen or run after the results)"),
        [raw("Upper-side variant of the rate monitor (chosen after the two-sided results, the direction a supervisor penalises): delay below 250 and below the traffic light's, "
             "and power cost under 10 points"),
         raw(f"x3: pooled median {u3['pooled_median']:.0f} [{u3['pooled_median_ci'][0]:.0f}, {u3['pooled_median_ci'][1]:.0f}], cost "
             f"{100 * u3['pooled_power_cost']:.1f} $\\pm$ {100 * u3['pooled_power_cost_se']:.1f} points; "
             f"x4: {u4['pooled_median']:.0f} [{u4['pooled_median_ci'][0]:.0f}, {u4['pooled_median_ci'][1]:.0f}], cost "
             f"{100 * u4['pooled_power_cost']:.1f} $\\pm$ {100 * u4['pooled_power_cost_se']:.1f} points"),
         raw("Met at both severities; needs a prospective confirmation" if u_ok else "Not met at both severities")],
        [raw("PD question (run after the results): are the defaults of five grades detected earlier than by the chi-square test across grades read every year, "
             "when the chi-square rule is given the size the e-process measured?"),
         raw(f"PD $\\times 1.05$: chi-square {pc(eq['all-x1.05']['chi2_sim']['ever'])}\\,\\% at a size of 5\\,\\% and {pc(eq['all-x1.05']['chi2_matched']['ever'])}\\,\\% at the "
             f"size of the e-process, average e-process {pc(abl['all-x1.05']['average']['ever'])}\\,\\%; "
             f"$\\times 1.1$: {pc(eq['all-x1.1']['chi2_sim']['ever'])}, {pc(eq['all-x1.1']['chi2_matched']['ever'])} and {pc(abl['all-x1.1']['average']['ever'])}\\,\\%"),
         raw("No: the chi-square rule detects more" if chi_more else "Yes")],
    ]
    figkit.table(
        OUT / "hypotheses.tex", ["Hypothesis", "Measured", "Outcome"], rows, align="p{6.0cm}p{6.6cm}p{2.4cm}",
        wide=True, label="tab:hypotheses",
        caption=("The hypotheses of the proposed monitors with the measurements that judge them and the outcome of each. The first block was stated before the experiments: "
                 "size on the generator of known truth, delay and power cost pooled over 20 independent seeds of 2,000 streams, the refutation clause on the two real windows "
                 "of the case on market risk at the 99\\,\\% level, and the prediction for the PD monitor, followed by the outcome of the hypothesis as a whole. "
                 "The second block was chosen or run after the results were known and is not a test of a pre-stated hypothesis."))


def c11_light_days() -> tuple[dict, dict]:
    e, light = {}, {}
    for w in ("equity-2007-09", "fx-2008"):
        s = C11["windows"][w]["levels"]["0.01"]["summary"]
        e[w] = f"{s['overlap']['median_e_day_among_light_flagged']:.0f}"
        light[w] = f"{s['overlap']['median_light_day']:.0f}"
    return e, light


C11_E, C11_L = c11_light_days()


def t_size_matched() -> None:
    sm = TH["size_matched_power"]
    rows = []
    for f in ("x2", "x3", "x4", "x6"):
        r = sm["factors"][f]
        e, eu = sc({"x2": "rate-x2", "x3": "rate-x3", "x4": "rate-x4", "x6": "rate-x6"}[f])["e_rate"], \
            sc({"x2": "rate-x2", "x3": "rate-x3", "x4": "rate-x4", "x6": "rate-x6"}[f])["e_rate_upper"]
        rows.append([raw(f"{f[1:]}"), pc(r["kupiec_power"]), pc(r["kupiec_upper_power"]), pc(r["np_power_at_e_process_size"]),
                     pci(e, "by"), pci(eu, "by")])
    figkit.table(
        OUT / "size-matched.tex",
        ["Hit-rate factor", "Kupiec power, two-sided, \\%", "Kupiec power, upper tail, \\%", "Best test at the e-process size, \\%",
         "Rate e-process by day 250, \\% [95\\% CI]", "Upper-side e-process by day 250, \\% [95\\% CI]"],
        rows, align="rrrrrr", wide=True, label="tab:size-matched",
        caption=(f"Exact power at day 250 and a VaR level of 1\\,\\% (expected count 2.5): the Kupiec test has a size of {pc(sm['kupiec_size'])}\\,\\% "
                 f"two-sided, of which {pc(sm['kupiec_upper_size'], 2)}\\,\\% lies in the upper tail that rejects an understated VaR (it rejects from "
                 f"{sm['kupiec_smallest_rejecting_count']} exceptions); the most powerful test, randomised, at the size {pc(sm['e_process_size_by_window'], 2)}\\,\\% "
                 "that the rate e-process spends by day 250 on correct models (computed exactly) bounds every test of that size; the last two columns are the "
                 "measured shares of the e-processes on the generator."))


def t_ablation_grid() -> None:
    g = AB["hits_grid"]
    names = {"full": "Full two-sided grid, $0.25$ to $10$", "upper": "Upper half, $1.5$ to $10$", "upper-low": "Upper alternatives $1.5$ to $4$",
             "upper-high": "Upper alternatives $3$ to $10$", "single-1.5": "Single alternative $1.5\\alpha$", "single-2": "Single alternative $2\\alpha$",
             "single-3": "Single alternative $3\\alpha$", "single-4": "Single alternative $4\\alpha$", "single-10": "Single alternative $10\\alpha$"}
    rows = []
    for vid, label in names.items():
        rows.append([raw(label), pci(g["null"][vid]), pci(g["rate-x2"][vid]), pci(g["rate-x3"][vid], "by"), med(g["rate-x3"][vid]),
                     pci(g["rate-x4"][vid], "by"), med(g["rate-x4"][vid]), med(g["rate-x6"][vid])])
    figkit.table(
        OUT / "ablation-grid.tex",
        ["Mixture grid", "Size, \\%", "Power x2, \\%", "Power by 250 x3, \\%", "Median day x3", "Power by 250 x4, \\%", "Median day x4", "Median day x6"],
        rows, align="p{4.4cm}rrrrrrr", wide=True, label="tab:ablation-grid",
        caption=(f"Ablation of the mixture over alternative hit rates of the rate monitor on {AB['meta']['reps']:,} streams of 1,000 days per scenario: "
                 "the full grid, its upper half, the upper half cut at its low and high ends, and each single alternative, which is the likelihood-ratio e-process "
                 "of one hit rate. Size and power (x2) are shares ever rejected; power by day 250 and median days are for hit rates three (x3), four (x4) "
                 "and six (x6) times too high; brackets are 95\\,\\% intervals."))


def t_ablation_battery() -> None:
    b = AB["hits_battery"]
    names = {"rate": "Rate e-process", "cluster": "Clustering e-process", "average": "Average of the two (battery, valid)",
             "union": "Either at threshold 40 (union, valid)", "product": "Product of the two (not an e-process on one stream)"}
    rows = []
    for vid, label in names.items():
        rows.append([raw(label), pci(b["null"][vid]), pci(b["rate-x3"][vid]), pci(b["cluster-0.2"][vid]), pci(b["cluster-0.4"][vid]),
                     med(b["cluster-0.4"][vid])])
    figkit.table(
        OUT / "ablation-battery.tex",
        ["Combination", "Size, \\%", "Rate x3, \\%", "Clustering $q=0.2$, \\%", "Clustering $q=0.4$, \\%", "Median day, $q=0.4$"],
        rows, align="p{5.4cm}rrrrr", wide=True, label="tab:ablation-battery",
        caption=("Ablation of the combination of the two VaR monitors that read the same stream, on "
                 f"{AB['meta']['reps']:,} streams of 1,000 days per scenario: share of streams ever rejected, in percent, when the model is right (size), "
                 "when the hit rate is three times too high, and when hits cluster at the right rate. The product is shown to measure its size, "
                 "which the theory does not bound."))


def t_ablation_pd() -> None:
    p = AB["pd_combine"]
    cols = ["all-x1", "all-x1.05", "all-x1.1", "all-x1.25", "grade5-x1.3"]
    names = {"product": "Product, two-sided", "product-upper": "Product, upper", "average": "Average, two-sided",
             "average-upper": "Average, upper", "average-upper-coarse": "Average, upper, four alternatives $1.1$ to $2$",
             "average-upper-single-1.25": "Average, upper, one alternative $1.25$"}
    rows = [[raw(label)] + [pci(p[c][vid]) for c in cols] for vid, label in names.items()]
    rows.append([raw("Chi-square across grades, read once at year 10")] + [pci(p[c]["chi2-one-shot-year-10"]) for c in cols])
    rows.append([raw("Chi-square across grades, read every year")] + [pci(p[c]["chi2-every-year"]) for c in cols])
    figkit.table(
        OUT / "ablation-pd.tex",
        ["Rule", "Every PD right (size)", "Every PD $\\times 1.05$", "Every PD $\\times 1.1$", "Every PD $\\times 1.25$", "10\\,\\% grade $\\times 1.3$"],
        rows, align="p{5.8cm}rrrrr", wide=True, label="tab:ablation-pd",
        caption=(f"Ablation of the PD monitor of five grades over ten years on {AB['meta']['pd_reps']:,} histories per column from the generator of default "
                 "counts with no asset correlation: share of histories ever rejected, in percent with 95\\,\\% Wilson intervals, for the grades combined by product or by average, "
                 "two-sided or upper, with coarser grids, and for the chi-square test across grades read once or every year."))


def t_pd_results() -> None:
    p = AB["pd_combine"]
    rows = []
    for c, lab in (("all-x1", "1 (size)"), ("all-x1.05", "1.05"), ("all-x1.1", "1.1"), ("all-x1.25", "1.25"), ("grade5-x1.3", "10\\% grade only, 1.3")):
        pr, av = p[c]["product"], p[c]["average"]
        rows.append([raw(lab), pci(pr), pci(av), pci(p[c]["chi2-one-shot-year-10"]), pci(p[c]["chi2-every-year"]),
                     raw(f"{pc(p[c]['average-upper'].get('by3', 0.0))}")])
    figkit.table(
        OUT / "pd-results.tex",
        ["PD scaling", "Product, \\%", "Average, \\%", "Chi-square at year 10, \\%", "Chi-square every year, \\%", "Average upper, by year 3, \\%"],
        rows, align="p{3.6cm}rrrrr", wide=True, label="tab:pd-results",
        caption=("Defaults against the predicted PD of five grades (0.5 to 10\\,\\%), 2,000 obligors per grade and year, ten years, "
                 f"{AB['meta']['pd_reps']:,} histories per row from the generator of default counts: share of histories rejected at some year by the "
                 "PD e-process combined by product or by average, by the chi-square test across grades on the cumulative counts read once at year 10, "
                 "and by the same test read every year; the last column is the share of histories the upper-side average e-process rejects by year 3."))


def t_c11(level: str, label: str, name: str, cap_level: str) -> None:
    rows = []
    for w, wd in C11["windows"].items():
        s = wd["levels"][level]["summary"]
        light = s["traffic_light"]
        rows.append([raw(w), f"{wd['n_days']}", f"{s['expected']:.1f}", f"{s['e_rate']['flagged']}", day_s(s["e_rate"]["median_day"]),
                     f"{s['e_wwz']['flagged']}", f"{s['kupiec_end']['flagged']}", f"{s['kupiec_cumulative']['flagged']}",
                     day_s(s["kupiec_cumulative"]["median_day"]), (f"{light['flagged']}" if wd["n_days"] >= 250 and level == "0.01" else "--"),
                     (day_s(light["median_day"]) if wd["n_days"] >= 250 and level == "0.01" else "--")])
    figkit.table(
        OUT / name,
        ["Window", "Days", "Expected exceptions", "E-process flags", "Median day", "E-backtest flags", "Kupiec at end flags",
         "Kupiec daily flags", "Median day", "Traffic light flags", "Median day"],
        rows, align="lrrrrrrrrrr", wide=True, label=label,
        caption=(f"The 18 models of the case on market risk in each of its six windows at the {cap_level} level: the number of models each rule flags at some day, "
                 "and the median first-flag day among the models it flags. The rules are the rate e-process, the e-backtest of Wang, Wang and Ziegel (2022), "
                 "the Kupiec test once at the end of the window (the eligibility gate), the Kupiec test on all days so far read daily from day 50, and the "
                 "Basel traffic light, which needs 250 days (a dash where the window is shorter or the level is not the 99\\,\\% one). No truth is known in these windows."))


def day_s(v: float | None) -> str:
    return "--" if v is None else f"{v:.0f}"


def t_c03() -> None:
    rows = []
    for stem, c in C03["cohorts"].items():
        fy = ", ".join(f"{v['fiscal_year']}" for v in c["vintages"])
        rej = ", ".join("--" if v["rejection_month"] is None else str(v["rejection_month"]) for v in c["vintages"])
        light = ", ".join(str(v["five_year_light"]) for v in c["vintages"])
        dflt = ", ".join(f"{v['defaults']:,}/{v['predicted_defaults']:,.0f}" for v in c["vintages"])
        a, p = c["average"], c["product"]
        rows.append([raw(stem.replace("fy", "FY")), raw(fy), raw(dflt), raw(rej), raw(light),
                     "--" if a["rejection_month"] is None else str(a["rejection_month"]),
                     "--" if p["rejection_month"] is None else str(p["rejection_month"]),
                     f"{a['max_log_e']:,.1f}"])
    figkit.table(
        OUT / "c03.tex",
        ["Cohort", "Vintages", "Charge-offs / predicted", "Month rejected, each", "Five-year light, each", "Month, average", "Month, product",
         "Largest $\\log E$, average"],
        rows, align="llllllrr", wide=True, label="tab:c03", digits=1,
        caption=("The PD e-process read at the ages 12, 24, 36, 48 and 60 months on the five cohorts of SBA 7(a) loans of the case on small-business credit, "
                 "from the committed vintage curves: the charge-offs observed over the observed ages against the charge-offs the predicted curve implies, the first age at which "
                 "each vintage and the cohort reject, and the light of the binomial test read once at the five-year mark. A dash means the monitor never reached 20."))


def t_pd_correlation() -> None:
    rows = []
    for r in PC["rows"]:
        rows.append([raw(f"{r['rho']:.2f}"), pci(r["e_product"]), pci(r["e_average"]), pci(r["e_average_upper"]),
                     pci(r["chi2_one_shot_year_10"]), pci(r["chi2_every_year"])])
    figkit.table(
        OUT / "pd-correlation.tex",
        ["Asset correlation $\\rho$", "Product, \\%", "Average, \\%", "Average, upper, \\%", "Chi-square at year 10, \\%", "Chi-square every year, \\%"],
        rows, align="rrrrrr", wide=True, label="tab:pd-correlation",
        caption=(f"Share of {PC['meta']['reps']:,} ten-year histories of five grades, with the predicted PD equal to the true PD, rejected at some year when "
                 "the defaults of a year share one systematic factor of asset correlation $\\rho$: the PD e-processes, whose null is binomial with no correlation, "
                 "and the chi-square test across grades. The first row has no correlation and is the size under the null of both families."))


def t_theory_delay() -> None:
    rows = []
    kl = TH["kl"]["rows"]
    mp = {1.5: "rate-x1.5", 2.0: "rate-x2", 3.0: "rate-x3", 4.0: "rate-x4", 6.0: "rate-x6", 10.0: "rate-x10"}
    for r in kl:
        s = sc(mp[r["factor"]])
        mt = MT["factors"]["x" + f"{r['factor']:g}"]
        rows.append([raw(f"{r['factor']:g}"), f"{1000 * r['kl_vs_null']:.2f}", f"{r['sprt_time']:.0f}", f"{r['mixture_time_bound']:.0f}",
                     med(mt), med(s["e_rate"])])
    figkit.table(
        OUT / "theory-delay.tex",
        ["Hit-rate factor $m$", "$1000\\,\\mathrm{KL}(m\\alpha\\|\\alpha)$", "Time $\\log 20/\\mathrm{KL}$", "Time with the mixture penalty", "Measured median, matched single alternative",
         "Measured median, mixture"],
        rows, align="rrrrrr", wide=True, label="tab:theory-delay",
        caption=("The first-order delay of the e-process at a VaR level of 1\\,\\%: the Kullback-Leibler divergence per day of the true hit rate from the null, in thousandths "
                 "of a nat, the number of days a log-optimal bet needs to reach the threshold $\\log 20$, the same with the penalty $\\log K$ of a mixture of $K=8$ "
                 "alternatives, and the measured median first-rejection days (95\\,\\% bootstrap intervals) of the single-alternative e-process whose alternative is the true hit rate "
                 "(matched at every factor) and of the mixture e-process, on the same 2,000 streams. "
                 "Where the median exceeds the 1,000-day horizon the symbol $>$ is printed."))


def t_null_expectation() -> None:
    ne = TH["null_expectation"]
    names = {"rate_two_sided": "Rate e-process, two-sided", "rate_upper": "Rate e-process, upper", "rate_lower": "Rate e-process, lower",
             "cluster": "Clustering e-process", "battery_average": "Average of the rate and clustering e-processes",
             "wwz_grel": "E-backtest of Wang, Wang and Ziegel (2022)", "beta_mixture": "Uniform-prior Bayes factor"}
    rows = [[raw(names[k]), raw(f"{v['max_abs_departure_from_one']:.1e}"), f"{v['expectation_at_t12']:.12f}"] for k, v in ne["processes"].items()]
    pc_ = TH["product_counterexample"]
    rows.append([raw("Product of the rate and clustering e-processes on one stream ($T=10$, $\\alpha=0.2$)"),
                 raw(f"{pc_['hits_rate_times_cluster']['max_expectation']:.0f}"), "--"])
    figkit.table(
        OUT / "null-expectation.tex", ["Process", "Largest departure of $\\mathbb E[E_t]$ from 1 over $t\\le 12$", "$\\mathbb E[E_{12}]$"], rows,
        align="p{7.4cm}rr", wide=False, label="tab:null-expectation", digits=12,
        caption=(f"Exact null expectation of each process by enumeration of all {ne['sequences']:,} hit sequences of {ne['T']} days at a VaR level of "
                 f"{ne['alpha']}: the largest departure of the expectation from 1 over the {ne['T']} days is at the level of floating-point error for every valid "
                 "process, and the last row shows the largest expectation of the product of two e-processes read on the same stream over ten days, which is not an e-process."))


def t_agreement() -> None:
    ref_h = C22["hits"]
    rows = []
    for sid, ref_id in (("null", "null"), ("rate-x3", "rate-x3"), ("rate-x4", "rate-x4"), ("cluster-0.4", "cluster-0.4")):
        r = next(s for s in ref_h["scenarios"] if s["id"] == ref_id)
        mine = sc(sid)
        for key, rkey, label in (("e_rate", "e_rate", "Rate e-process"), ("kupiec_trailing", "kupiec_trailing", "Kupiec, last 250 days"),
                                 ("traffic_light", "traffic_light", "Traffic light")):
            a, b = mine[key]["ever"], r[rkey]["ever"]
            rows.append([raw(sid.replace("-", " ")), raw(label), pc(a), pc(b), f"{100 * (a - b):+.1f}",
                         day_s(mine[key]["median_day"]), day_s(r[rkey]["median_day"])])
    figkit.table(
        OUT / "agreement.tex",
        ["Scenario", "Rule", "This run, ever, \\%", "Committed run, ever, \\%", "Difference, points", "This run, median day", "Committed run, median day"],
        rows, align="llrrrrr", wide=True, label="tab:agreement", digits=1,
        caption=("Agreement of this study with the committed document of the product (seed 42, 2,000 streams per scenario, same generator and engine release): "
                 "the share of streams ever rejected and the median first-rejection day of three rules in four scenarios, the difference being the Monte Carlo "
                 "error of two independent runs of 2,000 streams (about one point at the middle of the range)."))


def pdci(m: dict) -> str:
    lo, hi = m["ever_ci"]
    return raw(f"{pc(m['ever'])} [{pc(lo)}, {pc(hi)}]")


def t_pd_comparators() -> None:
    rows = []
    for r in PDC["correlation"]:
        pe = next(x for x in PC["rows"] if x["rho"] == r["rho"])
        rows.append([raw(f"{r['rho']:.2f}"), pci(pe["e_average"]), pdci(r["binomial"]["every_year"]), pdci(r["jeffreys"]["every_year"]),
                     pdci(r["vasicek_assumed"]["every_year"]), pdci(r["vasicek_true"]["every_year"]), pdci(r["vasicek_true"]["once"]),
                     pdci(r["chi2_sim"])])
    m = PDC["meta"]
    figkit.table(
        OUT / "pd-comparators.tex",
        ["$\\rho$", "Average e-process", "Binomial per grade", "Jeffreys per grade", "Vasicek, $0.12$ assumed",
         "Vasicek, true $\\rho$", "Vasicek, true $\\rho$, read once", "Chi-square, simulated critical value"],
        rows, align="p{0.8cm}" + ">{\\raggedleft\\arraybackslash}p{1.9cm}" * 7, wide=True, label="tab:pd-comparators",
        caption=(f"The PD e-process and the PD tests of the engine on the same {m['reps']:,} histories as \\cref{{tab:pd-correlation}} (predicted PD equal to the true PD, defaults of a year sharing "
                 "a systematic factor of asset correlation $\\rho$): share of histories rejected at some year, in percent with 95\\,\\% Wilson intervals. "
                 "The per-grade tests (the exact binomial test, the Jeffreys test, and the binomial test under the Vasicek one-factor mixture with the correlation assumed or the "
                 f"true one) are one-sided; read every year they reject when any of the 5 grades in any of the 10 years has a p-value below ${m['bonferroni_every_year']:.3f}$ "
                 f"(a Bonferroni split of 5\\,\\% over the 50 grade-years), and read once, on the defaults of year 10 alone, when any grade is below $0.01$. The chi-square rule reads the statistic across grades every year "
                 f"against one critical value set by simulation on {m['calibration_reps']:,} correct histories to a size of 5\\,\\% over the ten years."))


def t_pd_equal_size() -> None:
    eq = PDC["equal_size_chi2"]
    names = {"all-x1": "1 (size)", "all-x1.05": "1.05", "all-x1.1": "1.1", "all-x1.25": "1.25", "grade5-x1.3": "10\\% grade only, 1.3"}
    rows = []
    for sid, lab in names.items():
        a, v = AB["pd_combine"][sid]["average"], eq["scenarios"][sid]
        def trio(m: dict) -> str:
            lo, hi = m["ever_ci"]
            return raw(f"{pc(m['ever'])} [{pc(lo)}, {pc(hi)}] / {pc(m['by3'])} / {day_s(m['median_year_among_detected'])}")

        cells = [raw(lab), trio(a), trio(v["chi2_sim"]), trio(v["chi2_matched"]),
                 pdci(v["binomial"]["every_year"]), pdci(v["vasicek_assumed"]["every_year"])]
        rows.append(cells)
    size = AB["pd_combine"]["all-x1"]["average"]
    size_lo, size_hi = size["ever_ci"]
    figkit.table(
        OUT / "pd-equal-size.tex",
        [r"PD scaling", r"Average e-process", r"Chi-square, 5\,\% size", r"Chi-square, size of the e-process", r"Binomial per grade, ever", r"Vasicek, $0.12$ assumed, ever"],
        rows, align=r"p{2.0cm}" + r">{\raggedleft\arraybackslash}p{3.7cm}" * 3 + r">{\raggedleft\arraybackslash}p{2.6cm}" * 2, wide=True, label="tab:pd-equal-size",
        caption=(rf"Detection of a PD that is too low by the average PD e-process and by the chi-square test across grades read every year with a simulated constant critical value, "
                 rf"at a size of 5\,\% and at the size the average e-process measured ({pc(eq['matched_size'])}\,\%, {round(eq['matched_size'] * AB['meta']['pd_reps'])} of {AB['meta']['pd_reps']:,} histories, "
                 rf"a 95\,\% Wilson interval of [{pc(size_lo)}, {pc(size_hi)}]), on {AB['meta']['pd_reps']:,} histories per row (the histories of "
                 r"\cref{tab:pd-results}, no asset correlation). The first three rule columns give the share of histories rejected within ten years (\%) with its 95\,\% Wilson interval, "
                 r"the share rejected by year 3 (\%) and the median year of rejection among the histories rejected, separated by slashes. The last two columns give the share rejected within ten years (\%) "
                 r"with its interval by the engine's binomial test per grade and by its Vasicek-corrected binomial test with a correlation of 0.12 assumed, each read every year with a Bonferroni split over the 50 grade-years."))


def fit(path: pathlib.Path) -> None:
    """Scale a table that is wider than the text block to the line width (graphicx ``\\resizebox``); the numbers are untouched."""
    text = path.read_text(encoding="utf-8")
    if "\\resizebox" in text:
        return
    text = text.replace("\\begin{tabular}", "\\resizebox{\\linewidth}{!}{%\n\\begin{tabular}", 1)
    text = text.replace("\\end{tabular}", "\\end{tabular}}", 1)
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    t_main(); t_clustering(); t_x3(); t_hypotheses(); t_size_matched(); t_ablation_grid(); t_ablation_battery(); t_ablation_pd()
    t_pd_results()
    t_c11("0.01", "tab:c11", "c11.tex", "99\\,\\%")
    t_c11("0.025", "tab:c11-975", "c11-975.tex", "97.5\\,\\%")
    t_c03(); t_pd_correlation(); t_theory_delay(); t_null_expectation(); t_agreement(); t_pd_comparators(); t_pd_equal_size()
    for tex in sorted(OUT.glob("*.tex")):
        fit(tex)
    print("tables written:", len(list(OUT.glob("*.tex"))))


if __name__ == "__main__":
    main()
