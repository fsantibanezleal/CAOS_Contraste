"""Figures of the credit-capital section of the technical report (sections/10-credit-capital.tex).

Every figure is a vector PDF drawn from the committed documents of case C10 (``data/derived/C10``) through ``figkit``;
the IRB curves of the last figure are evaluated by the ``riskvalidation`` engine. Output: ``figures/credit-capital-*.pdf``.

Run from the repository root::

    E:/_venvs/contraste-u16-i/Scripts/python.exe manuscripts/contraste-technical-report/figures/make_credit-capital.py
"""
from __future__ import annotations

import argparse
import importlib.util
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import figkit  # noqa: E402

_spec = importlib.util.spec_from_file_location("cc_tables", HERE.parent / "tables" / "make_credit-capital.py")
T = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(T)  # type: ignore[union-attr]

LOANS = T.LOANS
W = 6.3  # text width in inches


def fig_tail(D: dict, out: pathlib.Path) -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 3, figsize=(W, 4.3), sharex=True)
    qstyle = {0.5: (":", "median"), 0.95: ("--", "95%"), 0.99: ("-.", "99%"), 0.999: ("-", "99.9%")}
    for ax, (lid, _, name) in zip(axes.flat, LOANS):
        o = D[lid]["outputs"]
        yrs = [a["year"] for a in o["annual_rates"] if a["loss_rate"] is not None]
        val = [100 * a["loss_rate"] for a in o["annual_rates"] if a["loss_rate"] is not None]
        win = [a["window"] for a in o["annual_rates"] if a["loss_rate"] is not None]
        fit_x = [y for y, w in zip(yrs, win) if w == "fit"]
        fit_y = [v for v, w in zip(val, win) if w == "fit"]
        ev_x = [y for y, w in zip(yrs, win) if w == "evaluation"]
        ev_y = [v for v, w in zip(val, win) if w == "evaluation"]
        ax.plot(fit_x, fit_y, "o", color="0.0", markersize=3, label="fit window")
        ax.plot(ev_x, ev_y, "s", mfc="white", mec="0.0", markersize=4, label="evaluation window")
        for q in o["fitted_distribution"]["quantiles"]:
            if q["level"] in qstyle:
                ax.axhline(100 * q["value"], color="0.35", linestyle=qstyle[q["level"]][0], linewidth=0.8)
        ax.axvline(2006.5, color="0.6", linewidth=0.6)
        ax.set_title(name, fontsize=8)
        ax.set_ylim(bottom=0)
        ax.tick_params(axis="x", labelrotation=45)
    ax = axes.flat[5]
    ax.axis("off")
    h = [plt.Line2D([], [], marker="o", color="0.0", linestyle="", markersize=3, label="fit window rate"),
         plt.Line2D([], [], marker="s", mfc="white", mec="0.0", color="0.0", linestyle="", markersize=4, label="evaluation window rate")]
    h += [plt.Line2D([], [], color="0.35", linestyle=s, linewidth=0.8, label=f"fitted {lab} quantile") for s, lab in qstyle.values()]
    ax.legend(handles=h, loc="center", frameon=False)
    for ax in axes[:, 0]:
        ax.set_ylabel("loss rate (% per year)")
    fig.tight_layout()
    figkit.save(fig, out, "credit-capital-tail")


def fig_correlation(D: dict, out: pathlib.Path) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(W, 2.9))
    for i, (lid, _, name) in enumerate(LOANS):
        o = D[lid]["outputs"]
        ml, mo, irb = o["fit"]["maximum_likelihood"]["rho"], o["fit"]["moments"]["rho"], o["irb_reference"]
        y = len(LOANS) - 1 - i
        ax.errorbar(ml["estimate"], y + 0.15, xerr=[[ml["estimate"] - ml["ci_low"]], [ml["ci_high"] - ml["estimate"]]], fmt="o", color="0.0",
                    capsize=2, label="maximum likelihood, profile interval" if i == 0 else None)
        ax.errorbar(mo["estimate"], y - 0.15, xerr=[[mo["estimate"] - mo["ci_low"]], [mo["ci_high"] - mo["estimate"]]], fmt="s", color="0.45",
                    mfc="white", capsize=2, label="moments, bootstrap interval" if i == 0 else None)
        ax.plot(irb["irb_correlation"], y, marker="D", color="0.0", linestyle="", markersize=6, label="IRB correlation" if i == 0 else None)
    ax.set_yticks(range(len(LOANS)))
    ax.set_yticklabels([n for _, _, n in LOANS][::-1])
    ax.set_xscale("log")
    ax.set_xlabel("asset correlation $\\rho$ (log scale)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=3, frameon=False, fontsize=7)
    figkit.save(fig, out, "credit-capital-correlation")


def fig_profile(D: dict, out: pathlib.Path) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(W, 3.0))
    cut = None
    for k, (lid, _, name) in enumerate(LOANS):
        p = D[lid]["outputs"]["profile_likelihood"]
        rho = np.array(p["rho"])
        ll = np.array(p["log_likelihood"]) - p["max_log_likelihood"]
        cut = p["cutoff"] - p["max_log_likelihood"]
        ax.plot(rho, ll, label=name, **{kk: v for kk, v in figkit.STYLES[k].items() if kk != "marker"})
    ax.axhline(cut, color="0.5", linewidth=0.8)
    ax.text(ax.get_xlim()[1] * 0.0 + 0.0025, cut + 0.12, "95% likelihood-ratio cutoff", fontsize=7, color="0.3")
    ax.set_xscale("log")
    ax.set_ylim(-6, 0.3)
    ax.set_xlabel("asset correlation $\\rho$ (log scale)")
    ax.set_ylabel("profile log-likelihood minus maximum")
    ax.legend(frameon=False, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=3)
    figkit.save(fig, out, "credit-capital-profile")


def fig_ladder(D: dict, out: pathlib.Path) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(W, 3.3))
    x = np.arange(len(T.RUNGS))
    for k, (lid, _, name) in enumerate(LOANS):
        base = T.meas(D[lid], "c1-lhp", 0.999)["var"]
        y, e = [], []
        for _, rid, _ in T.RUNGS:
            m = T.meas(D[lid], rid, 0.999)
            y.append(m["var"] / base)
            e.append(1.96 * (m["var_se"] or 0.0) / base)
        st = figkit.STYLES[k]
        ax.errorbar(x + 0.08 * (k - 2), y, yerr=e, fmt=st["marker"], color=st["color"], capsize=2, markersize=4, label=name)
    ax.axhline(1.0, color="0.7", linewidth=0.6)
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels([lab for _, _, lab in T.RUNGS], rotation=20, fontsize=7)
    ax.set_ylabel("99.9% VaR over the large-portfolio VaR")
    ax.set_ylim(0.8, 60)
    ax.legend(frameon=False, fontsize=7, ncol=3, loc="upper left")
    figkit.save(fig, out, "credit-capital-ladder")


def fig_ga(D: dict, out: pathlib.Path) -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(W, 2.8), sharey=True)
    for ax, (lid, _, name) in zip(axes, (LOANS[3], LOANS[4])):
        rows = D[lid]["outputs"]["granularity"]["by_n_names"]
        n = [r["n_names"] for r in rows]
        ax.plot(n, [100 * r["ga"] for r in rows], "o-", color="0.0", label="granularity adjustment (formula)")
        ax.plot(n, [100 * r["truth_ga"] for r in rows], "s--", color="0.45", mfc="white", label="CreditRisk+ recursion (reference)")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_title(name, fontsize=8)
        ax.set_xlabel("number of identical names $n$")
    axes[0].set_ylabel("gap above the large-portfolio VaR (% of exposure)")
    axes[0].legend(frameon=False, fontsize=7, loc="lower left")
    fig.tight_layout()
    figkit.save(fig, out, "credit-capital-granularity")


def fig_sizepower(D: dict, out: pathlib.Path) -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(W, 3.0), sharey=True)
    for ax, key, years in zip(axes, ("grid-22", "grid-40"), (22, 40)):
        cells = D[key]["outputs"]["cells"]
        rho = np.array([c["known_rho"] for c in cells])
        for k, est in enumerate(("maximum-likelihood", "moments")):
            r = np.array([next(e for e in c["estimators"] if e["estimator"] == est)["rejection_rate"] for c in cells])
            lo = np.array([next(e for e in c["estimators"] if e["estimator"] == est)["rejection_ci_low"] for c in cells])
            hi = np.array([next(e for e in c["estimators"] if e["estimator"] == est)["rejection_ci_high"] for c in cells])
            st = figkit.STYLES[k]
            ax.errorbar(rho + 0.0015 * (k - 0.5), r, yerr=[r - lo, hi - r], color=st["color"], linestyle=st["linestyle"], marker=st["marker"],
                        capsize=1.5, label="maximum likelihood" if k == 0 else "method of moments")
        ax.axhline(0.05, color="0.6", linewidth=0.7)
        ax.axvline(0.12, color="0.6", linewidth=0.7, linestyle=":")
        ax.set_title(f"series of {years} years", fontsize=8)
        ax.set_xlabel("known asset correlation $\\rho$")
    axes[0].set_ylabel("rejection rate of $H_0:\\rho=0.12$")
    axes[0].legend(frameon=False, fontsize=7, loc="upper center")
    fig.tight_layout()
    figkit.save(fig, out, "credit-capital-sizepower")


def fig_exceedance(D: dict, out: pathlib.Path) -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 3, figsize=(W, 4.4))
    show = (("c1-lhp", "LHP"), ("c2-gaussian-1f", "Gaussian 1F"), ("c2-gaussian-mf", "Gaussian 2F"), ("c3-student-t", "Student-t"),
            ("c4-creditrisk-plus", "CreditRisk+"))
    for ax, (lid, _, name) in zip(axes.flat, LOANS):
        for k, (rid, lab) in enumerate(show):
            dist = T.rung(D[lid], rid)["distribution"]
            loss = np.array(dist["loss"]) / 1e6
            sf = 1.0 - np.array(dist["cdf"])
            keep = sf > 1e-5
            st = figkit.STYLES[k]
            ax.plot(loss[keep], sf[keep], color=st["color"], linestyle=st["linestyle"], label=lab)
        ax.axhline(1e-3, color="0.7", linewidth=0.6)
        ax.set_yscale("log")
        ax.set_ylim(1e-4, 1.0)
        ax.set_title(name, fontsize=8)
        ax.set_xlabel("loss (million USD)")
    for ax in axes[:, 0]:
        ax.set_ylabel("probability of exceeding")
    ax = axes.flat[5]
    ax.axis("off")
    h = [plt.Line2D([], [], color=figkit.STYLES[k]["color"], linestyle=figkit.STYLES[k]["linestyle"], label=lab) for k, (_, lab) in enumerate(show)]
    h.append(plt.Line2D([], [], color="0.7", linewidth=0.6, label="probability 0.001 (the 99.9% level)"))
    ax.legend(handles=h, loc="center", frameon=False, fontsize=7)
    fig.tight_layout()
    figkit.save(fig, out, "credit-capital-exceedance")


def fig_irb(D: dict, out: pathlib.Path) -> None:
    import matplotlib.pyplot as plt
    from riskvalidation.regulatory import irb

    fig, ax = plt.subplots(figsize=(W, 3.3))
    pds = np.geomspace(0.0005, 0.2, 60)
    for k, (lid, _, name) in enumerate(LOANS):
        cls = D[lid]["outputs"]["irb_reference"]["asset_class"]
        kw = {} if cls in ("residential_mortgage", "qrre", "other_retail") else {"maturity": 2.5}
        curve = [100 * irb.capital_requirement(cls, float(p), 0.45, **kw).k for p in pds]
        st = figkit.STYLES[k]
        ax.plot(100 * pds, curve, color=st["color"], linestyle=st["linestyle"], label=f"{name} ({cls.replace('_', ' ')})")
        i = D[lid]["outputs"]["irb_reference"]
        ax.plot(100 * i["pd"], 100 * i["k_irb"], marker=st["marker"], color=st["color"], linestyle="", markersize=6)
        ax.plot(100 * i["pd"], 100 * i["ec_lhp_fitted"], marker=st["marker"], mfc="white", mec=st["color"], linestyle="", markersize=6)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("probability of default (%)")
    ax.set_ylabel("capital per unit of exposure $K$ (%)")
    ax.legend(frameon=False, fontsize=6.5, loc="lower right")
    figkit.save(fig, out, "credit-capital-irb")


def run(out: pathlib.Path) -> None:
    figkit.style()
    D = T.load()
    for fn in (fig_tail, fig_correlation, fig_profile, fig_ladder, fig_ga, fig_sizepower, fig_exceedance, fig_irb):
        fn(D, out)
    print(f"credit-capital: 8 figures -> {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", type=pathlib.Path, default=HERE)
    run(ap.parse_args().out_dir)
