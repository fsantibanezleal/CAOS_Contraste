# Design: U14-P2, case C20 (ML model validation: drift, robustness, explanation stability)

Status: live. Unit sizing `plans/contraste/units/U14-sizing.md` (CAOS_MANAGE), decisions Q5 to Q8, Q10, C5, G1 to G4, G13, G18, V1 to V6.
Contracts: `c20-outputs`, `c20-outputs-shift`, `c20-outputs-seeds`, `c20-outputs-perturbation`, `c20-outputs-leakage`, `c20-models`
(`docs/contracts/schemas/c20/`), `engine-ml-api` and `engine-fairness-api` (`docs/contracts/engine/`), `contract-family-scored_sample`.

## Question

Do performance, drift, attribution and reason-code stability survive shocks the model has and has not seen, shifted populations, input
noise and retraining seeds, and does the leakage screen catch a planted leak? Six variants answer it on a locked holdout, with synthetic
shifts on the evaluation set only. The case validates models; it certifies none, and nothing in it is a statement about any lender.

## The engine is binding

`docs/contracts/engine/ml-api.md` on this branch is 1.0.0, and its 2.0.0 amendment is written in parallel (decision G18). Where the page
and the engine at the pinned commit (`3767a3d`, `data-pipeline/requirements.txt` and the engine row of the SDD technology table, checked by
`tests/engine_pin.py`) differ, the engine wins. The bake uses the signatures of the engine: `conformal_coverage(sets, y, alpha, *, n_cal)`
(the Beta-Binomial p-value drives the light and the binomial p-value of the dossier sits beside it), `shift_development_reference(...)`
with 199 permutations and `validation.ml.shift_resilience(model_id, result, reference)`, the CBPE row always `not_evaluated` with the estimate in
`extras`, the reason codes as the signed attribution on the log-odds of default, and the `ml.` rows of the packaged default policy.

## What is real and what is a convention

Real: the labels and the features of the UCI Taiwan and Polish files, the 1,000 SGCD records and their shipped shocks, the 600 Fed loans.
Everything else that shapes a number is a convention, named in the document that uses it or in the page:

- the data: SGCD is the stressed German credit data (SantanderAI, commit `8403fa9`, CC BY 4.0); its records are the UCI German applicants
  (930 of the 930 complete records match a UCI row), so the German model is never fitted on the UCI file as a whole. It is fitted on the
  setup and adaptation batches (S1 to S4 and A1 to A10, 700 records, F1 nulls included) with a calibration slice taken from them, and scored
  on the locked test batches (T1 to T6, 300 records). The Taiwan and Polish models follow C01's stratified 70 / 30 split with a 20 percent
  calibration slice of the development part;
- the models: the C01 ladder rungs of `cases/c01_ladder.py`, read and never changed; the validated rung is the P4 LightGBM rung, and the seed
  sweep adds the XGBoost rung (the two boosted-tree learners with a random training and a TreeSHAP attribution);
- the shipped SGCD shocks reach a model that reads the structured view alone through F1 only, in 70 of 1,000 records (addendum H4); the
  applied block (`shocks.py`) applies each family to the structured view with the metadata's probabilities, fields and seed 42, with the
  stated conventions (F2 replaces one or two categorical fields by the modal setup code and does not apply `f2_core_weight`, whose core field
  set the metadata does not list; F3 leaves the structured view unchanged; F4 sets one of its five fields to an adjacent codebook code; the
  numeric noise rounds the duration to 6 months and the amount to 500 DM);
- the drift of a shock row: the PSI of each input on ten quantile bins of the setup batches, the CSI on five (the engine documents the CSI as
  the PSI of one characteristic, so the two bin sets are what tell them apart), the chi-square p-value, and the PSI and chi-square of the score
  on the setup deciles as engine rows;
- the Fed probes: the PSI, CSI, KS and chi-square of every loan variable between the portfolios, no model (reading a); and the portfolios
  as the size of a synthetic shift (reading b): the Polish ratios cannot be matched to the Fed variables, so the PSI of the rating between the
  typical and the higher-risk portfolio is the anchor, and the shift adds a mean displacement, in robust standard deviations, to the five
  features the model leans on most, in the direction that raises its PD, solved so that the PSI of the model's raw score on its baseline
  deciles is 0.25, 0.5 and 1 times the anchor. The raw score is used because the isotonic map is a step function whose plateaus make a PSI on
  deciles jump; the labels never move;
- the windows of the conformal coverage are the baseline and the three shifted sets, because the Polish files carry no date; CBPE reads the
  calibrated PD of the one-times shift;
- the perturbation: the engine's noise at 0.05 to 1 standard deviation on the evaluation features, a coded feature read as the nearest code, and
  a control curve that keeps every exact zero at zero;
- the leak: the default flag plus Gaussian noise of 0.2, dated one month after the observation date; at decision time its values are permuted
  across the holdout rows; the holdout stands in for the out-of-time sample in the resemblance screen, and a clean control is screened beside it;
- the cut-off of the Impact block: the PD that declines the worst 20 percent of the baseline decisions of the variant's model, held fixed;
- the fairness battery: sex, three marital groups and four age bands (under 30, 30 to 39, 40 to 49, 50 and over) on the Taiwan model; the
  decision is the PD at or above the cut-off, so the true positive rate is the share of defaulters the cut-off declines.

## The pipeline fits, the engine computes (ADR-0069)

The pipeline reads the sources, fits the rungs, computes the TreeSHAP attributions with the pinned `shap` 0.52.0 and hands arrays and callables
to `riskvalidation`: perturbation, shift score and worst subsample, the development-only permutation reference, the split conformal sets and
coverage, CBPE, the seed dispersion, the grade and rank stability, the reason-code overlap, the rank agreement, the accumulated local effects,
the overfit gap, the weak spots, the leakage screens, the data-quality counts, the stability tests and the four fairness tests. The product
writes the segment and the model id of a row and nothing else (`ops.row`). The cross-field checks are `tests/contracts_u14/semantics.py`
`check_c20`, run on every document before it is written, with the schema of every result row.

## Missing data

A source that is not in the data root stops the variants that need it (`fetch.missing_for`): the SGCD files stop the two shock variants and
the Fed files the shift variant, they are named with their URLs and nothing is written for them. A shock row without both classes has no AUC
and is not written. The Fed portfolios carry no outcome and no decision, so they cannot pass contract 1 as it stands (`scored_sample` asks a
decision of a sample that declares no outcome): the reader checks the layout itself (open question in the report).

## Resources

The full bake takes about five minutes and 840 MiB of peak working set on the default device (measured in the report); a subsample bake of the
tests takes about a minute. No bake runs in CI (ADR-0074).
