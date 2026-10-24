"""The downturn LGD of C08 (CT-911): the downturn period, the cohort-based add-on and its coverage.

Contraste's own cohort-based add-on, an illustration and not a regulatory estimate (dossier 04 F.4; the EBA/RTS/2018/04 and
EBA/GL/2019/03 wording is UNVERIFIED there). The engine does every step: ``identify_downturn`` marks the downturn years from
the supplied indicator, ``downturn_add_on`` takes the default-weighted means, ``coverage_shortfall`` and ``downturn_coverage``
judge the estimate against the realised downturn losses.

The indicator is the annual charge-off rate of the SBA 7(a) book (``panel.annual_rate``), a credit indicator: the pipeline's
source registry lists the Federal Reserve history tables for other cases and not for C08, so the case does not read a macro
path. The threshold is a policy parameter, the mean plus ``DOWNTURN_SD`` standard deviations of the rates of the years read.
A cohort is a downturn cohort when at least half of its default years are downturn years. The block is a fact of the whole
file (the long-run LGD is over the six cohorts), identical in every variant; the rungs are the models of a cutoff, this is not.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from riskvalidation.lgd_ead import downturn as rv_down
from riskvalidation.validation import lgd_ead as rv_val

from .build import DOWNTURN_SD, lgd, t
from .panel import COHORTS, AnnualRate, Defaults

INDICATOR = t("annual charge-off rate of the SBA 7(a) book (charge-offs of the year over loans open on 1 January)",
              "tasa anual de castigos de la cartera SBA 7(a) (castigos del año sobre los préstamos abiertos al 1 de enero)")
SOURCE = t("the SBA FOIA loan file (a credit indicator of the book itself; no macro path is read)",
           "el archivo de préstamos FOIA de la SBA (un indicador de crédito de la propia cartera; no se lee una trayectoria macro)")


@dataclass(frozen=True)
class DownturnPlan:
    period: dict[str, Any]
    approach: dict[str, str]
    rows: list[dict[str, Any]]
    coverage: dict[str, Any]
    tests: list[dict[str, Any]]
    threshold: float
    flagged_years: list[int]
    downturn_cohorts: list[str]
    long_run: float
    downturn: float


def downturn_threshold(rate: np.ndarray, sd: float = DOWNTURN_SD) -> float:
    r = rate[np.isfinite(rate)]
    return float(r.mean() + sd * r.std())


def longest_run(years: np.ndarray, flag: np.ndarray, indicator: np.ndarray) -> tuple[int, int]:
    """The first and last year of the longest run of consecutive downturn years (the highest peak breaks a tie)."""
    best: tuple[int, float, int, int] | None = None
    i = 0
    while i < len(years):
        if not flag[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(years) and flag[j + 1] and years[j + 1] == years[j] + 1:
            j += 1
        cand = (j - i + 1, float(np.max(indicator[i:j + 1])), int(years[i]), int(years[j]))
        if best is None or cand[:2] > best[:2]:
            best = cand
        i = j + 1
    if best is None:
        raise ValueError("no year of the indicator is above the threshold: there is no downturn to estimate")
    return best[2], best[3]


def plan(defaults: Defaults, annual: AnnualRate, threshold: float | None = None) -> DownturnPlan:
    """The downturn period, the add-on rows and the coverage tests, from every default of the file."""
    thr = downturn_threshold(annual.rate) if threshold is None else float(threshold)
    ok = np.isfinite(annual.rate)
    years, ind = annual.years[ok], annual.rate[ok]
    flag = np.asarray(rv_down.identify_downturn(years, ind, thr, True), dtype=bool)
    first, last = longest_run(years, flag, ind)
    flagged = {int(y) for y, f in zip(years, flag, strict=True) if f}
    y_all = defaults.y
    cohort_ids, lgds, weights, mask = [], [], [], []
    for cid, lo, hi in COHORTS:
        k = (defaults.year >= lo) & (defaults.year <= hi)
        cohort_ids.append(cid)
        lgds.append(float(y_all[k].mean()))
        weights.append(float(k.sum()))
        yrs = range(lo, hi + 1)
        mask.append(2 * sum(1 for y in yrs if y in flagged and first <= y <= last) >= len(yrs))
    res = rv_down.downturn_add_on(np.array(lgds), np.array(weights), np.array(mask, dtype=bool))
    rows, tests = [], []
    for cid, m, mean_lgd, w in zip(cohort_ids, mask, lgds, weights, strict=True):
        if not m:
            continue
        lo, hi = next((a, b) for c, a, b in COHORTS if c == cid)
        k = (defaults.year >= lo) & (defaults.year <= hi)
        covered, shortfall = rv_down.coverage_shortfall(res.downturn, mean_lgd)
        rows.append({"cohort_id": cid, "n": int(w), "long_run_lgd": lgd(res.long_run), "downturn_lgd": lgd(res.downturn),
                     "add_on": float(res.downturn - res.long_run), "crisis_realised_lgd": lgd(mean_lgd),
                     "covered": bool(covered), "shortfall": float(shortfall)})
        tests.append(rv_val.downturn_coverage(res.downturn, y_all[k], segment=f"cohort-{cid}").to_dict())
    if not rows:
        raise ValueError("no cohort has half of its default years inside the downturn period")
    coverage = {"n_cohorts": len(rows), "share_covered": float(sum(r["covered"] for r in rows) / len(rows))}
    period = {"first_year": first, "last_year": last, "indicator": dict(INDICATOR), "macro_source": dict(SOURCE)}
    approach = t(
        "Cohort-based add-on: the default-weighted mean LGD proxy of the downturn cohorts minus the long-run mean over the six "
        "cohorts, with the downturn identified from the annual charge-off rate of the SBA 7(a) book. An illustration, not a "
        "regulatory estimate.",
        "Ajuste por cohortes: la LGD proxy media ponderada por incumplimientos de las cohortes de crisis menos la media de largo "
        "plazo de las seis cohortes, con la crisis identificada por la tasa anual de castigos de la cartera SBA 7(a). Una "
        "ilustración, no una estimación regulatoria.")
    return DownturnPlan(period, approach, rows, coverage, tests, thr, sorted(flagged), [r["cohort_id"] for r in rows],
                        float(res.long_run), float(res.downturn))
