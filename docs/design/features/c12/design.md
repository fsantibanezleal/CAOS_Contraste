# Design: U9-P1, case C12 (swap exposure, CVA and SA-CCR on a synthetic USD swap book)

Status: live. Unit sizing `plans/contraste/units/U9-sizing.md` (CAOS_MANAGE), decisions D1 to D8, B1 to B10, S1 to S4 and R1 to R2.
Contracts: `c12-outputs`, `c12-models` (`docs/contracts/schemas/c12/`), `engine-ccr-api` 2.0.0 and `engine-regulatory-api` 2.0.0
(`docs/contracts/engine/`).

## Question

How large is the counterparty exposure of a swap book, what CVA does it imply, and would the simulated exposures have held against
the curves later realised? The book is synthetic (decision R1): a 10 year payer of 10M USD (the single swap), and with it a 5 year
receiver of 6M, a 3 year payer of 4M and a 0.5 year receiver of 2M (the netting set); the fixed rate of each is the par yield of its
maturity on the curve date, rounded to 10 bp. The curve date is the last backtest date, a month end.

## Real curves, synthetic book

The curves are the US Treasury daily par yield curves (1990 to today) and the HQM corporate spot curve; the book, the CSA, the
counterparty's LGD, the bank's own spread and every other named parameter are conventions, labelled as such in each document. The
Hull-White a and sigma are estimated from the Treasury history before each date (decision B6) and the model is fitted to the curve of
the date.

## What the bake computes, and what the engine computes

The product reads the files, bootstraps the curves, builds the book, sequences the calls and writes documents. Every exposure,
profile, PFE, CVA, DVA, EAD, add-on, GIRR charge, PIT statistic and test row is a `riskvalidation` call (ADR-0069); the bake adds
bookkeeping only (the grid indices, the batch errors of the first-year averages, the sticky-date roll of the swaps, ORE's input
files).

- **Measure.** The discounted EE is a price and does not depend on the measure the paths are drawn in. The undiscounted EE and ENE
  of a document are the expectation in the t-forward measure, the discounted EE divided by P(0, t): that is the rung-2 identity of
  the engine contract and the quantity ORE's own discounted profile reproduces. The mean of the paths themselves is the expectation in
  the simulation's own measure (the bank account for the engine, the LGM numeraire for ORE), which differs by the convexity gap
  (measured: ORE's own undiscounted profile sits up to 5 percent below the engine's at ten years). The PFE is a quantile of the
  paths (simulation measure) and says so.
- **Sticky-date close-out.** The close-out value at the default date t is the value of the portfolio under the market of t + delta
  with the portfolio not aged: the swap rolled forward by delta and valued at t + delta by the engine's `swap_value`, with the coupon
  fixed at the last reset on or before t read as fixed. delta is the calendar-day equivalent of the MPoR on the 30/360 axis of the case
  (14 days for 10 business days, 28 for 20), as ORE counts it.
- **Initial margin.** The engine's regression DIM (ORE's method, a proxy, never SIMM) applied path by path, E[max(X - DIM, 0)]
  (decision B2). `dim` in the document is the mean DIM; the expected exposure after margin lies between max(ee_vm_only - dim, 0)
  and ee_vm_only (Jensen). The main session amended `check_c12` to that inequality on this branch.

## Backtest

On every monthly date from 2000-01 the model is calibrated on the observations before the date, the book is originated at par, the
paths are simulated to the six horizons, and the book is revalued on the curve actually published at the end of each horizon by the
engine's `swap_value` (the model with sigma = 0 on that curve). The PIT, W^2 and the effective sample size are the engine's. The
critical values come from the engine's simulation of the whole backtest under the model: one Brownian path on a daily grid drives
every date, the deviation of the realised state from the date's forecast is the integral of the mean-reverting kernel at the date's
own a, so overlapping horizons share increments.

## Documents

`C12/<variant>.json` for the six variants (`c12-outputs`), `C12/models-hw1f-treasury-2000-2025.json` (`c12-models`: the calibration of
every backtest date, the counterparty curve, the GIRR parameters, the limits), `C12/SHA256SUMS.txt`, `C12/raw-sources.txt` and
`manifests/C12.json`. The ORE XML inputs of every run are committed under `data-pipeline/pipeline/cases/c12/ore_inputs/`.
