# Engine operational risk API contract: `engine-oprisk-api` 1.0.0

Owner: U12-S (unit sizing `plans/contraste/units/U12-sizing.md`, CAOS_MANAGE). Implemented by U12-E in `riskvalidation.oprisk` and
`riskvalidation.validation.oprisk` (repository CAOS_RiskValidation); called by the C17 bake (U12-P). The tests of every function are
written by U12-E against this file: a function exists with exactly the signature below, and each golden value or invariant is a test.
Changing a signature, a unit or a golden value is a breaking change (a new major version of this contract).
Sources: dossier 05 (`wip/contraste/05-market-ccr-alm-liquidity-oprisk-stress-sota-2026-10-04.md`, section F: F.1 to F.6, and the
operational risk ladder and case O1 under "Implications for Contraste"), dossier 01 (`wip/contraste/01-basel-pillar1-pillar2-framework-2026-10-04.md`,
section F: OPE25), and Shevchenko, "Implementing loss distribution approach for operational risk" (arXiv 1008.1108, J. Operational Risk 5(2):3-40,
2010) as quoted in dossier 05 F.3; the product SDD section 4 gives the acceptance rows this contract serves and section 5 the case C17.

The engine computes; it states no compliance claim. Nothing here is a Basel requirement beyond what dossier 01 section F cites for OPE25, and the LDA is the
economic-capital and validation tool of dossier 05 F.1, never a Pillar 1 model. Collection thresholds, quantile levels and light parameters are policy
parameters the caller supplies or the function states. Every constant and golden value below is transcribed from the dossier line named on it, or is
recomputed from the dossier's formula by a test of the product (`tests/contracts_u12/test_u12_contracts.py`); an item the dossier marks UNVERIFIED is
marked UNVERIFIED here and is not silently decided.

## Conventions (all functions)

- Arrays are `numpy.ndarray` of `float64` (integers `int64`, flags `bool`). Shapes: `N` losses or histories, `Y` years, `T` thresholds, `P` scenario points,
  `G` points of a discretised grid.
- Money is a float in EUR (C17 is in EUR throughout: the LDCE calibration is in EUR); the currency code travels in the document (`currency`), never in a
  function, and the engine never converts between currencies. Frequencies are expected counts per year. Quantile levels are decimals (`0.999`). A tail index is
  the GPD shape `xi`, a decimal; the severity laws are described by a name and a parameter tuple in a fixed order:
  `"lognormal"` `(mu, sigma)`; `"weibull"` `(shape, scale)`; `"gpd"` `(xi, beta, location)` with `Y = X - location` generalised Pareto,
  `G(y) = 1 - (1 + xi y / beta)^(-1/xi)`, `xi > 0` (dossier 05 F.2); `"lognormal-gpd-splice"` `(mu, sigma, u, xi, beta, w)` the body-tail splice of dossier 05
  F.2 with the lognormal body below the splice threshold `u`, the GPD tail above it and the body weight `w = P(X <= u)`. The frequency laws are `"poisson"`
  `(lam,)`; `"negative-binomial"` `(r, q)` with `p_n = Gamma(n + r) / (n! Gamma(r)) q^r (1 - q)^n`; `"binomial"` `(m, q)` (the three laws of Shevchenko Table 1).
- **A tail index of 1 or more has no mean** (dossier 05 F.6 and F.4; Degen 2010; Chavez-Demoulin, Embrechts and Neslehova 2006). `severity_moment` returns `math.inf`
  for a moment that does not exist, `compound_poisson_moments` reports an infinite mean and a `nan` skewness when the variance is infinite, and
  `sla_var_mean_corrected` raises `ValueError`: no function returns a finite number for a mean-based quantity of an infinite-mean severity. The C17
  documents carry the same rule as `infinite_mean` and null mean-based fields with their reason.
- Every function is pure and deterministic (no hidden state, no I/O, inputs never mutated) and returns new arrays. The only randomness is
  `simulate_annual_losses`, which takes an explicit `seed` and uses `numpy.random.Generator(PCG64)` streams keyed by that seed. A fit is deterministic for the
  same inputs (the optimiser, its start and its tolerance are fixed by the implementation).
- Dataclasses are frozen. A function that cannot compute a value because data is missing raises `ValueError` with the reason, or (a validation function) returns
  the `not_evaluated` light with its reason in `notes` and `statistic`, `p_value` and `metric` all null; it never returns a placeholder number. Mass beyond a
  discretised grid is reported, never renormalised or extrapolated.
- The parameters of a light rule (`tol_green`, `tol_amber`, `dispersion_green`, `jump_amber`, ...) travel in the row's `extras["thresholds"]`, a mapping from
  the parameter name to its value, beside `alpha_amber` and `alpha_red`, which are null here: these tests are descriptive and carry no p-value.
- Zero spread: a sample has zero spread when its standard deviation is at most `1e-12 * max(1, m)` with `m` the largest absolute value it is computed from (a
  scale-aware float tolerance).
- Tolerance: every golden value states its own tolerance or is exact; a golden stated to six decimals holds to `5e-7`, to four decimals to `5e-5`.
- A validation function returns one `TestResult` of `riskvalidation`, serialised by `TestResult.to_dict()` (core/result.py) into a row that validates against
  `common/test-result` (the schema `docs/contracts/schemas/common/test-result.schema.json`): `test_id`, `model_id`, `segment`, `statistic`, `p_value`, `metric`,
  `h0`, `alternative`, `policy_version`, `alpha_amber`, `alpha_red`, `light`, `n`, `n_events`, `inputs_hash`, `reference`, `notes`, `extras`.

## How the documents use the engine

| Document block (schema) | Produced by |
|---|---|
| C17 `outputs.truth` (the true parameters and the true 99.9 percent annual loss quantile), `outputs.exceedance` | `aggregate.discretise_severity`, `panjer_recursion`, `fft_aggregate`, `quantile_from_pmf`, `exceedance_from_pmf`, `simulate_annual_losses`, `mc_quantile`, `sla.sla_var` |
| C17 `outputs.cells[*].capital.lda_lognormal`, `lda_lognormal_truncated`, `lda_splice` | `distributions.fit_severity`, `fit_frequency`, `rescale_frequency`, `fit_splice`, then `aggregate.*` |
| C17 `outputs.cells[*].capital.sla`, `sla_mean_corrected` | `sla.sla_var`, `sla_var_poisson_gpd`, `sla_var_mean_corrected` (null with its reason at a tail index of 1 or more) |
| C17 `outputs.cells[*].capital.scenario`, `outputs.scenario_influence`; models `scenarios` | `scenarios.*`, `validation.oprisk.scenario_influence` |
| C17 `outputs.cells[*].threshold_stability` | `distributions.tail_index_profile`, `validation.oprisk.threshold_stability` |
| C17 `outputs.bank`, `outputs.cells[*].sma`, `outputs.sma_response`; models `sma` | `sma.*`, `validation.oprisk.sma_ilm_response` |
| C17 `outputs.cells[*].aggregation_agreement`, models `aggregation` | `aggregate.panjer_recursion`, `fft_aggregate`, `validation.oprisk.benchmark_reproduction` |
| C17 `outputs.cells[*].capital.*.ratio_to_truth`, `iqr_over_truth` | `validation.oprisk.capital_stability` |
| C17 `tests` | `riskvalidation.validation.oprisk.*` (rows of `common/test-result`) |

The truth of a C17 document is the generator's: every loss it draws at or above its floor (`truth.severity.location_eur`), whatever the collection threshold. The
collection threshold only decides what a bank records; the LDA rungs estimate the full distribution from the recorded losses, so a rung that ignores the
truncation (`lda_lognormal`) is biased against the truth, which is the finding the case is built to show.

## Module `riskvalidation/oprisk/distributions.py`

Frequency and severity laws of dossier 05 F.2, their truncated versions above the collection threshold `H` with the frequency rescaled, and their maximum
likelihood fits. Truncation: internal data are collected above `H`, so the severity is fitted as `f(x) / (1 - F(H))` and the frequency rescaled,
`lam_full = lam_obs / (1 - F(H))`; ignoring this biases capital (Mignola and Ugoccioni 2007; Cope et al. 2009, dossier 05 F.2).

### `riskvalidation.oprisk.distributions.frequency_pmf`

```python
def frequency_pmf(law: str, params: Sequence[float], n_max: int) -> np.ndarray: ...
```

- Units: `law` in `{"poisson", "negative-binomial", "binomial"}`; `params` as in Conventions; `n_max >= 0`; the result `(n_max + 1,)` probabilities `p_0 .. p_{n_max}`
  (counts per year, dimensionless).
- Invariants: every `p_n >= 0` and their sum is at most 1 (the tail beyond `n_max` is not added); Poisson `p_n = exp(-lam) lam^n / n!`; the recursion `p_n = (a + b / n) p_{n-1}`
  holds with the `(a, b)` of `panjer_coefficients`; `ValueError` for `lam <= 0`, `r <= 0`, `q` outside (0, 1), `m` not a positive integer.
- Golden: Poisson(2): `[0.135335, 0.270671, 0.270671]`; negative binomial `(r = 2, q = 0.5)`: `[0.25, 0.25, 0.1875]`; binomial `(m = 2, q = 0.5)`: `[0.25, 0.5, 0.25]`.

### `riskvalidation.oprisk.distributions.severity_cdf`

```python
def severity_cdf(law: str, params: Sequence[float], x: np.ndarray) -> np.ndarray: ...
```

- Units: `x` `(N,)` EUR; the result `(N,)` probabilities; zero at and below the law's origin (0 for the lognormal and the Weibull, `location` for the GPD).
- Invariants: nondecreasing in `x`, tends to 1; for the splice `F(u) = w` and `F` is continuous at `u`; `ValueError` for a nonpositive scale, `sigma`, shape or `xi`, or `w` outside (0, 1).
- Golden: lognormal `(0, 2)`: `F(1) = 0.5`; `gpd (0.5, 100, 0)`: `F(100) = 1 - 1.5^(-2) = 0.555556`; Weibull `(1, 1)`: `F(1) = 0.632121`.

### `riskvalidation.oprisk.distributions.severity_ppf`

```python
def severity_ppf(law: str, params: Sequence[float], q: np.ndarray) -> np.ndarray: ...
```

- Units: `q` `(N,)` probabilities in [0, 1]; the result `(N,)` EUR; `q = 0` gives the origin and `q = 1` gives `math.inf`.
- Invariants: the inverse of `severity_cdf` (`cdf(ppf(q)) = q` to `1e-12` away from the ends); for the GPD `ppf(q) = location + beta / xi ((1 - q)^(-xi) - 1)`.
- Golden: `gpd (0.5, 100, 0)`: `ppf(0.99) = 200 (10 - 1) = 1800`; lognormal `(0, 2)`: `ppf(0.5) = 1`.

### `riskvalidation.oprisk.distributions.severity_moment`

```python
def severity_moment(law: str, params: Sequence[float], k: int) -> float: ...
```

- Units: the raw moment `E[X^k]` in EUR to the power `k`; `k >= 1`.
- Invariants: lognormal `exp(k mu + k^2 sigma^2 / 2)`; Weibull `scale^k Gamma(1 + k / shape)`; GPD `sum_j C(k, j) location^(k-j) E[Y^j]` with `E[Y^j] = beta^j j! / prod_{i=1..j} (1 - i xi)`
  finite exactly when `k xi < 1`, and `math.inf` otherwise (a tail index of 1 or more has no mean: `severity_moment("gpd", (xi, ...), 1)` is `inf` for `xi >= 1`); the splice sums the body
  and tail parts and is `inf` when the tail's is.
- Golden: lognormal `(0, 2)`, `k = 1`: `e^2 = 7.389056`; `gpd (0.25, 100, 0)`: `k = 1` gives `133.333333`, `k = 2` gives `53333.333333`; `gpd (1.0, 100, 0)`, `k = 1`: `inf`; Weibull `(2, 1)`, `k = 1`: `0.886227`.

### `riskvalidation.oprisk.distributions.truncated_severity_cdf`

```python
def truncated_severity_cdf(law: str, params: Sequence[float], x: np.ndarray, threshold: float) -> np.ndarray: ...
```

- Units: `x` `(N,)` EUR, `threshold` EUR (the collection threshold `H`); the result `(N,)` is `(F(x) - F(H)) / (1 - F(H))` for `x >= H` and 0 below; `ValueError` when `F(H) = 1`.
- Invariants: zero at `H`, nondecreasing, tends to 1; for the GPD with `H > location` it equals the GPD with `beta' = beta + xi (H - location)` and location `H` (threshold stability).
- Golden: `gpd (0.5, 100, 0)`, `H = 100`: `beta' = 150`, `truncated_cdf(250) = 1 - 1.5^(-2) = 0.555556`, equal to `(F(250) - F(100)) / (1 - F(100)) = (0.802469 - 0.555556) / 0.444444`.

### `riskvalidation.oprisk.distributions.rescale_frequency`

```python
def rescale_frequency(rate_observed: float, law: str, params: Sequence[float], threshold: float) -> float: ...
```

- Units: `rate_observed` recorded losses per year above the threshold; `threshold` EUR; the result losses per year of the full severity, `lam_full = lam_obs / (1 - F(H))` (dossier 05 F.2).
- Invariants: at least `rate_observed`; equal to it when `F(H) = 0`; `ValueError` for a negative rate or `F(H) = 1`.
- Golden: `gpd (0.5, 100, 0)`, `H = 100`, `rate_observed = 10`: `1 - F(H) = 0.444444`, `lam_full = 22.5`.

### `riskvalidation.oprisk.distributions.FrequencyFit`

```python
@dataclass(frozen=True)
class FrequencyFit:
    law: str
    params: tuple[float, ...]
    std_errors: tuple[float, ...]
    n_years: int
    loglik: float
```

- Units: `params` as in Conventions (`lam` is losses per year); `std_errors` the same length, from the observed information; `loglik` natural log.
- Invariants: frozen; `n_years >= 1`; `std_errors` are nonnegative.

### `riskvalidation.oprisk.distributions.fit_frequency`

```python
def fit_frequency(counts: np.ndarray, law: str = "poisson") -> FrequencyFit: ...
```

- Units: `counts` `(Y,)` integer losses per year (recorded, above the collection threshold); the fit is of the recorded frequency, to be rescaled by `rescale_frequency`.
- Invariants: Poisson `lam_hat = mean(counts)`, `se = sqrt(lam_hat / Y)`; the negative binomial needs a sample variance above the mean, otherwise `ValueError("underdispersed")` (the caller then uses Poisson);
  `Y < 2` or negative counts raise `ValueError`.
- Golden: `counts = [3, 5, 4]` gives `lam_hat = 4.0` and `se = 1.154701`.

### `riskvalidation.oprisk.distributions.SeverityFit`

```python
@dataclass(frozen=True)
class SeverityFit:
    law: str
    params: tuple[float, ...]
    std_errors: tuple[float, ...]
    threshold: float
    truncated: bool
    n: int
    loglik: float
    converged: bool
```

- Units: `params` as in Conventions (EUR for scales and locations); `threshold` EUR; `loglik` natural log.
- Invariants: frozen; `std_errors` from the inverse observed information (a parameter on a boundary or a singular information matrix gives `nan` and `converged = False`, never a silent number).

### `riskvalidation.oprisk.distributions.fit_severity`

```python
def fit_severity(law: str, losses: np.ndarray, collection_threshold: float = 0.0, truncated: bool = True) -> SeverityFit: ...
```

- Units: `losses` `(N,)` EUR, each at or above `collection_threshold` (otherwise `ValueError`: the loss data rules reject below-threshold rows, SDD section 3); law in `{"lognormal", "weibull", "gpd"}`; for `"gpd"` the
  location of the fit is `collection_threshold`.
- Invariants: with `truncated = True` the log-likelihood is `sum ln f(x_i) - N ln(1 - F(H))` (dossier 05 F.2); with `truncated = False` it is `sum ln f(x_i)` and the threshold is ignored (rung 1, the biased baseline); the
  untruncated lognormal fit is closed form, `mu = mean(ln x)`, `sigma = sqrt(mean((ln x - mu)^2))` (divisor `N`); a truncated GPD fit recovers `(xi, beta')` of the excesses over `H`; deterministic.
- Golden: `losses = [1, e, e^2]`, lognormal untruncated: `mu = 1.0`, `sigma = 0.816497`, `std_errors = (0.471405, ...)` (`sigma / sqrt(N)` for `mu`).

### `riskvalidation.oprisk.distributions.SpliceFit`

```python
@dataclass(frozen=True)
class SpliceFit:
    params: tuple[float, ...]
    std_errors: tuple[float, ...]
    collection_threshold: float
    splice_threshold: float
    weight: float
    n_body: int
    n_tail: int
    converged: bool
```

- Units: `params` is `(mu, sigma, u, xi, beta, w)` of the `"lognormal-gpd-splice"` law; `weight = w`; thresholds EUR.
- Invariants: frozen; `params[2] == splice_threshold` and `params[5] == weight`; `n_body + n_tail` is the number of recorded losses.

### `riskvalidation.oprisk.distributions.fit_splice`

```python
def fit_splice(losses: np.ndarray, collection_threshold: float, splice_threshold: float, min_tail: int = 10) -> SpliceFit: ...
```

- Units: `losses` `(N,)` EUR at or above `collection_threshold`; `splice_threshold > collection_threshold`; the body is the lognormal truncated to `[H, u]` fitted by maximum likelihood to the losses at or below `u`, the tail is the
  GPD of the excesses over `u`.
- Invariants: the body weight follows from the observed tail share `t = n_tail / N` (the share of recorded losses above `u`) and `c = F_b(H) / F_b(u)` (the body lognormal's mass below `H` over its mass below `u`):
  `w = (1 - t) / (1 - t c)`, so that `(1 - w) / (1 - w c) = t`, derived here from the definitions of dossier 05 F.2 (`P(X > u) = 1 - w`, `P(X >= H) = 1 - w c`); `ValueError` when `n_tail < min_tail` or when no
  loss lies at or below `u`; deterministic.
- Golden: `t = 0.2`, `c = 0.5` gives `w = 0.888889`.

### `riskvalidation.oprisk.distributions.TailProfile`

```python
@dataclass(frozen=True)
class TailProfile:
    thresholds: np.ndarray
    n_exceedances: np.ndarray
    xi: np.ndarray
    xi_se: np.ndarray
    beta: np.ndarray
    converged: np.ndarray
```

- Units: arrays of shape `(T,)`; `thresholds` EUR; `n_exceedances` integer; `xi` the fitted GPD tail index (decimal) of the excesses over each threshold; `beta` EUR.
- Invariants: frozen; a threshold with fewer exceedances than the minimum has `xi`, `xi_se` and `beta` equal to `nan` and `converged` false (it is listed, never dropped).

### `riskvalidation.oprisk.distributions.tail_index_profile`

```python
def tail_index_profile(losses: np.ndarray, thresholds: np.ndarray, min_exceedances: int = 10) -> TailProfile: ...
```

- Units: `losses` `(N,)` EUR; `thresholds` `(T,)` EUR, strictly increasing (otherwise `ValueError`); the GPD is fitted by maximum likelihood to the excesses `x - u` of the losses above each `u` (the threshold-stability plot of
  dossier 05 F.3 and the ladder).
- Invariants: `n_exceedances` is nonincreasing along the thresholds; for data that are exactly GPD the modified scale `beta_hat(u) - xi_hat(u) u` is constant in expectation (threshold stability); deterministic.

## Module `riskvalidation/oprisk/aggregate.py`

The compound annual loss `Z = sum_{i=1..N} X_i` (dossier 05 F.2) by Monte Carlo, Panjer recursion and FFT, and the quantities read from it (dossier 05 F.3, Shevchenko 2010 sections 5 and 6).
Panjer recursion (Panjer 1981) with a discretised severity `f_j = P(X = j Delta)` and a frequency of the `(a, b, 0)` class, `p_n = (a + b / n) p_{n-1}`:
`h_n = 1 / (1 - a f_0) sum_{j=1..n} (a + b j / n) f_j h_{n-j}`, `h_0 = sum_k f_0^k p_k` (Shevchenko Theorem 5.2, eq. 36; Table 1 for `a`, `b`, `h_0`).
**Benchmark** (Shevchenko Example 9.4 and Tables 2 to 4, quoted in dossier 05 F.3 and re-read in the primary text, arXiv 1008.1108, for the review of this contract): Poisson(100) with LN(0, 2) severity has
`E[Z] = 738.9056`, `Var[Z] = 298095.7987`, skewness `40.3428`. Panjer with the central-difference discretisation of step 1 (`f_0 = F(0.5)`, `f_j = F(j + 0.5) - F(j - 0.5)`, zero-based indices, eq. 37) gives, in Shevchenko
Table 2 (verified, p. 37) and in an independent recomputation (the product test `test_m1_the_benchmark_indices_are_those_of_shevchenko_table_2`), `H_5847 = 0.998999329` (0.998999329180), `H_5848 = 0.998999773` and
`H_5849 = 0.999000217` (0.999000217026): the index of the table is the zero-based index of the recursion (the table's `n`), and the smallest index with `H_n >= 0.999` is 5849, so the 99.9 percent quantile at step 1 is 5849 (Table 3).
Dossier 05 F.3 printed the row-5847 value against the label 5849 (an erratum, corrected there); the contract carries the table's values. The forward bound of Table 4 (eq. 38, `f_j = F(j + 1) - F(j)`) gives
`H^U_5811 = 0.998999719 < 0.999 <= H^U_5812 = 0.999000163`, so its quantile is 5812 (the paper's text says 5811; if the engine adds the bounds as goldens, the table rows rule). The Monte Carlo estimate is of the continuous quantile,
5853.1 (Table 3 at step 0.0625 gives 5853.06; Table 7: `H(5853.1) = 0.9990000`), not of the discretised 5849 to 5850.

### `riskvalidation.oprisk.aggregate.panjer_coefficients`

```python
def panjer_coefficients(law: str, params: Sequence[float]) -> tuple[float, float]: ...
```

- Units: dimensionless `(a, b)` of Shevchenko Table 1: Poisson `(0, lam)`; negative binomial `(r, q)`: `(1 - q, (1 - q)(r - 1))`; binomial `(m, q)`: `(-q / (1 - q), q (m + 1) / (1 - q))`.
- Golden: Poisson(100): `(0, 100)`; negative binomial `(2, 0.5)`: `(0.5, 0.5)`; binomial `(2, 0.5)`: `(-1.0, 3.0)`.

### `riskvalidation.oprisk.aggregate.panjer_h0`

```python
def panjer_h0(law: str, params: Sequence[float], f0: float) -> float: ...
```

- Units: `f0` the severity mass at 0 of the discretisation, in [0, 1); the result `h_0 = P(Z = 0)`: Poisson `exp(lam (f_0 - 1))`; negative binomial `(1 + (1 - f_0)(1 - q) / q)^(-r)`; binomial `(1 + q (f_0 - 1))^m` (Shevchenko Table 1).
- Invariants: equals `sum_k f_0^k p_k` (the probability generating function of the frequency at `f_0`); `ValueError` for `f0` outside [0, 1).
- Golden: with `f_0 = 0.5`: Poisson(2) gives `0.367879`; negative binomial `(2, 0.5)` gives `0.444444`; binomial `(2, 0.5)` gives `0.5625`; the benchmark, Poisson(100) with `f_0 = F_LN(0,2)(0.5) = 0.364456`, gives `2.504194e-28`.

### `riskvalidation.oprisk.aggregate.discretise_severity`

```python
def discretise_severity(law: str, params: Sequence[float], step: float, n_points: int, method: str = "central") -> np.ndarray: ...
```

- Units: `step` EUR per grid cell; `n_points >= 2`; the result `(n_points,)` masses `f_j` for the loss `j * step`. `method` in `{"central", "forward", "backward"}`: central `f_0 = F(step / 2)`, `f_j = F((j + 1/2) step) - F((j - 1/2) step)`
  (the benchmark's); forward `f_j = F((j + 1) step) - F(j step)` (an upper bound); backward `f_0 = 0`, `f_j = F(j step) - F((j - 1) step)` (a lower bound).
- Invariants: every `f_j >= 0`; the sum is at most 1 and the missing mass `1 - sum` is the tail beyond the grid (the caller reads it; the function never renormalises).
- Golden: LN(0, 2), `step = 1`, central: `f_0 = 0.364456`, `f_1 = 0.215872`, `f_2 = 0.096248` (Shevchenko Table 2: 0.364455845, 0.215872117, 0.096248034); forward: the cumulative sums of Poisson(100) are `0.998999719` at zero-based index 5811 and `0.999000163` at 5812 (Table 4 rows).

### `riskvalidation.oprisk.aggregate.panjer_recursion`

```python
def panjer_recursion(law: str, params: Sequence[float], f: np.ndarray) -> np.ndarray: ...
```

- Units: `law`, `params` the frequency; `f` `(G,)` the discretised severity; the result `(G,)` the probabilities `h_n = P(Z = n * step)`, `n = 0 .. G - 1` (the step is the caller's).
- Invariants: `h_0 = panjer_h0(law, params, f[0])`; the recursion above for `n >= 1`; the sum of `h` is at most 1; `ValueError` when `a f_0 = 1` or the law is not in the `(a, b, 0)` class.
- Golden: Poisson(2) with `f = [0.5, 0.5, 0, ...]` (a severity of 0 or 1 with equal probability thins the count): `Z` is Poisson(1), `h = [0.367879, 0.367879, 0.183940, ...]`. The benchmark: Poisson(100), LN(0, 2), `step = 1`, `G >= 5850`:
  `H_5847 = sum_{n <= 5847} h_n = 0.998999329180`, `H_5848 = 0.998999773241`, `H_5849 = 0.999000217026` (Shevchenko Table 2, tolerance `5e-10`); see the benchmark paragraph above.

### `riskvalidation.oprisk.aggregate.fft_aggregate`

```python
def fft_aggregate(law: str, params: Sequence[float], f: np.ndarray, padding_factor: int = 2, tilt: float = 0.0) -> np.ndarray: ...
```

- Units: as `panjer_recursion`; `padding_factor >= 1` (the transform length is `padding_factor * G` rounded up to a power of two; zero padding guards against aliasing); `tilt >= 0` the exponential tilting parameter `theta`
  (the severity is multiplied by `exp(-theta j)` before the transform and the result by `exp(theta n)` after, Shevchenko section 6.2).
- Invariants: `h_hat = psi(f_hat)` with the frequency's probability generating function (Poisson `exp(lam (f_hat - 1))`; negative binomial `(q / (1 - (1 - q) f_hat))^r`; binomial `(1 + q (f_hat - 1))^m`); the result is the first `G`
  entries of the inverse transform, real and clipped at 0 only where a value is below `-1e-12` (a larger negative value raises `ValueError`: aliasing); agrees with `panjer_recursion` to `1e-9` per entry on the benchmark.
- Golden: Poisson(2) with `f = [0.5, 0.5, 0, ...]`: `h = [0.367879, 0.367879, 0.183940, ...]` to `1e-12`; the benchmark cumulative sums of `panjer_recursion` to `5e-10`.

### `riskvalidation.oprisk.aggregate.AnnualLossSample`

```python
@dataclass(frozen=True)
class AnnualLossSample:
    losses: np.ndarray
    n_years: int
    seed: int
```

- Units: `losses` `(n_years,)` the simulated annual loss per year in EUR; `seed` the seed it was drawn from.
- Invariants: frozen; `losses.shape == (n_years,)`; every entry nonnegative.

### `riskvalidation.oprisk.aggregate.simulate_annual_losses`

```python
def simulate_annual_losses(freq_law: str, freq_params: Sequence[float], sev_law: str, sev_params: Sequence[float],
                           n_years: int, seed: int, chunk_years: int = 1_000_000) -> AnnualLossSample: ...
```

- Units: `n_years >= 1`; the annual count is drawn, then that many severities, summed (dossier 05 F.3); `chunk_years` bounds the memory of one block and is not part of the result.
- Invariants: deterministic for `(n_years, seed)` and independent of `chunk_years`; the sample mean is within 4 standard errors of `lam E[X]` when the variance is finite; the per-year counts follow the frequency law.
- Golden: Poisson(100) with LN(0, 2), `n_years = 1_000_000`: `|mean - 738.9056| <= 2.184` (4 standard errors, `sqrt(298095.7987 / 10^6) = 0.545985`) for any seed.

### `riskvalidation.oprisk.aggregate.mc_quantile`

```python
def mc_quantile(losses: np.ndarray, level: float) -> tuple[float, float]: ...
```

- Units: `losses` `(n,)` EUR; `level` in (0, 1); the result `(quantile, standard_error)` in EUR. The quantile is the `ceil(n * level)`-th order statistic (1-based). The standard error is half the distance between the order statistics at
  `ceil(n * level + sqrt(n * level * (1 - level)))` and `floor(n * level - sqrt(n * level * (1 - level)))` (indices clipped to [1, n]), a one-standard-deviation binomial interval (dossier 05 F.3: the quantile error decays as `O(K^(-1/2))`
  in the number of years `K` and needs very large `K` at 99.9 percent).
- Golden: `losses = 1, 2, ..., 1000`: `level = 0.5` gives `(500, 16.0)` (order statistics 516 and 484); `level = 0.999` gives `(999, 1.0)` (order statistics 1000 and 998).

### `riskvalidation.oprisk.aggregate.quantile_from_pmf`

```python
def quantile_from_pmf(h: np.ndarray, step: float, level: float) -> float: ...
```

- Units: `h` `(G,)` probabilities, `step` EUR; the result is `n * step` for the smallest zero-based `n` whose cumulative sum is at least `level` (the VaR at that level).
- Invariants: `ValueError` when the cumulative sum never reaches `level` (mass beyond the grid): the function never extrapolates.
- Golden: `h = [0.5, 0.3, 0.2]`, `step = 10`: `level = 0.75` gives `10.0`, `level = 0.9` gives `20.0`; the benchmark gives `5849.0` at `level = 0.999`.

### `riskvalidation.oprisk.aggregate.es_from_pmf`

```python
def es_from_pmf(h: np.ndarray, step: float, level: float, max_missing_share: float = 1e-3) -> float: ...
```

- Units: as `quantile_from_pmf`; the expected shortfall `ES = (E[Z; Z > q] + q (P(Z <= q) - level)) / (1 - level)` with `q = quantile_from_pmf(h, step, level)`; `max_missing_share` a share of the tail `1 - level`.
- Invariants: **the grid must carry the tail: `ValueError` when the mass beyond the grid, `1 - sum(h)`, exceeds `max_missing_share * (1 - level)`** (default `1e-3 * (1 - level)`), because an expected shortfall read off a grid that ends before the tail is too small
  and can fall below its own VaR; the guard is not a test of the severity: the mass beyond any grid of a proper distribution falls to 0 as the grid end grows, so a coarse grid of an infinite-mean tail passes it (GPD(1.1, 100, 0) with Poisson(10), step 1e6 and 32768 points has missing mass 1.66e-7, below the tolerance, and gives a finite ES of 3.17e7).
  A finite ES or mean is therefore **never computed for a severity without a finite mean (tail index 1 or more), and that is checked on the severity before the ES**: the caller (the C17 bake) gates on `severity_moment(law, params, 1)` being finite, and writes the ES as null with the reason `infinite mean` otherwise. No new function is needed. When it returns, `ES >= VaR` and `ES` equals the VaR for a point mass; `ValueError` as `quantile_from_pmf` otherwise.
- Golden: `h = [0.5, 0.3, 0.2]`, `step = 10`, `level = 0.75`: `q = 10`, `E[Z; Z > q] = 4`, `ES = (4 + 10 (0.8 - 0.75)) / 0.25 = 18.0`. The benchmark pmf on a grid of 6000 points (`step = 1`, `level = 0.999`) **raises `ValueError`**: its missing mass is
  `0.000936`, far above the tolerance `1e-6`, and the grid-only reading would give `ES = 377.8`, below the VaR 5849. A Pareto-type tail with tail index 1.1 gives a finite grid-only ES that grows with the grid (818.6 at 4000 points, 1073.6 at 8000 in the review of U12-S), and the coarse grid above passes the guard (the engine review of U12-E): only the severity check refuses it.

### `riskvalidation.oprisk.aggregate.exceedance_from_pmf`

```python
def exceedance_from_pmf(h: np.ndarray, step: float) -> tuple[np.ndarray, np.ndarray]: ...
```

- Units: the result `(x, sf)` of shape `(G,)`: `x_n = n * step` in EUR and `sf_n = P(Z > x_n) = 1 - cumsum(h)_n` clipped at 0 (the exceedance curve of the C17 `exceedance` block).
- Invariants: `sf` is nonincreasing in [0, 1].
- Golden: `h = [0.5, 0.3, 0.2]`: `sf = [0.5, 0.2, 0.0]`.

### `riskvalidation.oprisk.aggregate.CompoundMoments`

```python
@dataclass(frozen=True)
class CompoundMoments:
    mean: float
    variance: float
    skewness: float
```

- Units: `mean` EUR per year, `variance` EUR squared, `skewness` dimensionless.
- Invariants: frozen; `mean = inf` when the severity mean is infinite, `variance = inf` when its second moment is, and `skewness = nan` when the variance is infinite.

### `riskvalidation.oprisk.aggregate.compound_poisson_moments`

```python
def compound_poisson_moments(lam: float, sev_law: str, sev_params: Sequence[float]) -> CompoundMoments: ...
```

- Units: `lam` losses per year; the compound Poisson moments `E[Z] = lam E[X]`, `Var[Z] = lam E[X^2]`, skewness `lam E[X^3] / Var[Z]^(3/2)`, from `severity_moment`.
- Golden: Poisson(100), LN(0, 2) (Shevchenko Example 9.4, dossier 05 F.3): `E[Z] = 738.9056`, `Var[Z] = 298095.7987`, skewness `40.3428` (the mean and the variance to `5e-5`, the skewness to `1e-4`: the dossier's 40.3428 is the exact `e^6 / 10 = 40.342879` cut at four decimals; the exact values are `100 e^2`, `100 e^8` and `e^6 / 10`).

## Module `riskvalidation/oprisk/sla.py`

The single loss approximation (SLA) of dossier 05 F.4: for a subexponential severity `F` and a frequency with `sum_n (1 + eps)^n P(N = n) < infinity`, `1 - H(z) ~ E[N] (1 - F(z))` as `z -> infinity` (Embrechts, Kluppelberg and Mikosch 1997,
Theorem 1.3.9, as cited by Shevchenko eq. 69), hence `VaR_alpha[Z] ~ F^{-1}(1 - (1 - alpha) / E[N])` (Shevchenko eq. 70; Bocker and Kluppelberg 2005). Shevchenko shows that it converges for heavy tails and is poor for LN(0, 1) at practical quantiles.

### `riskvalidation.oprisk.sla.sla_var`

```python
def sla_var(frequency_mean: float, sev_law: str, sev_params: Sequence[float], level: float) -> float: ...
```

- Units: `frequency_mean` `E[N]` losses per year; `level` in (0, 1); the result EUR: `F^{-1}(1 - (1 - level) / E[N])` (eq. 70).
- Invariants: `ValueError` when `E[N] <= 1 - level` (the argument of `F^{-1}` would not be in (0, 1)); nondecreasing in `E[N]` and in `level`.
- Golden: `gpd (0.5, 100, 0)`, `E[N] = 10`, `level = 0.99`: `6124.555320` (equal to `sla_var_poisson_gpd`).

### `riskvalidation.oprisk.sla.sla_var_poisson_gpd`

```python
def sla_var_poisson_gpd(lam: float, xi: float, beta: float, level: float, location: float = 0.0) -> float: ...
```

- Units: `lam` losses per year, `xi > 0` the tail index (decimal), `beta` EUR, `location` EUR; the result EUR: `location + beta / xi ((lam / (1 - level))^xi - 1)` (dossier 05 F.4: it scales like `lam^xi`).
- Invariants: equals `sla_var(lam, "gpd", (xi, beta, location), level)`; `ValueError` for `xi <= 0` or `beta <= 0`.
- Golden: `lam = 10`, `xi = 0.5`, `beta = 100`, `level = 0.99`: `200 (31.622777 - 1) = 6124.555320`. Dossier 05 F.6 (reproduced, review of this contract and decision D5): a GPD for the excesses over EUR 20,000 fitted by least squares on the log of the excess
  quantiles to the four LDCE median percentiles gives `xi = 0.96378` and `beta = 22349.4`, with the fitted quantiles 27409 / 42039 / 85025 / 412906, and at `lam = 41` (0.82 x 50), `location = 20000`, `level = 0.999` an SLA of **647.1 million** (the dossier's EUR 647 million).
  Rounding `xi` to 0.96 and `beta` to 22,350 gives 624.1 million: that is the sensitivity of the SLA to `xi` that dossier 05 F.6 warns of, not a different result.

### `riskvalidation.oprisk.sla.SlaResult`

```python
@dataclass(frozen=True)
class SlaResult:
    level: float
    var_first_order: float
    mean_correction: float
    var: float
    status: str
```

- Units: all money fields EUR; `var = var_first_order + mean_correction`; `status` is the string `"UNVERIFIED"`.
- Invariants: frozen; `status == "UNVERIFIED"` always: the mean-corrected form is UNVERIFIED in dossier 05 F.4 and the result says so (the C17 document labels the rung `UNVERIFIED` too).

### `riskvalidation.oprisk.sla.sla_var_mean_corrected`

```python
def sla_var_mean_corrected(frequency_mean: float, sev_law: str, sev_params: Sequence[float], level: float) -> SlaResult: ...
```

- Units: as `sla_var`; the result adds `mean_correction = E[N] E[X]`: `F^{-1}(1 - (1 - level) / E[N]) + E[N] E[X]`. This is the "commonly quoted corrected form" of dossier 05 F.4, which was **not checked** against Bocker and Sprittulla,
  "Operational VaR: meaningful means" (Risk 2006) or Degen (J. Operational Risk 5(4):3-17, 2010): UNVERIFIED. The function implements it only because the C17 ladder asks for the rung (rung 5 "SLA with and without correction"), labels the result
  UNVERIFIED, and the check against the primary text is an open item (a changed form is a new minor version of this contract).
- Invariants: **raises `ValueError` when the severity mean is infinite (a GPD tail index of 1 or more): the correction does not exist** (dossier 05, ladder failure modes: "`xi >= 1` (infinite mean, SLA correction invalid)"); the C17 bake then writes the rung as null with the reason `infinite mean`;
  `var >= var_first_order`.
- Golden: `E[N] = 10`, `gpd (0.5, 100, 0)`, `level = 0.99`: `E[X] = 200`, `mean_correction = 2000`, `var = 8124.555320`, `status = "UNVERIFIED"`; `gpd (1.0, 100, 0)` and `gpd (1.1, 100, 0)` raise `ValueError`.

## Module `riskvalidation/oprisk/scenarios.py`

Scenario analysis and its combination with loss data (dossier 05 F.5): scenarios are expert estimates of the frequency and severity of rare large events; the combination methods are (i) scenario points as pseudo-observations appended to the tail sample, (ii) the body
fitted to internal data and the tail to scenario-implied quantiles, (iii) Bayesian credibility with the scenarios as the prior for the GPD tail parameters (Shevchenko and Wuthrich 2006, J. Operational Risk 1(3):3-26). Validation must test the sensitivity of
capital to each scenario point (the scenario influence function).

### `riskvalidation.oprisk.scenarios.ScenarioPoint`

```python
@dataclass(frozen=True)
class ScenarioPoint:
    scenario_id: str
    kind: str
    loss: float
    exceedance_frequency: float
```

- Units: `kind` in `{"percentile", "individual"}` (the template of the 2008 LDCE scenarios, dossier 05 F.5, restricted to the two the C17 document carries); `loss` EUR; `exceedance_frequency` the expected number of losses of at least `loss` per year (one in ten years is `0.1`).
- Invariants: frozen; `loss > 0`, `exceedance_frequency > 0`.

### `riskvalidation.oprisk.scenarios.scenario_pseudo_observations`

```python
def scenario_pseudo_observations(points: Sequence[ScenarioPoint], n_years: float) -> tuple[np.ndarray, np.ndarray]: ...
```

- Units: the result `(losses, weights)`, each `(P,)`: the loss of each point in EUR and its pseudo-count `exceedance_frequency * n_years` (method (i)).
- Golden: points `(loss 100, f 0.1)` and `(loss 1000, f 0.01)` with `n_years = 10` give `weights = [1.0, 0.1]`.

### `riskvalidation.oprisk.scenarios.fit_tail_to_scenarios`

```python
def fit_tail_to_scenarios(points: Sequence[ScenarioPoint], threshold: float, frequency_above_threshold: float) -> SeverityFit: ...
```

- Units: `threshold` EUR; `frequency_above_threshold` losses per year above `threshold`; each point implies `P(X > loss | X > threshold) = exceedance_frequency / frequency_above_threshold`, i.e. the conditional quantile level `p = 1 - exceedance_frequency / frequency_above_threshold`;
  the result is a `"gpd"` `SeverityFit` with location `threshold` (method (ii)), fitted by least squares on the log excess quantiles: it minimises `sum_s (ln(q_model(p_s) - threshold) - ln(loss_s - threshold))^2`, the objective with which dossier 05 F.6 fits the LDCE percentiles.
- Invariants: at least two points with distinct losses (`ValueError` otherwise); exact when the points lie on a GPD (the fit then has zero residual); `ValueError` when a point's conditional probability is not in (0, 1) or a loss is not above `threshold`.
- Golden: `gpd (0.5, 100, 0)` has the tail function `(1 + x / 200)^(-2)`; the points `x = 200` (`S = 0.25`) and `x = 1800` (`S = 0.01`) with `threshold = 0` and `frequency_above_threshold = 10` (so `exceedance_frequency = 2.5` and `0.1`) give `xi = 0.5`, `beta = 100`.

### `riskvalidation.oprisk.scenarios.GammaPrior`

```python
@dataclass(frozen=True)
class GammaPrior:
    shape: float
    rate: float
    mean: float
    interval: tuple[float, float]
    interval_level: float
    kind: str
```

- Units: a Gamma prior on the Pareto shape `alpha = 1 / xi` (dimensionless; `xi` the tail index); `shape` and `rate` the Gamma shape and rate (`mean = shape / rate`); `interval` the expert interval of `alpha`; `interval_level` its probability mass; `kind` the string `"unrestricted-gamma-on-pareto-shape"`.
- Invariants: frozen; `mean = shape / rate`; `kind` is always `"unrestricted-gamma-on-pareto-shape"` and the C17 documents repeat it (decision D4: Shevchenko and Wuthrich (2006) restrict the prior to `alpha` above 1, a finite mean, which would exclude the true value of the tail index 1.1 variant, `alpha = 0.909`; this contract uses the unrestricted prior and states it on every result).

### `riskvalidation.oprisk.scenarios.gamma_prior_from_mean_interval`

```python
def gamma_prior_from_mean_interval(mean: float, lower: float, upper: float, interval_level: float = 0.9) -> GammaPrior: ...
```

- Units: `mean`, `lower`, `upper` are values of `alpha` with `0 < lower < mean < upper`; the Gamma `(shape, rate = shape / mean)` whose probability of `[lower, upper]` is `interval_level` (Shevchenko and Wuthrich 2006, section 4.3: the prior from an expert's mean and interval probability), found by bracketed root finding on the shape.
- Invariants: `ValueError` when `mean` is not inside the interval or no shape in `[1e-3, 1e6]` gives the mass; `GammaPrior.mean == mean` to `1e-12`.
- Golden: `mean = 1`, `lower = -ln 0.95 = 0.051293`, `upper = -ln 0.05 = 2.995732`, `interval_level = 0.9`: `shape = 1`, `rate = 1` (the exponential: its mass between its 5th and 95th percentiles is 0.9), to `1e-6`.

### `riskvalidation.oprisk.scenarios.gamma_prior_from_scenarios`

```python
def gamma_prior_from_scenarios(points: Sequence[ScenarioPoint], threshold: float, frequency_above_threshold: float, basis_years: float,
                               n_bootstrap: int = 1000, seed: int = 0, interval_level: float = 0.9) -> GammaPrior: ...
```

- Units: the mapping of the C17 scenario points to the expert input of Shevchenko and Wuthrich (decision D4): (1) `fit_tail_to_scenarios` gives a GPD (least squares on the log quantiles, as dossier 05 F.6 does for the LDCE percentiles) with tail index `xi_s`, and `alpha_s = 1 / xi_s` is the prior mean; (2) a parametric bootstrap gives the expert
  interval: each exceedance frequency is redrawn as `k / basis_years` with `k` Poisson with mean `exceedance_frequency * basis_years` (a count of 0 is replaced by 0.5), the GPD is refitted, and the 5th and 95th percentiles of `alpha` over `n_bootstrap` replications (`numpy.random.Generator(PCG64(seed))`) form the interval
  of mass `interval_level` (90 percent); (3) `gamma_prior_from_mean_interval` solves the Gamma shape and rate. `basis_years` is the number of years of experience each scenario frequency is worth (a policy parameter of the caller; the contract fixes the mechanism, not its value).
- Invariants: deterministic for the same `seed`; `mean = alpha_s`; precondition `exceedance_frequency * basis_years >= 1` for every point (otherwise most redraws are the replaced count 0.5 and the interval is not a statistic); a larger `basis_years` gives a narrower interval and a larger Gamma shape. **A bootstrap refit that reaches the
  search bound of the least squares (the tail index at its lower bound 1e-3, i.e. `alpha = 1000`, or at its upper bound) is a stated failure, never a statistic**: the function raises `ValueError` naming the bound (an interval end of `1000` is the bound, not an estimate), and raises ValueError when the interval does not contain `alpha_s`. The C17 bake then writes the scenario rung as null with its reason
  (the `scenario` member of a cell is null with its reason, `c17OptionalCapital`), or the test as `not_evaluated`; `ValueError` as `fit_tail_to_scenarios` and `gamma_prior_from_mean_interval` otherwise. The prior is never truncated to `alpha` above 1.

### `riskvalidation.oprisk.scenarios.CredibilityFit`

```python
@dataclass(frozen=True)
class CredibilityFit:
    prior: GammaPrior
    posterior_shape: float
    posterior_rate: float
    alpha_mean: float
    alpha_mle: float | None
    credibility_weight: float
    xi: float
    beta: float
    location: float
    infinite_mean: bool
    n: int
```

- Units: `alpha_mean` the posterior mean of the Pareto shape (dimensionless); `alpha_mle = n / sum ln(x_i / L)` or `None` when `n = 0`; `credibility_weight = w = sum ln(x_i / L) / (sum ln(x_i / L) + rate)` (Shevchenko and Wuthrich eq. 25); `xi = 1 / alpha_mean`, `beta = xi L`, `location = L` EUR, the GPD that is
  the one-parameter Pareto with shape `alpha_mean` above the threshold `L`; `infinite_mean` is `alpha_mean <= 1` (a tail index of 1 or more); `n` the number of excesses.
- Invariants: frozen; `alpha_mean = w alpha_mle + (1 - w) prior.mean`.

### `riskvalidation.oprisk.scenarios.credibility_pareto`

```python
def credibility_pareto(prior: GammaPrior, losses: np.ndarray, threshold: float) -> CredibilityFit: ...
```

- Units: `losses` `(N,)` EUR, each at or above `threshold` `L` (the tail data); the one-parameter Pareto `f(x | alpha) = (alpha / L) (x / L)^(-alpha - 1)` for `x >= L` with the Gamma(`shape`, `rate`) prior on `alpha` has the Gamma posterior (Shevchenko and Wuthrich 2006, section 3.3,
  eqs. 21 to 25): shape `shape + N`, rate `rate + sum ln(x_i / L)` (eq. 24), posterior mean `(shape + N) / (rate + sum ln(x_i / L))`, the credibility weighting of the maximum likelihood estimate `N / sum ln(x_i / L)` and the prior mean (eq. 25).
- Invariants: `N = 0` returns the prior (`alpha_mean = prior.mean`, `credibility_weight = 0`, `alpha_mle = None`); as `N` grows `credibility_weight` tends to 1 and `alpha_mean` to the maximum likelihood estimate; the prior is unrestricted, so `alpha_mean` may be 1 or below and then `infinite_mean` is true and no
  mean-based number follows (`sla_var_mean_corrected` raises); `ValueError` when a loss is below `threshold`, or `sum ln(x_i / L) = 0` with `N > 0` (all losses equal to `L`).
- Golden: prior Gamma(shape 2, rate 1) (mean 2), `L = 1`, `losses = [e, e, e]` (`sum ln(x / L) = 3`): posterior Gamma(5, 4), `alpha_mean = 1.25 = 0.75 x 1 + 0.25 x 2` with `w = 0.75` and `alpha_mle = 1`, posterior standard deviation `sqrt(5) / 4 = 0.559017`, `xi = 0.8`, `beta = 0.8`, `location = 1`, `infinite_mean = False`.

### `riskvalidation.oprisk.scenarios.scenario_influence`

```python
def scenario_influence(points: Sequence[ScenarioPoint], capital_fn: Callable[[Sequence[ScenarioPoint]], float]) -> np.ndarray: ...
```

- Units: `capital_fn` maps a set of scenario points to the 99.9 percent capital in EUR (the caller closes over the losses, the threshold and the prior weight); the result `(P,)` of `influence_i = (capital(all) - capital(all without i)) / capital(all)`, dimensionless
  (the `influence` of the C17 `scenario_influence` block).
- Invariants: `ValueError` when `capital(all) <= 0`; a point whose removal leaves the capital unchanged has influence 0; the function calls `capital_fn` `P + 1` times.
- Golden: `capital_fn(points) = sum(loss * exceedance_frequency)` for the points `(100, 0.1)`, `(1000, 0.01)`, `(50, 1.0)`: `capital(all) = 70`, `influence = [0.142857, 0.142857, 0.714286]`.

## Module `riskvalidation/oprisk/sma.py`

The Basel III standardised approach of OPE25 (dossier 01 section F; source OPE25 in force 2023-01-01, published 2024-07-05; the version in force 2027-01-01 only rewords OPE25.10 and OPE25.27(5), formulas unchanged):
`ORC = BIC x ILM`, `RWA_op = 12.5 x ORC` (OPE25.2); `BI = ILDC + SC + FC` (OPE25.4); `ILDC = min(avg |II - IE|, 2.25% x avg IEA) + avg DI`, `SC = max(avg OOI, avg OOE) + max(avg FI, avg FE)`, `FC = avg |Net P&L_TB| + avg |Net P&L_BB|`
with a bar the three-year average over `t, t-1, t-2` and the absolute values of net items taken year by year before averaging (OPE25.5 and footnote 1); the BIC with the marginal coefficients 12 percent to EUR 1bn, 15 percent from 1bn to 30bn, 18 percent above (OPE25.7 Table 1);
`ILM = ln(exp(1) - 1 + (LC / BIC)^0.8)` with `LC = 15 x` the average annual operational risk losses over the previous 10 years (OPE25.8); ILM = 1 when LC = BIC and ILM > 1 when LC > BIC (OPE25.9).
Loss data rules and discretions (OPE25.10: 10 years of high-quality loss data, transitional minimum 5 years, and under 5 years capital is BIC only per OPE25.15; losses net of recoveries, FAQ1 to OPE25.10; OPE25.11: bucket 1 banks have ILM = 1 unless national discretion allows
inclusion, and supervisors may set ILM = 1 for all banks of the jurisdiction; OPE25.18: collection threshold EUR 20,000, national discretion EUR 100,000 for buckets 2 and 3).

### `riskvalidation.oprisk.sma.ildc`

```python
def ildc(ii: np.ndarray, ie: np.ndarray, iea: np.ndarray, di: np.ndarray) -> float: ...
```

- Units: each input `(3,)` EUR for the years `t, t-1, t-2`; `ILDC = min(mean(|ii - ie|), 0.0225 * mean(iea)) + mean(di)` (OPE25.5); the absolute value is taken year by year.
- Golden: `ii = [10, 10, 10]`, `ie = [2, 2, 2]`, `di = [1, 1, 1]`: with `iea = [100, 100, 100]`, `ILDC = min(8, 2.25) + 1 = 3.25`; with `iea = [1000, 1000, 1000]`, `ILDC = min(8, 22.5) + 1 = 9.0`. Year by year: `ii = [10, 2, 10]`, `ie = [2, 10, 2]` gives `mean |ii - ie| = 8` (the netted value, the absolute value of the difference of the two averages, would be 2.667).

### `riskvalidation.oprisk.sma.service_component`

```python
def service_component(ooi: np.ndarray, ooe: np.ndarray, fi: np.ndarray, fe: np.ndarray) -> float: ...
```

- Units: each input `(3,)` EUR; `SC = max(mean(ooi), mean(ooe)) + max(mean(fi), mean(fe))` (OPE25.5).
- Golden: `ooi = 5`, `ooe = 3`, `fi = 2`, `fe = 4` (each in all three years): `SC = 5 + 4 = 9`.

### `riskvalidation.oprisk.sma.financial_component`

```python
def financial_component(pl_tb: np.ndarray, pl_bb: np.ndarray) -> float: ...
```

- Units: each input `(3,)` EUR net profit and loss of the trading and banking book; `FC = mean(|pl_tb|) + mean(|pl_bb|)` with the absolute value taken year by year (OPE25.5 footnote 1).
- Golden: `pl_tb = [10, -10, 10]`, `pl_bb = [-3, 3, -3]`: `FC = 10 + 3 = 13` (netted before the absolute value it would be 4.33).

### `riskvalidation.oprisk.sma.business_indicator`

```python
def business_indicator(ildc_value: float, sc_value: float, fc_value: float) -> float: ...
```

- Units: EUR; `BI = ILDC + SC + FC` (OPE25.4).
- Invariants: the sum; `ValueError` for a negative component.
- Golden: `3.25 + 9 + 13 = 25.25`.

### `riskvalidation.oprisk.sma.bic_bucket`

```python
def bic_bucket(bi: float) -> int: ...
```

- Units: `bi` EUR; the result 1 for `bi <= 1e9`, 2 for `1e9 < bi <= 30e9`, 3 above (OPE25.7 Table 1).
- Golden: `bic_bucket(1e9)` is 1, `bic_bucket(1.0000001e9)` is 2, `bic_bucket(30e9)` is 2, `bic_bucket(35e9)` is 3.

### `riskvalidation.oprisk.sma.bic`

```python
def bic(bi: float) -> float: ...
```

- Units: `bi` EUR, the result EUR: `0.12 min(bi, 1e9) + 0.15 (min(bi, 30e9) - 1e9)^+ + 0.18 (bi - 30e9)^+` (OPE25.7 Table 1).
- Invariants: continuous and piecewise linear, increasing, `bic(0) = 0`; `ValueError` for a negative `bi`.
- Golden (OPE25.7 footnote 2): `bic(35e9) = 1 x 12% + 29 x 15% + 5 x 18% = 5.37e9`; `bic(0.5e9) = 0.06e9`; `bic(1e9) = 0.12e9`; `bic(30e9) = 4.47e9`.

### `riskvalidation.oprisk.sma.loss_component`

```python
def loss_component(annual_losses: np.ndarray, window_years: int = 10) -> float: ...
```

- Units: `annual_losses` `(Y,)` EUR, the annual operational risk losses net of recoveries (FAQ1 to OPE25.10), oldest first, each at or above the collection threshold; only the most recent `window_years` are used; `LC = 15 x mean` over the years used (OPE25.8).
- Invariants: `ValueError` for `Y = 0` or a negative loss; the function does not apply the minimum-years rule (`sma_capital` does).
- Golden: ten annual losses of 10: `LC = 15 x 10 = 150`; `annual_losses = [20, 10, 30, 40, 0]`: `LC = 15 x 20 = 300`.

### `riskvalidation.oprisk.sma.ilm`

```python
def ilm(loss_component_value: float, bic_value: float) -> float: ...
```

- Units: EUR over EUR; `ILM = ln(e - 1 + (LC / BIC)^0.8)` (OPE25.8).
- Invariants: `ILM = 1` exactly when `LC = BIC` (OPE25.9); increasing in `LC`; `ILM > 1` when `LC > BIC`; `ValueError` for `BIC <= 0` or `LC < 0`.
- Golden: `LC = BIC = 150`: `1.0`; `LC / BIC = 2`: `1.241090`; `LC / BIC = 0.5`: `0.829700`; `LC = 0`: `ln(e - 1) = 0.541325`; `LC = 285`, `BIC = 150`: `1.220648`.

### `riskvalidation.oprisk.sma.SmaResult`

```python
@dataclass(frozen=True)
class SmaResult:
    bi: float
    bic: float
    bucket: int
    years_used: int
    basis: str
    loss_component: float | None
    ilm: float | None
    discretion_applied: str
    orc: float
    rwa: float
    reason: str | None
```

- Units: money fields EUR; `basis` in `{"bic-times-ilm", "bic-only"}`; `discretion_applied` in `{"none", "bucket-1-ilm-one", "national-ilm-one", "transitional-bic-only"}` (the named field of the C17 `sma` block); `rwa = 12.5 x orc`.
- Invariants: frozen; `basis == "bic-only"` exactly when `loss_component is None`, `ilm is None`, `reason` is a string and `discretion_applied == "transitional-bic-only"`.

### `riskvalidation.oprisk.sma.sma_capital`

```python
def sma_capital(bi: float, annual_losses: np.ndarray, bucket1_uses_losses: bool = False, national_ilm_one: bool = False,
                minimum_years: int = 5, window_years: int = 10) -> SmaResult: ...
```

- Units: `bi` EUR; `annual_losses` `(Y,)` as `loss_component`. Order of the rules: (1) **fewer than `minimum_years` years of loss data: capital is the BIC only** (OPE25.10, OPE25.15), `basis = "bic-only"`, no LC and no ILM, a reason, discretion `transitional-bic-only`; never an ILM computed on too little
  data (the missing-data behavior of the unit); (2) `national_ilm_one`: `ILM = 1`, discretion `national-ilm-one` (OPE25.11, disclosure stays the caller's); (3) bucket 1 and not `bucket1_uses_losses`: `ILM = 1`, discretion `bucket-1-ilm-one` (OPE25.11); (4) otherwise `ILM = ilm(LC, BIC)`, discretion `none`.
  In (2) and (3) `loss_component` is still computed and reported. `ORC = BIC x ILM` (OPE25.2).
- Invariants: `orc = bic` in the BIC-only basis and whenever `ilm == 1`; `rwa = 12.5 orc`; `ValueError` for a negative `bi` and **for `minimum_years < 5`**: 5 years is the transitional minimum of OPE25.15, so an ILM on fewer than 5 years is unreachable through this function (a national discretion would be a different, explicit function).
- Golden: `bi = 35e9` with ten annual losses of `5.37e9 / 15 = 358e6`: `BIC = 5.37e9`, `LC = 5.37e9`, `ILM = 1`, `ORC = 5.37e9`, `RWA = 67.125e9`. `bi = 1.4e9` (bucket 2, `BIC = 0.18e9`) with 3 annual losses: `basis = "bic-only"`, `ORC = 0.18e9`, a reason.
  `bi = 0.5e9` (bucket 1, `BIC = 0.06e9`): `ILM = 1`, discretion `bucket-1-ilm-one`, `ORC = 0.06e9`; with `bucket1_uses_losses = True` the ILM is computed.

## Module `riskvalidation/validation/oprisk.py`

The operational risk validation tests of the ladder (dossier 05, "Implications for Contraste": acceptance tests of the operational risk ladder and case O1: fit on simulated years 1 to K, evaluate the capital stability on independent replications, never re-use the replications used for tuning).
Each returns one `TestResult`. These tests are descriptive: `p_value`, `alpha_amber` and `alpha_red` are null and the lights compare a metric against tolerances the caller supplies (`extras["thresholds"]`).

### `riskvalidation.validation.oprisk.benchmark_reproduction`

```python
def benchmark_reproduction(moments: tuple[float, float, float], quantiles: Mapping[str, float], moment_rel_tol: float = 1e-5,
                           quantile_rel_tol: float = 0.01, model_id: str | None = None) -> TestResult: ...
```

- Units: `moments = (mean, variance, skewness)` of the compound Poisson(100) with LN(0, 2) annual loss, computed by the engine; `quantiles` maps `"monte-carlo"`, `"panjer"` and `"fft"` to the 99.9 percent quantile in loss units found by that method (step 1); tolerances are relative decimals; `moment_rel_tol` is **at least 1e-5** when the moments come from the engine: the reference skewness 40.3428 is `e^6 / 10 = 40.342879` cut to four decimals, a relative error of 1.97e-6, so the engine's exact moments read `amber` (metric 1.966876) at `moment_rel_tol = 1e-6` and `green` (metric 0.196688) at the default 1e-5.
  `test_id = "oprisk.benchmark_reproduction"`. `h0`: the engine reproduces Shevchenko's benchmark (dossier 05 F.3): `E[Z] = 738.9056`, `Var[Z] = 298095.7987`, skewness `40.3428`, and a 99.9 percent quantile in the range 5849 to 5850.
- Invariants: a moment's deviation is `|value - reference| / reference`; a `panjer` or `fft` quantile's deviation is 0 inside `[5849, 5850]` (the step-1 discretised quantile) and otherwise the distance to the nearest end over `5849.5`; a `monte-carlo` quantile estimates the continuous quantile, so its deviation is `|q - 5853.1| / 5853.1` (Shevchenko Table 3 at step 0.0625 gives 5853.06 and Table 7 gives `H(5853.1) = 0.9990000`); `metric = max(moment deviations / moment_rel_tol, quantile deviations / quantile_rel_tol)`, `statistic` equals `metric`;
  `extras["max_quantile_rel_dev"]` is the largest quantile deviation and `extras["deviations"]` lists every deviation by name; a missing method in `quantiles` gives `not_evaluated`.
- Light: green when `metric <= 1`, amber when `metric <= 2`, red above.
- Golden: `moments = (738.9056, 298095.7987, 40.3428)`, `quantiles = {"panjer": 5849.0, "fft": 5850.0, "monte-carlo": 5900.0}`, `moment_rel_tol = 1e-6`, `quantile_rel_tol = 0.01`: the moment and the Panjer and FFT deviations are 0, the Monte Carlo deviation is
  `46.9 / 5853.1 = 0.008013`, `metric = 0.801285`, `light = "green"`, `extras["max_quantile_rel_dev"] = 0.008013`.

### `riskvalidation.validation.oprisk.threshold_stability`

```python
def threshold_stability(thresholds: np.ndarray, xi_hat: np.ndarray, model_id: str | None = None, tol_green: float = 0.10,
                        tol_amber: float = 0.25) -> TestResult: ...
```

- Units: `thresholds` `(T,)` EUR strictly increasing and `xi_hat` `(T,)` the fitted tail indices (decimals, `nan` for a threshold that could not be fitted); `test_id = "oprisk.threshold_stability"`. `h0`: the fitted tail index is stable across thresholds (the
  threshold-stability plot of dossier 05, ladder rung 2 and 3).
- Invariants: over the finite `xi_hat`, `metric = max - min` (the range), `statistic` equals `metric`; fewer than 2 finite values give `not_evaluated`; `extras["n_infinite_mean"]` counts the values at or above 1 (an infinite-mean fit, dossier 05 failure modes: `xi >= 1`);
  `extras["thresholds"]` carries `tol_green` and `tol_amber`; `n` is the number of finite values.
- Light: green when `metric <= tol_green`, amber when `metric <= tol_amber`, red above.
- Golden: `xi_hat = [0.90, 0.95, 1.00, 0.97]` with `tol_green = 0.05`, `tol_amber = 0.15`: `metric = 0.10`, `light = "amber"`, `extras["n_infinite_mean"] = 1`.

### `riskvalidation.validation.oprisk.capital_stability`

```python
def capital_stability(capitals: np.ndarray, truth: float, model_id: str | None = None, dispersion_green: float = 0.25,
                      dispersion_amber: float = 0.50, bias_green: float = 0.10, bias_amber: float = 0.25) -> TestResult: ...
```

- Units: `capitals` `(R,)` the 99.9 percent capital of each independent loss history in EUR, `truth > 0` the true 99.9 percent annual loss quantile in EUR (known by construction in C17); `test_id = "oprisk.capital_stability"`. `h0`: the capital is stable across independent histories and unbiased
  against the truth.
- Invariants: percentiles by linear interpolation (the `numpy.percentile` default); `metric = (p75 - p25) / truth` (the dispersion), `statistic = median / truth - 1` (the bias); `extras` carries `ratio_p05`, `ratio_p25`, `ratio_median`, `ratio_p75`, `ratio_p95` (percentiles of `capitals / truth`) and
  `share_underestimating`; `R < 4` gives `not_evaluated`; `extras["thresholds"]` carries the four tolerances.
- Light: the worse of two lights: dispersion green when `metric <= dispersion_green`, amber when `metric <= dispersion_amber`, red above; bias green when `|statistic| <= bias_green`, amber when `|statistic| <= bias_amber`, red above.
- Golden: `capitals = [90, 100, 110, 120]`, `truth = 100`: `p25 = 97.5`, `median = 105`, `p75 = 112.5`, `metric = 0.15`, `statistic = 0.05`, `light = "green"`.

### `riskvalidation.validation.oprisk.sma_ilm_response`

```python
def sma_ilm_response(bic_value: float, annual_losses: np.ndarray, added_loss: float, model_id: str | None = None,
                     jump_green: float = 0.05, jump_amber: float = 0.15) -> TestResult: ...
```

- Units: `bic_value` EUR, `annual_losses` `(Y,)` EUR (net of recoveries, oldest first), `added_loss >= 0` EUR added to the latest year; `test_id = "oprisk.sma_ilm_response"`. `h0`: the ILM does not jump when one large loss is added to the history (the SMA's response to a single large loss, dossier 05 ladder).
- Invariants: `ILM_before` and `ILM_after` from `loss_component` and `ilm` on the history without and with the added loss; `metric = ILM_after - ILM_before`, `statistic = ILM_after`; `Y < 5` gives `not_evaluated` with the reason (OPE25.15: no ILM on under 5 years); `extras` carries `ilm_before`, `lc_before`, `lc_after`,
  `orc_before`, `orc_after`; `extras["thresholds"]` carries `jump_green` and `jump_amber`.
- Light: green when `metric <= jump_green`, amber when `metric <= jump_amber`, red above.
- Golden: `bic_value = 150`, `annual_losses = [10] * 10`, `added_loss = 90`: `LC_before = 150`, `ILM_before = 1.0`, `LC_after = 285`, `ILM_after = 1.220648`, `metric = 0.220648`, `light = "red"`.

### `riskvalidation.validation.oprisk.scenario_influence`

```python
def scenario_influence(influences: np.ndarray, model_id: str | None = None, influence_amber: float = 0.10,
                       influence_red: float = 0.25) -> TestResult: ...
```

- Units: `influences` `(P,)` the output of `scenarios.scenario_influence` (dimensionless relative changes of the 99.9 percent capital); `test_id = "oprisk.scenario_influence"`. `h0`: no single scenario point moves the capital by more than the tolerance (dossier 05 F.5: validation must test the sensitivity of capital to each scenario point).
- Invariants: `metric = max |influences|`, `statistic` equals `metric`; `extras["influences"]` lists the values and `extras["argmax"]` the index of the largest; `P < 1` gives `not_evaluated`; `extras["thresholds"]` carries `influence_amber` and `influence_red`.
- Light: green when `metric <= influence_amber`, amber when `metric <= influence_red`, red above.
- Golden: `influences = [0.05, 0.0, 0.2]`: `metric = 0.2`, `light = "amber"` (with `influence_amber = 0.10`, `influence_red = 0.25`).

## Golden values summary

| Value | Where | Source |
|---|---|---|
| `E[Z] = 738.9056`, `Var[Z] = 298095.7987`, skewness `40.3428` for Poisson(100) with LN(0, 2) | `compound_poisson_moments`, `benchmark_reproduction` | dossier 05 F.3 (Shevchenko Example 9.4), recomputed from `100 e^2`, `100 e^8`, `e^6 / 10` |
| `H_5847 = 0.998999329`, `H_5848 = 0.998999773`, `H_5849 = 0.999000217`, 99.9 percent quantile 5849 at step 1 (Monte Carlo reference 5853.1) | `panjer_recursion`, `quantile_from_pmf`, `benchmark_reproduction` | Shevchenko Tables 2 to 4 and 7 (arXiv 1008.1108, verified); recomputed by the Panjer recursion; dossier 05 F.3 labelled the first value H_5849 (erratum) |
| Panjer `h_0` of Poisson, negative binomial and binomial; `(a, b)` of each | `panjer_h0`, `panjer_coefficients` | dossier 05 F.3 (Shevchenko Table 1); worked instances recomputed from the formulas |
| BIC `5.37e9` at BI `35e9` | `bic` | dossier 01 section F, OPE25.7 footnote 2 |
| ILM `1` when LC equals BIC | `ilm`, `sma_capital` | dossier 01 section F, OPE25.9 |
| BIC-only under 5 years of loss data | `sma_capital` | dossier 01 section F, OPE25.10 and OPE25.15 |
| Poisson-GPD closed-form SLA `6124.555320` (worked instance); EUR 647.1 million at xi 0.96378, beta 22349.4, lambda 41 (rounding xi to 0.96 gives 624.1 million); mean-corrected `8124.555320` (UNVERIFIED form) | `sla_var_poisson_gpd`, `sla_var_mean_corrected` | dossier 05 F.4 and F.6, hand-computed and reproduced by the log excess least squares fit |
| LDCE percentiles 27,632 / 41,916 / 82,608 / 418,400 and frequency 0.82 | the C17 calibration targets (documents, not functions) | dossier 05 F.6 (BCBS 160, Table ILD7), derived-only |
