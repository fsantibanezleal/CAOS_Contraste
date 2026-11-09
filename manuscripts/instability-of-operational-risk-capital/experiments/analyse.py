"""The measurements of the manuscript: every number it states comes from ``results.json``, written here.

Inputs: ``histories-<variant>.json`` (the capital over the true quantile of every history of the 16 cells, written by
``extract_histories.py`` from the cached arrays that reproduce the committed documents) and ``data/derived/C17/xi-*.json`` (the
truth, the committed summaries and the validation tests). Nothing is typed: a statistic is computed from the histories, then
checked against the committed document where the document holds it.

Computed here (seeds and repetitions in ``SETTINGS``):

* per cell and rung: the median, the interquartile range, the share of histories below the truth, the share within a factor of two
  of it, the dispersion of the logarithm, each with a percentile bootstrap interval over the histories (or a Wilson interval for a
  share);
* the check against the committed percentiles, and the count of the committed ``oprisk.capital_stability`` rows by light;
* the share of histories whose fitted tail index above the collection threshold (and above two, four and eight times it) reaches 1;
* the theory of the manuscript evaluated at the true parameters of each cell: the predicted dispersion of the logarithm of the
  single loss approximation, the predicted interquartile range, the predicted share of histories with a fitted tail index of 1 or
  more, and the history that would bring the interquartile range under the green light of the product;
* the ablation: for each component of the estimation ladder the paired change on the histories where both rungs are defined;
* the precision of the measurement itself: the relative standard deviation of the interquartile range of a cell in the full-sample
  bootstrap (the 2,000 resamples of the cell) and over random subsets of 50 to 500 histories drawn WITH replacement;
* the hypothesis stated before the bake of the robust rungs (``S3_HYPOTHESIS`` of the case parameters): the counts of the cells in which
  the Cramer-von Mises and the bias-robust fits have the smaller spread and the smaller bias than the splice, checked against the
  committed findings F-5 of the four documents;
* the checks behind the reading of the results: the cell of the largest and smallest splice interquartile range, the pattern of the
  histories on which the splice and the truncated lognormal are undefined, the single loss approximation on those histories, the
  agreement of the two mean-corrected rungs on paired histories, and the interquartile range of the theory scaled by the measured median.

Run from the repository root (after ``extract_histories.py``)::

    python manuscripts/instability-of-operational-risk-capital/experiments/analyse.py
"""
from __future__ import annotations

import json
import math
import pathlib
import re

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DERIVED = ROOT / "data" / "derived" / "C17"
VARIANTS = ("xi-0-6", "xi-0-8", "xi-0-96", "xi-1-1")
RUNGS = ("lda_lognormal", "lda_lognormal_truncated", "lda_splice", "sla", "sla_mean_corrected", "scenario",
         "sla_mean_adjusted", "sla_cvm", "sla_obre", "sla_cvm_lognormal")
SETTINGS = {
    "bootstrap_resamples": 2000, "bootstrap_seed": 20261104, "subset_draws": 400, "subset_seed": 20261105, "subset_sizes": [50, 100, 250, 500, 1000],
    "level": 0.999, "z95": 1.959963984540054, "factor": 2.0,
    "green_iqr": 0.25,  # the green limit of the product's capital stability light for the interquartile range over the truth
    "pre_stated": {"sd_relative_error": 0.25, "share_absolute_error": 0.05},  # the criteria of the two theory hypotheses
    # the rule of the hypothesis stated before the bake (data-pipeline/pipeline/cases/c17/params.py S3_HYPOTHESIS, committed 2026-10-29)
    "robust_hypothesis": {"rungs": ["sla_cvm", "sla_obre"], "against": "lda_splice", "holds_at_share": 0.75, "refuted_below_share": 0.5},
}
Z = SETTINGS["z95"]
ALPHA = SETTINGS["level"]


def wilson(k: int, n: int) -> list[float]:
    """The Wilson score interval of a share (Wilson 1927) at 95 percent."""
    if n == 0:
        return [float("nan"), float("nan")]
    p = k / n
    d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return [c - h, c + h]


def norm_cdf(x: float) -> float:
    return 0.5 * math.erfc(-x / math.sqrt(2))


def pct(x: np.ndarray, p: float, axis: int = -1) -> np.ndarray:
    return np.percentile(x, p, axis=axis)


def boot_ci(x: np.ndarray, rng: np.random.Generator, resamples: int) -> dict[str, list[float]]:
    """Percentile bootstrap intervals (95 percent) of the median, the interquartile range and the share below one."""
    idx = rng.integers(0, x.size, size=(resamples, x.size))
    s = x[idx]
    q25, q50, q75 = np.percentile(s, [25, 50, 75], axis=1)
    below = (s < 1.0).mean(axis=1)
    f = lambda v: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]  # noqa: E731
    return {"median": f(q50), "iqr": f(q75 - q25), "below_one": f(below), "iqr_sd": float(np.std(q75 - q25, ddof=1))}


def rung_stats(x: np.ndarray, rng: np.random.Generator, resamples: int) -> dict:
    n = int(x.size)
    if n == 0:
        return {"n_defined": 0}
    q05, q25, q50, q75, q95 = (float(v) for v in np.percentile(x, [5, 25, 50, 75, 95]))
    within = int(((x >= 1 / SETTINGS["factor"]) & (x <= SETTINGS["factor"])).sum())
    below = int((x < 1.0).sum())
    out = {"n_defined": n, "p05": q05, "p25": q25, "median": q50, "p75": q75, "p95": q95, "iqr": q75 - q25,
           "share_below_one": below / n, "share_below_one_ci": wilson(below, n),
           "share_within_factor": within / n, "share_within_factor_ci": wilson(within, n),
           "log_sd": float(np.std(np.log(x), ddof=1)) if n > 1 else float("nan")}
    out["ci"] = boot_ci(x, rng, resamples)
    return out


def doc_summary(capital: dict, rung: str) -> dict | None:
    block = capital[rung]
    return block["summary"] if "summary" in block else block


# ---------------------------------------------------------------------------------------------------------------- theory
def gpd_quantile_capital(xi: float, beta_h: float, h: float, lam: float) -> float:
    """The single loss approximation of a Poisson count of rate ``lam`` and a GPD of location ``h``, scale ``beta_h`` and tail index ``xi``."""
    a = lam / (1 - ALPHA)
    return h + beta_h / xi * (a ** xi - 1.0)


def predicted(xi: float, beta: float, floor: float, lam_floor: float, h: float, years: int) -> dict:
    """The asymptotic dispersion of the logarithm of the single loss approximation fitted by maximum likelihood to the GPD tail.

    ``lam_h`` is the rate of recorded losses and ``k`` their expected number in ``years``. With the maximum likelihood estimates of
    (xi, beta) asymptotically normal with covariance (1 + xi) [[1 + xi, -1], [-1, 2]] / k in (xi, beta / beta) (Smith 1987;
    Hosking and Wallis 1987) and the count independent with Var(ln lambda_hat) = 1 / k, the delta method on ln q gives the variance."""
    surv = (1 + xi * (h - floor) / beta) ** (-1 / xi)
    lam_h = lam_floor * surv
    beta_h = beta + xi * (h - floor)
    k = lam_h * years

    def lnq(x: float, lb: float, ll: float) -> float:
        return math.log(gpd_quantile_capital(x, math.exp(lb), h, math.exp(ll)))

    lb0, ll0 = math.log(beta_h), math.log(lam_h)
    e = 1e-6
    g_xi = (lnq(xi + e, lb0, ll0) - lnq(xi - e, lb0, ll0)) / (2 * e)
    g_b = (lnq(xi, lb0 + e, ll0) - lnq(xi, lb0 - e, ll0)) / (2 * e)
    g_l = (lnq(xi, lb0, ll0 + e) - lnq(xi, lb0, ll0 - e)) / (2 * e)
    v_xi, v_b, c_xb = (1 + xi) ** 2, 2 * (1 + xi), -(1 + xi)
    var_fit = (g_xi ** 2 * v_xi + g_b ** 2 * v_b + 2 * g_xi * g_b * c_xb) / k
    var_count = g_l ** 2 / k
    var = var_fit + var_count
    sd = math.sqrt(var)
    # interquartile range of exp(N(0, sd^2)) with median one: 2 sinh(z_{0.75} sd)
    z75 = 0.6744897501960817
    iqr = 2 * math.sinh(z75 * sd)
    # the history (years) at which the interquartile range reaches the green limit, the variance scaling as 1 / years
    sd_green = math.asinh(SETTINGS["green_iqr"] / 2) / z75
    years_green = years * var / sd_green ** 2
    p_ge_one = 1 - norm_cdf((1 - xi) * math.sqrt(k) / (1 + xi))
    big_l = math.log(lam_h / (1 - ALPHA))
    return {"lam_h": lam_h, "beta_h": beta_h, "k": k, "L": big_l, "ell": big_l - 1 / xi, "grad_xi": g_xi, "grad_lnbeta": g_b, "grad_lnlambda": g_l,
            "var_fit": var_fit, "var_count": var_count, "sd_log": sd, "iqr": iqr, "years_green": years_green,
            "records_green": years_green * lam_h, "share_xi_hat_at_least_one": p_ge_one,
            "sd_log_xi_hat": (1 + xi) / math.sqrt(k)}


# ---------------------------------------------------------------------------------------------------------------- main
def main() -> int:
    rng = np.random.default_rng(SETTINGS["bootstrap_seed"])
    res: dict = {"settings": SETTINGS, "cells": [], "check": {"max_abs_diff_ratio_percentile": 0.0, "max_abs_diff_share": 0.0, "max_abs_diff_xi_share": 0.0},
                 "lights": {}, "variants": {}}
    pooled: dict[str, dict[str, list]] = {r: {"x": []} for r in RUNGS}
    pairs = {r: [] for r in RUNGS}
    comparisons = (("threshold", "lda_lognormal", "lda_lognormal_truncated"), ("heavy_tail", "lda_lognormal_truncated", "lda_splice"),
                   ("closed_form", "lda_splice", "sla"), ("mean_correction", "sla", "sla_mean_corrected"),
                   ("expert_prior", "lda_splice", "scenario"), ("mean_adjusted", "sla", "sla_mean_adjusted"),
                   ("cvm", "sla_mean_adjusted", "sla_cvm"), ("obre", "sla_mean_adjusted", "sla_obre"),
                   ("wrong_family", "sla_cvm", "sla_cvm_lognormal"))
    ab_acc = {name: {"a": [], "b": [], "cells": []} for name, _, _ in comparisons}
    lights = {"green": 0, "amber": 0, "red": 0}
    rel57: list[np.ndarray] = []
    robust_doc_counts: dict[str, dict[str, list[int]]] = {}
    lights_by_rung: dict[str, dict[str, int]] = {}
    for vid in VARIANTS:
        h = json.loads((HERE / f"histories-{vid}.json").read_text(encoding="utf-8"))
        doc = json.loads((DERIVED / f"{vid}.json").read_text(encoding="utf-8"))
        truth_block = doc["outputs"]["truth"]
        xi = float(h["tail_index"])
        sev, freq = truth_block["severity"], truth_block["frequency"]
        res["variants"][vid] = {"tail_index": xi, "truth_eur": h["truth_eur"], "scale_eur": sev["scale_eur"], "floor_eur": sev["location_eur"],
                                "lambda_floor": freq["lambda_per_year"], "mean_eur": truth_block["annual_loss_mean"]["value_eur"],
                                "mc_check": truth_block["annual_loss_quantile"]["mc_check"], "grid_step_eur": truth_block["annual_loss_quantile"]["grid_step_eur"],
                                "seed_first": [c["seed_first"] for c in h["cells"]]}
        for t in doc["tests"]:
            if t["test_id"] == "oprisk.capital_stability":
                lights[t["light"]] += 1
                lights_by_rung.setdefault(t["model_id"], {"green": 0, "amber": 0, "red": 0})[t["light"]] += 1
        for f in doc["findings"]:
            if f["id"] == "F-5":
                got = re.findall(r"smaller spread in (\d+) of (\d+) cells and the smaller bias in (\d+)", f["title"]["en"])
                verdicts = re.findall(r"hypothesis (holds|refuted|inconclusive)", f["title"]["en"])
                robust_doc_counts[vid] = {"counts": [[int(a), int(b), int(c)] for a, b, c in got], "verdicts": verdicts}
        tests_by_cell = {(t["model_id"], t["segment"]): t for t in doc["tests"] if t["test_id"] == "oprisk.capital_stability"}
        for c, dc in zip(h["cells"], doc["outputs"]["cells"], strict=True):
            assert c["id"] == dc["id"]
            cell = {"variant": vid, "tail_index": xi, "id": c["id"], "years": c["years"], "threshold_eur": c["threshold_eur"], "n_replications": c["n_replications"],
                    "n_failed": int(sum(c["failed"])), "n_losses_median": float(np.median(c["n_losses"])), "rungs": {}}
            arr = {r: np.array([np.nan if v is None else v for v in c["ratio"][r]], dtype=float) for r in RUNGS}
            for r in RUNGS:
                x = arr[r][np.isfinite(arr[r])]
                st = rung_stats(x, rng, SETTINGS["bootstrap_resamples"])
                cell["rungs"][r] = st
                s = doc_summary(dc["capital"], r)
                if s is not None and st["n_defined"]:
                    res["check"]["max_abs_diff_ratio_percentile"] = max(res["check"]["max_abs_diff_ratio_percentile"],
                                                                         abs(st["median"] - s["ratio_to_truth"]["median"]) / s["ratio_to_truth"]["median"],
                                                                         abs(st["iqr"] - s["iqr_over_truth"]) / s["iqr_over_truth"])
                    res["check"]["max_abs_diff_share"] = max(res["check"]["max_abs_diff_share"], abs(st["share_below_one"] - s["share_underestimating"]))
                pooled[r]["x"].append(x)
            # the committed light of every rung of this cell
            cell["lights"] = {m: tests_by_cell[(m, c["id"])]["light"] for (m, seg) in tests_by_cell if seg == c["id"]}
            # the fitted tail index profile
            xi_arr = np.array([[np.nan if v is None else v for v in row] for row in c["xi"]], dtype=float)
            prof = []
            for j, mult in enumerate((1, 2, 4, 8)):
                col = xi_arr[:, j]
                ok = np.isfinite(col)
                n = int(ok.sum())
                ge = int((col[ok] >= 1.0).sum())
                prof.append({"multiple": mult, "n_fits": n, "n_at_least_one": ge, "share_at_least_one": ge / n if n else float("nan"),
                             "ci_at_least_one": wilson(ge, n), "median": float(np.median(col[ok])) if n else float("nan"),
                             "p05": float(np.percentile(col[ok], 5)) if n else float("nan"), "p95": float(np.percentile(col[ok], 95)) if n else float("nan")})
            ts = dc["threshold_stability"][0]
            res["check"]["max_abs_diff_xi_share"] = max(res["check"]["max_abs_diff_xi_share"], abs(prof[0]["share_at_least_one"] - ts["share_at_least_one"]))
            cell["tail_profile"] = prof
            # the theory at the true parameters
            cell["theory"] = predicted(xi, sev["scale_eur"], sev["location_eur"], freq["lambda_per_year"], float(c["threshold_eur"]), int(c["years"]))
            # paired comparisons (histories where both rungs are defined)
            for name, a, b in comparisons:
                ok = np.isfinite(arr[a]) & np.isfinite(arr[b])
                if ok.sum() < 20:
                    continue
                ab_acc[name]["a"].append(arr[a][ok])
                ab_acc[name]["b"].append(arr[b][ok])
                ab_acc[name]["cells"].append(f"{vid}:{c['id']}")
            # the precision of the measurement: spread of the IQR over random subsets drawn WITH replacement from the defined histories of
            # the cell (a subset of m histories of the process; without replacement a subset of 500 of 550 shares most of its histories
            # with every other and its spread is shrunk by the finite-population factor), for the sizes that the cell can supply
            sub = {}
            r2 = np.random.default_rng(SETTINGS["subset_seed"] + len(res["cells"]))
            for r in ("lda_splice", "sla"):
                x = arr[r][np.isfinite(arr[r])]
                row = {}
                for m in SETTINGS["subset_sizes"]:
                    if m > x.size:
                        continue
                    vals = []
                    for _ in range(SETTINGS["subset_draws"]):
                        s = r2.choice(x, size=m, replace=True)
                        vals.append(float(np.subtract(*np.percentile(s, [75, 25]))))
                    row[str(m)] = {"mean": float(np.mean(vals)), "sd": float(np.std(vals, ddof=1))}
                sub[r] = row
            # the splice undefined: what the single loss approximation does on those histories (the proxy for the unobservable error of the splice there)
            fail = ~np.isfinite(arr["lda_splice"])
            lsla = np.abs(np.log(arr["sla"]))
            cell["splice_undefined"] = {"n_undefined": int(fail.sum()),
                                        "median_abs_log_sla_undefined": float(np.median(lsla[fail])) if fail.any() else float("nan"),
                                        "median_abs_log_sla_defined": float(np.median(lsla[~fail]))}
            # the two mean-corrected rungs on paired histories: they differ by one severity mean
            ok57 = np.isfinite(arr["sla_mean_corrected"]) & np.isfinite(arr["sla_mean_adjusted"])
            if ok57.any():
                rel = np.abs(arr["sla_mean_adjusted"][ok57] / arr["sla_mean_corrected"][ok57] - 1)
                rel57.append(rel)
                cell["rung5_vs_rung7"] = {"n_paired": int(ok57.sum()), "median_rel_diff": float(np.median(rel)), "max_rel_diff": float(rel.max())}
            cell["subset_iqr"] = sub
            res["cells"].append(cell)
    # claims of the SDD item, evaluated
    iqr_splice = [c["rungs"]["lda_splice"]["iqr"] for c in res["cells"]]
    six = ("lda-lognormal", "lda-lognormal-truncated", "lda-splice", "sla", "sla-mean-corrected", "scenario")
    res["lights"] = {"total": sum(lights.values()), **lights, "by_rung": lights_by_rung,
                     "six_rung_rows": sum(sum(v.values()) for k, v in lights_by_rung.items() if k in six),
                     "six_rung_red": sum(v["red"] for k, v in lights_by_rung.items() if k in six)}
    res["splice_iqr_range"] = [min(iqr_splice), max(iqr_splice)]
    # pooled statistics per rung over the 16 cells
    res["pooled"] = {}
    for r in RUNGS:
        x = np.concatenate(pooled[r]["x"]) if pooled[r]["x"] else np.array([])
        within = int(((x >= 0.5) & (x <= 2.0)).sum())
        res["pooled"][r] = {"n_defined": int(x.size), "n_histories": 16000, "share_defined": x.size / 16000,
                            "share_within_factor": within / x.size if x.size else float("nan"),
                            "share_within_factor_ci": wilson(within, int(x.size)),
                            "mean_cell_iqr": float(np.mean([c["rungs"][r]["iqr"] for c in res["cells"] if c["rungs"][r]["n_defined"]])) if x.size else float("nan"),
                            "mean_cell_median": float(np.mean([c["rungs"][r]["median"] for c in res["cells"] if c["rungs"][r]["n_defined"]])) if x.size else float("nan")}
    # the ablation
    res["ablation"] = {}
    brng = np.random.default_rng(SETTINGS["bootstrap_seed"] + 1)
    for name, a, b in comparisons:
        xa, xb = np.concatenate(ab_acc[name]["a"]), np.concatenate(ab_acc[name]["b"])
        n = int(xa.size)
        wa = ((xa >= 0.5) & (xa <= 2.0))
        wb = ((xb >= 0.5) & (xb <= 2.0))
        idx = brng.integers(0, n, size=(SETTINGS["bootstrap_resamples"], n))
        diff = wb[idx].mean(axis=1) - wa[idx].mean(axis=1)
        la, lb = np.log(xa), np.log(xb)
        dsd = [np.std(lb[i], ddof=1) - np.std(la[i], ddof=1) for i in idx[:400]]
        res["ablation"][name] = {
            "from": a, "to": b, "n_paired": n, "n_cells": len(ab_acc[name]["cells"]),
            "from_within": float(wa.mean()), "to_within": float(wb.mean()),
            "from_within_ci": wilson(int(wa.sum()), n), "to_within_ci": wilson(int(wb.sum()), n),
            "delta_within": float(wb.mean() - wa.mean()), "delta_within_ci": [float(np.percentile(diff, 2.5)), float(np.percentile(diff, 97.5))],
            "from_median_log": float(np.median(la)), "to_median_log": float(np.median(lb)),
            "from_log_sd": float(np.std(la, ddof=1)), "to_log_sd": float(np.std(lb, ddof=1)),
            "delta_log_sd_ci": [float(np.percentile(dsd, 2.5)), float(np.percentile(dsd, 97.5))],
            "from_below": float((xa < 1).mean()), "to_below": float((xb < 1).mean())}
    # the hypothesis stated before the bake of the robust rungs, with the rule of the case parameters, over the 16 cells and by tail index
    rh = SETTINGS["robust_hypothesis"]

    def verdict(n: int, spread: int, bias: int) -> str:
        if n == 0:
            return "inconclusive"
        if min(spread, bias) / n < rh["refuted_below_share"]:
            return "refuted"
        return "holds" if min(spread, bias) / n >= rh["holds_at_share"] else "inconclusive"

    res["robust_hypothesis"] = {"rule": rh, "by_rung": {}}
    matches_doc = True
    for k, rung in enumerate(rh["rungs"]):
        per_var = {}
        tot = [0, 0, 0]
        for vid in VARIANTS:
            n = sp = bi = 0
            for c in res["cells"]:
                if c["variant"] != vid:
                    continue
                a, b = c["rungs"][rung], c["rungs"][rh["against"]]
                if not a["n_defined"] or not b["n_defined"]:
                    continue
                n += 1
                sp += a["iqr"] < b["iqr"]
                bi += abs(math.log(a["median"])) < abs(math.log(b["median"]))
            per_var[vid] = {"cells": n, "smaller_spread": sp, "smaller_bias": bi, "verdict": verdict(n, sp, bi)}
            tot = [tot[0] + n, tot[1] + sp, tot[2] + bi]
            matches_doc &= robust_doc_counts[vid]["counts"][k] == [sp, n, bi] and robust_doc_counts[vid]["verdicts"][k] == per_var[vid]["verdict"]
        res["robust_hypothesis"]["by_rung"][rung] = {"cells": tot[0], "smaller_spread": tot[1], "smaller_bias": tot[2], "verdict": verdict(*tot),
                                                     "by_variant": per_var}
    res["robust_hypothesis"]["matches_committed_findings"] = bool(matches_doc)
    # the cells of the smallest and the largest splice interquartile range
    ext = {}
    for key, fn in (("min", min), ("max", max)):
        c = fn(res["cells"], key=lambda c: c["rungs"]["lda_splice"]["iqr"])
        s_ = c["rungs"]["lda_splice"]
        ext[key] = {"variant": c["variant"], "tail_index": c["tail_index"], "id": c["id"], "years": c["years"], "threshold_eur": c["threshold_eur"],
                    "n_defined": s_["n_defined"], "iqr": s_["iqr"], "iqr_ci": s_["ci"]["iqr"]}
    res["splice_iqr_extremes"] = ext
    # where the splice and the truncated lognormal are undefined: the higher threshold against the lower one, in the 8 pairs of cells
    pat = {}
    for rung in ("lda_splice", "lda_lognormal_truncated"):
        fewer = more = same = 0
        for vid in VARIANTS:
            for yrs in (5, 10):
                lo = next(c for c in res["cells"] if c["variant"] == vid and c["years"] == yrs and c["threshold_eur"] == 10000)["rungs"][rung]["n_defined"]
                hi = next(c for c in res["cells"] if c["variant"] == vid and c["years"] == yrs and c["threshold_eur"] == 20000)["rungs"][rung]["n_defined"]
                fewer += hi < lo
                more += hi > lo
                same += hi == lo
        pat[rung] = {"pairs": 8, "higher_threshold_fewer": fewer, "higher_threshold_more": more, "equal": same}
    res["undefined_pattern"] = pat
    su = [c["splice_undefined"] for c in res["cells"] if c["splice_undefined"]["n_undefined"] > 0]
    res["splice_undefined_proxy"] = {"cells_with_undefined": len(su),
                                     "cells_sla_further_on_undefined": sum(1 for u in su if u["median_abs_log_sla_undefined"] > u["median_abs_log_sla_defined"])}
    # the two mean-corrected rungs on paired histories
    r57 = np.concatenate(rel57) if rel57 else np.array([])
    res["rung5_vs_rung7"] = {"n_paired": int(r57.size), "cells": len(rel57), "median_rel_diff": float(np.median(r57)), "p95_rel_diff": float(np.percentile(r57, 95)),
                             "max_rel_diff": float(r57.max()), "n_defined_by_cell": {f"{c['variant']}:{c['id']}": [c["rungs"]["sla_mean_corrected"]["n_defined"],
                                                                                                                  c["rungs"]["sla_mean_adjusted"]["n_defined"]] for c in res["cells"]}}
    # the theory against the measurement
    th = []
    for c in res["cells"]:
        m = c["rungs"]["sla"]
        t = c["theory"]
        th.append({"variant": c["variant"], "id": c["id"], "tail_index": c["tail_index"], "sd_measured": m["log_sd"], "sd_predicted": t["sd_log"],
                   "relative_error": (t["sd_log"] - m["log_sd"]) / m["log_sd"], "iqr_measured": m["iqr"], "iqr_predicted": t["iqr"],
                   "median_measured": m["median"], "iqr_predicted_scaled": t["iqr"] * m["median"], "ell": t["ell"], "L": t["L"],
                   "share_measured": c["tail_profile"][0]["share_at_least_one"], "share_predicted": t["share_xi_hat_at_least_one"],
                   "share_abs_error": abs(c["tail_profile"][0]["share_at_least_one"] - t["share_xi_hat_at_least_one"]),
                   "years_green": t["years_green"], "records_green": t["records_green"]})
    res["theory_check"] = th
    res["theory_verdict"] = {
        "max_relative_error_sd": max(abs(r["relative_error"]) for r in th),
        "max_abs_error_share_near_one": max(r["share_abs_error"] for r in th if r["tail_index"] in (0.96, 1.1)),
        "sd_held": max(abs(r["relative_error"]) for r in th) <= SETTINGS["pre_stated"]["sd_relative_error"],
        "share_held": max(r["share_abs_error"] for r in th if r["tail_index"] in (0.96, 1.1)) <= SETTINGS["pre_stated"]["share_absolute_error"],
        "mean_relative_error_sd": float(np.mean([r["relative_error"] for r in th])),
        "mean_abs_relative_error_sd": float(np.mean([abs(r["relative_error"]) for r in th]))}
    # the shares of the SDD item
    s096 = [c["tail_profile"][0]["share_at_least_one"] for c in res["cells"] if c["tail_index"] == 0.96]
    s11 = [1 - c["tail_profile"][0]["share_at_least_one"] for c in res["cells"] if c["tail_index"] == 1.1]
    res["infinite_mean"] = {"xi_0_96_conclude_infinite": [min(s096), max(s096)], "xi_1_1_conclude_finite": [min(s11), max(s11)]}
    (HERE / "results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("wrote results.json", (HERE / "results.json").stat().st_size, "bytes")
    print("check vs committed:", res["check"])
    print("lights:", {k: v for k, v in res["lights"].items() if k != "by_rung"})
    print("splice IQR range:", res["splice_iqr_range"])
    print("infinite mean:", res["infinite_mean"])
    print("theory verdict:", res["theory_verdict"])
    print("robust hypothesis:", {k: {a: b for a, b in v.items() if a != "by_variant"} for k, v in res["robust_hypothesis"]["by_rung"].items()},
          "matches committed findings:", res["robust_hypothesis"]["matches_committed_findings"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
