# Engine liquidity API contract: `engine-liquidity-api` 1.0.0

Owner: U11-S (unit sizing `plans/contraste/units/U11-sizing.md`, CAOS_MANAGE). Implemented by U11-E in `riskvalidation.liquidity`,
`riskvalidation.regulatory.lcr_nsfr` and `riskvalidation.validation.liquidity` (repository CAOS_RiskValidation); called by the C16 bake
(U11-P). The tests of every function are written by U11-E against this file: a function exists with exactly the signature below, and each
golden value or invariant is a test. Changing a signature, a unit or a golden value is a breaking change (a new major version of this
contract). Sources: dossier 05 (`wip/contraste/05-market-ccr-alm-liquidity-oprisk-stress-sota-2026-10-04.md`, section E.1 to E.5 and
line 480), dossier 01 (`wip/contraste/01-basel-pillar1-pillar2-framework-2026-10-04.md`, section G.1 to G.3 and M.1), dossier 08
(`wip/contraste/08-data-and-scenario-sources-2026-10-04.md`, E.2, E.3, G.2, G.4), the U11 research addendum
(`wip/contraste/u11-research-addendum-2026-10-18.md`, L1 the ECB LiST 2019 tables, L2 the notices, L3 the FDIC fields, L4 the
Federal Reserve margins) and the sizing decisions Q1 to Q14 and A1 to A6. The case documents this contract feeds are `c16-outputs`,
`c16-outputs-reverse` and `c16-models` (`docs/contracts/schemas/c16/`).

The engine computes; it states no compliance claim. The LCR is a Basel formula applied to call-report aggregates with stated
assumptions and is never presented as the bank's reported or regulatory LCR (01 M.4; 05 lines 513 to 522). Every constant and table below
is transcribed from the dossier or the addendum named on its line; an item they mark UNVERIFIED, or that this contract reads in a way they
do not settle, is marked UNVERIFIED here and is not silently decided (list at the end). No official LCR or NSFR worked example exists
(01 lines 1045 to 1046), so none is claimed: the LCR and NSFR carry constructed tests and invariants (01 M.1).

Version history: 1.0.0, the first contract.

## Conventions (all functions)

- Arrays are `numpy.ndarray` of `float64` (integers `int64`, flags `bool`). Shapes: `S` deposit segments, `H` ladder days, `K` classes.
- **Money** is a float in USD thousands as the FDIC call report gives it (the currency and the scale travel in the document, never in a
  function); the engine never converts. **Rates** are decimals per relevant day; **shares** are decimals in `[0, 1]`; **horizons** and
  **days** are integers counted from 1 (day 1 is the first relevant day after the valuation date); a day grid is strictly increasing.
- Every function is pure and deterministic (no hidden state, no I/O, inputs never mutated); a function with randomness takes a `seed` or
  an `rng` (`numpy.random.default_rng`). Dataclasses are frozen. A function that cannot compute because data is missing or out of range
  raises `ValueError` naming the offending field and the reason (the checks of `_checks.py`), or (a validation function) returns the
  `not_evaluated` light with the reason in `notes` and `statistic`, `p_value` and `metric` all null; it never returns a placeholder number.
- A balance that never turns the net liquidity position negative has **no** survival day: `survival_period` returns "survives the
  horizon" with the horizon (`SurvivalResult.survives` true, `day` `None`), never a number.
- Tolerance: every golden value states its own tolerance or is exact; a golden stated to six decimals holds to `5e-7`.
- A validation function returns one `TestResult` of `riskvalidation` (`common/test-result`, the schema
  `docs/contracts/schemas/common/test-result.schema.json`): `test_id`, `model_id`, `segment`, `statistic`, `p_value`, `metric`, `h0`,
  `alternative`, `policy_version` (`contraste-liquidity-battery-1.0.0`), `alpha_amber`, `alpha_red`, `light`, `n`, `n_events`,
  `inputs_hash`, `reference`, `notes`, `extras`. The thresholds of a light rule travel in `extras["thresholds"]`; they are conventions
  (the named parameters of the case documents, Q14) and never regulatory thresholds. The ids are `liq.<function name>`.
- Missing data: a call-report item the source lacks is the caller's nullable value with its reason (the document schema), never a number
  the engine invents; a LiST class the caller does not map is refused (`compose_scenario`); collateral calls have no numeric LiST
  parameter and are a scenario input the caller supplies (A1).

## How the documents use the engine

| Document block (schema) | Produced by |
|---|---|
| `outputs.path.ladder.segments`, `daily_rates`, `cumulative_outflow_share`, `outflows` | `runoff.cumulative_outflow_path`, `contractual_rolloff`, `financial_no_rollover`, `ladder.behavioural_outflows` |
| `outputs.cbc.classes`, `haircut`, `liquidity_value`, `pledged`; `path.ladder.cbc_stack` | `cbc.haircut_rule`, `liquidity_value`, `cbc_stack`, `monetisation_capacity` |
| `outputs.path` (`nlp`, `survival`, `minimum_nlp`, `cliff`) | `ladder.net_liquidity_position`, `survival_period`, `minimum_nlp`, `cliff_effect` |
| `outputs.contractual_ladder` | `ladder.contractual_gaps` |
| `outputs.lcr` | `regulatory.lcr_nsfr.hqla_stock`, `lcr_outflows`, `lcr_inflows`, `net_cash_outflows`, `lcr_ratio` |
| `outputs.htm` | `cbc.cbc_with_htm_loss`; the revaluation row calls `riskvalidation.irrbb` (`engine-irrbb-api`, decision Q11) |
| `outputs.scoring.svb_anchor`, `models.calibration` | `runoff.daily_rate_from_cumulative`, `scenarios.anchor_from_observation`, `scenarios.fast_run_scenario` |
| `models.list_parameters`, `table_a1` | `runoff.LIST_PARAMETERS`, `runoff.TABLE_A1` (module data, below) |
| `models.generator` | `deposits.DepositorGenerator` (`config`, `truth`, `verify`) |
| reverse document `bases` | `reverse.survival_vs_multiplier`, `reverse.solve_multiplier` |
| sensitivities (uninsured share, HTM loss) | `scenarios.uninsured_share_grid`, `htm_loss_grid` |
| `tests` | `riskvalidation.validation.liquidity.*` (rows of `common/test-result`) |

## Tables as data

The engine carries these as module data with their source; the product documents repeat them in `c16-models`, and a test compares the two.

### LiST 2019 parameters (`runoff.LIST_PARAMETERS`)

Transcribed from the ECB methodological note (addendum L1, read 2026-10-18; paragraph numbers are the note's): Table 3.2 contractual
roll-off rates applied to each flow when it matures (para 94), Table 3.3 open-maturity daily compounding rates applied to the stock of the
day before on relevant days only (para 107), the committed-facility drawdown rates for the first three months (para 121) and the 125 and 63
relevant days. The note's relevant days are the 2019 TARGET2 calendar; the C16 ladder runs on a stated US business-day convention, so every
LiST cumulative figure says which calendar it is on (A2). The cumulative figures below are recomputed here (`1 - (1 - q)^n`), not printed
as formulas in the note.

| class | Baseline | Adverse | Extreme |
|---|---|---|---|
| open repos | 1.0 | 1.0 | 1.0 |
| stable retail sight deposits | 0.0 | 0.00103258 | 0.00161494 |
| other retail sight deposits | 0.0 | 0.00373218 | 0.00440873 |
| operational sight deposits | 0.0 | 0.00514464 | 0.00750509 |
| non-operational, credit institutions | 1.0 | 1.0 | 1.0 |
| non-operational, other financial customers | 1.0 | 1.0 | 1.0 |
| non-operational, non-financial corporates | 0.0 | 0.00688541 | 0.01065229 |
| non-operational, others | 0.0 | 0.00688541 | 0.01065229 |
| other transactions | 1.0 | 1.0 | 1.0 |

Contractual roll-off (Table 3.2): stable retail 0, 0.18, 0.27; other retail 0, 0.39, 0.48; operational 0, 0.37, 0.50; non-operational
non-financial corporates and others 0, 0.52, 0.76; credit institutions, other financial customers, securities issued, secured funding,
FX swaps, derivatives and other cash outflows 1.0 in all three; the inflow rates are 1.0 for secured lending, loans to credit institutions
and other financial customers, FX swaps, derivatives, own paper and other inflows, and 0 for loans to retail, non-financial corporates
and others. Drawdown (daily, three months): committed credit facilities 0.00202704 Adverse and 0.00257634 Extreme; liquidity facilities
0.01443904 and 0.02176434. Cumulated after 125 relevant days (recomputed): stable retail 0.121148 and 0.182930, other retail 0.373368 and
0.424381, operational 0.475201 and 0.610026, non-operational non-financial corporates and others 0.578381 and 0.737808; after 63 relevant
days the facilities reach 0.12 and 0.15 (credit) and 0.60 and 0.75 (liquidity).

### Table A.1 (`runoff.TABLE_A1`)

BCBS, Report on the 2023 banking turmoil (d555), Box A, Table A.1 (addendum L2.1; dossier 05 E.2 lines 248 to 259). Footnote (a): First
Republic's outflow excludes 30 bn USD of deposits placed by banks in Q1 2023; SVB's includes the expected outflow of management for 10
March. The daily rate each row implies, `1 - (1 - share)^(1 / days)`, is recomputed here, not a dossier value.

| row id | bank | year | outflow share | days | implied daily rate (recomputed) |
|---|---|---|---|---|---|
| svb-2023 | SVB | 2023 | 0.85 | 2 | 0.612702 |
| first-republic-2023 | First Republic | 2023 | 0.57 | 90 | 0.009334 |
| svb-uk-2023 | SVB UK | 2023 | 0.30 | 1 | 0.300000 |
| credit-suisse-2023 | Credit Suisse | 2023 | 0.21 | 90 | 0.002616 |
| signature-2023 | Signature | 2023 | 0.20 | 1 | 0.200000 |
| icesave-2008 | Icesave | 2008 | 0.20 | 75 | 0.002971 |
| northern-rock-2007 | Northern Rock | 2007 | 0.20 | 4 | 0.054258 |
| wamu-2008 | WaMu | 2008 | 0.10 | 10 | 0.010481 |
| indymac-2008 | IndyMac | 2008 | 0.08 | 14 | 0.005938 |

The tenth row, "LCR deposit outflow rates, 3% to 40% over 30 days", is data here as `TABLE_A1_LCR_RANGE = (0.03, 0.40, 30)`; the LCR rate table
itself belongs to `lcr_nsfr.py`, below, and is not copied into `runoff.py`. The segments of 05 E.5 line 276 are `SEGMENTS = ("retail-insured",
"retail-uninsured", "operational", "non-operational-corporate", "financial")`.

### LCR parameters (`lcr_nsfr.LCR_OUTFLOW_RATES`, `LCR_INFLOW_RATES`, `HQLA_HAIRCUTS`)

BCBS Basel Framework LCR20 (published 2022-12-08), LCR30 (2020-06-05), LCR40 (2023-03-30), LCR99 (2019-12-15), all in force 2019-12-15,
transcribed from dossier 01 G.1 (every parameter carries its paragraph and in-force date in the module; 01 M.3 item 8). The BIS notice
that covers the framework pages is the one read at addendum L2.1 (a reading, not legal advice); the text is never reproduced, only the
parameters. Key outflow rates (LCR99 summary table), as `key | rate | reference`:

| key | rate | reference |
|---|---|---|
| retail_stable_insurance_criteria | 0.03 | LCR99 retail stable deposits, deposit insurance scheme meets additional criteria |
| retail_stable | 0.05 | LCR99 retail stable deposits |
| retail_less_stable | 0.10 | LCR99 retail less stable deposits |
| retail_term_gt_30d | 0.00 | LCR99 retail term deposits with residual maturity over 30 days |
| small_business_stable | 0.05 | LCR99 small business stable |
| small_business_less_stable | 0.10 | LCR99 small business less stable |
| operational | 0.25 | LCR99 operational deposits (insured portion 0.05) |
| operational_insured_portion | 0.05 | LCR99 operational deposits, insured portion |
| cooperative_network | 0.25 | LCR99 cooperative network qualifying deposits |
| non_financial_corporate | 0.40 | LCR99 non-financial corporates, sovereigns, central banks, MDBs, PSEs |
| non_financial_corporate_fully_insured | 0.20 | LCR99 the same when fully insured |
| other_legal_entity | 1.00 | LCR99 other legal entity customers (for example financial institutions) |
| secured_central_bank | 0.00 | LCR40 secured funding with a central bank |
| secured_level1 | 0.00 | LCR40 secured funding backed by Level 1 |
| secured_level2a | 0.15 | LCR40 secured funding backed by Level 2A |
| secured_sovereign_mdb_pse | 0.25 | LCR40 backed by non-L1, non-L2A assets, domestic sovereign, MDB or PSE counterparty |
| secured_level2b_rmbs | 0.25 | LCR40 backed by eligible Level 2B RMBS |
| secured_other_level2b | 0.50 | LCR40 backed by other Level 2B |
| secured_other | 1.00 | LCR40 all other secured funding |
| non_level1_collateral_valuation | 0.20 | LCR99 valuation changes on non-Level-1 posted collateral |
| undrawn_retail_small_business | 0.05 | LCR99 undrawn committed facilities, retail and small business |
| undrawn_credit_non_financial_corporate | 0.10 | LCR99 undrawn credit facilities, non-financial corporates, sovereigns, MDBs, PSEs |
| undrawn_liquidity_non_financial_corporate | 0.30 | LCR99 undrawn liquidity facilities, the same counterparties |
| undrawn_credit_supervised_bank | 0.40 | LCR99 undrawn facilities, supervised banks |
| undrawn_liquidity_supervised_bank | 0.40 | LCR99 undrawn facilities, supervised banks |
| undrawn_credit_other_fi | 0.40 | LCR99 undrawn credit facilities, other financial institutions |
| undrawn_liquidity_other_fi | 1.00 | LCR99 undrawn liquidity facilities, other financial institutions |
| undrawn_other_legal_entity | 1.00 | LCR99 undrawn facilities, other legal entities |
| net_derivative_outflow | 1.00 | LCR99 net derivative outflows |
| other_contractual_outflow | 1.00 | LCR99 other contractual outflows |

Trade finance contingent outflows are 0 to 0.05 at national discretion (a caller-supplied rate within that interval, never a default), and
the downgrade-trigger and derivative look-back items are amounts (the largest absolute net 30-day collateral flow in the preceding 24
months), not rates. Key inflow rates (`LCR_INFLOW_RATES`; inflows are capped at 0.75 of gross outflows, LCR40.1 and LCR99):

| key | rate | reference |
|---|---|---|
| secured_lending_level1 | 0.00 | LCR99 maturing secured lending backed by Level 1 |
| secured_lending_level2a | 0.15 | LCR99 backed by Level 2A |
| secured_lending_level2b_rmbs | 0.25 | LCR99 backed by eligible RMBS |
| secured_lending_other_level2b | 0.50 | LCR99 backed by other Level 2B |
| secured_lending_other | 1.00 | LCR99 other collateral |
| margin_lending_other_collateral | 0.50 | LCR99 margin lending on other collateral |
| facilities_granted_to_bank | 0.00 | LCR99 facilities granted to the bank |
| operational_deposits_at_other_institutions | 0.00 | LCR99 operational deposits held at other institutions |
| retail_and_nonfinancial_wholesale | 0.50 | LCR99 retail and non-financial wholesale inflows |
| financial_institutions_and_central_banks | 1.00 | LCR99 financial institutions and central banks |
| net_derivative_inflow | 1.00 | LCR99 net derivative inflows |

HQLA haircuts (`HQLA_HAIRCUTS`, LCR30 and LCR99 table; Level 2A LCR30.43, Level 2B LCR30.45):

| key | haircut | reference |
|---|---|---|
| level_1 | 0.00 | LCR30 Level 1, no haircut (factor 100 percent) |
| level_2a | 0.15 | LCR30.43 Level 2A |
| level_2b_rmbs | 0.25 | LCR30.45 qualifying RMBS |
| level_2b_corporate_debt | 0.50 | LCR30.45 qualifying corporate debt A+ to BBB- |
| level_2b_common_equity | 0.50 | LCR30.45 qualifying common equity |
| level_2b_sovereign_bbb | 0.50 | LCR30.45 sovereign BBB+ to BBB- within the 15 percent cap (FAQ) |

### NSFR parameters (`lcr_nsfr.NSFR_ASF_FACTORS`, `NSFR_RSF_FACTORS`)

NSF20 (NSF20.2), NSF30 and NSF99 Tables 1 to 3 (in force 2019-12-15), from dossier 01 G.2; the selection the dossier prints:

| key | factor | reference |
|---|---|---|
| regulatory_capital | 1.00 | NSF99 ASF: regulatory capital excluding Tier 2 with residual maturity under one year |
| long_term_liabilities_ge_1y | 1.00 | NSF99 ASF: other capital and liabilities with effective residual maturity of one year or more |
| stable_retail_deposits | 0.95 | NSF99 ASF: stable retail and small business deposits (non-maturity or under one year) |
| less_stable_retail_deposits | 0.90 | NSF99 ASF: less stable retail and small business deposits |
| funding_lt_1y_non_financial_corporates | 0.50 | NSF99 ASF: funding under one year from non-financial corporates |
| operational_deposits | 0.50 | NSF99 ASF: operational deposits |
| funding_lt_1y_sovereigns_pse_mdb_ndb | 0.50 | NSF99 ASF: funding under one year from sovereigns, PSEs, MDBs, NDBs |
| other_funding_6m_to_1y | 0.50 | NSF99 ASF: other funding of 6 months to under one year including central banks and financial institutions |
| other_liabilities | 0.00 | NSF99 ASF: all other liabilities and equity, net derivative liabilities, trade-date payables |

| key | factor | reference |
|---|---|---|
| coins_banknotes_reserves | 0.00 | NSF99 RSF: coins, banknotes, central bank reserves, central bank claims under 6 months, trade-date receivables |
| unencumbered_level_1 | 0.05 | NSF99 RSF: unencumbered Level 1 excluding cash and reserves |
| loans_fi_lt_6m_level1_secured | 0.10 | NSF99 RSF: loans to financial institutions under 6 months secured by Level 1 with rehypothecation ability |
| loans_fi_lt_6m_other | 0.15 | NSF99 RSF: other unencumbered loans to financial institutions under 6 months |
| unencumbered_level_2a | 0.15 | NSF99 RSF: unencumbered Level 2A |
| unencumbered_level_2b | 0.50 | NSF99 RSF: unencumbered Level 2B |
| encumbered_hqla_6m_to_1y | 0.50 | NSF99 RSF: HQLA encumbered 6 months to under one year |
| loans_fi_6m_to_1y | 0.50 | NSF99 RSF: loans to financial institutions and central banks 6 months to under one year |
| other_assets_lt_1y | 0.50 | NSF99 RSF: all other assets under one year (corporate, retail, sovereign loans) |
| residential_mortgages_ge_1y_rw35 | 0.65 | NSF99 RSF: unencumbered residential mortgages of one year or more, SA risk weight at most 35 percent |
| other_loans_ge_1y_rw35 | 0.65 | NSF99 RSF: other loans of one year or more, risk weight at most 35 percent |
| initial_margin_ccp_default_fund | 0.85 | NSF99 RSF: initial margin and CCP default fund |
| other_loans_ge_1y_rw_gt_35 | 0.85 | NSF99 RSF: other performing loans of one year or more, risk weight above 35 percent |
| non_hqla_securities_ge_1y | 0.85 | NSF99 RSF: non-HQLA securities of one year or more and exchange-traded equities |
| physical_commodities | 0.85 | NSF99 RSF: physical commodities including gold |
| encumbered_ge_1y | 1.00 | NSF99 RSF: assets encumbered one year or more |
| net_derivative_assets | 1.00 | NSF99 RSF: net derivative assets |
| other_assets | 1.00 | NSF99 RSF: all other assets including NPLs and fixed assets |
| undrawn_facilities_obs | 0.05 | NSF99 RSF: irrevocable and conditionally revocable credit and liquidity facilities, 5 percent of the undrawn amount |

The derivative liabilities add-on (NSF30.8, dossier 01 G.2: "5% to 20% of derivative liabilities") is not a fixed factor: `derivative_liabilities_addon` is a caller-supplied rate within [0.05, 0.20], never a default, as trade finance is in the LCR (the in-force value is the supervisor's). `nsfr_rsf` raises `ValueError` naming it for a rate outside the interval.

## Module `riskvalidation/liquidity/_checks.py`

Input checks naming the offending field; they import `validation._common.as_float_array` and add only what the per-package `_checks.py` of
`oprisk`, `lgd_ead` and `provisions` do not hold. Each returns the validated array and raises `ValueError(f"{name}: {reason}, got {value}")`.

### `riskvalidation.liquidity._checks.check_nonnegative_stock`

```python
def check_nonnegative_stock(x: np.ndarray | float, name: str) -> np.ndarray: ...
```

- Units: money (USD thousands) of any shape; the result is the `float64` array.
- Invariants: a negative or non-finite entry raises, naming `name`; an empty array raises; zero is allowed.
- Golden: `check_nonnegative_stock([0.0, 5.0], "balance")` returns `[0.0, 5.0]`; `check_nonnegative_stock([-1.0], "balance")` raises `ValueError` starting `balance: must be non-negative`.

### `riskvalidation.liquidity._checks.check_unit_share`

```python
def check_unit_share(x: np.ndarray | float, name: str, closed: bool = True) -> np.ndarray: ...
```

- Units: shares or rates (decimals), closed `[0, 1]` when `closed`, else the open interval `(0, 1)`.
- Invariants: a value outside the interval or non-finite raises, naming `name`; a daily rate of exactly 0 or 1 is legitimate for a segment (a financial deposit leaves in full on day 1) and passes when `closed`.
- Golden: `check_unit_share([0.0, 1.0], "q")` passes; `check_unit_share(1.0, "q", closed=False)` and `check_unit_share(1.2, "q")` raise.

### `riskvalidation.liquidity._checks.check_weights_sum_to_one`

```python
def check_weights_sum_to_one(w: np.ndarray, name: str, tol: float = 1e-9) -> np.ndarray: ...
```

- Units: segment weights (shares) of shape `(S,)`.
- Invariants: every entry in `[0, 1]` and the sum within `tol` of 1, else `ValueError` naming `name`.
- Golden: `[0.057, 0.864, 0.079]` passes; `[0.5, 0.4]` raises (sum 0.9).

### `riskvalidation.liquidity._checks.check_increasing_grid`

```python
def check_increasing_grid(g: np.ndarray, name: str, minimum: float | None = None) -> np.ndarray: ...
```

- Units: a day grid or a multiplier grid, strictly increasing, optionally with every entry at least `minimum`.
- Invariants: a repeated or decreasing entry raises, naming `name` and the index.
- Golden: `[1, 2, 5]` passes; `[1, 1, 2]` raises; `[0.5, 1.0]` with `minimum=1.0` raises.

## Module `riskvalidation/liquidity/runoff.py`

Constant daily compounding and its inverse (05 E.1 line 237), the contractual roll-off rules, and the transcribed parameter sets as module
data (`LIST_PARAMETERS`, `TABLE_A1`, `SEGMENTS`, above). The arithmetic is that of `provisions.term_structure.from_hazard`, considered and
not reused: that function refuses a rate of exactly 0 or 1, both legitimate for a segment, and indexes months.

### `riskvalidation.liquidity.runoff.cumulative_outflow_constant`

```python
def cumulative_outflow_constant(q: np.ndarray | float, n: np.ndarray | int) -> np.ndarray | float: ...
```

- Units: `q` daily rate (decimal per relevant day) in `[0, 1]`; `n` relevant days (non-negative integer); the result is a share in `[0, 1]`.
- Invariants: `1 - (1 - q)^n`; zero at `n = 0` and at `q = 0`; one at `q = 1` for `n >= 1`; non-decreasing in `n` and in `q`; broadcasting follows NumPy.
- Golden: `q = 0.00103258`, `n = 125` gives `0.121148` (05 line 237), the dossier's 12.11 percent (the value is `0.12114837`); `q = 0.00161494`, `n = 125` gives `0.182930` (recomputed, not a dossier value); `q = 0.00688541`, `n = 2` gives `0.013723` (recomputed); `q = 0.00373218`, `n = 125` gives `0.373368` (recomputed).

### `riskvalidation.liquidity.runoff.cumulative_outflow_path`

```python
def cumulative_outflow_path(daily_rates: np.ndarray) -> np.ndarray: ...
```

- Units: `daily_rates` (H,) decimals per relevant day, one per day (a rate that changes with the stress state); the result (H,) cumulative shares.
- Invariants: `1 - cumprod(1 - q_d)`; non-decreasing; a constant path equals `cumulative_outflow_constant(q, 1..H)`; a rate of 1 on any day makes every later value 1.
- Golden: `[0.01, 0.02, 0.03]` gives `[0.01, 0.0298, 0.058906]` (`1 - 0.99 x 0.98 x 0.97`).

### `riskvalidation.liquidity.runoff.daily_rate_from_cumulative`

```python
def daily_rate_from_cumulative(share: np.ndarray | float, days: np.ndarray | int) -> np.ndarray | float: ...
```

- Units: `share` cumulative outflow in `[0, 1]`; `days` positive integer; the result a daily rate.
- Invariants: `q = 1 - (1 - F)^(1 / n)`, the inverse of `cumulative_outflow_constant`: the round trip returns `share` to `1e-12`; `share = 1` gives 1.
- Golden (recomputed from Table A.1, not dossier values): SVB `0.85` in `2` days gives `0.612702`; First Republic `0.57` in `90` gives `0.009334`; Northern Rock `0.20` in `4` gives `0.054258`; Icesave `0.20` in `75` gives `0.002971`; WaMu `0.10` in `10` gives `0.010481`; IndyMac `0.08` in `14` gives `0.005938`; Credit Suisse `0.21` in `90` gives `0.002616`; SVB UK `0.30` in `1` gives `0.3`; Signature `0.20` in `1` gives `0.2`.

### `riskvalidation.liquidity.runoff.contractual_rolloff`

```python
def contractual_rolloff(maturing: np.ndarray, outflow_rate: float) -> np.ndarray: ...
```

- Units: `maturing` (H,) money maturing on each day; `outflow_rate` the roll-off rate of the class (LiST Table 3.2, constant across maturities, para 94); the result (H,) outflows.
- Invariants: `outflow = rate x maturing` day by day; the rolled-over remainder `(1 - rate) x maturing` stays past the horizon and is not returned; rate in `[0, 1]`.
- Golden: `maturing = [100.0, 50.0]`, `rate = 0.18` (stable retail, Adverse) gives `[18.0, 9.0]`; at `0.27` (Extreme) `[27.0, 13.5]`.

### `riskvalidation.liquidity.runoff.financial_no_rollover`

```python
def financial_no_rollover(maturing: np.ndarray) -> np.ndarray: ...
```

- Units: `maturing` (H,) money of interbank and other financial deposits maturing on each day.
- Invariants: maturing interbank and financial deposits do not roll over: the outflow equals the maturing flow (LiST para 98, rate 1.0, 05 E.1 line 237); the input is returned as a new array.
- Golden: `[100.0, 0.0, 25.0]` returns `[100.0, 0.0, 25.0]`.

## Module `riskvalidation/liquidity/cbc.py`

The counterbalancing capacity (05 E.1 line 238; LiST para 73 to 75). The LCR haircut is taken from `lcr_nsfr.HQLA_HAIRCUTS`, never a second table
(decision Q1); the central bank's haircut is the caller's (the Federal Reserve margins of A4, 1 minus the margin), with the fallback only where
the framework gives none.

### `riskvalidation.liquidity.cbc.haircut_rule`

```python
def haircut_rule(kind: str, *, central_bank_eligible: bool = False, central_bank_haircut: float | None = None,
                 hqla_level: str | None = None, equity_rating: str | None = None) -> tuple[float, str]: ...
```

- Units: `kind` one of `"cash"`, `"equity"`, `"non-equity"`; `central_bank_haircut` a share (1 minus the central bank margin); `hqla_level` a key of `HQLA_HAIRCUTS` or `None` (not HQLA); `equity_rating` one of `"AAA-A-"`, `"BBB+-BBB-"`, `"lower-or-unrated"`; the result is `(haircut, rule label)`, the label one of `nominal-value`, `central-bank-framework`, `lcr-haircut-hqla`, `fifty-percent-fallback`, `ecb-equity-table`, `ecb-non-equity-hqla`.
- Invariants: order of the note (para 74): cash, reserves and committed facilities at nominal value (haircut 0, para 73); a central-bank-eligible asset takes the central bank's haircut when it is given; when it cannot be determined, the LCR haircut if HQLA and 0.50 otherwise; a marketable asset not eligible takes the equity table (AAA to A- 0.20, BBB+ to BBB- 0.35, lower or unrated 0.50) for equities and 0.30 if HQLA under the LCR Delegated Regulation, 0.50 otherwise, for the rest; every haircut is returned with its rule label.
- Golden (05 line 238): equity `AAA-A-` gives `(0.20, "ecb-equity-table")`; `BBB+-BBB-` `(0.35, ...)`; `lower-or-unrated` `(0.50, ...)`; non-equity HQLA `(0.30, "ecb-non-equity-hqla")`; non-equity not HQLA `(0.50, "fifty-percent-fallback")`; central-bank-eligible with haircut `0.04` gives `(0.04, "central-bank-framework")`; eligible, undetermined, `level_2a` gives `(0.15, "lcr-haircut-hqla")`; eligible, undetermined, not HQLA gives `(0.50, "fifty-percent-fallback")`; cash gives `(0.0, "nominal-value")`.

### `riskvalidation.liquidity.cbc.liquidity_value`

```python
def liquidity_value(market_value: np.ndarray | float, haircut: np.ndarray | float, encumbered: np.ndarray | float = 0.0) -> np.ndarray | float: ...
```

- Units: money (USD thousands) and shares; the result money.
- Invariants: `(market_value - encumbered) x (1 - haircut)` with `0 <= encumbered <= market_value` and `haircut` in `[0, 1]` (LiST para 63: unencumbered assets only; para 74: market value less a haircut); monotone decreasing in the haircut.
- Golden: `liquidity_value(100.0, 0.2)` gives `80.0`; `liquidity_value(100.0, 0.1, encumbered=20.0)` gives `72.0`.

### `riskvalidation.liquidity.cbc.monetisation_capacity`

```python
def monetisation_capacity(value: float, points: Sequence[tuple[int, float]], horizon: int) -> np.ndarray: ...
```

- Units: `value` liquidity value; `points` the step schedule `(day, cumulative share)` (the named parameter `monetisation_schedule`, Q6; 05 line 276); the result (H,) the amount usable on each day.
- Invariants: the share of day `d` is that of the last point with `day <= d` (zero before the first point); shares are non-decreasing and at most 1; the result is `value x share(d)`.
- Golden: `value = 100.0`, `points = [(1, 0.5), (2, 0.8), (3, 1.0)]`, `horizon = 4` gives `[50.0, 80.0, 100.0, 100.0]`.

### `riskvalidation.liquidity.cbc.cbc_stack`

```python
def cbc_stack(classes: Mapping[str, tuple[float, float, float]], points: Sequence[tuple[int, float]], horizon: int) -> dict[str, np.ndarray]: ...
```

- Units: `classes` maps a class id to `(value used, encumbered, haircut)`; the result maps each class id to its (H,) liquidity value by day (the CBC stack of the ladder).
- Invariants: each class is `liquidity_value(...) x monetisation share(d)`; the sum over classes is `CBC(t)`; the engine keys are those of the document's `cbc_stack`.
- Golden: `{"A": (100.0, 20.0, 0.1), "B": (50.0, 0.0, 0.5)}`, `points = [(1, 1.0)]`, `horizon = 2` gives `A = [72.0, 72.0]` and `B = [25.0, 25.0]`.

### `riskvalidation.liquidity.cbc.cbc_with_htm_loss`

```python
def cbc_with_htm_loss(carrying: float, fair_value: float, encumbered: float, haircut: float) -> HtmResult: ...
```

- Units: money (USD thousands); `HtmResult` is a frozen dataclass `(unrealised_loss, cbc_without_loss, cbc_with_loss, cbc_removed)`.
- Invariants: `unrealised_loss = fair_value - carrying`; `cbc_without_loss = liquidity_value(carrying, haircut, encumbered)`; `cbc_with_loss = liquidity_value(fair_value, haircut, encumbered)`; `cbc_removed = cbc_without_loss - cbc_with_loss`, non-negative whenever `fair_value <= carrying` (05 lines 263 and 480); the encumbered amount is the same on both bases; the loss is a stated assumption pro rata by type, never a reported by-type loss (A3).
- Golden: `carrying = 100.0`, `fair_value = 85.0`, `encumbered = 20.0`, `haircut = 0.1` gives `unrealised_loss = -15.0`, `cbc_without_loss = 72.0`, `cbc_with_loss = 58.5`, `cbc_removed = 13.5`.

## Module `riskvalidation/liquidity/ladder.py`

The contractual and behavioural ladders, the net liquidity position and the survival period (05 E.1 lines 234 to 236, E.5).

### `riskvalidation.liquidity.ladder.contractual_gaps`

```python
def contractual_gaps(inflows: np.ndarray, outflows: np.ndarray) -> tuple[np.ndarray, np.ndarray]: ...
```

- Units: `inflows`, `outflows` (B,) money per contractual bucket (05 E.5 rung 1; the SRP50 contractual maturity mismatch tool, 01 G.3 lines 642 and 643); the result is `(gap, cumulative_gap)` (B,) each.
- Invariants: `gap = inflows - outflows`; `cumulative_gap = cumsum(gap)`; the last cumulative gap is the sum of all gaps.
- Golden: `inflows = [10, 20, 30]`, `outflows = [40, 10, 5]` gives `gap = [-30, 10, 25]` and `cumulative_gap = [-30, -20, 5]`.

### `riskvalidation.liquidity.ladder.behavioural_outflows`

```python
def behavioural_outflows(opening: np.ndarray, daily_rates: np.ndarray) -> np.ndarray: ...
```

- Units: `opening` (S,) money; `daily_rates` (S, H) decimals per relevant day; the result (S, H) outflows by segment and day.
- Invariants: each row is `opening x diff(cumulative_outflow_path(rates), prepend=0)`; the row sum is `opening x cumulative_outflow_path(rates)[-1]`; the stock never goes negative (a rate of 1 empties it).
- Golden: `opening = [100.0]`, `daily_rates = [[0.1, 0.1]]` gives `[[10.0, 9.0]]` (the second day is `90 x 0.1`).

### `riskvalidation.liquidity.ladder.net_liquidity_position`

```python
def net_liquidity_position(cbc: np.ndarray, outflows: np.ndarray, inflows: np.ndarray) -> np.ndarray: ...
```

- Units: `cbc`, `outflows`, `inflows` (H,) money by day (the CBC available on day t, and the stressed outflows O(s) and inflows I(s)); the result (H,) NLP.
- Invariants: `NLP(t) = CBC(t) - sum over s <= t of (O(s) - I(s))` (05 E.1 line 234); equal length required; the input arrays are not mutated.
- Golden: `cbc = [100, 100, 100, 100]`, `outflows = [30, 40, 50, 60]`, `inflows = [0, 10, 0, 0]` gives `[70.0, 40.0, -10.0, -70.0]` (hand computed).

### `riskvalidation.liquidity.ladder.survival_period`

```python
def survival_period(nlp: np.ndarray) -> SurvivalResult: ...
```

- Units: `nlp` (H,) money; `SurvivalResult` is a frozen dataclass `(survives: bool, day: int | None, horizon: int)`.
- Invariants: `SP = min{t : NLP(t) < 0}` (05 E.1 line 235), counted from day 1; a zero NLP is not negative; a position that never turns negative returns `survives = True`, `day = None` and `horizon = H`: "survives the horizon" with the horizon, never a number.
- Golden: `[70.0, 40.0, -10.0, -70.0]` gives `day = 3`, `survives = False`; `[5.0, 4.0, 3.0]` gives `survives = True`, `day = None`, `horizon = 3`; `[1.0, 0.0, 0.0]` gives `survives = True`.

### `riskvalidation.liquidity.ladder.minimum_nlp`

```python
def minimum_nlp(nlp: np.ndarray) -> tuple[float, int]: ...
```

- Units: `nlp` (H,) money; the result `(minimum value, day)`.
- Invariants: the day is the first day on which the minimum is reached (day 1 is the first); the value is `nlp.min()`.
- Golden: `[70.0, 40.0, -10.0, -70.0]` gives `(-70.0, 4)`; `[5.0, 3.0, 3.0]` gives `(3.0, 2)`.

### `riskvalidation.liquidity.ladder.cliff_effect`

```python
def cliff_effect(nlp: np.ndarray, total_assets: float, near: int = 30, far: int = 35) -> float: ...
```

- Units: `nlp` (H,) money; `total_assets` money, positive; `near` and `far` days (the named parameter `cliff_days`; the LiST note does not say whether they count calendar or relevant days, UNVERIFIED); the result is a share of total assets.
- Invariants: `(NLP(far) - NLP(near)) / TA` (05 E.1 line 236), a diagnostic of LCR window optimisation, negative when the position drops; a horizon shorter than `far` raises `ValueError` naming it (the document then holds the cliff null with its reason).
- Golden: `NLP(30) = 100`, `NLP(35) = 40`, `total_assets = 1000` gives `-0.06`; `NLP(30) = 100`, `NLP(35) = 95` gives `-0.005`; a 30-day ladder raises.

## Module `riskvalidation/liquidity/scenarios.py`

Scenario families (idiosyncratic, market-wide, combined) and phases (acute 1 to 5 days, protracted up to 6 to 12 months), composed from the parameter
sets of `runoff.py` and the haircuts of `cbc.py` (05 E.2 line 244, E.5 line 277). `Scenario` and `ListScenario` are frozen dataclasses.

### `riskvalidation.liquidity.scenarios.list_scenario`

```python
def list_scenario(severity: str) -> ListScenario: ...
```

- Units: `severity` is `"baseline"`, `"adverse"` or `"extreme"`; `ListScenario` holds the open-maturity daily rates by LiST class, the contractual roll-off rates, the inflow rates, the committed-facility drawdown rates and `relevant_days = 125`.
- Invariants: the values are `LIST_PARAMETERS` exactly (no stable-retail proxy for uninsured corporate balances: the fastest sight class runs at its own rate, A1); the LiST shocks are idiosyncratic only (annex slide 5); an unknown severity raises.
- Golden: `list_scenario("adverse")` has `stable_retail = 0.00103258` and `non_operational_non_financial_corporates = 0.00688541`; `"extreme"` has `0.00161494` and `0.01065229`; `cumulative_outflow_constant(0.00103258, 125) = 0.121148`.

### `riskvalidation.liquidity.scenarios.compose_scenario`

```python
def compose_scenario(family: str, phase: str, parameter_set: ListScenario | FastRun, segments: Mapping[str, tuple[str, float]],
                     horizon: int) -> Scenario: ...
```

- Units: `family` one of `idiosyncratic`, `market-wide`, `combined`; `phase` one of `acute`, `protracted`; `segments` maps a segment id to `(LiST class, opening balance)`; `horizon` days; the result carries per segment the daily-rate path (H,).
- Invariants: every segment's rates are those of its class in the parameter set; a class the set does not hold raises (it is never mapped silently); a financial-customer sight class has rate 1.0 and empties the stock on day 1 (LiST para 111); the opening balances are not altered; the mapping of a variant to a family and phase is the named parameter `variant_scenarios`.
- Golden: `segments = {"retail": ("other-retail", 100.0)}`, Adverse, `horizon = 2` gives the rates `[0.00373218, 0.00373218]` and the outflows `[0.373218, 0.371825...]` (day 2 is `99.626782 x 0.00373218`); an unmapped class `"xyz"` raises.

### `riskvalidation.liquidity.scenarios.fast_run_scenario`

```python
def fast_run_scenario(rows: Sequence[tuple[float, int]], rule: str = "maximum-implied-daily-rate") -> FastRun: ...
```

- Units: `rows` the Table A.1 `(outflow share, days)` pairs the caller selects (pre-2023 only for the scored variant, Q4); `rule` one of `maximum-implied-daily-rate`, `median-implied-daily-rate`, `mean-implied-daily-rate` (the named parameter `fast_run_calibration_rule`); the result `FastRun` has the daily rate for the concentrated uninsured segment (decimal per relevant day) and the implied rates it came from.
- Invariants: each row's rate is `daily_rate_from_cumulative`; the fitted rate is the rule's statistic of the implied rates; the dossiers give no calibration method (UNVERIFIED), so the rule is a convention; calibration on the 2023 rows is refused with a message when the caller marks them scored.
- Golden (recomputed): the rows Icesave `(0.20, 75)`, Northern Rock `(0.20, 4)`, WaMu `(0.10, 10)`, IndyMac `(0.08, 14)` give the implied rates `[0.002971, 0.054258, 0.010481, 0.005938]` and the fitted rate `0.054258` (maximum), `0.0082095` (median) or `0.018412` (mean).

### `riskvalidation.liquidity.scenarios.anchor_from_observation`

```python
def anchor_from_observation(outflow_share: float, days: int) -> dict[str, float | int | bool]: ...
```

- Units: `outflow_share` in `[0, 1]`, `days` a positive integer; the result `{"outflow_share", "days", "implied_daily_rate", "forecast_claim": False}`.
- Invariants: the anchor row of Q4: the observed outflow and the daily rate it implies; `forecast_claim` is always `False` (the observation is never a forecast); the rate round-trips through `cumulative_outflow_constant`.
- Golden: `anchor_from_observation(0.85, 2)` gives `implied_daily_rate = 0.612702` (recomputed); `(0.20, 4)` gives `0.054258`.

### `riskvalidation.liquidity.scenarios.uninsured_share_grid`

```python
def uninsured_share_grid(insured: float, uninsured: float, shares: Sequence[float]) -> list[tuple[float, float]]: ...
```

- Units: `insured` and `uninsured` money of the call report (DEPINS, DEPUNA); `shares` the grid (the named parameter `uninsured_share_grid`); the result is one `(insured, uninsured)` pair per share.
- Invariants: the total `insured + uninsured` is preserved in every pair; `uninsured / total = share`; shares must lie in `[0, 1]` and increase (05 line 278).
- Golden: `insured = 40.0`, `uninsured = 60.0`, `shares = [0.5, 0.9]` gives `[(50.0, 50.0), (10.0, 90.0)]`.

### `riskvalidation.liquidity.scenarios.htm_loss_grid`

```python
def htm_loss_grid(reported_loss: float, multiples: Sequence[float]) -> list[float]: ...
```

- Units: `reported_loss` money (the HTM unrealised loss `SCHF - SCHA`, negative); `multiples` the grid (the named parameter `htm_loss_multiple_grid`); the result is the loss at each multiple.
- Invariants: `reported_loss x multiple`; a multiple of 0 removes the loss and 1 is the reported loss; multiples are non-negative and increase (05 line 278).
- Golden: `reported_loss = -15.0`, `multiples = [0.0, 1.0, 2.0]` gives `[0.0, -15.0, -30.0]`.

## Module `riskvalidation/liquidity/reverse.py`

Reverse liquidity stress (05 E.5 rung 5, line 279): the multiplier on the run-off rates at which the survival period first falls to the target (the dossier's example is 30 days, the named
parameter `reverse_target_days`), applied to every segment of a base scenario and capped so that each rate stays below 1 (Q9).

### `riskvalidation.liquidity.reverse.survival_vs_multiplier`

```python
def survival_vs_multiplier(scenario: Scenario, cbc: np.ndarray, multipliers: np.ndarray) -> list[SurvivalResult]: ...
```

- Units: `scenario` as composed by `compose_scenario`; `cbc` (H,) the CBC by day; `multipliers` increasing and at least 1; the result one `SurvivalResult` per multiplier.
- Invariants: each segment's rate becomes `min(m x q, 1)` (a rate already at 1 stays); `SP(m)` is non-increasing in `m` ("survives the horizon" counts as longer than any day); a multiplier beyond the cap `1 / max(q < 1)` is refused and the document omits that point.
- Golden: one segment, opening `1000.0`, `q = 0.01`, constant `cbc = 100.0`, `H = 125`: `m = 1` gives `SP = 11` (`0.99^t < 0.9` first at `t = 11`); the curve over `[1, 2, 3]` is non-increasing.

### `riskvalidation.liquidity.reverse.solve_multiplier`

```python
def solve_multiplier(scenario: Scenario, cbc: np.ndarray, target_days: int) -> SolveResult: ...
```

- Units: `target_days` an integer below the horizon; `SolveResult` is a frozen dataclass `(status, multiplier, survival_at_multiplier, reason)`, `status` one of `"solved"`, `"refused"`.
- Invariants: the smallest `m` (rounded up to six decimals) at which `SP(m) <= target_days`, solved on the monotone `SP(m)` by bracketing with `scipy.optimize.brentq`, never above the cap; the round trip holds: `survival_at_multiplier == target_days` within the named tolerance `round_trip_tolerance_days`; a target that is not bracketed (the base survival period already at or below it, no multiplier under the cap reaches it, or a target not below the horizon) is refused with the reason, never a number.
- Golden: the one-segment bank of `survival_vs_multiplier` and `target_days = 5` gives `multiplier = 2.085164` (`1 - 0.9^(1/5) = 0.0208516`, divided by `q`, rounded up), `survival_at_multiplier = 5` and `SP = 6` just below it; `target_days = 125` is refused (not below the horizon); `target_days = 100` is refused when the base `SP` is 11.

## Module `riskvalidation/liquidity/deposits.py`

The depositor generator with known truth (08 G.2 line 698; the generator contract of `generators._base`: a frozen configuration, one dataset per seed, an exact truth, a verifier). Placement in the engine, option (a), no
concentration parameter (Q10). This contract fixes the mechanism: a systemic two-state Markov chain over days (state 0 calm on day 1, calm to stress with probability `p_enter` and stress to calm with
`p_exit` per day, shared by all depositors) and, per segment, a withdrawal hazard `h_calm` or `h_stress` by the state of the day, equal balances within a segment. The stress-state transition law has
no dossier basis and is a convention (UNVERIFIED, listed below).

### `riskvalidation.liquidity.deposits.DepositorConfig`

```python
@dataclass(frozen=True)
class DepositorSegment:
    segment: str                 # one of SEGMENTS
    share_of_deposits: float     # share of the call-report deposits, in [0, 1]
    calm_daily_hazard: float     # in [0, 1]
    stress_daily_hazard: float   # in [0, 1]
    p_enter_stress: float        # per day, in [0, 1]
    p_exit_stress: float         # per day, in [0, 1]

@dataclass(frozen=True)
class DepositorConfig:
    segments: tuple[DepositorSegment, ...]
    n_depositors: int            # per segment, positive
    horizon_days: int            # positive
```

- Units: hazards and probabilities are decimals per relevant day; shares sum to 1 (`check_weights_sum_to_one`); the configuration serialises through `GeneratorBase.config()` into the `generator.config` block of `c16-models`.
- Invariants: frozen and hashable; a share vector that does not sum to one, a probability outside `[0, 1]` or a non-positive count raises `ValueError` naming the field; every segment id is in `SEGMENTS`.
- Golden: a configuration of one segment with `share_of_deposits = 1.0` passes; `0.9` raises; the three-segment shares `0.057, 0.864, 0.079` sum to 1.0.

### `riskvalidation.liquidity.deposits.DepositorGenerator`

```python
class DepositorGenerator(GeneratorBase):
    name = "depositors"
    def __init__(self, config: DepositorConfig) -> None: ...
    def draw(self, rng: np.random.Generator) -> dict[str, Any]: ...
    def truth(self) -> dict[str, Any]: ...
    def verify(self, n_draws: int = 20_000, seed: int = 20261005) -> list[Check]: ...
```

- Units: `draw` returns `{"state": (H,) int array, "withdrawn_day": {segment: (n,) int array, 0 = not within the horizon}, "outflow_rate": {segment: (H,) cumulative share}}`; `truth()` returns `{"outflow_rate": {segment: (H,) exact expected cumulative outflow share by horizon}}`; `verify` returns the `Check` list of `generators._base` (expected, observed, se).
- Invariants: one seed gives one dataset; the truth is computed exactly by the transfer recursion `u_1 = (1 - h_calm, 0)`, `u_{d+1} = ((u_d P) elementwise (1 - h_calm, 1 - h_stress))`, `truth(n) = 1 - sum(u_n)`; the truth is non-decreasing in the horizon; a large draw reproduces it within Monte Carlo error (the document's `generator.verification`, judged by the named parameters `generator_truth_se_green` and `generator_truth_se_red`).
- Golden: `h_calm = 0.001`, `h_stress = 0.01`, `p_enter = 1`, `p_exit = 0`: `truth` at horizons 1, 2, 3 is `0.001`, `0.01099` and `0.0208801` (`1 - 0.999 x 0.99 x 0.99`); with `p_enter = 0` the truth is `1 - (1 - h_calm)^n` (the constant compounding of `runoff.py`).

## Module `riskvalidation/regulatory/lcr_nsfr.py`

The LCR and the NSFR (decision Q1; U9 writes neither): the formulas of dossier 01 G.1 and G.2 with the parameters above as data, each with its paragraph and in-force date (2019-12-15, 01 M.3 item 8). The categories are inputs the caller maps to (the C16 mapping table, decision Q13).
Results are frozen dataclasses.

### `riskvalidation.regulatory.lcr_nsfr.hqla_stock`

```python
def hqla_stock(l1: float, l2a: float, l2b: float, adjusted_l1: float | None = None, adjusted_l2a: float | None = None,
               adjusted_l2b: float | None = None) -> HqlaResult: ...
```

- Units: money (USD thousands) after haircuts; the adjusted amounts (after unwinding short-term SFTs and collateral swaps maturing within 30 days, LCR30.37) default to the unadjusted ones; `HqlaResult` is `(l1, l2a, l2b, adj_15, adj_40, hqla, l2_share, l2b_share)`.
- Invariants: `HQLA = L1 + L2A + L2B - Adj15 - Adj40` (LCR30.38); `Adj15 = max(aL2B - 15/85 (aL1 + aL2A), aL2B - 15/60 aL1, 0)` and `Adj40 = max(aL2A + aL2B - Adj15 - two-thirds aL1, 0)` (LCR30.39); Level 1 is unlimited; Level 2 is at most 0.40 of HQLA (LCR30.31) and Level 2B at most 0.15 (LCR30.33), both after haircuts (LCR30.34); adjusted Level 2 is at most two-thirds of adjusted Level 1 (LCR30.35); Level 2B alone never exceeds 15/85 of Level 1 plus Level 2A after adjustment; `l2b_share = (L2B - Adj15) / HQLA` and `l2_share = (L2A + L2B - Adj15 - Adj40) / HQLA`; negative inputs raise.
- Golden (constructed, 01 M.1; no official example exists): `(100, 20, 30)` gives `adj_15 = 8.823529`, `adj_40 = 0`, `hqla = 141.176471`, `l2b_share = 0.15`; `(100, 80, 0)` gives `adj_15 = 0`, `adj_40 = 13.333333`, `hqla = 166.666667`, `l2_share = 0.40`; `(100, 0, 0)` gives `hqla = 100` (Level 1 only).

### `riskvalidation.regulatory.lcr_nsfr.lcr_outflows`

```python
def lcr_outflows(balances: Mapping[str, float], rates: Mapping[str, float] | None = None) -> OutflowResult: ...
```

- Units: `balances` maps a key of `LCR_OUTFLOW_RATES` to a money balance; `rates` overrides (the trade finance rate within 0 to 0.05 is supplied here); `OutflowResult` is `(total, rows)` with one `(key, balance, rate, amount, reference)` row per category.
- Invariants: `amount = balance x rate` (LCR40 and LCR99); the total is the sum of the amounts; a key outside the table raises `KeyError` naming it; the engine does not map customers to categories.
- Golden: `{"retail_stable": 1000.0}` gives `total = 50.0`; `{"retail_less_stable": 100.0, "non_financial_corporate": 100.0, "other_legal_entity": 10.0}` gives `10.0 + 40.0 + 10.0 = 60.0`.

### `riskvalidation.regulatory.lcr_nsfr.lcr_inflows`

```python
def lcr_inflows(balances: Mapping[str, float], rates: Mapping[str, float] | None = None) -> OutflowResult: ...
```

- Units: as `lcr_outflows`, with the keys of `LCR_INFLOW_RATES`.
- Invariants: `amount = balance x rate`; the sum is the gross inflow before the cap; keys outside the table raise `KeyError`.
- Golden: `{"retail_and_nonfinancial_wholesale": 100.0}` gives `50.0`; `{"secured_lending_level2a": 100.0}` gives `15.0`.

### `riskvalidation.regulatory.lcr_nsfr.net_cash_outflows`

```python
def net_cash_outflows(outflows: float, inflows: float, cap: float = 0.75) -> NetOutflowResult: ...
```

- Units: money; `cap` the inflow cap share (0.75, LCR40.1); `NetOutflowResult` is `(inflows_counted, net, cap_binds)`.
- Invariants: `net = outflows - min(inflows, 0.75 x outflows)` (LCR40.1); inflows never offset more than 0.75 of outflows, so `net >= 0.25 x outflows`; `cap_binds` is `inflows > 0.75 x outflows`.
- Golden: `(100.0, 90.0)` gives `inflows_counted = 75.0`, `net = 25.0`, `cap_binds = True`; `(100.0, 50.0)` gives `50.0`, `50.0`, `False`.

### `riskvalidation.regulatory.lcr_nsfr.lcr_ratio`

```python
def lcr_ratio(hqla: float, net_outflows: float) -> float: ...
```

- Units: money; the result a ratio (1.0 is 100 percent), `LCR = HQLA / net outflows` (LCR20.4, at least 1.0 required in normal times; a ratio below 1.0 under stress is not a breach, 01 J.3).
- Invariants: `net_outflows <= 0` raises `ValueError` (the ratio is undefined, never infinite); a negative HQLA raises; the label "a Basel formula on call-report aggregates, never the bank's reported or regulatory LCR" is the caller's, required in the document.
- Golden (closed form, a balance sheet of Level 1 and stable retail deposits only): `hqla = 100.0` and `lcr_outflows({"retail_stable": 1000.0}).total = 50.0` give `2.0`; `lcr_ratio(100.0, 0.0)` raises.

### `riskvalidation.regulatory.lcr_nsfr.nsfr_asf`

```python
def nsfr_asf(liabilities: Mapping[str, float], factors: Mapping[str, float] | None = None) -> float: ...
```

- Units: money by key of `NSFR_ASF_FACTORS`; the result is the available stable funding.
- Invariants: `ASF = sum of factor x amount` (NSF20.2, NSF99 Table 1); keys outside the table raise `KeyError`; negative amounts raise.
- Golden: `{"regulatory_capital": 10.0, "stable_retail_deposits": 100.0}` gives `10 + 95 = 105.0`.

### `riskvalidation.regulatory.lcr_nsfr.nsfr_rsf`

```python
def nsfr_rsf(assets: Mapping[str, float], obs: Mapping[str, float] | None = None, factors: Mapping[str, float] | None = None,
             derivative_liabilities: float = 0.0, derivative_liabilities_addon: float | None = None) -> float: ...
```

- Units: money by key of `NSFR_RSF_FACTORS` (assets) and off-balance-sheet undrawn amounts (`obs`, keyed `undrawn_facilities_obs`), the gross derivative liabilities and their add-on rate (a share within `[0.05, 0.20]`, NSF30.8); the result is the required stable funding.
- Invariants: `RSF = sum of factor x asset + sum of factor x OBS` (NSF20.2, NSF99 Tables 2 and 3); keys outside the table raise `KeyError`; negative amounts raise; `derivative_liabilities > 0` with `derivative_liabilities_addon` left `None` or outside `[0.05, 0.20]` raises `ValueError` naming `derivative_liabilities_addon` (no default rate); the add-on is `derivative_liabilities x derivative_liabilities_addon`.
- Golden: `{"unencumbered_level_2b": 100.0}` gives `50.0`; adding `obs = {"undrawn_facilities_obs": 100.0}` gives `55.0`; with that `obs` and `derivative_liabilities = 200.0` at `derivative_liabilities_addon = 0.10` it gives `75.0` (55 + 20), and a rate of `0.25` raises.

### `riskvalidation.regulatory.lcr_nsfr.nsfr_ratio`

```python
def nsfr_ratio(asf: float, rsf: float) -> float: ...
```

- Units: money; the result a ratio, `NSFR = ASF / RSF` (NSF20.2, at least 1.0).
- Invariants: `rsf <= 0` raises `ValueError`; the ratio is monotone increasing in ASF and decreasing in RSF.
- Golden: `nsfr_ratio(105.0, 50.0)` gives `2.1`; `nsfr_ratio(10.0, 0.0)` raises.

## Module `riskvalidation/validation/liquidity.py`

The tests of the Problem section of the unit sizing, each a `TestResult` with `reference`, `h0`, the policy label `contraste-liquidity-battery-1.0.0` and its thresholds in `policy_version` and `extras["thresholds"]`, as
`validation/irrbb.py` and `validation/oprisk.py` do (plain functions that do not read the default policy); the lights are conventions and are never presented as regulatory. The tests of
`lcr_nsfr.py` are constructed tests and invariants (`tests/liquidity/test_lcr_nsfr.py`, since U9-E1 owns `tests/regulatory/`), not `TestResult` functions.

### `riskvalidation.validation.liquidity.list_compounding_golden`

```python
def list_compounding_golden(q: float = 0.00103258, n: int = 125, expected: float = 0.121148, tol: float = 5e-7) -> TestResult: ...
```

- Units: `q` daily rate (decimal per relevant day), `n` relevant days, `expected` and `tol` shares; the statistic is `abs(1 - (1 - q)^n - expected)` and the metric the computed cumulative outflow.
- Test id: `test_id = "liq.list_compounding_golden"`; `reference` cites 05 line 237 and the SDD acceptance row.
- Light: green when the statistic is at most `tol`, red otherwise; `extras["thresholds"] = {"tolerance": tol}` (the named parameter `list_compounding_tolerance`).
- Golden: the defaults give metric `0.1211484` (`0.12114837`), statistic `3.7e-7` and green; `expected = 0.12` gives red.

### `riskvalidation.validation.liquidity.survival_monotone_in_severity`

```python
def survival_monotone_in_severity(survival_days: Sequence[float | None], tol_days: float = 0.0) -> TestResult: ...
```

- Units: `survival_days` ordered from the mildest to the most severe scenario, in relevant days; `None` is "survives the horizon" and counts as longer than any day; the statistic is the largest increase of the survival period along the order, in days.
- Test id: `test_id = "liq.survival_monotone_in_severity"`; SDD l.329, 05 line 480.
- Light: green when no step lengthens the survival period by more than `tol_days` (the named parameter `monotonicity_tolerance_days`), red otherwise; `extras["thresholds"] = {"tolerance_days": tol_days}`.
- Golden: `[None, 176, 122]` (the LiST 2019 median survival periods, Adverse then Extreme, 05 line 240, with a baseline longer than the horizon) is green with statistic 0; `[100, 120]` is red with statistic 20.

### `riskvalidation.validation.liquidity.cbc_haircut_rules`

```python
def cbc_haircut_rules(tol: float = 1e-12) -> TestResult: ...
```

- Units: none; it runs `cbc.haircut_rule` on the nine cases of 05 line 238 (the three equity bands, non-equity HQLA and not, central bank given, eligible and undetermined HQLA and not, cash) and compares the haircut and the rule label with the expected values; the statistic is the largest absolute haircut deviation, `n` is 9.
- Test id: `test_id = "liq.cbc_haircut_rules"`; 05 lines 238 and 480.
- Light: green when every haircut and label equals the expected one (deviation at most `tol`), red otherwise; `extras["thresholds"] = {"tolerance": tol}`.
- Golden: the engine as specified gives statistic 0.0, `n = 9` and green; a haircut table with `0.25` for `BBB+-BBB-` gives red.

### `riskvalidation.validation.liquidity.nlp_identity`

```python
def nlp_identity(cbc: np.ndarray, outflows: np.ndarray, inflows: np.ndarray, nlp: np.ndarray, tol: float = 1e-6) -> TestResult: ...
```

- Units: money (H,) arrays; the statistic is the largest absolute residual of `nlp - (cbc - cumsum(outflows - inflows))`, in USD thousands.
- Test id: `test_id = "liq.nlp_identity"`; 05 E.1 line 234 on hand-computed ladders.
- Light: green when the statistic is at most `tol` (the named parameter `nlp_identity_tolerance`), red otherwise; `extras["thresholds"] = {"tolerance": tol}`.
- Golden: the hand ladder `cbc = [100]*4`, `outflows = [30, 40, 50, 60]`, `inflows = [0, 10, 0, 0]`, `nlp = [70.0, 40.0, -10.0, -70.0]` gives statistic 0.0 and green; `nlp[0] = 71.0` gives statistic 1.0 and red.

### `riskvalidation.validation.liquidity.runoff_adequacy_back_test`

```python
def runoff_adequacy_back_test(modelled_share: float, realised_share: float, ratio_green: float = 0.8, ratio_amber: float = 0.5,
                              compared_at: str = "event-horizon", denominator: str | None = None) -> TestResult: ...
```

- Units: shares of the deposit base; `compared_at` is `"event-horizon"` or `"model-horizon"`; the statistic is the ratio `modelled_share / realised_share` and the metric the shortfall `realised_share - modelled_share`.
- Test id: `test_id = "liq.runoff_adequacy_back_test"`; a Basel outflow assumption back-tested against the observed rate (08 lines 566 to 568; 06 lines 971 to 973); a descriptive score on the real event, one observation, no p-value (Q5); `segment` is the denominator id.
- Light: green when the ratio is at least `ratio_green`, amber when at least `ratio_amber`, red below (the named parameters `scoring_ratio_green` and `scoring_ratio_amber`); `not_evaluated` when `realised_share` is 0; `extras["thresholds"]` holds both and `compared_at`.
- Golden: modelled `0.013723` (LiST Adverse after 2 days on non-operational non-financial corporates, recomputed) against `0.85` gives ratio `0.016145`, shortfall `0.836277` and red; `(0.85, 0.85)` gives ratio 1.0 and green; `(0.5, 0.85)` gives `0.588235` and amber.

### `riskvalidation.validation.liquidity.runoff_vs_generator_truth`

```python
def runoff_vs_generator_truth(estimated: np.ndarray, truth: np.ndarray, mc_se: np.ndarray, se_green: float = 2.0, se_red: float = 3.0) -> TestResult: ...
```

- Units: `estimated`, `truth` (K,) outflow rates by segment and horizon; `mc_se` (K,) Monte Carlo standard errors of the generator's verification (08 G.4 lines 739 to 742); the statistic is the largest `abs(estimated - truth) / mc_se`, in standard errors.
- Test id: `test_id = "liq.runoff_vs_generator_truth"`; 08 line 698; the generator test of Q5; `n` is `K`.
- Light: green when the statistic is at most `se_green`, amber when at most `se_red`, red above (the named parameters `generator_truth_se_green` and `generator_truth_se_red`); a zero or negative `mc_se` raises `ValueError`; `extras["thresholds"]` holds both.
- Golden: `estimated = truth` gives statistic 0.0 and green; one entry off by `2.5 x mc_se` gives 2.5 and amber; by `3.5 x mc_se` gives 3.5 and red.

### `riskvalidation.validation.liquidity.cliff_effect_diagnostic`

```python
def cliff_effect_diagnostic(nlp: np.ndarray, total_assets: float, near: int = 30, far: int = 35, amber: float = -0.01, red: float = -0.03) -> TestResult: ...
```

- Units: `nlp` (H,) money; shares of total assets; the statistic is `cliff_effect(nlp, total_assets, near, far)` and the metric `NLP(far) - NLP(near)` in money.
- Test id: `test_id = "liq.cliff_effect_diagnostic"`; 05 E.1 line 236 defines the diagnostic and no limit, so the lights are conventions (Q14).
- Light: green when the statistic is at least `amber`, amber when at least `red`, red below (the named parameters `cliff_amber_threshold` and `cliff_red_threshold`); `not_evaluated` with the reason in `notes` when the horizon is shorter than `far`; `extras["thresholds"]` holds both.
- Golden: `NLP(30) = 100`, `NLP(35) = 40`, `total_assets = 1000` gives `-0.06` and red; `100` to `95` gives `-0.005` and green; `100` to `80` gives `-0.02` and amber; a 30-day ladder gives `not_evaluated`.

### `riskvalidation.validation.liquidity.htm_loss_effect`

```python
def htm_loss_effect(cbc_without: float, cbc_with: float, survival_without: float | None, survival_with: float | None) -> TestResult: ...
```

- Units: money for the CBC; survival periods in relevant days with `None` as "survives the horizon" (longer than any day); the statistic is the CBC removed, `cbc_without - cbc_with`, and the metric its share of `cbc_without`.
- Test id: `test_id = "liq.htm_loss_effect"`; 05 lines 263, 278 and 480: the CBC and the survival period with and without HTM unrealised losses.
- Light: green when the unrealised loss does not raise the CBC (statistic at least 0) and does not lengthen the survival period, red otherwise; `extras["thresholds"] = {"tolerance": 0.0}`.
- Golden: `(72.0, 58.5, None, 48)` gives statistic `13.5`, metric `0.1875` and green; `(72.0, 80.0, 40, 60)` gives red.

### `riskvalidation.validation.liquidity.uninsured_share_sensitivity`

```python
def uninsured_share_sensitivity(shares: Sequence[float], survival_days: Sequence[float | None], tol_days: float = 0.0) -> TestResult: ...
```

- Units: `shares` increasing shares of domestic deposits (the named parameter `uninsured_share_grid`); `survival_days` the survival period under each share in relevant days, `None` surviving the horizon; the statistic is the largest increase of the survival period along the grid, in days.
- Test id: `test_id = "liq.uninsured_share_sensitivity"`; 05 line 278: the survival period does not lengthen as the uninsured share rises.
- Light: green when no step lengthens the survival period by more than `tol_days`, red otherwise; `extras["thresholds"] = {"tolerance_days": tol_days}`.
- Golden: `shares = [0.5, 0.9]`, `survival_days = [None, 67]` is green with statistic 0; `[40, 67]` is red with statistic 27.

### `riskvalidation.validation.liquidity.reverse_stress_round_trip`

```python
def reverse_stress_round_trip(solved_multiplier: float | None, survival_at_multiplier: int | None, target_days: int, tol_days: float = 0.0) -> TestResult: ...
```

- Units: the solved multiplier, the survival period it returns in relevant days, the target in days; the statistic is `abs(survival_at_multiplier - target_days)` and the metric the multiplier.
- Test id: `test_id = "liq.reverse_stress_round_trip"`; 05 line 279; `segment` is the base scenario id.
- Light: green when the statistic is at most `tol_days` (the named parameter `round_trip_tolerance_days`), red otherwise; `not_evaluated` with the reason when the multiplier is `None` (a refused solve); `extras["thresholds"] = {"tolerance_days": tol_days}`.
- Golden: `(2.085164, 5, 5)` gives statistic 0.0 and green; `(2.0, 7, 5)` gives 2.0 and red; `(None, None, 30)` gives `not_evaluated`.

### `riskvalidation.validation.liquidity.htm_revaluation_vs_reported`

```python
def htm_revaluation_vs_reported(model_fair_value: float | None, reported_fair_value: float, amortised_cost: float, green: float = 0.05, amber: float = 0.15) -> TestResult: ...
```

- Units: money; the HTM book revalued from its maturity profile under the Treasury curve through the engine's `irrbb` curves (`engine-irrbb-api`, decision Q11) against the reported fair value `SCHF`; the statistic is `abs(model - reported) / abs(reported - amortised)`, the share of the reported unrealised loss.
- Test id: `test_id = "liq.htm_revaluation_vs_reported"`; a model-against-reported validation row of the HTM variant.
- Light: green when the statistic is at most `green`, amber when at most `amber`, red above (the named parameters `htm_revaluation_green` and `htm_revaluation_amber`); `not_evaluated` with the reason when `model_fair_value` is `None` or the reported unrealised loss is 0; `extras["thresholds"]` holds both.
- Golden: `reported = 80.0`, `amortised = 100.0`: `model = 81.0` gives `0.05` and green; `82.0` gives `0.10` and amber; `85.0` gives `0.25` and red; `None` gives `not_evaluated`.

## Producer checks a bake calls

The cross-field rules JSON Schema cannot hold are functions, not test helpers: `tests/contracts_u11/semantics.py` (importable from the product, as the U10 checks are) exposes `check_document(doc) -> list[str]` (a non-empty list is a refusal to
publish), with `check_scenario`, `check_reverse`, `check_models` and `check_conventions_agree(docs)`. A bake calls `check_document` on every document it writes, after the schema. They check: the dating rule (no call report dated after the valuation
date), the recomputation of every run-off curve (`1 - prod(1 - q)`), the ladder totals, the CBC stack against the monetisation schedule, the NLP identity, the survival period (a day only where the NLP turns negative, "survives the horizon" with the horizon otherwise),
the minimum NLP and the cliff, the HQLA adjustments and caps, the LCR inflow cap and ratio, the HTM block and its par counterfactual, the scoring block (both denominators, the shortfall, the ratio and the light by the named parameters, the anchor's implied rate,
the Table A.1 rows), the reverse-stress curve (monotone, capped, the round trip) and the models document (the goldens, the calibration, the generator's shares), and that the named parameters are the same in every document of one bake.

## UNVERIFIED and open items

- The LiST relevant-day calendar is the 2019 TARGET2 calendar; the C16 ladder's US business-day calendar is a convention (A2) and every LiST cumulative figure says which calendar it is on.
- Collateral calls have no numeric parameter in the LiST note (addendum L1.5): a scenario input, labelled. The committed lines are not in the FDIC financials read: none is modelled and the document says so.
- Whether the cliff effect's day 30 and day 35 count calendar or relevant days (addendum L1.6): the named parameter `cliff_days` carries the basis.
- The calibration method of the fast run (the dossiers give none): the named parameter `fast_run_calibration_rule`; the monetisation schedule, the securities duration buckets, the deposit mapping and its band, the tolerances and the lights are conventions (Q13, Q14).
- The stress-state transition law of the depositor generator (a systemic two-state chain, calm on day 1) has no dossier basis; it is this contract's convention, and no concentration parameter is added (Q10).
- The FDIC names no call-report schedule or line for any field used (addendum L3); the fields are named by their FDIC names and titles. `DEPUNA` and `DEPINS` cover domestic offices (denominator `DEPDOM`) while `DEP` includes foreign offices; both denominators are stated where the uninsured share appears (A5).
- The held-to-maturity loss is not reported by type: it is applied to the book as a whole or pro rata, a stated assumption (A3). The Federal Reserve margins are those in force on 2023-03-10 (addendum L4); the Bank Term Funding Program par valuation is a labelled counterfactual from 2023-03-12.
- No official LCR or NSFR worked example exists (01 lines 1045 to 1046): the golden values of `lcr_nsfr.py` are constructed (01 M.1), not official.
- The licence classes of the BCBS d555 Table A.1 and of the ECB LiST parameters are readings of the notices (addendum L2.1 and L2.2), not legal advice; the BIS notice covering the Basel Framework pages of `lcr_nsfr.py` is read by analogy and stays UNVERIFIED for those pages.
- The upper edges of the contractual maturity buckets are a convention (SRP50 names none for the mismatch tool).
