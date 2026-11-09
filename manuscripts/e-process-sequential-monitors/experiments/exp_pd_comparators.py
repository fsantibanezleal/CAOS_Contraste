"""The product's own PD tests, and a chi-square rule of equal size, as comparators of the PD e-process on the same histories.

The review of the manuscript found that the PD comparison ran only a chi-square written in the experiment code, although the
engine (``riskvalidation.validation.calibration``, release 1.1.0) carries the binomial test, the Jeffreys test and the
binomial test under the Vasicek one-factor mixture, the published remedy for the correlation the correlation experiment
studies. This script regenerates the default histories of ``exp_pd_correlation.py`` (seed sequence ``[seed, 400 + k]``, 2,000
histories per asset correlation) and of ``exp_ablation.py`` (seed sequence ``[seed, 300 + k]``, 1,000 histories per scaling of
the PD), so the comparators read the same data as the e-processes, and reads each history with:

- ``binomial``: the engine's exact one-sided binomial test of each grade and year (independent defaults);
- ``jeffreys``: the engine's Jeffreys test of each grade and year;
- ``vasicek_assumed``: the engine's Vasicek-corrected binomial test with an asset correlation of 0.12 assumed (the lower end
  of the Basel corporate range), whatever the correlation that generated the history;
- ``vasicek_true``: the same test with the asset correlation that generated the history (the oracle, a test whose
  correlation is right);
- ``chi2_sim`` and ``chi2_matched``: the chi-square statistic across grades on the cumulative counts read every year, with
  one constant critical value set by simulation on 50,000 correct histories (no correlation) to a size of 5 % over the ten
  years, and to the size the average PD e-process measured (``results_ablation.json``), the equal-size comparison the design
  asks for.

Each per-grade test is read in two ways. Every year: the history is rejected at the first year in which any of the 5 grades
has a one-sided p-value below 0.05 / 50 (a Bonferroni split over the 10 years and 5 grades, valid whatever the dependence of
the grades and the years). Once: the history is rejected when any grade at year 10 has a p-value below 0.05 / 5. The engine
computes every p-value; a table of them by default count is built once per grade and test (6 ms per call), then looked up.

    python manuscripts/e-process-sequential-monitors/experiments/exp_pd_comparators.py
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from importlib import metadata

import numpy as np
from scipy import stats

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common as cm  # noqa: E402

SEED = 20261104
PD_BOOK = (0.005, 0.01, 0.02, 0.05, 0.10)
N_OBL, YEARS = 2000, 10
RHOS = (0.0, 0.03, 0.12, 0.24)
ASSUMED_RHO = 0.12
CALIBRATION_REPS, CALIBRATION_TAG = 50000, 450
# the scenarios of exp_ablation.py: (id, factor on every grade, or the vector for one grade)
SCALINGS: list[tuple[str, np.ndarray]] = [
    ("all-x1", np.ones(5)), ("all-x1.05", np.full(5, 1.05)), ("all-x1.1", np.full(5, 1.10)),
    ("all-x1.25", np.full(5, 1.25)), ("grade5-x1.3", np.array([1, 1, 1, 1, 1.3])),
]


def pvalue_table(kind: str, n: int, pd: float, rho: float, dmax: int) -> np.ndarray:
    """The engine's one-sided p-value for each default count ``0..dmax`` of ``n`` obligors with predicted PD ``pd``."""
    from riskvalidation.validation import calibration as cal

    if kind == "binomial":
        f = lambda d: cal.pd_binomial(n, d, pd).p_value  # noqa: E731
    elif kind == "jeffreys":
        f = lambda d: cal.pd_jeffreys(n, d, pd).p_value  # noqa: E731
    elif kind == "vasicek":
        f = lambda d: cal.pd_binomial_vasicek(n, d, pd, rho).p_value  # noqa: E731
    else:
        raise ValueError(kind)
    return np.array([f(d) for d in range(dmax + 1)])


def pvalues(draws: np.ndarray, kind: str, rho: float) -> np.ndarray:
    """The p-value of every (history, year, grade) default count of ``draws``, looked up in the engine's tables."""
    out = np.empty(draws.shape)
    d = draws.astype(int)
    for g, pd in enumerate(PD_BOOK):
        tab = pvalue_table(kind, N_OBL, pd, rho, int(d[:, :, g].max()))
        out[:, :, g] = tab[d[:, :, g]]
    return out


def read_rules(p: np.ndarray, level: float = cm.LEVEL) -> tuple[np.ndarray, np.ndarray]:
    """Read p-values (histories, years, grades) two ways. Returns the first year (1-based, infinity when none) at which any
    grade is below ``level / (years * grades)`` (every year), and whether any grade at the last year is below
    ``level / grades`` (once)."""
    reps, years, grades = p.shape
    hit = (p < level / (years * grades)).any(axis=2)
    any_ = hit.any(axis=1)
    first = np.where(any_, np.argmax(hit, axis=1) + 1.0, np.inf)
    once = (p[:, -1, :] < level / grades).any(axis=1)
    return first, once


def _gen(rho: float, pd_true: np.ndarray):
    from riskvalidation.generators import DefaultCounts

    pd = np.array(PD_BOOK)
    return DefaultCounts(obligors=np.full((YEARS, pd.size), N_OBL), pd_true=np.minimum(np.tile(pd_true, (YEARS, 1)), 0.999),
                         pd_forecast=np.tile(pd, (YEARS, 1)), rho=rho)


def draw_correlation(rho: float, tag: int, reps: int, seed: int) -> np.ndarray:
    """The histories of ``exp_pd_correlation.py`` for the ``tag``-th asset correlation (predicted PD equal to the true PD)."""
    gen = _gen(rho, np.array(PD_BOOK))
    rng = np.random.default_rng(np.random.SeedSequence([seed, 400 + tag]))
    return np.array([gen.draw(rng)["d"].astype(float) for _ in range(reps)])


def draw_scaling(tag: int, factor: np.ndarray, reps: int, seed: int) -> np.ndarray:
    """The histories of ``exp_ablation.py`` for the ``tag``-th scaling of the PD (no correlation)."""
    gen = _gen(0.0, np.array(PD_BOOK) * factor)
    rng = np.random.default_rng(np.random.SeedSequence([seed, 300 + tag]))
    return np.array([gen.draw(rng)["d"].astype(float) for _ in range(reps)])


def chi2_readings(draws: np.ndarray) -> dict[str, float]:
    """The nominal chi-square test across grades of ``exp_pd_correlation.py``: read once at year 10 and read every year."""
    pd = np.array(PD_BOOK)
    n = np.full((YEARS, pd.size), float(N_OBL))
    rej = stats.chi2.sf(cm.chi2_across_grades(draws, n, pd), pd.size) < cm.LEVEL
    return {"year_10": float(rej[:, -1].mean()), "every_year": float(rej.any(axis=1).mean())}


def share(first: np.ndarray, reps: int) -> dict:
    k = int(np.isfinite(first).sum())
    fin = first[np.isfinite(first)]
    return {"ever": k / reps, "ever_ci": list(cm.wilson(k, reps)),
            "by3": float((first <= 3).mean()), "median_year_among_detected": float(np.median(fin)) if fin.size else None}


def share_bool(mask: np.ndarray) -> dict:
    k = int(mask.sum())
    return {"ever": k / mask.size, "ever_ci": list(cm.wilson(k, mask.size))}


def per_grade_rules(draws: np.ndarray, rho_true: float, kinds: tuple[str, ...]) -> dict:
    reps = draws.shape[0]
    spec = {"binomial": ("binomial", 0.0), "jeffreys": ("jeffreys", 0.0), "vasicek_assumed": ("vasicek", ASSUMED_RHO),
            "vasicek_true": ("vasicek", rho_true)}
    out = {}
    for name in kinds:
        kind, rho = spec[name]
        first, once = read_rules(pvalues(draws, kind, rho))
        out[name] = {"every_year": share(first, reps), "once": share_bool(once)}
    return out


def chi2_sim_rules(draws: np.ndarray, crit: dict[str, float]) -> dict:
    pd = np.array(PD_BOOK)
    n = np.full((YEARS, pd.size), float(N_OBL))
    stat = cm.chi2_across_grades(draws, n, pd)
    out = {}
    for name, c in crit.items():
        rej = stat > c
        first = np.where(rej.any(axis=1), np.argmax(rej, axis=1) + 1.0, np.inf)
        out[name] = share(first, draws.shape[0])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--reps", type=int, default=2000, help="histories per asset correlation")
    ap.add_argument("--pd-reps", type=int, default=1000, help="histories per scaling of the PD")
    ap.add_argument("--ablation", type=pathlib.Path, default=HERE / "results_ablation.json")
    ap.add_argument("--out", type=pathlib.Path, default=HERE / "results_pd_comparators.json")
    args = ap.parse_args()
    t0 = time.time()
    ablation = json.loads(args.ablation.read_text(encoding="utf-8"))
    matched_size = float(ablation["pd_combine"]["all-x1"]["average"]["ever"])

    # the equal-size chi-square: one constant critical value on correct histories without correlation
    pd = np.array(PD_BOOK)
    n = np.full((YEARS, pd.size), float(N_OBL))
    gen0 = _gen(0.0, pd)
    rng = np.random.default_rng(np.random.SeedSequence([args.seed, CALIBRATION_TAG]))
    null = np.array([gen0.draw(rng)["d"].astype(float) for _ in range(CALIBRATION_REPS)])
    stat = cm.chi2_across_grades(null, n, pd)
    crit = {"chi2_sim": cm.constant_critical_value(stat, cm.LEVEL),
            "chi2_matched": cm.constant_critical_value(stat, matched_size)}
    print(f"calibrated {crit} (matched size {matched_size}) [{time.time() - t0:.0f} s]", flush=True)

    correlation = []
    for tag, rho in enumerate(RHOS):
        draws = draw_correlation(rho, tag, args.reps, args.seed)
        row = {"rho": rho, "reps": args.reps,
               **per_grade_rules(draws, rho, ("binomial", "jeffreys", "vasicek_assumed", "vasicek_true")),
               **chi2_sim_rules(draws, crit), "chi2_nominal": chi2_readings(draws)}
        correlation.append(row)
        print(f"[rho {rho}] " + "  ".join(f"{k}={row[k]['every_year']['ever']:.3f}/{row[k]['once']['ever']:.3f}"
                                         for k in ("binomial", "jeffreys", "vasicek_assumed", "vasicek_true"))
              + f"  chi2_sim={row['chi2_sim']['ever']:.3f} [{time.time() - t0:.0f} s]", flush=True)

    scenarios = {}
    for tag, (sid, factor) in enumerate(SCALINGS):
        draws = draw_scaling(tag, factor, args.pd_reps, args.seed)
        scenarios[sid] = {"reps": args.pd_reps, **per_grade_rules(draws, 0.0, ("binomial", "jeffreys", "vasicek_assumed")),
                          **chi2_sim_rules(draws, crit), "chi2_nominal": chi2_readings(draws)}
        print(f"[scaling {sid}] " + "  ".join(f"{k}={scenarios[sid][k]['ever']:.3f}" for k in ("chi2_sim", "chi2_matched"))
              + f" [{time.time() - t0:.0f} s]", flush=True)

    result = {"meta": {"seed": args.seed, "reps": args.reps, "pd_reps": args.pd_reps, "pd_book": list(PD_BOOK), "obligors": N_OBL,
                       "years": YEARS, "assumed_rho": ASSUMED_RHO, "calibration_reps": CALIBRATION_REPS,
                       "bonferroni_every_year": cm.LEVEL / (YEARS * len(PD_BOOK)), "bonferroni_once": cm.LEVEL / len(PD_BOOK),
                       "engine_version": metadata.version("riskvalidation"), "script": "experiments/exp_pd_comparators.py"},
              "correlation": correlation,
              "equal_size_chi2": {"critical_value_5pct": crit["chi2_sim"], "critical_value_matched": crit["chi2_matched"],
                                  "matched_size": matched_size, "scenarios": scenarios}}
    args.out.write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(f"done in {time.time() - t0:.0f} s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
