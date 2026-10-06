# Design: U3, case C22, validating the validator

Requirements: [`requirements.md`](requirements.md). Parent: [`../../SDD.md`](../../SDD.md) sections 4 and 5.
Sources: research dossier 12 (U3: Morris, White and Crowther 2019; BCBS WP14 pages 41 to 67; Yurdakul and Naranjo
2020; Demler, Pencina and D'Agostino 2012; Brown, Cai and DasGupta 2001), dossier 08 section G (generators and the
truth labels), and the generator and test pages of `riskvalidation` 0.3.0, which hold the formulas, the exact
rejection probabilities and the published reproductions.

## The question

A validator reads p-values every day. How often does each test reject a model that is right (its size), and how often
does it catch a model that is wrong in a given way (its power)? Which tests see which defects, which see nothing, and
which raise false alarms when their assumptions fail? With real outcomes none of this is measurable, because the truth
is unknown; on generators whose truth is known, all of it is.

## Data and inputs

No external data: every variant is drawn from `riskvalidation.generators` with its configuration and seed committed in
the artifact (truth status `synthetic-known-truth`, dossier 08 G.4). The registry needs no source; the lineage names the
generators.

## The variants

Severity runs from 0 (the null) to 5. The ladders are Contraste's design choices, set from pilot runs so that the
targeted tests' power runs from their size to near one at the variant's sample size; each ladder is printed with its
unit on every view.

| Variant | Generator | Severity ladder (unit) | Tests measured | Published reproduction |
|---|---|---|---|---|
| `null` | one per test, its null at the boundary | none: every test at its null | all 15 p-value tests at 5% and 1% (4,000 repetitions), p-value histograms; Hosmer-Lemeshow with G - 2, the traffic lights with the upper tie rule, the chi-square over a thin grade; estimator performance of the AUC and its ECB standard error | none |
| `miscalibration` | `DefaultCounts` (portfolio and grades), `LogisticPortfolio` (`calibration_intercept = -ln k`) | true PD = k times the PD applied: 1, 1.1, 1.25, 1.5, 2, 3 | binomial, Jeffreys, Vasicek-corrected (exact and simulated), chi-square over grades, default profile, Hosmer-Lemeshow, Spiegelhalter, normal, traffic lights | none |
| `clustering` | `DefaultCounts` with asset correlation; `LogisticPortfolio(rho)` | asset correlation: 0%, 2%, 5%, 10%, 15%, 20% (PDs right) | the same calibration tests: their true size when defaults are correlated | WP14 Tables 7 and 8 (144 cells, 25,000 runs); WP14 Figure 9 grid (exact) |
| `drift` | `TwoSample` (n = m = 1,000); `LogisticPortfolio(shift)` | mean shift of the current population: 0, 0.05, 0.1, 0.2, 0.3, 0.5 standard deviations | PSI (benchmark, 0.10 and 0.25 rules), CSI, chi-square, Kolmogorov-Smirnov; Hosmer-Lemeshow and Spiegelhalter under covariate shift with a right model | Yurdakul and Naranjo Table 4 (54 cells, 10,000 runs) |
| `discrimination-decay` | `BinormalScores` (150 defaulters, 4,850 survivors, development AUC 0.80) | AUC drop: 0, 0.01, 0.02, 0.03, 0.05, 0.08 | AUC against the development AUC; DeLong against a challenger with the same drop; the development AUC estimated on samples 1, 4 and 16 times the current | none |
| `leakage` | `BinormalScores(leak)` | the leaked feature's shift for defaulters in development: 0, 0.25, 0.5, 1, 1.5, 2 | AUC against the development AUC, CSI of the leaked feature | Demler et al. (nested discriminants, 1,000 runs) and the non-nested null |
| `broken-monotonicity` | `Migrations` (7 grades, 500 and 2,000 obligors per grade); `DefaultCounts` with two grades' PDs moved towards each other's | planted cell / closer neighbour: 1, 1.25, 1.5, 2, 3, 4; swap of grades 3 and 4: 0, 0.2, 0.4, 0.6, 0.8, 1 | migration z-tests; default profile, chi-square over grades | none |
| `concentration` | `GradeFrequencies` (10 grades, 5,000 obligors, development sample 5,000) | share moved into the modal grade: 0, 1%, 2%, 5%, 10%, 50% | ECB concentration test (HHI), chi-square of homogeneity on the counts; the ECB statistic's curve (exact) | none |

Repetitions: 4,000 for the null sizes, 2,000 per severity elsewhere (Monte Carlo SE at most 1.1 points), the published
numbers of runs for the reproductions. Seeds: one per (variant, test, severity), derived from the case seed, recorded.

## Outputs (contract 2, `outputs.kind = "validator"`)

- `family`, `ladder` (`values`, `label`), `levels` (0.05, 0.01), `panels` (`id`, `label`, `axis`: the x axis of a
  panel whose simulations do not run along the family's ladder, the swap of two grades' PDs and the current sample
  over the development sample, null otherwise; `measures`: `power` where the family plants a defect the panel's
  tests should see, or `size` where the tested model stays right and only an assumption fails, so a rejection is a
  false alarm: every panel of the null and clustering families, drift's calibration panel, the development AUC
  estimated with nothing changed, the DeLong designs of equal AUCs),
  `size_bounds` (per rule).
- `simulations`: one row per (test, scenario, severity): `key`, `test_id`, `label`, `scenario`, `panel`, `severity`,
  `x` (the setting on the panel's axis), `rates` (per rule: rejections, n, undefined, rate, se, wilson_low,
  wilson_high), `exact` and `agrees` (per level, or null), `p_histogram` (null variant), `seed`, `n_rep`, `generator`
  (a key of `generators`).
- `generators`: each generator's name, frozen configuration and exact truth.
- `golden`: the published reproductions (`bcbs-wp14`, `yurdakul-naranjo-2020`, `demler-2012`), each cell with
  published, measured, z and agrees, the counts and a note.
- `exact_curves`: exact curves computed without simulation: WP14's Figure 9 grid (the true confidence of a 99.9%
  binomial test under correlation) in the clustering variant, the ECB concentration statistic against the current CV
  in the concentration variant. The live calculator's parity points and the Gauss-Hermite rule are in the case's
  models artifact (`X1-exact`).
- `estimators` (null variant): the AUC's bias, empirical SE, ECB SE and interval coverage; the ECE of right PDs.
- `specimen`: the severity of the specimen dataset.

`tests`: the registered tests on one specimen dataset (severity 0 in the null family, severity 3 elsewhere:
what each test says about one sample, the lights under the committed policy). `impact`: decision numbers, each
`value, unit, label` (for example the true size of the binomial test at a 12% correlation, the PD underestimation the
portfolio Jeffreys test detects with 80% power).
`findings`: severity S1 to S4 with `rate:` evidence (CT-305).

## Lanes

Simulations are `precompute` (minutes of repetitions); the web replays them. The exact size and power of the count
tests are `live`: TypeScript ports of the binomial tail, the one-factor mixture tail (the 256-node Gauss-Hermite rule
committed in the case's models artifact) and the Jeffreys posterior (a regularised incomplete beta), held to the
engine within 1e-9 on exported parity points (CT-308).

## The web instrument

Rail (two sections, sized to fit a 1280 by 800 screen without scrolling, ADR-0071 rule 6): **Your portfolio**
(obligors, PD applied, the true-to-applied PD ratio, the true asset correlation) and **The tests** (the level, 5% or
1%, which every replayed view reads; the correlation the Vasicek-corrected test assumes). Both hold the live read-out of
the three count tests' exact rejection probability for the portfolio, which changes with every control of either
section. The committed policy is not a control here: every rate is a rejection rate at a level, not a light. Groups:

- **Model**: the generators of the family: configuration and exact truth (arrays summarised), the tests measured on
  each.
- **Validation**: Power (every panel of the family at once, one small multiple each: rejection rate against the
  severity per test, its exact curve dashed, the nominal level dotted; a panel of designs rather than a ladder, the
  nested and non-nested DeLong designs, is a small table), Rates (every rate of the family with its panel, SE, Wilson
  interval, scenario and exact value), Size (the null family: every test's size with its Wilson interval and the
  bound), p-values (histograms under the null, one small multiple per panel), Estimators (the AUC's bias, SEs and
  coverage), Papers (the published reproductions, cell by cell), One report (the registered tests on one specimen
  dataset).
- **Impact**: the live calculator's curves (rejection probability against the true-to-applied ratio and against the
  correlation, for the reader's portfolio), and the family's decision numbers.
- **Findings**: each finding with its cited rates, numbered, beside a chart of those rates with their Wilson intervals
  against the level.
- **Variants**: the families side by side, which test sees which defect: a row per test, each cell its rate at the
  family's highest severity, blue where it is power, amber where it is a false alarm (the null column's sizes, the
  size panels), darker for a higher rate; a column header loads the family. A family whose panels are all size panels
  names its Validation tab Size and says the model is right.
- **Context**: the sources with their licence classes, the generators' row, the truth status and the case write-up.

## Docs

`docs/cases/C22.md` (the case page: question, variants, ladders, results, findings, what not to claim); the web's
Methodology gains a Size and power part (the rate and its error, the exact rejection probabilities, the published
simulations rerun, what a measured size does not say) and its Discrimination, Calibration and Stability parts state
what the measurements changed; Experiments shows the eight families and the size of every test, Benchmark which test
sees which defect and the reproductions, every number read from the artifacts.
