# Design: U6-P2, case C08 (LGD and downturn LGD on the SBA 7(a) charge-off twin)

Status: live. The requirements are in [`requirements.md`](requirements.md), the adversarial checks in
[`validation.md`](validation.md), the reader-facing page in [`../../../cases/C08.md`](../../../cases/C08.md).

## Problem and what is built

A bank's credit risk function must defend its LGD: the loss given default behind a provision or a capital figure, whether it
holds across default cohorts, and what a downturn adds. C08 bakes that on public data and validates it the way a model risk
function would: six cohorts of defaults, each tested out of time on a model trained on what closed before it. It stands on the
engine contract `engine-lgd-ead-api` 1.0.0 (`docs/contracts/engine/lgd-ead-api.md`), implemented by `riskvalidation` 0.6.0 (tag
v0.06.000), and produces the `c08-outputs` and `c08-models` documents (`docs/contracts/schemas/c08/`) as their real producer.

The case runs on the **SBA 7(a) charge-offs, a small-business twin of the mortgage case**: the Freddie Mac loss fields need a
registration the owner has not made, so the product says so, runs on the twin and leaves a reader slot (`io/sba.read_freddie`)
that raises the declared absence. The SBA loans are small-business loans, not mortgages.

## The LGD proxy (CT-902, CT-903; decision D2 of the U6 sizing)

The public file has no recovery cash flows after the charge-off (dossier 08 A.6), so the realised LGD is a **proxy**:
`GrossChargeOffAmount / GrossApproval`, the gross charge-off over the gross approved amount, the only exposure field the file
carries. The approved amount overstates the exposure at default of an amortising loan, so the proxy is **biased low**; a second
effect pushes the other way (recoveries and costs are ignored, and capitalised interest or fees charged off can take the ratio above
1). Every document states the definition, the formula, the two fields, that no recovery cash flow exists and the direction of the
bias. A proxy outside [0, 1] is kept with its range flag and never clipped; the engine fits take an LGD in [0, 1], so a training
default outside it is left out by a counted exclusion. A ratio above ten is a unit error of `GrossApproval` and is left out by a
counted exclusion (17 charge-offs in the real file; one of them is 9,109 times its approval and would move a cohort mean by itself).

## The cutoff rule (CT-904, CT-905, CT-906)

The variants are the default cohorts by charge-off year: 2003-06, 2007-08, 2009-10, 2011-13, 2014-19, 2020-23. The model of a
cohort is trained to the last day of the year before it, on the defaults whose charge-off closed strictly before that cutoff
(the engine's `closed_before`); it is tested on the cohort and on every later cohort (all out of time by default date). The file
records the charge-off and nothing after it, so the charge-off date is the closing date of the workout. It also has no default date
before the charge-off, so a workout open at the cutoff cannot be observed; the document counts, as its stand-in, the charge-offs of
the twelve months after the cutoff (`n_open_workouts_excluded`): none of them is in the training set. The test perturbs every
default charged off on or after the cutoff and asserts that the fitted coefficients, the predictions and the counts are bit-identical.

## The ladder (CT-907)

Six rungs on the covariates known at the charge-off (log approval, log term, guaranteed share of the approval, seasoning, revolving,
eleven sector dummies): L1 OLS, L2 fractional logit, L3 beta (at three epsilons, 0.0001, 0.001 and 0.01, all reported in
`endpoint_sensitivity`), L4 hurdle, L5 gradient boosting (catboost 1.2.10, a classifier with the cross-entropy loss, one thread, a
fixed seed), L6 two-limit Tobit; the first four and the last are the engine's fits. A rung the engine refuses or that does not
converge is reported not evaluated with its reason and no number. The fits report no standard error (the engine's `LgdFit` has none),
so `std_error` is null.

## The documents (CT-910, CT-912)

The per-rung blocks (`rung_comparison`, `realised_vs_predicted`, `calibration_by_bucket`, `endpoint_sensitivity`) and the tests
come from the engine's `riskvalidation.validation.lgd_ead`: calibration by segment (the cohort), calibration over time (the default
years of the test cohort and later ones) and discrimination, for every fitted rung; the interval of a `realised_vs_predicted` row is
the predicted mean plus the engine's interval of the mean gap. The floors' bite is the engine's `apply_lgd_floor` on the reference rung
(L2, then L1) over four segments (lines of credit, terms to 7 years, 7 to 20 years, 20 years or more); the file has no collateral
field, so the collateral is inferred from the term and the revolving status and said so. The twelve floor cells are the engine's
`lgd_floor`.

## The downturn (CT-911)

Contraste's own cohort-based add-on, an illustration and not a regulatory estimate. The downturn years are the engine's
`identify_downturn` on the annual charge-off rate of the SBA book (charge-offs of the year over the loans open on 1 January) with the
mean plus one standard deviation as the threshold; the period is the longest run of such years; a cohort is a downturn cohort when at
least half of its default years are inside it. The add-on is the engine's `downturn_add_on`: the default-weighted mean over the
downturn cohorts minus the long-run mean over the six cohorts, judged against each downturn cohort's realised proxy by
`coverage_shortfall` and `downturn_coverage`. The block is a fact of the whole file and is identical in every variant; the rungs are
the models of a cutoff and it is not. The registry lists the Federal Reserve history tables for other cases and not for C08, so the
case reads no macro path; a macro indicator (unemployment) replaces the book's own rate the day the registry lists C08 for it.

## Limits

The proxy is not a workout LGD. The cohorts are by charge-off year, which lags the default by months to a year or more. The collateral
of the floors is inferred. The SBA book is a guaranteed-lending programme, its LGD to the lender is not the LGD of an unguaranteed
loan. The charge-off counts of 2004 and 2005 are low and 2006 jumps, a feature of the file's reporting that the rates carry.
