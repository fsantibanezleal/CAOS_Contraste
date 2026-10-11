# Tasks: U1, case C01 (retail cards PD, champion vs challenger)

| # | Task | Requirement | State |
|---|---|---|---|
| 1 | Readers for UCI Taiwan and the German twin through contract 1 (codes outside the codebook flagged, protected attributes kept out of the inputs) | CT-001 | done |
| 2 | The leakage-safe split: a locked stratified holdout of 30%, a disjoint calibration slice, five stratified folds repeated twice | CT-101, CT-102, CT-103 | done |
| 3 | The ladder P0 to P5 (optbinning and statsmodels scorecard, L1 and PLTR, EBM, monotone LightGBM with the XGBoost cross-check, TabPFN v2 as an optional extra), every machine-learning rung calibrated on the calibration slice | CT-108, CT-110 | done |
| 4 | The battery of riskvalidation 0.1.0 on every rung and variant, the per-group discrimination, the impact at an approval rate, the findings under the case's severity policy | CT-109 | done |
| 5 | Seven variants with their truth status, expected ranges checked at bake time | CT-111 | done |
| 6 | The live scorers (points table, EBM) held to the pipeline, and policy lights re-computed with the engine's rule | CT-104, CT-105 | done |
| 7 | The case page, the framework cards and the guides, from the dossiers | - | done |

## Convergence verdict (2026-10-05)

Converged. The canonical bake reproduces itself exactly (two bakes, identical values); the 68 pipeline tests, the 59
web tests and every guard pass; the expected ranges hold on every variant. Open for later units: out-of-time
validation needs a dataset with a time axis (finding F-OOT, by design here); TabPFN runs only where the optional extra
is installed.
