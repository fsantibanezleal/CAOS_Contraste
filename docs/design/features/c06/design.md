# Design: U5-P1, case C06 (lifetime PD, IFRS 9 staging and ECL on the SBA 7(a) twin)

Status: live. The requirements are in [`requirements.md`](requirements.md), the adversarial checks in
[`validation.md`](validation.md), the reader-facing page in [`../../../cases/C06.md`](../../../cases/C06.md).

## Problem and what is built

A bank's provisions function must defend its IFRS 9 expected credit loss: the lifetime PD behind it, the stage each loan
sits in, the scenarios that weight it, and how the model of a date behaves on what happened after that date. C06 bakes that
chain on public data and validates it the way a model risk function would. It stands on the engine contract
`engine-provisions-api` 1.0.0 (`docs/contracts/engine/provisions-api.md`), implemented by `riskvalidation` 0.5.0 (tag
v0.05.000), and produces the `c06-outputs` and `c06-models` documents (`docs/contracts/schemas/c06/`) as their real producer.

The case runs on the **SBA 7(a) loans, a small-business twin of the mortgage case**: the Freddie Mac loan-level data needs a
registration the owner has not made (owner prerequisite 4), so the product says so, runs on the twin and leaves a reader slot
(`readers.read_freddie`) that raises the declared absence. The SBA loans are small-business loans, not mortgages.

## The cutoff rule (CT-504, CT-505)

A model for a reporting date R sees the loans approved on or before R and, of each, only the exits on or before R; a loan with
no default or payment by R is censored at R (or at its maturity), and its hazard exposure counts only the quarters it was
observed. Whether a loan is in the book at R is read from its own exit dates (a fact of R). The macro history is cut at the
last quarter ended on or before R. The test perturbs every outcome, approval and macro value after R and asserts that the
rungs, the staging and the ECL of R are bit-identical.

The scenarios are the one place a 2026 file enters a 2006 model: the Federal Reserve publishes 13-quarter paths from a 2025 Q4
jump-off, and the product transposes their shape (the change of each variable from that jump-off) onto the last value known at R,
so a scenario is a stress design, not a forecast known at R. This is stated on the case page. The history values are the 2026
release (revised); real-time vintages are not in the files.

## The ladder (CT-506)

Statsmodels 0.15.0 (lifelines needs pandas below 3.0 and the pipeline pins 3.0.6): L0 Kaplan-Meier on loan age; L1 a
discrete-time hazard, a binomial logit on loan-quarter cells aggregated by (stratum, age band, calendar quarter), with the loan
covariates (size band, term band, sector group, revolving), the age profile and three macro variables (unemployment rate, real GDP
growth, prime rate) one quarter before each cell, limited to the training range widened by a quarter of it; L2 Cox with the loan
covariates (PHReg, Breslow ties, no time-varying covariate). Prepayment is censoring in every rung. A vintage with fewer than 200
loans or 30 defaults is not fitted and is reported with its counts and the reason.

## The chain (CT-507 to CT-509)

Per account of the book at R: the quarterly hazards under each scenario give a term structure (`from_hazard`), the marginal PDs
with the loss given default, the modelled balance and the original EIR give the ECL (`ecl_scenario`, mid-period), the origination
expectation (the same hazard with the macro frozen at its value one quarter before approval) and the probability-weighted current
PD, annualised (`annualise_pd`), give the SICR test (`allocate_stages` with the contract's policy), and the stages and ECLs give
the allowance (`portfolio_allowance`). The ECL is the probability-weighted one over three scenarios (baseline 0.60, adverse 0.30,
severely adverse 0.10, policy weights, not the Fed's); each scenario's figure is at 100 per cent weight with the staging frozen. The
one-factor view (rho 0.12, dossier 02 B.4 and C.1) gives the PD-level non-linearity and the weight simplex; the systematic factor of
a scenario is the one its mean hazard implies (`implied_z`), and the satellite is the least-squares reduced form of the hazard rung.
Overlays are separate lines carried in their stage and never change the model ECL; the public portfolio has none, none is invented,
and the line mechanics are tested with a declared test overlay.

## What the file cannot say (stated on the page and in the findings)

No delinquency, forbearance or watch-list history: the 30 days past due backstop never fires, only the quantitative SICR test moves
a loan to Stage 2, and a charge-off (default) removes the loan, so Stage 3 holds no balance at a date and the defaults of a window
pass through it in the roll-forward. No balance: a level-payment annuity at the EIR (revolving lines at their approval). No
recovery after the charge-off: the LGD is a charge-off severity proxy with an upward bias and the ECL is before the SBA guarantee.
The interest rate is recorded only from the FY2008 approvals: the earlier loans take the prime rate of the quarter before approval.

## The roll-forward (CT-510)

Between R minus 12 months and R each loan is continuing, repaid, charged off or new; the rules are the module text of
`rollforward.py`. The engine builds the rows and judges the identities on the contract's tolerance basis.

## Decisions taken without the owner (to confirm)

- No management overlay is invented for the public portfolio (the overlays array is empty).
- Probation is 0 months: the file has no cure dates and the reporting dates are a year apart.
- The scenario weights (0.60, 0.30, 0.10), the asset correlation 0.12, the lifetime cap (120 months) and the model's policy constants
  are policy parameters, listed on the case page.
