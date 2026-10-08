"""C04's agency variants (CT-403, CT-404, CT-407, CT-415) on synthetic cohorts built by hand: the three default
definitions and the one that keeps withdrawals, d2 over tab 2's own cohort, the long-run average against the pooled
rate, the last five cohorts, Moody's nulls, the definition gaps over the cohorts both pages cover, the lifetime check
of a window, the outputs' keys exactly as contract.md section 1 lists them, JSON safety, agreement with direct
riskvalidation calls, a grade without ratings in one cohort, the generators the engine cannot form (a diverging log
series, a grade that never stays), an agency whose pages differ in the default category, tab 3's events beyond the
cohort, every refusal, and determinism whatever the order. No CEREP answer is read."""
from __future__ import annotations

import dataclasses
import datetime as dt
import json

import numpy as np
import pytest
from riskvalidation.transitions import embedding, estimators, intervals, mobility
from riskvalidation.transitions.em import em_generator
from riskvalidation.validation import rating_system
from riskvalidation.validation import transitions as markov
from scipy.linalg import expm

from pipeline.cases import c04_agency as a4
from pipeline.io import cerep

# Each row: the counts to AAA, AA, A, BBB, BB, B, CCC-C and D at the end, then the withdrawals; rows by grade at the
# beginning. 2011 has no AAA rating at all; in 2013 every AAA rating was withdrawn and tab 2 is missing.
ANNUAL = {
    2010: ([[40, 4, 0, 0, 0, 0, 0, 0, 2],
            [2, 60, 5, 1, 0, 0, 0, 0, 3],
            [0, 3, 80, 6, 1, 0, 0, 0, 4],
            [0, 0, 4, 90, 5, 1, 0, 0, 5],
            [0, 0, 0, 5, 50, 6, 1, 1, 4],
            [0, 0, 0, 0, 4, 40, 5, 2, 3],
            [0, 0, 0, 0, 0, 3, 12, 5, 2]],
           [0, 0, 0, 0, 2, 3, 6], [0, 0, 0, 0, 2, 4, 8]),
    2011: ([[0, 0, 0, 0, 0, 0, 0, 0, 0],
            [1, 55, 6, 0, 1, 0, 0, 0, 2],
            [0, 4, 85, 5, 0, 0, 0, 0, 6],
            [0, 0, 6, 88, 4, 1, 1, 0, 4],
            [0, 0, 1, 4, 52, 5, 2, 2, 5],
            [0, 0, 0, 1, 3, 38, 6, 3, 4],
            [0, 0, 0, 0, 1, 2, 10, 6, 3]],
           [0, 0, 0, 0, 3, 4, 8], [0, 0, 0, 0, 3, 4, 9]),
    2012: ([[38, 5, 1, 0, 0, 0, 0, 0, 1],
            [3, 58, 4, 1, 0, 0, 0, 0, 4],
            [0, 5, 82, 7, 0, 1, 0, 0, 5],
            [0, 1, 5, 86, 7, 2, 0, 1, 6],
            [0, 0, 0, 6, 48, 7, 2, 3, 4],
            [0, 0, 0, 0, 5, 36, 7, 4, 5],
            [0, 0, 0, 0, 0, 4, 9, 8, 4]],
           [0, 0, 0, 1, 4, 5, 10], [0, 0, 0, 1, 4, 6, 12]),
    2013: ([[0, 0, 0, 0, 0, 0, 0, 0, 3],
            [2, 57, 5, 0, 0, 0, 0, 0, 3],
            [0, 4, 84, 6, 1, 0, 0, 0, 5],
            [0, 0, 5, 89, 6, 1, 0, 0, 5],
            [0, 0, 0, 5, 51, 6, 1, 2, 5],
            [0, 0, 0, 0, 4, 39, 6, 3, 4],
            [0, 0, 0, 0, 0, 3, 11, 7, 2]],
           None, [0, 0, 0, 0, 2, 4, 9]),
}
SIZES = {2010: [46, 71, 94, 105, 67, 54, 22], 2011: [0, 65, 100, 104, 71, 55, 22],
         2012: [45, 70, 100, 108, 70, 57, 25], 2013: [3, 67, 100, 106, 70, 56, 23]}
H1_2012 = [[42, 2, 0, 0, 0, 0, 0, 0, 1],
           [1, 64, 2, 1, 0, 0, 0, 0, 2],
           [0, 2, 92, 3, 0, 0, 0, 0, 3],
           [0, 0, 2, 98, 4, 1, 0, 0, 3],
           [0, 0, 0, 3, 57, 4, 1, 1, 4],
           [0, 0, 0, 0, 2, 47, 4, 2, 2],
           [0, 0, 0, 0, 0, 2, 17, 4, 2]]
H2_2012 = [[41, 3, 1, 0, 0, 0, 0, 0, 0],
           [2, 60, 3, 0, 0, 0, 0, 0, 2],
           [0, 3, 88, 4, 0, 1, 0, 0, 2],
           [0, 1, 3, 90, 3, 1, 0, 1, 3],
           [0, 0, 0, 3, 52, 3, 1, 2, 2],
           [0, 0, 0, 0, 3, 45, 3, 2, 3],
           [0, 0, 0, 0, 0, 2, 18, 4, 1]]

# contract.md section 1, key by key
TOP = {"kind", "agency", "attribution", "grades", "states", "cohorts", "semesters", "pd", "lra", "pooled", "embedding",
       "generators", "mobility", "ecb", "homogeneity", "semesters_vs_year", "definition_gap", "lifetime"}
COHORT_KEYS = {"label", "begin", "end", "size", "counts", "withdrawn", "defaulted", "events", "defaulted_cohort",
               "tab2_gap"}
LRA_ENTRY = {"rate", "cohorts", "defaults", "n", "pooled_rate", "wald", "agresti_coull", "jeffreys", "last5"}
EMBEDDING_KEYS = {"S", "series_converges", "det", "prod_diagonal", "theorem3", "exact_generator_excluded",
                  "stochastically_monotone", "monotonicity_violations"}
GENERATOR_KEYS = {"generator", "valid", "l1", "pd_1y", "pd_5y"}


def _cohort(cra, begin, end, rows, defaulted=None, events=None, has_default=True, tab2=None):
    """A cohort as the reader builds it: with tab 2, tab 2's own cohort (``tab2``, else tab 4's rows, the reader's
    value where the rows reproduce tab 2's rates) and the signed largest relative gap to tab 4's rows."""
    a = np.asarray(rows, dtype=float)
    counts, withdrawn = a[:, :8], a[:, 8]
    size = counts.sum(axis=1) + withdrawn
    base = gap = None
    if defaulted is not None:
        base = size if tab2 is None else np.asarray(tab2, dtype=float)
        rel = np.divide(base - size, size, out=np.zeros(7), where=size > 0)
        gap = float(rel[np.argmax(np.abs(rel))])
    return cerep.Cohort(cra, begin, end, counts, withdrawn, None if defaulted is None else np.asarray(defaulted, float),
                        None if events is None else np.asarray(events, float), size, has_default, base, gap)


def _year(cra, y, rows, defaulted=None, events=None, has_default=True, tab2=None):
    return _cohort(cra, dt.date(y, 1, 1), dt.date(y, 12, 31), rows, defaulted, events, has_default, tab2)


def _window(cra, y0, y1, rows, defaulted=None, has_default=True, tab2=None):
    return _cohort(cra, dt.date(y0, 1, 1), dt.date(y1, 12, 31), rows, defaulted, None, has_default, tab2)


def _half(cra, y, h, rows, has_default=True):
    b, e = (dt.date(y, 1, 1), dt.date(y, 6, 30)) if h == 1 else (dt.date(y, 7, 1), dt.date(y, 12, 31))
    return _cohort(cra, b, e, rows, has_default=has_default)


def _moodys_rows(rows):
    """Moody's transition page has no default category: what ended in default is not on the page (here, counted
    as withdrawn)."""
    return [r[:7] + [0, r[7] + r[8]] for r in rows]


def _sp_annual(cra="STPGB", tab2=True):
    return [_year(cra, y, rows, d if tab2 else None, e) for y, (rows, d, e) in ANNUAL.items()]


def _sp_semesters(cra="STPGB"):
    return [_half(cra, 2012, 1, H1_2012), _half(cra, 2012, 2, H2_2012)]


def _p(rows):
    """A cohort matrix by hand: each grade's counts over their sum (withdrawals removed), default absorbing."""
    a = np.asarray(rows, dtype=float)[:, :8]
    with np.errstate(invalid="ignore", divide="ignore"):
        p = a / a.sum(axis=1, keepdims=True)
    return np.vstack([p, np.eye(8)[7]])


def _p_state(rows):
    """The same with the withdrawals a ninth, absorbing state: each grade's row over the whole cohort."""
    a = np.asarray(rows, dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        p = a / a.sum(axis=1, keepdims=True)
    return np.vstack([p, np.eye(9)[7:]])


# seven years with every grade rated except AAA in 2015; BB's tab 2 count is the year's index, AAA's varies
BASE = [[45, 3, 0, 0, 0, 0, 0, 0, 2],
        [2, 50, 4, 0, 0, 0, 0, 0, 4],
        [0, 3, 60, 4, 0, 0, 0, 0, 3],
        [0, 0, 4, 70, 4, 0, 0, 0, 2],
        [0, 0, 0, 5, 80, 6, 2, 2, 5],
        [0, 0, 0, 0, 4, 40, 4, 2, 0],
        [0, 0, 0, 0, 0, 3, 12, 3, 2]]
AAA_DEFAULTED = [1, 0, 2, 0, 1, 0, 3]


def _seven_years():
    years = []
    for t, y in enumerate(range(2010, 2017)):
        rows = [list(r) for r in BASE]
        if y == 2015:
            rows[0] = [0] * 9
        d = [AAA_DEFAULTED[t], 0, 0, 0, t, 2, 3]
        years.append(_year("STPGB", y, rows, d, d))
    return years


def _same(got, want, rel=1e-12):
    """Nested lists equal: None where None is wanted, floats to ``rel``."""
    if want is None:
        assert got is None
    elif isinstance(want, (list, tuple, np.ndarray)):
        assert len(got) == len(want)
        for g, w in zip(got, want, strict=True):
            _same(g, w, rel)
    else:
        assert got == pytest.approx(want, rel=rel, abs=1e-15)


def _nan_none(a):
    return [None if not np.isfinite(x) else float(x) for x in np.asarray(a, dtype=float)]


@pytest.fixture(scope="module")
def sp():
    """The S&P-like variant's outputs (the tests rows are checked in test_test_rows)."""
    return a4.agency_outputs("STPGB", _sp_annual(), _sp_semesters())[0]


def test_the_fixture_is_what_the_hand_computations_assume():
    for c in _sp_annual():
        assert c.size.tolist() == SIZES[c.begin.year], c.label
    assert [c.label for c in _sp_semesters()] == ["2012H1", "2012H2"]


def test_pd_definitions_by_hand(sp):
    """CT-403: d2 = tab 2 / size, d3 = tab 3 / size, d4 = default column / (size - withdrawn), keep = default column /
    size; a grade with no rating is None in its cohort's row; a cohort without tab 2 has a row of None."""
    pd = sp["pd"]
    _same(pd["d2"], [[0, 0, 0, 0, 2 / 67, 3 / 54, 6 / 22],
                     [None, 0, 0, 0, 3 / 71, 4 / 55, 8 / 22],
                     [0, 0, 0, 1 / 108, 4 / 70, 5 / 57, 10 / 25],
                     [None] * 7])
    _same(pd["d3"], [[0, 0, 0, 0, 2 / 67, 4 / 54, 8 / 22],
                     [None, 0, 0, 0, 3 / 71, 4 / 55, 9 / 22],
                     [0, 0, 0, 1 / 108, 4 / 70, 6 / 57, 12 / 25],
                     [0, 0, 0, 0, 2 / 70, 4 / 56, 9 / 23]])
    # 2013's AAA ratings were all withdrawn: no d4 (nothing stayed to count) but keep is 0 of 3
    _same(pd["d4"], [[0, 0, 0, 0, 1 / 63, 2 / 51, 5 / 20],
                     [None, 0, 0, 0, 2 / 66, 3 / 51, 6 / 19],
                     [0, 0, 0, 1 / 102, 3 / 66, 4 / 52, 8 / 21],
                     [None, 0, 0, 0, 2 / 65, 3 / 52, 7 / 21]])
    _same(pd["keep"], [[0, 0, 0, 0, 1 / 67, 2 / 54, 5 / 22],
                       [None, 0, 0, 0, 2 / 71, 3 / 55, 6 / 22],
                       [0, 0, 0, 1 / 108, 3 / 70, 4 / 57, 8 / 25],
                       [0, 0, 0, 0, 2 / 70, 3 / 56, 7 / 23]])
    # removing withdrawals never lowers a cohort's default-column rate
    for row4, rowk in zip(pd["d4"], pd["keep"], strict=True):
        assert all(a >= b for a, b in zip(row4, rowk, strict=True) if a is not None and b is not None)


def test_long_run_average_against_the_pooled_rate(sp):
    """CT-403: the long-run average is the mean of the yearly rates over the cohorts with a defined rate (EBA
    paragraph 84), not the pooled rate; the counts, the intervals and the last five come from the same cohorts."""
    d2, d3, d4 = sp["lra"]["d2"], sp["lra"]["d3"], sp["lra"]["d4"]
    assert set(sp["lra"]) == {"d2", "d3", "d4"}
    # d2: 2013 has no tab 2, and 2011 no AAA rating
    assert d2["cohorts"] == [2, 3, 3, 3, 3, 3, 3]
    assert d2["defaults"] == [0, 0, 0, 1, 9, 12, 24] and d2["n"] == [91, 206, 294, 317, 208, 166, 69]
    _same(d2["rate"], [0, 0, 0, 1 / 108 / 3, (2 / 67 + 3 / 71 + 4 / 70) / 3, (3 / 54 + 4 / 55 + 5 / 57) / 3,
                       (6 / 22 + 8 / 22 + 10 / 25) / 3])
    _same(d2["pooled_rate"], [0, 0, 0, 1 / 317, 9 / 208, 12 / 166, 24 / 69])
    assert d2["rate"][4] != pytest.approx(d2["pooled_rate"][4], rel=1e-3)  # the two differ when the sizes differ
    _same(d2["last5"], d2["rate"])  # fewer than five cohorts: the last five are all of them
    # d3: every cohort; 2013's AAA, all withdrawn, still has ratings (0 events of 3)
    assert d3["cohorts"] == [3, 4, 4, 4, 4, 4, 4]
    assert d3["defaults"] == [0, 0, 0, 1, 11, 18, 38] and d3["n"] == [94, 273, 394, 423, 278, 222, 92]
    _same(d3["rate"][6], (8 / 22 + 9 / 22 + 12 / 25 + 9 / 23) / 4)
    # d4: n is the cohort less its withdrawals; AAA's rate is defined in 2010 and 2012 only
    assert d4["cohorts"] == [2, 4, 4, 4, 4, 4, 4]
    assert d4["defaults"] == [0, 0, 0, 1, 8, 12, 26] and d4["n"] == [88, 261, 374, 403, 260, 206, 81]
    _same(d4["pooled_rate"], [0, 0, 0, 1 / 403, 8 / 260, 12 / 206, 26 / 81])
    # the intervals are the engine's at 95% on the pooled counts
    for entry in (d2, d3, d4):
        d, n = np.array(entry["defaults"], float), np.array(entry["n"], float)
        for key, fn in (("wald", intervals.pd_wald), ("agresti_coull", intervals.pd_agresti_coull),
                        ("jeffreys", intervals.pd_jeffreys)):
            want = fn(d, n, level=0.95)
            _same(entry[key]["lower"], want["lower"])
            _same(entry[key]["upper"], want["upper"])
            assert all(lo <= r <= hi for lo, r, hi in zip(entry[key]["lower"], entry["pooled_rate"],
                                                          entry[key]["upper"], strict=True))
    assert d2["jeffreys"]["lower"][0] == 0.0 and d2["wald"]["upper"][0] == 0.0  # no default: Wald collapses


def test_last_five_reach_back_over_a_cohort_without_ratings():
    """CT-403: paragraph 86's comparison averages the last five cohorts where the grade has ratings: AAA has none in
    2015, so its last five are 2011 to 2014 and 2016."""
    out, _ = a4.agency_outputs("STPGB", _seven_years(), [])
    d2 = out["lra"]["d2"]
    assert d2["cohorts"][0] == 6 and d2["cohorts"][4] == 7
    assert d2["rate"][0] == pytest.approx(7 / 50 / 6) and d2["last5"][0] == pytest.approx((0 + 2 + 0 + 1 + 3) / 50 / 5)
    assert d2["rate"][4] == pytest.approx(3 / 100) and d2["last5"][4] == pytest.approx(4 / 100)
    assert d2["pooled_rate"][0] == pytest.approx(7 / 300)
    assert out["pd"]["d2"][5][0] is None and out["mobility"]["svd"][5] is None
    assert out["homogeneity"]["semesters"] is None and out["semesters_vs_year"] == []


def test_definition_gaps_by_hand(sp):
    """CT-403: each ratio to d2 pools both rates over the cohorts where both are defined for the grade, so a year
    with one page only enters neither sum (2013 has no tab 2: the gap is 2010 to 2012's); None where d2's pooled rate
    is zero."""
    gap = sp["definition_gap"]
    # d4 over 2010 to 2012: defaults 0, 0, 0, 1, 6, 9 and 19 of 88, 197, 279, 302, 195, 154 and 60 transitions
    _same(gap["d4_over_d2"], [None, None, None, (1 / 302) / (1 / 317), (6 / 195) / (9 / 208),
                              (9 / 154) / (12 / 166), (19 / 60) / (24 / 69)])
    # tab 3 counts 1, 9, 14 and 29 events where tab 2 counts 1, 9, 12 and 24 ratings, over the same cohorts
    _same(gap["d3_over_d2"], [None, None, None, 1.0, 1.0, 14 / 12, 29 / 24])
    without = a4.agency_outputs("STPGB", _sp_annual()[:3], [])[0]["definition_gap"]
    _same(gap["d4_over_d2"], without["d4_over_d2"])
    _same(gap["d3_over_d2"], without["d3_over_d2"])
    # a grade whose rate one definition lacks in a year leaves that year out of the grade's pair: every BB rating of
    # 2012 withdrawn (no d4 for BB that year) while tab 2 still counts its 4 defaults
    years = _sp_annual()[:3]
    rows, d, e = ANNUAL[2012]
    rows = [list(r) for r in rows]
    rows[4] = [0] * 8 + [70]
    years[2] = _year("STPGB", 2012, rows, d, e)
    out, _ = a4.agency_outputs("STPGB", years, [])
    assert out["pd"]["d4"][2][4] is None and out["pd"]["d2"][2][4] == pytest.approx(4 / 70)
    assert out["definition_gap"]["d4_over_d2"][4] == pytest.approx(((1 + 2) / (63 + 66)) / ((2 + 3) / (67 + 71)))
    assert out["definition_gap"]["d3_over_d2"][4] == pytest.approx(1.0)


def test_d2_over_tab_2s_own_cohort():
    """CT-403: d2 divides by tab 2's own cohort where it differs from tab 4's rows (S&P's tab 2 counts more ratings in
    some grades and years, design.md); a cohort without the reader's tab 2 cohort falls back to tab 4's rows."""
    years = _sp_annual()
    rows, d, e = ANNUAL[2012]
    tab2 = list(SIZES[2012])
    tab2[5] = 60  # tab 2 counts three more B ratings than tab 4's 57
    years[2] = _year("STPGB", 2012, rows, d, e, tab2=tab2)
    out, _ = a4.agency_outputs("STPGB", years, [])
    rec = out["cohorts"][2]
    assert rec["defaulted_cohort"] == tab2 and rec["tab2_gap"] == pytest.approx(3 / 57)
    assert out["cohorts"][0]["defaulted_cohort"] == SIZES[2010] and out["cohorts"][0]["tab2_gap"] == 0.0
    assert out["cohorts"][3]["defaulted_cohort"] is None and out["cohorts"][3]["tab2_gap"] is None
    assert out["pd"]["d2"][2][5] == pytest.approx(5 / 60) and out["pd"]["d3"][2][5] == pytest.approx(6 / 57)
    d2 = out["lra"]["d2"]
    assert d2["n"][5] == 54 + 55 + 60 and d2["pooled_rate"][5] == pytest.approx(12 / 169)
    assert d2["rate"][5] == pytest.approx((3 / 54 + 4 / 55 + 5 / 60) / 3)
    assert out["mobility"]["spec_default_rate"][2] == pytest.approx(19 / (70 + 60 + 25))
    bare = [dataclasses.replace(c, defaulted_cohort=None, tab2_gap=None) for c in _sp_annual()]
    a, b = a4.agency_outputs("STPGB", bare, [])[0], a4.agency_outputs("STPGB", _sp_annual(), [])[0]
    assert a["pd"] == b["pd"] and a["lra"] == b["lra"]


# three years with every grade rated, and the 2016 cohort followed over the window 2016 to 2018 (its own tab 4)
LIFE = {2016: BASE,
        2017: BASE[:4] + [[0, 0, 0, 5, 79, 6, 2, 3, 5], BASE[5], [0, 0, 0, 0, 0, 3, 11, 4, 2]],
        2018: BASE[:5] + [[0, 0, 0, 0, 4, 38, 4, 4, 0], BASE[6]]}
WINDOW = [[38, 6, 1, 0, 0, 0, 0, 0, 5],
          [3, 40, 8, 1, 0, 0, 0, 0, 8],
          [0, 5, 50, 8, 1, 0, 0, 0, 6],
          [0, 0, 8, 55, 8, 2, 0, 1, 6],
          [0, 0, 0, 10, 55, 12, 4, 6, 13],
          [0, 0, 0, 0, 8, 25, 6, 6, 5],
          [0, 0, 0, 0, 0, 3, 5, 6, 6]]


def test_lifetime_by_hand():
    """CT-415: a window's fixed cohort at its end (tab 4 as shares of the cohort; tab 2's cumulative rate over tab 2's
    cohort) against the window's annual matrices chained by hand, the pooled matrix to the window's years and the EM
    generator over them; a window whose years are not all annual cohorts has no chain."""
    annual = [_year("STPGB", y, rows, [0, 0, 0, 0, 1, 1, 2], [0, 0, 0, 0, 1, 1, 2]) for y, rows in LIFE.items()]
    windows = [_window("STPGB", 2016, 2018, WINDOW, [0, 0, 0, 1, 9, 9, 9], tab2=[50, 60, 70, 80, 100, 50, 22]),
               _window("STPGB", 2015, 2017, WINDOW)]
    out, _ = a4.agency_outputs("STPGB", annual, [], windows)
    assert [r["label"] for r in out["lifetime"]] == ["2015-2017", "2016-2018"]
    for r in out["lifetime"]:
        assert set(r) == {"label", "first", "last", "size", "observed", "projected"}
        assert set(r["observed"]) == {"default_end", "withdrawn_end", "cumulative_d2"}
        assert set(r["projected"]) == {"chain_state", "chain_state_withdrawn", "chain_exclude", "pooled_power", "em"}
    missing, life = out["lifetime"]
    assert (life["first"], life["last"], life["size"]) == (2016, 2018, [50, 60, 70, 80, 100, 50, 20])
    _same(life["observed"]["default_end"], [0, 0, 0, 1 / 80, 6 / 100, 6 / 50, 6 / 20])
    _same(life["observed"]["withdrawn_end"], [5 / 50, 8 / 60, 6 / 70, 6 / 80, 13 / 100, 5 / 50, 6 / 20])
    _same(life["observed"]["cumulative_d2"], [0, 0, 0, 1 / 80, 9 / 100, 9 / 50, 9 / 22])
    state = _p_state(LIFE[2016]) @ _p_state(LIFE[2017]) @ _p_state(LIFE[2018])
    exclude = _p(LIFE[2016]) @ _p(LIFE[2017]) @ _p(LIFE[2018])
    _same(life["projected"]["chain_state"], state[:7, 7])
    _same(life["projected"]["chain_state_withdrawn"], state[:7, 8])
    _same(life["projected"]["chain_exclude"], exclude[:7, 7])
    total = sum(np.asarray(LIFE[y], dtype=float)[:, :8] for y in LIFE)  # the pooled counts, by hand
    pooled = np.vstack([total / total.sum(axis=1, keepdims=True), np.eye(8)[7]])
    _same(out["pooled"]["matrix"], pooled)
    _same(life["projected"]["pooled_power"], np.linalg.matrix_power(pooled, 3)[:7, 7])
    _same(life["projected"]["em"], expm(3.0 * np.array(out["generators"]["em"]["generator"]))[:7, 7])
    # removing the withdrawals at every step can only raise the chained default probability
    chained = zip(life["projected"]["chain_exclude"], life["projected"]["chain_state"], strict=True)
    assert all(e >= s for e, s in chained)
    # 2015 is not an annual cohort: the window's own outcome stands, the chain does not
    assert missing["projected"]["chain_state"] == missing["projected"]["chain_exclude"] == [None] * 7
    assert missing["projected"]["chain_state_withdrawn"] == [None] * 7 and missing["observed"]["cumulative_d2"] is None
    assert missing["projected"]["pooled_power"] == life["projected"]["pooled_power"]
    json.dumps(out, allow_nan=False)
    with pytest.raises(ValueError, match="not a window of whole years"):
        a4.agency_outputs("STPGB", annual, [], [annual[0]])


def test_a_five_year_window_projects_as_the_generators_block():
    """CT-415: over five years, the pooled power and the EM projection are the generators block's pd_5y."""
    out, _ = a4.agency_outputs("STPGB", _seven_years(), [], [_window("STPGB", 2010, 2014, BASE)])
    (row,) = out["lifetime"]
    assert row["projected"]["pooled_power"] == out["generators"]["cohort_power"]["pd_5y"]
    assert row["projected"]["em"] == out["generators"]["em"]["pd_5y"]
    assert None not in row["projected"]["chain_state"]


def test_attribution_and_agency(sp):
    """CT-407: the attribution, the entity, the scope and the period of every cohort."""
    assert sp["kind"] == "agency" and sp["attribution"] == "Source: ESMA CEREP; tables transformed by Contraste"
    assert sp["agency"] == {"code": "STPGB", "name": cerep.AGENCIES["STPGB"],
                            "scope": "corporate, long-term, categories"}
    assert sp["grades"] == ["AAA", "AA", "A", "BBB", "BB", "B", "CCC-C"] and sp["states"] == sp["grades"] + ["D"]
    assert [(c["label"], c["begin"], c["end"]) for c in sp["cohorts"]] == [
        (str(y), f"{y}-01-01", f"{y}-12-31") for y in range(2010, 2014)]
    assert [(c["label"], c["begin"], c["end"]) for c in sp["semesters"]] == [
        ("2012H1", "2012-01-01", "2012-06-30"), ("2012H2", "2012-07-01", "2012-12-31")]
    first = sp["cohorts"][0]
    assert first["size"] == SIZES[2010] and first["withdrawn"] == [2, 3, 4, 5, 4, 3, 2]
    assert first["counts"][6] == [0, 0, 0, 0, 0, 3, 12, 5] and isinstance(first["counts"][6][6], int)
    assert sp["cohorts"][3]["defaulted"] is None and sp["cohorts"][3]["events"] == [0, 0, 0, 0, 2, 4, 9]


def test_outputs_keys_exactly_as_the_contract_lists(sp):
    assert set(sp) == TOP
    assert set(sp["agency"]) == {"code", "name", "scope"}
    assert all(set(c) == COHORT_KEYS for c in sp["cohorts"] + sp["semesters"])
    assert set(sp["pd"]) == {"d2", "d3", "d4", "keep"}
    for key in ("d2", "d3", "d4"):
        assert set(sp["lra"][key]) == LRA_ENTRY
        assert all(set(sp["lra"][key][i]) == {"lower", "upper"} for i in ("wald", "agresti_coull", "jeffreys"))
    assert set(sp["pooled"]) == {"matrix", "matrix_state", "counts", "withdrawn", "row_sizes", "cohorts"}
    assert set(sp["embedding"]) == EMBEDDING_KEYS and set(sp["embedding"]["theorem3"]) == {"a", "b", "c"}
    assert set(sp["generators"]) == {"diagonal", "weighted", "jlt", "em", "cohort_power"}
    for m in ("diagonal", "weighted", "jlt"):
        assert set(sp["generators"][m]) == GENERATOR_KEYS
    assert set(sp["generators"]["em"]) == GENERATOR_KEYS | {"iterations", "converged", "loglik"}
    assert set(sp["generators"]["cohort_power"]) == {"pd_5y"}
    assert set(sp["mobility"]) == {"labels", "svd", "trace", "spec_default_rate"}
    assert all(set(e) == {"label", "mwb_upper", "mwb_lower", "ztests_p"} for e in sp["ecb"])
    assert set(sp["homogeneity"]) == {"annual", "semesters", "reference"}
    for key in ("annual", "semesters"):
        assert set(sp["homogeneity"][key]) == {"statistic", "p_value", "dof", "periods"}
    assert all(set(r) == {"label", "statistic", "p_value", "dof", "impossible_moves"}
               for r in sp["homogeneity"]["reference"])
    assert all(set(r) == {"year", "l1", "pd_product", "pd_annual"} for r in sp["semesters_vs_year"])
    assert set(sp["definition_gap"]) == {"d4_over_d2", "d3_over_d2"}
    assert sp["lifetime"] == []  # no window passed (its rows' keys: test_lifetime_by_hand)
    # the shapes: n cohorts by seven grades, 8 x 8 and 9 x 9 matrices, 7 x 8 counts
    n = len(sp["cohorts"])
    assert all(len(sp["pd"][k]) == n and all(len(r) == 7 for r in sp["pd"][k]) for k in sp["pd"])
    assert np.shape(sp["pooled"]["matrix"]) == (8, 8) and np.shape(sp["pooled"]["matrix_state"]) == (9, 9)
    assert np.shape(sp["pooled"]["counts"]) == (7, 8) and sp["pooled"]["cohorts"] == n
    assert all(np.shape(sp["generators"][m]["generator"]) == (8, 8) for m in ("diagonal", "weighted", "jlt", "em"))
    assert len(sp["mobility"]["svd"]) == len(sp["ecb"]) == len(sp["homogeneity"]["reference"]) == n


def _walk(x):
    """Only dicts with str keys, lists, str, bool, int, float and None: plain Python types, no NumPy scalar."""
    if isinstance(x, dict):
        assert all(isinstance(k, str) for k in x)
        for v in x.values():
            _walk(v)
    elif isinstance(x, list):
        for v in x:
            _walk(v)
    else:
        assert x is None or type(x) in (str, bool, int, float), type(x)


def test_json_safe(sp):
    """Undefined values are None, never NaN or infinity (json refuses them with allow_nan=False)."""
    out, tests = a4.agency_outputs("STPGB", _sp_annual(), _sp_semesters())
    json.dumps(out, allow_nan=False)
    json.dumps(tests, allow_nan=False)
    _walk(out)
    _walk(tests)
    assert out["pd"]["d2"][3] == [None] * 7 and out["mobility"]["svd"][1] is None  # the undefined cells exist


def test_pooled_matrix_embedding_and_generators_are_the_engines(sp):
    """CT-404: every number is riskvalidation's, called directly here on the same counts."""
    years = _sp_annual()
    tables = [np.vstack([c.counts, np.zeros(8)]) for c in years]
    withdrawn = [np.append(c.withdrawn, 0.0) for c in years]
    ex = estimators.pooled_cohort(tables, withdrawn, treatment="exclude")
    st = estimators.pooled_cohort(tables, withdrawn, treatment="state")
    p = ex["matrix"]
    np.testing.assert_array_equal(np.array(sp["pooled"]["matrix"]), p)
    np.testing.assert_array_equal(np.array(sp["pooled"]["matrix_state"]), st["matrix"])
    assert sp["pooled"]["counts"] == ex["counts"][:7].astype(int).tolist()
    assert sp["pooled"]["withdrawn"] == [6, 12, 20, 20, 18, 16, 11]
    assert sp["pooled"]["row_sizes"] == [88, 261, 374, 403, 260, 206, 81]
    # by hand: CCC-C pooled over the four years, withdrawals removed
    _same(sp["pooled"]["matrix"][6], [0, 0, 0, 0, 1 / 81, 12 / 81, 42 / 81, 26 / 81])
    assert sp["pooled"]["matrix_state"][6][8] == pytest.approx(11 / 92)
    diag = embedding.embedding_diagnostics(p)
    e = sp["embedding"]
    assert e["S"] == diag["S"] and e["det"] == diag["det"] and e["prod_diagonal"] == diag["prod_diagonal"]
    assert e["series_converges"] is True and e["theorem3"]["c"] == [list(x) for x in diag["theorem3_c"]]
    assert e["exact_generator_excluded"] == diag["exact_generator_excluded"]
    assert e["stochastically_monotone"] == diag["stochastically_monotone"]
    assert len(e["monotonicity_violations"]) == len(diag["monotonicity_violations"])
    for method in ("diagonal", "weighted", "jlt"):
        g = sp["generators"][method]
        want = embedding.generator(p, method=method)
        q = np.array(g["generator"])
        np.testing.assert_array_equal(q, want["generator"])
        assert g["valid"] is True and g["l1"] == want["l1_distance"] == embedding.l1_distance(p, q)
        _same(g["pd_1y"], expm(q)[:7, 7])
        _same(g["pd_5y"], expm(5.0 * q)[:7, 7])
    fit = em_generator([{"counts": t, "dt": 1.0} for t in tables])
    em = sp["generators"]["em"]
    np.testing.assert_array_equal(np.array(em["generator"]), fit["generator"])
    assert em["l1"] == embedding.l1_distance(p, fit["generator"]) and em["valid"] is True
    assert em["iterations"] == fit["iterations"] and em["converged"] is True and em["loglik"] == fit["loglik"][-1]
    _same(em["pd_1y"], expm(fit["generator"])[:7, 7])
    _same(sp["generators"]["cohort_power"]["pd_5y"], np.linalg.matrix_power(p, 5)[:7, 7])
    # the repairs land close to the pooled matrix; JLT's one-move approximation is further away
    assert sp["generators"]["weighted"]["l1"] < sp["generators"]["jlt"]["l1"]


def test_mobility_ecb_and_markov_tests_are_the_engines(sp):
    """CT-404: mobility of each cohort's own matrix (None where a grade has no rating left), the ECB statistics on the
    performing block, time homogeneity across years and semesters, each year against the pooled matrix, and the
    semester product against the year, by hand."""
    years, halves = _sp_annual(), _sp_semesters()
    mob = sp["mobility"]
    assert mob["labels"] == ["2010", "2011", "2012", "2013"]
    assert mob["svd"][1] is None and mob["svd"][3] is None and mob["trace"][1] is None
    for t in (0, 2):
        m = _p(ANNUAL[2010 + t][0])
        assert mob["svd"][t] == pytest.approx(mobility.svd_mobility(m), rel=1e-12)
        assert mob["trace"][t] == pytest.approx((8 - np.trace(m)) / 7, rel=1e-12)
    # the speculative grades' d2 (the agency publishes tab 2), None in 2013 where tab 2 is missing
    _same(mob["spec_default_rate"], [11 / 143, 15 / 148, 19 / 152, None])
    for row, c in zip(sp["ecb"], years, strict=True):
        mwb = rating_system.rating_mwb(c.counts[:, :7])
        z = rating_system.rating_migration_ztests(c.counts[:, :7])
        assert row["label"] == c.label and row["mwb_upper"] == mwb.extras["mwb_upper"]
        assert row["mwb_lower"] == mwb.extras["mwb_lower"] and row["ztests_p"] == z.p_value
    sq = [np.vstack([c.counts, np.zeros(8)]) for c in years]
    th = markov.rating_time_homogeneity(sq)
    h = sp["homogeneity"]
    assert h["annual"] == {"statistic": th.statistic, "p_value": th.p_value, "dof": th.extras["dof"], "periods": 4}
    th2 = markov.rating_time_homogeneity([np.vstack([c.counts, np.zeros(8)]) for c in halves])
    assert h["semesters"]["statistic"] == th2.statistic and h["semesters"]["periods"] == 2
    p = np.array(sp["pooled"]["matrix"])
    for row, s in zip(h["reference"], sq, strict=True):
        r = markov.rating_matrix_reference(s, p)
        assert (row["statistic"], row["p_value"], row["dof"]) == (r.statistic, r.p_value, r.extras["dof"])
        assert row["impossible_moves"] == []  # a cohort's moves are in the pooled counts
    # P_H1 P_H2 against P_2012, by hand
    product, year = _p(H1_2012) @ _p(H2_2012), _p(ANNUAL[2012][0])
    (svy,) = sp["semesters_vs_year"]
    assert svy["year"] == 2012 and svy["l1"] == pytest.approx(np.abs(year - product).sum(), rel=1e-12)
    _same(svy["pd_product"], product[:7, 7])
    _same(svy["pd_annual"], [0, 0, 0, 1 / 102, 3 / 66, 4 / 52, 8 / 21])


def test_test_rows(sp):
    """Every registered test the variant runs, as TestResult.to_dict() with the agency and the segment."""
    out, tests = a4.agency_outputs("STPGB", _sp_annual(), _sp_semesters())
    labels = ["2010", "2011", "2012", "2013"]
    assert all(r["model_id"] == "STPGB" for r in tests)
    got = [(r["test_id"], r["segment"]) for r in tests]
    assert sorted(got) == sorted([(t, y) for y in labels for t in ("rating.mwb", "rating.migration_ztests",
                                                                   "rating.matrix_reference")]
                                 + [("rating.time_homogeneity", "annual"), ("rating.time_homogeneity", "semesters")])
    years = _sp_annual()
    th = markov.rating_time_homogeneity([np.vstack([c.counts, np.zeros(8)]) for c in years], model_id="STPGB",
                                        segment="annual")
    assert next(r for r in tests if r["segment"] == "annual") == th.to_dict()
    ref = markov.rating_matrix_reference(np.vstack([years[1].counts, np.zeros(8)]),
                                         np.array(out["pooled"]["matrix"]), model_id="STPGB", segment="2011")
    assert next(r for r in tests if r["test_id"] == "rating.matrix_reference" and r["segment"] == "2011") == \
        ref.to_dict()


def test_moodys_has_no_default_column():
    """CT-403: without a default category on the transition page, d4, keep and every PD read off a migration matrix
    are None; the tab 2 and tab 3 PDs and the migrations themselves are reported."""
    annual = [_year("MDYGB", y, _moodys_rows(rows), d, e, has_default=False)
              for y, (rows, d, e) in ANNUAL.items() if y < 2013]
    halves = [_half("MDYGB", 2012, 1, _moodys_rows(H1_2012), False),
              _half("MDYGB", 2012, 2, _moodys_rows(H2_2012), False)]
    window = _window("MDYGB", 2010, 2012, _moodys_rows(ANNUAL[2010][0]), ANNUAL[2010][1], has_default=False)
    out, tests = a4.agency_outputs("MDYGB", annual, halves, [window])
    (life,) = out["lifetime"]
    assert life["observed"]["default_end"] == [None] * 7
    assert all(life["projected"][k] == [None] * 7 for k in ("chain_state", "chain_exclude", "pooled_power", "em"))
    # BB: 4 withdrawn and 1 default that Moody's page does not show (here counted withdrawn) of 67
    assert life["observed"]["withdrawn_end"][4] == pytest.approx(5 / 67)
    assert life["observed"]["cumulative_d2"][4] == pytest.approx(2 / 67)
    # 2011 has no AAA rating: the chained rows that reach AAA in 2010 (AAA and AA) are undefined, the others are not
    withdrawn = life["projected"]["chain_state_withdrawn"]
    assert withdrawn[:2] == [None, None] and all(0.0 < x < 1.0 for x in withdrawn[2:])
    assert out["pd"]["d4"] is None and out["pd"]["keep"] is None and out["lra"]["d4"] is None
    assert out["pd"]["d2"][0][4] == pytest.approx(2 / 67) and out["lra"]["d3"] is not None
    assert out["definition_gap"]["d4_over_d2"] is None
    # 2010 to 2012 pooled: tab 3 counts 1, 9, 14 and 29 events where tab 2 counts 1, 9, 12 and 24 ratings
    _same(out["definition_gap"]["d3_over_d2"], [None, None, None, 1.0, 1.0, 14 / 12, 29 / 24])
    for m in ("diagonal", "weighted", "jlt", "em"):
        g = out["generators"][m]
        assert g["pd_1y"] == [None] * 7 and g["pd_5y"] == [None] * 7 and g["l1"] is not None
    assert out["generators"]["cohort_power"]["pd_5y"] == [None] * 7
    (svy,) = out["semesters_vs_year"]
    assert svy["pd_product"] == svy["pd_annual"] == [None] * 7 and svy["l1"] is not None
    assert all(row[7] == 0.0 for row in out["pooled"]["matrix"][:7])
    json.dumps(out, allow_nan=False)
    assert len(tests) == 3 * 3 + 2


def test_an_agency_without_tab_2():
    """A definition no cohort publishes is null throughout; the speculative default rate falls back to d3."""
    out, _ = a4.agency_outputs("FITGB", _sp_annual("FITGB", tab2=False), _sp_semesters("FITGB"))
    assert out["pd"]["d2"] is None and out["lra"]["d2"] is None
    assert out["definition_gap"] == {"d4_over_d2": None, "d3_over_d2": None}
    _same(out["mobility"]["spec_default_rate"], [(2 + 4 + 8) / 143, (3 + 4 + 9) / 148, (4 + 6 + 12) / 152,
                                                 (2 + 4 + 9) / 149])
    assert out["pd"]["d4"] is not None and out["lra"]["d4"]["n"] == [88, 261, 374, 403, 260, 206, 81]


def test_a_semester_grade_without_ratings_leaves_only_its_paths_undefined():
    """A grade with no rating left at the start of the second semester: the product's rows that reach it are None,
    the others are P_H1 P_H2 by hand."""
    h2 = [list(r) for r in H2_2012]
    h2[0] = [0, 0, 0, 0, 0, 0, 0, 0, 45]  # every AAA rating withdrawn by the end of the second semester
    out, _ = a4.agency_outputs("STPGB", _sp_annual(), [_half("STPGB", 2012, 1, H1_2012), _half("STPGB", 2012, 2, h2)])
    (svy,) = out["semesters_vs_year"]
    p1, p2 = _p(H1_2012), _p(h2)
    # AAA and AA reach AAA in the first semester; from A down nobody does, and their rows are defined
    assert p1[0, 0] > 0 and p1[1, 0] > 0 and not np.any(p1[2:7, 0])
    want = [None, None] + [float(p1[i, 1:] @ p2[1:, 7]) for i in range(2, 7)]
    _same(svy["pd_product"], want)
    assert svy["l1"] is None


def _b_and_ccc(ccc_row):
    """One year whose B and CCC-C ratings trade places more than CCC-C's stay: the pooled matrix has an eigenvalue
    left of zero, so Theorem 1's S >= 1 and the log series diverges."""
    rows = [list(r) for r in BASE]
    rows[5] = [0, 0, 0, 0, 4, 30, 14, 2, 0]
    rows[6] = ccc_row
    return [_year("STPGB", 2010, rows)]


def test_a_diverging_log_series_leaves_only_the_series_generators_undefined():
    """CT-404: with S >= 1 there is no series generator to repair (Israel et al., Theorem 1), so the diagonal and
    weighted generators are None (the engine refuses them); JLT (every p_ii > 0), EM and the cohort power stand."""
    out, _ = a4.agency_outputs("STPGB", _b_and_ccc([0, 0, 0, 0, 0, 12, 1, 6, 2]), [])
    emb, gen = out["embedding"], out["generators"]
    p = np.array(out["pooled"]["matrix"])
    assert emb["S"] == pytest.approx(embedding.eigen_condition(p)) and emb["S"] >= 1.0
    assert emb["series_converges"] is False
    with pytest.raises(ValueError, match="does not converge"):
        embedding.generator(p, method="diagonal")
    assert gen["diagonal"] is None and gen["weighted"] is None
    assert np.all(np.diag(p)[:7] > 0) and set(gen["jlt"]) == GENERATOR_KEYS
    np.testing.assert_array_equal(np.array(gen["jlt"]["generator"]), embedding.generator(p, method="jlt")["generator"])
    assert None not in gen["jlt"]["pd_1y"] and None not in gen["em"]["pd_5y"]
    assert None not in gen["cohort_power"]["pd_5y"]
    json.dumps(out, allow_nan=False)
    _walk(out)


def test_a_grade_that_never_stays_has_no_jlt_generator():
    """CT-404: JLT's equation (3) takes log(p_ii); with no CCC-C rating staying in CCC-C it is None (the engine
    refuses it), as are the series generators here (S >= 1), and EM still gives every PD."""
    out, _ = a4.agency_outputs("STPGB", _b_and_ccc([0, 0, 0, 0, 0, 12, 0, 6, 2]), [])
    p = np.array(out["pooled"]["matrix"])
    assert p[6, 6] == 0.0
    with pytest.raises(ValueError, match="p_ii = 0"):
        embedding.generator(p, method="jlt")
    assert all(out["generators"][m] is None for m in ("diagonal", "weighted", "jlt"))
    em = out["generators"]["em"]
    assert set(em) == GENERATOR_KEYS | {"iterations", "converged", "loglik"} and None not in em["pd_1y"]
    json.dumps(out, allow_nan=False)


def test_an_agency_whose_transition_pages_differ_in_the_default_category():
    """CT-403, CT-404, CT-415: when one year's transition page has no default category, the pooled matrix's default
    column holds the other years' defaults only, so no PD read off a pooled, chained or generated matrix is reported;
    the years with the category keep their d4 and keep, and the window keeps its own observed outcome."""
    rows, d, e = ANNUAL[2012]
    years = _sp_annual()[:2] + [_year("STPGB", 2012, _moodys_rows(rows), d, e, has_default=False)]
    out, _ = a4.agency_outputs("STPGB", years, _sp_semesters(), [_window("STPGB", 2010, 2012, WINDOW)])
    gen = out["generators"]
    for m in ("diagonal", "weighted", "jlt", "em"):
        assert gen[m]["pd_1y"] == gen[m]["pd_5y"] == [None] * 7 and gen[m]["l1"] is not None
    assert gen["cohort_power"]["pd_5y"] == [None] * 7
    assert out["pd"]["d4"][2] == out["pd"]["keep"][2] == [None] * 7 and None not in out["pd"]["d4"][0]
    assert out["lra"]["d4"]["cohorts"] == [1, 2, 2, 2, 2, 2, 2]
    (svy,) = out["semesters_vs_year"]
    assert svy["pd_product"] == svy["pd_annual"] == [None] * 7  # the semesters have the category, the year not
    (life,) = out["lifetime"]
    assert None not in life["observed"]["default_end"]
    assert all(life["projected"][k] == [None] * 7 for k in ("chain_state", "chain_exclude", "pooled_power", "em"))
    json.dumps(out, allow_nan=False)


def test_tab_3_events_beyond_the_cohort():
    """Tab 3 counts every default event, over a cohort of its own: more events than tab 4's rows give a d3 above 1,
    reported, with no binomial interval for the grade; events in a grade with no rating on tab 4 have no d3 and enter
    no pooled count."""
    rows, d, _ = ANNUAL[2010]
    out, _ = a4.agency_outputs("STPGB", [_year("STPGB", 2010, rows, d, [0, 0, 0, 0, 2, 4, 30])], [])
    d3 = out["lra"]["d3"]
    assert out["pd"]["d3"][0][6] == pytest.approx(30 / 22) and d3["pooled_rate"][6] == pytest.approx(30 / 22)
    for name in ("wald", "agresti_coull", "jeffreys"):
        assert d3[name]["lower"][6] is None and d3[name]["upper"][6] is None
        assert d3[name]["lower"][4] is not None and d3[name]["upper"][4] is not None
    years = _sp_annual()
    rows, d, _ = ANNUAL[2011]
    years[1] = _year("STPGB", 2011, rows, d, [1, 0, 0, 0, 3, 4, 9])  # an AAA event; 2011 has no AAA rating
    out, _ = a4.agency_outputs("STPGB", years, [])
    assert out["cohorts"][1]["events"][0] == 1 and out["pd"]["d3"][1][0] is None
    d3 = out["lra"]["d3"]
    assert (d3["defaults"][0], d3["n"][0], d3["pooled_rate"][0], d3["cohorts"][0]) == (0, 94, 0.0, 3)


def test_a_single_cohort_and_the_refusals():
    """One annual cohort: time homogeneity is undefined (no grade seen in two periods), never NaN. The refusals: an
    unknown agency, another agency's cohort, a half year in the annual list, an inconsistent size, no annual cohort, a
    grade without a rating over every cohort, two cohorts of one period, a page of the wrong shape, a count that is
    not a whole non-negative number, defaults on a page without a default category, an undefined tab 2 gap, more
    defaulted ratings on tab 2 than its cohort holds, and a cohort without ratings."""
    one = [_sp_annual()[0]]
    out, tests = a4.agency_outputs("STPGB", one, [])
    assert out["homogeneity"]["annual"] == {"statistic": None, "p_value": None, "dof": 0, "periods": 1}
    row = next(r for r in tests if r["test_id"] == "rating.time_homogeneity")
    assert row["p_value"] is None and row["light"] == "not_evaluated"
    assert out["homogeneity"]["reference"][0]["statistic"] == pytest.approx(0.0, abs=1e-12)  # a year against itself
    with pytest.raises(ValueError, match="unknown agency"):
        a4.agency_outputs("XXXGB", one, [])
    with pytest.raises(ValueError, match="a cohort of MDYGB"):
        a4.agency_outputs("STPGB", one + [_year("MDYGB", 2011, ANNUAL[2011][0])], [])
    with pytest.raises(ValueError, match="not a calendar year"):
        a4.agency_outputs("STPGB", one + [_half("STPGB", 2012, 1, H1_2012)], [])
    with pytest.raises(ValueError, match="not a half year"):
        a4.agency_outputs("STPGB", one, one)
    bad = _sp_annual()[0]
    bad = cerep.Cohort(bad.cra, bad.begin, bad.end, bad.counts, bad.withdrawn, bad.defaulted, bad.events,
                       bad.size + 1, True)
    with pytest.raises(ValueError, match="transitions plus its withdrawals"):
        a4.agency_outputs("STPGB", [bad], [])
    with pytest.raises(ValueError, match="at least one annual cohort"):
        a4.agency_outputs("STPGB", [], _sp_semesters())
    with pytest.raises(ValueError, match="AAA"):
        a4.agency_outputs("STPGB", [_sp_annual()[1]], [])  # 2011 alone: no AAA rating at all
    with pytest.raises(ValueError, match="two cohorts of one period"):
        a4.agency_outputs("STPGB", one + one, [])
    first, empty = one[0], [[0] * 9 for _ in range(7)]
    wide = np.hstack([first.counts, first.counts[:, :1]])
    for bad, match in (
            (dataclasses.replace(first, withdrawn=first.withdrawn[:6]), r"withdrawn must be \(7,\)"),
            (dataclasses.replace(first, counts=wide), r"counts must be \(7, 8\)"),
            (dataclasses.replace(first, events=first.events + 0.5), r"events must be \(7,\) whole"),
            (dataclasses.replace(first, defaulted=np.full(7, np.nan)), "defaulted must be"),
            (dataclasses.replace(first, events=-first.events - 1), "events must be"),
            (dataclasses.replace(first, has_default_column=False), "without a default category"),
            (dataclasses.replace(first, tab2_gap=float("nan")), "tab2_gap must be finite"),
            (dataclasses.replace(first, defaulted=first.defaulted_cohort + 1), "more defaulted ratings than"),
            (_year("STPGB", 2010, empty), "a cohort without ratings")):
        with pytest.raises(ValueError, match=match):
            a4.agency_outputs("STPGB", [bad], [])
    with pytest.raises(ValueError, match="a cohort without ratings"):
        a4.agency_outputs("STPGB", one, [], [_window("STPGB", 2010, 2012, empty)])


def test_deterministic_whatever_the_order():
    """Two runs, the cohorts given in opposite orders, give the same outputs and test rows to the byte; windows that
    share a first year are ordered by their last."""
    a = a4.agency_outputs("STPGB", _sp_annual(), _sp_semesters())
    b = a4.agency_outputs("STPGB", list(reversed(_sp_annual())), list(reversed(_sp_semesters())))
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    years = [_year("STPGB", y, rows, [0, 0, 0, 0, 1, 1, 2]) for y, rows in LIFE.items()]
    spans = [_window("STPGB", 2016, 2018, WINDOW), _window("STPGB", 2015, 2017, WINDOW),
             _window("STPGB", 2016, 2017, WINDOW)]
    c = a4.agency_outputs("STPGB", years, [], spans)
    d = a4.agency_outputs("STPGB", years[::-1], [], spans[::-1])
    assert json.dumps(c, sort_keys=True) == json.dumps(d, sort_keys=True)
    assert [r["label"] for r in c[0]["lifetime"]] == ["2015-2017", "2016-2017", "2016-2018"]
