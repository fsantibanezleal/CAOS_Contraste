# Changelog

All notable changes to this product. Versions are X.XX.XXX (VERSION is the single source); every release is
tagged.

## [0.11.001], 2026-10-15

Shell 0.14.3 and the CI base-integrity guard. No case, artifact or contract changes.

- Shell 0.14.3 (pinned exactly, lock file included). In Focus mode the stage label no longer covers the open group's
  controls. The live 0.11.000 showed it on C10 at 1280 x 800: "Portfolio credit capital: ASRF, Vasicek fit, copula MC"
  wrapped to two lines over the sub-tab row (Fitted distribution, Correlation, Back-test, Against IRB). The rail inside
  Focus no longer shows the Focus button. The shell's gate G18 fails both defects now.
- The CI base-integrity guard reads `git ls-files` once and runs every test on a here-string. Under `bash -eo pipefail`,
  `git ls-files | grep -q` failed at random: grep exits on its first match, git ls-files dies of SIGPIPE and the pipeline
  reports 141. That made the guard report a tracked `.env` once on main. A real `.env` used to pass whenever a root
  `.env.example` was tracked; any `.env` other than an `.example` file fails now. `tests/test_guards.py` runs the step
  itself on planted trees.
- The index and the readiness restamped for 0.11.001 (`pipeline.pipeline index`, `pipeline.pipeline readiness`).
## [0.11.000], 2026-10-15

Wave 2 batch 2: five new cases built on public data or a known truth, C10 (portfolio credit capital on the Federal Reserve charge-off rates), C11 (market VaR and ES back-testing across 2008, 2020, 2022 and 2023), C13 (FRTB desk eligibility with planted model deficiencies), C14 (IRRBB, six shocks on the balance sheet of the bank that failed in 2023) and C17 (operational risk, LDA against SMA); 14 of 22 cases built. The engine is riskvalidation 0.7.0, the shell 0.14.2 (flip cards, the card carousel, animated illustrations, Focus mode for the App).

- Engine `riskvalidation` 0.7.0 (tag v0.07.000, with the `market` extra that brings `arch` 8.0.0): one release of the reviewed portfolio, market, IRRBB and operational risk modules, pinned in `data-pipeline/requirements.txt`; the case pin tests accept the tagged line with its extra.
- Every new case (C10, C11, C13, C14, C17) is baked again on the released engine with VERSION 0.11.000 and proved identical to its first bake but for the version stamps: `scripts/compare_rebake.py` (new, tested) allows only the code and engine stamps and the document's own size moving by exactly their byte change.
- The contract catalog holds the U7, U8, U10 and U12 rows with their history (`api` 4.0.0; `engine-irrbb-api` 1.0.0 then 1.1.0); the built contracts of C10, C11, C13, C14, C17 and the four engine contracts are real; C15 stays on its fixture until the BCCh account works.
- The licence manifest pins every raw file the new cases read (FDIC BankFind, the Treasury par curve 1990 to 2023, the Federal Reserve charge-off page, the Kenneth French daily factors, the H.10 euro page); the provenance check accepts C10's constructed illustrative portfolio (class `illustrative`, outside the source registry, no files).
- A test family's own labelled policy keeps its committed light under the policy rail: C11's market back-tests are evaluated at the reviewed engine-market-api levels (Kupiec, Christoffersen, duration and DQ amber 0.10 and red 0.05, Acerbi-Szekely 0.05 and 0.0001) on which its eligibility gates rest; the rail moves the product policy only, and the label states the family's levels.
- The C10 and C17 descriptors declare the full provenance block; the contract test's schema walker narrows a property by a constraint-only `allOf` member.
- C11's requirement IDs are CT-601 to CT-615 (they repeated C10's); C11 reads its engine pin from `data-pipeline/requirements.txt` for its stamp and its cache key; C10 is registered.
- ruff clean on the U7 and U10 contract tests; full paths in the fragments and the C14 design; the case pages name the engine release.
- Shell 0.14.2 (pinned exactly; 0.14.0 brought the cards, the animation and Focus mode, 0.14.1 put the Focus control on the case select's row so the C04 and C22 rails no longer scroll, 0.14.2 keeps the cause shares whole at phone width): the executive view's four groups of small cards (the bearers, the roles, the state of the art, the 4 C's) flip, the bearers and the roles show as carousels; two state-of-the-art titles (the in-house validation teams and the supervisory guides) are shortened in both languages to fit the flip limit, with the same meaning and source.
- The three Introduction illustrations are animated where they explain a change: the pain (the evidence breaks at each handover, a finding reaches the supervisor, the capital held climbs), the roles (the evidence handed over from role to role, the broken links blinking as it passes) and the proposal (the tests sweep the evidence, each handover passes with its check, the extra capital is released to the planned level); each carries its reduced-motion block that shows the static final frame.
- Focus mode for the App: the rail head offers a Focus button for every case (`?focus=1` beside `?case=` and `?view=`); Escape or the exit button returns to the same case, group and sub-view. The gate runs with `--require-focus`.
- The US Treasury par curve reader is one shared module, `pipeline/io/treasury.py`, used by C11 (one tenor as a daily series) and C14 (whole curves on valuation dates, `curve_as_of`, `history_up_to`); the two copies in `cases/c11/readers.py` and `cases/c14/treasury.py` are removed (U8 and U10 sizing reservation R2). Every value either case reads is identical to before, compared exactly on every year file 1990 to 2023; no document under `data/derived/` changes.
- U10-P1 case C14 (IRRBB, six shocks on the USD balance sheet of the bank that failed in 2023): the real producer of `c14-outputs` and `c14-models` 1.0.0 in `data-pipeline/pipeline/cases/c14/`, replacing the fixtures. The FDIC BankFind financials of Silicon Valley Bank (CERT 24735) at 2021-12-31, 2022-06-30 and 2022-12-31, each read only up to its date, are slotted into the 19 SRP31.96 buckets (each report band spread uniformly over the buckets it overlaps, mortgage items amortising, the non-maturity deposits through the engine's `nmd_split` with the SRP31 Table 4 caps and `cap_applied`), with the US Treasury par curve of each date bootstrapped by the engine. Real aggregates, synthetic behaviour: every behavioural assumption is a named field with its value, unit, source kind and source.
- U10-P1 C14 results: per date the delta EVE under the six shocks, the 2024 and the 2016 calibrations, with and without behavioural NMD (the twelve-row comparison), the EVE risk measure from exactly six shock rows and its outlier test against 15 percent of Tier 1, the repricing gap and duration gap, the delta NII of the parallel shocks, the 12-month dynamic NII with deposit betas, EaR and EVaR at 95 and 99 percent from 100,000 Hull-White one-factor paths with the engine's batch-means Monte Carlo errors, the out-of-sample row (the 2021-Q4 projection against the realised 2022 NII), and the validation test rows of `riskvalidation.validation.irrbb`. Every EVE, NII, shock, test and Monte Carlo error is a `riskvalidation` call; the replicating portfolio, its stability windows and the deposit betas are fitted on the quarters up to each date.
- U10-P1 documents and checks: `data/derived/C14/` (three valuation-date documents, the models document, SHA256SUMS, `raw-sources.txt` with the URL, size, hash and date of the raw files, as rows of `data/sources/manifest.json`), `data/derived/manifests/C14.json`, the case page `docs/cases/C14.md` with its generated results block, the requirement rows CT-1401 to CT-1414 with their adversarial rows under `docs/design/features/c14/`, and `tests/c14/`; `semantics.py::check_document` runs on every document the bake writes. `data-pipeline/requirements.txt` pins the engine by the commit of `task/u10-irrbb` (ed224f3) until the release tag carries `riskvalidation.irrbb`.
- U10-P1 findings for the contract owner and the integrator: the C14 contract carries a single floor number, so SRP31.93's maturity-dependent floor is not applied; a valuation date on a weekend (2022-12-31) has no Treasury curve and carries the last published one, said in the curve `source`, because `dating_violations` requires `curve.date` to equal the valuation date (an `observation_date` field would say it in the schema); the scenario `net_cash_flows` of the contract carry the term-deposit overlay only, so the prepayment multipliers of SRP31.119 are tabled and not applied per shock; the Treasury reader of `cases/c14/treasury.py` is shared with C11 (U8-P1) and is to move to `pipeline/io/treasury.py`; the case is discovered by its `CASE` object, and the index, the readiness and the count tests are the integrator's.
- U10-S contracts: the JSON Schemas of the C14 (valuation-date) and C15 (annex1-variant) case documents and models documents under docs/contracts/schemas/c14 and c15, with plainly labelled fixtures under docs/contracts/fixtures/ that validate by discovery; the 19 buckets of SRP31.96, the SRP31 Table 4 NMD caps (a core share or maturity above its cap validates only with its flag), the shock sizes (a currency without a table entry validates only as a labelled Contraste estimate), the UR currency, the CLP and CLF offset rule state and the indexation charge are required fields, and a C14 document never reads a call report dated after its valuation date.
- U10-S engine contract: docs/contracts/engine/irrbb-api.md (engine-irrbb-api 1.0.0), the signatures, units, invariants, light rules and golden values of riskvalidation.irrbb (curves, shocks, slotting, eve_nii, behavioural, simulation) and riskvalidation.validation.irrbb; the catalog rows are in docs/contracts/rows/U10.md for the integrator to merge.
- U10-S fixes after the Opus review: the schemas fix the order of the six shocks, of the four C14 scenarios, of the 19 buckets with their midpoints, the shock sizes, the models tables and the thresholds (a bucket with another bucket's midpoint, a changed table cell and a tabled currency relabelled as an estimate now fail); an NMD position carries the requested value, the SRP31 Table 4 cap, the used value and cap_applied (a request above its cap validates only with cap_applied true and the used value at the cap); C14 carries the dynamic NII, the EaR and EVaR at 95 and 99 percent and the 2021-Q4 out-of-sample row, C15 the dynamic NII of the CLP and UR legs.
- U10-S producer checks: tests/contracts_u10/semantics.py exposes check_document and dating_violations, the cross-field rules (the dating rule, the recomputed EVE, delta NII, pair, offset state, indexation charge in the C15 delta NII, thresholds) that a bake calls on every document; 94 planted defects are refused by the schema or the checker.
- U10-S engine contract fixes: the weighted_average_maturity golden is 2.3, the eve_sum_of_parts golden uses the exact whole, the bootstrap golden is pinned to multiples of the coupon period, the fit_prepayment_logit golden states its design and a 3 standard error tolerance, the Diebold-Li maximum is 29.446 months, nmd_split returns the document fields (requested, cap, used, cap_applied).
- U10-S engine contract 1.1.0 after the engine review: the new function simulation.ear_evar_mc_error (batch-means Monte Carlo standard error of each EaR and EVaR quantile, with an exact and a closed-form golden) and, in the C14 schema, ear_se and evar_se at each level of ear_evar with mc_error_method and n_batches in place of the single monte_carlo_error; eve_risk_measure takes exactly six shock rows and refuses a transposed matrix; the Annex 1 goldens are checked at the printed precision of Hoja 10.
- U10-W: the C14 instrument (IRRBB on a USD balance sheet, one valuation date per variant): the delta EVE of the six prescribed shocks in currency and as a share of Tier 1 with the convention named, the shock curves, the 15 percent outlier threshold as a line, every result with and without the behavioural deposit assumptions, the replicating portfolios with their stability across windows, the NMD caps with and without the cap, the parameter changes flagged against limit breaches, the repricing and duration gap, the dynamic NII with the out-of-sample row, and EaR and EVaR; built against the c14 contracts and their fixtures.
- U10-W: the C15 instrument (IRRBB on a CLP and UF balance sheet under RAN 21-13 Annex 1): the CLP and UR legs apart, the 50 percent offset on and off, the delta NII as the rate result and the indexation charge kept apart, the CPI-surprise variant, the floors' effect, the prioritised-bank thresholds as lines, the Annex 1 shock sizes with their origin, and the dynamic NII of each leg; built against the c15 contracts and their fixtures, which it shows until the BCCh account exists.
- U10-W: the Methodology section on interest rate risk in the banking book (measures and shocks, the standardised EVE, behaviour and dynamics, the UF and Annex 1), the U10 references and coverage rows, and the run-time descriptors of the c14 and c15 documents.
- U12-P, case C17 (operational risk: LDA against SMA): data-pipeline/pipeline/cases/c17/ is the real producer, a seeded generator of annual operational loss histories for a synthetic bank (EUR 50 billion in assets, 41 losses of EUR 20,000 or more a year, a GPD severity whose scale is fitted by least squares on the log excess quantiles to the BCBS 2008 LDCE median percentiles 27,632, 41,916, 82,608 and 418,400) at the four tail indices 0.6, 0.8, 0.96 and 1.1, with the true 99.9 percent annual loss quantile computed once by the engine (Fourier on 2^21 points, checked by Panjer within 0.1 percent and by 10^7 Monte Carlo years within three standard errors); the data/derived/C17/ documents (four c17-outputs variants, one c17-models, checksums) and data/derived/manifests/C17.json replace the fixtures of docs/contracts/fixtures/c17 and validate against the reviewed c17-* schemas and tests/contracts_u12/c17_semantic.py.
- U12-P ladder: every cell (5 or 10 years of data by a collection threshold of EUR 10,000 or 20,000, 1,000 independent histories each, seeds disjoint across the 16 cells) removes the losses below the threshold before any fit, passes the rows through the loss_events family of contract 1, and estimates the Poisson-lognormal LDA that ignores the threshold, the truncated lognormal LDA, the lognormal body and GPD tail splice, the single loss approximation with and without the UNVERIFIED mean correction, the scenario combination by Bayesian credibility and the OPE25 standardised approach, every capital, quantile, fit, ILM and test from riskvalidation.oprisk and riskvalidation.validation.oprisk; no mean, no mean-corrected rung and no expected shortfall for a tail index of 1 or more; an ILM never on fewer than 5 years.
- U12-P tests and docs: tests/c17/ (calibration, truth, generator, engine calls, documents, determinism, case page, adversarial), requirements CT-1701 to CT-1715 with their design and adversarial validation under docs/design/features/c17/, and the case page docs/cases/C17.md with a results block generated from the committed documents.
- U12-P engine pin: data-pipeline/requirements.txt pins riskvalidation by the commit of CAOS_RiskValidation task/u12-oprisk (3665b51, after the Opus review fixes) until the integrator tags the engine release, then by the tag.
- U12-S contracts: the JSON Schemas of the C17 (operational risk, LDA against SMA) tail-index variant document and models document under docs/contracts/schemas/c17, with plainly labelled fixtures under docs/contracts/fixtures/c17 (a finite-mean variant and an infinite-mean one) that validate by discovery; every document carries the generator's true parameters and the true 99.9 percent annual loss quantile (synthetic-known-truth), a tail index of 1 or more carries the infinite-mean flag and null mean-based fields, the BCBS 2008 LDCE calibration targets carry their source and the derived-only label, and the SMA block names its discretion with a BIC-only basis under 5 years of loss data.
- U12-S engine contract: docs/contracts/engine/oprisk-api.md (engine-oprisk-api 1.0.0), the signatures, units, invariants, light rules and golden values of riskvalidation.oprisk (distributions, aggregate, sla, scenarios, sma) and riskvalidation.validation.oprisk; the catalog rows are in docs/contracts/rows/U12.md for the integrator to merge.
- U12-S contract fixes after the Opus review: `es_from_pmf` refuses a grid that does not carry the tail (`max_missing_share`) and never computes an expected shortfall for a tail index of 1 or more; the Shevchenko benchmark carries the verified Table 2 indices (H at 5847 is 0.998999329, H at 5849 is 0.999000217, quantile 5849) and the Monte Carlo reference 5853.1; the dossier's EUR 647.1 million SLA is reproduced (log excess least squares, xi 0.96378, beta 22349.4) and no longer UNVERIFIED; the credibility prior is the Shevchenko and Wuthrich Pareto-Gamma form with the unrestricted prior (`gamma_prior_from_scenarios`, `credibility_pareto`), stated on every result.
- U12-S schema tightening after the review: the cells are exactly the 2 x 2 cross of years 5 or 10 and collection thresholds 10,000 or 20,000 (an ILM on fewer than 5 years is unreachable), the tail index is one of 0.6, 0.8, 0.96, 1.1, a discretion that sets the ILM to 1 carries an ILM of 1, a truth that fails its Monte Carlo check is refused, `sma_response` rows carry the LDA capital of the same history, `sma_capital` refuses `minimum_years` below 5; the cross-field rules are `semantic_findings` in tests/contracts_u12/c17_semantic.py, the gate of the C17 bake.
- U12-S contract amendments after the engine review: `es_from_pmf` no longer claims its guard refuses a grid at any size (a coarse grid of an infinite-mean tail passes it), so a finite ES or mean is never computed for a severity without a finite mean and the caller checks `severity_moment(..., 1)` before the ES; a scenario-prior interval that reaches the search bound is a stated failure (ValueError, the scenario rung null with its reason), with the precondition `exceedance_frequency * basis_years >= 1`; `benchmark_reproduction` defaults `moment_rel_tol` to 1e-5 (the reference skewness has four decimals).
- U12-W C17 instrument: the operational risk views of the App on the reviewed c17 contracts and their fixtures, in `frontend/src/workbench/c17/`. Four groups (Loss, Capital, SMA, Model) with the Variants and Context views, and a rail of four sections (Years, Threshold, Method, Scenario), each with its control and a live read-out. The exceedance curve of the annual loss is on log-log axes with Monte Carlo, Panjer and FFT overlaid and the true 99.9 percent quantile and the single loss approximation marked; the capital of every rung is always drawn beside the true quantile; the tail-index threshold-stability plot, the capital across the grid of years and thresholds, the scenario influence bars, the SMA against the LDA and the response to one large loss complete it.
- U12-W labels and missing data: a tail index of 1 or more shows the infinite-mean flag and no mean (the mean-corrected SLA is not available, with the document's reason); the mean-corrected SLA carries UNVERIFIED in every place it is named; the LDCE targets are labelled derived-only with their source; the bank is labelled synthetic; a rung the bake did not evaluate and a test that did not run show their reason and no number; no view draws a number the document does not contain.
- U12-W Methodology: the `oprisk` section of the loss group (one `method` section with three parts as sub-tabs: the loss distribution approach with the truncated severity and the body and tail splice, the aggregation by Monte Carlo, Panjer and FFT with the single loss approximation and Shevchenko's benchmark, and the scenarios, the BCBS 2008 calibration targets and the OPE25 standardised approach), transcribed from dossiers 05 (F.1 to F.6, with the 2026-10-13 benchmark erratum) and 01 (F), with three theme-aware figures, captioned equations, one honest callout and 15 references in `frontend/src/content/citations/U12.ts`; the C17 row of the coverage matrix in `frontend/src/content/coverage/U12.ts`.
- U12-W checks: `c17.test.tsx` renders every view from the fixtures in both languages and asserts what each shows (25 tests); `frontend/src/workbench/c17/probe-bars.mjs` walks every group and sub-tab of the case in both variants, languages and themes in the gate's wide font and fails when a bar chart scrolls inside its drawing.
- C10, portfolio credit capital (U7-P): the real producer of `c10-outputs`, `c10-outputs-grid` and `c10-models` 1.0.0. The Vasicek distribution is fitted
  to the Federal Reserve net charge-off rates of five loan types on 1985-2006 and the 2007-2012 tail is placed in it; an illustrative portfolio per loan
  type gets its loss distribution by the six rungs of the ladder (LHP, Gaussian copula, Student-t copula, CreditRisk+, granularity adjustment,
  importance sampling) with Euler contributions; a known-correlation simulator gives the size and power of the correlation estimates. Every number
  comes from `riskvalidation.portfolio` (pinned in `data-pipeline/requirements.txt` by commit 502652b of `task/u7-portfolio` until the release is tagged).
  Case page `docs/cases/C10.md`, requirements CT-1101 to CT-1112, tests `tests/c10/`, documents `data/derived/C10/`.
- U7-S contracts: the JSON Schemas of the C10 (portfolio credit capital) case documents under docs/contracts/schemas/c10: the loan-type variant (outputs.kind loan-type; the Vasicek fit by maximum likelihood and moments with their intervals, the profile likelihood of the correlation, the realised loss rates 1985-2012 with the fit and evaluation windows marked, the 2007-2012 tail back-test, the IRB comparison, the illustrative portfolio, the loss distributions of the eight rungs C1 to C6 with EL, VaR, ES and EC at 99 and 99.9 percent and their Monte Carlo standard errors, the granularity adjustment against the number of names, the Euler contributions and the concentration measures), the correlation-grid variant (outputs.kind correlation-grid; the simulator's known correlation and the exact size and power of the correlation estimates per grid cell) and the models document, each with a plainly labelled fixture under docs/contracts/fixtures/c10 (never published as a result). A quarter missing from the Federal Reserve table is a null rate with its reason, a rung that did not run is a not-evaluated row with its reason, an ES the method does not define is null with its reason, a money block carries its currency, and an illustrative portfolio carries its label and its provenance input.
- U7-S engine contract: docs/contracts/engine/portfolio-api.md (engine-portfolio-api 1.0.0), the signatures, units, invariants, light rules and golden values of riskvalidation.portfolio (portfolio, copula, creditrisk_plus, granularity, importance, euler, asrf_fit) and riskvalidation.validation.portfolio, reusing engines.vasicek and regulatory.irb; the golden delta 4.83 at xi 0.25 and q 0.999 fixes the Gamma factor parametrisation (shape and rate xi, 4.8336), and the items the dossiers mark UNVERIFIED stay marked.
- U7-S catalog rows: docs/contracts/rows/U7.md (c10-outputs, c10-outputs-grid, c10-models, engine-portfolio-api, status active, the fixtures as providers) for the integrator to merge; the regenerated docs/contracts/api.openapi.json and frontend/src/lib/contract.gen.ts add the C10 components, which bumps the api contract to 4.0.0 at the merge.
- U7-S fixes (Opus review of 2026-10-13): the granularity adjustment is a share of EAD (Gordy and Lutkebohmert 2013 eq. 9 and 17), no longer scaled by K*: the document carries `granularity.levels[*]` (`q`, `alpha_q`, `delta`, `ga`, `ga_money`), `k_star` and `k_source`, and per-name `ga` and the recursion's `truth_ga` against the number of names; the API takes `K_i` as an input (`granularity_adjustment(share, k, pd, ...)`, the IRB capital at the regulatory correlation) and offers `k_creditrisk_plus` (eq. 13); the fit and evaluation windows are fixed consts (1985-2006 and 2007-2012), so overlapping or swapped windows fail the schema; the IRB reference enumerates `regime` and `asset_class` and carries `maturity` and `maturity_adjustment` (null for retail), with the same maturity treatment on both sides of the ratio; a rung that did not run carries no diagnostic; a delta band at xi 0.25, series lengths 22 and 40, and Monte Carlo rungs with their scenario counts are schema rules.
- U7-S fixes: the cross-field checks are one importable module, `tests/contracts_u7/c10_checks.py` (`violations(doc)`), which the C10 bake runs on every document it writes (measures, Euler sums and the asymptotic anchor, grid identities, window labels, currencies, IRB and granularity identities); the Euler anchor is renamed `asrf-asymptotic` (the first term of Emmer and Tasche 2005 eq. 2.17) and carries `asrf_var`; the `solve_theta` golden uses the threshold 2/11 and the Student-t joint default is printed 0.001647; every plant of the review table is refused by a named test.
- U7-S engine-review amendments (2026-10-13): `portfolio-api.md` fixes the multi-factor idiosyncratic scale to `sqrt(1 - beta' Sigma beta)` (the loading check uses `beta' Sigma beta < 1`; the old scale gave a marginal PD of 0.060 instead of 0.05 with correlated factors); `measures_from_sample` returns `var_se` and `es_se` None for a sample shorter than `10 * n_batches`; the VaR of a finite portfolio sits above the LHP VaR; `pmf_panjer` is no longer said to return negative entries; the importance-sampling tail estimates divide by the scenario count `S`, never by the realised weight sum.
- U7-W C10 instrument: the portfolio credit capital case on the contract fixtures, ready for the bakes. A loan-type variant has a rail of four sections (Rung of the ladder, Confidence level, Correlation estimator, Group of the portfolio), each with its control and a live read-out, and the groups Fit (fitted distribution with the years of both windows placed in it, the profile likelihood of the correlation with both estimators and their intervals, the 2007-2012 tail back-test, the fitted correlation and capital against the IRB ones), Capital (the loss distribution by rung with the expected loss, the VaR and the expected shortfall marked and their Monte Carlo error beside them and the large homogeneous portfolio drawn dashed and labelled as the infinitely granular approximation; the rungs side by side; the Euler contributions with the asymptotic anchor; the granularity adjustment against the number of names with the CreditRisk+ recursion beside it), Model (the ladder and the illustrative portfolio) and Findings, with the Variants and Context views. A correlation-grid variant has a rail of two sections (Known correlation, Estimator) and the Size and power group, which draws the known correlation against every estimate and gives the exact size and power with their intervals.
  Every view that uses the portfolio says it is illustrative; a rung that did not run, a test that did not run, a null expected shortfall, a null anchor and a year without a rate each show their reason and no number; money in the rail is scaled to one unit per read-out, long lists are one select, and no view prints an internal id.
- U7-W descriptors: `frontend/src/workbench/c10/descriptor.ts` holds the run-time descriptors of the C10 documents (`C10_OUTPUTS_LOAN_TYPE`, `C10_OUTPUTS_GRID`, `C10_FIT`), one key per key of the schemas and tied to the generated types by `satisfies`; the integrator composes them into `contract.types.ts` (`variantKind` for the kinds loan-type and correlation-grid, `modelsKind` for C10, with the narrowed `provenance` of the three schemas).
- U7-W Methodology: `pages/methodology/portfolio-capital.tsx`, one `method` topic in the loss group with three parts (Vasicek and the fit; loss, capital and contributions; copulas, CreditRisk+ and granularity), each with four dense paragraphs, its captioned equations (2, 2 and 3) and a theme-aware figure, one honest callout and 21 references as links, transcribed from dossier 04 (C.4 and H) and dossier 05 (G.4 and G.5) with every unverified item marked; `frontend/src/content/citations/U7.ts` (18 new references; the topic lists 21 with three from the base file) and `frontend/src/content/coverage/U7.ts` (the C10 row).
- C11 (market VaR and ES back-testing across 2008, 2020, 2022 and 2023): the real producer of the `c11-outputs` and `c11-models` documents. Six windows of rolling one-step forecasts on the Kenneth French (derived-only), US Treasury and Federal Reserve H.10 daily series, a ladder of seventeen models over rungs R1 to R9 (R10 recorded as a challenger that is not run), hyperparameters fixed on 1995 to 2003, every number from `riskvalidation.market` pinned to the `task/u8-market` commit with its `market` extra.
- U8-P2 case C13 (FRTB desk eligibility: PLA and desk back-testing): the real producer of c13-models and c13-outputs, a seeded generator of desk hypothetical and risk-theoretical P&L for a two-factor spread desk with a known true risk model and the six planted deficiencies of the SDD (none, missing basis, stale volatility, wrong correlation, omitted factor, time misalignment), 250-day windows and 1,000 independent replications per variant (one seed per replication, disjoint ranges per variant), every Spearman, KS, PLA zone, desk exception count and test row returned by riskvalidation.market; the committed documents replace the C13 fixtures, pass the producer checks of tests/contracts_u8 and are listed by the manifest with their hash.
- U8-P2 case page and gates: docs/cases/C13.md with its executive brief and a results table generated from the committed documents, requirements CT-1301 to CT-1313 with an adversarial check each, and the engine pin moved to origin/task/u8-market at 344ec9a with its market extra until the engine release is tagged.
- U8-S contracts: the JSON Schemas of the C11 (window) and C13 (deficiency) case documents and models documents under docs/contracts/schemas/c11 and c13, with plainly labelled fixtures under docs/contracts/fixtures/ that validate by discovery; the sign convention (the engine stores the return convention, the documents positive loss numbers) is a required field, a C13 document carries its known planted deficiency, a C11 forecast dated on or before the end of its estimation window is caught by the leakage check, the hyperparameter span must end before 2007 and before the window it serves, and a back-test that cannot run is a not_evaluated row with its reason.
- U8-S engine contract: docs/contracts/engine/market-api.md (engine-market-api 1.0.0), the signatures, units, invariants, light rules and golden values of riskvalidation.market (conventions, historical, parametric, garch, evt, caviar, gas_fz, scoring, frtb) and riskvalidation.validation.market, with the MAR32.9 cumulative probabilities, the chi-square critical values, the EWMA effective days, the FZ0 reduction and the PLA zone boundaries; the catalog rows are in docs/contracts/rows/U8.md for the integrator to merge.
- U8-S fixes (Opus review F1 to F16 and decisions D1 to D3): the hyperparameter span is the constant 1995-01-01 to 2003-12-31 for every window; the six windows carry the dates of decision D2, bound to their ids in the variant and the models schemas; a window with fewer than 250 forecast days must carry the Basel traffic light as not_evaluated with its reason, and a longer one must carry an evaluated zone; the MAR32.9 Table 1 rows, the C13 deficiency plans and the desk limits are constants; the CAViaR and GAS starts and the seed are required hyperparameters and the Diebold-Mariano lag count is recorded in the comparison.
- U8-S fixes, engine contract and checks: the sample ES is the A.0 tail integral with the fractional atom, the PLA KS statistic is an exact integer count of steps divided by 250, the filtered HS residual is demeaned, the McNeil-Frey test takes its alpha and has a numeric golden; the producer checks (leakage, span, window dates, counts, recomputed statistics, variant id) run on the fixtures and on every committed C11 and C13 document and are an acceptance check of the bakes.
- U8-S follow-up D4: the calm 2004-06 window is the control window with asset class mixed (the same portfolio composition as the mixed 2023 window); the variant and models schemas bind it, and a calm window of another class is refused.
- U8-S engine-review amendments (review-u8-engine-2026-10-13.md): the sample-ES and volatility-updated HS domain is alpha in (0, 0.5]; the age-weighted HS follows Boudoukh, Richardson and Whitelaw (1998) with a knot at each cumulated weight valued halfway between neighbouring returns, its golden is their worked example (2.63 and 2.34 percent, pages 6 and 7), and its ES (D-9) is the tail integral of that quantile function; conditional EVT uses a constant-mean GARCH with no AR term; the Taylor ES-CAViaR equations and its two-step estimation (D-10) are stated; the DQ test takes a Monte Carlo p-value with a stated size requirement near nominal.
- U8-W C11 instrument (market VaR and ES back-testing, one window per variant): the rail has three sections (tail level, model, back-test) with a live read-out each; the groups are Exceedances (the VaR, ES and realised-loss timeline with a point on each exceedance, and the rolling 250-day exceedance count against the MAR32.9 zones with the table of counts, multipliers and cumulative probabilities), Back-tests (Kupiec, Christoffersen and duration rows with their eligibility, and the Acerbi-Szekely Z2 null distribution with the realised statistic, the model's own simulated critical values and the published points only as a reference), Comparison (the champion and the model confidence set on FZ0, and Diebold-Mariano against the champion), Findings, Variants (the six windows) and Context (the hyperparameter span first). Every VaR and ES is a positive loss with the convention named once per view; a test that did not run shows its reason and no number; nothing draws a number the document does not hold.
- U8-W C13 instrument (FRTB desk eligibility on a generator with a planted deficiency, one deficiency per variant): the rail has two sections (desk back-test level, PLA statistic); the groups are PLA (the rank scatter and the two ECDFs with the Kolmogorov-Smirnov gap of the example replication, the zone counts across replications, and the detection rate with its interval), Desk back-test (the exceptions against the MAR32.18 limit), Findings, Variants (the six deficiencies) and Context. Every view names the known planted deficiency, its mechanism and the synthetic label.
- U8-W run-time descriptors for the c11-outputs, c11-models, c13-outputs and c13-models documents (workbench/c11/descriptor.ts and workbench/c13/descriptor.ts), checked against the fixtures in both directions; the integrator composes them in contract.types.ts.
- U8-W Methodology section on market risk (pages/methodology/market.tsx, tests group): the sign convention, elicitability and the FZ0 score, the estimator ladder, the back-tests and the comparison under a consistent score, and the FRTB desk and P&L attribution tests, with the MAR32.9 and MAR32.42 numbers transcribed and the unverified details named; 29 references in content/citations/U8.ts and the C11 and C13 coverage rows in content/coverage/U8.ts.
- Wave 2 batch 2 on Experiments and Benchmark: the six new cases (C10, C11, C13, C14, C15, C17) each have a table of one headline row per variant in the case's own measures, read from the committed artifacts when the page opens (`frontend/src/pages/Wave2Sections.tsx`). C10 reads the fitted PD and correlation with their interval, the 2007-2012 exceedances and the 99.9 percent capital of the C2 rung and the LHP, and the correlation grid its size and power; C11 the champion, the Basel traffic-light zone, the average FZ0 score and the size of the model confidence set at each level; C13 the planted deficiency, the share caught and the PLA zone counts; C14 and C15 the largest delta EVE and its shock with and without behavioural NMD (C15: with and without the offset, and the delta NII with the indexation charge) and the outlier tests; C17 the true 99.9 percent quantile, the bias and dispersion of the LDA capital and the SMA capital. A field the artifact leaves null reads "not available" with its reason.
- Wave 2 batch 2 Experiments families: `portfolio-capital` and `operational` join one "Capital models" group; `provisions` and `lgd-ead` join "Credit losses: provisions, severity and exposure"; `market-ccr` and `balance-sheet` join "Market and balance-sheet risk" (Spanish: "Modelos de capital", "Pérdidas de crédito: provisiones, severidad y exposición", "Riesgo de mercado y de balance"). The top row holds six groups and no group above six peer tabs (ADR-0071 rule 5).
- Wave 2 batch 2 Benchmark: C10 compares its rungs C1 to C6 against the one-factor Monte Carlo reference (and the correlation estimators against the known correlation), C11 the ladder by FZ0 and the model confidence set, C13 the detection rate of each test per planted deficiency, C17 the LDA rungs against the true quantile and the SMA. `NO_BENCHMARK` is now a map of reasons: C14 and C15 (an IRRBB measure is a regulatory calculation under prescribed shocks, compared in the App with and without the behavioural assumptions) and C06 and C07 are listed on the page in a section of cases without a champion-against-challenger comparison, each with its reason in both languages.
- Wave 2 batch 2 checks: `frontend/src/pages/wave2.test.tsx` (30 tests) builds every table from the contract fixtures in both languages and asserts the families, one row per variant, the values against the fixtures, the missing-data readings and the exclusion reasons; `families.test.tsx` follows the regroup.

## [0.10.002], 2026-10-13

The App is the leftmost tab again and the Introduction takes the full width of the page.

- The shell is pinned exactly at 0.13.1: the header order is App, Introduction, Methodology, Implementation, Experiments,
  Benchmark (0.13.0 had put the Introduction first when only the landing was to move to it); the site still lands on the
  Introduction's executive view; every documentation route is full width, the Introduction included (it was capped at
  1200 px while the other pages filled the screen).

## [0.10.001], 2026-10-13

The built cases no longer read as served by a fixture, and no bar chart scrolls inside its drawing.

- The catalog rows of C03, C06, C07, C08 and C09 (outputs and models) and of the two engine contracts are `real`: their
  owner is the producer (the case package, or the released riskvalidation module), their example a committed
  document, their producer test the case's own document test. The App had printed "Served by its provider
  (fixture:...); the real producer is not built yet" above these five cases since their bakes replaced the fixtures.
- C09's CCF estimates show the rail's design: its four treatments under both estimators (the mean of the facility
  factors and the pooled ratio), named in the label and in a column of the table. Before, the 24 rows of the three
  designs scrolled inside the chart and the two estimators of a treatment read as one label twice.
- The LGD distribution of C08 and the realised CCF distribution of C09 give their chart the height its rows need
  (`ChartOverTable` takes `chartMin`), so their first and last bins are no longer cut.

## [0.10.000], 2026-10-13

Contraste now validates loss severity and exposure, and its executive view frames the industry problem. Case C03 tests SME PD models by approval vintage on the SBA 7(a) loans through 2008, each cohort trained only on vintages whose five-year mark precedes it; case C08 builds LGD and downturn LGD on the SBA charge-offs with six model rungs, the downturn add-on and the IRB LGD floors; case C09 measures how each CCF design and treatment misses a known CCF on generated revolving lines. Nine of the 22 cases are built. The site lands on the Introduction's executive view, the problem of defending internal risk models before supervisors in five sub-tabs, general and never tied to a client. The engine is riskvalidation 0.06.000; on shell 0.13.0 and template 0.07.000.

- U6-S contracts: the JSON Schemas of the C03 (vintage-cohort), C08 (default-cohort) and C09 (acceleration-level) case documents and models documents under docs/contracts/schemas/c03, c08 and c09, with plainly labelled fixtures under docs/contracts/fixtures/ that validate by discovery; an LGD (C08) or a CCF (C09) outside [0, 1] validates only with its flag, a C08 document carries the LGD proxy definition and bias statement, and the Freddie Mac slot is nullable with its reason.
- U6-S engine contract: docs/contracts/engine/lgd-ead-api.md (engine-lgd-ead-api 1.0.0), the signatures, units, invariants, light rules and golden values of riskvalidation.lgd_ead (workout, lgd_models, downturn, ccf, floors) and riskvalidation.validation.lgd_ead; the catalog rows are in docs/contracts/rows/U6.md for the integrator to merge.
- U6-S fixes (review of 2026-10-13): C03 reads the 5-year target only at the mark (`horizon_months` and `observed_at_months` are the const 60, each vintage row carries `five_year_mark_date` and `mark_observed` with the observed or unobserved branch, each curve couples `observed_until_month` with its reason), each C03 models cohort window carries its own training window (decision D1: `last_fy <= first_fy - 6`), the C03 decile is at most 10 and the PD rung kind is an enumeration.
- U6-S fixes: the C08 proxy follows decision D2 (gross charge-off amount over `GrossApproval`, `exposure_field` and `source_field` consts, `bias_direction` downward, `exposure.gross_approval_total`), prediction sites use a `c08LgdPrediction` wrapper inside [0, 1], the floor cells and the floor rows are the 12 transcribed cells with a nonnegative uplift, `endpoint_sensitivity` has at least two rows and a none-proxy workout carries no discount rate.
- U6-S fixes: a `not_evaluated` test row of a C03, C08 or C09 variant carries null statistic, p_value and metric and a reason in notes (the rule is composed in the variant schemas; moving it to `common/test-result` is a contract bump for the integrator); C09 treated CCF estimates stay in [0, 1], `ead_models` carry the clipped counts and `ead_backtest.rows` a `prediction_flag`.
- U6-S fixes: the engine contract `lgd-ead-api.md` corrects the `workout_lgd` rate invariant, defines the zero-spread, per-period and zero-denominator cases of the validation clauses (`extras["thresholds"]`, `extras["excluded"]`), cites the CRE32.17 partially secured floor formula, cites dossier 01 section C for the standardised CCFs, and states the overdrawn-line and `small_undrawn_rule` aggregation rules.
- U6-S engine review amendments (2026-10-13): `lgd-ead-api.md` states what the engine does with no change to a signature or golden value: `fit_direct_ead` needs a finite `ead` and a positive `limit`, the hurdle severity design must be columns of X (`extras["severity_columns"]`) and the hurdle refuses an all-positive y, `to_us_terms` gives NaN for `limit <= drawn`, `reference_indices` requires references before the default, the backtest with no realised EAD is `not_evaluated`, the zero-spread tolerance, and rows are serialised by `TestResult.to_dict()`.
- U6-P1 C03 (SME PD by vintage through 2008): the real producer of the `c03-outputs` and `c03-models` documents on the SBA 7(a) loans, `data-pipeline/pipeline/cases/c03/`, with five test cohorts (FY2006-07, 2008-10, 2011-14, 2015-17, 2018-20), each trained on its own strictly out-of-time window (decision D1: approval fiscal years whose 5-year charge-off mark falls before the first approval of the cohort), the rungs of the C01 PD ladder fitted on a stratified sample of each window, and the PD validation tests of `riskvalidation` 0.5.0 as the only validation rows; the documents are in `data/derived/C03/` with the manifest `data/derived/manifests/C03.json`.
- U6-P1 target and censoring: a charge-off within 60 months of approval, read for a vintage only at its 5-year mark; a loan observed for the whole horizon and still active is a non-event, a loan observed for less and not charged off carries no outcome and is counted apart (`n_exempt_censored`), never counted as performing; a vintage before its mark has a null observed value with its reason, and a cohort with no observed mark is refused.
- U6-P1 tests and docs: `tests/c03/` (twelve requirements CT-801 to CT-812 with their adversarial checks, run on a committed sample of 10,800 SBA 7(a) rows, 300 per approval fiscal year), `docs/design/features/c03/`, and the case page `docs/cases/C03.md` with its result tables generated from the committed documents by `data-pipeline/pipeline/cases/c03/page.py`.
- U6-P2 case C08 (LGD and downturn LGD on the SBA 7(a) charge-off twin): the real producer of `c08-outputs` and `c08-models` (`data-pipeline/pipeline/cases/c08/`), calling `riskvalidation` 0.6.0 (`lgd_ead` and `validation.lgd_ead`) and catboost 1.2.10 for the gradient-boosted rung; six variants (default cohorts 2003-06, 2007-08, 2009-10, 2011-13, 2014-19, 2020-23), each trained on the defaults charged off before its cutoff and tested out of time, with six rungs (OLS, fractional logit, beta at three epsilons, hurdle, gradient boosting, Tobit), the downturn add-on and the floors' bite; the committed documents are `data/derived/C08/` and `data/derived/manifests/C08.json`.
- C08 LGD proxy (decision D2): `GrossChargeOffAmount` over `GrossApproval`, biased low and stated in every document; a proxy outside [0, 1] is kept with its flag and never clipped, a ratio above ten (a unit error of the approved amount, 17 charge-offs) is a counted exclusion; the Freddie Mac slot is declared absent in every document.
- C08 requirements CT-901 to CT-917 with their adversarial checks (`docs/design/features/c08/`), the committed test sample (`tests/c08/data`) and the case page `docs/cases/C08.md` with its generated results.
- U6-P3 case C09 (EAD and CCF for revolving lines): the real producer of `c09-models` and `c09-outputs` 1.0.0 in `data-pipeline/pipeline/cases/c09/`, replacing the fixtures. A seeded generator of revolving-line histories with a known CCF (a gamma-frailty geometric drawdown over the twelve months before default, so the known CCF of a level is a closed form of the parameters), its marginals calibrated from the Federal Reserve 2025 low, typical and high risk card portfolios (file sizes and hashes committed in the parameter file, recalculated by a test whenever the files are present), six utilisation acceleration levels 0 to 5 (known CCF 0.600 to 0.786), and 20 development and 20 test replications of 50,000 facilities fixed by disjoint seeds.
- U6-P3 C09 estimates: for each level the fixed-horizon, yearly-cohort and variable-horizon designs under the four treatments (none, censor, floor-cap, bounded-scale) and the mean and pooled aggregators, each scored against the level's known CCF with the bias, root mean square error, interval and a `lgd_ead.ccf_estimator_bias` test row; a CCF outside [0, 1] is flagged, never clipped; an undefined CCF (no undrawn amount) and a default in the first month of its cohort are excluded and counted; eight EAD models (CCF constants by design and treatment, a bounded-scale CCF model, direct EAD with its clipped counts, utilisation change) back-tested in USD by utilisation band, the IRB EAD floor and the small-undrawn count. Every number comes from `riskvalidation` 0.6.0.
- U6-P3 documents and checks: `data/derived/C09/` (six level documents, the models document, SHA256SUMS), `data/derived/manifests/C09.json`, the case page `docs/cases/C09.md` with its generated results block, the requirement rows CT-1001 to CT-1013 with their adversarial rows under `docs/design/features/c09/`, and `tests/c09/`.
- U6-P3 engine finding for the engine owner: `riskvalidation.lgd_ead.lgd_models.logit_quasi_mle` compares log-likelihoods of the order of the sample size to an absolute 1e-14, so on a pooled sample of about 38,000 observations it can stall at the optimum and raise "did not converge within 200 iterations" (level 2 direct EAD in this bake); the bake repeats the fit on every k-th observation and writes k in the models document.
- The App has the C03 instrument (the SME PD by approval vintage on the SBA 7(a) data): the cumulative PD curves of each vintage, predicted against observed, with the months not yet observed a gap and its reason, never a zero; the five-year mark of each vintage read only at its mark; the stability of the vintages; the PD rungs with their AUC interval; the calibration by decile; the training window of each test cohort, which ends before the cohort starts. The rail has three sections (Vintage, Horizon, Model), each with a select and a live read-out.
- The App has the C08 instrument (LGD and downturn LGD on the SBA charge-off twin): the LGD distribution with its masses at 0 and 1 and the values outside [0, 1] kept, flagged and never clipped; the charge-off proxy with its stated bias; the LGD models side by side, realised against predicted by default cohort, the calibration by bucket and the sensitivity of the beta regression to its endpoint shift; the downturn add-on against the losses of the crisis cohorts; the bite of the IRB LGD floors with the transcribed floor cells. The rail has four sections (Model, Endpoint, Cohort, Floor).
- The App has the C09 instrument (EAD and CCF for revolving lines on a generator with a known CCF): every reference-date design and treatment drawn against the known CCF, with the bias, the interval and the shares outside [0, 1]; the distribution of the realised CCF with the counts below 0 and above 1; the EAD back-test in currency by utilisation band; the EAD models with their clipped counts; the EAD floor, the supervisory CCFs and the small-undrawn rule. The rail has four sections (Design, Treatment, Model, Band).
- The three instruments read the c03, c08 and c09 1.0.0 contracts and render from their fixtures until the bakes replace them; a test that did not run shows its reason and no number, a null field says "not available" with its reason, and the Spanish text is written in Spanish.
- The Methodology page has the LGD and EAD topic (workout LGD, the shape of the distribution, the model ladder, the downturn add-on and the IRB LGD floors; the CCF, the reference-date designs, the treatments of a CCF outside [0, 1], the models with and without the CCF and the EAD floor), with its equations, two schematics and 21 references transcribed from the research dossiers.
- The coverage rows of C03, C08 and C09 name their data and truth status. The run-time descriptors of the three cases are in `workbench/c03/descriptor.ts`, `c08/descriptor.ts` and `c09/descriptor.ts`; the integrator composes them in `lib/contract.types.ts` (`variantKind`, `modelsKind`, with the `tests` of the three variant schemas as `json`), which turns the six descriptor tests of `contract.test.ts` green.
- The LGD and EAD Methodology topic is registered in the tests group because the models group already holds the six peers that ADR-0071 rule 5 allows (five own topics and provisions); the integrator moves it when `Methodology.tsx` gets a credit-risk group. With C03, C08 and C09 built, the Experiments page lists nine case tabs, which breaks rule 5 in `Experiments.tsx` (a shared file): the integrator groups them.
- U6 integration: the contract descriptors of C03, C08 and C09 are composed in `frontend/src/lib/contract.types.ts`
  (their partial-key rows stay `json`), so `contract.test.ts` checks the committed artifacts of the three cases again.
- Experiments groups its case tabs by the question family (credit scoring and PD, provisions, loss severity and
  exposure, validating the validator), so no tab row holds more than six peers (ADR-0071 rule 5).
- Experiments and Benchmark read C03, C06, C07, C08 and C09 from their own artifacts (`pages/U6Sections.tsx`): one
  headline row per variant, and a rung comparison per variant for C03, C08 and C09. Before, these cases went through the
  C01 scorecard table and showed "not available" in every cell. A case with no outside file no longer reads "It reads ,".
- Methodology: the LGD and EAD topic has a group of its own, "Loss severity and exposure".
- The vendored template checks move from 0.05.000 to 0.07.000: `check_sdd.py` validates the executive view against
  the shell's schema 2.0.0, `check_live.py` and `check_template_residue.py` know the `/app` route and the example
  executive view, and `tests/test_guards.py` covers the residue marker. `.template-version` is 0.07.000.
- The C09 requirement rows are CT-1001 to CT-1013 (they were CT-901 to CT-913, the IDs of C08's rows).
- A test row lit by a policy tolerance on its metric (`extras.thresholds.tolerance`, the C09 CCF estimator bias) keeps
  its committed light when the policy rail moves, like a row lit by an acceptance band, and its threshold reads "Policy
  tolerance, not regulatory".
- The findings card of C06, C07, C08 and C09 draws the findings by severity above its table, so the card meets its
  drawing floor; the C08 endpoint-shift chart writes its shift in scientific notation and its mean LGD at one fixed
  decimal, so no tick label repeats; the C22 rail leaves the variant title out (it stays in the Variants and Context
  groups), so the rail does not scroll at 1280 x 800 in the gate's wide font.
- The executive view is rebuilt to the standard of CAOS_MANAGE `conventions/problem-context-first.md` on shell 0.13.0 (pinned exactly, schema 2.0.0): the industry problem of defending internal risk models before supervisors, in five sub-tabs (the pain, the context, the current situation, the trends, the proposal with the 4 C's and its actions), general and never tied to a client. The Chilean supervisor's 571 million US dollars of extra provisions on individually assessed commercial loans stays as a headline figure, with its deadline of January 2031 and a titled link to the publication; every figure and claim carries a linked source (11 sources).
- The root of the site lands on the Introduction's executive view and `/app` is the workbench; old links with `?case=` are forwarded to it by the shell's `Landing`. The page for an unknown path is the landing, as the shell requires, so `NotFound.tsx` is removed.
- The Introduction's technical view shows its subsections as sub-tabs (six, with the two reading guides merged to stay within six peers); its lede no longer names a role or a country.
- Three new hand-authored illustrations (`pain`, `situation`, `proposal`) replace the three of the previous view; the pain and the proposal share one setting. The executive test now holds schema 2.0.0, the headline figure and its link, the general wording, the depth and the illustrations.
- The SDD's executive section names the data file and restates nothing.
- CI: the checks job installs the web dependencies and the schema validator before the SDD guard, as template 0.07.000
  does, since the guard validates `content/executive.json` against the shell's installed schema.

## [0.09.001], 2026-10-13

The executive view is general, never tied to one bank: it is addressed to chief risk officers and heads of model validation at banks that build internal credit and provisioning models; its answers no longer speak from inside one bank, and the question on cost is removed.

- content/executive.json: the audience and the organisation are a family of roles and a class of banks; the initiative, the vision, the dialogue and the captions are general; four questions remain.
- The initiative illustration's Spanish label reads 'Modelos de un banco'.

## [0.09.000], 2026-10-13

The Introduction opens on the executive view rebuilt to the standard every CAOS app now shares (the shell's ExecutiveView, 0.12.0): it is addressed to the chief risk officer of a Chilean commercial bank preparing the first CMF review of the bank's internal credit and provisioning models, with the CMF's own estimate of what is at stake, the outcomes proved by Contraste's committed results, the questions that officer asks, and three illustrations of the initiative, the problem and the proposed solution. The 4 C's section is pending their definition.

- The executive view is rebuilt on the shell's `ExecutiveView` (shell 0.12.0): one executive (the chief risk officer of a Chilean commercial bank), one context (the CMF's proposed internal-model rules), one sourced figure to act now (571 million US dollars of extra provisions on individual commercial loans, January 2031) and four outcomes whose proofs are Contraste's committed results (cases C07, C05, C01, C22), with a five-question dialogue, from `content/executive.json`.
- Three hand-authored illustrations of the initiative, the problem and the proposed solution, one shared setting, in `frontend/public/executive/`, in English and Spanish, theme tokens only.
- The Introduction's old executive areas (initiative, outcomes, positioning, credibility) are removed; the technical view keeps its five areas. The shell pin is exactly 0.12.0. `frontend/src/content/executive.test.ts` checks the data and the three drawings.

## [0.08.000], 2026-10-13

Contraste now computes loan-loss provisions. Case C06 runs IFRS 9 lifetime PD, staging and the expected credit loss on the public SBA 7(a) small-business loans at six reporting dates from 2006 to 2023, each model tested on what happened after its date. Case C07 provisions one synthetic Chilean bank, Banco Andino, calibrated to CMF system aggregates, under CMF B-1, IFRS 9 and BdE Annex 9 in six scenarios. Six of the 22 cases are built. The engine is riskvalidation 0.05.000; on shell 0.11.2 and template 0.05.000.

- Integration: the case index and the readiness list C06 and C07 as built (16 planned cases remain); the pi contract is 2.0.0 (the C06 and C07 documents join the documents the API may serve); a test row lit by an acceptance band rather than a p-value (the IFRS 9 lifetime PD backtest) keeps its committed light when the policy rail moves, and its threshold is labelled as a policy acceptance band, not regulatory.
- Case C06 (U5-P1): the real producer of the `c06-outputs` and `c06-models` documents on the SBA 7(a) FOIA loans (the public
  small-business twin of the mortgage case; Freddie Mac is not used, the owner's account is missing) and the Federal Reserve
  2026 scenario shapes, for six reporting dates (2006-12, 2008-12, 2010-12, 2019-12, 2020-06, 2023-06). A lifetime PD ladder on
  statsmodels (Kaplan-Meier, a discrete-time hazard with macro covariates, Cox), term structures per scenario, IFRS 9 staging,
  probability-weighted ECL, the IFRS 7 35H and 35I roll-forwards and the IFRS 9 battery, every number of a term structure, stage,
  ECL, allowance and test through `riskvalidation` 0.5.0 (tag v0.05.000). Case package `data-pipeline/pipeline/cases/c06/`,
  documents under `data/derived/C06/`, page `docs/cases/C06.md`, requirements CT-501 to CT-517 with adversarial validation rows,
  tests in `tests/c06/` on a committed sample of 12,000 SBA rows.
- Sources: `sba-foia` and `fed-stress-tests` gain their fetch specifications (`data-pipeline/config/sources.json`) and their
  files are pinned in `data/sources/manifest.json`.
- Case C07, the Chile provisions trilogy (U5-P2): the real producer of the `c07-models` and `c07-outputs` contracts. One synthetic bank,
  "Banco Andino" (171,500 accounts, CLP 6.0 trillion, labelled synthetic), calibrated to the CMF "Informe del Desempeno del Sistema
  Bancario y Cooperativas" of August 2026 (loan mix, provision index and 90-day delinquency by portfolio, each target with its URL,
  month and file hash), provisioned under CMF CNCB B-1, IFRS 9 and BdE Circular 4/2017 Annex 9 through `riskvalidation` 0.5.0 in six
  scenario variants (base, recession, consumer arrears shock, house price fall, UF inflation spike, combined severe). The IFRS 9
  column is the probability-weighted ECL with overlays as separate lines; the gap from B-1 to IFRS 9 is an exhaustive bridge that
  closes to the peso. Package `data-pipeline/pipeline/cases/c07/`, documents `data/derived/C07/` (seven documents, about 220 KB, with
  `SHA256SUMS.txt`), manifest `data/derived/manifests/C07.json`, case page `docs/cases/C07.md`, requirements CT-701 to CT-713 in
  `docs/design/features/c07/`, tests `tests/c07/` (a 3,430-account book, seconds).
- Contracts U5-S: the C06 case documents (`docs/contracts/schemas/c06/`: `variant-reporting-date` with outputs.kind
  `reporting-date`, and `models`) and the C07 case documents (`c07/`: `variant-three-regime` with outputs.kind
  `three-regime`, and `models`), each strict both ways, PD open (0, 1) at estimate sites, every money block carrying its
  `currency`, nullable fields with their reason where the bake may lack data; four fixture documents under
  `docs/contracts/fixtures/c06/` and `c07/` (labelled fixtures, never results).
- Contracts U5-S: the engine provisions API contract `docs/contracts/engine/provisions-api.md` 1.0.0: signatures, units,
  invariants and goldens (the 2.68% against 1.80% non-linearity example, the B-1 cells, the Annex 9 tables) of the term
  structure, staging, ECL, overlays, reconciliation, IFRS 9 battery, CMF B-1 and BdE Annex 9 modules; catalog rows in
  `docs/contracts/rows/U5.md`; tests in `tests/contracts_u5/`.
- Contracts U5-S, review fixes: the C06 and C07 schemas, the four fixtures, the engine provisions API and the rows fragment are
  corrected after the Opus review (fixes 1 to 14); the contracts stay at version 1.0.0 because nothing has consumed them yet.
  Engine API: competing risks are their own `CompetingRisks` record with `forward_pd` as `(F_D(b) - F_D(a)) / S_all(a)`; one
  tolerance basis `1e-6 * max(1, G)` (G the total gross carrying amount); `Overlay.stage` (null is carried in the stage1
  closing); an explicit POCI mask; the low credit risk exemption scope and `lcr_exempt`; one path for the collective transfer;
  Annex 9 doubtful buckets in days; the 0.50% minimum on the individual normal portfolio; a light rule per validation function;
  Aalen-Johansen when prepayment competes.
- Contracts U5-S, C06: waterfall line ids equal allowance movement ids (`overlay-<id>` for overlays), a GCA movement enum,
  non-negative stage 1 to 3 allowances, a re-balanced fixture, one staging policy source (`settings.sicr` with `default_dpd` and
  `low_credit_risk_pd`), at least two scenarios, no flow out of POCI, cohort and estimator on the lifetime backtest, and the
  12, 24 and 36 month decile calibration.
- Contracts U5-S, C07: the B-1 total is the statutory provisions plus the minimum top-up with additional provisions outside it
  (`booked_total`); a statutory status per regime and exactly three regimes; the IFRS 9 regime is a probability-weighted ECL over
  at least two scenarios (weights, staging policy, EIR basis and the variant `z_shift` in the models), overlays are their own
  lines; `internal` nullable with a reason; Annex 9 segment codes with separate labels; `delta_vs_base` follows the scenario.
- Tests U5-S: `tests/contracts_u5/test_u5_review_fixes.py` holds one plant per review finding; the rows fragment now passes
  `scripts/check_contracts.py`; the generated contract types and OpenAPI are regenerated.
- C06 instrument (`frontend/src/workbench/c06/`): mortgage lifetime PD, IFRS 9 staging and ECL at one reporting date, built against the `c06-outputs` and `c06-models` 1.0.0 contracts and their fixtures. Model: PD term structures per scenario (cumulative, marginal, hazard) with the origination forward curve of the selected account, the SICR scatter with the multiplier, absolute floor and threefold lines drawn from the document's own policy, the non-linearity panel and the ladder. Validation: lifetime backtest, calibration by decile, rung comparison, the roll-forward identities on their one tolerance basis and the test rows. Impact: stage flow between two reporting dates, the allowance waterfall with every overlay as a bar of its own, the scenario-weight simplex (staging recomputed against frozen, with the rail weights marked) and the stage summary.
- C07 instrument (`frontend/src/workbench/c07/`): the Chile provisions trilogy of the synthetic Banco Andino under CMF B-1, IFRS 9 and BdE Annex 9, built against the `c07-outputs` and `c07-models` 1.0.0 contracts and their fixtures. The three regimes with their legal status, the segments and gaps, the bridge from the B-1 comparable total to the IFRS 9 total, each regime in detail (the B-1 minimum, max rule and additional provisions outside the comparable total; the IFRS 9 probability-weighted components with a single scenario only as a labelled sensitivity and the overlays apart; the BdE categories mapped to stages), the calibration targets, the transcribed B-1 tables and the scenario change against the base.
- Both instruments show a value the contract allows to be null as "not available" with its reason, say when the document is a fixture, carry their lane on every view, and are registered by `useInstrument` in `instrument.tsx` (no shared file edited). The C06 capital bridge is not drawn: the `c06-outputs` 1.0.0 contract carries no capital data.
- Methodology: one `method` section on provisions (`pages/methodology/provisions.tsx`, models group): lifetime PD identities, the ECL as a sum of marginal losses, the one-factor conversion and non-linearity with the worked example of dossier 02, the SICR rule, CMF B-1 and BdE Annex 9, a schematic of the three regimes and one honest callout; bilingual, transcribed from dossiers 02 and 03.
- References of unit U5 in `content/citations/U5.ts` and the coverage rows of C06 and C07 in `content/coverage/U5.ts`.
- Consumer tests `workbench/c06/c06.test.tsx` and `workbench/c07/c07.test.tsx` render every view from the fixtures and read the numbers back from the markup.
- C06 and C07 rails fixed against the shell gate on the real bakes (ADR-0071 rules 6 and 7). The long lists taken from the documents (the scenarios, the segments, the 40 sampled accounts) are one select control each (`c06/RailSelect.tsx`, option text fitted with the shell text kit, the whole label and the hint as the title), not columns of chips. The rail is split in sections that each fit the 686 px rail at 1280x800 with a control group and a live read-out: C06 Scenarios, Curves, Account, Simplex; C07 Regimes, Segment, Scenario, Weight, B-1. New read-outs: the weighted curve of the segment in the measure chosen (C06), the regime in focus and the scenario in the document (C07).
- Money in a rail read-out or control is compact with its unit ("19.6 bn USD", "19,6 mil M USD"), never an eleven-digit amount (`compactMoney`, `axisScale` in `c06/format.tsx`); the tables beside the drawings keep the whole amount. The read-out labels no longer carry a scenario name from the document (the hint does). The C07 additional-provisions knob is in billions with its unit.
- C06 drawings: the allowance waterfall axis and bar values are in billions with the scale in the axis title (the title no longer overlaps an 11-digit tick); the scenario-weight simplex leaves each lower corner label the room its fitted label needs and gives the whole label as a title; the stage-flow bands are drawn widest first, so a thin band is not covered by a wide one. The Findings card (shared by C06 and C07) fills its stage, so the drawn views keep the 50% floor on the C07 Findings view.
- Tests: `c06.test.tsx` and `c07.test.tsx` read the real committed documents in both languages (no raw amount in a rail, the select controls, a shortened label with its title, the sections, the read-outs).
- Rail read-outs shortened to fit (accepted by the main session): the C06 "Weight" row (it repeats the knob), the C06 "Grid ECL, frozen" row and the C07 "BdE - B-1" rail row are no longer in the rail; the first two stay in the Simplex view table and the third in the C07 Segments view.
- C06 stage flow: the bands are no longer controls of their own (two bands can cross exactly at their middle, so one of them cannot be pointed at there, which the gate measured): a click on a band still selects it, and every flow is a button in the first column of its table row for the keyboard and the screen reader; a band is drawn at least 4 px thick.

## [0.07.000], 2026-10-12

Contraste now opens for the person accountable for a bank's models: the Introduction leads with an executive view (the
initiative and why 2027 matters, the outcomes with their proof points, the positioning, the questions a chief risk
officer would ask, with the product's limits), ahead of the technical view. Underneath, the product moved to
contract-first delivery: every document has a JSON Schema and a catalog row, the build states what is real and what is
not built yet, and all 22 planned cases are listed (4 built, 18 declared absent with their unit). The design document
follows the template's spec area. On shell 0.11.0 and template 0.05.000.

- Contracts as code: one JSON Schema 2020-12 file per document kind under docs/contracts/schemas/ (common, c01, c04,
  c05, c22) with the enumerations and the ranges the design states, and a catalog docs/contracts/catalog.md with one
  row per boundary (contract 1 and contract 2 of ADR-0057 are rows, not a second system).
- Producer tests (tests/contracts) validate every committed document of data/derived and the three registries against
  exactly one schema chosen by discovery (no file or case list) and refuse a removed key and an unknown key; the
  consumer test frontend/src/lib/contract.test.ts does the same.
- TypeScript types are generated from the schemas (frontend/src/lib/contract.gen.ts through
  docs/contracts/api.openapi.json); contract.types.ts exports them as aliases and keeps the run-time descriptors tied to
  them with satisfies, so a schema change the descriptors miss fails tsc.
- New commands: npm run gen:contracts and npm run check:contracts (fails naming the stale generated file); vendored
  scripts/check_contracts.py and scripts/check_skeleton.py from the template at v0.04.000.
- Review fixes of the contracts: one default (kind-less) variant schema per case in the Python and the TypeScript
  selector (two for one case fail, one for another case is accepted); every schema under schemas/<case>/ declares a
  case_id const equal to its folder upper-cased; the schemas that may have no committed document are derived (an active
  catalog row or a document under docs/contracts/fixtures/), common/readiness is no longer named by hand.
- The consumer test walks every schema and its run-time descriptor in parallel at every nesting level (key sets and
  kinds) and validates in strict mode with the validator as an exact devDependency (@redocly/ajv 8.11.2).
- Breaking: PD is open (0, 1) at the estimate sites and the C05 parity points (c01-variant, c05-sp, c05-ldp,
  c05-models-sp, bumped to 2.0.0) and stays closed at the C04 capital parity grid (PD 0 is an engine input), the C01 irb
  parity and the C22 models parity.
- The pipeline publishes all 22 planned cases: cases are discovered (modules `cases/c<NN>_*.py` and packages
  `cases/c<NN>/` that expose `CASE`; two modules claiming one id fail with both paths), and the 18 cases not built yet
  are declared once in `data-pipeline/config/planned_cases.json` (title, category, data kind, owner unit, question)
  and listed in `data/derived/manifests/index.json` with no manifest and no data.
- A readiness document (`data/derived/readiness.json`, `python data-pipeline/run.py readiness`) states what is real in
  the build: the planned cases are a partial `case-manifest` with their manifest paths, a missing rung of the C01
  ladder is `training` on the baseline. `scripts/check_readiness.py` recomputes it from committed files (stdlib only).
- Export refuses a document that fails its schema before writing it: artifacts, the manifest of each case and the
  index (`pipeline/core/schemas.py`); `python data-pipeline/run.py index` rebuilds the index without baking.
- The C01 model slot `c01-pd-rung` has a baseline (P0, `model/benchmark.py`) that answers in place of any rung.
- The dormant API serves `/api/readiness`, answers 503 with the declared state for a planned case and 404 for an
  unknown one; `scripts/check_artifacts.py` accepts an absent manifest only when the current readiness declares it.
- Frontend on the shared shell 0.11.0 (exact pin): the product's knob override is removed, horizontal reference levels (the amber and red thresholds, the nominal levels, the TTC rates, "no bias" lines) are toned `yMarks` instead of constant series, and the documentation pages follow the end-of-page references and full-width text.
- Every view says the declared state of the documents it reads (available, partial, stale, provider, training, missing) from `readiness.json`: an inline note inside the existing card, "readiness unknown" when the document cannot be read, and the readiness table on the Implementation page.
- The 18 planned cases are listed in the case selector with a planned mark, stay selectable, and show `data-state="unavailable"` with a bilingual reason in every group and the index entry in the Context group; no manifest the readiness lists as missing is fetched.
- Discovery registries for wave 2: `workbench/cNN/instrument.tsx` exporting `useInstrument`, `pages/methodology/*.tsx` exporting `methodologySection`, `content/citations/*.ts` (a duplicate id fails) and `content/coverage/*.ts`; the existing instruments, citations and coverage keep working.
- copy-data and declared apply the partial rule: an absent manifest is accepted only when the readiness lists it in the `missing` of a partial row.
- The Introduction opens with the executive view (initiative, outcomes, positioning, credibility) transcribed from the executive brief, with every number a `Stat` with its unit and source; the technical view keeps the previous page under its areas (problem, principles, math with a glossary, pipeline, honesty). The other four documentation pages declare their ADR-0017 areas, one method section per Methodology topic with a figure, two equations and an honest callout; the Benchmark waives only its live panel, with the reason.
- Design document restructured into the twelve sections of template 0.05.000 plus the executive brief: research basis with sources and an UNVERIFIED list, sizing and contracts pointing at the sizing and the catalog, a technology table of every pin, a measured resources table; nothing of the 2026-10-04 text was dropped.
- New `docs/design/README.md`, the map of the spec area, and a `validation.md` for each of the seven live features mapping all 73 CT requirements to an adversarial check.
- New `tests/adversarial/`: plants that copy the committed files to a temporary directory, plant one defect and run the existing gate on the copy.
- `scripts/check_sdd.py`, `scripts/check_contract_versions.py`, `scripts/check_tech_matrix.py` and `docs/contracts/versions.lock.json` vendored from template v0.05.000.

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
