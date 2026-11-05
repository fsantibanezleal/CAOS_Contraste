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

Since U16-P2 (BL-091, BL-075) C22 covers every p-value test the installed engine registers, 42 of them: the 21 of the five
credit families (discrimination, PD calibration, rating system, stability, transitions), drawn here from the generators of
the case's own scenarios, and the 21 of the other seven families (counterparty credit risk, IFRS 9, LGD and EAD, market,
portfolio, fairness, machine learning), which come from the engine's named studies, `riskvalidation.generators.size_studies.STUDIES`
(U16-E2): for each test a null generator at the boundary of the test's null, one stated alternative, seeds and the fixed
arguments of the test, 25 studies in all (the tail back-test has two levels, the dynamic quantile test four sample sizes).
C22 writes no simulation of its own for them (ADR-0069): it runs each study through `simulate_study`, the engine's one entry
point, with its own repetitions and a seed of its own, in worker processes (`pipeline/cases/c22_studies.py`; a repetition
depends on its seed and its index only, so the pool changes no byte). The bake stops, naming the test, when a registered
p-value test has no study, when an optional extra of the engine (arch, fairlearn, mapie, statsmodels) is not installed,
and when a repetition yields no p-value; nothing is skipped silently. Until the engine's 1.0.0 the studies come from the
branch `task/u16-e2` of `fsantibanezleal/CAOS_RiskValidation` (commit 1c379a6, over the pinned 0.9.0); the integrator re-bakes
C22 on the 1.0.0 release, and the artifacts record the engine version they were drawn with.

## The variants

Severity runs from 0 (the null) to 5. The ladders are Contraste's design choices, set from pilot runs so that the
targeted tests' power runs from their size to near one at the variant's sample size; each ladder is printed with its
unit on every view.

| Variant | Generator | Severity ladder (unit) | Tests measured | Published reproduction |
|---|---|---|---|---|
| `null` | one per test, its null at the boundary; for the 21 tests of the other seven families, the null of the engine's named study | none: every test at its null | every registered p-value test (42) at 5% and 1% (4,000 repetitions), p-value histograms; Hosmer-Lemeshow with G - 2, the traffic lights with the upper tie rule, the chi-square over a thin grade; estimator performance of the AUC and its ECB standard error; the engine's documented excess (`portfolio.mc_convergence`) with its measured excess and its page | none |
| `miscalibration` | `DefaultCounts` (portfolio and grades), `LogisticPortfolio` (`calibration_intercept = -ln k`) | true PD = k times the PD applied: 1, 1.1, 1.25, 1.5, 2, 3 | binomial, Jeffreys, Vasicek-corrected (exact and simulated), chi-square over grades, default profile, Hosmer-Lemeshow, Spiegelhalter, normal, traffic lights | none |
| `clustering` | `DefaultCounts` with asset correlation; `LogisticPortfolio(rho)` | asset correlation: 0%, 2%, 5%, 10%, 15%, 20% (PDs right) | the same calibration tests: their true size when defaults are correlated | WP14 Tables 7 and 8 (144 cells, 25,000 runs); WP14 Figure 9 grid (exact) |
| `drift` | `TwoSample` (n = m = 1,000); `LogisticPortfolio(shift)` | mean shift of the current population: 0, 0.05, 0.1, 0.2, 0.3, 0.5 standard deviations | PSI (benchmark, 0.10 and 0.25 rules), CSI, chi-square, Kolmogorov-Smirnov; Hosmer-Lemeshow and Spiegelhalter under covariate shift with a right model | Yurdakul and Naranjo Table 4 (54 cells, 10,000 runs) |
| `discrimination-decay` | `BinormalScores` (150 defaulters, 4,850 survivors, development AUC 0.80) | AUC drop: 0, 0.01, 0.02, 0.03, 0.05, 0.08 | AUC against the development AUC; DeLong against a challenger with the same drop; the development AUC estimated on samples 1, 4 and 16 times the current | none |
| `leakage` | `BinormalScores(leak)` | the leaked feature's shift for defaulters in development: 0, 0.25, 0.5, 1, 1.5, 2 | AUC against the development AUC, CSI of the leaked feature | Demler et al. (nested discriminants, 1,000 runs) and the non-nested null |
| `broken-monotonicity` | `Migrations` (7 grades, 500 and 2,000 obligors per grade); `DefaultCounts` with two grades' PDs moved towards each other's | planted cell / closer neighbour: 1, 1.25, 1.5, 2, 3, 4; swap of grades 3 and 4: 0, 0.2, 0.4, 0.6, 0.8, 1 | migration z-tests; default profile, chi-square over grades | none |
| `concentration` | `GradeFrequencies` (10 grades, 5,000 obligors, development sample 5,000) | share moved into the modal grade: 0, 1%, 2%, 5%, 10%, 50% | ECB concentration test (HHI), chi-square of homogeneity on the counts; the ECB statistic's curve (exact) | none |
| `other-families` | the engine's 14 generator classes of the named studies (`PfeSeries`, `StageTransitions`, `LgdCalibration`, `DownturnLgd`, `EsResiduals`, `LhpLossRates`, `McQuantile`, `CreditRiskPlusSample`, `ThresholdBiasPlant`, `VarHits`, `EsLosses`, `PitSeries`, `CovariateShiftPlant`, `ExchangeabilityBreakPlant`) | departure: 0 (the test's null) and 1 (the one alternative the engine states for it): two points per study | the 21 p-value tests outside the credit families, 25 studies, each against its stated alternative | none |

Repetitions: 4,000 for the null sizes, 2,000 per severity elsewhere (Monte Carlo SE at most 1.1 points), the published
numbers of runs for the reproductions. Seeds: one per (variant, test, severity), derived from the case seed, recorded.

The `other-families` design: a `Study` of the engine holds a null generator and an alternative generator, not a departure as
a parameter, so no severity ladder of 0, 0.5, 1, 1.5 and 2 times the stated departure applies to any of the 25, and each is
measured at two points, the null (severity 0, the rate is the test's size at 2,000 repetitions) and the stated alternative
(severity 1, the rate is its power); every row says so in its `study.departure` (`two-point`). Building a scaled generator
of the case's own would be a scenario the engine does not name (ADR-0069). The studies whose rule is not p < alpha (the
back-tests' red light, the Monte Carlo p <= 0.05, the light that is not green) carry their own rule's rate beside the rates
at p < 0.05 and p < 0.01 taken from their p-values, so every row of the null variant has the same two levels.

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
  (a key of `generators`), and `study` (c22-variant 2.0.0): null for the credit families, else the engine's named study
  behind the row: its `index` among the test's studies, `label`, `rule` (`p`, `p_le`, `red` or `alarm`) and `rule_label`,
  `arm` (`null` or `alternative`), `text` (what the arm is), `departure` (`null` or `two-point`) and `excess`, the
  engine's documented excess or null. The `excess` block (`c22Excess`) holds the engine page and repository that state it,
  the level, the measured size, the bound, the excess (measured minus bound), whether it exceeds in this run and the
  engine's statement, in both languages; today `portfolio.mc_convergence` (1.55% at 1% against a bound of 1.49% in the
  engine's run), shown whether or not this run exceeds. A key is the test id with `#index` from the second study of a test
  on, then `@null` (null variant) or `@d0` and `@d1` (other-families).
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
  each. The models artifact (c22-models 2.0.0) also records the engine's 25 named studies in `fit.studies`: the test, the
  generators of the null and of the alternative, the pipeline that runs the test where it is not the test itself, the
  fixed arguments, and the engine's own repetitions and seeds.
- **Validation**: Power (every panel of the family at once, one small multiple each: rejection rate against the
  severity per test, its exact curve dashed, the nominal level dotted; a panel of designs rather than a ladder, the
  nested and non-nested DeLong designs, is a small table), Rates (every rate of the family with its panel, SE, Wilson
  interval, scenario and exact value), Size (the null family: every test's size with its Wilson interval and the
  bound), p-values (histograms under the null, one small multiple per panel: 14 panels since U16-P2, the six of the credit
  families and eight of the others, the documented excess listed under the size table), Estimators (the AUC's bias, SEs and
  coverage), Papers (the published reproductions, cell by cell), One report (the registered tests on one specimen
  dataset).
- **Impact**: the live calculator's curves (rejection probability against the true-to-applied ratio and against the
  correlation, for the reader's portfolio), and the family's decision numbers.
- **Findings**: each finding with its cited rates, numbered, beside a chart of those rates with their Wilson intervals
  against the level.
- **Variants**: the families side by side, which test sees which defect: a row per test, each cell its rate at the
  family's highest severity, blue where it is power, amber where it is a false alarm (the null column's sizes, the
  size panels), darker for a higher rate; a column header loads the family. A family whose panels are all size panels
  names its Validation tab Size and says the model is right. A row per study of the null family; the Other families
  column is a test's power at 5% against the engine's stated alternative, blank for the credit families' tests.
- **Context**: the sources with their licence classes, the generators' row, the truth status and the case write-up.

## Docs

`docs/cases/C22.md` (the case page: question, variants, ladders, results, findings, what not to claim); the web's
Methodology gains a Size and power part (the rate and its error, the exact rejection probabilities, the published
simulations rerun, what a measured size does not say) and its Discrimination, Calibration and Stability parts state
what the measurements changed; Experiments shows the eight families and the size of every test, Benchmark which test
sees which defect and the reproductions, every number read from the artifacts.
