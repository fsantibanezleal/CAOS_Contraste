"""Write the figures of the manuscript (vector PDF, readable in grayscale) from the committed experiment outputs.

    python manuscripts/e-process-sequential-monitors/make_figures.py

Figures land in ``figures/``. The sources are ``experiments/results_*.json``; the sample paths of the first figure are
redrawn from the engine's generator with the seed sequence recorded in the code, and the PD book of the committed C22
document is not read here (every PD result comes from this manuscript's own runs).
"""
from __future__ import annotations

import json
import math
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_shared"))
sys.path.insert(0, str(HERE / "experiments"))
import common as cm  # noqa: E402
import figkit  # noqa: E402

EXP = HERE / "experiments"
OUT = HERE / "figures"
S = figkit.STYLES + [{"color": "0.1", "linestyle": (0, (3, 1, 1, 1, 1, 1)), "marker": "P"},
                      {"color": "0.5", "linestyle": (0, (1, 2)), "marker": "*"}]


def load(name: str) -> dict:
    return json.loads((EXP / name).read_text(encoding="utf-8"))


H = load("results_hits.json")
SH = load("results_size_horizon.json")
TH = load("results_theory.json")
AB = load("results_ablation.json")
PC = load("results_pd_correlation.json")
C11 = load("results_c11.json")
C03 = load("results_c03.json")
FACTORS = [(1.5, "rate-x1.5"), (2.0, "rate-x2"), (3.0, "rate-x3"), (4.0, "rate-x4"), (6.0, "rate-x6"), (10.0, "rate-x10")]


def sc(sid: str) -> dict:
    return H["scenarios"][sid]["methods"]


def fig_paths() -> None:
    import matplotlib.pyplot as plt

    figkit.style()
    fig, axes = plt.subplots(1, 3, figsize=(6.8, 2.4), sharey=True, constrained_layout=True)
    for ax, (title, kw, tag) in zip(axes, (("Correct model", {}, 1000), ("Hit rate 3 times too high", {"rate_factor": 3.0}, 1001),
                                           ("Hit rate 4 times too high", {"rate_factor": 4.0}, 1002))):
        h = cm.draw_hits(H["meta"]["seed"], tag, 12, **kw)
        paths = cm.engine_paths(h, cm.ALPHA)
        d = np.arange(1, paths.shape[1] + 1)
        for p in paths:
            ax.plot(d, p, color="0.35", linewidth=0.7)
        ax.axhline(math.log(20), color="0.0", linestyle="--", linewidth=1.0)
        ax.axvline(250, color="0.5", linestyle=":", linewidth=0.9)
        ax.set_title(title)
        ax.set_xlabel("Day")
        ax.set_ylim(-4, 8)
    axes[0].set_ylabel(r"$\log E_t$")
    axes[0].text(20, math.log(20) + 0.25, r"$\log 20$", fontsize=7)
    figkit.save(fig, OUT, "paths")


def fig_size_horizon() -> None:
    import matplotlib.pyplot as plt

    figkit.style()
    fig, axes = plt.subplots(1, 2, figsize=(6.9, 3.0), constrained_layout=True)
    lab = {"e_rate": "Rate e-process", "e_wwz": "E-backtest (Wang, Wang, Ziegel)", "e_beta": "Uniform-prior Bayes factor",
           "kupiec_cumulative": "Kupiec, all days so far", "kupiec_trailing": "Kupiec, last 250 days", "traffic_light": "Traffic light",
           "kupiec_calibrated": "Kupiec, simulated critical value (1,000 days)", "cusum_calibrated": "CUSUM, simulated threshold (1,000 days)"}
    for ax, top in zip(axes, (100, 12)):
        for i, (k, name) in enumerate(lab.items()):
            c = SH["curves"][k]
            ax.plot(SH["days"], [100 * s for s in c["share"]], label=name, **{**S[i % len(S)], "markersize": 2.5})
        ax.axhline(5, color="0.0", linewidth=0.7, linestyle="--")
        ax.axvline(1000, color="0.7", linewidth=0.7, linestyle=":")
        ax.set_xlabel("Days read")
        ax.set_ylim(0, top)
    axes[0].set_ylabel("Correct models rejected by that day, %")
    axes[1].set_title("Same data, vertical axis cut at 12 %")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncol=2, frameon=False, fontsize=6.5)
    figkit.save(fig, OUT, "size-horizon")


def fig_delay() -> None:
    import matplotlib.pyplot as plt

    figkit.style()
    fig, axes = plt.subplots(1, 2, figsize=(6.8, 3.4), constrained_layout=True)
    keys = [("e_rate", "Rate e-process"), ("e_rate_upper", "Upper-side e-process"), ("e_sprt3", "Single alternative $3\\alpha$"),
            ("e_wwz", "E-backtest"), ("kupiec_cumulative", "Kupiec, all days"), ("kupiec_calibrated", "Kupiec, simulated critical value"),
            ("traffic_light", "Traffic light")]
    x = [f for f, _ in FACTORS]
    for i, (k, name) in enumerate(keys):
        med = [sc(s)[k]["median_day"] if sc(s)[k]["median_day"] is not None else 1000 for _, s in FACTORS]
        by = [100 * sc(s)[k]["by"] for _, s in FACTORS]
        axes[0].plot(x, med, label=name, **S[i % len(S)])
        axes[1].plot(x, by, label=name, **S[i % len(S)])
    axes[0].axhline(250, color="0.0", linestyle="--", linewidth=0.8)
    axes[0].set_xscale("log")
    axes[0].set_yscale("log")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels([f"{v:g}" for v in x])
    axes[0].set_xlabel("Hit-rate factor")
    axes[0].set_ylabel("Median first-rejection day")
    axes[1].set_xscale("log")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels([f"{v:g}" for v in x])
    axes[1].set_xlabel("Hit-rate factor")
    axes[1].set_ylabel("Rejected by day 250, %")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncol=4, frameon=False, fontsize=6.5)
    figkit.save(fig, OUT, "delay-severity")


def fig_power_size() -> None:
    import matplotlib.pyplot as plt

    figkit.style()
    fig, ax = plt.subplots(figsize=(6.0, 3.0))
    sm = TH["size_matched_power"]["factors"]
    fk = [("x1.5", 1.5, "rate-x1.5"), ("x2", 2.0, "rate-x2"), ("x3", 3.0, "rate-x3"), ("x4", 4.0, "rate-x4"), ("x6", 6.0, "rate-x6")]
    x = [f for _, f, _ in fk]
    ax.plot(x, [100 * sm[k]["kupiec_upper_power"] for k, _, _ in fk], label="Kupiec, one reading, upper tail", **S[0])
    ax.plot(x, [100 * sm[k]["np_power_at_e_process_size"] for k, _, _ in fk], label="Best test at the e-process size", **S[1])
    for i, (key, name) in enumerate((("e_rate", "Rate e-process"), ("e_rate_upper", "Upper-side e-process"), ("e_wwz", "E-backtest"))):
        y = [100 * sc(s)[key]["by"] for _, _, s in fk]
        lo = [100 * (sc(s)[key]["by"] - sc(s)[key]["by_ci"][0]) for _, _, s in fk]
        hi = [100 * (sc(s)[key]["by_ci"][1] - sc(s)[key]["by"]) for _, _, s in fk]
        ax.errorbar(x, y, yerr=[lo, hi], label=name, capsize=2, **S[2 + i])
    ax.set_xscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{v:g}" for v in x])
    ax.set_xlabel("Hit-rate factor")
    ax.set_ylabel("Power by day 250, %")
    ax.legend(frameon=False, loc="lower right")
    figkit.save(fig, OUT, "power-size")


def fig_clustering() -> None:
    import matplotlib.pyplot as plt

    figkit.style()
    fig, ax = plt.subplots(figsize=(6.0, 2.9))
    cols = [("null", "Correct model"), ("cluster-0.1", "q = 0.1"), ("cluster-0.2", "q = 0.2"), ("cluster-0.4", "q = 0.4")]
    keys = [("e_cluster", "Clustering e-process"), ("e_battery", "Rate and clustering, averaged"), ("e_rate", "Rate e-process"),
            ("independence_trailing", "Independence test, last 250 days, daily"), ("kupiec_trailing", "Kupiec, last 250 days, daily"),
            ("traffic_light", "Traffic light")]
    w = 0.13
    hatches = ["", "///", "...", "xxx", "\\\\\\", "---"]
    shades = ["0.15", "0.35", "0.55", "0.75", "0.9", "1.0"]
    for i, (k, name) in enumerate(keys):
        y = [100 * sc(s)[k]["ever"] for s, _ in cols]
        ax.bar(np.arange(len(cols)) + (i - 2.5) * w, y, w, label=name, color=shades[i], edgecolor="0.0", hatch=hatches[i], linewidth=0.5)
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels([c for _, c in cols])
    ax.axhline(5, color="0.0", linestyle="--", linewidth=0.7)
    ax.set_ylabel("Rejected within 1,000 days, %")
    ax.legend(frameon=False, fontsize=6.5, loc="upper left", bbox_to_anchor=(1.01, 1.0))
    figkit.save(fig, OUT, "clustering")


def fig_pd() -> None:
    import matplotlib.pyplot as plt

    figkit.style()
    fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.8), constrained_layout=True)
    p = AB["pd_combine"]
    cols = [("all-x1", 1.0), ("all-x1.05", 1.05), ("all-x1.1", 1.1), ("all-x1.25", 1.25)]
    keys = [("product", "Product"), ("average", "Average"), ("average-upper", "Average, upper"), ("average-upper-coarse", "Average, upper, 4 alternatives"),
            ("chi2-one-shot-year-10", "Chi-square at year 10"), ("chi2-every-year", "Chi-square every year")]
    for i, (k, name) in enumerate(keys):
        axes[0].plot([f for _, f in cols], [100 * p[c][k]["ever"] for c, _ in cols], label=name, **S[i % len(S)])
    axes[0].set_xlabel("Every true PD divided by the predicted PD")
    axes[0].set_ylabel("Rejected within 10 years, %")
    axes[0].axhline(5, color="0.0", linestyle="--", linewidth=0.7)
    axes[0].legend(frameon=False, fontsize=6.5, loc="center right")
    rows = PC["rows"]
    rho = [r["rho"] for r in rows]
    for i, (k, name) in enumerate((("e_product", "Product"), ("e_average", "Average"), ("e_average_upper", "Average, upper"),
                                   ("chi2_one_shot_year_10", "Chi-square at year 10"), ("chi2_every_year", "Chi-square every year"))):
        axes[1].plot(rho, [100 * r[k]["ever"] for r in rows], label=name, **S[i % len(S)])
    axes[1].axhline(5, color="0.0", linestyle="--", linewidth=0.7)
    axes[1].set_xlabel(r"Asset correlation $\rho$ (predicted PD correct)")
    axes[1].set_ylabel("Rejected within 10 years, %")
    figkit.save(fig, OUT, "pd-books")


def fig_c11() -> None:
    import matplotlib.pyplot as plt

    figkit.style()
    fig, axes = plt.subplots(1, 3, figsize=(6.9, 2.7), constrained_layout=True)
    wins = [("equity-2007-09", "Equity 2007-09"), ("fx-2008", "FX 2008"), ("calm-2004-06", "Calm 2004-06")]
    for ax, (w, title) in zip(axes, wins):
        rows = C11["windows"][w]["levels"]["0.01"]["models"]
        n_days = C11["windows"][w]["n_days"]
        xs, ys, only_e, only_k = [], [], [], []
        for r in rows:
            e, k = r["e_rate"], r["kupiec_cumulative"]
            if e is not None and k is not None:
                xs.append(k)
                ys.append(e)
            elif e is not None:
                only_e.append(e)
            elif k is not None:
                only_k.append(k)
        ax.plot([1, n_days], [1, n_days], color="0.6", linestyle=":", linewidth=0.8)
        ax.scatter(xs, ys, s=14, color="0.1", label="Both flag")
        ax.scatter([n_days * 1.07] * len(only_e), only_e, s=14, marker="^", color="0.45", label="E-process only")
        ax.scatter(only_k, [n_days * 1.07] * len(only_k), s=14, marker="s", facecolor="none", edgecolor="0.0", label="Kupiec only")
        ax.axvline(250, color="0.7", linewidth=0.6)
        ax.axhline(250, color="0.7", linewidth=0.6)
        ax.set_title(title)
        ax.set_xlabel("Kupiec, all days, first flag (day)")
        ax.set_xlim(0, n_days * 1.15)
        ax.set_ylim(0, n_days * 1.15)
    axes[0].set_ylabel("E-process, first flag (day)")
    axes[0].legend(frameon=False, fontsize=6, loc="upper left")
    figkit.save(fig, OUT, "c11-days")


def fig_c03() -> None:
    import matplotlib.pyplot as plt

    figkit.style()
    fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.6), constrained_layout=True)
    docs = {}
    for stem in C03["cohorts"]:
        docs[stem] = json.loads((figkit.DERIVED / "C03" / f"{stem}.json").read_text(encoding="utf-8"))["outputs"]["sequential"]
    for i, (stem, s) in enumerate(docs.items()):
        m = s["months"]
        avg = [v for v in s["average"]["log_e"]]
        axes[0].plot(m, [np.nan if v is None else v for v in avg], label=stem.replace("fy", "FY"), **S[i % len(S)])
    axes[0].axhline(math.log(20), color="0.0", linestyle="--", linewidth=0.8)
    axes[0].set_yscale("symlog", linthresh=10)
    axes[0].set_xlabel("Age of the vintage, months")
    axes[0].set_ylabel(r"$\log E$, average over vintages")
    axes[0].legend(frameon=False, fontsize=6.5)
    names, vals = [], []
    for stem, c in C03["cohorts"].items():
        for v in c["vintages"]:
            names.append(f"{v['fiscal_year']}")
            vals.append((v["defaults"] - v["predicted_defaults"]) / max(v["predicted_defaults"], 1.0))
    axes[1].bar(range(len(vals)), [100 * v for v in vals], color="0.5", edgecolor="0.0", linewidth=0.5)
    axes[1].axhline(0, color="0.0", linewidth=0.6)
    axes[1].set_xticks(range(len(vals)))
    axes[1].set_xticklabels(names, rotation=90, fontsize=6)
    axes[1].set_ylabel("Charge-offs over predicted, %")
    axes[1].set_xlabel("Vintage (fiscal year)")
    figkit.save(fig, OUT, "c03-paths")


def fig_theory() -> None:
    import matplotlib.pyplot as plt

    figkit.style()
    fig, ax = plt.subplots(figsize=(5.6, 2.9))
    kl = TH["kl"]["rows"]
    f = [r["factor"] for r in kl]
    ax.plot(f, [r["sprt_time"] for r in kl], label=r"$\log 20/\mathrm{KL}$ (log-optimal bet)", **S[1])
    ax.plot(f, [r["mixture_time_bound"] for r in kl], label=r"$(\log 20+\log 8)/\mathrm{KL}$ (mixture of 8)", **S[2])
    mp = {1.5: "rate-x1.5", 2.0: "rate-x2", 3.0: "rate-x3", 4.0: "rate-x4", 6.0: "rate-x6", 10.0: "rate-x10"}
    ax.plot(f, [sc(mp[v])["e_sprt3"]["median_day"] or 1000 for v in f], label=r"Measured median, $3\alpha$ alternative", **S[0])
    ax.plot(f, [sc(mp[v])["e_rate"]["median_day"] or 1000 for v in f], label="Measured median, mixture", **S[3])
    ax.axhline(250, color="0.0", linestyle="--", linewidth=0.7)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xticks(f)
    ax.set_xticklabels([f"{v:g}" for v in f])
    ax.set_xlabel("Hit-rate factor")
    ax.set_ylabel("Days to reject")
    ax.legend(frameon=False, fontsize=6.5)
    figkit.save(fig, OUT, "delay-theory")


def main() -> None:
    for fn in (fig_paths, fig_size_horizon, fig_delay, fig_power_size, fig_clustering, fig_pd, fig_c11, fig_c03, fig_theory):
        fn()
        print("figure:", fn.__name__)


if __name__ == "__main__":
    main()
