"""Phase 2 of the experiments: turn the cached statistic rows into ``results.json``, the only source of every number the manuscript
reports (its tables and figures are written from this file by ``make_tables.py`` and ``make_figures.py``).

    python manuscripts/scale-and-level-complement-to-the-pla-test/experiments/analyse.py \
        [--cache <temp root>/contraste-scale-and-level/cache]

Sections of the output: ``thresholds``, ``main`` (the six variants of the committed bake), ``repeats`` (five further independent
bakes), ``ladder`` (stale-volatility lags), ``auc``, ``by_size`` (power against size), ``ablation``, ``altnull``, ``xform``,
``theory`` (the checks of the propositions), ``reconciliation`` (the engine statistics against the committed C13 documents).
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

import numpy as np
from scipy import stats

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import stats_core as sc  # noqa: E402
import theory  # noqa: E402
from riskvalidation.market import frtb  # noqa: E402

# The cache lives in the device's temp root (CAOS_TEMP_ROOT, as the pipeline reads it) or where --cache says.
DEFAULT_CACHE = (pathlib.Path(os.environ["CAOS_TEMP_ROOT"]) / "contraste-scale-and-level" / "cache"
                 if os.environ.get("CAOS_TEMP_ROOT") else None)
OUT = HERE / "results.json"
IDS = tuple(sc.params.IDS)
PLANTED = IDS[1:]
LADDER = (2, 5, 10, 20, 40, 80)
REPEAT_SEEDS = (23, 33, 43, 53, 63)
NULL_SEEDS = tuple(range(5013, 5023))
SIZE = 0.01
SIZES = (0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2)
#: calibrated single statistics: name in COLUMNS (each at the per-statistic size)
SINGLE = ("wald_hc3", "abs_spearman", "roll20", "wald_ols", "wald_var", "ljung_box_sq", "cc_975", "ks_reg", "spearman_reg")
PROPOSED = ("wald_hc3", "abs_spearman", "roll20")
DETECTORS = ("pla", "ks_alone", "ks_cal", "spearman_cal", "desk", "cc_975", "wald_ols", "wald_var", "ljung_box_sq", "wald_hc3", "abs_spearman", "roll20",
             "union", "union_pla")


class Cache:
    def __init__(self, folder: pathlib.Path) -> None:
        self.folder = folder

    def get(self, stem: str) -> np.ndarray:
        return np.load(self.folder / f"{stem}.npy")


def col(a: np.ndarray, name: str) -> np.ndarray:
    return a[:, sc.IDX[name]]


def rate(flags: np.ndarray) -> dict:
    k, n = int(flags.sum()), int(flags.size)
    lo, hi = sc.wilson(k, n)
    return {"k": k, "n": n, "rate": k / n, "lo": lo, "hi": hi}


class Rules:
    """The thresholds calibrated on the null pool and the flags of every detector on a block of statistic rows."""

    def __init__(self, null: np.ndarray) -> None:
        self.null = null
        self.n = null.shape[0]
        self.single = {s: sc.critical(col(null, s), SIZE, sc.is_high(s)) for s in SINGLE}
        self.union = {s: sc.critical(col(null, s), SIZE / 3, sc.is_high(s)) for s in PROPOSED}

    def thr(self, name: str, p: float) -> float:
        return sc.critical(col(self.null, name), p, sc.is_high(name))

    def flags(self, a: np.ndarray) -> dict[str, np.ndarray]:
        f: dict[str, np.ndarray] = {}
        f["pla"] = col(a, "zone") > 0
        f["ks_alone"] = col(a, "zone_ks") > 0
        f["desk"] = (col(a, "exc_99") > frtb.desk_exception_limit(0.01)) | (col(a, "exc_975") > frtb.desk_exception_limit(0.025))
        for s in ("cc_975", "wald_ols", "wald_var", "ljung_box_sq", "wald_hc3", "abs_spearman", "roll20"):
            f[s] = sc.flag(col(a, s), self.single[s], sc.is_high(s))
        f["ks_cal"] = sc.flag(col(a, "ks_reg"), self.single["ks_reg"], True)
        f["spearman_cal"] = sc.flag(col(a, "spearman_reg"), self.single["spearman_reg"], False)
        f["union"] = np.zeros(a.shape[0], dtype=bool)
        for s in PROPOSED:
            f["union"] |= sc.flag(col(a, s), self.union[s], sc.is_high(s))
        f["union_pla"] = f["union"] | f["pla"]
        return f


def union_flags(null: np.ndarray, a: np.ndarray, names: tuple[str, ...], size: float, correction: bool) -> np.ndarray:
    p = size / len(names) if correction else size
    out = np.zeros(a.shape[0], dtype=bool)
    for s in names:
        out |= sc.flag(col(a, s), sc.critical(col(null, s), p, sc.is_high(s)), sc.is_high(s))
    return out


def auc(pos: np.ndarray, neg: np.ndarray, high: bool, boot: int = 1000, seed: int = 0) -> dict:
    """Area under the ROC curve of a score (flagging on large values when ``high``, else on small ones) with a bootstrap interval."""
    if not high:
        pos, neg = -pos, -neg

    def one(p: np.ndarray, n: np.ndarray) -> float:
        r = stats.rankdata(np.concatenate([p, n]))
        return float((r[: p.size].sum() - p.size * (p.size + 1) / 2) / (p.size * n.size))

    rng = np.random.default_rng(seed)
    bs = [one(rng.choice(pos, pos.size), rng.choice(neg, neg.size)) for _ in range(boot)]
    return {"auc": one(pos, neg), "lo": float(np.quantile(bs, 0.025)), "hi": float(np.quantile(bs, 0.975))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=pathlib.Path, default=DEFAULT_CACHE, required=DEFAULT_CACHE is None,
                    help="cache folder; defaults to $CAOS_TEMP_ROOT/contraste-scale-and-level/cache")
    cache = Cache(ap.parse_args().cache)
    null = np.vstack([cache.get(f"null_{cs}") for cs in NULL_SEEDS])
    rules = Rules(null)
    res: dict = {"n_null": int(null.shape[0]), "size": SIZE}

    # thresholds -------------------------------------------------------------------------------------------------------------
    res["thresholds"] = {"per_statistic": rules.single, "union": rules.union,
                         "null_mean": {s: float(col(null, s).mean()) for s in sc.COLUMNS}}

    # main: the committed bake -----------------------------------------------------------------------------------------------
    committed = {d: cache.get(f"committed_{d}") for d in IDS}
    res["main"] = {d: {k: rate(v) for k, v in rules.flags(committed[d]).items()} for d in IDS}
    res["main_stat_means"] = {d: {s: float(col(committed[d], s).mean()) for s in
                                  ("wald_hc3", "abs_spearman", "roll20", "slope", "intercept", "roll20_pearson", "spearman_reg", "ks_reg")}
                              for d in IDS}

    # repeats: five further independent bakes --------------------------------------------------------------------------------
    rep: dict = {}
    for d in IDS:
        per = {k: [] for k in DETECTORS}
        for cs in REPEAT_SEEDS:
            f = rules.flags(cache.get(f"repeat_{cs}_{d}"))
            for k in DETECTORS:
                per[k].append(float(f[k].mean()))
        rep[d] = {k: {"values": v, "mean": float(np.mean(v)), "sd": float(np.std(v, ddof=1)), "min": float(min(v)), "max": float(max(v))}
                  for k, v in per.items()}
    res["repeats"] = {"case_seeds": list(REPEAT_SEEDS), "by_variant": rep}

    # the lag ladder ---------------------------------------------------------------------------------------------------------
    lag_blocks = {lag: (committed["stale-volatility"] if lag == 20 else cache.get(f"ladder_{lag}")) for lag in LADDER}
    res["ladder"] = [{"lag": lag, **{k: rate(v) for k, v in rules.flags(a).items()},
                      "mean": {s: float(col(a, s).mean()) for s in ("wald_hc3", "abs_spearman", "roll20", "slope", "roll20_pearson")}}
                     for lag, a in lag_blocks.items()]

    # AUC against the held-out null ------------------------------------------------------------------------------------------
    held = committed["none"]
    res["auc"] = {}
    for lag in (5, 10, 20):
        a = lag_blocks[lag]
        res["auc"][str(lag)] = {s: auc(col(a, s), col(held, s), sc.is_high(s)) for s in
                                ("roll20", "abs_spearman", "wald_hc3", "wald_ols", "wald_var", "ljung_box_sq", "cc_975", "ks_reg", "spearman_reg")}

    # power against size -----------------------------------------------------------------------------------------------------
    by_size = []
    for size in SIZES:
        row = {"size": size}
        for s in SINGLE:
            thr = sc.critical(col(null, s), size, sc.is_high(s))
            row[s] = {"power_l20": float(sc.flag(col(lag_blocks[20], s), thr, sc.is_high(s)).mean()),
                      "power_l10": float(sc.flag(col(lag_blocks[10], s), thr, sc.is_high(s)).mean()),
                      "held_out": float(sc.flag(col(held, s), thr, sc.is_high(s)).mean())}
        by_size.append(row)
    res["by_size"] = by_size

    # ablation ---------------------------------------------------------------------------------------------------------------
    configs = [
        ("full", ("wald_hc3", "abs_spearman", "roll20"), True),
        ("no_wald", ("abs_spearman", "roll20"), True),
        ("no_abs", ("wald_hc3", "roll20"), True),
        ("no_roll", ("wald_hc3", "abs_spearman"), True),
        ("wald_only", ("wald_hc3",), True),
        ("abs_only", ("abs_spearman",), True),
        ("roll_only", ("roll20",), True),
        ("window5", ("roll5",), True),
        ("window10", ("roll10",), True),
        ("window40", ("roll40",), True),
        ("window60", ("roll60",), True),
        ("ols_wald", ("wald_ols", "abs_spearman", "roll20"), True),
        ("no_correction", ("wald_hc3", "abs_spearman", "roll20"), False),
        ("multi_window", ("roll5", "roll10", "roll20", "roll40"), True),
    ]
    targets = {**{f"stale{lag}": lag_blocks[lag] for lag in (5, 10, 20, 40)}, **{d: committed[d] for d in PLANTED if d != "stale-volatility"}}
    abl = []
    for name, names, corr in configs:
        row = {"config": name, "statistics": list(names), "correction": corr,
               "held_out": rate(union_flags(null, held, names, SIZE, corr))}
        row["power"] = {t: rate(union_flags(null, a, names, SIZE, corr)) for t, a in targets.items()}
        abl.append(row)
    pla_row = {"config": "full_plus_pla", "statistics": list(PROPOSED), "correction": True,
               "held_out": rate(union_flags(null, held, PROPOSED, SIZE, True) | (col(held, "zone") > 0)),
               "power": {t: rate(union_flags(null, a, PROPOSED, SIZE, True) | (col(a, "zone") > 0)) for t, a in targets.items()}}
    abl.append(pla_row)
    res["ablation"] = abl

    # alternative nulls: thresholds unchanged --------------------------------------------------------------------------------
    alt = {}
    for name in ("phi090", "phi0995", "sd020", "sd050", "res005", "res030"):
        a = cache.get(f"altnull_{name}")
        f = rules.flags(a)
        alt[name] = {k: rate(f[k]) for k in ("pla", "wald_hc3", "abs_spearman", "roll20", "union", "wald_ols", "wald_var", "ljung_box_sq", "cc_975")}
    # the baseline null at the same case seed (the repeat bake, variant none) is the reference
    f0 = rules.flags(cache.get("repeat_23_none"))
    alt["baseline"] = {k: rate(f0[k]) for k in ("pla", "wald_hc3", "abs_spearman", "roll20", "union", "wald_ols", "wald_var", "ljung_box_sq", "cc_975")}
    res["altnull"] = alt

    # constant mis-scale and level error --------------------------------------------------------------------------------------
    xf = {}
    for name in ("scale080", "scale090", "scale110", "scale125", "shift010", "shift020"):
        a = cache.get(f"xform_{name}")
        f = rules.flags(a)
        # every detector the other experiments run, so that a statement about "the detectors" covers all of them
        xf[name] = {k: rate(f[k]) for k in DETECTORS}
        xf[name]["mean_slope"] = float(col(a, "slope").mean())
        xf[name]["mean_intercept"] = float(col(a, "intercept").mean())
    res["xform"] = xf

    # theory checks ----------------------------------------------------------------------------------------------------------
    th: dict = {}
    rng = np.random.default_rng(20261104)
    g = []
    for n, p, reps in ((100, 0.05, 20000), (1000, 0.01, 20000), (1000, 0.05, 20000), (10000, 0.01, 2000), (10000, 0.00333333, 2000)):
        k = int(np.floor(p * n + 1e-9))
        sizes = np.empty(reps)
        for i in range(reps):
            x = rng.standard_normal(n)
            t = np.sort(x)[::-1][k]
            sizes[i] = stats.norm.sf(t)
        g.append({"n": n, "p": p, "k": k, "reps": reps, "mean": float(sizes.mean()), "sd": float(sizes.std(ddof=1)),
                  "theory_mean": theory.size_mean(n, p), "theory_sd": theory.size_sd(n, p)})
    th["gaussian_size"] = g
    # leave-one-block-out on the real null
    blocks = [cache.get(f"null_{cs}") for cs in NULL_SEEDS]
    loo = {}
    for s in PROPOSED:
        high = sc.is_high(s)
        for label, p in (("single", SIZE), ("union_share", SIZE / 3)):
            sizes = []
            for j in range(len(blocks)):
                rest = np.concatenate([col(blocks[i], s) for i in range(len(blocks)) if i != j])
                thr = sc.critical(rest, p, high)
                sizes.append(float(sc.flag(col(blocks[j], s), thr, high).mean()))
            loo[f"{s}_{label}"] = {"mean": float(np.mean(sizes)), "sd": float(np.std(sizes, ddof=1)), "values": sizes, "p": p,
                                   "theory_mean": theory.size_mean(rest.size, p)}
    th["leave_one_block_out"] = loo
    # slope and rolling-mean correlation
    sl = []
    for lag in LADDER:
        a = lag_blocks[lag]
        sl.append({"lag": lag, "slope_mean": float(col(a, "slope").mean()), "slope_sd": float(col(a, "slope").std(ddof=1)),
                   "slope_theory": theory.slope(lag), "intercept_mean": float(col(a, "intercept").mean()),
                   "roll_pearson_mean": float(col(a, "roll20_pearson").mean()), "roll_pearson_sd": float(col(a, "roll20_pearson").std(ddof=1)),
                   "roll_pearson_theory": theory.rolling_corr(lag, 20)})
    a0 = committed["none"]
    sl.insert(0, {"lag": 0, "slope_mean": float(col(a0, "slope").mean()), "slope_sd": float(col(a0, "slope").std(ddof=1)),
                  "slope_theory": 1.0, "intercept_mean": float(col(a0, "intercept").mean()),
                  "roll_pearson_mean": float(col(a0, "roll20_pearson").mean()), "roll_pearson_sd": float(col(a0, "roll20_pearson").std(ddof=1)),
                  "roll_pearson_theory": theory.rolling_corr(0, 20)})
    th["slope_and_rolling_correlation"] = sl
    th["rolling_corr_by_window"] = {str(w): [theory.rolling_corr(L, w) for L in (5, 10, 20, 40)] for w in (5, 10, 20, 40, 60)}
    res["theory"] = th

    # reconciliation with the committed C13 documents ------------------------------------------------------------------------
    recon = {}
    derived = sc.ROOT / "data" / "derived" / "C13"
    for d in IDS:
        doc = json.loads((derived / f"{d}.json").read_text(encoding="utf-8"))["outputs"]["pla_complement"]
        f = rules.flags(committed[d])
        mine = {"wald": int(f["wald_hc3"].sum()), "abs": int(f["abs_spearman"].sum()), "roll": int(f["roll20"].sum()), "pla": int(f["pla"].sum())}
        theirs = {"wald": doc["flags"]["per_statistic"]["wald"]["k"], "abs": doc["flags"]["per_statistic"]["spearman_abs"]["k"],
                  "roll": doc["flags"]["per_statistic"]["spearman_roll"]["k"], "pla": doc["flags"]["pla_amber_or_red"]["k"]}
        recon[d] = {"here": mine, "committed": theirs, "equal": mine == theirs}
    res["reconciliation"] = recon

    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes); reconciliation equal: {all(v['equal'] for v in recon.values())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
