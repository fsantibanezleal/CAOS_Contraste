# Determinism and the artifacts

**A bake is a pure function of the inputs and the seed.** Every random choice draws from a generator seeded from
the case's seed (`data-pipeline/pipeline/core/rng.py` and the seeds passed to every engine: the split, the folds, the
binning solver, the penalised fits, the EBM, LightGBM with `deterministic` set, XGBoost, the resampled variants, the
bootstraps). The manifests carry no wall-clock time, so a second bake of the same release leaves git clean, and the
committed artifacts are the evidence the web merely shows.

**What an artifact holds** (contract 2, [08](08_data-contracts.md)):

- a models artifact per fit (`data/derived/<case>/models-<fit>.json`): the record of every rung, its engine,
  version, licence, parameters with units, calibration map and internals (the scorecard's points table and bins, the
  EBM's shape functions, the GBM's partial dependence, PLTR's rules), with the split and the training metadata;
- a variant artifact per regime (`data/derived/<case>/<variant>.json`): the outputs the views draw (ROC and CAP,
  calibration by grade, reliability before and after calibration, score distributions, cut-off curves, discrimination
  by group with each group's ROC, 50 scored applicants for the parity test), the `TestResult` rows of the battery, the impact, the findings,
  the provenance and the lane.

**Precision.** Numbers are written with nine significant digits to keep each artifact near the trace budget, except
the values a live computation must reproduce: the rungs' internals (`details`, `calibration`) and the scored sample,
which are written exactly, since the parity test holds the live scores to 1e-9 (CT-105). A C01 variant artifact is
215 to 254 KB and a models artifact 48 to 123 KB, all under the 256 KiB trace budget; every C01 artifact is replayed.
