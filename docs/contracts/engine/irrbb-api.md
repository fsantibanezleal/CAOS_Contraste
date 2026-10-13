# Engine IRRBB API contract: `engine-irrbb-api` 1.0.0

Owner: U10-S (unit sizing `plans/contraste/units/U10-sizing.md`, CAOS_MANAGE). Implemented by U10-E in `riskvalidation.irrbb` and
`riskvalidation.validation.irrbb` (repository CAOS_RiskValidation); called by the C14 and C15 bakes (U10-P1, U10-P2). The tests of
every function are written by U10-E against this file: a function exists with exactly the signature below, and each golden value or
invariant is a test. Changing a signature, a unit or a golden value is a breaking change (a new major version of this contract).
Sources: dossier 05 (`wip/contraste/05-market-ccr-alm-liquidity-oprisk-stress-sota-2026-10-04.md`, section D.1 to D.7), dossier 01
(`wip/contraste/01-basel-pillar1-pillar2-framework-2026-10-04.md`, section H.1 to H.5: SRP31.82 to SRP31.129 and the shock tables),
dossier 03 (`wip/contraste/03-chile-cmf-iape-and-spain-bde-2026-10-04.md`, section F.1 and F.2: RAN 21-13 Annex 1) and dossier 08
(`wip/contraste/08-data-and-scenario-sources-2026-10-04.md`, C.2, C.7, E.2); the product SDD sections 2.2, 3, 4 (the IRRBB acceptance
row) and 5 (cases C14 and C15). The case documents this contract feeds are `c14-outputs`, `c14-models`, `c15-outputs`, `c15-models`
(`docs/contracts/schemas/c14/`, `c15/`).

The engine computes; it states no compliance claim. Nothing here is a Basel, EBA or CMF requirement beyond what the dossier sections
cite; policy parameters (thresholds, floors a supervisor may choose, light parameters) are supplied by the caller or stated by the
function. Every constant and table below is transcribed from the dossier named on its line; an item the dossier marks UNVERIFIED, or
that this contract reads in a way the dossier does not settle, is marked UNVERIFIED here and is not silently decided (list at the end).

## Conventions (all functions)

- Arrays are `numpy.ndarray` of `float64` (integers `int64`, flags `bool`). Shapes: `K = 19` buckets, `S = 6` shocks (the order of
  `SHOCKS` below), `T` observation dates, `J` replicating tranches, `P` simulated paths, `M` months.
- **Sign convention (stated in every document, required field `sign_convention`):** a positive delta EVE or delta NII is a **loss**
  (SRP31.129; dossier 01 H.4). Only losses are aggregated across currencies.
- **Rates** are decimals; discounting is continuously compounded, `DF(t) = exp(-R t)` (SRP31.129). **Shocks** are basis points.
  **Bucket midpoints** are years. **Money** is a float in the currency of the document block (the currency code travels in the
  document, never in a function); the engine never converts between currencies. A UF-indexed amount is a CLF amount; the caller
  converts it with the UF value of the date (`ur_currency.uf_value` in the C15 document).
- `SHOCKS = ("parallel-up", "parallel-down", "steepener", "flattener", "short-up", "short-down")`, the order of SRP31.119 Table 5 and
  SRP31.125 Table 6; every per-shock array and list follows it.
- Every function is pure and deterministic (no hidden state, no I/O, inputs never mutated); a function with randomness takes a `seed`
  and uses `numpy.random.default_rng(seed)`. Dataclasses are frozen. A function that cannot compute because data is missing raises
  `ValueError` with the reason, or (a validation function) returns the `not_evaluated` light with its reason in `notes` and
  `statistic`, `p_value` and `metric` all null; it never returns a placeholder number.
- Tolerance: every golden value states its own tolerance or is exact; a golden stated to six decimals holds to `5e-7`.
- A validation function returns one `TestResult` of `riskvalidation`, serialised by `TestResult.to_dict()` into a row that validates
  against `common/test-result` (the schema `docs/contracts/schemas/common/test-result.schema.json`): `test_id`, `model_id`, `segment`,
  `statistic`, `p_value`, `metric`, `h0`, `alternative`, `policy_version`, `alpha_amber`, `alpha_red`, `light`, `n`, `n_events`,
  `inputs_hash`, `reference`, `notes`, `extras`. The parameters of a light rule that are not alphas travel in `extras["thresholds"]`.
- Missing data: a currency with no shock-table entry is refused (`shock_size`) unless the caller supplies the size and its label; a
  call-report item the source lacks is the caller's nullable value with its reason (the document schema), never a number the engine
  invents; an NMD core share or maturity above its SRP31 Table 4 cap is cut to the cap and reported when the caller asks for the
  standardised treatment, and kept and flagged `above-cap` when the caller asks for an internal assumption.

## How the documents use the engine

| Document block (schema) | Produced by |
|---|---|
| C14 `outputs.curve`, C15 `outputs.curves` | `curves.bootstrap_zero_curve`, `zero_rates_at`, `fit_nelson_siegel`, `fit_svensson` |
| C14 and C15 `shape_bp`, `floor_bound_buckets`; C14 `shock_size`, C14 models `shock_tables`, `shock_shape`, C15 models `annex1_table` | `shocks.shock_curve`, `shock_table`, `shock_size`, `apply_floor` |
| C14 `nmd_segments`, C15 `nmd_segments`, `assumptions`, `cash_flows`; models `nmd_caps`, `multipliers` | `slotting.bucket_grid`, `slot_cash_flows`, `nmd_split`, `prepayment_cpr`, `term_deposit_redemption_rate` |
| C14 `ladder`; `scenarios[].shocks[]`, `eve_risk_measure`, `outlier`, `behavioural_comparison` | `eve_nii.repricing_gap`, `delta_nii_gap`, `duration_gap`, `eve`, `delta_eve`, `eve_risk_measure`, `delta_nii`, `outlier_test` |
| C15 `eve`, `nii`, `offset_rule`, `indexation_charge`, `cpi_scenario`, `thresholds`, `floors` | `eve_nii.cmf_pair`, `annex1_delta_nii`, `annex1_delta_eve`, `indexation_charge`, `prioritised_bank`, `shocks.apply_floor` |
| C14 and C15 models `nmd_models`, `nmd_parameter_changes`, `prepayment` | `behavioural.replicating_portfolio`, `weighted_average_maturity`, `deposit_beta_passthrough`, `prepayment_logit`, `fit_prepayment_logit` |
| rung 5 and 6 (dynamic NII, EaR, EVaR; not a block of a fixture yet) | `simulation.simulate_nii`, `hw1f_scenarios`, `dns_scenarios`, `ear_evar` |
| C14 and C15 `tests` | `riskvalidation.validation.irrbb.*` (rows of `common/test-result`) |

## Tables as data

The engine carries these as module data with their source; the product documents repeat them in the models documents
(`c14-models.shock_tables`, `c15-models.annex1_table`), and a test compares the two.

### SRP31.96 Table 3: the 19 buckets and their midpoints (dossier 01 H.4; dossier 03 F.2)

| Bucket | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Range | overnight | O/N to 1M | 1M to 3M | 3M to 6M | 6M to 9M | 9M to 1Y | 1Y to 1.5Y | 1.5Y to 2Y | 2Y to 3Y | 3Y to 4Y | 4Y to 5Y | 5Y to 6Y | 6Y to 7Y | 7Y to 8Y | 8Y to 9Y | 9Y to 10Y | 10Y to 15Y | 15Y to 20Y | over 20Y |
| Midpoint (years) | 0.0028 | 0.0417 | 0.1667 | 0.375 | 0.625 | 0.875 | 1.25 | 1.75 | 2.5 | 3.5 | 4.5 | 5.5 | 6.5 | 7.5 | 8.5 | 9.5 | 12.5 | 17.5 | 25.0 |

### SRP31.90 Table 2, the 2024 calibration (dossier 01 H.3; in force 2026-01-01; data January 2000 to December 2023; 99.9th percentile; rounding 25 bp)

| Shock (bp) | ARS | AUD | BRL | CAD | CHF | CNY | EUR | GBP | HKD | IDR | INR | JPY | KRW | MXN | RUB | SAR | SEK | SGD | TRY | USD | ZAR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Parallel | 400 | 350 | 400 | 200 | 175 | 225 | 225 | 275 | 225 | 400 | 325 | 100 | 225 | 400 | 400 | 275 | 275 | 175 | 400 | 200 | 325 |
| Short | 500 | 425 | 500 | 275 | 250 | 300 | 350 | 425 | 375 | 500 | 475 | 100 | 350 | 500 | 500 | 375 | 425 | 250 | 500 | 300 | 500 |
| Long | 300 | 300 | 300 | 175 | 200 | 150 | 200 | 250 | 200 | 300 | 225 | 100 | 225 | 200 | 300 | 250 | 200 | 225 | 300 | 225 | 300 |

### BCBS d368 Annex 2 Table 1, the 2016 calibration (dossier 01 H.3; data 2000 to 2015; 99th percentile of global factors; rounding 50 bp)

| Shock (bp) | ARS | AUD | BRL | CAD | CHF | CNY | EUR | GBP | HKD | IDR | INR | JPY | KRW | MXN | RUB | SAR | SEK | SGD | TRY | USD | ZAR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Parallel | 400 | 300 | 400 | 200 | 100 | 250 | 200 | 250 | 200 | 400 | 400 | 100 | 300 | 400 | 400 | 200 | 200 | 150 | 400 | 200 | 400 |
| Short | 500 | 450 | 500 | 300 | 150 | 300 | 250 | 300 | 250 | 500 | 500 | 100 | 400 | 500 | 500 | 300 | 300 | 200 | 500 | 300 | 500 |
| Long | 300 | 200 | 300 | 150 | 100 | 150 | 100 | 150 | 100 | 350 | 300 | 100 | 200 | 300 | 300 | 150 | 150 | 100 | 300 | 150 | 300 |

The dossier notes that the 2016 PDF text layer interleaves rows and that the row assignment was checked against the column count and the
EUR 200/250/100 and USD 200/300/150 values; the 2016 table is verified with that caveat. CLP is in neither table.

### RAN 21-13 Annex 1 Hoja 9: shock sizes in basis points (dossier 03 F.2)

| Basket | Parallel | Short | Long |
|---|---|---|---|
| canasta-1 | 200 | 300 | 150 |
| canasta-2 | 400 | 500 | 300 |
| CLP | 300 | 400 | 200 |
| UR-nii | 300 | - | - |
| UR-eve | 200 | 250 | 150 |

`-` in the source is `None`. Canasta 1 and 2 are the currency baskets of the market-risk chapter; the CLP column is the CLP delta EVE and
delta NII size (a single 300 bp parallel shock for CLP and CLF in delta NII); UR-eve is the delta EVE size of the UR currency.

### Scenario multipliers (SRP31.119 Table 5 and SRP31.125 Table 6; RAN 21-13 Annex 1 repeats both; dossier 01 H.4, dossier 03 F.2)

| Shock | parallel-up | parallel-down | steepener | flattener | short-up | short-down |
|---|---|---|---|---|---|---|
| gamma (prepayment) | 0.8 | 1.2 | 0.8 | 1.2 | 0.8 | 1.2 |
| u (term-deposit early redemption) | 1.2 | 0.8 | 0.8 | 1.2 | 1.2 | 0.8 |

As rows in the order of `SHOCKS`: gamma `| 0.8 | 1.2 | 0.8 | 1.2 | 0.8 | 1.2 |`, u `| 1.2 | 0.8 | 0.8 | 1.2 | 1.2 | 0.8 |`.

### SRP31 Table 4: NMD caps (dossier 01 H.4); RAN 21-13 Annex 1 repeats the numbers (dossier 03 F.2)

| Category (BCBS) | Category (Annex 1) | Cap on the core share | Cap on the average maturity of the core |
|---|---|---|---|
| retail-transactional | retail-operational | 0.9 | 5.0 years |
| retail-non-transactional | retail-non-operational | 0.7 | 4.5 years |
| wholesale | wholesale | 0.5 | 4.0 years |

## Module `riskvalidation/irrbb/curves.py`

Zero curves and curve fits (dossier 05 D.5; dossier 08 C.2). The engine implements them in NumPy and SciPy; QuantLib is at most an
optional test extra that cross-checks the discount factors.

### `riskvalidation.irrbb.curves.bootstrap_zero_curve`

```python
def bootstrap_zero_curve(tenors: np.ndarray, par_yields: np.ndarray, frequency: int = 2) -> np.ndarray: ...
```

- Units: `tenors` (T,) years, strictly increasing and positive (otherwise `ValueError`); `par_yields` (T,) decimals, bond-equivalent with
  `frequency` coupons per year; the result (T,) continuously compounded zero rates at the tenors.
- Invariants: a tenor of at most `1 / frequency` is read as a simple-interest money-market rate, `R = ln(1 + y t) / t`; later pillars
  are bootstrapped with linear interpolation of the par yield between pillars for the coupon dates (the stated interpolation); a flat
  par curve gives a flat zero curve; a missing tenor is simply absent from `tenors` (the document lists it in `missing_tenors`), never
  filled.
- Golden: a flat par curve `y = 0.04`, `frequency = 2` gives `R = 2 ln(1.02) = 0.039605` at every tenor.

### `riskvalidation.irrbb.curves.zero_rates_at`

```python
def zero_rates_at(tenors: np.ndarray, zero_rates: np.ndarray, at: np.ndarray) -> np.ndarray: ...
```

- Units: `tenors` (T,) years, `zero_rates` (T,) decimals, `at` (N,) years; the result (N,) decimals.
- Invariants: linear interpolation in tenor, flat extrapolation outside the grid; exact at the pillars; the 19 bucket midpoints are a
  valid `at`.
- Golden: `tenors = [1, 2]`, `zero_rates = [0.01, 0.03]`: `at = 1.5` gives `0.02`, `at = 0.5` gives `0.01`, `at = 3` gives `0.03`.

### `riskvalidation.irrbb.curves.discount_factors`

```python
def discount_factors(rates: np.ndarray, times: np.ndarray) -> np.ndarray: ...
```

- Units: `rates` (K,) decimals, `times` (K,) years; the result (K,) in (0, 1] for nonnegative rates.
- Invariants: `DF = exp(-R t)` (SRP31.129, dossier 01 H.4); `DF(0) = 1`; monotone decreasing in `R` and in `t` for positive `R`.
- Golden: `R = 0.02`, `t = 2.5` gives `0.951229`.

### `riskvalidation.irrbb.curves.nelson_siegel_yield`

```python
def nelson_siegel_yield(m: np.ndarray, beta0: float, beta1: float, beta2: float, tau: float) -> np.ndarray: ...
```

- Units: `m` (N,) maturities in years, `tau` years; the result (N,) decimals; `y(m) = b0 + b1 (1 - e^{-m/tau}) / (m/tau) + b2 ((1 - e^{-m/tau}) / (m/tau) - e^{-m/tau})` (Nelson and Siegel 1987; dossier 05 D.5).
- Invariants: the limit `m -> 0` is `beta0 + beta1`, the limit `m -> infinity` is `beta0`; the term at `m = 0` is evaluated by its limit, not by a division by zero.
- Golden: `beta = (0.05, -0.02, 0.01)`, `tau = 2.0`, `m = 1` gives `0.036065`; `m = 1e-9` gives `0.03`; `m = 1e9` gives `0.05`.

### `riskvalidation.irrbb.curves.svensson_yield`

```python
def svensson_yield(m: np.ndarray, beta0: float, beta1: float, beta2: float, beta3: float, tau1: float, tau2: float) -> np.ndarray: ...
```

- Units: as `nelson_siegel_yield`; the second hump term is `beta3 ((1 - e^{-m/tau2}) / (m/tau2) - e^{-m/tau2})` (Svensson 1994; dossier 05 D.5).
- Invariants: with `beta3 = 0` the result equals `nelson_siegel_yield(m, beta0, beta1, beta2, tau1)` for any `tau2 > 0`.
- Golden: the Nelson-Siegel golden above with `beta3 = 0`, `tau2 = 5.0` gives `0.036065` at `m = 1`.

### `riskvalidation.irrbb.curves.fit_nelson_siegel`

```python
@dataclass(frozen=True)
class NelsonSiegelFit:
    beta0: float
    beta1: float
    beta2: float
    tau: float
    rmse: float          # decimals

def fit_nelson_siegel(maturities: np.ndarray, yields: np.ndarray, tau_grid: np.ndarray | None = None) -> NelsonSiegelFit: ...
```

- Units: `maturities` (N,) years, `yields` (N,) decimals, `N >= 4` (otherwise `ValueError`); `tau_grid` years (default a fixed grid), the betas by least squares for each `tau` and the best `tau` kept.
- Invariants: deterministic; data generated by `nelson_siegel_yield` is recovered (RMSE below `1e-9`); the fit never mutates its inputs.
- Golden: yields generated with the Nelson-Siegel golden parameters at maturities `[0.5, 1, 2, 3, 5, 7, 10]` are recovered to `1e-8` in every beta and in `tau`.

### `riskvalidation.irrbb.curves.fit_svensson`

```python
@dataclass(frozen=True)
class SvenssonFit:
    beta0: float
    beta1: float
    beta2: float
    beta3: float
    tau1: float
    tau2: float
    rmse: float

def fit_svensson(maturities: np.ndarray, yields: np.ndarray) -> SvenssonFit: ...
```

- Units: as `fit_nelson_siegel` with `N >= 6`.
- Invariants: deterministic (a fixed start and tolerance); the RMSE is not above the Nelson-Siegel RMSE of the same data (the family nests it); a fit that does not converge raises `ValueError` rather than returning its last iterate.
- Golden: data generated by `svensson_yield` with `(0.05, -0.02, 0.01, 0.005, 2.0, 6.0)` over `[0.5, 1, 2, 3, 5, 7, 10, 20]` is recovered to an RMSE below `1e-6`.

### `riskvalidation.irrbb.curves.dns_loadings`

```python
def dns_loadings(maturities_months: np.ndarray, lam: float = 0.0609) -> np.ndarray: ...
```

- Units: `maturities_months` (N,) months, strictly positive; `lam` per month; the result (N, 3), the columns being the level loading `1`, the slope loading `(1 - e^{-lam m}) / (lam m)` and the curvature loading `(1 - e^{-lam m}) / (lam m) - e^{-lam m}` (Diebold and Li 2006; dossier 05 D.5).
- Invariants: `lam = 0.0609` per month is the Diebold-Li decay; the curvature loading is maximal at `m* = x* / lam` with `x* = 1.7933` the maximiser of `(1 - e^{-x}) / x - e^{-x}`, that is `m* = 29.447` months for the default decay. Dossier 05 D.5 says the decay "maximises the curvature loading at exactly 30 months"; a recomputation gives 29.447 months (the loading at 30 months is `0.298384` against a maximum of `0.298426`), so 30 months is the paper's rounded figure and the engine and this contract use the decay `0.0609`, not a decay solved for 30. UNVERIFIED against the NBER WP 10048 text.
- Golden: at `m = 30`: slope loading `0.459280`, curvature loading `0.298384`; at `m = 12`: `0.709464` and `0.227941`; at `m = 60`: `0.266588` and `0.240701`.

### `riskvalidation.irrbb.curves.dns_yield`

```python
def dns_yield(maturities_months: np.ndarray, level: float, slope: float, curvature: float, lam: float = 0.0609) -> np.ndarray: ...
```

- Units: factors are decimals; the result (N,) decimals, `y = level + slope * L_slope(m) + curvature * L_curv(m)`.
- Invariants: equals `dns_loadings(m, lam) @ [level, slope, curvature]`; the long-maturity limit is `level`.
- Golden: `(0.05, -0.02, 0.01)` at `m = 30` gives `0.043798`.

### `riskvalidation.irrbb.curves.fit_dns_factors`

```python
def fit_dns_factors(maturities_months: np.ndarray, yields: np.ndarray, lam: float = 0.0609) -> np.ndarray: ...
```

- Units: `maturities_months` (N,), `yields` (T, N) decimals, `N >= 3`; the result (T, 3) factors (level, slope, curvature) by least squares at each date.
- Invariants: exact recovery of yields generated by `dns_yield` (to `1e-10`); rows are independent of one another; deterministic.
- Golden: yields generated by `dns_yield(m, 0.05, -0.02, 0.01)` at `m = [3, 12, 24, 60, 120]` return `[0.05, -0.02, 0.01]`.

### `riskvalidation.irrbb.curves.forecast_dns_factors`

```python
def forecast_dns_factors(factors: np.ndarray, horizon: int, n_paths: int, seed: int) -> np.ndarray: ...
```

- Units: `factors` (T, 3) history; `horizon` months; the result (P, horizon, 3) simulated factor paths from an AR(1) fitted to each factor (Diebold and Li 2006: level, slope and curvature as AR(1) factors).
- Invariants: deterministic given `seed`; with a history of zero residual variance every path equals the conditional mean path; the first step of every path depends only on the last row of `factors`; only data up to the last row is used (no look-ahead).
- Golden: a constant history `[[0.05, -0.02, 0.01]] * 12` gives every path equal to that row at every step.

## Module `riskvalidation/irrbb/shocks.py`

The six SRP31 shock shapes, the size tables as data, the CMF table, the post-shock floors (dossier 01 H.2 and H.3; dossier 03 F.2).

### `riskvalidation.irrbb.shocks.shock_scalars`

```python
def shock_scalars(midpoints: np.ndarray, x: float = 4.0) -> tuple[np.ndarray, np.ndarray]: ...
```

- Units: `midpoints` (K,) years; `x` years (4 for most currencies, SRP31.91 footnote 8, unless a supervisor determines otherwise); returns `(alpha_short, alpha_long)` with `alpha_short = exp(-t / x)` and `alpha_long = 1 - exp(-t / x)`.
- Invariants: `alpha_short + alpha_long = 1`; `alpha_short` is decreasing in `t`; both lie in (0, 1].
- Golden (SRP31.92, dossier 01 H.2): at `t = 3.5`, `x = 4`: `alpha_short = 0.417` (exactly `0.416862`) and `alpha_long = 0.583`.

### `riskvalidation.irrbb.shocks.shock_curve`

```python
def shock_curve(shock: str, parallel_bp: float, short_bp: float, long_bp: float, midpoints: np.ndarray, x: float = 4.0) -> np.ndarray: ...
```

- Units: sizes in basis points, nonnegative (otherwise `ValueError`); `midpoints` (K,) years; the result (K,) basis points. `parallel` is `+-parallel_bp`; `short` is `+-short_bp alpha_short`; steepener is `-0.65 |short| + 0.9 |long|`; flattener is `+0.8 |short| - 0.6 |long|`, with `|long| = long_bp alpha_long` (SRP31.90 to SRP31.92, dossier 01 H.2).
- Invariants: `shock` is one of `SHOCKS` (else `ValueError`); parallel shocks are constant; `short-up = -short-down`; the long shock enters only inside the rotations.
- Golden (SRP31.92, dossier 01 H.2): with `short_bp = long_bp = 100` at `t = 3.5`: `short-up` gives `+41.7` bp, steepener gives `+25.4` bp and flattener gives `-1.6` bp (unrounded `41.686`, `25.386`, `-1.639`; the tolerance is the printed precision, `0.05` bp). At the 19 midpoints the USD 2024 parallel-up shock is `200` at every bucket.

### `riskvalidation.irrbb.shocks.shock_table`

```python
def shock_table(calibration: str) -> dict[str, tuple[float, float | None, float | None]]: ...
```

- Units: `calibration` in `{"2024", "2016", "cmf-annex1"}`; the result maps a currency (ISO code; for `cmf-annex1` the baskets `canasta-1`, `canasta-2`, `CLP`, `UR-nii`, `UR-eve`) to `(parallel_bp, short_bp, long_bp)` in basis points, `None` where the source has `-`.
- Invariants: the 2024 and 2016 tables have exactly the 21 currencies of the tables above in table order and no CLP; the CMF table has exactly the five rows above; an unknown calibration raises `ValueError`.
- Golden: `shock_table("2024")["USD"] = (200, 300, 225)`, `shock_table("2016")["USD"] = (200, 300, 150)`, `shock_table("2016")["EUR"] = (200, 250, 100)`, `shock_table("cmf-annex1")["UR-nii"] = (300, None, None)`.

### `riskvalidation.irrbb.shocks.shock_size`

```python
@dataclass(frozen=True)
class ShockSize:
    currency: str
    parallel_bp: float
    short_bp: float
    long_bp: float
    origin: str                  # srp31-table-2024 | srp31-table-2016 | cmf-annex1 | contraste-estimate
    label: dict | None           # {"en": ..., "es": ...}, set only for contraste-estimate
    method: str | None

def shock_size(currency: str, calibration: str, estimate: tuple[float, float, float, dict, str] | None = None) -> ShockSize: ...
```

- Units: `currency` an ISO 4217 code (`CLF` for the UR currency); `estimate` is `(parallel_bp, short_bp, long_bp, label, method)`; the result serialises to the `ShockSize` object of the case schemas.
- Invariants: a currency with an entry returns that entry with the origin of the calibration; a currency **without** an entry raises `ValueError` unless `estimate` is supplied, in which case the result has `origin = "contraste-estimate"`, the label and the method (an estimate with an empty label or method raises `ValueError`); a CLP size is never invented (dossier 01 H.3: use the CMF prescription, or reproduce SRP98.56 to SRP98.63 on BCCh yield data and label it a Contraste estimate); the schema fails a tabled size that carries a label and an untabled size that does not.
- Golden: `shock_size("USD", "2024") = (200, 300, 225)` with origin `srp31-table-2024`; `shock_size("CLP", "2024")` raises `ValueError`; `shock_size("CLP", "cmf-annex1")` gives `(300, 400, 200)` with origin `cmf-annex1`; `shock_size("CLF", "cmf-annex1")` gives `(200, 250, 150)`.

### `riskvalidation.irrbb.shocks.apply_floor`

```python
def apply_floor(base_rates: np.ndarray, shock_bp: np.ndarray, floor: float | np.ndarray | None) -> np.ndarray: ...
```

- Units: `base_rates` (K,) decimals, `shock_bp` (K,) basis points, `floor` a decimal (SRP31.93: a floor not above zero; RAN 21-13 Annex 1: `-0.02` for UR rates and `0.0` for other currencies) or an array (K,) for a maturity-dependent floor, or `None` for no floor; the result (K,) decimals, `max(r0 + shock / 1e4, min(floor, r0))`.
- Invariants: with `floor = None` the result is `r0 + shock / 1e4`; the result is never below `min(floor, r0)` (a floor never lifts a rate above its pre-shock value; the reading of Annex 1 "or the pre-shock rate if lower" as applying to the UR floor too is UNVERIFIED); a rate that is already below the floor is left at its pre-shock value.
- Golden: `apply_floor(0.004, -300, 0.0) = 0.0`; `apply_floor(-0.001, -300, 0.0) = -0.001`; `apply_floor(0.03, -300, 0.0) = 0.0`; `apply_floor(0.004, -300, -0.02) = -0.026` is floored to `-0.02`.

### `riskvalidation.irrbb.shocks.eu_floor`

```python
def eu_floor(maturity_years: np.ndarray) -> np.ndarray: ...
```

- Units: `maturity_years` (N,) years, nonnegative; the result (N,) decimals: the maturity-dependent post-shock floor of Commission Delegated Regulation (EU) 2024/856 Article 3(7), `-0.015` at immediate maturity rising `0.0003` per year to `0` at 50 years (dossier 01 H.5).
- Invariants: nondecreasing in maturity; equal to `0` from 50 years; usable as the array `floor` of `apply_floor`.
- Golden: `eu_floor(0) = -0.015`, `eu_floor(10) = -0.012`, `eu_floor(50) = 0.0`, `eu_floor(60) = 0.0`.

## Module `riskvalidation/irrbb/slotting.py`

The 19 buckets, notional repricing cash flows, NMD, prepayment and term deposits (SRP31.96 to SRP31.126; dossier 01 H.4).

### `riskvalidation.irrbb.slotting.bucket_grid`

```python
@dataclass(frozen=True)
class BucketGrid:
    midpoints: np.ndarray    # (19,) years
    lower: np.ndarray        # (19,) years, exclusive
    upper: np.ndarray        # (19,) years, inclusive; the last is infinity
    labels: tuple[str, ...]

def bucket_grid() -> BucketGrid: ...
```

- Units: years.
- Invariants: 19 buckets; the midpoints are the SRP31.96 Table 3 values in the table above; `upper[k] = lower[k + 1]`; the edges are `0, 1/360, 1/12, 3/12, 6/12, 9/12, 1, 1.5, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20, infinity` (derived from the range labels of Table 3; the upper edge of the overnight bucket as `1/360` is UNVERIFIED, it is consistent with the midpoint 0.0028).
- Golden: `midpoints = [0.0028, 0.0417, 0.1667, 0.375, 0.625, 0.875, 1.25, 1.75, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5, 12.5, 17.5, 25.0]`.

### `riskvalidation.irrbb.slotting.bucket_of`

```python
def bucket_of(time_years: float, grid: BucketGrid | None = None) -> int: ...
```

- Units: `time_years >= 0` (negative raises `ValueError`); the result is the bucket number 1 to 19.
- Invariants: intervals are `(lower, upper]` with time 0 in bucket 1; the function is nondecreasing in time; the result is always in 1 to 19 (a time beyond 20 years is bucket 19).
- Golden: `bucket_of(0) = 1`, `bucket_of(0.5) = 4`, `bucket_of(0.75) = 5`, `bucket_of(20) = 18`, `bucket_of(20.5) = 19`, `bucket_of(25) = 19`.

### `riskvalidation.irrbb.slotting.slot_cash_flows`

```python
def slot_cash_flows(times: np.ndarray, amounts: np.ndarray, grid: BucketGrid | None = None) -> np.ndarray: ...
```

- Units: `times` (N,) years, `amounts` (N,) money (assets positive, liabilities negative); the result (19,) net notional repricing cash flows by bucket.
- Invariants: the sum of the result equals the sum of `amounts`; slotting is additive; an empty input gives zeros.
- Golden: `times = [0.5, 2.5, 9.5]`, `amounts = [100, -30, -70]` gives flows in buckets 4, 9 and 16 (`[0, 0, 0, 100, 0, 0, 0, 0, -30, 0, 0, 0, 0, 0, 0, -70, 0, 0, 0]`), the three-bucket sheet below.

### `riskvalidation.irrbb.slotting.nmd_split`

```python
@dataclass(frozen=True)
class NmdSlotting:
    flows: np.ndarray            # (19,) money magnitudes, the sign is the caller's
    core_share_used: float
    core_maturity_used: float    # years
    share_flag: str              # within-cap | above-cap
    maturity_flag: str
    capped: bool

def nmd_split(balance: float, category: str, core_share: float, core_maturity_years: float,
              enforce_caps: bool = True, grid: BucketGrid | None = None) -> NmdSlotting: ...
```

- Units: `balance >= 0` money; `category` in `retail-transactional`, `retail-non-transactional`, `wholesale` (the Annex 1 names `retail-operational` and `retail-non-operational` are accepted aliases); `core_share` in [0, 1]; `core_maturity_years >= 0`.
- Invariants: the non-core part `(1 - share) balance` goes to bucket 1; the core part is slotted in the two buckets around `core_maturity_years` so that its weighted average maturity is `core_maturity_years`; the total of `flows` is `balance`; with `enforce_caps` the share and the maturity are cut to the SRP31 Table 4 caps and `capped` is true when either was cut (the cap is applied and reported, SDD section 3, family `balance_sheet`); without it the values are used as stated and flagged `above-cap` (an internal assumption beyond the standardised cap, which the document schema accepts only with the flag); a flag agrees with the value (`within-cap` at or below the cap).
- Golden (SRP31 Table 4, dossier 01 H.4): `balance = 100`, `retail-transactional`, `core_share = 0.9`, `core_maturity_years = 5.0`: bucket 1 gets `10`, bucket 11 (4.5 y) `45` and bucket 12 (5.5 y) `45`, both flags `within-cap`. `balance = 100`, `wholesale`, `core_share = 0.6`, `core_maturity_years = 4.0` with `enforce_caps = True`: `core_share_used = 0.5`, `share_flag = "above-cap"`, `capped = True`; with `enforce_caps = False`: `core_share_used = 0.6`, `share_flag = "above-cap"`, `capped = False`.

### `riskvalidation.irrbb.slotting.prepayment_cpr`

```python
def prepayment_cpr(shock: str, cpr0: float) -> float: ...
```

- Units: `cpr0` an annual decimal in [0, 1]; the result `min(1, gamma_shock * cpr0)` with gamma from SRP31.119 Table 5 (0.8, 1.2, 0.8, 1.2, 0.8, 1.2 in the order of `SHOCKS`).
- Invariants: the result is in [0, 1]; an unknown shock raises `ValueError`. The cash flows `CF^p(k) = CF^s(k) + CPR N^p(k-1)` of SRP31.121 are the caller's slotting; the definition of the outstanding notional `N^p(k-1)` is UNVERIFIED (dossier 01 H.4 gives the formula without it).
- Golden (SRP31.119 Table 5): `prepayment_cpr("parallel-up", 0.05) = 0.04`; `prepayment_cpr("parallel-down", 0.05) = 0.06`; `prepayment_cpr("parallel-down", 0.9) = 1.0`.

### `riskvalidation.irrbb.slotting.smm_from_cpr`

```python
def smm_from_cpr(cpr: float) -> float: ...
```

- Units: decimals per year to decimals per month; `SMM = 1 - (1 - CPR)^(1/12)` (Fuster, Lucca and Vickery 2022; dossier 05 D.4).
- Invariants: `cpr_from_smm(smm_from_cpr(c)) = c`; `smm_from_cpr(0) = 0` and `smm_from_cpr(1) = 1`; a CPR outside [0, 1] raises `ValueError`.
- Golden: `smm_from_cpr(0.06) = 0.005143`.

### `riskvalidation.irrbb.slotting.cpr_from_smm`

```python
def cpr_from_smm(smm: float) -> float: ...
```

- Units: decimals per month to decimals per year; `CPR = 1 - (1 - SMM)^12`.
- Invariants: the inverse of `smm_from_cpr` to `1e-12`.
- Golden: `cpr_from_smm(0.005143) = 0.060000` to `1e-6`.

### `riskvalidation.irrbb.slotting.psa_cpr`

```python
def psa_cpr(month: int | np.ndarray, psa_percent: float = 100.0) -> float | np.ndarray: ...
```

- Units: `month >= 1` of the loan's age; `psa_percent` a percentage of the benchmark; the result an annual CPR decimal, `psa_percent / 100 * min(0.002 month, 0.06)` (100 percent PSA is 0.2 percent in month 1, rising 0.2 percent a month to 6 percent at month 30; dossier 05 D.4; the SIFMA primary text was not retrieved, UNVERIFIED against it).
- Invariants: nondecreasing in `month`; flat from month 30; linear in `psa_percent` before the cap of the benchmark.
- Golden: 100 percent PSA: `month = 1` gives `0.002` (0.2 percent), `month = 30` gives `0.06` (6.0 percent), `month = 60` gives `0.06`; 150 percent PSA: `month = 20` gives `0.06`, `month = 40` gives `0.09`.

### `riskvalidation.irrbb.slotting.term_deposit_redemption_rate`

```python
def term_deposit_redemption_rate(shock: str, tdrr0: float) -> float: ...
```

- Units: `tdrr0` a decimal in [0, 1]; the result `min(1, u_shock * tdrr0)` with u from SRP31.125 Table 6 (1.2, 0.8, 0.8, 1.2, 1.2, 0.8 in the order of `SHOCKS`).
- Invariants: the result is in [0, 1]. SRP31.126 gives `CF^p(1) = TD * TDRR_shock` (the redeemed share falls in bucket 1). The case fixtures read the rest of the deposit as scaled by `1 - TDRR_shock` in its contractual bucket, so the total is preserved; that reading of the remainder is UNVERIFIED (dossier 01 H.4 states the bucket-1 flow only).
- Golden (SRP31.125 Table 6): `term_deposit_redemption_rate("parallel-up", 0.05) = 0.06`; `term_deposit_redemption_rate("parallel-down", 0.05) = 0.04`.

## Module `riskvalidation/irrbb/eve_nii.py`

The repricing gap, the duration gap, the standardised EVE and the Annex 1 variant (dossier 05 D.1 and D.2; dossier 01 H.4 and H.5; dossier 03 F.2).

### `riskvalidation.irrbb.eve_nii.repricing_gap`

```python
def repricing_gap(asset_flows: np.ndarray, liability_flows: np.ndarray) -> np.ndarray: ...
```

- Units: (19,) money magnitudes (assets and liabilities both nonnegative); the result (19,) money, `G_k = RSA_k - RSL_k` (dossier 05 D.1).
- Invariants: antisymmetric in its arguments; the sum of the gap is total assets minus total liabilities.
- Golden: assets `100` in bucket 3 and liabilities `0` give `G_3 = 100`; swapped, `-100`.

### `riskvalidation.irrbb.eve_nii.delta_nii_gap`

```python
def delta_nii_gap(gap: np.ndarray, midpoints: np.ndarray, shift_bp: float) -> float: ...
```

- Units: `gap` (19,) money, `midpoints` (19,) years, `shift_bp` a parallel shift in basis points; the result is loss-positive: `-sum over t_k < 1 of G_k * dr * (1 - t_k)` with `dr = shift_bp / 1e4` (the textbook earnings-gap approximation, constant balance sheet; dossier 05 D.1, with the sign of this contract).
- Invariants: linear in `shift_bp` and in `gap`; buckets with `t_k >= 1` do not contribute; zero shift gives zero.
- Golden: `G_3 = 100` at `t = 0.1667`, `shift_bp = +100`: `-100 * 0.01 * (1 - 0.1667) = -0.8333` (an asset-sensitive book gains when rates rise).

### `riskvalidation.irrbb.eve_nii.duration_gap`

```python
@dataclass(frozen=True)
class DurationGap:
    asset_value: float
    liability_value: float
    asset_duration_years: float
    liability_duration_years: float
    duration_gap_years: float
    equity_change_100bp_up: float

def duration_gap(asset_flows: np.ndarray, liability_flows: np.ndarray, rates: np.ndarray, midpoints: np.ndarray) -> DurationGap: ...
```

- Units: flows (19,) money magnitudes, `rates` (19,) decimals, `midpoints` (19,) years; values are present values at the continuously compounded rates; durations are value-weighted times (with continuous compounding the modified duration equals the Macaulay duration); `DGAP = D_A - (L / A) D_L`; `equity_change_100bp_up = -DGAP * A * 0.01` (first-order, dossier 05 D.2).
- Invariants: a zero-asset book raises `ValueError`; with `L = 0` the gap is `D_A`.
- Golden: one asset flow `100` at `t = 2.0`, one liability flow `80` at `t = 1.0`, zero rates: `A = 100`, `L = 80`, `D_A = 2`, `D_L = 1`, `DGAP = 2 - 0.8 = 1.2`, `equity_change_100bp_up = -1.2`.

### `riskvalidation.irrbb.eve_nii.eve`

```python
def eve(cash_flows: np.ndarray, rates: np.ndarray, midpoints: np.ndarray) -> float: ...
```

- Units: `cash_flows` (19,) money (assets positive, liabilities negative), `rates` (19,) decimals, `midpoints` (19,) years; `EVE = sum CF_k exp(-R_k t_k)` (SRP31.129).
- Invariants: linear in the cash flows; additive over items (the sum-of-parts identity the validation test checks); zero rates give `sum CF`.
- Golden (the three-bucket sheet): net flows `+100` in bucket 4 (0.375 y), `-30` in bucket 9 (2.5 y), `-70` in bucket 16 (9.5 y) on a flat 2 percent curve: `EVE = 12.828783`; at zero rates `EVE = 0`.

### `riskvalidation.irrbb.eve_nii.delta_eve`

```python
def delta_eve(cf_base: np.ndarray, cf_shock: np.ndarray, rates_base: np.ndarray, rates_shock: np.ndarray, midpoints: np.ndarray, kao: float = 0.0) -> float: ...
```

- Units: as `eve`; `kao` money, the automatic-option add-on; the result is loss-positive: `sum CF0 DF0 - sum CFi DFi + KAO` (SRP31.129, dossier 01 H.4).
- Invariants: zero when the shocked rates, the shocked flows and the add-on equal the base; equals `eve(base) - eve(shocked) + kao`.
- Golden (the three-bucket sheet above, USD 2024 sizes 200/300/225 bp, flat 2 percent, no floor, `kao = 0`, flows unchanged), delta EVE by shock:

| Shock | Delta EVE |
|---|---|
| parallel-up | -10.666989 |
| parallel-down | 12.828783 |
| steepener | -8.944982 |
| flattener | 6.076550 |
| short-up | -1.625807 |
| short-down | 1.702071 |

### `riskvalidation.irrbb.eve_nii.eve_risk_measure`

```python
def eve_risk_measure(delta_eve_by_shock_currency: np.ndarray) -> float: ...
```

- Units: (S, C) money in one reporting currency, shocks in the order of `SHOCKS`, one column per currency with material exposure (more than 5 percent of banking-book assets or liabilities, SRP31.129); the result `max over i of max(0, sum over c with delta > 0 of delta_ic)`.
- Invariants: nonnegative; a gain in one currency never offsets a loss in another; one column gives `max(0, max_i delta_i)`.
- Golden: rows `[[3, -1], [2, 4], [-5, -2]]` give per-shock positive sums `3, 6, 0`, so the measure is `6`.

### `riskvalidation.irrbb.eve_nii.delta_nii`

```python
def delta_nii(cash_flows: np.ndarray, base_rates: np.ndarray, shocked_rates: np.ndarray, midpoints: np.ndarray) -> float: ...
```

- Units: as `eve`; the result is loss-positive: `sum over t_k < 1 (the first six buckets) of CF_k (r0_k - ri_k)(1 - t_k)` (RAN 21-13 Annex 1 Hoja 10; dossier 03 F.2; the same form serves SRP31.90's two parallel scenarios on the constant balance sheet, dossier 01 H.1).
- Invariants: buckets with `t_k >= 1` do not contribute; zero when the shocked rates equal the base rates; linear in the cash flows.
- Golden: `CF = +100` in bucket 5 (0.625 y), `r0 = 0.03`, `ri = 0.06`: `100 * (0.03 - 0.06) * (1 - 0.625) = -1.125`.

### `riskvalidation.irrbb.eve_nii.automatic_option_addon`

```python
def automatic_option_addon(delta_fv_sold: np.ndarray, delta_fv_bought: np.ndarray) -> float: ...
```

- Units: money, the change in fair value of the automatic options sold and bought under one shock; the result `KAO = sum sold - sum bought` (SRP31.127; dossier 01 H.4).
- Invariants: zero with no options; antisymmetric under swapping sold and bought.
- Golden: sold `[3, 2]`, bought `[1]` give `KAO = 4`.

### `riskvalidation.irrbb.eve_nii.cmf_pair`

```python
def cmf_pair(delta_clp: float, delta_clf: float, offset: bool = True, share: float = 0.5) -> float: ...
```

- Units: loss-positive money in the reporting currency (the CLF leg converted at the UF value); the CLP and CLF pair of RAN 21-13 Annex 1 (dossier 03 F.2). With `offset` and the two deltas of opposite signs (`delta_clp * delta_clf < 0`): if `delta_clp <= 0` the result is `max(share * delta_clp + delta_clf, 0)`, otherwise `max(delta_clp + share * delta_clf, 0)`. Otherwise (same sign, or either zero, or `offset = False`) the result is `max(delta_clp, 0) + max(delta_clf, 0)`.
- Invariants: nonnegative; `offset = False` never gives less than `offset = True`; symmetric in the two arguments when both are positive; the offset applies the 50 percent share to the gain leg only.
- Golden (both signs; the formula of dossier 03 F.2 evaluated by hand):

| delta CLP | delta CLF | pair |
|---|---|---|
| 10 | 20 | 30 |
| -10 | -20 | 0 |
| 30 | -20 | 20 |
| -20 | 30 | 20 |
| 10 | -40 | 0 |
| -40 | 10 | 0 |
| 0 | 25 | 25 |
| 25 | 0 | 25 |

### `riskvalidation.irrbb.eve_nii.annex1_delta_nii`

```python
@dataclass(frozen=True)
class Annex1Nii:
    pairs: np.ndarray            # (2,) used pair, parallel-up then parallel-down
    max_pair: float
    indexation_charge: float
    delta_nii: float
    worst_shock: str | None

def annex1_delta_nii(nii_clp: np.ndarray, nii_ur: np.ndarray, pn_ur: float, offset: bool = True,
                     other_currencies: np.ndarray | None = None) -> Annex1Nii: ...
```

- Units: `nii_clp`, `nii_ur` (2,) loss-positive money for the two parallel shocks, the UR leg converted at the UF value; `pn_ur` the net UF position in the reporting currency (assets positive); `other_currencies` (2, C) the deltas of significant currencies other than CLP and CLF, each contributing `max(delta, 0)`. `delta_NII = max over i in {1, 2} of {sum over other c of max(delta_ic, 0) + pair_i} + 0.025 |PN_UR|` (RAN 21-13 Annex 1 Hoja 10 to 12; dossier 03 F.2).
- Invariants: the charge is added after the maximum, once; the charge is nonnegative and does not depend on the sign of `pn_ur`; `worst_shock` is `None` when the maximum pair is zero.
- Golden: `nii_clp = [30, -10]`, `nii_ur = [-20, 5]`, `pn_ur = -200`: pairs `[20, 0]` (`cmf_pair(30, -20) = 20` and `cmf_pair(-10, 5) = max(0.5 * (-10) + 5, 0) = 0`), `max_pair = 20`, charge `0.025 * 200 = 5`, `delta_nii = 25`, `worst_shock = "parallel-up"`.

### `riskvalidation.irrbb.eve_nii.annex1_delta_eve`

```python
@dataclass(frozen=True)
class Annex1Eve:
    pairs: np.ndarray            # (6,)
    delta_eve: float
    worst_shock: str | None

def annex1_delta_eve(eve_clp: np.ndarray, eve_ur: np.ndarray, offset: bool = True,
                     other_currencies: np.ndarray | None = None) -> Annex1Eve: ...
```

- Units: (6,) loss-positive money in the order of `SHOCKS`; `delta_EVE = max over i in 1 to 6 of {sum over other c of max(delta_ic, 0) + pair_i}` with the same offset rule (Annex 1 Hoja 12). There is no indexation charge in the EVE measure.
- Invariants: nonnegative; `offset = False` never gives less; `worst_shock` is `None` when every pair is zero.
- Golden: `eve_clp = [10, -20, 0, 5, -30, 40]`, `eve_ur = [20, 30, -10, -2, 50, -15]` give pairs `[30, 20, 0, 4, 35, 32.5]`, `delta_eve = 35`, `worst_shock = "short-up"`.

### `riskvalidation.irrbb.eve_nii.indexation_charge`

```python
def indexation_charge(net_uf_position: float, rate: float = 0.025) -> float: ...
```

- Units: `net_uf_position` the net UF position `PN_UR` in the reporting currency (assets positive); the result `rate * abs(net_uf_position)`; the standardised indexation (reajustabilidad) charge, an implied 2.5 percent inflation surprise (RAN 21-13 Annex 1; dossier 03 F.2).
- Invariants: nonnegative; symmetric in the sign of the position; a CPI surprise scenario is a different quantity (`-pn_ur * surprise_pp / 100`, loss-positive), carried by `cpi_scenario` in the C15 document.
- Golden: `indexation_charge(-200) = 5.0`, `indexation_charge(200) = 5.0`, `indexation_charge(0) = 0.0`.

### `riskvalidation.irrbb.eve_nii.outlier_test`

```python
@dataclass(frozen=True)
class OutlierResult:
    ratio: float
    threshold: float
    breached: bool

def outlier_test(measure: float, tier1: float, threshold: float = 0.15) -> OutlierResult: ...
```

- Units: money in one currency; `tier1 > 0` (otherwise `ValueError`); the result compares `measure / tier1` with `threshold` (15 percent of Tier 1, SRP31.82 to SRP31.83; dossier 01 H.5).
- Invariants: `breached` is true only when the ratio is **strictly greater** than the threshold; a nonpositive measure never breaches.
- Golden: `measure = 16`, `tier1 = 100`: ratio `0.16`, breached; `measure = 15`: ratio `0.15`, not breached.

### `riskvalidation.irrbb.eve_nii.prioritised_bank`

```python
@dataclass(frozen=True)
class PrioritisedBank:
    tests: tuple[dict, ...]      # id, measure, base, ratio, threshold, breached
    prioritised: bool

def prioritised_bank(delta_nii: float, delta_eve: float, tier1: float, margin_12m: float) -> PrioritisedBank: ...
```

- Units: money in the reporting currency; the three tests of RAN 21-13 Annex 1 in this order: `nii-tier1` (delta NII over Tier 1 above 5 percent), `eve-tier1` (delta EVE over Tier 1 above 15 percent), `nii-margin` (delta NII over the 12-month cumulative net interest and indexation margin above 18 percent); `prioritised` is true when any is breached (dossier 03 F.2).
- Invariants: strict inequalities; `tier1 > 0` and `margin_12m > 0` (otherwise `ValueError`).
- Golden: `delta_nii = 6`, `delta_eve = 10`, `tier1 = 100`, `margin_12m = 40`: ratios `0.06` (breached), `0.10`, `0.15` (the last below 0.18), so `prioritised = True`.

## Module `riskvalidation/irrbb/behavioural.py`

NMD models and prepayment (dossier 05 D.3 and D.4).

### `riskvalidation.irrbb.behavioural.replicating_portfolio`

```python
@dataclass(frozen=True)
class ReplicatingPortfolio:
    maturities: np.ndarray       # (J,) years
    weights: np.ndarray          # (J,)
    margin_volatility: float | None

def replicating_portfolio(client_rate: np.ndarray, tranche_yields: np.ndarray, maturities: np.ndarray) -> ReplicatingPortfolio: ...
```

- Units: `client_rate` (T,) decimals, `tranche_yields` (T, J) decimals of rolling tranches of the given `maturities` (J,) years; weights minimise the variance of the margin `m_t = sum_j w_j y_jt - i_t` subject to `w_j >= 0` and `sum_j w_j = 1` (the static replicating portfolio, dossier 05 D.3).
- Invariants: the weights are nonnegative and sum to one to `1e-9`; deterministic; if the client rate equals one tranche's yield series the weight of that tranche is `1` and the margin volatility `0`; fewer than `J + 2` observations make `margin_volatility` `None` (the document carries the reason) rather than a number.
- Golden: a client-rate series equal to the second column of the yields gives `weights = [0, 1, 0]` and `margin_volatility = 0` to `1e-9`.

### `riskvalidation.irrbb.behavioural.weighted_average_maturity`

```python
def weighted_average_maturity(maturities: np.ndarray, weights: np.ndarray) -> float: ...
```

- Units: years; the result `sum_j w_j m_j / 2`: a rolling tranche of maturity `m` reinvested evenly over its life has a weighted average maturity of `m / 2` (BCBS 368 footnote 38 as read in dossier 05 D.3: one sixtieth reinvested monthly in a five-year fixed gives 2.5 years).
- Invariants: weights must sum to one to `1e-9` (otherwise `ValueError`); linear in the weights.
- Golden: one tranche of 5 years with weight 1 gives `2.5`; weights `[0.2, 0.3, 0.3, 0.2]` on `[1, 3, 5, 10]` give `2.5`.

### `riskvalidation.irrbb.behavioural.deposit_beta_passthrough`

```python
def deposit_beta_passthrough(client_rate: float, market_change: float, beta_up: float, beta_down: float) -> float: ...
```

- Units: decimals; the new client rate `client_rate + beta * market_change` with `beta_up` when `market_change >= 0` and `beta_down` otherwise (asymmetric pass-through, Drechsler, Savov and Schnabl 2021; dossier 05 D.3).
- Invariants: betas are nonnegative; a zero market change leaves the rate unchanged; the result is not floored (the caller floors).
- Golden: `deposit_beta_passthrough(0.01, 0.02, 0.4, 0.3) = 0.018`; `deposit_beta_passthrough(0.01, -0.02, 0.4, 0.3) = 0.004`.

### `riskvalidation.irrbb.behavioural.prepayment_logit`

```python
def prepayment_logit(incentive: np.ndarray, seasoning_months: np.ndarray, coef: np.ndarray) -> np.ndarray: ...
```

- Units: `incentive` (N,) decimals (the refinancing incentive, the contract rate minus the market rate), `seasoning_months` (N,) months, `coef` (3,) the intercept, the incentive coefficient and the seasoning coefficient; the result (N,) the SMM, `1 / (1 + exp(-(b0 + b1 incentive + b2 seasoning)))` (a reduced-form logit of the SMM on the refinancing incentive and seasoning, dossier 05 D.4; burnout and seasonality are not in this version).
- Invariants: in (0, 1); monotone in the incentive when `b1 > 0`.
- Golden: `coef = [0, 0, 0]` gives `0.5` for every input.

### `riskvalidation.irrbb.behavioural.fit_prepayment_logit`

```python
@dataclass(frozen=True)
class LogitFit:
    coef: np.ndarray             # (3,)
    n: int
    converged: bool

def fit_prepayment_logit(incentive: np.ndarray, seasoning_months: np.ndarray, prepaid: np.ndarray) -> LogitFit: ...
```

- Units: `prepaid` (N,) booleans (the loan prepaid in the month); maximum likelihood with a fixed start and tolerance.
- Invariants: deterministic; `converged` is false rather than an exception when the likelihood does not converge (the bake then uses the PSA benchmark and says so); complete separation sets `converged` false; inputs are never mutated.
- Golden: data simulated with `coef = [-2, 20, 0.01]` (seed 0, N = 20000) is recovered to `0.15` in each coefficient.

## Module `riskvalidation/irrbb/simulation.py`

The dynamic NII simulation and the stochastic EaR and EVaR (dossier 05 D.5 and D.6).

### `riskvalidation.irrbb.simulation.simulate_nii`

```python
@dataclass(frozen=True)
class NiiPath:
    monthly_nii: np.ndarray      # (M,) money per month
    total: float                 # money over the horizon

def simulate_nii(balances: np.ndarray, sides: np.ndarray, rate0: np.ndarray, spread: np.ndarray, beta: np.ndarray,
                 reprice_months: np.ndarray, short_rate_path: np.ndarray, growth_annual: float = 0.0) -> NiiPath: ...
```

- Units: per item (I,) arrays: `balances >= 0` money, `sides` `+1` asset and `-1` liability, `rate0` the current rate (decimal), `spread` and `beta` such that a reset rate is `spread + beta * r_t` (an asset indexed to the market has `beta = 1`; an NMD deposit has the deposit beta, dossier 05 D.3), `reprice_months` an integer (`0` reprices every month; `k >= 1` keeps `rate0` until month `k` and resets every `k` months afterwards); `short_rate_path` (M,) annual decimals, `M` from 12 to 36 (dossier 05 D.6); `growth_annual` the balance-sheet assumption (0 is the constant balance sheet: run-off is replaced by identical new business, DIS70.5, dossier 01 H.1). Monthly NII is `sum_i side_i * balance_i * (1 + g)^(m / 12) * rate_im / 12`.
- Invariants: with a flat path and `rate0 = spread + beta * r` the monthly NII is constant; a fixed item whose `reprice_months` exceeds the horizon is unaffected by the path; raising a liability beta never raises NII; NII is linear in the balances; an item with `balance = 0` contributes nothing.
- Golden: one asset (`balance 100`, `side +1`, `rate0 0.05`, `spread 0.02`, `beta 1`, `reprice 0`) and one liability (`balance 100`, `side -1`, `rate0 0.015`, `spread 0`, `beta 0.5`, `reprice 0`), a flat `short_rate_path` of `0.03` over 12 months: `total = 100 * 0.05 - 100 * 0.015 = 3.5`; the same book with the path stepping to `0.04` from month 1 gives `total = 100 * 0.06 - 100 * 0.02 = 4.0`.

### `riskvalidation.irrbb.simulation.hw1f_scenarios`

```python
def hw1f_scenarios(zero_rates: np.ndarray, tenors: np.ndarray, a: float, sigma: float, horizon_months: int, n_paths: int, seed: int) -> np.ndarray: ...
```

- Units: `zero_rates` (T,) decimals at `tenors` (T,) years (the initial curve), `a` mean reversion per year, `sigma` annual volatility; the result (P, horizon_months + 1) short-rate paths (Hull-White one factor fitted to today's curve through `theta(t)`; dossier 05 C.4 and D.5).
- Invariants: deterministic given `seed`; antithetic pairs; with `sigma = 0` every path is the initial instantaneous forward curve; the average discount factor of the paths reprices the initial curve within Monte Carlo error.
- Golden: a flat curve `0.03` with `sigma = 0` gives every path equal to `0.03` at every step.

### `riskvalidation.irrbb.simulation.dns_scenarios`

```python
def dns_scenarios(factor_history: np.ndarray, maturities_months: np.ndarray, horizon_months: int, n_paths: int, seed: int) -> np.ndarray: ...
```

- Units: `factor_history` (T, 3) level, slope and curvature; the result (P, horizon_months, N) yields at the maturities (dynamic Nelson-Siegel scenarios, `forecast_dns_factors` through `dns_yield`).
- Invariants: deterministic given `seed`; uses only the history it is given (no look-ahead: the C14 bake passes factors up to the valuation date).
- Golden: a constant history gives every path equal to `dns_yield` of that row.

### `riskvalidation.irrbb.simulation.ear_evar`

```python
@dataclass(frozen=True)
class EarEvar:
    ear: float
    evar: float

def ear_evar(nii_paths: np.ndarray, eve_paths: np.ndarray, base_nii: float, base_eve: float, level: float = 0.99) -> EarEvar: ...
```

- Units: `nii_paths` (P,) and `eve_paths` (P,) money; the result is loss-positive: `ear = base_nii - quantile(nii_paths, 1 - level)` and `evar = base_eve - quantile(eve_paths, 1 - level)` (linear-interpolated quantiles).
- Invariants: monotone in `level`; all-equal paths give `base - path`; `P >= 2` (otherwise `ValueError`).
- Golden: `nii_paths = [1, 2, ..., 100]`, `base_nii = 60`, `level = 0.99`: the first percentile is `1.99`, so `ear = 58.01`.

## Module `riskvalidation/validation/irrbb.py`

The IRRBB validation tests (dossier 05 D.7 and the IRRBB ladder acceptance; SDD section 4). Each returns one `TestResult` that validates against `common/test-result`.

### `riskvalidation.validation.irrbb.srp31_92_goldens`

```python
def srp31_92_goldens(tolerance_scalar: float = 5e-4, tolerance_bp: float = 5e-2) -> TestResult: ...
```

- Units: none; reproduces the SRP31.92 worked example (dossier 01 H.2): at `t = 3.5`, `alpha_short = 0.417`, a 100 bp short shock `+41.7` bp, steepener `+25.4` bp, flattener `-1.6` bp.
- Test id: `test_id = "irrbb.srp31_92_goldens"`. `statistic` is the largest absolute deviation of the four values from the printed ones, in their own units; `p_value` is `None`.
- Light: green when every deviation is within its tolerance, red otherwise; `extras["thresholds"]` holds the two tolerances.
- Golden: the engine at its release returns green; the statistic is the flattener's deviation, `0.0393` bp (`-1.6393` against the printed `-1.6`), below the `0.05` bp tolerance.

### `riskvalidation.validation.irrbb.cmf_annex1_goldens`

```python
def cmf_annex1_goldens() -> TestResult: ...
```

- Units: none; reproduces the Annex 1 formulas (dossier 03 F.2): the `cmf_pair` table on both signs (eight cases), the Hoja 9 table through `shock_table("cmf-annex1")`, the indexation charge (`indexation_charge(-200) = 5`) and the `annex1_delta_eve` golden (pairs `[30, 20, 0, 4, 35, 32.5]`).
- Test id: `test_id = "irrbb.cmf_annex1_goldens"`. `statistic` is the number of failed cases; `p_value` is `None`.
- Light: green when every case is exact (floating-point equality to `1e-12`), red otherwise.
- Golden: green with `statistic = 0` at the engine release.

### `riskvalidation.validation.irrbb.eve_sum_of_parts`

```python
def eve_sum_of_parts(item_flows: np.ndarray, rates: np.ndarray, midpoints: np.ndarray, whole_eve: float, rel_tol: float = 1e-9) -> TestResult: ...
```

- Units: `item_flows` (I, 19) money, one row per balance-sheet item; `whole_eve` the EVE of the aggregated flows; checks `sum_i eve(item_i) = whole_eve`.
- Test id: `test_id = "irrbb.eve_sum_of_parts"`. `statistic` is the absolute residual; `metric` the relative residual.
- Light: green when the relative residual is at most `rel_tol`, red otherwise; `extras["thresholds"] = {"rel_tol": ...}`.
- Golden: the three items `+100` (bucket 4), `-30` (bucket 9), `-70` (bucket 16) at a flat 2 percent with `whole_eve = 12.828783` give green and a residual below `1e-6`; `whole_eve = 12.9` gives red.

### `riskvalidation.validation.irrbb.nmd_parameter_stability`

```python
def nmd_parameter_stability(window_weights: np.ndarray, maturities: np.ndarray, gap_amber: float = 0.10, gap_red: float = 0.25) -> TestResult: ...
```

- Units: `window_weights` (W, J) replicating-portfolio weights re-estimated on W estimation windows (W >= 2), `maturities` (J,) years; the statistic is the largest sup-norm distance `max_j |w_aj - w_bj|` between consecutive windows (dossier 05 D.3: weight stability across estimation windows).
- Test id: `test_id = "irrbb.nmd_parameter_stability"`. `metric` is the largest change in the weighted average maturity in years.
- Light: green when the statistic is at most `gap_amber`, amber when at most `gap_red`, red above; `extras["thresholds"] = {"gap_amber": ..., "gap_red": ...}`; fewer than two windows gives `not_evaluated` with the reason in `notes`.
- Golden: windows `[[0.5, 0.5], [0.5, 0.5]]` give statistic `0` and green; `[[0.5, 0.5], [0.8, 0.2]]` give `0.30` and red; `[[0.5, 0.5], [0.65, 0.35]]` give `0.15` and amber.

### `riskvalidation.validation.irrbb.eve_with_without_behavioural`

```python
def eve_with_without_behavioural(measure_behavioural: float, measure_contractual: float, tier1: float,
                                 diff_amber: float = 0.05, diff_red: float = 0.15, threshold: float = 0.15) -> TestResult: ...
```

- Units: money in one currency; the two EVE risk measures of the same shocks with and without the behavioural assumptions, `tier1 > 0`. The result always reports both (dossier 05 D.7: always report EVE with and without behavioural assumptions).
- Test id: `test_id = "irrbb.eve_with_without_behavioural"`. `statistic` is `(contractual - behavioural) / tier1`; `metric` is the difference in money.
- Light: green when `abs(statistic) <= diff_amber`, amber when at most `diff_red`, red above; **red whatever the size** when the behavioural measure passes the outlier test and the contractual one breaches it (the behavioural assumptions hide a breach, the SVB lesson); `extras["thresholds"]` holds `diff_amber`, `diff_red`, `threshold` and both ratios.
- Golden: `measure_behavioural = 10`, `measure_contractual = 20`, `tier1 = 100`: statistic `0.10`, the contractual ratio `0.20` breaches and the behavioural `0.10` does not, so red. `10` against `12`: statistic `0.02`, green.

### `riskvalidation.validation.irrbb.behavioural_change_at_breach`

```python
def behavioural_change_at_breach(values: np.ndarray, dates: np.ndarray, breach: np.ndarray) -> TestResult: ...
```

- Units: `values` (T,) a behavioural parameter (a core share, a core maturity, a beta), `dates` (T,) `datetime64[D]` strictly increasing, `breach` (T,) booleans, true at a date where a limit was breached in the window ending there; a change is `values[t] != values[t - 1]` (dossier 05 D.7: flag any change in NMD behavioural parameters that coincides with a limit breach).
- Test id: `test_id = "irrbb.behavioural_change_at_breach"`. `statistic` is the number of flagged changes; `n` is the number of dates.
- Light: red when any change coincides with a breach (`breach[t]` true), green otherwise.
- Golden: values `[0.65, 0.75]`, breach `[False, True]` give statistic `1` and red; values `[3.0, 3.0]` with a breach give `0` and green; values `[0.35, 0.40]`, breach `[False, False]` give `0` and green.

### `riskvalidation.validation.irrbb.nii_out_of_sample`

```python
def nii_out_of_sample(projected_delta_nii: float, realised_delta_nii: float | None, err_green: float = 0.10, err_amber: float = 0.25) -> TestResult: ...
```

- Units: money in one currency, loss-positive; the projected change of NII under the scenario against the realised change over the 2022 hiking cycle (dossier 05, IRRBB acceptance: the 2022 hiking cycle as the out-of-sample test); the statistic is the relative error `abs(projected - realised) / abs(realised)`.
- Test id: `test_id = "irrbb.nii_out_of_sample"`. `metric` is `projected - realised` in money.
- Light: green when the relative error is at most `err_green`, amber when at most `err_amber`, red above; `not_evaluated` with the reason in `notes` when `realised_delta_nii` is `None` or zero; `extras["thresholds"]` holds both.
- Golden: projected `90`, realised `100`: statistic `0.10`, green; projected `70`: `0.30`, red; realised `None`: `not_evaluated`.

## UNVERIFIED and open items

- The Diebold-Li statement "maximises the curvature loading at exactly 30 months" (dossier 05 D.5): recomputed, the maximiser is 29.447 months for `lam = 0.0609`; the contract uses the decay 0.0609. UNVERIFIED against the paper.
- The definition of the outstanding notional `N^p(k-1)` in SRP31.121 and the treatment of the remainder of a redeemed term deposit in SRP31.126 (dossier 01 H.4 gives the formulas only).
- The upper edge of the overnight bucket (`1/360` years) is derived from the Table 3 midpoint.
- Whether the Annex 1 floor clause "or the pre-shock rate if lower" applies to the UR floor of `-2%` as well as the 0 percent of other currencies (dossier 03 F.2).
- The values of the 2024 table come from dossier 01 H.3 (d578 introduction and SRP98.60), the 2016 table with the caveat quoted above; CLP is not in either; the CMF Hoja 9 table was read from page images (dossier 03 F.2).
- The SIFMA primary text of the PSA definition (dossier 05 D.4, consistent across secondary sources).
- Chilean mortgage prepayment calibration (dossier 05 D.4: no Chilean primary source was checked); the Kalkbrener-Willing stochastic SDEs (dossier 05 D.3).
- The CRD article number for the EU EVE supervisory outlier test (dossier 01 H.5).
