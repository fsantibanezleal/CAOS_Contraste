# The staged pipeline

`data-pipeline/run.py` (invoked by path; the product declares no package) exports the contract-1 declarations, bakes
every case of the registry and writes the index. A case module (`data-pipeline/pipeline/cases/`) composes the named
stages:

| Stage | Module | What it does for C01 |
|---|---|---|
| ingest | `stages/ingest.py` | checks that the case may read the source (the registry), that the file on disk is the one the licence manifest pins (its SHA-256), reads it (`io/readers.py`) and passes it through contract 1 with the case's features and rules |
| split | `stages/split.py` | a locked stratified holdout (30%), a calibration slice (20% of the rest), the training slice, and repeated stratified five-fold folds inside it |
| fit (preprocess, feature extraction, train) | `cases/c01_ladder.py`, `model/` | every rung on the training slice: binning and WoE, the penalised fits and PLTR's rules, the EBM, the monotone GBMs, TabPFN on the small case; the calibration maps on the calibration slice |
| infer and evaluate | `stages/evaluate.py` | each rung's PD on each variant's evaluation set; the battery of `riskvalidation`; the curves and tables the views draw |
| export | `stages/export.py`, `core/manifest.py`, `core/lineage.py` | the models and variant artifacts through contract 2, refused if the lineage is not publishable; the gate verdict on the bytes written |
| validate | `core/expect.py` | every named result against the range the case declared before the bake; the bake fails on one outside it |

A bake of every C01 fit and variant takes about 12 minutes on a workstation (the Taiwan ladder about 3.5, PLTR's
cross-validation the longest part). Run a sandbox bake with `--output <dir>`; the canonical bake, which writes
`data/derived/`, is a release operation.
