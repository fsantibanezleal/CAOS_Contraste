# Design: U8-P1, case C11 (market VaR and ES back-testing across 2008, 2020, 2022 and 2023)

Status: live. The requirements are in [`requirements.md`](requirements.md), the adversarial checks in
[`validation.md`](validation.md), the reader-facing page in [`../../../cases/C11.md`](../../../cases/C11.md).

## Problem and what is built

A market risk function must defend its VaR and ES: which model is eligible, which beats the champion under a consistent
score, whether the exceedances cluster, and how the answer changes between a calm year and a crisis. C11 bakes that chain on
public daily series and validates it the way a model risk function would. It stands on the engine contract
`engine-market-api` 1.0.0 (`docs/contracts/engine/market-api.md`), implemented by `riskvalidation.market` and
`riskvalidation.validation.market` (release v0.07.000, with the `market` extra),
and produces the `c11-outputs` and `c11-models` documents (`docs/contracts/schemas/c11/`) as their real producer.

## The data and the windows (CT-601 to CT-603)

Three public daily series: the US equity market from the Kenneth French daily factors (excess return plus the risk-free rate;
derived-only), the 10-year US Treasury par yield and the euro in US dollars from the Federal Reserve H.10. Six windows with the
forecast dates of decision D2: calm 2004-01-02 to 2006-12-29, equity 2007-07-02 to 2009-06-30, FX 2008-07-01 to 2009-06-30,
equity 2020-02-03 to 2020-06-30, rates 2022-01-03 to 2022-12-30 and mixed 2023-03-01 to 2023-05-31. The book of a window is a
constant-weight, daily-rebalanced portfolio: 100 percent of one series, or the mixed book of 50 percent equity, 30 percent
Treasury bond and 20 percent euro for the mixed 2023 and the calm windows (decision D4). The Treasury return is minus the
modified duration of a 10-year par bond at the previous day's yield times the yield change; carry and convexity are left out.

The calendar of a book is the days on which every component is observed; the others are skipped and counted, never filled,
and the return after a skipped day is taken between the two observed days from the components' levels.

## The rolling scheme and the ladder (CT-604, CT-607)

For the forecast day at position `i`, every model sees `y[i - w:i]` and no more (`forecast.run_model`). The ladder is
dossier 05's rungs 1 to 9 and the R10 quantile network trained on FZ0 (S-1 of the method tiers): historical simulation (250 and 500 days), age-weighted
historical simulation, delta-normal and Cornish-Fisher on rolling moments, EWMA, GARCH(1,1), GJR and EGARCH with Student-t
innovations, filtered historical simulation, conditional EVT, CAViaR (SAV, AS and the two-step ES extension) and the three
GAS-FZ models and the network (one hidden layer of 8 tanh units, softplus outputs so that ES is at most VaR, Adam on the mean FZ0 of the standardised returns, 3 seeded starts, features from the previous five returns and two volatilities, all of the window's own days). Refit frequency: the GARCH family, the filtered historical simulation, the conditional EVT and the ES step of CAViaR every
day; the CAViaR VaR fits (20 starts) every 5 forecast days; the GAS-FZ fits (20 starts) every 20. Between refits the
parameters are kept and the filter runs over the current window. A fit that fails keeps the previous fit and is counted (the
GARCH family uses the unconverged first fit when it has no other); a day without a usable forecast holds the previous day's
and is counted (both are in the models document).

## The hyperparameters (CT-605)

Fixed once on 1995-01-01 to 2003-12-31 by `hyper.select` (the span ends before the calm window, which is itself a test
window): the estimation window (500, 750, 1,000 days), the EWMA decay (0.94, 0.97, 0.99), the age-weight decay (0.98, 0.99)
and the EVT threshold fraction (5, 10, 15 percent), each by the lowest summed average FZ0 of the model that uses it over the US
equity market and the 10-year bond, both tail levels, on every fifth forecast day of the span. The euro series starts in 2000
and cannot carry a window inside the span, so the FX leg is not part of the selection. The numbers of CAViaR and GAS starts and
the refit frequencies are set by the compute budget and not tuned.

## Tests, eligibility and comparison (CT-608 to CT-611)

Per model and level: Kupiec, Christoffersen independence and conditional coverage, the duration test, the dynamic quantile
test and the Acerbi-Szekely Z2 test. The Basel traffic light is the engine's zone over every rolling 250 days at 99 percent,
`not_evaluated` with its reason under 250 forecast days (decision D3). A model is eligible when none of Kupiec, conditional
coverage and Z2 is red at either level; the champion is the lowest average FZ0 among the eligible models with an ES on every
day; Diebold-Mariano (zero lags, one-step forecasts) compares each model with the champion, and the 90 percent model confidence
set (statistic TR, stationary bootstrap) is taken over the models with an ES on every day.

The Z2 null is the engine's simulation under a tail-consistent law: on each day the loss exceeds the VaR with probability
alpha, by an exponential excess whose mean is ES minus VaR. A historical, CAViaR or GAS model has no predictive distribution of
its own, so one null serves the whole ladder; it reproduces each model's VaR and ES and tests the ES level. Its shape is an
assumption: a heavier true tail makes the critical values too narrow. The Du-Escanciano and McNeil-Frey tests are in the engine
and need a probability integral transform or a volatility path that not every rung has; C11 does not run them.

## Documents, determinism and the expected ranges (CT-612 to CT-614)

Every array is rounded to the nine significant digits the writer keeps before any score is taken, so each score recomputes
from the committed arrays (the producer checks do). Every seed is the one in the hyperparameters; the forecasts are cached under a
hash of the series, the hyperparameters, the model and the engine commit. The French realised-loss series is withheld
(derived-only); the exceedance days and the scores stand. The bake declares the expected range of the forecast days of each
window and stops when a result leaves it.
