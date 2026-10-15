# Design: U12-P, case C17, operational risk: LDA against SMA

Requirements: [`requirements.md`](requirements.md). Parent: [`../../SDD.md`](../../SDD.md) sections 4 and 5. The case page, with the
generator, the known truth and the result read from the committed documents, is [`../../../cases/C17.md`](../../../cases/C17.md);
the contracts are `docs/contracts/schemas/c17/` (`c17-models`, `c17-outputs`) and the engine contract is
`docs/contracts/engine/oprisk-api.md` (`engine-oprisk-api` 1.0.0, `riskvalidation.oprisk` pinned to the release v0.07.000).

## The question

A validator is asked whether the 99.9 percent operational risk capital a bank estimates from 5 or 10 years of internal losses is right,
and how the standardised approach (SMA) of OPE25 compares with it. Real loss data never says what the true annual loss quantile was.
The case draws loss histories from a generator whose annual loss distribution is known, so that every rung of the loss distribution
approach (LDA) is scored against the truth at four tail indices, two lengths of history and two collection thresholds.

## Method

1. **Calibration** (`generator.py`, `params.py`). The severity is a GPD above the generator floor of EUR 10,000 with the tail index of the
   variant (0.6, 0.8, 0.96 or 1.1). Its scale is the one free parameter, fitted by least squares on the log excess quantiles to the four
   BCBS 2008 LDCE median percentiles above EUR 20,000 (27,632, 41,916, 82,608, 418,400; the dossier 05 F.6 objective, the tail index held at
   the variant's). A GPD conditioned above EUR 20,000 is a GPD with scale `beta + xi (20,000 - floor)`, which gives the floor-based scale.
   The frequency is Poisson, set so that the expected count of losses of EUR 20,000 or more is 0.82 (the LDCE median per EUR billion of
   assets) times the EUR 50 billion of assets of the synthetic bank: 41 a year. The statistics are derived-only; the documents carry the
   four medians and their source (BCBS 160, Table ILD7) and no other cell of the tables. The fit is a calibration, not a claim: medians of
   per-bank percentiles are not the percentiles of any bank, and the largest log error of each fit is in the document.
2. **The truth** (`truth.py`). The compound Poisson of the severity, every loss at or above the floor, whatever the collection threshold.
   Its 99.9 percent quantile is computed once by the engine's Fourier aggregation on a grid of 2^21 points (step EUR 1,000 or more),
   cross-checked by the engine's Panjer recursion on a coarser grid (within 0.1 percent) and by a Monte Carlo of 10^7 simulated years of the
   generator (within three standard errors). A tail index of 1 or more has no mean: none is computed.
3. **A replication** (`generator.py`, `replicate.py`). A history is a pure function of its seed: Poisson counts, GPD amounts by the
   engine's inverse cdf, then the labels (date, event type, business line). The bank records the losses at or above its collection threshold
   and nothing below; the rows pass the `loss_events` family of contract 1. The recorded losses go through the engine:
   rung 1 the Poisson-lognormal LDA that ignores the threshold (Monte Carlo of 200,000 years), rung 2 the lognormal truncated above the
   threshold with the frequency rescaled (Panjer, and the Fourier aggregation of the same grid for the agreement), rung 3 the lognormal body
   and GPD tail splice at a fixed EUR 100,000 (Fourier), rung 4 the single loss approximation on a truncated GPD
   fit, rung 5 the same with the mean correction (labelled UNVERIFIED, undefined where the fit has a tail index of 1 or more), rung 6 the
   scenario combination (the splice whose tail is the Bayesian credibility Pareto, Panjer). The grid of rungs 2, 3 and 6 ends at four times
   the single loss approximation of the fit, grown while it does not reach the quantile. The tail-index profile is the GPD fit above
   1, 2, 4 and 8 times the collection threshold. The standardised approach is `sma_capital` on the annual recorded losses with the 5-year
   minimum, at the business indicator of the synthetic bank (EUR 1.4 billion, bucket 2, BIC EUR 180 million from stated three-year
   components through the engine's OPE25 functions).
4. **The scenario points** (`replicate.scenario_points`, `scenario_prior`). The expert states the true severity quantile of eight
   exceedance frequencies (four a year down to one in two and a half years), rounded to two significant figures, and the true frequency of
   losses above EUR 100,000 rounded to two figures; the prior is the unrestricted Gamma on the Pareto shape (decision D4) with the bootstrap
   redrawing each frequency as Poisson over the years of the history (decision D6). The prior is the expert's: it is computed once per
   variant and number of years and reads no loss of any history; the bootstrap seed is the first of 0 to 99 whose 100 refits all lie inside
   the engine's search bounds (the engine refuses a bound as a statistic). The scenario rung updates it with the Pareto data above the
   splice threshold of the history.
5. **Replications and cells** (`bake.py`). Per variant four cells (5 or 10 years by threshold 10,000 or 20,000) of 1,000 independent
   histories, seeds `case_seed x 100,000 + 1,000 + 1,000 x (variant x 4 + cell) + k`, disjoint across the 16 cells. Cells are cached by
   variant, plan and source hash. The cell summaries (percentiles of the capital, ratio to the truth, share underestimating, dispersion) are
   `validation.oprisk.capital_stability`; the ILM and ORC are percentiles of the engine's per-history values.
6. **Single-history blocks** (`extras.py`). The SMA response: one large loss (0 to 1 times the BIC) added to the latest year of the first
   history of the 10-year cell, the loss component, ILM and ORC from the engine and the single loss approximation capital of the same history (a splice or lognormal fit of a history with one added loss can degenerate);
   the scenario influence on the first history of the same cell where the rung is defined; Shevchenko's benchmark through the three
   aggregations as a test row.

## Edge cases

A rung the engine refuses on a history (a fit that did not converge, a splice whose lognormal body degenerates to a body weight of 1, a grid that
never reaches the quantile) is NaN for that history and reduces `n_defined`; no number stands in for it. The engine's maximum likelihood fit of a truncated lognormal to Pareto-like data (a tail index near or above 1) can run to a
degenerate maximum (a mean of minus several hundred thousand and a scale of several hundred, flagged converged); the engine then refuses the
rescaling or the aggregation, and the bake counts the history as undefined without filtering any fit the engine accepts. A history with fewer than 20 recorded losses is a
failed replication. A tail index of 1 or more writes no mean, no mean-corrected rung and no expected shortfall.

## Out of scope

The engine, the views (U12-W), readiness and the index, the catalog, CHANGELOG.md and VERSION.
