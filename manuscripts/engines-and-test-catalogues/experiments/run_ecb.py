"""Experiment 1: the ECB reporting tests of the engine against an independent transcription of the specification, and against
the nearest generic test of the open libraries, on the committed C01 holdout.

Part A: for each of the five ECB statistics the engine implements (Jeffreys, AUC against the development AUC with the ECB variance,
matrix weighted bandwidth, migration z-tests, concentration), a transcription of the ECB formulas written here with loops, ``math`` and
``mpmath`` (never the engine's vectorised code, never SciPy's Beta distribution) is run on N_RANDOM seeded random inputs and compared
with the engine.  Part B: on every grade of every model of the committed C01 holdout, the engine's Jeffreys p-value is compared with the
exact binomial test of SciPy and with the Jeffreys interval of statsmodels, which are the nearest generic tools.

    python manuscripts/engines-and-test-catalogues/experiments/run_ecb.py
"""
from __future__ import annotations

import json
import math
import pathlib

import mpmath
import numpy as np
from scipy import stats
from statsmodels.stats.proportion import proportion_confint

import riskvalidation
from riskvalidation.validation import discrimination as rv_disc
from riskvalidation.validation import rating_system as rv_rs
from riskvalidation.validation import calibration as rv_cal

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SEED = 20261105
N_RANDOM = 500


def phi(x: float) -> float:
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


# ------------------------------------------------------------------------------------------ the specification, transcribed
def spec_jeffreys(n: int, d: int, pd: float) -> float:
    """ECB 2.5.3.1: p = F_Beta(D+1/2, N-D+1/2)(PD), by tanh-sinh quadrature of the Beta density written with ``math.lgamma``
    (never SciPy's Beta distribution)."""
    a, b = d + 0.5, n - d + 0.5
    log_b = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    mean = a / (a + b)
    sd = math.sqrt(a * b / ((a + b) ** 2 * (a + b + 1)))
    lo, hi = max(0.0, mean - 14 * sd), mean + 14 * sd
    if pd >= hi:
        return 1.0
    if pd <= lo:
        return 0.0

    def pdf(x):
        x = mpmath.mpf(x)
        return mpmath.exp((a - 1) * mpmath.log(x) + (b - 1) * mpmath.log1p(-x) - log_b)

    return float(mpmath.quad(pdf, [lo, pd]))


def spec_auc(risk: list[float], y: list[int]):
    """ECB Annex 3.1 with ratings r = -risk (higher is better): the kernel u_ab by double loop, V10, V01, s^2."""
    r = [-v for v in risk]
    a = [r[i] for i in range(len(r)) if y[i] == 1]
    b = [r[i] for i in range(len(r)) if y[i] == 0]
    u = [[1.0 if ra < rb else (0.5 if ra == rb else 0.0) for rb in b] for ra in a]
    auc = sum(map(sum, u)) / (len(a) * len(b))
    v10 = [sum(row) / len(b) for row in u]
    v01 = [sum(u[i][j] for i in range(len(a))) / len(a) for j in range(len(b))]

    def var(v):
        m = sum(v) / len(v)
        return sum((x - m) ** 2 for x in v) / (len(v) - 1)

    return auc, var(v10) / len(a) + var(v01) / len(b)


def spec_mwb(m: list[list[float]]):
    k = len(m)
    ni = [sum(row) for row in m]
    p = [[(m[i][j] / ni[i]) if ni[i] > 0 else 0.0 for j in range(k)] for i in range(k)]
    num_u = sum(abs(i - j) * ni[i] * p[i][j] for i in range(k - 1) for j in range(i + 1, k))
    den_u = sum(max(abs(i + 1 - k), abs(i)) * ni[i] * sum(p[i][i + 1:]) for i in range(k - 1))
    num_l = sum(abs(i - j) * ni[i] * p[i][j] for i in range(1, k) for j in range(i))
    den_l = sum(max(abs(i + 1 - k), abs(i)) * ni[i] * sum(p[i][:i]) for i in range(1, k))
    return (num_u / den_u if den_u > 0 else 0.0), (num_l / den_l if den_l > 0 else 0.0)


def spec_migration(m: list[list[float]]):
    """ECB 2.5.5.2: z for every off-diagonal cell against the neighbour nearer the diagonal; returns {(i, j): (z, p)}."""
    k = len(m)
    out = {}
    for i in range(k):
        ni = sum(m[i])
        if ni == 0:
            continue
        p = [x / ni for x in m[i]]
        for j in range(k):
            if j == i:
                continue
            nb = j + 1 if j < i else j - 1
            var = (p[j] * (1 - p[j]) + p[nb] * (1 - p[nb]) + 2 * p[j] * p[nb]) / ni
            if var <= 0:
                continue
            z = (p[nb] - p[j]) / math.sqrt(var)
            out[(i + 1, j + 1)] = (z, phi(z))
    return out


def spec_hhi(cur: list[float], ini: list[float]):
    def cv(f):
        s = sum(f)
        r = [x / s for x in f]
        k = len(r)
        return math.sqrt(k * sum((x - 1.0 / k) ** 2 for x in r))

    k = len(cur)
    c, i0 = cv(cur), cv(ini)
    s = math.sqrt(k - 1) * (c - i0) / math.sqrt(c ** 2 * (0.5 + c ** 2))
    return s, 1.0 - phi(s)


# ------------------------------------------------------------------------------------------------------- part A
def part_a() -> dict:
    rng = np.random.default_rng(SEED)
    res: dict[str, dict] = {}

    # Jeffreys
    diffs = []
    for _ in range(N_RANDOM):
        n = int(rng.integers(20, 20000))
        pd = float(rng.uniform(0.001, 0.3))
        d = int(rng.binomial(n, min(0.999, pd * rng.uniform(0.5, 2.0))))
        eng = rv_cal.pd_jeffreys(n, d, pd).p_value
        diffs.append(abs(eng - spec_jeffreys(n, d, pd)))
    res["pd.jeffreys"] = {"n_inputs": N_RANDOM, "max_abs_diff": max(diffs), "mean_abs_diff": float(np.mean(diffs))}

    # AUC against the development AUC (tied integer scores, sizes 60 to 150)
    diffs_auc, diffs_s2, diffs_p = [], [], []
    for _ in range(N_RANDOM):
        n = int(rng.integers(60, 150))
        y = (rng.random(n) < rng.uniform(0.1, 0.4)).astype(int)
        if y.sum() < 3 or y.sum() > n - 3:
            y[:3], y[3:6] = 1, 0
        risk = np.round(rng.normal(size=n) + 0.8 * y, 0 if rng.random() < 0.5 else 2)
        a, s2 = spec_auc(risk.tolist(), y.tolist())
        init = float(rng.uniform(0.55, 0.9))
        er = rv_disc.disc_auc_vs_initial(init, risk, y)
        eauc, es2, _, _ = rv_disc.auc_with_variance(risk, y)
        p_spec = 1.0 - phi((init - a) / math.sqrt(s2))
        diffs_auc.append(abs(eauc - a))
        diffs_s2.append(abs(es2 - s2))
        diffs_p.append(abs(er.p_value - p_spec))
    res["disc.auc_vs_initial"] = {
        "n_inputs": N_RANDOM, "max_abs_diff_auc": max(diffs_auc), "max_abs_diff_s2": max(diffs_s2), "max_abs_diff": max(diffs_p),
        "mean_abs_diff": float(np.mean(diffs_p))}

    # matrix weighted bandwidth
    diffs = []
    for _ in range(N_RANDOM):
        k = int(rng.integers(3, 13))
        m = rng.integers(0, 400, size=(k, k)).astype(float)
        m += np.diag(rng.integers(300, 2000, size=k))
        up, lo = spec_mwb(m.tolist())
        eu, el = rv_rs.matrix_weighted_bandwidth(m)
        diffs.append(max(abs(eu - up), abs(el - lo)))
    res["rating.mwb"] = {"n_inputs": N_RANDOM, "max_abs_diff": max(diffs), "mean_abs_diff": float(np.mean(diffs))}

    # migration z-tests, every cell
    diffs, ncells = [], 0
    for _ in range(N_RANDOM):
        k = int(rng.integers(3, 11))
        decay = rng.uniform(0.05, 0.3)
        base = np.array([[decay ** abs(i - j) for j in range(k)] for i in range(k)])
        base /= base.sum(axis=1, keepdims=True)
        n_i = rng.integers(200, 3000, size=k)
        m = np.array([rng.multinomial(int(n_i[i]), base[i]) for i in range(k)], dtype=float)
        sp = spec_migration(m.tolist())
        er = rv_rs.rating_migration_ztests(m)
        cells = {(c["from"], c["to"]): (c["z"], c["p"]) for c in er.extras["cells"]}
        assert set(cells) == set(sp), "the sets of defined cells differ"
        ncells += len(cells)
        diffs.append(max(max(abs(cells[c][0] - sp[c][0]), abs(cells[c][1] - sp[c][1])) for c in sp))
    res["rating.migration_ztests"] = {"n_inputs": N_RANDOM, "n_cells": ncells, "max_abs_diff": max(diffs),
                                      "mean_abs_diff": float(np.mean(diffs))}

    # concentration in grades
    diffs = []
    for _ in range(N_RANDOM):
        k = int(rng.integers(3, 16))
        cur = rng.dirichlet(rng.uniform(0.5, 4, size=k)) * int(rng.integers(500, 9000))
        ini = rng.dirichlet(rng.uniform(0.5, 4, size=k)) * int(rng.integers(500, 9000))
        s_spec, p_spec = spec_hhi(cur.tolist(), ini.tolist())
        er = rv_rs.rating_hhi(cur, ini)
        diffs.append(max(abs(er.statistic - s_spec), abs(er.p_value - p_spec)))
    res["rating.hhi"] = {"n_inputs": N_RANDOM, "max_abs_diff": max(diffs), "mean_abs_diff": float(np.mean(diffs))}
    return res


# ------------------------------------------------------------------------------------------------------- part B
def part_b() -> dict:
    doc = json.loads((ROOT / "data" / "derived" / "C01" / "holdout.json").read_text(encoding="utf-8"))
    rows = []
    for model, rung in doc["outputs"]["rungs"].items():
        n_tot = sum(g["n"] for g in rung["grades"])
        d_tot = sum(g["d"] for g in rung["grades"])
        pd_port = sum(g["n"] * g["pd"] for g in rung["grades"] if g["n"] > 0) / n_tot
        cells = [(g["grade"], g["n"], g["d"], g["pd"]) for g in rung["grades"] if g["n"] > 0]
        cells.append(("portfolio", n_tot, d_tot, pd_port))
        for grade, n, d, pd in cells:
            p_j = rv_cal.pd_jeffreys(n, d, pd).p_value
            p_b = float(stats.binomtest(d, n, pd, alternative="greater").pvalue)
            lo, _ = proportion_confint(d, n, alpha=0.10, method="jeffreys")  # one-sided 95 % lower limit
            rows.append({"model": model, "grade": grade, "n": n, "d": d, "pd": pd, "p_jeffreys": p_j, "p_binomial": p_b,
                         "sm_jeffreys_flag_005": bool(pd < lo)})
    out = {"cells": len(rows)}
    for alpha in (0.05, 0.01):
        fj = [r["p_jeffreys"] < alpha for r in rows]
        fb = [r["p_binomial"] < alpha for r in rows]
        out[f"alpha_{alpha}"] = {
            "flag_jeffreys": int(sum(fj)), "flag_binomial": int(sum(fb)),
            "disagree": int(sum(a != b for a, b in zip(fj, fb))),
            "jeffreys_only": int(sum(a and not b for a, b in zip(fj, fb))),
            "binomial_only": int(sum(b and not a for a, b in zip(fj, fb)))}
    out["statsmodels_flag_equals_engine_005"] = int(sum(r["sm_jeffreys_flag_005"] == (r["p_jeffreys"] < 0.05) for r in rows))
    out["max_abs_p_gap"] = max(abs(r["p_jeffreys"] - r["p_binomial"]) for r in rows)
    out["median_abs_p_gap"] = float(np.median([abs(r["p_jeffreys"] - r["p_binomial"]) for r in rows]))
    out["committed_match"] = None
    committed = {(t["model_id"], t["segment"]): t["p_value"] for t in doc["tests"] if t["test_id"] == "pd.jeffreys"}
    gaps = [abs(committed[(r["model"], r["grade"])] - r["p_jeffreys"]) for r in rows if (r["model"], r["grade"]) in committed]
    out["committed_match"] = {"compared": len(gaps), "max_abs_gap": max(gaps) if gaps else None}
    out["rows"] = rows
    return out


def main() -> None:
    result = {"riskvalidation": riskvalidation.__version__, "seed": SEED, "part_a": part_a(), "part_b": part_b()}
    (HERE / "results_ecb.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    for k, v in result["part_a"].items():
        print(k, v)
    print({k: v for k, v in result["part_b"].items() if k != "rows"})


if __name__ == "__main__":
    main()
