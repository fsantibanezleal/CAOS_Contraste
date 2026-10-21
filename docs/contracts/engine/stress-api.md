# Engine stress API contract: `engine-stress-api` 2.0.0

Owner: U13-S (unit sizing `plans/contraste/units/U13-sizing.md`, CAOS_MANAGE). Implemented by U13-E2 in `riskvalidation.stress` and
`riskvalidation.validation.stress` (repository CAOS_RiskValidation, released with the one engine tag of batch 3, R1 of the sizing); called
by the C18 bake (U13-P1). The tests of every function are written by U13-E2 against this file: a function exists with exactly the
signature below, and each golden value or invariant is a test. Changing a signature, a unit or a golden value is a breaking change (a new
major version of this contract). Sources: dossier 05 (`wip/contraste/05-market-ccr-alm-liquidity-oprisk-stress-sota-2026-10-04.md`, H.1
the three-layer architecture, H.2 scenario generation, H.4 the EBA 2025 test, H.5 reverse stress, H.7 what validators test), dossier 04 (I.1
to I.2, the satellites and the conditional PD), dossier 03 (B.2, B.4, the Annex 3 rows, G.4 the Chilean capital stack, H.2 the P2G proxy, M the
Santander Chile capital figures), dossier 01 (J.4 the reverse stress formulation), the U13 research addendum
(`wip/contraste/u13-research-addendum-2026-10-18.md`, F6 the EBA note, F7 the Annex 3 form, F8 the NGFS variables) and the unit sizing
decisions Q5 to Q13, E2 to E5.

Scope. Decision E1 of the sizing (2026-10-19) keeps C19 (supervisory stress model replication) planned: no Federal Reserve portfolio type is
replicable from the public record, so `riskvalidation/stress/supervisory.py` is void, this contract has no supervisory function and no
supervisory replication test, and BL-081 revisits it. The engine computes; it states no compliance claim. The formal statement of the
reverse stress and the P2G proxy are Contraste's, not regulatory text. Every constant and golden value is transcribed from the source on its
line or computed from a formula stated on its line and labelled as computed; an item a source marks UNVERIFIED is marked UNVERIFIED here.

Version history: 1.0.0, the first contract; 2.0.0 after the U13-E2 review and fix round (U13 decisions Z6 to Z9): `InternalTarget` carries `p2r` and the Annex 3 rows 7, 7.2 and 8 read it; `annex3_summary` refuses an RWA that differs from the plan's; the `not_evaluated` rows carry `model_id` and `segment`; the goldens of `satellite_backcast` and `bottom_up_vs_top_down` corrected to agree with their own light rules (a changed golden is breaking by this contract's rule); AT1 and T2 constant in every case of `capital_plan`.

## Conventions (all functions)

- Arrays are `numpy.ndarray` of `float64`. Shapes: `T` quarters of history, `H` projected quarters (12 in C18), `P` regressors, `K` factors,
  `Y` years (3 in C18). Money is a float in one currency (CLP millions in C18) and never converted by the engine. Rates, ratios and
  probabilities are decimals; a path keeps the unit of its source (percent for the Federal Reserve and EBA paths) and says so.
- Quarters are ISO dates of the quarter end (`"2019-12-31"`); a window is explicit (`start`, `end`), never implied by the data. The engine
  hard-codes no sample end: the product's contract refuses a fit window that reaches 2020 (C18 schemas) and the back-cast test refuses a
  window that overlaps the episode it predicts.
- Randomness: a function that draws or starts a search takes an integer `seed` and uses `numpy.random.Generator(numpy.random.PCG64(seed))`.
  No function reads global state, the clock or the environment; inputs are never mutated.
- Dataclasses are frozen. A function that cannot compute a value raises `ValueError` with the reason; a validation function returns a
  `not_evaluated` row with its reason in `notes` and `statistic`, `p_value` and `metric` all null, carrying `model_id` and `segment` as the evaluated rows do (2.0.0). Nothing returns a placeholder number.
- A validation function returns one `TestResult` of `riskvalidation` (`core/result.py`), serialised by `TestResult.to_dict()` into a row that
  validates against `common/test-result` (`docs/contracts/schemas/common/test-result.schema.json`); the parameters of a light rule that are not
  alphas travel in `extras["thresholds"]` beside `alpha_amber` and `alpha_red` (null here). The thresholds are policy parameters proposed by
  this contract (conventions of the case, none regulatory). All take `model_id` and `segment` last.
- Static balance sheet (decision E4; EBA Methodological Note 2025-01-20, F6 of the addendum): para 33 (p.18) assets and liabilities that mature or
  amortise within the horizon are replaced with similar instruments, no workout or cure of S3 assets, no capital measures taken after the
  reference date; para 34 (p.18) the same business mix and model; para 90 (p.36) S3 exposures are not replaced, new S3 exposures move into the
  stock of S3 keeping the total constant, no cures, charge-offs or write-offs within the three years; para 91 (p.36) the initial residual maturity
  is kept; para 92 (p.37) a constant balance sheet for impairments; para 24 (p.16) year-end starting figures and a three-year horizon. Para 133 (reversion of the
  adverse parameters linearly over six years after the horizon; the paragraph number 132 is UNVERIFIED in the record) matters only if a bake extends
  beyond three years; C18 does not.

## Reused engine functions

Reused unchanged from the engine (R13 of the sizing); this contract names them and never restates them.

| Function | Used by |
|---|---|
| `riskvalidation.engines.vasicek.conditional_pd`, `riskvalidation.engines.vasicek.implied_factor` | the conditional PD under a scenario and the implied systematic factor (04 l.819-827); the probit link of a satellite is the Vasicek-consistent choice (04 l.785-795) |
| `riskvalidation.provisions.term_structure.ttc_to_pit`, `riskvalidation.provisions.term_structure.implied_z` | the through-the-cycle to point-in-time map of a rate path |
| `riskvalidation.irrbb.eve_nii` | the IRRBB side of the capital engine (the C15 dynamic NII behind the PPNR row) |
| `riskvalidation.core.result.TestResult` | every validation function |

## Module `riskvalidation/stress/satellites.py`

The satellite of a default or loss rate, `g(DR_t) = alpha + sum_k phi_k g(DR_(t-k)) + sum_l beta_l' X_(t-l) + eps`, with `g` the probit
(Vasicek-consistent) or the logit, fitted by OLS in NumPy with standard errors and an explicit sample window (04 l.785-795). Regressors are the
agency series only (decision Q7).

### `riskvalidation.stress.satellites.link`

```python
def link(name: str, p: np.ndarray) -> np.ndarray: ...
```

- Units: `name` in `"probit"`, `"logit"`, `"identity"`; `p` rates; returns the link value. `probit`: `Phi^-1(p)`; `logit`: `ln(p / (1 - p))`; `identity`: `p`, the linear form of the Federal Reserve's own PD regression (05 l.399), for the segments whose rate is zero or negative in some quarters (net recoveries: commercial and residential real estate in the Board's table).
- Golden: `link("probit", 0.5) = 0.0`; `link("logit", 0.2) = -1.3863` (computed, `ln 0.25`); `link("identity", -0.0003) = -0.0003`.
- Invariants: strictly increasing; `ValueError` for a probit or logit `p` outside `(0, 1)` (a non-positive rate: use the identity link) and for an unknown name; the identity link takes any finite `p`.

### `riskvalidation.stress.satellites.inverse_link`

```python
def inverse_link(name: str, x: np.ndarray) -> np.ndarray: ...
```

- Units: link values; returns rates in `(0, 1)` for the probit and logit, and the value itself (signed) for the identity.
- Golden: `inverse_link("probit", 1.6449) = 0.9500` (to `5e-5`); `inverse_link("logit", -1.3863) = 0.2000`; `inverse_link("identity", -0.0003) = -0.0003`.
- Invariants: `inverse_link(name, link(name, p)) = p` to `1e-12` (the probit round trip DR to Z to DR of 04 l.791-793).

### `riskvalidation.stress.satellites.SatelliteFit`

```python
@dataclass(frozen=True)
class SatelliteFit:
    link: str
    window_start: str            # ISO quarter end
    window_end: str
    n_obs: int
    ar_order: int
    regressor_names: tuple[str, ...]
    lags: tuple[int, ...]
    coefficient_names: tuple[str, ...]   # "intercept", "ar_1".., "<regressor>_lag<k>"
    estimates: tuple[float, ...]
    std_errors: tuple[float, ...]
    r_squared: float
    residual_sd: float
```

- Units: dimensionless on the link scale; the window as ISO dates. `link` is the link the segment was fitted with: `identity` for commercial and residential real estate, whose windows start at 1991Q1 (the Board's table is missing both series from 1985Q1 to 1990Q4) and hold non-positive quarters (13 and 6 in 1991Q1 to 2019Q4); `probit` for the others, whose windows start 1985Q1. The document records `non_positive_quarters_in_window` beside the link.
- Invariants: maps onto the models document `fit.satellites[*]` (`link`, `sample_window`, `ar_order`, `n_obs`, `regressors`, `coefficients` with `name`, `estimate`, `std_error`, `fit_statistics`); `n_obs` is the number of quarters of the window less the largest lag (`max(ar_order, lags)`), the check of `semantics.py`.

### `riskvalidation.stress.satellites.fit_satellite`

```python
def fit_satellite(rates: np.ndarray, regressors: np.ndarray, regressor_names: Sequence[str], lags: Sequence[int], ar_order: int, link_name: str,
                  quarters: Sequence[str], window_start: str, window_end: str) -> SatelliteFit: ...
```

- Units: `rates` (T,) signed decimals (in `(0, 1)` for the probit and logit; net recoveries make a rate zero or negative and need the identity link), `regressors` (T, P) in the unit of each series, `quarters` (T,) ISO quarter ends, ascending and contiguous. OLS by `numpy.linalg.lstsq` on the observations of the window, with classical standard errors `sqrt(diag(s^2 (X'X)^-1))`.
- Golden (identity): `link_name = "identity"`, `rates = (-0.002, 0.0, 0.002, 0.004)`, `ar_order = 0`, one regressor `x = (0, 1, 2, 3)`: estimates `(-0.002, 0.002)`, `r_squared = 1.0`; the same rates with `link_name = "probit"` raise `ValueError` (net recoveries, non-positive).
- Golden: an exact line, `link(rate) = 1 + 2 x` with `ar_order = 0` and one regressor at lag 0 over four quarters `x = (0, 1, 2, 3)`: estimates `(1.0, 2.0)`, standard errors `(0.0, 0.0)`, `r_squared = 1.0`; the estimates equal `numpy.linalg.lstsq` to `1e-10`.
- Invariants: only quarters inside `[window_start, window_end]` enter; `ValueError` for a window outside the data, a gap in `quarters` (a missing quarter inside the window is never filled; one outside it is out of the window), a probit or logit fit on a non-positive rate (the reason reads "a probit or logit fit on a non-positive rate: the link needs a rate in (0, 1); use the identity link"), a probit or logit rate of 1 or more, a regressor name outside the agency list (`real_gdp_growth`, `unemployment_rate`, `cpi_inflation`, `treasury_3m`, `treasury_5y`, `treasury_10y`, `mortgage_rate`, `prime_rate`: the BBB corporate yield and the third-party index levels are not read, decision Q7), fewer observations than coefficients; `r_squared` in `[0, 1]`.

### `riskvalidation.stress.satellites.SatelliteProjection`

```python
@dataclass(frozen=True)
class SatelliteProjection:
    link_values: np.ndarray    # (H,)
    rates: np.ndarray          # (H,) in (0, 1)
```

- Units: link scale and decimal rates; `rates` are signed on the identity link and may be non-positive, read as net recoveries.
- Invariants: `rates = inverse_link(link, link_values)`; maps onto the variant block `outputs.satellites.fed_loan_types[*].quarters[*]` (`rate`, `link_value`).

### `riskvalidation.stress.satellites.project_scenario`

```python
def project_scenario(fit: SatelliteFit, last_link_values: np.ndarray, regressor_history: np.ndarray, regressor_path: np.ndarray) -> SatelliteProjection: ...
```

- Units: `last_link_values` (ar_order,) the last observed link values, most recent last; `regressor_history` (max lag, P) the last observed regressors; `regressor_path` (H, P) the transposed scenario path. The recursion plugs the path and recovers `DR_t` (04 l.785-795).
- Golden (computed): `alpha = 0`, `phi_1 = 0.5`, one regressor at lag 0 with `beta = 0.1`, last link value `1.0`, path `(2.0, 2.0)`: link values `(0.7, 0.55)` and probit rates `(0.758036, 0.708840)`.
- Invariants: monotone in the path: a regressor path that is weakly higher everywhere gives weakly higher link values when every `beta >= 0`; `ValueError` for shapes that do not match the fit; the conditional PD under a scenario and the implied factor are the reused `engines.vasicek` functions, not rewritten here.

## Module `riskvalidation/stress/paths.py`

Scenario path handling: the shape of a published path (its change from its jump-off) transposed onto the last observed value, reversion to the baseline after the published horizon, annual to quarterly conversion, deviation paths, and the check that a path's vintage does not postdate the observation date (SDD l.169). The engine form of the rule `cases/c06/macro.py` applies in the product (R14); its migration to this function is BL-079, and the engine test compares the two on C06's committed history.

### `riskvalidation.stress.paths.transpose_path`

```python
def transpose_path(levels: np.ndarray, source_jump_off: float, target_value: float, n: int) -> np.ndarray: ...
```

- Units: any unit of the path (percent for Federal Reserve paths); `n` the number of periods returned. `target_value + (levels - source_jump_off)` for the first `n` periods, periods aligned by their distance from the jump-off (decision Q6).
- Golden: `levels = (6, 8, 10)`, `source_jump_off = 5`, `target_value = 3`, `n = 3`: `[4.0, 6.0, 8.0]`.
- Invariants: the first difference of the result equals that of the source; `ValueError` for `n` above the length of `levels` (extend with `revert_to_baseline`).
- A level path of a growth regressor (the NGFS GDP level, `baseline-times-percent-deviation`): the transposed quarters of year `y` all carry that year's growth in percent, `(level_y / level_(y-1) - 1) * 100`, with `level_0` the source jump-off level; `semantics.py` `violations` checks it.

### `riskvalidation.stress.paths.revert_to_baseline`

```python
def revert_to_baseline(path: np.ndarray, baseline_tail: float, n: int, reversion_quarters: int) -> np.ndarray: ...
```

- Units: as the path; `n >= len(path)`. Past the published horizon the path reverts linearly to the baseline tail: for `k > len(path)`, `w = min(1, (k - len(path)) / reversion_quarters)` and `value = path[-1] + w (baseline_tail - path[-1])`. `REVERSION_QUARTERS = 12` is the product convention of `cases/c06/macro.py` (a convention, not a source value); it is the models field `capital_engine.reversion_quarters`. The EBA note reverts the adverse parameters over six years after the horizon (para 133, UNVERIFIED paragraph number), a different rule that C18 does not need within three years.
- Golden: `path = (8.0,)`, `baseline_tail = 5.0`, `n = 14`, `reversion_quarters = 12`: the values at `k - len(path) = 1, 6, 12, 13` are `[7.75, 6.5, 5.0, 5.0]`.
- Invariants: the first `len(path)` values are unchanged; reaches the baseline tail at `k - len(path) = reversion_quarters` and stays; `ValueError` for `reversion_quarters < 1`.

### `riskvalidation.stress.paths.annual_to_quarterly`

```python
def annual_to_quarterly(year_end_levels: np.ndarray, jump_off_level: float) -> np.ndarray: ...
```

- Units: any; returns `4 * len(year_end_levels)` values. Quarter `k` (1 to 4) of year `y` is `prev + (cur - prev) k / 4`, the year-end levels joined linearly from the jump-off level; the fourth quarter equals the year-end level. Whether the EBA workbook values are year averages or year-end values is UNVERIFIED in the research record (F6); this contract treats them as year-end levels and the bake states it.
- Golden: `year_end_levels = (6, 8)`, `jump_off_level = 4`: `[4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0]`.
- Invariants: every year-end value is reproduced exactly; the result is piecewise linear.

### `riskvalidation.stress.paths.level_from_deviation`

```python
def level_from_deviation(baseline: np.ndarray, deviation: np.ndarray, kind: str) -> np.ndarray: ...
```

- Units: `kind` in `"plus"` (a level in the unit of the baseline plus an absolute deviation) and `"percent"` (the baseline times `1 + deviation / 100`). NGFS scenario runs hold deviations from the Baseline run (F8), so a level is the baseline plus the deviation (rates, unemployment) or the baseline times the percent difference (GDP).
- Golden: NGFS Delayed transition, United States, 2031 unemployment: baseline `4.442` plus deviation `0.106` is `4.548`; a GDP baseline `26000.0` with a percent difference of `-4.239` is `24897.86` (computed; the 2031 baseline GDP level is a fixture value, the record gives 25481.079 for 2030 only).
- Invariants: shapes must match; `ValueError` for an unknown `kind`.

### `riskvalidation.stress.paths.check_vintage`

```python
def check_vintage(vintage_date: str, observation_date: str) -> None: ...
```

- Units: ISO dates. Rejects a path whose vintage postdates the model's observation date (SDD l.169, the `macro_path` family rule).
- Golden: `("2026-02-04", "2026-08-31")` returns `None`; `("2027-01-01", "2026-08-31")` raises `ValueError`.
- Invariants: equal dates pass.

## Module `riskvalidation/stress/capital.py`

The capital engine of H.1 layer 3 on a static balance sheet under the EBA rules of the conventions (05 l.384, l.408, l.422); the three-year IAPE projection for the base, the stress without mitigation and the stress with mitigation, and the deficit (03 l.197-206); the internal capital target `OI >= 8% + c_DSIB + c_P2 + c_CCoB + c_CCyB + c_d` of RWA (03 l.152-169) with its headroom; the Chilean capital stack (03 l.911-920); the P2G proxy, a Contraste approximation (03 l.1001-1005); the rows of the Annex 3 summary (03 l.232-241; F7). The revenue side (decision Q10): the headline CET1 path is loss-only depletion (CET1 at the jump-off less the cumulative stressed losses, no invented revenue) and a labelled row adds PPNR from the C15 dynamic NII plus a stated constant fee and cost ratio.

### `riskvalidation.stress.capital.cet1_path_loss_only`

```python
def cet1_path_loss_only(cet1_0: float, losses: Sequence[float]) -> np.ndarray: ...
```

- Units: money; `losses` (Y,) the losses of each year, not negative; returns (Y,) CET1 at each year end.
- Golden: RWA 100, `cet1_0 = 11.0` (11 percent), `losses = (1.0, 2.0, 1.5)`: `[10.0, 8.0, 6.5]`, ratios `(0.10, 0.08, 0.065)` (hand-computed).
- Invariants: nonincreasing; the last value is `cet1_0 - sum(losses)`; `ValueError` for a negative loss.

### `riskvalidation.stress.capital.PpnrRow`

```python
@dataclass(frozen=True)
class PpnrRow:
    nii: float
    fee_income: float
    operating_cost: float
    ppnr: float
```

- Units: money.
- Invariants: `fee_income = fee_ratio * nii`; `operating_cost = cost_ratio * (nii + fee_income)`; `ppnr = nii + fee_income - operating_cost`; maps onto the document row `headline_cet1.ppnr.rows[*]`.

### `riskvalidation.stress.capital.ppnr_row`

```python
def ppnr_row(nii: float, fee_ratio: float, cost_ratio: float) -> PpnrRow: ...
```

- Units: `nii` money; `fee_ratio` fee income over NII, `cost_ratio` operating cost over (NII + fee income), both decimals in `[0, 1]`, named parameters labelled assumptions of the case (decision Q10); the definitions of the two ratios are this contract's proposal (the Federal Reserve's efficiency-ratio element of the 2026 PPNR suite, 05 H.3, is the precedent for a cost ratio; the dossiers give no model for PPNR, 05 l.402).
- Golden (computed): `nii = 660000`, `fee_ratio = 0.25`, `cost_ratio = 0.55`: `fee_income = 165000`, `operating_cost = 453750`, `ppnr = 371250`.
- Invariants: `ValueError` for a ratio outside `[0, 1]`; PPNR is a labelled row and never the headline.

### `riskvalidation.stress.capital.InternalTarget`

```python
@dataclass(frozen=True)
class InternalTarget:
    min_pe: float      # 0.08
    c_dsib: float
    c_p2: float
    c_ccob: float
    c_ccyb: float
    c_d: float
    oi: float
    p2r: float = 0.0   # the art. 66 quinquies requirement (2.0.0)
```

- Units: shares of RWA (decimals).
- Invariants: `oi = min_pe + c_dsib + c_p2 + c_ccob + c_ccyb + c_d`; maps onto the document block `internal_capital_target`. `p2r` is the CMF's art. 66 quinquies requirement, the field the 4 percent cap binds (decision W3), stored by `internal_capital_target`; the Annex 3 rows 7, 7.2 and 8 read it, never `c_p2` (2.0.0, U13 decision Z7).

### `riskvalidation.stress.capital.internal_capital_target`

```python
def internal_capital_target(c_dsib: float, c_p2: float, c_ccob: float, c_ccyb: float, c_d: float, p2r: float = 0.0) -> InternalTarget: ...
```

- Units: shares of RWA; `p2r` the art. 66 quinquies requirement (the floor of `c_p2`: `c_P2,bank >= c_66 quinquies`, 03 l.152-169). `c_p2` and `c_d` are labelled assumptions of the case (decision Q4); `c_d` may be zero (03 B.2: "podria ser nula").
- Golden (Santander Chile 2025-12-31 ratios, dossier 03 l.1324-1328, Ch$ million: CET1 `4,601,923` of RWA `41,715,467`, effective equity `7,047,321`; Pillar 2 `52,144`, so `0.125` percent of RWA, countercyclical `0.50`, systemic `1.50`, conservation `2.50` percent; computed, Contraste arithmetic and not a reported figure): `c_dsib = 0.015`, `c_p2 = 0.00125`, `c_ccob = 0.025`, `c_ccyb = 0.005`, `c_d = 0.0` give `oi = 0.12625`; the effective-equity ratio is `0.168938`, so the headroom (Annex 3 row 12, `1.1 - 5`) is `0.042688`.
- Invariants: `ValueError` for a negative component, `c_p2 < p2r`, or `p2r` above the 4 percent cap of RWA (03 l.52, l.253-254: the cap bounds the CMF's art. 66 quinquies requirement): the cap is `0.04 * 41,715,467 = 1,668,618.68` in the Santander figures, above the `52,144` Pillar 2 requirement. `c_p2` is the bank's own estimate, at least `p2r` (03 l.156-163), and `c_p2` has no cap.

### `riskvalidation.stress.capital.chilean_cet1_stack`

```python
def chilean_cet1_stack(c_ccyb: float, c_dsib: float, p2_cet1: float) -> float: ...
```

- Units: shares of RWA; returns the minimum CET1/RWA of the Chilean legal stack, `4.5% + 2.5% + RCC + c_DSIB + the CET1 share of c_P2` (03 G.4, l.911-920; RAN 21-13). The failure point of the reverse stress (decision Q11).
- Golden (computed): `c_ccyb = 0.005`, `c_dsib = 0.015`, `p2_cet1 = 0.0` give `0.090000`, so the Santander Chile CET1 ratio `0.110317` (`4,601,923 / 41,715,467`) stands `0.020317` above it; with the whole Pillar 2 requirement in CET1 (`p2_cet1 = 0.00125`) the stack is `0.09125`.
- Invariants: increasing in each argument; `ValueError` for a negative argument or `c_ccyb` above `0.025`.

### `riskvalidation.stress.capital.PlanYear`

```python
@dataclass(frozen=True)
class PlanYear:
    year: int                  # 1 to 3
    rwa: float
    cet1: float
    at1: float
    t2: float
    pe: float                  # cet1 + at1 + t2
    requirement_pct: float
    pe_pct: float
    headroom_pct: float        # pe_pct - requirement_pct
    deficit: float             # max(0, requirement_pct * rwa - pe)
```

- Units: money and shares of RWA.
- Invariants: `rwa` is the same every year (a static balance sheet, para 33); maps onto the document rows `capital_plan.cases[*].years[*]`.

### `riskvalidation.stress.capital.capital_plan`

```python
def capital_plan(rwa: float, cet1_0: float, at1: float, t2: float, base_cet1: Sequence[float], stress_losses: Sequence[float],
                 mitigation_effects: Sequence[float], oi: float, legal_minimum: float) -> dict[str, tuple[PlanYear, ...]]: ...
```

- Units: money; `base_cet1` (Y,) the base-case CET1 at each year end (the baseline scenario's `cet1_0 + cumulated (PPNR - losses)`, computed by the caller), `stress_losses` (Y,), `mitigation_effects` (Y,) the effect of the mitigation actions on CET1 of each year, not cumulated; `oi` and `legal_minimum` shares of RWA. Returns the keys `"base"` (requirement `oi`), `"stress-without-mitigation"` (CET1 from `cet1_path_loss_only`, requirement `legal_minimum`) and `"stress-with-mitigation"` (the loss-only path plus the cumulated mitigation effects, requirement `legal_minimum`). AT1 and T2 stay at their jump-off values in every case: no capital measure after the reference date (para 33).
- Golden (hand-computed): `rwa = 100`, `cet1_0 = 11`, `at1 = 2`, `t2 = 3`, `stress_losses = (1, 2, 1.5)`, `mitigation_effects = (0, 1, 1)`, `legal_minimum = 0.09625`: stress without mitigation CET1 `(10, 8, 6.5)`, PE `(15, 13, 11.5)`, `pe_pct = (0.15, 0.13, 0.115)`, headroom `(0.05375, 0.03375, 0.01875)`, deficit `(0, 0, 0)`; with mitigation CET1 `(10, 9, 8.5)`.
- Invariants: the mitigated PE is not below the unmitigated PE in any year; `ValueError` for series of unequal length.

### `riskvalidation.stress.capital.p2g_proxy`

```python
def p2g_proxy(cet1_ratio_0: float, cet1_ratios_severe: Sequence[float], usable_buffers_and_mitigation: float) -> float: ...
```

- Units: shares of RWA; returns `max(0, max_t [(CET1/RWA)_0 - (CET1/RWA)_t severe] - usable)` (03 l.1001-1005, FAQ 24: "the maximum deterioration inside the three-year projection horizon", referenced to CET1/RWA). A Contraste approximation: the CMF calibration grid is not public and the value is not a P2G requirement; the document block carries the label `contraste-approximation`.
- Golden (hand-computed): `cet1_ratio_0 = 0.11`, severe ratios `(0.10, 0.08, 0.065)`, usable `0.02`: the peak depletion is `0.045` and the proxy `0.025`.
- Invariants: never negative; nonincreasing in `usable`; zero when the severe ratios never fall below the start.

### `riskvalidation.stress.capital.annex3_summary`

```python
def annex3_summary(capital: Mapping[str, float], target: InternalTarget, rwa_by_risk: Mapping[str, float], internal_capital: Mapping[str, float],
                   plan: Mapping[str, tuple[PlanYear, ...]], mitigation_applies: bool) -> tuple[dict, ...]: ...
```

- Units: money in CLP millions (the form states thousand pesos; the document states millions, `money_unit`); shares of RWA. Returns the 34 rows of the CMF summary with the labels as printed (F7: Circular 2.365 of 2025-07-08, Resolution 6801; URL https://www.cmfchile.cl/portal/principal/623/articles-29808_doc_pdf.pdf, Annex 3 from pdf p.29): rows `1`, `1.1`, `1.2`, `1.3`, `2`, `2.T2`, `2.AT1`, `2.CET1`, `3`, `4`, `4.1`, `4.1.1`, `4.1.2`, `4.2`, `4.3`, `4.4`, `4.4.1`, `4.4.2`, `4.4.3`, `4.5`, `4.6`, `4.7`, `4.8`, `5`, `6`, `7`, `7.1`, `7.2`, `8`, `9`, `10.1`, `10.2`, `11`, `12`, each with the four columns A (percent of RWA), B (amount), C (legal requirement), D (internal measurement) as cells of status `value`, `RI` (an immaterial risk), `not-to-be-filled` (market and operational risk under the standardised method) or `not-applicable`. The row ids `2.T2`, `2.AT1`, `2.CET1` are this contract's ids for the three unnumbered components of row 2.
- Golden (computed): capital start CET1 `0.11`, AT1 `0.0125`, T2 `0.025` of RWA and OI `0.145`: row 1.1 is `0.1475`, row 12 is `0.0025`; row 7 is `0.08 + row 7.1 + row 7.2` (`0.09625` for `0.015` and `0.00125`); row 9 is `c_CCoB + c_CCyB`; row 10.1 is the largest CET1/RWA fall of the stress without mitigation and row 10.2 is `not-applicable` when `mitigation_applies` is false (the form: "N/A if the stress leads to no mitigation actions").
- Invariants: the row ids and labels equal the transcribed table (a test); row 3 column B is the RWA; row 5 is `oi`; row 12 is row 1.1 less row 5; row 8 is row 6 less row 7.2; row 7.2 is `target.p2r` (2.0.0); an RWA that differs from the capital plan's beyond 1e-9 relative raises `ValueError` naming both values (2.0.0, U13 decision Z9).

### `riskvalidation.stress.capital.eba_static_balance_sheet`

```python
def eba_static_balance_sheet(stage_balances: np.ndarray, new_s3_flows: np.ndarray) -> np.ndarray: ...
```

- Units: `stage_balances` (3,) money in stages 1, 2, 3; `new_s3_flows` (H,) money moving into stage 3 each period; returns (H, 3) the balances after each period. Para 90: new S3 exposures move into the stock of S3 and reduce S1 and S2 (pro rata to their balances), the total exposure is constant, nothing leaves S3 (no cures, charge-offs or write-offs), nothing is replaced.
- Golden (hand-computed): `stage_balances = (80, 15, 5)`, `new_s3_flows = (2, 3)`: stage 3 is `(7, 10)` and the total `(100, 100)`; stage 1 plus stage 2 is `(93, 90)`.
- Invariants: the total is constant; stage 3 is nondecreasing; no balance is negative (`ValueError` for a flow larger than S1 plus S2); the input is not mutated.

## Module `riskvalidation/stress/reverse.py`

Reverse stress: the most plausible scenario that reaches a pre-defined failure point, `z* = argmin x' Sigma^-1 x subject to L(x) >= l` (the minimum Mahalanobis distance scenario), closed form for a linear loss and `scipy.optimize` otherwise, with the plausibility of the solution. EBA/GL/2018/04 defines a reverse stress test as one that starts from the identification of a pre-defined outcome (01 l.884-889); the formal statement is Contraste's, not regulatory text (01 l.891-894; 05 H.5). In C18 the failure point is CET1 at the Chilean legal minimum stack (decision Q11). Empirical likelihood (Glasserman, Kang and Kang) is out: only its abstract is in the dossier (05 l.412, l.545).

### `riskvalidation.stress.reverse.ReverseSolution`

```python
@dataclass(frozen=True)
class ReverseSolution:
    method: str                 # "closed-form-linear" or "scipy-optimize"
    x_star: np.ndarray          # (K,) deviation of the factors from the baseline, natural units
    z_star: np.ndarray          # (K,) x_star over the factor sd
    distance: float             # sqrt(x' Sigma^-1 x)
    loss_at_x: float
    threshold: float
    converged: bool
```

- Units: factors in their natural units; loss and threshold in money.
- Invariants: maps onto the document block `solution` (`method`, `x_star`, `z_star`, `mahalanobis_distance`, `loss_at_z_star_clp_m`, `loss_threshold_clp_m`).

### `riskvalidation.stress.reverse.reverse_stress_linear`

```python
def reverse_stress_linear(gradient: np.ndarray, cov: np.ndarray, threshold: float) -> ReverseSolution: ...
```

- Units: `gradient` (K,) loss per unit of each factor (money per unit), `cov` (K, K) the factor covariance, `threshold` money. Closed form for `L(x) = g'x`: `x* = Sigma g l / (g' Sigma g)`, `distance = l / sqrt(g' Sigma g)`.
- Golden (computed): `Sigma = diag(1, 4)`, `g = (1, 1)`, `l = 5`: `g' Sigma g = 5`, `x* = (1, 4)`, `distance = 5 / sqrt(5) = 2.2361`, `loss = g'x* = 5`.
- Invariants: `loss_at_x = threshold` to `1e-9` relative; no point with `L(x) >= l` is closer (the distance is the minimum); `ValueError` for a non-positive-definite `cov`, `g' Sigma g = 0` or a negative threshold.

### `riskvalidation.stress.reverse.reverse_stress`

```python
def reverse_stress(loss_fn: Callable[[np.ndarray], float], cov: np.ndarray, threshold: float, starts: Sequence[np.ndarray], tolerance: float = 1e-6) -> tuple[ReverseSolution, tuple[ReverseSolution, ...]]: ...
```

- Units: as `reverse_stress_linear`; `loss_fn` maps the factor deviation to money. Minimises `x' Sigma^-1 x` subject to `L(x) >= threshold` with `scipy.optimize` (SLSQP) from each start; returns the best converged solution and the per-start results.
- Golden: for the linear loss of the golden above the best solution equals the closed form to `1e-6` from every start; for a quadratic loss `L(x) = x_1^2 + x_2^2` with `Sigma = I` and `l = 4` the distance is `2.0` and the solution lies on the circle `|x| = 2`.
- Invariants: at least three starts (else `ValueError`); `|loss_at_x - threshold| / threshold <= tolerance` for a converged start; the best distance is the minimum of the converged distances; `ValueError` when no start converges.

### `riskvalidation.stress.reverse.plausibility`

```python
def plausibility(distance: float, df: int) -> float: ...
```

- Units: `distance` the Mahalanobis distance, `df` the number of factors; returns `P(chi2_df >= distance^2)`, the tail probability of a scenario at least as far.
- Golden (computed): `distance = sqrt(5) = 2.2361`: `df = 2` gives `0.0821` (`exp(-2.5)`), `df = 3` gives `0.1718`.
- Invariants: decreasing in `distance`; `1.0` at distance 0; `ValueError` for `df < 1`.

## Module `riskvalidation/stress/scenario_models.py`

Rungs 2 and 3 of the macro stress ladder (05 H.2, l.388, l.390), optional extra `stress` (`statsmodels`): engine functions with their own acceptance tests that no C18 variant bakes (decision Q13). The Minnesota BVAR and the panel quantile satellite are backlog item BL-078.

### `riskvalidation.stress.scenario_models.VarFit`

```python
@dataclass(frozen=True)
class VarFit:
    intercept: np.ndarray        # (n,)
    coefficients: tuple[np.ndarray, ...]   # A_1 .. A_p, each (n, n)
    sigma: np.ndarray            # (n, n) residual covariance
```

- Units: the units of the variables.
- Invariants: `sigma` symmetric positive semi-definite.

### `riskvalidation.stress.scenario_models.fit_var`

```python
def fit_var(y: np.ndarray, lags: int) -> VarFit: ...
```

- Units: `y` (T, n). OLS equation by equation of `y_t = c + sum_l A_l y_(t-l) + u_t` (05 H.2).
- Golden: data generated by `y_t = A y_(t-1)` exactly, with `A = [[0.5, 0], [0.2, 0.8]]`, recovers `A` to `1e-10` and `intercept = 0`.
- Invariants: `ValueError` for `T <= lags * n + 1`.

### `riskvalidation.stress.scenario_models.var_conditional_forecast`

```python
def var_conditional_forecast(fit: VarFit, y_history: np.ndarray, path: np.ndarray, conditioned: Sequence[int]) -> np.ndarray: ...
```

- Units: `y_history` (lags, n) the last observations, `path` (H, m) the given path of the `m` conditioned variables; returns (H, n). A stress scenario as a conditional forecast given a path for a subset of variables (05 l.388): the conditioned variables follow the path exactly.
- Golden (hand-computed, diagonal `sigma`): `A = [[0.5, 0], [0.2, 0.8]]`, `y_0 = (1, 1)`, the first variable conditioned on `(2.0, 3.0)`: the second variable is `(1.0, 1.2)` (`0.2 * 1 + 0.8 * 1`, then `0.2 * 2.0 + 0.8 * 1.0`); with no conditioning the forecast is `A^h y_0 = ((0.5, 1.0), (0.25, 0.9))`.
- Invariants: the conditioned columns equal `path` exactly; with a diagonal `sigma` the other variables follow their own equations with the conditioned path substituted; with correlated shocks the conditional mean uses the regression of the free shocks on the conditioned ones (Waggoner and Zha form, UNVERIFIED against the paper: the dossier names the method only).

### `riskvalidation.stress.scenario_models.skewed_t_pdf`

```python
def skewed_t_pdf(y: np.ndarray, mu: float, sigma: float, alpha: float, nu: float) -> np.ndarray: ...
```

- Units: `y` in the unit of the growth rate; `sigma > 0`, `nu > 0`. The Azzalini-Capitanio skewed t density `f(y) = (2 / sigma) t((y - mu) / sigma; nu) T(alpha (y - mu) / sigma sqrt((nu + 1) / (nu + ((y - mu) / sigma)^2)); nu + 1)` (05 l.390; Adrian, Boyarchenko and Giannone 2019).
- Golden (computed): `alpha = 0` reduces to the Student t: `skewed_t_pdf(0, 0, 1, 0, 5) = 0.379607` (`t_5` density at 0); the density integrates to `1` to `1e-6` for `(mu, sigma, alpha, nu) = (0, 1, 2, 5)`.
- Invariants: nonnegative; the mode shifts to the sign of `alpha`; `ValueError` for `sigma <= 0` or `nu <= 0`.

### `riskvalidation.stress.scenario_models.SkewedTFit`

```python
@dataclass(frozen=True)
class SkewedTFit:
    mu: float
    sigma: float
    alpha: float
    nu: float
    distance: float      # the squared distance to the four target quantiles
```

- Units: of the growth rate.
- Invariants: `distance >= 0`.

### `riskvalidation.stress.scenario_models.gar_quantile_regressions`

```python
def gar_quantile_regressions(y: np.ndarray, x: np.ndarray, taus: Sequence[float] = (0.05, 0.25, 0.75, 0.95)) -> np.ndarray: ...
```

- Units: `y` (T,) the average annualised growth, `x` (T, k) with a constant column; returns (len(taus), k) coefficients. Step 1 of growth-at-risk: quantile regressions of the growth on the constant, current growth and the Chicago Fed NFCI (05 l.390; the NFCI is in no dossier 08 row, so a bake that needs it must register it first).
- Golden: an exact line `y = 1 + 2 x` gives `(1.0, 2.0)` at every tau to `1e-6`.
- Invariants: the fitted quantiles are weakly increasing in tau at the sample mean of `x` for the golden-like data; `ValueError` for a tau outside `(0, 1)`.

### `riskvalidation.stress.scenario_models.fit_skewed_t_to_quantiles`

```python
def fit_skewed_t_to_quantiles(quantiles: np.ndarray, taus: Sequence[float] = (0.05, 0.25, 0.75, 0.95)) -> SkewedTFit: ...
```

- Units: `quantiles` (4,) in the unit of the growth rate. Step 2: fit the skewed t by minimising the squared distance to the estimated 5, 25, 75 and 95 percent quantiles (05 l.390).
- Golden: the quantiles of a standard Student t with `nu = 5` at the four taus are recovered with `alpha` within `1e-3` of 0 and `distance <= 1e-8`.
- Invariants: `distance` is the minimum found over the starts; `ValueError` for decreasing quantiles.

## Module `riskvalidation/validation/stress.py`

The tests of H.7 (05 l.422), each a `TestResult` with `reference`, `h0` and a policy version. The supervisory replication test of the sizing is void with decision E1.

### `riskvalidation.validation.stress.satellite_backcast`

```python
def satellite_backcast(predicted: np.ndarray, realised: np.ndarray, quarters: Sequence[str], fit_end: str, peak_amber: float = 0.35,
                       peak_red: float = 0.60, timing_quarters: int = 2, model_id: str | None = None, segment: str | None = None) -> TestResult: ...
```

- Units: rates as decimals, `quarters` ISO quarter ends, `fit_end` the last quarter of the fit window; `test_id = "stress.satellite_backcast"`. `h0`: satellites estimated before the episode back-cast it: the predicted loss-rate peak is within the thresholds of the realised peak, in size and timing (05 l.422).
- Invariants: `statistic` is the RMSE; `metric` is the peak timing error in quarters (predicted peak quarter less realised peak quarter); the size ratio `peak_predicted / peak_realised` is in `extras["peak_ratio"]` with `thresholds = {"peak_amber": peak_amber, "peak_red": peak_red, "timing_quarters": timing_quarters}`; the test returns `error` (light) with its reason when `fit_end` is not before the first quarter of the episode (leakage).
- Light: green when `|1 - peak_ratio| <= peak_amber` and `|timing| <= timing_quarters`; amber when `|1 - peak_ratio| <= peak_red`; red otherwise.
- Golden: predicted peak `1.0`, realised peak `1.2` (ratio `0.8333`, deviation `0.1667`) one quarter apart: green; predicted peak `0.4` against `1.2` (deviation `0.6667`): red (2.0.0: the 1.0.0 golden `0.5` gives `0.5833`, inside `peak_red` 0.60, which the light rule makes amber; U13 decision Z8).

### `riskvalidation.validation.stress.sensitivity_monotonicity`

```python
def sensitivity_monotonicity(estimates: Sequence[float], expected_signs: Sequence[str], model_id: str | None = None,
                             segment: str | None = None) -> TestResult: ...
```

- Units: coefficients and signs in `positive`, `negative`, `none`; `test_id = "stress.sensitivity_monotonicity"`. `h0`: every macro sensitivity has its expected sign, so the projected loss rate is monotone in the severity of the path (05 l.422).
- Invariants: `statistic` is the number of coefficients with the wrong sign (`none` is never wrong); `metric` null; `extras` lists the offending indices.
- Light: red when `statistic > 0`; green otherwise.
- Golden: `((0.82, -0.045, 0.06), ("positive", "negative", "positive"))`: `statistic = 0`, green; flipping the second estimate: `statistic = 1`, red.

### `riskvalidation.validation.stress.static_balance_sheet_rules`

```python
def static_balance_sheet_rules(balances: np.ndarray, tolerance: float = 1e-9, model_id: str | None = None,
                               segment: str | None = None) -> TestResult: ...
```

- Units: `balances` (H, 3) the stage balances after each period; `test_id = "stress.static_balance_sheet_rules"`. `h0`: the static balance sheet rules are applied: the total is constant, stage 3 never falls (no cure), no balance is negative (EBA paras 33 and 90).
- Invariants: `statistic` is the number of violated rules among the three; `extras` names them and `thresholds = {"tolerance": tolerance}`.
- Light: red when `statistic > 0`; green otherwise.
- Golden: the output of `eba_static_balance_sheet((80, 15, 5), (2, 3))`: green; the same rows with stage 3 `(7, 6)`: red.

### `riskvalidation.validation.stress.bottom_up_vs_top_down`

```python
def bottom_up_vs_top_down(bottom_up: float, top_down: float, amber: float = 0.25, red: float = 0.50, model_id: str | None = None,
                          segment: str | None = None) -> TestResult: ...
```

- Units: money (the stressed loss of the bottom-up result and of a top-down challenger); `test_id = "stress.bottom_up_vs_top_down"`. `h0`: the bottom-up result agrees with a top-down challenger within the thresholds (05 l.422).
- Invariants: `statistic = bottom_up / top_down - 1`; `metric` equals `statistic`; `top_down <= 0` gives `not_evaluated`; `thresholds = {"amber": amber, "red": red}`.
- Light: green when `|statistic| <= amber`; amber when `<= red`; red above.
- Golden: `bottom_up = 120`, `top_down = 100`: `statistic = 0.2`, green; `140`: amber (`0.4`); `200`: red (2.0.0: the 1.0.0 golden `160` gives `0.6`, above the red gate 0.50; U13 decision Z8).

### `riskvalidation.validation.stress.scenario_severity`

```python
def scenario_severity(path_peak: float, history_peak: float, is_stress: bool = True, minimum: float = 0.75,
                      model_id: str | None = None, segment: str | None = None) -> TestResult: ...
```

- Units: the peak deviation from the jump-off of a scenario variable (unemployment in percentage points, GDP in percentage points) and the same deviation in the global financial crisis; `test_id = "stress.scenario_severity"`. `h0`: a stress path is at least as severe as history (the EBA documents severity against the GFC: 05 l.422). It maps onto the document block `outputs.severity` (one row per path variable: `path_peak_deviation`, `history_peak_deviation`, `ratio`, `is_stress`; the reference episode 2008 to 2009 with its quarters and source).
- Invariants: `statistic = path_peak / history_peak`; `is_stress = False` (the baseline) gives `not_evaluated` with the reason "not a stress path"; `history_peak <= 0` gives `not_evaluated`; `thresholds = {"minimum": minimum}`.
- Light: green when `statistic >= minimum`; amber below (no red: a mild stress is a finding about the scenario, not a failure).
- Golden: unemployment peak `+5.5` points against a GFC peak `+5.5`: `statistic = 1.0`, green; `+3.0` against `+5.5`: `0.5455`, amber.

### `riskvalidation.validation.stress.reverse_solution_check`

```python
def reverse_solution_check(loss_at_x: float, threshold: float, distance: float, start_distances: Sequence[float], tolerance: float = 1e-6,
                           model_id: str | None = None, segment: str | None = None) -> TestResult: ...
```

- Units: money and the Mahalanobis distance; `test_id = "stress.reverse_solution_check"`. `h0`: the loss at `z*` equals the threshold and no start finds a closer point (05 l.422; the reverse stress check of H.7).
- Invariants: `statistic = |loss_at_x - threshold| / threshold`; `metric = min(start_distances) / distance - 1` (zero or positive when no start is closer); `thresholds = {"tolerance": tolerance}`; fewer than three starts gives `not_evaluated`.
- Light: red when `statistic > tolerance` or any start distance `< distance (1 - 1e-6)`; green otherwise.
- Golden: `loss = 5.0`, `threshold = 5.0`, `distance = 2.2361`, starts `(2.2361, 2.2361, 2.2362)`: green; a start at `1.5`: red.

## Golden values: the published figures and the derived identities

- Published figures (dossier 03 l.1324-1328, Banco Santander-Chile Form 20-F 2025, Ch$ million, derived-only: ratios only enter the documents): RWA `41,715,467` (credit `29,551,588`, market `7,143,966`, operational `5,019,913`), CET1 `4,601,923` (`0.110317` of RWA), effective equity `7,047,321`, Pillar 2 `52,144` (`0.125` percent), countercyclical `0.50`, systemic `1.50`, conservation `2.50` percent; the 4 percent cap of RWA on the additional requirement (03 l.253), `1,668,618.68` on these figures. The Santander Chile full phase-in Pillar 2 percentage is UNVERIFIED (03 l.278).
- Derived identities (SDD Oracles, item 4): the probit round trip DR to Z to DR through the reused `implied_factor` (04 l.791-793; at `pd = 0.02`, `rho = 0.12`, `z = 0` the conditional PD is `0.014287`, the golden of `implied_z`; at `z = -2` it is `0.073424`); the OLS fit against `numpy.linalg.lstsq`; the closed-form Mahalanobis scenario for a linear loss; a hand-computed three-quarter capital path (`[10.0, 8.0, 6.5]`); the skewed t density integrates to one.
- Independent references (SDD Oracles, item 5): the engine path rule against C06's committed output (R14, BL-079).

## Document mapping

| C18 block | Functions |
|---|---|
| `outputs.scenario.paths` | `paths.check_vintage`, `paths.level_from_deviation`, `paths.annual_to_quarterly`, `paths.transpose_path`, `paths.revert_to_baseline` |
| `outputs.satellites`, `fit.satellites` | `satellites.fit_satellite`, `satellites.project_scenario`, `satellites.link`, reused `engines.vasicek.conditional_pd` |
| `outputs.headline_cet1`, `capital_plan`, `internal_capital_target`, `p2g_proxy`, `annex3` | `capital.cet1_path_loss_only`, `ppnr_row`, `capital_plan`, `internal_capital_target`, `chilean_cet1_stack`, `p2g_proxy`, `annex3_summary`, `eba_static_balance_sheet` |
| `outputs.backcast` | `validation.stress.satellite_backcast` |
| the reverse variant | `reverse.reverse_stress_linear`, `reverse.reverse_stress`, `reverse.plausibility`, `validation.stress.reverse_solution_check` |
| `tests` | the six functions of `riskvalidation/validation/stress.py` |
