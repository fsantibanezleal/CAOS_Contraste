# Engine provisions API contract: `engine-provisions-api` 1.0.0

Owner: U5-S (unit sizing `plans/contraste/units/U5-sizing.md`, CAOS_MANAGE). Implemented by U5-E1 (term structure, staging,
ECL, overlays, reconciliation, the IFRS 9 battery) and U5-E2 (CMF B-1, BdE Annex 9) in `riskvalidation.provisions` and
`riskvalidation.validation.ifrs9` (repository CAOS_RiskValidation); called by the C06 and C07 bakes (U5-P1, U5-P2). The tests
of every function are written by U5-E1 and U5-E2 against this file: a function exists with exactly the signature below, and
each golden value or invariant is a test. Changing a signature, a unit or a golden value is a breaking change (a new major
version of this contract). Sources: dossier 02 (`wip/contraste/02-ifrs9-ecl-and-provisioning-2026-10-04.md`, sections B, C.1,
I.1, I.2) and dossier 03 (sections D.3 to D.6 for CMF CNCB B-1, K.2 and K.3 for BdE Circular 4/2017 Annex 9); the product SDD
section 4 gives the acceptance rows this contract serves ("IFRS 9 ECL engine", "CMF B-1", "BdE Annex 9", "Lifetime PD rungs").

The engine computes; it states no compliance claim. Nothing here is an IFRS 9, CMF or BdE requirement beyond what the dossier
sections cite; multipliers, floors, probation lengths and horizons are policy parameters the caller supplies.

## Conventions (all functions)

- Arrays are `numpy.ndarray` of `float64` (integers `int64`, flags `bool`). Shapes: `A` accounts, `S` scenarios, `T` periods,
  `K` cash-flow dates. A leading batch dimension is allowed wherever a shape is written `(..., T)`.
- Rates are decimals in [0, 1]. A PD at an estimate site (a hazard, a marginal or cumulative PD, an annualised PD, a PIT PD) is
  open: `0 < pd < 1`; a function raises `ValueError` outside it. LGD, CCF, coverage rates and weights are closed [0, 1]. Statutory
  table parameters (the B-1 and Annex 9 tables) are closed [0, 1] and are transcribed as decimals (1.0916 per cent is 0.010916).
- Money is a float in the portfolio currency; the currency code travels in the document (`currency`), never in a function. Money is
  never converted between currencies by the engine.
- Horizons and period ends are integer months; `months` is strictly increasing and gives the end month of each period; a
  period of `Delta` months ends at `t * Delta`. Dates are ISO strings and appear only at the document boundary.
- Probability weights are in [0, 1], sum to 1 within `1e-9`, and at least two scenarios are required when scenarios are used
  (IFRS 9 B5.5.42); otherwise `ValueError`.
- Every function is pure and deterministic (no hidden state, no randomness, no I/O, inputs never mutated) and returns new arrays.
- Dataclasses are frozen. A function that cannot compute a value because data is missing raises or returns the `not_evaluated`
  light with its reason in `notes`; it never returns a placeholder number.
- Tolerance basis (one definition for every function and test): a money identity closes when its absolute difference is at most
  `1e-6 * max(1, G)`, where `G` is the total gross carrying amount of the document, the sum of the absolute closing amounts of the
  `reconciliation.gross_carrying_amount` rows (in the document currency). The same `G` serves the allowance, the gross carrying
  amount, the waterfall and the stage-closing identities; a `RollForwardRow.residual` is always the difference `closing - (opening + sum(movements))` itself, never a clipped or tolerance-adjusted value (a document may store it rounded to 1e-9).
  Probability identities close to `1e-12`, and a tighter tolerance is written where a function needs one. Every golden value states
  its own tolerance (`to 1e-8`) or is exact.
- A validation function returns one `TestResult` of `riskvalidation`, serialised by `TestResult.to_dict()` into a row that validates
  against `common/test-result` (the schema `docs/contracts/schemas/common/test-result.schema.json`): `test_id`, `model_id`,
  `segment`, `statistic`, `p_value`, `metric`, `h0`, `alternative`, `policy_version`, `alpha_amber`, `alpha_red`, `light`, `n`,
  `n_events`, `inputs_hash`, `reference`, `notes`, `extras`.

## How the documents use the engine

| Document block (schema) | Produced by |
|---|---|
| C06 `outputs.term_structures`, `account_curves`, `lifetime_backtest` | `term_structure.*`, `ifrs9.lifetime_pd_backtest` |
| C06 `outputs.sicr_points`, `stage_flows`, `stage_summary` | `staging.*` |
| C06 `outputs.ecl_by_scenario`, `weight_grid`, `non_linearity` | `ecl.*`, `term_structure.weighted_pit_pd` |
| C06 `outputs.waterfall`, `overlays`, `reconciliation` | `overlays.*`, `reconciliation.*` |
| C06 and C07 `tests` | `riskvalidation.validation.ifrs9.*` (rows of `common/test-result`) |
| C07 `outputs.regimes[cmf-b1]`, `b1_detail` | `local_cl.*` |
| C07 `outputs.regimes[ifrs9]`, `ifrs9_detail` | `staging.*`, `ecl.*` (`probability_weighted_ecl` over at least two weighting scenarios, the variant a shift of current conditions), `overlays.*` |
| C07 `outputs.regimes[bde-annex9]`, `bde_detail` | `local_es.*` |

The C07 `ifrs9` regime of every scenario variant is a probability-weighted ECL (IFRS 9 5.5.17(a), B5.5.42): the bake runs
`ecl_scenario` once per weighting scenario of `models.fit.ifrs9.weighting_scenarios` (factor `z_s + z_shift_v`, where `z_shift_v` is the
variant's shift of current conditions), staging frozen at the weighted conditions, and combines them with `probability_weighted_ecl`.
A 100 per cent single-scenario ECL is a component (`weighted_components[].single_scenario_ecl`) or a sensitivity, never the IFRS 9
measure and never a column of the three-regime comparison.

## Module `riskvalidation/provisions/term_structure.py`

Marginal and cumulative PD and hazards from a supplied PD curve per scenario; TTC to PIT by the one-factor model (dossier 02
B.2 and C.1). Identities (Botha and Verster 2025, eqs. 7 to 10): `S(t) = prod_{u<=t} (1 - h(u))`, `q(t) = S(t-1) h(t)`,
`F(t) = sum_{u<=t} q(u) = 1 - S(t)`, `h(t) = q(t) / S(t-1)`.

### `riskvalidation.provisions.term_structure.TermStructure`

```python
@dataclass(frozen=True)
class TermStructure:
    months: np.ndarray      # (T,) int64, strictly increasing end months of the periods
    hazard: np.ndarray      # (..., T) h(t), conditional PD per period, open (0, 1)
    survival: np.ndarray    # (..., T) S(t)
    marginal: np.ndarray    # (..., T) q(t), unconditional PD of period t, open (0, 1)
    cumulative: np.ndarray  # (..., T) F(t)
```

- Units: PD decimals per period (not annualised); `months` integers.
- Invariants: `q(t) = S(t-1) h(t)` and `F(t) = 1 - S(t)` to 1e-12 for every instance without exception (a result of
  `competing_risks` is a `CompetingRisks` record, never a `TermStructure`); `F` strictly increasing; `F(t)` in (0, 1); all arrays share the
  leading shape; the C06 `term_structures` document block is this structure (hazard, marginal_pd, cumulative_pd, months).

### `riskvalidation.provisions.term_structure.from_hazard`

```python
def from_hazard(hazard: np.ndarray, months: np.ndarray) -> TermStructure: ...
```

- Units: `hazard` (..., T) decimals per period; `months` (T,) integer months.
- Invariants: `S = cumprod(1 - hazard)`; round trip `from_marginal(from_hazard(h).marginal)` equals `from_hazard(h)` to 1e-12.
- Golden: constant `h = 0.01`, `months = [3, 6]`: `S = [0.99, 0.9801]`, `q = [0.01, 0.0099]`, `F = [0.01, 0.0199]`.

### `riskvalidation.provisions.term_structure.from_marginal`

```python
def from_marginal(marginal: np.ndarray, months: np.ndarray) -> TermStructure: ...
```

- Units: `marginal` (..., T) unconditional PD per period.
- Invariants: raises `ValueError` when `sum(marginal) >= 1` or any `q <= 0`; `h(t) = q(t) / S(t-1)`.
- Golden: `q = [0.01, 0.0099]` gives `h = [0.01, 0.01]` to 1e-12.

### `riskvalidation.provisions.term_structure.from_cumulative`

```python
def from_cumulative(cumulative: np.ndarray, months: np.ndarray) -> TermStructure: ...
```

- Units: `cumulative` (..., T) cumulative PD from the reporting date.
- Invariants: raises `ValueError` unless `cumulative` is strictly increasing inside (0, 1) (a monotone cumulative PD is the SDD
  acceptance row "Lifetime PD rungs"); `q(t) = F(t) - F(t-1)` with `F(0) = 0`.
- Golden: `F = [0.01, 0.0199]` gives `h = [0.01, 0.01]`.

### `riskvalidation.provisions.term_structure.forward_pd`

```python
def forward_pd(ts: TermStructure | CompetingRisks, start_month: int, end_month: int) -> np.ndarray: ...
```

- Units: months are 0 or members of `ts.months`; returns decimals, shape `ts.survival.shape[:-1]` (for `CompetingRisks`, `survival_all.shape[:-1]`).
- Invariants: for a `TermStructure`, `PD(a, b) = (S(a) - S(b)) / S(a)` with `S(0) = 1` (dossier 02 B.2), so `forward_pd(ts, 0, b) = F(b)`; for a
  `CompetingRisks` record the conditional default PD over `(a, b]` is `(F_D(b) - F_D(a)) / S_all(a)` with `F_D(0) = 0` and `S_all(0) = 1`
  (default only, given survival of both exits to `a`), so `forward_pd(cr, 0, b) = F_D(b)`; raises when `end_month <= start_month`; result
  in (0, 1).
- Golden: constant `h = 0.01` per 3-month period: `forward_pd(ts, 3, 9) = 1 - 0.99**2 = 0.0199` to 1e-12. Competing risks (`h_D = 0.01`,
  `h_P = 0.02`): `forward_pd(cr, 0, 6) = 0.0197` to 1e-12, never the default-or-prepayment probability `1 - S_all(6) = 0.0591`.

### `riskvalidation.provisions.term_structure.annualise_pd`

```python
def annualise_pd(pd: np.ndarray, horizon_years: float) -> np.ndarray: ...
```

- Units: `pd` a PD over `horizon_years`; returns the annual PD `1 - (1 - pd)**(1 / horizon_years)` (Contraste's documented
  convention for the SICR comparison, dossier 02 B.5; not asserted as the EBA's).
- Invariants: identity at `horizon_years = 1`; monotone increasing in `pd`; raises when `horizon_years <= 0`.
- Golden: `annualise_pd(0.19, 2.0) = 0.1` to 1e-12.

### `riskvalidation.provisions.term_structure.competing_risks`

```python
@dataclass(frozen=True)
class CompetingRisks:
    months: np.ndarray            # (T,) int64, strictly increasing end months of the periods
    hazard_default: np.ndarray    # (..., T) h_D(t), open (0, 1)
    hazard_prepay: np.ndarray     # (..., T) h_P(t), open (0, 1)
    survival_all: np.ndarray      # (..., T) S_all(t) = prod (1 - h_D - h_P), survival of both exits
    marginal_default: np.ndarray  # (..., T) q_D(t) = S_all(t-1) h_D(t), default incidence
    cumulative_default: np.ndarray  # (..., T) F_D(t) = cumsum(q_D), cumulative default incidence (not 1 - S_all)

def competing_risks(hazard_default: np.ndarray, hazard_prepay: np.ndarray, months: np.ndarray) -> CompetingRisks: ...
```

- Units: both hazards (..., T) decimals per period; `hazard_default + hazard_prepay < 1`. `CompetingRisks` is not a `TermStructure` and is
  exempt from `F = 1 - S` on purpose: `F_D` is the cumulative incidence of default, `1 - S_all` is the probability of default or
  prepayment. A caller that needs a `TermStructure` of default alone calls `from_hazard(hazard_default)`.
- Invariants: `F_D(t) < 1 - S_all(t)` whenever `h_P > 0`; with `hazard_prepay = 0` the arrays equal `from_hazard(hazard_default)` (`survival_all =
  survival`, `F_D = cumulative`); prepayment never raises `F_D`; `forward_pd` on this record is `(F_D(b) - F_D(a)) / S_all(a)`.
- Golden: `h_D = 0.01`, `h_P = 0.02` constant, two periods: `S_all = [0.97, 0.9409]`, `q_D = [0.01, 0.0097]`, `F_D = [0.01, 0.0197]` (against
  `1 - S_all = [0.03, 0.0591]`) to 1e-12.

### `riskvalidation.provisions.term_structure.ttc_to_pit`

```python
def ttc_to_pit(pd_ttc: np.ndarray, rho: float, z: np.ndarray) -> np.ndarray: ...
```

- Units: `pd_ttc` open (0, 1); `rho` open (0, 1) asset correlation; `z` the systematic factor in standard-normal units.
  Returns the conditional PD `Phi((Phi^-1(pd_ttc) - sqrt(rho) z) / sqrt(1 - rho))` (dossier 02 C.1).
- Invariants: strictly decreasing in `z`; `E_Z[ttc_to_pit(pd, rho, Z)] = pd`; `ttc_to_pit(pd, rho, 0) < pd` for `pd < 0.5`.
- Golden (dossier 02 B.4, `pd_ttc = 0.02`, `rho = 0.12`): `z = +1` gives 0.526% (0.005255059), `z = 0` gives 1.429% (0.014287387),
  `z = -2` gives 7.342% (0.073424082), each to 1e-8.

### `riskvalidation.provisions.term_structure.implied_z`

```python
def implied_z(default_rate: np.ndarray, pd_ttc: float, rho: float) -> np.ndarray: ...
```

- Units: `default_rate` open (0, 1) observed segment default rates; returns `Z = (Phi^-1(pd_ttc) - sqrt(1 - rho) Phi^-1(DR)) / sqrt(rho)`.
- Invariants: inverse of `ttc_to_pit`: `implied_z(ttc_to_pit(p, r, z), p, r) = z` to 1e-9.
- Golden: `implied_z(0.014287387, 0.02, 0.12) = 0` to 1e-6.

### `riskvalidation.provisions.term_structure.weighted_pit_pd`

```python
def weighted_pit_pd(pd_ttc: float, rho: float, z: np.ndarray, weights: np.ndarray) -> float: ...
```

- Units: `z` (S,) scenario factors; `weights` (S,) probabilities; returns `sum_s w_s ttc_to_pit(pd_ttc, rho, z_s)`.
- Invariants: weights validated per the conventions; by Jensen, `weighted_pit_pd(...) >= ttc_to_pit(pd_ttc, rho, sum(w z))` in the
  convex regime (a property test).
- Golden (dossier 02 B.4): `z = (1, 0, -2)`, `w = (0.25, 0.5, 0.25)`: weighted PD 2.681% (0.026813479) against the PD at the weighted
  mean factor `z = -0.25` of 1.800% (0.017997448), ratio 1.49 (1.48985), each to 1e-8; with LGD 40% the weighted 12-month loss rate is 1.07%
  against 0.72%.

### `riskvalidation.provisions.term_structure.gauss_hermite_pit_pd`

```python
def gauss_hermite_pit_pd(pd_ttc: float, rho: float, n_nodes: int = 64) -> float: ...
```

- Units: integrates `ttc_to_pit` over `Z ~ N(0, 1)` with probabilists' Gauss-Hermite nodes (the non-linearity cross check, dossier
  02 I.1 item 6).
- Invariants: equals `pd_ttc` to 1e-9 for `n_nodes >= 32`; raises when `n_nodes < 2`.
- Golden: `gauss_hermite_pit_pd(0.02, 0.12, 64) = 0.02` to 1e-9.

## Module `riskvalidation/provisions/staging.py`

Stage allocation: relative and absolute PD tests against the origination forward PD, the 30 dpd backstop, the threefold backstop,
forbearance and watch-list triggers, cure probation (dossier 02 B.5). Only the 30 dpd and 90 dpd presumptions are in IFRS 9; the
threefold ratio is an EBA supervisory expectation (EBA/Rep/2023/36 para 32) and the rest are policy.

### `riskvalidation.provisions.staging.StagingPolicy`

```python
@dataclass(frozen=True)
class StagingPolicy:
    multiplier_schedule: tuple[tuple[float, float], ...]  # (pd_origination_upper, multiplier), upper bounds increasing
    absolute_floor: float            # delta, absolute annualised PD increase floor, in [0, 1]
    threefold_ratio: float = 3.0     # backstop ratio, > 1
    dpd_backstop: int = 30           # days past due, rebuttable presumption, trigger when dpd > dpd_backstop
    default_dpd: int = 90            # days past due, Stage 3 when dpd >= default_dpd
    probation_months: int = 0        # cure probation, >= 0
    low_credit_risk_pd: float | None = None  # optional exemption: annualised PD at or below stays Stage 1 on the quantitative tests only
```

- Units: PDs annualised decimals; days and months integers; the C06 `outputs.settings.sicr` (with `settings.probation_months`) is this record
  and is the one source: the C06 and C07 models `staging_policy` repeat it field by field (`low_credit_risk_exemption` is `low_credit_risk_pd
  is not None`).
- Low credit risk exemption: `low_credit_risk_pd` suppresses only `relative-absolute` and `threefold` (the rebuttable assumption of 5.5.10);
  the 30 dpd backstop, forbearance, watch-list, collective and default triggers still apply (5.5.11, B5.5.37).
- Invariants: `pd_origination_upper` strictly increasing with the last bound at least the largest PD; multipliers `>= 1` and
  non-increasing as the origination PD rises (the schedule is non-increasing in risk); raises `ValueError` otherwise.

### `riskvalidation.provisions.staging.sicr_quantitative`

```python
def sicr_quantitative(pd_origination_annualised: np.ndarray, pd_current_annualised: np.ndarray,
                      policy: StagingPolicy) -> np.ndarray: ...
```

- Units: both (A,) annualised PDs, open (0, 1); returns `bool` (A,). `True` when `(rep/orig >= m(orig) and rep - orig >= floor)` or
  `rep/orig >= threefold_ratio` (dossier 02 B.5), with `m(orig)` read from the schedule.
- Invariants: monotone in `pd_current_annualised` (a higher current PD never turns a flag off); with `rep == orig` the result is
  `False`; elementwise (row `i` depends on row `i` only); it never applies the low credit risk exemption (that is `allocate_stages`).
- Golden: schedule `((0.01, 4.0), (0.05, 2.5), (0.5, 1.5))`, floor 0.005, threefold 3.0: `orig = 0.02`: `rep = 0.05` gives `True`
  (ratio 2.5, difference 0.03), `rep = 0.049` gives `False`; `orig = 0.001`, `rep = 0.003` gives `True` by the threefold backstop.

### `riskvalidation.provisions.staging.allocate_stages`

```python
@dataclass(frozen=True)
class StageResult:
    stage: np.ndarray    # (A,) int8 in {1, 2, 3}
    trigger: np.ndarray  # (A,) str: none | relative-absolute | threefold | dpd-backstop | forbearance | watch-list | default | collective
    lcr_exempt: np.ndarray  # (A,) bool: Stage 1 only because the low credit risk exemption suppressed a quantitative trigger

def allocate_stages(pd_origination_annualised: np.ndarray, pd_current_annualised: np.ndarray, dpd: np.ndarray,
                    forborne: np.ndarray, watch_list: np.ndarray, defaulted: np.ndarray,
                    policy: StagingPolicy, collective: np.ndarray | None = None) -> StageResult: ...
```

- Units: `dpd` (A,) int64 days; `forborne`, `watch_list`, `defaulted`, `collective` (A,) bool; PDs as above. The `trigger` strings are
  the enum of the C06 `sicr_points.trigger` (plus `cure-probation`, set by `apply_cure_probation`).
- Invariants: Stage 3 iff `defaulted` or `dpd >= policy.default_dpd`; else Stage 2 iff any trigger fires; else Stage 1; the low credit risk
  exemption (`current PD <= policy.low_credit_risk_pd`) suppresses only `relative-absolute` and `threefold`, never `dpd-backstop`,
  `forbearance`, `watch-list`, `collective` or `default` (5.5.11 still applies); `lcr_exempt[i]` is `True` iff the account is Stage 1 and
  `sicr_quantitative` would have flagged it without the exemption (SICR effectiveness reports its count, dossier 02 I.2); `trigger` is
  `none` iff stage 1; precedence `default`, `dpd-backstop`, `forbearance`, `watch-list`, `collective`, `relative-absolute`,
  `threefold`; row `i` depends on row `i` only (the isolation property test of dossier 02 I.2: a change of an unrelated account
  changes no stage).
- Golden: `dpd = 31` with unremarkable PDs gives stage 2 `dpd-backstop`; `dpd = 30` gives stage 1; `dpd = 90` gives stage 3 `default`; with
  `low_credit_risk_pd = 0.03`, `orig = 0.001`, `rep = 0.003`, `dpd = 0` gives stage 1, `trigger = none`, `lcr_exempt = True`, and the same
  account at `dpd = 31` gives stage 2 `dpd-backstop`, `lcr_exempt = False`.

### `riskvalidation.provisions.staging.apply_cure_probation`

```python
def apply_cure_probation(stage_now: np.ndarray, stage_previous: np.ndarray, months_since_cure: np.ndarray,
                         policy: StagingPolicy, now: StageResult) -> StageResult: ...
```

- Units: `months_since_cure` (A,) int64 months since the last stage 2 trigger cleared; `now` (required) the `StageResult` of
  `allocate_stages` for `stage_now`.
- Invariants: an account that is stage 1 now, stage 2 before, with `months_since_cure < policy.probation_months` stays stage 2 with
  trigger `cure-probation`; every other account is unchanged and keeps the trigger and exemption flag of `now`, so every stage 2 or 3
  account carries a trigger of the C06 `sicr_points.trigger` enumeration; with `probation_months = 0` the output equals `now`.
- Amended 2026-10-12 (engine review decision C2, riskvalidation v0.05.000): `now` became a required argument; before it, an unchanged
  stage 2 or 3 account could come back without a trigger.
- Golden: probation 6 months: `months_since_cure = 3` gives stage 2 `cure-probation`; `months_since_cure = 6` gives stage 1.

### `riskvalidation.provisions.staging.collective_transfer`

```python
def collective_transfer(gross_carrying_amount: np.ndarray, segment: np.ndarray,
                        share_by_segment: dict[str, float]) -> dict[str, float]: ...
```

- Units: `gross_carrying_amount` (A,) money; `segment` (A,) str; shares `pi_g` in [0, 1] (the top-down Stage 2 share of segment `g`,
  dossier 02 B.5). Returns the target money to be in stage 2 per segment. It reports only: the amount is never added to any allowance.
- One path into the stages and the ECL: the caller (the bake) turns each target into accounts, taking the accounts of segment `g` in
  descending current PD (ties by account id) until the cumulative gross carrying amount first reaches the target, and passes them as the
  `collective` mask of `allocate_stages` (trigger `collective`, Stage 2, lifetime ECL through `portfolio_allowance`). The ECL of the
  collective transfer therefore reaches the allowance only through the stage of those accounts; applying the transferred money again would
  double count. The realised collective gross carrying amount exceeds the target by less than one account.
- Invariants: `amount_g = pi_g * sum(gca in g)`; the sum of the transfers never exceeds the total; `pi_g = 0` gives 0; a segment
  absent from `share_by_segment` raises `KeyError`.
- Golden: segment totals `{s1: 100000}`, `pi = 0.1` gives `{s1: 10000.0}`.

## Module `riskvalidation/provisions/ecl.py`

ECL as a sum of discounted marginal losses per scenario, probability weighting, EIR conventions, Stage 3 by discounted recoveries,
POCI, the simplified approach matrix (dossier 02 B.3, B.4, B.7, A.5, A.6): `ECL_{i,s}(T) = sum_t q_D(t) LGD(t) EAD(t) DF(t)`.

### `riskvalidation.provisions.ecl.discount_factors`

```python
def discount_factors(eir: np.ndarray, months: np.ndarray, convention: str = "mid-period") -> np.ndarray: ...
```

- Units: `eir` (A,) annual effective interest rate (the original EIR, B5.5.44; never a risk-free rate), decimals `>= 0`; `months`
  (T,) period end months; `convention` in `mid-period` (`delta = month - Delta/2`) or `end-of-period`. Returns (A, T) with
  `DF = (1 + eir) ** (-delta / 12)`; the first period's `Delta` is `months[0]`.
- Invariants: `DF` in (0, 1] and strictly decreasing in `t` for `eir > 0`; `eir = 0` gives 1; discounting is to the reporting date.
- Golden: `eir = 0.06`, `months = [3, 6]`, mid-period: `DF(1) = 1.06 ** -0.125 = 0.992742848`, `DF(2) = 1.06 ** -0.375 = 0.978386160`.

### `riskvalidation.provisions.ecl.ecl_scenario`

```python
def ecl_scenario(marginal_pd: np.ndarray, lgd: np.ndarray, ead: np.ndarray, eir: np.ndarray, months: np.ndarray,
                 horizon_months: int, convention: str = "mid-period") -> np.ndarray: ...
```

- Units: `marginal_pd` (A, T) `q_D(t)`; `lgd` in [0, 1] and `ead` money, each scalar, (A,) or (A, T); `horizon_months` 12 for the
  12-month ECL, the expected life (capped per 5.5.19, 5.5.20) for the lifetime ECL; returns money (A,) for one scenario.
- Invariants: `horizon_months` must be a member of `months` or at least `months[-1]` (else `ValueError`: no proration of a straddling
  period); sums the periods with `months <= horizon_months`; `>= 0`; nondecreasing in `horizon_months`; linear in `ead` and in `lgd`; a
  horizon beyond `months[-1]` equals the lifetime ECL.
- Golden: `q = [0.01, 0.01]`, `months = [6, 12]`, `lgd = 0.4`, `ead = 100000`, `eir = 0`: `horizon_months = 12` gives 800.0,
  `horizon_months = 6` gives 400.0.

### `riskvalidation.provisions.ecl.probability_weighted_ecl`

```python
def probability_weighted_ecl(ecl_by_scenario: np.ndarray, weights: np.ndarray) -> np.ndarray: ...
```

- Units: `ecl_by_scenario` (S, A) or (S,) money; `weights` (S,) probabilities with `S >= 2`; returns `sum_s w_s ECL_s`.
- Invariants: weights validated per the conventions; with a convex ECL in the macro path the result `>=` the ECL at the weighted
  mean path (property test, SDD acceptance row "IFRS 9 ECL engine"); permuting scenarios with their weights leaves it unchanged.
- Golden (dossier 02 B.4): per unit of EAD with `LGD = 0.4`, `ecl_s = 0.4 * (0.005255059, 0.014287387, 0.073424082)` and
  `w = (0.25, 0.5, 0.25)` gives 0.010725392 (1.07%); at the mean path 0.007198979 (0.72%), each to 1e-8.

### `riskvalidation.provisions.ecl.stage3_ecl`

```python
def stage3_ecl(gross_carrying_amount: np.ndarray, expected_recoveries: np.ndarray, recovery_months: np.ndarray,
               eir: np.ndarray) -> np.ndarray: ...
```

- Units: `gross_carrying_amount` (A,) money; `expected_recoveries` (A, K) money; `recovery_months` (A, K) months from the reporting
  date; `eir` (A,). Returns `GCA - sum_k CF_k (1 + eir) ** (-months_k / 12)` (B5.5.33), clipped at 0.
- Invariants: `>= 0`; nonincreasing in each recovery; zero recoveries give the gross carrying amount; discounting at the EIR.
- Golden: `GCA = 50000`, one recovery of 30000 at month 12, `eir = 0.08`: `50000 - 30000 / 1.08 = 22222.2222` (22222.22 to 5e-3), tested to 1e-6.

### `riskvalidation.provisions.ecl.poci_allowance`

```python
def poci_allowance(ecl_lifetime_now: np.ndarray, ecl_lifetime_initial: np.ndarray) -> np.ndarray: ...
```

- Units: money (A,), both lifetime ECLs at the credit-adjusted EIR (5.5.13).
- Invariants: result `now - initial`; may be negative (5.5.14); no clipping.
- Golden: `now = 120`, `initial = 100` gives 20; `now = 80` gives -20.

### `riskvalidation.provisions.ecl.simplified_matrix_ecl`

```python
def simplified_matrix_ecl(gross_carrying_amount_by_bucket: np.ndarray, loss_rate_by_bucket: np.ndarray,
                          forward_looking_multiplier: float = 1.0) -> float: ...
```

- Units: money (B,) and loss rates in [0, 1] (B,) per past-due bucket; the multiplier `>= 0`. Provision matrix of the simplified approach
  (B5.5.35).
- Invariants: result `= min(sum(gca), m * sum(gca * rate))`, in `[0, sum(gca)]`; linear in the exposure below the cap.
- Golden: buckets `[1000, 500, 200]`, rates `[0.01, 0.05, 0.20]`: `10 + 25 + 40 = 75.0`.

### `riskvalidation.provisions.ecl.commitment_ead`

```python
def commitment_ead(drawn: np.ndarray, undrawn: np.ndarray, ccf: np.ndarray) -> np.ndarray: ...
```

- Units: `drawn`, `undrawn` money (A,) or (A, T); `ccf` in [0, 1]; returns `drawn + ccf * undrawn` (B5.5.30, B5.5.31).
- Invariants: between `drawn` and `drawn + undrawn`; `ccf = 0` gives `drawn`.
- Golden: `drawn = 60`, `undrawn = 40`, `ccf = 0.5` gives 80.

### `riskvalidation.provisions.ecl.non_linearity_index`

```python
def non_linearity_index(ecl_weighted: float, ecl_at_mean_path: float) -> float: ...
```

- Units: money inputs (or PDs for the PD-level index); returns `NL = ecl_weighted / ecl_at_mean_path - 1`; raises when the
  denominator is not positive. This is the C06 `non_linearity.index`.
- Invariants: `NL >= 0` in the convex regime; `NL = 0` when the weighted and mean-path values coincide.
- Golden (PD level, dossier 02 B.4): `non_linearity_index(0.026813479, 0.017997448) = 0.4898489` (0.48985 rounded), ratio 1.49, to 1e-6.

### `riskvalidation.provisions.ecl.weight_sensitivity`

```python
def weight_sensitivity(ecl_by_scenario: np.ndarray, reference_index: int) -> np.ndarray: ...
```

- Units: `ecl_by_scenario` (S,) money; returns `ECL_s - ECL_ref`, the derivative `dECL/dw_s` when moving weight from the reference
  scenario to `s` (dossier 02 B.4; the ECL is linear in the weights with staging frozen).
- Invariants: entry `reference_index` is 0; antisymmetric under swapping the reference; the weighted ECL changes by `dw * entry`.
- Golden: `[10, 20, 60]` with `reference_index = 1` gives `[-10, 0, 40]`.

### `riskvalidation.provisions.ecl.portfolio_allowance`

```python
@dataclass(frozen=True)
class AllowanceBreakdown:
    by_stage: dict[str, float]   # always the four keys stage1, stage2, stage3, poci: model ECL only, money; poci is 0.0 with no POCI row
    model_total: float
    overlay_total: float
    total: float

def portfolio_allowance(stage: np.ndarray, ecl_12m: np.ndarray, ecl_lifetime: np.ndarray, ecl_stage3: np.ndarray,
                        poci: np.ndarray | None = None, poci_delta: np.ndarray | None = None,
                        overlays: Sequence["Overlay"] = ()) -> AllowanceBreakdown: ...
```

- Units: `stage` (A,) int in {1, 2, 3} for non-POCI accounts; `poci` (A,) bool, the explicit POCI mask (`None` means no POCI account);
  `poci_delta` (A,) money, read only where `poci` is true (any value, including NaN, elsewhere); the ECL arrays (A,) money; returns
  `LA = sum_{S1} ECL_12m + sum_{S2} ECL_life + sum_{S3} ECL_D + sum_{POCI} delta + sum_k OVL_k` (dossier 02 B.5).
- POCI rows are excluded from stages 1 to 3 whatever their `stage` value (a POCI account counts once, in `poci`); `poci` true with a
  non-finite `poci_delta` raises `ValueError`; `by_stage` always has the four keys.
- Invariants: `total = model_total + overlay_total` exactly; overlays never enter `by_stage`; the C06 `stage_summary.ecl` is
  `by_stage`.
- Golden: `stage = [1, 2, 3]`, `ecl_12m = [10, 20, 30]`, `ecl_lifetime = [15, 40, 45]`, `ecl_stage3 = [0, 0, 25]`, one overlay of 5:
  `by_stage = {stage1: 10, stage2: 40, stage3: 25, poci: 0.0}`, `model_total = 75`, `total = 80`; with `poci = [False, False, True]`,
  `poci_delta = [nan, nan, 7]` the third account leaves stage 3: `by_stage = {stage1: 10, stage2: 40, stage3: 0.0, poci: 7.0}`.

## Module `riskvalidation/provisions/overlays.py`

Overlays as explicit line items (dossier 02 I.1 item 9; ECB July 2024; d350 paras 50, 51): each overlay is reported separately in
every output, never merged into model ECL.

### `riskvalidation.provisions.overlays.Overlay`

```python
@dataclass(frozen=True)
class Overlay:
    id: str
    rationale_en: str
    rationale_es: str
    method: str            # simulation | scenario | expert
    target: str            # pd | lgd | ead | staging-share
    segment_id: str | None
    stage: str | None      # stage1 | stage2 | stage3 | poci; None is portfolio level
    amount: float          # money, signed
    staging_effect: str    # none | transfers-to-stage2
    review_date: str       # ISO date
    currency: str          # ISO 4217
```

- Units: money in `currency`; the C06 `overlays[]` item is this record (`rationale` is `{en, es}`).
- Stage rule: an overlay with a `stage` is carried in that stage's allowance closing; an overlay with `stage = None` (portfolio level)
  is carried in the stage1 closing, because the roll-forward has no portfolio row (a convention of this contract, not an IFRS rule). The
  waterfall line of an overlay has `stage = overlay.stage` (null stays null) and the id `overlay-<overlay id>`.
- Invariants: `amount` finite; `method`, `target`, `staging_effect`, `stage` in their enums; ids unique within a run (raises otherwise).

### `riskvalidation.provisions.overlays.overlay_lines`

```python
def overlay_lines(overlays: Sequence[Overlay]) -> list[dict]: ...
```

- Units: returns the waterfall lines (`id = "overlay-<overlay id>"`, `kind = "overlay"`, `overlay_id`, `amount`, `stage = overlay.stage`), one per
  overlay, in id order; a positive amount raises the allowance.
- Invariants: one line per overlay; `sum(line.amount) = sum(overlay.amount)` exactly; an overlay is never merged into another line.
- Golden: one overlay `OVL-RATES` of 1500 at `stage1` gives one line with `id = "overlay-OVL-RATES"`, `overlay_id = "OVL-RATES"`,
  `stage = "stage1"` and `amount = 1500.0`.

### `riskvalidation.provisions.overlays.overlay_share`

```python
def overlay_share(overlay_total: float, total_allowance: float) -> float: ...
```

- Units: money inputs; returns `overlay_total / total_allowance` in [0, 1] for non-negative overlays; raises `ValueError` when
  `total_allowance <= 0` (no placeholder).
- Invariants: 0 with no overlays; at most 1.
- Golden: `overlay_share(5, 80) = 0.0625`.

### `riskvalidation.provisions.overlays.total_allowance`

```python
def total_allowance(model_ecl: float, overlays: Sequence[Overlay]) -> float: ...
```

- Units: money; returns `model_ecl + sum(overlay.amount)`.
- Invariants: equals `portfolio_allowance(...).total` for the same inputs.
- Golden: `total_allowance(75, [5]) = 80`.

## Module `riskvalidation/provisions/reconciliation.py`

The IFRS 7 35H (allowance) and 35I (gross carrying amount) roll-forwards and their identities (dossier 02 I.1 items 9 and 10, I.2).

### `riskvalidation.provisions.reconciliation.allowance_rollforward`

```python
@dataclass(frozen=True)
class RollForwardRow:
    stage: str                       # stage1 | stage2 | stage3 | poci
    opening: float
    movements: tuple[tuple[str, float], ...]   # (line_id, signed amount); a positive amount raises the allowance
    closing: float
    residual: float                  # closing - (opening + sum(movements))

def allowance_rollforward(stage: str, opening: float, movements: Mapping[str, float], closing: float) -> RollForwardRow: ...
```

- Units: money in the portfolio currency; the row is the C06 `reconciliation.allowance[]` item. Each `line_id` is the `id` of a C06
  `waterfall.lines[]` line (the model lines `originations`, `transfer-1-2`, ..., and `overlay-<overlay id>` for an overlay), so the waterfall can
  be opened into the 35H table.
- Invariants: `residual = closing - (opening + sum(movements))` exactly; the identity closes when `|residual|` is within the tolerance basis
  of the Conventions (`1e-6 * max(1, G)`), judged by `check_identities`, never by the row; movement order is preserved; the allowance of
  stage1 to stage3 is not negative (only POCI may be, 5.5.14).
- Golden: `opening = 1000`, movements `{originations: 200, write-off: -50}`, `closing = 1150` gives `residual = 0`.

### `riskvalidation.provisions.reconciliation.gca_rollforward`

```python
def gca_rollforward(stage: str, opening: float, movements: Mapping[str, float], closing: float) -> RollForwardRow: ...
```

- Units: gross carrying amount money; the C06 `reconciliation.gross_carrying_amount[]` item; `line_id` in the enum `originations`,
  `transfer-1-2`, `transfer-2-3`, `transfer-2-1`, `transfer-3-2`, `repayments`, `write-off`, `derecognition`, `other`.
- Invariants: as `allowance_rollforward`.
- Golden: `opening = 100000`, movements `{repayments: -5000, originations: 20000}`, `closing = 115000` gives `residual = 0`.

### `riskvalidation.provisions.reconciliation.check_identities`

```python
def check_identities(allowance: Sequence[RollForwardRow], gca: Sequence[RollForwardRow], waterfall_lines: Sequence[dict],
                     stage_ecl: Mapping[str, float], overlays: Sequence[Overlay] = (), tolerance: float = 1e-6) -> list[str]: ...
```

- Units: money; returns the names of the identities that fail (empty when all close): `allowance-rollforward:<stage>`,
  `gca-rollforward:<stage>`, `waterfall-closes` (`opening + sum(moves) = closing`), `waterfall-equals-stage-closings` (the sum of the stage
  closings equals the waterfall closing), `waterfall-lines-equal-movements` (every movement `line_id` is a waterfall line id and the line
  amount is the sum of the movements of that id over the stages), `stage-closing-equals-ecl:<stage>` (the allowance closing of a stage equals
  `stage_ecl` plus the overlays carried in that stage, by the stage rule of `Overlay`).
- Invariants: all identities close within `tolerance * max(1, G)` with `G` the total gross carrying amount of the `gca` rows (the 1e-6 gate
  of dossier 02 I.2, one basis for every identity); the function returns names and never raises on a mismatch.
- Golden: the C06 fixture `docs/contracts/fixtures/c06/variant-reporting-date-fixture.json` returns `[]` (its Stage 2 closing 1758.76 differs
  from its ECL 1758.7575 by 0.0025, inside the tolerance 1e-6 * 230000 = 0.23); moving one movement by 1.0 returns a non-empty list.

## Module `riskvalidation/validation/ifrs9.py`

The battery of dossier 02 I.2, each a `TestResult` row of `common/test-result` (`test_id` as named, `h0`, `alternative`,
`policy_version`, `reference` always set; `light` in green, amber, red, not_evaluated, error). The acceptance gates are Contraste
internal gates, stated as such, not regulatory thresholds: each function states its light rule on a `- Light:` line, with its parameters
named so that a view can explain a light; the parameters travel in `policy_version`, `alpha_amber` and `alpha_red`. A test with no data
returns `not_evaluated` with its reason in `notes`.

### `riskvalidation.validation.ifrs9.lifetime_pd_backtest`

```python
def lifetime_pd_backtest(months: np.ndarray, predicted_cumulative: np.ndarray, observed_cumulative: np.ndarray,
                         n_at_risk: np.ndarray, n_events: np.ndarray, rho: float | None = None,
                         competing_prepayment: bool = False,
                         model_id: str | None = None, segment: str | None = None) -> TestResult: ...
```

- Units: arrays (H,) by horizon in months; predicted open (0, 1); observed cumulative default in [0, 1] (NaN where the horizon is not yet
  observed), estimated by the Aalen-Johansen cumulative incidence when `competing_prepayment` is true (the prediction then comes from
  `competing_risks`, and Kaplan-Meier would treat prepayment as censoring and estimate `1 - S_D`, not the incidence) and by Kaplan-Meier
  otherwise; `rho` for the Vasicek acceptance band. The C06 `lifetime_backtest` and `decile_calibration` rows name the `estimator`. `test_id = "ifrs9.lifetime_pd_backtest"` (EBA/Rep/2023/36
  paras 114 to 118).
- Invariants: `metric` is the largest absolute gap `|observed - predicted|` over observed horizons; `extras` carries `gap`, `brier` and
  (with `rho`) `band_low`, `band_high` per horizon; unobserved horizons are excluded, none observed gives `not_evaluated`.
- Light: with `rho`, red if any observed horizon is outside the Vasicek band at `alpha_red` (0.01), amber if outside at `alpha_amber`
  (0.05), else green; without `rho`, the relative gap `|observed - predicted| / predicted` per observed horizon: green below `gap_amber`
  (0.25), amber below `gap_red` (0.50), red otherwise; the worst horizon decides.
- Golden: `observed == predicted` gives `metric = 0.0` and `light = "green"`.

### `riskvalidation.validation.ifrs9.sicr_effectiveness`

```python
def sicr_effectiveness(stage_at_origination_view: np.ndarray, defaulted_within_k: np.ndarray, k_months: int,
                       months_in_stage2_before_default: np.ndarray, stage3_from_stage1: np.ndarray,
                       backstop_only: np.ndarray, model_id: str | None = None) -> TestResult: ...
```

- Units: arrays (A,): stage in {1, 2} at the reference date, `defaulted_within_k` bool, months, booleans. `test_id =
  "ifrs9.sicr_effectiveness"` (EBA/Rep/2023/36 paras 94 to 99; d350 A38).
- Invariants: `metric = DR_S2 / DR_S1`; `extras` carries `roc_auc`, `hit_rate`, `share_stage3_direct_from_stage1`,
  `mean_months_in_stage2`, `share_stage2_backstop_only`, each with an interval where defined; no Stage 1 defaults gives
  `not_evaluated`.
- Light: green when `metric >= 2.0` (Stage 2 defaults at least twice as often as Stage 1), amber when `1.0 <= metric < 2.0`, red below 1.0;
  amber at least when `share_stage3_direct_from_stage1 > 0.5`.
- Golden: Stage 1: 1000 accounts, 10 defaults; Stage 2: 100 accounts, 30 defaults: `metric = 30.0`, green.

### `riskvalidation.validation.ifrs9.sicr_threshold_stability`

```python
def sicr_threshold_stability(implied_multiplier: np.ndarray, condition_index: np.ndarray,
                             model_id: str | None = None) -> TestResult: ...
```

- Units: `implied_multiplier` (P,) over reporting periods, `condition_index` (P,) higher when conditions worsen. `test_id =
  "ifrs9.sicr_threshold_stability"` (EBA/Rep/2023/36 paras 29 to 33).
- Invariants: `metric` counts periods where the multiplier rises (the threshold loosens) while the condition index rises; zero is
  green, any is not green.
- Light: `metric = 0` green; `metric >= 1` amber; red when `metric` is at least half of the periods.
- Golden: multipliers `[2.0, 2.5]`, condition index `[0.0, 1.0]`: `metric = 1.0`, `light != "green"`.

### `riskvalidation.validation.ifrs9.stage_migration_backtest`

```python
def stage_migration_backtest(predicted_matrix: np.ndarray, observed_counts: np.ndarray,
                             model_id: str | None = None) -> TestResult: ...
```

- Units: `predicted_matrix` (3, 3) row-stochastic (rows sum to 1 within 1e-9); `observed_counts` (3, 3) non-negative integers.
  `test_id = "ifrs9.stage_migration_backtest"`; chi-square on the transition counts (EBA/Rep/2023/36 para 97).
- Invariants: `statistic >= 0`, `p_value` in [0, 1], rows with no observations are skipped and counted in `extras`.
- Light: green when `p_value >= alpha_amber` (0.05), amber when `alpha_red <= p_value < alpha_amber` (0.01), red below `alpha_red`.
- Golden: counts exactly proportional to the predicted matrix give `statistic = 0.0`, `p_value = 1.0`, green.

### `riskvalidation.validation.ifrs9.ecl_backtest`

```python
def ecl_backtest(realised_pv_losses: np.ndarray, ecl_horizon: np.ndarray, horizon_months: int,
                 model_id: str | None = None) -> TestResult: ...
```

- Units: money (A,) of the same accounts: discounted realised losses within `horizon_months` and the model ECL for that horizon,
  overlays excluded. `test_id = "ifrs9.ecl_backtest"` (IFRS 9 B5.5.52; EBA/Rep/2023/36 paras 100 to 104).
- Invariants: `metric = R_H = sum(realised) / sum(ecl)`; zero ECL gives `not_evaluated`.
- Light: green when `0.8 <= metric <= 1.25`, amber when `0.5 <= metric < 0.8` or `1.25 < metric <= 2.0`, red outside; the bounds are the
  parameters `r_green` and `r_amber`.
- Golden: realised total 90 against ECL total 100 gives `metric = 0.9`, green.

### `riskvalidation.validation.ifrs9.scenario_sensitivity`

```python
def scenario_sensitivity(ecl_by_scenario: np.ndarray, weights: np.ndarray, ecl_at_mean_path: float,
                         model_id: str | None = None) -> TestResult: ...
```

- Units: `ecl_by_scenario` (S,) money; weights (S,); `test_id = "ifrs9.scenario_sensitivity"` (d350 para 36(a); GPPC 2.8.1.2).
- Invariants: `metric` is the non-linearity index `NL`; `extras` carries the 100 per cent single-scenario ECLs and
  `weight_sensitivity` against each reference scenario.
- Light: informational, green when `0 <= NL <= 1.0` (parameter `nl_amber`), amber when `NL > 1.0` or `NL < 0` (a concave ECL is
  unexpected), red when `NL > 3.0` (`nl_red`).
- Golden: `ecl_by_scenario = [0.4 * 0.005255059, 0.4 * 0.014287387, 0.4 * 0.073424082]`, `w = (0.25, 0.5, 0.25)`, `ecl_at_mean_path
  = 0.4 * 0.017997448`: `metric = 0.4898489` to 1e-6 (0.48985 rounded), green. The 100 per cent single-scenario ECLs in `extras` are
  sensitivities, never the IFRS 9 measure (5.5.17(a), B5.5.42).

### `riskvalidation.validation.ifrs9.nonlinearity_test`

```python
def nonlinearity_test(pd_ttc: float, rho: float, z: np.ndarray, weights: np.ndarray,
                      model_id: str | None = None) -> TestResult: ...
```

- Units: as `weighted_pit_pd`; `test_id = "ifrs9.nonlinearity"`; the PD-level index with the Gauss-Hermite cross check.
- Invariants: `metric = weighted / at_mean_z - 1`; `extras` carries `pd_weighted`, `pd_at_mean_z`, `gauss_hermite_error` (below 1e-9).
- Light: green when `gauss_hermite_error <= 1e-9` and `metric >= 0`; red otherwise (a numerical failure, not a model finding).
- Golden: `pd_ttc = 0.02`, `rho = 0.12`, `z = (1, 0, -2)`, `w = (0.25, 0.5, 0.25)`: `pd_weighted = 0.026813479` (2.681%),
  `pd_at_mean_z = 0.017997448` (1.800%) each to 1e-8, `metric = 0.4898489` to 1e-6, green.

### `riskvalidation.validation.ifrs9.overlay_diagnostics`

```python
def overlay_diagnostics(overlays: Sequence[Overlay], allowance_by_stage: Mapping[str, float],
                        scenario_direction: int, model_id: str | None = None) -> TestResult: ...
```

- Units: money; `scenario_direction` is +1 when the scenarios worsened, -1 when they improved, 0 otherwise. `test_id =
  "ifrs9.overlay_diagnostics"` (ECB July 2024; d350 paras 50, 51).
- Invariants: `metric` is the overlay share of the total allowance; `extras` carries the share by stage and by segment, the
  parameter-level versus total-level split and a `direction_consistent` flag (a positive overlay in an improving scenario is flagged).
- Light: green when `metric <= 0.10` (parameter `share_amber`) and `direction_consistent`; amber when `metric <= 0.25` (`share_red`) or the
  direction is inconsistent; red above 0.25.
- Golden: overlays 5 against model ECL 75 gives `metric = 0.0625`, green.

### `riskvalidation.validation.ifrs9.reconciliation_identities`

```python
def reconciliation_identities(allowance: Sequence[RollForwardRow], gca: Sequence[RollForwardRow],
                              waterfall_lines: Sequence[dict], stage_ecl: Mapping[str, float],
                              model_id: str | None = None, *, tolerance: float = 1e-6) -> TestResult: ...
```

- Units: as `check_identities`; `test_id = "ifrs9.reconciliation_identities"` (IFRS 7 35H, 35I).
- Invariants: `metric` is the largest absolute roll-forward residual; the largest gap between a stage's closing allowance and its
  `stage_ecl` is reported separately as `extras.stage_ecl_gap_max` and judged against the same tolerance; `extras` carries the failing
  identity names. A reconciliation with no rows, without its opening or closing waterfall line, or with a stage lacking its stage
  ECL returns `light = "not_evaluated"` with the reason, never an
  infinite metric.
- Light: green when the metric and `extras.stage_ecl_gap_max` are both `<= tolerance * max(1, G)` (the tolerance basis of the
  Conventions), red otherwise.
- Amended 2026-10-12 (engine review decisions C1 and F4, riskvalidation v0.05.000): the stage gap moved out of `metric` into
  `extras.stage_ecl_gap_max`; the `tolerance` keyword and the `not_evaluated` case were added.
- Golden: the C06 fixture reconciliation gives `metric = 0.0` and `light = "green"`.

## Module `riskvalidation/provisions/local_cl.py`

CMF CNCB Chapter B-1 standard methods for group portfolios (dossier 03 D.5 tables transcribed with their cells), the individual
assessment categories (D.3), the 0.50% minimum and additional provisions (D.6). Parameters are decimals; the B-1 factor is
`PE = PI * PDI`. The tables are statutory parameters, returned as transcribed (a PE is the transcribed cell, equal to `PI * PDI`
within the table's own rounding of 5e-7 as a decimal). B-1 is not IFRS 9 (dossier 02 F.5).

### `riskvalidation.provisions.local_cl.b1_individual_category`

```python
def b1_individual_category(category: str) -> tuple[float, float, float]: ...
```

- Units: category in A1..A6, B1..B4; returns `(pi, pdi, pe)` decimals (CNCB B-1 N 2.1, "Hoja 3"); raises `KeyError` otherwise.
- Invariants: `pe = pi * pdi` to 1e-9 for the individual table; PI strictly increasing from A1 to B4.
- Golden: `A1 = (0.0004, 0.9, 0.00036)`, `A4 = (0.02, 0.875, 0.0175)`, `B4 = (0.45, 0.975, 0.43875)`.

### `riskvalidation.provisions.local_cl.b1_individual_provision`

```python
def b1_individual_provision(eap: float, ea: float, category: str, guarantor_category: str | None = None) -> float: ...
```

- Units: `eap` exposure subject to provisions (loans plus contingent credits less collateral at realisable value) and `ea` guaranteed
  exposure, money; returns `(EAP - EA) * PI * PDI + EA * PI_aval * PDI_aval` (B-1 N 2.1.3).
- Invariants: `0 <= ea <= eap`; `ea = 0` gives `eap * pe`; guarantees are never deducted from the exposure.
- Golden: `eap = 1000`, `ea = 0`, `A4` gives 17.5; `eap = 1000`, `ea = 400`, debtor `A4`, guarantor `A1` gives 10.644.

### `riskvalidation.provisions.local_cl.b1_default_provision`

```python
def b1_default_provision(exposure: float, recoverable: float) -> tuple[float, str, float]: ...
```

- Units: money; returns `(tpe, category, provision)` with `TPE = (E - R) / E`, rounded to 1e-9 before any bucket comparison (so a float
  `TPE` at a boundary lands in its inclusive bucket), and `provision = E * PP` (B-1 N 2.2): C1 up to 3% pays
  2%, C2 up to 20% pays 10%, C3 up to 30% pays 25%, C4 up to 50% pays 40%, C5 up to 80% pays 65%, C6 above 80% pays 90%; upper
  bounds inclusive.
- Invariants: `provision` nondecreasing in `exposure - recoverable`; `0 <= R <= E` else `ValueError`.
- Golden: `E = 1000`, `R = 700` gives `(0.30, "C3", 250.0)`; `TPE = 0.03` gives C1; `TPE = 0.80` gives C5; `TPE = 0.81` gives C6.

### `riskvalidation.provisions.local_cl.b1_mortgage_pe`

```python
def b1_mortgage_pe(pvg: float, dpd_bucket: str) -> tuple[float, float, float]: ...
```

- Units: `pvg` = outstanding principal over the mortgage collateral value (decimal); `dpd_bucket` in `0`, `1-29`, `30-59`, `60-89`,
  `default`; PVG buckets `<= 40%`, `<= 80%`, `<= 90%`, `> 90%`; returns `(pi, pdi, pe)` (Circular 2.346, "Hoja 11"; 20 cells).
- Invariants: every cell has `pe = pi * pdi` to 5e-7; PI in a row increases across the dpd buckets and equals 1 in `default`.
- Golden: `pvg = 0.75`, `"0"` gives `(0.019158, 0.021955, 0.000421)`; `pvg = 0.95`, `"default"` gives `(1.0, 0.302436, 0.302436)`.

### `riskvalidation.provisions.local_cl.b1_leasing_pe`

```python
def b1_leasing_pe(pvb: float, dpd_bucket: str, real_estate: bool) -> tuple[float, float, float]: ...
```

- Units: `pvb` = present value of the lease over the asset value; returns `(pi, pdi, pe = pi * pdi)` from the commercial leasing tables
  (D.5 3.1.2 a).
- Invariants: `pe = pi * pdi` exactly; PI 1 at `default`.
- Golden: real estate, `"0"`, `pvb = 0.45`: `pi = 0.0079`, `pdi = 0.0005`, `pe = 3.95e-6`.

### `riskvalidation.provisions.local_cl.b1_student_loan_pe`

```python
def b1_student_loan_pe(scheme: str, dpd_bucket: str) -> tuple[float, float, float]: ...
```

- Units: `scheme` in `CAE`, `CORFO`; `dpd_bucket` in `0`, `1-29`, `30-59`, `60-89`, `default`, `not-due` (D.5 3.1.3 b).
- Invariants: `pe = pi * pdi`; PI 1 at `default`.
- Golden: `("CAE", "0")` gives `(0.052, 0.709, 0.036868)`; `("CAE", "not-due")` gives `(0.416, 0.503, 0.209248)`.

### `riskvalidation.provisions.local_cl.b1_commercial_pe`

```python
def b1_commercial_pe(dpd_bucket: str, ptvg: float | None, factoring_with_recourse: bool = False) -> tuple[float, float, float]: ...
```

- Units: `ptvg` = obligations over the value of real guarantees (decimal), `None` for no guarantee (D.5 3.1.2 c); returns `(pi, pdi, pe)`.
- Invariants: `pe = pi * pdi`; PI 1 at `default`; PDI with guarantee increases with `ptvg` across the buckets `<= 60%`, `<= 75%`,
  `<= 90%`, `> 90%`; factoring with recourse uses its own PDI column.
- Golden: `("0", None)` gives `(0.0491, 0.569, 0.0279379)`; `("0", 0.5)` gives `(0.0186, 0.05, 0.00093)`.

### `riskvalidation.provisions.local_cl.b1_consumer_pe`

```python
def b1_consumer_pe(max_dpd_in_bank: int, has_mortgage_in_system: bool, arrears_30_in_system_3m: bool,
                   product: str) -> tuple[float, float, float]: ...
```

- Units: days past due integer; `product` in `leasing-auto`, `instalment`, `cards-lines-other`; returns `(pi, pdi, pe)` (Circular
  2.346, D.5 3.1.3). The PI matrix has 16 cells (4 dpd buckets `0-7`, `8-30`, `31-60`, `61-89` by 4 columns: mortgage or not, system
  arrears or not); `dpd >= 90` gives PI 1. PDI: with a mortgage 0.332 / 0.477 / 0.495, without 0.332 / 0.566 / 0.603.
- Invariants: all 16 cells reproduced exactly; PI increases down each column and across no-arrears to arrears; `pe = pi * pdi`.
- Golden (16 cells, the PI column "with mortgage, no 30+ system arrears" is 0.033, 0.204, 0.502, 0.626): `(3, True, False,
  "instalment")` gives `(0.033, 0.477, 0.015741)`; `(70, False, True, "cards-lines-other")` gives `(0.869, 0.603, 0.524007)`.

### `riskvalidation.provisions.local_cl.b1_group_provision`

```python
def b1_group_provision(group_exposure: float, pe_group: float, guaranteed_share: float = 0.0,
                       pe_guarantor: float = 0.0) -> float: ...
```

- Units: money; `pe_group` and `pe_guarantor` decimals; `guaranteed_share` in [0, 1] is `EA / 100`. Returns
  `EG (1 - EA) PE_group + EG EA PE_aval` (B-1 N 4.1).
- Invariants: `guaranteed_share = 0` gives `EG * PE`; with `pe_guarantor <= pe_group` the result is at most `EG * pe_group`.
- Golden: `EG = 1000`, `pe_group = 0.02`, `guaranteed_share = 0.5`, `pe_guarantor = 0.0004` gives 10.2.

### `riskvalidation.provisions.local_cl.b1_minimum_normal_check`

```python
@dataclass(frozen=True)
class MinimumCheck:
    minimum_rate: float      # 0.005
    minimum_amount: float
    binding: bool
    top_up: float

def b1_minimum_normal_check(normal_exposure: float, normal_provision: float) -> MinimumCheck: ...
```

- Units: money; the 0.50% minimum on the individually assessed normal portfolio (categories A1 to A6), loans plus contingent credits
  (B-1 N 2.1.3; dossier 03 D.3), `minimum_rate = 0.005` constant. `normal_exposure` and `normal_provision` are those of that portfolio
  only, not the group-assessed book and not the whole performing book.
- Invariants: `minimum_amount = 0.005 * normal_exposure`; `top_up = max(0, minimum_amount - normal_provision)`; `binding = top_up > 0`;
  the minimum is always enforced (the C07 `b1_detail.minimum_check` block).
- Golden: exposure 25e9, provision 100e6 gives `minimum_amount = 125e6`, `binding = True`, `top_up = 25e6`; provision 150e6 gives
  `binding = False`, `top_up = 0`.

### `riskvalidation.provisions.local_cl.b1_group_max_rule`

```python
def b1_group_max_rule(standard: float, internal: float | None, internal_not_objected: bool = False) -> tuple[float, str]: ...
```

- Units: money; returns `(applied, method)` with `method` in `standard`, `internal`, `max` (B-1 N 3: the larger of the standard and
  the internal method unless the internal method has the CMF "no objection"). The C07 `group_max_rule[]` item carries `internal = null`
  with `internal_reason` when the bank has no internal method.
- Invariants: `applied >= standard` unless `internal_not_objected`; `internal = None` gives `(standard, "standard")`.
- Golden: `(100, 90, False)` gives `(100, "max")`; `(100, 90, True)` gives `(90, "internal")`; `(100, None, False)` gives `(100, "standard")`.

### `riskvalidation.provisions.local_cl.b1_additional_provisions`

```python
def b1_additional_provisions(amount: float, policy_min: float, policy_max: float) -> float: ...
```

- Units: money; counter-cyclical general provisions inside the board's policy limits (B-1 N 9), reported as their own line and never
  used to cover model deficiencies.
- Invariants: returns `amount` when `policy_min <= amount <= policy_max`, else raises `ValueError`; the C07 `b1_detail.additional_provisions`.
- Golden: `(60e6, 0, 120e6)` returns 60e6; `(130e6, 0, 120e6)` raises `ValueError`.

## Module `riskvalidation/provisions/local_es.py`

Banco de Espana Circular 4/2017 Annex 9 coverage tables and the category-to-stage mapping (dossier 03 K.2, K.3). Point numbers (144,
140) are as of Circular 6/2021; whether they shifted after Circular 1/2025 is UNVERIFIED in the dossier and stays a documented
limitation. Coverage is applied to the amount not covered by effective guarantees: `Cobertura = c * max(0, EAD - sum(adjusted guarantees))`.

### `riskvalidation.provisions.local_es.annex9_uncovered_amount`

```python
def annex9_uncovered_amount(ead: float, adjusted_guarantee_values: Sequence[float]) -> float: ...
```

- Units: money; returns `max(0, EAD - sum(adjusted))`.
- Invariants: in `[0, EAD]`; nonincreasing in the guarantees.
- Golden: `(100, [30, 20])` gives 50; `(100, [120])` gives 0.

### `riskvalidation.provisions.local_es.annex9_normal_coverage`

```python
def annex9_normal_coverage(segment: str, category: str) -> float: ...
```

- Units: `segment` code (A.1.1, A.1.2, A.1.3, A.2.1, A.2.2, A.2.3, B.1.1, B.1.2, B.1.3, B.2, B.2.1, B.3), `category` in `normal`,
  `normal-special-watch`; returns the coverage decimal (point 144, from 2022-06-30).
- Invariants: special-watch coverage exceeds normal coverage for every segment; values in (0, 1).
- Golden: `("B.1.1", "normal") = 0.007`, `("B.1.1", "normal-special-watch") = 0.18`, `("A.1.1", "normal") = 0.019`,
  `("A.1.1", "normal-special-watch") = 0.30`, `("B.2", "normal-special-watch") = 0.202`, `("B.2.1", "normal") = 0.010`.

### `riskvalidation.provisions.local_es.annex9_doubtful_coverage`

```python
def annex9_doubtful_coverage(segment: str, days_past_due: int) -> float: ...
```

- Units: `days_past_due` the age of the oldest past-due amount in days. Point 140 counts months; this contract converts them once, at
  30.4375 days per month rounded to the nearest day (Contraste's convention; a bank's own day count overrides it in the caller), giving the
  buckets `(90, 183]`, `(183, 274]`, `(274, 365]`, `(365, 457]`, `(457, 548]`, `(548, 639]` and above 639 days, upper bounds inclusive (the
  7 columns `>90d-6m` to `>21m`); raises `ValueError` for `days_past_due <= 90`. The C07 models carry the bounds as
  `bde.doubtful_bucket_upper_days` (`null` for the last).
- Invariants: nondecreasing in age; 1.0 above 639 days for every segment.
- Golden: `("B.1.1", 150) = 0.45`; `("B.1.1", 91) = 0.45`; `("B.1.1", 670) = 1.0`; `("B.2", 243) = 0.65`; `("A.2.3", 122) = 0.35`; `("B.1.1", 90)` raises.

### `riskvalidation.provisions.local_es.annex9_category_to_stage`

```python
def annex9_category_to_stage(category: str) -> str: ...
```

- Units: category in `normal`, `normal-special-watch`, `doubtful`, `written-off` (norma 29.11; the mapping Circular 6/2021 states for
  reporting); returns `stage1`, `stage2`, `stage3` or `written-off`.
- Invariants: a total, injective map on the four categories; the C07 `bde_detail.categories[].mapped_stage`.
- Golden: `normal` gives `stage1`; `normal-special-watch` gives `stage2`; `doubtful` gives `stage3`; `written-off` gives `written-off`.

### `riskvalidation.provisions.local_es.annex9_coverage`

```python
def annex9_coverage(segment: str, category: str, ead: float, adjusted_guarantee_values: Sequence[float],
                    days_past_due: int | None = None) -> float: ...
```

- Units: money; for `doubtful` the coverage comes from `annex9_doubtful_coverage` (`days_past_due` required and above 90), otherwise from
  `annex9_normal_coverage`; returns `c * annex9_uncovered_amount(ead, adjusted_guarantee_values)`; `written-off` returns 0. A doubtful account
  for reasons other than arrears (riesgo dudoso por razones distintas de la morosidad) has no transcribed coverage (dossier 03 K.3): the
  call with `days_past_due` missing or at most 90 raises `ValueError`, and the caller reports the account as not evaluated.
- Invariants: `0 <= coverage <= EAD`; nondecreasing in `ead`; with full guarantee cover the result is 0.
- Golden: `("B.1.1", "normal", 100000, [40000]) = 0.007 * 60000 = 420.0`.

## Golden values summary

| Value | Where | Source |
|---|---|---|
| PD 0.526%, 1.429%, 7.342% at z = +1, 0, -2 (`pd_ttc` 2%, `rho` 0.12) | `ttc_to_pit` | dossier 02 B.4 |
| weighted PD 2.681% against 1.800% at the mean factor, ratio 1.49; LGD 40% gives 1.07% against 0.72% | `weighted_pit_pd`, `probability_weighted_ecl`, `nonlinearity_test` | dossier 02 B.4 |
| reconciliation identities within 1e-6 * max(1, G), G the total gross carrying amount | `reconciliation_identities`, `check_identities` | dossier 02 I.2 |
| B-1 consumer matrix, 16 cells; PE = PI x PDI for every transcribed cell; 0.50% minimum on the normal portfolio | `local_cl.*` | dossier 03 D.3, D.5 |
| Annex 9 point 144 and point 140 tables as transcribed; the category to stage map | `local_es.*` | dossier 03 K.2, K.3 |

Open items carried from the dossiers, never silently decided: the Annex 9 point numbers after Circular 1/2025 (UNVERIFIED);
the EBA's own annualisation formula (the geometric form here is Contraste's convention); the August 2026 CMF reform proposal is not
in force and is not implemented.
