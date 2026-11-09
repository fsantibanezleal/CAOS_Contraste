# Predictions fixed before the ORE replicate runs

Written on 7 November 2026, before `exp_ore_replicates.py` was run for any variant, and kept unchanged afterwards. The
manuscript reports each as held or not held.

Context at the time of writing. The committed reconciliations (`data/derived/C12/*.json`) and the experiments
`exp_printed.py`, `exp_routes.py`, `exp_closedforms.py` and `exp_committed.py` had been run. A pilot of four repetitions of
`exp_criterion.py` had been run: it showed that the standard error of the product's per-date difference treats the paths of an
antithetic pair as independent, so the standardised differences of two runs of the same model have a spread near 0.6 and not 1.
The 400-repetition run of `exp_criterion.py` was started after that pilot, so no prediction about its outcome was fixed in advance.

The predictions below concern the repeated engine-against-ORE comparison on new seeds (engine: 20,000 paths, ORE: 10,000
samples, seed 5000 + r for both, r = 0 to 23 for the uncollateralised variants and r = 0 to 7 for the 10-day CSA variant).

* **R1.** For the single swap and the netting set, the mean over repetitions of the standardised difference z at each of the 33
  report dates lies within 0.5 of zero (no systematic gap between the two engines), and the mean over the dates of the means lies
  within 0.25 of zero.
* **R2.** With the product's standard errors (paths treated as independent) the standard deviation over repetitions of z, taken at
  its median over the report dates, is below 0.8 for both variants; with pair-aware standard errors on both sides it lies between
  0.8 and 1.2.
* **R3.** The pass rate of the product's rule (every z within 2, EEPE and CVA within 2) over the 24 repetitions is at least 50 %
  for the single swap and for the netting set.
* **R4.** For the 10-day CSA variant, the rule fails in every one of the 8 repetitions, and the mean over repetitions of the largest
  |z| exceeds 5 (the committed gap of 9.9 combined standard errors is not a property of one draw).
* **R5.** For the 10-day CSA variant, the CVA z is below -5 in at least 7 of the 8 repetitions (the committed value is -15.9).

## Amendments after the review of 7 November 2026

Nothing above this line was changed. The review found two things about this file, and one comparison was added.

* **R2 was written after a pilot.** The context paragraph above records that a pilot of `exp_criterion.py` had already shown a
  spread near 0.6 for two runs of the engine before R1 to R5 were written. R2 therefore restates that result for a second pair
  of engines (the engine and ORE) and tests whether it transfers; it is not a blind prediction.
* **The order of the commit cannot show when the predictions were fixed.** The file and every `results_ore_*.json` entered the
  repository in one commit. Only the modification times of the files order them, and they are consistent with the predictions
  coming first.

Predictions for `exp_maxt.py`, written on 7 November 2026 after the review and before that script was run for the first time. The
script repeats the 400 paired runs of `exp_criterion.py` with the same seeds on five of its seven conditions and adds two rules:
the largest of the 35 standardised differences against the 95 % point of the largest absolute value of a Gaussian vector with the
covariance of the 35 differences under the null, estimated on the other half of the repetitions (the maximum-T bound).

* **M1.** With the product's errors the maximum-T rule has a size between 3 % and 8 % on both variants, and with pair-aware errors
  the same.
* **M2.** The maximum-T rule with pair-aware errors rejects a 2 % volatility error on the netting set in at least as many
  repetitions as the pair-aware rule at the bound 3.18 (76.5 %), because the 35 comparisons are strongly dependent and the bound
  3.18 is conservative for them.
* **M3.** The maximum-T rule with the product's errors rejects a 2 % volatility error in fewer repetitions than the one with
  pair-aware errors, because the product's errors overstate the sampling error.
