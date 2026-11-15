- C06 and C08: loan-level bootstrap intervals beside the pre-registered verdicts of the S-4 comparison (PC-Hazard against Cox at each reporting
  date) and the S-5 benchmark (the better of the random forest and the neural network against each of the six earlier rungs, per test cohort).
  The out-of-time accounts (C06) or defaults (C08) are resampled with replacement, 1,000 times with the seed of the bake, the predictions held
  fixed (the interval is the sampling noise of the comparison, not the uncertainty of the fits); each difference of the integrated Brier score and
  of the mean absolute decile gap (C06) or of the RMSE (C08) carries the 2.5 and 97.5 percentiles of its replicates, null with its reason where a
  rung is not fitted or a date has fewer than 30 defaults. The documents count how many of the dates or cohorts where the hypothesis holds have
  an interval that excludes zero; the verdicts are unchanged. One shared helper (`pipeline/cases/bootstrap.py`); the integrated Brier score of
  every replicate is the engine's `lifetime_pd_backtest`. Contracts `c06-models` 2.0.0 (`fit.s4_bootstrap`) and `c08-outputs` 4.0.0
  (`outputs.ml_benchmark`), `api` 37.0.0 (a newly required property is breaking by the ADR-0080 floor, so major, not the minor the brief named);
  requirements CT-518 to CT-520 and CT-918 to CT-920; the PC-Hazard and Models views and both case pages print each interval beside its
  difference and the count, in English and Spanish.
