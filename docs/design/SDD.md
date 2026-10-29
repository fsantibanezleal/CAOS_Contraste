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

The topic 02 notebooks (credit scoring, unit U17-B) cite, in addition:

- Navas-Palencia (2020), optimal binning, weight of evidence and information value, https://arxiv.org/abs/2001.08025;
- Siddiqi (2017), Intelligent Credit Scoring, https://doi.org/10.1002/9781119282396, and the open `skorecard` implementation of its
  points scaling, https://github.com/ing-bank/skorecard/blob/main/skorecard/rescale/rescale.py;
- DeLong, DeLong and Clarke-Pearson (1988), correlated ROC curves, https://doi.org/10.2307/2531595;
- the SBA 7(a) FOIA loan data, https://data.sba.gov/dataset/7a-504-foia;
- the UCI Polish companies bankruptcy data, https://archive.ics.uci.edu/dataset/365/polish+companies+bankruptcy+data, DOI
  https://doi.org/10.24432/C5F600, and the UCI Statlog German credit data, https://archive.ics.uci.edu/dataset/144/statlog+german+credit+data;
- the credit-scoring benchmarks and challengers of dossier 04: Baesens et al. (2003), https://doi.org/10.1057/palgrave.jors.2601545;
  Dumitrescu, Hue, Hurlin and Tokpavi (2022), https://doi.org/10.1016/j.ejor.2021.06.053; Lou, Caruana, Gehrke and Hooker (2013),
  https://doi.org/10.1145/2487575.2487579; van den Goorbergh et al. (2022), https://doi.org/10.1093/jamia/ocac093; King and Zeng (2001),
  https://doi.org/10.1093/oxfordjournals.pan.a004868; Zadrozny and Elkan (2002), https://doi.org/10.1145/775047.775151;
  the monotone-constraint documentation of XGBoost, https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html, and of LightGBM,
  https://lightgbm.readthedocs.io/en/latest/Parameters.html; the TabPFN project and its weights licences, https://github.com/PriorLabs/TabPFN;
- Kozodoi et al. (2025), sampling bias in the training and the evaluation of credit scoring models, https://doi.org/10.1016/j.ejor.2025.01.040.

The topic 04 notebooks (provisions) cite, from dossiers 02 and 03 of the persisted research:

- IASB, IFRS 9 Financial Instruments as endorsed by Commission Regulation (EU) 2016/2067,
  https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32016R2067;
- Botha and Verster (2025), the term-structure of default risk under IFRS 9 by discrete-time survival analysis,
  https://arxiv.org/abs/2507.15441, and Botha, Verster and Breedt (2025), the multistate framework, https://arxiv.org/abs/2502.14479;
- GPPC (2016), The implementation of IFRS 9 impairment requirements by banks,
  https://www.globalpublicpolicycommittee.org/wp-content/uploads/2022/12/gppc-ifrs9-implementation-considerations-20160617.pdf;
- BCBS (2015), Guidance on credit risk and accounting for expected credit losses (d350), https://www.bis.org/bcbs/publ/d350.htm;
- EBA (2023), IFRS 9 implementation by EU institutions, 2023 monitoring report, EBA/Rep/2023/36,
  https://www.eba.europa.eu/sites/default/files/2023-11/25b12d35-9c28-4335-a589-166c77198920/Final%20Report%20on%20IFRS9%20implementation%20by%20EU%20institutions.pdf,
  and EBA (2021), EBA/Rep/2021/35,
  https://www.eba.europa.eu/sites/default/files/document_library/Publications/Reports/2021/1024609/IFRS9%20monitoring%20report.pdf;
- ECB Banking Supervision (2024), IFRS 9 overlays and model improvements for novel risks,
  https://www.bankingsupervision.europa.eu/ecb/pub/pdf/ssm.IFRS9novelrisks_202407~5e0eb30b5c.en.pdf;
- BCBS (2005), An explanatory note on the Basel II IRB risk weight functions,
  https://www.bis.org/publications/explanatory-note-basel-ii-irb-risk-weight-functions.pdf, and Gordy (2003), a risk-factor model
  foundation for ratings-based bank capital rules, https://doi.org/10.1016/S1042-9573(03)00040-8;
- Anderson and Goodman (1957), statistical inference about Markov chains, https://doi.org/10.1214/aoms/1177707039;
- Shumway (2001), forecasting bankruptcy more accurately: a simple hazard model, https://doi.org/10.1086/209665;
- Cox (1972), regression models and life-tables, https://doi.org/10.1111/j.2517-6161.1972.tb00899.x; Fine and Gray (1999), a
  proportional hazards model for the subdistribution of a competing risk, https://doi.org/10.1080/01621459.1999.10474144; Breeden
  (2016), lifecycle and environment in loan-level forecasts and stress tests, https://doi.org/10.1016/j.ejor.2016.06.008;
- ECB Banking Supervision (2020), IFRS 9 in the context of the coronavirus pandemic, letter of 1 April 2020,
  https://www.bankingsupervision.europa.eu/press/letterstobanks/shared/pdf/2020/ssm.2020_letter_IFRS_9_in_the_context_of_the_coronavirus_COVID-19_pandemic~4cab8e5650.en.pdf;
- CMF Chile, Compendio de Normas Contables para Bancos (CNCB),
  https://www.cmfchile.cl/portal/normativa/624/articles-29177_doc_pdf.pdf;
- Banco de España, Circular 4/2017 (https://www.boe.es/buscar/act.php?id=BOE-A-2017-14334) and Circular 6/2021
  (https://www.boe.es/buscar/doc.php?id=BOE-A-2021-21666).

The topic 07 notebooks (market risk, cases C11 and C13) also cite the following, all taken from the persisted research (dossiers 01 and
05) and from the engine's own reference strings:

- Kupiec (1995), https://doi.org/10.3905/jod.1995.407942; Christoffersen (1998), https://doi.org/10.2307/2527341; Christoffersen and
  Pelletier (2004), https://doi.org/10.1093/jjfinec/nbh004; Engle and Manganelli (2004), https://doi.org/10.1198/073500104000000370;
- Basel Committee (1996), the backtesting framework, https://www.bis.org/publ/bcbs22.htm;
- Du and Escanciano (2017), https://doi.org/10.1287/mnsc.2015.2342; McNeil and Frey (2000), https://doi.org/10.1016/S0927-5398(00)00012-8;
  Moldenhauer and Pitera on the Acerbi-Szekely reference point, https://arxiv.org/abs/1709.01337;
- Patton, Ziegel and Chen (2019), https://doi.org/10.1016/j.jeconom.2018.10.008 and https://arxiv.org/abs/1707.05108; Taylor (2019),
  https://doi.org/10.1080/07350015.2017.1281815; the neural joint VaR and ES preprint, https://arxiv.org/abs/2606.04576;
- Gneiting (2011), https://doi.org/10.1198/jasa.2011.r10138; Fissler and Ziegel (2016), https://doi.org/10.1214/16-AOS1439; Diebold and
  Mariano (1995), https://doi.org/10.1080/07350015.1995.10524599; Hansen, Lunde and Nason (2011), https://doi.org/10.3982/ECTA5771;
  Nolde and Ziegel (2017), https://doi.org/10.1214/17-AOAS1041; Kratz, Lok and McNeil (2018), https://doi.org/10.1016/j.jbankfin.2018.01.002;
- Pritsker (2001), https://www.federalreserve.gov/Pubs/feds/2001/200127/200127pap.pdf; Boudoukh, Richardson and Whitelaw (1998),
  https://pages.stern.nyu.edu/~rwhitela/papers/hybrid%20risk98.pdf; the RiskMetrics Technical Document (1996),
  https://www.msci.com/documents/10199/5915b101-4206-4ba0-aee2-3449d5c7e95a; Cornish and Fisher (1938), https://doi.org/10.2307/1400905;
  Bollerslev (1986), https://doi.org/10.1016/0304-4076(86)90063-1; Glosten, Jagannathan and Runkle (1993),
  https://doi.org/10.1111/j.1540-6261.1993.tb05128.x; Nelson (1991), https://doi.org/10.2307/2938260; Hull and White (1998),
  https://doi.org/10.21314/JOR.1998.001.

The topic 11 (operational risk) notebooks cite, besides the BIS d424 page above:

- BCBS (2009), Results from the 2008 Loss Data Collection Exercise for Operational Risk, https://www.bis.org/publ/bcbs160.htm;
- BCBS (2016), Standardised Measurement Approach for operational risk, consultative document, https://www.bis.org/bcbs/publ/d355.htm;
- Basel Framework, OPE25, Calculation of RWA for operational risk (the standardised approach), https://www.bis.org/basel_framework/chapter/OPE/25.htm;
- Shevchenko (2010), Calculation of aggregate loss distributions, J. Operational Risk 5(2), https://arxiv.org/abs/1008.1108 and
  https://doi.org/10.21314/JOP.2010.077;
- Shevchenko and Wuthrich (2006), The structural modeling of operational risk via Bayesian inference, https://doi.org/10.21314/JOP.2006.016;
- Panjer (1981), Recursive evaluation of a family of compound distributions, https://doi.org/10.1017/S0515036100006796;
- Chavez-Demoulin, Embrechts and Neslehova (2006), Quantitative models for operational risk, https://doi.org/10.1016/j.jbankfin.2005.11.008;
- Mignola and Ugoccioni (2007), Effect of a data collection threshold in the loss distribution approach,
  https://doi.org/10.21314/JOP.2006.019;
- Degen (2010), The calculation of minimum regulatory capital using single-loss approximations, https://doi.org/10.21314/JOP.2010.084;
- Peters, Shevchenko, Hassani and Chapelle (2016), Should the advanced measurement approach be replaced with the standardized
  measurement approach for operational risk?, https://arxiv.org/abs/1607.02319;
- Mignola, Ugoccioni and Cope (2016), Comments on the Basel Committee proposal for a new standardized approach for operational risk,
  https://doi.org/10.21314/JOP.2016.184.

The topic 10 (liquidity) notebooks cite, from the research dossier 05 (section E) and the research addendum of the liquidity unit:

- ECB Banking Supervision (2019), Sensitivity analysis of liquidity risk, stress test 2019, methodological note (2019-02-06),
  https://www.bankingsupervision.europa.eu/ecb/pub/pdf/ssm.ECB_sensitivity_analysis_of_liquidity_risk-stress_test_2019-methodological_note_20190206~6771e88926.en.pdf,
  and its results annex (2019-10-07), https://www.bankingsupervision.europa.eu/press/pr/date/2019/html/ssm.pr191007_annex~537c259b6d.en.pdf;
- BCBS (2008), Principles for sound liquidity risk management and supervision, Principle 10, https://www.bis.org/publ/bcbs144.htm;
- BCBS (2023), Report on the 2023 banking turmoil, Box A and Table A.1, https://www.bis.org/bcbs/publ/d555.htm;
- Federal Reserve Board (2023-04-28), Review of the Federal Reserve's Supervision and Regulation of Silicon Valley Bank,
  https://www.federalreserve.gov/publications/files/svb-review-20230428.pdf;
- Federal Reserve discount window, margins in force from 2022-03-14 to 2023-03-12,
  https://www.frbdiscountwindow.org/generalpages/historical_margins/2022/03142022_03122023_securities_table;
- the Basel Framework, LCR standard (LCR20 to LCR99), https://www.bis.org/committees/bcbs/basel-framework/standard/lcr, and NSFR standard
  (NSF20 to NSF99), https://www.bis.org/committees/bcbs/basel-framework/standard/nsf/99/inforce/2019-12-15/published/2019-12-15;
- Diamond and Dybvig (1983), bank runs, deposit insurance, and liquidity, https://doi.org/10.1086/261155;
- Cookson, Fox, Gil-Bazo, Imbet and Schiller (2026), social media as a bank run catalyst, https://doi.org/10.1016/j.jfineco.2025.104218;
- Jiang, Matvos, Piskorski and Seru (2024), monetary tightening and U.S. bank fragility in 2023: mark-to-market losses and uninsured depositor runs, https://doi.org/10.1016/j.jfineco.2024.103899.

The topic 08 notebooks (counterparty credit risk and the regulatory calculators) cite, besides those:

- BCBS, Basel Framework, CRE52 Standardised approach to counterparty credit risk (in force 2023-01-01, published 2020-06-05). https://www.bis.org/committees/bcbs/basel-framework/standard/cre/52/inforce/2023-01-01/published/2020-06-05
- BCBS, Basel Framework, CRE53 Internal model method for counterparty credit risk (in force 2023-01-01, published 2020-06-05). https://www.bis.org/basel_framework/chapter/CRE/53.htm?inforce=20230101&published=20200605
- BCBS, Basel Framework, CRE99 Illustrative examples of the standardised approach to counterparty credit risk (in force 2023-01-01). https://www.bis.org/committees/bcbs/basel-framework/standard/cre/99/inforce/2023-01-01/published/2020-03-27
- BCBS, Basel Framework, CRE20 Standardised approach: individual exposures (in force 2023-01-01, published 2025-06-10). https://www.bis.org/committees/bcbs/basel-framework/standard/cre/20/inforce/2023-01-01/published/2025-06-10
- BCBS, Basel Framework, MAR50 CVA risk framework (in force 2023-01-01, published 2020-07-08). https://www.bis.org/committees/bcbs/basel-framework/standard/mar/50/inforce/2023-01-01/published/2020-07-08
- BCBS, Basel Framework, MAR21 Standardised approach: sensitivities-based method (in force 2023-01-01). https://www.bis.org/committees/bcbs/basel-framework/standard/mar/21/inforce/2023-01-01/published/2026-03-23
- BCBS, Basel Framework, RBC20 Calculation of minimum risk-based capital requirements (in force 2023-01-01, published 2020-11-26). https://www.bis.org/committees/bcbs/basel-framework/standard/rbc/20/inforce/2023-01-01/published/2020-11-26
- BCBS, Basel Framework, RBC90 Transitional arrangements and the output floor phase-in (in force 2023-01-01). https://www.bis.org/committees/bcbs/basel-framework/standard/rbc/90/inforce/2023-01-01/published/2020-03-27
- BCBS (2010), Sound practices for backtesting counterparty credit risk models, publication 185. https://www.bis.org/publ/bcbs185.htm
- Hull, J. and White, A. (2012), CVA and wrong way risk, Financial Analysts Journal 68(5), 58-69. https://doi.org/10.2469/faj.v68.n5.6
- Hull, J. and White, A. (1990), Pricing interest-rate-derivative securities, Review of Financial Studies 3(4), 573-592. https://doi.org/10.1093/rfs/3.4.573
- Brigo, D., Dalessandro, A., Neugebauer, M. and Triki, F. (2008), A stochastic processes toolkit for risk management, arXiv 0812.4210. https://arxiv.org/abs/0812.4210
- Formenti, L., Spadafora, L., Terraneo, F. and Ramponi, A., Probability integral transform and Anderson-Darling backtests, arXiv 1505.04593. https://arxiv.org/abs/1505.04593
- Andersen, L., Pykhtin, M. and Sokol, A. (2017), Rethinking the margin period of risk, Journal of Credit Risk 13(1). https://doi.org/10.21314/JCR.2016.218
- Open Source Risk Engine, Methodology, value adjustments and margin period of risk (xva.tex at tag 1.8.17.0). https://github.com/OpenSourceRisk/Engine/blob/1.8.17.0/Docs/UserGuide/methods/xva.tex
- Open Source Risk Engine (ORE), release 1.8.17.0. https://github.com/OpenSourceRisk/Engine
- QuantLib, the open-source quantitative finance library. https://github.com/lballabio/QuantLib
- U.S. Department of the Treasury, Daily Treasury Par Yield Curve Rates. https://home.treasury.gov/resource-center/data-chart-center/interest-rates/
- U.S. Department of the Treasury, High Quality Market (HQM) Corporate Bond Yield Curve. https://home.treasury.gov/data/treasury-coupon-issues-and-corporate-bond-yield-curve/corporate-bond-yield-curve

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

The topic 13 notebooks (ML and AI risk) cite, in the same way, the sources below. Each is printed by a persisted research dossier or addendum
(model risk and validation, credit risk models, the fair-lending addendum), and none is cited for more than what its line says:

- ECB (2019), Instructions for reporting the validation results of internal models: IRB Pillar I models for credit risk, Annex 1 (the AUC and its variance). https://www.bankingsupervision.europa.eu/activities/internal_models/shared/pdf/instructions_validation_reporting_credit_risk.en.pdf;
- ING (2026), probatus, `sample_similarity`: a resemblance model between two datasets. https://github.com/ing-bank/probatus;
- EBA (2023), Follow-up report on machine learning for IRB models, EBA/REP/2023/28. https://www.eba.europa.eu/sites/default/files/document_library/Publications/Reports/2023/1061483/Follow-up%20report%20on%20machine%20learning%20for%20IRB%20models.pdf;
- Yeh, I-C. and Lien, C-H., Default of credit card clients, UCI Machine Learning Repository (CC BY 4.0), the Taiwan cards of the C20 variants. https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients;
- PiML-Toolbox (Apache-2.0), outcome tests WeakSpot, Overfit, Reliability, Robustness and Resilience; Sudjianto et al. (2023), arXiv 2305.04214. https://github.com/SelfExplainML/PiML-Toolbox;
- ECB (2025), Guide to internal models, the paragraphs on the randomness of the training process, overfitting, explainability and the justification of complexity (43, 59, 60, 62, 64 to 66). https://www.bankingsupervision.europa.eu/ecb/pub/pdf/ssm.supervisory_guide202507.en.pdf;
- Phipson, B. and Smyth, G. K. (2010), Permutation p-values should never be zero, Statistical Applications in Genetics and Molecular Biology 9(1). https://doi.org/10.2202/1544-6115.1585;
- Board of Governors of the Federal Reserve System, supervisory stress test scenarios and methodology data (public domain), the three corporate portfolios of 2025. https://www.federalreserve.gov/supervisionreg/dfa-stress-tests-2026.htm;
- Lundberg, S. M. and Lee, S.-I. (2017), A unified approach to interpreting model predictions, NeurIPS, arXiv 1705.07874. https://arxiv.org/abs/1705.07874;
- Lundberg, S. M. et al. (2020), From local explanations to global understanding with explainable AI for trees, Nature Machine Intelligence 2(1). https://doi.org/10.1038/s42256-019-0138-9;
- Friedman, J. H. (2001), Greedy function approximation: a gradient boosting machine, Annals of Statistics 29(5). https://doi.org/10.1214/aos/1013203451;
- Goldstein, A., Kapelner, A., Bleich, J. and Pitkin, E. (2015), Peeking inside the black box: visualizing statistical learning with plots of individual conditional expectation, Journal of Computational and Graphical Statistics 24(1). https://doi.org/10.1080/10618600.2014.907095;
- Apley, D. W. and Zhu, J. (2020), Visualizing the effects of predictor variables in black box supervised learning models, Journal of the Royal Statistical Society B 82(4). https://doi.org/10.1111/rssb.12377;
- Angelopoulos, A. N. and Bates, S. (2021), A gentle introduction to conformal prediction and distribution-free uncertainty quantification, arXiv 2107.07511. https://arxiv.org/abs/2107.07511;
- Vovk, V., Gammerman, A. and Shafer, G. (2022), Algorithmic Learning in a Random World, 2nd edition, Springer, https://doi.org/10.1007/978-3-031-06649-8;
- NannyML, how confidence-based performance estimation (CBPE) works. https://nannyml.readthedocs.io/en/stable/how_it_works/performance_estimation.html;
- MAPIE (BSD-3-Clause), conformal prediction for scikit-learn. https://github.com/scikit-learn-contrib/MAPIE;
- Bank of England PRA (2023), SS1/23 Model risk management principles for banks, principle 3.3(b)(iii) on challenger comparisons. https://www.bankofengland.co.uk/prudential-regulation/publication/2023/may/model-risk-management-principles-for-banks-ss;
- Zieba, M., Tomczak, S. K. and Tomczak, J. M., Polish companies bankruptcy data, UCI Machine Learning Repository (CC BY 4.0). https://archive.ics.uci.edu/dataset/365/polish+companies+bankruptcy+data;
- Hardt, M., Price, E. and Srebro, N. (2016), Equality of opportunity in supervised learning, arXiv 1610.02413. https://arxiv.org/abs/1610.02413;
- 29 CFR 1607.4(D), Uniform Guidelines on Employee Selection Procedures: the four-fifths rule, an employment benchmark. https://www.law.cornell.edu/cfr/text/29/1607.4;
- CFPB (2026), Equal Credit Opportunity Act (Regulation B), final rule, 91 FR 21620, effective 2026-07-21. https://www.govinfo.gov/content/pkg/FR-2026-04-22/pdf/2026-07804.pdf;
- OCC, FDIC, Federal Reserve Board, OTS and NCUA (2009), Interagency Fair Lending Examination Procedures. https://www.federalreserve.gov/boarddocs/caletters/2009/0906/09-06_attachment.pdf;
- Kozodoi, N., Jacob, J. and Lessmann, S. (2022), Fairness in credit scoring: assessment, implementation and profit implications, European Journal of Operational Research 297(3). https://doi.org/10.1016/j.ejor.2021.06.023;
- FFIEC and CFPB, Home Mortgage Disclosure Act data publication (the licence sentence of the data is UNVERIFIED). https://ffiec.cfpb.gov/data-publication/;
- Alvarez, J. M. and Ruggieri, S. (2025), Counterfactual situation testing: from single to multidimensional discrimination, Journal of Artificial Intelligence Research 82, arXiv 2502.01267. https://doi.org/10.1613/jair.1.17935;
- Alvarez, J. M. and Ruggieri, S. (2026), Mutatis mutandis: revisiting the comparator in discrimination testing, Computational Intelligence 42(4), arXiv 2405.13693. https://doi.org/10.1111/coin.70238;
- ValidMind library (AGPL-3.0 or commercial licence): data and model validation tests and documentation. https://github.com/validmind/validmind-library;
- BBVA mercury-robust (Apache-2.0): data and model test suites, drift and label-leakage checks. https://github.com/BBVA/mercury-robust;
- ING popmon (MIT): population shift monitoring. https://github.com/ing-bank/popmon;
- Evidently (Apache-2.0): drift, data quality and model quality reports. https://github.com/evidentlyai/evidently;
- NannyML (Apache-2.0), the open implementation of CBPE. https://github.com/NannyML/nannyml;
- fairlearn (MIT), fairness assessment and mitigation. https://github.com/fairlearn/fairlearn;
- SHAP (MIT), the reference implementation of Shapley explanations. https://github.com/shap/shap;
- Romano, Y., Patterson, E. and Candes, E. J. (2019), Conformalized quantile regression, arXiv 1905.03222. https://arxiv.org/abs/1905.03222;
- Barber, R. F., Candes, E. J., Ramdas, A. and Tibshirani, R. J. (2021), Predictive inference with the jackknife+, Annals of Statistics 49(1). https://doi.org/10.1214/20-AOS1965;
- Vovk, V. and Petej, I. (2012), Venn-Abers predictors, arXiv 1211.0025. https://arxiv.org/abs/1211.0025.

The topic 06 (portfolio capital) notebooks cite, from the persisted research dossiers 04 and 05, the engine's module documentation and
its contract:

- Board of Governors of the Federal Reserve System, charge-off and delinquency rates on loans and leases at commercial banks, table
  `chgallsa`, https://www.federalreserve.gov/releases/chargeoff/chgallsa.htm (public domain, licence class mirror-allowed);
- BCBS, Basel Framework CRE31, the IRB risk weight functions, https://www.bis.org/basel_framework/chapter/CRE/31.htm;
- Gordy (2003), a risk-factor model foundation for ratings-based bank capital rules, https://doi.org/10.1016/S1042-9573(03)00040-8;
- Gordy (2000), a comparative anatomy of credit risk models, https://doi.org/10.1016/S0378-4266(99)00054-0 (the dossier records it from
  its abstract, the wording is UNVERIFIED);
- Gupton, Finger and Bhatia (1997), CreditMetrics technical document, as reissued in 2007 and hosted by MSCI,
  https://www.msci.com/documents/10199/93396227-d449-4229-9143-24a94dab122f (page-level formula references UNVERIFIED);
- Li (2000), on default correlation: a copula function approach, https://doi.org/10.3905/jfi.2000.319253;
- Frey and McNeil (2003), dependent defaults in models of portfolio credit risk, https://doi.org/10.21314/jor.2003.089;
- Demarta and McNeil (2005), the t copula and related copulas, https://doi.org/10.1111/j.1751-5823.2005.tb00254.x;
- Haaf, Reiss and Schoenmakers (2004), numerically stable computation of CreditRisk+, https://doi.org/10.21314/jor.2004.097;
- Gordy and Lutkebohmert (2013), granularity adjustment for regulatory capital assessment,
  https://www.ijcb.org/sites/default/files/journal/v9n3/ijcb-v9n3-granularity-adjustment-regulatory-capital-assessment.pdf;
- Tasche (2008), capital allocation to business units and sub-portfolios: the Euler principle, https://arxiv.org/abs/0708.2542;
- Tasche (2009), capital allocation for credit portfolios with kernel estimators, https://doi.org/10.1080/14697680802620599;
- Emmer and Tasche (2005), calculating credit risk capital charges with the one-factor model, https://arxiv.org/abs/cond-mat/0302402;
- Glasserman and Li (2005), importance sampling for portfolio credit risk, https://doi.org/10.1287/mnsc.1050.0415 (the dossier marks its
  transcription of the twist UNVERIFIED);
- Glasserman, Heidelberger and Shahabuddin (2002), portfolio value-at-risk with heavy-tailed risk factors,
  https://doi.org/10.1111/1467-9965.00141;
- Acerbi and Tasche (2002), on the coherence of expected shortfall, https://doi.org/10.1016/S0378-4266(02)00283-2;
- Dullmann and Masschelein (2007), a tractable model to measure sector concentration risk in credit portfolios,
  https://doi.org/10.1007/s10693-007-0014-3;
- BCBS (2006), studies on credit risk concentration, working paper 15, https://www.bis.org/publ/bcbs_wp15.pdf (a search summary in the
  dossier);
- Wilson (1927), probable inference, the law of succession, and statistical inference, https://doi.org/10.1080/01621459.1927.10502953.

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
| pipeline | networkx | 3.7 | the layered layout of the governance dependency map (`topological_generations`, `multipartite_layout`; U15-P); BSD-3-Clause, pipeline only, never an engine dependency; https://pypi.org/pypi/networkx/json read on 2026-10-20 | a hand-written layering, rejected: the library's layout is tested and the map is not a method of the product |
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
| engine | riskvalidation | 1.1.0 | the validation tests, regulatory calculators and generators (the PyPI release 1.0.1, tag v1.01.000, the patch of the first stable release 1.0.0: the batch 3 packages of 0.8.x (liquidity, aggregation and stress testing, the regulatory calculators and counterparty credit risk, ML model validation and fair lending) and model governance, `riskvalidation.governance`) | none: no toolkit implements the ECB tests as specified |
| models | torch | 2.14.1 | CPU runtime of the C11 R10 quantile network trained on FZ0 and of the C06 PC-Hazard rung (BSD-3-Clause; `data-pipeline/requirements.txt`), and of the TabPFN extra | none recorded |
| models (optional) | tabpfn | 9.1.0 | the TabPFN challenger of the small cases, weights under the Prior Labs License | none recorded |
| notebooks | arch | 8.0.0 | the independent GARCH reference of the topic 07 state-of-the-art notebook, the package the engine's garch rung calls (the engine's `market` extra, `arch>=8.0,<9`; U17 sizing technology matrix) | none: the engine's own reference |
| notebooks | mapie | 1.5.0 | the conformal reference of the topic 13 state-of-the-art notebook (the engine's `ml` extra, `mapie>=1.5,<2`; BSD-3-Clause) | none: the engine's own reference |
| notebooks | fairlearn | 0.15.0 | the fairness-metric reference of the topic 13 state-of-the-art notebook (the engine's `ml` extra, `fairlearn>=0.15,<0.16`; MIT) | none: the engine's own reference |
| notebooks | matplotlib | 3.11.2 | the figures of the notebooks (`notebooks/requirements.txt`) | none recorded |
| notebooks | nbclient | 0.11.0 | executes the notebooks top to bottom in a fresh kernel (`scripts/run_notebooks.py`, a local release gate) | none recorded |
| notebooks | nbformat | 5.11.1 | reads and writes the notebook documents of the runner | none recorded |
| notebooks | ipykernel | 7.4.0 | the kernel the notebooks run in | none recorded |
| tests | pytest | 9.1.1 | the pipeline, contract, guard and adversarial tests | none recorded |
| lint | ruff | 0.15.18 | lint of data-pipeline, tests, scripts and app | none recorded (0.17.0 is current and was not adopted) |
| contracts | jsonschema | 4.26.0 | validates every document against its schema file | none recorded |
| shell | @fasl-work/caos-app-shell | 0.19.6 | the shared app shell, pinned exactly (ADR-0078); since 0.19.0 it draws every chart with Tier A and the C07 and C18 waterfalls, bridge and grouped bars; 0.19.1 lets a filling card flow on a phone (data-caos-flow) and names Spanish dates; 0.19.2 corrects the gate's sticky-header reading (G5); 0.19.3 writes its own labels in Spanish (D16-21); 0.19.4 wraps the rail's lane badge and judges a drawing by its visible part (G6); 0.19.5 gives a case whole notes at 1280 px (`noteFit`, C04); 0.19.6 marks the footer licence translate=no | a hand-rolled shell, forbidden by ADR-0078 |
| web | react | 19.3.0 | the UI | none: the shell requires it |
| web | react-dom | 19.3.0 | the UI renderer | none: the shell requires it |
| web | react-router | 8.4.0 | the six routes | none: the shell requires it |
| web | zustand | 5.0.15 | the workbench selection store | none recorded |
| web | katex | 0.16.47 | typeset equations on the Methodology pages | none recorded (0.19.0 is current and was not adopted) |
| web | lucide-react | 1.52.0 | icons | none recorded |
| web | uplot | 1.6.32 | the interactive curves | none recorded |
| build | vite | 8.3.5 | bundler and dev server; 8.3.5 carries the fixes of the Windows command-execution advisories (template 0.11.001) | none recorded |
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

Every bake pins its thread counts (`OPENBLAS_NUM_THREADS`, `OMP_NUM_THREADS`, `MKL_NUM_THREADS` = 4, set by `data-pipeline/pipeline/__init__.py` and `data-pipeline/run.py` before numpy or a model library loads; `tests/test_pinned_threads.py`), because the BLAS summation order and LightGBM's OpenMP split follow the thread count: a bake writes the same bytes on any device. The one stated exception is the wall-clock `run_seconds` of the C12 ORE reconciliation, which the C12 determinism test excludes.

What each stage needs on the development workstation (Windows 11, 2026-10-12; Python 3.13.14, Node 24.14.1; 16 GB of RAM
free at the preflight of 2026-10-11; no GPU is used by any stage listed). Every value not marked otherwise was measured by running the
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
| bake C22 (`run.py C22`, the size and power runs of all nine variants, at least 4,000 repetitions per test, every registered p-value test; the 75 simulations of the engine's named studies run first on 8 worker processes, the longest, the machine-learning shift resilience study, taking most of the wall time) | about 1.4 GB summed over the main process and the 8 workers (sampled while the pool ran, shared machine) | 695,453 bytes | 9,578 s (U16-P2, riskvalidation 0.9.0 plus the U16-E2 studies; 1,096.8 s before it, eight variants on engine 0.4.3) | workstation, never CI |
| tests (`pytest tests`, 3,998 tests collected on 2026-10-21 at the wave 3 integration line, 21 of the 22 cases built: the pipeline, contract, guard, bake-artifact and case tests; the full run is made by the release run that writes the convergence verdict, `docs/design/features/release-1-0/design.md`) | not re-measured here: 435 MB peak (300 MB the largest process) when the suite had 387 tests | none outside the temporary directory | not re-measured here: 125.6 s at 387 tests | workstation, never CI |
| tests (`pytest tests/adversarial`, 88 tests collected on 2026-10-21 the plants of this document's validation files, including two browser-gate plants) | 677 MB peak (282 MB the largest process) | temporary copies of the repository's committed files, about 10 MB each | 1,344.9 s for 88 plants (the two gate plants take 424 s, the leakage plants 30 to 186 s each) | workstation; the Python plants alone also fit CI (ADR-0074) |
| tests (`npm test` in `frontend/`, 57 files, 1,913 tests, all passed on 2026-10-21 at the wave 3 integration line) | 1,872 MB peak summed over the vitest workers when the suite had 560 tests | none | measured by the release run (3.9 s at 560 tests) | workstation and CI web job |
| build (`npm run build`; 21 of the 22 cases are built and C19 is planned, so the build reads the index of the 21 manifests) | 566 MB peak, measured at four built cases | 6,727,923 bytes in `frontend/dist`, 123 files, measured at four built cases | 16.0 s, measured at four built cases | workstation and CI web job; UNVERIFIED at 21 built cases until the release run measures it |
| gate (`npm run gate`, every route, tab, sub-tab and case at five sizes, both themes and both languages, on that build) | 910 MB peak, measured at 868 states | 14,285,565 bytes of captures in `gate-output`, measured at 868 states | 427.4 s at 868 states | workstation, never CI. The last full gate log is the 0.12.000 release: 2,069 measured states, 0 failures, 15 cases built. The 0.13.000 gate walked all 21 built cases with no failure (`CHANGELOG.md`, 0.13.000); its state count is UNVERIFIED here and the release run records it |
| deploy payload (GitHub Pages) | none | UNVERIFIED at 21 built cases: 6,727,923 bytes of `frontend/dist` were measured at four built cases, and the 21 built cases add their documents under `data/derived/`; the release run measures the payload | at most the 15-minute timeout of the CI web job; one Pages deploy after CI on main | CI after main |

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

Every method of Contraste is a row, with its tier (`classical`, `sota` or `beyond`; CAOS_MANAGE `conventions/method-tiers-and-manuscripts.md`,
template 0.13.000). A method is accepted only with its engine called for real, pinned dependency and licence, configuration with
units, training or calibration where applicable, a checkpoint or parameter record, inference on every applicable case variant, its
validation tests, documentation transcribed from the dossier, and an honest lane label (ADR-0069). The beyond rows name what each is:
BS-1 to BS-12 are the product's measurements, protocols, reconciliations and test constructions beyond common practice; BS-13 to BS-16
are the methods Contraste proposes (the plan `plans/contraste/method-tiers-sdd-plan.md` in CAOS_MANAGE, validated 2026-10-28).

| id | tier | method | acceptance criterion | gate |
|---|---|---|---|---|
| M-1 | classical | WoE monotone scorecard (P) | optbinning bins fitted on train only reproduce monotone event rates; the points table recomputes every score exactly; AUC with DeLong CI, KS, Brier, calibration by grade and PSI out of sample are reported. | `tests/test_c01.py` |
| M-2 | classical | Penalised logistic regression (P) | paired DeLong against the scorecard reported | `tests/test_c01.py` |
| M-3 | sota | Penalised logistic tree regression, PLTR (P) | rule set stable across 20 bootstraps (Jaccard reported) | `tests/test_c01.py` |
| M-4 | sota | EBM/GA2M (P) | monotone shape functions where declared; per-term points table; post-calibration reliability; live additive scoring equals offline within 1e-9. | `tests/test_c01.py` |
| M-5 | sota | Monotone GBM plus calibration (P) | monotonicity verified on PDP grids; isotonic or Platt map fitted on a separate slice; Brier and reliability before and after; reason-code stability (bootstrap top-4 overlap). | `tests/test_c01.py` |
| M-6 | sota | TabPFN challenger (P) | runs only on small cases; the weights licence is shown on every view; same gates as GBM. | `tests/test_c01.py` |
| M-7 | classical | Rating master scale and calibration (E) | Tasche (2013) Table 1 scaled PD and scaled LR columns reproduced; Pluto-Tasche tables 1, 2, 3, 4, 7 reproduced to 0.01 pp. | `tests/test_c05.py` |
| M-8 | classical | TTC/PIT Z-factor (E) | implied Z reproduces the LHP relation; PIT PDs average back to TTC over the cycle on the generator. | `tests/test_c04.py` |
| M-9 | sota | Transition estimators (E) | rows sum to 1; generator rows to 0; equality with the transitionMatrix cohort estimator on the same data; regularised generator distance reported. | `tests/test_c04.py` |
| M-10 | sota | Lifetime PD rungs (P) | cumulative PD monotone; calibration at 12, 24, 36 months against Aalen-Johansen per decile; C-index and integrated Brier for Cox rungs. | `tests/c06/` |
| M-11 | sota | IFRS 9 ECL engine (E) | reconciliation identities close within 1e-6; weighted ECL >= average-scenario ECL in the convex regime (property test); the non-linearity example 2.68% vs 1.80% reproduced; overlays reported as separate lines. | `tests/c06/` |
| M-12 | classical | CMF B-1 (E) | PE = PI x PDI / 100 for every transcribed cell; the consumer matrix lookup reproduces the 16 cells; the 0.50% minimum enforced. | `tests/c07/` |
| M-13 | classical | BdE Annex 9 (E) | coverage tables reproduced as transcribed; the category-to-stage mapping exposed. | `tests/c07/` |
| M-14 | classical | LGD rungs (P) | predictions inside [0,1]; out-of-time calibration by bucket; endpoint sensitivity reported for beta rungs. | `tests/c08/` |
| M-15 | classical | CCF/EAD rungs (P) | known CCF recovered on the generator within the reported error; the CCF convention named on every view. | `tests/c09/` |
| M-16 | classical | IRB and LHP (E) | CRE99 Table 1 reproduced within 0.005 pp; Basel II mode carries 1.06 and 0.03%; Chile mode uses the RAN 21-6 correlations. | `tests/test_c01_capital.py` |
| M-17 | sota | Copula MC, CreditRisk+, GA, IS (E) | MC converges to LHP as n grows; Euler contributions sum to the total; the CreditRisk+ recursion matches MC; GA delta = 4.83; IS unbiased against plain MC. | `tests/c10/` |
| M-18 | sota | VaR/ES estimators (E and P) | each rung run over the full rolling schedule with no look-ahead; own GARCH-t (scipy) matches `arch` within 1e-4 on the log-likelihood; FZ0 losses computed for every rung. | `tests/c11/` |
| M-19 | classical | VaR/ES backtests (E) | MAR99 Table 2 reproduced to two decimals; Kupiec and Christoffersen match closed forms; Acerbi-Szekely critical values simulated per model. | `tests/c11/` |
| M-20 | sota | CCR and CVA (P) | own HW1F single-swap EE matches ORE within MC error at every grid point; EEPE and CVA recomputed from EE match ORE; path convergence reported. | `tests/c12/` |
| M-21 | classical | SA-CCR, BA-CVA, SMA, output floor, LCR/NSFR, FRTB cascade (E) | official worked examples reproduced (SA-CCR five netting sets, SMA 5.37bn, output floor 101.5 and 95); invariants for BA-CVA, SBM, LCR, NSFR where no official example exists. | `tests/test_regulatory*.py` |
| M-22 | sota | IRRBB/ALM (E) | SRP31.92 values reproduced (0.417, 41.7, +25.4, -1.6 bp); the 2016 and 2024 shock tables as fixtures; EVE sum-of-parts reconciles; the CMF Annex 1 worked example reproduced; CLP shocks labelled when not from the CMF. | `tests/c14/`, `tests/c15/` |
| M-23 | sota | Liquidity (E) | LiST compounding 12.11% after 125 days reproduced; survival period monotone in run-off severity. | `tests/c16/` |
| M-24 | sota | Op risk (E) | Shevchenko benchmark mean 738.9056 and 99.9% quantile 5,849 to 5,850 across MC, Panjer and FFT. | `tests/c17/` |
| M-25 | sota | Aggregation (E) | Euler contributions sum to the total; the dependence band (sum, var-covar, Gaussian, t, worst case) always shown. | `tests/c18/` |
| M-26 | classical | Stress satellites (P) | back-cast through 2008-2009 and 2020 with satellites estimated on prior data; coefficient signs checked. | `tests/c18/` |
| M-27 | classical | Fed supervisory replication (P) | published hypothetical-portfolio loss rates reproduced within the tolerance stated in the case. | `tests/c18/` |
| M-28 | classical | Validation tests, all (E) | each reproduces a published worked example or an independent reference (scipy distributions) to a stated tolerance; every result carries `reference`, `h0` and a policy version. | `tests/test_c22.py` |
| M-29 | sota | ML validation and fairness tests (E) | each test detects its planted defect on the generator with power reported at alpha 0.05 and holds its size under the null within Monte Carlo error. | `tests/c20/`, `tests/c21/` |
| M-30 | sota | Quantile network trained on the FZ0 loss, C11 R10 (P; plan S-1) | trained on each window's train span only, no look-ahead; its VaR and ES pass the same eligibility gates and FZ0 ranking as the other rungs; reported whether it wins or not | `tests/c11/` |
| M-31 | sota | VAR conditional forecasts and growth-at-risk quantile satellites, C18 (E and P; plan S-2) | back-cast through 2008-09 and 2020 on prior data beside the OLS satellites, with the coefficient-sign checks | `tests/c18/` |
| M-32 | sota | Robust severity estimators (optimally bias-robust, Cramer-von Mises) with the mean-adjusted SLA, C17 (E; plan S-3) | on the generators of known truth, the capital's bias and spread reported beside the MLE splice | `tests/c17/` |
| M-33 | sota | Neural discrete-time survival, PC-Hazard, C06 (P; plan S-4) | calibration at 12, 24 and 36 months against Aalen-Johansen per decile, C-index and integrated Brier beside Cox, at the six reporting dates | `tests/c06/` |
| M-34 | sota | Random forest and neural LGD rungs, C08 (P; plan S-5) | out-of-time calibration by bucket and the ladder's metrics on the same split as the other LGD rungs | `tests/c08/` |
| M-35 | sota | Reject inference (parcelling and augmentation) on a sample with a known rejected population (P; plan S-6) | the accepted-only model's bias on the full population measured, and each reject-inference rung's reduction of it with its interval | `tests/test_c01.py`, `tests/c02/` |
| BS-1 | beyond | Measurement: The measured size and power of the validation tests on planted defects | its committed evidence, as `## Beyond the state of the art` states it | the evidence and tests that section lists for BS-1 |
| BS-2 | beyond | Reconciliation: The reconciliations against reference engines that exist today | its committed evidence, as `## Beyond the state of the art` states it | the evidence and tests that section lists for BS-2 |
| BS-3 | beyond | Protocol: The leakage-safe protocol per case, with gates | its committed evidence, as `## Beyond the state of the art` states it | the evidence and tests that section lists for BS-3 |
| BS-4 | beyond | Method-adjacent: estimator treatment: The default definition as part of the PD, informative withdrawals and thin grades | its committed evidence, as `## Beyond the state of the art` states it | the evidence and tests that section lists for BS-4 |
| BS-5 | beyond | Protocol: Provisions reconciliation identities as gates, overlays apart, three regimes on one portfolio | its committed evidence, as `## Beyond the state of the art` states it | the evidence and tests that section lists for BS-5 |
| BS-6 | beyond | Engine coverage: Engines and test catalogues no open toolkit provides | its committed evidence, as `## Beyond the state of the art` states it | the evidence and tests that section lists for BS-6 |
| BS-7 | beyond | Method-adjacent: currency treatment: The UF as its own currency in IRRBB | its committed evidence, as `## Beyond the state of the art` states it | the evidence and tests that section lists for BS-7 |
| BS-8 | beyond | Test construction: A test that flags a behavioural assumption changed at a limit breach | its committed evidence, as `## Beyond the state of the art` states it | the evidence and tests that section lists for BS-8 |
| BS-9 | beyond | Protocol: The dependence band shown with every aggregate | its committed evidence, as `## Beyond the state of the art` states it | the evidence and tests that section lists for BS-9 |
| BS-10 | beyond | Test construction: The batch 3 test corrections, with the error rate each one removes measured on planted data | its committed evidence, as `## Beyond the state of the art` states it | the evidence and tests that section lists for BS-10 |
| BS-11 | beyond | Method-adjacent: reverse stress rule: Reverse liquidity stress as a run-off multiplier with a refusal rule, scored against a labelled run | its committed evidence, as `## Beyond the state of the art` states it | the evidence and tests that section lists for BS-11 |
| BS-12 | beyond | Measurement: The instability of the operational-risk capital, measured on independent histories of known truth | its committed evidence, as `## Beyond the state of the art` states it | the evidence and tests that section lists for BS-12 |
| BS-13 | beyond | Proposed method: a scale-and-level complement to the FRTB PLA test (C13) | at a size of at most 1 %, the stale-volatility model flagged in at least 30 % of replications; refuted below 10 % | `tests/c13/`; engine `market` tests |
| BS-14 | beyond | Proposed method: an anchored tipping-point PD under informative rating withdrawals (C04) | the anchored interval covers the true PD in at least 90 % of 200 repetitions at k = 9, the existing treatments under 50 %; refuted if not better or if the anchored k is unstable | `tests/test_c04.py`; engine `transitions` tests |
| BS-15 | beyond | Proposed method: e-process sequential monitors for calibration and back-tests (C22, C11, C03) | size held at 5 % under optional stopping where the repeated Kupiec rule exceeds it, median delay below the 250-day window at severity 3 or more, power cost under 10 points; refuted if the delay is not lower | `tests/test_c22.py`, `tests/c11/`; engine `validation.sequential` tests |
| BS-16 | beyond | Proposed method: adaptive conformal recalibration of VaR against the 17-model ladder (C11) | HS-250, GARCH-t and FHS wrapped pass in at least one more stress window without worsening FZ0 by more than 5 %; refuted if the wrapper fails independence in 2007-09 | `tests/c11/`; engine `market` tests |

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

EARS (Mavin et al., RE'09, doi:10.1109/RE.2009.9). Product requirements (`CT-`, plus `NB-`, `RP-` and `CV-` for the notebooks, the
README and the verdict) are stated with their gates in the 27 feature folders of `docs/design/features/`. Engine requirements (`RV-`)
are stated and gated in the engine repository. Convergence is generated, not written here: `scripts/convergence_verdict.py` lists every
requirement of both repositories with its gate and the gate's result in the release run (ADR-0075 section 4;
`docs/design/features/release-1-0/`).

| Unit | Feature folder | Requirements |
|---|---|---|
| U0 | `docs/design/features/contracts/` | CT-001 to CT-014: ingestion contracts, licence lineage, provenance, the TypeScript mirror, licences of the default install, data classes, content standards, the source registry, the licence manifest, the data root, hash pinning, the bring-your-own-model door (contract 1 then the battery on a reader's scored sample) |
| U1 | `docs/design/features/c01-retail-pd/` | CT-101 to CT-105 and CT-108 to CT-111: leakage-safe split, disjoint calibration slice, invariance to information outside the training set, threshold labels, live parity, the points table, the battery per rung, GBM monotonicity, expected ranges |
| U1 | `docs/design/features/web/` | CT-106, CT-107 and CT-112 to CT-114: the App route fits the viewport with one row of navigation; every route passes the measured gate; the six instrument groups; the lane on every view; sources and licences in Context |
| U2 | `docs/design/features/c05-ldp-calibration/` | CT-201 to CT-211: the paper readers checked against their own print; every golden cell within the engine's tolerance; the generator's truth recovered; coverage and power; the capital's assumptions; expected ranges; no derived-only counts published; live parity; the C05 instrument; the measured gate |
| U2 | `docs/design/features/c01-irb-capital/` | CT-212 to CT-217: C01's IRB capital along every cut-off under three regimes with its stated assumptions; each point the engine's sum; every card a revolver, the six-month full payers as the sensitivity; the live capital linear in the LGD and the retail functions at parity; the Basel III LGD floor flagged; the measured gate |
| U3 | `docs/design/features/c22-validator/` | CT-301 to CT-313: the size of every test with a p-value on its null; power against seven planted defects at severities 0 to 5; exact rejection probabilities beside the simulated ones; WP14, Yurdakul-Naranjo and Demler et al. reproduced cell by cell; findings evidenced by measured rates; known truth and determinism; expected ranges; the live exact size and power at parity; the C22 instrument; the measured gate; C05 on the engine's generator; C01's Hosmer-Lemeshow with G degrees of freedom and its AUC test with the development variance |
| U4 | `docs/design/features/c04-transitions/` | CT-401 to CT-414 (15 requirements): case C04 (rating transitions and TTC PD by grade) |
| U5-P1 | `docs/design/features/c06/` | CT-501 to CT-517 (17 requirements): case C06 (lifetime PD, IFRS 9 staging and ECL on the SBA 7(a) twin) |
| U5-P2 | `docs/design/features/c07/` | CT-701 to CT-713 (13 requirements): case C07 (the Chile provisions trilogy) |
| U6-P1 | `docs/design/features/c03/` | CT-801 to CT-812 (12 requirements): case C03 (SME PD by vintage through 2008, on the SBA 7(a) loans) |
| U6-P2 | `docs/design/features/c08/` | CT-901 to CT-917 (17 requirements): case C08 (LGD and downturn LGD on the SBA 7(a) charge-off twin) |
| U6-P3 | `docs/design/features/c09/` | CT-1001 to CT-1013 (13 requirements): case C09 (EAD and CCF for revolving lines) |
| U7-P | `docs/design/features/c10/` | CT-1101 to CT-1112 (12 requirements): case C10 (portfolio credit capital) |
| U8-P1 | `docs/design/features/c11/` | CT-601 to CT-615 (15 requirements): case C11 (market VaR and ES back-testing across 2008, 2020, 2022 and 2023) |
| U8-P2 | `docs/design/features/c13/` | CT-1301 to CT-1313 (13 requirements): case C13 (FRTB desk eligibility: PLA and desk back-testing) |
| U9-P1 | `docs/design/features/c12/` | CT-1201 to CT-1221 (21 requirements): case C12 (swap exposure, CVA and SA-CCR on a synthetic USD swap book) |
| U10-P1 | `docs/design/features/c14/` | CT-1401 to CT-1414 (14 requirements): case C14 (IRRBB six shocks on a USD balance sheet, SVB 2022) |
| U10-P2 | `docs/design/features/c15/` | CT-1501 to CT-1517 (17 requirements): case C15 (IRRBB on a CLP and UF balance sheet, RAN 21-13 Annex 1) |
| U11-P | `docs/design/features/c16/` | CT-1601 to CT-1623 (23 requirements): case C16 (liquidity stress, LCR and the March 2023 run, on the call reports of the bank that failed on 2023-03-10) |
| U12-P | `docs/design/features/c17/` | CT-1701 to CT-1715 (15 requirements): case C17 (operational risk: LDA against SMA) |
| U13-P1 | `docs/design/features/c18/` | CT-1801 to CT-1825 (25 requirements): case C18 (ICAAP and IAPE capital aggregation under macro scenarios) |
| U14-P1 | `docs/design/features/c02/` | CT-0201 to CT-0218 (18 requirements): case C02 (corporate PD across the 1 to 5 year horizons on the UCI Polish bankruptcy files) |
| U14-P2 | `docs/design/features/c20/` | CT-2001 to CT-2025 (25 requirements): case C20 (ML model validation: drift, robustness, explanation stability) |
| U14-P3 | `docs/design/features/c21/` | CT-2101 to CT-2119 (19 requirements): case C21 (fair-lending disparity testing on HMDA decisions, Delaware, 2018 to 2024) |
| U16 | `docs/design/features/release-1-0/` | CV-001 to CV-013 (13 requirements): the generated convergence verdict of release 1.0 |
| U17 | `docs/design/features/notebooks/` | NB-001 to NB-021 (21 requirements): the product notebooks |
| U17 | `docs/design/features/repository/` | RP-001 to RP-005 (5 requirements): the README states the repository by areas |
| engine | `CAOS_RiskValidation` `docs/design/features/` | RV- requirements (21 feature folders, 514 requirement rows at the engine head of 2026-10-21), stated and gated in the engine repository; the verdict lists them beside the product's (`docs/design/features/release-1-0/`) |

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

Two kinds of entry are listed here. **BS-1 to BS-12** are what Contraste does beyond common practice without proposing a new
method: measurements, protocols, reconciliations, engine coverage and test constructions (the rule counts none of them, by itself,
as a method beyond the state of the art; each says what it is in the Method ladder). **BS-13 to BS-16** are the methods Contraste
proposes, each with its hypothesis, its method and the evaluation that confirms or refutes it; each is reported whatever its result.

A component of Contraste that goes further than the practice its research found enters this section with the topic unit that
demonstrates it: an identifier of the form BS-<n>, the committed evidence a reader can open, the practice it goes beyond, and a level 4
notebook in each language (`notebooks/`, CAOS_MANAGE `conventions/product-notebooks.md`). Topic 01 teaches the package's contract and
demonstrates none. The candidate claims and their evidence are drafted in the U17 sizing (decision N8) and enter here one by one, so
no claim is stated before its demonstration exists. Each claim is stated only as far as its committed evidence goes.

- **BS-1** The measured size and power of the validation tests on planted defects.
  What it adds: for each of the 21 tests with a p-value, its rejection rate under its null at 5% and 1% (its size), and for 17 of
  them its rejection rate against defects of known severity (its power); the four transition tests (time homogeneity, Markov order,
  matrix against a reference, downward momentum) have a size and no power. The measurement is 231 simulations and 551,000 seeded
  repetitions in eight families, every one of its 476 rates with its Monte Carlo standard error (Morris, White and Crowther 2019,
  https://doi.org/10.1002/sim.8086) and its Wilson interval (Brown, Cai and DasGupta 2001, https://doi.org/10.1214/ss/1009213286),
  an exact rejection probability beside 47 of the rows, on 123 generators whose truth is known and reproduces from the committed
  configuration. Demonstrated by `notebooks/en/14-validating-the-validator/08-beyond-the-size-and-power-of-every-test-measured-on-planted-defects.ipynb`
  and its Spanish counterpart.
  Evidence: `data/derived/C22/null.json`, `data/derived/C22/miscalibration.json`, `data/derived/C22/clustering.json`,
  `data/derived/C22/drift.json`, `data/derived/C22/discrimination-decay.json`, `data/derived/C22/leakage.json`,
  `data/derived/C22/broken-monotonicity.json`, `data/derived/C22/concentration.json`,
  `docs/design/features/c22-validator/requirements.md`, `tests/test_c22.py`.
  Beyond: the ECB 2019 instructions define the tests and set no pass or fail thresholds; BCBS Working Paper 14 concludes that "no
  really powerful tests of adequate calibration are currently available"
  (https://www.bis.org/publications/studies-validation-internal-rating-systems-revised.pdf); the PSI bands are used without a statement
  of their type I and type II error (Yurdakul and Naranjo 2020, https://doi.org/10.21314/JRMV.2020.227); and the validation toolkits
  the research surveyed list tests, thresholds and traffic lights and record no measured size or power (UNVERIFIED beyond the
  documentation the survey read).
  Not claimed: the power of the four transition tests; that a rate holds outside the generator and the severity ladder it was
  measured on (the ladders are design choices of Contraste, and power against them is not a probability of detecting a real bank's
  problem); any regulatory threshold implied by a size or a power.

- **BS-2** The reconciliations against reference engines that exist today.
  What it adds: the engine's tests and estimators are held to independent implementations and to the printed digits of the papers,
  and the gap is reported. The reconciliations that exist are the ones claimed:
  - the printed tables and papers recomputed beside their prints (413 printed numbers of five papers in the ratings and calibration
    cases, 296 reproduced to the printed digit, every other one listed with its cell and its explanation);
  - the p-values of the Jeffreys and binomial tests against two recomputations that call neither of the engine's SciPy functions (a
    quadrature of the Beta density and an exact rational sum of the binomial terms), equal within 1e-9 on a grid of 36 cases;
  - the Hull-White exposure of the single swap and of the four-swap netting set against ORE 1.8.17.0, within two combined Monte Carlo
    standard errors at all 33 report dates, with the EEPE and the CVA;
  - the Hull-White closed forms against QuantLib 1.44 to a relative 1e-6;
  - the wrong-way calibration against the printed values of the Appendix of Hull and White (2012).

  Reported as gaps and not claimed: the collateralised variants (CSA with 10 and with 20 days) and the initial-margin variant against
  ORE, with the largest EE gaps of 9.9, 7.1 and 11.7 combined standard errors, CVA gaps of 15.9 and 9.9 in the two CSA variants, and a
  mean dynamic initial margin of ORE at 0.88 of the engine's. Not claimed: the wrong-way variant against ORE, whose example is a
  different model, and the equality with the transition-matrix cohort estimator, which the engine tests since 0.8.0 (RV-415, backlog item BL-083, where the
  optional `transitions` extra is installed) and no notebook of Contraste reruns.
  Evidence: `tests/test_c04_parity.py`, `tests/test_c04_published.py`, `tests/test_c05.py`, `data/derived/C04/published.json`,
  `data/derived/C05/ldp-published.json`, `data/derived/C05/sp-2010.json`, `data/derived/C05/sp-2011.json`,
  `docs/frameworks/01_riskvalidation/riskvalidation.md`, `data/derived/C12/single-swap.json`, `data/derived/C12/netting-set.json`,
  `data/derived/C12/csa-mpor-10d.json`, `data/derived/C12/csa-mpor-20d.json`, `data/derived/C12/with-im.json`,
  `data/derived/C12/wrong-way-risk.json`.
  Beyond: toolkits ship the estimators and leave the reconciliation to the user; the persisted research (dossier 05) lists ORE and
  QuantLib as reference engines whose numbers Contraste must not claim as validated beyond the reconciliations actually run.
  Demonstrated by: `notebooks/en/03-ratings-and-calibration/11-beyond-the-reconciliations-against-printed-answers.ipynb` and
  `notebooks/en/08-counterparty-and-regulatory-calculators/08-beyond-exposure-reconciled-to-a-reference-engine.ipynb`, with their
  Spanish counterparts.

- **BS-3** The leakage-safe protocol per case, with gates.
  What it adds: a split declared per case (a locked stratified holdout for C01 and C02, out-of-time cohorts read at their 5-year mark
  for C03) and enforced by tests: transforms fitted on the training slice only, a calibration slice disjoint from the test slice, and
  every fitted parameter unchanged when a value outside the training information set is perturbed. The artifacts record the split and
  its limits (C01 has no out-of-time validation, C02 makes no out-of-time claim). The planted leak of C22 shows what the engine's tests
  see of a leak: a drop of discrimination out of time, not a drift of the leaked feature. It is enforcement of known rules, not a new
  method.
  Evidence: `docs/design/features/c01-retail-pd/requirements.md` (CT-101 to CT-103), `tests/test_leakage.py` (3 passed when the claim
  was assembled), `data/derived/C01/models-taiwan.json`, `data/derived/C02/h1.json` to `h5.json` and `pooled.json`,
  `data/derived/C03/fy2015-17.json`, `data/derived/C03/fy2018-20.json`, `data/derived/C22/leakage.json`. Demonstrated by
  `notebooks/en/02-credit-scoring/07-beyond-the-leakage-safe-protocol-per-case-with-gates.ipynb` and its Spanish counterpart
  `notebooks/es/02-credit-scoring/07-beyond-the-leakage-safe-protocol-per-case-with-gates.ipynb`.
  Beyond: the research dossier 04 states the leakage rules, and dossier 07 names the single-split evaluation of an open toolkit as the
  counter-example; neither gives a protocol declared per case with a gate that fails when it is broken. Not claimed: a calibration
  before the test window (the drafted text names it for a later case) and any leak by time beyond what the gate CT-103 perturbs.

- **BS-4** The default definition as part of the PD, informative withdrawals and thin grades.
  What it adds: the same agency's long-run PD of the CCC to C grade is 26.64% under the CEREP default page and 8.61% under the
  transition page, and the IRB risk weight of the cohort mix moves from 58.0% to 47.5% with the definition; informative
  withdrawals and thin grades are measured on rating paths of known truth (with withdrawals ten times as likely in the year before
  default, removing them understates the PD of B by 34% and following them as EBA paragraph 76 asks by 15%, and no matrix test sees
  it; with 50 obligors per grade the Wald interval contains the PD of AAA in 0.33% of the samples).
  Evidence: `data/derived/C04/sp.json`, `data/derived/C04/withdrawals.json`, `data/derived/C04/thin.json`,
  `docs/design/features/c04-transitions/requirements.md`.
  Beyond: the ESMA CEREP publication (https://registers.esma.europa.eu/cerep-publication/) states no deterministic definition of a
  default event, and cohort and duration estimators take the agencies' tables as given.
  Demonstrated by: `notebooks/en/03-ratings-and-calibration/10-beyond-the-default-definition-withdrawals-and-thin-grades.ipynb` and
  its Spanish counterpart.

- **BS-5** Provisions reconciliation identities as gates, overlays apart, three regimes on one portfolio.
  What it adds: the IFRS 7 roll-forward closes as a gate on the engine's tolerance basis, one millionth of the gross carrying amount
  of the book, and the notebook measures the size of the smallest planted defect the gate catches; overlays are separate lines that
  move only the total allowance; the non-linearity of the weighted ECL is reproduced, the weighted PD being at least the PD at the
  weighted mean factor in the convex regime and able to fall below it outside; and one synthetic bank is provisioned under CMF B-1,
  IFRS 9 and Bank of Spain Annex 9 with a gap bridge that reconciles in six scenarios.
  Evidence: `data/derived/C06/rd-2008-12.json`, `data/derived/C07/base.json`, `docs/design/features/c06/requirements.md`,
  `docs/design/features/c07/requirements.md`, and the level 4 notebook `notebooks/en/04-provisions/08-beyond-reconciliation-overlays-and-three-regimes.ipynb`
  (Spanish: `notebooks/es/04-provisions/08-beyond-reconciliation-overlays-and-three-regimes.ipynb`), which extends it to the six C06 dates and the six C07 scenarios.
  Beyond: IFRS 9 does not prescribe detailed methods; the research (dossiers 02 and 03) found no public comparison of the three
  regimes on one portfolio, which is UNVERIFIED beyond the searches those dossiers record. The C07 bank is synthetic and labelled so.
  Not claimed: that any regime is right or any engine figure compliant; that the weighted ECL is above the mean-path ECL on every
  date (the committed C06 ECL-level index of 2010-12 is below zero); a tolerance of 1e-6 in units of money (the basis is relative).

- **BS-6** Engines and test catalogues no open toolkit provides.
  What it adds: the ECB 2019 IRB validation-reporting tests as specified, a copula and CreditRisk+ portfolio engine and a bank IRRBB
  engine, with golden values reproduced from the primary sources. It is an absence claim: on 2026-10-04 a search of GitHub and PyPI
  found no toolkit that implements these tests as specified. Topic 06 (portfolio capital) demonstrates the portfolio engine: the
  closed forms and the published test vector it is held to, the committed Gaussian copula rung regenerated bit for bit by the
  released engine, and the engine's estimator measured against a simulator with a known truth. The ECB tests and the IRRBB engine
  are demonstrated by the units of their own topics.
  Evidence: `docs/frameworks/01_riskvalidation/riskvalidation.md`, `data/derived/C01/holdout.json`, `data/derived/C10/grid-22.json`,
  `data/derived/C10/grid-40.json`, `data/derived/C10/commercial-industrial.json`, `data/derived/C10/credit-cards.json`,
  `data/derived/C14/vd-2022-q2.json`, `notebooks/en/06-portfolio-capital/08-beyond-an-engine-reconciled-to-its-anchors.ipynb`.
  Beyond: the research dossiers 04, 05 and 06 record no maintained permissive implementation of these families. Scope of the
  record: for the portfolio engines, dossier 04 section H.8 records a search of 2026-10-04 on CRAN and GitHub (archived CRAN
  packages, a GPL-2 CRAN package, a GPL-2.0 repository and small educational repositories), and the search of GitHub and PyPI is
  dossier 06's, for the validation toolkits; no record states that PyPI was searched for CreditMetrics or CreditRisk+. The claim is
  about maintained, permissively licensed implementations on those dates and is UNVERIFIED beyond them. Not claimed: equality with a
  reference engine (the research found none), freedom from defects (the anchors are necessary conditions), and the Student t
  importance sampler, which the engine records as a rung that did not run.

- **BS-7** The UF as its own currency in IRRBB.
  What it adds: the reajustabilidad risk of CMF RAN 21-13 Annex 1 as a separate currency (the UR) with its own curve, its own shock sizes (200/250/150 bp for the EVE and 300 bp for the NII, against 300/400/200 bp and 300 bp for the peso), its own floor (-2 percent, against 0 for the peso), the indexation charge (2.5% of the absolute net UF position) and the 50% offset of the gain leg against the loss leg. On the committed Banco Andino variants the charge is 55.9% of the delta NII of the short-UF variant, and a single-currency treatment of the same flows (peso curve, peso sizes, zero floor, no charge) gives a delta NII 6.8 to 8.8 times smaller and a delta EVE 10 to 27% smaller in the three variants whose net UF position is 30% of Tier 1.
  Evidence: `data/derived/C15/long-uf.json`, `data/derived/C15/short-uf.json`, `data/derived/C15/floors-active.json`, `data/derived/C15/offset-on-off.json`, `docs/design/features/c15/requirements.md`, `notebooks/en/09-irrbb/08-beyond-the-uf-and-the-breach-test.ipynb`, `notebooks/es/09-irrbb/08-beyond-the-uf-and-the-breach-test.ipynb`.
  Beyond: the BCBS standard (https://www.bis.org/basel_framework/chapter/SRP/31.htm, with the 2016 calibration https://www.bis.org/bcbs/publ/d368.htm and the 2024 recalibration https://www.bis.org/publications/202407-standards-recalibration-shocks-interest-rate-risk-banking-book.pdf) has 21 currencies in its shock table, neither the peso nor a UF-like unit; the Chilean treatment is the Annex 1 of chapter 21-13 of the CMF (https://www.cmfchile.cl/portal/principal/623/articles-29808_doc_pdf.pdf). The claim is regional: no public implementation of Annex 1 was found, which is UNVERIFIED beyond the dossier's search. Limits: the floors are implemented and tested but none binds on the committed curves (the closest post-shock rate is 20.48 bp from its floor in every variant), so their effect on a number is not demonstrated; there is no second implementation to reconcile with; the bank is synthetic.

- **BS-8** A test that flags a behavioural assumption changed at a limit breach.
  What it adds: `irrbb.behavioural_change_at_breach` turns the Federal Reserve's finding on Silicon Valley Bank into a test: it counts the dates at which a behavioural parameter changed while a limit was breached. On the committed C14 balance sheet it is not evaluated at 2021-Q4 (one date), red at 2022-Q2 with "1 change(s) coincide with a breach" and red at 2022-Q4 with two. The parameter it flags is the weighted average maturity of the fitted replicating portfolio; the core share and the core maturity that Contraste states are held fixed and are not flagged. On constructed histories it is green for a parameter held through a breach, for a change with no breach and for a change before the breach, and red for a change at the breach; the committed series with the breach flags set to false is green.
  Evidence: `data/derived/C14/vd-2021-q4.json`, `data/derived/C14/vd-2022-q2.json`, `data/derived/C14/vd-2022-q4.json`, `data/derived/C14/models-svb-2021-2022.json`, `docs/design/features/c14/requirements.md`, `notebooks/en/09-irrbb/08-beyond-the-uf-and-the-breach-test.ipynb`, `notebooks/es/09-irrbb/08-beyond-the-uf-and-the-breach-test.ipynb`.
  Beyond: the supervisor's review (https://www.federalreserve.gov/publications/files/svb-review-20230428.pdf) states the practice as a finding and the research dossier 05 proposes the test; it cites no tool that implements it, which is UNVERIFIED beyond the dossier's search. The bank of C14 is real in aggregate and synthetic in behaviour, and its outlier test is breached at the three dates, so the breach flag does not vary and the flagged parameter is a fitted one, re-estimated at each date: the red rows show that the test operates on those parameters, not that the bank did it in these numbers.

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
  never a scalar. Notebook 09 of topic 12 checks the structure and recomputes the closed-form rows of the two distinct committed
  aggregates (the five documents carry one and the same aggregation block, shown by its hash, and the market-credit 0.8 stress is the
  second); notebook 03 reproduces the engine's published worst-case example (the rearrangement bounds of eight Pareto marginals) and
  runs the band on the marginals rebuilt from the committed quantile grids (`data/derived/C18/models-banco-andino.json`,
  `fit.aggregation.quantile_grid`).
  Beyond: the research (dossier 05, G.3) prescribes the band, "instead of a single diversified number", and warns against claiming that
  diversification benefits are robust; Rosenberg and Schuermann report the sensitivity of the aggregate to the copula choice and the
  additive overestimate of 30 to 40 percent as a study result (https://doi.org/10.1016/j.jfineco.2005.03.001); Embrechts, Puccetti and
  Rueschendorf give the sharp worst-case bounds (https://doi.org/10.1016/j.jbankfin.2013.03.014); the Joint Forum found aggregation models
  "a work in progress" on which supervisors generally do not rely (https://www.bis.org/publ/joint25.pdf; the press release of
  21 October 2010, https://www.bis.org/press/p101021.htm, gives both phrases). Those are the ingredients and the recommendation; what the case adds is to compose them and show the band with every aggregate
  as a gated rule. The claim is about what the case does: that no maintained toolkit or published practice ships the band beside every
  aggregate is UNVERIFIED beyond the dossier's own search. The committed band rests on marginals that the pipeline simulates; the documents commit
  their EL, VaR, ES and EC and, since c18-models 3.0.0, each marginal's quantile function on a named grid (the simulated samples
  themselves are not committed), and Banco Andino is synthetic.

- **BS-10** The batch 3 test corrections, with the error rate each one removes measured on planted data.
  What it adds: the split-conformal coverage test reads the Beta-Binomial law of the covered count given the calibration size (the coverage of
  the set is Beta(k, n_cal + 1 - k) distributed) instead of the binomial the dossier names, and keeps the binomial p-value beside it; the
  shift-resilience light reads an exact permutation reference built from the development rows (199 draws by default) instead of a fixed AUC
  drop; the situation-testing amber cut is 0.20, set on a measured size and power. The level 4 notebooks measure, with the engine's own
  functions on seeded plants and with the standard error of every rate, the rejection rate each correction changes: the binomial coverage
  test rejects 0.1587 and 0.3893 of exchangeable replications at test-to-calibration ratios of 1 and 4 against about 0.044 for the
  Beta-Binomial one, a fixed drop of 0.05 or 0.10 AUC points fires on 0.2000 and 0.0833 of no-shift replications against 0.0667 for the
  permutation reference (which pays in power in that small design), and the situation cut 0.10 fires on 0.0850 of null replications against
  0.0150 for 0.20.
  Evidence: `data/derived/C20/fed-shift.json` (the conformal rows carry the Beta-Binomial `p_value` and `extras.p_value_binomial` side by
  side with `n_cal` and `k`; the resilience row carries its 199 draws and the null summary), `data/derived/C21/pair-2018-19.json` (the
  situation-testing row with its cut point), `docs/design/features/c20/requirements.md` (CT-2009), `tests/c20/test_c20_documents.py`.
  Beyond: the dossier prescribes "a binomial test on coverage indicators" (dossier 06 C.7 l.1025-1026) and PiML's worst-subsample resilience
  (l.1013-1015) without their error rates; Angelopoulos and Bates (https://arxiv.org/abs/2107.07511) give the coverage guarantee, not the size
  of a validation test built on a finite calibration window. Not claimed: the sizes measured in the engine's review (0.1055 for the
  worst-subsample rule, the size and power page of the engine) live in the coordination and engine repositories and are not reproduced by the
  notebook, whose simulations are smaller (1,500, 60 and 200 replications); the measurement shows the direction and the order of magnitude,
  not those figures.

- **BS-11** Reverse liquidity stress as a run-off multiplier with a refusal rule, scored against a labelled run.
  What it adds: the multiplier on the daily run-off rates of every segment at which the survival period first falls to a target of 30
  days, capped so that no rate exceeds 1 and solved as a threshold (the survival period is at most the target at the multiplier and
  longer just below it): 2.118175 on the LiST Adverse base and 1.383141 on the Extreme base. A target that cannot be bracketed is
  refused with its reason and no number is returned (the fast-run base has a horizon of 5 days, below the target of 30). The fast-run
  base is calibrated on the rows of Table A.1 dated before 2023 only, the engine refuses a 2023 row in a scored call, and the 2023 rows
  score it, with the 85% of Silicon Valley Bank in 2 days as a labelled anchor and never a forecast: the modelled loss in those two days
  is 0.1708 against 0.85.
  Evidence: `data/derived/C16/reverse-stress.json`, `data/derived/C16/fast-run.json`, `data/derived/C16/models-svb-liquidity.json`,
  `docs/design/features/c16/requirements.md`.
  Beyond: the research dossier 05 lists reverse liquidity stress as the last rung of its liquidity model ladder ("the run-off multiplier
  at which the survival period falls below a target, for example 30 days") without a measured case, and the ECB's LiST fixes smooth
  scenarios first and reports the survival period they give; the research found no tool that implements the multiplier, which is
  UNVERIFIED beyond the dossier's search. The bank is real in aggregate and synthetic in behaviour and deposits: the multipliers show
  the method on those parameters, not the headroom of the bank.

- **BS-12** The instability of the operational-risk capital, measured on independent histories of known truth.
  What it adds: for four tail indices (0.6, 0.8, 0.96 and 1.1), two history lengths (5 and 10 years) and two collection thresholds
  (EUR 10,000 and 20,000), 1,000 independent simulated histories per cell on disjoint seed ranges (16,000 histories). For each rung
  of a six-rung estimation ladder and for the standardised approach it records the 99.9% capital against the true annual-loss
  quantile of the generator, as the median over the truth, the interquartile range over the truth, the share of histories that
  underestimate and the number of histories on which the rung is defined, and the share of histories whose fitted tail index
  reaches 1, that is, that would conclude an infinite mean. On the committed grid the interquartile range of the splice rung is
  1.35 to 3.30 times the truth, all 92 `oprisk.capital_stability` rows are red against stated internal gates, 27% to 34% of the
  histories of the variant with tail index 0.96 conclude an infinite mean that does not exist, and 9% to 27% of those of the
  variant with tail index 1.1 conclude a finite one.
  Evidence: `data/derived/C17/xi-0-6.json`, `data/derived/C17/xi-0-8.json`, `data/derived/C17/xi-0-96.json`,
  `data/derived/C17/xi-1-1.json`, `docs/design/features/c17/requirements.md`, `tests/c17/test_c17_documents.py`.
  Beyond: the research dossier 05 presents the instability near a tail index of 1 as a teaching case from one illustrative
  calibration of the 2008 loss data medians, with caveats; the Basel Committee's consultative document
  (https://www.bis.org/bcbs/publ/d355.htm) gives complexity and lack of comparability, not a measurement of error, as its reasons
  for removing the advanced approach, and the academic critique of the standardised approach (https://arxiv.org/abs/1607.02319)
  argues its instability and risk insensitivity. None of the sources found measures the dispersion of the LDA capital against a
  known truth over independent histories; that absence is UNVERIFIED beyond the dossier's search. The claim is about a synthetic
  bank whose severity is drawn from the family the tail estimators assume (which favours them) and whose lights use Contraste's
  internal gates; it says nothing about the capital of any real bank.


- **BS-13** A scale-and-level complement to the FRTB P&L attribution test (C13).
  Problem: the PLA's Spearman and Kolmogorov-Smirnov statistics miss a risk model that uses 20-day-old volatility (amber or red in 0.0 % of
  1,000 replications, `data/derived/C13/stale-volatility.json`). Method: a Mincer-Zarnowitz regression of HPL on RTPL with a joint Wald test
  of intercept 0 and slope 1, and the Spearman correlation of |HPL| and |RTPL| and of their 20-day rolling means, with thresholds set to the
  PLA's own size. Hypothesis: at a size of at most 1 %, the stale-volatility model is flagged in at least 30 % of replications; refuted below
  10 %. Evaluation: the six C13 variants from the committed generator, a lag ladder of 5, 10, 20 and 40 days, the size cross-checked on C22.
  Beyond: the regulatory PLA (BCBS MAR32) has no statistic of scale or of volatility timing. Evidence: written with the result.
- **BS-14** An anchored tipping-point PD under informative rating withdrawals (C04).
  Problem: removing, keeping or following withdrawals understates the B-grade PD by 15 to 38 % when withdrawal is informative (`docs/cases/C04.md`).
  Method: the PD by grade as a function of the odds k of withdrawal in the year of default (k = 1 the usual estimate, k large the Manski
  bound, Manski 1989, https://doi.org/10.2307/145818), the tipping k at which a decision flips, k anchored where two sources count defaults
  differently. Hypothesis: the anchored interval covers the true PD in at least 90 % of 200 repetitions at k = 9, the existing treatments
  under 50 %; refuted if coverage is not better or the anchored k is unstable across years. Evidence: written with the result.
- **BS-15** E-process sequential monitors for calibration and back-tests (C22, C11, C03).
  Problem: the fixed-window tests are read once per window. Method: betting e-processes for VaR hits, for defaults against predicted PD by
  grade and for a battery, rejecting when the process exceeds 20 (Ville's inequality: an anytime-valid size of 5 %; Ramdas et al.,
  https://arxiv.org/abs/2210.01948). Hypothesis: the size holds at 5 % under optional stopping where the repeated Kupiec rule exceeds it, and
  the median detection delay is below the 250-day window at severity 3 or more, at a power cost under 10 points; refuted if the delay is not
  lower than the traffic light's. Evidence: written with the result.
- **BS-16** Adaptive conformal recalibration of VaR against the 17-model ladder (C11).
  Method: adaptive conformal inference on each model's level (Gibbs and Candes, https://arxiv.org/abs/2106.00170), wrapped against unwrapped
  on Kupiec, conditional coverage, Acerbi-Szekely Z2 and FZ0 in the stress windows. Hypothesis: HS-250, GARCH-t and FHS wrapped pass in at
  least one more stress window without worsening FZ0 by more than 5 %; refuted if the wrapper fails independence in 2007-09. The French
  equity series is derived-only: the recalibration runs on the device's data root and only its outputs are committed. Evidence: written
  with the result.

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
| ADR-0070 | fits: the App is a workbench with Focus mode (`CaseWorkbench` `focus`, `frontend/src/workbench/Workbench.tsx`); `npm run gate` runs with `--require-focus` (G18); the App's kind is `product.json` `app` (default workbench), and only a surface App without simulation waives Focus, with its reason here as "not applicable: <reason>" |
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
