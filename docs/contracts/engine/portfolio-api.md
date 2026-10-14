# Engine portfolio API contract: `engine-portfolio-api` 1.0.0

Owner: U7-S (unit sizing `plans/contraste/units/U7-sizing.md`, CAOS_MANAGE). Implemented by U7-E in `riskvalidation.portfolio` and
`riskvalidation.validation.portfolio` (repository CAOS_RiskValidation, release 0.07.000 or the number the integrator serialises); called by
the C10 bake (U7-P). The tests of every function are written by U7-E against this file: a function exists with exactly the signature below,
and each golden value or invariant is a test. Changing a signature, a unit or a golden value is a breaking change (a new major version of
this contract). Sources: dossier 04 (`wip/contraste/04-credit-risk-models-sota-2026-10-04.md`, sections C.4 for the Vasicek and ASRF model,
H.1 to H.8 for portfolio credit risk and the ladder table "Portfolio credit risk", rungs C1 to C6), dossier 05
(`wip/contraste/05-market-ccr-alm-liquidity-oprisk-stress-sota-2026-10-04.md`, G.4 for the Euler principle and G.5 for the validation tests of
an economic capital model) and dossier 08 (B.4 and rows 23 and 24 for the Federal Reserve charge-off series); the product SDD section 4
gives the acceptance row this contract serves ("Copula MC, CreditRisk+, GA, IS": MC converges to LHP as n grows; Euler contributions sum to
the total; the CreditRisk+ recursion matches MC; GA delta = 4.83; IS unbiased against plain MC) and section 5 the case C10.

The engine computes; it states no compliance claim. Nothing here is a Basel, CRR or supervisory requirement beyond what the dossier sections
cite; confidence levels, tolerances, light parameters and seeds are policy parameters the caller supplies or the function states. Every
constant and golden value below is transcribed from the dossier named on its line, computed from the existing engine functions
(`riskvalidation.engines.vasicek`, `riskvalidation.regulatory.irb`, release v0.06.000), or computed from a formula stated on its line and
labelled as computed. An item the dossier marks UNVERIFIED is marked UNVERIFIED here and is not silently decided.

## Conventions (all functions)

- Arrays are `numpy.ndarray` of `float64` (integers `int64`, flags `bool`). Shapes: `N` obligors, `G` groups of obligors, `F` systematic factors,
  `K` CreditRisk+ sectors, `S` scenarios, `M` loss units, `T` years, `R` replications.
- Rates, probabilities, loadings and confidence levels are decimals (a PD of 1% is `0.01`, a level of 99.9% is `0.999`). A **PD**, an **asset
  correlation** and an **observed loss rate** are open at every estimate site: `0 < x < 1`; a value outside raises `ValueError` (the Vasicek
  model has no value at 0 or 1, `engines.vasicek._check`). **LGD** is the expected LGD in `[0, 1]`.
- Money is a float in the portfolio currency; the currency code travels in the `Portfolio` and in the document (`currency`), never in a
  function. Money is never converted between currencies by the engine. Loss rates are per year; the horizon is one year.
- The loss is the default-mode loss of dossier 04 H.1: `L = sum_i EAD_i * LGD_i * D_i` with the expected LGD deterministic; the variance
  parameter `lgd_gamma` (`V[LGD] = gamma E[LGD](1 - E[LGD])`, Gordy and Lutkebohmert 2013 eq. 16) is used only by the granularity adjustment
  in 1.0.0. `EL = sum_i EAD_i E[LGD_i] PD_i`. `VaR_q(L) = inf{l : P(L <= l) >= q}`. `ES_q(L) = (1/(1-q)) int_q^1 VaR_u du`, which is
  `E[L | L >= VaR_q]` for a continuous loss (dossier 04 H.1; Acerbi and Tasche 2002). `EC_q = VaR_q - EL` (dossier 04 H.1, BCBS 2005
  explanatory note section 4.4).
- Sample estimators (the definition of this contract; the dossier gives the integral, not the estimator): for a sample of `S` losses sorted
  ascending `L_(1) <= ... <= L_(S)` and `k = ceil(q S - 1e-9)` (the tolerance guards `0.9 * 10 = 9.000000000000002`), `VaR = L_(k)` and
  `ES = (1/(1-q)) [ sum_{i>k} L_(i) / S + (k/S - q) L_(k) ]` (the Acerbi-Tasche weights: the boundary scenario carries the fractional mass, so
  the tail has exactly mass `1 - q`).
- Randomness: a function that draws takes an integer `seed` and uses `numpy.random.Generator(numpy.random.PCG64(seed))`; the result is
  reproducible for the same `(seed, n_scenarios, chunk_scenarios)`; a different chunk size gives a different but equally valid sample (the
  document records `chunk_size` in `simulation`). No function reads global state, the clock or the environment; inputs are never mutated and
  the functions return new arrays.
- Memory: a Monte Carlo function simulates in chunks of `chunk_scenarios` scenarios (default `100_000`), so one chunk holds
  `chunk_scenarios * N * 8` bytes of `float64` (about 0.8 GB at `N = 1000`, the bound the unit sizing states).
- Dataclasses are frozen. A function that cannot compute a value because data is missing raises `ValueError` with the reason, or (a
  validation function) returns the `not_evaluated` light with its reason in `notes` and `statistic`, `p_value` and `metric` all null; it never
  returns a placeholder number. A yearly loss rate that is `NaN` is a year the table lacks (a quarter missing from the Federal Reserve
  table); the validation and fit functions exclude it, count it (`n_missing` in `extras` or the fit) and never interpolate it.
- Tolerance: every golden value states its own tolerance or is exact; a golden stated to six decimals holds to `5e-7`.
- A validation function returns one `TestResult` of `riskvalidation`, serialised by `TestResult.to_dict()` (`core/result.py`) into a row that
  validates against `common/test-result` (the schema `docs/contracts/schemas/common/test-result.schema.json`): `test_id`, `model_id`,
  `segment`, `statistic`, `p_value`, `metric`, `h0`, `alternative`, `policy_version`, `alpha_amber`, `alpha_red`, `light`, `n`, `n_events`,
  `inputs_hash`, `reference`, `notes`, `extras`. A `not_evaluated` row has `statistic`, `p_value` and `metric` all null and its reason in
  `notes` (the variant schemas of C10 enforce it).
- The parameters of a light rule that are not alphas travel in `extras["thresholds"]`, a mapping from the parameter name to its value, beside
  `alpha_amber` and `alpha_red`; a view reads them from there to explain a light.
- **Cross-field checks run on every document the bake writes** (not only on the fixtures). What JSON Schema cannot compare (VaR not below EL, ES
  not below VaR, `EC = VaR - EL`, the Euler sums and the asymptotic anchor, the grid identities, the window labels, one currency per document,
  the IRB identity with its maturity treatment, the granularity identities, the Monte Carlo ladder) is one importable function,
  `tests/contracts_u7/c10_checks.py` `violations(doc) -> list[str]` (an empty list is a sound document; `document_violations(path)` reads a file).
  The C10 bake (U7-P) imports it from `tests/c10/` and fails on a non-empty list for every document under `data/derived/C10/`: a bake that
  produces ES below VaR, Euler rows that do not sum, an off-grid cell or windows that overlap does not pass its own tests. `c10_checks.violations`
  is part of this contract (`engine-portfolio-api` 1.0.0).
- An **illustrative** portfolio is constructed, never a bank's: its `label` is `"illustrative"` and the document carries it in the portfolio
  block and in the provenance input `illustrative-portfolio` (class `illustrative`); the engine only carries the label.

## Reused functions of the existing engine (release v0.06.000)

The new API reuses these and does not reimplement them. U7-E calls them; the goldens below are computed from them.

| Function | Reused for | Golden (computed from the function) |
|---|---|---|
| `riskvalidation.engines.vasicek.lhp_quantile(q, pd, rho)` | C1 VaR of the large homogeneous portfolio (dossier 04 C.4) | `lhp_quantile(0.999, 0.02, 0.15) = 0.176329`, `lhp_quantile(0.99, 0.02, 0.15) = 0.105587` |
| `riskvalidation.engines.vasicek.lhp_cdf(x, pd, rho)` | the fitted distribution function; the exceedance flags | `lhp_cdf(0.176329, 0.02, 0.15) = 0.999` |
| `riskvalidation.engines.vasicek.lhp_pdf(x, pd, rho)` | the likelihood of `asrf_fit`; the fitted density | `lhp_pdf(0.02, 0.02, 0.15) = 18.004184` |
| `riskvalidation.engines.vasicek.conditional_pd(pd, rho, z)` | the conditional PD of the copulas and of the ASRF contributions | `conditional_pd(0.02, 0.15, -1.387222) = 0.05` |
| `riskvalidation.engines.vasicek.implied_factor(default_rate, pd, rho)` | `implied_factors` (the Z-factor of dossier 04 C.4) | `implied_factor(0.05, 0.02, 0.15) = -1.387222` |
| `riskvalidation.regulatory.irb.capital_requirement(asset_class, pd, lgd, ...)` | the IRB comparison of the document (`irb_reference.k_irb`) | `capital_requirement("residential_mortgage", 0.02, 0.45).k = 0.070348` (correlation 0.15, no maturity adjustment) |
| `riskvalidation.regulatory.irb.correlation(asset_class, pd, ...)` | the IRB correlation of the loan type's class | `correlation("residential_mortgage", 0.02) = 0.15`; `correlation("qrre", 0.02) = 0.04` |

## How the documents use the engine

| Document block (schema) | Produced by |
|---|---|
| C10 loan-type `outputs.annual_rates`, `fit`, `profile_likelihood`, `fitted_distribution`; C10 correlation-grid `cells[*].estimators` | `asrf_fit.*` |
| C10 loan-type `outputs.backtest`; its `tests` row `portfolio.tail_backtest` | `validation.portfolio.tail_backtest` |
| C10 loan-type `outputs.irb_reference` (class, regime, maturity, maturity adjustment, `k_irb`, `ec_lhp_fitted` with the same maturity treatment) | `engines.vasicek`, `regulatory.irb` (reused) |
| C10 loan-type `outputs.portfolio` (groups, totals, concentration) | `portfolio.portfolio_from_groups`, `euler.hhi`, `euler.effective_names` |
| C10 loan-type `outputs.rungs` C1 | `portfolio.lhp_measures` |
| `outputs.rungs` C2 and C3 (the loss sample, VaR, ES and their standard errors) | `copula.simulate_gaussian`, `copula.simulate_student_t`, `portfolio.measures_from_sample`, `copula.mc_standard_errors` |
| `outputs.rungs` C4 | `creditrisk_plus.pmf_stable`, `creditrisk_plus.measures_from_pmf` |
| `outputs.rungs` C5 and `outputs.granularity` (`levels`, `k_star`) | `granularity.gamma_quantile`, `delta`, `granularity_adjustment` (with `K_i` from `regulatory.irb`), `k_creditrisk_plus` |
| `outputs.granularity.by_n_names[*].truth_ga` | `creditrisk_plus.pmf_stable` and `measures_from_pmf` of n identical names, minus `mu(alpha_q(X))` (null with its reason where not run) |
| `outputs.rungs` C6 | `importance.*` |
| `outputs.euler` (`anchor` is `euler.asrf_var_contributions`) | `euler.es_contributions`, `euler.var_contributions_kernel`, `euler.asrf_var_contributions`; its `tests` row `portfolio.euler_additivity` is `validation.portfolio.euler_additivity` |
| `tests` rows `portfolio.mc_convergence`, `portfolio.crp_recursion_vs_mc` | `validation.portfolio.mc_convergence`, `validation.portfolio.crp_recursion_vs_mc` |
| C10 correlation-grid `outputs.cells`; its `tests` row `portfolio.correlation_size_power` | the simulator of the bake with `asrf_fit.*`; `validation.portfolio.correlation_size_power` |

A rung that did not run is a not-evaluated row of the document (`evaluated` false, its `reason`, no measure and no curve): the bake writes it
when a function raises `ValueError` for the combination (importance sampling has no Student-t twist in 1.0.0) and never writes a number for
it.

## Module `riskvalidation/portfolio/portfolio.py`

The portfolio as data and its loss measures (dossier 04 H.1).

### `riskvalidation.portfolio.portfolio.Portfolio`

```python
@dataclass(frozen=True)
class Portfolio:
    ead: np.ndarray          # (N,) money, strictly positive
    pd: np.ndarray           # (N,) open (0, 1)
    lgd: np.ndarray          # (N,) expected LGD in [0, 1]
    loadings: np.ndarray     # (N, F) factor loadings beta_i; each row has beta_i' Sigma beta_i < 1 (Sigma = factor_corr)
    factor_corr: np.ndarray  # (F, F) correlation matrix of the factors (identity for F = 1), symmetric positive definite
    group: np.ndarray        # (N,) int64 index into group_ids
    group_ids: tuple[str, ...]
    lgd_gamma: float         # gamma of V[LGD] = gamma E[LGD] (1 - E[LGD]), >= 0
    currency: str            # ISO 4217
    label: str               # "illustrative" for a constructed portfolio
```

- Units: money in `currency`; PD, LGD and loadings decimals; `lgd_gamma` dimensionless.
- Invariants: `__post_init__` raises `ValueError` for a shape mismatch, `ead <= 0`, a PD outside the open interval, an LGD outside `[0, 1]`, a
  loading row with `beta_i' Sigma beta_i >= 1`, a `factor_corr` that is not a symmetric positive definite correlation matrix, a `group` index out
  of range, an empty `group_ids` entry or a `currency` that is not three capital letters. The arrays are copied and made read-only. In the
  one-factor case `F = 1`, `loadings[i, 0] = sqrt(rho_i)` and the asset correlation of two names is `loadings[i, 0] loadings[j, 0]`.
- Golden: the fixture portfolio (`docs/contracts/fixtures/c10/variant-loan-type-fixture.json`, `outputs.portfolio.groups`) has `N = 1060`
  names and `sum(ead) = 100000000.0`.

### `riskvalidation.portfolio.portfolio.portfolio_from_groups`

```python
def portfolio_from_groups(groups: Sequence[Mapping[str, Any]], currency: str, lgd_gamma: float,
                          factor_corr: np.ndarray | None = None, one_factor: bool = False,
                          label: str = "illustrative") -> Portfolio: ...
```

- Units: each group is a mapping with the keys of the document block `portfolio.groups` (`id`, `n_names`, `ead_each`, `pd`, `lgd`, `loading`,
  `sector`); `n_names` identical names are expanded per group in group order.
- Invariants: with `one_factor = True` every name loads on the single factor with its group's `loading` (`F = 1`); otherwise `F` is the
  number of distinct `sector` values in order of first appearance, a name loads on its sector's factor with its group's `loading`, and
  `factor_corr` (`F x F`) is required when `F > 1` (`ValueError` otherwise: the correlation between sectors is an input, never a default).
  `group_ids` are the group ids in order; `N = sum(n_names)`.
- Golden: the three groups of the fixture (10 names of 4000000.0, 50 of 600000.0 and 1000 of 30000.0 with PDs 0.0015, 0.0030, 0.0050 and LGD
  0.45) give `N = 1060`, `sum(ead) = 100000000.0` and, with `one_factor = True`, `F = 1`; `expected_loss` of it is `135000.0`.

### `riskvalidation.portfolio.portfolio.expected_loss`

```python
def expected_loss(p: Portfolio) -> float: ...
```

- Units: money in `p.currency`.
- Invariants: `sum_i ead_i lgd_i pd_i` (dossier 04 H.1, the independent-LGD case); linear in `ead`; zero only if every PD is zero (not allowed).
- Golden: the fixture portfolio gives `0.45 * (10*4000000*0.0015 + 50*600000*0.0030 + 1000*30000*0.0050) = 0.45 * (60000 + 90000 + 150000) = 135000.0`
  (hand-computed).

### `riskvalidation.portfolio.portfolio.LossMeasures`

```python
@dataclass(frozen=True)
class LossMeasures:
    level: float             # q in (0, 1)
    el: float
    var: float
    es: float | None         # None where the method defines no ES (the granularity adjustment)
    ec: float                # var - el
    var_se: float | None     # Monte Carlo standard error; None for an analytic method
    es_se: float | None
```

- Units: money in the portfolio currency for `el`, `var`, `es`, `ec`, `var_se`, `es_se`; `level` a decimal.
- Invariants: `ec = var - el` to `1e-9 * max(1, var)`; `var >= el - 1e-9`; `es >= var - 1e-9` when `es` is not None (JSON Schema cannot compare fields,
  so the C10 documents carry these as producer checks, `c10_checks.violations` on every baked document); `var_se` and `es_se` are both None or both set; they map one to
  one onto the document block `rungs[*].measures[*]` (`level`, `el`, `var`, `es`, `es_reason`, `ec`, `var_se`, `es_se`).

### `riskvalidation.portfolio.portfolio.lhp_measures`

```python
def lhp_measures(total_ead: float, lgd: float, pd: float, rho: float, levels: Sequence[float]) -> tuple[LossMeasures, ...]: ...
```

- Units: `total_ead` money, `lgd`, `pd`, `rho` decimals, `levels` decimals (0.99, 0.999); the result is in money, one `LossMeasures` per level, `var_se`
  and `es_se` None.
- Invariants: `el = total_ead lgd pd`; `var = total_ead lgd lhp_quantile(q, pd, rho)` (`engines.vasicek`, dossier 04 C.4); `es = total_ead lgd E[p(Z) | Z <= G(1 - q)]`,
  the expected shortfall of the loss fraction `p(Z)`, computed by quadrature (Simpson on `[G(1-q) - 12, G(1-q)]`, 4000 steps; tolerance `5e-6`),
  where `G` is the standard normal quantile; it is the large-portfolio limit, so the VaR of a finite portfolio sits above the LHP VaR by the granularity
  effect (the granularity adjustment is nonnegative, dossier 04 H.5). `EC` at 99.9% equals `total_ead` times the IRB form `K` of a retail
  class without maturity adjustment when `lgd` and `rho` are the IRB's (golden below).
- Golden: `total_ead = 1`, `lgd = 1`, `pd = 0.02`, `rho = 0.15`: at 0.99 `var = 0.105587`, `es = 0.135971`; at 0.999 `var = 0.176329`, `es = 0.209404`, `el = 0.02`,
  `ec = 0.156329`. With `lgd = 0.45`: `ec(0.999) = 0.45 * (0.176329 - 0.02) = 0.070348`, the IRB `K` of `capital_requirement("residential_mortgage", 0.02, 0.45)` (existing
  engine). The ES values are computed (quadrature, described above) and checked at `5e-6`.

### `riskvalidation.portfolio.portfolio.var_from_sample`

```python
def var_from_sample(losses: np.ndarray, q: float) -> float: ...
```

- Units: `losses` (S,) money, `q` decimal.
- Invariants: `L_(k)` with `k = ceil(q S - 1e-9)` (conventions); nondecreasing in `q`; `ValueError` for `S = 0`, a NaN loss or `q` outside `(0, 1)`; independent of the order of `losses`.
- Golden: `losses = [0, 1, ..., 9]`: `var_from_sample(q = 0.9) = 8.0`, `var_from_sample(q = 0.95) = 9.0`, `var_from_sample(q = 0.85) = 8.0`.

### `riskvalidation.portfolio.portfolio.es_from_sample`

```python
def es_from_sample(losses: np.ndarray, q: float) -> float: ...
```

- Units: as `var_from_sample`.
- Invariants: the Acerbi-Tasche estimator of the conventions; `es >= var` always; nondecreasing in `q`; the mean of the top `(1 - q) S` losses when `(1 - q) S` is an integer.
- Golden: `losses = [0, 1, ..., 9]`: `es_from_sample(q = 0.9) = 9.0`, `es_from_sample(q = 0.95) = 9.0`, `es_from_sample(q = 0.85) = 8.666667`
  (`(9/10 + (0.9 - 0.85) * 8) / 0.15 = 1.3 / 0.15`; hand-computed).

### `riskvalidation.portfolio.portfolio.measures_from_sample`

```python
def measures_from_sample(losses: np.ndarray, levels: Sequence[float], el: float, n_batches: int = 20) -> tuple[LossMeasures, ...]: ...
```

- Units: money; `el` the portfolio's expected loss (`expected_loss(p)`, supplied so the measure does not re-estimate it from the sample).
- Invariants: per level `var = var_from_sample`, `es = es_from_sample`, `ec = var - el`, and `var_se`, `es_se` from `copula.mc_standard_errors(losses, q, n_batches)`; for a sample with fewer than `10 * n_batches` losses (the batch requirement of `mc_standard_errors`) `var_se` and `es_se` are None, never an error and never a number; `var >= el`
  is not forced: a sample whose VaR falls below `el` (a toy sample) raises `ValueError` with the reason rather than returning a negative capital.
- Golden: `losses = [0, 1, ..., 9]`, `el = 4.5`, `levels = (0.9,)`: `var = 8.0`, `es = 9.0`, `ec = 3.5`.

## Module `riskvalidation/portfolio/copula.py`

Default-mode Monte Carlo of the Gaussian and Student-t copulas (dossier 04 H.3).

### `riskvalidation.portfolio.copula.LossSample`

```python
@dataclass(frozen=True)
class LossSample:
    losses: np.ndarray               # (S,) money
    group_losses: np.ndarray | None  # (S, G) money, columns in group_ids order; None unless asked
    n_scenarios: int
    seed: int
    chunk_scenarios: int
```

- Units: money in the portfolio currency.
- Invariants: `group_losses.sum(axis=1) == losses` to `1e-9 * max(1, losses)` when present; `losses >= 0`; `n_scenarios == len(losses)`; the fields map onto the document block `rungs[*].simulation` (`n_scenarios`, `seed`, `chunk_size = chunk_scenarios`).

### `riskvalidation.portfolio.copula.simulate_gaussian`

```python
def simulate_gaussian(p: Portfolio, n_scenarios: int, seed: int, chunk_scenarios: int = 100_000,
                      track_groups: bool = False) -> LossSample: ...
```

- Units: money; `n_scenarios`, `chunk_scenarios` positive integers.
- Invariants: the asset return `A_i = beta_i' Z + sqrt(1 - beta_i' Sigma beta_i) e_i` with `Z ~ N(0, factor_corr)` (Sigma = factor_corr, so `Var(A_i) = 1` and the marginal default probability is `PD_i` also when the factors are correlated; the scale without Sigma is right only for uncorrelated factors) and `e_i` independent `N(0, 1)`; name `i` defaults iff `A_i < G(PD_i)` and
  then loses `ead_i lgd_i` (dossier 04 H.3, Li 2000); the marginal default probability of each name is `PD_i` (within 4 Monte Carlo standard errors); the mean loss is `expected_loss(p)`
  within 4 standard errors; reproducible for the same `(seed, n_scenarios, chunk_scenarios)`; one chunk holds at most `chunk_scenarios * N * 8` bytes; `ValueError` for a
  non-positive count. For a portfolio of identical names with `F = 1`, `VaR_q / (sum ead * lgd)` converges to `lhp_quantile(q, pd, rho)` as `N` grows, within the Monte Carlo
  interval (the gate of rung C2, dossier 04 ladder).
- Golden: two names with `pd = 0.01` and `rho = 0.3` (loading `sqrt(0.3)`): the joint default probability is `0.000556` (computed: `E[p(Z)^2]` by quadrature,
  `p(z) = Phi((G(0.01) - sqrt(0.3) z) / sqrt(0.7))`), and the simulated fraction of scenarios in which both default lies within 4 standard errors of it at `S = 2e7` (tolerance `1e-5`).

### `riskvalidation.portfolio.copula.simulate_student_t`

```python
def simulate_student_t(p: Portfolio, nu: float, n_scenarios: int, seed: int, chunk_scenarios: int = 100_000,
                       track_groups: bool = False) -> LossSample: ...
```

- Units: as `simulate_gaussian`; `nu > 2` degrees of freedom (`ValueError` otherwise).
- Invariants: `A_i = sqrt(W) (beta_i' Z + sqrt(1 - beta_i' Sigma beta_i) e_i)` with `W = nu / chi2_nu` independent of `Z` and `e`, and name `i` defaults iff `A_i < t_nu^{-1}(PD_i)` (dossier 04 H.3,
  Frey and McNeil 2003; Demarta and McNeil 2005); the marginal default probability is `PD_i`; the joint default probability exceeds the Gaussian one for equal correlation (the gate
  of rung C3, dossier 04 ladder: tail dependence); as `nu -> infinity` the sample tends to `simulate_gaussian`'s.
- Golden: two names with `pd = 0.01`, `rho = 0.3` and `nu = 5`: the joint default probability is `0.001647` (computed by two-dimensional quadrature of the mixture representation,
  `0.0016473`, confirmed by `scipy.stats.multivariate_t.cdf`, and checked by simulation: `0.001653` with standard error `0.000009` at `S = 2e7`), above the Gaussian `0.000556`; tolerance `1e-5`.

### `riskvalidation.portfolio.copula.mc_standard_errors`

```python
def mc_standard_errors(losses: np.ndarray, q: float, n_batches: int = 20) -> tuple[float, float]: ...
```

- Units: money; returns `(se_var, se_es)`.
- Invariants: the sample is split in `n_batches` consecutive equal batches (the remainder dropped), `VaR` and `ES` are computed per batch with the sample estimators of the conventions, and the
  standard error is `sd(batch estimates, ddof=1) / sqrt(n_batches)` (the batch-means estimator; the estimator is the contract's choice, the dossier names none); both are positive for a
  non-degenerate sample, decrease as `1 / sqrt(S)` for a fixed `q` (a property test on `S = 1e5` and `4e5`), and are reproducible; `ValueError` for `n_batches < 2` or fewer than `10`
  losses per batch.
- Golden: `losses = [0, 1, ..., 9]` repeated 20 times (the same ten values in each of 20 batches of 10) gives `se_var = 0.0` and `se_es = 0.0` (every batch estimate is equal).

## Module `riskvalidation/portfolio/creditrisk_plus.py`

CreditRisk+ with `K` Gamma sectors (dossier 04 H.4; Haaf, Reiss and Schoenmakers 2004).

### `riskvalidation.portfolio.creditrisk_plus.CreditRiskPlusInput`

```python
@dataclass(frozen=True)
class CreditRiskPlusInput:
    nu: np.ndarray        # (N,) int64 >= 1, exposure in integer multiples of the loss unit
    pd: np.ndarray        # (N,) open (0, 1)
    w0: np.ndarray        # (N,) >= 0, weight on the idiosyncratic Poisson part
    weights: np.ndarray   # (N, K) >= 0, weights w_{k,i} on the sector factors; w0 + sum_k w_{k,i} = 1
    sigma2: np.ndarray    # (K,) > 0, variance of the Gamma sector factors S_k (mean 1)
    loss_unit: float      # money per unit
    currency: str
```

- Units: `nu` loss units, `loss_unit` money, weights and PDs decimals.
- Invariants: `__post_init__` raises `ValueError` unless `w0 + weights.sum(axis=1) = 1` to `1e-12`; `K = 0` (shape `(N, 0)`, empty `sigma2`) is the independent Poisson case. The intensity is
  `R_i = p_i (w0_i + sum_k w_{k,i} S_k)` and `X = sum_i nu_i Y_i`, `Y_i` Poisson (dossier 04 H.4).

### `riskvalidation.portfolio.creditrisk_plus.pmf_stable`

```python
def pmf_stable(inp: CreditRiskPlusInput, n_max: int) -> np.ndarray: ...
```

- Units: the result is `(n_max + 1,)` probabilities of `X = 0, 1, ..., n_max` loss units; the tail mass `1 - sum` is left out, never added to the last entry.
- Invariants: the coefficients of the probability generating function `G(z) = exp(sum_i w0_i p_i (z^{nu_i} - 1) - sum_k (1/sigma2_k) ln[1 - sigma2_k sum_i w_{k,i} p_i (z^{nu_i} - 1)])`
  (dossier 04 H.4) by the stable recursion of Haaf, Reiss and Schoenmakers (2004) (series expansions of `log` and `exp`; no subtraction of terms of opposite sign); every entry is `>= 0` (a
  negative entry is a bug, the gate of rung C4); `sum <= 1`; for `K = 0` equal to the direct convolution of the Poisson laws of `nu_i Y_i` to `1e-12`; the mean is `sum_i nu_i p_i`
  whatever the sectors (mean-one factors); the recursion and the Monte Carlo of the same Poisson-Gamma model agree within Monte Carlo error (`validation.portfolio.crp_recursion_vs_mc`).
  Limitations carried from the dossier: default mode only, deterministic recoveries, and the Poisson approximation can give several defaults of one obligor for a large PD.
- Golden (direct convolution, `K = 0`): `nu = (1, 2, 3)`, `pd = (0.1, 0.2, 0.3)`, `w0 = 1`: `pmf[0..7] = 0.548812, 0.054881, 0.112506, 0.175711, 0.027992, 0.034868, 0.028804, 0.006003`
  (`pmf[0] = exp(-0.6) = 0.548812`, `pmf[1] = exp(-0.6) * 0.1 = 0.054881`; computed by convolving the three Poisson laws), mean `1.4`. Golden (closed form, one sector): one obligor with `nu = 1`,
  `pd = 0.2`, `w0 = 0`, `w = 1`, `sigma2 = 0.5`: the negative binomial `pmf[0..3] = 0.826446, 0.150263, 0.020490, 0.002484`
  (`P(X = k) = Gamma(k + r) / (Gamma(r) k!) (1/(1 + s p))^r (s p / (1 + s p))^k` with `r = 1/s = 2`, `s = sigma2`, `p = 0.2`; computed). Tolerance `5e-7`.

### `riskvalidation.portfolio.creditrisk_plus.pmf_panjer`

```python
def pmf_panjer(inp: CreditRiskPlusInput, n_max: int) -> np.ndarray: ...
```

- Units: as `pmf_stable`.
- Invariants: the Panjer recursion advocated in the original CreditRisk+ document, kept only for comparison with the stable recursion (dossier 04 H.4: the recursion sums terms of opposite sign and is
  numerically unstable; it is never a result and no document field carries it); the same signature; it equals `pmf_stable` to `1e-10` on the two goldens above; entries are never clipped; the U7-E review found no negative entry on four harsh stress cases, the largest gap to `pmf_stable` being 2.8e-11, so no negative entry is promised or expected.
- Golden: on the two goldens of `pmf_stable`, `max |pmf_panjer - pmf_stable| < 1e-10`.

### `riskvalidation.portfolio.creditrisk_plus.measures_from_pmf`

```python
def measures_from_pmf(pmf: np.ndarray, loss_unit: float, levels: Sequence[float], el: float | None = None) -> tuple[LossMeasures, ...]: ...
```

- Units: `pmf` probabilities on the unit grid, `loss_unit` money, the result in money.
- Invariants: with `F(n) = cumsum(pmf)`, `k = min{n : F(n) >= q - 1e-12}` and `VaR = k loss_unit`; `ES = (1/(1-q)) [ sum_{n>k} n pmf(n) + (F(k) - q) k ] loss_unit` (the discrete form of the
  Acerbi-Tasche estimator); `el` defaults to `loss_unit * sum n pmf(n)`; `ValueError` when `F(n_max) < q` (the grid is too short, the reason names the missing mass); `var_se` and `es_se` None.
- Golden: `pmf = (0.5, 0.3, 0.2)`, `loss_unit = 1`: at `q = 0.8` `var = 1.0`, `es = 2.0`; at `q = 0.7` `var = 1.0`, `es = 1.666667`
  (`(2 * 0.2 + (0.8 - 0.7) * 1) / 0.3`; hand-computed); `el = 0.7`.

## Module `riskvalidation/portfolio/granularity.py`

The granularity adjustment of Gordy and Lutkebohmert (2013) (dossier 04 H.5; International Journal of Central Banking 9(3), pp. 37-46).

### `riskvalidation.portfolio.granularity.gamma_quantile`

```python
def gamma_quantile(xi: float, q: float) -> float: ...
```

- Units: `xi > 0` dimensionless, `q` a decimal; returns `alpha_q(X)`.
- Invariants: the `q`-quantile of the systematic factor `X ~ Gamma(shape = xi, rate = xi)` (mean 1, variance `1/xi`): this is the parametrisation that reproduces the paper's test vector
  `delta = 4.83` at `xi = 0.25`, `q = 0.999` (the other reading, variance `xi`, gives `delta = 1.0867`); confirmed on the paper (Gordy and Lutkebohmert 2013, p. 43: "X is gamma-distributed
  with mean 1 and variance 1/xi, where xi > 0 is the precision parameter", read by the U7-S review). Increasing in `q`; `alpha_q > 1` for `q` above the median.
- Golden: `gamma_quantile(0.25, 0.999) = 17.505777` (computed from the regularised incomplete gamma function; checked with `scipy.stats.gamma.ppf(0.999, a=0.25, scale=4)`).

### `riskvalidation.portfolio.granularity.delta`

```python
def delta(xi: float, q: float) -> float: ...
```

- Units: dimensionless.
- Invariants: `delta = (alpha_q - 1) (xi + (1 - xi) / alpha_q)` with `alpha_q = gamma_quantile(xi, q)` (Gordy and Lutkebohmert 2013 eq. 15, dossier 04 H.5).
- Golden: `delta(0.25, 0.999) = 4.8336` (computed `4.833601`; the paper states `4.83`, dossier 04 H.5: the test passes when `abs(delta - 4.83) < 0.005`).

### `riskvalidation.portfolio.granularity.lgd_variance`

```python
def lgd_variance(mean_lgd: np.ndarray, gamma: float) -> np.ndarray: ...
```

- Units: decimals.
- Invariants: `V[LGD] = gamma E[LGD] (1 - E[LGD])` (eq. 16); zero at `E[LGD]` equal to 0 or 1; `ValueError` for `gamma < 0` or `E[LGD]` outside `[0, 1]`.
- Golden: `lgd_variance(0.45, 0.25) = 0.061875` (`0.25 * 0.45 * 0.55`; dossier 04 H.5 states the form and a typical `gamma = 0.25`).

### `riskvalidation.portfolio.granularity.k_creditrisk_plus`

```python
def k_creditrisk_plus(pd: np.ndarray, lgd_mean: np.ndarray, omega: np.ndarray, alpha_q: float) -> np.ndarray: ...
```

- Units: decimals (`omega_i` in `[0, 1]` is the weight of name `i` on the systematic factor of the single-factor CreditRisk+ model); returns (N,) the UL capital per unit of EAD.
- Invariants: eq. 13 of Gordy and Lutkebohmert (2013, p. 45): `K_i = E[U_i | X = alpha_q(X)] - E[U_i] = E[LGD_i] PD_i omega_i (alpha_q - 1)`, which equals `E[LGD_i] (pi_i(alpha_q) - PD_i)` with
  `pi_i(x) = PD_i (1 + omega_i (x - 1))`; a helper for a caller that has `omega` and no IRB capital. The regulatory use takes `K_i` from the IRB formula instead (`granularity_adjustment`).
- Golden: `pd = 0.01`, `lgd_mean = 0.45`, `omega = 0.5`, `alpha_q = 17.505777`: `K = 0.45 * 0.01 * 0.5 * 16.505777 = 0.037138` (hand-computed; both forms agree).

### `riskvalidation.portfolio.granularity.GranularityResult`

```python
@dataclass(frozen=True)
class GranularityResult:
    ga: float            # the granularity adjustment of eq. 17, a share of EAD (eq. 9)
    k_star: float        # K* = sum_i s_i K_i, share of EAD
    delta: float
    alpha_q: float
    c: np.ndarray        # (N,) C_i of eq. 11
```

- Units: `ga` and `k_star` shares of EAD (decimals); maps onto the document block `granularity.levels[*]` (`q`, `alpha_q`, `delta`, `ga`; `ga_money = ga * total_ead`) and `granularity.k_star`.
- Invariants: `ga` is the adjustment to add to the loss rate of the infinitely granular portfolio, `GA = alpha_q(L_n) - mu(alpha_q(X))` (eq. 9, p. 41), already a share of EAD: it is **not** scaled by `K*`
  (the first draft read eq. 17 as a ratio to `K*` and multiplied by it; the U7-S review, blocker B1, refuted that on the paper); nonnegative for `q >= 0.99`.

### `riskvalidation.portfolio.granularity.granularity_adjustment`

```python
def granularity_adjustment(share: np.ndarray, k: np.ndarray, pd: np.ndarray, lgd_mean: np.ndarray, lgd_gamma: float,
                           xi: float, q: float = 0.999) -> GranularityResult: ...
```

- Units: `share` (N,) exposure shares `s_i` summing to 1, `k` (N,) the UL capital `K_i` per unit of EAD, `pd`, `lgd_mean` (N,) decimals, `lgd_gamma` and `xi` dimensionless.
- Invariants: the simplified GA of eq. 17 (p. 46): `ga = (1 / (2 K*)) sum_i s_i^2 C_i (delta (K_i + R_i) - K_i)` with `C_i = (V[LGD_i] + E[LGD_i]^2) / E[LGD_i]` (eq. 11), reserve `R_i = E[LGD_i] PD_i`,
  `K* = sum_i s_i K_i` and `delta = delta(xi, q)`. `K_i` is an input, as in the paper's regulatory algorithm (p. 47, algorithm step (iv): "Compute UL capital requirement K_i as a function of PD_i, E[LGD_i],
  and M_i by IRB formula"; p. 45: with `R_i` and `K_i` substituted the PD_i and omega_i inputs are eliminated). **The bake passes the IRB capital per unit of EAD at the regulatory correlation and the
  loan type's maturity** (`regulatory.irb.capital_requirement(...).k`, the document's `granularity.k_source = "irb-regulatory-correlation"`); `k_creditrisk_plus` (eq. 13) serves a caller that has `omega`
  instead. For `n` identical names `ga * n` is constant (`ga` is proportional to `1 / n`, `hhi = 1 / n`), `ga -> 0` as `n -> infinity`; `ValueError` for `share` not summing to 1 within `1e-9`, a negative
  `k`, or `K* = 0`. The exact GA (eq. 14) with second-order terms is not in 1.0.0.
- Golden: `delta = 4.8336` at `xi = 0.25`, `q = 0.999` (above); for `n = 10` identical names (`s = 0.1`, `pd = 0.01`, `E[LGD] = 0.45`, `gamma = 0.25`, `xi = 0.25`, `q = 0.999`, `k = 0.037138` from
  `k_creditrisk_plus` with `omega = 0.5`): `C = 0.5875`, `R = 0.0045`, `ga = 0.129817` of EAD and, at `n = 100`, `0.012982` (computed from eq. 17; the paper's own numbers for this portfolio are not in
  the dossier). Tolerance `5e-7`.

## Module `riskvalidation/portfolio/importance.py`

Importance sampling for the Gaussian copula (dossier 04 H.7; Glasserman and Li 2005). The transcription of the exponential twist and of the factor mean shift is marked UNVERIFIED in dossier 04 H.7
(the paper is paywalled); the contract therefore fixes the acceptance by **unbiasedness against plain Monte Carlo**, never by the form of the twist.

### `riskvalidation.portfolio.importance.twisted_pd`

```python
def twisted_pd(p: np.ndarray, c: np.ndarray, theta: float) -> np.ndarray: ...
```

- Units: `p` conditional default probabilities (decimals), `c` loss given default in money (`ead_i lgd_i`), `theta >= 0` per money unit; returns the twisted probabilities.
- Invariants: `p_theta = p exp(theta c) / (1 + p (exp(theta c) - 1))` (dossier 04 H.7); equals `p` at `theta = 0`; increasing in `theta`; stays in `(0, 1)`; `ValueError` for `theta < 0`.
- Golden: `p = 0.1`, `c = 1`, `theta = ln 2`: `p_theta = 0.2 / 1.1 = 0.181818`.

### `riskvalidation.portfolio.importance.solve_theta`

```python
def solve_theta(p: np.ndarray, c: np.ndarray, threshold: float) -> float: ...
```

- Units: money for `c` and `threshold`; returns `theta` per money unit.
- Invariants: the root `theta >= 0` of `sum_i c_i p_{theta,i} = threshold` (the twisted conditional mean loss equals the threshold, dossier 04 H.7); `0.0` when `sum_i c_i p_i >= threshold`;
  `ValueError` when `threshold >= sum_i c_i` (unreachable); deterministic (bracketed root finding with a fixed tolerance `1e-12`).
- Golden: `p = 0.1`, `c = 1`, `threshold = 2/11` (`= 0.181818...`, the twisted `p_theta` of `twisted_pd` at `theta = ln 2`) gives `theta = 0.693147` (`ln 2` exactly; a threshold rounded to `0.181818` gives `0.693146`).

### `riskvalidation.portfolio.importance.ImportanceResult`

```python
@dataclass(frozen=True)
class ImportanceResult:
    losses: np.ndarray        # (S,) money, drawn under the twisted measure
    weights: np.ndarray       # (S,) likelihood ratios dP/dQ, > 0
    factor_shift: np.ndarray  # (F,) mean shift of the systematic factor
    n_scenarios: int
    seed: int
    chunk_scenarios: int
```

- Units: money; weights dimensionless.
- Invariants: `mean(weights) = 1` within 4 standard errors (the first unbiasedness identity); `sum(weights * losses) / S = EL` within 4 standard errors (the second).

### `riskvalidation.portfolio.importance.importance_sample_gaussian`

```python
def importance_sample_gaussian(p: Portfolio, threshold: float, n_scenarios: int, seed: int,
                               factor_shift: np.ndarray | None = None,
                               chunk_scenarios: int = 100_000) -> ImportanceResult: ...
```

- Units: money for `threshold` (the loss level the twist targets, normally the plain-MC 99.9% VaR or the LHP VaR); `factor_shift` (F,) or None.
- Invariants: given the factor, defaults are drawn from the twisted conditional probabilities; the factor is drawn with mean `factor_shift` (None: the engine solves the shift deterministically
  by maximising the log of the zero-variance density, UNVERIFIED in dossier 04 H.7); the weight is the likelihood ratio `exp(-theta L + sum_i ln(1 + p_i (exp(theta c_i) - 1))) exp(-mu' z + mu' mu / 2)`
  for factor shift `mu` (identity-correlated factors; `ValueError` for a correlated `factor_corr`, the multi-factor twist is a failure mode of the ladder). **Unbiasedness against plain Monte Carlo is the
  acceptance test:** for any `factor_shift` and any `threshold`, the weighted tail probability `sum(weights * (losses > x)) / S` (divided by the scenario count `S`, never by the realised weight sum: the latter is itself random and biases a rare tail) agrees with the plain Monte Carlo estimate of `simulate_gaussian` within
  4 combined standard errors, and the weighted `VaR` and `ES` agree with the plain ones within the same bound. Only the Gaussian copula is supported: `ValueError("no Student-t twist")` for a
  Student-t portfolio request through the bake (the rung is then a not-evaluated row).
- Golden: for one name (`pd = 0.1`, `ead = lgd = 1`, `F = 1`, `rho = 0.3`) the weighted mean of `D` equals `0.1` and `mean(weights) = 1` within 4 standard errors at `S = 1e6`; the weighted mean of `1{L > 0.5}`
  equals the plain `0.1` (it is the same event).

### `riskvalidation.portfolio.importance.weighted_var_es`

```python
def weighted_var_es(res: ImportanceResult, q: float) -> tuple[float, float, float, float]: ...
```

- Units: money; returns `(var, es, se_var, se_es)`.
- Invariants: the weighted empirical quantile (smallest loss `x` with `1 - sum(weights * (losses > x)) / S >= q`, the tail probability divided by `S`, never by the realised weight sum) and the weighted Acerbi-Tasche ES with the same normalisation (tail mass `sum(weights * 1{L > VaR}) / S` plus the boundary mass); the standard errors by the batch-means estimator of
  `mc_standard_errors` on 20 consecutive batches; with unit weights `sum(weights) = S` and they equal the plain estimators.
- Golden: `losses = [0, 1, 2, 3]`, `weights = [1, 1, 1, 1]`, `q = 0.5`: `var = 1.0`, `es = 2.5`.

### `riskvalidation.portfolio.importance.variance_ratio`

```python
def variance_ratio(plain_se: float, is_se: float) -> float: ...
```

- Units: money for the standard errors; dimensionless result.
- Invariants: `(plain_se / is_se)^2`, the variance reduction at equal sample size (the number reported in `rungs[*].diagnostics` as `variance_ratio_vs_plain_mc`); `ValueError` for a non-positive `is_se`.
- Golden: `variance_ratio(0.002, 0.0005) = 16.0`.

## Module `riskvalidation/portfolio/euler.py`

Euler risk contributions (dossier 04 H.2; dossier 05 G.4; Tasche 2008) and the concentration measures (dossier 04 H.6).

### `riskvalidation.portfolio.euler.es_contributions`

```python
def es_contributions(group_losses: np.ndarray, losses: np.ndarray, q: float) -> np.ndarray: ...
```

- Units: `group_losses` (S, G) money, `losses` (S,) money with `group_losses.sum(axis=1) = losses`; returns (G,) money.
- Invariants: `RC_g = E[L_g | L >= VaR_q]` (dossier 04 H.2; dossier 05 G.4, `ES_alpha(L_i | L) = E[L_i | L >= q_alpha(L)]`) with the Acerbi-Tasche weights, so that `sum_g RC_g = es_from_sample(losses, q)`
  **exactly** (to `1e-9 * max(1, es)`: the full allocation property of the Euler principle); ties at the boundary share its fractional mass in input order; `ValueError` when the rows do not sum to `losses`.
- Golden: `S = 10`, group 1 losses `[0, 1, ..., 9]`, group 2 losses `[0, 2, ..., 18]`, `losses = 3 * [0, ..., 9]`, `q = 0.9`: `es_from_sample = 27.0` and `RC = (9.0, 18.0)`, sum `27.0`.

### `riskvalidation.portfolio.euler.var_contributions_kernel`

```python
def var_contributions_kernel(group_losses: np.ndarray, losses: np.ndarray, q: float, bandwidth: float | None = None) -> np.ndarray: ...
```

- Units: as `es_contributions`.
- Invariants: `RC_g = E[L_g | L = VaR_q]` estimated by the Nadaraya-Watson kernel estimator with a Gaussian kernel at `L = VaR_q` (Tasche 2009, dossier 04 H.2; VaR contributions by conditioning on a single sample point are
  noisy, dossier 05 G.4); the default bandwidth is Silverman's `1.06 sd(L) S^{-1/5}` (the dossier names the paper, not the bandwidth: UNVERIFIED, the choice is this contract's); every contribution is `>= 0`;
  `sum_g RC_g` agrees with `var_from_sample` within the document tolerance `0.01` (relative) at `S = 1e6` (the C10 documents state it in `var_sum_tolerance`); `sum_g RC_g = VaR` exactly is **not** promised (a
  kernel estimator is biased in the boundary), which is why the tolerance is a field of the document.
- Invariants (property): if `L_g = a_g L` for every group (the shares are constant) the estimate tends to `a_g VaR` as `S` grows; the estimate is invariant to the order of the scenarios.

### `riskvalidation.portfolio.euler.asrf_var_contributions`

```python
def asrf_var_contributions(ead: np.ndarray, pd: np.ndarray, lgd: np.ndarray, rho: np.ndarray | float, q: float) -> np.ndarray: ...
```

- Units: money for `ead`, decimals for `pd`, `lgd`, `rho`, `q`; returns (N,) money.
- Invariants: the asymptotic one-factor VaR contribution at the factor quantile, the anchor of the sample-based contributions: `RC_i = EAD_i LGD_i p_i(G(1 - q))` with
  `p_i(z) = Phi((G(pd_i) - sqrt(rho_i) z) / sqrt(1 - rho_i))` (dossier 04 C.4: the loss is monotone in `z`, so the loss quantile is the conditional mean at `z = G(1 - q)`). It is the first term of
  Emmer and Tasche (2005, Journal of Risk 7(2):85-101; arXiv cond-mat/0302402v5) eq. 2.17 times `u_j` (the asymptotic, portfolio-invariant part of their contribution; eq. 2.15 and 2.18), read on the
  paper by the U7-S review: it is **not** their full contribution, which adds granularity terms (eq. 2.17 under 2.12b) or their semi-asymptotic charge (Definition 3.1). The document names it
  `asrf-asymptotic`. The contributions sum to the ASRF (infinitely granular) VaR `sum_i EAD_i LGD_i p_i(G(1 - q))`, which for identical names equals `EAD LGD lhp_quantile(q, pd, rho)`; the sample VaR of a
  finite portfolio sits near it, not on it, and the document's `anchor.asrf_var` is the sum of its rows (`c10_checks` recomputes both).
- Golden (the asymptotic anchor): two names `ead = (60, 40)`, `lgd = 0.45`, `pd = (0.01, 0.05)`, `rho = 0.15`, `q = 0.999` (`G(0.001) = -3.090232`): `p = (0.110265, 0.313506)`,
  `RC = (2.977148, 5.643106)` and the sum `8.620255` (computed from `engines.vasicek.conditional_pd`; the U7-S review recomputed the same values from eq. 2.17).

### `riskvalidation.portfolio.euler.hhi`

```python
def hhi(ead: np.ndarray) -> float: ...
```

- Units: money in, a decimal in `[1/N, 1]` out.
- Invariants: `sum_i s_i^2` with `s_i = ead_i / sum_j ead_j` (dossier 04 H.6, a definition); equals `1/N` for equal exposures and `1` for one name; invariant to the scale of `ead`; `ValueError` for a non-positive total.
- Golden: `ead = (50, 30, 20)`: `hhi = 0.380000` (`0.25 + 0.09 + 0.04`).

### `riskvalidation.portfolio.euler.effective_names`

```python
def effective_names(ead: np.ndarray) -> float: ...
```

- Units: a count (not an integer).
- Invariants: `1 / hhi(ead)` (dossier 04 H.6); between `1` and `N`.
- Golden: `ead = (50, 30, 20)`: `effective_names = 2.631579`; the fixture portfolio's `effective_names` is `1 / hhi` of its names (`hhi = 0.01789`).

## Module `riskvalidation/portfolio/asrf_fit.py`

The fit of the Vasicek distribution to a series of yearly loss or default rates (dossier 04 C.4).

### `riskvalidation.portfolio.asrf_fit.AsrfFit`

```python
@dataclass(frozen=True)
class AsrfFit:
    pd: float
    rho: float
    log_likelihood: float
    converged: bool
    method: str       # "maximum-likelihood" or "moments"
    n_years: int      # rates used
    n_missing: int    # NaN rates excluded, never interpolated
```

- Units: decimals; the log-likelihood in nats.
- Invariants: `0 < pd < 1`, `0 < rho < 1`; maps onto the document blocks `fit.maximum_likelihood` and `fit.moments`.

### `riskvalidation.portfolio.asrf_fit.log_likelihood`

```python
def log_likelihood(rates: np.ndarray, pd: float, rho: float) -> float: ...
```

- Units: `rates` (T,) decimals per year, each in `(0, 1)` (NaN entries are excluded and counted by the callers; any other value outside raises `ValueError`).
- Invariants: `sum_t ln lhp_pdf(rate_t, pd, rho)` with `engines.vasicek.lhp_pdf` (the density of the large homogeneous portfolio's default fraction, dossier 04 C.4); permutation-invariant.
- Golden: `rates = (0.01, 0.02, 0.05)`, `pd = 0.02`, `rho = 0.15`: the densities are `34.661219, 18.004184, 3.517955` and `log_likelihood = 7.694105` (computed from `engines.vasicek.lhp_pdf`).

### `riskvalidation.portfolio.asrf_fit.fit_ml`

```python
def fit_ml(rates: np.ndarray) -> AsrfFit: ...
```

- Units: as `log_likelihood`.
- Invariants: the maximiser of `log_likelihood` over `(pd, rho)` in the open unit square (a bounded optimiser on the logit scale with a fixed start and tolerance, so the fit is deterministic); `converged` is
  False when the optimiser stops at its iteration cap or at a bound; the maximum is not below `log_likelihood` at any of 25 neighbouring points; `ValueError` for fewer than 3 usable years or for a series with
  zero spread (the correlation is not identified: the reason says so); NaN rates are excluded and counted in `n_missing`.
- Golden (recovery on a quasi-sample): `rates_t = lhp_quantile((t - 0.5)/T, 0.02, 0.15)` for `t = 1..T`, `T = 2000`, returns `pd = 0.019995` and `rho = 0.149917` (computed with a Nelder-Mead on the logit scale),
  recovering the generating `(0.02, 0.15)` to `1e-3`; tolerance `5e-5` on the printed values.

### `riskvalidation.portfolio.asrf_fit.fit_moments`

```python
def fit_moments(rates: np.ndarray) -> AsrfFit: ...
```

- Units: as `fit_ml`.
- Invariants: `pd = mean(rates)` and `rho` solves `E[L^2] = P(two obligors default) = Phi_2(G(pd), G(pd); rho) = mean(rates^2)` (the second moment of the large-portfolio default fraction is the joint default probability
  of two names, dossier 04 C.4); the joint probability is increasing in `rho`, so the root is unique when it exists; when `mean(rates^2) <= pd^2` (no excess dispersion) the correlation is not identified and the function raises
  `ValueError` with the reason (never returns 0); `log_likelihood` is evaluated at the moment estimates for comparison.
- Golden: `rates = (0.01, 0.02, 0.03)`: `pd = 0.02`, `mean(rates^2) = 0.000467` and `rho = 0.026880` (computed: root of `E[p(Z)^2] = 0.000467` by quadrature; tolerance `5e-7`).

### `riskvalidation.portfolio.asrf_fit.profile_likelihood`

```python
def profile_likelihood(rates: np.ndarray, rho_grid: np.ndarray) -> tuple[np.ndarray, np.ndarray]: ...
```

- Units: `rho_grid` (R,) strictly increasing in `(0, 1)`; returns `(log_likelihood, pd_at_rho)`, each (R,).
- Invariants: at each grid correlation the PD that maximises the likelihood (a one-dimensional bounded search); `max(log_likelihood) <= fit_ml(rates).log_likelihood + 1e-9`; when the grid contains the
  maximum-likelihood correlation the two are equal to `1e-6`; the arrays have the length of the grid (the document's three profile arrays have one length).
- Golden: on the quasi-sample of `fit_ml` the profile has its maximum at the grid point nearest `0.15` and is unimodal on `rho_grid = (0.02, 0.04, ..., 0.30)`.

### `riskvalidation.portfolio.asrf_fit.profile_interval`

```python
def profile_interval(rates: np.ndarray, level: float = 0.95) -> dict[str, tuple[float, float]]: ...
```

- Units: decimals; returns `{"pd": (low, high), "rho": (low, high)}`.
- Invariants: the likelihood-ratio interval: the parameter values whose profile log-likelihood is at least `max - chi2_1(level) / 2` (for `level = 0.95`, `chi2_1 = 3.841459` and the cutoff is `max - 1.920729`;
  the document stores it as `profile_likelihood.cutoff`); the interval contains the estimate; an endpoint that reaches the bound of the parameter space is returned as the bound and `ValueError` is not raised
  (the document keeps it inside `(0, 1)` by the bound used, `1e-4` and `0.9999`); deterministic.
- Golden: `chi2_1(0.95) / 2 = 1.920729` (`G(0.975)^2 / 2`, computed); the interval of `rho` on the quasi-sample of `fit_ml` contains `0.15`.

### `riskvalidation.portfolio.asrf_fit.bootstrap_interval`

```python
def bootstrap_interval(rates: np.ndarray, estimator: str, n_boot: int, seed: int, level: float = 0.95) -> dict[str, tuple[float, float]]: ...
```

- Units: `estimator` in `{"maximum-likelihood", "moments"}`; `n_boot >= 100`; returns the percentile intervals `{"pd": ..., "rho": ...}`.
- Invariants: a parametric bootstrap: fit the estimator, draw `n_boot` series of the same length with `z_t ~ N(0, 1)` and `rate_t = conditional_pd(pd, rho, z_t)`, refit each, and take the `(1 - level)/2` and
  `(1 + level)/2` percentiles of the refits; a refit that fails (moments with no excess dispersion) is dropped and counted; reproducible for the same `seed`; the interval is not required to contain the estimate for a skewed refit
  distribution (the document check is `ci_low <= estimate <= ci_high`, and the bake reports a failure rather than editing an interval).
- Golden: none beyond reproducibility; `n_boot = 200` on the quasi-sample returns identical intervals for equal seeds and different ones for different seeds.

### `riskvalidation.portfolio.asrf_fit.implied_factors`

```python
def implied_factors(rates: np.ndarray, pd: float, rho: float) -> np.ndarray: ...
```

- Units: `rates` (T,) decimals; returns (T,) standard normal factor values, NaN where the rate is NaN.
- Invariants: `engines.vasicek.implied_factor` elementwise (dossier 04 C.4: `z_t = (G(pd) - sqrt(1 - rho) G(rate_t)) / sqrt(rho)`); decreasing in the rate (a high loss rate is a low factor);
  `conditional_pd(pd, rho, z_t) = rate_t`; `ValueError` for a rate outside `(0, 1)`.
- Golden: `implied_factors((0.05,), 0.02, 0.15) = -1.387222` and `conditional_pd(0.02, 0.15, -1.387222) = 0.05` (computed from the existing engine).

## Module `riskvalidation/validation/portfolio.py`

The economic capital validation tests (dossier 05 G.5), each a `TestResult` row of `common/test-result` (`test_id` as named, `h0`, `alternative`, `policy_version`, `reference` always set; `light` in green,
amber, red, not_evaluated, error). The acceptance gates are Contraste internal gates, stated as such, not regulatory thresholds; each function states its light rule on a `- Light:` line with its parameters named so
that a view can explain a light. A test with no data returns `not_evaluated` with its reason in `notes`. `reference` is dossier 05 G.5 ("check the allocation sums to the total", the sensitivity checks) and the
source of each statistic.

### `riskvalidation.validation.portfolio.tail_backtest`

```python
def tail_backtest(realised: np.ndarray, pd: float, rho: float, levels: Sequence[float] = (0.95, 0.99, 0.999),
                  primary_level: float = 0.99, model_id: str | None = None, segment: str | None = None,
                  alpha_amber: float = 0.05, alpha_red: float = 0.01) -> TestResult: ...
```

- Units: `realised` (T,) yearly loss rates of the evaluation window, decimals per year (NaN for a year the table lacks, excluded and counted in `extras["n_missing"]`); `pd`, `rho` the fitted parameters (open (0, 1));
  `test_id = "portfolio.tail_backtest"`. `h0`: the number of evaluation years above the fitted `q`-quantile is Binomial(`n`, `1 - q`); `alternative`: more years exceed it than the fit says.
- Invariants: per level `fitted_quantile = lhp_quantile(level, pd, rho)`, `observed` = years with `rate > fitted_quantile`, `expected = n (1 - level)` and the upper binomial tail `P(X >= observed)` with success probability `1 - level`;
  `statistic` is the observed count at `primary_level`, `p_value` its upper tail, `metric` the expected count at `primary_level`; `extras["levels"]` lists `level`, `fitted_quantile`, `expected`, `observed`, `years_exceeding`
  (indexes into `realised`), `p_value` for every level; fewer than 1 usable year gives `not_evaluated`; `ValueError` for `primary_level` not in `levels`.
- Light: green when `p_value >= alpha_amber` (0.05), amber when `alpha_red <= p_value < alpha_amber` (0.01), red below `alpha_red`. The Binomial test on a few years has little power: the p-value is shown beside the counts.
- Golden: `pd = 0.003`, `rho = 0.06` (`lhp_quantile(0.99, 0.003, 0.06) = 0.012340`, `0.95: 0.007791`, `0.999: 0.020018`, computed from the existing engine), `realised = (0.0045, 0.0085, 0.0160, 0.0120, 0.0080, 0.0050)`:
  one year above the 99% quantile, `statistic = 1.0`, `metric = 0.06`, `p_value = 0.058520` (`1 - 0.99^6`), `light = "green"`. With `realised = (0.0045, 0.0085, 0.0160, 0.0230, 0.0080, 0.0050)`: two years,
  `p_value = 0.001460` (`1 - 0.99^6 - 6 * 0.01 * 0.99^5`), `light = "red"`.

### `riskvalidation.validation.portfolio.mc_convergence`

```python
def mc_convergence(estimate: float, se: float, anchor: float, quantity: str = "var", model_id: str | None = None,
                   segment: str | None = None, alpha_amber: float = 0.05, alpha_red: float = 0.01) -> TestResult: ...
```

- Units: `estimate`, `se`, `anchor` in the same unit (money or a loss rate); `quantity` in `{"var", "es", "ec"}` (a label for the notes); `test_id = "portfolio.mc_convergence"`. `h0`: the Monte Carlo estimate equals the
  analytic anchor (the LHP quantile of C1, or the CreditRisk+ recursion); `alternative`: it differs.
- Invariants: `statistic = (estimate - anchor) / se`, `p_value = 2 (1 - Phi(abs(statistic)))`, `metric = estimate - anchor`; `extras` carries `estimate`, `se`, `anchor`, `quantity`; `se <= 0` or a NaN input gives `not_evaluated`.
  The anchor is exact only for a large homogeneous portfolio: a finite portfolio's VaR is expected to sit above the LHP VaR by the granularity effect, so the bake compares an LHP-like portfolio (many equal names) and reports
  the granularity gap separately (dossier 04 H.5).
- Light: green when `p_value >= alpha_amber`, amber when `alpha_red <= p_value < alpha_amber`, red below `alpha_red`.
- Golden: `estimate = 0.1030`, `anchor = 0.1000`, `se = 0.0010`: `statistic = 3.0`, `p_value = 0.002700`, `metric = 0.003`, `light = "red"`; with `estimate = 0.1015`: `statistic = 1.5`, `p_value = 0.133614`, `light = "green"`.

### `riskvalidation.validation.portfolio.euler_additivity`

```python
def euler_additivity(contributions: np.ndarray, total: float, tolerance: float = 1e-6, model_id: str | None = None,
                     segment: str | None = None) -> TestResult: ...
```

- Units: `contributions` (G,) money, `total` money (the portfolio ES or VaR the contributions allocate), `tolerance` a relative decimal; `test_id = "portfolio.euler_additivity"`. `h0`: the Euler contributions add up to the total
  (dossier 05 G.4 and G.5: "check the allocation sums to the total").
- Invariants: `statistic = sum(contributions)`, `metric = abs(sum - total) / abs(total)`, `p_value` null; `extras` carries `sum`, `total` and `thresholds = {"tolerance": tolerance}`; `total = 0` gives `not_evaluated`. The ES
  contributions of `euler.es_contributions` pass at `1e-6`; the kernel VaR contributions are tested with the document tolerance (`0.01`).
- Light: green when `metric <= tolerance`, red above (no amber: an allocation either adds up or it does not).
- Golden: `contributions = (0.5, 0.3, 0.2)`, `total = 1.0`: `statistic = 1.0`, `metric = 0.0`, `light = "green"`; `contributions = (0.5, 0.3, 0.1)`: `statistic = 0.9`, `metric = 0.1`, `light = "red"`.

### `riskvalidation.validation.portfolio.crp_recursion_vs_mc`

```python
def crp_recursion_vs_mc(pmf: np.ndarray, mc_units: np.ndarray, model_id: str | None = None, segment: str | None = None,
                        alpha_amber: float = 0.05, alpha_red: float = 0.01) -> TestResult: ...
```

- Units: `pmf` (M + 1,) probabilities of `0..M` loss units from `creditrisk_plus.pmf_stable`, `mc_units` (S,) integer loss units of a Monte Carlo sample of the same Poisson-Gamma model; `test_id = "portfolio.crp_recursion_vs_mc"`.
  `h0`: the recursion's distribution is the Monte Carlo sample's distribution (the gate of rung C4, dossier 04 ladder).
- Invariants: `statistic = D = max_n |F_pmf(n) - F_mc(n)|` over `n = 0..M` (the Kolmogorov distance), `p_value = 2 sum_{j>=1} (-1)^(j-1) exp(-2 j^2 S D^2)` (the asymptotic Kolmogorov law, `1.0` at `D = 0`; conservative for a
  discrete null, the contract's definition), `metric = D`; `extras` carries `negative_entries`, the number of negative entries of `pmf` (the Panjer instability check: any negative entry makes the light `red` whatever the p-value);
  `S < 10` or a sample above `M` gives `not_evaluated` with the reason.
- Light: green when `p_value >= alpha_amber`, amber when `alpha_red <= p_value < alpha_amber`, red below `alpha_red` or with a negative entry.
- Golden: `pmf = (0.5, 0.3, 0.2)`, a sample with counts `(5, 3, 2)` of `0, 1, 2`: `statistic = 0.0`, `p_value = 1.0`, `light = "green"`; counts `(3, 3, 4)`: `D = 0.2`, `p_value = 0.818621` (asymptotic, `S = 10`), `light = "green"`.

### `riskvalidation.validation.portfolio.correlation_size_power`

```python
def correlation_size_power(rejected: np.ndarray, known_rho: float, null_rho: float, alpha: float = 0.05,
                           estimator: str | None = None, model_id: str | None = None, segment: str | None = None,
                           alpha_amber: float = 0.05, alpha_red: float = 0.01, power_green: float = 0.80,
                           power_amber: float = 0.50) -> TestResult: ...
```

- Units: `rejected` (R,) bool, one per valid replication, whether `H0: rho = null_rho` was rejected at level `alpha`; `known_rho`, `null_rho` open (0, 1); `test_id = "portfolio.correlation_size_power"`.
  `h0`: at `known_rho = null_rho` the rejection rate equals `alpha` (the size); at any other known correlation the rate is the power.
- Invariants: `rate = mean(rejected)`, `se = sqrt(rate (1 - rate) / R)` and the Wilson 95% interval (the document's `rejection_se`, `rejection_ci_low`, `rejection_ci_high`); the **size cell** (`known_rho` equal to `null_rho`
  to `1e-12`): `statistic = (rate - alpha) / sqrt(alpha (1 - alpha) / R)`, `p_value` two-sided normal, `metric = rate`; a **power cell**: `statistic` and `p_value` null, `metric = rate`; `extras` carries `role` (`size` or `power`),
  `known_rho`, `null_rho`, `rate`, `se`, `ci_low`, `ci_high`, `estimator` and `thresholds = {"power_green": ..., "power_amber": ...}`; `R < 1` gives `not_evaluated`. The simulator's replications are independent with one seeded stream each.
- Light: size cell: green when `p_value >= alpha_amber`, amber when `alpha_red <= p_value < alpha_amber`, red below `alpha_red`; power cell: green when `rate >= power_green` (0.80, the conventional power), amber when
  `rate >= power_amber` (0.50), red below. These are Contraste gates, stated as such.
- Golden: `R = 1000`, `rate = 0.052` at the size cell, `alpha = 0.05`: `statistic = 0.290191`, `p_value = 0.771671`, `metric = 0.052`, `light = "green"`; at a power cell with 830 rejections of 1000, `metric = 0.83`, `light = "green"`;
  with 400 of 1000, `metric = 0.4`, `light = "red"`.

## Golden values summary

| Value | Where | Source |
|---|---|---|
| LHP quantile 0.176329 (99.9%) and 0.105587 (99%) at pd 0.02, rho 0.15; LHP density 18.004184 at 0.02 | `lhp_measures`, `fit_ml` | existing engine `engines.vasicek` (computed), dossier 04 C.4 |
| IRB K 0.070348 = 0.45 * (0.176329 - 0.02) for residential_mortgage at pd 0.02, LGD 0.45 | `lhp_measures` and the IRB comparison | existing engine `regulatory.irb.capital_requirement` (computed), dossier 04 C.4 |
| LHP expected shortfall 0.135971 (99%) and 0.209404 (99.9%) at pd 0.02, rho 0.15 | `lhp_measures` | computed: the conditional mean of `p(Z)` given `Z <= G(1 - q)`, by quadrature (dossier 04 H.1 and C.4 definitions) |
| delta 4.8336 (paper 4.83) at xi 0.25, q 0.999; alpha_q 17.505777; K = 0.037138, C = 0.5875, ga 0.129817 of EAD at n = 10 | `granularity.*`, `k_creditrisk_plus` | dossier 04 H.5 (Gordy and Lutkebohmert 2013 eq. 13, 15, 16 and 17, read on the paper by the U7-S review); the example is computed |
| CreditRisk+ pmf 0.548812, 0.054881, 0.112506, 0.175711, 0.027992, 0.034868, 0.028804, 0.006003 for nu (1,2,3), pd (0.1,0.2,0.3) | `pmf_stable` | direct convolution, computed (dossier 04 H.4 PGF) |
| negative binomial 0.826446, 0.150263, 0.020490, 0.002484 (one obligor, one sector, sigma2 0.5) | `pmf_stable` | closed form, computed (dossier 04 H.4 PGF) |
| discrete VaR 1.0 and ES 2.0 (q 0.8), 1.666667 (q 0.7) of pmf (0.5, 0.3, 0.2) | `measures_from_pmf` | hand-computed (dossier 04 H.1 definition) |
| sample VaR 8.0, ES 9.0, 8.666667 on losses 0..9 | `var_from_sample`, `es_from_sample` | hand-computed (dossier 04 H.1 definition, Acerbi-Tasche weights) |
| Euler ES contributions (9.0, 18.0) sum 27.0 | `es_contributions` | hand-computed (dossier 05 G.4 formula) |
| ASRF VaR contributions 2.977148 and 5.643106, sum 8.620255 | `asrf_var_contributions` | computed from `engines.vasicek.conditional_pd` (dossier 04 C.4 and H.2; the first term of Emmer and Tasche 2005 eq. 2.17) |
| HHI 0.380000 and effective names 2.631579 for exposures (50, 30, 20) | `hhi`, `effective_names` | dossier 04 H.6, hand-computed |
| EL 135000.0 of the fixture portfolio | `expected_loss` | dossier 04 H.1, hand-computed |
| twisted PD 0.181818 and theta 0.693147 (threshold 2/11) | `twisted_pd`, `solve_theta` | dossier 04 H.7 formula (twist UNVERIFIED there), hand-computed |
| variance ratio 16.0 | `variance_ratio` | hand-computed |
| log-likelihood 7.694105 of rates (0.01, 0.02, 0.05) at pd 0.02, rho 0.15 | `log_likelihood` | existing engine `lhp_pdf` (computed) |
| moments rho 0.026880 for rates (0.01, 0.02, 0.03) | `fit_moments` | computed: root of `E[p(Z)^2] = mean(rates^2)` (dossier 04 C.4) |
| quasi-sample ML recovery 0.019995 and 0.149917 | `fit_ml` | computed (Nelder-Mead on the logit scale) |
| implied factor -1.387222 for rate 0.05 | `implied_factors` | existing engine `engines.vasicek.implied_factor` (computed) |
| joint default 0.000556 (Gaussian) and 0.001647 (Student-t, nu 5) at pd 0.01, rho 0.3 | `simulate_gaussian`, `simulate_student_t` | computed by quadrature (dossier 04 H.3 definitions); the t value checked by simulation 0.001653 +/- 0.000009 |
| binomial p-values 0.058520 and 0.001460 (6 years, 99%) | `tail_backtest` | closed form, computed (dossier 05 G.5 back-test) |
| z 3.0 with p 0.002700; z 1.5 with p 0.133614 | `mc_convergence` | closed form, computed |
| additivity metric 0.0 and 0.1 | `euler_additivity` | hand-computed (dossier 05 G.4 and G.5) |
| Kolmogorov distance 0.2 with p 0.818621 at S 10 | `crp_recursion_vs_mc` | closed form, computed |
| size z 0.290191 with p 0.771671; power 0.83 | `correlation_size_power` | closed form, computed |

Open items carried from the dossiers, never silently decided: the exponential twist and the factor mean shift of Glasserman and Li (2005) (UNVERIFIED in dossier 04 H.7: acceptance is unbiasedness against plain
Monte Carlo); the equation numbers of Tasche (2008) (UNVERIFIED in dossier 04 H.2); the kernel bandwidth of Tasche (2009); the page-level formulas of the CreditMetrics technical document (migration mode is not in
1.0.0); the multi-factor extension of the importance sampling (a failure mode of the ladder); the sector concentration adjustment of Pykhtin (2004) (UNVERIFIED in dossier 04 H.6, not implemented); the exact
granularity adjustment (eq. 14), random LGD in the copulas and CreditMetrics migration mode are not in 1.0.0. Settled by the U7-S review on the primary papers: the Gamma factor of the granularity adjustment (shape
and rate xi, p. 43), `K_i` (eq. 13, p. 45; the regulatory algorithm takes it from the IRB formula, p. 47), GA as a share of EAD (eq. 9, p. 41) and the asymptotic anchor as the first term of Emmer and Tasche (2005)
eq. 2.17.
