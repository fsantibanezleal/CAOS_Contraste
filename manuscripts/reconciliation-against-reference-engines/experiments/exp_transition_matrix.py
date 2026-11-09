"""The engine's cohort and Aalen-Johansen estimators against Open Risk's ``transitionMatrix`` 0.5.1, on seeded panels.

    <python with riskvalidation 1.1.0, transitionMatrix 0.5.1, pandas> exp_transition_matrix.py [--panels 30] [--out results_transition_matrix.json]

The engine tests this comparison itself (its release notes of 0.8.0, the test file ``tests/test_transitions_reconciliation.py``
of its repository); the product's notebooks do not rerun it, and the optional ``transitions`` extra that carries the library is
not among the product's pins. This script runs the comparison in an environment that has the extra, on ``--panels`` seeded
rating panels with withdrawals (600 entities, four grades and default, six observation dates, a withdrawal probability of 6 % per
period), and reports for each convention the largest element-wise difference over all panels:

* the cohort estimator with the withdrawn kept as a state, per period and pooled (Anderson and Goodman), against the package's
  period matrices and count-averaged matrix;
* the cohort estimator with the withdrawn excluded, against the package's matrix renormalised on the performing columns;
* the package's double count of the last record of its last entity (reported with and without the sentinel entity that avoids
  it, and checked against the engine's counts corrected by that one migration);
* the Aalen-Johansen estimator on the four-obligor example whose risk set the package counts after the exit.

The panel generator and the conversions follow the engine's test file; the seeds differ (20261104 + r).
"""
from __future__ import annotations

import argparse
import importlib.metadata as md
import json
import pathlib
import warnings

import numpy as np
import pandas as pd

from riskvalidation.transitions.estimators import aalen_johansen, cohort, pooled_cohort
from transitionMatrix.estimators import aalen_johansen_estimator as aj_module
from transitionMatrix.estimators import cohort_estimator as cohort_module
from transitionMatrix.statespaces import statespace as statespace_module

HERE = pathlib.Path(__file__).resolve().parent
M, T = 5, 6
P = np.array([[0.90, 0.07, 0.02, 0.009, 0.001], [0.05, 0.85, 0.07, 0.02, 0.01], [0.02, 0.08, 0.80, 0.07, 0.03],
              [0.00, 0.03, 0.10, 0.77, 0.10], [0.00, 0.00, 0.00, 0.00, 1.00]])


def panel(seed: int, n: int = 600) -> np.ndarray:
    rng = np.random.default_rng(seed)
    out = np.full((n, T), -1, dtype=int)
    out[:, 0] = rng.integers(0, M - 1, n)
    for t in range(1, T):
        for i in range(n):
            prev = out[i, t - 1]
            if prev < 0:
                continue
            if prev != M - 1 and rng.random() < 0.06:
                continue
            out[i, t] = rng.choice(M, p=P[prev])
    out[-1] = [1, 1, 2, 1, 1, 2]       # the last entity never withdraws and ends in a performing grade
    return out


def engine_input(pn: np.ndarray):
    tables, withdrawn = [], []
    for k in range(T - 1):
        a, b = pn[:, k], pn[:, k + 1]
        both = (a >= 0) & (b >= 0)
        table = np.zeros((M, M))
        np.add.at(table, (a[both], b[both]), 1.0)
        tables.append(table)
        withdrawn.append(np.bincount(a[(a >= 0) & (b < 0)], minlength=M).astype(float))
    return tables, withdrawn


def package_cohort(pn: np.ndarray, sentinel: bool = True):
    ids, times = np.nonzero(pn >= 0)
    rows = list(zip(ids.tolist(), times.tolist(), pn[pn >= 0].tolist(), strict=True))
    if sentinel:
        rows += [(pn.shape[0], T - 2, M - 1), (pn.shape[0], T - 1, M - 1)]
    data = pd.DataFrame(rows, columns=["ID", "Time", "State"])
    space = statespace_module.StateSpace(definition=[(str(i), str(i)) for i in range(M)])
    est = cohort_module.CohortEstimator(states=space, cohort_bounds=list(range(T)), ci={"method": "goodman", "alpha": 0.05})
    with warnings.catch_warnings(), np.errstate(all="ignore"):
        warnings.simplefilter("ignore")
        est.fit(data)
    return est


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panels", type=int, default=30)
    ap.add_argument("--out", default=str(HERE / "results_transition_matrix.json"))
    args = ap.parse_args()
    state_period, state_pooled, exclude_pooled, exclude_period, raw_gap, corrected_gap, sentinel_gap = [], [], [], [], [], [], []
    n_elements = 0
    for r in range(args.panels):
        pn = panel(20261104 + r)
        tables, withdrawn = engine_input(pn)
        pkg = package_cohort(pn)
        d = 0.0
        for k in range(T - 1):
            eng = cohort(tables[k], withdrawn[k], treatment="state")["matrix"][:M, :M]
            d = max(d, float(np.max(np.abs(eng[: M - 1] - pkg.matrix_set[k][: M - 1]))))
            n_elements += (M - 1) * M
        state_period.append(d)
        pooled = pooled_cohort(tables, withdrawn, treatment="state")
        state_pooled.append(float(np.max(np.abs(pooled["matrix"][:M, :M] - pkg.average_matrix))))
        n_elements += M * M
        block = pkg.average_matrix[: M - 1]
        eng_ex = pooled_cohort(tables, withdrawn, treatment="exclude")["matrix"]
        exclude_pooled.append(float(np.max(np.abs(eng_ex[: M - 1] - block / block.sum(axis=1, keepdims=True)))))
        n_elements += (M - 1) * M
        d = 0.0
        for k in range(T - 1):
            eng_k = cohort(tables[k], withdrawn[k], treatment="exclude")["matrix"][: M - 1]
            blk = pkg.matrix_set[k][: M - 1]
            d = max(d, float(np.max(np.abs(eng_k - blk / blk.sum(axis=1, keepdims=True)))))
            n_elements += (M - 1) * M
        exclude_period.append(d)
        raw = package_cohort(pn, sentinel=False)
        raw_gap.append(float(np.max(np.abs(raw.average_matrix - pooled["matrix"][:M, :M]))))
        a, b = pn[-1][-2], pn[-1][-1]
        num = pooled["counts"][:M, :M].copy()
        size = pooled["row_sizes"][:M].copy()
        num[a, b] += 1.0
        size[b] += 1.0
        corrected_gap.append(float(np.max(np.abs(raw.average_matrix - num / size[:, None]))))
        sentinel_gap.append(state_pooled[-1])
    seg = {"obligor": np.array([0, 0, 1, 2, 3]), "start": np.array([0.0, 2.0, 0.0, 0.0, 0.0]), "stop": np.array([2.0, 5.0, 5.0, 5.0, 5.0]),
           "state": np.array([0, 1, 0, 0, 0]), "to": np.array([1, -1, -1, -1, -1])}
    eng_aj = aalen_johansen(seg, 2, 0.0, 5.0)["matrix"]
    rows = [(i, 0.0, 0, 0) for i in range(4)] + [(0, 2.0, 0, 1), (1, 3.0, 0, 0), (2, 4.0, 0, 0), (3, 5.0, 0, 0)]
    data = pd.DataFrame(rows, columns=["ID", "Time", "From", "To"]).sort_values("Time", kind="stable")
    est = aj_module.AalenJohansenEstimator(states=statespace_module.StateSpace(definition=[("0", "0"), ("1", "1")]))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        est.fit(data, labels={"Time": "Time", "From": "From", "To": "To", "ID": "ID"})
    pkg_aj = float(est.etm[:, :, -1][0, 1])
    out = {"riskvalidation": md.version("riskvalidation"), "transitionMatrix": md.version("transitionMatrix"), "panels": args.panels, "entities": 600,
           "elements_compared": n_elements, "tolerance": 1e-12,
           "state_period_max_abs_diff": max(state_period), "state_pooled_max_abs_diff": max(state_pooled),
           "exclude_period_max_abs_diff": max(exclude_period), "exclude_pooled_max_abs_diff": max(exclude_pooled),
           "last_record_double_count": {"min_gap_without_sentinel": min(raw_gap), "max_gap_without_sentinel": max(raw_gap),
                                         "max_gap_after_correction": max(corrected_gap), "max_gap_with_sentinel": max(sentinel_gap)},
           "aalen_johansen": {"engine": float(eng_aj[0, 1]), "package": pkg_aj, "difference": pkg_aj - float(eng_aj[0, 1]),
                              "at_risk_before_exit": 4, "at_risk_after_exit": 3}}
    out["all_within_tolerance"] = bool(max(state_period + state_pooled + exclude_period + exclude_pooled) <= 1e-12)
    pathlib.Path(args.out).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
