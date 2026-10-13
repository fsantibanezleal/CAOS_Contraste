# Engine LGD and EAD API contract: `engine-lgd-ead-api` 1.0.0

Owner: U6-S (unit sizing `plans/contraste/units/U6-sizing.md`, CAOS_MANAGE). Implemented by U6-E in `riskvalidation.lgd_ead` and
`riskvalidation.validation.lgd_ead` (repository CAOS_RiskValidation); called by the C08 and C09 bakes (U6-P2, U6-P3). The tests of
every function are written by U6-E against this file: a function exists with exactly the signature below, and each golden value or
invariant is a test. Changing a signature, a unit or a golden value is a breaking change (a new major version of this contract).
Sources: dossier 04 (`wip/contraste/04-credit-risk-models-sota-2026-10-04.md`, sections F.1 to F.4 for LGD and G.1 to G.3 for EAD and
CCF) and dossier 01 (`wip/contraste/01-basel-pillar1-pillar2-framework-2026-10-04.md`, section A.5 for the IRB LGD, EAD and CCF
floors, section B.2 for the standardised CCFs); the product SDD section 4 gives the acceptance rows this contract serves ("LGD
rungs", "CCF/EAD rungs") and section 5 the cases C03, C08 and C09.

The engine computes; it states no compliance claim. Nothing here is a Basel, CRR or EBA requirement beyond what the dossier sections
cite; discount rates, downturn periods, thresholds and light parameters are policy parameters the caller supplies or the function
states. Every constant and floor cell below is transcribed from the dossier named on its line; an item the dossier marks UNVERIFIED
is marked UNVERIFIED here and is not silently decided.

## Conventions (all functions)

- Arrays are `numpy.ndarray` of `float64` (integers `int64`, flags `bool`, dates `datetime64[D]`). Shapes: `A` facilities or
  defaulted exposures, `K` cash-flow dates, `N` observations, `R` reference dates, `B` bins, `T` months of a facility path.
- Rates are decimals. **LGD** is closed [0, 1] at an estimate site (a prediction): every model of `lgd_models` returns a value in
  [0, 1]. A **realised** LGD may lie outside [0, 1] (costs, fees, additional drawings; dossier 04 F.2): it is kept, never clipped, and
  flagged with `range_flag` (`in-range`, `below-zero`, `above-one`); the case documents carry the pair as `{value, flag}` and a
  value outside [0, 1] validates only with its flag. **CCF** is in the EU convention (the share of the undrawn amount drawn by default,
  the LEQ in US terms; dossier 04 G.1): a CCF below 0 or above 1 is kept and flagged the same way (dossier 04 G.2) unless a named
  treatment (`treat_ccf`) is asked for, and the treatment is reported with its counts. PDs do not appear here.
- Money is a float in the portfolio currency; the currency code travels in the document (`currency`), never in a function. Money is
  never converted between currencies by the engine.
- Horizons and reference dates are integer months; a workout cash-flow time is a float number of years since the default date; dates
  are ISO strings or `datetime64[D]` only at the boundary of `closed_before`.
- Every function is pure and deterministic (no hidden state, no randomness, no I/O, inputs never mutated) and returns new arrays. A
  fit is deterministic for the same inputs (the optimiser, its start and its tolerance are fixed by the implementation).
- Dataclasses are frozen. A function that cannot compute a value because data is missing raises `ValueError` with the reason, or (a
  validation function) returns the `not_evaluated` light with its reason in `notes`; it never returns a placeholder number.
- Tolerance: every golden value states its own tolerance or is exact; a golden stated to six decimals holds to `5e-7`.
- A validation function returns one `TestResult` of `riskvalidation`, serialised by `dataclasses.asdict` into a row that validates
  against `common/test-result` (the schema `docs/contracts/schemas/common/test-result.schema.json`): `test_id`, `model_id`,
  `segment`, `statistic`, `p_value`, `metric`, `h0`, `alternative`, `policy_version`, `alpha_amber`, `alpha_red`, `light`, `n`,
  `n_events`, `inputs_hash`, `reference`, `notes`, `extras`.

## How the documents use the engine

| Document block (schema) | Produced by |
|---|---|
| C08 `outputs.workout`, `exposure`, `lgd_distribution` (masses at 0 and 1, values outside [0, 1] counted) | `workout.*` |
| C08 `outputs.rung_comparison`, `realised_vs_predicted`, `calibration_by_bucket`, `endpoint_sensitivity`; C08 models `ladder` | `lgd_models.*`, `validation.lgd_ead.lgd_calibration_by_segment`, `lgd_calibration_over_time`, `lgd_discrimination` |
| C08 `outputs.downturn` | `downturn.*`, `validation.lgd_ead.downturn_coverage` |
| C08 `outputs.floors_bite`; C08 models `floors.cells` | `floors.lgd_floor`, `floors.apply_lgd_floor` |
| C09 `outputs.ccf_by_design`, `ccf_distribution`, `small_undrawn`; C09 models `designs`, `treatments` | `ccf.reference_indices`, `ccf_observations`, `aggregate_ccf`, `treat_ccf`, `small_undrawn_rule`, `validation.lgd_ead.ccf_estimator_bias` |
| C09 `outputs.ead_models`, `ead_backtest` | `ccf.fit_direct_ead`, `fit_utilisation_change`, `predict_ead`, `ead_from_ccf`, `validation.lgd_ead.ead_backtest_by_band` |
| C09 `outputs.ead_floor`; C09 models `floors` | `floors.ead_floor`, `apply_ead_floor`, `supervisory_ccf` |
| C03 (SME PD by vintage) | no function of this contract: C03 calls the PD rungs and tests the engine already has (release 0.05.000) |
| C08 and C09 `tests` | `riskvalidation.validation.lgd_ead.*` (rows of `common/test-result`) |

The C08 document describes a **proxy**: the SBA 7(a) public file has no recovery cash flows (dossier 08 A.6), so the C08 bake does
not call `workout_lgd`; it states `workout.discount_rate_convention = "none-proxy"` and `incomplete_workouts.treatment =
"not-applicable"`, and divides the gross charge-off by the exposure at charge-off. `workout_lgd` serves the workout case (and its
golden values) the moment recovery data exists, for instance the Freddie Mac loss fields once the owner's account does.

## Module `riskvalidation/lgd_ead/workout.py`

Realised (workout) LGD of dossier 04 F.1: for a defaulted exposure `i` with `EAD_i`, recoveries `R`, direct and indirect costs `C` and
additional drawings `Add` after default at times `t` (years since the default date), discounted at `r_i`:
`LGD_i = 1 - sum_t (R_t - C_t - Add_t) (1 + r_i)^(-t) / EAD_i`.

### `riskvalidation.lgd_ead.workout.eba_discount_rate`

```python
def eba_discount_rate(interbank_rate: float, add_on: float = 0.05) -> float: ...
```

- Units: decimals per year; `interbank_rate` is the primary interbank offered rate at the default date in the currency (for example the
  3-month rate), `add_on` five percentage points by default.
- Invariants: returns `interbank_rate + add_on`; `ValueError` for a negative `add_on`. The convention is the reading of EBA/GL/2017/16
  in dossier 04 F.1 (an interbank rate plus 5 percentage points); its paragraph number (section 6.3.1.3 per a search summary) is
  UNVERIFIED. The caller may pass any other rate to `workout_lgd`; this function only names the convention.
- Golden: `eba_discount_rate(0.0325) = 0.0825`.

### `riskvalidation.lgd_ead.workout.workout_lgd`

```python
def workout_lgd(ead: np.ndarray, times: np.ndarray, recoveries: np.ndarray, costs: np.ndarray,
                drawings: np.ndarray, rate: float | np.ndarray) -> np.ndarray: ...
```

- Units: `ead` (A,) money, strictly positive (otherwise `ValueError`); `times` (A, K) years since the default date, strictly positive;
  `recoveries`, `costs`, `drawings` (A, K) money, nonnegative, zero-padded where an exposure has fewer than `K` flows; `rate` a decimal per
  year, scalar or (A,); the result (A,) LGD decimals, **not clipped**.
- Invariants: `LGD = 1 - sum_k (R - C - Add) (1 + r)^(-t) / EAD`; with `rate = 0` the result is `1 - sum(R - C - Add) / EAD`; the result is
  nonincreasing in `recoveries` and nondecreasing in `costs`, `drawings` and `rate`; a value below 0 or above 1 is returned as is (the
  caller flags it with `range_flag`).
- Golden: one exposure `ead = 100`, `times = [[1, 2]]`, `recoveries = [[40, 30]]`, `costs = [[10, 0]]`, `drawings = [[0, 0]]`, `rate = 0.10`:
  `PV = 30 / 1.1 + 30 / 1.21 = 52.066116`, `LGD = 0.479339`. With `recoveries = [[5, 0]]`, `costs = [[20, 0]]`: `LGD = 1.136364` (above-one). With
  `recoveries = [[120, 0]]`, `costs = [[0, 0]]`: `LGD = -0.090909` (below-zero).

### `riskvalidation.lgd_ead.workout.range_flag`

```python
def range_flag(values: np.ndarray) -> np.ndarray: ...
```

- Units: a (N,) array of LGD or CCF decimals; the result (N,) of `str` in `{"in-range", "below-zero", "above-one"}`.
- Invariants: `below-zero` for `value < 0`, `above-one` for `value > 1`, otherwise `in-range` (0 and 1 are in range); a NaN raises
  `ValueError`; the flag agrees with the `{value, flag}` wrapper of `c08Lgd` and `c09Ccf` (a document with a different flag does not validate).
- Golden: `[-0.090909, 0.0, 0.5, 1.0, 1.136364]` gives `["below-zero", "in-range", "in-range", "in-range", "above-one"]`.

### `riskvalidation.lgd_ead.workout.ResolvedWorkouts`

```python
@dataclass(frozen=True)
class ResolvedWorkouts:
    lgd: np.ndarray        # (M,) the LGDs that remain
    n_excluded: int        # incomplete workouts dropped
    n_projected: int       # incomplete workouts replaced by a projection
    treatment: str         # "excluded" or "projected"
```

- Units: LGD decimals; counts.
- Invariants: `n_excluded + n_projected` equals the number of incomplete workouts; `treatment = "excluded"` has `n_projected = 0` and
  `M = A - n_excluded`; `treatment = "projected"` has `n_excluded = 0` and `M = A`. The counts map to the document block
  `workout.incomplete_workouts` (`treatment`, `n_excluded`, `n_projected`).

### `riskvalidation.lgd_ead.workout.resolve_incomplete`

```python
def resolve_incomplete(lgd: np.ndarray, complete: np.ndarray, treatment: str,
                       projected: np.ndarray | None = None) -> ResolvedWorkouts: ...
```

- Units: `lgd` (A,) decimals (the values of incomplete workouts are ignored), `complete` (A,) bool, `treatment` in `{"excluded", "projected"}`,
  `projected` (A,) decimals required and finite at every incomplete position when `treatment = "projected"`.
- Invariants: an incomplete workout is never silently kept as if complete: excluding them biases LGD down, so the treatment is a required
  argument and the counts are returned (dossier 04 F.1); `ValueError` for an unknown treatment or a missing projection.
- Golden: `lgd = [0.2, 0.6, 0.9]`, `complete = [True, True, False]`: `"excluded"` gives `lgd = [0.2, 0.6]`, `n_excluded = 1` (mean 0.4);
  `"projected"` with `projected = [nan, nan, 0.7]` gives `lgd = [0.2, 0.6, 0.7]`, `n_projected = 1` (mean 0.5).

### `riskvalidation.lgd_ead.workout.closed_before`

```python
def closed_before(close_dates: np.ndarray, cutoff: str) -> np.ndarray: ...
```

- Units: `close_dates` (A,) `datetime64[D]`, `NaT` for an open workout; `cutoff` an ISO date; the result (A,) bool.
- Invariants: true only when the workout closed strictly before the cutoff (a close on the cutoff date is not before it); an open workout is
  false; this is the training-set rule of dossier 04 (leakage rule 5): the training set holds only defaults whose workout closed before the
  training cutoff, and the test set uses later default cohorts.
- Golden: `close_dates = [2008-06-30, 2008-12-31, 2009-03-31, NaT]`, `cutoff = "2008-12-31"` gives `[True, False, False, False]`.

### `riskvalidation.lgd_ead.workout.LgdDistribution`

```python
@dataclass(frozen=True)
class LgdDistribution:
    edges: np.ndarray      # (B + 1,) strictly increasing, edges[0] = 0.0 and edges[-1] = 1.0
    counts: np.ndarray     # (B,) int64 values inside [0, 1], bin i is [edges[i], edges[i+1]), the last bin is closed
    n: int
    n_below_zero: int
    n_above_one: int
    mass_zero: int         # values exactly 0
    mass_one: int          # values exactly 1
```

- Units: counts; the C08 block `lgd_distribution` serialises it (`bins`, `mass_at_zero`, `mass_at_one`, `n_below_zero`, `n_above_one`,
  shares as counts over `n`).
- Invariants: `counts.sum() + n_below_zero + n_above_one == n`; `mass_zero <= counts[0]` and `mass_one <= counts[-1]`; values outside
  [0, 1] are counted, never placed in an end bin.

### `riskvalidation.lgd_ead.workout.lgd_distribution`

```python
def lgd_distribution(lgd: np.ndarray, edges: np.ndarray) -> LgdDistribution: ...
```

- Units: `lgd` (N,) decimals, `edges` as in `LgdDistribution` (otherwise `ValueError`).
- Invariants: the masses at 0 and 1 are exact equality counts, so the bimodality of dossier 04 F.2 is visible; a NaN raises `ValueError`.
- Golden: `lgd = [-0.05, 0, 0, 0.25, 0.5, 1, 1, 1.2]`, `edges = [0, 0.5, 1.0]` gives `counts = [3, 3]`, `n = 8`, `n_below_zero = 1`,
  `n_above_one = 1`, `mass_zero = 2`, `mass_one = 2`.

## Module `riskvalidation/lgd_ead/lgd_models.py`

The LGD rungs of dossier 04 F.3. A design matrix `X` (N, K) **includes its intercept column**; no function adds one. Library notes
(statsmodels `GLM` Binomial for the fractional logit, `othermod.betareg.BetaModel` for beta regression, which its documentation marks
experimental; scipy for Tobit) are implementation choices of U6-E, not part of the contract; the golden values below hold to the stated
tolerance whatever the optimiser.

### `riskvalidation.lgd_ead.lgd_models.endpoint_transform`

```python
def endpoint_transform(y: np.ndarray, epsilon: float) -> np.ndarray: ...
```

- Units: `y` (N,) LGD decimals; `epsilon` in (0, 0.5), otherwise `ValueError`; the result (N,) in [epsilon, 1 - epsilon].
- Invariants: `min(max(y, epsilon), 1 - epsilon)`; values already inside are unchanged. This is Contraste's statement of the "small epsilon
  adjustment" that beta rungs need at the endpoints and to which Qi and Zhao (2011) find the results very sensitive (dossier 04 F.3); the
  C08 block `endpoint_sensitivity` reports the fit at several epsilons, and `ladder[].epsilon` records the one used.
- Golden: `endpoint_transform([0.0, 0.5, 1.0], 0.001) = [0.001, 0.5, 0.999]`.

### `riskvalidation.lgd_ead.lgd_models.LgdFit`

```python
@dataclass(frozen=True)
class LgdFit:
    kind: str                  # "ols", "fractional-logit", "beta", "hurdle", "tobit"
    names: tuple[str, ...]     # one per column of X
    coefficients: np.ndarray   # (K,) of the mean model (for a hurdle: the severity stage)
    extras: dict               # beta: "phi", "epsilon"; hurdle: "stage1_coefficients"; tobit: "sigma"
```

- Units: coefficients on the link scale of the kind (identity for ols and tobit, logit for the rest).
- Invariants: `kind` is one of the five strings (the document `ladder[].kind` adds `gradient-boosted` and `cure-decomposition`, which
  are not fits of this class); a fit stores everything `predict_lgd` needs and nothing else.

### `riskvalidation.lgd_ead.lgd_models.fit_ols`

```python
def fit_ols(X: np.ndarray, y: np.ndarray, names: tuple[str, ...] | None = None) -> LgdFit: ...
```

- Units: `y` (N,) in [0, 1] (the baseline of dossier 04 F.3, "OLS clipped to [0, 1]"; the clipping happens in `predict_lgd`).
- Invariants: least squares; a rank-deficient `X` raises `ValueError`.
- Golden: `X = [[1, 0], [1, 1]]`, `y = [0, 1]` gives `coefficients = [0, 1]` to 1e-12, and `predict_lgd` of `[[1, 2]]` is `1.0` (clipped).

### `riskvalidation.lgd_ead.lgd_models.fit_fractional_logit`

```python
def fit_fractional_logit(X: np.ndarray, y: np.ndarray, names: tuple[str, ...] | None = None) -> LgdFit: ...
```

- Units: `y` (N,) in the closed [0, 1] (otherwise `ValueError`); the Bernoulli quasi-maximum-likelihood estimator of Papke and Wooldridge
  (1996), `E[y | x] = 1 / (1 + exp(-x b))`, consistent for the endpoints (dossier 04 F.3).
- Invariants: the score equation `X' (y - mu) = 0` holds to 1e-8, so with an intercept `sum(mu) = sum(y)`; predictions lie in (0, 1).
- Golden (a saturated one-dummy model, whose estimate is the logit of each group mean): `X = [[1, 0], [1, 0], [1, 1], [1, 1]]`,
  `y = [0, 0.5, 0.5, 1.0]` gives `coefficients = [-1.098612, 2.197225]` (that is `[ln(1/3), 2 ln 3]`), and the fitted means are `[0.25, 0.75]`.

### `riskvalidation.lgd_ead.lgd_models.fit_beta`

```python
def fit_beta(X: np.ndarray, y: np.ndarray, epsilon: float,
             names: tuple[str, ...] | None = None) -> LgdFit: ...
```

- Units: `y` in [0, 1], transformed by `endpoint_transform(y, epsilon)` before the fit; logit mean link, log precision link (Ferrari and
  Cribari-Neto 2004); `extras["phi"]` is the precision at the mean of `X`, `extras["epsilon"]` the epsilon used.
- Invariants: predictions in (0, 1); `ValueError` for `epsilon` outside (0, 0.5); the fit is a function of `epsilon`, and the endpoint
  sensitivity (the same fit at several epsilons) is reported, never hidden (SDD section 4, "LGD rungs").
- Golden: none closed form exists for a beta fit; the invariants above are tests, and so is the sensitivity report: two fits of the same
  data at `epsilon = 0.01` and `0.0001` are both returned and may differ.

### `riskvalidation.lgd_ead.lgd_models.fit_hurdle`

```python
def fit_hurdle(X: np.ndarray, y: np.ndarray, X_severity: np.ndarray | None = None,
               names: tuple[str, ...] | None = None, *, min_positive: int = 5) -> LgdFit: ...
```

- Units: stage 1 is a logit of `y > 0` on `X`; stage 2 is a fractional logit of `y` on `X_severity` (default `X`) among the exposures with
  `y > 0`; `E[LGD] = Pr(loss > 0) * E[LGD | loss > 0]` (Leow and Mues 2012; Tong, Mues and Thomas 2013; dossier 04 F.3).
- Invariants: `coefficients` are the stage 2 ones and `extras["stage1_coefficients"]` the stage 1 ones; fewer than `min_positive` (default 5) positive-loss
  exposures raise `ValueError`; predictions in [0, 1].
- Golden: intercept-only `X = [[1], [1], [1], [1]]`, `y = [0, 0.4, 0.4, 0.4]`: stage 1 probability `0.75` (coefficient `ln 3 = 1.098612`),
  stage 2 mean `0.4` (coefficient `ln(0.4 / 0.6) = -0.405465`), prediction `0.75 * 0.4 = 0.3` to 1e-9. (The golden runs with `min_positive=3`.)

### `riskvalidation.lgd_ead.lgd_models.fit_tobit`

```python
def fit_tobit(X: np.ndarray, y: np.ndarray, names: tuple[str, ...] | None = None) -> LgdFit: ...
```

- Units: two-limit censored normal `y = min(1, max(0, y*))`, `y* = X b + e`, `e ~ N(0, sigma^2)` (Tobin 1958); `extras["sigma"]` positive.
- Invariants: with no `y` at 0 or 1 the likelihood is the normal one and `coefficients` equal the OLS ones to 1e-6; the prediction is the
  expectation of the censored variable, in [0, 1].
- Golden: `X = [[1, 0], [1, 1], [1, 2]]`, `y = [0.2, 0.3, 0.6]` (no censoring, a nonzero residual) gives `coefficients = [0.166667, 0.2]` to 1e-6 (the OLS fit) and
  `sigma = sqrt(RSS / 3) = 0.0471405` to 1e-6.

### `riskvalidation.lgd_ead.lgd_models.cure_decomposition`

```python
def cure_decomposition(p_cure: np.ndarray, lgd_cure: np.ndarray, lgd_liquidation: np.ndarray) -> np.ndarray: ...
```

- Units: all three in [0, 1] (otherwise `ValueError`); `LGD = p_cure * LGD_cure + (1 - p_cure) * LGD_liq`. The structure is the practitioner
  decomposition of dossier 04 F.3; its single academic source was not pinned there (attribution UNVERIFIED).
- Invariants: the result lies between `lgd_cure` and `lgd_liquidation`; `p_cure = 1` returns `lgd_cure`.
- Golden: `(0.3, 0.05, 0.6) = 0.015 + 0.42 = 0.435`.

### `riskvalidation.lgd_ead.lgd_models.predict_lgd`

```python
def predict_lgd(fit: LgdFit, X: np.ndarray) -> np.ndarray: ...
```

- Units: `X` (M, K) with the columns of the fit; the result (M,) LGD decimals in [0, 1].
- Invariants: for `ols` the linear prediction is clipped to [0, 1] (the only place a model clips); every other kind is in [0, 1] by
  construction; a prediction is therefore always `in-range`, and the document wrapper of a prediction carries `in-range`.
- Golden: see `fit_ols` (the clipped `1.0`) and `fit_fractional_logit` (the fitted means `[0.25, 0.75]`).

## Module `riskvalidation/lgd_ead/downturn.py`

Downturn LGD (dossier 04 F.4): the period is identified from a supplied macro path and the add-on is Contraste's cohort-based one. The
EBA/RTS/2018/04 and EBA/GL/2019/03 approaches are cross-references only: the wording of the three calibration approaches is not in the
dossier (UNVERIFIED), so this module claims no regulatory approach, and the C08 view labels the add-on an illustration.

### `riskvalidation.lgd_ead.downturn.identify_downturn`

```python
def identify_downturn(years: np.ndarray, indicator: np.ndarray, threshold: float,
                      higher_is_worse: bool = True) -> np.ndarray: ...
```

- Units: `years` (Y,) integers strictly increasing; `indicator` (Y,) a macro series (for example the unemployment rate in percent);
  `threshold` in the unit of the indicator; the result (Y,) bool.
- Invariants: with `higher_is_worse` a year is a downturn year when `indicator > threshold` (strictly; a tie is not a downturn), otherwise
  when `indicator < threshold`; a NaN raises `ValueError`; the caller records the indicator and its source in the document
  (`downturn.period.indicator`, `macro_source`).
- Golden (a constructed path, labelled so, not BLS data): `years = [2006, ..., 2011]`, `indicator = [4.6, 4.6, 5.8, 9.3, 9.6, 8.9]`,
  `threshold = 7.0` gives `[False, False, False, True, True, True]`.

### `riskvalidation.lgd_ead.downturn.DownturnResult`

```python
@dataclass(frozen=True)
class DownturnResult:
    long_run: float     # default-weighted mean LGD over all cohorts
    downturn: float     # default-weighted mean LGD over the downturn cohorts
    add_on: float       # downturn - long_run
```

- Units: LGD decimals; the add-on may be negative if the downturn cohorts lost less than average (reported as is).
- Invariants: `add_on = downturn - long_run` exactly; the C08 `downturn.rows[].add_on` equals `downturn_lgd.value - long_run_lgd.value`.

### `riskvalidation.lgd_ead.downturn.downturn_add_on`

```python
def downturn_add_on(cohort_lgd: np.ndarray, cohort_weights: np.ndarray, downturn_mask: np.ndarray) -> DownturnResult: ...
```

- Units: `cohort_lgd` (C,) decimals, `cohort_weights` (C,) positive (the number of defaults), `downturn_mask` (C,) bool.
- Invariants: weighted means; `ValueError` when the mask has no true entry; the result does not depend on the order of the cohorts.
- Golden: `cohort_lgd = [0.30, 0.60, 0.40]`, `cohort_weights = [100, 50, 50]`, `mask = [False, True, False]`: `long_run = 0.40`,
  `downturn = 0.60`, `add_on = 0.20` to 1e-12.

### `riskvalidation.lgd_ead.downturn.coverage_shortfall`

```python
def coverage_shortfall(estimate: float, realised: float) -> tuple[bool, float]: ...
```

- Units: LGD decimals; returns `(covered, shortfall)` with `covered = estimate >= realised - 1e-12` and `shortfall = max(0, realised - estimate)`.
- Invariants: the C08 `downturn.rows[].covered` and `shortfall` are this pair, and `coverage.share_covered` is the share of rows covered.
- Golden: `(0.55, 0.60) = (False, 0.05)`; `(0.70, 0.68) = (True, 0.0)`.

## Module `riskvalidation/lgd_ead/ccf.py`

CCF and EAD (dossier 04 G.1 to G.3). `CCF = (EAD - E(t_r)) / (L(t_r) - E(t_r))`, `EAD = E(t_r) + CCF * (L(t_r) - E(t_r))`, with
`t_r` the reference date before default `t_d`, `E` the drawn amount and `L` the limit. The three reference-date designs are Moral (2006) as
summarised in dossier 04 G.1 (the chapter was not read; detail UNVERIFIED). Every page that shows a CCF names the convention
(`convention.name = "eu-undrawn"`); in Qi (2009) terms the ratio is the LEQ, "CCF" is EAD over outstanding and "EADF" is EAD over the limit.

### `riskvalidation.lgd_ead.ccf.reference_indices`

```python
def reference_indices(design: str, default_index: int, cohort_start_index: int | None = None,
                      horizon: int = 12, n_reference: int = 4, step: int = 3) -> np.ndarray: ...
```

- Units: `design` in `{"fixed-horizon", "cohort", "variable-horizon"}`; indices are months on the facility path (`default_index` is `t_d`); the
  result (R,) int64.
- Invariants: fixed horizon gives `[t_d - horizon]`; cohort gives `[cohort_start_index]` (required, `ValueError` otherwise; the start of the
  calendar cohort that contains `t_d`); variable horizon gives `t_d - horizon + k * step` for `k = 0 .. n_reference - 1`; a negative index
  raises `ValueError` (the reference date precedes the first observation).
- Golden: `default_index = 21`: fixed horizon `[9]`; cohort with `cohort_start_index = 12` `[12]`; variable horizon `[9, 12, 15, 18]`.

### `riskvalidation.lgd_ead.ccf.ccf_observations`

```python
def ccf_observations(drawn: np.ndarray, limit: np.ndarray, ead: float,
                     reference_index: np.ndarray) -> tuple[np.ndarray, np.ndarray]: ...
```

- Units: `drawn` (T,) and `limit` (T,) money by month, `ead` money at default, `reference_index` (R,) months; returns `(ccf, undrawn)`, both (R,),
  `undrawn = limit[ref] - drawn[ref]`.
- Invariants: `ccf = (ead - drawn[ref]) / undrawn` where `undrawn > 0`; where `undrawn <= 0` (a fully drawn or overdrawn line, dossier 04 G.2)
  the CCF is undefined and returned as NaN, never as 0 or 1; the values below 0 and above 1 are returned as they come.
- Golden: a facility with `limit = 1000` and `ead = 900` and `drawn[9, 12, 15, 18] = [420, 500, 560, 640]` (other months arbitrary) with
  `reference_index = [9, 12, 15, 18]` gives `undrawn = [580, 500, 440, 360]` and `ccf = [0.827586, 0.8, 0.772727, 0.722222]`: the fixed-horizon design
  (`t_d = 21`, `t_r = 9`) reads `0.827586`, the cohort design (`t_r = 12`) `0.8`.

### `riskvalidation.lgd_ead.ccf.aggregate_ccf`

```python
def aggregate_ccf(ccf: np.ndarray, undrawn: np.ndarray, aggregator: str) -> float: ...
```

- Units: `ccf` and `undrawn` as returned by `ccf_observations` (NaN entries are excluded and counted nowhere else), `aggregator` in
  `{"mean", "pooled"}`; the result a CCF decimal, not clipped.
- Invariants: `mean` is the unweighted mean of the finite CCFs; `pooled` is the ratio of sums `sum(ccf * undrawn) / sum(undrawn)`, which equals
  `sum(EAD - E) / sum(L - E)`; all-NaN input raises `ValueError`. The document `ccf_by_design.rows[].estimator` names the aggregator.
- Golden: the four observations above give `mean = 0.780634` and `pooled = 1480 / 1880 = 0.787234`.

### `riskvalidation.lgd_ead.ccf.TreatedCcf`

```python
@dataclass(frozen=True)
class TreatedCcf:
    values: np.ndarray    # (M,) the CCFs that remain after the treatment
    n_dropped: int        # observations removed (censor) or NaN removed
    n_below_zero: int     # counted before the treatment
    n_above_one: int      # counted before the treatment
```

- Units: counts and CCF decimals. The counts feed `share_below_zero` and `share_above_one` of the document row.
- Invariants: `n_below_zero` and `n_above_one` are counted on the input whatever the treatment, so a treatment never hides how many
  observations lay outside [0, 1].

### `riskvalidation.lgd_ead.ccf.treat_ccf`

```python
def treat_ccf(ccf: np.ndarray, treatment: str) -> TreatedCcf: ...
```

- Units: `treatment` in `{"none", "censor", "floor-cap", "bounded-scale"}` (dossier 04 G.2); NaN entries are dropped first and counted.
- Invariants: `none` keeps every value (to be flagged by `range_flag`); `censor` drops the observations outside [0, 1]; `floor-cap` clips to
  [0, 1] (floor at 0, cap at 1; it biases EAD, dossier 04 G.2); `bounded-scale` returns the values clipped to [0, 1] as the input of
  `fit_fractional_logit`, and the estimate is then the model's predicted mean, not a clip-and-average.
- Golden: `ccf = [-0.1, 0.0, 0.2, 0.6, 1.3]`: `none` mean `0.4`; `censor` values `[0.0, 0.2, 0.6]` (mean `0.266667`, `n_dropped = 2`); `floor-cap` values
  `[0.0, 0.0, 0.2, 0.6, 1.0]` (mean `0.36`); in each, `n_below_zero = 1` and `n_above_one = 1`.

### `riskvalidation.lgd_ead.ccf.ead_from_ccf`

```python
def ead_from_ccf(drawn: np.ndarray, limit: np.ndarray, ccf: np.ndarray) -> np.ndarray: ...
```

- Units: money (A,), CCF decimals (A,); the result (A,) money, **not clipped** (a CCF outside [0, 1] can give an EAD below the drawn amount or above the limit).
- Invariants: `EAD = drawn + ccf * (limit - drawn)`; the round trip with `ccf_observations` returns the EAD.
- Golden: `(600, 1000, 0.75) = 900.0`.

### `riskvalidation.lgd_ead.ccf.to_us_terms`

```python
def to_us_terms(drawn: np.ndarray, limit: np.ndarray, ead: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]: ...
```

- Units: money (A,); returns `(leq, ccf_us, eadf)`: `leq = (ead - drawn) / (limit - drawn)` (the EU CCF), `ccf_us = ead / drawn` (Qi 2009: EAD as a share of
  the outstanding amount) and `eadf = ead / limit` (EAD as a share of the credit line).
- Invariants: undefined entries (`limit == drawn`, `drawn == 0`) are NaN; the function exists so a page can show both conventions and never mix them.
- Golden: `(600, 1000, 900) = (0.75, 1.5, 0.9)`.

### `riskvalidation.lgd_ead.ccf.small_undrawn_rule`

```python
def small_undrawn_rule(drawn: np.ndarray, limit: np.ndarray, ead: np.ndarray,
                       threshold: float) -> tuple[np.ndarray, np.ndarray]: ...
```

- Units: money (A,); `threshold` money in the same currency (Qi 2009 switches below USD 50); returns `(switched, ratio)` with `switched` (A,) bool for
  `limit - drawn < threshold` and `ratio` (A,) equal to the EADF `ead / limit` where switched and to the EU CCF elsewhere.
- Invariants: the threshold is a parameter, never a hard-coded constant; the document block `small_undrawn` records it with its currency and the number switched.
- Golden: `threshold = 50`; `(drawn, limit, ead) = (980, 1000, 990)` is switched with ratio `0.99`; `(600, 1000, 900)` is not, with ratio `0.75`.

### `riskvalidation.lgd_ead.ccf.EadFit`

```python
@dataclass(frozen=True)
class EadFit:
    kind: str                  # "direct-ead" or "utilisation-change"
    names: tuple[str, ...]
    coefficients: np.ndarray   # (K,)
    extras: dict               # direct-ead: "n_clipped_below", "n_clipped_above"
```

- Units: coefficients on the logit scale (`direct-ead`) or the identity scale of the utilisation change (`utilisation-change`).
- Invariants: everything `predict_ead` needs and nothing else.

### `riskvalidation.lgd_ead.ccf.fit_direct_ead`

```python
def fit_direct_ead(X: np.ndarray, ead: np.ndarray, limit: np.ndarray,
                   names: tuple[str, ...] | None = None) -> EadFit: ...
```

- Units: money (N,) for `ead` and `limit` (strictly positive); the target is the EADF `ead / limit`, fitted with a fractional logit (an intercept column in `X`).
  Dossier 04 G.3 describes direct EAD models (a zero-adjusted gamma mixture, Tong et al. 2016); that mixture is **not** in 1.0.0 of this contract and
  would be a minor version.
- Invariants: an EADF outside [0, 1] (an overlimit EAD) is clipped to [0, 1] for the fit and counted in `extras["n_clipped_below"]` and `["n_clipped_above"]`,
  never silently; the clipped count is reported in the document.
- Golden: `X = [[1, 0], [1, 0], [1, 1], [1, 1]]`, `ead = [0, 500, 500, 1000]`, `limit = [1000, 1000, 1000, 1000]` gives `coefficients = [-1.098612, 2.197225]`
  (the `fit_fractional_logit` golden, since the EADF is `[0, 0.5, 0.5, 1.0]`).

### `riskvalidation.lgd_ead.ccf.fit_utilisation_change`

```python
def fit_utilisation_change(X: np.ndarray, drawn_ref: np.ndarray, drawn_default: np.ndarray,
                           limit_ref: np.ndarray, names: tuple[str, ...] | None = None) -> EadFit: ...
```

- Units: money (N,); the target is the change of utilisation `(E(t_d) - E(t_r)) / L(t_r)`, fitted by least squares (a ratio-free model, dossier 04 G.3).
- Invariants: no ratio with the undrawn amount in the denominator, so no instability for small undrawn amounts; `limit_ref` strictly positive.
- Golden: `X = [[1], [1], [1]]`, `drawn_ref = [400, 500, 600]`, `drawn_default = [700, 800, 900]`, `limit_ref = [1000, 1000, 1000]` gives `coefficients = [0.3]`.

### `riskvalidation.lgd_ead.ccf.predict_ead`

```python
def predict_ead(fit: EadFit, X: np.ndarray, drawn_ref: np.ndarray, limit_ref: np.ndarray) -> np.ndarray: ...
```

- Units: money (M,); the result (M,) money. `direct-ead`: `limit_ref * EADF_hat`; `utilisation-change`: `drawn_ref + limit_ref * delta_hat`.
- Invariants: the `direct-ead` prediction lies in [0, limit_ref]; the `utilisation-change` prediction is not clipped (flag it in the document).
- Golden: the `fit_direct_ead` golden fit with `X = [[1, 1]]`, `limit_ref = [1000]` gives `750.0` (the fitted EADF of that group is 0.75); the
  `fit_utilisation_change` golden fit with `X = [[1]]`, `drawn_ref = [600]`, `limit_ref = [1000]` gives `900.0`.

### `riskvalidation.lgd_ead.ccf.ccf_bias`

```python
def ccf_bias(estimate: float, truth: float) -> float: ...
```

- Units: CCF decimals; the result `estimate - truth`, signed, not clipped.
- Invariants: on the C09 generator the truth is known; the document row stores `bias = estimate.value - truth.value`, and `within_tolerance = abs(bias) <= tolerance`.
- Golden: `ccf_bias(0.83, 0.60) = 0.23` to 1e-12.

## Module `riskvalidation/lgd_ead/floors.py`

The IRB floors and supervisory CCFs of dossier 01 section A.5 (Basel III final in force 2023-01-01; Basel II is not implemented here). Every cell is
transcribed from the dossier; the paragraph text itself was not re-read for this contract.

### `riskvalidation.lgd_ead.floors.lgd_floor`

```python
def lgd_floor(portfolio: str, collateral: str) -> float: ...
```

- Units: `portfolio` in `{"corporate", "retail"}`, `collateral` in `{"unsecured", "financial", "receivables", "real-estate", "other-physical", "qrre", "mortgage"}`;
  the result an LGD decimal. A combination without a cell (a corporate `qrre`) raises `ValueError`. Sovereign exposures are exempt (CRE32.16) and are not
  passed to this function.
- Invariants: the table below, exactly; the floor of a partly secured exposure is not a cell of dossier 01 (the blending formula is not transcribed, UNVERIFIED), so
  the caller applies the floor per secured and unsecured part and combines them.
- Golden (every cell):

| portfolio | collateral | floor | reference |
|---|---|---|---|
| corporate | unsecured | 0.25 | CRE32.16 |
| corporate | financial | 0.00 | CRE32.16 |
| corporate | receivables | 0.10 | CRE32.16 |
| corporate | real-estate | 0.10 | CRE32.16 |
| corporate | other-physical | 0.15 | CRE32.16 |
| retail | mortgage | 0.05 | CRE32.58 |
| retail | qrre | 0.50 | CRE32.58 |
| retail | unsecured | 0.30 | CRE32.58 |
| retail | financial | 0.00 | CRE32.59 |
| retail | receivables | 0.10 | CRE32.59 |
| retail | real-estate | 0.10 | CRE32.59 |
| retail | other-physical | 0.15 | CRE32.59 |

  The retail secured floors are listed in the dossier as "0% / 10% / 10% / 15% by collateral" without naming the order; the order financial, receivables, real
  estate, other physical is read from the corporate row and is **UNVERIFIED** against CRE32.59. The same cells are the C08 models `floors.cells`.

### `riskvalidation.lgd_ead.floors.FloorBite`

```python
@dataclass(frozen=True)
class FloorBite:
    applied: np.ndarray      # (A,) the estimates after the floor
    binding: np.ndarray      # (A,) bool, the floor raised the estimate
    share_binding: float
    mean_before: float
    mean_after: float
    uplift: float            # mean_after - mean_before, never negative
```

- Units: LGD decimals for an LGD floor, money for an EAD floor.
- Invariants: `applied >= input` elementwise; `uplift >= 0`; `binding` is true exactly where `applied > input`; the C08 `floors_bite.rows` and the C09 `ead_floor.rows`
  serialise it (`share_binding`, `mean_before`, `mean_after`, `uplift`).

### `riskvalidation.lgd_ead.floors.apply_lgd_floor`

```python
def apply_lgd_floor(lgd: np.ndarray, floor: float) -> FloorBite: ...
```

- Units: `lgd` (A,) decimals, `floor` in [0, 1].
- Invariants: `applied = max(lgd, floor)`; a floor of 0 binds nowhere.
- Golden: `lgd = [0.20, 0.30, 0.60]`, `floor = 0.25` gives `applied = [0.25, 0.30, 0.60]`, `binding = [True, False, False]`, `share_binding = 1/3`, `mean_before = 0.366667`,
  `mean_after = 0.383333`, `uplift = 0.016667`.

### `riskvalidation.lgd_ead.floors.supervisory_ccf`

```python
def supervisory_ccf(item: str) -> float: ...
```

- Units: `item` in `{"direct-credit-substitutes", "nifs-rufs-transaction-related-contingents", "commitments",
  "short-term-self-liquidating-trade-letters-of-credit", "unconditionally-cancellable"}`; the result a CCF decimal. The F-IRB CCFs equal the standardised ones (CRE32.33),
  CRE20.94 to CRE20.101.
- Invariants: the table below, exactly (dossier 01 sections A.5 and B.2); an unknown item raises `ValueError`.
- Golden: `direct-credit-substitutes = 1.0`, `nifs-rufs-transaction-related-contingents = 0.5`, `commitments = 0.4` (CRE20.98), `short-term-self-liquidating-trade-letters-of-credit = 0.2`,
  `unconditionally-cancellable = 0.1` (CRE20.100). Basel II's 75% for commitments (old CRE32.33) is not implemented.

### `riskvalidation.lgd_ead.floors.ead_floor`

```python
def ead_floor(drawn: np.ndarray, limit: np.ndarray, sa_ccf: np.ndarray, off_balance_share: float = 0.5) -> np.ndarray: ...
```

- Units: money (A,); `sa_ccf` (A,) the standardised CCF of the facility; the result (A,) money. Dossier 01 A.5 states the floor as "on-balance amount + 50% of off-balance exposure
  using the SA CCF" (CRE32.36 corporate, CRE32.64 retail; sovereigns exempt): `floor = drawn + off_balance_share * sa_ccf * (limit - drawn)`. The reading that the 50% applies
  to the SA-CCF-weighted off-balance exposure follows the dossier's wording and is **UNVERIFIED** against the paragraph text.
- Invariants: `drawn <= floor <= limit` for `sa_ccf` in [0, 1]; nondecreasing in `sa_ccf` and `limit`.
- Golden: `(600, 1000, 0.40) = 600 + 0.5 * 0.4 * 400 = 680.0`.

### `riskvalidation.lgd_ead.floors.apply_ead_floor`

```python
def apply_ead_floor(ead: np.ndarray, floor: np.ndarray) -> FloorBite: ...
```

- Units: money (A,).
- Invariants: `applied = max(ead, floor)` elementwise; a `FloorBite` as above.
- Golden: `ead = [650, 700]`, `floor = [680, 680]` gives `applied = [680, 700]`, `share_binding = 0.5`, `mean_before = 675`, `mean_after = 690`, `uplift = 15`.

## Module `riskvalidation/validation/lgd_ead.py`

The LGD and EAD validation tests, each a `TestResult` row of `common/test-result` (`test_id` as named, `h0`, `alternative`, `policy_version`, `reference` always set; `light` in
green, amber, red, not_evaluated, error). The acceptance gates are Contraste internal gates, stated as such, not regulatory thresholds; each function states its light rule on a
`- Light:` line with its parameters named so that a view can explain a light, and the parameters travel in `policy_version`, `alpha_amber` and `alpha_red`. A test with no data
returns `not_evaluated` with its reason in `notes`. LGD calibration is judged by mean realised against mean predicted by segment and over time, not by R2 alone (dossier 04 F.3, Takeaway).

### `riskvalidation.validation.lgd_ead.lgd_calibration_by_segment`

```python
def lgd_calibration_by_segment(realised: np.ndarray, predicted: np.ndarray, segment: str | None = None,
                               model_id: str | None = None, alpha_amber: float = 0.05,
                               alpha_red: float = 0.01) -> TestResult: ...
```

- Units: `realised` and `predicted` (N,) LGD decimals of one segment (realised values outside [0, 1] are kept); `test_id = "lgd_ead.lgd_calibration_by_segment"`.
  `h0`: the mean realised LGD equals the mean predicted LGD in the segment.
- Invariants: with `d = realised - predicted`, `statistic = mean(d) / (sd(d) / sqrt(N))` (paired t, `N - 1` degrees of freedom, `sd` with `ddof = 1`), `p_value` two-sided, `metric = mean(d)`;
  `extras` carries `mean_realised`, `mean_predicted`, `ci_low`, `ci_high` (95% interval of the mean gap), `n_below_zero` and `n_above_one` of the realised values; `N < 2` or `sd(d) = 0`
  gives `not_evaluated`.
- Light: green when `p_value >= alpha_amber` (0.05), amber when `alpha_red <= p_value < alpha_amber` (0.01), red below `alpha_red`.
- Golden: `realised = [0.4, 0.5, 0.6]`, `predicted = [0.3, 0.3, 0.3]` gives `statistic = 3.464102`, `p_value = 0.074180` (two-sided, two degrees of freedom: `1 - t / sqrt(t^2 + 2)`), `metric = 0.2`,
  `light = "green"`.

### `riskvalidation.validation.lgd_ead.lgd_calibration_over_time`

```python
def lgd_calibration_over_time(realised: np.ndarray, predicted: np.ndarray, period: np.ndarray,
                              model_id: str | None = None, alpha_amber: float = 0.05,
                              alpha_red: float = 0.01) -> TestResult: ...
```

- Units: `realised`, `predicted` (N,) decimals and `period` (N,) integers (a default year or a cohort index); `test_id = "lgd_ead.lgd_calibration_over_time"`. `h0`: in every period the mean
  realised LGD equals the mean predicted LGD.
- Invariants: the paired t of the segment test per period with at least 2 observations and nonzero spread; `statistic` is the largest `|t|` over those periods; `p_value` is the Bonferroni-adjusted
  `min(1, K * p_min)` with `K` the number of periods tested; `metric` is the largest `|mean(d)|` over the periods; `extras["periods"]` lists `period`, `n`, `mean_gap`, `t`, `p` of each; no period
  evaluable gives `not_evaluated`.
- Light: as `lgd_calibration_by_segment`, on the adjusted `p_value`.
- Golden: period A with `d = [0.1, 0.2, 0.3]` (`t = 3.464102`, `p = 0.074180`) and period B with `d = [-0.1, 0.0, 0.1]` (`t = 0`, `p = 1.0`) give `statistic = 3.464102`, `p_value = 0.148360`
  (`2 * 0.074180`), `metric = 0.2`, `light = "green"`.

### `riskvalidation.validation.lgd_ead.lgd_discrimination`

```python
def lgd_discrimination(realised: np.ndarray, predicted: np.ndarray, segment: str | None = None,
                       model_id: str | None = None, rho_green: float = 0.30,
                       rho_amber: float = 0.10) -> TestResult: ...
```

- Units: (N,) decimals; `test_id = "lgd_ead.lgd_discrimination"`. `h0`: predicted and realised LGD are rank-independent. The statistic is the Spearman rank correlation (ties by average rank); it is
  the rank-statistic family the engine's discrimination tests already use, and U6-E reuses an existing implementation if one exists (the numbers are the same).
- Invariants: `statistic = metric = rho` in [-1, 1]; `p_value` is the two-sided p of the rank correlation; `N < 3` or a constant input gives `not_evaluated`.
- Light: green when `rho >= rho_green` (0.30), amber when `rho_amber <= rho < rho_green` (0.10), red below. LGD rank power is modest in the literature (R2 between 4% and 43% in Loterman et al. 2012,
  dossier 04 F.3), so the gate is low and is a Contraste gate, not a regulatory one.
- Golden: `realised = [0.1, 0.4, 0.6, 0.9]`, `predicted = [0.2, 0.3, 0.7, 0.8]` gives `statistic = 1.0`, `light = "green"`; with `predicted = [0.8, 0.7, 0.3, 0.2]`, `statistic = -1.0`, `light = "red"`.

### `riskvalidation.validation.lgd_ead.downturn_coverage`

```python
def downturn_coverage(estimate: float, realised_downturn: np.ndarray, segment: str | None = None,
                      model_id: str | None = None, alpha_amber: float = 0.05,
                      alpha_red: float = 0.01) -> TestResult: ...
```

- Units: `estimate` the downturn LGD decimal, `realised_downturn` (N,) realised LGD decimals of the defaults in the downturn period; `test_id = "lgd_ead.downturn_coverage"`. `h0`: the mean realised
  downturn LGD does not exceed the estimate; `alternative`: it does (the estimate does not cover the downturn losses).
- Invariants: `statistic = (mean(realised) - estimate) / (sd / sqrt(N))`, one-sided upper `p_value` with `N - 1` degrees of freedom, `metric = max(0, mean(realised) - estimate)` (the shortfall, the
  same number as `coverage_shortfall`); `N < 2` or zero spread gives `not_evaluated`.
- Light: green when `p_value >= alpha_amber` (0.05), amber when `alpha_red <= p_value < alpha_amber`, red below `alpha_red`.
- Golden: `estimate = 0.55`, `realised_downturn = [0.5, 0.6, 0.7]` gives `statistic = 0.866025`, `p_value = 0.238884` (one-sided, two degrees of freedom: `0.5 - t / (2 sqrt(t^2 + 2))`), `metric = 0.05`,
  `light = "green"`.

### `riskvalidation.validation.lgd_ead.ead_backtest_by_band`

```python
def ead_backtest_by_band(predicted_ead: np.ndarray, realised_ead: np.ndarray, utilisation: np.ndarray,
                         band_edges: np.ndarray, model_id: str | None = None, gap_amber: float = 0.10,
                         gap_red: float = 0.25) -> TestResult: ...
```

- Units: money (N,) for predicted and realised EAD in the same currency (the currency travels in the document, `ead_backtest.currency`), `utilisation` (N,) the drawn share of the limit at the reference
  date, `band_edges` (B + 1,) strictly increasing; bands are `[edge_i, edge_{i+1})`, the last closed; a utilisation outside the edges raises `ValueError`. `test_id = "lgd_ead.ead_backtest_by_band"`. `h0`: predicted EAD equals realised EAD in every utilisation band (back-tested in currency, not only as a CCF; dossier 04 G.3).
- Invariants: per band `gap = sum(predicted) - sum(realised)` and `relative_gap = gap / sum(realised)`; `statistic` is the relative gap of the total; `metric = max_band |relative_gap|`;
  `extras["bands"]` lists `lower`, `upper`, `n`, `predicted_ead`, `realised_ead`, `gap`, `relative_gap`; a band with no observation is listed with null values and does not enter the metric;
  `p_value` is null.
- Light: green when `metric <= gap_amber` (0.10), amber when `metric <= gap_red` (0.25), red above.
- Golden: `predicted_ead = [900, 500]`, `realised_ead = [800, 600]`, `utilisation = [0.2, 0.8]`, `band_edges = [0, 0.5, 1.0]`: band 1 `relative_gap = 0.125`, band 2 `relative_gap = -0.166667`,
  `statistic = 0.0`, `metric = 0.166667`, `light = "amber"`.

### `riskvalidation.validation.lgd_ead.ccf_estimator_bias`

```python
def ccf_estimator_bias(estimates: np.ndarray, truth: float, tolerance: float, model_id: str | None = None,
                       alpha_amber: float = 0.05, alpha_red: float = 0.01) -> TestResult: ...
```

- Units: `estimates` (R,) CCF decimals, one per independent test replication of the C09 generator (not clipped), `truth` the generator's known CCF, `tolerance` a CCF decimal (the document
  `ccf_by_design.tolerance`); `test_id = "lgd_ead.ccf_estimator_bias"`. `h0`: the estimator is unbiased (the mean estimate equals the known CCF).
- Invariants: with `e = estimates - truth`, `metric = mean(e)` (the bias, equal to `ccf_bias(mean(estimates), truth)`), `statistic = mean(e) / (sd(e) / sqrt(R))`, `p_value` two-sided with `R - 1`
  degrees of freedom; `extras` carries `rmse`, `ci_low`, `ci_high` and `within_tolerance`; `R < 2` or zero spread gives `not_evaluated`.
- Light: green when `abs(metric) <= tolerance`, amber when `abs(metric) <= 2 * tolerance`, red above; the p-value is informative (a statistically significant bias inside the tolerance stays green, and
  the view shows both).
- Golden: `estimates = [0.61, 0.63, 0.65]`, `truth = 0.60`, `tolerance = 0.05` gives `metric = 0.03`, `statistic = 2.598076`, `p_value = 0.121690` (two-sided, two degrees of freedom), `light = "green"`.

## Golden values summary

| Value | Where | Source |
|---|---|---|
| workout LGD 0.479339 for EAD 100, recoveries 40 and 30 at 1 and 2 years, one cost of 10 at 1 year, 10% rate; 1.136364 and -0.090909 outside [0, 1] | `workout_lgd` | dossier 04 F.1, hand-computed |
| discount rate 0.0825 = 0.0325 + 0.05 | `eba_discount_rate` | dossier 04 F.1 (EBA/GL/2017/16 paragraph UNVERIFIED) |
| fractional logit `[-1.098612, 2.197225]` on a saturated dummy model (the logit of each group mean) | `fit_fractional_logit`, `fit_direct_ead` | dossier 04 F.3, closed form |
| cure decomposition 0.435; downturn add-on 0.20 | `cure_decomposition`, `downturn_add_on` | dossier 04 F.3 and F.4, hand-computed |
| CCF 0.827586 (fixed horizon), 0.8 (cohort), mean 0.780634 and pooled 0.787234 (variable horizon) for the constructed facility | `ccf_observations`, `aggregate_ccf` | dossier 04 G.1, hand-computed |
| treated mean 0.266667 (censor) and 0.36 (floor-cap) against 0.4 (none) | `treat_ccf` | dossier 04 G.2, hand-computed |
| LGD floors 0.25, 0.00, 0.10, 0.10, 0.15 (corporate) and 0.05, 0.50, 0.30, 0.00, 0.10, 0.10, 0.15 (retail); EAD floor 680 | `lgd_floor`, `ead_floor` | dossier 01 A.5 (CRE32.16, CRE32.58 to CRE32.59, CRE32.36, CRE32.64) |
| SA CCFs 1.0, 0.5, 0.4, 0.2, 0.1 | `supervisory_ccf` | dossier 01 A.5 and B.2 (CRE32.33, CRE20.94 to CRE20.101) |
| t = 3.464102 with p = 0.074180 at two degrees of freedom | `lgd_calibration_by_segment` | closed form, hand-computed |

Open items carried from the dossiers, never silently decided: the EBA/GL/2017/16 paragraph for the discount rate and the EBA/GL/2019/03 downturn approaches (UNVERIFIED in dossier 04); the
Moral (2006) reference-date designs (summary only); the retail secured floor order and the EAD floor reading (above); the blending formula for partly secured exposures; the zero-adjusted gamma
direct EAD model (not in 1.0.0); whether the EBA's CCF guidelines consulted in 2025 are final (UNVERIFIED in dossier 04 G.2, not implemented).
