# Engine CCR API contract: `engine-ccr-api` 1.0.0

Owner: U9-S (unit sizing `plans/contraste/units/U9-sizing.md`, CAOS_MANAGE). Implemented by U9-E2 in `riskvalidation.ccr` (`hw1f.py`,
`swaps.py`, `exposure.py`, `collateral.py`, `cva.py`) and `riskvalidation.validation.ccr` (repository CAOS_RiskValidation); called by the C12
bake (U9-P1). The tests of every function are written by U9-E2 against this file: a function exists with exactly the signature below, and each
golden value or invariant is a test. Changing a signature, a unit or a golden value is a breaking change (a new major version of this contract).
Sources: the U9 research addendum (`wip/contraste/u9-research-addendum-2026-10-17.md`: R1 wrong-way risk, R2 initial margin, R3 MPoR and CSA, R4
Hull-White closed forms, R5 backtest, R6 estimators, R9 IMM measures), dossier 05 (`wip/contraste/05-market-ccr-alm-liquidity-oprisk-stress-sota-2026-10-04.md`,
section C and the counterparty ladder at line 476), dossier 08 (row 27, line 832) and the sizing decisions D3 to D8 and B1 to B10. The documents this
contract feeds are `c12-outputs` and `c12-models` (`docs/contracts/schemas/c12/`).

The engine computes; it states no compliance claim. It is pure NumPy and SciPy: ORE and QuantLib never enter the engine (ADR-0069); the
reconciliation against ORE 1.8.17.0 and the QuantLib 1.44 check of the closed forms are the C12 bake's. Every constant is transcribed from the
record named on its line; an item the record marks UNVERIFIED is marked so here and is not silently decided (list at the end).

## Conventions (all functions)

- Arrays are `numpy.ndarray` of `float64`. Shapes: `P` paths, `K` grid points. Money is a float in the currency of the netting set (USD for C12; the
  currency code travels in the document, never in a function). Rates are decimals compounded continuously; times are years from the valuation date;
  the margin period of risk is in business days with 250 to the year.
- **Sign convention (required field `sign_convention` of every document):** EE is the positive exposure to the counterparty; ENE is the bank's own,
  reported positive; CVA is a positive cost and DVA a positive benefit.
- Every function is pure and deterministic; a function with randomness takes a `seed` and uses `numpy.random.default_rng(seed)`. Dataclasses are
  frozen. Inputs are never mutated.
- The ladder of dossier 05 line 476: rung 1 current exposure plus add-on is SA-CCR's RC plus PFE (decision D3, `riskvalidation.regulatory.sa_ccr`, not
  re-implemented here); rung 2 the analytical EE of a single swap (`hw1f` and `exposure.analytic_ee_single_swap`); rung 3 the Monte Carlo netting set;
  rung 4 collateral with the MPoR and initial margin; rung 5 wrong-way risk.
- A validation function returns one `TestResult` of `riskvalidation`, serialised by `TestResult.to_dict()` into a row that validates against
  `common/test-result`. Its `test_id` is prefixed `ccr.`. A function that cannot compute because data is missing returns the `not_evaluated` light with
  its reason in `notes` and `statistic`, `p_value` and `metric` all null; it never returns a placeholder number.
- Tolerance: every golden value states its own tolerance or is exact; a golden stated to six decimals holds to `5e-7`.

## Module `riskvalidation/ccr/hw1f.py`

The Hull-White one-factor model on any time grid (the close-out grid needs days, the IRRBB scenarios are monthly): `r_t = phi(t) + x_t`, `x_t` an
Ornstein-Uhlenbeck process `dx = -a x dt + sigma dW` (addendum R4, QuantLib 1.44 `hullwhite.hpp`). The curve and forward functions of
`irrbb.curves` and `irrbb.simulation` are reused, never copied; `irrbb.simulation.hw1f_scenarios` is unchanged (contract `engine-irrbb-api`).

### `riskvalidation.ccr.hw1f.phi`

```python
def phi(t: np.ndarray, a: float, sigma: float, forward: Callable[[np.ndarray], np.ndarray]) -> np.ndarray: ...
```

- Units: `t` years, `a` per year (positive), `sigma` per square-root year, `forward` the instantaneous forward rate of today's curve `f(0, t)` (decimal); the result a decimal.
- Invariants: `phi(t) = f(0, t) + (sigma (1 - exp(-a t)) / a)^2 / 2` (R4, QuantLib `FittingParameter`); `phi(0) = f(0, 0)`; for `a` below `sqrt(eps)` the bracket is `sigma t`; with `sigma = 0` it equals `f(0, t)`.
- Golden: flat `f = 0.03`, `a = 0.1`, `sigma = 0.01`, `t = 2` gives `0.030164` (recomputed from the formula).

### `riskvalidation.ccr.hw1f.bond_b`

```python
def bond_b(t: np.ndarray, big_t: np.ndarray, a: float) -> np.ndarray: ...
```

- Units: times in years, `a` per year; the result in years.
- Invariants: `B(t, T) = (1 - exp(-a (T - t))) / a` (R4); `B(t, t) = 0`; for `a` below `sqrt(eps)` it is `T - t`.
- Golden: `a = 0.1`, `t = 0`, `T = 5` gives `3.934693`.

### `riskvalidation.ccr.hw1f.bond_a`

```python
def bond_a(t: np.ndarray, big_t: np.ndarray, a: float, sigma: float, p0: Callable[[np.ndarray], np.ndarray], forward: Callable[[np.ndarray], np.ndarray]) -> np.ndarray: ...
```

- Units: `p0` today's discount factor `P(0, T)`; the result unitless.
- Invariants: `A(t, T) = P(0, T) / P(0, t) exp(B f(0, t) - sigma^2 / (4 a) (1 - exp(-2 a t)) B^2)` (R4, `HullWhite::A`); `A(t, t) = 1`; at `t = 0` it equals `P(0, T)`.
- Golden: at `t = 0` and any `a`, `sigma`: `A(0, T) = P(0, T)` exactly.

### `riskvalidation.ccr.hw1f.bond_price`

```python
def bond_price(r: np.ndarray, t: float, big_t: float, a: float, sigma: float, p0: Callable, forward: Callable) -> np.ndarray: ...
```

- Units: `r` (P,) the short rate at `t` (decimal); the result (P,) a discount factor.
- Invariants: `P(t, T) = A(t, T) exp(-B(t, T) r)` (R4); the theta fit reprices today's curve: with `t = 0` and `r = phi(0)` the price equals `P(0, T)` to `1e-12` for every `T` of the curve; decreasing in `r`.
- Golden: a flat curve `P(0, T) = exp(-0.03 T)` and any `a`, `sigma` give `P(0, T)` to `1e-12` at `t = 0`.

### `riskvalidation.ccr.hw1f.simulate_state`

```python
def simulate_state(grid: np.ndarray, a: float, sigma: float, n_paths: int, seed: int, antithetic: bool = True) -> np.ndarray: ...
```

- Units: `grid` (K,) years starting at 0, strictly increasing (otherwise `ValueError`); the result (P, K) the state `x` with `x(0) = 0`.
- Invariants: exact discretisation `x(t_i) = x(t_{i-1}) e^{-a dt} + sigma sqrt((1 - e^{-2 a dt}) / (2 a)) z` (R6 equations 49 to 52), so the result does not depend on the step size in law; the same `seed` gives the same array; with `antithetic` the sample mean of `x` is 0 to `1e-12`; `Var(x(t)) = sigma^2 (1 - e^{-2 a t}) / (2 a)` to the Monte Carlo error.
- Golden: `a = 0.1`, `sigma = 0.01`, `t = 5`: `Var = 0.00031606` (`1e-4 (1 - e^{-1}) / 0.2`, recomputed); the sample variance of 20,000 antithetic paths lies within 3 standard errors.

### `riskvalidation.ccr.hw1f.simulate_short_rate`

```python
def simulate_short_rate(grid: np.ndarray, a: float, sigma: float, forward: Callable, n_paths: int, seed: int) -> np.ndarray: ...
```

- Units: the result (P, K) short rates, decimals, `r = phi(t) + x`.
- Invariants: the martingale check: the sample mean of `exp(-integral r) P(t, T; r_t)` equals `P(0, T)` within the Monte Carlo error at every grid point (test `ccr.martingale_discounted_bonds`); the mean of `r(t)` is `phi(t)` to the Monte Carlo error.
- Golden: none beyond the invariants.

### `riskvalidation.ccr.hw1f.bond_option`

```python
def bond_option(is_call: bool, strike: float, expiry: float, bond_maturity: float, a: float, sigma: float, p0: Callable) -> float: ...
```

- Units: `strike` a bond price (unitless), times in years; the result a price per unit nominal.
- Invariants: `sigma_p = sigma B(T, S) sqrt((1 - e^{-2 a T}) / (2 a))` and `ZBC = P(0, S) N(h) - K P(0, T) N(h - sigma_p)` with `h = ln(P(0, S) / (K P(0, T))) / sigma_p + sigma_p / 2` (R4, `HullWhite::discountBondOption`; for `a` below `sqrt(eps)` use `sigma B sqrt(T)`); put-call parity `ZBC - ZBP = P(0, S) - K P(0, T)` to `1e-12`; the price is non-negative and agrees with the Monte Carlo of `bond_price` within the Monte Carlo error.
- Golden: `a = 0.1`, `sigma = 0.01`, `T = 2`, `S = 5`: `sigma_p = 0.033276` (recomputed from the formula, tolerance 5e-7).

### `riskvalidation.ccr.hw1f.swaption_jamshidian`

```python
def swaption_jamshidian(is_payer: bool, expiry: float, fixed_times: np.ndarray, fixed_amounts: np.ndarray, a: float, sigma: float, p0: Callable, forward: Callable) -> float: ...
```

- Units: `fixed_times` (n,) the fixed payment times after the expiry in years, `fixed_amounts` (n,) the coupon amounts with the nominal added to the last (money); the result in the money of the nominal.
- Invariants: the Jamshidian decomposition of R4 (QuantLib `jamshidianswaptionengine.cpp`): find `r*` with `N - sum c_i R_i(r*) = 0` by Brent on `[-10, 10]` with tolerance `1e-8`, the legs' strikes `K_i = R_i(r*)`, value `sum c_i ZBO(K_i)`; the type is a put for a payer swaption and a call for a receiver; payer minus receiver swaption of the same fixed rate equals the forward swap value (parity) to `1e-9`; non-negative; zero when `sigma` tends to zero and the swaption is out of the money.
- Golden: none numeric in the addendum; the C12 bake reconciles the engine against QuantLib 1.44 numerically (sizing B4), and the unit test checks parity and the Monte Carlo agreement.

### `riskvalidation.ccr.hw1f.calibrate_ar1`

```python
@dataclass(frozen=True)
class Ar1Fit:
    a: float; sigma: float; theta: float; a_se: float; sigma_se: float; n_obs: int; sample_start: str; sample_end: str

def calibrate_ar1(dates: list[str], short_rate: np.ndarray, before: str, min_years: float = 3.0, dt: float | None = None) -> Ar1Fit: ...
```

- Units: `dates` ISO dates, `short_rate` (N,) the shortest Treasury zero rate (decimal) on those dates; `before` an ISO date: only observations strictly before it are used; `dt` the step in years (default the median spacing); `a` per year, `sigma` per square-root year.
- Invariants: OLS of `x(t_i)` on `x(t_{i-1})` gives `c`, `b`, `delta`; `a = -ln b / dt`, `theta = c / (1 - b)`, `sigma = delta / sqrt((b^2 - 1) dt / (2 ln b))` (R6 equations 55 to 57, Brigo et al. arXiv 0812.4210); the sample window ends before `before` (the result's `sample_end < before`, the document check "no look-ahead"); fewer than `min_years` of history raises `ValueError` (CRE53.51); a series with `b >= 1` or `b <= 0` raises `ValueError` (not mean-reverting); the standard errors are those of the OLS coefficients propagated to `a` and `sigma` by the delta method (they drive the sensitivity block of B6).
- Golden: `b = 0.99`, `delta = 0.002`, `dt = 1/12` map to `a = 0.120604` and `sigma = 0.006963` (recomputed from R6 equations 55 to 57, tolerance 5e-7); a series simulated from `simulate_state` with known `a`, `sigma` is recovered within three standard errors.

## Module `riskvalidation/ccr/swaps.py`

### `riskvalidation.ccr.swaps.Swap`

```python
@dataclass(frozen=True)
class Swap:
    trade_id: str
    notional: float          # money
    fixed_rate: float        # decimal, annual-equivalent coupon rate paid per fixed period
    is_payer: bool           # the bank pays the fixed rate
    start: float             # years
    maturity: float          # years
    fixed_frequency: int     # fixed payments per year
```

- Units: as the comments; the floating leg resets on the single curve of the case (no spread).
- Invariants: `maturity > start >= 0`, `notional > 0` (otherwise `ValueError`); frozen.

### `riskvalidation.ccr.swaps.cash_flow_times`

```python
def cash_flow_times(swap: Swap) -> np.ndarray: ...
```

- Units: the result (n,) fixed payment times in years, `start + k / fixed_frequency` up to `maturity`.
- Invariants: the last time is `maturity`; cash flows are by date so a close-out window sees the flows it contains (sizing, modules table).
- Golden: `start = 0`, `maturity = 2`, frequency 2 gives `[0.5, 1.0, 1.5, 2.0]`.

### `riskvalidation.ccr.swaps.swap_value`

```python
def swap_value(swap: Swap, t: float, r: np.ndarray, a: float, sigma: float, p0: Callable, forward: Callable) -> np.ndarray: ...
```

- Units: `t` years, `r` (P,) the short rate at `t`; the result (P,) money, to the bank (positive is an asset); only flows after `t` are valued (sticky date, R3).
- Invariants: fixed leg `sum c_i P(t, T_i)` and floating leg `N (P(t, T_0) - P(t, T_n))` from the affine bond prices; a payer value is minus the receiver value of the same terms; at `t = 0` on today's curve with the par fixed rate the value is 0 to `1e-12`; no flows after `t` gives value 0.
- Golden: a flat curve `P(0, T) = exp(-0.03 T)`, a receiver swap at its par rate has value 0 at `t = 0` for any `a`, `sigma`.

### `riskvalidation.ccr.swaps.par_fixed_rate`

```python
def par_fixed_rate(maturity: float, frequency: int, p0: Callable, start: float = 0.0) -> float: ...
```

- Units: the result a decimal per year.
- Invariants: `(P(0, start) - P(0, maturity)) / (sum (1 / frequency) P(0, T_i))`; the value of a swap at that rate is 0.
- Golden: flat continuous `0.03`, `start = 0`, `maturity = 1`, `frequency = 1` gives `(1 - e^{-0.03}) / e^{-0.03} = 0.030455` (recomputed).

### `riskvalidation.ccr.swaps.swap_values_on_grid`

```python
def swap_values_on_grid(swaps: list[Swap], grid: np.ndarray, short_rate: np.ndarray, a: float, sigma: float, p0: Callable, forward: Callable) -> np.ndarray: ...
```

- Units: `short_rate` (P, K) from `simulate_short_rate`; the result (S, P, K) money per swap, path and grid point.
- Invariants: equals `swap_value` at each grid point; the sum over swaps is the netting-set value (netting is on the sum, not the sum of positive parts).
- Golden: a single swap at its par rate has mean value 0 at the first grid point within the Monte Carlo error of `sigma sqrt(t)` scale.

## Module `riskvalidation/ccr/exposure.py`

### `riskvalidation.ccr.exposure.expected_exposure`

```python
def expected_exposure(values: np.ndarray, numeraire: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]: ...
```

- Units: `values` (P, K) netting-set values (money); `numeraire` (P, K) the numeraire `N(t)` for the discounted measure, `None` for the undiscounted Basel style; the result `(ee, mc_se)` each (K,) in money, `ee = mean(max(values, 0) / N)`, `mc_se` its Monte Carlo standard error `std / sqrt(P)`.
- Invariants: `EE >= 0`; ENE is `expected_exposure(-values)`; `EE - ENE` equals the mean of the value (to `1e-9`); the discounted EE is at most the undiscounted one for positive rates.
- Golden: values `[[-1, 2], [3, -4]]` give `EE = [1.5, 1.0]` and `ENE = [0.5, 2.0]` (arithmetic).

### `riskvalidation.ccr.exposure.effective_ee`

```python
def effective_ee(ee: np.ndarray, current_exposure: float = 0.0) -> np.ndarray: ...
```

- Units: `ee` (K,) money; the result (K,) money.
- Invariants: `Effective EE_{t_k} = max(Effective EE_{t_{k-1}}, EE_{t_k})` with `Effective EE_{t_0}` the current exposure (CRE53.12 equation 2, R9); non-decreasing; at least `ee`.
- Golden: `[1, 3, 2]` gives `[1, 3, 3]`.

### `riskvalidation.ccr.exposure.effective_epe`

```python
def effective_epe(grid: np.ndarray, eff_ee: np.ndarray, horizon: float = 1.0) -> float: ...
```

- Units: `grid` (K,) years, strictly increasing; the result in money (the EEPE).
- Invariants: `sum_{t_k <= min(1, maturity)} EffectiveEE_k dt_k` over the covered time (CRE53.13 equation 3, R9, weights `dt_k = t_k - t_{k-1}`, `t_0 = 0`), normalised by the covered time so that a constant profile returns its value; at most the maximum of the EE the profile came from; EEPE recomputed from EE equals the document value (test `ccr.eepe_recomputed`).
- Golden: grid `[0.25, 0.5, 1.0]`, effective EE `[1, 3, 3]` gives `(1 x 0.25 + 3 x 0.25 + 3 x 0.5) / 1 = 2.5`.

### `riskvalidation.ccr.exposure.epe`

```python
def epe(grid: np.ndarray, ee: np.ndarray, horizon: float = 1.0) -> float: ...
```

- Units: as `effective_epe`.
- Invariants: the plain time-weighted average of EE over the first year (dossier 05 C.1 `EPE_B`); at most `effective_epe` of the same EE.
- Golden: grid `[0.25, 0.5, 1.0]`, EE `[1, 3, 2]` gives `(0.25 + 0.75 + 1.0) = 2.0`.

### `riskvalidation.ccr.exposure.pfe`

```python
def pfe(values: np.ndarray, quantile: float) -> tuple[np.ndarray, np.ndarray]: ...
```

- Units: `values` (P, K) money, `quantile` in (0, 1); the result `(pfe, mc_se)` each (K,) in money, `pfe = max(quantile of the value, 0)`.
- Invariants: dossier 05 C.1 `PFE_alpha(t) = (inf {x : F_t(x) >= alpha})^+`; non-negative; non-decreasing in the quantile; at least EE for a quantile of at least 0.5 on a symmetric value; the standard error is the order-statistic one (`sqrt(q (1 - q) / P) / density`, estimated by the bootstrap of the sample, seeded).
- Golden: the values `1, 2, ..., 100` at quantile 0.95 give 95 (the inverse empirical distribution).

### `riskvalidation.ccr.exposure.net_values`

```python
def net_values(values_by_trade: np.ndarray) -> np.ndarray: ...
```

- Units: `values_by_trade` (S, P, K) money; the result (P, K).
- Invariants: the sum over trades; the netted EE is at most the sum of the single-trade EE for any input (`max(sum v, 0) <= sum max(v, 0)`), the difference being the netting benefit.
- Golden: trades `+1` and `-1` on one path give 0 and the netted EE is 0 while the sum of single-trade EE is 1.

### `riskvalidation.ccr.exposure.netting_benefit`

```python
def netting_benefit(ee_by_trade: np.ndarray, ee_netted: np.ndarray) -> np.ndarray: ...
```

- Units: `ee_by_trade` (S, K), `ee_netted` (K,) money; the result (K,) money.
- Invariants: `sum_s EE_s - EE_netted`; non-negative when the EEs come from the same paths.
- Golden: `[[1, 2], [1, 2]]` and `[1.5, 3.0]` give `[0.5, 1.0]`.

### `riskvalidation.ccr.exposure.effective_maturity`

```python
def effective_maturity(grid: np.ndarray, ee: np.ndarray, eff_ee: np.ndarray, df: np.ndarray, cap: float = 5.0) -> float: ...
```

- Units: `df` (K,) discount factors; the result in years.
- Invariants: CRE53.20 `M = (sum_{t_k <= 1} EffEE dt df + sum_{t_k > 1} EE dt df) / (sum_{t_k <= 1} EffEE dt df)`, capped at `cap` (5 years); when every contract matures within one year the second sum is empty and `M = 1`; at least 1.
- Golden: a profile whose grid ends at or before one year gives `M = 1` exactly.

### `riskvalidation.ccr.exposure.analytic_ee_single_swap`

```python
def analytic_ee_single_swap(swap: Swap, grid: np.ndarray, a: float, sigma: float, p0: Callable, forward: Callable) -> np.ndarray: ...
```

- Units: the result (K,) the undiscounted EE in money.
- Invariants: rung 2 (R4, derived statement): `EE_B(t) = Swaption(0; t) / P(0, t)` where the swaption is the payer one (payer swap) or the receiver one (receiver swap) expiring at `t` on the remaining swap, from `swaption_jamshidian`; flows at or before `t` are excluded (sticky date); it equals the Monte Carlo `expected_exposure` of the same swap within the Monte Carlo error at every grid point (test `ccr.ee_analytic_vs_simulated`); valid for the risk-neutral measure only (a check of the engine's EE, not a real-world measure).
- Golden: at the last grid point at or after the maturity the EE is 0.

### `riskvalidation.ccr.exposure.rung1_ead`

```python
def rung1_ead(v: float, c: float, addon_aggregate: float, margined: bool = False, th: float = 0.0, mta: float = 0.0, nica: float = 0.0) -> float: ...
```

- Units: money in one currency.
- Invariants: decision D3: ladder rung 1 is SA-CCR's `1.4 (RC + PFE)`; the function calls `riskvalidation.regulatory.sa_ccr` and equals its `netting_set_ead(...).ead` exactly.
- Golden: the CRE99 netting set 5 inputs of `engine-regulatory-api` give 1,878.9 (printed 1,879), to one unit.

## Module `riskvalidation/ccr/collateral.py`

ORE credit support amount and delivery amount equations with the close-out grid approach and a sticky-date close-out (addendum R3, ORE `xva.tex` at tag 1.8.17.0). The Andersen, Pykhtin and Sokol timelines are not modelled; that limit is stated in the document.

### `riskvalidation.ccr.collateral.credit_support_amount`

```python
def credit_support_amount(npv: np.ndarray, independent_amount: float, threshold_receive: float, threshold_pay: float) -> np.ndarray: ...
```

- Units: money; the result as `npv`.
- Invariants: with `x = NPV + IA`: `max(0, x - Th_rec)` if `x >= 0`, `min(0, x + Th_pay)` if `x < 0` (R3); with `NPV = 0`, `Th_rec = 0` and `IA > 0` the amount equals `IA` (the independent amount is an offset to the threshold).
- Golden: `NPV = 100`, `IA = 0`, `Th_rec = 0` gives 100; `NPV = 100`, `Th_rec = 30` gives 70; `NPV = -50`, `Th_pay = 20` gives -30; `NPV = 0`, `IA = 5` gives 5.

### `riskvalidation.ccr.collateral.delivery_amount`

```python
def delivery_amount(csa: np.ndarray, collateral: np.ndarray, outstanding_calls: np.ndarray, mta: float) -> np.ndarray: ...
```

- Units: money.
- Invariants: `Delta = CSA - C - M`; `D = Delta` if `|Delta| >= MTA`, else 0 (R3); with `MTA = 0` it is `Delta`.
- Golden: `CSA = 100`, `C = 90`, `M = 0`, `MTA = 10` gives 10; `C = 92` gives 0 (the shortfall 8 is below the MTA).

### `riskvalidation.ccr.collateral.mpor_floor`

```python
def mpor_floor(repo_only: bool = False, n_trades: int = 0, illiquid: bool = False, disputes_over_two: bool = False) -> int: ...
```

- Units: the result in business days.
- Invariants: CRE53.24: 5 for repo-style netting sets, 10 otherwise; 20 when the number of trades exceeds 5000 or the collateral is illiquid or an OTC derivative cannot be easily replaced; CRE53.25: more than two disputes longer than the MPoR over two quarters double the floor.
- Golden: `mpor_floor()` = 10; `mpor_floor(repo_only=True)` = 5; `mpor_floor(n_trades=5001)` = 20; `mpor_floor(disputes_over_two=True)` = 20.

### `riskvalidation.ccr.collateral.mpor_with_remargining`

```python
def mpor_with_remargining(floor: int, remargining_days: int) -> int: ...
```

- Units: business days.
- Invariants: CRE53.26 `F + N - 1`; `N = 1` gives `F`.
- Golden: `(10, 1)` gives 10; `(10, 5)` gives 14 (R3).

### `riskvalidation.ccr.collateral.collateralised_exposure`

```python
def collateralised_exposure(value_closeout: np.ndarray, collateral: np.ndarray) -> np.ndarray: ...
```

- Units: `value_closeout` (P, K) the netting-set value on the close-out grid, `collateral` (P, K) the balance determined at the default date minus the MPoR; money.
- Invariants: the residual `max(V(t) - C(t), 0)` (R3, Hull-White equation 4); positive "even if minimum transfer amounts and thresholds are zero" (because of the lag); with zero threshold and an MPoR tending to zero the exposure tends to zero (the close-out value tends to the collateral); never above the uncollateralised exposure plus the maximum collateral posted by the bank.
- Golden: the ORE lagged toy example of R3: value 10, collateral 8 gives residual 2.

### `riskvalidation.ccr.collateral.variation_margin_exposure`

```python
def variation_margin_exposure(values_main: np.ndarray, values_closeout: np.ndarray, independent_amount: float, threshold_receive: float, threshold_pay: float, mta: float) -> tuple[np.ndarray, np.ndarray]: ...
```

- Units: `values_main` and `values_closeout` (P, K) money on the default grid and on the grid offset by the MPoR; the result `(exposure, collateral_balance)` each (P, K).
- Invariants: the balance follows `credit_support_amount` and `delivery_amount` on the main grid; the exposure is `collateralised_exposure(values_closeout, balance)`; the cash flows of the close-out window are those of the sticky-date approach (a swap with no flows in the window needs no spike); an uncollateralised netting set takes the main grid value (ORE).
- Golden: threshold and MTA zero, a path whose value is constant gives exposure 0.

### `riskvalidation.ccr.collateral.dynamic_initial_margin`

```python
def dynamic_initial_margin(values_now: np.ndarray, values_mpor: np.ndarray, flows: np.ndarray, quantile: float, horizon_days: int, mpor_days: int, order: int = 2, regressor: np.ndarray | None = None) -> np.ndarray: ...
```

- Units: `values_now` and `values_mpor` (P,) the netting-set value at `t` and at `t + MPoR`, `flows` (P,) the cash flows in the window, all in money; `regressor` (P,) a market variable (default `values_now`); the result (P,) the DIM per path in money.
- Invariants: R2 (ORE `xva.tex`, `dimregressioncalculator.cpp`): `X = V(t + MPoR) + F - V(t)`; `E[X^2]` by regression of `X^2` on a polynomial of the regressor of the given order (order 0 is the sample variance); `S = sqrt(max(E[X^2] - E[X]^2, 0))` with `E[X]` the sample mean; `DIM = Phi^{-1}(quantile) S sqrt(horizon_days / mpor_days)`; zero where `S` is zero; non-negative; labelled a regression proxy, never SIMM (SIMM is not used: its public notice restricts use to a market participant's own transactions).
- Golden: order 0, `X` samples `[-2, -1, 1, 2]` (zero flows, `values_now = 0`), quantile 0.99, `horizon_days = mpor_days`: `S = sqrt(2.5) = 1.581139` and `DIM = 2.326348 x 1.581139 = 3.678279` (recomputed; the guide's rounded factor 2.33 gives 3.684053).

### `riskvalidation.ccr.collateral.apply_initial_margin`

```python
def apply_initial_margin(exposure_before_im: np.ndarray, dim: np.ndarray) -> np.ndarray: ...
```

- Units: money.
- Invariants: `max(exposure - DIM, 0)` (R2, `nettedexposurecalculator.cpp`); at most `exposure_before_im`; with `dim = 0` it is unchanged; IM applies only with variation margin ("don't apply initial margin without VM"): the caller passes the VM exposure.
- Golden: exposure 5, DIM 2 gives 3; exposure 1, DIM 2 gives 0.

## Module `riskvalidation/ccr/cva.py`

### `riskvalidation.ccr.cva.survival_from_spread`

```python
def survival_from_spread(spread: np.ndarray, t: np.ndarray, lgd: float) -> np.ndarray: ...
```

- Units: `spread` per year (decimal), `t` years, `lgd` in (0, 1]; the result in (0, 1].
- Invariants: the credit triangle `lambda = s / LGD`, `S(t) = exp(-s t / LGD)` (dossier 05 C.2, Hull-White equation 6 and page 13); `S(0) = 1`; non-increasing in `t`; a zero spread gives 1.
- Golden: `s = 0.012`, `LGD = 0.6`, `t = 5` gives `exp(-0.1) = 0.904837` (recomputed).

### `riskvalidation.ccr.cva.default_probabilities`

```python
def default_probabilities(survival: np.ndarray) -> np.ndarray: ...
```

- Units: `survival` (K+1,) at `t_0 = 0, ..., t_K`; the result (K,).
- Invariants: `PD(t_{i-1}, t_i) = S(t_{i-1}) - S(t_i)`; non-negative; sums to `S(0) - S(t_K)`.
- Golden: `[1, 0.9, 0.8]` gives `[0.1, 0.1]` (arithmetic).

### `riskvalidation.ccr.cva.cva`

```python
def cva(epe_discounted: np.ndarray, pd: np.ndarray, lgd: float) -> tuple[float, np.ndarray]: ...
```

- Units: `epe_discounted` (K,) money (the discounted EE at `t_i`), `pd` (K,), `lgd` in (0, 1]; the result `(cva, terms)` with `terms` (K,) the bucket terms in money.
- Invariants: dossier 05 C.2 `CVA = sum PD(t_{i-1}, t_i) LGD EPE(t_i)` (the advanced discretisation); CVA is a positive cost; with a zero spread (`pd = 0`) CVA is exactly 0; linear in `lgd` and in the EE; the document's `cva_dva.buckets` are `terms`, so CVA recomputed from EE equals the document value (test `ccr.cva_recomputed_from_ee`).
- Golden: `epe = [10, 20]`, `pd = [0.1, 0.1]`, `lgd = 0.6` gives `0.6 + 1.2 = 1.8` (arithmetic).

### `riskvalidation.ccr.cva.dva`

```python
def dva(ene_discounted: np.ndarray, pd_bank: np.ndarray, lgd_bank: float) -> tuple[float, np.ndarray]: ...
```

- Units: as `cva` with the bank's own default probabilities and the discounted ENE.
- Invariants: `DVA = sum PD_Bank LGD_Bank ENE(t_i)` (dossier 05 C.2); a positive benefit; zero with a zero bank spread; the simple form `BCVA = CVA - DVA` (the first-to-default form is not implemented, stated).
- Golden: the `cva` golden with the ENE in place of the EPE gives 1.8.

### `riskvalidation.ccr.cva.b_from_two_points`

```python
def b_from_two_points(w1: float, hazard1: float, w2: float, hazard2: float) -> float: ...
```

- Units: `w` in USD million of portfolio value, hazards per year; the result per USD million.
- Invariants: `b = (ln h2 - ln h1) / (w2 - w1)` for a flat hazard term structure (Hull-White 2012 page 16); `h1 = h2` gives 0.
- Golden: `w = 3` and `20` USD million, hazards `0.05` and `0.10` give `b = 0.040773` (printed 0.0408 in the paper, tolerance 5e-5).

### `riskvalidation.ccr.cva.wwr_calibrate_a`

```python
def wwr_calibrate_a(w: np.ndarray, survival_target: np.ndarray, dt: np.ndarray, b: float, sigma_noise: float = 0.0, eps: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]: ...
```

- Units: `w` (P, K) the simulated portfolio value in the unit `b` is stated in; `survival_target` (K,) the spread-implied survival `exp(-s_k t_k / (1 - R))`; `dt` (K,) years; the result `(a, h)` with `a` (K,) and the hazards `h` (P, K) per year.
- Invariants: hazard `h_ij = exp(a_i + b w_ij + sigma eps_ij)`; sequential calibration (Hull-White Appendix, page 22): for each `k` the average over paths of `exp(-sum_{i <= k} h_ij dt_i)` equals `survival_target[k]` (the largest error is reported in `a_calibration_max_error` of the document, at most `1e-10`); `k = 1` by a root search from `w_1j`, then `k = 2` from `w_2j` and the `h_1j`, and so on; with `b = 0` every path has the same hazard.
- Golden: the Appendix three-path example, copied inputs: `sigma = 0`, `m = 3`, spread 1 percent at every maturity, recovery 0, `dt = 0.5`, `b = 0.01`, `w` at step 1 `[100, 200, 300]`, at step 2 `[100, 300, 400]`: `a_1 = -6.9128`, `h_1 = [0.00270, 0.00735, 0.01998]`, `a_2 = -7.8509`, `h_2 = [0.00106, 0.00782, 0.02126]` (the paper's printed digits; recomputed on the printed equations: `a_1 = -6.91283`, `a_2 = -7.85077`, `h_1 = [0.002705, 0.007352, 0.019984]`, `h_2 = [0.001059, 0.007822, 0.021263]`; tolerance one unit of the last printed digit).

### `riskvalidation.ccr.cva.wwr_cva`

```python
def wwr_cva(w: np.ndarray, exposure_discounted: np.ndarray, survival_target: np.ndarray, dt: np.ndarray, lgd: float, b: float) -> tuple[float, float]: ...
```

- Units: `exposure_discounted` (P, K) the discounted positive exposure per path and grid point (money); the result `(cva, mc_se)`.
- Invariants: the Hull-White model (B1): `CVA = LGD sum_i mean_j [PD_ij E_ij]` with `PD_ij` the path-wise default probability in the bucket from the calibrated hazards; with `b = 0` it equals the independent `cva` on the same paths exactly (bit for bit: the same arithmetic is used); non-decreasing in `b` for a positively correlated exposure (wrong-way risk raises CVA); the sweep over the named grid of `b` is the document's `wrong_way_risk.sweep`; ORE's wrong-way example is a different model (a correlated credit LGM), so no ORE golden applies.
- Golden: `b = 0` equals the independent CVA exactly (invariant); the Hull-White 2012 Tables 1 and 2 (CVA at `b = 0` of 0.048, 0.036, 0.011, 0.002 and the percentage impacts at `b = 0.03`) are an FX forward and are not reproduced here (UNVERIFIED as a swap check).

## Module `riskvalidation/validation/ccr.py`

Each function returns a `TestResult` whose `test_id` is prefixed `ccr.` and whose rows validate against `common/test-result`.

### `riskvalidation.validation.ccr.ee_analytic_vs_simulated`

```python
def ee_analytic_vs_simulated(ee_analytic: np.ndarray, ee_simulated: np.ndarray, mc_se: np.ndarray, k_se: float = 3.0) -> TestResult: ...
```

- Units: money (K,) each.
- Test id: `test_id = "ccr.ee_analytic_vs_simulated"`. `statistic` is the largest `|analytic - simulated| / mc_se`; `metric` the largest absolute difference.
- Light: green when every grid point is within `k_se` standard errors, red otherwise; `extras["thresholds"] = {"k_se": ...}`.
- Golden: identical arrays give green with `statistic` 0; a difference of `4 mc_se` at one point gives red.

### `riskvalidation.validation.ccr.martingale_discounted_bonds`

```python
def martingale_discounted_bonds(discounted_bond_means: np.ndarray, p0: np.ndarray, mc_se: np.ndarray, k_se: float = 3.0) -> TestResult: ...
```

- Units: unitless (K,).
- Test id: `test_id = "ccr.martingale_discounted_bonds"`. `statistic` is the largest `|mean - P(0, T)| / mc_se`.
- Light: green within `k_se`, red otherwise.
- Golden: means equal to `p0` give green; the theta fit that reprices `P(0, T)` to `1e-12` is the exact version (a unit test of `bond_price`).

### `riskvalidation.validation.ccr.eepe_recomputed`

```python
def eepe_recomputed(grid: np.ndarray, ee: np.ndarray, eepe_reported: float, rel_tol: float = 1e-9) -> TestResult: ...
```

- Units: money.
- Test id: `test_id = "ccr.eepe_recomputed"`. `statistic` is the absolute residual; `metric` the relative residual.
- Light: green when the relative residual is at most `rel_tol`, red otherwise.
- Golden: grid `[0.25, 0.5, 1.0]`, EE `[1, 3, 2]` and a reported 2.5 gives green; a reported 2.0 gives red (2.0 is the plain EPE, not the effective one).

### `riskvalidation.validation.ccr.cva_recomputed`

```python
def cva_recomputed(epe_discounted: np.ndarray, pd: np.ndarray, lgd: float, cva_reported: float, rel_tol: float = 1e-9) -> TestResult: ...
```

- Units: money.
- Test id: `test_id = "ccr.cva_recomputed"`. `statistic` the absolute residual; `metric` the relative one.
- Light: green when the relative residual is at most `rel_tol`.
- Golden: the `cva` golden (1.8) reported as 1.8 gives green; 1.9 gives red.

### `riskvalidation.validation.ccr.path_convergence`

```python
def path_convergence(ee_by_path_count: dict[int, np.ndarray], cva_by_path_count: dict[int, float], k_se: float = 3.0) -> TestResult: ...
```

- Units: money; the keys are increasing path counts.
- Test id: `test_id = "ccr.path_convergence"`. `statistic` is the largest relative change of the EE profile between the two largest path counts; `metric` the relative change of CVA.
- Light: green when the change is within the Monte Carlo error implied by the smaller count, amber within `2 k_se`, red beyond; `extras["thresholds"] = {"k_se": ...}`.
- Golden: identical profiles at every count give green with `statistic` 0; fewer than two path counts gives `not_evaluated` with its reason.

### `riskvalidation.validation.ccr.reconcile_ee_profile`

```python
def reconcile_ee_profile(ee: np.ndarray, mc_se: np.ndarray, reference_ee: np.ndarray, reference_se: np.ndarray, k_se: float = 2.0) -> TestResult: ...
```

- Units: money (K,) each; the reference profile (ORE's, passed in as arrays) and its Monte Carlo error.
- Test id: `test_id = "ccr.reconcile_ee_profile"`. `statistic` is the largest `|ee - reference| / sqrt(mc_se^2 + reference_se^2)`; `extras["agreement"]` lists the per-point difference and combined error (the document's `ore_reconciliation.agreement`).
- Light: green when every point is within `k_se` combined standard errors, red otherwise.
- Golden: identical profiles give green; a point at `3` combined standard errors gives red under the default `k_se = 2`.

### `riskvalidation.validation.ccr.pfe_exceedance_backtest`

```python
def pfe_exceedance_backtest(realised: np.ndarray, pfe_forecast: np.ndarray, quantile: float) -> TestResult: ...
```

- Units: `realised` (N,) the realised mark-to-market of the revalued book, `pfe_forecast` (N,) the forecast PFE at `quantile`, money.
- Test id: `test_id = "ccr.pfe_exceedance_backtest"`. `n_events` the number of exceedances; `statistic` the Kupiec likelihood ratio; `p_value` its chi-square(1) value. A secondary row (BCBS 185 paragraph 27: exception counts assume independence, and the data may overlap).
- Light: green when `p_value` is at least 0.05, amber below 0.05, red below 0.01; `extras["thresholds"]`.
- Golden: `N = 100`, `quantile = 0.95` and 5 exceedances give `statistic` 0 and green; 0 exceedances give a likelihood ratio of `-2 N ln(quantile)` = 10.2587 (recomputed) and red.

### `riskvalidation.validation.ccr.pit_exposure_backtest`

```python
def pit_exposure_backtest(realised: np.ndarray, simulated: np.ndarray, critical_simulated: dict[str, float] | None = None, effective_sample_size: float | None = None) -> TestResult: ...
```

- Units: `realised` (N,) the realised values at the horizon, one per backtest date; `simulated` (N, P) the simulated sample at the same horizon.
- Test id: `test_id = "ccr.pit_exposure_backtest"`. `statistic` is the Anderson-Darling `W^2`; `extras` carry the PITs, the iid critical values and the simulated ones.
- Light: PIT of each realised value by `(i + 1) / (N_sim + 2)` with `1 / (N_sim + 2)` and `(N_sim + 1) / (N_sim + 2)` the tails (R5, Formenti et al. arXiv 1505.04593); `W^2 = -n - sum (2k - 1) / n [ln F(x_k) + ln(1 - F(x_{n+1-k}))]`; green below the simulated 5 percent critical value, amber between the 5 and 1 percent values, red above the 1 percent value; the critical values come from simulating the whole backtest under the model itself with the same dates and overlapping horizons (B5), the iid table values `1.248, 1.610, 1.933, 2.492, 3.880, 4.500, 6.000` (upper-tail probabilities 0.25, 0.15, 0.10, 0.05, 0.01, 0.005, 0.001) reported beside them; the effective sample size is stated.
- Golden: PITs `(i + 1) / (n + 2)`-uniform give a small `W^2`; the iid table values above; the PITs of a realised path drawn from the model itself have the size of the nominal level, and a halved sigma has power (U9-E2 tests); with PITs `[0.25, 0.5, 0.75]`, `W^2 = 0.269431` (recomputed from the formula, tolerance 5e-7).

## UNVERIFIED and open items

- The HW1F journal derivations (Hull and White 1990 and 1994, Jamshidian 1989) are not read as papers; the closed forms are transcribed from QuantLib 1.44 and the C12 bake reconciles the engine against it (sizing B4).
- The Andersen, Pykhtin and Sokol (2017) MPoR timelines are not modelled; the document states the limit (sizing B3).
- The Anderson-Darling critical values for the overlapping-horizon backtest come from simulating the backtest under the model; the Ruiz (2014) and Anfuso et al. (2014) procedures were not read (addendum R5).
- The default of ORE's `horizonCalendarDays` is not read (addendum R2); the contract takes `horizon_days` as a named parameter of the document.
- ORE's wrong-way example is a different model (correlated credit LGM): the wrong-way variant has no ORE reconciliation and no ORE golden.
- No open CDS spread series is known (R5 of the sizing); the base credit curve is the HQM minus Treasury proxy of addendum R10, a floor for lower ratings.
