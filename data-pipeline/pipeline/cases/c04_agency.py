"""C04, rating transitions and TTC PD by grade (U4): the agency variants (CT-403, CT-404, CT-407, CT-415).

The design is docs/design/features/c04-transitions/design.md and contract.md section 1 fixes the outputs. Input: one
agency's cohorts as ``pipeline.io.cerep.read_agency`` returns them, the EU entity's corporate long-term ratings by
category on the common scale of seven performing grades and default (ESMA, CEREP help file, ESMA65-8-10634). Every
computation is ``riskvalidation`` 0.4.0; this module arranges the counts, calls the engine and makes the results
JSON-safe (no NaN or infinity: None where a value is undefined).

- One-year PD by grade and cohort, under the pages' own definitions (help file, sections 4.2 to 4.4): ``d2``, tab 2's
  "distinct number of ratings included in the 'number of defaults'" over "the total number of ratings belonging in the
  initial cohort", taken over tab 2's own cohort (``Cohort.defaulted_cohort``: S&P's tab 2 counts more ratings than
  tab 4 in some grades and years, design.md); ``d3``, tab 3's default events ("all default events will be counted")
  over the transition page's cohort, tab 4's rows; ``d4``, the transition page's default column over the cohort less
  its withdrawals, the industry treatment that "treats transitions to NR as non-informative" (Schuermann and Hanson
  2004, FRBNY Staff Report 190, footnote 4); ``keep``, the same column over the whole cohort, as EBA/GL/2017/16
  paragraph 76 keeps closed obligations in the denominator. "For the purposes of reporting into the CEREP, no
  deterministic definition of a default event has been set up": each PD names its page. Moody's transition page has
  no default category, so its d4, keep and every PD read off a migration matrix are None.
- What d3 measures (2026-10-07, the cached answers and two percentage-mode tab 3 requests): in every annual cohort read
  (S&P's and Moody's 26, Fitch's 24) tab 3's events equal tab 2's distinct defaulted ratings grade by grade, so d3
  differs from d2 only in its cohort. Tab 3's own printed rates divide by a cohort of its own, at or above tab 4's
  rows, below tab 2's and nearer tab 4's in every label measured (S&P's B in 2018: 1,798 to 1,818 ratings against
  1,752 and 2,021; BB in 2020: 1,124 to 1,134 against 1,129 and 1,340), which the number-mode answers do not carry:
  tab 4's rows are the nearer of the two cohorts the reader holds.
- The long-run average default rate, EBA/GL/2017/16 paragraph 84: "the observed average of the one-year default
  rates", here over the cohorts where the grade has ratings; paragraph 86's comparison, the average of the most recent
  five such cohorts; the Wald (2.2), Agresti-Coull (3.2, 3.3) and Jeffreys intervals at 95% on the pooled counts
  (Schuermann and Hanson 2004; Brown, Cai and DasGupta 2001, doi:10.1214/ss/1009213286), ``transitions.intervals``.
  The gap between two definitions is the ratio of their rates pooled over the cohorts where both are defined.
- The pooled one-year matrix, Anderson and Goodman (1957, doi:10.1214/aoms/1177707039) equation (2.8), withdrawals
  removed or kept as an absorbing state (``transitions.estimators``); its embedding, Israel, Rosenthal and Wei (2001,
  doi:10.1111/1467-9965.00114): Theorem 1's S, Theorem 3's conditions, Lemma 1's monotonicity, the diagonal (2),
  weighted (2') and JLT (3) generators with the L1 distance of exp(Q) to the pooled matrix (``transitions.embedding``);
  the maximum likelihood generator of the annual counts by EM (Bladt and Sorensen 2005, as presented by Smith and dos
  Reis 2018, doi:10.1080/14697688.2017.1383627; ``transitions.em``). The PD by grade at horizon t is the default
  column of exp(tQ), as the engine's rating-path truth reads it.
- Mobility by cohort: Jafry and Schuermann's M_SVD and the trace index (``transitions.mobility``), beside the
  speculative-grade default rate; the ECB's matrix weighted bandwidth and migration z-tests on the performing grades
  (ECB 2019, section 2.5.5; ``rating.mwb``, ``rating.migration_ztests``).
- Anderson and Goodman's tests on the count matrices CEREP publishes: time homogeneity across the annual and across
  the semester cohorts (3.8), each annual cohort against the pooled matrix (the likelihood-ratio form of 3.1)
  (``rating.time_homogeneity``, ``rating.matrix_reference``); and the product of a year's two semester matrices
  against the year's matrix, equal for a Markov chain by the Chapman-Kolmogorov equation up to sampling error (the
  second semester's cohort also holds the ratings issued in the first).
- The lifetime check (CT-415): a multi-year window's fixed cohort, followed to the window's end on its own tab 4 and
  tab 2, beside the projections one-year matrices give for it: the window's annual matrices chained (withdrawals an
  absorbing state, or removed), the pooled matrix to the window's number of years, and the EM generator over them.
  The chain's default column and the window's tab 4 count different things (``_lifetime``): their gap is not by
  itself a failure of the Markov chain.
"""
from __future__ import annotations

import dataclasses
import math
from collections.abc import Sequence
from typing import Any

import numpy as np
from scipy.linalg import expm

from riskvalidation.transitions import embedding, estimators, intervals, mobility
from riskvalidation.transitions.em import em_generator
from riskvalidation.validation import rating_system
from riskvalidation.validation import transitions as markov

from ..io.cerep import AGENCIES, DEFAULT, GRADES as SCALE_GRADES, Cohort

GRADES: list[str] = list(SCALE_GRADES)
STATES: list[str] = [*GRADES, DEFAULT]
K = len(GRADES)              # seven performing grades
D = K                        # default, the last state (the withdrawals, where a state, come after it)
SCOPE = "corporate, long-term, categories"
ATTRIBUTION = "Source: ESMA CEREP; tables transformed by Contraste"
LEVEL = 0.95                 # the intervals' confidence level
RECENT = 5                   # EBA/GL/2017/16 paragraph 86: "the most recent 5 years"
SPECULATIVE = (4, 5, 6)      # BB, B and CCC-C
HORIZON = 5.0                # pd_5y: years
DEFINITION_KEYS = ("d2", "d3", "d4", "keep")
LRA_KEYS = ("d2", "d3", "d4")


# ---------------------------------------------------------------------------------------------------------------------
# JSON-safe values


def _num(x: Any) -> float | None:
    """A finite float, or None (JSON holds no NaN or infinity)."""
    if x is None:
        return None
    v = float(x)
    return v if math.isfinite(v) else None


def _floats(a: Any) -> Any:
    """An array as nested lists of finite floats, None where a value is undefined."""
    arr = np.asarray(a, dtype=float)
    out = arr.astype(object)
    out[~np.isfinite(arr)] = None
    return out.tolist()


def _counts(a: Any) -> Any:
    """Counts as nested lists of ints: CEREP counts ratings, and ``_checked`` refuses a count that is not whole."""
    return np.rint(np.asarray(a, dtype=float)).astype(np.int64).tolist()


def _pairs(cells: Sequence[Sequence[int]]) -> list[list[int]]:
    return [[int(i), int(j)] for i, j in cells]


# ---------------------------------------------------------------------------------------------------------------------
# the cohorts

#: the periods each kind of cohort covers: (begin month, begin day, end month, end day), within one year except windows
PERIODS = {"annual": {(1, 1, 12, 31)}, "semester": {(1, 1, 6, 30), (7, 1, 12, 31)}, "window": {(1, 1, 12, 31)}}


def _checked(code: str, cohorts: Sequence[Cohort], kind: str) -> list[Cohort]:
    """The cohorts oldest first (by first day, then last: two windows may share a first year), each the agency's and
    of its kind (a calendar year, a half year, or a window of whole years), with the reader's shapes, whole counts, its
    identity size = counts + withdrawals, ratings in it (``read_agency`` returns only periods with data), and no more
    defaulted ratings on tab 2 than tab 2's cohort holds; the arrays as float arrays. Tab 3 may count more events than
    the cohort holds ratings: it counts every default event, over a cohort of its own."""
    out = []
    for c in sorted(cohorts, key=lambda x: (x.begin, x.end)):
        if c.cra != code:
            raise ValueError(f"{code}: a cohort of {c.cra} ({c.begin} to {c.end})")
        years = c.end.year > c.begin.year
        if years != (kind == "window") or (c.begin.month, c.begin.day, c.end.month, c.end.day) not in PERIODS[kind]:
            what = {"annual": "a calendar year", "semester": "a half year", "window": "a window of whole years"}[kind]
            raise ValueError(f"{code}: {c.begin} to {c.end} is not {what}")
        arrays: dict[str, np.ndarray | None] = {"counts": np.asarray(c.counts, dtype=float),
                                                "withdrawn": np.asarray(c.withdrawn, dtype=float),
                                                "size": np.asarray(c.size, dtype=float)}
        for name in ("defaulted", "events", "defaulted_cohort"):
            v = getattr(c, name)
            arrays[name] = None if v is None else np.asarray(v, dtype=float)
        for name, v in arrays.items():
            shape = (K, K + 1) if name == "counts" else (K,)
            if v is not None and (v.shape != shape or not np.all(np.isfinite(v)) or np.any(v < 0)
                                  or np.any(v != np.round(v))):
                raise ValueError(f"{code} {c.label}: {name} must be {shape} whole non-negative counts")
        if not np.allclose(arrays["size"], arrays["counts"].sum(axis=1) + arrays["withdrawn"]):
            raise ValueError(f"{code} {c.label}: the cohort size is not its transitions plus its withdrawals")
        if not arrays["size"].sum() > 0:
            raise ValueError(f"{code} {c.label}: a cohort without ratings")
        if not c.has_default_column and np.any(arrays["counts"][:, D] > 0):
            raise ValueError(f"{code} {c.label}: defaults counted on a page without a default category")
        tab2 = arrays["defaulted_cohort"] if arrays["defaulted_cohort"] is not None else arrays["size"]
        if arrays["defaulted"] is not None and np.any(arrays["defaulted"] > tab2):
            raise ValueError(f"{code} {c.label}: tab 2 counts more defaulted ratings than its cohort holds")
        gap = None if c.tab2_gap is None else float(c.tab2_gap)
        if gap is not None and not math.isfinite(gap):
            raise ValueError(f"{code} {c.label}: tab2_gap must be finite")
        out.append(dataclasses.replace(c, tab2_gap=gap, **arrays))
    labels = [c.label for c in out]
    if len(set(labels)) != len(labels):
        raise ValueError(f"{code}: two cohorts of one period in {labels}")
    return out


def _tab2_cohort(c: Cohort) -> np.ndarray:
    """The cohort tab 2's rates are taken over: the reader's ``defaulted_cohort``, else tab 4's rows (the reader's own
    value wherever tab 4's rows reproduce tab 2's printed rates)."""
    return c.defaulted_cohort if c.defaulted_cohort is not None else c.size


def _square(c: Cohort) -> np.ndarray:
    """The engine's square input: the 7 x 8 counts with an empty default row (the engine makes default absorbing)."""
    return np.vstack([c.counts, np.zeros(K + 1)])


def _withdrawn(c: Cohort) -> np.ndarray:
    return np.append(c.withdrawn, 0.0)


def _matrix(c: Cohort, treatment: str = "exclude") -> dict[str, Any]:
    """One period's cohort matrix (Anderson and Goodman 2.9), withdrawals removed or kept as a state."""
    return estimators.cohort(_square(c), _withdrawn(c), treatment=treatment)


def _record(c: Cohort) -> dict[str, Any]:
    return {"label": c.label, "begin": c.begin.isoformat(), "end": c.end.isoformat(), "size": _counts(c.size),
            "counts": _counts(c.counts), "withdrawn": _counts(c.withdrawn),
            "defaulted": None if c.defaulted is None else _counts(c.defaulted),
            "events": None if c.events is None else _counts(c.events),
            "defaulted_cohort": None if c.defaulted_cohort is None else _counts(c.defaulted_cohort),
            "tab2_gap": _num(c.tab2_gap)}


# ---------------------------------------------------------------------------------------------------------------------
# the PD definitions and the long-run average (CT-403)


@dataclasses.dataclass(frozen=True)
class _Rates:
    """One PD definition over the cohorts: the yearly rates (cohorts x grades, NaN where undefined) with their
    numerators and denominators (zero where the rate is undefined: the cohort lacks the definition's page, or the grade
    has no ratings under it)."""

    rates: np.ndarray
    defaults: np.ndarray
    n: np.ndarray

    def pooled(self, cells: np.ndarray | None = None) -> np.ndarray:
        """Defaults over n by grade, summed over the cohorts (``cells``: only the cohort-grade cells it marks); NaN
        where nothing is pooled."""
        d, n = self.defaults, self.n
        if cells is not None:
            d, n = np.where(cells, d, 0.0), np.where(cells, n, 0.0)
        d, n = d.sum(axis=0), n.sum(axis=0)
        return np.divide(d, n, out=np.full(K, np.nan), where=n > 0)


def _definition(cohorts: list[Cohort], key: str) -> _Rates | None:
    """The yearly rates of one definition, or None where no cohort has its page (tab 2 or 3 not fetched; no default
    category on the transition page)."""
    rates, num, den = np.full((len(cohorts), K), np.nan), np.zeros((len(cohorts), K)), np.zeros((len(cohorts), K))
    seen = False
    for t, c in enumerate(cohorts):
        if key in ("d2", "d3"):
            page = c.defaulted if key == "d2" else c.events
            if page is None:
                continue
            base = _tab2_cohort(c) if key == "d2" else c.size
            num[t], den[t] = page, base
            rates[t] = np.divide(page, base, out=np.full(K, np.nan), where=base > 0)
        else:
            if not c.has_default_column:
                continue
            # the default column of the engine's cohort matrix: over the transitions (d4, "exclude") or over the
            # whole cohort with the withdrawals as a ninth state (keep, "state"); a row without ratings is NaN
            m = _matrix(c, "exclude" if key == "d4" else "state")
            num[t], den[t] = c.counts[:, D], m["row_sizes"][:K]
            rates[t] = m["matrix"][:K, D]
        seen = True
    # a cell without a rate pools nothing (tab 3's events in a grade without ratings on tab 4 have no cohort here)
    undefined = ~np.isfinite(rates)
    num[undefined], den[undefined] = 0.0, 0.0
    return _Rates(rates, num, den) if seen else None


def _intervals(defaults: np.ndarray, n: np.ndarray) -> dict[str, dict[str, Any]]:
    """Wald, Agresti-Coull and Jeffreys at 95% on the pooled counts; None for a grade without ratings, and for tab 3's
    events where they outnumber the cohort (a rate of events, not a binomial proportion)."""
    ok = (n > 0) & (defaults <= n)
    out: dict[str, dict[str, Any]] = {}
    for name, fn in (("wald", intervals.pd_wald), ("agresti_coull", intervals.pd_agresti_coull),
                     ("jeffreys", intervals.pd_jeffreys)):
        lo, hi = np.full(K, np.nan), np.full(K, np.nan)
        if ok.any():
            r = fn(defaults[ok], n[ok], level=LEVEL)
            lo[ok], hi[ok] = r["lower"], r["upper"]
        out[name] = {"lower": _floats(lo), "upper": _floats(hi)}
    return out


def _lra(r: _Rates) -> dict[str, Any]:
    """The long-run average (paragraph 84) over the cohorts where the grade's rate is defined, the pooled counts with
    their intervals, and the average of the last five such cohorts (paragraph 86)."""
    rate, last5, used = np.full(K, np.nan), np.full(K, np.nan), np.zeros(K, dtype=int)
    for g in range(K):
        series = r.rates[np.isfinite(r.rates[:, g]), g]  # oldest first
        used[g] = series.size
        if series.size:
            rate[g], last5[g] = series.mean(), series[-RECENT:].mean()
    defaults, n = r.defaults.sum(axis=0), r.n.sum(axis=0)
    return {"rate": _floats(rate), "cohorts": used.tolist(), "defaults": _counts(defaults), "n": _counts(n),
            "pooled_rate": _floats(r.pooled()), **_intervals(defaults, n), "last5": _floats(last5)}


def _definition_gap(rates: dict[str, _Rates | None]) -> dict[str, Any]:
    """The pooled rates of d4 and d3 over d2's, by grade, each pair pooled over the cohorts where both rates are
    defined for the grade: a cohort with one of the two pages enters neither sum, so the ratio compares the definitions
    and not the years. None where d2's pooled rate is zero, the two share no cohort, or a definition is missing. Where
    tab 3's events equal tab 2's defaulted ratings (every CEREP cohort read, module docstring), d3_over_d2 is the ratio
    of tab 2's pooled cohort to tab 4's rows, not a count of repeated defaults."""
    base = rates["d2"]

    def ratio(key: str) -> list[float | None] | None:
        top = rates[key]
        if base is None or top is None:
            return None
        both = np.isfinite(top.rates) & np.isfinite(base.rates)
        num, den = top.pooled(both), base.pooled(both)
        return _floats(np.divide(num, den, out=np.full(K, np.nan), where=np.isfinite(num) & (den > 0)))

    return {"d4_over_d2": ratio("d4"), "d3_over_d2": ratio("d3")}


# ---------------------------------------------------------------------------------------------------------------------
# the pooled matrix, its embedding and its generators (CT-404)


def _pooled(cohorts: list[Cohort]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Anderson and Goodman's (2.8) over the annual cohorts, withdrawals removed (the industry treatment) and kept as
    an absorbing ninth state."""
    tables, withdrawn = [_square(c) for c in cohorts], [_withdrawn(c) for c in cohorts]
    ex = estimators.pooled_cohort(tables, withdrawn, treatment="exclude")
    if ex["empty_rows"]:
        empty = [GRADES[i] for i in ex["empty_rows"]]
        raise ValueError(f"no rating stays in {empty} over the cohorts: the pooled matrix, its generators and the "
                         "tests against it are undefined")
    return ex, estimators.pooled_cohort(tables, withdrawn, treatment="state")


def _pd_column(p: np.ndarray, has_default: bool) -> list[float | None]:
    """A matrix's default column over the performing grades; None throughout where the transition page has no default
    category (Moody's: the column's zeros are not PDs)."""
    return _floats(p[:K, D]) if has_default else [None] * K


def _horizon_pds(q: np.ndarray, has_default: bool) -> dict[str, list[float | None]]:
    return {"pd_1y": _pd_column(expm(q), has_default), "pd_5y": _pd_column(expm(HORIZON * q), has_default)}


def _embedding(diag: dict[str, Any]) -> dict[str, Any]:
    return {
        "S": _num(diag["S"]), "series_converges": bool(diag["series_converges"]), "det": _num(diag["det"]),
        "prod_diagonal": _num(diag["prod_diagonal"]),
        "theorem3": {"a": bool(diag["theorem3_a"]), "b": bool(diag["theorem3_b"]), "c": _pairs(diag["theorem3_c"])},
        "exact_generator_excluded": bool(diag["exact_generator_excluded"]),
        "stochastically_monotone": bool(diag["stochastically_monotone"]),
        "monotonicity_violations": [{"row": int(v["row"]), "next_row": int(v["next_row"]), "column": int(v["column"]),
                                     "tail": _num(v["tail"]), "next_tail": _num(v["next_tail"])}
                                    for v in diag["monotonicity_violations"]],
    }


def _generators(p: np.ndarray, fit: dict[str, Any], has_default: bool, series_converges: bool) -> dict[str, Any]:
    """The repaired generators of the pooled matrix, the EM generator of the annual counts (``fit``) and the pooled
    matrix's fifth power, each with its PDs by grade."""
    out: dict[str, Any] = {}
    for method in ("diagonal", "weighted", "jlt"):
        if method != "jlt" and not series_converges:
            out[method] = None  # Theorem 1's series diverges (S >= 1): there is no series generator to repair
            continue
        if method == "jlt" and np.any(np.diag(p)[:K] <= 0):
            out[method] = None  # equation (3) takes log(p_ii)
            continue
        g = embedding.generator(p, method=method)
        out[method] = {"generator": _floats(g["generator"]), "valid": bool(g["valid"]), "l1": _num(g["l1_distance"]),
                       **_horizon_pds(g["generator"], has_default)}
    q = fit["generator"]
    out["em"] = {"generator": _floats(q), "valid": embedding.is_generator(q), "l1": _num(embedding.l1_distance(p, q)),
                 **_horizon_pds(q, has_default), "iterations": int(fit["iterations"]),
                 "converged": bool(fit["converged"]), "loglik": _num(fit["loglik"][-1])}
    # the cohort projection a Markov reading gives without a generator: the one-year matrix to the fifth power
    out["cohort_power"] = {"pd_5y": _pd_column(np.linalg.matrix_power(p, int(HORIZON)), has_default)}
    return out


# ---------------------------------------------------------------------------------------------------------------------
# mobility, the ECB statistics and the Markov tests (CT-404)


def _mobility(cohorts: list[Cohort], rates: dict[str, _Rates | None]) -> dict[str, Any]:
    """M_SVD and the trace index of each annual cohort's own 8 x 8 matrix (None when a grade has no rating left to
    estimate its row), beside the cohort's speculative-grade default rate: d2 where the agency publishes tab 2, else
    d3, pooled over BB, B and CCC-C."""
    svd: list[float | None] = []
    trace: list[float | None] = []
    for c in cohorts:
        m = _matrix(c)["matrix"]
        ok = bool(np.all(np.isfinite(m)))
        svd.append(_num(mobility.svd_mobility(m)) if ok else None)
        trace.append(_num(mobility.trace_mobility(m)) if ok else None)
    spec: list[float | None] = [None] * len(cohorts)
    r = rates["d2"] if rates["d2"] is not None else rates["d3"]
    if r is not None:
        cols = list(SPECULATIVE)
        for t in range(len(cohorts)):
            d, n = r.defaults[t, cols].sum(), r.n[t, cols].sum()
            spec[t] = _num(d / n) if n > 0 else None
    return {"labels": [c.label for c in cohorts], "svd": svd, "trace": trace, "spec_default_rate": spec}


def _ecb(code: str, cohorts: list[Cohort], tests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The matrix weighted bandwidth and the migration z-tests of each annual cohort, on the 7 x 7 block of
    transitions between performing grades."""
    rows = []
    for c in cohorts:
        block = c.counts[:, :K]
        mwb = rating_system.rating_mwb(block, model_id=code, segment=c.label)
        z = rating_system.rating_migration_ztests(block, model_id=code, segment=c.label)
        tests += [mwb.to_dict(), z.to_dict()]
        rows.append({"label": c.label, "mwb_upper": _num(mwb.extras["mwb_upper"]),
                     "mwb_lower": _num(mwb.extras["mwb_lower"]), "ztests_p": _num(z.p_value)})
    return rows


def _homogeneity(code: str, cohorts: list[Cohort], halves: list[Cohort], p: np.ndarray,
                 tests: list[dict[str, Any]]) -> dict[str, Any]:
    """Time homogeneity across the annual and across the semester count matrices, and each annual cohort's counts
    against the pooled matrix (the engine's default forms, chosen by their measured size)."""

    def across(group: list[Cohort], segment: str) -> dict[str, Any]:
        r = markov.rating_time_homogeneity([_square(c) for c in group], model_id=code, segment=segment)
        tests.append(r.to_dict())
        # without a grade observed in two periods the engine returns an undefined statistic and no extras (dof 0)
        return {"statistic": _num(r.statistic), "p_value": _num(r.p_value), "dof": int(r.extras.get("dof", 0)),
                "periods": int(r.extras.get("periods", len(group)))}

    out: dict[str, Any] = {"annual": across(cohorts, "annual"),
                           "semesters": across(halves, "semesters") if halves else None, "reference": []}
    for c in cohorts:
        r = markov.rating_matrix_reference(_square(c), p, model_id=code, segment=c.label)
        tests.append(r.to_dict())
        out["reference"].append({"label": c.label, "statistic": _num(r.statistic), "p_value": _num(r.p_value),
                                 "dof": int(r.extras.get("dof", 0)),
                                 "impossible_moves": _pairs(r.extras.get("impossible_moves", []))})
    return out


def _chain(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """The two-period matrix A B. A grade with no ratings at the start of the second period has an undefined row in B,
    which matters only to the rows of A that reach it: those rows are undefined (NaN), the others are not."""
    defined = np.all(np.isfinite(b), axis=1)
    out = a @ np.where(defined[:, None], b, 0.0)
    out[np.any((np.nan_to_num(a) > 0) & ~defined[None, :], axis=1)] = np.nan
    return out


def _semesters_vs_year(cohorts: list[Cohort], halves: list[Cohort]) -> list[dict[str, Any]]:
    """For every year with an annual cohort and both semesters: the L1 distance of P_H1 P_H2 to P_year (withdrawals
    removed in all three) and the default columns of both."""
    by_label = {c.label: c for c in halves}
    out = []
    for c in cohorts:
        h1, h2 = by_label.get(f"{c.label}H1"), by_label.get(f"{c.label}H2")
        if h1 is None or h2 is None:
            continue
        year = _matrix(c)["matrix"]
        product = _chain(_matrix(h1)["matrix"], _matrix(h2)["matrix"])
        has_default = c.has_default_column and h1.has_default_column and h2.has_default_column
        out.append({"year": c.begin.year, "l1": _num(np.abs(year - product).sum()),
                    "pd_product": _pd_column(product, has_default), "pd_annual": _pd_column(year, has_default)})
    return out


# ---------------------------------------------------------------------------------------------------------------------
# the lifetime check (CT-415)


def _lifetime(windows: list[Cohort], cohorts: list[Cohort], p: np.ndarray, q: np.ndarray,
              has_default: bool) -> list[dict[str, Any]]:
    """Each window's fixed cohort at the window's end, as shares of the cohort (its tab 4 with the withdrawals a
    state; its tab 2, the rated defaulters over tab 2's cohort), against the projections over the same years: the
    window's annual matrices chained, withdrawals a state (its default and withdrawal columns) or removed; the pooled
    matrix to the number of years; exp(years Q) of the EM generator. A chain with a year missing is None throughout.

    The three default shares count different ratings. ``default_end`` is in a default category at the window's end:
    a rating that defaulted and was then withdrawn, or re-rated after a distressed exchange, within the window has left
    tab 4's default column. The chain's default column, default absorbing in the engine, holds a rating in default at
    any year-end (each year's tab 4 already misses the defaults withdrawn within that year). ``cumulative_d2`` counts
    every rated defaulter. What the chain's default column targets therefore lies between the other two by definition
    (CCC-C over 2015 to 2019, default_end, chain_state and cumulative_d2: S&P 0.0, 0.148 and 0.465; Fitch 0.0, 0.109
    and 0.380): chain_state above default_end is not by itself a failure of the Markov chain, and it is read against
    both."""
    by_year = {c.begin.year: c for c in cohorts}
    out = []
    for w in windows:
        first, last = w.begin.year, w.end.year
        years = last - first + 1
        fixed = _matrix(w, "state")["matrix"]  # 9 x 9: the grades, D, then the withdrawn
        chain = [by_year.get(y) for y in range(first, last + 1)]
        projected: dict[str, Any] = {"chain_state": [None] * K, "chain_state_withdrawn": [None] * K,
                                     "chain_exclude": [None] * K}
        if all(c is not None for c in chain):
            state, exclude = _matrix(chain[0], "state")["matrix"], _matrix(chain[0])["matrix"]
            for c in chain[1:]:
                state, exclude = _chain(state, _matrix(c, "state")["matrix"]), _chain(exclude, _matrix(c)["matrix"])
            chain_default = all(c.has_default_column for c in chain)
            projected = {"chain_state": _pd_column(state, chain_default),
                         "chain_state_withdrawn": _floats(state[:K, D + 1]),
                         "chain_exclude": _pd_column(exclude, chain_default)}
        projected["pooled_power"] = _pd_column(np.linalg.matrix_power(p, years), has_default)
        projected["em"] = _pd_column(expm(years * q), has_default)
        cumulative = None
        if w.defaulted is not None:
            base = _tab2_cohort(w)
            cumulative = _floats(np.divide(w.defaulted, base, out=np.full(K, np.nan), where=base > 0))
        out.append({"label": w.label, "first": first, "last": last, "size": _counts(w.size),
                    "observed": {"default_end": _pd_column(fixed, w.has_default_column),
                                 "withdrawn_end": _floats(fixed[:K, D + 1]), "cumulative_d2": cumulative},
                    "projected": projected})
    return out


# ---------------------------------------------------------------------------------------------------------------------


def agency_outputs(code: str, annual: list[Cohort], semesters: list[Cohort],
                   windows: list[Cohort] | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """The outputs of one agency variant (contract section 1) and every registered test run on its cohorts, as
    ``TestResult.to_dict()`` rows with ``model_id`` the agency code and ``segment`` the cohort label, ``"annual"`` or
    ``"semesters"``. ``annual``, ``semesters`` and ``windows`` (the multi-year windows of the lifetime check, none by
    default) are the agency's cohorts with data as ``read_agency`` returns them, in any order."""
    if code not in AGENCIES:
        raise ValueError(f"unknown agency {code!r}: one of {sorted(AGENCIES)}")
    years = _checked(code, annual, "annual")
    halves = _checked(code, semesters, "semester")
    spans = _checked(code, windows or [], "window")
    if not years:
        raise ValueError(f"{code}: an agency variant needs at least one annual cohort")
    tests: list[dict[str, Any]] = []
    rates = {key: _definition(years, key) for key in DEFINITION_KEYS}
    ex, st = _pooled(years)
    p = ex["matrix"]
    diag = embedding.embedding_diagnostics(p)
    has_default = all(c.has_default_column for c in years)
    # EM on the annual steps of length one (withdrawn ratings leave a step's counts: the industry treatment)
    fit = em_generator([{"counts": _square(c), "dt": 1.0} for c in years])
    outputs: dict[str, Any] = {
        "kind": "agency",
        "agency": {"code": code, "name": AGENCIES[code], "scope": SCOPE},
        "attribution": ATTRIBUTION,
        "grades": list(GRADES),
        "states": list(STATES),
        "cohorts": [_record(c) for c in years],
        "semesters": [_record(c) for c in halves],
        "pd": {key: None if rates[key] is None else _floats(rates[key].rates) for key in DEFINITION_KEYS},
        "lra": {key: None if rates[key] is None else _lra(rates[key]) for key in LRA_KEYS},
        "pooled": {"matrix": _floats(p), "matrix_state": _floats(st["matrix"]), "counts": _counts(ex["counts"][:K]),
                   "withdrawn": _counts(ex["withdrawn"][:K]), "row_sizes": _counts(ex["row_sizes"][:K]),
                   "cohorts": int(ex["periods"])},
        "embedding": _embedding(diag),
        "generators": _generators(p, fit, has_default, bool(diag["series_converges"])),
        "mobility": _mobility(years, rates),
        "ecb": _ecb(code, years, tests),
        "homogeneity": _homogeneity(code, years, halves, p, tests),
        "semesters_vs_year": _semesters_vs_year(years, halves),
        "definition_gap": _definition_gap(rates),
        "lifetime": _lifetime(spans, years, p, fit["generator"], has_default),
    }
    return outputs, tests
