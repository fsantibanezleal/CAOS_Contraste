# Engine regulatory API contract: `engine-regulatory-api` 2.1.0

Owner: U9-S (unit sizing `plans/contraste/units/U9-sizing.md`, CAOS_MANAGE). Implemented by U9-E1 in `riskvalidation.regulatory`
(`standardised.py`, `output_floor.py`, `sa_ccr.py`, `ba_cva.py`, `frtb.py`; repository CAOS_RiskValidation); called by the regulatory
parity bake (U9-P2), the C12 bake (U9-P1) and held by the live TypeScript ports (U9-W1, U9-W2). The tests of every function are written
by U9-E1 against this file: a function exists with exactly the signature below, and each golden value or invariant is a test. Changing a
signature, a unit or a golden value is a breaking change (a new major version of this contract). `regulatory/irb.py` and its contract
are not part of it; SMA is `oprisk/sma.py`; LCR and NSFR are U11's (`regulatory/lcr_nsfr.py`, sizing decision D2).

Version history: 1.0.0, the first contract; 1.1.0 and 2.0.0 after the U9-E1 review (the curvature gamma, see the catalog); 2.1.0 adds `entity_aggregate_terms`, `credit_addon_terms`, `equity_addon_terms` and `cross_bucket_charge_detail` (U9-E1 terms, engine 3d77e77), so the regulatory parity bake reads the CRE52.61 terms and the MAR21.4(5)(b) flag from the engine; the existing functions keep their signatures and results.
Sources: dossier 01 (`wip/contraste/01-basel-pillar1-pillar2-framework-2026-10-04.md`, sections C, C.1, D.2, D.3, E.1, E.2, M.1, M.3),
the U9 research addendum (`wip/contraste/u9-research-addendum-2026-10-17.md`, R7 and R8) and the unit sizing. The documents this contract
feeds are `regulatory-calculators` (`docs/contracts/schemas/regulatory/calculators.schema.json`) and `c12-outputs` (`sa_ccr`, `ba_cva`,
`girr`, `regulatory_comparison`).

The engine computes; it states no compliance claim (dossier 01 M.4). Every constant and table is transcribed from the dossier line named;
an item the dossiers mark UNVERIFIED is marked so here and is not silently decided (list at the end).

## Conventions (all functions)

- Arrays are `numpy.ndarray` of `float64`. Money is a float in one currency the caller states; the engine never converts currencies.
  Rates and risk weights are decimals (0.05 is 5 percent); times are years; MPoR is in business days with 250 to the year (CRE52.52).
- Every function is pure and deterministic (no hidden state, no I/O, inputs never mutated). Dataclasses are frozen.
- **Every parameter the engine returns carries its paragraph and in-force date** (dossier 01 M.3 item 8): a table lookup returns a
  `RegulatoryParameter(value, paragraph, table, in_force)` (`RiskWeight` stays as an alias of it) and a parameter table is module data of
  entries with the same fields. The
  in-force dates are those of the chapter version the dossier names: CRE20 2023-01-01 (published 2025-06-10), CRE52 2023-01-01 (published
  2020-06-05), MAR50 2023-01-01 (published 2020-07-08), MAR21 2023-01-01 (published 2026-03-23), MAR33 2023-01-01 (published 2020-06-05),
  RBC20 2023-01-01 (published 2020-11-26), RBC90 2023-01-01 (published 2020-03-27).
- A key outside a table (an unknown rating bucket, an LTV below zero) raises `ValueError` naming the table and the paragraph; the engine
  never returns a placeholder weight.
- Tolerance: each golden value states its own tolerance or is exact; a golden stated to three decimals holds to `5e-4`. An EAD printed as
  an integer is reproduced EXACTLY after rounding on the trade-level path: `round(netting_set_ead(...))` from the trade inputs of the BIS
  page (intermediates carried unrounded, CRE99.20) equals 569, 381, 5,406, 936 and 1,879 (dossier 01 M.3 item 2). The one-unit tolerance
  stays only on the path from the printed (rounded) intermediates.
- The worked-example values below are those of dossier 01 E.2 and of the BIS CRE99 page (CRE99.20 to CRE99.97, USD thousands). The
  trade inputs of the five netting sets are transcribed from the BIS page (paragraph numbers kept) into the document
  `regulatory-calculators` (`trades` of each example), so the engine tests start from the trades, not from the printed intermediates.

## Module `riskvalidation/regulatory/standardised.py`

The CRE20 standardised credit risk weights as data with their paragraph (dossier 01 C). Rating buckets: sovereigns, banks ECRA and
corporates use `"AAA to AA-"`, `"A+ to A-"`, `"BBB+ to BBB-"`, `"BB+ to B-"` (corporates `"BB+ to BB-"`), `"below B-"` (corporates
`"below BB-"`), `"unrated"`.

### `riskvalidation.regulatory.standardised.RegulatoryParameter`

```python
@dataclass(frozen=True)
class RegulatoryParameter:
    value: float         # a risk weight, a credit conversion factor, a phase-in factor or a multiplier, as a decimal
    paragraph: str       # for example "CRE20.7"
    table: str           # for example "CRE20 Table 1"
    in_force: str        # ISO date of the chapter version

RiskWeight = RegulatoryParameter  # alias: the class also carries the CCF (CRE20.94) and the phase-in factor (RBC90.1)
```

- Units: `value` a decimal; `paragraph` and `table` strings; `in_force` an ISO date.
- Invariants: every function of this module returns a `RegulatoryParameter` (never a bare float), so a view shows the paragraph and the in-force date of every parameter (dossier 01 M.3 item 8); the `RiskWeight` alias is kept so a caller written against the first name still works.

### `riskvalidation.regulatory.standardised.sovereign_risk_weight`

```python
def sovereign_risk_weight(rating: str) -> RegulatoryParameter: ...
```

- Units: `rating` a bucket label; the weight a decimal.
- Golden: CRE20.7 Table 1: `AAA to AA-` 0, `A+ to A-` 0.2, `BBB+ to BBB-` 0.5, `BB+ to B-` 1.0, `below B-` 1.5, `unrated` 1.0 (dossier 01 C); paragraph `CRE20.7`.

### `riskvalidation.regulatory.standardised.eca_risk_weight`

```python
def eca_risk_weight(score: int) -> RegulatoryParameter: ...
```

- Units: `score` an integer 0 to 7.
- Golden: CRE20.9 Table 2: scores 0 and 1 give 0, 2 gives 0.2, 3 gives 0.5, 4 to 6 give 1.0, 7 gives 1.5; a score outside 0 to 7 raises `ValueError`.

### `riskvalidation.regulatory.standardised.bank_risk_weight_ecra`

```python
def bank_risk_weight_ecra(rating: str, short_term: bool = False) -> RegulatoryParameter: ...
```

- Units: `rating` a bucket label of the ECRA; `short_term` the CRE20.18 short-term claims column.
- Golden: CRE20.18 Table 6, base: 0.2, 0.3, 0.5, 1.0, 1.5 for the five buckets; short-term: 0.2, 0.2, 0.2, 0.5, 1.5; `unrated` is not in the table and raises `ValueError` (the SCRA applies).

### `riskvalidation.regulatory.standardised.bank_risk_weight_scra`

```python
def bank_risk_weight_scra(grade: str, short_term: bool = False) -> RegulatoryParameter: ...
```

- Units: `grade` one of `A`, `B`, `C`.
- Golden: CRE20.21 Table 7: Grade A 0.4 (short-term 0.2), Grade B 0.75 (0.5), Grade C 1.5 (1.5).

### `riskvalidation.regulatory.standardised.corporate_risk_weight`

```python
def corporate_risk_weight(rating: str, sme: bool = False, investment_grade_unrated: bool = False, regulatory_retail_sme: bool = False) -> RegulatoryParameter: ...
```

- Units: `rating` a corporate bucket label or `unrated`.
- Golden: CRE20.43 Table 10: `AAA to AA-` 0.2, `A+ to A-` 0.5, `BBB+ to BBB-` 0.75, `BB+ to BB-` 1.0, `below BB-` 1.5, `unrated` 1.0; where ratings are not allowed investment grade is 0.65 (CRE20.44, CRE20.46); unrated SME 0.85 and regulatory retail SME 0.75 (CRE20.47).

### `riskvalidation.regulatory.standardised.retail_risk_weight`

```python
def retail_risk_weight(kind: str) -> RegulatoryParameter: ...
```

- Units: `kind` one of `regulatory`, `transactor`, `other`.
- Golden: CRE20.68: regulatory retail 0.75, transactors 0.45, other retail 1.0.

### `riskvalidation.regulatory.standardised.equity_risk_weight`

```python
def equity_risk_weight(kind: str) -> RegulatoryParameter: ...
```

- Units: `kind` one of `equity`, `speculative-unlisted`, `legislated-programme`, `subordinated-debt`.
- Golden: CRE20.57 to CRE20.60: equity 2.5, speculative unlisted 4.0, legislated programmes 1.0 (up to 10 percent of Total capital, the cap is the caller's), subordinated debt and non-equity capital instruments 1.5.

### `riskvalidation.regulatory.standardised.residential_re_risk_weight`

```python
def residential_re_risk_weight(ltv: float, cash_flow_dependent: bool = False, loan_splitting: bool = False) -> RegulatoryParameter: ...
```

- Units: `ltv` a decimal (0.8 is 80 percent), at least 0.
- Golden: CRE20.82 Table 11 (not cash-flow dependent): LTV at most 0.5 gives 0.2; to 0.6 gives 0.25; to 0.8 gives 0.3; to 0.9 gives 0.4; to 1.0 gives 0.5; above 1.0 gives 0.7. CRE20.84 Table 12 (cash-flow dependent): 0.3, 0.35, 0.45, 0.6, 0.75, 1.05 on the same bands. The upper edge of a band belongs to it (LTV exactly 0.8 gives 0.3). With `loan_splitting` (CRE20.83) the weight is 0.2 up to 55 percent of the property value; the split of the loan is the caller's.

### `riskvalidation.regulatory.standardised.commercial_re_risk_weight`

```python
def commercial_re_risk_weight(ltv: float, cash_flow_dependent: bool, counterparty_weight: float | None = None) -> RegulatoryParameter: ...
```

- Units: `ltv` a decimal; `counterparty_weight` the weight of the counterparty, required when not cash-flow dependent.
- Golden: CRE20.85 Table 13 (not cash-flow dependent): LTV at most 0.6 gives min(0.6, counterparty weight), above gives the counterparty weight. CRE20.87 Table 14 (cash-flow dependent): at most 0.6 gives 0.7, to 0.8 gives 0.9, above 0.8 gives 1.1.

### `riskvalidation.regulatory.standardised.apply_currency_mismatch`

```python
def apply_currency_mismatch(weight: float) -> RegulatoryParameter: ...
```

- Units: `weight` the unadjusted weight, a decimal; the result is the ADJUSTED weight (the multiplier 1.5 is the `currency-mismatch` / `multiplier` row of `lookup`).
- Golden: CRE20.92: 1.5 times the weight, at most 1.5 (150 percent): 0.75 gives 1.125, 1.2 gives 1.5.

### `riskvalidation.regulatory.standardised.credit_conversion_factor`

```python
def credit_conversion_factor(kind: str) -> RegulatoryParameter: ...
```

- Units: `kind` one of `direct-credit-substitute`, `repo`, `securities-lending`, `forward-purchase`, `nif-ruf`, `transaction-related-contingent`, `commitment`, `trade-letter-of-credit`, `unconditionally-cancellable`.
- Golden: CRE20.94 to CRE20.101: 1.0 for the first four, 0.5 for `nif-ruf` and `transaction-related-contingent`, 0.4 for `commitment`, 0.2 for `trade-letter-of-credit`, 0.1 for `unconditionally-cancellable` (the `value` field carries the factor).

### `riskvalidation.regulatory.standardised.defaulted_risk_weight`

```python
def defaulted_risk_weight(specific_provision_share: float, residential_non_cash_flow_dependent: bool = False) -> RegulatoryParameter: ...
```

- Units: `specific_provision_share` the specific provisions over the outstanding amount, a decimal.
- Golden: CRE20.104 to CRE20.107: 1.5 when the share is below 0.2, 1.0 when it is at least 0.2; defaulted residential real estate that is not cash-flow dependent 1.0.

### `riskvalidation.regulatory.standardised.lookup`

```python
def lookup(exposure_class: str, key: str, **options) -> RegulatoryParameter: ...
```

- Units: `exposure_class` one of `sovereign`, `eca`, `bank-ecra`, `bank-scra`, `corporate`, `retail`, `equity`, `residential-re`, `commercial-re`, `defaulted`, `ccf`, `currency-mismatch`; `key` the rating bucket, grade, kind or the LTV as a string of the number (an ECA score as a string of the integer; for `ccf` the kind; for `currency-mismatch` `multiplier` or `cap`); the options `short_term`, `cash_flow_dependent` and `counterparty_weight` are those of the functions above.
- Invariants: dispatches to the functions above and returns exactly their `RegulatoryParameter`; every cell of the `cre20_grid` of `regulatory-calculators` is keyed as `lookup(exposure_class, key, short_term, cash_flow_dependent, counterparty_weight)` and equals it (the grid is generated by the engine, the document test and `check_regulatory` compare them); an unknown class or key raises `ValueError`.

## Module `riskvalidation/regulatory/output_floor.py`

### `riskvalidation.regulatory.output_floor.phase_in_factor`

```python
def phase_in_factor(year: int) -> RegulatoryParameter: ...
```

- Units: `year` a calendar year; the factor a decimal.
- Golden: RBC90.1 Table 1: 2023 gives 0.50, 2024 0.55, 2025 0.60, 2026 0.65, 2027 0.70, 2028 and later 0.725; a year before 2023 raises `ValueError`. These are the BCBS dates; jurisdictional dates differ (dossier 01 L) and are the caller's factor.

### `riskvalidation.regulatory.output_floor.floored_rwa`

```python
def floored_rwa(rwa_nominated: float, rwa_sa_only: float, factor: float, cap_share: float | None = None) -> float: ...
```

- Units: RWA in one currency or index points; `factor` a decimal; `cap_share` the RBC90.2 cap of the increase as a share of the pre-floor RWA (0.25), or `None`.
- Golden: RBC20.13 Table 1 (dossier 01 C.1, M.1): `floored_rwa(76, 140, 0.725)` = 101.5 and `floored_rwa(76, 140, 0.725, cap_share=0.25)` = 95 (exact: 140 x 0.725 = 101.5; 76 x 1.25 = 95). Invariants: the result is `max(rwa_nominated, factor x rwa_sa_only)` without the cap, and the `min` of that and `rwa_nominated x (1 + cap_share)` with it; it is never below `rwa_nominated`; the floor base takes standardised approaches only (RBC20.11 to RBC20.12), which is the caller's `rwa_sa_only`.

## Module `riskvalidation/regulatory/sa_ccr.py`

SA-CCR (CRE52, dossier 01 E.2). The supervisory parameters of CRE52.72 Table 2 are module data (IR factor 0.5 percent, option volatility
50 percent; FX 4.0 percent, 15 percent; credit single name AAA 0.38, AA 0.38, A 0.42, BBB 0.54, BB 1.06, B 1.6, CCC 6.0 percent with
correlation 50 percent; credit index IG 0.38 and SG 1.06 percent with correlation 80 percent; equity single name 32 percent (50 percent),
index 20 percent (80 percent); commodity electricity 40 percent (40 percent), oil and gas, metals, agricultural, other 18 percent (40
percent)).

### `riskvalidation.regulatory.sa_ccr.supervisory_duration`

```python
def supervisory_duration(start: float, end: float) -> float: ...
```

- Units: `start` and `end` in years, `0 <= start < end`; the result in years.
- Golden: CRE52.34 `(exp(-0.05 S) - exp(-0.05 E)) / 0.05`: `(0, 5)` gives 4.423984, `(0, 1)` gives 0.975412, `(1, 5)` gives 3.448573 (recomputed from the formula, tolerance 5e-7). Invariants: additive over adjacent intervals (`sd(0, 1) + sd(1, 5) = sd(0, 5)` to 1e-12); `start` is floored at 0 by the caller (a started trade has `S = 0`).

### `riskvalidation.regulatory.sa_ccr.supervisory_delta_option`

```python
def supervisory_delta_option(price: float, strike: float, vol: float, expiry: float, is_call: bool, is_long: bool) -> float: ...
```

- Units: `price`, `strike` in one unit, `vol` a decimal, `expiry` in years; the delta unitless.
- Invariants: CRE52.38 to CRE52.41 `+-Phi(+-(ln(P/K) + 0.5 vol^2 T) / (vol sqrt(T)))` by bought or sold call or put (dossier 01 E.2); a bought call lies in (0, 1), a sold call in (-1, 0), a bought put in (-1, 0), a sold put in (0, 1); the bought call delta minus the bought put delta is 1 (put-call parity of the deltas); the CRE99 netting set 1 swaption delta is -0.2694 (golden, dossier 01 E.2; the swaption inputs are read from CRE99 by U9-E1 and reported if unreadable).

### `riskvalidation.regulatory.sa_ccr.supervisory_delta_tranche`

```python
def supervisory_delta_tranche(attachment: float, detachment: float, is_long: bool) -> float: ...
```

- Units: `attachment` and `detachment` decimals with `0 <= A < D <= 1`.
- Golden: CRE52.41 `+-15 / ((1 + 14 A) (1 + 14 D))`: `A = 0`, `D = 1` gives 1 (long); `A = 0`, `D = 0.1` gives 15 / (1 x 2.4) = 6.25 (recomputed). Short is the negative.

### `riskvalidation.regulatory.sa_ccr.maturity_factor`

```python
def maturity_factor(maturity_years: float, mpor_business_days: int | None = None) -> float: ...
```

- Units: `maturity_years` in years; `mpor_business_days` the margin period of risk in business days (250 to the year), `None` for an unmargined netting set.
- Golden: CRE52.48 unmargined `sqrt(min(M, 1))`: `M = 0.25` gives 0.5, `M = 5` gives 1. CRE52.52 margined `1.5 sqrt(MPOR / 250)`: 14 business days gives 0.354965 (the CRE99 netting set 5 value `1.5 sqrt(14/250)`), 10 gives 0.3. Invariants: monotone in `M` (unmargined) and in MPoR (margined); the MPoR floor of 10 business days (CRE52.50) is the caller's, the function does not raise it.

### `riskvalidation.regulatory.sa_ccr.maturity_bucket`

```python
def maturity_bucket(end_years: float) -> str: ...
```

- Units: `end_years` the end date of the trade in years.
- Golden: CRE52.57: `B1` below 1 year, `B2` from 1 to 5 years inclusive, `B3` above 5: 0.5 gives `B1`, 1 and 5 give `B2`, 5.01 gives `B3`.

### `riskvalidation.regulatory.sa_ccr.ir_effective_notional`

```python
def ir_effective_notional(d_b1: float, d_b2: float, d_b3: float, offset: bool = True) -> float: ...
```

- Units: the three bucket effective notionals in one currency.
- Golden: CRE52.57: offset `sqrt(D1^2 + D2^2 + D3^2 + 1.4 D1 D2 + 1.4 D2 D3 + 0.6 D1 D3)`, no offset `|D1| + |D2| + |D3|`: `(100, 0, 0)` gives 100; `(100, -100, 0)` gives `sqrt(10000 + 10000 - 14000)` = 77.459667; `(100, 100, 0)` with no offset gives 200. Invariant: the offset value is at most the no-offset value for any inputs. The CRE99 netting set 1 values EN_USD 59,270 and EN_EUR 10,083 give AddOn 296.35 and 50.415 at the 0.5 percent factor (dossier 01 E.2).

### `riskvalidation.regulatory.sa_ccr.ir_addon`

```python
def ir_addon(trades: list[IrTrade], mpor_business_days: int | None = None, offset: bool = True) -> IrAddOn: ...
```

- Units: `IrTrade(hedging_set, start, end, notional, delta)` with times in years and money in the hedging set's currency; the result carries per trade the duration, adjusted notional, maturity factor, bucket and effective notional, per hedging set `d_b1`, `d_b2`, `d_b3`, `effective_notional` and `addon = 0.005 x EN`, and the sum over hedging sets.
- Invariants: every intermediate of the `sa_ccr` block of `c12-outputs` is a field of the result (the live port is checked step by step); the add-on of a hedging set is 0.005 times its effective notional; a payer swap has delta +1 and a receiver -1 (the receiver's effective notional is negative); two opposite swaps of equal terms net to add-on 0; trades of two currencies sum their hedging-set add-ons (CRE52.57).

### `riskvalidation.regulatory.sa_ccr.fx_addon`

```python
def fx_addon(hedging_sets: dict[str, float]) -> float: ...
```

- Units: per currency pair the signed effective notional in the reporting currency; the add-on in the same currency.
- Invariants: CRE52.59: `sum over pairs of 0.04 |EN_pair|`; a pair with EN 0 contributes 0; scaling every EN by k scales the result by k.

### `riskvalidation.regulatory.sa_ccr.entity_aggregate`

```python
def entity_aggregate(addons: list[float], rhos: list[float]) -> float: ...
```

- Units: `addons` the entity add-ons `SF x EN_e`, `rhos` the correlation of each entity (one per add-on, the same length; a different length raises `ValueError`). The correlation is per entity because CRE52.61 aggregates single names (0.5) and indices (0.8) in one formula, as `CommodityEntity(sf, rho, effective_notional)` already does.
- Invariants: CRE52.61, CRE52.66, CRE52.70 `sqrt((sum rho_e A_e)^2 + sum (1 - rho_e^2) A_e^2)`: one entity returns its own add-on for any `rho`; every `rho = 1` returns `|sum A_e|`; every `rho = 0` returns `sqrt(sum A_e^2)`.
- Golden: the CRE99 netting set 2 (CRE99.54): add-ons `106, -280, 168` (unrounded `105.86194, -279.91632, 168.11140`) with correlations `0.5, 0.5, 0.8` give the systematic term `(sum rho A)^2 = 2,252.635` (printed 2,253), the idiosyncratic term `sum (1 - rho^2) A^2 = 77,344.043` (printed 77,344) and `AddOn_credit = 282.128832` (printed 282), recomputed from the trade inputs.

### `riskvalidation.regulatory.sa_ccr.entity_aggregate_terms` (added in 2.1.0)

```python
@dataclass(frozen=True)
class AddonTerms: systematic: float; idiosyncratic: float; addon: float
def entity_aggregate_terms(addons: list[float], rhos: list[float]) -> AddonTerms: ...
```

- Units: as `entity_aggregate`; `systematic` and `idiosyncratic` in money squared, `addon` in money.
- Invariants: `systematic = (sum rho_e A_e)^2`, `idiosyncratic = sum (1 - rho_e^2) A_e^2`, `addon = sqrt(systematic + idiosyncratic) = entity_aggregate(addons, rhos)`; the refusals of `entity_aggregate`.
- Golden: the CRE99 netting set 2 terms of `entity_aggregate` (2,252.635, 77,344.043, 282.128832).

### `riskvalidation.regulatory.sa_ccr.credit_addon`

```python
def credit_addon(entities: list[CreditEntity]) -> float: ...
```

- Units: `CreditEntity(rating, is_index, effective_notional)` in one currency.
- Invariants: CRE52.61 to CRE52.65 with the CRE52.72 factors and correlations (50 percent single name, 80 percent index): equals `entity_aggregate(addons, rhos)` of the entity add-ons `SF x EN` with `rhos` 0.5 for a single name and 0.8 for an index; the CRE99 netting set 2 add-on is 282.128832 (printed 282; dossier 01 E.2, CRE99.54).

### `riskvalidation.regulatory.sa_ccr.credit_addon_terms` (added in 2.1.0)

```python
def credit_addon_terms(entities: list[CreditEntity]) -> AddonTerms: ...
```

- Units: as `credit_addon`.
- Invariants: `entity_aggregate_terms` of the entity add-ons `SF x EN` with `rhos` 0.5 and 0.8 (CRE52.61 to CRE52.65); `addon == credit_addon(entities)`.
- Golden: the CRE99 netting set 2 (CRE99.54): systematic 2,252.635, idiosyncratic 77,344.043, add-on 282.128832.

### `riskvalidation.regulatory.sa_ccr.equity_addon`

```python
def equity_addon(entities: list[EquityEntity]) -> float: ...
```

- Units: `EquityEntity(is_index, effective_notional)`.
- Invariants: CRE52.66 to CRE52.69: factors 32 percent single name and 20 percent index, correlations 50 and 80 percent; equals `entity_aggregate` of the entity add-ons.

### `riskvalidation.regulatory.sa_ccr.equity_addon_terms` (added in 2.1.0)

```python
def equity_addon_terms(entities: list[EquityEntity]) -> AddonTerms: ...
```

- Units: as `equity_addon`.
- Invariants: `entity_aggregate_terms` of the entity add-ons with the CRE52.66 to CRE52.69 factors and correlations; `addon == equity_addon(entities)`.

### `riskvalidation.regulatory.sa_ccr.commodity_addon`

```python
def commodity_addon(hedging_sets: dict[str, list[CommodityEntity]]) -> float: ...
```

- Units: per hedging set (energy, metals, agricultural, other) the entities `CommodityEntity(sf, rho, effective_notional)`.
- Golden: CRE52.70: the sum over hedging sets of `entity_aggregate`; the CRE99 netting set 3 add-ons are 2,041 (energy) and 1,800 (metals), 3,841 in total (dossier 01 E.2).

### `riskvalidation.regulatory.sa_ccr.replacement_cost`

```python
def replacement_cost(v: float, c: float, th: float = 0.0, mta: float = 0.0, nica: float = 0.0, margined: bool = False) -> float: ...
```

- Units: money in one currency: `v` the netting set value, `c` the net collateral, `th` the threshold, `mta` the minimum transfer amount, `nica` the net independent collateral amount.
- Golden: CRE52.10 unmargined `max(V - C, 0)`; CRE52.18 margined `max(V - C, TH + MTA - NICA, 0)`: CRE99 netting set 1 `V - C = 30 - 20 + 50 = 60` gives RC 60; netting set 5 `max(80 - 200, 0 + 5 - 150, 0)` gives 0; netting set 3 gives 20 and set 4 gives 40 (dossier 01 E.2).

### `riskvalidation.regulatory.sa_ccr.multiplier`

```python
def multiplier(v_minus_c: float, addon_aggregate: float, floor: float = 0.05) -> float: ...
```

- Units: `v_minus_c` and `addon_aggregate` in one currency; the multiplier unitless in `[floor, 1]`.
- Golden: CRE52.23 `min(1, floor + (1 - floor) exp((V - C) / (2 (1 - floor) AddOn)))`: `(-20, 282.128832)` gives 0.965208 (6 decimals, recomputed with the unrounded add-on; printed 0.965); `(-120, 1400.96238)` gives 0.958123 (printed 0.958, tolerance 5e-4); `V - C >= 0` gives 1. Invariants: monotone increasing in `V - C`; tends to the floor as `V - C` tends to minus infinity; an add-on of 0 returns 1.

### `riskvalidation.regulatory.sa_ccr.netting_set_ead`

```python
def netting_set_ead(v: float, c: float, addon_by_class: AddOnByClass, margined: bool = False, th: float = 0.0, mta: float = 0.0, nica: float = 0.0, alpha: float = 1.4) -> SaCcrResult: ...
```

- Units: money in one currency; `AddOnByClass(interest_rate, fx, credit, equity, commodity)`.
- Golden: CRE52.1 `EAD = 1.4 (RC + multiplier x AddOn)` with the aggregate add-on the sum of the five classes (CRE52.24 to CRE52.25); the result carries `rc`, `addon_aggregate`, `multiplier`, `pfe`, `ead`. The five CRE99 values (USD thousands, dossier 01 E.2, M.3 item 2), exact after rounding on the trade-level path (the `trades` of the example in `regulatory-calculators`, intermediates unrounded): set 1 RC 60, AddOn 346.764386, multiplier 1 gives EAD 569.470141 (569); set 2 RC 0, AddOn 282.128832, multiplier 0.965208 gives 381.238319 (381); set 3 RC 20, AddOn 3,841.154273 gives 5,405.615982 (5,406); set 4 RC 40, AddOn 628.893218 gives 936.450506 (936; the printed rounded add-ons give 1.4 x 669 = 936.6, which the printed value 936 does not follow, so the golden uses the unrounded ones); set 5 RC 0, AddOn 1,400.962380, multiplier 0.958123 gives 1,879.212632 (1,879). `round(ead)` equals the published integer exactly on this path; the path from the printed intermediates (RC, multiplier and AddOn as printed) holds to one unit. Invariants: `ead = alpha (rc + pfe)`; alpha is 1.4 by default (CRE52.1).

## Module `riskvalidation/regulatory/ba_cva.py`

BA-CVA (MAR50.14 to MAR50.25, dossier 01 E.1). Table 1 of MAR50.16 (risk weights, investment grade then high yield or not rated):
sovereigns, central banks and MDBs 0.5 and 2.0 percent; local government and public 1.0 and 4.0; financials 5.0 and 12.0; basic materials,
energy, industrials, agriculture, manufacturing, mining 3.0 and 7.0; consumer goods and services, transport, administrative 3.0 and 8.5;
technology and telecoms 2.0 and 5.5; health care, utilities, professional 1.5 and 5.0; other 5.0 and 12.0. There is no verified official
numeric example (addendum R8): the tests rest on the invariants of dossier 01 M.1.

### `riskvalidation.regulatory.ba_cva.materiality_threshold_applies`

```python
def materiality_threshold_applies(aggregate_notional_eur: float) -> bool: ...
```

- Units: `aggregate_notional_eur` the aggregate non-centrally-cleared derivative notional in EUR.
- Golden: MAR50.9: true at or below EUR 100 billion (the bank may set CVA capital equal to 100 percent of CCR capital): 1e11 gives true, 1.0000001e11 gives false.

### `riskvalidation.regulatory.ba_cva.sector_risk_weight`

```python
def sector_risk_weight(sector: str, investment_grade: bool) -> RegulatoryParameter: ...
```

- Units: `sector` one of the eight MAR50.16 Table 1 sector labels of the `c12-outputs` schema.
- Golden: MAR50.16 Table 1: financials 0.05 investment grade and 0.12 high yield or not rated; sovereigns, central banks, MDBs 0.005 and 0.02; technology and telecoms 0.02 and 0.055 (dossier 01 E.1).

### `riskvalidation.regulatory.ba_cva.discount_factor`

```python
def discount_factor(m: float, imm_bank: bool = False) -> float: ...
```

- Units: `m` the effective maturity in years.
- Golden: MAR50.15 `(1 - exp(-0.05 M)) / (0.05 M)` (1 for an IMM bank): `M = 1` gives 0.975412, `M = 5` gives 0.884797 (recomputed).

### `riskvalidation.regulatory.ba_cva.scva`

```python
def scva(risk_weight: float, netting_sets: list[tuple[float, float]], imm_bank: bool = False, alpha: float = 1.4) -> float: ...
```

- Units: `netting_sets` a list of `(M in years, EAD in one currency)`.
- Invariants: MAR50.15 `(1 / alpha) RW sum_NS M EAD DF`: linear in the EAD and in the risk weight; an EAD of 0 gives 0; one netting set with `M = 5`, `EAD = 100`, `RW = 0.05` gives `0.05 x 5 x 100 x 0.884797 / 1.4` = 15.799944 (recomputed).

### `riskvalidation.regulatory.ba_cva.k_reduced`

```python
def k_reduced(scvas: list[float], rho: float = 0.5) -> float: ...
```

- Units: the SCVA per counterparty in one currency.
- Invariants: MAR50.14 `sqrt((rho sum SCVA)^2 + (1 - rho^2) sum SCVA^2)`: with `rho = 1` it equals the sum of the SCVA (dossier 01 M.1; the entry `ba-cva-rho-one` of `regulatory-calculators`: SCVA 10 and 20 give 30); one counterparty gives its own SCVA; at most the sum of the SCVA for `rho <= 1`.

### `riskvalidation.regulatory.ba_cva.k_hedged`

```python
def k_hedged(scva_minus_snh: list[float], ih: float, hma: list[float], rho: float = 0.5) -> float: ...
```

- Units: money in one currency: `scva_minus_snh` the per-counterparty `SCVA - SNH`, `ih` the index hedge, `hma` the hedging misalignment terms.
- Invariants: MAR50.21 to MAR50.25 `sqrt((rho sum (SCVA - SNH) - IH)^2 + (1 - rho^2) sum (SCVA - SNH)^2 + sum HMA)`; with no hedges (`SNH = 0`, `IH = 0`, `HMA = 0`) it equals `k_reduced`; the result is real (the radicand is never negative).

### `riskvalidation.regulatory.ba_cva.k_full`

```python
def k_full(k_reduced_value: float, k_hedged_value: float, beta: float = 0.25) -> float: ...
```

- Units: money in one currency.
- Golden: MAR50.20 `beta K_reduced + (1 - beta) K_hedged`: `(30, 0)` gives 7.5 (the entry `ba-cva-hedges-floor`); the result is at least `beta K_reduced` for `K_hedged >= 0` (hedges never take it below, dossier 01 M.1).

### `riskvalidation.regulatory.ba_cva.capital`

```python
def capital(k: float, ds: float = 0.65) -> float: ...
```

- Units: money in one currency.
- Golden: MAR50.14 and MAR50.20 `DS x K` with `DS = 0.65`: `capital(100)` = 65.

## Module `riskvalidation/regulatory/frtb.py`

The capital aggregation of the sensitivities-based method and the liquidity-horizon cascade (dossier 01 D.2 and D.3; addendum R7). The
existing `riskvalidation/market/frtb.py` holds the backtesting and PLA statistics; the two modules do not import each other.

### `riskvalidation.regulatory.frtb.girr_parameters`

```python
def girr_parameters(specified_currency: bool = True) -> GirrParameters: ...
```

- Units: tenors in years, risk weights decimals, correlations decimals.
- Golden: the addendum R7 values: tenors `0.25, 0.5, 1, 2, 3, 5, 10, 15, 20, 30` (MAR21.8), risk weights `1.7, 1.7, 1.6, 1.3, 1.2, 1.1, 1.1, 1.1, 1.1, 1.1` percent (MAR21.42 Table 1), the 10 by 10 correlation matrix of MAR21.46 Table 2 (for example 0.5 to 5 years 0.763, 2 to 3 years 0.985, 0.25 to 30 years 0.40), 0.999 for the same tenor on other curves (MAR21.45), `gamma = 0.5` (MAR21.50), curvature shock 0.017 (MAR21.99); with `specified_currency` the weights are divided by `sqrt(2)` (MAR21.44, the bank's discretion: 0.017 / sqrt(2) = 0.012021) and the field `sqrt2_applied` says so. A curvature consumer uses `curvature_shock_undivided` (0.017): MAR21.99 bases the curvature weight on "the highest prescribed delta risk weight" and MAR21.44's division names the delta weights of MAR21.42 to 43, so the divided 0.012021 is a derived reading, kept exposed and labelled (1.1.0, U9 decision H4). Invariant: the matrix is symmetric with a unit diagonal and every off-diagonal entry in `[0.40, 1)`; it equals `max(exp(-0.03 |Tk - Tl| / min(Tk, Tl)), 0.40)` to the printed 0.1 percent (a reconstructed check, the table is primary).

### `riskvalidation.regulatory.frtb.scenario_correlation`

```python
def scenario_correlation(rho: np.ndarray, scenario: str) -> np.ndarray: ...
```

- Units: `rho` any correlation array; `scenario` one of `low`, `medium`, `high`.
- Golden: MAR21.6: medium is `rho`; high `min(1.25 rho, 1)`; low `max(2 rho - 1, 0.75 rho)`: `rho = 0.5` gives 0.375, 0.5, 0.625; `rho = 0.8` gives low 0.6 and high 1.0; `rho = 1` gives 1 in every scenario (the diagonal is untouched by the caller).

### `riskvalidation.regulatory.frtb.bucket_charge`

```python
def bucket_charge(ws: np.ndarray, rho: np.ndarray, scenario: str = 'medium') -> float: ...
```

- Units: `ws` weighted sensitivities (money), `rho` the within-bucket correlations.
- Invariants: MAR21.4 `K_b = sqrt(max(0, sum WS_k^2 + sum_{k != l} rho_kl WS_k WS_l))` with `rho` of the scenario: one factor gives `|WS|`; perfectly correlated factors (`rho = 1` off the diagonal) give `|sum WS|`; the result is never negative even when the radicand is.

### `riskvalidation.regulatory.frtb.cross_bucket_charge`

```python
def cross_bucket_charge(k_b: np.ndarray, s_b: np.ndarray, gamma: np.ndarray, scenario: str = 'medium') -> float: ...
```

- Units: `k_b` the bucket charges, `s_b` the signed bucket sums `sum WS` (money), `gamma` the cross-bucket correlations.
- Invariants: MAR21.4 `sqrt(sum K_b^2 + sum_{b != c} gamma_bc S_b S_c)`; if the radicand is negative, `S_b` is replaced by `max(min(sum WS, K_b), -K_b)` and the sum recomputed (MAR21.4(5)(b)); one bucket gives its `K_b`; the result is never negative.
- Golden: the invariant cases `sbm-bucket-and-cross-bucket-aggregation` and `sbm-cross-bucket-fallback` of `regulatory-calculators` (the second: two buckets `WS = (10, 10)` and `(-10, -10)` with within-bucket rho 0.5 and gamma 0.8 give `K_b = 17.3205`, `S_b = +-20`, a negative radicand under the medium scenario, the fallback `S_b = +-17.3205` and the charge 10.9545).

### `riskvalidation.regulatory.frtb.cross_bucket_charge_detail` (added in 2.1.0)

```python
@dataclass(frozen=True)
class CrossBucket: charge: float; fallback_used: bool
def cross_bucket_charge_detail(k_b: np.ndarray, s_b: np.ndarray, gamma: np.ndarray, scenario: str = 'medium') -> CrossBucket: ...
```

- Units: as `cross_bucket_charge`.
- Invariants: `charge == cross_bucket_charge(k_b, s_b, gamma, scenario)`; `fallback_used` is true exactly when the radicand with the plain `S_b` is negative and the MAR21.4(5)(b) replacement applied; the refusals of `cross_bucket_charge`.
- Golden: the case `sbm-cross-bucket-fallback` gives charge 10.9545 with `fallback_used` true; `sbm-bucket-and-cross-bucket-aggregation` gives `fallback_used` false.

### `riskvalidation.regulatory.frtb.girr_delta_charge`

```python
def girr_delta_charge(sensitivities: np.ndarray, tenors: np.ndarray, params: GirrParameters) -> SbmResult: ...
```

- Units: `sensitivities` (10,) `s_k = (V(r + 0.0001) - V(r)) / 0.0001` at each GIRR tenor in one currency: the change in value for a 1 basis point shift DIVIDED BY 0.0001, as MAR21.19 defines it (dossier 01 D.2, addendum R7), not the PV01 per basis point; one bucket (a single currency). A PV01 of 4,500 USD per basis point is `s_k = 4.5e7` USD per unit of rate.
- Invariants: the weighted sensitivities `RW_k s_k` (divided by `sqrt(2)` for a specified currency), the bucket charge under each of the three scenarios and `charge = max` over them (MAR21.6 to MAR21.7); the result is a `SbmResult(weighted, k_by_scenario, charge)`; the charge with the `sqrt(2)`-divided weights is `1 / sqrt(2)` times the undivided charge (the weights scale uniformly); a zero sensitivity vector gives 0; the `girr.scenarios` of `c12-outputs` are `k_by_scenario` in the order low, medium, high.
- Golden: a 10 million USD 10-year payer swap with `s = 8.0e7` at the 10-year tenor and no other sensitivity gives `WS = 0.011 x 8.0e7 / sqrt(2) = 622,253.97` and a charge of the same size (one factor gives `|WS|` under every scenario); the `girr` block of the C12 fixtures carries the four swaps of the book.

### `riskvalidation.regulatory.frtb.curvature_charge`

```python
def curvature_charge(cvr_plus: np.ndarray, cvr_minus: np.ndarray, rho: np.ndarray, gamma: np.ndarray, scenario: str = 'medium') -> float: ...
```

- Units: `cvr_plus` and `cvr_minus` (B, K) curvature risk positions per bucket and factor (money).
- Invariants: MAR21.5 with `psi(x, y) = 0` if both are negative and 1 otherwise, `K_b = max(K_b+, K_b-)`, the within-bucket correlations the squares of the delta ones (MAR21.100) and the cross-bucket ones too: `gamma` is the DELTA cross-bucket correlation and the function squares it (MAR21.101, transcribed verbatim in the engine's `docs/regulatory/u9/05_frtb-sbm-and-cascade.md`; 1.1.0, U9 decision H2), so a caller never passes it squared; when `K_b+ = K_b-` the upward scenario is selected if and only if the sum of `CVR+` exceeds the sum of `CVR-` (MAR21.5(3)(a)(iii); 1.1.0, U9 decision H3); `S_b` is the sum of the CVR of the scenario that selected `K_b`; all-negative CVR give 0; the result is never negative. The GIRR curvature shock is 0.017 (MAR21.99).

### `riskvalidation.regulatory.frtb.sbm_capital`

```python
def sbm_capital(delta: dict[str, float], vega: dict[str, float], curvature: dict[str, float]) -> SbmCapital: ...
```

- Units: each dict maps a scenario `low`, `medium`, `high` to the sum over risk classes of that measure, in one currency.
- Invariants: MAR21.7: the SBM requirement is the maximum over the three scenarios of `delta + vega + curvature`; with one non-zero scenario it returns that scenario; it is at least every scenario's sum.

### `riskvalidation.regulatory.frtb.liquidity_cascade_es`

```python
def liquidity_cascade_es(es_t_full: float, es_t_by_horizon: dict[int, float], base_horizon: int = 10) -> float: ...
```

- Units: ES in one currency; `es_t_by_horizon` maps each liquidity horizon `LH_j` in days (10, 20, 40, 60, 120) to `ES_T(P, j)`, the ES shocking only the factors with horizon at least `LH_j`.
- Golden: MAR33.4 `sqrt(ES_T(P)^2 + sum_{j >= 2} (ES_T(P, j) sqrt((LH_j - LH_{j-1}) / T))^2)` with `T = 10`, the horizons of MAR33.4 Table 1 (10, 20, 40, 60, 120): with every factor at `LH = 10` the result equals `ES_T(P)` (entry `cascade-all-lh-ten`: 10 gives 10); `ES_T(P) = 10`, `ES_T(P, 2) = 6` with the other horizons empty gives `sqrt(100 + 36 x 1)` = 11.661904 (recomputed). Invariants: monotone in each `ES_T(P, j)`; at least `ES_T(P)`; the liquidity horizon of a risk factor class is module data from MAR33.12 Table 2 (dossier 01 D.3).

## Producer checks a bake calls

The product's `tests/contracts_u9/semantics.py` recomputes from a document the SA-CCR intermediates from the trade inputs (and, in the
regulatory document, the five CRE99 netting sets from their trades, exact after rounding), BA-CVA from SCVA and the GIRR weighted
sensitivities, the bucket charge of each scenario from the Table 2 matrix and the charge as the maximum over the three scenarios. A bake
calls `check_c12` and `check_regulatory` on every document it writes; a non-empty list is a refusal to publish. A checker returns a
message, never an exception, on a document the schema would refuse.

## UNVERIFIED and open items

- The CRE99 trade inputs are transcribed from the BIS page (CRE99.20 to CRE99.97, in force 2023-01-01, fetched 2026-10-19) into the
  `trades` of the five examples of `regulatory-calculators`; the equations of the page are images and are not transcribed, the formulas are
  those of CRE52 and recompute every printed intermediate and the five EADs exactly after rounding. The swaption inputs (price 6 percent,
  strike 5 percent, volatility 50 percent, expiry 1 year) give the delta -0.2693952 (printed -0.2694).
- BA-CVA full (MAR50.20 to MAR50.25): no official numeric example (addendum R8, RBI draft Annex I is backlog BL-080).
- GIRR: the footnote 13 formula of MAR21.46 is reconstructed (`max(exp(-0.03 |Tk - Tl| / min(Tk, Tl)), 40%)`) and matches all 100 entries of
  Table 2; the table is the primary value. The vega risk-weight formula (footnote 24) is not transcribed (a swap book has no vega).
- MAR21.101 (curvature cross-bucket aggregation) was not read in the addendum; the U9-E1 fix round transcribed it and MAR21.5(3)(a)(iii) from the BIS page (in force 2023-01-01), and `curvature_charge` follows both (1.1.0).
- CRE20 version in force 2028-01-01 (published 2025-06-10) is not compared.
- SA-CVA, DRC and RRAO are out of scope (sizing decision D1).
- Curvature across buckets (S4, main session 2026-10-19): `curvature_charge` follows dossier 01 D.2 (MAR21.5, the psi rule). C12 is a
  single-currency USD book with one GIRR bucket, so the cross-bucket step of MAR21.101 does not bind; from 1.1.0 the engine
  applies it (gamma squared) for a multi-currency book.
- The row of MAR33.12 Table 2 "commodity volatility, 60 or 120 days" is ambiguous in dossier 01 D.3 and is not transcribed into the parameter
  table of the document.
