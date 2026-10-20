# Design: U14-P1, case C02 (corporate PD across the 1 to 5 year horizons on the UCI Polish bankruptcy files)

Status: live. Unit sizing `plans/contraste/units/U14-sizing.md` (CAOS_MANAGE), decisions Q9, Q10, Q14, V6 and G18. Contracts: `c02-outputs`
and `c02-models` (`docs/contracts/schemas/c02/`), `engine-ml-api` (the engine at the pinned commit is binding where the page on this
branch, 1.0.0, differs), `engine-provisions-api`, `contract-family-scored_sample`.

## Question

How fast does discrimination fall from the 1-year to the 5-year horizon, do the learned rungs beat the scorecard by a margin a paired test
supports, and do they stay calibrated? Six documents: the five horizon files and the pooled variant (the five stacked with a horizon
indicator, decision Q9), each with a locked holdout, the C01 ladder, the battery per rung and three exploratory blocks.

## What is real and what is a convention

The rows are the UCI Polish Companies Bankruptcy files (CC BY 4.0, DOI 10.24432/C5F600), read from the device data root. Nothing else
is invented. The conventions, all labelled so in the documents:

- the horizon of a document is the dataset's own definition (decision G21): the UCI page labels the file kyear with the bankruptcy
  status after 6 - k years, so h{n} (n years ahead) reads the file {6-n}year. Each document states its file beside its horizon; the reading
  of the source paper is UNVERIFIED (finding `F-PAPER-READING`, `conventions.MAPPING_NOTE`);
- contract 1 needs an identity and a date the files do not carry: `id = <horizon>-<row>` and `observation_date = 2013-12-31`, the end
  of the span the page gives. No out-of-time claim and no temporal order rests on the date;
- the overfit tolerance 0.05 AUC points (decision V6, the only named parameter the case uses);
- the missing-indicator share (5 percent), the bootstrap size (1,000 resamples), the grade distance (2 notches) and the loss given
  default of the Impact block (45 percent, an assumption).

## The protocol (dossier 04 l.1054-1059)

1. A locked stratified holdout of 30 percent of each file, a calibration slice of 20 percent of the rest, the training slice, repeated
   stratified folds inside the training slice (`pipeline.stages.split`, the C01 stage, unchanged).
2. Imputation (the training median) and the missing indicators (ratios missing in at least 5 percent of the training slice) are fitted
   on the training slice only and applied unchanged elsewhere (`prep.py`).
3. The ladder is `cases/c01_ladder.fit_ladder` unchanged: calibration maps on the calibration slice, no resampling.
4. The pooled variant is the union of the five slices (its holdout is the union of the five locked holdouts), with `horizon_years`.

## The battery

Per rung (P0 single variable, P1 scorecard, P2a L1, P2b PLTR, P3 EBM, P4 LightGBM and XGBoost) on the holdout: AUC with the DeLong
interval (`disc_auc`), KS, Hosmer-Lemeshow (`fitted=False`), Brier, ECE with its bins (the reliability diagram: bins with equal mean PD
merged, the Wilson interval of the engine), the PSI of the PD and the CSI of every input against the training slice, the overfit gap
(`overfit_gap`, `validation.ml.overfit`), the Jeffreys and binomial level tests. The descriptive figures (AUC, KS, Brier, ECE) are the
`outputs` of the rung; the `tests` carry only rows with a light or a p-value, because the contract refuses a `not_evaluated` row with a
number. The constant PD is fitted and recorded in the models document and has no battery: a constant has no risk groups.
The challenger table compares each learned rung with P1 (`disc_delong`, `paired_brier_bootstrap`, `grade_disagreement`).

## The exploratory blocks

- Transfer: the rung fitted on the document's file, scored on the locked holdout of each file. Empty for the pooled variant.
- Term structure (decision G22): the five file event rates as a cumulative PD through `from_cumulative`, with the `lifetime_pd_backtest` row of the
  champion's mean PD on each holdout, when the rates rise strictly with the horizon. Under the dataset mapping (G21) they fall (6.94 to 3.86 percent):
  the files are independent samples of different forecast years, so the block is null with `term_structure_reason` (`c02-outputs` 1.1.0) and there is no back-test row.
- Impact: the 12-month and lifetime ECL of one unit of exposure (`ecl_scenario`, undiscounted) under the horizon PDs (the five file event rates). Under
  the dataset mapping the rates fall with the horizon and cannot form a term structure, so the block is null with its reason (`reason_if_null`).

## Out of scope

The engine, the views, the registries, the readiness and the index. A P5 TabPFN challenger (dossier 04 l.969).
