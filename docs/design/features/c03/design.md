# Design: U6-P1, case C03 (SME PD by vintage through 2008, on the SBA 7(a) loans)

Status: live. The requirements are in [`requirements.md`](requirements.md), the adversarial checks in
[`validation.md`](validation.md), the reader-facing page in [`../../../cases/C03.md`](../../../cases/C03.md).

## Problem and what is built

A bank that built a small-business PD model on the cohorts it had seen, and then lived through a crisis, has to know three things
about the model: whether it ranked borrowers, whether its level was right for the cohorts that followed, and whether the validator
that said so read the outcomes honestly. C03 bakes that chain on the public SBA 7(a) loans. It produces the `c03-outputs` and
`c03-models` documents (`docs/contracts/schemas/c03/`) as their real producer, with the rungs of the C01 PD ladder
(`cases/c01_ladder.py` over `pipeline/model`) and the PD validation tests of the `riskvalidation` 0.5.0 engine (tag v0.05.000);
the product defines no rung and no test.

The loans are **small-business loans made under a federal guarantee, not the SME book of a bank**: the file has no delinquency
history, no balance and no rating, the interest rate is recorded only from the FY2008 approvals, and a sample of guaranteed loans
is not a bank's portfolio. The page and the findings say so.

## The target and the cutoff rule (CT-802, CT-804, CT-805)

The target of a loan is a charge-off within 60 months of approval. A vintage is the approval fiscal year (1 October to 30
September) and its target is read only at its 5-year mark, 30 September of the fiscal year plus 5, the date by which every loan
of the vintage has been observed for 60 months. The label of a loan at an observation date O is an event (a charge-off dated on or
before the horizon end and O), a non-event (O on or after the horizon end and no such charge-off) or no outcome (O before the
horizon end and no charge-off yet). The file shows a charge-off as CHGOFF, never as an active loan, so a loan active at O and
older than 60 months is a known non-event; a loan active and younger is right-censored: it has no outcome, is counted apart
(`n_exempt_censored`) and is never counted as performing. A vintage whose mark is after O carries a null observed value with its
reason; a cohort with no observed mark is refused.

## The training windows (CT-803, decision D1)

Each test cohort trains only on approval fiscal years whose 5-year mark falls before its first approval date, so no outcome is seen
early: a cohort starting in fiscal year F trains on FY1991 to FY(F - 6), the outcomes read up to 30 September of F - 1. The
FY2006-07 cohort trains on FY1991-2000, FY2008-10 on FY1991-2002, FY2011-14 on FY1991-2005, FY2015-17 on FY1991-2009 and
FY2018-20 on FY1991-2012. "Trained through the crisis" holds for FY2011-14 and later: the flag is computed, not declared, from
the charge-offs of the window dated in the December 2007 to June 2009 recession (NBER). The test perturbs every approval and
every outcome after the cutoff and asserts that the training labels, the declared directions and every rung are bit-identical.

## The ladder (CT-806)

The rungs are those of C01, fitted on each window by `fit_ladder`: the constant PD, the WoE scorecard (the champion), the
penalised (L1) logit on WoE, PLTR, the explainable boosting machine and the monotone LightGBM (isotonic maps from the calibration
slice for the last two). The inputs are five origination attributes: the log amount, the guaranteed share, the term, the sector
group and whether the loan is revolving. The monotone directions are declared from the window before any fit, the sign of the
Spearman correlation with the target where it is at least 0.02 in magnitude. A window of about a million loans is fitted on a
stratified sample of 40,000 (the isotonic maps on a disjoint sample of up to 20,000; the PLTR rung alone took 13 minutes at 100,000 rows); the sizes are in every model record. A
window with fewer than 100 events or 100 non-events fits the constant only and reports the other rungs as not evaluated with the
counts. The TabPFN challenger is the optional extra and is declared absent with its reason.

The predicted cumulative curve of a vintage is the 5-year PD of the champion allocated in time by the share of the window's
5-year charge-offs that fall by month 12, 24, 36, 48 and 60 (half an event is added to every count so that the share by month 12
is not zero). The 5-year PD is the model's; the allocation is a description of the training window.

## The battery (CT-807)

Every row is a `riskvalidation` 0.5.0 `TestResult` under the engine's default policy: the AUC against the calibration slice
(`disc.auc_vs_initial`), DeLong against the champion, the level of the PD (Jeffreys, the exact binomial, the Vasicek-corrected
binomial with a 0.12 asset correlation, the one-factor value of dossier 02 B.4), Hosmer-Lemeshow and Spiegelhalter, and the PSI of
the PD against the training rows; per vintage the level tests. The descriptive metrics (AUC with its interval, Brier score) are
the engine's, in the rung comparison and the vintage rows: the engine gives them no traffic light, and the variant contract
reserves `not_evaluated` for a test that did not run, with null numbers and a reason.

## Documents, determinism and the expected ranges (CT-808 to CT-811)

`data/derived/C03/models-sba-7a.json` (the five cohort windows, each with its own training window, and the rungs of the latest
window with their internals), one variant per cohort, and the manifest `data/derived/manifests/C03.json`, which lists each
document with its path and exact size (the manifest schema has no hash field; the bake is a pure function of the files and the
seed, and the test compares the content hashes of two bakes). The expected ranges are declared in `_case.EXPECT` before the bake,
from the charge-off counts per fiscal year.
