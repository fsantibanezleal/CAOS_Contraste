"""Experiment 1: the test on the committed history of case C14, on constructed histories, and by exhaustion.

    python manuscripts/behavioural-assumption-test-at-a-limit-breach/experiments/run_reproduction.py

Reads the committed documents ``data/derived/C14/vd-*.json`` and ``models-svb-2021-2022.json``, the raw inputs of the case (to rebuild the fitted weighted
average maturity at the three dates), and calls the engine ``riskvalidation`` 1.1.0. Writes ``results_reproduction.json`` next to this file.

Parts: (a) the committed rows against the engine rerun on the committed series; (b) the fitted weighted average maturity rebuilt from the raw inputs;
(c) the constructed histories with a known answer; (d) the engine against the closed-form count on every history of a binary grid up to six dates and on
20,000 random histories; (e) the two comparator tests of the engine rerun on the committed inputs; (f) the effect of a last-digit difference.
"""
from __future__ import annotations

import itertools
import json
import pathlib

import numpy as np
from riskvalidation.validation import irrbb as rv_irrbb

import core

HERE = pathlib.Path(__file__).resolve().parent
DERIVED = core.ROOT / "data" / "derived" / "C14"
VDS = ("vd-2021-q4", "vd-2022-q2", "vd-2022-q4")
SEED = 20261104


def doc(name: str) -> dict:
    return json.loads((DERIVED / f"{name}.json").read_text(encoding="utf-8"))


def num(x):
    """A statistic as JSON holds it: None for the absent number of a test that was not evaluated."""
    return None if x is None or x != x else x


def row_of(docs: dict, test_suffix: str) -> dict:
    return next(t for t in docs["tests"] if t["test_id"].endswith(test_suffix))


def committed() -> dict:
    """(a) The test on the committed series: the three parameters of the wholesale deposits at the three dates, with the breach flags of the outlier test."""
    docs = {v: doc(v) for v in VDS}
    fit = doc("models-svb-2021-2022")["fit"]
    by_date = {m["valuation_date"]: m for m in fit["nmd_models"]}
    dts = [docs[v]["outputs"]["valuation_date"] for v in VDS]
    breach = np.array([bool(docs[v]["outputs"]["scenarios"][0]["outlier"]["breached"]) for v in VDS])
    ratios = [float(docs[v]["outputs"]["scenarios"][0]["outlier"]["ratio"]) for v in VDS]
    seg = [next(s for s in docs[v]["outputs"]["nmd_segments"] if s["category"] == "wholesale") for v in VDS]
    series = {"weighted average maturity of the fitted portfolio": [by_date[d]["weighted_average_maturity_years"] for d in dts],
              "requested core share": [s["requested_core_share"] for s in seg],
              "requested core maturity": [s["requested_core_maturity_years"] for s in seg]}
    out: dict = {"dates": dts, "breach_flags": breach.tolist(), "outlier_ratios": ratios, "series": {}, "prefix_runs": {}}
    for name, vals in series.items():
        full = rv_irrbb.behavioural_change_at_breach(np.array(vals), np.array(dts, dtype="datetime64[D]"), breach)
        out["series"][name] = {"values": vals, "light": full.light.value, "statistic": num(full.statistic), "flagged_dates": full.extras.get("flagged_dates", [])}
    # the committed rows are the test at each date on the history up to it
    wam = np.array(series["weighted average maturity of the fitted portfolio"])
    for k, v in enumerate(VDS):
        run = rv_irrbb.behavioural_change_at_breach(wam[: k + 1], np.array(dts[: k + 1], dtype="datetime64[D]"), breach[: k + 1])
        row = row_of(docs[v], "behavioural_change_at_breach")
        out["prefix_runs"][v] = {"rerun_light": run.light.value, "rerun_statistic": num(run.statistic), "committed_light": row["light"],
                                 "committed_statistic": row["statistic"], "committed_flagged": row["extras"].get("flagged_dates", []),
                                 "rerun_flagged": run.extras.get("flagged_dates", []), "committed_note": row["notes"],
                                 "agree": run.light.value == row["light"] and num(run.statistic) == row["statistic"]
                                 and run.extras.get("flagged_dates", []) == row["extras"].get("flagged_dates", [])}
    control = rv_irrbb.behavioural_change_at_breach(wam, np.array(dts, dtype="datetime64[D]"), np.zeros(3, dtype=bool))
    out["control_no_breach"] = {"light": control.light.value, "statistic": control.statistic}
    return out


def rebuilt(real: core.RealSeries) -> dict:
    """(b) The fitted weighted average maturity at the three dates rebuilt from the raw inputs against the committed value."""
    fit = doc("models-svb-2021-2022")["fit"]
    rows = []
    for m in fit["nmd_models"]:
        i = real.fit_dates.index(m["valuation_date"])
        rows.append({"date": m["valuation_date"], "committed": m["weighted_average_maturity_years"], "rebuilt": float(real.wam[i]),
                     "abs_diff": abs(float(real.wam[i]) - m["weighted_average_maturity_years"])})
    d = np.abs(np.diff(real.wam))
    return {"dates": rows, "n_fits": int(real.wam.size), "first_fit": real.fit_dates[0], "last_fit": real.fit_dates[-1],
            "median_abs_change": float(np.median(d)), "max_abs_change": float(d.max()), "share_changes_zero": float(np.mean(d == 0.0)),
            "share_dates_at_cap": float(np.mean(real.wam >= core.WAM_MAX - 1e-9)), "wam": real.wam.tolist(), "fit_dates": real.fit_dates}


def constructed() -> list[dict]:
    """(c) Histories with a known answer: the four of the acceptance criterion, three more, and a single date."""
    d3 = ["2021-12-31", "2022-06-30", "2022-12-31"]
    cases = [
        ("parameter held through a breach", [4.0, 4.0, 4.0], [True, True, True], "green"),
        ("change with no breach", [4.0, 4.5, 5.0], [False, False, False], "green"),
        ("change before the breach", [4.0, 4.5, 4.5], [False, False, True], "green"),
        ("change at the breach", [4.0, 4.0, 4.5], [False, False, True], "red"),
        ("breach at the earlier date only", [4.0, 4.5, 4.5], [True, False, False], "green"),
        ("two changes at two breaches", [4.0, 4.5, 5.0], [False, True, True], "red"),
        ("change at the first date (no previous date)", [4.0, 4.0, 4.0], [True, False, False], "green"),
        ("a single date", [4.0], [True], "not_evaluated"),
    ]
    out = []
    for label, vals, flags, want in cases:
        r = core.engine_test(np.array(vals), np.array(flags, dtype=bool)) if len(vals) > 1 else \
            rv_irrbb.behavioural_change_at_breach(np.array(vals), np.array(d3[:1], dtype="datetime64[D]"), np.array(flags, dtype=bool))
        out.append({"label": label, "values": vals, "breach": flags, "expected": want, "light": r.light.value,
                    "statistic": r.statistic, "flagged_dates": r.extras.get("flagged_dates", []), "agree": r.light.value == want})
    return out


def exhaustive() -> dict:
    """(d) The engine against Equation (count) on every history of a binary grid (each change pattern with distinct amounts, each breach pattern) and on
    random real-valued histories with ties at a cap."""
    grid = {}
    total = bad = 0
    for t in range(2, 7):
        n_hist = 0
        for ch in itertools.product([0, 1], repeat=t - 1):
            theta = np.concatenate([[4.0], 4.0 + np.cumsum(np.array(ch) * np.arange(1, t))])
            for bits in itertools.product([False, True], repeat=t):
                b = np.array(bits)
                r = core.engine_test(theta, b)
                c = core.closed_form_count(theta, b)
                want = "red" if c else "green"
                n_hist += 1
                if r.statistic != c or r.light.value != want:
                    bad += 1
        grid[str(t)] = n_hist
        total += n_hist
    rng = np.random.default_rng(SEED)
    n_rand = 20_000
    bad_rand = 0
    for _ in range(n_rand):
        t = int(rng.integers(2, 25))
        theta = np.minimum(rng.normal(3.0, 1.5, t), 5.0).round(2) if rng.random() < 0.5 else rng.normal(3.0, 1.5, t)
        b = rng.random(t) < rng.uniform(0.05, 0.9)
        r = core.engine_test(theta, b)
        if r.statistic != core.closed_form_count(theta, b):
            bad_rand += 1
    return {"grid_histories_by_length": grid, "grid_total": total, "grid_disagreements": bad, "random_histories": n_rand, "random_disagreements": bad_rand,
            "seed": SEED}


def comparators() -> dict:
    """(e) The two other tests of the engine on the committed inputs: the stability of the weights and the economic value with and without the behavioural treatment."""
    out = {}
    for v in VDS:
        x = doc(v)
        o = x["outputs"]
        stab_w = np.array([w["weights"] for w in next(m for m in doc("models-svb-2021-2022")["fit"]["nmd_models"]
                                                       if m["valuation_date"] == o["valuation_date"])["stability"]])
        st = rv_irrbb.nmd_parameter_stability(stab_w, core.MATS)
        sc = o["scenarios"][0]["outlier"]
        thr = row_of(x, "eve_with_without_behavioural")["extras"]["thresholds"]
        beh = float(sc["eve_risk_measure"])
        con = float(thr["ratio_contractual"]) * float(sc["tier1"])
        ew = rv_irrbb.eve_with_without_behavioural(beh, con, float(sc["tier1"]))
        out[v] = {"stability_light": st.light.value, "stability_statistic": st.statistic, "stability_metric_years": st.metric,
                  "committed_stability_light": row_of(x, "nmd_parameter_stability")["light"],
                  "with_without_light": ew.light.value, "with_without_statistic": ew.statistic,
                  "committed_with_without_light": row_of(x, "eve_with_without_behavioural")["light"],
                  "hidden_breach": bool(ew.extras["hidden_breach"])}
    return out


def last_digit() -> dict:
    """(f) The test compares floating point numbers for inequality: a parameter recomputed to the last digit is a change."""
    rng = np.random.default_rng(SEED + 1)
    t = core.T_DEFAULT
    b = np.zeros(t, dtype=bool)
    b[[4, 8]] = True
    base = np.full(t, 4.0)
    exact = core.engine_test(base, b)
    rows = []
    for eps in (0.0, 1e-16, 1e-13, 1e-9, 1e-6):
        theta = base + eps * rng.standard_normal(t)
        r = core.engine_test(theta, b)
        rows.append({"noise_sd": eps, "light": r.light.value, "statistic": r.statistic})
    # the same held value recomputed through a different order of operations
    s1 = 0.1 + 0.2
    s2 = 0.3
    th = np.array([s1 if k % 2 == 0 else s2 for k in range(t)])
    r = core.engine_test(th, b)
    return {"held_exact": {"light": exact.light.value, "statistic": exact.statistic}, "noise": rows,
            "recomputed_0_1_plus_0_2_vs_0_3": {"equal_in_floating_point": bool(s1 == s2), "light": r.light.value, "statistic": r.statistic}}


def main() -> None:
    real = core.load_real()
    res = {"engine": "riskvalidation " + __import__("riskvalidation").__version__, "committed": committed(), "rebuilt": rebuilt(real),
           "constructed": constructed(), "exhaustive": exhaustive(), "comparators": comparators(), "last_digit": last_digit()}
    path = HERE / "results_reproduction.json"
    path.write_text(json.dumps(res, indent=1), encoding="utf-8")
    c = res["constructed"]
    print("constructed agree:", all(x["agree"] for x in c), "| exhaustive disagreements:", res["exhaustive"]["grid_disagreements"],
          res["exhaustive"]["random_disagreements"], "| committed rows agree:", all(v["agree"] for v in res["committed"]["prefix_runs"].values()))
    print("wrote", path)


if __name__ == "__main__":
    main()
