# Design: U7-P, case C10, portfolio credit capital

Requirements: [`requirements.md`](requirements.md). Parent: [`../../SDD.md`](../../SDD.md) sections 4 and 5. The case page, with the
executive brief, the data, the fitted distributions, the ladder and the simulator read from the committed documents, is
[`../../../cases/C10.md`](../../../cases/C10.md); the contracts are `docs/contracts/schemas/c10/` (`c10-models`, `c10-outputs`,
`c10-outputs-grid`) and the engine contract is `docs/contracts/engine/portfolio-api.md` (`riskvalidation.portfolio`, pinned by commit
502652b of `task/u7-portfolio` until the integrator tags the release).

## The question

A validator is asked whether the capital of a credit portfolio is right. Three things decide it: how much the loss rates of a loan type
move together (the asset correlation), what the tail of that movement looked like when it came (2007-2012), and how much the
portfolio's own shape (concentration, tail dependence, the form of the model) adds to the single-factor answer. The case fits the
Vasicek distribution to the Federal Reserve's yearly net charge-off rates of five loan types on 1985-2006, places the realised
2007-2012 rates in it, builds one illustrative portfolio per loan type, runs the ladder of dossier 04 on it, and measures on a
simulator with a known correlation how often the correlation estimate is right.

## Method

1. **The data** (`fed.py`): the Board's `chgallsa.htm` (net charge-off rates, All Banks, seasonally adjusted, quarterly from
   1985:1). The page is parsed with the standard library; columns are named by the header ids of their cells (`CI`, `RECI`, `RERES`,
   `CONCC`, `CONOTH`), a percentage becomes a decimal, `n.a.` is a missing quarter and any other word is refused. The annual rate of a
   year is the mean of its four quarterly rates; a year with a missing quarter has no rate and a reason, never an interpolated one.
   Residential and commercial real estate are `n.a.` for 1985-1990, so their fit window has sixteen years, not twenty-two. The saved
   page is pinned by bytes and, because the Board's page carries a per-request script token, by the digest of its numbers over the
   years used (`params.RAW`); the page, its URL, size, SHA-256 and dates are recorded in `data/derived/C10/SOURCES.txt` and the
   provenance names the file and its hash.
2. **The fit** (`documents.fit_series`): maximum likelihood (`asrf_fit.fit_ml`) with the profile-likelihood interval, and the method of
   moments (`asrf_fit.fit_moments`) with the parametric-bootstrap interval, on the fit-window years only (a leak into the evaluation
   window is refused by `check_fit_input`). The profile of the asset correlation on a grid that contains the estimate, the implied
   factor of every year and its place in the fitted distribution come from the same engine module.
3. **The tail** (`documents.backtest_block`): the engine's `tail_backtest` places the evaluation years against the fitted 95%, 99% and
   99.9% quantiles, with the upper binomial tail beside each count.
4. **The IRB comparison** (`documents.irb_block`): the fitted correlation against the IRB correlation of the nearest regulatory class,
   the capital per unit of EAD both ways with the same maturity treatment, so the ratio isolates the correlation. The class is the
   nearest of the Basel framework, not a claim about the Board's series.
5. **The illustrative portfolio** (`portfolios.py`): three groups (large, mid-size, small names), 100 million USD, one expected LGD of
   0.45, group PDs a multiple (0.5, 1, 1.5) of the fitted PD scaled so that the exposure-weighted PD is exactly the fitted PD, every
   name loading on the factor with the square root of the fitted correlation. Names and exposures differ by loan type (few large loans
   for commercial, many small ones for consumer). It is labelled illustrative in the block and in the provenance.
6. **The ladder** (`ladder.py`): C1 the large homogeneous portfolio at the fitted PD and correlation; C2 the Gaussian copula, one factor
   (the fitted correlation) and two sector factors (correlation 0.5 between sectors); C3 the Student-t copula with 5 degrees of
   freedom; C4 CreditRisk+ with one Gamma sector whose variance matches the Vasicek default-rate variance and the stable recursion; C5
   the granularity adjustment of Gordy and Lutkebohmert with K at the IRB capital at the regulatory correlation; C6 importance
   sampling of the Gaussian copula, twisted at the plain Monte Carlo 99.9% VaR, and its Student-t counterpart written as not
   evaluated. The Monte Carlo runs 10^6 scenarios in chunks bounded at 0.8 GB, seeded. The Euler contributions of the three
   sample-based rungs come from the sample that gave the rung's measures, so they add to its VaR (kernel, within 1%) and ES (exactly).
7. **The checks of the ladder** (engine tests): the Monte Carlo against the analytic LHP anchor on a portfolio of 5,000 identical names
   (the finite portfolio's granularity gap is the C5 rung's), the Euler additivity at both levels, and the CreditRisk+ recursion
   against a Monte Carlo of the same Poisson-Gamma model (the comparator draws the model's definition; the engine's test compares).
8. **The simulator** (`simulator.py`): a yearly factor draw turned into the LHP default fraction by the engine's conditional PD, a known
   correlation on the grid 0.02 to 0.24, series of 22 and 40 years, 1,000 replications per cell, each with its own seeded stream; the
   two estimators with their 95% intervals; H0: rho = 0.12 rejected when the null lies outside the interval; the rate, its error and
   its Wilson interval from the engine's `correlation_size_power`.

## Decisions the contracts left to the bake

- A year that lacks a quarter is one entry of `data_status.missing_quarters` (the contract's cross-field check compares the entries
  with the years that have fewer than four quarters, one for one): its `quarter` is the first missing quarter of the year and its reason
  names every missing quarter.
- The convergence check and the Euler anchor use the contract's definitions; the granularity truth uses the weight on the systematic
  factor implied by K (`omega = K / (LGD PD (alpha_q - 1))`, Gordy and Lutkebohmert 2013, eq. 13), so `mu(alpha_q) = EL + K`.
- The recursion has deterministic recoveries, so its granularity truth excludes the LGD-variance term the formula carries; the page
  states the difference.
- Replications whose series cannot identify the correlation (a constant series, or no excess dispersion for the moments) are failed
  replications, counted in `n_failed`; a maximum-likelihood estimate at the parameter bound is kept as an estimate.

## Limits

The large homogeneous portfolio and the IRB form are approximations (infinite granularity, one factor, a Gaussian copula); the
charge-off rate is a net loss rate, not a default frequency; the Board's series are of all banks, not of a portfolio; the portfolio
is illustrative; the Student-t importance sampling is not specified (a not-evaluated rung); the multi-factor rungs have no closed-form
anchor.
