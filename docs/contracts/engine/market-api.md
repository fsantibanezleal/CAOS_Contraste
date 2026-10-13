# Engine market API contract: `engine-market-api` 1.0.0

Owner: U8-S (unit sizing `plans/contraste/units/U8-sizing.md`, CAOS_MANAGE). Implemented by U8-E in `riskvalidation.market` and
`riskvalidation.validation.market` (repository CAOS_RiskValidation); called by the C11 and C13 bakes (U8-P1, U8-P2). The tests of
every function are written by U8-E against this file: a function exists with exactly the signature below, and each golden value or
invariant is a test. Changing a signature, a unit or a golden value is a breaking change (a new major version of this contract).
Sources: dossier 05 (`wip/contraste/05-market-ccr-alm-liquidity-oprisk-stress-sota-2026-10-04.md`, sections A.0 to A.2 for the estimators
and B.1 to B.6 for the back-tests and the comparison, and "Implications for Contraste" for the ladder, the champion rule and the
leakage-safe windows), dossier 01 (`wip/contraste/01-basel-pillar1-pillar2-framework-2026-10-04.md`, section D.4 for MAR32.9 Table 1,
the desk limits of MAR32.18 to MAR32.19 and the PLA test of MAR32.36 to MAR32.42) and dossier 08 (`wip/contraste/08-data-and-scenario-sources-2026-10-04.md`,
C.2, C.5 and C.8 for the public series); the product SDD section 5 gives the cases C11 and C13 and their variants.

The engine computes; it states no compliance claim. Nothing here is a Basel requirement beyond what the dossier lines cite; policy
parameters (alphas of a light, thresholds, replication counts) are supplied by the caller or stated by the function. Every constant and
golden value below is transcribed from, or recomputed from a formula of, the dossier line named on it; an item the dossier marks
UNVERIFIED, or that the dossier does not give, is marked UNVERIFIED here and is not silently decided. Three kinds of mark are used:
**UNVERIFIED** (the dossier says so, or does not give the detail: U8-E reads the primary source before transcription), **D-n** (a
contract decision this unit takes where the dossier leaves a choice open, with its reason; the integrator may amend it before U8-E
starts) and **Golden** (a number recomputed by `tests/contracts_u8/market_math.py` from the formula the line names).

## Conventions (all functions)

- Arrays are `numpy.ndarray` of `float64` (integers `int64`, flags `bool`, dates `datetime64[D]`). Shapes: `T` observations (days), `M`
  models, `K` the size of a window.
- **Return convention in the engine, positive loss numbers in the documents** (dossier 05 A.0). A return `y` is a decimal of the
  portfolio value; at a tail level `alpha` (0.01 or 0.025) the engine stores `VaR = v = F^-1(alpha)` and `ES = e = (1/alpha) integral
  of F^-1(u) du over (0, alpha)`, both negative in practice, with `e <= v`. The case documents store positive loss numbers
  (`loss = -y`, `VaR_loss = -v`, `ES_loss = -e`) and carry a required `sign_convention` field (`engine_convention =
  "return-negative"`, `document_convention = "positive-loss"`, a bilingual definition); the conversion is made once, at the reporting
  layer, with `conventions.to_loss_numbers`. Functions named `*_loss` or taking `loss` arguments are the exceptions and say so.
- **Exceedance**: day `t` is an exceedance when `loss_t > VaR_loss_t`, equivalently `y_t < v_t` (dossier 05 B: `I_t = 1{loss_t > VaR_t}`).
  The FZ0 indicator is `1{y <= v}` (A.1); the two differ only at equality, which the documents treat as no exceedance.
- **Leakage**: every forecast function receives only data dated before the forecast day and returns the forecast for the next day (the
  rolling scheme of dossier 05 "Candidate cases and leakage-safe evaluation windows"); no function receives the realised value of the
  day it forecasts. The case documents record, per forecast day, the end of its estimation window, which is strictly before the day
  (a producer check, since a date comparison is not a JSON Schema rule); the hyperparameters (window length, lambda, EVT threshold
  fraction, the CAViaR and GAS starts and the seed) are fixed once, for every window, on 1995-01-01 to 2003-12-31 (decision D1 of the U8
  sizing: the span ends before the earliest test window, calm 2004-06, and a span reaching into the 2004 to 2006 calm window would tune on it); the six
  windows have the dates of decision D2 (calm 2004-01-02 to 2006-12-29; equity 2007-09 2007-07-02 to 2009-06-30; FX 2008 2008-07-01 to
  2009-06-30; equity 2020 2020-02-03 to 2020-06-30; rates 2022 2022-01-03 to 2022-12-30; mixed 2023 2023-03-01 to 2023-05-31), which the
  schemas bind to the window ids. No lead-in: a window with fewer than 250 forecast days carries the Basel traffic light as
  `not_evaluated` with its reason (decision D3; MAR32.9 is defined on 250 observations) and every other back-test runs on the days it has.
- **Missing days**: a day missing from a public series (a holiday, a gap) is skipped in the rolling window and counted in the document
  (`data_status.missing_days`), never filled; a function never receives a NaN return (`ValueError`); the caller removes the day.
- Every function is pure and deterministic (no hidden state, no I/O, inputs never mutated); a function that simulates or bootstraps takes
  a `seed: int` and gives the same result for the same seed. A fit is deterministic for the same inputs (the optimiser, its starts and
  its tolerance are fixed by the implementation and reported in the fit).
- Dataclasses are frozen. A function that cannot compute a value because data is missing raises `ValueError` with the reason, or (a
  validation function) returns the `not_evaluated` light with its reason in `notes` and `statistic`, `p_value` and `metric` all null; it
  never returns a placeholder number. Two cases the dossier names: a duration test with no completed spell, and the ES of a conditional
  EVT with a fitted shape `xi` at or above 1 (the formula of A.2 row 10 is valid for `xi < 1`).
- A validation function returns one `TestResult` of `riskvalidation`, serialised by `TestResult.to_dict()` into a row that validates against
  `common/test-result` (the schema `docs/contracts/schemas/common/test-result.schema.json`): `test_id`, `model_id`, `segment`, `statistic`,
  `p_value`, `metric`, `h0`, `alternative`, `policy_version`, `alpha_amber`, `alpha_red`, `light`, `n`, `n_events`, `inputs_hash`,
  `reference`, `notes`, `extras`. The `test_id` is `market.<function name>`; the `segment` is `alpha=<alpha>` for a test at a tail level
  (null for a test with none); a row never carries a number when `light` is `not_evaluated`.
- The parameters of a light rule that are not alphas travel in the row's `extras["thresholds"]`, a mapping from the parameter name to
  its value, beside `alpha_amber` and `alpha_red`; a view reads them from there to explain a light.
- Tolerance: every golden value states its own tolerance or is exact; a golden stated to six decimals holds to `5e-7`.

## How the documents use the engine

| Document block (schema) | Produced by |
|---|---|
| C11 `outputs.grid`, `models[].by_level[].var`, `es`, `es_status`, `es_undefined_days` | `historical.*`, `parametric.*`, `garch.*`, `evt.*`, `caviar.*`, `gas_fz.*`, converted by `conventions.to_loss_numbers` |
| C11 `outputs.models[].by_level[].fz0_mean`, `n_fz0`, `tick_loss_mean` | `scoring.mean_scores` |
| C11 `outputs.models[].by_level[].traffic_light` (alpha 0.01 only) | `frtb.traffic_light_zone`, `frtb.binomial_cumulative_probability`; C11 models `fit.traffic_light` rows: `frtb.mar32_multiplier` |
| C11 `outputs.comparison.dm`, `mcs`, `champions` | `scoring.diebold_mariano`, `scoring.model_confidence_set` |
| C11 `outputs.es_backtests` and the `tests` rows | `validation.market.acerbi_szekely` and the other back-tests |
| C11 `outputs.hyperparameters`, models `fit.ladder` (`window_fits`, `evt` diagnostics) | `evt.threshold_stability`, the fits of `garch`, `caviar`, `gas_fz` |
| C13 `outputs.example`, `pla`, `detection` | `frtb.pla_spearman`, `pla_ks`, `pla_zone`, `validation.market.pla_test` |
| C13 `outputs.desk_backtest` | `frtb.desk_exceptions`, `desk_exception_limit`, `validation.market.desk_backtest` |
| C11 and C13 `tests` | `riskvalidation.validation.market.*` (rows of `common/test-result`) |

The Kenneth French returns are **derived-only** (dossier 08 C.5): a C11 window with a derived-only component commits forecasts, scores
and test statistics but not the realised loss series (`grid.realised_loss.status = "withheld-derived-only"` with its reason); the
Treasury par curve and the H.10 rates are mirror-allowed (dossier 08 C.2, C.8) and a window built only on them may carry the realised
series, so a view can draw the P&L bars and a test can recompute the exceedances.

## Module `riskvalidation/market/conventions.py`

The sign convention of dossier 05 A.0, and VaR and ES at a tail level from a sample or a distribution.

### `riskvalidation.market.conventions.to_loss_numbers`

```python
def to_loss_numbers(values: np.ndarray) -> np.ndarray: ...
```

- Units: any array of returns, VaR or ES in the return convention (decimals); the result has the same shape, positive loss numbers.
- Invariants: the result is `-values`; it is the inverse of `from_loss_numbers`; a NaN is kept as NaN (the caller reports an undefined
  ES as null in the document, never as a number); the function is the only place the sign is flipped.
- Golden: `[-0.023263, -0.026652]` gives `[0.023263, 0.026652]`.

### `riskvalidation.market.conventions.from_loss_numbers`

```python
def from_loss_numbers(values: np.ndarray) -> np.ndarray: ...
```

- Units: positive loss numbers (decimals); the result is in the return convention.
- Invariants: `from_loss_numbers(to_loss_numbers(x))` equals `x` exactly.
- Golden: `[0.02, 0.03]` gives `[-0.02, -0.03]`.

### `riskvalidation.market.conventions.var_es_from_sample`

```python
def var_es_from_sample(returns: np.ndarray, alpha: float) -> tuple[float, float]: ...
```

- Units: `returns` (N,) decimals; `alpha` in (0, 0.5); the result `(var, es)` in the return convention.
- Invariants: with `k = ceil(alpha * N)` and the returns `r(1) <= ... <= r(N)` sorted ascending, `var = r(k)` (D-3: the left-continuous
  inverse `F^-1(alpha) = inf{y : F(y) >= alpha}` of A.0) and `es = (sum_{i<k} r(i) + (alpha N - (k - 1)) r(k)) / (alpha N)`, the
  tail integral `(1/alpha) integral_0^alpha F^-1(u) du` of the empirical quantile function of A.0: the k-th return carries the fractional
  weight `alpha N - (k - 1)` when `alpha N` is not an integer (review F4: the mean of the k smallest overstates the tail count, and `alpha N` is
  2.5 and 6.25 for the 250-day rung at 0.01 and 0.025); `es <= var`; `ValueError` for `alpha` outside (0, 0.5), `N = 0` or a NaN; the
  result is invariant to the order of `returns`.
- Golden: `returns = [-0.001 * i for i in 1..100]`: `alpha = 0.05` gives `var = -0.096` and `es = -0.098` (`k = 5`, an integer
  `alpha N`); `alpha = 0.025` gives `var = -0.098` and `es = -0.0992` (`k = 3`, `alpha N = 2.5`: `(-0.100 - 0.099 + 0.5 * -0.098) / 2.5`).

### `riskvalidation.market.conventions.var_es_from_distribution`

```python
def var_es_from_distribution(ppf: Callable[[np.ndarray], np.ndarray], alpha: float, n_nodes: int = 200) -> tuple[float, float]: ...
```

- Units: `ppf` the quantile function of the return distribution (vectorised); `alpha` in (0, 0.5); the result `(var, es)` in the return convention.
- Invariants: `var = ppf(alpha)` and `es = (1/alpha) integral_0^alpha ppf(u) du` by Gauss-Legendre quadrature with `n_nodes` nodes (the
  definition of A.0); `es <= var`; for a location-scale family the result is affine in the location and scale.
- Golden: (formula of A.2 row 4, `es = mu - sigma phi(z)/alpha` with `z = Phi^-1(alpha)`) the standard normal at `alpha = 0.01` gives
  `var = -2.326348` and `es = -2.665214`; at `alpha = 0.025` it gives `var = -1.959964` and `es = -2.337803` (tolerance `1e-5`).

## Module `riskvalidation/market/historical.py`

The historical-simulation family of dossier 05 A.2 rows 1 to 3. Every function takes the returns dated before the forecast day, most
recent last, and returns the one-step forecast in the return convention.

### `riskvalidation.market.historical.age_weights`

```python
def age_weights(lam: float, k: int) -> np.ndarray: ...
```

- Units: `lam` in (0, 1), `k >= 1` a count of days; the result (k,) weights, index 0 the return observed one day ago.
- Invariants: `w_i = (1 - lam) / (1 - lam^k) * lam^(i-1)` for `i = 1..k` (A.2 row 2); the weights sum to 1 and decrease in `i`.
- Golden: `lam = 0.98`, `k = 100` (the worked example of Boudoukh, Richardson and Whitelaw 1998 in A.2 row 2) gives `w_1 = 0.023058`
  and a sum of 1.

### `riskvalidation.market.historical.historical_var_es`

```python
def historical_var_es(returns: np.ndarray, alpha: float, window: int) -> tuple[float, float]: ...
```

- Units: `returns` (N,) decimals with `N >= window`; `window` in days (250 or 500 for rung 1); the result in the return convention.
- Invariants: equal to `var_es_from_sample(returns[-window:], alpha)`; `ValueError` if `N < window`; a crisis return that leaves the window
  moves the result (the "ghost" effect of A.2 row 1 is a property to display, not to hide).
- Golden: `returns = [-0.001 * i for i in 1..100]`, `window = 100`, `alpha = 0.05` gives `(-0.096, -0.098)`.

### `riskvalidation.market.historical.age_weighted_var_es`

```python
def age_weighted_var_es(returns: np.ndarray, alpha: float, lam: float, window: int) -> tuple[float, float]: ...
```

- Units: `returns` (N,) decimals with `N >= window`; `lam` in (0, 1) (0.98 and 0.99 for rung 2); the result in the return convention.
- Invariants: the weight of the return observed `i` days ago is `age_weights(lam, window)[i-1]`; the returns are sorted ascending, the
  weights cumulated to `alpha` and the quantile interpolated linearly (A.2 row 2); as `lam` tends to 1 the result tends to
  `historical_var_es`; `es <= var`. UNVERIFIED: which points the linear interpolation joins (the midpoints of the weight steps or the
  cumulated weights themselves) is not stated in the dossier, and the tail-mean rule for the ES is not given there at all; U8-E reads
  Boudoukh, Richardson and Whitelaw (1998, author PDF in A.2 row 2) and its worked example before transcription. No golden value until then.

### `riskvalidation.market.historical.filtered_hs_var_es`

```python
def filtered_hs_var_es(std_residuals: np.ndarray, mu_next: float, sigma_next: float, alpha: float) -> tuple[float, float]: ...
```

- Units: `std_residuals` (N,) standardised residuals `z_t = (r_t - mu_t) / sigma_t` (the conditional mean removed, so the mean is not counted twice) of a GARCH or EWMA filter fitted on data before the forecast day;
  `mu_next` and `sigma_next` the one-step conditional mean and volatility (decimals); the result in the return convention.
- Invariants: the scenarios are `r*_{T+1} = mu_next + sigma_next * z_s` for every residual `z_s` (A.2 row 3; D-4: all residuals are used,
  not a random bootstrap, so the forecast is deterministic) and the result is `var_es_from_sample(scenarios, alpha)`; with `mu_next = 0` the
  result scales linearly with `sigma_next`; `ValueError` for `sigma_next <= 0`.
- Golden: `std_residuals = [-2, -1, 0, 1, 2]`, `mu_next = 0`, `sigma_next = 0.01`, `alpha = 0.2` gives `(-0.02, -0.02)` (`k = 1`).

### `riskvalidation.market.historical.volatility_updated_hs_var_es`

```python
def volatility_updated_hs_var_es(returns: np.ndarray, sigma_hist: np.ndarray, sigma_next: float, alpha: float) -> tuple[float, float]: ...
```

- Units: `returns` (N,) decimals; `sigma_hist` (N,) the conditional volatility estimated on each of those days; `sigma_next` the volatility
  for the forecast day; the result in the return convention.
- Invariants: the scenarios are `r*_i = r_i * sigma_next / sigma_hist_i` (Hull and White 1998, A.2 row 3) and the result is
  `var_es_from_sample(scenarios, alpha)`; with `sigma_hist` constant and equal to `sigma_next` the result equals `historical_var_es` on the whole input.
- Golden: `returns = [-0.02, 0.01]`, `sigma_hist = [0.01, 0.02]`, `sigma_next = 0.015`, `alpha = 0.5` gives scenarios `[-0.03, 0.0075]` and `(-0.03, -0.03)`.

## Module `riskvalidation/market/parametric.py`

Rungs 3 and 4: delta-normal, Cornish-Fisher, EWMA (dossier 05 A.2 rows 4 to 6).

### `riskvalidation.market.parametric.delta_normal_var_es`

```python
def delta_normal_var_es(mu: float, sigma: float, alpha: float) -> tuple[float, float]: ...
```

- Units: `mu` and `sigma` the portfolio mean and volatility over the horizon (decimals), `sigma > 0`; the result in the return convention.
- Invariants: `var = mu + Phi^-1(alpha) * sigma` and `es = mu - sigma * phi(Phi^-1(alpha)) / alpha` (A.2 row 4 in the return convention);
  `es <= var`; affine in `mu` and linear in `sigma`.
- Golden: `(mu, sigma, alpha) = (0, 1, 0.01)` gives `(-2.326348, -2.665214)`; `(0, 1, 0.025)` gives `(-1.959964, -2.337803)`.

### `riskvalidation.market.parametric.cornish_fisher_var`

```python
@dataclass(frozen=True)
class CornishFisher:
    var: float      # return convention
    z_cf: float     # the adjusted quantile
    valid: bool     # the validity domain holds

def cornish_fisher_var(mu: float, sigma: float, skew: float, excess_kurtosis: float, alpha: float) -> CornishFisher: ...
```

- Units: `mu`, `sigma` decimals; `skew` and `excess_kurtosis` dimensionless; `alpha` in (0, 0.5).
- Invariants: with `z = Phi^-1(alpha)`, `z_cf = z + (z^2-1) S/6 + (z^3-3z) Ke/24 - (2 z^3 - 5 z) S^2/36` and `var = mu + z_cf * sigma` (A.2 row 5);
  with `S = Ke = 0` the result equals the delta-normal VaR. The expansion is non-monotone for large `S` and `Ke` and the dossier requires the
  validity domain to be reported; D-6: `valid` is true when the derivative of the map `z -> z_cf(z)`, `1 + 2zS/6 + (3z^2-3)Ke/24 - (6z^2-5)S^2/36`,
  is positive at every point of `[Phi^-1(alpha), 0]` (checked on a grid of 201 points); the dossier does not define the domain. The origin of Cornish-Fisher VaR
  (Zangari, RiskMetrics Monitor 1996) is UNVERIFIED in the dossier. A document reports `valid = false` rather than hiding the forecast.
- Golden: (formula of A.2 row 5) `alpha = 0.01`, `S = -0.5`, `Ke = 1.0` gives `z_cf = -2.833709` and `valid = True`; `S = -3`, `Ke = 20` gives `z_cf = -5.821010` and
  `valid = False`.

### `riskvalidation.market.parametric.ewma_variance`

```python
def ewma_variance(returns: np.ndarray, lam: float, initial_variance: float) -> np.ndarray: ...
```

- Units: `returns` (T,) decimals; `lam` in (0, 1) (0.94 daily, 0.97 monthly, A.2 row 6); `initial_variance` the variance before the first return; the result (T+1,)
  one-step variances, element 0 the initial variance and element `t+1` the forecast for day `t+1` after observing `r_t`.
- Invariants: `sigma2_{t+1|t} = lam * sigma2_{t|t-1} + (1 - lam) * r_t^2` (the zero-mean assumption is part of the method, A.2 row 6); every element is
  positive when `initial_variance > 0`; `ValueError` for `initial_variance <= 0`.
- Golden: `returns = [0.02]`, `lam = 0.94`, `initial_variance = 0.0001` gives `[0.0001, 0.000118]`.

### `riskvalidation.market.parametric.ewma_effective_days`

```python
def ewma_effective_days(lam: float, tolerance: float) -> float: ...
```

- Units: `lam` in (0, 1), `tolerance` in (0, 1); the result a number of days (a float).
- Invariants: `K = ln(tolerance) / ln(lam)` (A.2 row 6); increasing in `lam`.
- Golden: `(0.94, 0.01)` gives `74.4` and `(0.97, 0.01)` gives `151.2` (74.427 and 151.191); the dossier states 74 days and 151 days at 1 percent, the integer parts.

### `riskvalidation.market.parametric.ewma_var_es`

```python
def ewma_var_es(returns: np.ndarray, lam: float, alpha: float, initial_variance: float) -> tuple[float, float]: ...
```

- Units: `returns` (T,) decimals before the forecast day; the result in the return convention.
- Invariants: the one-step variance is `ewma_variance(returns, lam, initial_variance)[-1]` and the result is `delta_normal_var_es(0, sqrt(variance), alpha)` (rung 4: the quantile is
  normal and the mean is zero).
- Golden: `returns = [0.02]`, `lam = 0.94`, `alpha = 0.01`, `initial_variance = 0.0001` gives `(-0.025271, -0.028952)` (`sigma = 0.010863`).

## Module `riskvalidation/market/garch.py`

Rung 5: GARCH(1,1), GJR-GARCH and EGARCH with Student-t innovations, through `arch` (dossier 05 A.2 rows 7 to 9 and the library mapping).

### `riskvalidation.market.garch.GarchFit`

```python
@dataclass(frozen=True)
class GarchFit:
    kind: str                       # "garch", "gjr" or "egarch"
    innovation: str                 # "student-t", "skew-t" or "normal"
    params: dict[str, float]        # omega, alpha[1], gamma[1] (gjr), beta[1], nu, mu
    log_likelihood: float
    converged: bool
    n_obs: int
```

- Units: parameters as returned by `arch` for returns scaled to percent (the engine rescales: `omega` is reported in decimals squared); `nu` degrees of freedom; counts.
- Invariants: for `kind = "garch"` the fit satisfies `omega > 0`, `alpha >= 0`, `beta >= 0` and `alpha + beta < 1` (A.2 row 7) or `converged` is false; for `"gjr"` the
  recursion is `sigma2_t = omega + (alpha + gamma * 1{eps_{t-1} < 0}) eps_{t-1}^2 + beta sigma2_{t-1}` (row 8); for `"egarch"` it is `ln sigma2_t = omega + beta ln sigma2_{t-1} + theta z_{t-1} + gamma (|z_{t-1}| - E|z_{t-1}|)` (row 9); `nu > 2` for Student-t
  innovations (unit variance).

### `riskvalidation.market.garch.fit_garch`

```python
def fit_garch(returns: np.ndarray, kind: str = "garch", innovation: str = "student-t", mean: str = "constant") -> GarchFit: ...
```

- Units: `returns` (N,) decimals before the forecast day, `N >= 250` (`ValueError` otherwise); `mean` in `{"zero", "constant"}`.
- Invariants: quasi-maximum-likelihood through `arch.arch_model`; deterministic (a fixed optimiser start and tolerance); a failed optimisation returns `converged = False`, never a made-up parameter;
  the fit never reads beyond the last element of `returns` (leakage).

### `riskvalidation.market.garch.garch_var_es_forecast`

```python
def garch_var_es_forecast(fit: GarchFit, returns: np.ndarray, alpha: float) -> tuple[float, float]: ...
```

- Units: `returns` the same series the fit used (the filter is run through it to the last day); the result `(var, es)` for the next day, in the return convention.
- Invariants: `var = mu + sigma_{t+1} q_alpha` and `es = mu + sigma_{t+1} * (1/alpha) integral_0^alpha q_u du` with `q` the quantile function of the unit-variance innovation (A.0); `es <= var`; for
  `innovation = "normal"` the result equals `delta_normal_var_es(mu, sigma_{t+1}, alpha)`.
- Golden: `innovation = "normal"`, `mu = 0`, `sigma_{t+1} = 0.01`, `alpha = 0.01` gives `(-0.023263, -0.026652)` (the A.2 row 4 formula).

## Module `riskvalidation/market/evt.py`

Rung 7: conditional EVT of McNeil and Frey (2000) (dossier 05 A.2 row 10). The formulas of row 10 are in the loss convention for the standardised residuals of
the filter, `z_loss = -z`, with `q` near 1; the functions of this module take and return the loss convention where they say so and convert at the boundary.

### `riskvalidation.market.evt.GpdFit`

```python
@dataclass(frozen=True)
class GpdFit:
    threshold: float     # u, the loss-residual threshold
    xi: float            # shape
    beta: float          # scale, > 0
    n: int               # residuals used
    n_exceed: int        # N_u, residuals above the threshold
    converged: bool
```

- Units: `threshold`, `beta` in standardised-residual units, `xi` dimensionless, counts.
- Invariants: `n_exceed <= n`; `beta > 0` when `converged`; a fit with `xi >= 1` is a valid fit whose ES is undefined (see `evt_var_es`).

### `riskvalidation.market.evt.fit_gpd`

```python
def fit_gpd(z_loss: np.ndarray, threshold_fraction: float) -> GpdFit: ...
```

- Units: `z_loss` (N,) standardised loss residuals; `threshold_fraction` in (0, 0.5), the share of residuals above the threshold (the original paper uses about the top 10 percent: UNVERIFIED in dossier 05 A.2 row 10).
- Invariants: `u` is the empirical `(1 - threshold_fraction)` quantile of `z_loss`; `N_u` counts the residuals strictly above `u`; the excesses `z - u` are fitted by maximum likelihood with
  `scipy.stats.genpareto` (location fixed at 0); `ValueError` if `N_u < 10`.

### `riskvalidation.market.evt.evt_var_es`

```python
def evt_var_es(fit: GpdFit, q: float) -> tuple[float, float | None]: ...
```

- Units: `q` the confidence level near 1 (`q = 1 - alpha`); the result `(z_q, es_q)` in standardised loss units; `es_q` is `None` when `xi >= 1`.
- Invariants: `z_q = u + (beta/xi) * ((n/N_u (1-q))^(-xi) - 1)` and `es_q = z_q/(1-xi) + (beta - xi u)/(1-xi)` for `xi < 1` (A.2 row 10); `es_q >= z_q` for `xi in [0, 1)`;
  `xi >= 1` gives `es_q = None` and the caller records the day in `es_undefined_days`, never a number.
- Golden: (formula of A.2 row 10) `u = 1`, `beta = 1`, `xi = 0.5`, `n = 1000`, `N_u = 100`, `q = 0.99` gives `z_q = 5.324555` and `es_q = 11.649111`.

### `riskvalidation.market.evt.conditional_evt_forecast`

```python
@dataclass(frozen=True)
class EvtForecast:
    var: float                 # return convention
    es: float | None           # None when xi >= 1
    xi: float
    n_exceed: int

def conditional_evt_forecast(returns: np.ndarray, alpha: float, threshold_fraction: float, kind: str = "garch") -> EvtForecast: ...
```

- Units: `returns` (N,) decimals before the forecast day; the result in the return convention.
- Invariants: an AR-GARCH filter is fitted by QML, the standardised residuals are tail-fitted by `fit_gpd`, and `VaR_{t+1} = mu_{t+1} + sigma_{t+1} z_q` in the loss convention (A.2 row 10),
  returned in the return convention; deterministic; `es = None` exactly when `xi >= 1`; the forecast never reads a return dated on or after the forecast day.

### `riskvalidation.market.evt.threshold_stability`

```python
def threshold_stability(z_loss: np.ndarray, fractions: np.ndarray) -> list[tuple[float, float, int]]: ...
```

- Units: `fractions` in (0, 0.5); the result one `(fraction, xi, n_exceed)` per fraction, ascending in `fraction`.
- Invariants: each `xi` is `fit_gpd(z_loss, fraction).xi`; `n_exceed` is nondecreasing in `fraction`; the threshold choice is the main model risk of the method (A.2 row 10), so the
  C11 models document keeps this table per window.

## Module `riskvalidation/market/caviar.py`

Rung 8: CAViaR (Engle and Manganelli 2004) and the ALD extension for ES (Taylor 2019) (dossier 05 A.2 row 11).

### `riskvalidation.market.caviar.CaviarFit`

```python
@dataclass(frozen=True)
class CaviarFit:
    spec: str                    # "sav" or "as"
    alpha: float
    params: np.ndarray           # (3,) for "sav", (4,) for "as"
    tick_loss: float             # the minimised sum of tick losses
    n_starts: int
    converged: bool
```

- Units: parameters in return units; `tick_loss` the sum over the estimation sample.
- Invariants: `sav`: `f_t = b1 + b2 f_{t-1} + b3 |y_{t-1}|`; `as`: `f_t = b1 + b2 f_{t-1} + b3 (y_{t-1})^+ + b4 (y_{t-1})^-` (A.2 row 11); UNVERIFIED: the dossier does not define `(y)^-`
  (Engle and Manganelli's convention, `-min(y, 0)`, is not confirmed in the dossier). `n_starts >= 2` (the objective is non-convex: multiple starts are needed, A.2 rung 8).

### `riskvalidation.market.caviar.fit_caviar`

```python
def fit_caviar(y: np.ndarray, alpha: float, spec: str = "sav", n_starts: int = 20, seed: int = 0) -> CaviarFit: ...
```

- Units: `y` (N,) returns before the forecast day, `N >= 500`; `spec` in `{"sav", "as"}`.
- Invariants: the parameters minimise the tick loss `sum_t (alpha - 1{y_t < f_t})(y_t - f_t)` (A.2 row 11) over `n_starts` random starts; the reported `tick_loss` is the best found and does not
  exceed the tick loss of the constant empirical-quantile benchmark; same inputs and seed give the same fit.

### `riskvalidation.market.caviar.caviar_var_forecast`

```python
def caviar_var_forecast(fit: CaviarFit, y: np.ndarray) -> float: ...
```

- Units: `y` the estimation series; the result the next-day VaR in the return convention.
- Invariants: the recursion is run through `y` from the fit's initial value to the last day; the result is the `f_{T+1}` of the specification; it never reads beyond `y[-1]`; the model forecasts VaR only (A.2 row 11).

### `riskvalidation.market.caviar.caviar_es_forecast`

```python
def caviar_es_forecast(fit: CaviarFit, y: np.ndarray) -> float: ...
```

- Units: as `caviar_var_forecast`; the result the next-day ES in the return convention.
- Invariants: `es <= caviar_var_forecast(fit, y)`. UNVERIFIED: the ALD-based ES extension of Taylor (2019, JBES 37(1):121-133) is cited in dossier 05 A.2 row 11 but its equations are not transcribed there;
  U8-E reads the paper before transcription. No golden value until then.

### `riskvalidation.market.caviar.dynamic_quantile_statistic`

```python
def dynamic_quantile_statistic(hits: np.ndarray, var: np.ndarray, alpha: float, lags: int = 4) -> tuple[float, float]: ...
```

- Units: `hits` (T,) the exceedance indicators `1{y_t < VaR_t}`; `var` (T,) the VaR forecasts; the result `(statistic, p_value)` of the dynamic quantile (DQ) test of Engle and Manganelli (2004), asymptotically chi-square.
- Invariants: `p_value` in [0, 1]; the statistic is the Wald-type quadratic form of the regression of `hits - alpha` on a constant, `lags` lagged hits and the contemporaneous VaR; UNVERIFIED: the dossier names the test
  (A.2 row 11) but gives neither the regressor set nor the degrees of freedom; U8-E reads the paper and the regressor set above is the one to confirm.

## Module `riskvalidation/market/gas_fz.py`

Rung 9: the dynamic semiparametric models of Patton, Ziegel and Chen (2019), estimated by minimising the average FZ0 loss (dossier 05 A.1 and A.2 row 12).

### `riskvalidation.market.gas_fz.GasFzFit`

```python
@dataclass(frozen=True)
class GasFzFit:
    spec: str                    # "one-factor", "two-factor" or "hybrid"
    alpha: float
    params: np.ndarray
    mean_fz0: float              # the minimised average FZ0 loss on the estimation sample
    n_starts: int
    converged: bool
```

- Units: parameters in the units of the recursion; `mean_fz0` the average FZ0 loss of A.1.
- Invariants: the objective is the average FZ0 loss (A.1, arXiv 1707.05108 eq. 6); every fitted path has `e_t <= v_t < 0`. UNVERIFIED: dossier 05 A.1 states only that the models are dynamic, GAS-type and estimated
  on the FZ0 loss; the score-driven recursions themselves are not transcribed there; U8-E reads Patton, Ziegel and Chen (2019, arXiv 1707.05108) before transcription.

### `riskvalidation.market.gas_fz.fit_gas_fz`

```python
def fit_gas_fz(y: np.ndarray, alpha: float, spec: str = "one-factor", n_starts: int = 20, seed: int = 0) -> GasFzFit: ...
```

- Units: `y` (N,) returns before the forecast day, `N >= 500`; `spec` in `{"one-factor", "two-factor"}`.
- Invariants: the best of `n_starts` starts; `mean_fz0` does not exceed the average FZ0 of the constant (unconditional empirical VaR and ES) benchmark on the same sample, since the benchmark is nested; the estimation is unstable for small `alpha`
  (A.2 rung 9), so `converged = False` is a result, not an error; same inputs and seed give the same fit.

### `riskvalidation.market.gas_fz.gas_fz_forecast`

```python
def gas_fz_forecast(fit: GasFzFit, y: np.ndarray) -> tuple[float, float]: ...
```

- Units: `y` the estimation series; the result `(var, es)` for the next day in the return convention.
- Invariants: `es <= var < 0`; the recursion is run through `y` and never reads beyond `y[-1]`.

### `riskvalidation.market.gas_fz.fit_hybrid_garch_fz`

```python
def fit_hybrid_garch_fz(y: np.ndarray, alpha: float, n_starts: int = 20, seed: int = 0) -> GasFzFit: ...
```

- Units: as `fit_gas_fz`; the fit has `spec = "hybrid"`.
- Invariants: a GARCH volatility filter drives the (VaR, ES) pair and the parameters minimise the average FZ0 loss (A.1: "a hybrid GARCH-FZ"); `es <= var < 0` on every day of the fitted path; UNVERIFIED as for `GasFzFit`.

## Module `riskvalidation/market/scoring.py`

The FZ0 and tick losses and the comparison tests (dossier 05 A.1, B.6).

### `riskvalidation.market.scoring.fz0_loss`

```python
def fz0_loss(y: np.ndarray, v: np.ndarray, e: np.ndarray, alpha: float) -> np.ndarray: ...
```

- Units: `y` realised returns, `v` VaR forecasts and `e` ES forecasts in the return convention (decimals), same shape; the result the per-day FZ0 loss (dimensionless; it can be negative; only differences between models are meaningful).
- Invariants: `L = -(1/(alpha e)) 1{y <= v} (v - y) + v/e + log(-e) - 1` (A.1, arXiv 1707.05108 eq. 6); `ValueError` unless `v < 0`, `e < 0` and `e <= v` elementwise; it is the FZ loss of eq. 4 with `G1 = 0`,
  `G2(x) = -1/x` and `calG2(x) = -log(-x)` (the reduction of A.1, checked by the test); with `e = v` and `y > v` the value is `1 + log(-v) - 1 = log(-v)`.
- Golden: `(y, v, e, alpha) = (-0.03, -0.02, -0.025, 0.01)` gives `36.111121`; `(0.01, -0.02, -0.03, 0.025)` gives `-3.839891`; `(0.0, -0.02, -0.02, 0.01)` gives `-3.912023` (`log 0.02`). Reduction: the general FZ loss with `G1 = 0`,
  `G2 = -1/x`, `calG2 = -log(-x)` equals `fz0_loss` at every point (tolerance `1e-12`).

### `riskvalidation.market.scoring.tick_loss`

```python
def tick_loss(y: np.ndarray, v: np.ndarray, alpha: float) -> np.ndarray: ...
```

- Units: return convention, same shape; the result the per-day tick loss (decimals, nonnegative).
- Invariants: `(alpha - 1{y < v})(y - v)` (A.2 row 11); nonnegative; zero at `y = v`.
- Golden: `(y, v, alpha) = (-0.03, -0.02, 0.01)` gives `0.0099`; `(-0.01, -0.02, 0.01)` gives `0.0001`.

### `riskvalidation.market.scoring.mean_scores`

```python
@dataclass(frozen=True)
class Scores:
    n: int                       # days scored for the tick loss
    n_fz0: int                   # days with both VaR and ES defined
    fz0_mean: float | None       # None when n_fz0 = 0
    tick_mean: float

def mean_scores(y: np.ndarray, v: np.ndarray, e: np.ndarray, alpha: float) -> Scores: ...
```

- Units: return convention; `e` may hold NaN on days the ES is undefined; the result maps onto the document fields `n_scored`, `n_fz0`, `fz0_mean` (null when `n_fz0 = 0`, with `fz0_reason`) and `tick_loss_mean`.
- Invariants: `fz0_mean` averages `fz0_loss` over the days with a finite `e`; `tick_mean` averages `tick_loss` over all `n` days; `n_fz0 <= n`; a model that forecasts no ES has `n_fz0 = 0` and `fz0_mean = None`, never a number.

### `riskvalidation.market.scoring.diebold_mariano`

```python
@dataclass(frozen=True)
class DmResult:
    mean_diff: float             # mean of loss_a - loss_b
    statistic: float
    p_value: float               # two-sided, normal
    n: int
    lags: int

def diebold_mariano(loss_a: np.ndarray, loss_b: np.ndarray, lags: int) -> DmResult: ...
```

- Units: per-day losses (FZ0 for the pair (VaR, ES), the tick loss for the VaR, B.6) on the common sample; `lags >= 0`. The lag rule (review F11): the forecasts of this
  contract are one-step ahead, so `lags = 0` (h - 1 lags for an h-step forecast, after Diebold and Mariano 1995; UNVERIFIED: the primary text was not read in this session); the
  documents record the value used in `comparison.hac_lags` and every `dm` row repeats it.
- Invariants: `d_t = loss_a_t - loss_b_t`, `DM = mean(d) / sqrt(LRV / T)` with the Newey-West long-run variance `LRV = g0 + 2 sum_{j=1}^{lags} (1 - j/(lags+1)) g_j`, `g_j = (1/T) sum_t (d_t - mean)(d_{t-j} - mean)` (D-2: the dossier says only
  "a HAC long-run variance"; the Bartlett kernel is the contract choice and the documents name it, `comparison.hac_kernel = "bartlett"`); `p_value = 2 (1 - Phi(|DM|))` (the dossier: `DM -> N(0, 1)`); a negative `mean_diff` means model A has the lower loss;
  `ValueError` if `d` has zero spread (the statistic is undefined) or `T <= lags + 1`; the two series must be defined on the same days.
- Golden: `d = [0.1, -0.05, 0.2, 0.1, 0.0, 0.15]`, `lags = 0` gives `DM = 2.401922` and `p_value = 0.016309` (the document test recomputes every `dm` row of the fixture from its stated series this way).

### `riskvalidation.market.scoring.model_confidence_set`

```python
@dataclass(frozen=True)
class McsResult:
    members: list[int]           # indices of the models in the set
    p_values: np.ndarray         # (M,) MCS p-values
    confidence: float
    statistic: str               # "Tmax" or "TR"

def model_confidence_set(losses: np.ndarray, confidence: float = 0.90, statistic: str = "TR", n_bootstrap: int = 1000, block_length: int = 10, seed: int = 0) -> McsResult: ...
```

- Units: `losses` (T, M) per-day losses (FZ0) on the common sample; `confidence` in (0, 1).
- Invariants: through `arch.bootstrap.MCS` (Hansen, Lunde and Nason 2011, B.6); a model is in the set iff its MCS p-value is at least `1 - confidence`; the set is never empty; `M = 1` gives that model with p-value 1;
  same inputs and seed give the same result.

## Module `riskvalidation/market/frtb.py`

The FRTB statistics of dossier 01 D.4 (MAR32.4 to MAR32.9, MAR32.18 to MAR32.19, MAR32.36 to MAR32.42).

### `riskvalidation.market.frtb.binomial_cumulative_probability`

```python
def binomial_cumulative_probability(k: int, n: int, p: float) -> float: ...
```

- Units: counts and a probability; the result `P(X <= k)`, `X ~ Bin(n, p)`, in [0, 1].
- Invariants: `sum_{i=0}^{k} C(n,i) p^i (1-p)^(n-i)` (D.4); nondecreasing in `k`; 1 at `k = n`.
- Golden: (MAR32.9 Table 1, dossier 01 D.4; `n = 250`, `p = 0.01`, in percent to two decimals) `k = 0..10` gives 8.11, 28.58, 54.32, 75.81, 89.22, 95.88, 98.63, 99.60, 99.89, 99.97, 99.99.

### `riskvalidation.market.frtb.traffic_light_zone`

```python
def traffic_light_zone(exceptions: int, n: int = 250, coverage: float = 0.99) -> str: ...
```

- Units: a count in 250 days (or `n`); the result in `{"green", "amber", "red"}`.
- Invariants: amber starts where the binomial cumulative probability at true coverage first reaches 95 percent and red where it reaches 99.99 percent (MAR99.17 notes, D.4); for `n = 250` and `coverage = 0.99` green is 0 to 4, amber 5 to 9, red 10 or more (MAR32.9 Table 1); monotone in `exceptions`.
- Golden: `4 -> green`, `5 -> amber`, `9 -> amber`, `10 -> red`.

### `riskvalidation.market.frtb.mar32_multiplier`

```python
def mar32_multiplier(exceptions: int) -> float: ...
```

- Units: a count; the result the backtesting-dependent multiplier `m_c` (dimensionless).
- Invariants: nondecreasing in `exceptions`; 1.50 for 0 to 4, then 1.70, 1.76, 1.83, 1.88, 1.92 for 5 to 9, and 2.00 for 10 or more (MAR32.9 Table 1, D.4). The US multiplication factors of 12 CFR 217.204 Table 1 (dossier 05 B.4: 3.00 for 0 to 4, 3.40, 3.50, 3.65, 3.75, 3.85 for 5 to 9, 4.00 for 10 or more)
  are reference values in the C11 models document, not a function of the engine.
- Golden: `mar32_multiplier(4) = 1.50`, `mar32_multiplier(5) = 1.70`, `mar32_multiplier(9) = 1.92`, `mar32_multiplier(10) = 2.00`.

### `riskvalidation.market.frtb.desk_exception_limit`

```python
def desk_exception_limit(alpha: float) -> int: ...
```

- Units: `alpha` in `{0.01, 0.025}`; the result the maximum tolerated exceptions in the last 12 months.
- Invariants: 12 at 0.01 (99 percent VaR) and 30 at 0.025 (97.5 percent VaR) (MAR32.18 to MAR32.19, D.4: a desk with more than 12 exceptions at 99 percent or 30 at 97.5 percent in the last 12 months moves to the standardised approach); `ValueError` for another `alpha`.
- Golden: `desk_exception_limit(0.01) = 12`; `desk_exception_limit(0.025) = 30`.

### `riskvalidation.market.frtb.desk_exceptions`

```python
def desk_exceptions(loss: np.ndarray, var: np.ndarray, missing_as_exception: bool = True) -> int: ...
```

- Units: `loss` and `var` (T,) positive loss numbers, T the days of the window (250); the result a count.
- Invariants: the count of days with `loss > var`; with `missing_as_exception` a NaN in either input counts as an exception (MAR32.4 to MAR32.9 states "missing P&L or VaR counts as an outlier" for the bank-wide test; for a desk the dossier
  does not say, UNVERIFIED, and the flag is explicit); the count is at most `T`.
- Golden: `loss = [0.01, 0.03, nan, 0.02]`, `var = [0.02, 0.02, 0.02, 0.02]` gives 1 with `missing_as_exception = False` and 2 with `True`.

### `riskvalidation.market.frtb.pla_spearman`

```python
def pla_spearman(hpl: np.ndarray, rtpl: np.ndarray) -> float: ...
```

- Units: `hpl` and `rtpl` (250,) daily P&L as decimals of the desk notional; the result in [-1, 1].
- Invariants: the Pearson correlation of the rank series (average ranks for ties), `cov(R_HPL, R_RTPL) / (sigma_R_HPL sigma_R_RTPL)` (MAR32.36 to MAR32.38, D.4); `ValueError` unless both have exactly 250 finite observations
  (MAR32.20: the most recent 250 trading days) or either has zero spread; invariant to any strictly increasing transform of either series.
- Golden: `hpl = [0, 1, ..., 249]` and `rtpl` equal to `hpl` gives `1.0`; `rtpl` the reverse gives `-1.0`; `rtpl` equal to `hpl` with its first two values swapped gives `1 - 6 * 2 / (250 * (250^2 - 1)) = 0.999999` (the rank formula without ties).

### `riskvalidation.market.frtb.pla_ks`

```python
def pla_ks(hpl: np.ndarray, rtpl: np.ndarray) -> float: ...
```

- Units: as `pla_spearman`; the result in [0, 1].
- Invariants: `KS = sup_x |F_RTPL(x) - F_HPL(x)|` with `F(x) = 0.004 * #{observations <= x}` (MAR32.39 to MAR32.41, D.4: the ECDF step is 0.004 for 250 observations). The gap is computed as an exact integer
  count of steps, `gap = max_x |#{rtpl <= x} - #{hpl <= x}|`, and `KS = gap / 250`: the literal product `0.004 * a - 0.004 * b` gives `0.12000000000000002` for an exact 30-step gap, which would put a desk that MAR32.42
  classes as amber (KS not above 0.12) in red (review F5); `30 / 250` is exactly the float `0.12`. The supremum is taken over the union of the observations; symmetric in the two series; 0 for identical series; `ValueError` unless both have 250 finite observations.
- Golden: `hpl = [0, 1, ..., 249]` and `rtpl = hpl + 0.5` give `0.004` (every ECDF step is shifted by one observation); `rtpl = hpl + 29.5` (a 30-step gap) gives exactly `0.12` and, with Spearman 1.0, the `pla_zone` amber; `rtpl = hpl + 30.5` (31 steps) gives `0.124`, red.

### `riskvalidation.market.frtb.pla_zone`

```python
def pla_zone(spearman: float, ks: float) -> str: ...
```

- Units: the two statistics; the result in `{"green", "amber", "red"}`.
- Invariants (MAR32.42, D.4): green when Spearman is above 0.80 and KS is below 0.09; red when Spearman is below 0.70 or KS is above 0.12; amber otherwise; the boundaries belong to amber; red takes precedence over green only through
  the stated conditions (they are exclusive).
- Golden: `(0.81, 0.08) -> green`, `(0.80, 0.05) -> amber`, `(0.85, 0.09) -> amber`, `(0.69, 0.05) -> red`, `(0.70, 0.05) -> amber`, `(0.95, 0.121) -> red`, `(0.95, 0.12) -> amber`. The single-statistic zones used by the C13 `pla.zones.spearman` and `ks` counts are
  green above 0.80 / below 0.09, red below 0.70 / above 0.12, amber between.

## Module `riskvalidation/validation/market.py`

The back-tests as `TestResult`s. Common arguments: `model_id: str | None`. A light rule compares the p-value (or the stated statistic) to `alpha_amber` and `alpha_red` supplied by the caller (policy parameters; the dossier fixes the 5 percent level
for the Kupiec and Christoffersen tests in "Implications for Contraste", rung 1: `alpha_red = 0.05`; the fixtures use `alpha_amber = 0.10`): red when `p < alpha_red`, amber when `p < alpha_amber`, otherwise green.

### `riskvalidation.validation.market.kupiec_pof`

```python
def kupiec_pof(exceedances: np.ndarray, alpha: float, model_id: str | None = None, alpha_amber: float = 0.10, alpha_red: float = 0.05) -> TestResult: ...
```

- Test: test_id = "market.kupiec_pof"; `exceedances` (T,) bool; `segment = "alpha=<alpha>"`.
- Units: `statistic = LR_POF`; `p_value` the asymptotic chi-square(1) p-value; `metric` the exact binomial p-value; `n = T`; `n_events = x`; `extras = {"p_value_exact_basis": "binomial-minlike", "expected_events": alpha * T}`.
- Light: by the asymptotic `p_value` against `alpha_amber` and `alpha_red`; `not_evaluated` if `T = 0`.
- Invariants: `LR_POF = -2 ln[(1-p)^(T-x) p^x / ((1-pi)^(T-x) pi^x)]`, `pi = x/T`, with `0 ln 0 = 0` (B.1); asymptotically chi-square(1), critical value 3.841 at 5 percent; D-1: the exact binomial p-value is the total probability of the outcomes at most as likely as `x`
  under `Bin(T, alpha)` (the dossier asks for "the exact binomial p-value" next to the asymptotic one and does not define the two-sided form); with `T = 250`, `p = 0.01` the expected count is 2.5 and the power is low (B.1), which the row's `notes` states.
- Golden: `T = 250`, `x = 5`, `alpha = 0.01` gives `statistic = 1.956810`, `p_value = 0.161855`, `metric = 0.107812`, light green; `T = 250`, `x = 0` gives `statistic = 5.025168`, `p_value = 0.024982`; the critical value `chi2.ppf(0.95, 1) = 3.841`.

### `riskvalidation.validation.market.christoffersen_independence`

```python
def christoffersen_independence(exceedances: np.ndarray, alpha: float, model_id: str | None = None, alpha_amber: float = 0.10, alpha_red: float = 0.05) -> TestResult: ...
```

- Test: test_id = "market.christoffersen_independence"; `segment = "alpha=<alpha>"`.
- Units: `statistic = LR_ind`; `p_value` chi-square(1); `n = T`; `n_events = x`; `extras = {"transitions": [n00, n01, n10, n11]}`.
- Light: by `p_value`; `not_evaluated` when `x = 0` or `x = T` (D-7: no exceedance, or all, leaves nothing to test for clustering; the convention `0^0 = 1` of B.2 would otherwise return the number 0 for a test that did not run).
- Invariants: `LR_ind = -2 ln[(1-pi)^(n00+n10) pi^(n01+n11) / ((1-pi01)^n00 pi01^n01 (1-pi11)^n10 pi11^n11)]` with `pi01 = n01/(n00+n01)`, `pi11 = n11/(n10+n11)`, `pi = (n01+n11)/(n00+n01+n10+n11)` and `0^0 = 1` when `n11 = 0` (B.2); clustered exceedances raise the statistic.
- Golden: `exceedances = [0]*10 + [1, 1] + [0]*8` (transitions `n00=16, n01=1, n10=1, n11=1`) gives `statistic = 2.407835` and `p_value = 0.120729`.

### `riskvalidation.validation.market.christoffersen_conditional_coverage`

```python
def christoffersen_conditional_coverage(exceedances: np.ndarray, alpha: float, model_id: str | None = None, alpha_amber: float = 0.10, alpha_red: float = 0.05) -> TestResult: ...
```

- Test: test_id = "market.christoffersen_conditional_coverage"; `segment = "alpha=<alpha>"`.
- Units: `statistic = LR_cc = LR_POF + LR_ind`; `p_value` chi-square(2); `n = T`; `n_events = x`.
- Light: by `p_value`; `not_evaluated` exactly when `christoffersen_independence` is.
- Invariants: `LR_cc = LR_POF + LR_ind`, asymptotically chi-square(2), critical value 5.991 at 5 percent (B.2); never below `LR_POF`.
- Golden: the sequence of the independence golden (`T = 20`, `x = 2`) at `alpha = 0.01` has `LR_POF = 5.779174`, so `statistic = 8.187009` and `p_value = 0.016681`; the critical value `chi2.ppf(0.95, 2) = 5.991`; `statistic` equals the Kupiec statistic plus the independence statistic to `1e-12`.

### `riskvalidation.validation.market.duration_test`

```python
def duration_test(exceedances: np.ndarray, alpha: float, model_id: str | None = None, n_mc: int = 10000, seed: int = 0, alpha_amber: float = 0.10, alpha_red: float = 0.05) -> TestResult: ...
```

- Test: test_id = "market.duration_test"; `segment = "alpha=<alpha>"`.
- Units: `statistic` the likelihood-ratio statistic of `b = 1` against a Weibull hazard; `p_value` by Monte Carlo with `n_mc` draws (small-sample p-values are recommended, B.3); `n = T`; `n_events = x`.
- Light: by `p_value`; `not_evaluated` with fewer than 2 exceedances (D-8: no completed no-hit duration; the dossier says the test treats the censored first and last spells explicitly and does not give a minimum, so the minimum is for U8-E to confirm against the paper).
- Invariants: under correct conditional coverage the durations are memoryless (exponential, Weibull `b = 1`), asymptotically chi-square(1); same inputs and seed give the same p-value. UNVERIFIED: the Weibull hazard parameterisation `lambda(d) = a^b b d^(b-1)` is the standard one used in later
  literature; the exact form in Christoffersen and Pelletier (2004) was not read in full text (dossier 05 B.3): re-check before transcription.
- Golden: none until U8-E transcribes the likelihood (UNVERIFIED); the invariant above (a reproducible Monte Carlo p-value, and `not_evaluated` below 2 exceedances) is the test until then.

### `riskvalidation.validation.market.basel_traffic_light`

```python
def basel_traffic_light(exceedances: np.ndarray, model_id: str | None = None, coverage: float = 0.99, window: int = 250) -> TestResult: ...
```

- Test: test_id = "market.basel_traffic_light"; `segment = "alpha=0.01"`.
- Units: `statistic` the number of exceptions in the last `window` days; `metric` the cumulative probability `P(X <= k)` in percent; `p_value` null; `n = window`; `n_events = k`; `extras = {"mar32_multiplier": m_c, "zone": zone}`.
- Light: the zone of `traffic_light_zone` (green, amber, red); `not_evaluated` with fewer than `window` days.
- Invariants: counts only the last `window` days; consistent with `binomial_cumulative_probability` and `mar32_multiplier`; the zone is monotone in the count.
- Golden: (MAR32.9 Table 1) `k = 4` gives `metric = 89.22`, green, multiplier 1.50; `k = 5` gives 95.88, amber, 1.70; `k = 9` gives 99.97, amber, 1.92; `k = 10` gives 99.99, red, 2.00.

### `riskvalidation.validation.market.acerbi_szekely`

```python
def acerbi_szekely(loss: np.ndarray, var: np.ndarray, es: np.ndarray, alpha: float, simulate_null: Callable[[np.random.Generator], np.ndarray], model_id: str | None = None, statistic: str = "Z2", n_sim: int = 10000, seed: int = 0, alpha_amber: float = 0.05, alpha_red: float = 0.0001) -> TestResult: ...
```

- Test: test_id = "market.acerbi_szekely"; `segment = "alpha=<alpha>"`.
- Units: `loss`, `var`, `es` (T,) positive loss numbers; `simulate_null(rng)` returns one simulated loss path (T,) from the model's own predictive distributions; `statistic` the realised `Z1` or `Z2`; `p_value` the left-tail share of the `n_sim` simulated statistics (with the +1 correction);
  `extras = {"statistic_name": "Z2", "critical_5pct": ..., "critical_0_01pct": ..., "reference": {"yellow": -0.70, "red": -1.8}, "n_draws": n_sim}`.
- Light: by the simulated `p_value` against `alpha_amber` (5 percent) and `alpha_red` (0.01 percent, which needs at least 10,000 draws to resolve); `not_evaluated` when any `es` is NaN (the ES is undefined that day, for example a conditional EVT with `xi >= 1`) or the model forecasts no ES.
- Invariants: `Z1 = (1/N_T) sum X_t I_t / ES_t + 1`, `Z2 = sum X_t I_t / (T alpha ES_t) + 1`, `X_t = -loss_t`, `I_t = 1{loss_t > VaR_t}` (B.5); both have expectation 0 under H0 and are negative when risk is underestimated; the critical values are simulated per model (B.5: they
  are model dependent in principle); the values -0.70 (5 percent, yellow) and -1.8 (0.01 percent, red) for `T = 250`, `alpha = 2.5%` are a published reference point verified only through Moldenhauer and Pitera (arXiv 1709.01337, section 6) and are never a regulatory threshold
  (dossier 05 "What NOT to claim"). UNVERIFIED: the primary Acerbi and Szekely text (Risk, December 2014, gated) was not retrieved.
- Golden: (formula of B.5) `loss = [0, 0, 0, 0, 0.05]`, `var = 0.02` everywhere, `es = 0.03` everywhere, `alpha = 0.025`, `T = 5` gives `Z2 = -12.333333`.

### `riskvalidation.validation.market.du_escanciano_unconditional`

```python
def du_escanciano_unconditional(pit: np.ndarray, alpha: float, model_id: str | None = None, alpha_amber: float = 0.10, alpha_red: float = 0.05) -> TestResult: ...
```

- Test: test_id = "market.du_escanciano_unconditional"; `segment = "alpha=<alpha>"`.
- Units: `pit` (T,) probability integral transforms `u_t = F_t(Y_t)` in [0, 1] from the forecast distributions; `statistic = U_ES`; `p_value` one-sided upper tail of N(0, 1); `n = T`.
- Light: by `p_value`; `not_evaluated` if the model gives no predictive distribution (`pit` all NaN) or `T < 2`.
- Invariants: `H_t = (1/alpha)(alpha - u_t) 1{u_t <= alpha}`, `E[H_t] = alpha/2`, `Var(H_t) = alpha (1/3 - alpha/4)` (derived in dossier 05 B.5 from `u ~ U(0, 1)`), `U_ES = sqrt(T)(mean(H) - alpha/2) / sqrt(alpha (1/3 - alpha/4))`, asymptotically N(0, 1)
  (Du and Escanciano 2017); D-5: a large positive `U_ES` means underestimated risk, so the p-value is one-sided (the dossier does not state the side); the plain asymptotic version ignores parameter estimation uncertainty, which the row's `notes` states (B.5).
- Golden: `alpha = 0.025`: `E[H] = 0.0125` and `Var(H) = 0.0081770833`; `pit = 0.5` for `T = 100` days gives `H = 0` and `statistic = -1.382327`.

### `riskvalidation.validation.market.du_escanciano_conditional`

```python
def du_escanciano_conditional(pit: np.ndarray, alpha: float, lags: int = 5, model_id: str | None = None, alpha_amber: float = 0.10, alpha_red: float = 0.05) -> TestResult: ...
```

- Test: test_id = "market.du_escanciano_conditional"; `segment = "alpha=<alpha>"`.
- Units: `pit` as above; `statistic = C_ES(m)`; `p_value` chi-square(`lags`); `n = T`; `extras = {"lags": lags}`.
- Light: by `p_value`; `not_evaluated` as the unconditional test, or `T <= lags`, or when `H - alpha/2` has zero spread.
- Invariants: `C_ES(m) = T sum_{j=1}^m rho_j^2`, the Box-Pierce statistic of the first `m` autocorrelations of `H_t - alpha/2` (B.5); nonnegative; asymptotically chi-square(`m`).
- Golden: a constant `H` series has zero spread and is `not_evaluated`; the 5 percent critical value is `chi2.ppf(0.95, m)` (3.841 for `m = 1`, 5.991 for `m = 2`).

### `riskvalidation.validation.market.mcneil_frey_residual_test`

```python
def mcneil_frey_residual_test(loss: np.ndarray, var: np.ndarray, es: np.ndarray, sigma: np.ndarray, alpha: float, model_id: str | None = None, n_boot: int = 10000, seed: int = 0, alpha_amber: float = 0.10, alpha_red: float = 0.05) -> TestResult: ...
```

- Test: test_id = "market.mcneil_frey_residual_test"; `segment = "alpha=<alpha>"`.
- Units: positive loss numbers (T,), `sigma` (T,) the conditional volatility forecasts; `statistic` the mean of the exceedance residuals; `p_value` the one-sided bootstrap p-value of a zero mean; `n_events` the exceedance count.
- Light: by `p_value`; `not_evaluated` with fewer than 2 exceedances (D-8 reasoning: a bootstrap needs spread) or any NaN `es`.
- Invariants: on exceedance days `r_t = (L_t - ES_t) / sigma_t` should be i.i.d. with mean zero (B.5, McNeil and Frey 2000); same inputs and seed give the same p-value.
- Golden: the bootstrap resamples the exceedance residuals centred at their mean, with a +1 correction, and the p-value is the share of resampled means at or above the observed mean (a positive mean means the loss exceeds the ES, risk underestimated).
  Exceedance residuals `[1.0, 2.0, 3.0]` give `statistic = 2.0`; every centred resample mean is at most 1.0, so `p_value = 1/(n_boot + 1) = 0.00009999` for `n_boot = 10000`, any seed.

### `riskvalidation.validation.market.dynamic_quantile_test`

```python
def dynamic_quantile_test(hits: np.ndarray, var: np.ndarray, alpha: float, lags: int = 4, model_id: str | None = None, alpha_amber: float = 0.10, alpha_red: float = 0.05) -> TestResult: ...
```

- Test: test_id = "market.dynamic_quantile_test"; `segment = "alpha=<alpha>"`.
- Units: as `caviar.dynamic_quantile_statistic`; `statistic` the DQ statistic; `p_value` chi-square; `n = T`.
- Light: by `p_value`; `not_evaluated` when `T <= lags + 2`.
- Invariants: wraps `caviar.dynamic_quantile_statistic` and adds nothing; UNVERIFIED as that function (dossier 05 A.2 row 11 names the test without its form).
- Golden: none until U8-E transcribes the statistic (UNVERIFIED); the invariant above is the test until then.

### `riskvalidation.validation.market.pla_test`

```python
def pla_test(hpl: np.ndarray, rtpl: np.ndarray, model_id: str | None = None) -> TestResult: ...
```

- Test: test_id = "market.pla_test"; `segment = null`.
- Units: 250 daily values as decimals of the desk notional; `statistic` the Spearman correlation; `metric` the KS statistic; `p_value` null (MAR32.42 zones are defined on the statistics); `n = 250`; `extras = {"zone": zone, "thresholds": {"spearman_green": 0.80, "spearman_red": 0.70, "ks_green": 0.09, "ks_red": 0.12}}`.
- Light: the zone of `pla_zone` (green, amber, red); `not_evaluated` unless both series have exactly 250 finite observations and nonzero spread. `alpha_amber` and `alpha_red` are null.
- Invariants: `statistic = pla_spearman(hpl, rtpl)`, `metric = pla_ks(hpl, rtpl)`, `light = pla_zone(statistic, metric)` (MAR32.36 to MAR32.42); red means the desk is ineligible for the IMA and amber triggers the capital surcharge (MAR32.43, MAR32.44).
- Golden: the zone boundaries 0.80 and 0.70 for Spearman and 0.09 and 0.12 for KS of `pla_zone`; identical series give `statistic = 1.0`, `metric = 0.0`, green.

### `riskvalidation.validation.market.desk_backtest`

```python
def desk_backtest(loss: np.ndarray, var: np.ndarray, alpha: float, model_id: str | None = None, basis: str = "HPL") -> TestResult: ...
```

- Test: test_id = "market.desk_backtest"; `segment = "alpha=<alpha>"`.
- Units: positive loss numbers (250,) of the desk on `basis` in `{"HPL", "APL"}` against the desk VaR at 99 or 97.5 percent; `statistic` the exception count; `metric` the limit (`desk_exception_limit`); `p_value` null; `n = 250`; `n_events` the count; `extras = {"basis": basis}`.
- Light: red when the count exceeds the limit (more than 12 at 0.01, more than 30 at 0.025; MAR32.18 to MAR32.19), otherwise green; there is no amber (the dossier states one limit); `not_evaluated` with fewer than 250 days.
- Invariants: `statistic = desk_exceptions(loss, var)`; `metric = desk_exception_limit(alpha)`; the light is monotone in the count. A C13 aggregate over replications is built by the bake from per-replication rows and is not a function of the engine.
- Golden: 12 exceptions at `alpha = 0.01` is green and 13 is red; 30 at `alpha = 0.025` is green and 31 is red.

## Open items for U8-E and the integrator

- UNVERIFIED details to read at the primary source before transcription: the age-weighted HS interpolation and ES rule (Boudoukh et al. 1998), the `(y)^-` convention and the Taylor (2019) ALD ES extension of CAViaR, the DQ regressor set, the GAS-FZ recursions (Patton, Ziegel and Chen 2019),
  the Weibull form of the duration test (Christoffersen and Pelletier 2004), the McNeil-Frey threshold fraction, the Zangari origin of Cornish-Fisher VaR, the primary Acerbi and Szekely text, and whether the desk test counts a missing value as an exception.
- Contract decisions D-1 to D-8 above (D-1 the exact two-sided p-value, D-2 the Bartlett HAC kernel, D-3 the empirical VaR and ES of a sample, D-4 FHS without resampling, D-5 the one-sided Du-Escanciano p-value, D-6 the Cornish-Fisher validity domain, D-7 the independence test at no exceedance, D-8 the minimum exceedances of the duration and McNeil-Frey tests) are the integrator's to amend before U8-E starts.
- Acceptance check of U8-P1 and U8-P2 (review F14): CI runs no pytest (ADR-0074), so the producer checks of `tests/contracts_u8/producer_checks.py` (leakage, span, window dates, counts, recomputed statistics, the variant id) run only in a local
  pytest run; `pytest tests/contracts_u8` green on the committed documents of `data/derived/C11` and `C13` is an acceptance check of those two units.
- The asset class of the calm 2004-06 window is not decided by the SDD or decision D2, so the schema accepts any of the four for that window and no other.
