# Design: U1, case C01, retail cards PD (champion vs challenger)

Requirements: [`requirements.md`](requirements.md). Parent: [`../../SDD.md`](../../SDD.md) sections 4 and 5.
Sources: research dossier 04 (sections A, B, J and the PD ladder), dossier 06 (sections C.1 to C.4, the test
catalogue), dossier 08 (A.1, the UCI licences).

## The question

Does a monotone WoE logistic scorecard (the champion a validator expects) match the challengers that the literature
says can beat it (penalised LR and PLTR, EBM, monotone gradient boosting), on discrimination, calibration and
stability, and is any challenger's gain significant (DeLong) once calibration is required? And what do the
validation tests a validator and a supervisor would run say about each, when the evaluation population shifts?

## Data

- **UCI Default of Credit Card Clients (Taiwan)**, Yeh and Lien (2009), CC BY 4.0, DOI 10.24432/C55S3H: 30,000
  card holders, payment records April to September 2005, target "default payment next month" (Yes = 1). The 23
  explanatory variables as the UCI page describes them (read 2026-10-05): X1 `LIMIT_BAL`, the given credit in NT
  dollars including the family (supplementary) credit; X2 `SEX` (1 male, 2 female); X3 `EDUCATION` (1 graduate
  school, 2 university, 3 high school, 4 others); X4 `MARRIAGE` (1 married, 2 single, 3 others); X5 `AGE` in years;
  X6 to X11 `PAY_0`, `PAY_2` to `PAY_6`, the repayment status in September back to April 2005 (-1 pay duly, 1 to 8
  months of delay, 9 nine months and above); X12 to X17 `BILL_AMT1` to `BILL_AMT6`, the bill statements in NT
  dollars, September back to April; X18 to X23 `PAY_AMT1` to `PAY_AMT6`, the amounts paid.
- **UCI Statlog German Credit**, Hofmann (1994), CC BY 4.0, DOI 10.24432/C5NC77: 1,000 applicants, 20 attributes
  (7 numerical, 13 categorical), good (1) or bad (2), with the dataset's cost matrix (a bad classified as good costs
  5, a good classified as bad costs 1). It is the small-sample twin.

Both are single snapshots: **no out-of-time validation is possible**, and every page that shows C01 says so.

### Codes outside the documented scale

The data carry values the codebook does not define (`EDUCATION` 0, 5 and 6; `MARRIAGE` 0; repayment status -2 and
0). Contract 1 accepts them and flags each one, counted in the manifest; they are kept as their own bins (the
binning engine bins them separately), never recoded to a documented value, because recoding would be a guess.

### Protected characteristics

Sex and marital status (Taiwan), and personal status and sex and foreign-worker status (German), are prohibited
bases in fair-lending regimes; age is restricted. C01's models do not take sex, marital status, personal status or
foreign-worker status as inputs. Age is also excluded, so that no rung needs an age-specific justification. Sex is
kept as the record's `protected_attr`, so the Validation view can report discrimination by group; the fairness
battery itself is C21's (dossier 04 J.3).

## The split (leakage-safe)

1. A **locked stratified holdout** of 30% (seeded), opened only by the evaluate stage.
2. The remaining 70% is the development set: a **calibration slice** of 20% of it (stratified, seeded), disjoint
   from the holdout, fits every calibration map; the rest is the **training slice**.
3. Binning, WoE, imputation, scaling, rule extraction and hyperparameter choice are fitted on the training slice
   only; hyperparameters are chosen by repeated stratified 5-fold CV inside it.

## The variants (each changes the evaluation population; none touches training, except where stated)

| Variant | What it is | Truth status |
|---|---|---|
| `holdout` | the locked holdout as observed | real-outcomes |
| `drift-moderate` | the holdout resampled with a known covariate shift toward recent delinquency (weights proportional to exp(0.25 z), z the standardised September repayment status); P(y given x) unchanged | synthetic-known-truth |
| `drift-severe` | the same shift at exp(0.6 z) | synthetic-known-truth |
| `prior-shift` | the holdout resampled so the default rate is 1.5 times the observed one; P(x given y) unchanged | synthetic-known-truth |
| `label-noise` | 5% of the holdout labels flipped at random | synthetic-known-truth |
| `small-sample` | the ladder retrained on 2,000 rows of the training slice and evaluated on the same holdout (estimation risk) | real-outcomes |
| `german-twin` | the whole ladder on German Credit, with the TabPFN challenger (small data is where it is strongest) | real-outcomes |

Each shift is a deliberate perturbation with a known size, so the test that should detect it (PSI for covariate
shift, the calibration tests for prior shift, the discrimination tests for label noise) can be judged against the
truth.

## The ladder

| Rung | Method | Engine (licence) | Accepted when |
|---|---|---|---|
| P0 | constant PD (the training default rate) and the single-variable benchmark (the September repayment status, binned) | own | AUC of the constant is 0.5 exactly |
| P1 | WoE logistic scorecard: optimal monotone binning, logistic regression on WoE, PDO scaling (600 points at odds 50 to 1, 20 points to double the odds) | optbinning (Apache-2.0), statsmodels (BSD-3) | monotone event rates in every binned variable; the points table recomputes every holdout score exactly |
| P2a | penalised logistic regression (L1, cross-validated strength) on the WoE inputs | scikit-learn (BSD-3) | coefficient signs agree with WoE; paired DeLong against P1 reported |
| P2b | PLTR, Dumitrescu et al. (2022): rules from depth-2 trees as extra inputs to an L1 logistic regression | scikit-learn, own rule extraction | rule set stability across 20 bootstraps (Jaccard) reported |
| P3 | EBM with monotone constraints where declared, a few pairwise terms | InterpretML (MIT) | shape functions monotone where declared; per-term points; the live additive score equals the offline one within 1e-9 |
| P4 | monotone gradient boosting (LightGBM; XGBoost as the engine cross-check) with an isotonic calibration map fitted on the calibration slice | LightGBM (MIT), XGBoost (Apache-2.0), scikit-learn | monotone on the partial-dependence grid of every constrained feature; Brier and reliability before and after calibration; SHAP reason-code stability (top-4 overlap across bootstraps) |
| P5 | TabPFN, German twin only (TabPFN v2 weights, Prior Labs License v1.1, attribution "Built with PriorLabs-TabPFN") | tabpfn (code Apache-2.0) | same gates as P4; its view shows the weight licence and the attribution, and Context lists it with every engine |

Monotone directions (declared before fitting, from the meaning of the variable): more delinquency (`PAY_*` higher)
raises risk; a larger limit and larger payments lower it. Bill amounts carry no declared direction.

## The battery (riskvalidation, under its versioned policy)

Per rung and variant: AUC with its DeLong variance and the ECB comparison against the development AUC
(`disc_auc`, `disc_auc_vs_initial`), DeLong paired against the champion (`disc_delong`), KS (`disc_ks`); on the
master scale (geometric PD grades), the Jeffreys test per grade and for the portfolio, the binomial and
Vasicek-adjusted binomial tests, the chi-square over grades, Hosmer-Lemeshow, Spiegelhalter, Brier with the Murphy
decomposition, ECE; grade concentration (HHI); PSI of the score and CSI of every input against the training slice,
with the Yurdakul and Naranjo chi-square benchmark beside the conventional bands.

## The impact

Decision impact at a cut-off chosen in the rail: approval rate, bad rate among the approved, the expected loss
EL = PD x LGD x EAD with EAD the current bill (`BILL_AMT1`, floored at 0) and a stated LGD assumption; the cost of
the German cost matrix for the twin. The IRB capital of each approved book (qualifying revolving retail for the cards,
other retail for the German loans, under Basel III final, CRR3 and Basel II) is U2's second part:
[`../c01-irb-capital/design.md`](../c01-irb-capital/design.md).

## The artifacts

One models artifact per fit (`taiwan`, `taiwan-small`, `german`): the points table, the EBM shape functions, the
GBM partial-dependence grids, the reason-code stability, the hyperparameters and the training metadata. One
variant artifact per variant: the outputs (ROC and CAP curves, calibration by grade, reliability before and after
calibration, score distributions, PSI and CSI, the cut-off curve, a sample of 50 scored applicants for the live
parity test), the `TestResult` rows, the impact, the findings and the provenance. Every artifact stays under the
256 KiB trace budget.
