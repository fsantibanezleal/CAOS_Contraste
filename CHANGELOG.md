# Changelog

All notable changes to this product. Versions are X.XX.XXX (VERSION is the single source); every release is
tagged.

## [0.06.000], 2026-10-09

The base moves to the shell 0.10.0 and the template 0.03.001 (CAOS_MANAGE `plans/app-shell/rollout-0-10.md`, #12).

### Changed

- The web runs on `@fasl-work/caos-app-shell` 0.10.0, pinned exactly (from 0.9.3). It carries known shell defects 32
  and 33, which the 0.9.3 gate failed on this product: a 1e-6 tick on a log axis of PDs read `1E-4 %`, and the active
  chip under the pointer wrote its label at 3.04:1.
- The template's guards are 0.03.001's, verbatim (they were 0.02.004's, unchanged): the web-baseline guard requires
  an exact pin equal to the installed package, judges each rule of the product's CSS by its subject against the
  shell's reserved classes, and fails a shell entry imported without its stylesheet; the version guard reads code, not
  history. The build writes `build.json` in `writeBundle`, so a failed build reports its own error.
- Every view row is the shell's `ViewsRow` (60 rows in C01, C04, C05 and C22). The product's own column wrapper
  (`.ct-col`, `.ct-share-2`, `.ct-share-3`, `.ct-findings-*`) is gone; the shell's column has the same box and the
  same stacking below 900 px, and takes the shares as a prop. A split that depends on the screen is read in the
  script, since a product's media query cannot reach the shell's column: the findings views give the drawing two
  thirds from 2000 px wide, and C04's Variants view draws the agencies' chart on a screen at least 1100 px tall.
  Two cards that split one column's height (C04's families) are `.ct-part`, a layout the shell does not have.
- C04's matrix map measures and fits its labels with the shell's text kit (`textWidth`, `fitLabel`) instead of a
  canvas of its own: the two lines of column labels are a label's box apart (16 px; 12 px left the boxes overlapping
  by 3 px in the wide font), a label has two columns of room on its line, and one still wider is shortened with an
  ellipsis and carries its name as a title. The clip paths and the `textLength` squeeze of 0.05.000 are gone.

### Kept, and why

- The knob's range without side margins in the product's control blocks: CAOS_APP_SHELL#91 is open in 0.10.0 (known
  shell defect 35).
- Card notes cite papers by their authors: a note is a string the shell cannot mark (CAOS_APP_SHELL#87, open).
- Reference levels drawn as dashed constant series (a test's nominal size, the policy's amber and red thresholds, no
  bias, one default): 0.10.0's `yMarks` draws every line dotted in the warning colour and leaves out a line beyond
  the data's range, so the red threshold would read as amber and a nominal level as an alarm (CAOS_APP_SHELL#94).

### Fixed

The gate measured every state without a failure, but its captures show each route's first view only. Every view of
the App was captured and read (130 views: light in English and dark in Spanish at 1280 x 800, light in English at
390 x 844, page by page), and showed what a reader could not use, all of it before this release:

- C04's Drift for an agency kept a plot of 10 to 30 px for the projection and for the mix by grade over the table.
  The mix sits beside the projection on a screen at least 1100 px tall; the mix and the table, which show shares of
  the balance and not a PD, close with CEREP's line without ESMA's statement on definitions.
- C04's Definitions left the definitions' table one row under the cohorts where tab 2 differs from tab 4. That card
  shows on a tall screen; elsewhere the chart's note points to the By year view, the chart and the definitions share
  the row equally, and the chart (ratios of definitions, not PDs) closes with CEREP's line, ESMA's statement heading
  the definitions beside it.
- C04's Findings for the papers stacked a short table over its drawing and left the drawing no plot. It stacks only
  on a tall screen, and the chart's axis title fits its height ("Gap to the print").
- The Markov family's rail scrolled at 1280 x 800 in Spanish: six estimator chips take three rows there and pushed
  the read-outs past the rail. The estimators have a rail section of their own.
- C22's small multiples kept a plot of 30 px under a key of eight series: a row of panels is at least 320 px and the
  grid scrolls inside its card; on a phone they are one to a row.
- C04's matrix map left a cell blank where its value with its unit did not fit, which read as no data, and on a
  phone printed its zeros only. It prints every value or none, without units when only that fits (the header then
  carries the unit).

### Known

- In Spanish at 1280 x 800, C04's agency charts keep plots of 50 to 90 px under their notes (PD by grade, Lifetime,
  Findings): a filling card gives its note all the height it asks for. The notes carry what CT-407 requires; the
  fix belongs to the shell, a floor for the stage (CAOS_APP_SHELL#95). Every chart keeps its read-out and its table.

### Verified

- `npm test`: 468 tests in 22 files (three new for the short-screen layouts, one for the matrix map's units); `tsc`;
  `npm run build`.
- `pytest`: 175 passed with `CONTRASTE_DATA` set (the CEREP and paper tests read the data root), 1 skipped (a
  template-only guard); `ruff check`.
- Every CI guard, the template 0.03.001 guards among them: web baseline, version coherence, artifacts, provenance,
  data classes, licences, SDD, deploy place, template residue, document paths, content standards, CI budget.
- `caos-shell-gate` on the release build: OK, 910 measured states (C01, C04, C05 and C22; five sizes, both themes,
  both languages, the wide-font pass), 0 failures.
- The 130 captures above, read; the rails of every C04 variant measured in both languages and both fonts at
  1280 x 800 (none scrolls).

## [0.05.000], 2026-10-08

Unit U4: case C04, rating transitions and TTC PD by grade.

### Added

- Case C04 reads ESMA's CEREP for the EU entities of S&P, Moody's and Fitch (corporate long-term ratings, annual
  cohorts 2000 to 2025, semesters from 2010): 361 answers fetched through CEREP's own interface, paced, cached in the
  data root and pinned by hash, every table carrying "Source: ESMA CEREP; tables transformed by Contraste" and the
  agency's entity (CT-401, CT-407). The reader puts each agency's labels on one scale of seven grades and keeps CEREP's
  default counts apart: the default page's distinct defaulted ratings (D2), the defaults page's events (D3), the
  transition page's default column (D4) and that column with withdrawals kept in the denominator (CT-402). ESMA sets
  no common definition of a default event for CEREP, and every PD shown names its definition.
- Three agency variants (CT-403, CT-404, CT-415): the long-run average PD by grade under each definition (EBA/GL/2017/16
  paragraph 84) with the Wald, Agresti-Coull and Jeffreys intervals of the pooled rate; the pooled one-year matrix; the
  EM, diagonal, weighted and JLT generators with Israel, Rosenthal and Wei's embedding diagnostics; time homogeneity
  across years and semesters, every cohort against the pooled matrix, the ECB migration statistics; mobility; two
  semesters against the year; and the lifetime check of every five-year window. Measured: the transition matrix's
  default column gives 29% of the default page's CCC to C PD for S&P and 19% for Fitch (Fitch's default columns hold no
  rating in the years 2006 to 2014, while its default page counts 189 rated defaulters there; every view built on that
  column says so); Moody's page has no default category; S&P's CCC to C cohort of 2020 lived 61.4% defaults in five
  years where its chained annual matrices give 9.1%.
- Five generator families on riskvalidation's `RatingPaths`, from the EM generator of S&P's counts (synthetic known
  truth, CT-405): the Markov null (the estimators' bias and RMSE by grade with their Monte Carlo errors, the zero
  PDs, the four transition tests' size, the intervals' coverage), momentum calibrated to dos Reis et al.'s estimate
  (alpha 0.125 fits c 0.34; theirs is 0.33), a recession year, informative withdrawals and thin cohorts. A bias and a
  projection error are differences of probabilities and read in percentage points.
- Published answers recomputed by the engine from the papers in the data root, derived-only (CT-406): Israel,
  Rosenthal and Wei's distances (8 of 9 to the printed digits, the ninth only from the printed generator),
  Schuermann and Hanson's Table 5 (all twelve bounds with 15 defaults of 531) and Engelmann's section 4 (the TTC
  portfolio and its PD, 1.198%; W hat within the rounding of its printed entries, the reason stated in both languages).
- The live tools (CT-410, CT-411): a portfolio's projection under the one-year matrix towards its TTC portfolio
  (Engelmann 2024), the three intervals at a reader's default correlation and level, and the IRB risk weight of the
  cohort mix under each definition (Keep's from the mean of its yearly rates) and generator; the TypeScript port
  equals riskvalidation on the models artifact's parity points within 1e-9, and the tests check what each live and
  published chart draws against the ports and the artifacts.
- The C04 instrument (CT-412): the agency, family and papers views, the rail's Grade, Projection and Interval sections
  with their live read-outs; the findings with their cited p-values, rates or design blocks drawn and the years the
  findings name marked; the Methodology's Transitions part; C04's sections of Experiments and Benchmark; the case page
  with its results.
- Case C22's null family adds the four rating-transition tests on riskvalidation's size-study chain: 19 of its 21 tests
  hold their size at 5% and 1% (finding F-TRANSITION-SIZE), the order test measured again over 20,000 repetitions.
- Guide 07: PDs by grade from rating transitions on your own history, and what to check before using them.

### Changed

- The engine is pinned to riskvalidation 0.04.003. Building C04 found what the base lacked, and each piece was fixed
  and released upstream first: 0.04.001 floors a PD of exactly zero where the regime has a floor (it refused one, so
  every caller applied the floor itself, a second copy of the regime's value; an agency's AAA that never defaulted is
  the case the floor exists for); 0.04.002 adds the MSE and RMSE with their Monte Carlo errors and the exact coverage
  and overlap of the PD intervals, which C04 had computed itself; 0.04.003 refuses a non-finite rate in `RatingPaths`
  (a NaN rate made a draw run without end) and records that the order test's size depends on the chain. C01 and C05
  change only in their engine and policy versions.
- C01 reads TabPFN's weights from the models root, never the user's home directory: the cache setting is applied
  before TabPFN is imported, and the rung refuses to fit without a checkpoint there.
- The web is on the shared shell 0.9.3, pinned exactly (ADR-0078 section 5): the views row, the marks, the number
  formats, the rail's knobs and the gate's checks G1 to G14. Building C04 found four shell defects, each fixed in the
  shell first: a calendar year was written 2,021 on an axis or in a readout (known shell defect 30, the `grouping`
  option, in 0.9.0); a log axis reaching below about 1e-22 was never drawn (defect 31, shell 0.9.2: uPlot threw on
  C04's p-values of 1e-124); a value on the scientific boundary read 1E-4 % as a percent of 1e-6, and turned a whole
  log axis of PDs scientific (defect 32); and the active chip under the pointer wrote the text colour on the accent,
  3.04:1 (defect 33, found by the 0.9.3 gate on every rail section it clicks). Defects 32 and 33 are in the shell
  0.9.4, tagged and not yet on npm: on 0.9.3 the gate fails G13 wherever it hovers an active chip, and on the 0.9.4
  build it passes, so the release to main waits for 0.9.4 on npm. C04's year axes are calendar years; every p-value
  below 1e-16 is drawn at 1e-16 with its exact value in the table, a reading choice (C01 draws the same floor).
- Stale pages brought up to date: the live lane's architecture page and the Implementation page list every case's
  live computations, the Introduction describes each case's rail, the cases index lists C04 and C22.

### Fixed

What the shell 0.9.3 gate found across the site, on its first run here:

- A Spanish page wrote decimal points (G11): C01's scorecard bins now read in the page's number format (a Spanish
  interval separates its bounds with a semicolon) with the special bins named, the rules are code, and why a feature
  left the scorecard reads in the page's language; the equation, section and theorem numbers that the Methodology and
  the case pages cite are marked as references (`Ref`), the notes cite papers by their authors (a note is a string the
  shell cannot mark, CAOS_APP_SHELL#87), and licence identifiers, the sources' verbatim attributions, C22's paper cells
  and quoted passages are kept as written.
- C04's rail scrolled at 1280 x 800 (ADR-0071 rule 6) and its colour bar's lowest tick was cut (G10).
- CT-407 held unevenly: every card drawn from CEREP now closes with one line (the EU entity, its code, the scope, the
  period and ESMA's attribution), and every card that shows a PD carries ESMA's statement.

What the gate found on the shell 0.9.4 build, after the release commit and before the merge into develop:

- G5 at 390 and 768 px: the knob's range input keeps the user agent's 2 px side margins at width 100%, so in a card
  body that clips it reached past the edge (CAOS_APP_SHELL#91); the product's control blocks set no side margin.
- G10 in the wide font: C04's matrix map printed column labels and cell values wider than their cells. It measures
  them in the page's font: a value prints only where it fits, and column labels too wide for their column alternate
  between two lines.
- ADR-0071 rule 6 in the wide font: C04's and C05's rails scrolled at 1280 x 800; their variant lists leave out the
  variants' titles and C04's interval read-out writes one percent sign for its two bounds.
- The develop CI (Node 22) drew C04's PD axis from 9.999999999999999e-6 where Node 24 gives 1e-5, since `10 ** -5`
  differs between them; the axis decades are read as `1e-5` and so on.

## [0.04.000], 2026-10-06

Unit U3: case C22, validating the validator.

### Added

- Case C22 measures the size and power of every test with a p-value that Contraste has built, on riskvalidation's
  known-truth generators (synthetic known truth; the engine is pinned to 0.03.002, whose Wilson interval is exact at
  zero rejections, a defect this case found). The null family gives each of the 17 tests its rejection rate
  at 5% and 1% from 4,000 repetitions on data where its null holds at its boundary, with the Monte Carlo SE, the Wilson
  interval, the p-value histogram and the size bound (CT-301); seven defect families (miscalibration, default
  clustering, drift, discrimination decay, leakage, broken monotonicity, concentration) give the power of the tests
  each targets at severities 0 to 5 (CT-302). Where a rejection probability is exact (the count tests, the traffic
  lights) it is committed beside the simulated rate, and every rate agrees with it within 3.29 SE (CT-303).
- Three published simulation studies are rerun from the tables read out of their PDFs (derived-only): BCBS WP14
  Tables 7 and 8 (143 of 144 cells), Yurdakul and Naranjo Table 4 (50 of 54 with this case's seed, the harness sitting
  slightly above the paper on average, the offset stated), and Demler, Pencina and D'Agostino's nested design (2
  rejections in 1,000 at 5%, their 0.001) (CT-304). Findings cite measured rates as their evidence (`rate:`), and the
  contract refuses one that names no simulation of its artifact (CT-305).
- The live calculator: the exact size and power of the binomial, Vasicek-corrected binomial and Jeffreys tests for a
  reader's portfolio, in the browser, held to the engine within 1e-9 on parity points that span the rail's knobs to
  their corners (CT-308); a full set of curves costs about 10 ms at any portfolio size; the C22
  instrument with its rail, groups and views (CT-309).
- The web's Methodology gains a Size and power part, and its seven parts are grouped by the reader's question (the
  models and their risk; the validation tests), the shell's limit being six peers; Experiments shows C22's families
  and the size of every test, Benchmark which test sees which defect and the reproductions.
- The Findings group of every case draws its evidence beside the table: C01's cited p-values on a log scale against
  the policy's thresholds, C22's cited rates with their Wilson intervals against the level, numbered as in the table.

### Changed

- C01's Hosmer-Lemeshow test on the holdout uses as many degrees of freedom as groups, the PDs being fitted on other
  data (CT-312): with G - 2 the test rejects right PDs about one time in nine at 5% on such samples. The champion's p
  on the holdout moves from 0.005 (red) to 0.015 (amber).
- C01's test of the AUC against the initial AUC adds the variance of the calibration slice's AUC, an extension of the
  ECB formula the result states (CT-313): with the slice's AUC taken as known the test rejects about one time in six
  at 5% when nothing changed. The holdout's LightGBM finding on discrimination is gone (p 0.026 to 0.132); German
  twin's LightGBM moves from red to amber.
- C05's generator is riskvalidation's `DefaultCounts`; every C05 number is unchanged (CT-311).
- The Methodology's Discrimination, Calibration and Stability parts state what the measurements changed: the AUC
  test's development variance, the degrees of freedom of Hosmer-Lemeshow on validation data, and the bounded ECB
  concentration statistic.

## [0.03.000], 2026-10-05

U2's second part: C01's IRB capital.

### Added

- C01's Impact group has two views, Decision and Capital. Capital gives the IRB capital (8% of the RWA) of the
  champion's and the challenger's approved books at the rail's approval rate and LGD under Basel III final, EU CRR3
  and Basel II, in money and as a share of the EAD, and the capital against the approval rate (CT-212). The Taiwan
  cards are qualifying revolving retail, every card a revolver: Basel III defines a transactor by twelve months of
  repayment history (BCBS d424, standardised paragraph 56, IRB paragraph 25) and the data hold six; counting the
  six-month full payers as transactors is reported as a sensitivity (CT-214). The German loans are other retail.
- The pipeline sums riskvalidation's capital requirement at unit LGD over each rung's cut-off curve (CT-213); the web
  multiplies by the rail's LGD, exact for the retail functions, and the TypeScript retail functions are held to the
  engine on exported parity points within 1e-9 (CT-215). A rail LGD below the Basel III input floor (50% for QRRE,
  30% for unsecured other retail) is flagged (CT-216).

### Changed

- At 80% approved, LGD 50% and Basel III, the monotone GBM's book needs 4.2% less capital than the scorecard's on the
  holdout; Basel II asks 6% more than Basel III and CRR3 the same. C05's artifacts changed only their code version.

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

- On CAOS_PRODUCT_TEMPLATE 0.02.004 (tag `v0.02.004`), whose two guards this product's C05 work found wrong; both are
  copied verbatim with their tests. The residue guard's immunisation marker matched the hyphenated finding id
  `F-SCALED-COVERAGE`; the doc-path guard judged the disk, so it passed here and failed the develop CI on two docs
  naming the gate's screenshot folder (`frontend/gate-output/shots`, ignored on purpose).

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
