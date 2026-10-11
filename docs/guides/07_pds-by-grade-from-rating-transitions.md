# Guide: PDs by grade from rating transitions, and what to check before using them

Case C04 does this on CEREP's pages for three agencies and on rating paths whose truth is known; this guide is the same
work on your own rating history, with riskvalidation 0.4.3 in Python, and on CEREP for another scope. Grades are best
first and default is the last state, as in the engine.

## 1. Say which default you count

A grade's PD is a count of defaults over a count of obligors, and both counts are choices. EBA/GL/2017/16 sets them for
the one-year default rate: the denominator is the non-defaulted obligors at the start of the year (paragraph 73), an
obligor stays in it when it migrates or its obligations are sold, written off, repaid or closed during the year
(paragraph 76), each defaulted obligor is counted once (paragraph 77), and the long-run average is the average of the
one-year rates over a representative period (paragraph 84). A migration matrix built the usual way does something
else: it removes the ratings withdrawn by the end of the year (Schuermann and Hanson's "industry standard"), so a
rating that defaulted and was then withdrawn leaves the count.

C04 measured how far apart the two are on the same ratings. CEREP's transition matrix gives 29% of the default page's
long-run CCC to C PD for S&P and 19% for Fitch (whose default columns hold no rating at all from 2006 to 2014), and
Moody's matrix has no default column. On paths with informative withdrawals (the hazard of withdrawal ten times higher
in the year before default) B's PD is 34% below the truth with withdrawals removed, 38% below with them kept in the
denominator, and 15% below when they are followed to their outcome as paragraph 76 asks. Follow a withdrawn obligor
where your data allow it, and say which definition every PD follows.

## 2. The one-year matrix

```python
from riskvalidation.transitions.estimators import cohort, pooled_cohort, duration_generator

year = cohort(counts_2024, withdrawn_2024)                     # one cohort; withdrawals removed by default
kept = cohort(counts_2024, withdrawn_2024, treatment="state")  # or kept as an absorbing state
pooled = pooled_cohort(counts_by_year, withdrawn_by_year)       # Anderson and Goodman (2.8): tables added, rows normalised
p = pooled["matrix"]
```

`counts` is square (start state by end state, default last); a row with no ratings comes back as NaN and is listed in
`empty_rows`. Expect zeros where the truth is not zero: the cohort PD of AAA is exactly zero in every one of S&P's and
Moody's 26 CEREP years, and on rating paths with S&P-like cohorts in 99% of samples, while the true one-year PD is
0.66bp. If you have the dates of rating changes, `duration_generator(paths, n_states)` counts every move and the time
at risk, and it is the only estimator in C04's measurements that recovers that PD (0.82bp in RMSE).

## 3. A generator, if one exists

```python
from riskvalidation.transitions import embedding
from riskvalidation.transitions.em import em_generator

d = embedding.embedding_diagnostics(p)
print(d["S"], d["theorem3_c"], d["exact_generator_excluded"], d["stochastically_monotone"])
for method in ("diagonal", "weighted", "jlt"):
    g = embedding.generator(p, method=method)
    print(method, g["valid"], g["l1_distance"])
em = em_generator([{"counts": c, "dt": 1.0} for c in counts_by_year])   # maximum likelihood from snapshots
```

Israel, Rosenthal and Wei's Theorem 3 excludes an exact generator for each of CEREP's three pooled matrices (6 moves
reachable but never observed for S&P and Moody's, 15 for Fitch), and none is stochastically monotone. The diagonal and
weighted adjustments come within L1 0.0013 to 0.0100 of the matrix, JLT 10 to 53 times further. From annual snapshots
EM does no better than the adjustments on a rare PD: on C04's paths they all miss AAA's 0.66bp by 3.7bp to 3.8bp in
RMSE, their biases within their Monte Carlo errors of one another.

## 4. Is the chain Markov and time-homogeneous?

```python
from riskvalidation.validation.transitions import (
    rating_markov_order, rating_matrix_reference, rating_momentum, rating_time_homogeneity)

rating_time_homogeneity(counts_by_year)               # one-year count tables: CEREP is enough
rating_matrix_reference(counts_2024, p)                # one year against a reference matrix
rating_markov_order(triplets)                          # obligors in i, then j, then k: needs your own histories
rating_markov_order(triplets, form="lr")               # report both forms
rating_momentum(paths)                                 # rating paths with times: the downgrade hazard
```

What each needs decides what you can test: CEREP's aggregates allow time homogeneity and the reference test only. With
thousands of ratings time homogeneity rejects almost every year against the pooled matrix (all 26 of S&P's): read
which years depart and by how much, not the global p-value. The order test's two forms do not hold their size on every
chain: on C04's S&P-like chain the chi-square rejects 7.10% at 5% and the likelihood ratio 4.55%, on riskvalidation's
size-study chain the chi-square holds; report both. Momentum at the strength dos Reis et al. estimate (C04's alpha
0.125) is seen by the momentum test every time and by time homogeneity in 8.5% of samples.

## 5. An interval for each grade's PD

```python
from riskvalidation.transitions import intervals

intervals.pd_jeffreys(defaults, n, level=0.95)
intervals.pd_agresti_coull(defaults, n, level=0.95, rho=0.01)      # the dependence correction, (3.4)
intervals.effective_n(2000, 0.01)                                  # what 2,000 correlated obligors are worth
intervals.exact_coverage("wald", 50, 0.000066)                     # the coverage you may claim, by enumeration
intervals.overlap_probability("jeffreys", 1000, 0.000066, 0.0004)  # can two grades be told apart?
```

The Wald interval collapses to zero width when a grade has no default, which is the usual case for good grades: on
C04's paths it covers AAA's true PD in 1% of samples, and with 50 obligors its exact coverage is 0.33%. Agresti-Coull
and Jeffreys hold near their level. Adjacent investment grades are often not separable at all: with 1,000 obligors per
grade the Jeffreys intervals of AAA and AA overlap with probability 1.00.

## 6. The lifetime a matrix gives, against the one a cohort lived

A lifetime PD built by chaining one-year matrices (an IFRS 9 staple) assumes the chain is Markov and stable. Check it on
a closed window: take one cohort, count how many of its ratings defaulted within five years, and compare with the
window's own annual matrices chained and with the pooled matrix to the fifth power. On CEREP, S&P's CCC to C cohort of
2020 lived 61.4% defaults in five years; its annual matrices chained give 9.1% and the pooled matrix to the fifth power
25.3%. CEREP's transition pages put a rating that defaulted and was withdrawn within the year in the withdrawals
column, so the matrices' default column misses most defaults, which is why the gap is this wide there; on your own
data, with every default kept as an absorbing state, the gap measures the chain's other failures (momentum, a cycle
that moves).

## 7. Drift with no scenario at all

```python
from riskvalidation.transitions import ttc

t = ttc.ttc_portfolio(p, origination)                 # Engelmann's TTC portfolio of the matrix and its PD
proj = ttc.project(p, portfolio_today, origination, 10)
print(t["default_rate"], proj["default_rate"])
```

Under one unstressed matrix a portfolio drifts towards the matrix's own TTC portfolio (Engelmann 2024), so its projected
default rate moves with no scenario: S&P's TTC portfolio defaults at 0.61% a year and the latest cohort's mix at 0.77%.
Separate that drift from the scenario's effect before reading a stress result.

## 8. CEREP for another scope

The fetch plan is data: `data-pipeline/config/sources.json`, source `esma-cerep`, lists the agencies' EU entities
(`cras`), the rating type (`C`, categories), the horizon (`L`, long-term), the years, the semesters and the five-year
windows, and a pace of at least four seconds between requests (the service resets the connection when asked faster).
`data-pipeline/fetch.py esma-cerep` writes every answer to `$CONTRASTE_DATA/raw/esma-cerep` and pins its hash in the
licence manifest (`data/sources/manifest.json`); `pipeline.io.cerep.read_agency(root, cra, years, semester_years,
windows=...)` reads the annual, semester and window cohorts. An agency's labels must be in `cerep.SCALE`: the reader
refuses a label it does not know rather than guess its grade. CEREP's reproduction is authorised provided the source
is acknowledged, so every table you publish says "Source: ESMA CEREP" and that you transformed it. Expect the default
page to count a larger cohort than the transition page in many years (18 of S&P's 26) with no reason given: keep both,
and take each rate over its own page's cohort.
