# Design: U6-P3, case C09, EAD and CCF for revolving lines

Requirements: [`requirements.md`](requirements.md). Parent: [`../../SDD.md`](../../SDD.md) sections 4 and 5. The case page, with
the executive brief, the generator, the known truth and the result read from the committed documents, is
[`../../../cases/C09.md`](../../../cases/C09.md); the contracts are `docs/contracts/schemas/c09/` (`c09-models`, `c09-outputs`)
and the engine contract is `docs/contracts/engine/lgd-ead-api.md` (`riskvalidation` 0.6.0).

## The question

A validator is asked whether a bank's exposure-at-default model for revolving lines is right. The CCF a model estimates depends on
the reference date it is read at, on how the values outside [0, 1] are treated and on how the observations are averaged, and real
data never says what the true CCF was. The case draws revolving-line histories from a generator whose CCF is known, so that each
design, treatment and aggregator can be scored against the truth, at six levels of how strongly drawing accelerates before default.

## Method

1. **Marginals** (`calibration.py`): the three Federal Reserve 2025 card portfolios (200 hypothetical accounts each, low, typical
   and high risk) give, by tier, the credit-limit lognormal, the utilisation (an interior Beta, a share of fully drawn lines and a
   share of lines over their limit, with an exponential excess), the credit score and the APR. The files are fetched to the device
   data root; their size and hash are committed in `params.PARAMS["sources"]`, the recalculated marginals are committed in
   `params.PARAMS["fed_calibration"]`, and a test recalculates them whenever the files are present.
2. **The generator** (`params.py`, `generator.py`): a replication draws 50,000 facilities, assigns each a tier and a 12-month default
   (assumption of the case), and gives each defaulter a default month, a limit and a state twelve months before default from the
   marginals. An interior line draws down its undrawn amount geometrically at the rate `r rho_tier nu` weighted by the monthly
   weights of the level (1 outside the acceleration window, the level's factor inside it), with `nu` a mean-one gamma frailty. Its
   CCF at twelve months is `1 - exp(-r rho nu S)` plus a normal noise (fees, paydowns, overlimit drawings) and its EAD is
   `E0 + CCF (L - E0)`, floored at 0. A line fully drawn or over its limit cannot draw: its EAD is its balance plus capitalised
   interest and fees. The balance path between is the geometric curve scaled to end at the EAD, with a small month-to-month noise.
3. **The known CCF** (`params.known_ccf`): the mean CCF of the defaulters with a defined CCF is the closed form
   `sum_t w_t (1 - (1 + r rho_t S / phi) ** -phi)` (the Laplace transform of the gamma frailty), with `w_t` the tier weights of those
   defaulters. The draw rate `r` is solved once so that level 0 has the anchor 0.60; the other five levels keep `r` and differ only in
   their weights, so their known CCF (0.634, 0.664, 0.714, 0.754, 0.786) is fixed by the parameters and never estimated.
4. **Replications** (`bake.plan`): 20 development and 20 test replications of 50,000 facilities, seeds derived from the case seed
   and disjoint; the six levels of one seed share their facilities (common random numbers), so a difference between levels is the
   drawing profile and not sampling noise.
5. **Estimates** (`estimators.py`): for each defaulter the engine places the reference dates of a design (`ccf.reference_indices`),
   reads the CCF and the undrawn amount (`ccf.ccf_observations`), applies a treatment (`ccf.treat_ccf`) and aggregates
   (`ccf.aggregate_ccf`, `mean` or `pooled`). The bounded-scale estimate is the predicted mean of a fractional logit
   (`lgd_models.fit_fractional_logit`). Each estimate is one value per test replication; the row of `ccf_by_design` is their mean, the
   bias, root mean square error and interval come from `validation.lgd_ead.ccf_estimator_bias`.
6. **EAD models** (`models.py`): CCF constants by design and treatment (pooled, fitted on the development replications), a
   bounded-scale CCF model, a direct EAD model (`ccf.fit_direct_ead`) and a utilisation-change model (`ccf.fit_utilisation_change`),
   each predicted on the test replications and back-tested in currency by utilisation band (`validation.lgd_ead.ead_backtest_by_band`).
   The IRB EAD floor is applied to the 12-month floor-cap model's predictions at the supervisory CCFs (`floors.supervisory_ccf`,
   `ead_floor`, `apply_ead_floor`).
7. **Documents** (`documents.py`, `bake.py`): `c09-models` once, `c09-outputs` per level, the checksums file and the manifest.

## Decisions of the unit (each also stated on the case page)

- The known CCF is the CCF twelve months before default, the Basel fixed horizon. The cohort and the variable-horizon designs read the
  CCF nearer the default, where less of the undrawn amount remains to be drawn, so they are biased low against it; that bias is the
  finding, not a defect of the generator, and the acceleration level changes it.
- The known CCF differs by level (acceleration draws more of the line by default) and is a closed form of the parameters: each
  document carries its own level's truth beside every estimate, and the six levels are not compared to one number.
- A line whose undrawn amount at the reference date is not positive has an undefined CCF. It is excluded from every CCF estimate and
  counted (about one defaulter in five, from the over-limit and fully drawn shares of the Fed files); the EAD models still predict it.
- A default in the first month of its calendar cohort has no reference date before it, so the engine refuses the cohort reference;
  those defaulters (one in twelve) leave the cohort design and are counted.
- The small-undrawn rule of Qi (2009) is computed and its switched lines are counted (`small_undrawn.n_switched`), but it is not
  applied to the estimates (`applied` is false): the generator's CCF noise is on the CCF scale, so a small undrawn amount does not
  blow the CCF up, and dropping those lines would move the truth.
- The CCF-based EAD models apply the CCF to the undrawn amount floored at zero, so a line at or over its limit is predicted at its
  balance; the direct EAD model fits the share of the limit and the engine clips an over-limit share to 1, so the clipped counts are
  reported (`ead_models[].n_clipped_above`) and the model cannot predict an EAD above the limit.
- The engine's fractional-logit solver compares log-likelihoods to 1e-14, so on a pooled sample of tens of thousands of observations it
  can stall at the optimum and raise "did not converge" (found while baking level 2; reported in the unit report). The fit is then
  repeated on every k-th observation of the pooled development sample for the smallest k in (1, 2, 3, 4, 6, 8) that converges; the k
  used is written in the models document (`by_level[].fitted_on_every`).
- `prediction_flag` follows the engine contract literally: `outside-range` when any facility of a band has a prediction below 0 or
  above its limit. A line already over its limit is predicted at least at its balance, so a band of over-limit lines is flagged.

## Limits

Synthetic: the lines are generated, the acceleration levels and the noise are assumptions of the case, and the Fed files give the
shape of the marginals but no default or drawdown history, so no real CCF is estimated. The limit is constant over the run-up (no limit
cut by the lender, so no race to default in Qi's sense); the model of the pre-default drawing is one geometric curve with a gamma
frailty; a revolving line is one product (cards). The mean CCF of the known truth is over the defaulters with a defined CCF. The
zero-adjusted gamma direct EAD model (Tong et al. 2016) is not in the engine release. No compliance claim: the floors and the
supervisory CCFs are the engine's transcriptions of Basel III final (CRE20, CRE32).
