"""BS-14 on C04: the anchored tipping-point PD under informative rating withdrawals (riskvalidation 1.1.0
``transitions.withdrawals``). Closed-form checks of the real-data anchor on hand-built cohorts (the anchored k, the
cohort rules, the stability criterion fixed before the run, the tipping k of a master-scale boundary), the known-truth
coverage study at a few repetitions (structure, determinism, the inputs refused), the verdict read off the numbers, and
the family output's contract keys. The committed documents are checked in test_c04_bounds_committed.py."""
from __future__ import annotations

import datetime as dt
import json
import math

import numpy as np
import pytest

from pipeline.cases import c04_bounds as bnd
from pipeline.cases import c04_families as fam
from pipeline.io.cerep import Cohort

K = 7
D = 7


def _cohort(year: int, stay: list[float], defaults: list[float], withdrawn: list[float],
            d2: list[float] | None, d2_cohort: list[float] | None, has_default: bool = True) -> Cohort:
    """A cohort whose grade g keeps ``stay[g]`` ratings, defaults ``defaults[g]`` and loses ``withdrawn[g]``; the
    transitions put the stayers on the diagonal."""
    counts = np.zeros((K, K + 1))
    for g in range(K):
        counts[g, g] = stay[g]
        counts[g, D] = defaults[g] if has_default else 0
    w = np.asarray(withdrawn, dtype=float)
    return Cohort(
        cra="STPGB", begin=dt.date(year, 1, 1), end=dt.date(year, 12, 31), counts=counts, withdrawn=w,
        defaulted=None if d2 is None else np.asarray(d2, dtype=float), events=None,
        size=counts.sum(axis=1) + w, has_default_column=has_default,
        defaulted_cohort=None if d2_cohort is None else np.asarray(d2_cohort, dtype=float))


def _plain(x) -> bool:
    if isinstance(x, dict):
        return all(isinstance(k, str) and _plain(v) for k, v in x.items())
    if isinstance(x, list):
        return all(_plain(v) for v in x)
    if isinstance(x, float):
        return math.isfinite(x)
    return x is None or isinstance(x, (str, bool, int))


# ---------------------------------------------------------------------------------------------------------------------
# real cohorts: the default page (tab 2) as the anchor of the transition page (tab 4)

def _one_grade_cohorts(n: int, d: float, s: float, w: float, a: float, na: float, grade: int = 5) -> list[Cohort]:
    """``n`` identical cohorts that carry data in one grade (the others hold 100 stayers and no default)."""
    def row(v: float, other: float = 0.0) -> list[float]:
        return [v if g == grade else other for g in range(K)]

    return [_cohort(2000 + i, row(s, 100), row(d), row(w), row(a), row(na, 100)) for i in range(n)]


def test_the_anchored_k_is_the_closed_form():
    # D = 10, S = 190, W = 20, N = 220; the default page counts 14 of 200: X = N A / Na - D = 220 * 0.07 - 10 = 5.4
    out = bnd.real_bounds(_one_grade_cohorts(1, 10, 190, 20, 14, 200), has_default_column=True)
    g = out["grades"][5]
    c = g["cohorts"][0]
    x = 220 * (14 / 200) - 10
    assert c["defaults_implied"] == pytest.approx(x)
    assert c["k"] == pytest.approx(x * 190 / (10 * (20 - x)))
    assert c["pd_industry"] == pytest.approx(10 / 200)
    assert c["pd_anchored"] == pytest.approx((10 + x) / 220)
    assert c["k_low"] < c["k"] < c["k_high"]
    assert c["flag"] == "ok" and c["reason"] == "ok"
    # a single cohort is its own pool
    assert g["pooled"]["k"] == pytest.approx(c["k"])


def test_pooled_counts_are_the_sums_over_the_usable_cohorts():
    cohorts = _one_grade_cohorts(3, 10, 190, 20, 14, 200)
    g = bnd.real_bounds(cohorts, has_default_column=True)["grades"][5]
    p = g["pooled"]
    assert (p["defaults"], p["survivors"], p["withdrawn"]) == (30, 570, 60)
    assert (p["anchor_defaults"], p["anchor_cohort"]) == (42, 600)
    assert p["k"] == pytest.approx(g["cohorts"][0]["k"])  # identical cohorts: the pool has their rate


def test_a_cohort_without_the_second_source_or_without_withdrawals_is_left_out():
    base = _one_grade_cohorts(1, 10, 190, 20, 14, 200)
    no_tab2 = _cohort(2001, [100] * K, [0] * K, [5] * K, None, None)
    no_withdrawal = _cohort(2002, [190] * K, [10] * K, [0] * K, [10] * K, [200] * K)
    g = bnd.real_bounds([*base, no_tab2, no_withdrawal], has_default_column=True)["grades"][5]
    assert [c["label"] for c in g["cohorts"]] == ["2000"]


def test_an_agency_without_a_default_category_has_no_bounds():
    cohorts = [_cohort(2000, [100] * K, [0] * K, [5] * K, [1] * K, [105] * K, has_default=False)]
    assert bnd.real_bounds(cohorts, has_default_column=False) is None


def test_the_anchor_below_what_the_transition_page_saw_is_flagged_and_k_is_zero():
    # the default page counts 5 of 200 but the transition page already saw 10 defaults
    c = bnd.real_bounds(_one_grade_cohorts(1, 10, 190, 20, 5, 200), has_default_column=True)["grades"][5]["cohorts"][0]
    assert c["flag"] == "anchor_below_observed"
    assert c["k"] == 0.0


def test_stability_is_the_share_of_cohort_bands_that_contain_the_pooled_k():
    stable = bnd.real_bounds(_one_grade_cohorts(5, 10, 190, 20, 14, 200), has_default_column=True)["grades"][5]
    assert stable["stability"]["usable_cohorts"] == 5
    assert stable["stability"]["cohorts_containing_pooled_k"] == 5
    assert stable["stability"]["stable"] is True
    # two regimes: five cohorts with a high k and five with a very low one; the pooled k sits between
    # (large counts, so the bands are narrow against the gap between the regimes)
    hi = _one_grade_cohorts(5, 500, 9500, 1000, 950, 10000)
    lo = [_cohort(2010 + i, *(_row_of(5, v) for v in (9500, 500, 1000, 500, 10000))) for i in range(5)]
    mixed = bnd.real_bounds([*hi, *lo], has_default_column=True)["grades"][5]
    assert mixed["stability"]["share_cohorts_containing_pooled_k"] < bnd.STABILITY_SHARE
    assert mixed["stability"]["stable"] is False
    assert bnd.STABILITY_SHARE == 0.80  # fixed before the run


def _row_of(grade: int, v: float) -> list[float]:
    return [v if g == grade else 100.0 for g in range(K)]


def test_hypothesis_ii_reads_the_pooled_k_and_its_lower_bound():
    g = bnd.real_bounds(_one_grade_cohorts(2, 10, 190, 20, 14, 200), has_default_column=True)["grades"][5]
    assert g["k_above_1"]["holds"] is True
    # the stricter reading, the band's lower end above 1, is its own number (small counts: a wide band)
    assert g["k_above_1"]["holds_with_lower_bound"] is (g["k_above_1"]["pooled_k_low"] > 1.0)
    big = bnd.real_bounds(_one_grade_cohorts(2, 500, 9500, 1000, 950, 10000), has_default_column=True)["grades"][5]
    assert big["k_above_1"]["holds_with_lower_bound"] is True
    g = bnd.real_bounds(_one_grade_cohorts(2, 10, 190, 20, 10, 200), has_default_column=True)["grades"][5]
    assert g["pooled"]["k"] <= 1.0 + 1e-9 and g["k_above_1"]["holds"] is False


def test_the_tipping_k_is_at_the_geometric_mean_of_adjacent_industry_pds():
    cohorts = [_cohort(2000, [900, 900, 900, 900, 900, 900, 900], [0, 1, 2, 5, 20, 60, 200], [100] * 7, [1] * 7,
                       [1000] * 7)]
    out = bnd.real_bounds(cohorts, has_default_column=True)
    ind = [g["pooled"]["pd_industry"] for g in out["grades"]]
    for g in range(K - 1):
        tip = out["grades"][g]["tipping"]
        if ind[g] > 0 and ind[g + 1] > 0:
            assert tip["threshold"] == pytest.approx(math.sqrt(ind[g] * ind[g + 1]))
    assert out["grades"][K - 1]["tipping"] is None  # CCC-C has no worse grade to be mapped to
    # BB: PD(k) rises from the industry value 20/920 toward (20 + 100)/1000, the boundary to B is in between or beyond
    tip = out["grades"][4]["tipping"]
    assert tip["status"] in ("flips_up", "robust")
    if tip["status"] == "flips_up":
        from riskvalidation.transitions.withdrawals import withdrawal_pd

        assert float(withdrawal_pd(20, 900, 100, tip["k"])[0]) == pytest.approx(tip["threshold"], rel=1e-9)


def test_the_real_block_is_json_safe():
    out = bnd.real_bounds(_one_grade_cohorts(3, 10, 190, 20, 14, 200), has_default_column=True)
    assert _plain(json.loads(json.dumps(out)))
    assert out["level"] == 0.95 and out["stability_share"] == 0.80


# ---------------------------------------------------------------------------------------------------------------------
# the known-truth coverage study

Q = np.array([
    [0.0, 0.0800, 0.0080, 0.0010, 0.0003, 0.0001, 0.00002, 0.00008],
    [0.0100, 0.0, 0.0900, 0.0070, 0.0020, 0.0006, 0.0001, 0.0002],
    [0.0010, 0.0250, 0.0, 0.0600, 0.0060, 0.0020, 0.0004, 0.0006],
    [0.0003, 0.0030, 0.0450, 0.0, 0.0500, 0.0080, 0.0017, 0.0020],
    [0.0001, 0.0010, 0.0050, 0.0650, 0.0, 0.0900, 0.0100, 0.0090],
    [0.0, 0.0003, 0.0020, 0.0050, 0.0700, 0.0, 0.0900, 0.0330],
    [0.0, 0.0, 0.0010, 0.0020, 0.0100, 0.1500, 0.0, 0.3100],
    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
])
np.fill_diagonal(Q, -Q.sum(axis=1))
OBLIGORS = [80, 550, 1800, 1500, 800, 900, 200]
REPS = 6
RATE_KEYS = {"rejections", "n", "undefined", "rate", "se", "wilson_low", "wilson_high"}
TREATMENTS = ("industry", "unfollowed", "followed", "anchored", "identified")


def _study(informative: float = 9.0, reps: int = REPS, seed: int = 11, scale_seed: int = 12) -> dict:
    return bnd.bounds_rung(fam._paths, Q, OBLIGORS, seed=seed, scale_seed=scale_seed, reps=reps,
                           informative=informative, withdrawal_rate=fam.WITHDRAWAL_RATE, window=fam.WINDOW)


@pytest.fixture(scope="module")
def study() -> dict:
    return _study()


def test_the_study_has_the_four_designs_and_five_treatments(study):
    assert [d["id"] for d in study["designs"]] == ["first_year", "pooled", "capture70", "first_year_x10"]
    assert study["level"] == 0.95
    for d in study["designs"]:
        assert d["reps"] == REPS
        assert [t["id"] for t in d["treatments"]] == list(TREATMENTS)
        for t in d["treatments"]:
            assert len(t["coverage"]) == K and len(t["mean_width"]) == K and len(t["relative_bias"]) == K
            for r in t["coverage"]:
                assert set(r) == RATE_KEYS and r["n"] == REPS and 0 <= r["rate"] <= 1
            assert all(w is None or w >= 0 for w in t["mean_width"])
        assert set(d["anchored_k"]) == {"median", "q05", "q95", "share_infinite"}
    cohorts = {d["id"]: (d["cohorts"], d["cohort_scale"], d["capture"]) for d in study["designs"]}
    assert cohorts == {"first_year": (1, 1, 1.0), "pooled": (5, 1, 1.0), "capture70": (1, 1, 0.7),
                       "first_year_x10": (1, 10, 1.0)}
    assert len(study["truth"]) == K and all(0 < p < 1 for p in study["truth"])
    assert _plain(study)


def test_the_study_is_deterministic():
    a, b = _study(), _study()
    assert json.dumps(a) == json.dumps(b)
    assert json.dumps(_study(seed=12)) != json.dumps(a)


def test_the_truth_is_the_generators_one_year_pd(study):
    assert study["truth"] == pytest.approx(fam._pd(fam._paths(Q, OBLIGORS)).tolist())


def test_the_oracle_follows_the_withdrawn_so_it_is_not_biased_against_the_truth_at_k0():
    # without informative withdrawal the three point estimates agree on average within a Monte Carlo error: the
    # first-year relative bias of B is small for the industry and followed treatments
    d = _study(informative=0.0, reps=40)["designs"][0]
    by = {t["id"]: t for t in d["treatments"]}
    assert abs(by["followed"]["relative_bias"][5]) < 0.25
    assert abs(by["industry"]["relative_bias"][5]) < 0.25


def test_the_study_refuses_what_it_cannot_measure():
    with pytest.raises(ValueError, match="repetitions"):
        _study(reps=1)
    with pytest.raises(ValueError, match="informative"):
        _study(informative=-1.0)


# ---------------------------------------------------------------------------------------------------------------------
# the verdict, read off the numbers


def _rate(rate: float, n: int = 200) -> dict:
    return {"rejections": round(rate * n), "n": n, "undefined": 0, "rate": rate, "se": 0.0, "wilson_low": rate,
            "wilson_high": rate}


def _design(did: str, cov: dict[str, float]) -> dict:
    return {"id": did, "reps": 200, "cohorts": 1, "cohort_scale": 1, "capture": 1.0, "seed_key": "x", "seed": 1,
            "treatments": [{"id": t, "coverage": [_rate(cov.get(t, 0.9))] * K, "mean_width": [0.01] * K,
                            "relative_bias": [0.0] * K} for t in TREATMENTS],
            "anchored_k": {"median": [1.0] * K, "q05": [1.0] * K, "q95": [1.0] * K, "share_infinite": [0.0] * K}}


def _rungs(first: dict[str, float], pooled: dict[str, float], x10: dict[str, float]) -> list[dict]:
    return [{"value": k, "bounds": {"level": 0.95, "truth": [0.01] * K,
                                    "designs": [_design("first_year", first), _design("pooled", pooled),
                                                _design("first_year_x10", x10)]}}
            for k in fam.INFORMATIVE]


def test_the_verdict_holds_where_the_anchor_covers_and_the_existing_treatments_do_not():
    cov = {"anchored": 0.99, "industry": 0.20, "unfollowed": 0.10, "followed": 0.30}
    v = bnd.verdict(_rungs(cov, cov, cov))
    assert v["grade"] == 5 and v["reps"] == 200
    by = {(r["id"], r["design"]): r for r in v["rows"]}
    assert by[("anchored-coverage", "pooled")]["holds"] is True
    assert by[("existing-coverage", "pooled")]["holds"] is True
    assert by[("anchored-better", "pooled")]["holds"] is True
    assert v["summary"]["refuted"] is False


def test_the_verdict_refutes_where_the_anchor_does_not_beat_the_existing_treatments():
    cov = {"anchored": 0.80, "industry": 0.95, "unfollowed": 0.95, "followed": 0.95}
    v = bnd.verdict(_rungs(cov, cov, cov))
    by = {(r["id"], r["design"]): r for r in v["rows"]}
    assert by[("anchored-coverage", "first_year")]["holds"] is False
    assert by[("existing-coverage", "first_year")]["holds"] is False
    assert by[("anchored-better", "first_year")]["holds"] is False
    assert v["summary"]["refuted"] is True


def test_the_verdict_reports_each_existing_treatment_apart():
    cov = {"anchored": 0.99, "industry": 0.83, "unfollowed": 0.83, "followed": 0.96}
    v = bnd.verdict(_rungs(cov, cov, cov))
    rows = [r for r in v["rows"] if r["id"] == "existing-coverage" and r["design"] == "first_year"]
    assert {r["treatment"]: r["holds"] for r in rows} == {"industry": False, "unfollowed": False, "followed": False}
    assert all(r["informative"] == 9.0 and r["threshold"] == 0.5 for r in rows)
    ac = [r for r in v["rows"] if r["id"] == "anchored-coverage" and r["design"] == "first_year"]
    assert [r["informative"] for r in ac] == [1.0, 3.0, 9.0] and all(r["threshold"] == 0.90 for r in ac)


# ---------------------------------------------------------------------------------------------------------------------
# the family output


def test_the_withdrawals_family_carries_the_bounds_and_its_verdict():
    out = fam.family_outputs("withdrawals", Q, OBLIGORS, 20261006, reps=REPS, source="hand-made")
    for r in out["rungs"]:
        assert set(r["bounds"]) == {"level", "truth", "designs"}
        assert [d["id"] for d in r["bounds"]["designs"]] == ["first_year", "pooled", "capture70", "first_year_x10"]
    assert out["bounds_verdict"]["grade"] == 5
    assert out["bounds_verdict"]["rows"]
    for family in ("markov", "thin"):
        other = fam.family_outputs(family, Q, OBLIGORS, 20261006, reps=REPS, source="hand-made")
        assert other["bounds_verdict"] is None
    assert _plain(out)


def test_the_bounds_use_their_own_draws_so_the_existing_rung_numbers_do_not_move():
    with_bounds = fam.family_outputs("withdrawals", Q, OBLIGORS, 20261006, reps=REPS, source="hand-made")
    again = fam.family_outputs("withdrawals", Q, OBLIGORS, 20261006, reps=REPS, source="hand-made")
    keep = ("pd_removed", "pd_kept", "pd_followed", "pd_latent", "withdrawn_share", "seed", "seed_key")
    for a, b in zip(with_bounds["rungs"], again["rungs"], strict=True):
        assert {k: a[k] for k in keep} == {k: b[k] for k in keep}
    # the bounds' seeds are keys of their own, never the rung's
    for r in with_bounds["rungs"]:
        seeds = {d["seed_key"] for d in r["bounds"]["designs"]}
        assert r["seed_key"] not in seeds
