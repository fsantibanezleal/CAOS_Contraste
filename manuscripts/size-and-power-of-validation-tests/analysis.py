"""Every number of the manuscript, computed from the committed C22 documents (``data/derived/C22``) and from the compact
results of the experiments (``experiments/results``). ``make_numbers.py``, ``make_tables.py`` and ``make_figures.py`` import
this module; nothing in the text is typed by hand.

Conventions. A "credit-family test" is one of the 21 tests of the five credit families (calibration, discrimination, stability,
rating system, transitions) whose key ends in ``@null`` in the null variant. A rate is judged by the rule of the measurement:
by its exact rejection probability where the test has one, and otherwise by the one-sided Monte Carlo bound
``alpha + z_{0.999} sqrt(alpha (1 - alpha) / R)``.
"""
from __future__ import annotations

import json
import math
import pathlib
from collections import defaultdict
from typing import Any

import numpy as np
from scipy import stats

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DERIVED = ROOT / "data" / "derived" / "C22"
RESULTS = HERE / "experiments" / "results"

VARIANTS = ["null", "miscalibration", "clustering", "drift", "discrimination-decay", "leakage", "broken-monotonicity",
            "concentration"]
EXTENSION = "other-families"
LEVELS = ("p<0.05", "p<0.01")
ALPHA = {"p<0.05": 0.05, "p<0.01": 0.01}
Z_BOUND = float(stats.norm.ppf(0.999))
Z_AGREE = 3.29

#: the order of the 21 credit-family tests in every table
TEST_ORDER = [
    "pd.binomial", "pd.jeffreys", "pd.binomial_vasicek", "pd.chi2_grades", "pd.default_profile", "pd.hosmer_lemeshow",
    "pd.spiegelhalter", "pd.normal_multiperiod", "pd.traffic_lights", "disc.auc_vs_initial", "disc.delong", "stability.psi",
    "stability.csi", "stability.chi2", "stability.ks", "rating.migration_ztests", "rating.hhi", "rating.time_homogeneity",
    "rating.markov_order", "rating.matrix_reference", "rating.momentum",
]
#: short names for the tables (the engine's own labels, shortened where a column is narrow)
NAME = {
    "pd.binomial": "Binomial", "pd.jeffreys": "Jeffreys", "pd.binomial_vasicek": "Vasicek-corrected binomial",
    "pd.chi2_grades": "Chi-square over grades", "pd.default_profile": "Default profile",
    "pd.hosmer_lemeshow": "Hosmer--Lemeshow", "pd.spiegelhalter": "Spiegelhalter", "pd.normal_multiperiod": "Normal, five years",
    "pd.traffic_lights": "Traffic lights", "disc.auc_vs_initial": "AUC against development (ECB)", "disc.delong": "DeLong",
    "stability.psi": "Population stability index", "stability.csi": "Characteristic stability index",
    "stability.chi2": "Chi-square of homogeneity", "stability.ks": "Kolmogorov--Smirnov",
    "rating.migration_ztests": "Migration z-tests", "rating.hhi": "Concentration (ECB)",
    "rating.time_homogeneity": "Time homogeneity", "rating.markov_order": "Markov order",
    "rating.matrix_reference": "Matrix against a reference", "rating.momentum": "Downward momentum",
}
FAMILY = {t: ("Calibration" if t.startswith("pd.") else "Discrimination" if t.startswith("disc.") else
              "Stability" if t.startswith("stability.") else "Rating system" if t in (
                  "rating.migration_ztests", "rating.hhi") else "Transitions") for t in TEST_ORDER}
HAS_POWER = [t for t in TEST_ORDER if not FAMILY[t] == "Transitions"]

_cache: dict[str, Any] = {}


def doc(name: str) -> dict[str, Any]:
    if name not in _cache:
        _cache[name] = json.loads((DERIVED / f"{name}.json").read_text(encoding="utf-8"))
    return _cache[name]


def result(name: str) -> dict[str, Any]:
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


def credit_rows(variant: str) -> list[dict[str, Any]]:
    """The simulations of the five credit families of one variant (the engine's named studies carry a ``study`` block)."""
    return [r for r in doc(variant)["outputs"]["simulations"] if not r.get("study")]


def bound(alpha: float, n: int) -> float:
    return alpha + Z_BOUND * math.sqrt(alpha * (1 - alpha) / n)


def holds(row: dict[str, Any]) -> bool:
    """The rule of the measurement: exact rejection probability where there is one, else the Monte Carlo bound."""
    if row.get("exact"):
        return all(row["exact"][lv] <= ALPHA[lv] + 1e-12 for lv in LEVELS)
    return all(row["rates"][lv]["rate"] <= bound(ALPHA[lv], row["rates"][lv]["n"]) for lv in LEVELS)


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, c - h), min(1.0, c + h)


def wald(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    p = k / n
    h = z * math.sqrt(p * (1 - p) / n)
    return p - h, p + h


def agresti_coull(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    nt = n + z * z
    pt = (k + z * z / 2) / nt
    h = z * math.sqrt(pt * (1 - pt) / nt)
    return pt - h, pt + h


def clopper_pearson(k: int, n: int, a: float = 0.05) -> tuple[float, float]:
    lo = 0.0 if k == 0 else float(stats.beta.ppf(a / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(stats.beta.ppf(1 - a / 2, k + 1, n - k))
    return lo, hi


def jeffreys_interval(k: int, n: int, a: float = 0.05) -> tuple[float, float]:
    lo = 0.0 if k == 0 else float(stats.beta.ppf(a / 2, k + 0.5, n - k + 0.5))
    hi = 1.0 if k == n else float(stats.beta.ppf(1 - a / 2, k + 0.5, n - k + 0.5))
    return lo, hi


INTERVALS = {"Wald": wald, "Wilson": wilson, "Agresti--Coull": agresti_coull, "Clopper--Pearson": clopper_pearson,
             "Jeffreys": jeffreys_interval}


def coverage(interval, p: float, n: int) -> float:
    """The exact coverage of a 95% interval for a binomial proportion ``p`` with ``n`` trials."""
    ks = np.arange(n + 1)
    pm = stats.binom.pmf(ks, n, p)
    tot = 0.0
    for k, w in zip(ks, pm):
        if w < 1e-15:
            continue
        lo, hi = interval(int(k), n)
        if lo <= p <= hi:
            tot += float(w)
    return tot


# ---------------------------------------------------------------------------------------------------------------------
# the measurement in numbers


def totals() -> dict[str, Any]:
    sims = reps = rates = exact_rows = 0
    gens: set[tuple[str, str]] = set()
    for v in VARIANTS:
        for r in credit_rows(v):
            sims += 1
            reps += r["n_rep"]
            rates += len(r["rates"])
            exact_rows += 1 if r.get("exact") else 0
            gens.add((v, r["generator"]))
    return {"sims": sims, "reps": reps, "rates": rates, "exact_rows": exact_rows, "generators": len(gens)}


def size_table() -> list[dict[str, Any]]:
    """One row per credit-family test: the rate at 5% and 1% of its null cell with Wilson interval, the exact value,
    the bound and whether it holds."""
    null = {r["test_id"]: r for r in credit_rows("null") if r["key"].endswith("@null")}
    out = []
    for t in TEST_ORDER:
        r = null[t]
        row = {"test": t, "name": NAME[t], "family": FAMILY[t], "n": r["n_rep"], "seed": r["seed"], "holds": holds(r),
               "exact": r.get("exact"), "key": r["key"]}
        for lv in LEVELS:
            x = r["rates"][lv]
            row[lv] = {"rate": x["rate"], "se": x["se"], "lo": x["wilson_low"], "hi": x["wilson_high"], "k": x["rejections"],
                       "bound": bound(ALPHA[lv], x["n"]),
                       "exceeds_bound": x["rate"] > bound(ALPHA[lv], x["n"]),
                       "above_level": x["rate"] > ALPHA[lv]}
        out.append(row)
    return out


def settings_rows() -> list[dict[str, Any]]:
    out = []
    for r in credit_rows("null"):
        if r["key"].endswith("@null"):
            continue
        row = {"key": r["key"], "test": r["test_id"], "scenario": r["scenario"]["en"], "n": r["n_rep"], "exact": r.get("exact")}
        for lv, x in r["rates"].items():
            row[lv] = {"rate": x["rate"], "se": x["se"], "lo": x["wilson_low"], "hi": x["wilson_high"], "k": x["rejections"]}
        out.append(row)
    return out


def exact_comparisons() -> list[dict[str, Any]]:
    out = []
    for v in VARIANTS:
        for r in credit_rows(v):
            if not r.get("exact"):
                continue
            for lv in LEVELS:
                x = r["rates"][lv]
                p = r["exact"][lv]
                n = x["n"]
                z = (x["rejections"] - n * p) / math.sqrt(n * p * (1 - p)) if 0 < p < 1 else 0.0
                out.append({"variant": v, "key": r["key"], "level": lv, "k": x["rejections"], "n": n, "exact": p,
                            "rate": x["rate"], "z": z, "agrees": bool(r["agrees"][lv]), "degenerate": not (0.005 < p < 0.995)})
    return out


def interval_on_exact_rows() -> dict[str, dict[str, int]]:
    rows = exact_comparisons()
    nondeg = [r for r in rows if not r["degenerate"]]
    out = {}
    for name, f in INTERVALS.items():
        out[name] = {"all": sum(1 for r in rows if f(r["k"], r["n"])[0] <= r["exact"] <= f(r["k"], r["n"])[1]),
                     "nondegenerate": sum(1 for r in nondeg if f(r["k"], r["n"])[0] <= r["exact"] <= f(r["k"], r["n"])[1])}
    out["_counts"] = {"all": len(rows), "nondegenerate": len(nondeg)}
    return out


def interval_coverage_grid(n: int = 4000, ps=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5)) -> dict[str, dict[str, float]]:
    return {name: {f"{p:g}": coverage(f, p, n) for p in ps} for name, f in INTERVALS.items()}


def curves(variant: str, measures: str = "power") -> dict[tuple[str, str], list[dict[str, Any]]]:
    """Rows grouped by (test, panel) for the panels of the variant that measure ``measures`` (``power`` or ``size``),
    ordered along the variant's ladder."""
    panels = {p["id"]: p for p in doc(variant)["outputs"]["panels"]}
    by: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in credit_rows(variant):
        if panels[r["panel"]]["measures"] == measures:
            by[(r["test_id"], r["panel"])].append(r)
    for rows in by.values():
        rows.sort(key=lambda r: (r["x"], r["key"]))
    return by


#: the curve each test is summarised by in the power table: (variant, panel)
MAIN_CURVE = {
    "pd.binomial": ("miscalibration", "portfolio"), "pd.jeffreys": ("miscalibration", "portfolio"),
    "pd.binomial_vasicek": ("miscalibration", "portfolio"), "pd.chi2_grades": ("miscalibration", "grades"),
    "pd.default_profile": ("miscalibration", "grades"), "pd.hosmer_lemeshow": ("miscalibration", "obligors"),
    "pd.spiegelhalter": ("miscalibration", "obligors"), "pd.normal_multiperiod": ("miscalibration", "years"),
    "pd.traffic_lights": ("miscalibration", "years"), "disc.auc_vs_initial": ("discrimination-decay", "ecb"),
    "disc.delong": ("discrimination-decay", "delong"), "stability.psi": ("drift", "stability"),
    "stability.csi": ("leakage", "feature"), "stability.chi2": ("drift", "stability"),
    "stability.ks": ("drift", "stability"), "rating.migration_ztests": ("broken-monotonicity", "migration-500"),
    "rating.hhi": ("concentration", "ecb"),
}


def main_curve(test: str) -> list[dict[str, Any]]:
    variant, panel = MAIN_CURVE[test]
    return curves(variant)[(test, panel)]


def severity_at_power(rows: list[dict[str, Any]], target: float = 0.8, level: str = "p<0.05") -> dict[str, Any]:
    """The setting of the ladder at which the power curve first reaches ``target`` (linear interpolation between ladder
    points), with the interval obtained from the Wilson limits of the points; ``None`` where the curve does not reach it."""
    xs = [r["x"] for r in rows]

    def cross(ys: list[float]) -> float | None:
        for i in range(len(xs)):
            if ys[i] >= target:
                if i == 0:
                    return xs[0]
                x0, x1, y0, y1 = xs[i - 1], xs[i], ys[i - 1], ys[i]
                return x0 + (target - y0) * (x1 - x0) / (y1 - y0)
        return None

    rate = [r["rates"][level]["rate"] for r in rows]
    lo = [r["rates"][level]["wilson_low"] for r in rows]
    hi = [r["rates"][level]["wilson_high"] for r in rows]
    return {"x": cross(rate), "x_low": cross(hi), "x_high": cross(lo)}


def monotonicity(variant_filter=None) -> dict[str, Any]:
    """Adjacent-pair check of every power curve: a violation is a fall of the rate larger than 3.29 combined Monte Carlo
    standard errors."""
    pairs = viol = 0
    detail = []
    for v in VARIANTS[1:]:
        for (t, panel), rows in curves(v).items():
            if v == "broken-monotonicity" and panel == "curve":
                pass
            for a, b in zip(rows, rows[1:]):
                if a["x"] == b["x"]:
                    continue
                for lv in LEVELS:
                    ra, rb = a["rates"][lv], b["rates"][lv]
                    d = rb["rate"] - ra["rate"]
                    se = math.sqrt(ra["se"] ** 2 + rb["se"] ** 2)
                    pairs += 1
                    if se > 0 and d < -Z_AGREE * se:
                        viol += 1
                        detail.append((v, t, panel, lv, a["x"], b["x"], d, se))
    return {"pairs": pairs, "violations": viol, "detail": detail}


def standard_error_calibration() -> dict[str, Any]:
    """The z of every exact comparison has mean 0 and standard deviation 1 when the Monte Carlo SE is right."""
    z = np.array([r["z"] for r in exact_comparisons() if not r["degenerate"]])
    return {"n": int(z.size), "mean": float(z.mean()), "sd": float(z.std(ddof=1)), "max_abs": float(np.abs(z).max())}


def reproductions() -> list[dict[str, Any]]:
    out = []
    for v in ("clustering", "drift", "leakage"):
        g = doc(v)["outputs"]["golden"][0]
        zs = np.array([c["z"] for c in g["cells"]])
        interior = [c for c in g["cells"] if 0 < c["published"] < 1]
        out.append({"variant": v, "study": g["study"], "title": g["title"]["en"], "runs_published": g["runs_published"],
                    "runs": g["runs"], "agree": g["agree"], "total": g["total"], "mean_z": float(zs.mean()),
                    "mean_z_interior": float(np.mean([c["z"] for c in interior])) if interior else None,
                    "interior": len(interior),
                    "disagreeing": [c for c in g["cells"] if not c["agrees"]]})
    return out


def families_of_defects() -> list[dict[str, Any]]:
    out = []
    for v in VARIANTS:
        d = doc(v)
        rows = credit_rows(v)
        out.append({"variant": v, "sims": len(rows), "reps": sum(r["n_rep"] for r in rows),
                    "n_rep_values": sorted({r["n_rep"] for r in rows}), "rates": sum(len(r["rates"]) for r in rows),
                    "generators": len({r["generator"] for r in rows}), "tests": len({r["test_id"] for r in rows}),
                    "ladder": d["outputs"]["ladder"]})
    return out


# ---------------------------------------------------------------------------------------------------------------------
# the extension: the 21 tests outside the credit families


def extension_table() -> list[dict[str, Any]]:
    nulls = [r for r in doc("null")["outputs"]["simulations"] if r.get("study")]
    alts = {(r["test_id"], r["study"]["index"]): r for r in doc(EXTENSION)["outputs"]["simulations"]
            if r["study"]["arm"] == "alternative"}
    out = []
    for r in nulls:
        s = r["study"]
        a = alts[(r["test_id"], s["index"])]
        own = [k for k in r["rates"] if k not in LEVELS]
        rule = own[0] if own else "p<0.05"
        x5, x1 = r["rates"]["p<0.05"], r["rates"]["p<0.01"]
        out.append({
            "test": r["test_id"], "label": s["label"]["en"], "rule": s["rule"], "rule_key": rule,
            "size5": x5["rate"], "size1": x1["rate"], "size_rule": r["rates"][rule]["rate"],
            "size_rule_bound": bound(0.05, r["rates"][rule]["n"]),
            "holds": all(r["rates"][lv]["rate"] <= bound(ALPHA[lv], r["rates"][lv]["n"]) for lv in LEVELS),
            "power5": a["rates"]["p<0.05"]["rate"], "power5_lo": a["rates"]["p<0.05"]["wilson_low"],
            "power5_hi": a["rates"]["p<0.05"]["wilson_high"], "power5_se": a["rates"]["p<0.05"]["se"],
            "power_rule": a["rates"][rule]["rate"],
            "power_n": a["n_rep"], "size_n": r["n_rep"],
        })
    return out


# ---------------------------------------------------------------------------------------------------------------------
# the experiments


def seed_replication() -> dict[str, Any]:
    d = result("seed_replication.json")
    n_rep = d["n_rep"]
    out: dict[str, Any] = {"blocks": d["blocks"], "n_rep": n_rep, "tests": {}}
    for key, blocks in d["cells"].items():
        t = key.split("@")[0]
        out["tests"][t] = {lv: {} for lv in LEVELS}
        for lv, tag in (("p<0.05", "0.05"), ("p<0.01", "0.01")):
            ks = np.array([b[f"k{tag}"] for b in blocks])
            slices = np.array([b[f"slices{tag}"] for b in blocks]).reshape(-1)
            rates = ks / n_rep
            total, N = int(ks.sum()), n_rep * len(blocks)
            pooled = total / N
            lo, hi = wilson(total, N)
            a = ALPHA[lv]
            res = {"pooled": pooled, "pooled_lo": lo, "pooled_hi": hi, "pooled_k": total, "pooled_n": N,
                   "se_pooled": math.sqrt(pooled * (1 - pooled) / N),
                   "sd_blocks": float(rates.std(ddof=1)), "se_binomial": math.sqrt(pooled * (1 - pooled) / n_rep),
                   "min_block": float(rates.min()), "max_block": float(rates.max()),
                   "flag_bound_4000": float(np.mean(rates > bound(a, n_rep))),
                   "flag_naive_4000": float(np.mean(rates > a)),
                   "slices": slices.tolist(), "blocks": ks.tolist()}
            out["tests"][t][lv] = res
    return out


def committed_verdict_vs_pooled() -> list[dict[str, Any]]:
    """For each credit-family test the verdict of the committed cell, the verdict of the pooled replication, and the verdict
    of the pooled replication by the same rule (exact where there is an exact value)."""
    rep = seed_replication()["tests"]
    size = {r["test"]: r for r in size_table()}
    out = []
    for t in TEST_ORDER:
        s = size[t]
        pooled_holds = True
        for lv in LEVELS:
            p = rep[t][lv]
            if s["exact"]:
                ok = s["exact"][lv] <= ALPHA[lv] + 1e-12
            else:
                ok = p["pooled"] <= bound(ALPHA[lv], p["pooled_n"])
            pooled_holds = pooled_holds and ok
        out.append({"test": t, "committed_holds": s["holds"], "pooled_holds": pooled_holds,
                    "flag_bound_blocks": max(rep[t][lv]["flag_bound_4000"] for lv in LEVELS),
                    "agree": s["holds"] == pooled_holds})
    return out


def flag_rates_by_repetitions() -> dict[str, dict[str, float]]:
    """Share of cells flagged by the bound rule and by the naive rule (rate above the level), at each repetition number, over
    the tests whose pooled size lies within the level (true size at most alpha) and over those whose pooled size lies above
    the level by more than the pooled Monte Carlo bound (clearly oversized). Slices of 1,000 repetitions are valid cells of
    1,000; consecutive slices of one block pool to cells of 2,000, whole blocks are cells of 4,000, five blocks cells of
    20,000."""
    d = result("seed_replication.json")
    out: dict[str, dict[str, float]] = {}
    pooled = seed_replication()["tests"]
    within, over = [], []
    for t in TEST_ORDER:
        if t == "rating.hhi" or t == "rating.migration_ztests":
            pass
        ok = all(pooled[t][lv]["pooled"] <= ALPHA[lv] for lv in LEVELS)
        clearly = any(pooled[t][lv]["pooled_lo"] > ALPHA[lv] + 0.0 for lv in LEVELS)
        if ok:
            within.append(t)
        elif clearly:
            over.append(t)
    for R in (1000, 2000, 4000, 20000):
        for group_name, group in (("within", within), ("over", over)):
            flags_b = flags_n = cells = 0
            for t in group:
                blocks = d["cells"][f"{t}@null"]
                for lv, tag in (("p<0.05", "0.05"), ("p<0.01", "0.01")):
                    pass
                # build the stream of 1,000-slices per level per block, then group
                per_level = {}
                for tag in ("0.05", "0.01"):
                    per_level[tag] = [b[f"slices{tag}"] for b in blocks]
                if R <= 4000:
                    m = R // 1000
                    n_cells = len(blocks) * (4 // m)
                    ks = {tag: [sum(bl[i * m:(i + 1) * m]) for bl in per_level[tag] for i in range(4 // m)] for tag in per_level}
                else:
                    m = R // 4000
                    n_cells = len(blocks) // m
                    ks = {tag: [sum(sum(per_level[tag][j * m + q]) for q in range(m)) for j in range(n_cells)] for tag in per_level}
                for c in range(n_cells):
                    fb = fn = False
                    for tag, a in (("0.05", 0.05), ("0.01", 0.01)):
                        r = ks[tag][c] / R
                        fb = fb or r > bound(a, R)
                        fn = fn or r > a
                    flags_b += fb
                    flags_n += fn
                    cells += 1
            out.setdefault(str(R), {})[group_name + "_bound"] = flags_b / cells if cells else float("nan")
            out[str(R)][group_name + "_naive"] = flags_n / cells if cells else float("nan")
            out[str(R)][group_name + "_cells"] = cells
            out[str(R)][group_name + "_tests"] = len(group)
    return out


def groups_by_pooled() -> dict[str, list[str]]:
    pooled = seed_replication()["tests"]
    within = [t for t in TEST_ORDER if all(pooled[t][lv]["pooled"] <= ALPHA[lv] for lv in LEVELS)]
    over = [t for t in TEST_ORDER if t not in within and any(pooled[t][lv]["pooled_lo"] > ALPHA[lv] for lv in LEVELS)]
    return {"within": within, "over": over, "neither": [t for t in TEST_ORDER if t not in within and t not in over]}


# ---------------------------------------------------------------------------------------------------------------------
# the derivations of the Theory section, evaluated


def psi_fixed_band_false_alarm(n: float, band: float, bins: int = 10) -> float:
    """Asymptotic P(PSI > band) with equal samples of n and no shift: PSI * n / 2 is chi-square with bins - 1 degrees of
    freedom (Yurdakul and Naranjo)."""
    return float(stats.chi2.sf(band * n / 2.0, bins - 1))


def hl_dof_oversize(groups: int = 10) -> float:
    """P(chi-square_G > the 95% point of chi-square_{G-2}): the size of the Hosmer-Lemeshow test with G - 2 degrees of freedom
    when the statistic has G."""
    return float(stats.chi2.sf(stats.chi2.ppf(0.95, groups - 2), groups))


def auc_known_vs_estimated_size(m: float, alpha: float = 0.05) -> float:
    """P(Z > z_{1-alpha} / sqrt(1 + 1/m)): the size of the ECB AUC test when the development AUC is an estimate on a sample
    m times the current one."""
    return float(stats.norm.sf(stats.norm.ppf(1 - alpha) / math.sqrt(1 + 1.0 / m)))


def hhi_statistic_peak() -> dict[str, float]:
    """Largest value of the ECB concentration statistic over the exact curve of the concentration variant, and the critical
    value of a one-sided test at 5%."""
    ec = doc("concentration")["outputs"]["exact_curves"][0]
    ys = ec["series"][0]["y"] if "y" in ec["series"][0] else ec["series"][0]["values"]
    return {"max": float(max(ys)), "critical": float(stats.norm.ppf(0.95))}


# ---------------------------------------------------------------------------------------------------------------------
# an independent recomputation of the exact size of the binomial test under asset correlation (no engine call)


def binomial_size(n: int, pd: float, rho: float, alpha: float, pd_true: float | None = None) -> float:
    """P(reject) of the binomial test (p-value P(Bin(n, pd) >= D)) when the defaults follow the one-factor model with
    asset correlation rho and the true PD equals pd: the mixture over a 256-node Gauss-Hermite rule."""
    kstar = int(stats.binom.isf(alpha, n, pd)) + 1          # smallest k with P(Bin >= k) < alpha
    while stats.binom.sf(kstar - 1, n, pd) >= alpha:
        kstar += 1
    while kstar > 0 and stats.binom.sf(kstar - 2, n, pd) < alpha:
        kstar -= 1
    if rho == 0.0:
        return float(stats.binom.sf(kstar - 1, n, pd if pd_true is None else pd_true))
    x, w = np.polynomial.hermite_e.hermegauss(256)
    w = w / w.sum()
    pt = pd if pd_true is None else pd_true
    p = stats.norm.cdf((stats.norm.ppf(pt) - math.sqrt(rho) * x) / math.sqrt(1 - rho))
    return float(np.sum(w * stats.binom.sf(kstar - 1, n, p)))


def binomial_size_limit(pd: float, rho: float) -> float:
    """The limit of the size of the independence-based count test as n grows, at fixed rho > 0 (Proposition on clustering)."""
    return float(stats.norm.cdf(stats.norm.ppf(pd) * (1 - math.sqrt(1 - rho)) / math.sqrt(rho)))


def hhi_peak_gain(c0: float) -> float:
    """max over c of (c - c0) / (c sqrt(1/2 + c^2)): the statistic of the ECB concentration test is sqrt(K - 1) times it."""
    c = np.linspace(c0 + 1e-6, 6.0, 600001)
    return float(np.max((c - c0) / (c * np.sqrt(0.5 + c * c))))


def hhi_min_grades(c0: float, alpha: float = 0.05) -> int:
    """The smallest number of grades K with which the ECB concentration test can reject at level alpha."""
    g = hhi_peak_gain(c0)
    return int(math.ceil(1 + (stats.norm.ppf(1 - alpha) / g) ** 2))


def reconcile_binomial() -> dict[str, Any]:
    """The committed exact rejection probabilities of the binomial test, recomputed with ``binomial_size`` (which calls no
    function of the engine) from the configuration of each generator."""
    diffs = []
    for v in ("miscalibration", "clustering"):
        gens = doc(v)["outputs"]["generators"]
        for r in credit_rows(v):
            if r["test_id"] != "pd.binomial" or not r.get("exact"):
                continue
            cfg = gens[r["generator"]]["config"]
            n = int(cfg["obligors"][0][0])
            pdt, pdf, rho = float(cfg["pd_true"][0][0]), float(cfg["pd_forecast"][0][0]), float(cfg["rho"][0])
            for lv in LEVELS:
                mine = binomial_size(n, pdf, rho, ALPHA[lv], pd_true=pdt)
                diffs.append(abs(mine - r["exact"][lv]))
    diffs += []
    for r in credit_rows("null"):
        if r["key"] == "pd.binomial@null":
            for lv in LEVELS:
                diffs.append(abs(binomial_size(1000, 0.01, 0.0, ALPHA[lv]) - r["exact"][lv]))
    return {"n": len(diffs), "max_abs": max(diffs)}
