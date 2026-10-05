# Changelog

All notable changes to this product. Versions are X.XX.XXX (VERSION is the single source); every release is
tagged.

## [0.02.000], 2026-10-05

Unit U2, its first case: C05 end to end.

### Added

- Case C05, low-default portfolios and PD calibration. Tasche (2013) and Pluto and Tasche (2005) are read from their
  arXiv PDFs (derived-only); each reader checks its tables against their own print and refuses the bake otherwise,
  and every printed cell is recomputed with `riskvalidation` 0.2.0 with its gap recorded (CT-201 to CT-203). The 2009
  S&P curve is carried to 2010 and 2011 by every approach of the paper's section 4 and tested by its Monte Carlo
  default-profile chi-square; the most prudent bounds (independent, correlated, scaled, over five years) run on the
  paper's example; a seeded Vasicek generator (20,000 years) measures coverage, size and power (CT-204, CT-205). The
  IRB capital of every curve and estimate states its regime, LGD, maturity and floor (CT-206); expected ranges are
  checked at bake time and no S&P grade count is published (CT-207, CT-208). Six variants.
- The C05 instrument: live TypeScript ports of the IRB risk weight, the most prudent bounds, quasi moment matching and
  the four case 1 approaches, held to the engine within 1e-9 on exported parity points (CT-209); rail sections with
  live read-outs and the six groups (CT-210), among them what the confidence level costs in capital and a comparison
  of the variants of each kind; C05's sections of Experiments and Benchmark; the case page and the guide to
  calibrating a PD curve and estimating low-default PDs.

### Changed

- `riskvalidation` 0.2.0 (tag `v0.02.000`). C01's artifacts changed only the engine and code versions in their
  lineage.
- The web on `@fasl-work/caos-app-shell` 0.7.2 (0.7.1 and 0.7.2 on npm since 2026-10-05): tiny p-values in scientific
  notation, the workbench rows that no longer shrink, a key under every chart of several series, integer axes that
  tick only at integers (C01's AUC across the variants repeated its labels). C05's own chart key, the bridge for the
  missing one, is gone.

### Fixed

- Two guides named a local machine path, which failed the guards job on develop.

### Base

- The residue guard and its tests are those of CAOS_PRODUCT_TEMPLATE 0.02.004 (template PR #14, not yet tagged):
  its immunisation marker matched the hyphenated finding id `F-SCALED-COVERAGE`. `.template-version` names 0.02.003
  until the tag exists.

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
