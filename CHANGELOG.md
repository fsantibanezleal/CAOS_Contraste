# Changelog

All notable changes to this product. Versions are X.XX.XXX (VERSION is the single source); every release is
tagged.

## [0.01.000], 2026-10-05

The first release: units U0 (the contracts, the sources and their licences) and U1 (case C01 end to end, the web).

### Added

- Contract 1: eight ingestion families (scored sample, loan panel, rating history, market series, curve, balance
  sheet, loss events, macro path), each record accepted, rejected, flagged or excluded with its reason, never
  coerced; exported to `data/derived/contract/` and mirrored by the web (CT-001, CT-004).
- The source registry (49 sources, four licence classes, the verbatim fragment of each licence), the fetcher with
  a licence manifest that pins the SHA-256 of every file, a data root outside the repository, and the lineage that
  refuses to publish an artifact built on a link-only or unusable source (CT-002, CT-003, CT-008 to CT-011).
- Case C01, retail cards PD, champion vs challenger: the ladder P0 to P5 (optbinning, statsmodels, scikit-learn,
  interpret, LightGBM, XGBoost, TabPFN v2 as an optional extra), the leakage-safe split, isotonic calibration on a
  disjoint slice, the battery of `riskvalidation` 0.1.0 on every rung and seven variants, the impact at an approval
  rate, the findings under a severity policy, and expected ranges checked at bake time (CT-101 to CT-111).
- `data-pipeline/validate.py`: contract 1 and the battery on a reader's own scored sample, with two known-truth
  examples in `data/examples/` (CT-012 to CT-014).
- The web on `@fasl-work/caos-app-shell` 0.7.1: the App workbench (Model, Validation, Impact, Findings, Variants,
  Context), the five documentation routes, the architecture modal, live scorers held to the pipeline to 1e-9 and
  live policy lights (CT-105, CT-112 to CT-114).
- Guards: licences of the default install, data classes, provenance, the SDD, content standards; the docs wiki
  (architecture, frameworks, cases, guides).

### Base

- On CAOS_PRODUCT_TEMPLATE 0.02.003 and the shell 0.7.1, whose fixes this product's first gate run found.
