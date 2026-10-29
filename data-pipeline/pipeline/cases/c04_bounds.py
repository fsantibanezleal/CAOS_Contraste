"""C04, BS-14: the PD by grade under informative rating withdrawals, with the anchored tipping point.

Removing the withdrawn ratings, keeping them in the denominator or following them each fix one answer to a question
the transition page cannot answer: would a withdrawn rating have defaulted? riskvalidation 1.1.0's
``transitions.withdrawals`` states the PD as a function of the odds ratio ``k`` of withdrawal for ratings that default
within the period, PD(k) = (D + X(k)) / N with X(k) = W k D / (k D + S) (k = 1 the usual estimate, k to infinity
Manski's 1989 bound), finds the ``k`` at which a decision flips, and, where a second source counts the defaults of the
same grade differently, reads ``k`` off that source (the anchor). The sources, the model and its assumptions are in
that module's text and docs/transitions/06_withdrawal-bounds.md of the engine; this module runs it on C04's data. Two
parts:

- ``bounds_rung``: the known-truth study. The EM generator of S&P's counts drives ``RatingPaths`` with withdrawal at 6%
  a year and 6% (1 + informative) in the year before default (the withdrawals family's own setting); per repetition the
  latent and the observed paths come from the same stream, the transition page's counts (D, S, W) are read off the
  observed paths and the default page's count off the latent ones (a rating that defaulted within the year, withdrawn
  or not: CEREP's tab 2). Coverage of the true one-year PD by grade of the Jeffreys interval of each existing treatment
  (``industry`` k = 1, ``unfollowed`` k = 0, ``followed``, the oracle that reads the year end of the withdrawn: it is
  the default page's count) and of the anchored interval and the identified band of ``withdrawal_bounds``. Four
  designs: ``first_year`` (the model's exact setting, nobody was withdrawn earlier), ``pooled`` (Contraste's own five
  annual cohorts pooled, where a rating withdrawn in an earlier year is missing from a later cohort, a selection the
  one-period model does not see), ``capture70`` (the second source counts only 70% of the true defaults: a definition
  mismatch) and ``first_year_x10`` (ten times the cohort, where the bias is large against the sampling noise). The
  draws are the study's own (seed keys ``withdrawals-bounds:...``), so the family's other numbers do not move.
- ``real_bounds``: the anchored ``k`` of an agency's real cohorts, the default page (tab 2) as the anchor of the
  transition page (tab 4), per annual cohort and pooled, per grade, with the tipping ``k`` of the master-scale
  boundary between a grade and the next one.

The criteria below are the plan's (docs/design/SDD.md, BS-14), fixed here before any run: the anchored interval covers
the true PD in at least 90% of the repetitions at informative 1, 3 and 9; the existing treatments cover it in under
50% at 9; the anchored ``k`` is stable across years when at least 80% of the cohorts' ``k`` bands contain the pooled
``k``; ``k`` of CCC to C above 1. Whatever the result, the documents carry it. The anchored interval is conditional on
the two sources defining default alike (they do not exactly: ESMA sets no common definition).
"""
from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

import numpy as np
from riskvalidation.harness import Rate
from riskvalidation.transitions.intervals import pd_jeffreys
from riskvalidation.transitions.withdrawals import withdrawal_bounds

from ..io.cerep import GRADES as SCALE_GRADES
from ..io.cerep import Cohort

GRADES: list[str] = list(SCALE_GRADES)
K = len(GRADES)
D = K                                  # the default column of a cohort's 7 x 8 counts
LEVEL = 0.95
CAPTURE = 0.7                          # the second source counts this share of the true defaults (capture70)
SCALE = 10                             # the cohort multiplier of first_year_x10
B = GRADES.index("B")                  # the grade the plan's hypothesis is read on
TREATMENTS = ("industry", "unfollowed", "followed", "anchored", "identified")
DESIGNS = ("first_year", "pooled", "capture70", "first_year_x10")

# the plan's criteria (docs/design/SDD.md BS-14), fixed before the run
ANCHORED_COVERAGE = 0.90               # the anchored interval covers at least this share at informative 1, 3 and 9
ANCHORED_AT = (1.0, 3.0, 9.0)
EXISTING_COVERAGE = 0.50               # an existing treatment covers under this share at informative 9
EXISTING_AT = 9.0
STABILITY_SHARE = 0.80                 # stable when this share of the cohorts' k bands contain the pooled k
VERDICT_DESIGNS = ("first_year", "pooled", "first_year_x10")


def seed_keys(informative: float) -> tuple[str, str]:
    """The seed keys of the study's two draws of a rung (the standard cohort and the ten-fold one); never the rung's."""
    base = f"withdrawals-bounds:informative={informative:g}"
    return base, f"{base}:x{SCALE}"


def _f(x: Any) -> float | None:
    """A finite float or None (JSON holds no NaN or infinity)."""
    if x is None:
        return None
    v = float(x)
    return v if math.isfinite(v) else None


def _list(a: Any) -> list[float | None]:
    return [_f(x) for x in np.asarray(a, dtype=float)]


# ---------------------------------------------------------------------------------------------------------------------
# the known-truth study


def _intervals(res: dict[str, Any], followed: np.ndarray) -> dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Each treatment's (lower, upper, point) by grade for one repetition."""
    d, s, n = res["defaults"], res["survivors"], res["n"]
    out: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    for name, (num, den) in {"industry": (d, d + s), "unfollowed": (d, n), "followed": (followed, n)}.items():
        iv = pd_jeffreys(num, den, level=LEVEL)
        out[name] = (np.asarray(iv["lower"], dtype=float), np.asarray(iv["upper"], dtype=float),
                     np.asarray(iv["estimate"], dtype=float))
    an = res["anchor"]
    out["anchored"] = (np.asarray(an["lower"], dtype=float), np.asarray(an["upper"], dtype=float),
                       np.asarray(an["pd"], dtype=float))
    idn = res["identified"]
    out["identified"] = (np.asarray(idn["lower"], dtype=float), np.asarray(idn["upper"], dtype=float),
                         np.asarray(res["pd_industry"], dtype=float))
    return out


def _study(latent_gen: Any, gen: Any, truth: np.ndarray, seed: int, reps: int,
           designs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The designs' records over ``reps`` paired draws (the observed paths are the latent ones truncated at a
    withdrawal: the engine draws the withdrawals after the path, from the same stream)."""
    g = truth.shape[0]
    children = np.random.SeedSequence(seed).spawn(reps)
    second = np.random.SeedSequence(seed + 1).spawn(reps)
    acc = {d["id"]: {"hit": {t: np.zeros((reps, g), dtype=bool) for t in TREATMENTS},
                     "und": {t: np.zeros((reps, g), dtype=bool) for t in TREATMENTS},
                     "width": {t: np.full((reps, g), np.nan) for t in TREATMENTS},
                     "point": {t: np.full((reps, g), np.nan) for t in TREATMENTS},
                     "k": np.full((reps, g), np.nan)} for d in designs}
    m = latent_gen.n_states
    for r, (ch, ch2) in enumerate(zip(children, second, strict=True)):
        lat = latent_gen.draw(np.random.default_rng(ch))
        obs = gen.draw(np.random.default_rng(ch))
        o, la = obs["snapshot_states"], lat["snapshot_states"]
        years = len(obs["steps"])
        # the default page: each year's cohort as observed, its end read on the latent paths
        follow = [latent_gen.snapshot_counts(np.column_stack([o[:, t], la[:, t + 1]]))[0] for t in range(years)]
        for design in designs:
            n_steps = years if design["pooled"] else 1
            counts = sum(s["counts"] for s in obs["steps"][:n_steps])
            withdrawn = sum(s["withdrawn"] for s in obs["steps"][:n_steps])
            followed = sum(f["counts"][:, m - 1] for f in follow[:n_steps])[: m - 1]
            anchor = followed.copy()
            if design["capture"] < 1.0:
                anchor = np.random.default_rng(ch2).binomial(followed.astype(int), design["capture"]).astype(float)
            res = withdrawal_bounds(counts, withdrawn, anchor_defaults=anchor, level=LEVEL)
            a = acc[design["id"]]
            for name, (lo, hi, pt) in _intervals(res, followed).items():
                und = ~(np.isfinite(lo) & np.isfinite(hi))
                a["und"][name][r] = und
                a["hit"][name][r] = (lo <= truth) & (truth <= hi) & ~und
                a["width"][name][r], a["point"][name][r] = hi - lo, pt
            a["k"][r] = res["anchor"]["k"]
    out = []
    for design in designs:
        a = acc[design["id"]]
        treatments = []
        for name in TREATMENTS:
            treatments.append({
                "id": name,
                "coverage": [Rate(int(a["hit"][name][:, i].sum()), reps, int(a["und"][name][:, i].sum())).to_dict()
                             for i in range(g)],
                "mean_width": _list(np.nanmean(a["width"][name], axis=0)),
                "relative_bias": _list(np.nanmean(a["point"][name], axis=0) / truth - 1.0)})
        k = a["k"]
        finite = [k[np.isfinite(k[:, i]), i] for i in range(g)]
        out.append({
            "id": design["id"], "reps": reps, "cohorts": design["cohorts"], "cohort_scale": design["scale"],
            "capture": design["capture"], "seed_key": design["seed_key"], "seed": seed,
            "treatments": treatments,
            "anchored_k": {"median": [_f(np.median(x)) if x.size else None for x in finite],
                           "q05": [_f(np.quantile(x, 0.05)) if x.size else None for x in finite],
                           "q95": [_f(np.quantile(x, 0.95)) if x.size else None for x in finite],
                           "share_infinite": [float(np.mean(np.isposinf(k[:, i]))) for i in range(g)]}})
    return out


def bounds_rung(make_paths: Callable[..., Any], q: np.ndarray, obligors: list[int], *, seed: int, scale_seed: int,
                reps: int, informative: float, withdrawal_rate: float, window: float) -> dict[str, Any]:
    """The coverage study of one informativeness: ``make_paths(q, obligors, years=5, **defect)`` builds the
    ``RatingPaths`` (the ten-fold design needs one year only); ``seed`` and ``scale_seed`` seed the standard and the ten-fold cohort's draws (one stream per
    repetition, spawned as ``harness.simulate`` does). Returns ``{"level", "truth", "designs"}`` with the four designs
    of the module text, each the coverage of the true one-year PD by grade, the mean width and the relative bias of the
    point estimate, for the five treatments."""
    if reps < 2:
        raise ValueError("at least two repetitions are needed for a Monte Carlo standard error (reps)")
    if not (math.isfinite(informative) and informative >= 0):
        raise ValueError("informative must be a finite number, 0 or more (the extra withdrawal odds before default)")
    defect = {"withdrawal_rate": withdrawal_rate, "informative": informative, "window": window}
    base, scaled = seed_keys(informative)
    latent = make_paths(q, obligors)
    truth = np.asarray(latent.truth()["pd_by_grade"]["1"], dtype=float)
    one = _study(latent, make_paths(q, obligors, **defect), truth, seed, reps, [
        {"id": "first_year", "pooled": False, "cohorts": 1, "scale": 1, "capture": 1.0, "seed_key": base},
        {"id": "pooled", "pooled": True, "cohorts": 5, "scale": 1, "capture": 1.0, "seed_key": base},
        {"id": "capture70", "pooled": False, "cohorts": 1, "scale": 1, "capture": CAPTURE, "seed_key": base}])
    big_obligors = [int(o) * SCALE for o in obligors]
    big = _study(make_paths(q, big_obligors, 1), make_paths(q, big_obligors, 1, **defect), truth, scale_seed, reps, [
        {"id": "first_year_x10", "pooled": False, "cohorts": 1, "scale": SCALE, "capture": 1.0, "seed_key": scaled}])
    return {"level": LEVEL, "truth": _list(truth), "designs": [*one, *big]}


def _coverage(rungs: list[dict[str, Any]], design: str, informative: float, treatment: str) -> dict[str, Any]:
    rung = next(r for r in rungs if r["value"] == informative)
    d = next(x for x in rung["bounds"]["designs"] if x["id"] == design)
    return next(t for t in d["treatments"] if t["id"] == treatment)["coverage"][B]


def verdict(rungs: list[dict[str, Any]]) -> dict[str, Any]:
    """The plan's hypothesis (i) read off the rungs' coverage of grade B's true PD, design by design, with the criteria
    fixed in this module: ``anchored-coverage`` (at least 90% at informative 1, 3 and 9), ``existing-coverage``
    (each existing treatment under 50% at 9; the oracle ``followed`` is reported apart: it needs the year end of the
    withdrawn, which no transition page has), ``anchored-better`` (the anchored interval covers more than every
    existing treatment at 9; the plan's refutation is that it does not). ``summary`` says whether the hypothesis was
    refuted in any design the verdict reads."""
    rows: list[dict[str, Any]] = []
    reps = 0
    for design in VERDICT_DESIGNS:
        for k in ANCHORED_AT:
            if design == "first_year_x10" and k != EXISTING_AT:
                continue
            c = _coverage(rungs, design, k, "anchored")
            reps = c["n"]
            rows.append({"id": "anchored-coverage", "design": design, "informative": k, "treatment": "anchored",
                         "value": c["rate"], "mcse": c["se"], "threshold": ANCHORED_COVERAGE,
                         "comparison": "at_least", "holds": c["rate"] >= ANCHORED_COVERAGE})
        existing = {}
        for treatment in ("industry", "unfollowed", "followed"):
            c = _coverage(rungs, design, EXISTING_AT, treatment)
            existing[treatment] = c["rate"]
            rows.append({"id": "existing-coverage", "design": design, "informative": EXISTING_AT,
                         "treatment": treatment, "value": c["rate"], "mcse": c["se"],
                         "threshold": EXISTING_COVERAGE, "comparison": "below", "holds": c["rate"] < EXISTING_COVERAGE})
        anchored = _coverage(rungs, design, EXISTING_AT, "anchored")
        best = max(existing.values())
        rows.append({"id": "anchored-better", "design": design, "informative": EXISTING_AT, "treatment": "anchored",
                     "value": anchored["rate"], "mcse": anchored["se"], "threshold": best,
                     "comparison": "above", "holds": anchored["rate"] > best})
    refuted = any(r["id"] == "anchored-better" and not r["holds"] for r in rows)
    return {"grade": B, "reps": reps, "level": LEVEL, "designs": list(VERDICT_DESIGNS), "rows": rows,
            "summary": {"refuted": refuted,
                        "anchored_covers_90": all(r["holds"] for r in rows if r["id"] == "anchored-coverage"),
                        "existing_under_50": all(r["holds"] for r in rows if r["id"] == "existing-coverage"
                                                 and r["treatment"] != "followed")}}


# ---------------------------------------------------------------------------------------------------------------------
# the real cohorts


def _one(d: float, s: float, w: float, a: float, na: float) -> dict[str, Any]:
    """One grade of one period (or of the pooled periods): the engine on a two-state matrix, the transition page's D, S
    and W against the default page's A over its cohort Na."""
    r = withdrawal_bounds([[s, d], [0.0, 0.0]], [w, 0.0], anchor_defaults=[a], anchor_obligors=[na], level=LEVEL)
    an = r["anchor"]
    ks = {"k": float(an["k"][0]), "k_low": float(an["k_low"][0]), "k_high": float(an["k_high"][0])}
    return {"defaults": d, "survivors": s, "withdrawn": w, "anchor_defaults": a, "anchor_cohort": na,
            "pd_industry": float(r["pd_industry"][0]), "pd_anchor_rate": float(an["anchor_rate"][0]),
            "pd_anchored": float(an["pd"][0]), "pd_lower": _f(an["lower"][0]), "pd_upper": _f(an["upper"][0]),
            "defaults_implied": float(an["defaults_implied"][0]), **{k: _f(v) for k, v in ks.items()},
            "infinite": [k for k, v in ks.items() if math.isinf(v)],
            "flag": an["flag"][0], "reason": r["reason"][0], "_k": ks}


def _public(rec: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in rec.items() if not k.startswith("_")}


def _tipping(d: float, s: float, w: float, threshold: float, next_grade: str) -> dict[str, Any]:
    r = withdrawal_bounds([[s, d], [0.0, 0.0]], [w, 0.0], thresholds=[threshold], level=LEVEL)
    t = r["tipping"]
    k = float(t["k"][0])
    return {"threshold": threshold, "next_grade": next_grade, "k": _f(k), "infinite": ["k"] if math.isinf(k) else [],
            "decision_industry": t["decision_industry"][0], "status": t["status"][0],
            "pd_manski_upper": float(r["pd_manski_upper"][0])}


def real_bounds(cohorts: list[Cohort], *, has_default_column: bool) -> dict[str, Any] | None:
    """The anchored ``k`` of an agency's annual cohorts, per grade, or None where the transition page has no default
    category (Moody's: there is no D to anchor). A cohort enters a grade when it has the default page (tab 2), the grade
    has ratings and withdrawals in it, and tab 2 does not count more defaulted ratings than its own cohort holds.
    ``tipping``: the master-scale boundary between a grade and the next is the geometric mean of their industry PDs
    (the transition page's, pooled over all the cohorts), and the tipping ``k`` is where the grade's PD(k) reaches it:
    the informativeness it takes to move the grade to the next notch (None for the last grade, or where a PD is 0).
    Stability (the criterion fixed in the module text) and hypothesis (ii), ``k`` above 1, are read per grade."""
    if not has_default_column:
        return None
    out_grades = []
    sums_all = np.zeros((K, 3))
    for c in cohorts:
        d = c.counts[:, D]
        sums_all += np.column_stack([d, c.counts.sum(axis=1) - d, c.withdrawn])
    ind = np.divide(sums_all[:, 0], sums_all[:, 0] + sums_all[:, 1], out=np.zeros(K),
                    where=(sums_all[:, 0] + sums_all[:, 1]) > 0)
    for g in range(K):
        recs, sums = [], np.zeros(5)
        for c in cohorts:
            if c.defaulted is None:
                continue
            d = float(c.counts[g, D])
            s = float(c.counts[g].sum() - d)
            w = float(c.withdrawn[g])
            a = float(c.defaulted[g])
            na = float((c.defaulted_cohort if c.defaulted_cohort is not None else c.size)[g])
            if d + s + w <= 0 or na <= 0 or a > na or w <= 0:
                continue
            rec = _one(d, s, w, a, na)
            rec["label"] = c.label
            recs.append(rec)
            sums += (d, s, w, a, na)
        tip = None
        if g < K - 1 and ind[g] > 0 and ind[g + 1] > 0:
            tip = _tipping(*sums_all[g], math.sqrt(ind[g] * ind[g + 1]), GRADES[g + 1])
        if not recs:
            out_grades.append({"grade": GRADES[g], "cohorts": [], "pooled": None, "k_over_cohorts": None,
                               "stability": None, "k_above_1": None, "tipping": tip})
            continue
        pooled = _one(*sums)
        kp = pooled["_k"]["k"]
        usable = [r for r in recs if r["reason"] == "ok" and math.isfinite(r["_k"]["k_low"])
                  and not math.isnan(r["_k"]["k_high"])]
        contain = [r for r in usable if r["_k"]["k_low"] <= kp <= r["_k"]["k_high"]]
        ks = np.array([r["_k"]["k"] for r in usable if math.isfinite(r["_k"]["k"])])
        share = len(contain) / len(usable) if usable else 0.0
        out_grades.append({
            "grade": GRADES[g], "cohorts": [_public(r) for r in recs], "pooled": _public(pooled),
            "k_over_cohorts": {"n": int(ks.size), "median": _f(np.median(ks)) if ks.size else None,
                               "q25": _f(np.quantile(ks, 0.25)) if ks.size else None,
                               "q75": _f(np.quantile(ks, 0.75)) if ks.size else None,
                               "share_above_1": _f(np.mean(ks > 1.0)) if ks.size else None},
            "stability": {"usable_cohorts": len(usable), "cohorts_containing_pooled_k": len(contain),
                          "share_cohorts_containing_pooled_k": share, "stable": bool(usable) and share >= STABILITY_SHARE},
            "k_above_1": {"pooled_k": _f(kp), "pooled_k_low": _f(pooled["_k"]["k_low"]),
                          "holds": bool(kp > 1.0), "holds_with_lower_bound": bool(pooled["_k"]["k_low"] > 1.0)},
            "tipping": tip})
    return {"level": LEVEL, "stability_share": STABILITY_SHARE, "grades": out_grades}
