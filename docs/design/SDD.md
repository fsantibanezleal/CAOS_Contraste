# Software design document: Contraste

Status: reviewed design (ADR-0075), written before development from eight primary-source research dossiers (the
regulatory framework, IFRS 9, the Chilean and Spanish regimes, credit-model SOTA, market, counterparty, ALM,
liquidity, operational risk and stress SOTA, model risk management and validation, the SantanderAI reference and bank
open source, and the data and scenario sources with their licences) and the product plan; Felipe validated the plan
on 2026-10-04. Restructured on 2026-10-12 (unit CF-D, template 0.05.000) into the twelve sections the spec area
requires, plus the executive brief; nothing of the 2026-10-04 text was dropped, and the table below says where each
old section went.

Where the requirements live: the product-level requirements are stated, with their gates, in
`docs/design/features/<feature>/requirements.md`, and each live feature carries a `validation.md` that maps every
requirement to an adversarial check (the plants are in `tests/adversarial/`). The map of the spec area is
[`README.md`](README.md). The engine, `riskvalidation` (repository `CAOS_RiskValidation`), carries its own
`docs/design/SDD.md` with the engine-side requirements; the Method ladder and the requirements map mark which side owns
each (E for the engine, P for this product). `scripts/check_sdd.py` holds every requirement to a gate that exists and
every validation row to an adversarial test that exists.

| Section of the 2026-10-04 SDD | Where it is now |
|---|---|
| 1. Problem and non-goals | `Problem and non-goals` (unchanged) |
| 2. Contracts (2.1 ingestion, 2.2 artifact) | `Sizing and contracts` (subsections `Ingestion contracts` and `Artifact contract`) |
| 3. Lanes | `Lanes` |
| 4. Method ladder and acceptance | `Method ladder` |
| 5. Cases and coverage | `Cases` (subsection `Coverage and variants`) |
| 6. Oracles | `Oracles` |
| 7. Deploy driver | `Deploy driver` |
| 8. Risks and kill criteria | `Risks and kill criteria` |
| 9. ADR fit | `ADR fit` |
| 10. Web companion | `Cases` (subsection `Web companion`) |
| 11. Requirements | `Cases` (subsection `Requirements map`) |
| new | `Executive brief`, `Research basis`, `Technology and versions`, `Resources` |

## Problem and non-goals

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

## Executive brief

The executive view of the Introduction is data, kept apart from this document: one file frames the industry problem of defending internal risk models before supervisors, in five sections, with its illustrations and the linked source of every figure, in English and Spanish. It is valid against the shell's `executive.schema.json` 2.0.0, is general and never tied to a client, and is rendered by the shell's `ExecutiveView` first on the Introduction, with the shell's flip cards, carousels and animated illustrations under their rules of use (shell 0.14). The standard is CAOS_MANAGE `conventions/problem-context-first.md`.

Data file: `content/executive.json`

## Research basis

Done before the plan and kept here so a reader can re-check it (ADR-0075; rule 11 section 12). The research is
persisted as dated dossiers in the coordination repository (CAOS_MANAGE, `wip/contraste/`): the eight primary-source
dossiers of 2026-10-04 (01 Basel framework, 02 IFRS 9, 03 Chile and Spain, 04 credit-model SOTA, 05 market, CCR, ALM,
liquidity, operational risk and stress, 06 model risk management and validation, 07 SantanderAI and bank open source,
08 data and scenario sources), the unit dossiers (10 golden values, 11 C01 IRB capital, 12 size, power and generators,
13 rating transitions) and the problem-context dossier of 2026-10-12 (14), summarised in `plans/contraste/findings.md`
there. The table lists what was decided and from what; every source below appears in one of those dossiers with this DOI
or address.

| decision | what the research found | source |
|---|---|---|
| IRB capital follows Basel III final, with CRR3 and Basel II as comparison regimes | The 1.06 scaling factor is Basel II only; the PD floor is 0.05%; F-IRB unsecured corporate LGD is 40% | https://www.bis.org/committees/bcbs/basel-framework/standard/cre/32/inforce/2023-01-01/published/2020-03-27 |
| Retail revolvers and transactors are treated apart, and the LGD input floor is flagged | The transactor definition needs twelve months of repayment history; the retail LGD input floors are in the IRB chapter (paragraph 121) | https://www.bis.org/bcbs/publ/d424.htm |
| The validation battery is the ECB's reporting template for credit-risk models, not an invented list | No toolkit implements the ECB 2019 IRB validation-reporting tests as specified, so the product owns them | https://www.bankingsupervision.europa.eu/activities/internal_models/shared/pdf/instructions_validation_reporting_credit_risk.en.pdf |
| The product answers the supervisor's findings on validation | 200 investigations at 65 banks, more than 5,800 findings, thresholds and back-testing missing | https://www.bankingsupervision.europa.eu/ecb/pub/pdf/ssm.trim_project_report~aa49bb624c.en.pdf |
| Model-risk governance is shown as the supervisors state it | PRA SS1/23 (re-issued 2026-04); the US SR 11-7 is superseded by SR 26-2; OSFI E-23 applies from 2027-05-01 | https://www.bankofengland.co.uk/prudential-regulation/publication/2023/may/model-risk-management-principles-for-banks-ss |
| A test is judged by its measured size and power on known truth, not on real outcomes alone | BCBS WP14: no really powerful PD calibration tests exist under default correlation; its Tables 7 and 8 are reproduced | https://www.bis.org/publications/studies-validation-internal-rating-systems-revised.pdf |
| The PSI thresholds are a policy, never a regulatory limit | The scaled PSI is about chi-square with B-1 degrees of freedom; 0.10 and 0.25 are conventions | https://doi.org/10.21314/JRMV.2020.227 |
| The AUC test against the development AUC adds the development variance | The DeLong test is misused on nested models and treating an estimated reference as known inflates the size | https://doi.org/10.1002/sim.5328 |
| Hosmer-Lemeshow uses as many degrees of freedom as groups on PDs fitted elsewhere | The standard G-2 result is for in-sample fitted probabilities | https://doi.org/10.1080/03610928008827941 |
| Low-default portfolios use the most prudent estimate, with the golden tables recomputed | Pluto and Tasche's confidence bounds and tables 1 to 14 | https://arxiv.org/abs/cond-mat/0411699 |
| PD curve calibration uses the approaches of Tasche, with Table 1 as golden values | Scaled PD, scaled likelihood ratio and invariant approaches | https://doi.org/10.21314/jcr.2013.169 |
| Rating migration is a Markov model with generators and embedding diagnostics, tested rather than assumed | Israel, Rosenthal and Wei: nine generator distances, the embedding conditions | https://doi.org/10.1111/1467-9965.00114 |
| The Markov tests are Anderson and Goodman's, with their size measured | Time homogeneity and order tests; the printed forms do not all hold size on sparse tables | https://doi.org/10.1214/aoms/1177707039 |
| Schuermann and Hanson's Table 5 and the New York Fed default bounds are recomputed beside their print | A published known answer for the one-year PD by grade | https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr190.pdf |
| Rating data come from ESMA's CEREP, with its attribution and its definition caveat | ESMA sets no common definition of a default event for CEREP | https://registers.esma.europa.eu/cerep-publication/ |
| The ladder pairs each learned method with its classical baseline and never claims that ML beats logistic regression | Tree ensembles beat logistic regression by modest, dataset-dependent margins | https://doi.org/10.1016/j.ejor.2015.05.030 |
| Deep learning is not the state of the art on tabular credit data | Deep nets do not beat boosting on tabular credit | https://doi.org/10.1016/j.ejor.2021.03.006 |
| Tree-based models stay state of the art on medium-sized tabular data | Three inductive-bias explanations for the gap | https://arxiv.org/abs/2207.08815 |
| TabPFN is a research challenger on the small cases only, with its weights licence shown | Code Apache-2.0, default weights non-commercial; the v2 weights carry the Prior Labs License | https://doi.org/10.1038/s41586-024-08328-6 |
| The explainable additive challenger is the EBM | Glass-box GA2M with monotone shape functions | https://arxiv.org/abs/1909.09223 |
| The four UCI credit datasets are mirror-allowed (CC BY 4.0) and carry the credit-scoring cases | Taiwan cards with six months of history, German credit as the twin | https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients |
| The executive view rests on the supervisory record, not on surveys | 77 investigations in 2025, about 16 findings each; no primary source found for fines or inventory sizes | https://www.bankingsupervision.europa.eu/press/other-publications/annual-report/html/ssm.ar2025~6ee989dc7e.en.html |

Choices with no source because they are engineering, measured in this document instead: the live lane runs TypeScript
ports with parity tests (Pyodide is not used, and is admitted only by measurement, see `Lanes`), and the page and
payload budgets of the deploy driver.

UNVERIFIED: the dossiers flag as unconfirmed, and this document does not state as fact, the following. No primary
source was found for a supervisory fine or capital add-on tied by name to weak model validation, nor for the size of
banks' model inventories or validation backlogs (industry surveys only; the PwC survey answered HTTP 403). The job
titles that own model risk are not named in the supervisory texts read (the brief's mapping to the chief risk officer
and the head of model validation is a judgement). The OJ publication date of the AI Act omnibus, the entry into force of
the Commission delegated act C(2026) 3647 and the UK output-floor schedule from 60% to 72.5% by 2030 rest on search
summaries or reproductions. The Chilean Pillar 2 phase-in percentage for 2026 and the countercyclical buffer decisions
rest on press reports (the central bank site blocks scripted access); no CMF standalone model-risk standard was found.
The Fed's re-proposal of Basel III in the US has no effective date. Freddie Mac's terms for derived aggregates in a
public site are unconfirmed, so the mortgage cases ship the SBA twin as the publishable path. The EBA dashboard
figures other than those of Q4 2025 are not read at the EBA. The four C's of the positioning are not defined in the
records. The details of each dossier's own unverified list (10 items in dossier 01, 15 in dossier 03) are kept there.

### Sources the notebooks cite

A notebook cites only sources this document lists (`scripts/check_notebooks.py`). Besides the sources named above and in the research
basis, the topic 01 notebooks cite:

- Brown, Cai and DasGupta (2001), Interval estimation for a binomial proportion, https://doi.org/10.1214/ss/1009213286;
- Hanley and McNeil (1982), the meaning and use of the area under a receiver operating characteristic curve,
  https://doi.org/10.1148/radiology.143.1.7063747;
- Spiegelhalter (1986), probabilistic prediction in patient management and clinical trials, https://doi.org/10.1002/sim.4780050506.

The topic 12 (capital and stress) notebooks cite, besides the above, the sources the persisted research verified for the aggregation and
stress layers (dossiers 03, 05 and 06):

- Rosenberg and Schuermann (2006), a general approach to integrated risk management with skewed, fat-tailed risks,
  https://doi.org/10.1016/j.jfineco.2005.03.001;
- Embrechts, Puccetti and Rueschendorf (2013), model uncertainty and VaR aggregation, https://doi.org/10.1016/j.jbankfin.2013.03.014;
- Embrechts, McNeil and Straumann (2002), correlation and dependence in risk management, https://doi.org/10.1017/CBO9780511615337.008;
- Tasche (2007), capital allocation to business units and sub-portfolios: the Euler principle, https://arxiv.org/abs/0708.2542;
- Glasserman and Xu (2014), robust risk measurement and model risk, https://doi.org/10.1080/14697688.2013.822989;
- Barrieu and Scandolo (2015), assessing financial model risk, https://doi.org/10.1016/j.ejor.2014.10.032;
- Glasserman, Kang and Kang (2015), stress scenario selection by empirical likelihood, https://doi.org/10.1080/14697688.2014.926019;
- Adrian, Boyarchenko and Giannone (2019), vulnerable growth, https://doi.org/10.1257/aer.20161923;
- Litterman (1986), forecasting with Bayesian vector autoregressions, https://doi.org/10.1080/07350015.1986.10509491;
- Banbura, Giannone and Reichlin (2010), large Bayesian vector auto regressions, https://doi.org/10.1002/jae.1137;
- the Joint Forum (2010), developments in modelling risk aggregation, https://www.bis.org/publ/joint25.pdf (the wording the dossier takes
  from the press release is UNVERIFIED);
- the EBA 2025 EU-wide stress test Methodological Note of 2025-01-20,
  https://www.eba.europa.eu/sites/default/files/2025-01/0246e2f3-fa57-47d1-99f2-7a5b80cae509/2025%20EU-wide%20stress%20test%20-%20Methodological%20Note.pdf;
- the Federal Reserve, Supervisory Stress Test Model Documentation: Credit Risk Models, Fall 2026,
  https://www.federalreserve.gov/supervisionreg/files/fall-2026-credit-risk-models-description.pdf, and the 2026 severely adverse scenario,
  https://www.federalreserve.gov/supervisionreg/files/2026_Final_Supervisory_Severely_Adverse_Domestic.csv;
- the CMF Annex 3 of the IAPE self-assessment (Circular 2.365), https://www.cmfchile.cl/portal/principal/623/articles-29808_doc_pdf.pdf;
- the NGFS Phase V scenarios, https://www.ngfs.net/en/news/ngfs-scenarios-phase-v-launch-event and
  https://data.ene.iiasa.ac.at/ngfs.

## Sizing and contracts

The design rests on two artifacts of contract-first parallel delivery (ADR-0080): the sizing and the contract catalog.

- **The sizing** is kept with the coordination records outside the product, in CAOS_MANAGE
  ([`plans/contraste/sizing.md`](https://github.com/fsantibanezleal/CAOS_MANAGE/blob/develop/plans/contraste/sizing.md)):
  the four repositories, the components (offline pipeline, engine, static frontend, dormant API, contract set, guards),
  the modules with their owner units, the fourteen boundaries B1 to B14, the technology versions verified on primary
  sources, the machine limits and the parallel units with disjoint write scopes (wave 1 is CF-A to CF-D, wave 2 is U5 to
  U14, wave 3 is U15 and U16). The units of a feature are the sizing's parallel units, built at once against the fixed
  catalog rows.
- **The catalog** is kept here, [`docs/contracts/catalog.md`](../contracts/catalog.md): one row per boundary and per
  model slot, with its version, owner, schema file under `docs/contracts/schemas/`, example, producer and consumer tests,
  missing-data behavior, provider, swap test and status. Its `History` records each version, and
  [`docs/contracts/versions.lock.json`](../contracts/versions.lock.json) holds the digest of every schema, checked by
  `scripts/check_contract_versions.py`. The two contracts of ADR-0057 stay as rows: contract 1 (the eight ingestion
  families) and contract 2 (the case index, the case manifest and the variant and models artifacts); the readiness
  document records, row by row, what is real and what a provider or a baseline serves.

The boundaries of the sizing, in one line each: B1 the source registry to the fetcher; B2 the fetcher to the licence
manifest; B3 the source readers to contract 1; B4 the contract-1 export to the Implementation page and the
bring-your-own-data door; B5 the engine's test functions to the case bakes; B6 and B7 the pipeline export to the
frontend and the API (case index, case manifest); B8 the case bakes to the views (variant envelope plus the case
outputs); B9 the case model fits to the Model and Benchmark views; B10 the C01 rungs to the evaluate stage (model slots
with the benchmark rung as baseline); B11 the readiness document; B12 the committed artifacts and the TypeScript ports
(live parity); B13 the dormant API; B14 each wave 2 case bake to its views (a provider until the case lands).

### Ingestion contracts (contract 1, raw to pipeline), one per source family


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

### Artifact contract (contract 2, pipeline to web)

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

## Technology and versions

Every pinned dependency of the offline lane (`data-pipeline/requirements.txt`, the optional
`data-pipeline/requirements-tabpfn.txt` and `data-pipeline/requirements-ore.txt`), of `requirements-dev.txt` and of `frontend/package.json`, with the version
actually pinned or locked; `scripts/check_tech_matrix.py` fails when a pin and this table disagree. A `package.json`
range is recorded at the version `frontend/package-lock.json` resolves it to. The runtimes are Python 3.13.14 on the
development workstation and 3.12 in CI, and Node 22 in CI (24.14.1 on the workstation). The full evaluation of every
tool, with its primary source and verification date, is the technology matrix of the sizing; the alternatives below are
the ones the dossiers and `docs/frameworks/` record.

| component | package | version | use | alternative considered |
|---|---|---|---|---|
| engine | numpy | 2.4.6 | arrays, the generators and every estimator | none: the base of the stack (2.5.4 is current and was not adopted in 0.07.000) |
| engine | scipy | 1.18.1 | distributions and special functions; the reference for every test statistic | none recorded |
| data | pandas | 3.0.6 | tabular reading, the splits and the case frames | none recorded |
| data | xlrd | 2.0.2 | reading the legacy Excel files of the UCI Taiwan dataset | none recorded |
| models | scikit-learn | 1.9.1 | penalised logistic regression, splits, isotonic and Platt calibration | none recorded |
| models | statsmodels | 0.15.0 | the maximum-likelihood logistic scorecard with inference | none recorded |
| models | optbinning | 1.0.0 | monotone optimal binning and WoE for the scorecard | scorecardpy, toad and skorecard, rejected: unmaintained on PyPI or heuristic binning (docs/frameworks) |
| models | interpret-core | 0.7.8 | the EBM (GA2M) challenger with monotone shape functions | none recorded |
| models | lightgbm | 4.7.0 | the monotone gradient-boosted challenger | xgboost as the second boosting engine on the same constraints |
| models | xgboost | 3.4.1 | the second gradient-boosting engine, to show the gain is a property of the data | none recorded |
| models | catboost | 1.2.10 | the gradient-boosted LGD challenger of case C08 (U6 sizing technology matrix) | lightgbm on the same features |
| models | shap | 0.52.0 | reason codes and explanation stability of the boosted rung | none recorded (0.53.0 is current and was not adopted) |
| data | pypdf | 6.19.0 | reading the published tables of the papers (Tasche, Pluto and Tasche, BCBS WP14) | none recorded (6.20.0 is current and was not adopted) |
| data | openpyxl | 3.1.5 | reading the EBA/ESRB 2025 macro-financial scenario workbook of C18 (U13 decision Q15; MIT) | none recorded |
| reference (optional) | open-source-risk-engine | 1.8.17.0 | ORE, run natively from its Windows wheel as the reference engine of the C12 exposure reconciliation (`data-pipeline/requirements-ore.txt`, U9 decision D4); pipeline only, never an engine dependency | none: ORE is the open reference engine the dossiers name |
| reference (optional) | QuantLib | 1.44 | the independent check of the Hull-White closed forms in C12 (`data-pipeline/requirements-ore.txt`, U9 decision B4); pipeline only | none recorded |
| engine | riskvalidation | 0.8.1 | the validation tests, regulatory calculators and generators (the PyPI release of the batch 3 engine, tag v0.08.001, 0.8.1 (0.8.0 with the fairness metric rows at null alphas): liquidity, aggregation and stress testing, the regulatory calculators and counterparty credit risk, ML model validation and fair lending) | none: no toolkit implements the ECB tests as specified |
| models (optional) | torch | 2.14.1 | CPU runtime of the TabPFN extra, outside the default install | none recorded |
| models (optional) | tabpfn | 9.1.0 | the TabPFN challenger of the small cases, weights under the Prior Labs License | none recorded |
| notebooks | matplotlib | 3.11.2 | the figures of the notebooks (`notebooks/requirements.txt`) | none recorded |
| notebooks | nbclient | 0.11.0 | executes the notebooks top to bottom in a fresh kernel (`scripts/run_notebooks.py`, a local release gate) | none recorded |
| notebooks | nbformat | 5.11.1 | reads and writes the notebook documents of the runner | none recorded |
| notebooks | ipykernel | 7.4.0 | the kernel the notebooks run in | none recorded |
| tests | pytest | 9.1.1 | the pipeline, contract, guard and adversarial tests | none recorded |
| lint | ruff | 0.15.18 | lint of data-pipeline, tests, scripts and app | none recorded (0.17.0 is current and was not adopted) |
| contracts | jsonschema | 4.26.0 | validates every document against its schema file | none recorded |
| shell | @fasl-work/caos-app-shell | 0.15.0 | the shared app shell, pinned exactly (ADR-0078) | a hand-rolled shell, forbidden by ADR-0078 |
| web | react | 19.3.0 | the UI | none: the shell requires it |
| web | react-dom | 19.3.0 | the UI renderer | none: the shell requires it |
| web | react-router | 8.4.0 | the six routes | none: the shell requires it |
| web | zustand | 5.0.15 | the workbench selection store | none recorded |
| web | katex | 0.16.47 | typeset equations on the Methodology pages | none recorded (0.19.0 is current and was not adopted) |
| web | lucide-react | 1.52.0 | icons | none recorded |
| web | uplot | 1.6.32 | the interactive curves | none recorded |
| build | vite | 8.3.2 | bundler and dev server | none recorded |
| build | @vitejs/plugin-react | 6.1.1 | the React transform for vite | none recorded |
| build | typescript | 5.9.3 | type check of the web and the generated contract types | none recorded (7.0.2 is a major change and was not adopted) |
| build | openapi-typescript | 7.13.0 | generates `contract.gen.ts` from the OpenAPI document built from the schema files | hand-written types, rejected: they drift (the generation step fails when they are not current) |
| build | @redocly/ajv | 8.11.2 | the strict validator of the contract generator, pinned exactly | none recorded |
| build | @types/node | 24.19.1 | types of the build scripts | none recorded |
| build | @types/react | 19.3.0 | types of React | none recorded |
| build | @types/react-dom | 19.3.0 | types of React DOM | none recorded |
| tests | vitest | 5.0.3 | the web unit tests and the adversarial web plants | none recorded |
| gate | playwright | 1.63.0 | the measured UI gate (`npm run gate`), local only | none recorded |

## Resources

What each stage needs on the development workstation (Windows 11, 2026-10-12; Python 3.13.14, Node 24.14.1; 16 GB of RAM
free at the preflight of 2026-10-11; no GPU is used by any stage listed). Every value was measured by running the
command in the `where it runs` column's first cell with the process tree polled every 20 ms: memory is the largest
summed working set of the tree, time is the wall clock, disk is what the stage leaves behind. The commands and their
outputs are in the CF-D report. Bakes were run with `--output` into a temporary root, so `data/derived/` is never
touched; raw data are read from the device data root (`CONTRASTE_DATA`) and are not counted in the disk column.

| stage | memory | disk | time | where it runs |
|---|---|---|---|---|
| fetch (`data-pipeline/fetch.py uci-german`, one source; all sources are bounded by CEREP's pacing of at least four seconds per request, CT-401) | 44 MB peak | 29,607 bytes in the device data root | 1.2 s | workstation with network, never CI |
| bake C01 (`data-pipeline/run.py C01`, every rung trained, seven variants) | 634 MB peak | 2,064,356 bytes of artifacts | 183.7 s | workstation, never CI |
| bake C04 (`run.py C04`, nine variants: three agencies, five families, the papers) | 157 MB peak | 856,267 bytes | 296.4 s | workstation, never CI |
| bake C05 (`run.py C05`, six variants) | 212 MB peak | 561,195 bytes | 32.0 s | workstation, never CI |
| bake C22 (`run.py C22`, the size and power runs of all eight variants, at least 4,000 repetitions per test) | 231 MB peak | 523,182 bytes | 1,096.8 s | workstation, never CI |
| tests (`pytest tests`, 385 passed and 2 skipped: the pipeline, contract, guard and bake-artifact tests) | 435 MB peak (300 MB the largest process) | none outside the temporary directory | 125.6 s | workstation, never CI |
| tests (`pytest tests/adversarial`, the plants of this document's validation files, including two browser-gate plants) | 677 MB peak (282 MB the largest process) | temporary copies of the repository's committed files, about 10 MB each | 1,344.9 s for 88 plants (the two gate plants take 424 s, the leakage plants 30 to 186 s each) | workstation; the Python plants alone also fit CI (ADR-0074) |
| tests (`npm test` in `frontend/`, 22 files, 560 tests) | 1,872 MB peak summed over the vitest workers (294 MB the largest process) | none | 3.9 s | workstation and CI web job |
| build (`npm run build`, the four built cases, measured in a copy whose index lists them: the branch's own index lists 22 and its build stops before the web reads the readiness) | 566 MB peak | 6,727,923 bytes in `frontend/dist`, 123 files | 16.0 s | workstation and CI web job |
| gate (`npm run gate`, every route, tab, sub-tab and case at five sizes, both themes and both languages, on that build) | 910 MB peak | 14,285,565 bytes of captures in `gate-output` | 427.4 s, 868 measured states | workstation, never CI |
| deploy payload (GitHub Pages) | none | at most 7.7 MB: the 6,727,923 bytes measured for the four built cases plus under 1 MB for the provider documents of the 18 planned cases (36 empty-envelope files; the one example in `docs/contracts/fixtures` is 368 bytes) | at most the 15-minute timeout of the CI web job; one Pages deploy after CI on main | CI after main |

## Lanes

- **Offline (canonical).** `.venv-pipeline` with the pinned engines (optbinning, scikit-learn, LightGBM, XGBoost,
  CatBoost, InterpretML, SHAP, lifelines, statsmodels, arch, QuantLib, pyvinecopulib, MAPIE, fairlearn; ORE 1.8.17.0
  natively (its CPython 3.13 Windows wheel, in `data-pipeline/requirements-ore.txt`, pipeline-only);
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

## Method ladder

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

## Cases

### Coverage and variants

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
| C22 | the null family; defect severity 0 to 5 for each of seven defect families (miscalibration, default clustering, drift, discrimination decay, leakage, broken monotonicity, concentration) | independent seeded repetitions, one random stream each; every rate with its Monte Carlo error |

Why each category exists: credit-scoring (the most common model and the validator's daily work),
ratings-calibration (the IRB core and the low-default reality), provisions (IFRS 9 and the Chilean carve-out),
lgd-ead (the other two parameters), portfolio-capital (what Pillar 1 ignores and ICAAP must cover), market-ccr
(VaR/ES, exposure, FRTB), balance-sheet (IRRBB and liquidity, the 2023 lessons), operational (why AMA went away),
capital-stress (ICAAP, IAPE, supervisory models), ml-ai-risk (ML validation and fairness), validator (the size and
power of the tests).

### Web companion

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
  case is, its data and licence, its limits). Each view carries its lane badge; nothing is cross-case. Since shell 0.14.0 the App offers Focus mode (`CaseWorkbench`'s `focus`, ADR-0070): a Focus button in the rail head opens the open group of the selected case in the full viewport (`?focus=1` beside `?case=` and `?view=`), and Escape or the exit button returns to the same case, group and sub-view; the measured gate runs with `--require-focus` and visits Focus mode for every case (G18).
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

### Requirements map

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
| U3 | `docs/design/features/c22-validator/` | CT-301 to CT-313: the size of every test with a p-value on its null; power against seven planted defects at severities 0 to 5; exact rejection probabilities beside the simulated ones; WP14, Yurdakul-Naranjo and Demler et al. reproduced cell by cell; findings evidenced by measured rates; known truth and determinism; expected ranges; the live exact size and power at parity; the C22 instrument; the measured gate; C05 on the engine's generator; C01's Hosmer-Lemeshow with G degrees of freedom and its AUC test with the development variance |
| engine | `CAOS_RiskValidation` `docs/design/` | RV-001 to RV-007 (the `TestResult` record, the policy, the suite runner) and RV-101 to RV-114 (PD and stability tests), converged in `riskvalidation` 0.01.000; RV-901 (regulatory parameters with paragraph and in-force date) lands in U9 |

## Oracles

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

## Beyond the state of the art

A component of Contraste that goes further than the practice its research found enters this section with the topic unit that
demonstrates it: an identifier of the form BS-<n>, the committed evidence a reader can open, the practice it goes beyond, and a level 4
notebook in each language (`notebooks/`, CAOS_MANAGE `conventions/product-notebooks.md`). A claim is stated only as far as its evidence
goes, and no claim is stated before its demonstration exists. The claims enter one by one with their topic units.

- **BS-9** The dependence band shown with every aggregate.
  What it adds: every aggregate capital figure of C18 is shown with the band of aggregation methods over the same marginals, one
  horizon and one confidence level, and never as one diversified number: the lower bound, the simple sum (the only row labelled headline
  capital), the square-root rule, the Gaussian copula, one t copula for each degree of freedom of the named set and the sharp worst case
  by the rearrangement algorithm, in that order, with every row but the headline labelled information and not capital. The Euler
  allocation of the aggregate expected shortfall adds up to it, and the model-risk measures of the band are labelled information too.
  Evidence: `data/derived/C18/baseline.json`, `data/derived/C18/eba-2025-adverse.json`, `data/derived/C18/fed-2026-severely-adverse.json`
  and `data/derived/C18/ngfs-delayed-transition.json` (`outputs.aggregation.band`, eight rows in each), `data/derived/C18/t-copula-baseline.json`
  (the band again and the band under the market-credit correlation stress), `docs/design/features/c18/requirements.md` (CT-1811 and
  CT-1812, each with its gate), and the engine's `riskvalidation.aggregation.band.dependence_band`, which returns the whole band and
  never a scalar. Notebook 09 of topic 12 checks the structure and recomputes the closed-form rows of all six committed aggregates;
  notebook 03 reproduces the engine's published worst-case example (the rearrangement bounds of eight Pareto marginals) and checks the
  band's structure and ordering on stand-in marginals.
  Beyond: the research (dossier 05, G.3) prescribes the band, "instead of a single diversified number", and warns against claiming that
  diversification benefits are robust; Rosenberg and Schuermann report the sensitivity of the aggregate to the copula choice and the
  additive overestimate of 30 to 40 percent as a study result (https://doi.org/10.1016/j.jfineco.2005.03.001); Embrechts, Puccetti and
  Rueschendorf give the sharp worst-case bounds (https://doi.org/10.1016/j.jbankfin.2013.03.014); the Joint Forum found aggregation models
  "a work in progress" on which supervisors generally do not rely (https://www.bis.org/publ/joint25.pdf, the wording is UNVERIFIED in the
  dossier). Those are the ingredients and the recommendation; what the case adds is to compose them and show the band with every aggregate
  as a gated rule. The claim is about what the case does: that no maintained toolkit or published practice ships the band beside every
  aggregate is UNVERIFIED beyond the dossier's own search. The committed band rests on marginals that the pipeline simulates and does not
  commit (only their EL, VaR, ES and EC), and Banco Andino is synthetic.

## Deploy driver

One place only, decided in the plan: **`github-pages` with a `CNAME` on `contraste.fasl-work.com`**
(`deploy/TARGET` = `pages`, checked by `scripts/check_deploy_place.py`; the template's VPS files were removed at
instantiation). Driver: the repository is public and every web capability is static replay or client-side compute;
no ADR-0002 backend trigger exists (no server state, no private data, no request-time compute). Measured guard at
every release: the published site under GitHub Pages' 1 GB limit and every committed file under 100 MB
(`scripts/check_artifacts.py`); Pyodide is loaded from its CDN, not from the bundle. The Pyodide cold start with
`riskvalidation` loaded (median of 5, cold cache) is measured to admit live features (`Lanes`), not to choose the
host. The deploy runs only after CI passes on `main` and ends with `scripts/check_live.py` against the published
site.

## Risks and kill criteria

| Risk | Kill or re-scope criterion |
|---|---|
| Freddie Mac terms do not allow derived aggregates in a public web | C06 and C08 publish the SBA twin; Freddie Mac results stay offline |
| Pyodide cold start too slow | live features move to TypeScript ports with parity tests, or to replay only, per measurement |
| ORE 1.8.17.0 will not install or run on the workstation | C12 uses QuantLib plus the analytic HW1F check only, and its ORE reconciliation rows are `not_evaluated` with the error, stated |
| A golden value cannot be reproduced | the method or test is not shipped until it is |
| Scope (22 cases, 17 units) | units ship vertically; nothing is presented as done until the convergence verdict |
| Licence contamination | `scripts/check_licences.py` fails on AGPL, GPL or BSL in the default install |
| A committed file carries rows a licence forbids | `scripts/check_data_classes.py` fails the build |
| The site looks right and is not (a blank chart, a dead control, a broken deep link) | the measured gate (`npm run gate`) fails before a deploy |

## ADR fit

Every ADR and convention that binds Contraste was evaluated against what Contraste is (a workbench that builds and
validates financial risk models, 22 cases, an engine package, a static web companion) before any code (2026-10-04).
Where an ADR did not fit, the ADR was amended first and the base (the shared shell and the template) was fixed to
carry the amended rule, with a gate (ADR-0078, "rules live in the base"); Contraste then instantiated the fixed
template and makes no structural edits outside its core.

Where the ADRs fit as written:

| ADR / convention | Fit, and what carries it here |
|---|---|
| ADR-0057 product archetype (offline pipeline, two contracts, named stages, static replay, lane gate) | fits: Contraste is offline-heavy with a static companion; `data-pipeline/`, `Sizing and contracts` |
| ADR-0069 full scientific repository | fits: every model rung and every validation test is a vertical with engine, tests, docs and lane (`Method ladder`) |
| ADR-0075 SDD before development | fits: this document; `scripts/check_sdd.py` |
| ADR-0058 architecture modal (at least five themed tabs) | fits: `frontend/src/architecture/`, validated by the shell on mount |
| ADR-0056 `docs/` wiki | fits: engine and product wikis, authored per unit from the dossiers |
| ADR-0011 and ADR-0012 i18n and theming | fits: the shell; every string is bilingual |
| ADR-0061 and the no-internal-packages rule | fits: `riskvalidation` is the separate engine repository; this product declares no package |
| ADR-0065 to ADR-0068 community files, English, no em-dash, versioning | fit: `scripts/check_content_standards.py`, `scripts/check_version_coherence.py` |
| ADR-0074 CI budget | fits: the product CI runs no pipeline suite; the engine's unit tests are cheap and run in its own CI |
| Product quality bar, section 0 (one selected case on App, real action capability, honesty) | fits strongly: thresholds, policy, segments, windows and scenario weights are real live inputs |
| Units gate | applies from the second observable on: PD in (0, 1), LGD in [0, 1], CCF by stated convention, VaR and ES in the portfolio's units |
| One deploy place | fits: GitHub Pages (`Deploy driver`) |

Where they did not fit, and the amendment now in force:

| # | ADR text | Why it failed for Contraste | Amendment, and what carries it |
|---|---|---|---|
| 1 | ADR-0016 9.A: the App is a top-level `Tabs` strip, one tab per case | 22 cases would be 22 tabs; ADR-0071 caps peers near six and makes a categorised one-of-N a `select` with `optgroup` | cases are chosen with the shell's `CaseSelector`, grouped by category, a `select` with `optgroup` beyond the chip budget |
| 2 | ADR-0016 9.A: four fixed sub-tabs Field, Live, Charts, Context | the instrument is itself several questions (the model, its validation, its impact, the findings); a separate Live tab assumes a live engine distinct from the replay | ONE tab row of at most six groups named for the user's question (`Web companion` under `Cases`); the live lane is a property of each view (lane badge and live controls) |
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
