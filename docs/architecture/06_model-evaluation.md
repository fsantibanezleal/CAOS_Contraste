# The validation and evaluation design

`stages/evaluate.py` runs, for each rung and each variant, the tests of `riskvalidation` (dossier 06, section C)
under its versioned policy; nothing in the pipeline re-implements a statistic. What the stage decides is the design:

- **Which sample each test reads.** Discrimination, calibration and stability are measured on the variant's
  evaluation set, never on the training or calibration slices. The "initial validation" AUC of the ECB comparison is
  the AUC on the calibration slice, the development's first out-of-sample measurement.
- **The master scale.** Twelve geometric grades (upper bounds 1% x 1.5^k, then 100%); a grade's PD in the grade-level
  tests is the mean PD of the obligors the rung maps to it.
- **The references of the stability tests.** PSI of each rung's PD against the training slice, on ten bins of its
  quantiles, with the chi-square benchmark of Yurdakul and Naranjo beside the conventional bands; CSI of every input
  against the training slice; the grade concentration against the calibration slice.
- **The asset correlation** of the Vasicek-adjusted binomial test: the QRRE value of the Basel framework, R = 0.04
  (CRE31.15).
- **What is not run, and why.** Migration matrices and their tests, the multi-period normal test and the traffic
  lights need several periods; C01 is one snapshot, so the page says so instead of showing them.

**Segments.** A test on the whole evaluation set is reported for the segment `portfolio`, a grade-level Jeffreys
test for its grade, a CSI row for `characteristic:<name>`.

**Findings** follow the case's severity policy: a red test of the PD's level (Jeffreys, binomial, Vasicek-adjusted
binomial) of the champion or the challenger is S2 and an amber one S3; a red test of the fit across the range
(chi-square over grades, Hosmer-Lemeshow, Spiegelhalter) is S3 and an amber one S4, because at thousands of obligors
these reject deviations too small to matter; stability and discrimination tests are S2 when red and S3 when amber; the
design limits (no out-of-time sample) are S3 and the data-quality flags S4, both accepted.

**Known truth.** The perturbed variants say what each test should do: under covariate drift with P(default | x)
unchanged, a calibrated model stays calibrated and the PSI flags the shift; under a prior shift every level test
rejects; under label noise discrimination falls. The C01 bake checks the strongest of these as expected ranges.
