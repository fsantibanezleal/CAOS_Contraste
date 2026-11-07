"""Write the booktabs tables of the manuscript into ``tables/`` from ``experiments/*.json`` and the committed C11 documents.

    python manuscripts/adaptive-conformal-recalibration-of-var/make_tables.py
"""
from __future__ import annotations

import collections
import pathlib
import statistics as st
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_shared"))
sys.path.insert(0, str(HERE / "experiments"))
import common  # noqa: E402
import figkit  # noqa: E402

OUT = HERE / "tables"
E2, E3, E4, E5, E6 = (common.load(f"e{i}_{n}.json") for i, n in ((2, "wrap_ladder"), (3, "ablation"), (4, "score_space"), (5, "generators"), (6, "theory")))
MN = {"hs-250": "HS-250", "garch-t": "GARCH-t", "fhs": "FHS", "hs-500": "HS-500", "awhs": "AWHS", "dn-rolling": "Delta-normal", "ewma": "EWMA",
      "gjr-t": "GJR-t", "egarch-t": "EGARCH-t", "evt-mf": "Conditional EVT"}
WN = {"equity-2007-09": "Equity 2007--09", "equity-2020": "Equity 2020", "rates-2022": "Rates 2022", "fx-2008": "FX 2008", "mixed-2023": "Mixed 2023",
      "calm-2004-06": "Calm 2004--06"}


def p(x):
    return "--" if x is None else (f"{x:.3f}" if x >= 0.0005 else "$<0.001$")


def pc(x, d=1):
    return f"{100 * x:+.{d}f}\\%"


def T(name, header, rows, **kw):
    """``figkit.table`` with the cells that carry LaTeX passed through, and the tabular fitted to the text width."""
    rows = [[("\\relax " + c) if isinstance(c, str) and ("\\" in c or "$" in c) and not c.startswith(("$", "\\")) else c for c in r] for r in rows]
    path = figkit.table(OUT / f"{name}.tex", header, rows, **kw)
    text = path.read_text(encoding="utf-8")
    text = text.replace("\\begin{tabular}", "\\begin{adjustbox}{max width=\\textwidth}\n\\begin{tabular}", 1)
    text = text.replace("\\end{tabular}", "\\end{tabular}\n\\end{adjustbox}", 1)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def main_results():
    rows = []
    for w in common.STRESS:
        for m in common.WRAPPED3:
            for a in common.LEVELS:
                r = next(x for x in E2["rows"] if x["window"] == w and x["model"] == m and x["alpha"] == a)
                u, v = r["unwrapped"], r["wrapped"]
                lo, hi = r["hit_ci_wrapped"]
                rows.append([WN[w], MN[m], f"{100 * a:g}", f"{u['n_hits']}", f"{v['n_hits']} ({100 * v['hit_rate']:.1f}; {100 * lo:.1f}--{100 * hi:.1f})",
                             f"{p(u['kupiec_p'])} / {p(v['kupiec_p'])}", f"{p(u['cc_p'])} / {p(v['cc_p'])}", p(v["independence_p"]),
                             f"{pc(r['fz0_change'])} [{pc(r['ci95'][0])}, {pc(r['ci95'][1])}]"])
    T("main-results", ["Window", "Model", "Level (\\%)", "Hits U", "Hits W (rate \\%; 95\\% Wilson)", "Kupiec $p$ U / W", "CC $p$ U / W", "Indep. $p$ W",
                       "FZ0 change [95\\% CI]"], rows, align="llrrlllll", wide=True,
      caption="Unwrapped (U) and wrapped (W) value at risk of three ladder models in the three stress windows of C11, at tail levels 1\\% and 2.5\\%: hits, the "
              "hit rate of the wrapped model with its 95\\% Wilson interval, the p-values of the Kupiec and conditional coverage (CC) tests, the Christoffersen "
              "independence p-value of the wrapped model and the relative change of the mean FZ0 score with a 95\\% moving-block bootstrap interval (positive is "
              "worse). The windows hold 504, 104 and 249 forecast days.", label="tab:main-results")


def hypotheses():
    rows = []
    for m in E2["models"]:
        for a in common.LEVELS:
            rs = [x for x in E2["rows"] if x["model"] == m and x["alpha"] == a and x["window"] in common.STRESS]
            pu = sum(common.passes(x["unwrapped"]) for x in rs)
            pw = sum(common.passes(x["wrapped"]) for x in rs)
            wst = max(x["fz0_change"] for x in rs)
            ind = next(x for x in rs if x["window"] == "equity-2007-09")["wrapped"]["independence_p"]
            hold = pw - pu >= 1 and wst <= 0.05 and not (ind is not None and ind < 0.05)
            rows.append([MN[m], f"{100 * a:g}", pu, pw, pw - pu, pc(wst), p(ind), "yes" if hold else "no"])
    T("hypotheses", ["Model", "Level (\\%)", "Windows passed U", "Windows passed W", "Extra", "Worst FZ0 change", "Indep. $p$ W, 2007--09", "Holds"], rows,
      align="lrrrrrrl",
      caption="The prediction for each of the ten wrapped ladder models and two tail levels: windows passed (Kupiec and conditional coverage both at least 0.05) "
              "out of the three stress windows, unwrapped (U) and wrapped (W), the extra windows gained, the worst relative FZ0 change in any stress window, "
              "the independence p-value of the wrapped model in equity 2007--09 and whether the prediction holds. The first six rows are the models of the "
              "prediction as stated; the other rows apply the same rule to the remaining models.", label="tab:hypotheses")


def ladder():
    rows = []
    U = {(r["window"], r["model"], r["alpha"]): r["passes"] for r in E4["rows"] if r["method"] == "unwrapped"}
    wr = {(r["window"], r["model"], r["alpha"]): common.passes(r["wrapped"]) for r in E2["rows"]}
    for w in common.STRESS:
        for a in common.LEVELS:
            ms = sorted({m for (ww, m, aa) in U if ww == w and aa == a})
            n0 = sum(U[(w, m, a)] for m in ms)
            n3 = sum(wr[(w, m, a)] if m in common.WRAPPED3 else U[(w, m, a)] for m in ms)
            n10 = sum(wr[(w, m, a)] if (w, m, a) in wr else U[(w, m, a)] for m in ms)
            rows.append([WN[w], f"{100 * a:g}", len(ms), n0, n3, n10])
    T("ladder-context", ["Window", "Level (\\%)", "Ladder models", "Pass, none wrapped", "Pass, three wrapped", "Pass, ten wrapped"], rows, align="lrrrrr",
      caption="The eighteen-model ladder of C11 in the three stress windows: how many models pass the Kupiec and conditional coverage tests (both p at least 0.05) "
              "as the ladder runs, with the three models of the prediction replaced by their wrapped versions, and with the ten level-parametric models replaced "
              "by their wrapped versions.", label="tab:ladder-context")


def comparators():
    TEN = set(E2["models"])
    rows = []

    def add(name, rs, fz):
        n = len(rs)
        ind = sum(1 for r in rs if r[0]["independence_p"] is not None and r[0]["independence_p"] < 0.05)
        rows.append([name, f"{sum(r[1] for r in rs)} / {n}", ind, f"{100 * st.mean(abs(r[0]['hit_rate'] - r[2]) for r in rs):.2f}",
                     pc(st.mean(fz)) if fz else "--", pc(max(fz)) if fz else "--", sum(1 for x in fz if x > 0.05) if fz else "--"])

    for meth, name in (("unwrapped", "Unwrapped"), ("rolling", "Rolling split-conformal scale"), ("tracker-eta-0.01", "Quantile tracker, $\\eta = 0.01$"),
                       ("tracker", "Quantile tracker, $\\eta = 0.05$"), ("tracker-eta-0.2", "Quantile tracker, $\\eta = 0.2$")):
        rs = [(r["scores"], r["passes"], r["alpha"]) for r in E4["rows"] if r["method"] == meth and r["window"] in common.STRESS and r["model"] in TEN]
        fz = [r["fz0_change"] for r in E4["rows"] if r["method"] == meth and r["window"] in common.STRESS and r["model"] in TEN and "fz0_change" in r]
        add(name, rs, fz)
        if meth == "unwrapped":
            rw = [(r["wrapped"], common.passes(r["wrapped"]), r["alpha"]) for r in E2["rows"] if r["window"] in common.STRESS]
            add("Level wrapper, $\\gamma = 0.005$ (proposed)", rw, [r["fz0_change"] for r in E2["rows"] if r["window"] in common.STRESS])
    T("comparators", ["Recalibration", "Cells passing", "Independence failures", "Mean $|$hit $-$ target$|$ (points)", "Mean FZ0 change", "Worst FZ0 change",
                      "Cells over $+5\\%$"], rows, align="lrrrrrr",
      caption="Online recalibrations compared on the same forecasts: the ten level-parametric ladder models at two tail levels in the three stress windows (60 cells). "
              "A cell passes when the Kupiec and conditional coverage p-values are both at least 0.05; independence failures count the cells with a Christoffersen "
              "independence p-value below 0.05; the FZ0 change is relative to the unwrapped model.", label="tab:comparators")


def ablation():
    V = collections.defaultdict(list)
    for r in E3["rows"]:
        if r["window"] in common.STRESS:
            V[r["variant"]].append(r)
    names = [("off", "Unwrapped ($\\gamma = 0$)"), ("full", "Full wrapper ($\\gamma = 0.005$)"), ("gamma-0.001", "Step $\\gamma = 0.001$"),
             ("gamma-0.0025", "Step $\\gamma = 0.0025$"), ("gamma-0.01", "Step $\\gamma = 0.01$"), ("gamma-0.02", "Step $\\gamma = 0.02$"),
             ("gamma-0.05", "Step $\\gamma = 0.05$"), ("band-wide", "Band $[10^{-5}, 0.5]$"), ("band-narrow", "Band $[\\alpha/2, 2\\alpha]$"),
             ("es-ratio", "ES keeps the target ES/VaR ratio"), ("es-target", "ES left at the target level")]
    rows = []
    for v, n in names:
        rs = V[v]
        fz = [r["fz0_change"] for r in rs if r["fz0_change"] is not None]
        rows.append([n, f"{sum(r['passes'] for r in rs)} / {len(rs)}", sum(1 for r in rs if r["scores"]["independence_p"] is not None and r["scores"]["independence_p"] < 0.05),
                     f"{100 * st.mean(abs(r['scores']['hit_rate'] - r['alpha']) for r in rs):.2f}", pc(st.mean(fz)) if fz else "--",
                     pc(max(fz)) if fz else "--", f"{st.mean(r['scores']['z2'] for r in rs):.2f}", sum(r["n_clipped"] for r in rs)])
    T("ablation", ["Variant", "Cells passing", "Independence failures", "Mean $|$hit $-$ target$|$ (points)", "Mean FZ0 change", "Worst FZ0 change",
                   "Mean $Z_2$", "Clipped days"], rows, align="lrrrrrrr",
      caption="Ablation of the wrapper on HS-250, GARCH-t and FHS at two tail levels in the three stress windows (18 cells): each row changes one component of the "
              "full wrapper (the step, the clipping band of the working level, the ES paired with the recalibrated VaR) and keeps the others. $Z_2$ is the "
              "Acerbi--Szekely statistic, zero for a correct ES and negative for an understated one; clipped days count updates cut by the band.",
      label="tab:ablation")


def generators():
    G = collections.defaultdict(list)
    for r in E5["rows"]:
        G[(r["scenario"], r["model"], r["alpha"], r["method"])].append(r)
    nm = {"no-shift": "No shift", "crisis-persistent": "Persistent crisis", "crash-decay": "Decaying crash", "drift-up": "Upward drift"}
    rows = []
    for s in E5["scenarios"]:
        for m in common.WRAPPED3:
            for a in common.LEVELS:
                row = [nm[s], MN[m], f"{100 * a:g}"]
                for me in ("unwrapped", "aci", "rolling", "tracker"):
                    rs = G[(s, m, a, me)]
                    k = sum(x["passes"] for x in rs)
                    lo, hi = common.wilson(k, len(rs))
                    row.append(f"{k / len(rs):.2f} ({lo:.2f}--{hi:.2f})")
                eu = st.mean(x["log_var_err"] for x in G[(s, m, a, "unwrapped")])
                ea = st.mean(x["log_var_err"] for x in G[(s, m, a, "aci")])
                fz = st.median(x["fz0_change"] for x in G[(s, m, a, "aci")])
                row += [f"{eu:.3f} / {ea:.3f}", pc(fz)]
                rows.append(row)
    T("generators", ["Scenario", "Model", "Level (\\%)", "Unwrapped", "Level wrapper", "Rolling scale", "Tracker", "VaR error U / W", "Median FZ0 change W"], rows,
      align="llrlllllr", wide=True,
      caption="Generators of known truth, 100 replications per scenario: pass rate (Kupiec and conditional coverage both at least 0.05) of the unwrapped model and of "
              "three recalibrations, each with its 95\\% Wilson interval; the mean absolute log error of the VaR against the true conditional VaR, unwrapped (U) "
              "and wrapped (W); and the median relative FZ0 change of the level wrapper.", label="tab:generators")


def scale_sweep():
    rows = []
    for r in E6["C"]["rows"]:
        rows.append([f"{100 * r['alpha']:g}", f"{r['scale_ratio']:g}", f"{100 * r['a_star']:.3f}", "yes" if r["in_band"] else "no",
                     f"{100 * r['level_mean']:.3f}", f"{100 * r['level_sd']:.3f}", "--" if r["level_sd_pred"] != r["level_sd_pred"] else f"{100 * r['level_sd_pred']:.3f}",
                     f"{100 * r['hit_rate']:.2f} $\\pm$ {100 * 1.96 * r['hit_rate_se']:.2f}", f"{100 * r['clipped_share']:.1f}"])
    T("scale-sweep", ["Level (\\%)", "Scale ratio $c$", "Fixed point $a^*$ (\\%)", "$a^*$ in band", "Simulated mean level (\\%)", "Simulated sd (\\%)",
                      "Predicted sd (\\%)", "Hit rate (\\%, 95\\% CI)", "Clipped days (\\%)"], rows, align="rrrlrrrlr", wide=True,
      caption="A model facing returns $c$ times larger in scale than it assumes (Student-$t$ with five degrees of freedom): the fixed point of the working level, the "
              "mean and standard deviation of the level simulated over 50 replications of 5,000 days, the standard deviation predicted by the linearisation, the "
              "long-run hit rate with its 95\\% interval and the share of updates cut by the band $[0.1\\%, 25\\%]$.", label="tab:scale-sweep")


def cluster():
    rows = [[f"{100 * r['alpha']:g}", r["cluster"], r["quiet_days"], r["gamma"], r["T"], f"{100 * r['frequency']:.2f}", p(r["kupiec_p"]),
             f"{r['independence_p']:.1e}", f"{100 * r['level_min']:.3f} to {100 * r['level_max']:.3f}"] for r in E6["B"]["rows"]]
    T("cluster", ["Level (\\%)", "Cluster $m$", "Quiet days $q$", "Step $\\gamma$", "Days", "Hit frequency (\\%)", "Kupiec $p$", "Independence $p$", "Level range (\\%)"],
      rows, align="rrrrrrrlr",
      caption="A hit sequence of clusters of $m$ consecutive hits separated by $q = m(1-\\alpha)/\\alpha$ quiet days has frequency exactly $\\alpha$: the engine's "
              "Kupiec test accepts it, its independence test rejects it with a p-value that rounds to zero, and the recursion stays inside the band throughout.",
      label="tab:cluster")


def windows():
    rows = []
    for w in common.WINDOWS:
        d = common.doc(w)["outputs"]
        comp = d["portfolio"]["components"]
        names = ", ".join(c.get("series_id", "") if isinstance(c, dict) else str(c) for c in comp)
        rows.append([WN[w], d["window"]["asset_class"], d["window"]["start_date"], d["window"]["end_date"], d["window"]["n_forecast_days"],
                     d["data_status"]["n_observed_days"], names.replace("-", "--"), "stress" if w in common.STRESS else "other"])
    T("windows", ["Window", "Class", "First forecast day", "Last forecast day", "Forecast days", "Observed days", "Series", "Role"], rows, align="llllrrll", wide=True,
      caption="The six windows of case C11: the asset class of the portfolio, the first and last forecast day, the number of forecast days and of observed days of the "
              "common calendar, the public series of the portfolio and the role of the window in the evaluation.", label="tab:windows")


def notation():
    rows = [["$y_t$, $L_t$", "Return and loss of day $t$ ($L_t = -y_t$)", "decimal"], ["$\\alpha$", "Target tail level of the VaR", "probability"],
            ["$a_t$", "Working tail level on day $t$", "probability"], ["$\\gamma$", "Step of the level update", "probability"],
            ["$[\\ell, u]$", "Clipping band of the working level", "probability"], ["$V_t(a)$, $E_t(a)$", "VaR and ES of the model at level $a$ (positive loss)", "decimal"],
            ["$e_t$", "Hit indicator $\\indic\\{L_t > V_t(a_t)\\}$", "0 or 1"], ["$T$", "Number of forecast days", "days"], ["$C_T$", "Total amount the band removes from the level",
            "probability"], ["$c$", "Ratio of the true scale to the scale the model assumes", "1"], ["$F$, $f$, $q_\\nu$", "Distribution, density and quantile function of the unit-variance Student-$t$", "1"],
            ["$a^*$", "Fixed point of the level update", "probability"], ["$S_t$, $\\theta_t$", "Score $L_t/V_t$ and the scale applied to the VaR", "1"],
            ["FZ0", "Mean Fissler--Ziegel score of the VaR and ES pair", "score"], ["$Z_2$", "Acerbi--Szekely ES statistic", "1"]]
    T("notation", ["Symbol", "Meaning", "Unit"], rows, align="lll", caption="Notation of the manuscript: each symbol with its meaning and its unit; the symbols of the "
      "back-tests and scores are those defined where they are first used in the experimental design.", label="tab:notation")


if __name__ == "__main__":
    for f in (main_results, hypotheses, ladder, comparators, ablation, generators, scale_sweep, cluster, windows, notation):
        f()
        print("wrote", f.__name__)
