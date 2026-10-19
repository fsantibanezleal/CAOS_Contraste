# Engine aggregation API contract: `engine-aggregation-api` 1.0.0

Owner: U13-S (unit sizing `plans/contraste/units/U13-sizing.md`, CAOS_MANAGE). Implemented by U13-E1 in `riskvalidation.aggregation` and
`riskvalidation.validation.aggregation` (repository CAOS_RiskValidation, released with the one engine tag of batch 3, R1 of the sizing);
called by the C18 bake (U13-P1). The tests of every function are written by U13-E1 against this file: a function exists with exactly the
signature below, and each golden value or invariant is a test. Changing a signature, a unit or a golden value is a breaking change (a new
major version of this contract). Sources: dossier 05 (`wip/contraste/05-market-ccr-alm-liquidity-oprisk-stress-sota-2026-10-04.md`, G.1
the ladder, G.2 Rosenberg and Schuermann, G.3 the dependence pitfalls and the band, G.4 the Euler allocation, G.5 the validation tests),
dossier 06 B.12 (model risk aggregation), the U13 research addendum (`wip/contraste/u13-research-addendum-2026-10-18.md`, F5 the
rearrangement algorithm) and the unit sizing decisions Q5, Q12, Q13, E3. Scope: decision E1 (2026-10-19) keeps C19 planned; this contract
has nothing of it.

The engine computes; it states no compliance claim. The headline capital of C18 is the simple sum (IAPE, 03 l.185-190; ECB, 01 l.846);
every other figure of this module is information, not capital (05 l.519). Every constant and golden value below is transcribed from the
source on its line, or computed from a formula stated on its line and labelled as computed. An item the source marks UNVERIFIED is marked
UNVERIFIED here and is not silently decided.

## Conventions (all functions)

- Arrays are `numpy.ndarray` of `float64`. Shapes: `K` risks (4 in C18: credit, market, irrbb, operational, in that order), `S` draws, `N`
  rows of the rearrangement matrix, `D` marginals.
- Money is a float in one currency (CLP millions in C18); the currency is the caller's and never converted. Correlations and confidence
  levels are decimals (a level of 99.9 percent is `0.999`). One horizon (one year) and one confidence level (0.999) apply to every
  marginal and every aggregate (05 l.378); a function that takes a level checks `0 < level < 1`.
- Capital basis (this contract's definition; the dossier writes EC for the capital of a risk): `EC = VaR_level(L) - EL`. The expected loss
  is additive, so the simple sum of the marginal EC equals the comonotonic EC of the total. Aggregates are returned as EC on the same basis.
- `VaR`, `ES` and their Monte Carlo errors are those of the reused `portfolio` helpers (below), never restated.
- Randomness: a function that draws takes an integer `seed` and uses `numpy.random.Generator(numpy.random.PCG64(seed))`; the result is
  reproducible for the same `(seed, n, chunk_size)`; another chunk size gives a different but equally valid sample. No function reads
  global state, the clock or the environment; inputs are never mutated.
- Dataclasses are frozen. A function that cannot compute a value because an input is missing or invalid raises `ValueError` with the reason
  (a correlation matrix that is not symmetric with a unit diagonal and positive semi-definite, a level outside `(0, 1)`, a `nu` not above 2);
  a validation function returns a `not_evaluated` row instead, with its reason in `notes` and `statistic`, `p_value` and `metric` all null.
  Nothing returns a placeholder number.
- A validation function returns one `TestResult` of `riskvalidation` (`core/result.py`), serialised by `TestResult.to_dict()` into a row that
  validates against `common/test-result` (`docs/contracts/schemas/common/test-result.schema.json`). The parameters of a light rule that are
  not alphas travel in `extras["thresholds"]`, a mapping from the parameter name to its value, beside `alpha_amber` and `alpha_red`
  (both null here: these tests are not hypothesis tests). The thresholds named here are policy parameters proposed by this contract
  (conventions of the case); none is a regulatory value.
- Cross-field checks of the documents the bake writes are `tests/contracts_u13/semantics.py` `violations(doc)` and `cross_violations(docs)`.

## Reused engine functions

Reused unchanged from the engine (R13 of the sizing); this contract names them and never restates them. A bake imports them from their own modules.

| Function | Used by |
|---|---|
| `riskvalidation.portfolio.portfolio.var_from_sample`, `riskvalidation.portfolio.portfolio.es_from_sample` | VaR and ES of every simulated aggregate and of the hybrid quantile |
| `riskvalidation.portfolio.portfolio.measures_from_sample`, `riskvalidation.portfolio.portfolio.LossMeasures` | `copula.copula_aggregate` (the level, EL, VaR, ES, EC and the Monte Carlo errors) |
| `riskvalidation.portfolio.copula.mc_standard_errors` | the batch-means standard errors of the VaR and ES of an aggregate |
| `riskvalidation.portfolio.euler.es_contributions`, `riskvalidation.portfolio.euler.var_contributions_kernel` | the Euler allocation of the aggregate (the Acerbi-Tasche ES contributions add up exactly) |
| `riskvalidation.validation.portfolio.euler_additivity` | the Euler additivity test of the band (`test_id = "portfolio.euler_additivity"`) |
| `riskvalidation.oprisk.aggregate`, `riskvalidation.oprisk.sma` | the operational marginal (decision Q5: recomputed from the C17 generator parameters) |
| `riskvalidation.irrbb.simulation.ear_evar` | the IRRBB marginal (decision Q5) |
| `riskvalidation.core.result.TestResult` | every validation function |

## Module `riskvalidation/aggregation/simple.py`

The first rungs of the ladder (05 G.1 items 1 and 2, item 4) and the closed-form allocation and diversification quantities (05 G.4).

### `riskvalidation.aggregation.simple.simple_sum`

```python
def simple_sum(ec: np.ndarray) -> float: ...
```

- Units: `ec` (K,) money, each `>= 0`; returns money. The headline capital of C18.
- Golden: `ec = (3, 4)` gives `7.0`.
- Invariants: equals `variance_covariance(ec, R)` with `R` all ones; `ValueError` for an empty array, a NaN or a negative element.

### `riskvalidation.aggregation.simple.check_correlation`

```python
def check_correlation(corr: np.ndarray, tol: float = 1e-9) -> None: ...
```

- Units: `corr` (K, K) dimensionless.
- Invariants: raises `ValueError` unless `corr` is square, symmetric to `tol`, has a unit diagonal to `tol`, every entry in `[-1, 1]` and the smallest eigenvalue is `>= -tol` (positive semi-definite); returns `None` otherwise.
- Golden: `[[1, 0.5], [0.5, 1]]` passes; `[[1, 0.9, -0.9], [0.9, 1, 0.9], [-0.9, 0.9, 1]]` raises (not positive semi-definite).

### `riskvalidation.aggregation.simple.variance_covariance`

```python
def variance_covariance(ec: np.ndarray, corr: np.ndarray) -> float: ...
```

- Units: `ec` (K,) money, `corr` (K, K) correlation; returns money. `EC_tot = sqrt(EC' R EC)` (05 G.1 item 2); exact for elliptical losses with a common quantile scaling, an approximation otherwise.
- Golden: `ec = (3, 4)`, `R = I`: `5.0`; `R` all ones: `7.0`; `R = [[1, 0.5], [0.5, 1]]`: `sqrt(37) = 6.0828` (computed, to `5e-5`).
- Invariants: calls `check_correlation` first; between `sqrt(sum ec_k^2)` (R the identity) and the simple sum (R all ones) for any `R` with nonnegative entries; symmetric under a joint permutation of `ec` and `R`; homogeneous of degree 1 in `ec`.

### `riskvalidation.aggregation.simple.hybrid_quantile`

```python
def hybrid_quantile(samples: np.ndarray, q: float) -> float: ...
```

- Units: `samples` (S, K) money, one loss sample per risk with a common row index; `q` decimal. The hybrid approximation of Rosenberg and Schuermann (05 G.1 item 4, "H-VaR"): the quantile of each column combined with the empirical correlation of the columns, `sqrt(v' R_emp v)` with `v_k = var_from_sample(samples[:, k], q)`. The dossier names the approach and not the estimator: the Pearson correlation of the columns is this contract's definition (UNVERIFIED against the paper).
- Golden: columns `x` and `2 x` (correlation 1) give `q_x + q_2x = 3 q_x`; two columns with Pearson correlation 0 give `sqrt(v_1^2 + v_2^2)`.
- Invariants: `ValueError` for `S < 2` or a constant column (a correlation is undefined); not above `sum v_k` (to rounding).

### `riskvalidation.aggregation.simple.diversification_factor`

```python
def diversification_factor(rho_total: float, rho_marginals: Sequence[float]) -> float: ...
```

- Units: money; returns a decimal. `DF = rho(L) / sum rho(L_i)` (05 G.4).
- Golden: `(6.0828, [3, 4])` gives `0.8690` (`6.0828 / 7`, computed, to `5e-5`).
- Invariants: `ValueError` for a zero or negative denominator; `DF <= 1` is not forced (VaR is not subadditive, 05 G.3): the sign of every benefit is reported by the validation test, never repaired here.

### `riskvalidation.aggregation.simple.euler_diversification_benefit`

```python
def euler_diversification_benefit(rho_contribution: float, rho_standalone: float) -> float: ...
```

- Units: money; returns a decimal. `1 - rho(L_i | L) / rho(L_i)` (05 G.4).
- Golden: `(6.0, 8.0)` gives `0.25`.
- Invariants: `ValueError` for `rho_standalone <= 0`; zero when the contribution equals the standalone measure.

### `riskvalidation.aggregation.simple.std_contributions`

```python
def std_contributions(cov: np.ndarray, c: float = 1.0) -> np.ndarray: ...
```

- Units: `cov` (K, K) the covariance matrix of `(L_1, ..., L_K)` in money squared, `c` a multiplier; returns (K,) money. The closed-form Euler contributions of the standard deviation measure, `c cov[L_i, L] / sqrt(var L)` (Tasche eq. 3.4, 05 G.4), so that the variance-covariance total allocates exactly.
- Golden: `cov = [[4, 2], [2, 9]]`, `c = 1`: `cov[L_1, L] = 6`, `cov[L_2, L] = 11`, `var L = 17`, contributions `(1.4552, 2.6679)`, sum `4.1231 = sqrt(17)` (computed, to `5e-5`).
- Invariants: the contributions sum to `c sqrt(var L)` to `1e-12 relative`; `ValueError` for a non-symmetric or non-positive-semi-definite `cov` or `var L = 0`.

## Module `riskvalidation/aggregation/copulas.py`

Rungs 3 and 4 of the ladder (05 G.1 item 3): Gaussian and Student t copula aggregation. The copula draw of `U` is restated here from the sources the engine's own `portfolio.copula` docstring cites (Frey and McNeil 2003; Demarta and McNeil 2005), because `portfolio.copula` keeps its sampler private (R13). Clayton sampling is deferred (decision Q13, BL-078). Vine copulas are not in this contract (BL-078).

### `riskvalidation.aggregation.copulas.marginal_ppf_sample`

```python
def marginal_ppf_sample(sorted_losses: np.ndarray) -> Callable[[np.ndarray], np.ndarray]: ...
```

- Units: `sorted_losses` (n,) money ascending; the returned function maps probabilities in `(0, 1)` to money. The interpolation rule (this contract's definition): `ppf(u) = numpy.interp(u, (i - 0.5) / n for i = 1..n, sorted_losses)`, linear between the Hazen positions and clamped at the ends.
- Golden: `sorted_losses = [0, 10]`: `ppf(0.5) = 5.0`, `ppf(0.1) = 0.0`, `ppf(0.9) = 10.0`.
- Invariants: nondecreasing; `ValueError` for an unsorted array, `n < 2` or a NaN; the result never leaves `[min, max]` of the sample.

### `riskvalidation.aggregation.copulas.marginal_ppf_pmf`

```python
def marginal_ppf_pmf(grid: np.ndarray, pmf: np.ndarray) -> Callable[[np.ndarray], np.ndarray]: ...
```

- Units: `grid` (m,) money ascending, `pmf` (m,) probabilities summing to 1 (to `1e-9`); the returned function maps probabilities to money. Rule: the smallest grid point whose cumulative probability is `>= u - 1e-12` (the rule of `oprisk.aggregate.quantile_from_pmf`).
- Golden: `grid = [0, 1, 2]`, `pmf = [0.5, 0.3, 0.2]`: `ppf(0.5) = 0`, `ppf(0.51) = 1`, `ppf(0.8) = 1`, `ppf(0.81) = 2`.
- Invariants: nondecreasing; `ValueError` for a pmf with a negative entry or a sum off 1.

### `riskvalidation.aggregation.copulas.simulate_copula_uniforms`

```python
def simulate_copula_uniforms(corr: np.ndarray, family: str, nu: float | None, n: int, seed: int) -> np.ndarray: ...
```

- Units: `corr` (K, K) correlation, `family` in `"gaussian"`, `"t"`, `nu` degrees of freedom (required above 2 for `"t"`, `None` for `"gaussian"`); returns (n, K) probabilities in `(0, 1)`. Gaussian: `Z = L e` with `L` the Cholesky factor of `corr`, `U = Phi(Z)`. Student t: `W = nu / chi2_nu`, `X = sqrt(W) Z`, `U = t_nu(X)` (Demarta and McNeil 2005).
- Invariants: the same `(seed, n)` gives the same array; each column is uniform (Kolmogorov distance below `3 / sqrt(n)` at `n = 1e5`); the Kendall rank correlation of a pair is `(2 / pi) arcsin(rho)` for both families (elliptical copulas), which for `rho = 0.5` is `0.3333` (computed); `ValueError` for a `corr` that fails `check_correlation`, `n < 1`, a `"t"` without `nu > 2`.

### `riskvalidation.aggregation.copulas.simulate_component_losses`

```python
def simulate_component_losses(ppfs: Sequence[Callable[[np.ndarray], np.ndarray]], corr: np.ndarray, family: str, nu: float | None,
                              n_draws: int, seed: int, chunk_size: int = 100_000) -> np.ndarray: ...
```

- Units: `ppfs` K marginal quantile functions (money), `n_draws` the number of scenarios; returns (S, K) money with `S = n_draws`, `L_k = ppf_k(U_k)` (05 G.1 item 3, Sklar). Drawn in chunks of `chunk_size`, so the working memory of the draw is `chunk_size * K * 8` bytes; the returned array is `n_draws * K * 8` bytes (320 MB at `1e7` draws of 4 risks, the known maximum of the sizing).
- Invariants: reproducible for the same `(seed, n_draws, chunk_size)`; with `corr` all ones every row is comonotonic (the columns are nondecreasing functions of one `U`); with `corr = I` the columns are independent (the sample correlation of two columns is within `4 / sqrt(S)` of 0); every column has the marginal of its `ppf`.

### `riskvalidation.aggregation.copulas.t_tail_dependence`

```python
def t_tail_dependence(rho: float, nu: float) -> float: ...
```

- Units: `rho` in `(-1, 1)`, `nu > 0`; returns the symmetric tail dependence coefficient of the bivariate t copula, `lambda = 2 t_(nu+1)(-sqrt((nu + 1)(1 - rho) / (1 + rho)))` (05 G.1 item 3, McNeil, Frey and Embrechts; the chapter number is UNVERIFIED there).
- Golden (computed by Simpson quadrature of the `t_(nu+1)` density, checked against `scipy.stats.t.cdf` to `5e-5`): `(rho = 0.5, nu = 4)`: `0.2532`; `(rho = 0, nu = 4)`: `0.0756`; `(rho = 0.5, nu = 8)`: `0.1173`; `(rho = 0.5, nu = 30)`: `0.0030`.
- Invariants: decreasing in `nu` for fixed `rho`; increasing in `rho`; tends to 0 as `nu` grows; `ValueError` for `|rho| >= 1`.

### `riskvalidation.aggregation.copulas.clayton_copula`

```python
def clayton_copula(u: float, v: float, theta: float) -> float: ...
```

- Units: `u`, `v` in `(0, 1]`, `theta > 0`; returns a probability. `C_theta(u, v) = (u^-theta + v^-theta - 1)^(-1/theta)` (05 G.1 item 3). Bivariate; sampling is deferred (decision Q13).
- Golden: `(0.5, 0.5, 1.0)` gives `0.3333` (`1 / 3`); `C(u, 1) = u`.
- Invariants: bounded by the Frechet bounds `max(u + v - 1, 0) <= C <= min(u, v)`; symmetric in `(u, v)`.

### `riskvalidation.aggregation.copulas.clayton_lower_tail_dependence`

```python
def clayton_lower_tail_dependence(theta: float) -> float: ...
```

- Units: `theta > 0`; returns a decimal. `2^(-1 / theta)` (05 G.1 item 3).
- Golden: `theta = 1` gives `0.5`; `theta = 2` gives `0.7071` (computed).
- Invariants: increasing in `theta`; in `(0, 1)`.

### `riskvalidation.aggregation.copulas.CopulaAggregate`

```python
@dataclass(frozen=True)
class CopulaAggregate:
    family: str              # "gaussian" or "t"
    nu: float | None
    n_draws: int
    seed: int
    chunk_size: int
    level: float             # 0.999
    el: float                # the caller's sum of the marginal expected losses
    var: float               # VaR of the total
    es: float
    ec: float                # var - el
    var_se: float | None     # batch-means standard errors (portfolio.copula.mc_standard_errors)
    es_se: float | None
```

- Units: money for `el`, `var`, `es`, `ec`, `var_se`, `es_se`; `level` a decimal.
- Invariants: `ec = var - el` to `1e-9 * max(1, var)`; `es >= var - 1e-9`; `var_se` and `es_se` are both None or both set (None when `n_draws < 10 * 20`, never an error and never a number); they map onto the band row's `mc_se_clp_m` and the marginal-free fields of the C18 aggregation block.

### `riskvalidation.aggregation.copulas.copula_aggregate`

```python
def copula_aggregate(ppfs: Sequence[Callable[[np.ndarray], np.ndarray]], corr: np.ndarray, family: str, nu: float | None, el: float,
                     level: float = 0.999, n_draws: int = 1_000_000, seed: int = 0, chunk_size: int = 100_000) -> CopulaAggregate: ...
```

- Units: as `simulate_component_losses`; `el` money (the sum of the marginal expected losses); returns a `CopulaAggregate`. VaR, ES and the errors are computed by the reused `portfolio.measures_from_sample` on the row sums.
- Invariants: with `corr` all ones the VaR agrees with `sum ppf_k(level)` (the comonotonic total) within Monte Carlo error; with `corr = I` and two Uniform marginals the total has the triangular law (`VaR_0.5 = 1` for `U(0, 1) + U(0, 1)`) within `5 se`; with normal marginals and a Gaussian copula the VaR agrees with the variance-covariance quantile `mu + z_level sqrt(sum_ij R_ij sigma_i sigma_j)` within `5 se` (exact in the elliptical case for a common quantile scaling: 05 l.350); `ValueError` for the failures of `simulate_copula_uniforms` and a `level` outside `(0, 1)`.

## Module `riskvalidation/aggregation/bounds.py`

Rung 6 of the ladder: worst-case (and best-case) VaR bounds for given marginals and unknown dependence, by the rearrangement algorithm of Embrechts, Puccetti and Ruschendorf, "Model uncertainty and VaR aggregation", Journal of Banking and Finance 37(8), 2750-2764, 2013 (accepted manuscript https://people.math.ethz.ch/~embrecht/ftp/MUVaR.pdf, section 2.2, pp.8-11; transcribed in F5 of the research addendum). VaR is not subadditive, so the comonotonic sum is not the worst case (05 l.366). Decision E3: the module implements the algorithm as F5 transcribes it, with Tables 1 and 4 of the authors' paper as golden values.

### `riskvalidation.aggregation.bounds.comonotonic_var`

```python
def comonotonic_var(ppfs: Sequence[Callable[[np.ndarray], np.ndarray]], q: float) -> float: ...
```

- Units: money; `q` decimal. The VaR of the comonotonic total, `sum_k F_k^-1(q)`.
- Golden: Pareto(2) marginals, `F(x) = 1 - (1 + x)^-2`, so `F^-1(q) = (1 - q)^(-1/2) - 1`: `d = 8` marginals at `q = 0.99` give `72.00`, at `0.995` `105.14`, at `0.999` `244.98`; `d = 56`: `504.00`, `735.96`, `1714.88`; `d = 648`: `5832.00`, `8516.10`, `19843.56` (Table 4, column "comonotonic (exact)", PDF p.14; recomputed from the formula).
- Invariants: equals `copula_aggregate(..., corr = all ones)` VaR within Monte Carlo error; `F^-1(0.99) = 9` for Pareto(2).

### `riskvalidation.aggregation.bounds.rearrangement_algorithm`

```python
def rearrangement_algorithm(matrix: np.ndarray, objective: str, epsilon: float, max_sweeps: int, seed: int) -> tuple[np.ndarray, float, int, bool]: ...
```

- Units: `matrix` (N, D) money; `objective` in `"max-min-row-sum"` (maximise the smallest row sum, the upper VaR bound, F5 steps 2 to 5 on `X-underline`) and `"min-max-row-sum"` (minimise the largest row sum, the lower VaR bound); `epsilon > 0` the accuracy; returns `(rearranged matrix, value, sweeps, converged)` with `value` the smallest (largest) row sum of the result. Steps (F5, p.10): permute each column randomly (seeded); then, in a sweep, rearrange column `j` to be oppositely ordered to the sum of the other columns, for `j = 1..D`; repeat sweeps until the value changes by less than `epsilon` between two successive full sweeps, or `max_sweeps` is reached (`converged = False`; the paper's remark 6, p.11, says there is no analytic proof of convergence for all starting configurations: UNVERIFIED as a theorem, the random permutation of step 3 is the paper's mitigation).
- Golden (Table 1, PDF p.12): `d = 3`, Pareto(2), `alpha = 0.99`, `N = 50`, `X-underline` with `x_(i,j) = F^-1(0.99 + 0.01 (i - 1) / 50)`: the first row is `(9.00000, 9.00000, 9.00000)` with row sum `27.0000`, the last row `(69.71068, 69.71068, 69.71068)` with row sum `209.1320`, every column sums to `851.72901`. After the algorithm every column still sums to `851.72901` (a column-wise permutation of the input), the smallest row sum is `44.7671` and the largest `87.8122` of the printed matrix `X*`; rows 1 to 3 of the printed result are `(13.43376, 15.66667, 15.66667)`, `(12.86750, 14.81139, 17.25742)`, `(15.66667, 13.14214, 16.14986)`. The random start moves the last digits: the test asserts the column sums to `5e-5` and the smallest and largest row sums within `0.5` of the printed values (a tolerance proposed by this contract).
- Invariants: the output is a permutation of each input column; with `D = 1` the value is the minimum entry; `ValueError` for `epsilon <= 0`, `N < 2`, `D < 2`.

### `riskvalidation.aggregation.bounds.VarBounds`

```python
@dataclass(frozen=True)
class VarBounds:
    alpha: float
    n: int
    epsilon: float
    lower_range: tuple[float, float]    # (t_N, t-bar_N): the best VaR, F5 (21)
    upper_range: tuple[float, float]    # (s_N, s-bar_N): the worst VaR, F5 (19)
    sweeps: tuple[int, int, int, int]
    converged: bool
```

- Units: money for the ranges; `alpha` decimal. The interval of each range is the "rearrangement range" of remark 6.
- Invariants: `lower_range[0] <= lower_range[1] <= comonotonic <= upper_range[0] <= upper_range[1]` in the cases of the golden below.

### `riskvalidation.aggregation.bounds.worst_var_bounds`

```python
def worst_var_bounds(ppfs: Sequence[Callable[[np.ndarray], np.ndarray]], alpha: float, n: int = 100_000, epsilon: float = 1e-3,
                     max_sweeps: int = 1_000, seed: int = 0) -> VarBounds: ...
```

- Units: money; returns both bounds. The upper bound uses the matrices of F5 (18) over `[alpha, 1]` (cell edges `F_j^-1(alpha + (1 - alpha)(i - 1) / N)` and `F_j^-1(alpha + (1 - alpha) i / N)`), the lower bound those of F5 (20) over `[0, alpha]`. No distribution function is inverted: the quantile functions are evaluated on the grid.
- Golden (Table 4, Pareto(2), `N = 1e5`, `epsilon = 1e-3`, `d = 8`; PDF p.14, columns lower RA range, upper exact, upper RA range): `alpha = 0.99`: lower `9.00 - 9.00`, upper exact `141.67`, upper RA `141.66 - 141.67`; `alpha = 0.995`: lower `13.13 - 13.14`, upper exact `203.66`, upper RA `203.65 - 203.66`; `alpha = 0.999`: lower `30.47 - 30.62`, upper exact `465.29`, upper RA `465.28 - 465.30`. The test asserts the ranges within `0.05` of the printed ranges for `alpha = 0.99` and `0.995` and within `0.5` for `0.999` (tolerances proposed by this contract). The exact upper value comes from the paper's Proposition 4 for homogeneous Pareto marginals, which F5 does not transcribe (UNVERIFIED as a transcription: the table values are the golden numbers).
- Invariants: `lower_range[1] < comonotonic_var < upper_range[0]` for `d >= 3` Pareto(2); `ValueError` for `alpha` outside `(0, 1)` or `n < 2`.

## Module `riskvalidation/aggregation/band.py`

The dependence-uncertainty band every aggregate is shown with (SDD l.331; 05 G.3, l.366). The band is returned whole, never one diversified number. Decision Q12: the lower bound is added to the SDD's five rows.

### `riskvalidation.aggregation.band.BandRow`

```python
@dataclass(frozen=True)
class BandRow:
    method: str              # lower-bound, simple-sum, variance-covariance, gaussian-copula, t-copula, worst-case
    nu: float | None         # set for t-copula, None otherwise
    capital: float           # EC on the capital basis, money
    diversification_factor: float   # capital / simple sum
    status: str              # "headline-capital" for the simple sum, "information-not-capital" for every other row
    mc_se: float | None      # Monte Carlo standard error where the row is simulated
```

- Units: money for `capital` and `mc_se`; the factor a decimal.
- Invariants: `status` follows `method` exactly; `nu` is set exactly for `t-copula`; maps one to one onto the document row `outputs.aggregation.band[*]` (`method`, `nu`, `capital_clp_m`, `diversification_factor`, `status`, `mc_se_clp_m`).

### `riskvalidation.aggregation.band.Band`

```python
@dataclass(frozen=True)
class Band:
    rows: tuple[BandRow, ...]
    headline: float          # the simple sum
    horizon_years: int       # 1
    confidence_level: float  # 0.999
    capital_basis: str       # "economic-capital-var-less-el"
```

- Units: money for `headline`.
- Invariants: `headline` is the `capital` of the single `simple-sum` row; the rows are the lower bound, the simple sum, variance-covariance, Gaussian, one t row per `nu` of the set, the worst case; `lower-bound <= every other row <= worst-case`; the diversified rows are `<= headline` (the sign of every diversification benefit: a row above the headline is reported by `validation.aggregation.diversification_sign`, never repaired).

### `riskvalidation.aggregation.band.dependence_band`

```python
def dependence_band(ppfs: Sequence[Callable[[np.ndarray], np.ndarray]], ec: np.ndarray, el: np.ndarray, corr: np.ndarray,
                    nu_set: Sequence[float], level: float = 0.999, horizon_years: int = 1, n_draws: int = 1_000_000, seed: int = 0,
                    chunk_size: int = 100_000, bounds_n: int = 100_000, bounds_epsilon: float = 1e-3) -> Band: ...
```

- Units: `ec`, `el` (K,) money; `nu_set` degrees of freedom above 2, ascending and distinct; returns a `Band`. The rows run over the same marginals: `simple_sum`, `variance_covariance`, `copula_aggregate` for the Gaussian copula and for each `nu`, and `worst_var_bounds` (its `lower_range[0]` and `upper_range[1]` less `sum el`) for the lower and the worst case.
- Golden: `ec = (3, 4)`, `el = (0, 0)`, `R = [[1, 0.5], [0.5, 1]]`: the simple-sum row is `7.0`, the variance-covariance row `6.0828`, and `lower <= 6.0828 <= worst`.
- Invariants: one horizon and one confidence level on every row (`ValueError` otherwise); `ValueError` for a `nu_set` that is empty, unsorted or has a value `<= 2`; the same `seed` gives the same band.

## Module `riskvalidation/aggregation/model_risk.py`

The model risk measures of dossier 06 B.12 over the set of aggregation models of the band: sensitivity information, never a regulatory capital figure (06 l.699-704). Built and shown beside the band (decisions Q12, Q13).

### `riskvalidation.aggregation.model_risk.ModelRisk`

```python
@dataclass(frozen=True)
class ModelRisk:
    rho_x0: float     # the risk measure under the reference model
    rho_max: float
    rho_min: float
    am: float         # rho_max / rho_x0 - 1
    rm: float         # (rho_max - rho_x0) / (rho_max - rho_min), in [0, 1]
```

- Units: money for the `rho`s; `am` and `rm` decimals.
- Invariants: `am = rho_max / rho_x0 - 1`; `0 <= rm <= 1`; `rm = 0` when `rho_max = rho_min` (this contract's convention for the undefined `0 / 0`; UNVERIFIED in the paper).

### `riskvalidation.aggregation.model_risk.barrieu_scandolo`

```python
def barrieu_scandolo(rhos: Sequence[float], reference_index: int) -> ModelRisk: ...
```

- Units: `rhos` money, the risk measure under each model of the set (the band rows); `reference_index` the position of the reference model `X0`. Barrieu and Scandolo (2015), "Assessing financial model risk", EJOR 242(2):546-556: `AM = max rho / rho(X0) - 1` ("generalizes the Basel multiplier") and `RM = (max rho - rho(X0)) / (max rho - min rho)` (06 l.692-698).
- Golden: `rhos = (100, 130, 90)`, `reference_index = 0`: `am = 0.3`, `rm = 0.75` (computed).
- Invariants: `rho_x0 > 0` else `ValueError`; `reference_index` in range; `am >= 0` and `0 <= rm <= 1` when the reference model is one of the models of the set (the maximum is taken over a set that contains it).

### `riskvalidation.aggregation.model_risk.GlassermanXu`

```python
@dataclass(frozen=True)
class GlassermanXu:
    theta: float
    relative_entropy: float   # E[m log m] at theta
    baseline: float           # E[V]
    worst_case: float         # E[m V]
```

- Units: `baseline` and `worst_case` in the units of `V`; `theta` and the entropy dimensionless.
- Invariants: `worst_case >= baseline`; `relative_entropy` equals the budget to `tol`.

### `riskvalidation.aggregation.model_risk.glasserman_xu_worst_case`

```python
def glasserman_xu_worst_case(v: np.ndarray, budget: float, tol: float = 1e-10) -> GlassermanXu: ...
```

- Units: `v` (S,) the loss function evaluated on the baseline sample, `budget > 0` the relative entropy budget `eta`. Glasserman and Xu (2014), Quantitative Finance 14(1):29-58: `sup_{m: E[m log m] <= eta} E[m V]` is attained at `m_theta = exp(theta V) / E[exp(theta V)]` with `theta > 0` set (by bisection) so that the entropy constraint binds (06 l.684-691); the worst case is computed by reweighting the baseline sample.
- Golden: `v = [0, 1]` (equally likely), `theta = 1`: `m = (0.5379, 1.4621)`, relative entropy `0.1109`, `worst_case = 0.7311` against `baseline = 0.5`; calling with `budget = 0.1109` recovers `theta = 1` to `1e-3` (computed).
- Invariants: `ValueError` when `budget` exceeds `log S` (the largest attainable entropy of a finite sample) or `v` is constant; `worst_case` is increasing in `budget`.

## Module `riskvalidation/validation/aggregation.py`

The tests of G.5 (05 l.378), each a `TestResult` with `reference`, `h0` and a policy version. The Euler additivity test is the reused `riskvalidation.validation.portfolio.euler_additivity`. All take `model_id: str | None = None, segment: str | None = None` last.

### `riskvalidation.validation.aggregation.simple_sum_and_variance_covariance`

```python
def simple_sum_and_variance_covariance(ec: np.ndarray, corr: np.ndarray, aggregate: float, amber: float = 0.10, tolerance: float = 1e-9,
                                       model_id: str | None = None, segment: str | None = None) -> TestResult: ...
```

- Units: `ec` money, `aggregate` money (a copula aggregate), `amber` a relative decimal; `test_id = "aggregation.simple_sum_and_variance_covariance"`. `h0`: the aggregate is not above the simple sum and agrees with the variance-covariance formula (05 G.5: "benchmark the aggregation against the simple sum and the variance-covariance formula").
- Invariants: `statistic = aggregate / variance_covariance(ec, corr)`, `metric = aggregate / simple_sum(ec)`; `p_value` null; `extras` carries `simple_sum`, `variance_covariance` and `thresholds = {"amber": amber, "tolerance": tolerance}`.
- Light: red when `aggregate > simple_sum (1 + tolerance)` (a diversified figure above the sum); amber when `|statistic - 1| > amber`; green otherwise.
- Golden: `ec = (3, 4)`, `R = I`, `aggregate = 5.0`: `statistic = 1.0`, `metric = 0.7143`, green; `aggregate = 8.0`: red; `aggregate = 5.6`: `statistic = 1.12`, amber.

### `riskvalidation.validation.aggregation.copula_choice_sensitivity`

```python
def copula_choice_sensitivity(gaussian: float, t_capitals: Sequence[tuple[float, float]], amber: float = 0.05, red: float = 0.15,
                              model_id: str | None = None, segment: str | None = None) -> TestResult: ...
```

- Units: money; `t_capitals` pairs `(nu, capital)`; `test_id = "aggregation.copula_choice_sensitivity"`. `h0`: the choice between the Gaussian and the t copula over the stated nu set moves the capital by less than the thresholds (05 G.5; Rosenberg and Schuermann find the choice has "a more modest effect on risk", 05 G.2).
- Invariants: `statistic = max over nu of |t / gaussian - 1|`; `metric` the signed value at the smallest `nu`; `extras` carries the per-`nu` differences and `thresholds = {"amber": amber, "red": red}`.
- Light: green when `statistic <= amber`; amber when `<= red`; red above.
- Golden: `gaussian = 100`, `t_capitals = ((4, 107), (8, 103.5), (30, 101))`: `statistic = 0.07`, amber.

### `riskvalidation.validation.aggregation.worst_case_bracket`

```python
def worst_case_bracket(lower: float, rows: Sequence[float], worst: float, tolerance: float = 1e-9,
                       model_id: str | None = None, segment: str | None = None) -> TestResult: ...
```

- Units: money; `test_id = "aggregation.worst_case_bracket"`. `h0`: every row of the band lies between the lower bound and the worst case (05 G.3, G.5: report worst-case bounds).
- Invariants: `statistic = worst - lower`, `metric = (worst - lower) / max(rows)`; `extras` carries `thresholds = {"tolerance": tolerance}`.
- Light: red when any row is outside `[lower - tolerance, worst + tolerance]` or `lower > worst`; green otherwise (no amber: a bracket holds or it does not).
- Golden: `lower = 4.0`, `rows = (5.0, 6.0828, 7.0)`, `worst = 8.0`: `statistic = 4.0`, green; `worst = 6.5`: red.

### `riskvalidation.validation.aggregation.correlation_stress`

```python
def correlation_stress(base: float, stressed: float, amber: float = 0.10, tolerance: float = 1e-9,
                       model_id: str | None = None, segment: str | None = None) -> TestResult: ...
```

- Units: money; `test_id = "aggregation.correlation_stress"`. `h0`: raising the market-credit correlation to 0.8 (05 G.5) does not lower the capital and raises it by less than `amber`.
- Invariants: `statistic = stressed / base - 1`; `metric` equals `statistic`; `extras` carries `thresholds = {"amber": amber, "tolerance": tolerance}`.
- Light: red when `statistic < -tolerance` (capital falls when a correlation rises); amber when `statistic > amber`; green otherwise.
- Golden: `base = 100`, `stressed = 105`: `statistic = 0.05`, green; `stressed = 112`: amber; `stressed = 95`: red.

### `riskvalidation.validation.aggregation.diversification_sign`

```python
def diversification_sign(factors: Sequence[float], tolerance: float = 1e-9, model_id: str | None = None,
                         segment: str | None = None) -> TestResult: ...
```

- Units: decimals (the `DF` of each diversified row); `test_id = "aggregation.diversification_sign"`. `h0`: every diversification benefit has the right sign, `DF <= 1` (05 G.5: "the sign of every diversification benefit").
- Invariants: `statistic = max(factors)`, `metric = 1 - min(factors)`; `extras` carries the count of rows above 1 and `thresholds = {"tolerance": tolerance}`.
- Light: red when `max(factors) > 1 + tolerance`; green otherwise.
- Golden: `factors = (0.87, 0.9, 0.93)`: green; `(0.87, 1.02)`: red.

### `riskvalidation.validation.aggregation.horizon_confidence_consistency`

```python
def horizon_confidence_consistency(horizons: Sequence[float], levels: Sequence[float], expected_horizon: float = 1.0,
                                   expected_level: float = 0.999, model_id: str | None = None,
                                   segment: str | None = None) -> TestResult: ...
```

- Units: years and decimals; `test_id = "aggregation.horizon_confidence_consistency"`. `h0`: one risk horizon and one confidence level across the marginals (05 G.5; 01 l.837-839).
- Invariants: `statistic` is the number of marginals that differ from the expected horizon or level; `metric` null; `extras` carries the offending indices and `thresholds = {"expected_horizon": expected_horizon, "expected_level": expected_level}`.
- Light: red when `statistic > 0`; green otherwise.
- Golden: `((1, 1, 1, 1), (0.999, 0.999, 0.999, 0.999))`: `statistic = 0`, green; one level `0.99`: `statistic = 1`, red.

### `riskvalidation.validation.aggregation.elliptical_mc_agreement`

```python
def elliptical_mc_agreement(mc_capital: float, mc_se: float, vc_capital: float, z: float = 3.0, model_id: str | None = None,
                            segment: str | None = None) -> TestResult: ...
```

- Units: money; `test_id = "aggregation.elliptical_mc_agreement"`. `h0`: in the elliptical case (normal marginals, Gaussian copula) the Monte Carlo capital agrees with the variance-covariance anchor within `z` standard errors (exact there for a common quantile scaling: 05 l.350).
- Invariants: `statistic = (mc_capital - vc_capital) / mc_se`, `metric = mc_capital / vc_capital - 1`; `mc_se > 0` else `not_evaluated`; `extras` carries `thresholds = {"z": z}`.
- Light: green when `|statistic| <= z`; red above.
- Golden: `mc = 100.4`, `se = 0.2`, `vc = 100.0`: `statistic = 2.0`, green; `mc = 101.0`: `statistic = 5.0`, red.

### `riskvalidation.validation.aggregation.rosenberg_schuermann_reference`

```python
def rosenberg_schuermann_reference(simple_sum: float, gaussian: float, low: float = 0.30, high: float = 0.40,
                                   model_id: str | None = None, segment: str | None = None) -> TestResult: ...
```

- Units: money; `test_id = "aggregation.rosenberg_schuermann_reference"`. `h0`: none to reject: the additive approximation typically overestimates risk by about 30 to 40 percent (Rosenberg and Schuermann 2006; 05 l.360, l.484), reported beside the result as a reference, never a gate.
- Invariants: `statistic = simple_sum / gaussian - 1`; `metric` equals `statistic`; the light is always `green` (a reference, never a gate: the row exists to be shown) and `notes` states whether the figure lies inside or outside `[low, high]`; `extras` carries `role = "reference-not-a-gate"` and `thresholds = {"low": low, "high": high}`.
- Light: always green (a reference, never a gate); the row carries the figure and says whether it lies inside the published range.
- Golden: the benchmark parameters of 05 l.360 (risk weights market 4.1, credit 26.4, operational 69.5 percent; correlations market-credit 0.5, market and credit with operational 0.2) give `sqrt(w' R w) = 0.80624` and an additive overestimate of `1 / 0.80624 - 1 = 0.2403`: outside the published 30 to 40 percent, which is the point of the reference: the benchmark weights are the weights of simulated return components, not capital (computed; the published range itself is UNVERIFIED in its original, 05 l.542).

## Golden values: the published benchmark and the derived identities

- The one published benchmark of the unit is the Rosenberg and Schuermann reference run (05 l.360), a labelled reference, never a gate: weights `(4.1, 26.4, 69.5)` percent, correlations `0.5` and `0.2` under a normal copula. The inter-risk correlation ranges of Kuritzkes, Schuermann and Weiner (05 l.360, l.542), the Joint Forum wording (05 l.362) and the fallacy wording of Embrechts, McNeil and Straumann (05 l.366) are UNVERIFIED in the dossier and are not used as values.
- The rearrangement golden values are the printed Tables 1 and 4 of Embrechts, Puccetti and Ruschendorf (2013), above.
- Derived identities (SDD Oracles, item 4: not published values): Gaussian copula at `rho = 1` equals the comonotonic sum and at `rho = 0` the independent convolution; variance-covariance with `R = I` equals `sqrt(sum ec^2)` and with `R` all ones equals the sum; Gaussian copula with normal marginals equals the variance-covariance quantile within Monte Carlo error; the t tail dependence formula against `scipy.stats.t`; ES contributions add up exactly (the golden of the reused `es_contributions`: `S = 10`, group losses `[0, ..., 9]` and `[0, 2, ..., 18]`, `q = 0.9`: `es_from_sample = 27.0` and contributions `(9.0, 18.0)`); the AM and RM identities.
- Information, not capital: every figure of the band except the simple sum, the model risk measures, the Euler allocation and the diversification are information for the validator and never a capital claim (05 l.519); the document labels carry it (`status = "information-not-capital"`).

## Document mapping

| C18 block | Functions |
|---|---|
| `outputs.aggregation.marginals` | `oprisk.aggregate`, `oprisk.sma`, `irrbb.simulation.ear_evar`, `portfolio.portfolio.portfolio_from_groups` (reused), the C11 outputs scaled |
| `outputs.aggregation.band`, `headline` | `simple.simple_sum`, `simple.variance_covariance`, `copulas.copula_aggregate`, `bounds.worst_var_bounds`, `band.dependence_band` |
| `outputs.aggregation.model_risk` | `model_risk.barrieu_scandolo`, `model_risk.glasserman_xu_worst_case` |
| `outputs.aggregation.euler`, `diversification` | `portfolio.euler.es_contributions` (reused), `simple.diversification_factor`, `simple.euler_diversification_benefit` |
| `outputs.copula_sensitivity`, `rosenberg_schuermann`, `correlation_stress` | `validation.aggregation.copula_choice_sensitivity`, `rosenberg_schuermann_reference`, `correlation_stress` |
| `tests` | the eight functions of `riskvalidation/validation/aggregation.py` and `portfolio.euler_additivity` |
