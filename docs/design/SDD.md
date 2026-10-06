# Software design document: Contraste

Status: reviewed design (ADR-0075), written before development from eight primary-source research dossiers (the
regulatory framework, IFRS 9, the Chilean and Spanish regimes, credit-model SOTA, market, counterparty, ALM,
liquidity, operational risk and stress SOTA, model risk management and validation, the SantanderAI reference and bank
open source, and the data and scenario sources with their licences) and the product plan. Felipe validated the plan
on 2026-10-04.

Where the requirements live: the product-level requirements whose gates land in U0 and U1 are listed in section 11
and stated, with their gates, in `docs/design/features/<unit>/requirements.md`. Each later unit adds its own
feature folder (`requirements.md`, opened `Status: planned`, with `design.md` and `tasks.md` beside it) on the day it
starts. The engine, `riskvalidation` (repository `CAOS_RiskValidation`), carries its own `docs/design/SDD.md` with the
engine-side requirements; sections 4 and 11 mark which side owns each (E for the engine, P for this product).
`scripts/check_sdd.py` holds every requirement to a gate that exists.

## 1. Problem and non-goals

**Problem.** A bank's financial, risk and analytical models must be technically robust, compliant with the
applicable regulation and used appropriately in decisions. The people who build them and the people who
independently validate them need the same things: the model families done properly, the full battery of
validation tests with their exact formulas and references, the model's regulatory and accounting impact, and a
record of the outcome. Contraste answers, for 22 authored cases: *what does this model say, does it pass the
tests that a validator and a supervisor would run, what does it change in capital, provisions, liquidity or
decisions, and what are its limits?*

It answers the three lenses of the request: technical robustness (the validation battery and the size and power of
every test), regulatory compliance (each test and calculator mapped to its paragraph and in-force date) and
appropriate use in decisions (the impact view and the findings record).

**Non-goals** (things a reader would reasonably assume, and that are out):

1. Certifying, approving or declaring any model compliant with SR 26-2, PRA SS1/23, ECB, EBA, CMF, BdE, IFRS 9 or
   the EU AI Act. A passed test is evidence, not compliance.
2. Representing any real bank. "Banco Andino" and every other synthetic institution is labelled synthetic; real
   balance-sheet aggregates (FDIC, CMF) are used as public aggregates only.
3. Production scoring, origination, or any decision about a real person. The HMDA work measures disparity in
   public decisions; it scores nobody.
4. Investment advice, market forecasting, trading signals.
5. Hosting third parties' private data. Bring-your-own-data runs in the visitor's browser and is not uploaded.
6. Reproducing proprietary datasets or tables (S&P, Moody's, Fitch, ORX, Fannie Mae, Kaggle competitions, FRED
   third-party series, Yahoo); they are linked, never mirrored.
7. Claiming that ML beats logistic regression, that deep learning beats boosting on tabular credit, or that any
   neural VaR model is better, unless the held-out comparison in that case shows it.
8. A real-time risk system, market data feeds, or a model inventory for an actual institution. The governance
   module records Contraste's own models.
9. Generative or agentic AI model validation beyond a documented practice note (the SR 26-2 scope).
10. An affiliation with Santander or with any institution named in the sources.

## 2. Contracts

### 2.1 Ingestion contracts (contract 1, raw to pipeline), one per source family

Declared once in `data-pipeline/pipeline/io/contract.py`, exported to `data/derived/contract/<family>.json`, read
by the pipeline, the live lane and the bring-your-own-data upload. Every record either validates or is rejected
with the failing field, its expected range and the policy that applied; nothing is coerced.

| Family | Required fields (types, units, ranges) | Outlier and missing policy |
|---|---|---|
| `scored_sample` (any PD/ML case) | `id`; `observation_date` ISO date; `target` in {0,1}; features with declared units; optional `score`, `pd` in (0,1), `grade`, `segment`, `protected_attr` (fairness only) | reject PD outside (0,1), unknown grade; flag missing features, imputation fitted on train only |
| `loan_panel` (lifetime PD, IFRS 9, LGD, EAD) | `account_id`, `reporting_date`, `origination_date` <= `reporting_date`, `balance` >= 0, `limit` >= `balance` for revolving, `eir` in [0, 1], `dpd` >= 0, `default_flag`, `prepay_flag`, `writeoff_flag`, cash flows with dates for workouts | reject inconsistent dates; flag dpd jumps > 31 per month; workouts incomplete at cutoff excluded and counted |
| `rating_history` | `obligor_id`, `date`, `grade` in the declared scale incl. `D` and `WR` | reject unknown grades; `WR` handled per declared convention (counted) |
| `market_series` | `date`, `series_id`, `value`, `unit` (return, level, rate in decimal) | reject non-finite; flag gaps over 5 business days; no forward fill across the forecast date |
| `curve` | `date`, `tenor_years` > 0, `rate` decimal, `compounding` | reject non-monotone tenors; flag rates outside [-0.05, 0.30] |
| `balance_sheet` (IRRBB, liquidity) | `as_of`, `item`, `currency` in {USD, CLP, CLF, EUR}, `amount`, `repricing_bucket` in the 19-band grid, `behavioural_class` | reject unknown bucket or currency; NMD caps enforced and reported |
| `loss_events` (op risk) | `event_id`, `date`, `business_line`, `event_type`, `gross_loss` >= collection threshold, `recovery` | reject below threshold (truncation is modelled, not silently kept) |
| `macro_path` | `scenario`, `date`, `variable`, `value`, `unit`, `vintage_date` | reject a path whose vintage postdates the model's observation date |

**Sources and their licence classes.** Every source the pipeline may use is declared in
`data-pipeline/config/sources.json` with its publisher, landing page, the verbatim licence fragment, its
redistribution class and the cases that use it. The four classes:

- **mirror-allowed**: raw rows may be committed or re-hosted, with attribution where required;
- **derived-only**: the pipeline may download raw data, but only aggregates, fitted parameters and results derived
  from it are committed and replayed;
- **link-only**: fetched at run time from the publisher at most; neither raw rows nor substantial derived extracts
  are redistributed; the web only links;
- **unusable**: the terms forbid the intended use, or the data is not publicly obtainable.

Every fetch writes a row of the licence manifest, `data/sources/manifest.json`: source id, URL, retrieval date,
licence class, the licence fragment, SHA-256 and byte count of every file. Raw files are written to the device's
data root (the environment variable `CONTRASTE_DATA` or the `--data-root` argument), never into the repository.

### 2.2 Artifact contract (contract 2, pipeline to web)

`data/derived/manifests/index.json` inventories the cases (bilingual titles, categories, the case the App opens
on). One manifest per case, `data/derived/manifests/<case>.json`, and one artifact per variant,
`data/derived/<case>/<variant>.json`, carry:

- `model`: id, family, rung, engine and version, licence, checkpoint hash, calibration map, parameters with units.
- `outputs`: the case's arrays (scores, grades, term structures, exposure profiles, loss distributions, curves,
  ladders), decimated per the trace budget.
- `tests`: `TestResult` rows from `riskvalidation` (`test_id, model_id, segment, statistic, p_value, metric, h0,
  alternative, policy_version, alpha_amber, alpha_red, light, n, n_events, inputs_hash, reference, notes`).
- `impact`: RWA, capital, ECL by stage, provisions, LCR, survival days, delta EVE and NII, op-risk capital, with
  units.
- `findings`: id, severity S1 to S4, evidence (test ids), status.
- `provenance`: `truth_status` in {real-outcomes, synthetic-known-truth, synthetic-calibrated, published-answer},
  the licence class of every input, source hashes, code version, seed, `riskvalidation` version.
- `lane`: offline, replay or live, with the gate measurements.

The TypeScript mirror `frontend/src/lib/contract.types.ts` is checked against every committed artifact in both
directions by `frontend/src/lib/contract.test.ts`; a drift fails the build.

## 3. Lanes

- **Offline (canonical).** `.venv-pipeline` with the pinned engines (optbinning, scikit-learn, LightGBM, XGBoost,
  CatBoost, InterpretML, SHAP, lifelines, statsmodels, arch, QuantLib, pyvinecopulib, MAPIE, fairlearn; ORE in WSL;
  TabPFN and scikit-survival as optional extras with their licence notes). The only lane that writes artifacts.
  It runs on a workstation, never in CI (ADR-0074).
- **Replay.** The SPA reads the committed artifacts for first paint and for every value marked precomputed. GBM
  scores are always replayed: ONNX Runtime Web has no tree-ensemble kernel.
- **Live.** The SPA bundles the pinned `riskvalidation` pure wheel and loads it in a Pyodide worker (numpy, scipy
  and statsmodels ship with Pyodide). Live offers: re-running any validation test with user-set thresholds,
  segments and windows on replayed inputs; the regulatory calculators; ECL recompute with user scenario weights
  and SICR settings on a replayed account sample; IRRBB shocks on the case balance sheet; small LDA and Vasicek
  simulations; scorecard and EBM scoring (additive, parity-checked). A live feature is admitted only when
  `data-pipeline/pipeline/core/gate.py` measures cold start, run time and payload under the gate and the parity
  test reproduces the committed value (tolerance 1e-9 for deterministic functions, the Monte Carlo error bound for
  simulations). TypeScript ports are used only where the measured gate rejects Pyodide; they then carry their own
  parity tests.
- **API.** Dormant (`app/`). No ADR-0002 trigger: no server state, no private data, no request-time compute.

## 4. Method ladder and acceptance (owner: E = engine, P = product)

A method is accepted only with its engine called for real, pinned dependency and licence, configuration with
units, training or calibration where applicable, a checkpoint or parameter record, inference on every applicable
case variant, its validation tests, documentation transcribed from the dossier, and an honest lane label
(ADR-0069).

| Method (owner) | Accepted when |
|---|---|
| WoE monotone scorecard (P) | optbinning bins fitted on train only reproduce monotone event rates; the points table recomputes every score exactly; AUC with DeLong CI, KS, Brier, calibration by grade and PSI out of sample are reported. |
| Penalised LR and PLTR (P) | paired DeLong against the scorecard reported; rule set stable across 20 bootstraps (Jaccard reported). |
| EBM/GA2M (P) | monotone shape functions where declared; per-term points table; post-calibration reliability; live additive scoring equals offline within 1e-9. |
| Monotone GBM plus calibration (P) | monotonicity verified on PDP grids; isotonic or Platt map fitted on a separate slice; Brier and reliability before and after; reason-code stability (bootstrap top-4 overlap). |
| TabPFN challenger (P) | runs only on small cases; the weights licence is shown on every view; same gates as GBM. |
| Rating master scale and calibration (E) | Tasche (2013) Table 1 scaled PD and scaled LR columns reproduced; Pluto-Tasche tables 1, 2, 3, 4, 7 reproduced to 0.01 pp. |
| TTC/PIT Z-factor (E) | implied Z reproduces the LHP relation; PIT PDs average back to TTC over the cycle on the generator. |
| Transition estimators (E) | rows sum to 1; generator rows to 0; equality with the transitionMatrix cohort estimator on the same data; regularised generator distance reported. |
| Lifetime PD rungs (P) | cumulative PD monotone; calibration at 12, 24, 36 months against Aalen-Johansen per decile; C-index and integrated Brier for Cox rungs. |
| IFRS 9 ECL engine (E) | reconciliation identities close within 1e-6; weighted ECL >= average-scenario ECL in the convex regime (property test); the non-linearity example 2.68% vs 1.80% reproduced; overlays reported as separate lines. |
| CMF B-1 (E) | PE = PI x PDI / 100 for every transcribed cell; the consumer matrix lookup reproduces the 16 cells; the 0.50% minimum enforced. |
| BdE Annex 9 (E) | coverage tables reproduced as transcribed; the category-to-stage mapping exposed. |
| LGD rungs (P) | predictions inside [0,1]; out-of-time calibration by bucket; endpoint sensitivity reported for beta rungs. |
| CCF/EAD rungs (P) | known CCF recovered on the generator within the reported error; the CCF convention named on every view. |
| IRB and LHP (E) | CRE99 Table 1 reproduced within 0.005 pp; Basel II mode carries 1.06 and 0.03%; Chile mode uses the RAN 21-6 correlations. |
| Copula MC, CreditRisk+, GA, IS (E) | MC converges to LHP as n grows; Euler contributions sum to the total; the CreditRisk+ recursion matches MC; GA delta = 4.83; IS unbiased against plain MC. |
| VaR/ES estimators (E and P) | each rung run over the full rolling schedule with no look-ahead; own GARCH-t (scipy) matches `arch` within 1e-4 on the log-likelihood; FZ0 losses computed for every rung. |
| VaR/ES backtests (E) | MAR99 Table 2 reproduced to two decimals; Kupiec and Christoffersen match closed forms; Acerbi-Szekely critical values simulated per model. |
| CCR and CVA (P) | own HW1F single-swap EE matches ORE within MC error at every grid point; EEPE and CVA recomputed from EE match ORE; path convergence reported. |
| SA-CCR, BA-CVA, SMA, output floor, LCR/NSFR, FRTB cascade (E) | official worked examples reproduced (SA-CCR five netting sets, SMA 5.37bn, output floor 101.5 and 95); invariants for BA-CVA, SBM, LCR, NSFR where no official example exists. |
| IRRBB/ALM (E) | SRP31.92 values reproduced (0.417, 41.7, +25.4, -1.6 bp); the 2016 and 2024 shock tables as fixtures; EVE sum-of-parts reconciles; the CMF Annex 1 worked example reproduced; CLP shocks labelled when not from the CMF. |
| Liquidity (E) | LiST compounding 12.11% after 125 days reproduced; survival period monotone in run-off severity. |
| Op risk (E) | Shevchenko benchmark mean 738.9056 and 99.9% quantile 5,849 to 5,850 across MC, Panjer and FFT. |
| Aggregation (E) | Euler contributions sum to the total; the dependence band (sum, var-covar, Gaussian, t, worst case) always shown. |
| Stress satellites (P) | back-cast through 2008-2009 and 2020 with satellites estimated on prior data; coefficient signs checked. |
| Fed supervisory replication (P) | published hypothetical-portfolio loss rates reproduced within the tolerance stated in the case. |
| Validation tests, all (E) | each reproduces a published worked example or an independent reference (scipy distributions) to a stated tolerance; every result carries `reference`, `h0` and a policy version. |
| ML validation and fairness tests (E) | each test detects its planted defect on the generator with power reported at alpha 0.05 and holds its size under the null within Monte Carlo error. |

## 5. Cases and coverage

22 cases in 11 categories. Variants: at least six wherever a meaningful parametric or temporal family exists; a
case without one ships as a single documented benchmark, never padded.

| Case | Category | Data (class) | Truth status |
|---|---|---|---|
| C01 retail cards PD, champion vs challenger | credit-scoring | UCI Taiwan, German twin (mirror-allowed) | real outcomes |
| C02 corporate PD across 1 to 5 year horizons | credit-scoring | UCI Polish bankruptcy (mirror-allowed) | real outcomes |
| C03 SME PD by vintage through 2008 | credit-scoring | SBA 7(a) FOIA (mirror-allowed) | real outcomes |
| C04 rating transitions and TTC PD by grade | ratings-calibration | ESMA CEREP (mirror-allowed) and a CTMC generator | real aggregates and known truth |
| C05 low-default portfolios and PD calibration | ratings-calibration | published tables as golden values and a Vasicek generator | published answers and known truth |
| C06 mortgage lifetime PD, IFRS 9 staging and ECL | provisions | Freddie Mac (derived-only, noncommercial) and Fed scenarios; SBA twin | real outcomes |
| C07 Chile provisions trilogy: CMF B-1 vs IFRS 9 vs BdE Annex 9 | provisions | synthetic "Banco Andino" calibrated to CMF aggregates | synthetic calibrated |
| C08 LGD and downturn LGD | lgd-ead | Freddie Mac loss fields (derived-only); SBA charge-off twin (mirror-allowed) | real outcomes |
| C09 EAD and CCF for revolving lines | lgd-ead | generator shaped on the Fed card portfolios | known truth |
| C10 portfolio credit capital: ASRF, Vasicek fit, copula MC | portfolio-capital | Fed charge-off rates, FDIC failures (mirror-allowed) and a simulator | real aggregates and known truth |
| C11 market VaR/ES backtesting across 2008, 2020, 2022, 2023 | market-ccr | Kenneth French (derived-only), Treasury, H.10 (mirror-allowed) | real outcomes |
| C12 swap exposure, CVA and SA-CCR | market-ccr | Treasury curves and synthetic trades; ORE | real market, synthetic trades |
| C13 FRTB desk eligibility: PLA and desk backtesting | market-ccr | generator with planted model deficiencies | known truth |
| C14 IRRBB six shocks on a USD balance sheet (SVB 2022) | balance-sheet | FDIC call reports, Treasury curve (mirror-allowed) | real aggregates, synthetic behaviour |
| C15 IRRBB on a CLP/UF balance sheet (RAN 21-13 Annex 1) | balance-sheet | CMF, BCCh F022 (mirror-allowed) and Banco Andino | real aggregates, synthetic bank |
| C16 liquidity stress, LCR and the March 2023 run | balance-sheet | FDIC, H.8, the Fed SVB review (mirror-allowed) and a depositor generator | real event, synthetic deposits |
| C17 operational risk: LDA vs SMA | operational | generator calibrated to BCBS LDCE 2008 (derived-only) | synthetic calibrated |
| C18 ICAAP and IAPE capital aggregation under macro scenarios | capital-stress | Fed 2026, EBA/ESRB 2025 (mirror-allowed), NGFS (derived-only) paths; Banco Andino | real paths, synthetic bank |
| C19 supervisory stress model replication (known answer) | capital-stress | Fed hypothetical portfolios and published loss rates (mirror-allowed) | published answers |
| C20 ML model validation: drift, robustness, explanation stability | ml-ai-risk | UCI, SantanderAI SGCD (CC BY 4.0), Fed portfolios as shift probes | real outcomes and known shifts |
| C21 fair-lending disparity testing | ml-ai-risk | HMDA (mirror-allowed) | real decisions |
| C22 validating the validator: size and power of every test | validator | generators with planted defects | known truth |

Variants and the leakage-safe split of each case:

| Case | Variants (the regime each shows) | Leakage-safe split |
|---|---|---|
| C01 | holdout as is; covariate drift moderate; drift severe; prior shift x1.5; label noise 5%; small sample (2,000 rows); German twin | locked stratified holdout 30%, repeated stratified 5-fold CV inside train; shifts applied to the evaluation set only and labelled synthetic perturbations; no OOT (single snapshot), stated |
| C02 | 1, 2, 3, 4, 5-year files; pooled | within-file holdout; cross-file transfer labelled exploratory (firm overlap unknown) |
| C03 | test cohorts FY2006-07, 2008-10, 2011-14, 2015-17, 2018-20; model trained through the crisis | OOT by approval fiscal year; the 5-year charge-off target observed only at each cohort's 5-year mark |
| C04 | CEREP early vs late cohorts; generator calm, stressed, regime switch; cohort vs duration | estimate on earlier cohorts, test on later; estimator error against the known generator |
| C05 | S&P 2009 curve to 2010 and to 2011 (every approach of Tasche 2013); the Pluto-Tasche example (0, 2, 1 defaults); Vasicek generator years with 0, 1, 3 defaults | golden tables recomputed from the papers' own inputs; 20,000 generator replications |
| C06 | reporting dates 2006-12, 2008-12, 2010-12, 2019-12, 2020-06, 2023-06 | train on reporting dates up to T1, test later; vintages by origination; macro as known at the cutoff |
| C07 | base; recession; consumer arrears shock; house price fall; UF inflation spike; combined severe | scenario conditioning only; synthetic portfolio fixed per seed |
| C08 | default cohorts 2003-06, 2007-08, 2009-10, 2011-13, 2014-19, 2020-23 | OOT by default date; workouts closed before the training cutoff |
| C09 | utilisation acceleration levels 0 to 5 | independent simulated development and test replications |
| C10 | C&I, CRE, residential, cards, other consumer; simulator correlation grid | fit 1985-2006, evaluate the 2007-2012 tail; simulator exact size and power |
| C11 | equity 2007-09; equity 2020; rates 2022; FX 2008; mixed 2023; calm 2004-06 | strictly rolling, the forecast for day t uses data to t-1; hyperparameters fixed on a pre-2007 span |
| C12 | single swap; netting set; CSA MPoR 10d; MPoR 20d; with IM; wrong-way risk | calibrate to curves up to each backtest date |
| C13 | no deficiency; missing basis; stale volatility; wrong correlation; omitted factor; time misalignment | generator replications |
| C14 | 2021-Q4, 2022-Q2, 2022-Q4; with and without behavioural NMD; 2016 vs 2024 shocks | call reports dated up to the valuation date only |
| C15 | long UF; short UF; CPI surprise +2.5 pp; CLP steepener; CLP/CLF offset on and off; floors active | balance sheet and curves as of one stated month |
| C16 | LCR standard run-off; LiST adverse; LiST extreme; 2023 fast run; HTM losses in CBC; reverse stress | calibrate on pre-2023 data, score on March 2023 |
| C17 | 5 vs 10 years; tail index 0.6, 0.8, 0.96, 1.1; collection threshold 10k vs 20k | independent simulated histories |
| C18 | baseline; EBA 2025 adverse; Fed 2026 severely adverse; NGFS disorderly; t-copula aggregation; reverse stress | satellites fitted 1985-2019, validated OOT 2020-2026 |
| C19 | one variant per published hypothetical portfolio type (count as published) | none: the published loss rate is the answer key |
| C20 | SGCD seen shocks; SGCD held-out shocks; Fed corporate shift probes; seed sweep; perturbation grid; leakage planted | locked holdout plus synthetic shifts on the evaluation set only |
| C21 | year pairs 2018-19, 2019-20, 2020-21, 2021-22, 2022-23, 2023-24 | fit on year t, confirm on t+1 |
| C22 | defect severity 0 (null) to 5 for each defect family (miscalibration, drift, leakage, broken monotonicity, exceedance clustering, concentration) | Monte Carlo replications with the binomial error reported |

Why each category exists: credit-scoring (the most common model and the validator's daily work),
ratings-calibration (the IRB core and the low-default reality), provisions (IFRS 9 and the Chilean carve-out),
lgd-ead (the other two parameters), portfolio-capital (what Pillar 1 ignores and ICAAP must cover), market-ccr
(VaR/ES, exposure, FRTB), balance-sheet (IRRBB and liquidity, the 2023 lessons), operational (why AMA went away),
capital-stress (ICAAP, IAPE, supervisory models), ml-ai-risk (ML validation and fairness), validator (the size and
power of the tests).

## 6. Oracles

1. **Golden values** from official worked examples and published tables: the strongest oracle; a test that cannot
   reproduce its golden value is not shipped.
2. **Known truth** from generators: the true PD, CCF, VaR, exposure or loss distribution is known, so estimator
   error, test size and test power are measured, with their Monte Carlo error.
3. **Real outcomes on held-out data** with leakage-safe splits: discrimination and calibration of real models,
   backtests of VaR on real P&L. Trustworthy only as far as the split is; the leakage tests guard it.
4. **Identities and invariants**: the IFRS 7 roll-forward, Euler sums, row sums of transition matrices, EVE
   sum-of-parts, monotonicities.
5. **Independent engine reconciliation**: own HW1F against ORE, own GARCH against `arch`, own estimators against
   transitionMatrix and lifelines, scipy distributions for every test statistic.
6. **Licence lineage**: an artifact derived from a link-only or unusable source is refused.

No oracle here is a model judging another model.

## 7. Deploy driver

One place only, decided in the plan: **`github-pages` with a `CNAME` on `contraste.fasl-work.com`**
(`deploy/TARGET` = `pages`, checked by `scripts/check_deploy_place.py`; the template's VPS files were removed at
instantiation). Driver: the repository is public and every web capability is static replay or client-side compute;
no ADR-0002 backend trigger exists (no server state, no private data, no request-time compute). Measured guard at
every release: the published site under GitHub Pages' 1 GB limit and every committed file under 100 MB
(`scripts/check_artifacts.py`); Pyodide is loaded from its CDN, not from the bundle. The Pyodide cold start with
`riskvalidation` loaded (median of 5, cold cache) is measured to admit live features (section 3), not to choose the
host. The deploy runs only after CI passes on `main` and ends with `scripts/check_live.py` against the published
site.

## 8. Risks and kill criteria

| Risk | Kill or re-scope criterion |
|---|---|
| Freddie Mac terms do not allow derived aggregates in a public web | C06 and C08 publish the SBA twin; Freddie Mac results stay offline |
| Pyodide cold start too slow | live features move to TypeScript ports with parity tests, or to replay only, per measurement |
| ORE unusable in WSL | C12 uses QuantLib plus the analytic HW1F check only, stated |
| A golden value cannot be reproduced | the method or test is not shipped until it is |
| Scope (22 cases, 17 units) | units ship vertically; nothing is presented as done until the convergence verdict |
| Licence contamination | `scripts/check_licences.py` fails on AGPL, GPL or BSL in the default install |
| A committed file carries rows a licence forbids | `scripts/check_data_classes.py` fails the build |
| The site looks right and is not (a blank chart, a dead control, a broken deep link) | the measured gate (`npm run gate`) fails before a deploy |

## 9. ADR fit

Every ADR and convention that binds Contraste was evaluated against what Contraste is (a workbench that builds and
validates financial risk models, 22 cases, an engine package, a static web companion) before any code (2026-10-04).
Where an ADR did not fit, the ADR was amended first and the base (the shared shell and the template) was fixed to
carry the amended rule, with a gate (ADR-0078, "rules live in the base"); Contraste then instantiated the fixed
template and makes no structural edits outside its core.

Where the ADRs fit as written:

| ADR / convention | Fit, and what carries it here |
|---|---|
| ADR-0057 product archetype (offline pipeline, two contracts, named stages, static replay, lane gate) | fits: Contraste is offline-heavy with a static companion; `data-pipeline/`, section 2 |
| ADR-0069 full scientific repository | fits: every model rung and every validation test is a vertical with engine, tests, docs and lane (section 4) |
| ADR-0075 SDD before development | fits: this document; `scripts/check_sdd.py` |
| ADR-0058 architecture modal (at least five themed tabs) | fits: `frontend/src/architecture/`, validated by the shell on mount |
| ADR-0056 `docs/` wiki | fits: engine and product wikis, authored per unit from the dossiers |
| ADR-0011 and ADR-0012 i18n and theming | fits: the shell; every string is bilingual |
| ADR-0061 and the no-internal-packages rule | fits: `riskvalidation` is the separate engine repository; this product declares no package |
| ADR-0065 to ADR-0068 community files, English, no em-dash, versioning | fit: `scripts/check_content_standards.py`, `scripts/check_version_coherence.py` |
| ADR-0074 CI budget | fits: the product CI runs no pipeline suite; the engine's unit tests are cheap and run in its own CI |
| Product quality bar, section 0 (one selected case on App, real action capability, honesty) | fits strongly: thresholds, policy, segments, windows and scenario weights are real live inputs |
| Units gate | applies from the second observable on: PD in (0, 1), LGD in [0, 1], CCF by stated convention, VaR and ES in the portfolio's units |
| One deploy place | fits: GitHub Pages (section 7) |

Where they did not fit, and the amendment now in force:

| # | ADR text | Why it failed for Contraste | Amendment, and what carries it |
|---|---|---|---|
| 1 | ADR-0016 9.A: the App is a top-level `Tabs` strip, one tab per case | 22 cases would be 22 tabs; ADR-0071 caps peers near six and makes a categorised one-of-N a `select` with `optgroup` | cases are chosen with the shell's `CaseSelector`, grouped by category, a `select` with `optgroup` beyond the chip budget |
| 2 | ADR-0016 9.A: four fixed sub-tabs Field, Live, Charts, Context | the instrument is itself several questions (the model, its validation, its impact, the findings); a separate Live tab assumes a live engine distinct from the replay | ONE tab row of at most six groups named for the user's question (section 10); the live lane is a property of each view (lane badge and live controls) |
| 3 | ADR-0016 5 and ADR-0017 1: the App root capped at 1200 px | validation scorecards, matrices and curves need the screen | both defer to ADR-0071 2: App and railed routes take the full viewport; only a single prose column is capped |
| 4 | ADR-0017 2: Implementation has at least 8 tabs | contradicts ADR-0071 5 | at least eight topics, organised in at most six top-level groups |
| 5 | ADR-0017 2 and the quality bar: at least two learned tabs, "a CNN and an autoencoder" | a CNN on tabular credit data is not the state of the art (Gunnarsson et al. 2021; Grinsztajn et al. 2022) | at least two learned methods that are the state of the art for the domain (monotone GBM, EBM, TabPFN, deep survival, a neural quantile VaR challenger), each beside its classical baseline |
| 6 | ADR-0017 2 Benchmark: "a confusion matrix with per-class recall" | PD models are judged by discrimination and calibration; VaR models by backtests and consistent scoring | the Benchmark uses the domain's held-out metrics; a confusion matrix only where the task is classification at a decision threshold |
| 7 | ADR-0017 and ADR-0016 name exemplar apps as the binding reference | an exemplar app cannot be the reference for a domain it was not built for, and copying another product's code is not a solution | the reference implementation is the shared shell plus the template, executed and gated |
| 8 | Quality bar: every app ports `.chip` and the workbench CSS from another product | copying another product's CSS | the shell (0.7.0) ships the workbench primitives and their CSS; apps compose them |
| 9 | ADR-0016 9 and ADR-0017 6: "until then, copy RotorVitals" | the template shipped a stub frontend | the template (0.02.x) is a running six-page app on the shell; the interim clause is removed |
| 10 | ADR-0075 6: the template ships `scripts/check_sdd.py` | it did not | the template ships it, wired in CI |
| 11 | ADR-0057 described a "Python pkg `<slug>lab`"; the residue guard forbade the frozen path | Contraste could not keep the frozen path and pass the guard | the frozen path `data-pipeline/pipeline/` holds plain scripts invoked by path; the residue guard detects the example by content markers |
| 12 | The template shipped both the Pages workflow and the VPS files | one place only | `deploy/TARGET`, `scripts/check_deploy_place.py`; instantiation removes the unchosen path |

The base this product starts from is recorded in `.template-version` (the template release) and in
`frontend/package.json` (the shell version). A later base is adopted deliberately, as its own commit.

## 10. Web companion

Exactly six routes on the shared shell (`@fasl-work/caos-app-shell`), in English and Spanish, light and dark, with
the architecture modal:

- **App**: the case workbench (the shell's `CaseWorkbench`). The rail holds the case selector (grouped by category),
  the variant bar and the case's live controls in sections shown one at a time (for C01: the decision, the policy
  thresholds with their light counts, the applicant with its live scores); chips carry the short labels the artifacts
  declare, and no section scrolls at 1280x800. The
  instrument has one tab row of at most six groups, named for the validator's question: **Model** (what the model
  says: scores, grades, term structures, curves), **Validation** (the battery: every `TestResult` with its light,
  statistic, H0, reference and policy), **Impact** (capital, provisions, liquidity, IRRBB, decisions), **Findings**
  (severity S1 to S4, evidence, the opinion), **Variants** (the case's variants side by side), **Context** (what the
  case is, its data and licence, its limits). Each view carries its lane badge; nothing is cross-case.
- **Introduction**: the problem, who it serves, the three lenses, the honest scope, the overview diagram.
- **Methodology**: one sub-tab per family (credit scoring, rating and calibration, lifetime PD and IFRS 9, LGD/EAD,
  portfolio capital, market, CCR, IRRBB, liquidity, op risk, aggregation and stress, ML validation, the test
  catalogue, the regulation map), at most six groups at the top level, each with KaTeX, assumptions, a theme-aware
  SVG and inline citations.
- **Implementation**: pipeline, lanes, contracts, the engine package, the measured live gate, provenance and
  licences.
- **Experiments**: the coverage matrix, the model inventory and tier matrix, the size and power of the tests, the
  leakage-safe protocol per case.
- **Benchmark**: held-out comparisons per family (challenger vs champion with DeLong, the VaR ladder in the model
  confidence set, estimator error on known truth), real numbers from committed artifacts.

Every route is measured by the shell's gate (`npm run gate`: every route, tab and case at five sizes, both themes,
both languages) before any deploy.

## 11. Requirements

EARS (Mavin et al., RE'09, doi:10.1109/RE.2009.9). Product requirements (`CT-`) are stated with their gates in the
feature folders; the hundreds digit is the unit (0 for U0, 1 for U1). Engine requirements (`RV-`) are stated and
gated in the engine repository.

| Unit | Feature folder | Requirements |
|---|---|---|
| U0 | `docs/design/features/contracts/` | CT-001 to CT-014: ingestion contracts, licence lineage, provenance, the TypeScript mirror, licences of the default install, data classes, content standards, the source registry, the licence manifest, the data root, hash pinning, the bring-your-own-model door (contract 1 then the battery on a reader's scored sample) |
| U1 | `docs/design/features/c01-retail-pd/` | CT-101 to CT-105 and CT-108 to CT-111: leakage-safe split, disjoint calibration slice, invariance to information outside the training set, threshold labels, live parity, the points table, the battery per rung, GBM monotonicity, expected ranges |
| U1 | `docs/design/features/web/` | CT-106, CT-107 and CT-112 to CT-114: the App route fits the viewport with one row of navigation; every route passes the measured gate; the six instrument groups; the lane on every view; sources and licences in Context |
| U2 | `docs/design/features/c05-ldp-calibration/` | CT-201 to CT-211: the paper readers checked against their own print; every golden cell within the engine's tolerance; the generator's truth recovered; coverage and power; the capital's assumptions; expected ranges; no derived-only counts published; live parity; the C05 instrument; the measured gate |
| U2 | `docs/design/features/c01-irb-capital/` | CT-212 to CT-217: C01's IRB capital along every cut-off under three regimes with its stated assumptions; each point the engine's sum; every card a revolver, the six-month full payers as the sensitivity; the live capital linear in the LGD and the retail functions at parity; the Basel III LGD floor flagged; the measured gate |
| engine | `CAOS_RiskValidation` `docs/design/` | RV-001 to RV-007 (the `TestResult` record, the policy, the suite runner) and RV-101 to RV-114 (PD and stability tests), converged in `riskvalidation` 0.01.000; RV-901 (regulatory parameters with paragraph and in-force date) lands in U9 |
